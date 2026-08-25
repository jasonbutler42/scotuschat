# Phase 50: Unified Import Path - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

The corpus import path stops being a guest in a house built for the PDF pipeline. Three
things become true:

1. **Corpus import owns its own lifecycle.** It writes `import_run` directly (already true
   since Phase 47) and stops fabricating an `AdminJob` to borrow the PDF path's
   resolve/approve/publish machinery. A new argument-scoped approve replaces the job-scoped
   one for corpus arguments.
2. **Re-import reconciles instead of skipping.** Today `_import_conversation` returns early
   on an `oyez_transcript_id` match and compares nothing. It becomes a real
   compare-and-record pass whose writes are governed by the Phase 49 authority ladder, and
   which is idempotent by construction.
3. **The authority ladder gains its remaining callers.** `decide_write` exists with all four
   rungs but has exactly one caller today. Every pipeline writer that touches a gated value
   column delegates to it.

**Scope is corpus-only.** IMPORT-02 (the PDF path adopting `import_run` as a peer strategy)
split out to Phase 999.11 on 2026-08-25. Requirements in scope: IMPORT-01, IMPORT-03,
IMPORT-04, IMPORT-05.

**Not this phase:** any new admin screen, server-side paging on the review queue, PDF-route
feature work, argument-scoped resolve or create-person parity, Phase 51's design system.

</domain>

<decisions>
## Implementation Decisions

### Reconcile scope & trigger

- **D-01:** A repeat corpus import **always reconciles** — there is no `--reconcile` flag and
  no skip-existing default. Every repeat pass walks the compare set through `decide_write`.
  Rationale: SC-3 says "re-running *any* import is idempotent"; a guarantee that only holds
  on a flagged path is not that guarantee. Accepted cost: a full-term re-run stops being a
  near-zero-work no-op.
- **D-02:** The compare set is: `Argument.argued_date` / `question_number` / `source_docket`;
  lead `Case.case_name` / `docket_number`; `ArgumentParticipant.person_id` / `side` /
  `descriptor`; and `Person` name-parts (`_NAME_PART_FIELDS`). Derived values (`slug`,
  `term_year`, `CaseArgument.is_lead`) and `Person.is_justice` are **out** of the compare set.
- **D-03:** An **empty incoming value against a populated stored value means "no opinion"** —
  skip the field, write nothing, record nothing. A missing corpus field is an absence of
  information, not a claim that the value is empty. ConvoKit genuinely ships gaps
  (`_parse_argued_date` can return nothing, advocate side codes can be absent), so the
  alternative floods the review queue with items whose only resolution is "still fine" — and
  D-24 of Phase 49 rejected bulk confirm, so each would be an individual click.
- **D-04:** Participant pairing on re-import uses a **new explicit `oyez_speaker_id` column on
  `ArgumentParticipant`**, not the existing `(argument_id, raw_speaker_label)` dedup key and
  not a Person lookup. Rationale: pairing via Person breaks exactly when the operator has
  reassigned the participant — the highest-value case in the phase — and a display string is
  inferred lineage, which is what this milestone exists to end.
  — **Reversibility:** costly — needs an Alembic column add plus every pairing call site;
  reverting means re-deriving the pairing from `raw_speaker_label` across the importer and
  any reconcile query.
- **D-05:** A stored participant the corpus **no longer mentions is left in place with nothing
  recorded**. Consistent with D-03: corpus silence is not a claim. Deleting would also orphan
  its utterances' person links, and a deletion path inside an import writer is how a
  re-import becomes a data-loss event if the pairing key ever misfires.
- **D-06:** A reconciling pass mints an `ImportRun` **lazily and with `step="reconcile"`** —
  only when it actually writes a value or records a discrepancy. Two forces pin this: a true
  no-op must add zero rows for D-09's byte-identical proof to be possible, and
  `value_discrepancy`'s natural key requires an `import_run_id` to attribute a record to.
  `step="reconcile"` keeps it structurally invisible to the utterance read path (see Hard
  Constraints).
- **D-07:** On an **accepted** overwrite (`ACCEPT_AND_RECORD`), the row's `source`/`method` are
  **restamped to `corpus`/`direct`** and its `review_state` is **left untouched**. The
  provenance columns must describe where the value came *from*, not where it originally came
  from, or the archaeology returns. `review_state` is not flipped because the recorded
  discrepancy already pulls the argument into `/admin/review` through the attention predicate
  49-06 added — flipping it would surface one fact by two mechanisms that can then disagree.
  Note this branch is only reachable on rows whose `review_state` is `unreviewed` or
  `needs_review`; an operator-confirmed/edited row outranks corpus and gets
  `REJECT_AND_RECORD`.
