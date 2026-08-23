---
status: issues_found
phase: 49-review-model
depth: standard
files_reviewed: 35
critical: 4
warning: 3
info: 1
generated: 2026-08-23T00:00:00Z
---

# Phase 49 — Code Review Report

**Depth:** standard
**Files Reviewed:** 35 (full list below)
**Status:** issues_found

## Summary

Phase 49 builds a review-state/discrepancy model (migrations 0028/0029), a pure authority
ladder (`api/domain/authority.py`), one authority-gated writer
(`apply_participant_value_change` / `apply_person_value_change` in
`api/services/admin_review.py`), a review queue API/UI, and a dev-only seeder. The pure
domain module, the migrations, the dev-only gating (`api/main.py` / `api/routers/admin_dev.py`
/ `api/services/admin_dev.py`), the public-leak boundary (schemas), and the review-queue's
D-05 inclusion predicate are all sound and match their documentation closely — I could not
break any of those.

The problems are all in the claim that **every value write to `argument_participants` /
`people` routes through the one authority gate, and every gated write closes its own
discrepancies in the same transaction**. That claim is false in two different, independently
serious ways:

1. `update_resolve_row_for_job` — one of the three writers `49-04-PLAN.md`/`49-04-SUMMARY.md`
   explicitly name as delegating through the gate — routes its writes through the gate
   correctly, but then never advances `review_state` to `OPERATOR_EDITED` and never calls
   `close_open_discrepancies`, unlike its sibling `update_participant_side`. Given that a
   first-time `side` resolution (`UNKNOWN` → a real side) is the single most common thing the
   Resolve card does, and any values-differ write where the incoming value strictly outranks
   the stored one is `ACCEPT_AND_RECORD` regardless of whether the stored value was genuinely
   disagreeing or just blank, this leaves an open, unclosed `value_discrepancy` behind on
   essentially every ordinary resolve action taken through the Resolve card, and the
   resulting review-queue row has no available action button (see CR-01 below for the full
   trace, including a test file whose teardown comment independently confirms the leak).
2. Two other write paths in `api/services/admin_jobs.py` (`resolve_job` and
   `create_person_for_job`) write `ArgumentParticipant.person_id`/`.side`/`.source`/`.method`
   directly via `update()`, never calling `apply_participant_value_change` at all — a second,
   fully ungated write path to the exact columns the D-31 gate exists to protect (CR-02).

A third, unrelated correctness bug was found in `pipeline/commands/import_justices_csv.py`:
rerunning that (explicitly rerunnable) importer silently resets `Person.review_state` back to
`UNREVIEWED` for every already-matched Justice, discarding prior operator
confirmations/edits — the sibling function in `import_convokit.py` has the identical
responsibility and gets it right (CR-03).

