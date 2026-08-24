# Deferred Items — Phase 49 (out of scope for 49-02)

## `api/tests/test_admin_jobs_service.py` — two trust-tier regression tests broken by plan 49-01's D-18 change, intersecting a deliberately-deferred PDF-pipeline wiring gap

**Found during:** 49-02 Task 3, running the full `api/tests -q` suite for the first time
since plan 49-01 landed.

**Failing tests:**
- `test_resolve_job_recomputes_tier_when_last_speaker_resolves`
- `test_repeated_writer_call_leaves_tier_unchanged`

Both assert `argument.trust_tier is TrustTier.TRUSTED` after `resolve_job` /
`update_resolve_row_for_job` (both in `api/services/admin_jobs.py`) resolve or edit an
`ArgumentParticipant` row; both now observe `TrustTier.UNCERTAIN` instead.

**Root cause:** Plan 49-01 (D-18) changed `api/services/trust.py::_load_constituents` to
feed `derive_tier` a real `(source, method, review_state)` triple for every
*resolved* `ArgumentParticipant` row, instead of contributing nothing. Neither
`resolve_job` nor `update_resolve_row_for_job` ever writes `ArgumentParticipant.source`/
`.method` — only `person_id` (and, for the latter, `side`/`descriptor`) — so a participant
resolved through either path now has `source=NULL, method=NULL`, and
`derive_tier("", "", "unreviewed")` floors to `UNCERTAIN`. This was silently latent because
49-01 never ran `api/tests/test_admin_jobs_service.py` in its own verification.