- **D-08:** On a **PUBLISHED** argument the pass **compares and records but never writes**.
  D-35a freezes a published argument's data, and the reconcile writer is a seventh path to
  the same data that `decide_write` alone has no notion of publication to stop. The
  disagreement is still recorded so it is visible; the workflow is unpublish → reconcile →
  republish, with the operator deciding. A CLI batch must never change live public content
  unattended.
- **D-09:** SC-3 is closed by a **live double-import byte-identical diff plus an
  operator-edit-survival walkthrough**, backed by automated tests but not closed by them.
  Import a fixture, snapshot every affected row, re-import the identical input, diff — must
  be identical. Then edit a value as the operator, re-import, and prove the edit survived and
  a discrepancy was recorded. Same vehicle Phase 47 used for provenance; Phase 48's three
  real defects were all found live and none by the 1209-test suite.

### Utterances on re-import

- **D-10:** If **any** utterance differs, the argument's **full utterance set is rewritten as a
  new `step="parse"` / `COMPLETED` `ImportRun`**. The `MAX(ImportRun.id)` read path then flips
  atomically and prior rows survive — exactly what Architecture Rule 3 and that read path
  were built for. Identical input produces no diff, so no new run, so D-09's proof holds.
  In-place per-utterance update was rejected: the read path cannot express "half these rows
  came from a later pass."
- **D-11:** The new run's utterance `person_id` values come **from the paired post-reconcile
  `ArgumentParticipant`**, never from the raw corpus speaker mapping. The participant row is
  where operator resolve work lives and is authority-protected, so operator corrections
  survive a re-import for free. Sourcing from the corpus directly would silently discard
  every operator reassignment — a direct IMPORT-04 violation.
- **D-12:** Superseded utterance rows are **retained**, with an offline **`pipeline prune-runs`**
  CLI so the operator can reclaim space deliberately. Mirrors `pipeline recompute-trust`'s
  shape from Phase 48. Deletion is never a side effect of an import.
- **D-13:** Change detection uses a **content digest stamped on the `ImportRun`** over the
  ordered utterance tuples; a re-import hashes the incoming set and skips row-level
  comparison when they match. Turns a no-op pass into one comparison per argument rather
  than hundreds. The digest definition must stay frozen once shipped — changing it reads as
  a universal diff. A count/boundary pre-check was rejected: a same-length text correction
  passes every such check.
  — **Reversibility:** costly — an Alembic column add plus a frozen hash contract; changing
  the digest definition later forces a full-corpus false-positive pass.

### AdminJob retirement for corpus

- **D-14:** A new **argument-scoped approve** sets `status = DRAFT` and `resolved_at = now()`,
  gated on the same completeness conditions `approve_job` enforces, surfaced where the
  operator already works (`/admin/review` and/or the argument editor). `approve_job` stays as
  the PDF path's job-scoped wrapper. **This is load-bearing:** `approve_job` is currently the
  only path that sets `resolved_at`, and `publish_argument` refuses on `resolved_at IS NULL`
  as a non-overridable gate — so without this, a jobless corpus argument could never be
  published at all.
- **D-15:** **No data migrations for legacy rows.** Operator, verbatim: *"we still have a lot of
  parsing and design work so the ability to reseed over and over is not going away. The
  current database is all throwaway entries so I don't care about migrating anything at this
  point."* Existing corpus `AdminJob` rows are not deleted or rewritten — the importer simply
  stops minting them and a reseed produces the clean state. Alembic DDL for new columns is
  still required (Alembic remains sole DDL authority); what is out is backfill-and-cleanup
  work on disposable data.
- **D-16:** The new `ArgumentParticipant.oyez_speaker_id` column gets **no backfill** — nullable
  column, populated by the importer on every row it writes, and a reseed makes that every row
  that matters. Follows directly from D-15.
- **D-17:** **No `admin_job` ↔ `import_run` FK in this phase.** The "inventing one" SC-2 objects
  to is the corpus path minting a fake job; removing that satisfies the criterion. The
  remaining linkage is PDF-only, one job spawns three runs (ingest/parse/resolve) so a single
  FK is the wrong cardinality, and `get_run_id_for_step` already derives it from
  `(argument_id, step)` with an explicit docstring rationale. **This is a deliberate deviation
  from `import-entity-sketch.md`'s `ADMIN_JOB { int import_run_id FK }`** — the sketch item is
  inherited by Phase 999.11, not implemented here.