A frontend Svelte-5-runes bug (`CreatePersonPopover.svelte`'s `initialSide` prop) was found by
tracing `$state()` initializer semantics; it was already flagged in `49-EVIDENCE.md` as an
un-observed-in-browser walkthrough item, and this review's code trace confirms the failure
mode is real, not merely unconfirmed (WR-01).

## Critical Issues

### CR-01: `update_resolve_row_for_job` never advances `review_state` or closes its own discrepancies — the Resolve card's normal, everyday write leaves a permanently stuck, unactionable review-queue row

**File:** `api/services/admin_jobs.py:813-935` (function `update_resolve_row_for_job`)

**Issue:** Compare this function to its sibling `update_participant_side`
(`api/services/admin_arguments.py:775-813`). Both call `apply_participant_value_change` for
`side`/`descriptor` under the exact same D-31 gate. `update_participant_side` then does three
more things before its commit: sets `review_state = ReviewState.OPERATOR_EDITED`, calls
`close_open_discrepancies(db, target_type="argument_participant", target_id=participant_id)`,
and only then recomputes the tier and commits. `update_resolve_row_for_job` does **none** of
the three — it goes straight from the `apply_participant_value_change` calls to the
source/method backfill, `recompute_argument_tier`, and `db.commit()`. Grepping the full
function body confirms `close_open_discrepancies` and `ReviewState.OPERATOR_EDITED` do not
appear anywhere in it.

Why this matters concretely: `decide_write` (`api/domain/authority.py`) returns
`ACCEPT_AND_RECORD` — which records a `value_discrepancy` row — whenever the values differ
*and* the incoming authority strictly outranks the existing one, with no special case for "the
existing value was just blank/default." `ArgumentParticipant.side` is `NOT NULL` and starts at
its parse-time default (commonly `UNKNOWN`, per `update_participant_side`'s own docstring: "An
advocate's side must be resolved to Petitioner, Respondent, or Amicus" before it can be saved
via that path — implying `UNKNOWN` is the normal pre-resolve state the Resolve card exists to
clear). An operator resolving a row's side for the first time via the Resolve card — the
single most ordinary action this whole subsystem exists to support — has existing authority
`UNKNOWN` rank (unreviewed, no source) and incoming authority `OPERATOR` rank
(`incoming_source="operator"`), so `OPERATOR > UNKNOWN` and the values differ →
`ACCEPT_AND_RECORD`. A `value_discrepancy` row is created. Because this function never calls
`close_open_discrepancies`, that row stays open forever.

The consequence is visible end-to-end:
- `_argument_attention_predicate`'s leg 4 (`ArgumentParticipant.id.in_(open discrepancy
  subquery)`) now flags this argument permanently in `/admin/review`.
- The constituent row in `app/src/routes/admin/review/+page.svelte` renders with a
  `Discrepancy` badge that can never go away through the UI, because:
  - **Confirm** only renders when `constituent.person_id !== null && constituent.review_state
    === 'needs_review'` (line 506) — but `review_state` was never advanced past its default
    (`unreviewed`), so this is `false`.
  - **Confirm as unattributable** only renders when `person_id === null` (line 515) — `false`,
    the row is resolved.
  - **Re-flag** only renders when `review_state` is `operator_confirmed`/`operator_edited`
    (line 528) — `false`.
  - No action button renders at all for this row. The backend's own `resolve_participant_review`
    would in fact accept a `"confirm"` PATCH regardless of the row's current `review_state`
    (it only checks `person_id is not None`), but the frontend never offers it, so an operator
    using only the admin UI has no way to clear this discrepancy.

Independent confirmation this is a real, already-noticed leak rather than my own
misreading: `api/tests/test_authority_matrix.py::test_update_resolve_row_for_job_succeeds_on_draft_and_unpublished_but_not_published`'s
`finally:` teardown block contains this comment and explicit cleanup step:
```python
# A successful update_resolve_row_for_job call routes through
# the authority gate, which may record a value_discrepancy —
# no real FK to argument_participants.id, so clean it up
# explicitly before the participant row is deleted.
await db.execute(
    sa_delete(ValueDiscrepancy).where(
        ValueDiscrepancy.target_type == "argument_participant",
        ValueDiscrepancy.target_id == participant_id,
    )
)
```
The test author noticed the row leaks and worked around it in test teardown instead of
treating it as a product defect.

This directly contradicts D-15 ("discrepancies close in the same transaction as the value
write") and D-25/D-26 ("the row stays visible with its new review-state badge" — there is no
new review-state badge, because `review_state` never changes).

**Fix:** Add the same three steps `update_participant_side` performs, in the same order,
before the existing `recompute_argument_tier`/`commit`:
```python
await db.execute(
    update(ArgumentParticipant)
    .where(
        ArgumentParticipant.id == participant.id,
        ArgumentParticipant.argument_id == argument.id,
    )
    .values(review_state=ReviewState.OPERATOR_EDITED)
    .execution_options(synchronize_session=False)
)
await close_open_discrepancies(
    db, target_type="argument_participant", target_id=participant.id
)
```
(import `close_open_discrepancies` alongside the existing `apply_participant_value_change`
import from `api.services.admin_review`.)

---

### CR-02: `resolve_job` and `create_person_for_job` write `ArgumentParticipant.person_id`/`.side`/`.source`/`.method` directly, bypassing the D-31 authority gate entirely

**File:** `api/services/admin_jobs.py:531-546` (Step 2c of `resolve_job`) and
`api/services/admin_jobs.py:1079-1086` (`create_person_for_job`)

**Issue:** `49-04-PLAN.md`/`49-04-SUMMARY.md` state the gate's scope as "`update_participant_side`,
`update_resolve_row_for_job`, and `update_person` all route their value writes through it; no
second, ungated write path to those columns survives." That is true for those three, but two
other functions in the same file were left out and were never brought into scope:

- `resolve_job`'s Step 2c issues a raw `update(ArgumentParticipant).where(argument_id ==
  ..., raw_speaker_label == ...).values(person_id=match.person_id, source=case(...),
  method=case(...))` — no `decide_write` call, no `record_value_discrepancy`, no
  `review_state` touch at all.
- `create_person_for_job` issues a raw `update(ArgumentParticipant).where(id == ...,
  argument_id == ...).values(person_id=person.id, side=body.side)` — same absence.

Both functions are gated only by `AdminJob.status == PAUSED`, which says nothing about the
*participant's own* review state. `resolve_participant_review`'s `"confirm_unattributable"`
action is specifically designed to be usable on a participant whose job is still `PAUSED`
(that is the exact state the Phase 49-06 seeder reproduces: "argument 1788 had 11
`argument_participants` rows with `person_id IS NULL`... linked to `admin_jobs` row 1147
(status `paused`)" — `49-EVIDENCE.md` §1). Concrete collision:

1. Operator opens `/admin/review`, sees an unresolved participant on a paused job, clicks
   "Confirm as unattributable." `resolve_participant_review` sets `review_state =
   OPERATOR_CONFIRMED` (person_id stays `NULL`), and `_load_constituents`'s D-17 branch now
   floors this participant to `TrustTier.VERIFIED` instead of `UNCERTAIN` — a genuine,
   recorded operator judgment.
2. The same (still-`PAUSED`) job is later resolved with a match for that exact
   `raw_speaker_label` (a completely ordinary next step — nothing in the pipeline UI prevents
   it, since the participant's own review state is invisible to the resolve-job flow).
   `resolve_job`'s Step 2c silently overwrites `person_id` on that row. No discrepancy is
   recorded, no `review_state` change happens — it stays `OPERATOR_CONFIRMED`.
3. `_load_constituents`'s *other* branch (person_id now not-null) computes
   `derive_tier(source.value, method.value, review_state.value)`, and rule 1 of `derive_tier`
   is "`review_state` in `{operator_confirmed, operator_edited}` → `VERIFIED`" — matched
   regardless of the newly-written `source`/`method`. The argument now reads `VERIFIED` for a
   participant whose actual person assignment was never reviewed by anyone — it inherited
   `OPERATOR_CONFIRMED` from a *different* decision (confirming "no attribution possible") that
   the new write silently invalidated.

This is exactly the class of bug D-31/D-16 exist to prevent (an incoming, lower-authority
write silently overwriting an operator's own decision, with no discrepancy record at all —
worse than "reject and record," it doesn't even reject).

**Fix:** Route both write sites through `apply_participant_value_change` for the `person_id`
field (and let the existing `source`/`method` backfill continue to run only when
`participant.source is None`, unchanged), e.g. in `resolve_job`'s Step 2c:
```python
result = await db.execute(
    select(ArgumentParticipant).where(
        ArgumentParticipant.argument_id == job.argument_id,
        ArgumentParticipant.raw_speaker_label == match.raw_speaker_label,
    )
)
for participant in result.scalars().all():
    await apply_participant_value_change(
        db, participant=participant, field="person_id",
        incoming_value=match.person_id,
        incoming_source="operator", incoming_method="manual",
    )
