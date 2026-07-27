"""
TDD tests for api.schemas.admin_people and api.services.admin_people.

These tests verify the schema imports and the pure-function logic
(_missing_fields, empty-string normalization, tenure filtering) without
requiring a database connection.

DB-dependent service tests live in test_admin_people.py (Task 3, extended by
Phase 38 Plan 03 for the name-authority enforcement contract — first-only/
last-only create, partial-PATCH merge, mass-assignment rejection of
full_name, and name-review-flag clearing all require a real Person row and
therefore a live DATABASE_URL).

Phase 38 Plan 03 (PEOPLE-09, D-01 through D-04, D-09, D-12): PersonUpdate and
PersonCreateRequest no longer accept a client-supplied `full_name` at all —
both are now `extra="forbid"`, so a posted `full_name` is a 422, not a
silently-ignored write (T-38-07). Full Name is always derived server-side
through the single shared `api.domain.person_names.prepare_person_name`
helper (Plan 01). This file's pure/no-DB tests cover the schema-level
allow-list contract (extra="forbid") and the "name review" directory
indicator (_missing_fields); the DB-dependent end-to-end create/update
behavior lives in test_admin_people.py per the split established above.

Phase 27 Plan 08 (UAT Gap 3 closure) adds two DB-guarded tests at the bottom
of this file proving create_person persists structured name-part fields when
supplied, and leaves them None when only one is supplied (updated for the
Phase 38 D-09 minimum-data invariant — a bare full_name is no longer a valid
create_person input at all) — mirroring the direct-engine + manual-cleanup
pattern in test_admin_people_merge.py (create_person calls db.commit()
internally, so the rollback-fixture pattern used elsewhere in this file's
sibling test modules does not apply here).
"""

import os

import pydantic
import pytest


# ---------------------------------------------------------------------------
# Schema import test
# ---------------------------------------------------------------------------


def test_schemas_import() -> None:
    """All required Pydantic schemas must import without error."""
    from api.schemas.admin_people import (  # noqa: F401
        NameExtractionMetadata,
        ParticipantItem,
        PersonCreateRequest,
        PersonDetail,
        PersonListItem,
        PersonUpdate,
        RoleCreate,
        RoleResponse,
        TenureRow,
        TenureWrite,
    )


# ---------------------------------------------------------------------------
# Service import test
# ---------------------------------------------------------------------------


def test_service_import() -> None:
    """All required service functions must import without error."""
    from api.services.admin_people import (  # noqa: F401
        _missing_fields,
        _replace_tenures,
        create_person,
        create_role,
        get_person_detail,
        list_participants_for_job,
        list_people,
        update_person,
    )


# ---------------------------------------------------------------------------
# _missing_fields unit tests (no DB required)
# ---------------------------------------------------------------------------


class _FakePerson:
    """Minimal stand-in for an ORM Person with the fields _missing_fields checks."""

    def __init__(
        self,
        first_name: str | None,
        last_name: str | None,
        photo_url: str | None,
        bio_text: str | None,
        is_justice: bool = False,
        birthdate: str | None = None,
        name_needs_review: bool = False,
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.photo_url = photo_url
        self.bio_text = bio_text
        self.is_justice = is_justice
        self.birthdate = birthdate
        self.name_needs_review = name_needs_review


def test_missing_fields_advocate_all_missing() -> None:
    """Advocate, all four core fields None → all four labels in order (D-05)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name=None, last_name=None, photo_url=None, bio_text=None, is_justice=False
    )
    result = _missing_fields(person, tenure_count=0)
    assert result == ["first name", "last name", "photo", "bio"]


def test_missing_fields_advocate_none_missing() -> None:
    """Advocate, all four core fields set → empty list."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="Sarah",
        last_name="Advocate",
        photo_url="https://example.com/photo.jpg",
        bio_text="Some bio",
        is_justice=False,
    )
    result = _missing_fields(person, tenure_count=0)
    assert result == []


def test_missing_fields_advocate_never_flags_birthdate_or_tenures() -> None:
    """Advocate with no birthdate and zero tenures never surfaces those labels (D-05)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="Sarah",
        last_name="Advocate",
        photo_url="https://example.com/photo.jpg",
        bio_text="Some bio",
        is_justice=False,
        birthdate=None,
    )
    result = _missing_fields(person, tenure_count=0)
    assert "birthdate" not in result
    assert "no tenures" not in result


def test_missing_fields_bench_all_missing() -> None:
    """Bench, everything None + zero tenures → all six labels in order (D-06)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name=None,
        last_name=None,
        photo_url=None,
        bio_text=None,
        is_justice=True,
        birthdate=None,
    )
    result = _missing_fields(person, tenure_count=0)
    assert result == ["first name", "last name", "photo", "bio", "birthdate", "no tenures"]


