"""
Phase 44 Plan 01 — full-stack `ArgumentParticipant.title` -> `.descriptor` rename
residual-name source contract (D-05).

Locks the rename's completeness by *pure static source contract* — no
database, no `_db_configured` gate, no `node` subprocess. Follows
`api/tests/test_phase39_popover_ui_contract.py`'s `ROOT` + module-level path
constant + `_source()` shape.

Guards, in order:
  1. Migration 0025 is a true in-place rename (no add/drop column) with the
     correct `down_revision` (T-44-05).
  2. `api/models/models.py` declares the renamed column and no `title` column.
  3. The unrelated `office_title`/`reason_left_title` formal-office vocabulary
     was NOT swept up by the rename (PATTERNS.md caution).
  4. No file under api/, pipeline/, scripts/, or app/src/ still references
     `title_hint` — the rename left no residue anywhere in the stack.
  5. `ResolveRowUpdate` and `ParticipantSideUpdate` still expose exactly their
     pre-rename field counts and the WR-03 length cap survived (T-44-01,
     T-44-02 mass-assignment guards, asserted structurally via model_fields).
"""

from pathlib import Path

ROOT = Path(__file__).parents[2]
MIGRATION_PATH = (
    ROOT / "alembic" / "versions" / "0025_rename_participant_title_to_descriptor.py"
)
MODELS_PATH = ROOT / "api" / "models" / "models.py"

# Directories to walk for the residual title_hint sweep, and the exclusions
# within them (Phase 44 D-05's own site inventory).
SWEEP_DIRS = ["api", "pipeline", "scripts", "app/src"]
SWEEP_EXCLUDE_DIR_NAMES = {"__pycache__", "node_modules", ".svelte-kit"}
SWEEP_EXCLUDE_FILE_SUFFIXES = {
    # Historical migration 0013 added the original title column; it is
    # deliberately preserved byte-identical and is never edited (CLAUDE.md:
    # raw history is immutable). This test file's own needle is also excluded
    # — the string appears here only as the thing being searched for.
    "0013_participant_title_and_tenure_appointed_by.py",
    "test_phase44_descriptor_rename.py",
    # planner-discipline-allow: title_hint
}


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Migration 0025 — true in-place rename, correct down_revision
# ─────────────────────────────────────────────────────────────────────────────


def test_migration_0025_renames_in_place() -> None:
    source = _source(MIGRATION_PATH)

    assert 'down_revision: str = "0024"' in source, (
        "Migration 0025 must chain directly off head 0024 (T-44-05)"
    )
    assert source.count('new_column_name="descriptor"') == 1, (
        "upgrade() must rename title -> descriptor exactly once"
    )
    assert source.count('new_column_name="title"') == 1, (
        "downgrade() must be the exact mirror, renaming descriptor -> title"
    )
    assert "op.add_column" not in source, (
        "This must be a true in-place rename — no add-column step (D-05 prohibition)"
    )
    assert "op.drop_column" not in source, (
        "This must be a true in-place rename — no drop-column step (D-05 prohibition)"
    )
    assert "Base.metadata.create_all" not in source, (
        "Alembic is the sole DDL authority (CLAUDE.md) — never create_all"
    )


# ─────────────────────────────────────────────────────────────────────────────
# api/models/models.py — descriptor column declared, no stray title column,
# unrelated office-title vocabulary untouched
# ─────────────────────────────────────────────────────────────────────────────


def test_models_declares_descriptor_column() -> None:
    source = _source(MODELS_PATH)

    assert "descriptor = Column(String(500), nullable=True)" in source, (
        "ArgumentParticipant.descriptor must be declared exactly as the "
        "renamed title column was (same type/nullability)"
    )
    assert "title = Column(" not in source, (
        "No model may declare a bare `title` column any more — the rename "
        "must be complete, not additive"
    )


def test_office_title_vocabulary_untouched() -> None:
    """Guard against a blind find-and-replace of the word 'title' — the
    formal office-title helpers are a distinct, unrelated concept and must
    survive the rename verbatim (PATTERNS.md caution, D-05 prohibition)."""
    source = _source(MODELS_PATH)

    assert "def office_title(" in source
    assert "def reason_left_title(" in source


# ─────────────────────────────────────────────────────────────────────────────
# Residual-name sweep — no title_hint anywhere in the touched trees
# ─────────────────────────────────────────────────────────────────────────────


def test_no_residual_title_hint_anywhere() -> None:
    offenders: list[str] = []

    for dir_name in SWEEP_DIRS:
        base = ROOT / dir_name
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SWEEP_EXCLUDE_DIR_NAMES for part in path.parts):
                continue
            if path.name in SWEEP_EXCLUDE_FILE_SUFFIXES:
                continue
            # Only scan text-ish source files; skip binaries/images/etc.
            if path.suffix not in {
                ".py",
                ".ts",
                ".svelte",
                ".js",
                ".json",
                ".md",
            }:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if "title_hint" in text:
                offenders.append(str(path.relative_to(ROOT)))

    assert not offenders, (
        "The following files still reference the pre-rename `title_hint` "
        f"name (D-05 residue): {offenders}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ResolveRowUpdate / ParticipantSideUpdate — mass-assignment guards survived
# the rename structurally, not just by grep (T-44-01, T-44-02)
# ─────────────────────────────────────────────────────────────────────────────


def test_resolve_row_update_guard_and_length_cap_survive() -> None:
    from api.schemas.admin_jobs import ResolveRowUpdate

    field_names = set(ResolveRowUpdate.model_fields.keys())
    assert field_names == {"participant_id", "side", "descriptor"}, (
        f"ResolveRowUpdate must expose exactly {{participant_id, side, "
        f"descriptor}} — mass-assignment guard T-25-15/T-44-01 got: {field_names}"
    )

    descriptor_field = ResolveRowUpdate.model_fields["descriptor"]
    assert descriptor_field.metadata, "descriptor field must carry length-cap metadata"
    max_lengths = [
        getattr(m, "max_length", None)
        for m in descriptor_field.metadata
        if getattr(m, "max_length", None) is not None
    ]
    assert 500 in max_lengths, (
        "descriptor must retain the WR-03 500-character cap — without it an "
        "over-length value raises an unhandled asyncpg DataError (500) "
        "instead of a 422"
    )


def test_participant_side_update_guard_survives() -> None:
    from api.schemas.admin_arguments import ParticipantSideUpdate

    field_names = set(ParticipantSideUpdate.model_fields.keys())
    assert field_names == {"side", "descriptor"}, (
        f"ParticipantSideUpdate must expose exactly {{side, descriptor}} — "
        f"mass-assignment guard T-26-04/T-44-02 got: {field_names}"
    )
