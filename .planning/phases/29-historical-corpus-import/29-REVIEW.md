---
phase: 29-historical-corpus-import
reviewed: 2026-07-10T00:00:00Z
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
  critical: 1
  warning: 6
  info: 4
  total: 11
status: issues_found
---

# Phase 29: Code Review Report

**Reviewed:** 2026-07-10T00:00:00Z
**Depth:** standard
**Files Reviewed:** 27
**Status:** issues_found

## Summary

This is a re-review of the historical-corpus-import phase after two
gap-closure plans (29-07, 29-08) landed on top of the original six plans. A
prior review (`29-REVIEW.md`, superseded by this report) had found the
`argued_date` non-optional-over-nullable-column defect as CR-01; that
specific finding is confirmed fixed and correctly integrated. Per the review
brief, extra scrutiny was applied to both gap-closure changes:

- **29-07 (argued_date nullability):** `api/schemas/cases.py::CaseItem` and
  `api/schemas/utterance.py::ArgumentMetadataResponse` both now declare
  `argued_date: datetime.date | None = None`, matching the nullable
  `Argument.argued_date` column (`api/models/models.py:175`). No other
  schema in the reviewed set treats `argued_date` as non-optional over this
  column, and `api/services/arguments.py` passes the raw (possibly-`None`)
  value straight through without re-validating it. Regression tests
  (`test_argument_oyez_field.py`, `test_case_item_argued_date_optional.py`)
  cover both schemas directly, including a live-DB round trip through
  `get_argument_with_utterances`. **This fix is correctly and consistently
  integrated.**
- **29-08 (`PipelineRun.step` relabel):** `pipeline/commands/import_convokit.py`
  now stamps every corpus-imported `PipelineRun` with `step="parse"`
  (line 342), matching the filter `api/services/arguments.py:87` already
  used (`PipelineRun.step == "parse"`, `status == COMPLETED`). This is
  verified end-to-end by
  `test_import_convokit_utterances.py::test_utterances_readable_via_arguments_service_after_import`,
  which runs the real importer and the real `get_argument_with_utterances`
  together and asserts utterances actually come back. No other reviewed
  code path assumes `step == "ingest"` for a corpus-imported argument — the
  `admin_jobs`-based `step` lookups elsewhere in the codebase are keyed by
  `job_id`, and corpus-imported arguments never have an `admin_jobs` row, so
  they simply don't participate in that flow (by design, not by accident).
  **This fix is correctly and consistently integrated.**

