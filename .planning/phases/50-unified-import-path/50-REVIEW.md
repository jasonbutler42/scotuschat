---
phase: 50-unified-import-path
reviewed: 2026-08-26T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - alembic/versions/0030_argument_case_provenance_and_digest.py
  - api/domain/content_digest.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_dev.py
  - api/schemas/admin_review.py
  - api/services/admin_arguments.py
  - api/services/admin_dev.py
  - api/services/admin_jobs.py
  - api/services/admin_review.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_dev_routes.py
  - api/tests/test_admin_review_service.py
  - api/tests/test_argument_authority_gate.py
  - api/tests/test_authority_matrix.py
  - api/tests/test_phase49_review_ui_contract.py
  - api/tests/test_trust_public_leak_ban.py
  - app/src/routes/admin/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/review/+page.server.ts
  - app/src/routes/admin/review/+page.svelte
  - pipeline/__main__.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/import_justices_csv.py
  - pipeline/commands/parse.py
  - pipeline/commands/prune_runs.py
  - pipeline/commands/resolve.py
  - pipeline/tests/test_content_digest.py
  - pipeline/tests/test_gated_column_writers.py
  - pipeline/tests/test_import_convokit_adminjob.py
  - pipeline/tests/test_import_convokit_reconcile.py
  - pipeline/tests/test_import_convokit_reimport_tracer.py
  - pipeline/tests/test_import_convokit_utterances.py
  - pipeline/tests/test_import_justices_csv.py
  - pipeline/tests/test_parse.py
  - pipeline/tests/test_prune_runs.py
  - pipeline/tests/test_resolve.py
findings:
  critical: 2
  warning: 4
  info: 1
  total: 7
status: issues_found
---

# Phase 50: Code Review Report

**Reviewed:** 2026-08-26
**Depth:** standard
**Files Reviewed:** 33 (of the required-reading set; some files were skimmed rather than exhaustively line-audited given volume — see notes below)
**Status:** issues_found

## Summary

Phase 50's authority-gate plumbing (`api/services/admin_review.py`'s four gate
functions, `api/domain/content_digest.py`'s frozen digest contract, and
`pipeline/commands/prune_runs.py`'s deletion-safety logic) is well-built and
internally consistent — the digest contract is correct and stable, and
`prune-runs`'s served-run re-derivation, dry-run purity, and open-discrepancy
refusal all held up under adversarial reading.

Two real defects were found in the reconcile/provenance plumbing that
undercut the phase's central promise ("an import must never clobber operator
work" / "authority-governed so it never clobbers operator work"):

1. A published argument's reconcile pass silently drops genuine
   participant `person_id`/`side`/`descriptor` disagreements instead of
   recording them (unlike the Argument/Case legs, which correctly route to
   record-only mode) — contradicting the reconcile function's own docstring
   claim about why this is safe.
2. `update_argument_metadata` — a second, live, HTTP-reachable writer of the
   same D-02-gated `argued_date`/`case_name` columns `update_argument`
   writes — never stamps operator provenance on those writes, so an
   operator's edit made through the pipeline-job metadata card is
   indistinguishable from an unedited value on the next gated write and can
   be silently overwritten.

Both are unrelated to the two already-logged deferred items (the ungated
`_update_participant_sides`/`_update_participant_descriptors` writer in
`parse.py`, and the Person-level `review_state` gap-fill granularity), which
are not re-reported here.

## Critical Issues

### CR-01: Published-argument reconcile drops participant disagreements instead of recording them

> **RESOLVED 2026-08-27** — `_reconcile_conversation` now runs a record-only
> branch for a PUBLISHED argument's paired participants, mirroring the
> Argument/Case legs: `person_id`/`side`/`descriptor` go through
> `_record_published_diff`, so a genuine disagreement is recorded as an open
> `value_discrepancy` while nothing is written. A new read-only
> `_lookup_person_readonly` replaces `_resolve_person` on that path (the
> latter creates Persons, backfills `oyez_speaker_id`, and applies name
> provenance — all writes D-08 forbids). Deliberately still skipped when
> published: the four `Person` name-part writes (genuinely gap-fill-only)
> and the new-participant-creation leg (creating a row is a write). The
> false docstring claim is corrected in place. Five tests added, including
> the over-correction guard and a no-rows-created guard; falsifiability-
> checked by restoring the blanket skip and watching three fail.

