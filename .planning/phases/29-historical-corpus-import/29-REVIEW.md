---
phase: 29-historical-corpus-import
reviewed: 2026-07-10T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - alembic/versions/0017_add_oyez_external_ids.py
  - api/models/models.py
  - api/schemas/utterance.py
  - api/services/arguments.py
  - api/tests/test_argument_oyez_field.py
  - app/src/lib/components/TopNav.svelte
  - app/src/routes/attributions/+page.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - data/corpus/.gitignore
  - data/corpus/.gitkeep
  - pipeline/__main__.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/import_justices_csv.py
  - pipeline/corpus/__init__.py
  - pipeline/corpus/apolitical.py
  - pipeline/corpus/loader.py
  - pipeline/corpus/stage_directions.py
  - pipeline/tests/test_corpus_apolitical.py
  - pipeline/tests/test_corpus_loader.py
  - pipeline/tests/test_corpus_stage_directions.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_import_convokit_utterances.py
  - pipeline/tests/test_import_justices_csv.py
findings:
  critical: 1
  warning: 4
  info: 2
  total: 7
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-07-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the historical-corpus-import pipeline (`import_convokit.py`, `import_justices_csv.py`, `pipeline/corpus/*`), the associated migration/model/schema changes, and the frontend attribution surface.

**Apolitical boundary (explicitly requested focus):** `pipeline/corpus/apolitical.py` is confirmed to be the sole path raw `conversations.json`/`cases.jsonl` dicts take into ORM fields. Both `_import_conversation` and `_get_or_create_case` in `import_convokit.py` only ever read from the allowlisted `conversation`/`case_fields` dicts returned by `apolitical.extract_conversation_fields`/`extract_case_fields`, and every `Case(...)`/`Argument(...)` constructor call passes explicit named kwargs (never `Case(**case_fields)` or similar unpacking), so a forbidden key present in the allowlisted dict could not silently reach an ORM column even if the allowlist were ever misconfigured. `win_side`/`votes*`/`scdb_docket_id` are not read anywhere in `import_convokit.py` or `import_justices_csv.py`. This boundary holds.

The one critical finding is a schema/data mismatch: the public utterances endpoint's response model requires a non-null `argued_date`, but the new historical importer can legitimately produce `Argument` rows with `argued_date = None`, and the frontend was explicitly built to handle that null case — meaning the two halves of this feature disagree about nullability and the mismatch is untested. Several warnings cover missing DB-level integrity backstops and inconsistent error-handling postures between the two new importers.

## Critical Issues

### CR-01: `ArgumentMetadataResponse.argued_date` is non-optional but the new importer can produce NULL

**File:** `api/schemas/utterance.py:47`, `api/services/arguments.py:130`, `pipeline/commands/import_convokit.py:192-210`

**Issue:** `pipeline/commands/import_convokit.py`'s `_parse_argued_date` returns `None` whenever a `cases.jsonl` row has an empty/missing `"transcripts"` list, no `"name"` on the first entry, or a `"name"` string `dateutil` can't fuzzy-parse (`ValueError`/`OverflowError` caught and swallowed). `Argument.argued_date` is nullable (`api/models/models.py`, Phase 19/D-08), so this is a real, reachable state for corpus-imported rows — not merely hypothetical.

`api/services/arguments.py:130` passes `argument.argued_date` straight through into the response dict, and `GET /arguments/{argument_id}/utterances` is declared with `response_model=ArgumentUtterancesResponse` (`api/routers/arguments.py:27`). `ArgumentMetadataResponse.argued_date` is typed `datetime.date` (non-Optional, `api/schemas/utterance.py:47`). FastAPI/Pydantic v2 validates the *outgoing* payload against the response model, so any historical argument with an unparseable/missing date will raise a `ResponseValidationError` and return an HTTP 500 for that argument's page — for both the admin preview and, once published, the public site.

Tellingly, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`'s `formatDate()` helper (line 54-55: `if (!dateStr) return 'Date unknown';`) was explicitly written to handle a null `argued_date` — but the backend contract makes that branch unreachable, because the request never successfully returns for that case. The two sides of this feature disagree, and no test in the reviewed suite exercises it: every fixture in `test_import_convokit_core.py` / `test_import_convokit_utterances.py` supplies a valid, parseable `transcripts` entry, so this path is silently untested.

**Fix:**
```python
# api/schemas/utterance.py
class ArgumentMetadataResponse(BaseModel):
    ...
    argued_date: datetime.date | None = None  # nullable — matches Argument.argued_date (D-08) and frontend's "Date unknown" handling
