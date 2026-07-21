"""
TDD tests for api.schemas.admin_people and api.services.admin_people.

These tests verify the schema imports and the pure-function logic
(_missing_fields, empty-string normalization, tenure filtering) without
requiring a database connection.

DB-dependent service tests live in test_admin_people.py (Task 3).

Phase 27 Plan 08 (UAT Gap 3 closure) adds two DB-guarded tests at the bottom
of this file proving create_person persists structured name-part fields when
supplied, and leaves them None when omitted — mirroring the direct-engine +
manual-cleanup pattern in test_admin_people_merge.py (create_person calls
db.commit() internally, so the rollback-fixture pattern used elsewhere in
this file's sibling test modules does not apply here).
"""

import os

import pytest


# ---------------------------------------------------------------------------
# Schema import test
# ---------------------------------------------------------------------------


def test_schemas_import() -> None:
    """All required Pydantic schemas must import without error."""
    from api.schemas.admin_people import (  # noqa: F401
        ParticipantItem,
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
        _derive_full_name,
        _missing_fields,
        _replace_tenures,
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
    ) -> None:
        self.first_name = first_name
        self.last_name = last_name
        self.photo_url = photo_url
        self.bio_text = bio_text
        self.is_justice = is_justice
        self.birthdate = birthdate


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
# PersonUpdate empty-string normalization (schema / logic check)
# ---------------------------------------------------------------------------


def test_person_update_accepts_optional_fields() -> None:
    """PersonUpdate accepts all-None fields (nothing required for a PATCH)."""
    from api.schemas.admin_people import PersonUpdate

    body = PersonUpdate()
    assert body.full_name is None
    assert body.bio_text is None
    assert body.photo_url is None
    assert body.tenures is None


def test_person_update_with_all_fields() -> None:
    """PersonUpdate can carry all fields including a tenure list."""
    from api.schemas.admin_people import PersonUpdate, TenureWrite

    body = PersonUpdate(
        full_name="John Roberts",
        bio_text="Chief Justice",
        photo_url="https://example.com/roberts.jpg",
        tenures=[TenureWrite(office="chief", start_date="2005-09-29", end_date=None)],
    )
    assert body.full_name == "John Roberts"
    assert body.tenures is not None
    assert len(body.tenures) == 1
    assert body.tenures[0].office == "chief"


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
    assert "role_id" not in PersonListItem.model_fields
    assert "role_name" not in PersonListItem.model_fields


def test_person_detail_shape() -> None:
    """PersonDetail has tenures list (no person-level role — D-10)."""
    from api.schemas.admin_people import PersonDetail, TenureRow

    detail = PersonDetail(
        id=1,
        full_name="John Roberts",
        bio_text=None,
        photo_url=None,
        tenures=[TenureRow(office="chief", start_date="2005-09-29")],
    )
    assert len(detail.tenures) == 1
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
# _derive_full_name unit tests (D-04, no DB required)
# ---------------------------------------------------------------------------


def test_derive_full_name_first_middle_last() -> None:
    """first + middle + last → 'Amy Coney Barrett' (no suffix)."""
    from api.services.admin_people import _derive_full_name

    result = _derive_full_name("Amy", "Coney", "Barrett", None)
    assert result == "Amy Coney Barrett"


def test_derive_full_name_first_last_suffix() -> None:
    """first + last + suffix, no middle → 'John Roberts Jr.'"""
    from api.services.admin_people import _derive_full_name

    result = _derive_full_name("John", None, "Roberts", "Jr.")
    assert result == "John Roberts Jr."


def test_derive_full_name_blank_suffix_omitted() -> None:
    """Blank string suffix (empty string) is omitted from the result."""
    from api.services.admin_people import _derive_full_name

    result = _derive_full_name("Ketanji", "Brown", "Jackson", "")
    assert result == "Ketanji Brown Jackson"


def test_derive_full_name_blank_middle_omitted() -> None:
    """Blank string middle (empty string) is omitted from the result."""
    from api.services.admin_people import _derive_full_name

    result = _derive_full_name("Elena", "", "Kagan", None)
    assert result == "Elena Kagan"


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
# Phase 27 Plan 08 (UAT Gap 3 closure): create_person persists name parts
# ---------------------------------------------------------------------------


def _db_configured() -> bool:
    """Return True if DATABASE_URL is set and non-placeholder in the environment."""
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_persists_name_parts_when_supplied() -> None:
    """create_person with all four name-part fields persists them onto the new row.

    Matches the [id] editor's save-action behavior (PersonUpdate) — a person
    created with structured name parts must retain them, not just full_name.
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
                full_name="Gap Closure Test Person",
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

        async with async_session() as db:
            refetched = await get_person_detail(db, person_id)
            assert refetched["first_name"] == "Gap"
            assert refetched["middle_name"] == "Closure"
            assert refetched["last_name"] == "Person"
            assert refetched["name_suffix"] == "Jr."
    finally:
        if person_id is not None:
            async with async_session() as db:
                await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))
                await db.commit()
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.skipif(not _db_configured(), reason="Requires DATABASE_URL")
async def test_create_person_leaves_name_parts_none_when_omitted() -> None:
    """create_person with only full_name + is_justice leaves name parts None.

    Backward-compatible with D-08's minimum-required contract — omitting the
    name-part fields must still succeed.
    """
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
            body = PersonCreateRequest(
                full_name="Gap Closure Minimal Person",
                is_justice=True,
            )
            detail = await create_person(db, body)
            person_id = detail["id"]

            assert detail["first_name"] is None
            assert detail["middle_name"] is None
            assert detail["last_name"] is None
            assert detail["name_suffix"] is None
    finally:
        if person_id is not None:
            async with async_session() as db:
                await db.execute(text(f"DELETE FROM people WHERE id = {person_id}"))
                await db.commit()
        await engine.dispose()