**File:** `pipeline/commands/import_convokit.py:1106-1206` (see also the docstring at 1106-1112)
**Issue:**
`_reconcile_conversation` walks the whole D-02 compare set. For `Argument`
and `Case` fields, a `PUBLISHED` argument correctly runs in **record-only**
mode via `_record_published_diff` (no write, but a genuine disagreement is
still recorded as an open `value_discrepancy` so an operator can see it).
For the participant/person leg, however, the entire block is gated on
`if not is_published:` and skipped **entirely** for a published argument —
no write, but also **no record**:

```python
if not is_published:
    paired = await _pair_participants_by_speaker_id(...)
    ...
    decision = await _reconcile_field(
        ctx,
        functools.partial(apply_participant_value_change, participant=participant),
        target=participant,
        field="person_id",
        ...
    )
```

The docstring justifies this by claiming "there is nothing here that could
ever accept-and-record even on the ordinary path
(`_apply_extracted_name_provenance` only ever gap-fills or no-ops...)". That
claim is only true for the four *name-part* writes on `Person`. It is false
for `ArgumentParticipant.person_id`/`.side`/`.descriptor`:
`apply_participant_value_change` (`api/services/admin_review.py:190-289`) is
a full authority-ladder gate that **can** return `ACCEPT_AND_RECORD` or
`REJECT_AND_RECORD` whenever the incoming and existing values genuinely
differ (not a gap-fill) — e.g. the corpus re-resolves a speaker to a
different `person_id` than the one currently stored, or a Justice/advocate
`side` genuinely disagrees.

Net effect: for a **published** (live, publicly served) argument, a real
speaker/side reassignment discovered by a corpus re-import is silently
dropped on the floor — never written (correct, per D-08), but also never
surfaced to the operator via the review queue (incorrect — this is exactly
the class of disagreement `_record_published_diff` exists to preserve for
the Argument/Case legs). No test in `pipeline/tests/test_import_convokit_reconcile.py`
exercises a published argument with a genuine participant disagreement.

**Fix:** Route the participant/person `person_id`/`side` comparisons (not
the four name-part writes, which genuinely are gap-fill-only) through a
`_record_published_diff`-style record-only branch when `is_published`,
mirroring the Argument/Case legs above them in the same function. At
minimum, correct the docstring so the false safety claim doesn't mislead the
next reader, and add a test asserting a published argument with a
person_id/side disagreement produces an open `value_discrepancy` row.

### CR-02: `update_argument_metadata` never stamps operator provenance on its `case_name` (and `argued_date`) writes

> **RESOLVED 2026-08-27** — both halves. `case_name` now calls
> `_stamp_operator_provenance(db, model=Case, ...)` after its write (this
> half was also found independently by the Phase 50 UAT walkthrough as gap
> G-50-2a, where its live effect was visible: `/admin/review` rendered an
> operator-typed value as `(corpus/direct)`). `argued_date` is no longer
> scoped out of the Argument stamp condition — CR-02 asked for either that
> or a recorded product decision to leave it out, and parity with
> `update_argument` (which does stamp on its own `argued_date` write) is the
> answer. Four tests, including a parity guard per column asserting both
> operator routes land on `AuthorityRank.OPERATOR`; falsifiability-checked.

**File:** `api/services/admin_arguments.py:1291-1413` (case_name write at ~1391-1406; argued_date write at ~1349-1350; contrast with `update_argument` at 545-676)
**Issue:**
Two live HTTP-reachable service functions write the same D-02-gated
columns:

- `update_argument` (used by `/admin/arguments/{id}`'s Case card) — for
  every `argued_date`/`case_name`/`docket_number` write, correctly calls
  `_stamp_operator_provenance(db, model=Argument|Case, row_id=...)`
  (lines 625, 673). This is the **only** mechanism by which
  `authority_rank` can ever read `source == "operator"` for `Argument`/
  `Case` (both tables have no `review_state` column — see
  `_stamp_operator_provenance`'s own docstring, `admin_arguments.py:66-85`).

- `update_argument_metadata` (used by `/admin/pipeline/{job_id}`'s
  metadata card, still live and routed at `api/routers/admin.py:1286`) also
  writes `Argument.argued_date` (`values_to_set["argued_date"] = parsed_date`)
  and `Case.case_name` (`update(Case).values(case_name=body.case_name)`,
  ~1401), but:
  - only stamps Argument provenance when `question_number` or
    `source_docket` was written (`if "question_number" in values_to_set or
    "source_docket" in values_to_set:`) — `argued_date` is explicitly
    excluded, per the function's own comment ("`argued_date` is
    deliberately NOT stamped here — this call site is scoped to exactly
    the two fields named by this task").
  - **never** stamps Case provenance for the `case_name` write at all — no
    call to `_stamp_operator_provenance(db, model=Case, ...)` exists
    anywhere in this function, and there is no comment acknowledging the
    gap the way the `argued_date` one does.

Confirmed via the test suite: `test_admin_arguments_service.py` has
dedicated tests
(`test_update_argument_metadata_stamps_operator_provenance_on_question_number_write`,
`..._on_source_docket_write`) proving the stamp fires for those two
fields, but no equivalent test exists for `case_name` or `argued_date`.

Net effect: an operator who corrects `case_name` (or `argued_date`) via the
pipeline-job metadata card leaves the `Case`/`Argument` row's
`source`/`method` exactly as they were before the edit — typically NULL
(unknown provenance, which `_existing_authority_is_unknown` still fails
closed against, so this specific sub-case is defended) **or** whatever a
prior PDF-parse/corpus write already stamped (`pdf_pipeline`/`corpus`). In
the latter case, the very next `apply_case_value_change`/
`apply_argument_value_change` call (a re-parse's `_write_cover_metadata_through_gate`,
or a corpus reconcile pass) sees the row's provenance as
equal-or-comparable-authority to its own incoming write rather than
`operator` (the ceiling), and the operator's manual correction can be
silently outranked/overwritten or, at best, is never distinguished from an
untouched value — the exact clobber Phase 50 exists to prevent.

**Fix:** Add the same `_stamp_operator_provenance(db, model=Case,
row_id=lead_ca.case_id)` call after the `case_name` write, and either
extend the Argument stamp condition to include `"argued_date" in
values_to_set` or get an explicit product decision to leave it out and
record that as a tracked deferred item (it is currently an undocumented
behavioral gap for `case_name`, and a self-acknowledged-but-unaddressed one
for `argued_date`).

## Warnings

### WR-01: Dry-run prediction double-counts `published_writes_skipped` when a published argument's content changed

**File:** `pipeline/commands/import_convokit.py:1450-1454` (compare to the real path at ~1236-1243)
**Issue:** `_predict_reconcile` (the `--dry-run` path) increments
`published_writes_skipped` unconditionally once at the top for any
published argument:

```python
if is_published:
    counters["published_writes_skipped"] = (
        counters.get("published_writes_skipped", 0) + 1
    )
```

and then increments it **again** in the branch that fires when the content
digest differs and the argument is published:

```python
elif is_published:
    counters["arguments_reconciled"] = counters.get("arguments_reconciled", 0) + 1
    counters["published_writes_skipped"] = (
        counters.get("published_writes_skipped", 0) + 1
    )
```

The real (non-dry-run) path's equivalent branch
(`_reconcile_conversation`, `import_convokit.py:1236-1243`) only prints a
warning and increments `arguments_reconciled` — it does **not**
re-increment `published_writes_skipped` a second time, since that counter
is already incremented unconditionally once per pass at the top. So for
every published argument whose utterance content changed, `--dry-run`
reports one more `published_writes_skipped` than the real run would —
misleading in exactly the scenario a dry run exists to preview accurately.

**Fix:** Remove the second `counters["published_writes_skipped"] += 1` from
the `elif is_published:` branch in `_predict_reconcile`, matching the real
path's counter shape exactly.

### WR-02: `argument_participants.oyez_speaker_id` width contradicts its own migration's stated invariant

**File:** `alembic/versions/0030_argument_case_provenance_and_digest.py:9-14, 65-68`; `api/models/models.py:155` (`Person.oyez_speaker_id`) vs `api/models/models.py:484` (`ArgumentParticipant.oyez_speaker_id`)
**Issue:** The migration's docstring states:

> `argument_participants.oyez_speaker_id` — sa.String(50), nullable. ...
> Width matches Person.oyez_speaker_id and ImportRun.external_id, which
> carry the same ConvoKit id vocabulary.

`ImportRun.external_id` is indeed `String(50)`, but `Person.oyez_speaker_id`
is declared `String(100)` (`api/models/models.py:155`), not `String(50)`.
The claim that "width matches Person.oyez_speaker_id" is false in the
actual schema. In practice this only becomes a live bug if a legitimate
ConvoKit speaker id exceeds 50 characters (the reason `Person`'s column was
presumably sized wider) — such an id would insert fine into `Person` but
raise a Postgres `StringDataRightTruncation`/length-constraint error the
moment `import_convokit.py`'s `_resolve_and_link_participant` tries to
stamp it onto a new `ArgumentParticipant` row, aborting that conversation's
import mid-transaction.

**Fix:** Either widen `argument_participants.oyez_speaker_id` to
`String(100)` to genuinely match `Person.oyez_speaker_id`, or correct the
migration comment to state the real (narrower, `ImportRun.external_id`-only)
invariant it actually satisfies.

### WR-03: `prune-runs`'s "served run" candidate selection has no floor when no completed parse run exists

**File:** `pipeline/commands/prune_runs.py:92-117`
**Issue:** `_prunable_run_ids` computes `served_run_id` via
`MAX(ImportRun.id) WHERE step='parse' AND status='completed'`, then builds
candidates as:

```python
candidate_ids = [
    run_id
    for run_id, step in all_runs
    if run_id != served_run_id and step in _PRUNABLE_STEPS
]
```

When an argument has **no** completed `step="parse"` run at all (e.g. every
parse attempt for it is stuck at `RUNNING`/`FAILED`), `served_run_id` is
`None`, and `run_id != None` is true for every real run id — so **every**
`parse`-step `ImportRun` row for that argument becomes a prune candidate,
including a still-`RUNNING` or `FAILED` one, with none of the "this is the
currently-served run" protection the rest of the module is built around.

Under the current codebase this is low-probability in practice: both
`pipeline/commands/parse.py` and `import_convokit.py` always create their
`ImportRun` row with `status=COMPLETED` on success, and a mid-run exception
rolls back the whole per-argument transaction (nothing partial is ever
committed) — so a genuinely orphaned non-completed parse run with committed
`Utterance` rows shouldn't currently arise. It is a real gap, though, and
would become live the moment `parse.py`'s dead `_fail_run` helper (see IN-01
below) is ever wired up to actually persist a `FAILED` parse run, or if any
future writer starts leaving a run in a non-`COMPLETED` terminal state.

**Fix:** Treat `served_run_id is None` as "nothing is currently served, so
require an explicit `--include-never-served` (or similar) opt-in" rather
than silently treating it as "everything is prunable," or at minimum print
a distinct warning line when this path is taken so an operator running
`--all` is not surprised by whole-history pruning on an argument that never
finished parsing.

### WR-04: `/admin/review` `confirm` action reports every failure as 502, unlike its sibling actions

**File:** `app/src/routes/admin/review/+page.server.ts:206-215` (contrast with `confirmUnattributable` at 222-230 and `reflag` at 232-241)
**Issue:** `patchReviewAction` returns `{ error }` for both network-level
failures (`catch` block) and ordinary non-OK API responses (e.g. a 422 from
a tagged `ValueError` like `"unresolved_requires_unattributable"`). The
`confirm` action always reports this as `fail(502, failure)`:

```javascript
const failure = await patchReviewAction(fetch, kind, id, 'confirm');
if (failure) return fail(502, failure);
```

while `confirmUnattributable` and `reflag` — calling the exact same helper
— use `fail(422, failure)` for the identical failure shape. A genuine
validation rejection from the `confirm` action (e.g. confirming an
unresolved participant, which the service rejects with
`unsupported_requires_unattributable`) is therefore reported to the client
as a 502 (implying a transient/server-side failure) instead of a 422
(implying a client-side/validation rejection) — inconsistent with the rest
of the page and potentially misleading to any client-side logic that
branches on status code.

**Fix:** Change `confirm`'s `fail(502, failure)` to `fail(422, failure)` to
match its siblings (reserve 502 for the `catch` network-failure path only,
consistent with how the other two actions already behave).

## Info

### IN-01: `pipeline/commands/parse.py`'s `_fail_run` is dead code

**File:** `pipeline/commands/parse.py:650-666`
**Issue:** `_fail_run` (transitions a running `ImportRun` to `FAILED` and
records `failure_reason`) is defined but has zero call sites in this file
(confirmed via `grep -n "_fail_run(" pipeline/commands/parse.py`, which
only matches its own `def`). The module's own top-of-file docstring
("Failure classification (PIPE-06): Structural ... set status=failed,
failure_reason, return early") describes exactly the behavior this function
implements, but no code path actually invokes it — a parse failure today
either rolls back its whole transaction (leaving no row) or is caught only
by the outer `run_parse` try/except, which marks the **AdminJob** FAILED
but never the parse `ImportRun` row itself.
**Fix:** Either wire `_fail_run` into the actual failure paths described by
the module docstring, or remove it if that classification is intentionally
handled elsewhere/differently now (and update the docstring to match reality).

---

_Reviewed: 2026-08-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
