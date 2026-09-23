# D-35a Published-Write Inventory — Phase 49

Moved verbatim out of `deferred-items.md` on 2026-09-23 during the v1.8 milestone close.
This section was already `Status: closed` (D-23, operator, 2026-08-25). It is a dispositioned
decision record, not deferred work, and its four GFM tables were being parsed by the open-artifact
audit as 14 separate unresolved items that the acknowledge writer cannot suppress by design.
Content below is unchanged.

---

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
