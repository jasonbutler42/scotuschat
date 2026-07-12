---
phase: 29-historical-corpus-import
reviewed: 2026-07-10T14:36:18Z
depth: standard
files_reviewed: 27
files_reviewed_list:
  - alembic/versions/0017_add_oyez_external_ids.py
  - api/models/models.py
  - api/schemas/cases.py
  - api/schemas/utterance.py
  - api/services/arguments.py
  - api/tests/test_argument_oyez_field.py
  - api/tests/test_case_item_argued_date_optional.py
  - app/src/lib/components/TopNav.svelte
  - app/src/routes/attributions/+page.svelte
  - app/src/routes/cases/[slug]/+page.svelte
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
  critical: 0
  warning: 9
  info: 4
  total: 13
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-07-10T14:36:18Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

This is a re-review after gap-closure plan 29-09 (commit `7bb1c5a2`, "derive per-docket question_number, add docket_question_conflict counter"), which set out to fix the prior BLOCKER, CR-01: `pipeline/commands/import_convokit.py`'s dedup logic hard-coded `question_number=1` for every corpus-imported `Argument`, which collided with the real `uq_arguments_source_docket_question` DB constraint for reargued cases or dockets already ingested via the ordinary PDF pipeline, silently folding the failure into the generic `conversations_errored` counter.

