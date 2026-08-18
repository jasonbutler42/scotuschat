"""
Unit tests for tenure date-range role resolution in api/services/speakers.py.

Tests cover (Phase 15, ROLE-01; Phase 37, PEOPLE-08/D-15):
  - _tenure_role_name: empty list returns None
  - _tenure_role_name: argued_date within a window returns that tenure's formal office title
  - _tenure_role_name: open-ended tenure (end_date=None) covers all dates past start
  - _tenure_role_name: argued_date outside all windows returns highest-start_date tenure's
    formal title (D-14)
  - _tenure_role_name: argued_date=None falls back to most-recent tenure (Pitfall 5)
  - _tenure_role_name: valid records always resolve to "Chief Justice"/"Associate Justice",
    never the generic "Justice" fallback (D-15)
  - ADVOCATE_LABEL_MAP: correct label for each SideEnum value

These tests do NOT require a live database — pure Python function tests.
"""

import datetime
import os

import pytest

from api.models.models import OFFICE_ASSOCIATE, OFFICE_CHIEF, SideEnum


# ---------------------------------------------------------------------------
# Module under test
# ---------------------------------------------------------------------------


def _get_helpers():
    """Import the helpers under test (deferred so import errors report clearly)."""
    from api.services.speakers import ADVOCATE_LABEL_MAP, _tenure_role_name

    return _tenure_role_name, ADVOCATE_LABEL_MAP


def _db_configured() -> bool:
    """Same placeholder guard every DB-gated fixture in this suite uses."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


# ---------------------------------------------------------------------------
# _tenure_role_name tests
# ---------------------------------------------------------------------------


class TestTenureRoleName:
    """Tests for the _tenure_role_name helper."""

    def test_empty_tenures_returns_none(self):
        """_tenure_role_name([], any_date) returns None."""
        _tenure_role_name, _ = _get_helpers()
        assert _tenure_role_name([], datetime.date(2020, 1, 15)) is None

    def test_empty_tenures_none_date_returns_none(self):
        """_tenure_role_name([], None) returns None."""
        _tenure_role_name, _ = _get_helpers()
        assert _tenure_role_name([], None) is None

    def test_argued_date_inside_window_returns_formal_title(self):
        """Returns the formal title whose [start_date, end_date] contains argued_date."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2010, 8, 7),
                "end_date": datetime.date(2022, 6, 30),
            },
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
        ]
        result = _tenure_role_name(tenures, datetime.date(2015, 10, 5))
        assert result == "Associate Justice"

    def test_argued_date_on_start_date_boundary(self):
        """Date exactly on start_date is within the window."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2020, 1, 1),
                "end_date": datetime.date(2025, 12, 31),
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2020, 1, 1))
        assert result == "Associate Justice"

    def test_argued_date_on_end_date_boundary(self):
        """Date exactly on end_date is within the window."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2020, 1, 1),
                "end_date": datetime.date(2025, 12, 31),
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2025, 12, 31))
        assert result == "Associate Justice"

    def test_open_ended_tenure_end_date_none(self):
        """end_date=None means the tenure is open-ended (currently active)."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2018, 10, 6),
                "end_date": None,  # open-ended
            }
        ]
        result = _tenure_role_name(tenures, datetime.date(2023, 11, 1))
        assert result == "Associate Justice"

    def test_argued_date_before_all_tenures_uses_fallback(self):
        """D-14: argued_date earlier than all windows returns highest-start_date
        tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2010, 8, 7),
                "end_date": datetime.date(2022, 6, 30),
            },
        ]
        # argued_date is before both tenures
        result = _tenure_role_name(tenures, datetime.date(2000, 1, 1))
        # Fallback: most recent tenure by start_date = the associate tenure
        assert result == "Associate Justice"

    def test_argued_date_after_all_tenures_uses_fallback(self):
        """D-14: argued_date later than all closed windows returns highest-start_date
        tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2005, 9, 29),
                "end_date": datetime.date(2010, 8, 6),
            },
        ]
        # argued_date is after the only tenure's end_date
        result = _tenure_role_name(tenures, datetime.date(2015, 5, 1))
        assert result == "Chief Justice"

    def test_argued_date_none_uses_most_recent_tenure(self):
        """Pitfall 5: argued_date=None returns the most-recent tenure's formal title."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": datetime.date(2000, 1, 1),
                "end_date": datetime.date(2010, 6, 30),
            },
            {
                "office": OFFICE_CHIEF,
                "start_date": datetime.date(2015, 9, 1),
                "end_date": None,
            },
        ]
        result = _tenure_role_name(tenures, None)
        assert result == "Chief Justice"

    def test_single_tenure_no_start_date_returns_formal_title(self):
        """A tenure with start_date=None falls back correctly (date.min key)."""
        _tenure_role_name, _ = _get_helpers()
        tenures = [
            {
                "office": OFFICE_ASSOCIATE,
                "start_date": None,
                "end_date": None,
            }
        ]
        result = _tenure_role_name(tenures, None)
        assert result == "Associate Justice"

    def test_valid_records_never_return_generic_justice_fallback(self):
        """D-15: every valid canonical office resolves to its formal title, never
        the bare generic "Justice" wording, regardless of window match or fallback."""
        _tenure_role_name, _ = _get_helpers()
        for office, expected in ((OFFICE_CHIEF, "Chief Justice"), (OFFICE_ASSOCIATE, "Associate Justice")):
            tenures = [
                {
                    "office": office,
                    "start_date": datetime.date(2000, 1, 1),
                    "end_date": None,
                }
            ]
            assert _tenure_role_name(tenures, datetime.date(2001, 1, 1)) == expected
            assert _tenure_role_name(tenures, None) == expected
            assert _tenure_role_name(tenures, datetime.date(1990, 1, 1)) == expected