```
and equivalently in `create_person_for_job`. At minimum, if the intended design really is that
pipeline-driven resolution is out of D-31's scope until Phase 50, that decision needs to be
recorded explicitly (it currently is not — neither `49-CONTEXT.md` D-31/D-31a nor
`49-RESEARCH.md`'s "two participant-side writers exist today" enumeration mentions
`resolve_job`/`create_person_for_job` as deliberately excluded), and the `_load_constituents`
D-17 lift needs a guard against being invalidated by a later ungated `person_id` write.

---

### CR-03: `import_justices_csv.py` silently discards operator review state on every rerun

**File:** `pipeline/commands/import_justices_csv.py:299-309`

**Issue:** In the "person already exists" branch, every other field this function touches is
guarded by a blank-only-prefill check ("never overwrite a part an operator has already
saved" — the function's own comments, applied consistently to `first_name`, `middle_name`,
`last_name`, `name_suffix`, `birthdate`, `death_date`). `review_state` is the one exception:
```python
person.provenance_metadata = extraction_metadata
person.review_state = ReviewState.UNREVIEWED
```
This runs unconditionally for every existing Person matched by `full_name`, regardless of the
row's *current* `review_state`. The function's own module docstring/comment calls this script
rerunnable ("every rerun refreshes the extraction provenance envelope"), and Justice
biographical data (birthdate/death_date/reason-left) is exactly the kind of CSV that gets
periodically corrected and re-imported. If an operator has ever confirmed or edited a Justice's
Person row through `/admin/people` or `/admin/review` (setting `review_state` to
`OPERATOR_CONFIRMED`/`OPERATOR_EDITED`), the next CSV rerun resets it to `UNREVIEWED` for
*every* Justice matched by name, not just the ones whose data actually changed — silently
re-injecting every Justice back into the People review queue (`_person_attention_predicate`
includes `UNREVIEWED`) and discarding the durable operator-review record this phase exists to
build.

Contrast with the analogous function in `pipeline/commands/import_convokit.py`
(`_apply_extracted_name_provenance`), which gets this right: it returns *before* touching
`review_state` whenever `has_any_part` is true (i.e., the person already has any saved name
data) — `review_state` is only ever set on a genuinely blank row. `import_justices_csv.py` has
no equivalent guard.

**Fix:** Only set `review_state` when the row does not already carry an operator-authored
state, mirroring the existing name-part guards:
```python
if person.review_state not in (ReviewState.OPERATOR_CONFIRMED, ReviewState.OPERATOR_EDITED):
    person.review_state = ReviewState.UNREVIEWED
