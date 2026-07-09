"""
TDD tests for api.schemas.admin_people and api.services.admin_people.

These tests verify the schema imports and the pure-function logic
(_missing_fields, empty-string normalization, tenure filtering) without
requiring a database connection.

DB-dependent service tests live in test_admin_people.py (Task 3).
"""

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
    """Minimal stand-in for an ORM Person with role_id, bio_text, photo_url."""

    def __init__(
        self,
        role_id: int | None,
        bio_text: str | None,
        photo_url: str | None,
    ) -> None:
        self.role_id = role_id
        self.bio_text = bio_text
        self.photo_url = photo_url


def test_missing_fields_all_none() -> None:
    """All three fields None → ['role', 'bio', 'photo'] in that order (D-04, D-06)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=None, bio_text=None, photo_url=None)
    result = _missing_fields(person)
    assert result == ["role", "bio", "photo"]


def test_missing_fields_none_missing() -> None:
    """All three fields set → empty list."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=1, bio_text="Some bio", photo_url="https://example.com/photo.jpg")
    result = _missing_fields(person)
    assert result == []


def test_missing_fields_bio_only() -> None:
    """Only bio_text None → ['bio']."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=1, bio_text=None, photo_url="https://example.com/photo.jpg")
    result = _missing_fields(person)
    assert result == ["bio"]


def test_missing_fields_role_only() -> None:
    """Only role_id None → ['role']."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=None, bio_text="bio", photo_url="https://example.com/photo.jpg")
    result = _missing_fields(person)
    assert result == ["role"]


def test_missing_fields_photo_only() -> None:
    """Only photo_url None → ['photo']."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=1, bio_text="bio", photo_url=None)
    result = _missing_fields(person)
    assert result == ["photo"]


def test_missing_fields_order_role_bio() -> None:
    """role and bio missing → ['role', 'bio'] (role before bio per D-06)."""
    from api.services.admin_people import _missing_fields

    person = _FakePerson(role_id=None, bio_text=None, photo_url="https://example.com/photo.jpg")
    result = _missing_fields(person)
    assert result == ["role", "bio"]


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
    from api.schemas.admin_people import PersonUpdate, TenureRow

    body = PersonUpdate(
        full_name="John Roberts",
        role_id=1,
        bio_text="Chief Justice",
        photo_url="https://example.com/roberts.jpg",
        tenures=[TenureRow(seat="Chief Justice", start_date="2005-09-29", end_date=None)],
    )
    assert body.full_name == "John Roberts"
    assert body.tenures is not None
    assert len(body.tenures) == 1
    assert body.tenures[0].seat == "Chief Justice"


# ---------------------------------------------------------------------------
# TenureRow schema
# ---------------------------------------------------------------------------


def test_tenure_row_all_optional() -> None:
    """TenureRow fields are all Optional[str] = None."""
    from api.schemas.admin_people import TenureRow

    row = TenureRow()
    assert row.seat is None
    assert row.start_date is None
    assert row.end_date is None


def test_tenure_row_with_values() -> None:
    """TenureRow accepts string ISO dates."""
    from api.schemas.admin_people import TenureRow

    row = TenureRow(seat="Associate Justice Seat 3", start_date="2006-01-31", end_date="2009-08-08")
    assert row.seat == "Associate Justice Seat 3"
    assert row.start_date == "2006-01-31"
    assert row.end_date == "2009-08-08"


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
    """PersonListItem has id, full_name, role_id, role_name, missing."""
    from api.schemas.admin_people import PersonListItem

    item = PersonListItem(
        id=42,
        full_name="Elena Kagan",
        role_id=2,
        role_name="Associate Justice",
        missing=[],
    )
    assert item.id == 42
    assert item.missing == []


def test_person_detail_shape() -> None:
    """PersonDetail has tenures list."""
    from api.schemas.admin_people import PersonDetail, TenureRow

    detail = PersonDetail(
        id=1,
        full_name="John Roberts",
        role_id=1,
        role_name="Chief Justice",
        bio_text=None,
        photo_url=None,
        tenures=[TenureRow(seat="Chief Justice", start_date="2005-09-29")],
    )
    assert len(detail.tenures) == 1


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