- **D-18:** Phase 49's deferred **`admin_jobs.discrepancies`** item closes as a **no-op**. The
  corpus write at `import_convokit.py:~640` disappears with the job, leaving the blob
  PDF-only by construction. Nothing to migrate, rename, or retire.
- **D-19:** **No new visibility screen.** `/admin/pipeline` becomes honestly PDF-only; corpus
  arguments are reached through `/admin/arguments` and `/admin/review`, which Phase 49 built
  for exactly this sweep, and the batch reports through its own stdout. A runs-based list or
  a dedicated Imports view is unscoped by all four success criteria and would front-run
  Phase 51.
- **D-20:** **No argument-scoped `resolve` / `create_person` parity.** Evidence: the corpus
  path's only unresolved participants are ConvoKit's unattributable sentinels (`type == "U"`),
  which the importer never mints a Person for by design, and `/admin/review` already ships
  confirm-as-unattributable for exactly those. Every identifiable corpus speaker gets a
  Person at import (the D-12 ambiguous-type case included). So the argument-scoped approve is
  the only new action needed.

### Authority gate: every writer

- **D-21:** The import writers **call the existing gated writer in
  `api/services/admin_review.py` directly** — no extraction, no relocation, no pipeline-side
  adapter. Verified importable: that module pulls only SQLAlchemy + `api.domain` +
  `api.models`, no FastAPI, and four pipeline commands already import
  `api.services.trust.recompute_argument_tier`. Keeps D-31a's "one gated writer" literally
  one implementation; an adapter over a gate is where a second, subtly different gate grows.
- **D-22:** **Every pipeline writer of a gated value column delegates:** `import_convokit`,
  `import_justices` (`source=seed`), `parse.py`, and `resolve.py`. The three API writers
  already do. Corpus is proven by D-09's live double-import; the two PDF legs are proven by
  real-writer tests with the LLM monkeypatched — the same verification split Phase 47
  established and the split the ROADMAP's own Phase 50 scope note already describes.
- **D-23:** **No Person-level published lock.** This closes the single open operator question
  Phase 49 recorded in `deferred-items.md` and deliberately did not guess. A `Person` is
  shared across every argument they appear in, so any lock freezes a sitting Justice's record
  permanently the moment one argument publishes; under D-35 a Person's name/photo/bio is not
  "the data for that argument"; and it keeps the road open for the deferred Person-dedup fix
  (White/Black/Clark/Douglas), which needs merges on exactly those Justices. Zero
  implementation. **Per the Phase 40.1 lesson in PROJECT.md Key Decisions, flip
  `deferred-items.md`'s `Status: open` in the same commit that records this** — do not leave a
  closed question reading as open.
- **D-24:** SC-4 is closed by an **executable behavioral gate plus a dispositioned inventory**.
  The gate must exercise real writes and fail when a gated column changes without a decision
  being recorded — **not a grep over source text.** This project has twice shipped green
  source-text gates that could not see a live defect (49-12's fourth horizontal-scroll cause
  past three passing gates; the `$state` proxy case with 28 green tests over a fully broken
  button). The inventory takes the shape of 49-11's dispositioned table: every writer that can
  reach a gated column, with an explicit disposition and reason.

### Delete gate and cascade

- **D-25:** An argument is **deletable in every state except `published`**. Delete is the
  strongest edit there is, so this is D-35a's doctrine applied consistently — gated only by
  published, nothing else — and it is the most useful shape under a reseed-heavy workflow.
  Closes Phase 48's D-05 item, which pointed at this phase.
- **D-26:** **MUST-FIX defect found during this discussion.** `delete_argument`'s FK-ordered
  cascade deletes the argument's `ImportRun` rows (step 2) but never touches
  `value_discrepancy`, which carries `import_run_id` as a **hard FK** — so deleting an argument
  with any recorded discrepancy raises `ForeignKeyViolation`. It is latent today only because
  almost nothing creates discrepancies yet; D-01's always-reconcile makes it routine, and
  D-25 makes candidates newly deletable. Separately, `value_discrepancy.target_id` is a
  **soft** reference to the participant, so participant deletion orphans rows silently. This is
  the same defect class Phase 48 closed for `argument_status_log` — fix both legs and cover
  them with a test that actually deletes an argument carrying discrepancies.

### Volume and observability

