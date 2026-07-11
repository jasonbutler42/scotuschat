"""
Targeted regression test for the arguments.question_number NOT-NULL-over-
nullable-column defect diagnosed in 30.1-UAT.md test 3 (AEDIT-04 gap):
blanking the Question number field in the Argument Details card and saving
raised an unhandled asyncpg IntegrityError instead of persisting NULL, since
the column was never migrated to nullable (unlike argued_date, migration
0011). Fixed by migration 0019 (nullable=True, no server default) plus
schema/router hardening in this plan.

Mirrors api/tests/test_case_item_argued_date_optional.py exactly: pure-Python
schema construction, no DB, no async, no fixtures — safe against the known
shared-dev-DB test-leak issue (see ROADMAP.md backlog Phase 999.19).
"""

import inspect


def test_case_item_accepts_null_question_number() -> None:
    """Constructing CaseItem with question_number=None must not raise."""
    from api.schemas.cases import CaseItem

    item = CaseItem(
        id=1,
        slug="synthetic-case",
        case_name="Synthetic Case",
        docket_number="1955-71",
        term_year=1955,
        argument_id=1,
        question_number=None,
        argued_date=None,
    )
    assert item.question_number is None


def test_argument_metadata_response_accepts_null_question_number() -> None:
    """Constructing ArgumentMetadataResponse with question_number=None must not raise."""
    from api.schemas.utterance import ArgumentMetadataResponse

    item = ArgumentMetadataResponse(
        argument_id=1,
        case_name="Synthetic Case",
        docket_number="1955-71",
        question_number=None,
    )
    assert item.question_number is None


def test_admin_router_catches_integrity_error() -> None:
    """update_argument_metadata must catch sqlalchemy.exc.IntegrityError so any
    future NOT NULL / constraint violation degrades to a clean 4xx instead of
    an unhandled 500 (defense-in-depth regression guard).
    """
    from api.routers import admin

    source = inspect.getsource(admin)
    assert "IntegrityError" in source, (
        "update_argument_metadata handler must reference IntegrityError "
        "(sqlalchemy.exc.IntegrityError) to catch constraint violations"
    )