However, deeper tracing of `import_convokit.py` against the `arguments`
table's actual DB constraints surfaced a new, untested **data-loss defect**
(CR-01 below, distinct from the previous review's CR-01): the importer's
idempotency check and the database's real uniqueness constraint are keyed on
two different things, so any docket that legitimately needs a second
`Argument` row (a reargued case, or a docket already ingested through the
ordinary PDF pipeline) has its corpus import silently swallowed into a
generic error counter rather than imported or clearly flagged.

Most of the previous review's warnings and info items were outside the
scope of what 29-07/29-08 set out to fix and remain open in the current
code — they are re-affirmed below (re-verified directly against the current
file contents, not carried over blindly) alongside two new warnings and two
new info items found during this pass.

## Critical Issues

### CR-01: Corpus import silently drops arguments for any docket that collides with an existing Argument row (reargued cases / dockets already PDF-ingested)

**File:** `pipeline/commands/import_convokit.py:299-320`
**Also relevant:** `api/models/models.py:207-216` (the `UniqueConstraint` that actually fires)

**Issue:**

`_import_conversation`'s idempotency check is keyed *only* on
`Argument.oyez_transcript_id`:

```python
existing_argument_result = await session.execute(
    select(Argument).where(Argument.oyez_transcript_id == conversation_id)
)
if existing_argument_result.scalar_one_or_none() is not None:
    counters["skipped_existing"] += 1
    return
```

But every corpus-imported `Argument` is created with a hard-coded
`question_number=1`:

```python
argument = Argument(
    argued_date=argued_date,
    question_number=1,
    source_docket=case_fields["docket_no"],
    status=ArgumentStatusEnum.DRAFT,
    oyez_transcript_id=conversation_id,
)
session.add(argument)
await session.flush()
```

`arguments` has a real DB constraint on the *other* key:

```python
UniqueConstraint("source_docket", "question_number", name="uq_arguments_source_docket_question")
```

Two ways this fires in production:

1. **Reargued cases.** ConvoKit's corpus spans terms where several cases
   were reargued (a second oral argument for the same docket, under a
   different `conversation_id`). The importer has no concept of a second
   `question_number` for corpus rows — every row is `question_number=1` —
   so the second conversation's `INSERT` violates the unique constraint.
2. **Overlap with the ordinary PDF-ingest pipeline.** Any docket already
   ingested manually via `pipeline ingest` (e.g. the flagship `14-556`
   Obergefell example used throughout this codebase's own docs, argued in
   the 2014 term, well within ConvoKit's covered range) already occupies
   `(source_docket="14-556", question_number=1)`. Running
   `import-convokit --term 2014` (or any range spanning an already-ingested
   docket) hits the same constraint for that docket's corpus record.

Because `session.flush()` is called immediately after `session.add(argument)`,
the resulting `IntegrityError` propagates out of `_import_conversation`
(nothing catches it locally) and is caught only by the blanket handler in
`run_import_convokit`:

```python
except Exception as exc:  # per-row resilience, T-29-05b/Pitfall 5
    counters["conversations_errored"] = counters.get("conversations_errored", 0) + 1
    print(f"WARNING: conversation {conversation_id!r} raised {exc!r} -- errored, term continues.")
```

The transcript for that conversation is never imported, and the failure is
indistinguishable in the printed summary from a malformed/bad-join row
(`conversations_errored`). An operator running a full `--term-range
1955-2019` backfill has no way to tell "this docket's second oral argument
was silently dropped because of a docket collision" apart from re-reading
raw WARNING lines for `IntegrityError` — and no test in
`pipeline/tests/test_import_convokit_core.py` or
`test_import_convokit_utterances.py` exercises this path at all, so it went
undetected.

**Fix:** Derive `question_number` per docket instead of hard-coding `1`,
and/or handle the constraint violation explicitly so it's never silently
folded into the generic error bucket:

```python
# Before creating the Argument, find the next free question_number for this docket
existing_q_result = await session.execute(
    select(func.max(Argument.question_number)).where(
        Argument.source_docket == case_fields["docket_no"]
    )
)
next_question = (existing_q_result.scalar_one_or_none() or 0) + 1

argument = Argument(
    argued_date=argued_date,
    question_number=next_question,
    source_docket=case_fields["docket_no"],
    status=ArgumentStatusEnum.DRAFT,
    oyez_transcript_id=conversation_id,
)
session.add(argument)
try:
    await session.flush()
except IntegrityError:
    await session.rollback()
    counters["docket_question_conflict"] = counters.get("docket_question_conflict", 0) + 1
    print(
        f"WARNING: conversation {conversation_id!r} (docket "
        f"{case_fields['docket_no']!r}) collided with an existing Argument "
        "row -- not imported, flagged separately from other errors."
    )
    return
```

Add a regression test that pre-creates an `Argument` row for a docket (e.g.
seeded as if from the PDF pipeline, `question_number=1`) and then runs
`run_import_convokit` against a ConvoKit conversation for that same docket,
asserting the corpus record is either imported as `question_number=2` or
counted in a distinct, clearly-labeled counter — never silently lumped into
`conversations_errored`.

## Warnings

### WR-01: Stage-direction whole-turn regex accepts mismatched bracket/paren pairs

**File:** `pipeline/corpus/stage_directions.py:48`

**Issue:** `_WHOLE_TURN_MARKER_RE = re.compile(r"^\s*[\[\(]([^\[\]\(\)]*)[\]\)]\s*$")`
allows the opening delimiter to be `[` or `(` independently of the closing
delimiter, which can also be `]` or `)`. A turn whose text is exactly
`"(Laughter]"` or `"[Recess)"` would match and be misclassified as a stage
direction, even though the module's own docstring states the intent is "a
curated vocabulary inside EITHER brackets or parens" — implying a matched
pair, not an arbitrary open/close mix.

**Fix:**

```python
_WHOLE_TURN_MARKER_RE = re.compile(
    r"^\s*(?:\[([^\[\]]*)\]|\(([^\(\)]*)\))\s*$"
)
# then: inner = _normalize(match.group(1) or match.group(2))
```

### WR-02: Multi-term rollup silently drops `participants_created`

**File:** `pipeline/commands/import_convokit.py:682-704`

**Issue:** `_SUMMARY_COUNTER_KEYS` (used by both `_new_counters()` and
`_accumulate_counters()`) does not include `"participants_created"`, even
though `_new_counters()` separately initializes it
(`| {"participants_created": 0}`) and `_resolve_and_link_participant`
increments it on every run. Because `_accumulate_counters` only iterates
`_SUMMARY_COUNTER_KEYS`, a `--term-range` spanning multiple terms will
always report a rollup `participants_created` of `0`, regardless of how
many participants were actually created across the range. Currently
invisible because `_print_summary` never prints this key — but it's a real
aggregation bug waiting to surface the moment `participants_created` is
added to the printed summary, which is a likely future change given every
other creation counter is already surfaced there.

**Fix:** Add `"participants_created"` to `_SUMMARY_COUNTER_KEYS` (and print
it in `_print_summary` — arguably the most operationally interesting count,
since it reflects how many bench/advocate identities were touched).

### WR-03: `import_justices_csv._parse_optional_date` has no error handling, and the importer has no per-row resilience

**File:** `pipeline/commands/import_justices_csv.py:102-107, 141-236`

**Issue:** `_parse_optional_date` calls `dateutil_parser.parse(value).date()`
with no `try/except`, unlike `import_convokit.py`'s `_parse_argued_date`
(which explicitly catches `ValueError`/`OverflowError` and treats a bad date
as "no date" rather than a fatal error). `run_import_justices_csv` also has
no per-row try/except around the CSV loop — the entire import runs inside a
single `async with get_session() as session:` block, so one row with an
unparseable (non-blank) date, or any other unexpected exception, raises out
of the loop and rolls back the *entire* transaction, discarding every
upgrade/creation already staged in that run. This is inconsistent with the
per-row resilience pattern (T-29-05b) deliberately built into
`import_convokit.py` for the same class of problem (malformed input in an
operator-supplied file), and with this module's own `rows_skipped` counter,
which exists for other malformed-row cases but is never incremented for a
bad date.

**Fix:** Wrap the per-row body in `try/except`, counting/reporting a bad row
rather than aborting the whole run; wrap `_parse_optional_date`'s
`dateutil_parser.parse` call in the same `(ValueError, OverflowError)` catch
used by `_parse_argued_date`.

### WR-04: New `oyez_*` external-ID columns used as sole application-level dedup keys have no DB-level uniqueness backing

**File:** `alembic/versions/0017_add_oyez_external_ids.py:34-58`

**Issue:** `arguments.oyez_transcript_id` and `people.oyez_speaker_id` are
both used as the *sole* idempotency key for a SELECT-then-INSERT pattern
(`_import_conversation`'s existing-argument check;
`_resolve_person`'s existing-Person-by-`oyez_speaker_id` check), but neither
column has a `UNIQUE` constraint or index. Every comparable existing dedup
key in this schema (`cases.docket_number`, `cases.slug`,
`speaker_alias.normalized_label`) is backed by a DB-level `unique=True`.
Without one here: (1) there is no DB-level backstop against duplicate rows
if the CLI is ever interrupted and re-run in a way that races with itself,
or invoked twice concurrently against the same term; and (2) every dedup
`SELECT` against these columns is an unindexed full-table scan.

**Fix:** Add unique indexes on `arguments.oyez_transcript_id` and
`people.oyez_speaker_id` in a follow-up migration (both columns are
nullable, which is compatible with a unique index under Postgres's
multiple-`NULL`s semantics).

### WR-05: `pipeline/corpus/loader.py` has no error handling around JSON parsing — a single bad line aborts the whole batch

**File:** `pipeline/corpus/loader.py:40, 52, 69, 85`

**Issue:** `stream_utterances_for_conversation_ids`, `load_conversations_for_term`,
`load_speakers`, and `load_cases` all call `json.loads`/`json.load` with no
`try/except`. `import_convokit.py`'s design goes to considerable lengths to
make per-conversation and per-utterance-row failures non-fatal (`T-29-05b`,
"Pitfall 5", `counters["conversations_errored"]`,
`counters["utterance_rows_errored"]`) — but none of that resilience covers
the file-loading/streaming layer itself. A single malformed/corrupted line
anywhere in the ~900MB `utterances.jsonl` (or the smaller
`conversations.json`/`cases.jsonl`) raises an unhandled
`json.JSONDecodeError` that aborts the entire `import-convokit` invocation,
including a multi-term `--term-range` batch, with no per-row recovery —
directly at odds with the resilience goal documented throughout the rest of
the module.

**Fix:** Wrap the per-line `json.loads` calls in `loader.py` in a
`try/except json.JSONDecodeError`, skip/count the bad line, and let the
caller's existing counters (or a new `rows_errored` counter) surface it in
the per-batch summary.

### WR-06: Advocates resolved only from utterance turns (not `conversations.json`'s `advocates` dict) are silently recorded as `SideEnum.UNKNOWN` with no flag

**File:** `pipeline/commands/import_convokit.py:601-632`

**Issue:** `_import_utterances` calls `_resolve_and_link_participant(...,
side_code=None, ...)` for any speaker encountered in `turns` that wasn't
already present in `resolved_participants` (i.e., not listed in the
conversation's `advocates` dict). Because `side_code=None`,
`_ADVOCATE_SIDE_MAP.get(None, SideEnum.UNKNOWN)` always resolves to
`UNKNOWN` for non-justice speakers picked up this way — silently. Unlike the
missing/ambiguous-`type` case (which increments
`counters["speakers_flagged"]` and prints a `WARNING`), this
genuinely-unknown-side case is never counted or logged, so an operator
reviewing the D-14 per-batch summary has no way to know how many advocate
participants ended up with an indeterminate side because they weren't in
the advocates dict.

**Fix:** Increment `counters["speakers_flagged"]` (or a dedicated counter)
and print a `WARNING` when a non-justice participant is resolved with
`side_code=None`, so this gap is visible in the batch summary rather than
silent.

## Info

### IN-01: `TopNav.svelte`'s `variant` prop is declared but never used

**File:** `app/src/lib/components/TopNav.svelte:2`

**Issue:** `let { variant }: { variant: 'public' } = $props();` destructures
`variant`, but the template never references it — the markup is identical
regardless of the prop's value, and the type only permits the single
literal `'public'`. Every call site (`app/src/routes/+layout.svelte`,
`app/src/routes/admin/+layout.svelte`) passes `variant="public"`.
`AdminSubNav.svelte`'s comment ("same as TopNav admin variant") references
an admin variant that doesn't actually exist in this component — this reads
like a vestige of a planned (but never implemented) admin-variant nav.

**Fix:** Either implement the admin variant the prop/comment implies, or
drop the prop entirely and hardcode the public nav markup (matches actual
usage).

### IN-02: `ArgumentParticipant` dedup keyed on `raw_speaker_label`, not `person_id`

**File:** `pipeline/commands/import_convokit.py:489-497`

**Issue:** `_resolve_and_link_participant` checks for an existing
`ArgumentParticipant` via `(argument_id, raw_speaker_label)` rather than
`(argument_id, person_id)`. Two distinct `speaker_id`s in the same
conversation that happen to share an identical display name (e.g. two
same-named advocates) would collapse into a single shared
`ArgumentParticipant` row keyed off whichever one resolved first, silently
misattributing the second speaker's turns to the first's participant
record. Low-probability given the corpus's naming conventions, but the
analogous `Person`-level full_name dedup (D-13) is explicitly documented as
a known tradeoff while this one isn't.

**Fix:** Consider deduping on `(argument_id, person_id)` when `person_id`
is available, falling back to `raw_speaker_label` only when it isn't; at
minimum, document the assumption inline near the dedup query.

### IN-03: Unreachable `if not rows: continue` branch in `_import_utterances`

**File:** `pipeline/commands/import_convokit.py:600-602`

**Issue:** `_split_turn_into_rows` always returns at least one `(text,
bool)` tuple — even an empty-string `text` produces `[("", False)]`, since
`"".split("\n")` yields `[""]` and the `pending` list (`[""]`) is truthy
when flushed. The `if not rows: continue` guard can therefore never
trigger.

**Fix:** Remove the dead branch, or (if the intent was to skip genuinely
empty turns) change `_split_turn_into_rows` to filter out an all-empty
result and add a test asserting that behavior explicitly.

### IN-04: Stale "out-of-scope" comment in a now-passing regression test

**File:** `api/tests/test_argument_oyez_field.py:150-157`

**Issue:** The docstring for
`test_utterances_endpoint_returns_200_for_null_argued_date` still describes
the `PipelineRun.step="ingest"` vs. `step=="parse"` mismatch as "a separate,
out-of-scope" issue deferred to a later plan. Plan 29-08 has since fixed
that exact mismatch (confirmed by
`test_import_convokit_utterances.py::test_utterances_readable_via_arguments_service_after_import`),
so this comment is now stale and could mislead a future reader into
thinking the gap is still open.

**Fix:** Update the docstring to note the mismatch was resolved by 29-08
and point at the test that now covers it end-to-end.

---

_Reviewed: 2026-07-10T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