**CR-01 fix verdict: sound for its stated purpose.** `_next_question_number` now derives the next available `question_number` for a `source_docket` via `select(func.max(Argument.question_number)).where(Argument.source_docket == source_docket)`, correctly aligning with the real DB constraint. Because each conversation is imported inside its own `get_session()` context (a fresh transaction per conversation, committed before the next conversation is processed in `run_import_convokit`'s loop), sequential same-docket conversations correctly observe prior commits and increment 1 → 2 → 3, etc. The defense-in-depth `except IntegrityError: await session.rollback()` safety net (for a residual race, e.g. a concurrent writer) correctly rolls back before returning, and is counted in a new, distinct `docket_question_conflict` counter rather than folded into `conversations_errored`, exactly as the gap called for. Two new tests (`test_docket_already_at_question_number_1_imports_at_question_number_2`, `test_forced_collision_increments_docket_question_conflict_not_errored`) exercise both the normal-derivation path and the safety-net rollback path directly.

**However, the rollback safety net has an untested side effect that is a new defect introduced by this fix** — see WR-07 below: it can cause the printed per-batch summary to overreport `cases_created` when the colliding conversation's `Case` row is newly created in the same transaction that gets rolled back. The new regression test for the collision path pre-seeds the `Case` row so it already exists, which is exactly the combination that hides this drift.

Beyond the CR-01 fix, this pass re-verified every previously-reported item directly against the current file contents (none had been touched by 29-09, since that plan only modified `import_convokit.py`'s question-number logic) and found all six prior warnings and four prior info items still present and unfixed (re-affirmed below, not carried over blindly). Two further new issues were found during this pass's full read of `import_convokit.py`: a data-loss edge case in mixed spoken/stage-direction turns with no resolvable speaker (WR-08), and a Person-identity merge risk in the exact-`full_name` fallback match (WR-09). No new BLOCKER-level issues were found.

## Warnings

### WR-07 (new — introduced by the 29-09 fix): `cases_created` counter is not reverted when the docket/question rollback discards the `Case` it just created

**File:** `pipeline/commands/import_convokit.py:251-252` (increment) and `:354-373` (rollback path)

**Issue:** `_get_or_create_case` increments `counters["cases_created"]` immediately after flushing a newly-created `Case` row (line 252), *before* the Argument insert that follows in `_import_conversation` is attempted. If that Argument insert then hits the `uq_arguments_source_docket_question` constraint (the CR-01 safety-net path added by 29-09), the code calls `await session.rollback()` (line 363), which reverts the entire transaction — including the `Case` row flushed moments earlier in the *same* transaction. The DB correctly ends up with no orphan `Case` row, but `counters["cases_created"]` is a plain Python `int` and is never decremented on this path. The final `_print_summary` (D-14) will therefore report a case as "created" that does not actually exist in the database.

This is reachable whenever a **brand-new** docket (no pre-existing `Case` row) also collides on `(source_docket, question_number)` at flush time. The new regression test (`test_forced_collision_increments_docket_question_conflict_not_errored`) pre-seeds the `Case` row before forcing the collision, so `cases_created` is never incremented on that path and this drift is not caught by the new test suite.

**Fix:** Track whether `_get_or_create_case` actually created a new row, and only increment `cases_created` after the Argument flush succeeds:

```python
async def _get_or_create_case(session, case_fields, counters):
    ...
    session.add(new_case)
    await session.flush()
    return new_case, True  # (case, is_new) — caller decides when to count it

# in _import_conversation:
case, case_is_new = await _get_or_create_case(session, case_fields, counters)
...
try:
    await session.flush()
except IntegrityError:
    await session.rollback()
    counters["docket_question_conflict"] += 1
    return
counters["arguments_created"] += 1
if case_is_new:
    counters["cases_created"] += 1
```

### WR-08 (new): A mixed turn with no resolvable speaker silently drops its stage-direction segment too

**File:** `pipeline/commands/import_convokit.py:658-687` (`_import_utterances`)

**Issue:** When a turn's `\n`-delimited segments mix spoken text with an inline stage-direction marker (D-16), only the spoken rows actually need a resolved speaker — a stage-direction row is always written with `raw_speaker_label=None`/`person_id=None`. But the current logic gates on the *whole turn*: if `any(not is_stage for _, is_stage in rows)` and `turn.get("speaker")` is falsy, the code increments `utterance_rows_errored` and does `continue`, which skips **every** row produced from this turn — including the marker segment(s) that never needed a speaker in the first place:

```python
if any(not is_stage for _, is_stage in rows):
    speaker_id = turn.get("speaker")
    if not speaker_id:
        counters["utterance_rows_errored"] += 1
        print(...)
        continue   # <-- also drops any stage-direction row(s) split from this same turn
```

**Fix:** Only skip the spoken rows when the speaker cannot be resolved; still write any stage-direction rows unconditionally:

```python
for row_text, is_stage in rows:
    sequence += 1
    if is_stage:
        session.add(Utterance(..., raw_speaker_label=None, side=SideEnum.UNKNOWN, person_id=None, ...))
        counters["stage_direction_utterances_created"] += 1
        continue
    if participant is None:
        counters["utterance_rows_errored"] += 1
        continue
    session.add(Utterance(..., raw_speaker_label=participant.raw_speaker_label, ...))
```

### WR-09 (new): Exact `full_name` match in `_resolve_person` can silently merge two different real people into one `Person` row

**File:** `pipeline/commands/import_convokit.py:471-485` (`_resolve_person`)

**Issue:** When a speaker id has no `oyez_speaker_id` match, `_resolve_person` falls back to `select(Person).where(Person.full_name == full_name)`. There is no uniqueness constraint on `people.full_name` and no additional disambiguation (era, role, docket). Across ~70 years of historical justices and advocates spanned by this corpus, two different real individuals sharing an identical display name will resolve to the same `Person` row, and the second speaker's `oyez_speaker_id` gets backfilled onto the wrong person, permanently binding that identity going forward. Given the apolitical-framing hard constraint (every speaker gets identical, non-derived treatment), a misattributed identity is a correctness defect in the historical record, not a cosmetic one.

**Fix:** At minimum, increment a new counter (e.g. `people_full_name_ambiguous_match`) and print a `WARNING` whenever a full-name-only match is used, so operators can audit these merges after an import; consider also requiring the fallback match's existing `Person.is_justice` to agree with the new speaker's `is_justice` classification before reusing the row.

### WR-01: Stage-direction whole-turn regex accepts mismatched bracket/paren pairs

**File:** `pipeline/corpus/stage_directions.py:48`

**Status:** re-verified, still present, unfixed by 29-09 (not in scope for that plan).

**Issue:** `_WHOLE_TURN_MARKER_RE = re.compile(r"^\s*[\[\(]([^\[\]\(\)]*)[\]\)]\s*$")` allows the opening delimiter to be `[` or `(` independently of the closing delimiter, which can also be `]` or `)`. A turn whose text is exactly `"(Laughter]"` or `"[Recess)"` would match and be misclassified as a stage direction, even though the module's own docstring states the intent is "a curated vocabulary inside EITHER brackets or parens" — implying a matched pair, not an arbitrary open/close mix.

**Fix:**

```python
_WHOLE_TURN_MARKER_RE = re.compile(r"^\s*(?:\[([^\[\]]*)\]|\(([^\(\)]*)\))\s*$")
# then: inner = _normalize(match.group(1) or match.group(2))
```

### WR-02: Multi-term rollup silently drops `participants_created`

**File:** `pipeline/commands/import_convokit.py:751-760`

**Status:** re-verified, still present, unfixed by 29-09.

**Issue:** `_SUMMARY_COUNTER_KEYS` (used by both `_new_counters()` and `_accumulate_counters()`) does not include `"participants_created"`, even though `_new_counters()` separately initializes it (`| {"participants_created": 0}`) and `_resolve_and_link_participant` increments it on every run. Because `_accumulate_counters` only iterates `_SUMMARY_COUNTER_KEYS`, a `--term-range` spanning multiple terms will always report a rollup `participants_created` of `0`, regardless of how many participants were actually created across the range.

**Fix:** Add `"participants_created"` to `_SUMMARY_COUNTER_KEYS` (and print it in `_print_summary`).

### WR-03: `import_justices_csv._parse_optional_date` has no error handling, and the importer has no per-row resilience

**File:** `pipeline/commands/import_justices_csv.py:102-107, 141-230`

**Status:** re-verified, still present, unfixed.

**Issue:** `_parse_optional_date` calls `dateutil_parser.parse(value).date()` with no `try/except`, unlike `import_convokit.py`'s `_parse_argued_date` (which explicitly catches `(ValueError, OverflowError)` and treats a bad date as "no date" rather than a fatal error). `run_import_justices_csv` also has no per-row try/except around its CSV loop — the entire import runs inside a single `async with get_session() as session:` block (one transaction for the whole file), so one row with an unparseable date, or any other unexpected exception, raises out of the loop and rolls back *every* upgrade/creation already staged in that run, with no summary ever printed. This is inconsistent with the per-conversation resilience pattern (T-29-05b) deliberately built into `import_convokit.py` for the same class of problem (malformed input in an operator-supplied file).

**Fix:** Wrap `_parse_optional_date`'s `dateutil_parser.parse` call in the same `(ValueError, OverflowError)` catch used by `_parse_argued_date`; wrap the per-row loop body in `try/except`, counting/reporting a bad row rather than aborting the whole run.

### WR-04: New `oyez_*` external-ID columns used as sole application-level dedup keys have no DB-level uniqueness backing

**File:** `alembic/versions/0017_add_oyez_external_ids.py:34-58`

**Status:** re-verified, still present, unfixed.

**Issue:** `arguments.oyez_transcript_id` and `people.oyez_speaker_id` are both used as the *sole* idempotency key for a SELECT-then-INSERT pattern (`_import_conversation`'s existing-argument check; `_resolve_person`'s existing-Person-by-`oyez_speaker_id` check), but neither column has a `UNIQUE` constraint or index. Every comparable existing dedup key in this schema (`cases.docket_number`, `cases.slug`, `speaker_alias.normalized_label`) is backed by a DB-level `unique=True`. Without one here, there is no DB-level backstop against duplicate rows if the CLI is ever interrupted and re-run in a way that races with itself, and every dedup `SELECT` against these columns is an unindexed full-table scan.

**Fix:** Add unique indexes on `arguments.oyez_transcript_id` and `people.oyez_speaker_id` in a follow-up migration (both columns are nullable, which is compatible with a unique index under Postgres's multiple-`NULL`s semantics).

### WR-05: `pipeline/corpus/loader.py` has no error handling around JSON parsing — a single bad line aborts the whole batch

**File:** `pipeline/corpus/loader.py:40, 52, 69, 85`

**Status:** re-verified, still present, unfixed.

**Issue:** `stream_utterances_for_conversation_ids`, `load_conversations_for_term`, `load_speakers`, and `load_cases` all call `json.loads`/`json.load` with no `try/except`. `import_convokit.py`'s design goes to considerable lengths to make per-conversation and per-utterance-row failures non-fatal, but none of that resilience covers the file-loading/streaming layer. A single malformed/corrupted line anywhere in the ~900MB `utterances.jsonl` (or the smaller `conversations.json`/`cases.jsonl`) raises an unhandled `json.JSONDecodeError` that aborts the entire `import-convokit` invocation, including a multi-term `--term-range` batch, with no per-row recovery.

**Fix:** Wrap the per-line `json.loads` calls in `loader.py` in a `try/except json.JSONDecodeError`, skip/count the bad line, and let the caller's existing counters (or a new `rows_errored` counter) surface it in the per-batch summary.

### WR-06: Advocates resolved only from utterance turns (not `conversations.json`'s `advocates` dict) are silently recorded as `SideEnum.UNKNOWN` with no flag

**File:** `pipeline/commands/import_convokit.py:661-687`

**Status:** re-verified, still present, unfixed.

**Issue:** `_import_utterances` calls `_resolve_and_link_participant(..., side_code=None, ...)` for any speaker encountered in `turns` that wasn't already present in `resolved_participants` (i.e., not listed in the conversation's `advocates` dict). Because `side_code=None`, `_ADVOCATE_SIDE_MAP.get(None, SideEnum.UNKNOWN)` always resolves to `UNKNOWN` for non-justice speakers picked up this way — silently. Unlike the missing/ambiguous-`type` case (which increments `counters["speakers_flagged"]` and prints a `WARNING`), this genuinely-unknown-side case is never counted or logged, so an operator reviewing the D-14 per-batch summary has no way to know how many advocate participants ended up with an indeterminate side.

**Fix:** Increment `counters["speakers_flagged"]` (or a dedicated counter) and print a `WARNING` when a non-justice participant is resolved with `side_code=None`, so this gap is visible in the batch summary rather than silent.

## Info

### IN-01: `TopNav.svelte`'s `variant` prop is declared but never used

**File:** `app/src/lib/components/TopNav.svelte:2`

**Status:** re-verified, still present.

**Issue:** `let { variant }: { variant: 'public' } = $props();` destructures `variant`, but the template never references it — the markup is identical regardless of the prop's value, and the type only permits the single literal `'public'`.

**Fix:** Either implement the admin variant the prop implies, or drop the prop entirely and hardcode the public nav markup (matches actual usage).

### IN-02: `ArgumentParticipant` dedup keyed on `raw_speaker_label`, not `person_id`

**File:** `pipeline/commands/import_convokit.py:543-549`

**Status:** re-verified, still present.

**Issue:** `_resolve_and_link_participant` checks for an existing `ArgumentParticipant` via `(argument_id, raw_speaker_label)` rather than `(argument_id, person_id)`. Two distinct `speaker_id`s in the same conversation that happen to share an identical display name would collapse into a single shared `ArgumentParticipant` row keyed off whichever one resolved first, silently misattributing the second speaker's turns to the first's participant record.

**Fix:** Consider deduping on `(argument_id, person_id)` when `person_id` is available, falling back to `raw_speaker_label` only when it isn't; at minimum, document the assumption inline near the dedup query.

### IN-03: Unreachable `if not rows: continue` branch in `_import_utterances`

**File:** `pipeline/commands/import_convokit.py:655-656`

**Status:** re-verified, still present.

**Issue:** `_split_turn_into_rows` always returns at least one `(text, bool)` tuple — even an empty-string `text` produces one row, since `"".split("\n")` yields `[""]` and the `pending` list (`[""]`) is truthy when flushed. The `if not rows: continue` guard can therefore never trigger; a turn with legitimately empty text silently creates an `Utterance` row with empty text rather than being skipped.

**Fix:** Remove the dead branch, or (if the intent was to skip genuinely empty turns) change `_split_turn_into_rows`/its caller to explicitly filter out an all-empty result.

### IN-04: Stale "out-of-scope" comment in a now-passing regression test

**File:** `api/tests/test_argument_oyez_field.py:150-157`

**Status:** re-verified, still present.

**Issue:** The docstring for `test_utterances_endpoint_returns_200_for_null_argued_date` still describes the `PipelineRun.step="ingest"` vs. `step=="parse"` mismatch as "a separate, out-of-scope" issue deferred to a later plan. Plan 29-08 has since fixed that exact mismatch (confirmed by `test_import_convokit_utterances.py::test_utterances_readable_via_arguments_service_after_import`), so this comment is now stale and could mislead a future reader into thinking the gap is still open.

**Fix:** Update the docstring to note the mismatch was resolved by 29-08 and point at the test that now covers it end-to-end.

---

_Reviewed: 2026-07-10T14:36:18Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
