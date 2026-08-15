# Phase 42: Corpus Import Fidelity Diff & Fix - Pattern Map

**Mapped:** 2026-07-30
**Files analyzed:** 8 (new/modified)
**Analogs found:** 8 / 8

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/diff_corpus_fixture.py` (new — diff/classification doc generator) | utility (offline audit script) | batch / transform | `scripts/select_corpus_fixtures.py` | exact (same dir, same "operator-run offline script over `data/corpus/`" role) |
| `pipeline/commands/import_convokit.py` — new `--conversation-id` CLI option (D-01) | route/CLI arg handling | request-response (CLI) | `pipeline/commands/import_convokit.py::_resolve_terms` / `_resolve_corpus_dir` (same file, same function family) | exact |
| `pipeline/commands/import_convokit.py` — Marshall bench-misclassification fix (Pitfall 2) | service (core import logic) | transform | `pipeline/commands/import_convokit.py::_is_justice_type` / `_resolve_and_link_participant` | exact |
| `pipeline/commands/import_convokit.py` — `section_hint` population fix (Pitfall 3) | service (core import logic) | transform | `pipeline/commands/import_convokit.py::_import_utterances` (write side); `pipeline/commands/parse.py` (derivation side, `assign_side`/`section_hint` usage) | role-match (import_convokit is the write site; parse.py is the only existing `section_hint`-deriving precedent) |
| `scripts/delete_fixture_argument.py` (new — delete-then-reimport routine, D-01/Pitfall 1) | utility (offline admin script) | event-driven (one-shot destructive op) | `api/services/admin_arguments.py::delete_argument` | role-match (same FK-cascade shape; cannot reuse directly — gate removed) |
| `pipeline/tests/test_import_convokit_marshall.py` or extension of `test_import_convokit_core.py` (new test coverage for Pitfall 2) | test | transform | `pipeline/tests/test_import_convokit_core.py` (`_write_corpus_fixture` pattern) | exact |
| `pipeline/tests/test_import_convokit_utterances.py` (extended — assert `section_hint` populated) | test | transform | `pipeline/tests/test_import_convokit_utterances.py` (existing file, extend in place) | exact |
| `.planning/CORPUS-FIDELITY-DIFF.md` or similar (new — durable diff/classification doc, D-04) | config/doc (durable artifact) | batch | `.planning/FIXTURES.md` | exact (explicit precedent named in CONTEXT.md D-04) |

## Pattern Assignments

### `scripts/diff_corpus_fixture.py` (utility, batch/transform)

**Analog:** `scripts/select_corpus_fixtures.py`

**Imports pattern** (from `pipeline/commands/import_convokit.py` lines 63-101, the canonical import shape any corpus-reading script must mirror):
```python
from __future__ import annotations

import argparse
from pathlib import Path

from pipeline.corpus import apolitical
from pipeline.corpus.loader import (
    load_cases,
    load_conversations_for_term,
    load_speakers,
    stream_utterances_for_conversation_ids,
)
```

**CLI arg validation pattern** (`scripts/select_corpus_fixtures.py` lines 103-175 — `_parse_args`, `_resolve_corpus_dir`, `_require_corpus_files`): mirror the fail-fast validation shown in `import_convokit.py` lines 190-205:
```python
def _resolve_corpus_dir(args) -> Path:
    raw = getattr(args, "corpus_dir", None)
    corpus_dir = Path(raw) if raw else DEFAULT_CORPUS_DIR
    if not corpus_dir.is_dir():
        raise FileNotFoundError(
            f"--corpus-dir does not exist: {corpus_dir}. Place the ConvoKit "
            "supreme-corpus source files ... there before running ..."
        )
    return corpus_dir
```

**Core allow-list-only reading pattern** — the diff script must NEVER read raw dicts directly for anything written to the durable doc; always go through `pipeline/corpus/apolitical.py`'s extractors (full file, 74 lines):
```python
# pipeline/corpus/apolitical.py lines 36-58
def extract_case_fields(raw_case: dict) -> dict:
    return {
        "title": raw_case.get("title"),
        "petitioner": raw_case.get("petitioner"),
        "respondent": raw_case.get("respondent"),
        "docket_no": raw_case.get("docket_no"),
        "decided_date": raw_case.get("decided_date"),
        "citation": raw_case.get("citation"),
        "court": raw_case.get("court"),
        "year": raw_case.get("year"),
        "transcripts": raw_case.get("transcripts"),
        "advocates": raw_case.get("advocates"),
        "case_id": raw_case.get("id"),
    }
