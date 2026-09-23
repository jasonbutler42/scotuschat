---
phase: 49-review-model
plan: 11
subsystem: api
tags: [fastapi, sqlalchemy, svelte, sveltekit, published-lock, trust]

requires:
  - phase: 49-review-model
    provides: "49-09's published-lock flag (speakersLocked) and the folded-todo-cited guard on update_participant_side; 49-10's converged Speakers card"
provides:
  - "Published guards on update_argument, update_argument_metadata (api/services/admin_arguments.py)"
  - "Published guards on resolve_job, create_person_for_job (api/services/admin_jobs.py)"
  - "D-35a recorded in 49-CONTEXT.md; complete four-way-dispositioned write-path inventory in deferred-items.md"
  - "The always-editable decision reversed in place on the argument-detail page; Case card and Argument Details card locked behind 49-09's single flag; one page-level lock statement"
affects: [49-verify-work, 49-ship]

actuals:
  tokens: 21000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Whole-argument published lock: six argument-data writers (2 pre-existing + 4 new) share one predicate (ArgumentStatusEnum.PUBLISHED) and one error-prose clause ('is published (current status: ...)'), asserted by name-scoped parity tests rather than an extracted helper"
    - "Guard reuses the already-loaded row instead of a second SELECT, pinned by an executable select-count assertion, because three AsyncMock-driven tests depend on the exact db.execute call sequence"

key-files:
  created:
    - api/tests/test_phase49_argument_lock_contract.py
  modified:
    - api/services/admin_arguments.py
    - api/services/admin_jobs.py
    - api/routers/admin.py
    - api/tests/test_admin_arguments_service.py
    - app/src/routes/admin/arguments/[id]/+page.svelte
    - app/src/routes/admin/arguments/[id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - .planning/phases/49-review-model/49-CONTEXT.md
    - .planning/phases/49-review-model/deferred-items.md

key-decisions:
  - "Raised-message citation: the two pre-existing guards (update_participant_side, update_resolve_row_for_job) cite the folded todo 2026-08-21-widen-participant-editability-to-all-unpublished-states in their raised ValueError text; this plan's four new guards instead cite 'D-35/D-35a, operator, 2026-08-24' in the raised text (the folded todo is participant-editability-specific and doesn't fit whole-argument data). All six share the SAME structural shape and the SAME literal clause 'is published (current status: ...)', which is what the grep gate and the parity test actually pin — not a byte-identical citation string. Recorded here per the plan's own read_first instruction to align to what shipped rather than mint a third dialect."
  - "create_person_for_job's guard only fires when the job resolves to an actual PUBLISHED Argument (job.argument_id is not None AND that argument exists AND is published) — unlike resolve_job, a job with NO linked argument is a legitimate call here (bare Person creation, out of D-35a's scope per the Person-writer prohibition), so an unconditional 'Argument not found for this job' raise would have broken that path."
  - "The page-level lock statement's flag is 49-09's speakersLocked, reused verbatim (never renamed) even though its name now covers the whole page, not just the Speakers card — the plan explicitly forbids minting a second flag."
  - "test_page_derives_no_second_published_lock_flag scopes 'exactly one published-status comparison' to FLAG DECLARATIONS ((const|let) NAME = data.argument.status === 'published';), not to every inline use of the raw comparison — the Status card's 'Last published' label and the Danger Zone's publish/unpublish branch both use the raw comparison directly for unrelated reasons and this plan's prohibitions require both to stay untouched. A literal whole-page-comparison-count would already be 3 before this plan even started."

requirements-completed: [REVIEW-02, REVIEW-04]

duration: 70min
completed: 2026-08-25
status: complete
---

# Phase 49 Plan 11: Whole-Argument Published Lock (D-35a) Summary

**Six argument-data writers (update_argument, update_argument_metadata, update_participant_side, update_resolve_row_for_job, resolve_job, create_person_for_job) now share one published predicate and one error-prose clause; the argument-detail page's prior always-editable decision is reversed in place and cited, with the Case and Argument Details cards locked behind 49-09's single `speakersLocked` flag.**

## Performance

- **Duration:** ~70 min
- **Tasks:** 3/3 complete
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- `api/services/admin_arguments.py::update_argument` and `::update_argument_metadata` both refuse a PUBLISHED argument, proved by live non-persistence tests across every affected column (argued_date, case_name, docket_number, docket_number_norm, slug, source_docket, source_dockets, question_number).
- `api/services/admin_jobs.py::resolve_job` and `::create_person_for_job` — the two job-scoped participant writers D-35's first half (49-09) never reached — now refuse a PUBLISHED argument too, closing the inventory with defence-in-depth guards against a currently-unreachable-but-plausible-future path.
- Deliberate non-locks proved live: `unpublish_argument` still succeeds on a published argument; `resolve_participant_review` still advances `review_state` on one.
- A parity assertion extracts all six argument-data writers BY NAME and asserts each carries `ArgumentStatusEnum.PUBLISHED` and the shared `"is published (current status:"` clause — scoped away from `publish_argument`/`unpublish_argument` so it can't be trivially satisfied.
- The argument-detail page's `readonly is always false here` decision is reversed in place, cited to D-35/D-35a/operator/2026-08-24 at the same call site; the Case card's two inputs and Save button, and one page-level lock statement, all consult 49-09's single `speakersLocked` flag — no second flag minted.
- Both `save` and `saveArgumentDetails` server actions surface honest published-rejection copy naming unpublishing as the remedy, matching 49-09's own `detail.includes('is published')` technique; pre-existing collision/duplicate branches untouched.
- `deferred-items.md`'s inventory is now complete and four-way dispositioned (locked / lifecycle / not-the-argument's-data / ambiguous); `49-CONTEXT.md` carries `### D-35a (locked)`.