- **D-27:** **Nothing beyond batch counters** for reconcile volume. Phase 49's D-04 declined
  server-side paging with "revisit if the unbounded query proves slow against the real
  corpus"; applying the frequency test first, a discrepancy needs either an operator edit or
  a genuine corpus change, and reseeding prevents systematic drift from accumulating across
  code changes. A fail-loud cap was offered and declined. No paging, no cap.
- **D-28:** The reconcile pass gets a **`--dry-run` flag**. Default stays always-reconcile-and-
  write per D-01; `--dry-run` reports what it would accept, reject, record, and replace
  without touching a row. A batch that can rewrite utterance sets across thousands of
  arguments should be inspectable before it runs, and it eases D-09's proof setup.
- **D-29:** Reporting is **extended stdout counters** in the shape the importer already prints
  (`arguments_created`, `skipped_existing`, `docket_question_conflict`): arguments reconciled,
  unchanged, values accepted, values rejected, discrepancies recorded, utterance sets
  replaced. No report file, no verbose per-argument stream.
- **D-30:** The **transaction boundary stays per-argument, unchanged**. One argument's whole
  reconcile — new run row, full utterance set, value writes, discrepancy records, trust
  recompute — commits or rolls back together, and the batch continues past a failure exactly
  as `run_import_convokit`'s per-row try/except does now. This atomicity is what guarantees a
  `step="parse"` run can never become visible without its utterances (see Hard Constraints).

### Claude's Discretion

Nothing was answered with "you decide." Two implications were recorded rather than asked,
and the operator was invited to correct either:

- A stored participant with **no** external id (operator-created via `create_person_for_job`,
  or otherwise not derivable) is unpairable, and since `operator > corpus`, re-import leaves
  it entirely alone.
- Left to the planner and researcher: the digest algorithm and exact tuple it covers, counter
  names, the argument-scoped approve's surface placement, `prune-runs` flag design, and test
  file placement.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design notes (the paper design this milestone implements)
- `.planning/notes/import-architecture-diagnosis.md` — why the import layer felt wrong; names
  the three fabrications the corpus path performs and the "unified import with provenance as
  the discriminator" direction. Its "Agreed direction" §2 is this phase's mandate.
- `.planning/notes/import-entity-sketch.md` — the target entity shape. **Read alongside D-17:**
  its `ADMIN_JOB { int import_run_id FK }` is deliberately NOT implemented here.
- `.planning/notes/provenance-and-trust-model.md` — the authority ladder's source of truth,
  cited directly by `api/domain/authority.py`'s module docstring.

### Prior-phase decisions that bind this phase
- `.planning/phases/49-review-model/49-CONTEXT.md` — D-31/D-31a/D-31b (one gated writer, the
  ladder's return shape), D-14/D-15 (discrepancy record vs the legacy blob), D-22 (an operator
  edit does not rewrite provenance), D-35/D-35a (**the published lock — D-08 above turns on
  this**), D-24 (bulk confirm rejected).
- `.planning/phases/49-review-model/deferred-items.md` — the full dispositioned write-path
  inventory D-24 should extend, and the open Person-scoped question **D-23 closes**. Its
  `Status: open` line must be flipped in the same commit.
- `.planning/phases/47-provenance-foundation/47-CONTEXT.md` — the corpus/PDF verification split
  D-22 reuses.

### Project-level contracts
- `CLAUDE.md` — Architecture Rule 3 (re-running a step produces new rows under a new run id;
  **D-10 depends on this**), Alembic sole DDL authority, pipeline-offline-only.
- `.planning/PROJECT.md` — Key Decisions: the 2026-08-18 corpus-first / PDF-deferred constraint
  and its 2026-08-25 action; Phase 48's trust and two-gate publish decisions; the Phase 40.1
  stale-status lesson **D-23 invokes**.
- `.planning/ROADMAP.md` §"Phase 50: Unified Import Path" — the resolved corpus-only scope flag
  and the four renumbered success criteria.
- `.planning/REQUIREMENTS.md` — IMPORT-01/03/04/05 in scope; IMPORT-02 remapped to 999.11.

### Source files this phase turns on
- `pipeline/commands/import_convokit.py` — `_import_conversation` (the skip-existing early
  return at ~490, the `ImportRun` stamp at ~583, the fabricated `AdminJob` at ~640,
  `raw_speaker_label = full_name` at ~883, the participant dedup at ~912).
- `api/domain/authority.py` — `authority_rank` / `decide_write` / `WriteDecision`; all four
  rungs already defined.