```
`FORBIDDEN_FIELDS` (apolitical.py lines 24-33) is the exact frozenset (`win_side`, `win_side_detail`, `votes`, `votes_detail`, `votes_side`, `scdb_docket_id`) the diff script must classify as "intentional exclusion," never inspect/print raw values from in its committed output.

**Reading raw fixture files without a second parser** — reuse `pipeline/corpus/loader.py` verbatim (full file, 101 lines): `load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids`. Do not hand-roll a second `json.load`/`grep` pass for anything that becomes part of the diff document (ad hoc `grep`/manual reads are fine for scratch research only, per RESEARCH.md's Don't-Hand-Roll table).

**DB-side read pattern** (for cross-referencing imported rows against the raw side) — reuse the project's async session helper, same as every pipeline command:
```python
# pipeline/commands/import_convokit.py line 101, lines 1075-1084
from pipeline.db import get_session
...
async with get_session() as session:
    result = await session.execute(select(Argument).where(Argument.oyez_transcript_id == conversation_id))
```

---

### `pipeline/commands/import_convokit.py` — new `--conversation-id` scoped import option (D-01)

**Analog:** same file's existing `--term`/`--term-range` mutually-exclusive group (CLI wiring in `pipeline/__main__.py` lines 282-315) plus `_resolve_terms` (lines 175-187).

**CLI registration pattern** (`pipeline/__main__.py` lines 282-315, exact site to extend):
```python
import_convokit_term_group = import_convokit_p.add_mutually_exclusive_group(required=True)
import_convokit_term_group.add_argument("--term", type=int, help="Single October Term year, e.g. 1955")
import_convokit_term_group.add_argument("--term-range", type=str, help="Inclusive October Term range, e.g. 1955-1960")
```
A new `--conversation-id` option should either join this mutually-exclusive group or be layered as an additional filter applied after term resolution — planner/executor discretion per RESEARCH.md, but it MUST still call `_next_question_number` (never hardcode `1`) and MUST still validate existence in the loaded `conversations.json` before use (V5 pattern, matching `_resolve_terms`'s `argparse.ArgumentTypeError` style, lines 175-187):
```python
def _resolve_terms(args) -> list[int]:
    term = getattr(args, "term", None)
    if term is not None:
        return [term]
    term_range = getattr(args, "term_range", None)
    if term_range:
        start, end = _parse_term_range(term_range)
        return list(range(start, end + 1))
    raise argparse.ArgumentTypeError("Either --term or --term-range is required.")
```

**Entry-point loop to scope** (`run_import_convokit`, lines 1023-1096) — the new option must filter `conversations` (or `wanted_ids`) down to the single conversation_id before the `for conversation_id, raw_conversation in conversations.items():` loop at line 1073, not after — otherwise `stream_utterances_for_conversation_ids` (line 1067) still streams the full term's utterance rows unnecessarily. Reuse the existing loaders unchanged (`load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids`, lines 95-100).

---

### `pipeline/commands/import_convokit.py` — Marshall bench-misclassification fix (Pitfall 2, pending D-05 review)

**Analog:** same file, `_is_justice_type` (lines 566-577) and `_resolve_and_link_participant` (lines 697-773).

**Current logic to modify (only after operator approval per D-05/D-06):**
```python
# lines 566-577
def _is_justice_type(speaker_meta: dict) -> bool | None:
    speaker_type = speaker_meta.get("type")
    if speaker_type is None:
        return None
    return str(speaker_type).strip().lower() in _JUSTICE_TYPE_VALUES
```
```python
# lines 737-752 (call site inside _resolve_and_link_participant)
is_justice = _is_justice_type(speaker_meta)
...
side = SideEnum.BENCH if is_justice else _ADVOCATE_SIDE_MAP.get(side_code, SideEnum.UNKNOWN)
```
If the operator approves the "general fix" option (RESEARCH.md Open Question 2), the fix site is here: cross-check `argued_date` (available in `_import_conversation`, line 433: `argued_date = _parse_argued_date(...)`) against `CourtTenure` rows for the resolved `Person` before trusting `type=="J"` — this requires passing `argued_date` down into `_resolve_and_link_participant`/`_is_justice_type` (currently not threaded through — planner must add it as a parameter). Query pattern to reuse (same session/select idiom already used everywhere in this file, e.g. line 667-669):
```python
result = await session.execute(
    select(CourtTenure).where(
        CourtTenure.person_id == person.id,
        CourtTenure.start_date <= argued_date,
        (CourtTenure.end_date.is_(None)) | (CourtTenure.end_date >= argued_date),
    )
)
```

---

### `pipeline/commands/import_convokit.py` — `section_hint` population fix (Pitfall 3)

**Analog (write site):** `_import_utterances` (lines 816-948), specifically the two `Utterance(...)` constructor calls (lines 907-919 stage-direction row, 929-943 spoken row) — neither currently sets `section_hint`.

**Analog (derivation precedent, PDF pipeline):** `pipeline/commands/parse.py` lines 198-206, 279:
```python
# parse.py lines 198-206
from pipeline.parser.state_machine import assign_side
...
"section_hint": u.section_hint,
"side": assign_side(u.raw_speaker_label, u.is_stage_direction),
```
```python
# parse.py line 279
section_hint=u.get("section_hint"),
```
The corpus importer has no `state_machine.py`-equivalent side-transition tracker; the fix must derive `section_hint` from the conversation-level `advocates[].side` codes (already available via `_ADVOCATE_SIDE_MAP`, lines 114-119) plus turn order, inside `_import_utterances`'s per-row loop (lines 904-943) — set `section_hint` on both `Utterance(...)` calls using the resolved `participant.side` (already computed) mapped to `"petitioner"`/`"respondent"`/`"rebuttal"`/`"amicus"` (column comment, `api/models/models.py` line 425: `section_hint = Column(String(50), nullable=True)  # "petitioner"|"respondent"|"rebuttal"|"amicus"`).