**Why not fixed here:** 49-CONTEXT.md D-20 locks the exact `source`/`method` mapping for
every participant-resolution mechanism that exists TODAY — corpus auto-match (`corpus`/
`direct`), PDF alias-table HIT (`pdf_pipeline`/`normalized`, explicitly **not yet wired**,
per the same document's "Out of scope" list: "Wiring the PDF alias-HIT participant method;
the mapping is recorded, not built (D-20), consistent with the corpus-first scope
decision"), and operator popover assignment (`admin.py:1423`, unchanged by design, D-22).
Neither `resolve_job` nor `update_resolve_row_for_job` appears in that table at all — there
is no locked decision for what provenance an admin-driven resolve-job/Resolve-card action
should stamp. Inventing one here would be a new architectural decision (Rule 4), not a bug
fix, and would risk conflicting with whatever Phase 50's corpus-first PDF-pipeline wiring
plan eventually decides for this exact code path. Neither file
(`api/services/admin_jobs.py`, `api/tests/test_admin_jobs_service.py`) is in plan 49-02's
`files_modified` list, and the fix genuinely requires a decision this plan has no mandate to
make.

**Contrast with the fix this plan DID make:** `pipeline/commands/import_convokit.py`'s
`ArgumentParticipant` creation had the exact same NULL-source/method gap and was fixed in
this plan (see 49-02-SUMMARY.md) — that fix was in-scope because it implements an
ALREADY-LOCKED D-20 mapping row (corpus resolution -> `corpus`/`direct` -> TRUSTED) in a file
already in this plan's `files_modified` list, not a new decision.

**Status:** open — out of scope for 49-02. Candidate follow-up: either fold into whatever
plan wires the PDF-pipeline participant provenance (D-20's deferred row), or raise as its
own small decision — "what source/method (if any) should an admin-driven resolve_job/
Resolve-card resolution stamp on `ArgumentParticipant`?" — via `/gsd-review-backlog` or a
phase-49 cleanup plan.

## D-35 published-write inventory (49-09) — every write path that can still mutate a published argument

**Found during:** 49-09 Task 3, closing the FIRST half of D-35 (*"If an argument is
currently published, the data for that argument is locked. If an argument is in any
other state, I expect the data to be editable and have almost the exact interface."*).

49-09 locked exactly one path: `api/services/admin_arguments.py::update_participant_side`.
`api/services/admin_jobs.py::update_resolve_row_for_job` was already locked before this
plan. Every other write path that can reach an `Argument`, a `Case`, an `ArgumentParticipant`,
or a `Person` from admin is inventoried below with an explicit disposition.

| Write path | Disposition | Reasoning |
|---|---|---|
| `admin_jobs.update_resolve_row_for_job` | **LOCKED**, pre-existing | Refuses on `ArgumentStatusEnum.PUBLISHED`, citing the folded todo `2026-08-21-widen-participant-editability-to-all-unpublished-states`. This is the writer 49-09's new guard was built to mirror. |
| `admin_arguments.update_participant_side` | **LOCKED by this plan (49-09)** | Same predicate (`== PUBLISHED`), same folded-todo citation, same "refuse before the authority gate" ordering as the sibling above. Proved by a live test asserting non-persistence, not merely an exception. |
| `admin_review.resolve_participant_review` / `resolve_person_review` | **NOT locked, intentionally** | Both write `review_state` only — never a value column (`side`, `descriptor`, `full_name`, etc.). Under D-35, review metadata is not *"the data for that argument"*: marking a published row confirmed, or re-flagging it, changes nothing a member of the public can see. Locking it would also break the review queue for exactly the published rows most likely to need auditing. Recorded here so a future reader does not file this as a miss. |
| `admin_arguments.update_argument` / `admin_arguments.update_argument_metadata` | **NOT locked, OUT OF SCOPE for Phase 49 — this is where the NEW question lives** | Both write value columns (`argued_date`, `source_docket`/`source_dockets`, `question_number`, and the lead `Case.case_name` via `update_argument`) on a published argument with **no status check at any layer**. `update_argument` freezes only the SLUG on published/unpublished, which shows the published state was *considered* for this function and only partially acted on — it is not an oversight of omission, it is a decision that was never finished. The argument-detail page's own comment above `ArgumentDetailsCard` (`app/src/routes/admin/arguments/[id]/+page.svelte`) reads: *"readonly is always false here: this page's argument details remain editable regardless of publish status."* That is a prior explicit decision. 49-09 does not reverse it — reversing a recorded decision without the operator's say-so is a worse failure than leaving a known gap visible. |
| `admin_arguments.publish_argument` / `admin_arguments.unpublish_argument` | Not applicable — status transitions | These functions exist to *change* `status` itself; by definition they must remain callable on (or into) a published argument. Not part of "the data," they are the state machine that governs it. |
| `admin_people.update_person` | **NOT locked, out of scope** | A `Person` is shared across every argument they appear in (potentially many), so a `Person` row is never *"the data for **that** argument"* — it has no single owning argument to lock against. Out of scope for D-35 as scoped to arguments. |

**The one NEW question left for the operator** (distinct from G-49-3, which 49-10 closes):
does D-35's *"the data for that argument is locked"* extend to the Case card and the
Argument Details card on the same `/admin/arguments/{id}` page — which would reverse the
page's own `readonly is always false here` comment and lock `argued_date`, `case_name`,
`source_docket`/`source_dockets`, and `question_number` on a published argument — or is
D-35 scoped to participant data only (the half this plan closed)?

This plan deliberately leaves the page half-locked rather than guess at the answer. The
half-locked state is visible and therefore self-reporting: the Speakers card now visibly
locks on publish while the Case/Argument-Details cards do not, so anyone looking at a
published argument's admin page sees the asymmetry rather than a silently-inconsistent rule.
The answer, whichever way it goes, is one small follow-up plan.

**Status:** open — awaiting the operator's answer to the NEW question above.

## D-35 convergence (49-10) — the public chat page's independently derived bench flag is NOT reconciled, and this plan makes it MORE reachable

**Found during:** 49-10 Task 3, closing G-49-3 by converging the Speakers card onto the
Resolve card's full side vocabulary (D-35, "Converge both surfaces").

Admin derives `is_bench` from `side == SideEnum.BENCH`. The public chat page derives its own,
independent bench signal from `tenure.length > 0`
(`app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:36`), and
`api/services/speakers.py` falls through to `ADVOCATE_LABEL_MAP` when the bench branch is
skipped — so a `BENCH` participant with no covering `CourtTenure` reads **Bench** in admin
and **Counsel** in public. This is the open todo
`2026-08-12-speakers-bench-classification-silent-fallback.md`; its reconcile-the-two-signals
suggestion is the eventual fix.

**This plan makes the divergence MORE reachable, stated plainly rather than buried.** Before
49-10, this state required a data accident (a corpus-resolved bench participant landing
without a covering tenure row). After 49-10, an operator can produce it **on purpose** by
moving any participant to Bench from the Speakers card. That is a real, direct consequence of
D-35 and is recorded here as such — not softened.

**Partial mitigation, not a fix:** 49-09's published lock means this divergence cannot be
*introduced* on an already-published argument — a reclassification is only reachable on
draft/unpublished/candidate data. It CAN still reach the public site: the argument must be
published (or re-published) afterward, and the publish trust gate does not currently check
tenure coverage as a precondition. Reconciling the two signals touches the public read path
(`api/services/speakers.py`, `app/src/routes/cases/[slug]/...`), which is outside Phase 49's
boundary (admin-only).

**Status:** open — accepted with this consequence stated, tracked by
`2026-08-12-speakers-bench-classification-silent-fallback.md`.

## D-35 convergence (49-10) — person-to-participant assignment remains uneditable on the Speakers card

**Found during:** 49-10 Task 3.

The Speakers card converges the SIDE control (bench vs. every advocate role) but does not add
a person picker — its Name column stays plain text (`speaker.full_name ?? '—'`), unchanged
from before this plan. Reassigning WHICH person a participant row refers to (as opposed to
reclassifying that row's side) remains possible only via the Resolve card's person combobox.
This is a genuinely separate gap from G-49-3 — the operator has not raised it, and D-35's
"almost the exact interface" language was read (see 49-10-PLAN.md `<planner_decisions>`) as
covering the side/role vocabulary the operator explicitly complained about, not the person-
assignment mechanism, which is a materially different control (a searchable combobox against
a candidate pool) that this plan's `files_modified` list and time budget do not cover.

**Status:** open — not raised by the operator; current remedy is the Resolve card. Candidate
follow-up if the operator wants person reassignment from the argument-detail page directly.
