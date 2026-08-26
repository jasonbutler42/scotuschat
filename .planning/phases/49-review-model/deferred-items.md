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

## D-35a published-write inventory (49-11) — every write path that can reach an argument, dispositioned (2026-08-24)

**Found during:** 49-11 Task 2, closing the SECOND half of D-35 — the operator's
whole-argument answer (D-35a) to the scope question 49-09's Task 3 recorded below as an
open question. Supersedes the 49-09 inventory this section used to carry: that inventory
covered only the participant-side half; this one is complete across every writer that can
reach an `Argument`, a `Case`, an `ArgumentParticipant`, a `Utterance`, or a `Person`, and
every row below carries an explicit disposition and reason.

**Locked (refuse while `status == PUBLISHED`):**

| Write path | Disposition | Reasoning |
|---|---|---|
| `admin_jobs.update_resolve_row_for_job` | **LOCKED**, pre-existing | Refuses on `ArgumentStatusEnum.PUBLISHED`, citing the folded todo `2026-08-21-widen-participant-editability-to-all-unpublished-states`. Phase 25 + the folded todo's widening. Writes participant `side`/`descriptor`. |
| `admin_arguments.update_participant_side` | **LOCKED by 49-09** | Same predicate, same folded-todo citation, same "refuse before the authority gate" ordering as the sibling above. Writes participant `side`/`descriptor`. Proved by a live test asserting non-persistence. |
| `admin_arguments.update_argument` | **LOCKED by 49-11 (D-35a)** | Writes `Argument.argued_date`, lead `Case.case_name`/`docket_number`/`docket_number_norm`/`slug`. Previously froze only the SLUG on a published argument — case name, docket, and argued date all stayed writable on live public data. Closed. |
| `admin_arguments.update_argument_metadata` | **LOCKED by 49-11 (D-35a)** | Writes `Argument.argued_date`/`source_docket`/`source_dockets`/`question_number`, lead `Case.case_name`. Had NO status check at any layer before this plan — not the service, not the router, not the SvelteKit action. Closed. |
| `admin_jobs.resolve_job` | **LOCKED by 49-11 (D-35a), defence in depth** | Writes participant and utterance `person_id`, `SpeakerAlias` rows, `Argument.resolved_at`. Not reachable through any current path — a PAUSED job never points at a publishable argument today (traced in 49-11-PLAN.md `<planner_decisions>`) — so this makes an indirect, job-lifecycle-mediated control direct and explicit rather than an emergent property of job lifecycle ordering. |
| `admin_jobs.create_person_for_job` | **LOCKED by 49-11 (D-35a), defence in depth** | Writes participant `person_id`/`side`/`review_state` (when `raw_speaker_label` is set). Same reachability trace as `resolve_job`. Guard fires only when the job resolves to an actual PUBLISHED argument — a job with no linked argument still legitimately creates a bare `Person` (out of scope, see the ambiguous row below). |

**Deliberately NOT locked — lifecycle (status transitions, not edits):**

| Write path | Disposition | Reasoning |
|---|---|---|
| `admin_arguments.publish_argument` / `unpublish_argument` | Not applicable — status transitions | These functions exist to *change* `status` itself; by definition they must remain callable on (or into) a published argument. Locking either would make a published argument permanently frozen, defeating D-35's own second sentence ("if an argument is in any other state I expect the data to be editable," which presupposes an argument can always leave the published state). Proved still working by a live assertion in 49-11. |
| `admin_jobs.approve_job` | Not locked — already narrower | Candidate → draft transition, already gated to CANDIDATE only, strictly narrower than the published lock. |
| `admin_arguments.delete_argument` | Not locked — already narrower | Already gated to DRAFT only; a published argument is already undeletable, a stronger control than this lock. |
| `admin_jobs.delete_job` | Not locked — out of reach | Deletes only the `admin_job` row and is documented as never touching the argument or its children. |

**Deliberately NOT locked — not the argument's data:**

| Write path | Disposition | Reasoning |
|---|---|---|
| `admin_review.resolve_participant_review` / `resolve_person_review` | **NOT locked, intentionally** | Both write `review_state` only — never a value column. Under D-35, review metadata is not *"the data for that argument"*: marking a published row confirmed, or re-flagging it, changes nothing a member of the public can see. Locking it would break the review queue for exactly the published rows most likely to need auditing. 49-09's classification, carried forward and proved live by 49-11. |
| `trust.recompute_argument_tier` | Not locked — derived column | Writes the derived `Argument.trust_tier` and is called by `publish_argument`/`unpublish_argument` themselves; locking it would break the lifecycle transitions this plan must keep working. |
| `admin_dev.seed_unresolved_speaker_fixture` / reset-to-fixture path | Not locked — dev-only | Behind the dev router; its entire purpose is to rewrite state for test fixtures. |

**Genuinely AMBIGUOUS — left unlocked, recorded, not guessed:**