**Frontend consumer to verify against post-fix** (not modified, read-only reference): `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` lines ~96-120, ~313-320 — filters out any utterance where `section_hint` is null.

---

### `scripts/delete_fixture_argument.py` (new delete-and-reimport routine, Pitfall 1)

**Analog:** `api/services/admin_arguments.py::delete_argument` (lines 743-822) — same FK-ordered cascade shape, but the `status == DRAFT` gate (lines 776-780) must NOT be reused/copied — this script targets PIPELINE-status corpus arguments by design.

**Cascade pattern to mirror (order-critical, gate removed):**
```python
# api/services/admin_arguments.py lines 782-819 — mirror this exact FK order,
# drop lines 776-780's DRAFT-only gate entirely (out-of-scope status check
# for an offline, non-admin-API script)
await db.execute(
    delete(Utterance).where(Utterance.argument_id == argument_id)
    .execution_options(synchronize_session=False)
)
await db.execute(
    delete(PipelineRun).where(PipelineRun.argument_id == argument_id)
    .execution_options(synchronize_session=False)
)
await db.execute(
    delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument_id)
    .execution_options(synchronize_session=False)
)
await db.execute(
    delete(CaseArgument).where(CaseArgument.argument_id == argument_id)
    .execution_options(synchronize_session=False)
)
await db.execute(
    update(AdminJob).where(AdminJob.argument_id == argument_id)
    .values(argument_id=None)
    .execution_options(synchronize_session=False)
)
await db.execute(
    delete(Argument).where(Argument.id == argument_id)
    .execution_options(synchronize_session=False)
)
```
**Additions this new script needs beyond `delete_argument`'s cascade** (per RESEARCH.md's Fixture Delete-and-Reimport Lifecycle, items 6, 8, 9):
- Also delete `ArgumentStatusLog` rows where `argument_id == <this argument>` (defensive — `delete_argument` never needed this since DRAFT arguments never reach ArgumentStatusLog; a PIPELINE-status fixture-delete script has no such guarantee).
- Explicitly decide whether to also delete the `Case`/`CaseArgument` row for docket 642/term 1966 (recommended: yes, to exercise the Case-CREATE branch on re-import) — guard with a check for other `CaseArgument` links before deleting (Assumptions Log A2), matching the existing "check before delete" idiom already used at `_get_or_create_case` (import_convokit.py lines 259-315).
- Do NOT delete advocate `Person` rows — they re-match idempotently by `full_name`/`oyez_speaker_id` on reimport (`_resolve_person`, import_convokit.py lines 645-694).

**Safety pattern (STRIDE: Tampering/Repudiation mitigation):** scope every delete strictly by a looked-up `argument_id`/`case_id`, never by docket/term bulk match — mirror `delete_argument`'s own `.where(Model.argument_id == argument_id)` on every statement (already shown above).

---

### Test files (Pitfall 2 / Pitfall 3 / re-import verification coverage)

**Analog:** `pipeline/tests/test_import_convokit_core.py` lines 143-163 — the exact synthetic-fixture-writing helper any new test must reuse:
```python
def _write_corpus_fixture(
    tmp_path: Path,
    conversations: dict,
    cases: list[dict],
    speakers: dict,
) -> Path:
    """Write a small synthetic corpus_dir tree (never the real corpus files)."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(json.dumps(conversations), encoding="utf-8")
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    (corpus_dir / "utterances.jsonl").write_text("", encoding="utf-8")
    return corpus_dir
```
A Marshall-scenario test needs a synthetic speaker with `{"type": "J", "role": "justice"}` in the fake `speakers.json`, an `argued_date`-bearing case/transcript entry that predates a synthetic `CourtTenure` row's `start_date` for that same `Person`, and an assertion that the resulting `ArgumentParticipant.side` is NOT `BENCH` (or is flagged) once the fix lands — model the DB-session fixture on lines 120-140 of the same file (function-scoped `AsyncSession`, rollback after test, matches the project's Windows/asyncpg stale-event-loop workaround already documented there).