## Task Commits

1. **Task 1: Lock update_argument and update_argument_metadata** - `afd880650` (feat)
2. **Task 2: Lock resolve_job and create_person_for_job; prove non-locks; publish inventory** - `912418432` (feat)
3. **Task 3: Reverse always-editable decision; lock Case/Argument Details cards** - `6e379ed94` (feat)

_Note: `api/routers/admin.py`'s four docstring-only edits (2 for Task 1's endpoints, 2 for Task 2's) landed together in the Task 1 commit — a single small doc-only file edited in one pass rather than split by task, since the edits are independent, non-conflicting docstring additions with no functional coupling. Documented here rather than left implicit._

## Files Created/Modified

- `api/tests/test_phase49_argument_lock_contract.py` (created) - The whole-argument lock contract module: 17 assertions across all three tasks.
- `api/services/admin_arguments.py` - Published guards on `update_argument` (before the lead-Case load) and `update_argument_metadata` (reusing the row already loaded at step a).
- `api/services/admin_jobs.py` - Published guards on `resolve_job` (loads the owning Argument, previously not loaded at all) and `create_person_for_job` (guarded only when the job resolves to an actual published Argument).
- `api/routers/admin.py` - Four docstring additions documenting the new 422 case on both PATCH argument endpoints and both job-scoped endpoints.
- `api/tests/test_admin_arguments_service.py` - Three `AsyncMock`-driven `SimpleNamespace` fixtures gained an explicit `status=ArgumentStatusEnum.DRAFT` attribute — an addition, nothing else changed.
- `app/src/routes/admin/arguments/[id]/+page.svelte` - Comment reversal + citation at the `ArgumentDetailsCard` call site; `readonly={speakersLocked}`; Case card inputs/button disabled under `speakersLocked`; one page-level lock statement above the Case card.
- `app/src/routes/admin/arguments/[id]/+page.server.ts` - `save` and `saveArgumentDetails` actions branch on `detail.includes('is published')` and return honest copy.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` - `metadataReadonly` comment corrected: `update_argument_metadata` now has its own published guard; the page's restriction is a narrower CANDIDATE-boundary concern layered on top.
- `.planning/phases/49-review-model/49-CONTEXT.md` - `### D-35a (locked)` appended after D-35, D-35's own text unmodified.
- `.planning/phases/49-review-model/deferred-items.md` - The D-35 published-write inventory replaced with the complete D-35a inventory (locked / lifecycle / not-the-argument's-data / ambiguous), plus the one new operator question.

## Decisions Made

See `key-decisions` in frontmatter. In addition:

- **49-09's published-lock flag, as found:** `speakersLocked`, declared at `app/src/routes/admin/arguments/[id]/+page.svelte:124` as `const speakersLocked = data.argument.status === 'published';`. Reused verbatim for the Case card and the page-level statement — no second flag introduced (confirmed structurally: exactly one such declaration exists on the page).
- **49-09's frontend match substring, as found:** `updateParticipantSide`'s server action branches on `detail.includes('is published')` and returns `'This argument is published, so its data is read-only. Unpublish it first to edit roles or descriptors.'`. This plan's `save` and `saveArgumentDetails` actions match on the identical substring and use closely matching copy (adapted per-form: "edit it" instead of "edit roles or descriptors").
- **49-09's error prose shape, as found:** both pre-existing guards (`update_participant_side`, `update_resolve_row_for_job`) raise `ValueError(f"Argument {argument.id} is published (current status: {argument.status.value!r}); ... is read-only once an argument has been published (Phase 49 folded todo: 2026-08-21-widen-participant-editability-to-all-unpublished-states).")`. This plan's four new guards keep the identical structural shape (id, status value, "is published (current status: ...)" clause) but cite `(D-35/D-35a, operator, 2026-08-24)` in place of the folded-todo slug, since that slug is specific to participant-editability widening and doesn't describe whole-argument data. The docstrings on all four new guards separately cite D-35/D-35a in full prose. This is recorded as an intentional, structurally-consistent choice, not a drift — the plan's own read_first note for Task 1 anticipated exactly this reconciliation ("align to what actually shipped ... do not mint a third shape").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring literal `select(Argument)` inflated the select-count assertion**
- **Found during:** Task 1, first run of `test_published_guards_add_no_second_argument_select`
- **Issue:** `update_argument_metadata`'s new docstring paragraph originally read "...never a second `select(Argument)`..." — the literal substring matched the test's regex-based select-count extractor, which does not distinguish docstring prose from executable code, inflating the count to 2 and failing the assertion even though the actual guard added zero queries.
- **Fix:** Reworded the docstring to say "never a second SELECT of the Argument row" instead of the literal `select(Argument)` call-shape text.
- **Files modified:** `api/services/admin_arguments.py`
- **Verification:** `test_published_guards_add_no_second_argument_select` passes; count is 1 for both functions.
- **Committed in:** `afd880650`

**2. [Rule 1 - Bug] New reversal comment accidentally quoted the exact banned phrase it replaced**
- **Found during:** Task 3, first run of `test_always_editable_decision_is_reversed_in_place`
- **Issue:** The replacement comment above `ArgumentDetailsCard` initially quoted the prior decision VERBATIM in quotation marks ("readonly is always false here: ...") to explain what it reversed — which meant the exact banned phrase was still present in source, failing the assertion that the phrase is gone.
- **Fix:** Reworded the replacement comment to paraphrase the prior decision instead of quoting it verbatim.
- **Files modified:** `app/src/routes/admin/arguments/[id]/+page.svelte`
- **Verification:** `test_always_editable_decision_is_reversed_in_place` passes.
- **Committed in:** `6e379ed94`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs caught by the RED-phase assertions themselves, exactly the mechanism they exist to provide).
**Impact on plan:** Both are wording-only corrections inside the same task's own edit; no scope creep, no architectural change.