| Write path | Disposition | Reasoning |
|---|---|---|
| `admin_people.update_person`, `merge_people`, `delete_person_if_orphan`, `update_photo_url`, `upload_photo`, `create_role` | **NOT locked, ambiguous** | `merge_people` in particular repoints `ArgumentParticipant.person_id` and `Utterance.person_id` across every argument the source person appears in, published ones included — so by a literal reading of "lock everything" it writes a published argument's data. Left unlocked because a `Person` is shared: one published argument would freeze that person for every other argument permanently, which for a sitting Justice means forever. This was NOT decided by the planner — it is the one NEW operator question below, distinct from the whole-argument-scope question D-35a just answered. |

**The one NEW question left for the operator** (distinct from D-35a, which this plan
implements, and distinct from G-49-3, which 49-10 closed): a published argument displays
`Person` data — names, titles, photos — and that data is editable from the People
directory and can be repointed wholesale by a person merge; because a `Person` is shared
across every argument they appear in, any lock there would freeze a sitting Justice's
record permanently the moment one of their arguments publishes. Should `Person`-level
edits be restricted at all, and if so on what boundary?

**Answered by D-23 (operator, 2026-08-25, Phase 50, `50-CONTEXT.md`): no Person-level
published lock.** Zero implementation follows — this is a decision record, not a code
change. Three reasons, carried verbatim in substance from `50-CONTEXT.md`:

1. A `Person` is shared across every argument they appear in, so any lock freezes a
   sitting Justice's record permanently the moment one of their arguments publishes.
2. Under D-35 a Person's name, photo, and bio is not "the data for that argument" — the
   same reasoning that already keeps `resolve_participant_review`/`resolve_person_review`
   (review-state-only writes) unlocked in the table above.
3. It keeps the road open for the deferred Person-dedup fix (White/Black/Clark/Douglas,
   carried since Phase 42), which needs merges on exactly these Justices.

**Status:** closed — 2026-08-25, D-23 (operator), cited in `50-CONTEXT.md`. D-35a itself
(the whole-argument scope question this section used to record as open) has been LOCKED
and implemented since 49-11 — see `49-CONTEXT.md`'s `### D-35a (locked)` entry.

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

## D-24 writer inventory (50-07) — `parse.py`'s TOC-mapping side/descriptor writers bypass the authority gate entirely

**Found during:** 50-07 Task 3, building `50-WRITER-INVENTORY.md` — reading every writer's
source directly (per D-24's own instruction) rather than trusting D-22's enumeration or
50-06's already-converted list, exactly the discipline that already found the two writers
50-05/50-06 fixed (`resolve.py`'s bulk `person_id` UPDATE, `import_convokit`'s
`_apply_extracted_name_provenance`).

**The defect:** `pipeline/commands/parse.py::_update_participant_sides` and
`::_update_participant_descriptors` (Phase 16 PARSE-02 / Phase 22 PJOB-13, both pre-dating
Phase 49's authority ladder) write `ArgumentParticipant.side`/`.descriptor` by direct ORM
attribute assignment (`p.side = ...`, `p.descriptor = ...`) from a TOC-derived label map,
called unconditionally on **every** parse pass — including a re-parse of an argument whose
participant rows already survived a prior pass. `ArgumentParticipant` rows persist across
re-parses (select-before-insert dedup on `raw_speaker_label`, `_run_parse_inner` Step 7b) —
so a participant an operator already moved to a different side via
`admin_arguments.update_participant_side` (gated) can be silently overwritten back to the
TOC's mapping on the next re-parse. No `apply_participant_value_change` call, no
`review_state` check, no `source`/`method` stamp — the exact overwrite-an-operator-edit
failure mode D-22's whole sweep exists to close, on the one call site the sweep never
named.

**Why not fixed here:** out of scope for plan 50-07 (a documentation-and-closeout plan;
`pipeline/commands/parse.py` is not in its `files_modified`) and out of scope for 50-06
(already shipped, closed, and summarized before this defect was found — 50-06's own
`files_modified` covered `parse.py`'s Blocks A/B/D cover-metadata writes only, never this
Phase-16-era TOC-mapping helper pair). A real fix needs a per-row `apply_participant_value_
change` conversion mirroring `resolve.py`'s own `_apply_resolved_person_ids` shape (50-06's
established pattern), a decision on `incoming_source`/`incoming_method` for a TOC-derived
correction (likely `run.source`/`run.method`, matching Block D's convention), and dedicated
tests — the same class of "new decision, not a bug fix, needs its own mandate" reasoning
the trust-tier regression item at the top of this file already used for a sibling gap in
this same file's history.

**Status:** open — not fixed by this plan. Candidate follow-up: a small plan converting
`_update_participant_sides`/`_update_participant_descriptors` to per-row gate calls,
mirroring 50-06's `resolve.py` conversion, with its own `test_gated_column_writers.py`
coverage.