A `section_hint` test extends `pipeline/tests/test_import_convokit_utterances.py` in place — check whether it currently asserts `section_hint is None` (would need updating, not just extending) before adding a new assertion that populated `Utterance` rows carry a non-null `section_hint` matching the advocate side transitions, per RESEARCH.md's Wave 0 Gaps.

---

### `.planning/CORPUS-FIDELITY-DIFF.md` (durable diff/classification document, D-04)

**Analog:** `.planning/FIXTURES.md` — CONTEXT.md D-04 names this explicitly as the pattern to follow. Read `.planning/FIXTURES.md`'s own structure (ranked shortlist tables, per-fixture field notes, explicit caveats like the `_parse_argued_date` divergence warning) as the template for this phase's diff document's shape — one row per raw field, per table (cases, arguments, utterances, people, argument_participants, court_tenures), each classified as Faithful / Dropped / Mis-mapped / Defaulted, and each classification tagged with one of: real defect, apolitical allow-list exclusion, schema-absent field, upstream-missing data. The Field Inventory tables already assembled in `42-RESEARCH.md` (Architecture Patterns section) are the literal raw material to transcribe into this document — do not re-derive them from scratch.

## Shared Patterns

### Apolitical allow-list gate (applies to: diff script, any importer fix)
**Source:** `pipeline/corpus/apolitical.py` (full file, 74 lines)
**Apply to:** `scripts/diff_corpus_fixture.py`, any modified code path in `import_convokit.py`
```python
FORBIDDEN_FIELDS: frozenset[str] = frozenset(
    {"win_side", "win_side_detail", "votes", "votes_detail", "votes_side", "scdb_docket_id"}
)
```
Never pass a raw corpus dict into an ORM constructor, a JSONB column, or the committed diff document except through `extract_case_fields`/`extract_conversation_fields`.

### Async session handling (applies to: diff script's DB-read half, delete script, any test)
**Source:** `pipeline.db.get_session` (used throughout `import_convokit.py`, e.g. line 1075) and `pipeline/tests/test_import_convokit_core.py` lines 120-140 for the test-specific engine/session fixture.
**Apply to:** `scripts/diff_corpus_fixture.py`, `scripts/delete_fixture_argument.py`, new tests.

### Fail-fast CLI validation (V5) (applies to: any new CLI flag)
**Source:** `pipeline/commands/import_convokit.py::_resolve_terms` (lines 175-187), `_resolve_corpus_dir` (lines 190-205) — `argparse.ArgumentTypeError` on malformed input, `FileNotFoundError` on missing paths, validated before any file load.
**Apply to:** the new `--conversation-id` option (D-01) and any CLI flags on the new scripts.

### `(source_docket, question_number)` derivation — never hardcode 1 (applies to: scoped import path)
**Source:** `pipeline/commands/import_convokit.py::_next_question_number` (lines 318-340).
**Apply to:** any new scoped single-conversation import path (D-01) — must call this exact helper, per Phase 29 CR-01 and CONTEXT.md canonical refs.

### FK-ordered cascade delete (applies to: delete-and-reimport routine)
**Source:** `api/services/admin_arguments.py::delete_argument` (lines 743-822) — order: Utterance → PipelineRun → ArgumentParticipant → CaseArgument → AdminJob (NULL) → Argument.
**Apply to:** `scripts/delete_fixture_argument.py`, with the DRAFT-only gate removed and an added `ArgumentStatusLog` delete step.

## No Analog Found

None — every file identified from CONTEXT.md/RESEARCH.md has at least a role-match analog already in the codebase (see table above). The `court_tenures` integrity check (D-02) has no ConvoKit-diff analog by design (RESEARCH.md is explicit that this is a DB-side lookup against `data/corpus/supreme_court_justices_sections.csv`, not a diff against raw corpus source) — its query shape should follow the same `select(CourtTenure).where(...)` idiom shown above under the Marshall-fix pattern, not a new pattern.

## Metadata

**Analog search scope:** `pipeline/commands/`, `pipeline/corpus/`, `pipeline/tests/`, `scripts/`, `api/services/`, `api/models/`, `app/src/routes/cases/[slug]/arguments/[id]/`
**Files scanned:** `import_convokit.py` (1098 lines, read in full), `apolitical.py` (74 lines, full), `loader.py` (101 lines, full), `admin_arguments.py::delete_argument` (80 lines), `select_corpus_fixtures.py` (function signatures), `pipeline/__main__.py` (CLI wiring, lines 282-330), `test_import_convokit_core.py` (lines 120-190), `parse.py` (section_hint call sites), `models.py` (Person/CourtTenure/Case/Argument/CaseArgument/ArgumentParticipant column lists)
**Pattern extraction date:** 2026-07-30