- `api/services/admin_review.py` — the single gated writer (`_NAME_PART_FIELDS` at :54,
  `decide_write` calls at :187 and :254) that D-21 makes the pipeline's callee.
- `api/services/arguments.py:100-132` — the `MAX(ImportRun.id)` read path behind the blank-page
  hazard.
- `api/services/admin_jobs.py` — `get_run_id_for_step` at :377 (the derivation D-17 keeps),
  `approve_job` at :653 (the only `resolved_at` writer, per D-14), the corpus-source EXISTS
  subqueries at :161 and :268.
- `api/services/admin_arguments.py` — `publish_argument` at :626 (the non-overridable
  `resolved_at` gate), `delete_argument` at ~990 (the cascade with the D-26 defect).
- `api/models/models.py` — `ImportRun` at :465, `AdminJob` at :601, `ArgumentParticipant` at
  ~:420, `ValueDiscrepancy` at :642.

</canonical_refs>

<code_context>
## Existing Code Insights

### Stale-map warning — read this first

`.planning/codebase/*.md` are dated **2026-07-02 through 2026-07-08**, i.e. before Phases 47,
48, and 49 landed. They predate `import_run`, `trust_tier`, `review_state`,
`value_discrepancy`, `api/domain/authority.py`, and `/admin/review` entirely. **Do not plan
from them.** This discussion scouted current source directly; a researcher should do the same
or refresh the maps first.

### Reusable assets

- **`api/domain/authority.py`** — `decide_write` with all four rungs plus a fail-closed
  `UNKNOWN`, and a three-way `WriteDecision` enum that makes "reject silently" inexpressible.
  Nothing about the ladder needs building; it needs callers.
- **`api/services/admin_review.py`** — the gated writer, discrepancy recorder, and the four
  resolve actions. Imports no FastAPI, so the offline pipeline can call it (D-21).
- **`api.services.trust.recompute_argument_tier`** — already imported by four pipeline
  commands; never commits, so it composes inside the caller's transaction. Precedent for
  D-21's import direction, and the reconcile pass must call it after writes.
- **`api/services/argument_uniqueness.is_argument_pair_violation`** — the shared classifier the
  importer already uses as its `IntegrityError` safety net.
- **`pipeline recompute-trust`** — the offline drift-repair CLI shape D-12's `prune-runs`
  should mirror.
- **`/admin/review`** — tabs, tier × review-state × status filters, expandable discrepancy
  detail, inline confirm, confirm-as-unattributable. D-14's approve action and D-20's
  no-parity decision both lean on this already existing.
- **`_build_discrepancies(resolved)`** in `import_convokit.py` — dies with the corpus AdminJob
  (D-18); check for other callers before deleting.

### Established patterns

- **Provenance is declared at write time, never inferred.** Phase 47's D-02: `source`/`method`
  have no column default so every writer must state them. D-04 and D-07 follow this.
- **One pure domain module per contract, no ORM imports.** `api/domain/trust.py`,
  `person_names.py`, `authority.py` all take plain strings and stay importable by migrations
  and CLI alike. Any new pure logic belongs in that shape.
- **Structural/behavioral gates over source-text greps.** 49-02's no-parallel-mechanism test
  and 49-12's computed chrome sweep are the precedent D-24 names.
- **Per-conversation transaction, per-row error isolation.** `get_session()` commits one
  conversation atomically; `run_import_convokit` catches per row so one bad conversation never
  aborts the batch (D-30 keeps this).
- **Explicit kwargs over inherited model defaults.** `import_convokit` passes
  `status=ArgumentStatusEnum.CANDIDATE` explicitly and documents why — a changed model default
  does not reach an explicit call site.

### Integration points

- `_import_conversation`'s early return at ~line 490 is where the reconcile branch replaces
  skip-existing.
- The `AdminJob(...)` block at ~line 640 is the deletion site for D-14/D-19.
- `ArgumentParticipant` needs the D-04 column; `ImportRun` needs the D-13 digest column. One
  Alembic revision can carry both.
- `delete_argument`'s cascade needs a `value_discrepancy` step before its `ImportRun` delete
  (D-26), plus a participant-orphan sweep.
- `parse.py` / `resolve.py` / `import_justices` are the D-22 delegation sites.

### Hard constraints discovered during this discussion