# ---------------------------------------------------------------------------
# ADVOCATE_LABEL_MAP tests
# ---------------------------------------------------------------------------


class TestAdvocateLabelMap:
    """Tests for the ADVOCATE_LABEL_MAP constant."""

    def test_petitioner_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.PETITIONER] == "Petitioner's Counsel"

    def test_respondent_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.RESPONDENT] == "Respondent's Counsel"

    def test_amicus_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.AMICUS] == "Amicus Curiae"

    def test_unknown_label(self):
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.UNKNOWN] == "Counsel"

    def test_advocate_legacy_label(self):
        """SideEnum.ADVOCATE (legacy) must map to 'Counsel' (Pitfall 4)."""
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert ADVOCATE_LABEL_MAP[SideEnum.ADVOCATE] == "Counsel"

    def test_bench_not_in_map(self):
        """BENCH is not an advocate — it must NOT appear in ADVOCATE_LABEL_MAP."""
        _, ADVOCATE_LABEL_MAP = _get_helpers()
        assert SideEnum.BENCH not in ADVOCATE_LABEL_MAP


# ---------------------------------------------------------------------------
# get_argument_speakers end-to-end tracer test (Phase 39 Plan 01, Task 1)
# ---------------------------------------------------------------------------


class TestGetArgumentSpeakersReasonLeft:
    """DB-backed proof that a stored reason_left value travels all the way from
    the database through the ORM and public service assembly (39-01-PLAN.md
    Task 1, Step 7) — the tracer slice for the whole Phase 39 data path."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
    async def test_tenure_reason_left_reaches_public_service_output(self, db_session) -> None:
        """A CourtTenure row storing reason_left='died' surfaces as
        reason_left: "died" inside that tenure's entry of
        get_argument_speakers() output (D-01, D-13)."""
        from api.models.models import (
            Argument,
            ArgumentParticipant,
            ArgumentStatusEnum,
            CourtTenure,
            ImportMethod,
            ImportRun,
            ImportRunStatus,
            ImportSource,
            Person,
            Role,
            Utterance,
        )

        role = Role(name="Associate Justice")
        db_session.add(role)
        await db_session.flush()

        person = Person(full_name="Died In Office Justice", role_id=role.id, is_justice=True)
        db_session.add(person)
        await db_session.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            argued_date=datetime.date(2024, 1, 10),
            # get_argument_speakers() gates on published_at (BUG-01/D-02) — this
            # fixture tests payload shape, not the publish gate, so it publishes
            # the argument to keep the pre-existing assertions meaningful.
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db_session.add(arg)
        await db_session.flush()

        tenure = CourtTenure(
            person_id=person.id,
            office=OFFICE_ASSOCIATE,
            start_date=datetime.date(2010, 1, 1),
            end_date=datetime.date(2023, 6, 1),
            reason_left="died",
        )
        db_session.add(tenure)
        await db_session.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE EXAMPLE",
            side=SideEnum.BENCH,
        )
        db_session.add(participant)
        await db_session.flush()

        run = ImportRun(
            argument_id=arg.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.RULE_BASED,
        )
        db_session.add(run)
        await db_session.flush()

        utterance = Utterance(
            argument_id=arg.id,
            import_run_id=run.id,
            sequence=1,
            raw_speaker_label="JUSTICE EXAMPLE",
            text="An example utterance.",
            side=SideEnum.BENCH,
            person_id=person.id,
        )
        db_session.add(utterance)
        await db_session.flush()

        from api.services.speakers import get_argument_speakers

        result = await get_argument_speakers(db_session, arg.id)

        assert len(result) == 1
        assert result[0]["tenure"][0]["reason_left"] == "died"


# ---------------------------------------------------------------------------
# Widened public contract regression guards (Phase 39, Plan 04)
# ---------------------------------------------------------------------------


class TestPartyFieldNotSilentlyReExcluded:
    """Regression guard against silently re-narrowing the deliberately-widened
    public speaker payload (39-CONTEXT.md D-11/D-12, reverses T-14-02).

    A future edit that re-adds the old apolitical-exclusion of
    appointing_president_party must fail this test loudly, not silently
    narrow the public contract again.
    """

    def test_appointing_president_party_present_on_tenure_entry(self):
        from api.schemas.speakers import TenureEntry

        assert "appointing_president_party" in TenureEntry.model_fields

    def test_top_level_appointing_president_field_not_reintroduced(self):
        """The retired top-level field (D-13 promote) must not come back."""
        from api.schemas.speakers import SpeakerPopoverEntry

        assert "appointing_president" not in SpeakerPopoverEntry.model_fields


class TestGetArgumentSpeakersWidenedContractShape:
    """DB-backed proof that the widened public contract (Plan 39-04, Task 1)
    is an exact, closed key set — not merely a superset check — and that
    every entry is shaped identically regardless of the values it carries
    (T-39-13's positive allow-list, enforced here as an executable test)."""

    _SPEAKER_KEYS = {
        "person_id",
        "full_name",
        "role_name",
        "photo_url",
        "birthdate",
        "death_date",
        "bio_text",
        "tenure",
        "side",
    }
    _TENURE_KEYS = {
        "office",
        "start_date",
        "end_date",
        "appointed_by",
        "appointing_president_party",
        "reason_left",
    }

    async def _seed_bench_speaker_with_two_tenures(
        self,
        db_session,
        *,
        full_name: str,
        birthdate: datetime.date | None,
        death_date: datetime.date | None,
        bio_text: str | None,
    ):
        """Seed a Role/Person/Argument/two-CourtTenure/ArgumentParticipant/
        ImportRun/Utterance set, mirroring
        TestGetArgumentSpeakersReasonLeft's seeding shape, extended with a
        second tenure (different office, dates, appointed_by,
        appointing_president_party and reason_left) and the three new
        person-level fields.

        Returns the seeded Argument.
        """
        from api.models.models import (
            Argument,
            ArgumentParticipant,
            ArgumentStatusEnum,
            CourtTenure,
            ImportMethod,
            ImportRun,
            ImportRunStatus,
            ImportSource,
            Person,
            Role,
            Utterance,
        )

        role = Role(name="Associate Justice")
        db_session.add(role)
        await db_session.flush()

        person = Person(
            full_name=full_name,
            role_id=role.id,
            is_justice=True,
            birthdate=birthdate,
            death_date=death_date,
            bio_text=bio_text,
        )
        db_session.add(person)
        await db_session.flush()

        arg = Argument(
            status=ArgumentStatusEnum.PIPELINE,
            argued_date=datetime.date(2024, 1, 10),
            # get_argument_speakers() gates on published_at (BUG-01/D-02) — this
            # fixture tests payload shape, not the publish gate, so it publishes
            # the argument to keep the pre-existing assertions meaningful.
            published_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db_session.add(arg)
        await db_session.flush()

        tenure_1 = CourtTenure(
            person_id=person.id,
            office=OFFICE_ASSOCIATE,
            start_date=datetime.date(1990, 1, 1),
            end_date=datetime.date(2005, 6, 1),
            appointed_by="Example President One",
            appointing_president_party="Party A",
            reason_left="promoted",
        )
        tenure_2 = CourtTenure(
            person_id=person.id,
            office=OFFICE_CHIEF,
            start_date=datetime.date(2005, 6, 2),
            end_date=None,
            appointed_by="Example President Two",
            appointing_president_party="Party B",
            reason_left=None,
        )
        db_session.add_all([tenure_1, tenure_2])
        await db_session.flush()

        participant = ArgumentParticipant(
            argument_id=arg.id,
            person_id=person.id,
            raw_speaker_label="JUSTICE EXAMPLE",
            side=SideEnum.BENCH,
        )
        db_session.add(participant)
        await db_session.flush()

        run = ImportRun(
            argument_id=arg.id,
            step="parse",
            status=ImportRunStatus.COMPLETED,
            source=ImportSource.PDF_PIPELINE,
            method=ImportMethod.RULE_BASED,
        )
        db_session.add(run)
        await db_session.flush()

        utterance = Utterance(
            argument_id=arg.id,
            import_run_id=run.id,
            sequence=1,
            raw_speaker_label="JUSTICE EXAMPLE",
            text="An example utterance.",
            side=SideEnum.BENCH,
            person_id=person.id,
        )
        db_session.add(utterance)
        await db_session.flush()

        return arg

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
    async def test_speaker_and_tenure_key_sets_are_exact_not_subset(self, db_session) -> None:
        """The assembled entry's key set equals the closed allow-list exactly
        (== not <=), so any future leak of an adjacent Person column — for
        example oyez_speaker_id — fails this test."""
        from api.services.speakers import get_argument_speakers

        arg = await self._seed_bench_speaker_with_two_tenures(
            db_session,
            full_name="Exact Key Set Justice",
            birthdate=datetime.date(1950, 3, 4),
            death_date=None,
            bio_text="A short biography.",
        )

        result = await get_argument_speakers(db_session, arg.id)

        assert len(result) == 1
        entry = result[0]
        assert set(entry.keys()) == self._SPEAKER_KEYS
        assert len(entry["tenure"]) == 2
        for tenure_entry in entry["tenure"]:
            assert set(tenure_entry.keys()) == self._TENURE_KEYS

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
    async def test_person_fields_with_values_produce_iso_strings_and_verbatim_bio(
        self, db_session
    ) -> None:
        """A person with birthdate/death_date/bio_text set produces
        ISO-format date strings and the verbatim bio string."""
        from api.services.speakers import get_argument_speakers

        arg = await self._seed_bench_speaker_with_two_tenures(
            db_session,
            full_name="Fully Populated Justice",
            birthdate=datetime.date(1930, 1, 1),
            death_date=datetime.date(2020, 12, 31),
            bio_text="Verbatim biography text.",
        )

        result = await get_argument_speakers(db_session, arg.id)

        assert len(result) == 1
        entry = result[0]
        assert entry["birthdate"] == "1930-01-01"
        assert entry["death_date"] == "2020-12-31"
        assert entry["bio_text"] == "Verbatim biography text."

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
    async def test_person_fields_all_null_produce_none_with_keys_still_present(
        self, db_session
    ) -> None:
        """A person with birthdate/death_date/bio_text all NULL produces
        three None values with the keys still present (T-39-16)."""
        from api.services.speakers import get_argument_speakers

        arg = await self._seed_bench_speaker_with_two_tenures(
            db_session,
            full_name="No Person Fields Justice",
            birthdate=None,
            death_date=None,
            bio_text=None,
        )

        result = await get_argument_speakers(db_session, arg.id)

        assert len(result) == 1
        entry = result[0]
        assert "birthdate" in entry and entry["birthdate"] is None
        assert "death_date" in entry and entry["death_date"] is None
        assert "bio_text" in entry and entry["bio_text"] is None

    @pytest.mark.asyncio
    @pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
    async def test_tenures_with_differing_party_values_are_identically_shaped(
        self, db_session
    ) -> None:
        """Two tenures whose appointing_president_party values differ
        produce byte-identically-shaped dicts — same keys, same ordering of
        the tenure list as the service's order_by (start_date ascending),
        no extra or missing key on either."""
        from api.services.speakers import get_argument_speakers

        arg = await self._seed_bench_speaker_with_two_tenures(
            db_session,
            full_name="Two Parties Justice",
            birthdate=None,
            death_date=None,
            bio_text=None,
        )

        result = await get_argument_speakers(db_session, arg.id)

        assert len(result) == 1
        tenures = result[0]["tenure"]
        assert len(tenures) == 2

        first, second = tenures
        assert list(first.keys()) == list(second.keys())
        assert first["appointing_president_party"] != second["appointing_president_party"]
        assert first["appointing_president_party"] == "Party A"
        assert second["appointing_president_party"] == "Party B"
        # order_by(CourtTenure.start_date.asc()) — earlier start_date first.
        assert first["start_date"] < second["start_date"]