def test_missing_fields_bench_with_tenures_and_birthdate() -> None:
    """Bench with birthdate set and at least one tenure → no birthdate/no-tenures labels."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="John",
        last_name="Roberts",
        photo_url="https://example.com/roberts.jpg",
        bio_text="Chief Justice",
        is_justice=True,
        birthdate="1955-01-27",
    )
    result = _missing_fields(person, tenure_count=1)
    assert result == []


def test_missing_fields_bench_birthdate_only() -> None:
    """Bench missing only birthdate (has tenures) → ['birthdate']."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="John",
        last_name="Roberts",
        photo_url="https://example.com/roberts.jpg",
        bio_text="Chief Justice",
        is_justice=True,
        birthdate=None,
    )
    result = _missing_fields(person, tenure_count=1)
    assert result == ["birthdate"]


# ---------------------------------------------------------------------------
# Phase 38 (D-12): "name review" attention indicator/filter vocabulary
# ---------------------------------------------------------------------------


def test_missing_fields_appends_name_review_when_flagged_advocate() -> None:
    """An otherwise-complete Advocate flagged name_needs_review=True gets
    'name review' appended — not a NULL-field label, an ambiguity flag."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="Sarah",
        last_name="Advocate",
        photo_url="https://example.com/photo.jpg",
        bio_text="Some bio",
        is_justice=False,
        name_needs_review=True,
    )
    result = _missing_fields(person, tenure_count=0)
    assert result == ["name review"]


def test_missing_fields_appends_name_review_when_flagged_bench() -> None:
    """Bench rows also surface 'name review' — not gated by is_justice (D-12)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="John",
        last_name="Roberts",
        photo_url="https://example.com/roberts.jpg",
        bio_text="Chief Justice",
        is_justice=True,
        birthdate="1955-01-27",
        name_needs_review=True,
    )
    result = _missing_fields(person, tenure_count=1)
    assert result == ["name review"]


