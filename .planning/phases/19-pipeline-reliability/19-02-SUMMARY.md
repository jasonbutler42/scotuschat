---
phase: 19
plan: "02"
subsystem: pipeline
tags:
  - cover-extractor
  - ingest
  - parse
  - sqlalchemy
  - docket-extraction
  - integrity-error
dependency_graph:
  requires:
    - alembic/versions/0011_add_source_docket_cover_metadata.py
    - api/models/models.py (Argument.source_docket, Argument.cover_metadata, Argument.argued_date nullable)
  provides:
    - pipeline/parser/cover_extractor.DOCKET_RE
    - pipeline/commands/ingest._run_ingest_inner (source_docket, nullable argued_date, IntegrityError)
    - pipeline/commands/parse._run_parse_inner Block C (cover_metadata write)
    - pipeline/commands/parse._run_parse_inner Block D (source_docket conditional write)
  affects:
    - All callers of ingest (job-driven path no longer generates synthetic argued_date)
    - All callers of parse (cover_metadata now always written; argued_date write is conditional)
tech_stack:
  added: []
  patterns:
    - TDD (RED/GREEN) for cover_extractor DOCKET_RE
    - IntegrityError catch-and-reraise as ValueError pattern (D-02)
    - Conditional UPDATE with .is_(None) WHERE clause (D-09)
    - execution_options(synchronize_session=False) on all UPDATE statements
key_files:
  created: []
  modified:
    - pipeline/parser/cover_extractor.py
    - pipeline/tests/test_cover_extractor.py
    - pipeline/commands/ingest.py
    - pipeline/commands/parse.py
decisions:
  - "[19-02]: DOCKET_RE compiled at module level: r'No\\.\\s+(\\d{1,2}-\\d+)' re.IGNORECASE — Alderson cover format; Heritage partial-match fallback accepted per D-10"
  - "[19-02]: Job-driven ingest path removes _derive_metadata_from_key call; primary_docket, case_name, argued_date left as None when operator did not supply them (D-03/D-08)"
  - "[19-02]: Argument.argued_date uses date.fromisoformat(argued_date) if argued_date else None — no synthetic today() date in job-driven mode (D-08)"
  - "[19-02]: IntegrityError from sqlalchemy.exc imported; wrap session.flush() in try/except that raises ValueError with readable duplicate message (D-02)"
  - "[19-02]: Filename/slug/term_year fallbacks when primary_docket or case_name is None: job-{job_id}-q{N}.pdf, job-{job_id} base_slug, date.today().year for term_year"
  - "[19-02]: parse.py Block A WHERE clause adds Argument.argued_date.is_(None) — conditional not unconditional (D-09)"
  - "[19-02]: parse.py Block C unconditional cover_metadata UPDATE; Block D conditional source_docket UPDATE with .is_(None) guard (D-09a, D-09b)"
  - "[19-02]: all_dockets list in ingest excludes None primary_docket — avoids Case row with docket_number=None"
metrics:
  duration: 4
  completed: "2026-06-30"
status: complete
---

# Phase 19 Plan 02: Pipeline Layer — Cover Extractor, Ingest, Parse Summary

**One-liner:** Extends cover_extractor with DOCKET_RE for docket extraction, updates ingest to populate source_docket and leave argued_date NULL when not provided with IntegrityError deduplication, and updates parse to write cover_metadata unconditionally and auto-populate null fields conditionally.

## What Was Built

### Task 1: Extend cover_extractor.py and add tests (TDD)

**RED phase commit:** `e4641849` — four failing test functions added to `pipeline/tests/test_cover_extractor.py`:
- `test_docket_re_matches_alderson_format` — expects `DOCKET_RE` to match "No. 14-556" with group(1)=="14-556"
- `test_docket_re_matches_longer_number` — expects match on "No. 23-1003" with group(1)=="23-1003"
- `test_docket_re_no_match_when_absent` — expects None on "No docket here."
- `test_extract_cover_metadata_still_failsafe` — confirms D-10 fail-safe preserved

**GREEN phase commit:** `1922a535` — `pipeline/parser/cover_extractor.py` updated:
- `DOCKET_RE = re.compile(r'No\.\s+(\d{1,2}-\d+)', re.IGNORECASE)` added after `TOC_AMICUS_RE`
- `primary_docket` extraction block added in `for raw in raws` loop (after `case_name`)
- Early-exit condition changed from `len(result) == 2` to `len(result) == 3`
- Fail-safe `except Exception: pass` block unchanged (D-10)
- All 25 tests pass (22 pre-existing + 3 new docket tests + 1 fail-safe test)

### Task 2: Update ingest.py

**Commit:** `7177c595` — three change groups in `pipeline/commands/ingest.py`:

**CHANGE 1 — IntegrityError import:**
`from sqlalchemy.exc import IntegrityError` added with other sqlalchemy imports.

**CHANGE 2 — Job-driven path:**
Replaced the `_derive_metadata_from_key` fallback block. `primary_docket`, `case_name`, `argued_date` are now left as-is (may be None) per D-03/D-08. The function definition is still present but is no longer called from the job-driven path.

