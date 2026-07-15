"""Phase 37 migration safety contract.

These Wave 0 tests intentionally describe production artifacts introduced by
37-02.  Missing artifacts fail at test execution (RED) without preventing
pytest collection.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "migrate_tenure_offices.py"
RENAME_REVISION = ROOT / "alembic" / "versions" / "0020_rename_tenure_seat_to_office.py"
CONSTRAINT_REVISION = ROOT / "alembic" / "versions" / "0021_constrain_tenure_office.py"


def _source(path: Path) -> str:
    assert path.exists(), f"Phase 37 artifact is missing: {path.relative_to(ROOT)}"
    return path.read_text(encoding="utf-8")


def _migration_module() -> ModuleType:
    assert SCRIPT.exists(), "scripts/migrate_tenure_offices.py has not been implemented"
    spec = importlib.util.spec_from_file_location("migrate_tenure_offices", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("legacy", "expected"),
    [
        ("Chief Justice", "chief"),
        ("Associate Justice", "associate"),
        ("Associate Justice Seat 3", "associate"),
        ("Associate Justice Seat 12", "associate"),
    ],
)
def test_audit_maps_only_recognized_formal_and_numbered_values(legacy, expected):
    module = _migration_module()
    assert module.classify_office(legacy) == expected


@pytest.mark.parametrize("legacy", [None, "", "   ", "Unknown", "Associate-ish", "Seat 3"])
def test_audit_leaves_blank_and_unrecognized_values_unresolved(legacy):
    module = _migration_module()
    assert module.classify_office(legacy) is None


def test_numbered_associate_mapping_is_anchored_not_substring_inference():
    source = _source(SCRIPT)
    assert "fullmatch" in source or "^Associate Justice Seat" in source
    assert "if \"associate\" in" not in source.lower()


def test_dry_run_report_is_versioned_deterministic_and_preserves_every_original():
    module = _migration_module()
    rows = [
        {"id": 9, "original_office": "Associate Justice Seat 3"},
        {"id": 2, "original_office": "Chief Justice"},
        {"id": 7, "original_office": ""},
    ]
    report = module.build_report(rows, database_identity="test-db")
    assert report["schema_version"]
    assert report["database_identity"] == "test-db"
    assert report["expected_revision"] == "0020"
    assert [row["id"] for row in report["rows"]] == [2, 7, 9]
    assert {row["id"]: row["original_office"] for row in report["rows"]} == {
        2: "Chief Justice",
        7: "",
        9: "Associate Justice Seat 3",
    }
    assert report["unresolved_ids"] == [7]


def test_report_digest_is_sha256_over_canonical_payload_not_credentials():
    module = _migration_module()
    report = module.build_report(
        [{"id": 1, "original_office": "Chief Justice"}],
        database_identity="db-fingerprint",
    )
    digest = report.pop("sha256")
    canonical = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert digest == hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    serialized = json.dumps(report)
    assert "postgresql" not in serialized and "password" not in serialized.lower()


def test_dry_run_writes_no_database_mutation_statements():
    tree = ast.parse(_source(SCRIPT))
    dry_run = next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "run_dry_run"
    )
    text = ast.unparse(dry_run).upper()
    assert "UPDATE " not in text and "COMMIT" not in text


def test_report_writer_refuses_to_overwrite_reviewed_report(tmp_path):
    module = _migration_module()
    path = tmp_path / "reviewed.json"
    path.write_text("reviewed", encoding="utf-8")
    with pytest.raises((FileExistsError, ValueError), match="exist|overwrite"):
        module.write_report(path, {"schema_version": 1})
    assert path.read_text(encoding="utf-8") == "reviewed"


@pytest.mark.parametrize("case", ["missing", "malformed", "tampered", "wrong_database"])
def test_execute_refuses_missing_malformed_modified_or_wrong_database_report(tmp_path, case):
    module = _migration_module()
    path = tmp_path / "reviewed.json"
    if case == "malformed":
        path.write_text("{not-json", encoding="utf-8")
    elif case in {"tampered", "wrong_database"}:
        report = module.build_report(
            [{"id": 1, "original_office": "Chief Justice"}],
            database_identity="reviewed-db",
        )
        if case == "tampered":
            report["rows"][0]["original_office"] = "Associate Justice"
        path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises((FileNotFoundError, ValueError, json.JSONDecodeError)):
        module.load_reviewed_report(path, database_identity="current-db")


def test_execute_consumes_explicit_resolution_json_without_defaulting(tmp_path):
    module = _migration_module()
    resolutions = tmp_path / "resolutions.json"
    resolutions.write_text(json.dumps({"7": "chief"}), encoding="utf-8")
    assert module.load_resolutions(resolutions, unresolved_ids=[7]) == {7: "chief"}
    resolutions.write_text(json.dumps({"7": "unknown"}), encoding="utf-8")
    with pytest.raises(ValueError, match="chief|associate"):
        module.load_resolutions(resolutions, unresolved_ids=[7])


def test_execute_requires_the_existing_report_and_never_regenerates_it():
    source = _source(SCRIPT)
    assert "--report" in source and "--execute" in source and "--resolutions" in source
    execute_body = source[source.find("async def run_execute") :]
    assert "load_reviewed_report" in execute_body
    assert "write_report" not in execute_body


def test_execute_revalidates_every_original_before_first_update_and_locks_rows():
    source = _source(SCRIPT).upper()
    assert "FOR UPDATE" in source
    drift = source.find("DRIFT")
    update = source.find("UPDATE COURT_TENURES")
    assert drift != -1 and update != -1 and drift < update


def test_execute_uses_one_transaction_and_has_no_per_row_commit():
    source = _source(SCRIPT)
    assert "engine.begin()" in source
    assert ".commit()" not in source
    assert "statement_cache_size" in source


def test_execute_rolls_back_all_updates_when_any_update_fails():
    source = _source(SCRIPT)
    assert "async with engine.begin()" in source
    assert "except" not in source or "commit" not in source[source.find("except") :]


def test_execute_checks_whole_table_postcondition_and_rejects_added_or_missing_rows():
    source = _source(SCRIPT).lower()
    assert "postcondition" in source
    assert "missing" in source and "added" in source
    assert "chief" in source and "associate" in source


def test_rename_revision_only_renames_nullable_string_column():
    source = _source(RENAME_REVISION)
    assert 'revision: str = "0020"' in source
    assert 'down_revision: str = "0019"' in source or 'down_revision = "0019"' in source
    assert "new_column_name=\"office\"" in source
    assert "new_column_name=\"seat\"" in source
    assert "nullable=True" in source
    assert "UPDATE" not in source.upper()


def test_final_revision_preflights_then_adds_named_check_and_not_null():
    source = _source(CONSTRAINT_REVISION)
    upper = source.upper()
    preflight = upper.find("SELECT")
    check = source.find("create_check_constraint")
    not_null = source.find("nullable=False")
    assert 'revision: str = "0021"' in source
    assert preflight != -1 and check != -1 and not_null != -1
    assert preflight < check < not_null
    assert "chief" in source and "associate" in source
    assert "office" in source and "court_tenures" in source


def test_final_constraint_downgrade_drops_check_before_relaxing_nullability():
    source = _source(CONSTRAINT_REVISION)
    downgrade = source[source.find("def downgrade") :]
    assert downgrade.find("drop_constraint") < downgrade.find("nullable=True")