def test_missing_fields_omits_name_review_by_default() -> None:
    """name_needs_review defaults False — 'name review' never appears unasked."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(
        first_name="Sarah",
        last_name="Advocate",
        photo_url="https://example.com/photo.jpg",
        bio_text="Some bio",
        is_justice=False,
    )
    result = _missing_fields(person, tenure_count=0)
    assert "name review" not in result


# ---------------------------------------------------------------------------
# PersonUpdate empty-string normalization (schema / logic check)
# ---------------------------------------------------------------------------


def test_person_update_accepts_optional_fields() -> None:
    """PersonUpdate accepts all-None fields (nothing required for a PATCH)."""
    from api.schemas.admin_people import PersonUpdate

    body = PersonUpdate()
    assert body.bio_text is None
    assert body.photo_url is None
    assert body.tenures is None
    assert "full_name" not in PersonUpdate.model_fields


def test_person_update_with_all_fields() -> None:
    """PersonUpdate can carry all fields including a tenure list."""
    from api.schemas.admin_people import PersonUpdate, TenureWrite

    body = PersonUpdate(
        first_name="John",
        last_name="Roberts",
        bio_text="Chief Justice",
        photo_url="https://example.com/roberts.jpg",
        tenures=[TenureWrite(office="chief", start_date="2005-09-29", end_date=None)],
    )
    assert body.first_name == "John"
    assert body.last_name == "Roberts"
    assert body.tenures is not None
    assert len(body.tenures) == 1
    assert body.tenures[0].office == "chief"


# ---------------------------------------------------------------------------
# Phase 38 (T-38-07): writable schemas reject a client-supplied full_name
# and any other undeclared field (mass-assignment / extra="forbid")
# ---------------------------------------------------------------------------


def test_person_update_rejects_full_name_as_extra_field() -> None:
    """PersonUpdate has no full_name field; posting one is a 422-worthy
    ValidationError, not a silently-dropped write (D-01, T-38-07)."""
    from api.schemas.admin_people import PersonUpdate

    with pytest.raises(pydantic.ValidationError):
        PersonUpdate(full_name="Should Be Rejected")


def test_person_update_rejects_arbitrary_extra_field() -> None:
    """Any undeclared field (not just full_name) is rejected by the same
    extra="forbid" mass-assignment guard."""
    from api.schemas.admin_people import PersonUpdate

    with pytest.raises(pydantic.ValidationError):
        PersonUpdate(role_id=99)


def test_person_create_request_rejects_full_name_as_extra_field() -> None:
    """PersonCreateRequest has no full_name field; posting one is a
    ValidationError (D-01, D-04, T-38-07) — Full Name is always derived."""
    from api.schemas.admin_people import PersonCreateRequest

    with pytest.raises(pydantic.ValidationError):
        PersonCreateRequest(full_name="Should Be Rejected", is_justice=False)


def test_person_create_request_accepts_name_parts_without_full_name() -> None:
    """PersonCreateRequest accepts only structured parts + is_justice; the
    first-or-last minimum-data invariant (D-09) is enforced by the service
    layer's prepare_person_name, not by this schema, so omitting every part
    still constructs validly here."""
    from api.schemas.admin_people import PersonCreateRequest

    body = PersonCreateRequest(is_justice=True, last_name="Barrett")
    assert body.last_name == "Barrett"
    assert body.first_name is None
    assert "full_name" not in PersonCreateRequest.model_fields


# ---------------------------------------------------------------------------
# TenureWrite schema (strict submitted-tenure contract, D-01/D-03/D-04/D-17)
# ---------------------------------------------------------------------------


def test_tenure_write_requires_canonical_office() -> None:
    """TenureWrite.office is a required Literal["chief", "associate"]."""
    from api.schemas.admin_people import TenureWrite

    row = TenureWrite(office="chief", start_date="2005-09-29", end_date="2009-08-08")
    assert row.office == "chief"
    assert row.start_date == "2005-09-29"
    assert row.end_date == "2009-08-08"

    row2 = TenureWrite(office="associate")
    assert row2.office == "associate"
    assert row2.start_date is None
    assert row2.end_date is None


def test_tenure_write_rejects_blank_office() -> None:
    """A blank/empty string office fails validation (D-03)."""
    import pydantic

    from api.schemas.admin_people import TenureWrite

    with pytest.raises(pydantic.ValidationError):
        TenureWrite(office="")


def test_tenure_write_rejects_missing_office() -> None:
    """office is required — omitting it entirely fails validation (D-03)."""
    import pydantic

    from api.schemas.admin_people import TenureWrite

    with pytest.raises(pydantic.ValidationError):
        TenureWrite()


def test_tenure_write_rejects_unknown_office_values() -> None:
    """Legacy numbered-seat strings and formal titles are rejected on write
    (D-03, D-04, D-17) — only the two canonical values are accepted."""
    import pydantic

    from api.schemas.admin_people import TenureWrite

    for invalid_office in (
        "Associate Justice Seat 3",
        "Chief Justice",
        "Associate Justice",
        "Unknown",
        "CHIEF",
        "Chief",
    ):
        with pytest.raises(pydantic.ValidationError):
            TenureWrite(office=invalid_office)


# ---------------------------------------------------------------------------
# TenureRow schema (legacy-tolerant read-response contract, D-11)
# ---------------------------------------------------------------------------


def test_tenure_row_all_optional() -> None:
    """TenureRow fields are all Optional[str] = None."""
    from api.schemas.admin_people import TenureRow

    row = TenureRow()
    assert row.office is None
    assert row.start_date is None
    assert row.end_date is None


def test_tenure_row_with_canonical_office() -> None:
    """TenureRow accepts a canonical office and string ISO dates."""
    from api.schemas.admin_people import TenureRow

    row = TenureRow(office="associate", start_date="2006-01-31", end_date="2009-08-08")
    assert row.office == "associate"
    assert row.start_date == "2006-01-31"
    assert row.end_date == "2009-08-08"


def test_tenure_row_tolerates_invalid_legacy_office() -> None:
    """TenureRow (read response) can still carry an invalid/original value
    for operator correction (D-11) — it must NOT reject arbitrary strings
    the way TenureWrite does."""
    from api.schemas.admin_people import TenureRow

    row = TenureRow(office="Associate Justice Seat 3", start_date="2006-01-31")
    assert row.office == "Associate Justice Seat 3"


# ---------------------------------------------------------------------------
# RoleCreate / RoleResponse schema
# ---------------------------------------------------------------------------


def test_role_create_requires_name() -> None:
    """RoleCreate.name is required (str, not Optional)."""
    from api.schemas.admin_people import RoleCreate

    role = RoleCreate(name="Associate Justice")
    assert role.name == "Associate Justice"


def test_role_response_fields() -> None:
    """RoleResponse has id (int) and name (str)."""
    from api.schemas.admin_people import RoleResponse

    resp = RoleResponse(id=5, name="Petitioner's Counsel")
    assert resp.id == 5
    assert resp.name == "Petitioner's Counsel"


# ---------------------------------------------------------------------------
# PersonListItem / PersonDetail / ParticipantItem schema shapes
# ---------------------------------------------------------------------------


def test_person_list_item_shape() -> None:
    """PersonListItem has id, full_name, missing (no person-level role — D-10)."""
    from api.schemas.admin_people import PersonListItem

    item = PersonListItem(
        id=42,
        full_name="Elena Kagan",
        missing=[],
    )
    assert item.id == 42
    assert item.missing == []
    assert item.name_needs_review is False
    assert "role_id" not in PersonListItem.model_fields
    assert "role_name" not in PersonListItem.model_fields


def test_person_detail_shape() -> None:
    """PersonDetail has tenures list (no person-level role — D-10) plus the
    Phase 38 review/provenance fields (D-12, D-14, D-15, D-18)."""
    from api.schemas.admin_people import NameExtractionMetadata, PersonDetail, TenureRow

    detail = PersonDetail(
        id=1,
        full_name="John Roberts",
        bio_text=None,
        photo_url=None,
        tenures=[TenureRow(office="chief", start_date="2005-09-29")],
        name_needs_review=True,
        name_extraction_metadata={
            "source": "legacy_migration_0022",
            "raw": "John Roberts",
            "confidence": "Low",
            "reason": "single-part name is ambiguous",
            "auto_applied": False,
        },
    )
    assert len(detail.tenures) == 1
    assert detail.name_needs_review is True
    assert isinstance(detail.name_extraction_metadata, NameExtractionMetadata)
    assert detail.name_extraction_metadata.confidence == "Low"
    assert "role_id" not in PersonDetail.model_fields
    assert "role_name" not in PersonDetail.model_fields


def test_participant_item_shape() -> None:
    """ParticipantItem has participant_id, person_id, full_name, role_name, side."""
    from api.schemas.admin_people import ParticipantItem

    item = ParticipantItem(
        participant_id=42,
        person_id=10,
        full_name="Solicitor General",
        role_name="Petitioner's Counsel",
        side="PETITIONER",
    )
    assert item.participant_id == 42
    assert item.person_id == 10
    assert item.full_name == "Solicitor General"
    assert item.side == "PETITIONER"


# ---------------------------------------------------------------------------
# Phase 38 (D-01, D-03): admin_people no longer owns an independent full_name
# formatter — create_person/update_person both call the single shared
# api.domain.person_names.prepare_person_name helper (fully fixture-tested
# in test_person_names.py). These tests confirm the service module itself
# imports and re-exposes that dependency rather than reintroducing a local
# derivation (the old _derive_full_name — buggy: no suffix comma, required
# both first AND last — has been removed entirely).
# ---------------------------------------------------------------------------


def test_service_module_has_no_local_full_name_formatter() -> None:
    """_derive_full_name must not exist — prepare_person_name is now the only
    full_name derivation path (D-01, D-03)."""
    import api.services.admin_people as admin_people_service

    assert not hasattr(admin_people_service, "_derive_full_name")


def test_service_imports_shared_prepare_person_name() -> None:
    """admin_people imports the Plan 01 shared helper directly, rather than
    reimplementing formatting locally."""
    from api.services.admin_people import prepare_person_name

    result = prepare_person_name("John", None, "Roberts", "Jr.")
    assert result.full_name == "John Roberts, Jr."


# ---------------------------------------------------------------------------
# Phase 18: is_justice field tests (no DB required)
# ---------------------------------------------------------------------------


def test_person_update_is_justice_optional() -> None:
    """PersonUpdate.is_justice defaults None; can carry True or False explicitly."""
    from api.schemas.admin_people import PersonUpdate

    assert PersonUpdate().is_justice is None
    assert PersonUpdate(is_justice=True).is_justice is True
    assert PersonUpdate(is_justice=False).is_justice is False


def test_person_detail_is_justice_default_false() -> None:
    """PersonDetail.is_justice defaults False; can be set True."""
    from api.schemas.admin_people import PersonDetail

    assert PersonDetail(id=1, full_name="X").is_justice is False
    assert PersonDetail(id=1, full_name="X", is_justice=True).is_justice is True


def test_person_list_item_is_justice() -> None:
    """PersonListItem.is_justice can be set True."""
    from api.schemas.admin_people import PersonListItem

    item = PersonListItem(id=1, full_name="X", missing=[], is_justice=True)
    assert item.is_justice is True


# ---------------------------------------------------------------------------
# Phase 27 Plan 08 (UAT Gap 3 closure), updated by Phase 38 Plan 03:
# create_person persists derived name parts through prepare_person_name
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.mark.asyncio
async def test_create_person_rejects_missing_first_and_last() -> None:
    """create_person rejects a create with neither first_name nor last_name
    (D-09) — api.domain.person_names.PersonNameError is raised by the shared
    prepare_person_name helper BEFORE any DB access, so this test needs no
    DATABASE_URL/live database at all (db=None is never touched)."""
    from api.domain.person_names import PersonNameError
    from api.schemas.admin_people import PersonCreateRequest
    from api.services.admin_people import create_person

    body = PersonCreateRequest(is_justice=False)
    with pytest.raises(PersonNameError):
        await create_person(None, body)  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_persists_name_parts_when_supplied() -> None:
    """create_person with all four name-part fields persists them onto the
    new row and derives full_name through prepare_person_name (D-01, D-03) —
    there is no full_name field on PersonCreateRequest to supply directly.
    """
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from api.schemas.admin_people import PersonCreateRequest
    from api.services.admin_people import create_person, get_person_detail

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    person_id = None
    try:
        async with async_session() as db:
            body = PersonCreateRequest(
                is_justice=False,
                first_name="Gap",
                middle_name="Closure",
                last_name="Person",
                name_suffix="Jr.",
            )
            detail = await create_person(db, body)
            person_id = detail["id"]

            assert detail["first_name"] == "Gap"
            assert detail["middle_name"] == "Closure"
            assert detail["last_name"] == "Person"
            assert detail["name_suffix"] == "Jr."
            assert detail["full_name"] == "Gap Closure Person, Jr."
            assert detail["name_needs_review"] is False

        async with async_session() as db:
            refetched = await get_person_detail(db, person_id)
            assert refetched["first_name"] == "Gap"
            assert refetched["middle_name"] == "Closure"
            assert refetched["last_name"] == "Person"
            assert refetched["name_suffix"] == "Jr."
            assert refetched["full_name"] == "Gap Closure Person, Jr."
    finally:
        if person_id is not None:
            async with async_session() as db:
                await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))
                await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_last_name_only_leaves_others_none() -> None:
    """create_person with ONLY last_name (D-09 last-only minimum) leaves
    first_name/middle_name/name_suffix None and derives full_name from
    last_name alone."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from api.schemas.admin_people import PersonCreateRequest
    from api.services.admin_people import create_person

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    person_id = None
    try:
        async with async_session() as db:
            body = PersonCreateRequest(is_justice=True, last_name="Souter")
            detail = await create_person(db, body)
            person_id = detail["id"]

            assert detail["first_name"] is None
            assert detail["middle_name"] is None
            assert detail["last_name"] == "Souter"
            assert detail["name_suffix"] is None
            assert detail["full_name"] == "Souter"
    finally:
        if person_id is not None:
            async with async_session() as db:
                await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))
                await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_first_name_only_leaves_others_none() -> None:
    """create_person with ONLY first_name (D-09 first-only minimum) leaves
    last_name/middle_name/name_suffix None and derives full_name from
    first_name alone."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from api.schemas.admin_people import PersonCreateRequest
    from api.services.admin_people import create_person

    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    person_id = None
    try:
        async with async_session() as db:
            body = PersonCreateRequest(is_justice=False, first_name="Solicitor")
            detail = await create_person(db, body)
            person_id = detail["id"]

            assert detail["first_name"] == "Solicitor"
            assert detail["middle_name"] is None
            assert detail["last_name"] is None
            assert detail["name_suffix"] is None
            assert detail["full_name"] == "Solicitor"
    finally:
        if person_id is not None:
            async with async_session() as db:
                await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))
                await db.commit()
        await engine.dispose()