```
(or, more conservatively, only set it on rows that had no `review_state` history at all —
i.e., skip the write whenever any of the name-part prefills above were also skipped because
data already existed).

---

### CR-04: `_load_constituents`'s D-17 floor-lift and CR-02's bypass compound into an unreviewed value reading as `VERIFIED`

**File:** `api/services/trust.py:132-146` in combination with CR-02 above

**Issue:** This is the mechanism, not a separate defect: `derive_tier`'s rule 1
(`review_state in {operator_confirmed, operator_edited} -> VERIFIED`) is evaluated first,
before source/method, by design (D-22: operator authority is carried entirely by
`review_state`, never by re-stamping `source`/`method`). That design is correct *as long as*
every write that changes what `review_state` is attesting to also updates `review_state`
itself. CR-02 breaks that precondition: `resolve_job`/`create_person_for_job` can change
*what a row's `person_id` actually is* while leaving a stale `OPERATOR_CONFIRMED`/
`OPERATOR_EDITED` `review_state` in place from a prior, unrelated decision, so `derive_tier`
reports `VERIFIED` for a value nobody has actually reviewed. Recorded here because it is the
concrete, observable damage from CR-02 (a wrong publish-gate-relevant trust tier), not just an
abstract authority-model gap. Fixing CR-02 by routing `person_id` through
`apply_participant_value_change` does not, by itself, close this — `apply_participant_value_change`
never resets `review_state` either (that's D-22's whole point for genuine operator edits), so
the real fix also needs `resolve_job`/`create_person_for_job` to reset `review_state` to
`NEEDS_REVIEW` (or `UNREVIEWED`) when a pipeline-driven write changes `person_id` on a row that
was previously `OPERATOR_CONFIRMED`/`OPERATOR_EDITED` under a *different* person_id state, so
the row re-enters review rather than silently inheriting a decision that no longer applies to
its new value.

**Fix:** Same fix as CR-02, plus: when `apply_participant_value_change`'s `field == "person_id"`
and the write is `ACCEPT`/`ACCEPT_AND_RECORD` on a row whose stored `review_state` was already
`OPERATOR_CONFIRMED`/`OPERATOR_EDITED`, downgrade `review_state` to `NEEDS_REVIEW` in the same
call (this is a case `apply_participant_value_change` doesn't currently need to handle for
`side`/`descriptor`, since those never change what "resolved" means for D-17's purposes).

## Warnings

### WR-01: `CreatePersonPopover.svelte`'s `initialSide` only captures the prop's value at first mount — toggling the row's Bench/Advocate bucket after that point does not update the pre-selected radio until an unrelated close/reopen cycle happens to run after the toggle

**File:** `app/src/lib/components/CreatePersonPopover.svelte:32,48,59` and its caller
`app/src/lib/components/ResolveCard.svelte:1209-1213`

**Issue:** `let side = $state<'BENCH' | 'ADVOCATE'>(initialSide);` (line 48) only reads
`initialSide` once, at the moment this component instance is created — Svelte 5's `$state()`
initializer is not reactive to later prop changes. `ResolveCard.svelte` passes
`initialSide={side === 'BENCH' ? 'BENCH' : 'ADVOCATE'}` (its own per-row `side` state) to an
always-rendered (not conditionally mounted/destroyed) `<CreatePersonPopover>` instance. The
only place the internal `side` state is ever reassigned to `initialSide` again is
`resetForm()`, called from `onOpenChange` **only when the popover transitions to closed**
(`if (!next) resetForm();`) — never on open, and never merely because the prop changed.

Concretely: row starts as Advocate → popover instance mounts, internal `side` = `'ADVOCATE'`.
Operator toggles the row to Bench (never having opened the popover yet, or having already
closed it once before the toggle) → `ResolveCard`'s own `side` becomes `'BENCH'`, the trigger
label becomes "Create new bench person," but the popover's internal `side` state is untouched
(still `'ADVOCATE'`). Operator clicks "Create new bench person" → the radio group renders with
`side === 'BENCH'` false, `side === 'ADVOCATE'` true — Advocate is pre-selected, not Bench,
contradicting the trigger label and the row's own toggle state.

This is exactly the walkthrough `49-EVIDENCE.md` §9 item 2 lists as never observed in a
browser ("toggle a row to Bench, open 'Create new bench person,' confirm Bench pre-selected").
This review's code trace shows the mechanism is broken independent of any browser
verification. The radio buttons remain visible and independently clickable before submit, so
an attentive operator can still correct it — this is a UI-correctness bug, not a silent data
write — but an inattentive operator trusting the trigger label's implication could create a
Justice/advocate `Person` row with the wrong `is_justice` value.

**Fix:** Either derive the radio state instead of state-initializing it (`$derived` only works
one-way for display, not for a user-mutable control, so the simplest correct fix is to reset on
**open**, not just on close):
```ts
<Popover.Root bind:open onOpenChange={(next) => {
  if (next) side = initialSide;
  else resetForm();
}}>
```
so the pre-selection is always re-synced to the row's *current* side at the moment the popover
is actually shown.

---

### WR-02: Filling a previously-blank field for the first time always records a `value_discrepancy`, even though nothing actually disagreed

**File:** `api/services/admin_review.py:78-96` (`_values_differ`) and `api/domain/authority.py:66-70`
(`WriteDecision.ACCEPT` docstring)

**Issue:** `api/domain/authority.py`'s `WriteDecision.ACCEPT` docstring says "the values agree
after normalization (**or the stored side is empty/blank**)" — but `decide_write`'s actual code
has no such special case, and neither does `_values_differ`. Populating a blank field (e.g. a
participant's `descriptor`, previously `NULL`) with a real value for the first time always
computes `values_differ=True` (since `None != "some text"`), and because the incoming write is
almost always higher-authority than a never-reviewed row, this resolves to `ACCEPT_AND_RECORD`
— a `value_discrepancy` row gets created with `existing_value=None`, even though there was no
actual competing value to disagree with. This is confirmed live in `49-EVIDENCE.md` §5b's own
walkthrough: `STEP 1 update_participant_side result: ... 'descriptor_write_decision':
'accept_and_record'` for a descriptor that was `None` immediately beforehand.

This is harmless wherever the caller immediately calls `close_open_discrepancies` in the same
transaction (`update_participant_side`, `update_person`, and the three `resolve_*_review`
actions all do), since the spurious row is opened and closed within the same commit and never
surfaces to an operator — but it permanently pollutes the `value_discrepancy` audit table with
rows that look like a genuine authority conflict (`existing_source`/`existing_method` both
`None`, `existing_value` `None`) but are actually just "first time this field was ever set."
Anyone auditing `value_discrepancy` history later (or building tooling against it, e.g. for
Phase 50's corpus-reimport work) will need to know to distinguish these from real conflicts,
and nothing in the schema or the row itself records that distinction.

It also compounds directly with CR-01: because `update_resolve_row_for_job` is missing the
`close_open_discrepancies` call, this is the specific mechanism by which its rows leak (any
value-agreement write would be silent `ACCEPT`, so the leak specifically requires a
first-time/blank-to-value fill or a genuine conflict — both are common on first resolve).

**Fix:** Either special-case a `None`/blank existing value as always `ACCEPT` (matching the
`authority.py` docstring's stated intent) inside `_values_differ`, or, if recording first-fill
provenance is intentional, add a way to distinguish a first-fill `value_discrepancy` row from
a genuine conflict (e.g. a boolean column, or simply never calling `record_value_discrepancy`
when `existing_value is None`).

---

### WR-03: Broad `except DBAPIError: pass` in the orphan-discrepancy sweep could mask unrelated fixture-teardown failures

**File:** `api/tests/conftest.py:126-149` (`_sweep_orphaned_value_discrepancies`)

**Issue:** The fixture's hard safety guard (checking `TEST_DATABASE_URL`'s resolved database
name is exactly `scotus_test`) is sound and correctly placed for a fixture that is only
meaningful when `api/tests` is already part of collection (it does not need to be in the
root-level `conftest.py` per the project's invocation-shape-independence rule, since it has no
effect at all unless `api/tests` tests actually ran). The concern is narrower: the `try/except
DBAPIError: pass` around the entire sweep body (select, per-row existence check, delete,
commit) will silently swallow any `DBAPIError` from any of those steps, not just the documented
"schema downgraded mid-test" case. A future test that leaves the connection/session in a bad
state for an unrelated reason would have its symptom masked here instead of surfacing.

**Fix:** Narrow the catch to the specific condition being guarded against (e.g. catch
`ProgrammingError`/check the exception message for the missing-table case), or at minimum log
the swallowed exception so a genuine future regression is not silently absorbed.

## Info

### IN-01: Five-column dashboard StatCard grid width was never visually verified

**File:** `app/src/routes/admin/+page.svelte:250-262`

**Issue:** `grid-template-columns: repeat(5, 1fr)` replacing the previous 4-column literal is a
plausible, mechanically correct change, but `49-EVIDENCE.md` §9 item 4 already lists "all five
dashboard StatCards sitting evenly in one row" and "no horizontal scroll at 375px" as
unobserved-in-browser. Not re-flagging as a new finding — already tracked — noting only that
this review's static read cannot confirm or refute the visual outcome either.

---

## Files Reviewed

```
alembic/versions/0028_review_state_and_discrepancy.py
alembic/versions/0029_person_review_state_fold.py
api/domain/authority.py
api/services/admin_review.py
api/services/admin_dev.py
api/services/admin_people.py
api/services/admin_arguments.py
api/services/admin_jobs.py
api/services/trust.py
api/schemas/admin_review.py
api/schemas/admin_people.py
api/schemas/admin_dev.py
api/routers/admin_review.py
api/routers/admin_dev.py
api/models/models.py
api/main.py
api/tests/conftest.py
app/src/routes/admin/review/+page.server.ts
app/src/routes/admin/review/+page.svelte
app/src/routes/admin/people/+page.server.ts
app/src/routes/admin/people/[id]/+page.server.ts
app/src/routes/admin/people/[id]/+page.svelte
app/src/routes/admin/people/new/+page.server.ts
app/src/routes/admin/arguments/+page.svelte
app/src/routes/admin/arguments/[id]/+page.svelte
app/src/routes/admin/pipeline/[job_id]/+page.server.ts
app/src/routes/admin/pipeline/[job_id]/+page.svelte
app/src/routes/admin/help/+page.svelte
app/src/routes/admin/+page.server.ts
app/src/routes/admin/+page.svelte
app/src/lib/components/CreatePersonPopover.svelte
app/src/lib/components/ResolveCard.svelte
app/src/lib/components/AdminSubNav.svelte
pipeline/commands/import_convokit.py
pipeline/commands/import_justices_csv.py
scripts/diff_corpus_fixture.py
```

_Reviewed: 2026-08-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