## Issues Encountered

**Environment note, not a code issue:** this sandbox's Bash tool intermittently returned early (exit code 144) from long-running `pytest api/tests -q` invocations while the underlying process continued running to completion in the background. This was resolved by polling the redirected log file / process id rather than trusting the tool call's own return code, and — for the final full-suite gate — by splitting the ~1150-test suite into two halves to keep each invocation well under whatever resource ceiling was triggering the early return. Both halves passed cleanly with no failures. This is an execution-environment quirk, not a defect in the plan or the code; recorded here in case a future executor hits the same thing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- D-35a is fully closed: the whole-argument published lock is proved live on all four new writers, the deliberate non-locks are proved live, and the page-level UI reversal is in place with structural coverage.
- This plan does NOT close G-49-3 — 49-10 already did. `gap_ids` is deliberately empty in this plan's frontmatter so `/gsd-verify-work`'s reconciliation attributes G-49-3 to exactly one plan.
- One NEW operator question remains open (recorded in `deferred-items.md` and in `49-CONTEXT.md`'s D-35a entry): whether `Person`-scoped writers (`update_person`, `merge_people`, and siblings) should be restricted at all, given a `Person` is shared across every argument they appear in. Not decided here — genuinely ambiguous, distinct from the whole-argument-scope question this plan answered.
- Five `<human-check>` items from Task 3's browser verification are NOT observed by this executor (no browser tool available) — see the dedicated section below.

## Human-Check Items (Not Observed — Browser Required)

None of the following were run; all require a live browser, which this executor does not have. Recorded per-item rather than merged with the structural claims:

1. **Not observed.** On a PUBLISHED argument at `/admin/arguments/{id}`: confirm the one page-level lock line reads correctly near the top; confirm the Case card's title/docket inputs and Save button render visibly disabled; confirm the Argument Details card's docket pills/question number/argued date render disabled and its own Save button does not render; confirm every Copy affordance on both cards still works.
2. **Not observed.** Same page: confirm Publish/Unpublish and the Danger Zone still work exactly as before; confirm unpublishing the argument makes every locked control editable again and the lock line disappears.
3. **Not observed.** On a DRAFT/UNPUBLISHED/CANDIDATE argument: confirm neither card shows any change and there is no lock line.
4. **Not observed.** Force a save against a published argument (e.g. publish in a second tab, submit the Case card from the first) and confirm the message names unpublishing as the remedy, never a generic try-again message, and never shows a raw decision id or date.
5. **Not observed / judgment call.** Confirm one page-level line (rather than a line per locked card) reads well when scrolled to the Argument Details card specifically — if it reads as broken rather than locked at that scroll position, that becomes a follow-up.

Per the plan's standing note (49-EVIDENCE.md §9 item 4 — `.env` credential-access denial, unchanged since 49-01), this browser pass could not be run by this executor. Filed to the broken-windows ledger below as an `unrun-verify` entry rather than left implicit.

## Self-Check: PASSED

All 9 created/modified source files and 3 task commit hashes (afd880650, 912418432, 6e379ed94) verified present on disk / in git history.

---
*Phase: 49-review-model*
*Completed: 2026-08-25*