**CHANGE 3 — Argument creation:**
```python
argument = Argument(
    argued_date=date.fromisoformat(argued_date) if argued_date else None,  # D-08: nullable
    question_number=args.question,
    source_docket=primary_docket or None,  # D-01: NULL when operator did not supply
)
```
Wrapped `session.flush()` in `try/except IntegrityError` that raises `ValueError(f"Duplicate argument: docket {primary_docket!r} Q{args.question} already exists.")`.

**Additional fallbacks (None safety):**
- `pdf_filename`: `f"job-{args.job_id}-q{args.question}.pdf"` when `primary_docket` is None
- `base_slug`: `f"job-{args.job_id}"` when `case_name` is None
- `term_year`: `date.today().year` when `argued_date` is None (Case.term_year is NOT NULL)
- `all_dockets` list excludes None primary_docket to prevent `Case(docket_number=None)`

**Verification:** `python -c "from pipeline.commands.ingest import _run_ingest_inner; print('import ok')"` exits 0.

### Task 3: Update parse.py

**Commit:** `f3d01cfc` — two changes in `pipeline/commands/parse.py` within the Phase 16 PARSE-01 block:

**CHANGE 1 — Block A conditional WHERE clause:**
```python
# Before (Phase 16 — always overwrite per D-04):
.where(Argument.id == source_run.argument_id)

# After (Phase 19 — only if NULL per D-09):
.where(Argument.id == source_run.argument_id, Argument.argued_date.is_(None))
```
Comment updated to reference D-09 / "only if currently NULL".

**CHANGE 2 — Block C and Block D added after Block B:**

Block C — cover_metadata unconditional write:
```python
await session.execute(
    update(Argument)
    .where(Argument.id == source_run.argument_id)
    .values(cover_metadata=cover_meta if cover_meta else None)
    .execution_options(synchronize_session=False)
)
```

Block D — source_docket conditional write (only when Argument.source_docket IS NULL):
```python
if cover_meta.get("primary_docket") is not None:
    await session.execute(
        update(Argument)
        .where(Argument.id == source_run.argument_id, Argument.source_docket.is_(None))
        .values(source_docket=cover_meta["primary_docket"])
        .execution_options(synchronize_session=False)
    )
```

Both blocks placed before Step 8 (run.status = COMPLETED) and inside the existing main `async with get_session()` block.

**Verification:** `python -c "from pipeline.commands.parse import run_parse; print('import ok')"` exits 0.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All changes are pipeline logic — no UI rendering, placeholder text, or hardcoded empty values.

## Threat Flags

No new security-relevant surface beyond the plan's threat model. All changes are within the pipeline-only write path (T-19-02-01 through T-19-02-04 accepted per threat register).

## Self-Check

| Artifact | Status |
|----------|--------|
| pipeline/parser/cover_extractor.py DOCKET_RE | FOUND — module-level, committed at 1922a535 |
| DOCKET_RE matches "No. 14-556" group(1)=="14-556" | VERIFIED — test_docket_re_matches_alderson_format PASSED |
| DOCKET_RE matches "No. 23-1003" group(1)=="23-1003" | VERIFIED — test_docket_re_matches_longer_number PASSED |
| DOCKET_RE.search("No docket here.") is None | VERIFIED — test_docket_re_no_match_when_absent PASSED |
| primary_docket extraction in for-raw-in-raws loop | FOUND — in extract_cover_metadata |
| early-exit len(result)==3 | VERIFIED — in extract_cover_metadata |
| fail-safe except Exception: pass unchanged | VERIFIED — unchanged |
| 4 new test functions in test_cover_extractor.py | FOUND — all 25 tests pass |
| pipeline/commands/ingest.py IntegrityError import | FOUND — committed at 7177c595 |
| job-driven path no longer calls _derive_metadata_from_key | VERIFIED — grep shows 0 calls |
| Argument.source_docket=primary_docket or None | FOUND — in Argument creation |
| argued_date nullable: date.fromisoformat(argued_date) if argued_date else None | FOUND |
| try/except IntegrityError wrapping flush | FOUND — raises ValueError with "Duplicate argument" |
| filename fallback for None primary_docket | FOUND — job-{job_id}-q{N}.pdf |
| pipeline/commands/parse.py Block A WHERE adds argued_date.is_(None) | FOUND — committed at f3d01cfc |
| parse.py Block C unconditional cover_metadata UPDATE | FOUND — with execution_options |
| parse.py Block D conditional source_docket UPDATE | FOUND — with .is_(None) and execution_options |
| Both new blocks inside existing main session | VERIFIED — not a new async with get_session() |
| python -m pytest pipeline/tests/test_cover_extractor.py -v | 25 passed, 0 failed |
| all imports ok (ingest + parse) | VERIFIED — both exit 0 |

## Self-Check: PASSED

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1: Tests (RED) | e4641849 | test(19-02): add failing tests for DOCKET_RE and docket extraction (RED) |
| Task 1: Implementation (GREEN) | 1922a535 | feat(19-02): extend cover_extractor with DOCKET_RE and primary_docket extraction (GREEN) |
| Task 2: ingest.py | 7177c595 | feat(19-02): update ingest — source_docket, nullable argued_date, IntegrityError (D-01/D-02/D-08) |
| Task 3: parse.py | f3d01cfc | feat(19-02): update parse — conditional argued_date write, Block C/D cover metadata (D-09) |