1. **The blank-page hazard.** `api/services/arguments.py:100-108` selects the newest run as
   `MAX(ImportRun.id)` filtered to `step="parse"` AND `status=COMPLETED` — deliberately not a
   max over utterances, to avoid surfacing a crashed run's partial writes. **A `step="parse"` /
   `COMPLETED` run with no utterance rows makes that argument's public chat page render
   empty.** D-06 (`step="reconcile"`), D-10 (whole-set replace), and D-30 (per-argument
   atomicity) all exist to make this unreachable. Any plan that mints a parse-step run
   without writing its utterances in the same transaction is wrong.
2. **`resolved_at` is a non-overridable publish precondition** and `approve_job` is its only
   writer. Removing the corpus job without D-14 makes corpus arguments permanently
   unpublishable.
3. **`value_discrepancy` requires an `import_run_id`** to attribute a record to — which is why
   D-06's run is lazy rather than absent.
4. **`decide_write` normalizes before comparing** and already treats a blank stored value as
   ACCEPT; D-03 covers only the mirror case (blank *incoming*), which the ladder does not
   decide.

</code_context>

<specifics>
## Specific Ideas

- The operator's own framing on migrations is worth carrying verbatim into planning, because
  it removes work rather than adding it: *"we still have a lot of parsing and design work so
  the ability to reseed over and over is not going away. The current database is all throwaway
  entries so I don't care about migrating anything at this point."* Read as a standing
  constraint: in this milestone, propose DDL freely and legacy-data backfill never. It killed
  a data migration (D-15) and a column backfill (D-16) in the same breath.
- Two decisions were reversed toward *less* work by asking about frequency before severity —
  the reconcile-volume cap (D-27) and the argument-scoped resolve parity (D-20). In both, the
  evidence that settled it was how often the path actually fires and on which rows, not how
  bad it would be. Phase 49's D-20 exchange established this test; it keeps paying.
- Conversely, the two most valuable findings of this session came from reading the read path
  and the delete cascade rather than the write path everyone was discussing: the blank-page
  hazard and the `value_discrepancy` FK defect. Both are invisible from the importer. Budget
  the same outward read when planning.
- D-08 is the decision most likely to be second-guessed later, so its reasoning bears
  restating: the reconcile writer is a *seventh* path to argument data and `decide_write` has
  no notion of publication. Authority answers "may this value overwrite that one," never "may
  anything write here at all." Those two gates compose; they do not substitute.

</specifics>

<deferred>
## Deferred Ideas

- **`admin_job.import_run_id` (or the inverted `import_run.admin_job_id`)** → Phase 999.11 with
  the PDF route. Explicitly deviates from `import-entity-sketch.md` (D-17).
- **A runs-based pipeline list, or a dedicated Imports view over `ImportRun`** → Phase 51's
  design work at the earliest; unscoped by all four success criteria (D-19).
- **Argument-scoped `resolve` / `create_person` parity, closing 49-10's recorded
  person-assignment gap** → not now (D-20). Revisit if a corpus participant ever needs person
  *reassignment* with no job to do it from.
- **Server-side paging on `/admin/review`** → still Phase 49's D-04 bet; revisit only if real
  reconcile volume proves it (D-27).
- **A fail-loud cap on discrepancies per pass** → offered and declined (D-27).
- **A written per-argument reconcile report file** → offered and declined (D-29); counters only.
- **The Person-dedup mismatch across the two justice-import tools (White/Black/Clark/Douglas)**
  → still its own future phase, carried since Phase 42. D-23 deliberately keeps person merges
  unlocked so that fix stays possible.
- **Anything on the PDF route beyond D-22's real-writer test coverage** → Phase 999.11.

### Reviewed Todos (not folded)

All seven pending todos were surfaced by keyword match and **none were folded** — operator's
call. Recorded so a later phase knows they were considered:

- `2026-08-18-pdf-provenance-live-fixture-verification.md` (pipeline) — explicitly deferred
  *with* the PDF route; folding it would re-import deprioritized work into a corpus-only phase.
- `2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` (api) — genuinely adjacent
  (D-09's proof leans on `reset_to_fixture`), but kept out of scope.
- `2026-08-20-reset-error-copy-overclaims-db-corruption.md` (ui) — error copy on a destructive
  dev action.
- `2026-08-20-reset-has-no-timeout-or-progress.md` (ui) — observability on `reset_to_fixture`.
- `2026-08-12-speaker-popover-frontend-duplication-cleanup.md` (ui) — keyword noise.
- `2026-08-12-speakers-bench-classification-silent-fallback.md` (api) — a read-path
  classification bug; also why Phase 49's D-07 declined a `side` filter.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (dev-environment) — unrelated.

</deferred>

---

*Phase: 50-unified-import-path*
*Context gathered: 2026-08-25*