```
Add a regression test with a `cases.jsonl` fixture that has no `"transcripts"` entry (or an unparseable date string) asserting `GET /arguments/{id}/utterances` returns 200 with `argued_date: null`, not a 500.

## Warnings

### WR-01: No unique constraint/index on the new `oyez_*` external-ID columns

**File:** `alembic/versions/0017_add_oyez_external_ids.py:34-58`, `api/models/models.py` (`Argument.oyez_transcript_id`, `Case.oyez_case_id`, `Person.oyez_speaker_id`)

**Issue:** All three idempotency checks in `import_convokit.py` (`Argument.oyez_transcript_id` dedup at line 300-305, `Person.oyez_speaker_id` lookup at line 410-413) rely purely on application-level check-then-insert against columns that carry no `unique=True`/index at the DB layer — unlike the existing precedent in this same file (`Case.docket_number` is `unique=True`; `Argument` has `uq_arguments_source_docket_question`). This means: (1) there is no DB-level backstop against duplicate rows if the CLI is ever interrupted and re-run in a way that races with itself, or invoked twice concurrently against the same term; and (2) every dedup `SELECT` against these columns is an unindexed full-table scan.

**Fix:** Add a follow-up migration with `op.create_unique_constraint`/`op.create_index` on `arguments.oyez_transcript_id`, `people.oyez_speaker_id`, and (if desired) `cases.oyez_case_id`, matching the existing `uq_arguments_source_docket_question` pattern already used in this table.

### WR-02: `pipeline/corpus/loader.py` has no error handling around JSON parsing — a single bad line crashes the whole batch

**File:** `pipeline/corpus/loader.py:40, 52, 69, 85`; `pipeline/commands/import_convokit.py:769-780`

**Issue:** `stream_utterances_for_conversation_ids`, `load_conversations_for_term`, `load_speakers`, and `load_cases` all call `json.loads`/`json.load` with no `try/except`. `import_convokit.py`'s design goes to considerable lengths to make per-conversation and per-utterance-row failures non-fatal (`T-29-05b`, "Pitfall 5", `counters["conversations_errored"]`, `counters["utterance_rows_errored"]`) — but none of that resilience covers the file-loading/streaming layer itself. A single malformed/corrupted line anywhere in the ~900MB `utterances.jsonl` (or the smaller `conversations.json`/`cases.jsonl`) raises an unhandled `json.JSONDecodeError` that aborts the entire `import-convokit` invocation, including a multi-term `--term-range` batch, with no per-row recovery — directly at odds with the resilience goal documented throughout the rest of the module.

**Fix:** Wrap the per-line `json.loads` calls in `loader.py` in a `try/except json.JSONDecodeError`, skip/count the bad line, and let the caller's existing counters (or a new `rows_errored` counter) surface it in the per-batch summary, consistent with how `_import_utterances` already handles malformed turns.

### WR-03: Advocates resolved only from utterance turns (not `conversations.json`'s `advocates` dict) are silently recorded as `SideEnum.UNKNOWN` with no flag

**File:** `pipeline/commands/import_convokit.py:601-626`

**Issue:** `_import_utterances` calls `_resolve_and_link_participant(..., side_code=None, ...)` for any speaker encountered in `turns` that wasn't already present in `resolved_participants` (i.e., not listed in the conversation's `advocates` dict). Because `side_code=None`, `_ADVOCATE_SIDE_MAP.get(None, SideEnum.UNKNOWN)` always resolves to `UNKNOWN` for non-justice speakers picked up this way — silently. Unlike the missing/ambiguous-`type` case (which increments `counters["speakers_flagged"]` and prints a `WARNING`), this genuinely-unknown-side case is never counted or logged, so an operator reviewing the D-14 per-batch summary has no way to know how many advocate participants ended up with an incorrect/indeterminate side because they weren't in the advocates dict.

**Fix:** Increment `counters["speakers_flagged"]` (or a dedicated counter) and print a `WARNING` when a non-justice participant is resolved with `side_code=None`, so this gap is visible in the batch summary rather than silent.

### WR-04: `import_justices_csv._parse_optional_date` has no exception handling for malformed (non-blank) dates

**File:** `pipeline/commands/import_justices_csv.py:102-107`

**Issue:** `_parse_optional_date` only special-cases blank/whitespace-only cells; any non-blank but malformed date string raises an uncaught exception from `dateutil_parser.parse(value)` (no `fuzzy=True`, no `try/except`), aborting the entire `import-justices` run for the whole CSV (spanning 100+ historical justices) with no per-row recovery. This is inconsistent with its sibling importer's `_parse_argued_date` in `import_convokit.py`, which explicitly catches `(ValueError, OverflowError)` and degrades to `None`, and with this same module's own `rows_skipped` counter, which exists for other malformed-row cases but is never incremented here.

**Fix:** Wrap the `dateutil_parser.parse(value)` call in a `try/except (ValueError, OverflowError)`, count/log the bad row (or bad cell), and continue rather than crashing the whole CSV import.

## Info

### IN-01: `ArgumentParticipant` dedup keyed on `raw_speaker_label`, not `person_id`

**File:** `pipeline/commands/import_convokit.py:482-487`

**Issue:** `_resolve_and_link_participant` checks for an existing `ArgumentParticipant` via `(argument_id, raw_speaker_label)` rather than `(argument_id, person_id)`. Two distinct `speaker_id`s in the same conversation that happen to share an identical display name (e.g. two same-named advocates) would collapse into a single shared `ArgumentParticipant` row keyed off whichever one resolved first, silently misattributing the second speaker's turns to the first's participant record. This is a low-probability edge case given the corpus's naming conventions, but worth a code comment noting the assumption, since the analogous `Person`-level full_name dedup (D-13) is explicitly documented as a known tradeoff while this one isn't.

**Fix:** Consider deduping on `(argument_id, person_id)` when `person_id` is available, falling back to `raw_speaker_label` only when it isn't; at minimum, document the assumption inline near the dedup query.

### IN-02: `TopNav.svelte`'s `variant` prop is declared but never branched on

**File:** `app/src/lib/components/TopNav.svelte:2`

**Issue:** `variant: 'public'` is typed as a single-value literal and both call sites (`app/src/routes/+layout.svelte`, `app/src/routes/admin/+layout.svelte`) pass `variant="public"`, but the component template never reads `variant` to change its rendering — it always renders the same public-style nav (Cases/Attributions/Admin links) regardless of the prop's value. `AdminSubNav.svelte`'s comment ("same as TopNav admin variant") references an admin variant that doesn't actually exist in this component. The prop is effectively dead/vestigial.

**Fix:** Either remove the unused `variant` prop until an actual admin-specific variant is implemented, or implement the branching the comment implies.

---

_Reviewed: 2026-07-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
