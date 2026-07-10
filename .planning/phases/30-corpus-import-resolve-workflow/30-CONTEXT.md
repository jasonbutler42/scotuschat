# Phase 30: Corpus Import Resolve Workflow - Context

**Gathered:** 2026-07-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Corpus-imported arguments (from Phase 29's `import-convokit`) currently land at `status=draft` with `Argument.resolved_at` permanently `NULL`, because `import-convokit` never sets it. The existing publish gate (`publish_argument()` in `api/services/admin_arguments.py`) requires `resolved_at IS NOT NULL`, so as things stand today no corpus-imported argument can ever be published — the gate is permanently unsatisfiable for this import path.

This phase routes every corpus-imported argument through the same `AdminJob`-based paused/resolve review workflow the PDF-ingest pipeline already uses (built in Phase 25), so an operator reviews and fixes each one (missing name parts on auto-created people, stray bad speaker attributions, general correctness) via the existing Resolve card UI before it can be published.

**Discovered during Phase 29 gap-closure debugging (this session), not from planned scope:**
- Two real data-quality gaps this phase's review workflow is meant to catch: (1) `_resolve_person` in `pipeline/commands/import_convokit.py` only ever sets `full_name` on newly-created `Person` rows — `first_name`/`last_name`/`middle_name` stay `NULL` (real `speakers.json` only has a single `name` string, no name parts). This is already surfaced by the existing People admin "Missing fields" filter (Phase 27), so it doesn't need separate tooling — the resolve review is where an operator would notice and fix it. (2) A ConvoKit speaker-identity sentinel bug (`<INAUDIBLE>`/`<UNKNOWN>` resolving as if they were real advocates) was found and fixed directly in Phase 29's code during this session (commit `4dc2c072`) — not part of this phase's scope, mentioned here only as context for why "human review before publish" matters for this data source.

</domain>

<decisions>
## Implementation Decisions

### Job Creation Trigger
- **D-01:** `import-convokit` creates an `AdminJob` row (status=`paused`, current_step=`resolve`, `argument_id=<the newly-created argument>`) immediately, as part of creating each `Argument` row — not a separate backfill command, not lazy/on-demand creation. The moment an operator runs a term import, every argument from that batch already has a paused job waiting in the Pipeline list.
- **D-02:** No backfill path for the term-1955 data already imported without `AdminJob` rows (this feature didn't exist yet when that import ran). Simplest fix: wipe and re-run `import-justices` + `import-convokit` for term 1955 once this phase ships, so the same import path that creates future jobs also creates this batch's jobs. No separate one-off migration/backfill script needed.

### Pause Scope — Universal, No Auto-Skip
- **D-03:** EVERY corpus-imported argument pauses for review, with no exceptions — even one with zero flagged speakers and perfectly clean auto-matched people still sits at `status=paused`/`resolved_at=NULL` until an operator explicitly completes resolve. No conditional "only pause if something was flagged" logic. This is a deliberate, explicit choice (not a default) given the review queue could reach ~7,800 items across the full historical corpus — the user chose correctness/consistency over queue size.

### Bulk Review Tooling — Deferred
- **D-04:** No bulk/batch-approve tooling in this phase. The operator reviews one `AdminJob` at a time via the existing per-job Resolve UI, exactly as with PDF-ingested arguments. A future phase may revisit this once the review flow has been validated against real volume (deferred idea, not built here — see Deferred section).

### Resolve UI — Reuse Unchanged
- **D-05:** The existing Resolve card UI (`ResolveCard` on `/admin/pipeline/[id]`) is reused completely unchanged for corpus-imported jobs — same columns (Raw label / Resolved as / Bench/Advocate / Argument Role / Title / Action), same person re-matching affordances (Confirm/Select/Create person), same `?/resolve` batch action. The only difference from a PDF-ingest job is that corpus-imported rows arrive already populated (advocates/bench resolved via Phase 29's `_resolve_person`/`_resolve_and_link_participant`) instead of starting blank — the operator still confirms or corrects via the identical UI, not a new one.

### Claude's Discretion
- Exact mechanism for creating the `AdminJob` row inside `import_convokit.py`'s `_import_conversation` (e.g. whether it's created before or after the `PipelineRun` row, and whatever query/insert shape fits the existing per-conversation transaction) — left to the planner/implementer.
- Whether `resolve_job()`/`update_resolve_row_for_job()` (currently PDF-pipeline-specific service functions in `api/services/admin_jobs.py`) need any corpus-specific branching, or whether they already generalize correctly once a corpus-sourced `AdminJob` row exists in the right shape — the researcher should verify this against the real code before planning locks an approach.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Prior Decisions
- `.planning/ROADMAP.md` — Phase 30 goal (§ "Phase 30: Corpus Import Resolve Workflow"), depends on Phase 29.
- `.planning/phases/29-historical-corpus-import/29-CONTEXT.md` — original corpus-import decisions (D-06: draft status is the review gate; D-11: `oyez_speaker_id` primary match key; D-12: no automated QA gate, import everything).
- `.planning/PROJECT.md` — Key Decisions table, Phase 29 entries (esp. the `question_number` dedup gap-closure and PDF pipeline being unaffected).

### Prior Phase Establishing the Reused Mechanism
- `.planning/phases/25-pipeline-job-detail-page/25-CONTEXT.md` — original design of the paused/resolve `AdminJob` workflow this phase extends to corpus-sourced arguments.
- `.planning/REQUIREMENTS.md` §"Pipeline Job Detail (`/admin/pipeline/[id]`)" — PJOB-01 through PJOB-23, the existing Resolve card contract (columns, states, actions) this phase must not diverge from (D-05).

### Code This Session Already Touched (Phase 29 gap-closure, informs this phase's starting point)
- `pipeline/commands/import_convokit.py` — `_import_conversation`, `_get_or_create_case`, `_resolve_person`, `_resolve_and_link_participant`; this is where the new `AdminJob` creation (D-01) gets wired in.
- `api/services/admin_jobs.py` — `resolve_job()`, `update_resolve_row_for_job()`, `try_advance_parse_to_resolve()`; the existing paused/resolve state machine this phase's jobs must fit into without modification (per D-05).
- `api/services/admin_arguments.py` — `publish_argument()`; the `resolved_at IS NOT NULL` gate this whole phase exists to eventually satisfy.
- `api/models/models.py` — `AdminJob`, `AdminJobStatus`, `AdminJobStep`, `Argument`, `ArgumentStatusEnum` — no schema changes anticipated, but the researcher should confirm.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/services/admin_jobs.py` — the entire paused/resolve state machine (`AdminJobStatus.PAUSED` + `AdminJobStep.RESOLVE`, `resolve_job()`, `update_resolve_row_for_job()`) already exists and works for PDF-ingest jobs; this phase's job is to make corpus-imported arguments land in that same state, not build a new one.
- `app/src/routes/admin/pipeline/[job_id]/` (`ResolveCard`, `RunStatusCard`) — the existing UI this phase reuses unchanged (D-05).

### Established Patterns
- `AdminJob` rows today are created in exactly one place (`api/services/admin_jobs.py:77`, inside the normal ingest-job-creation flow) at `status=PENDING`/`current_step=INGEST`, then advance through PARSE → RESOLVE via `try_advance_parse_to_resolve()`. This phase introduces a SECOND creation path (from `import_convokit.py`, directly at `status=PAUSED`/`current_step=RESOLVE`) — a new pattern, not an extension of the existing one, since corpus imports skip ingest/parse entirely.
- Idempotency pattern already established for corpus imports: check-before-insert via `select()` → `scalar_one_or_none()` (Plan 29-04/29-09) — the new `AdminJob` creation should follow the same discipline so re-running an already-imported term doesn't create duplicate jobs for the same argument.

### Integration Points — Gaps Found During Scouting (not user decisions — planner/researcher must address)
- No existing code path creates an `AdminJob` directly in the `PAUSED`/`RESOLVE` state for an argument that already has fully-populated `ArgumentParticipant` rows. The researcher should verify whether `update_resolve_row_for_job()`/`resolve_job()` genuinely work unmodified against a corpus-sourced job, or whether they make PDF-ingest-specific assumptions (e.g., about `PipelineRun.step` values, or fields expected to still be null) that need a small adjustment.
- `admin_jobs.py`'s `AdminJob.argument_id` is nullable (`NULL` until ingest creates the argument, per the existing model comment) — for corpus-imported jobs, `argument_id` should be set immediately at job-creation time (the argument already exists by then), which is a different invariant than the PDF-ingest path's "starts NULL, gets set later." Confirm nothing downstream assumes `argument_id IS NULL` implies "not yet ingested" in a way that would misclassify a corpus-sourced job.

</code_context>

<specifics>
## Specific Ideas

- User's own framing: "It's going to be a lot of work for the operator but they should probably all be sitting in the paused state and waiting for the operator to review and finish the resolve." — directly resulted in D-01/D-03 (universal pause, no auto-skip, even knowing the review queue could reach ~7,800 items).
- User discovered two concrete data-quality problems during Phase 29 debugging that motivated this phase: several new justices/advocates created during import only had `full_name` populated (no first/last name parts), and a bogus advocate named `<INAUDIBLE>` was created from a ConvoKit sentinel value. The `<INAUDIBLE>` bug was fixed directly in Phase 29's code this session (not part of this phase); the missing-name-parts gap is a real data quality issue this phase's review workflow addresses via the existing "Missing fields" filter, not new tooling.

</specifics>

<deferred>
## Deferred Ideas

- **Bulk/batch-approve tooling** (D-04) — e.g. "approve all with zero flags in this term/batch." Explicitly deferred: the user wants to validate the one-at-a-time review flow against real volume first before deciding what's safe to bulk-approve. Revisit as its own future phase once this phase has shipped and been used against a larger term range.

### Reviewed Todos (not folded)
- **Edit affordance on utterances and speaker popover** (`.planning/todos/pending/2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md`) — surfaced again by automated todo cross-referencing (third phase in a row: also declined for Phase 28 and Phase 29). It's a public-facing UI feature, unrelated to this phase's admin-only backend review workflow. User confirmed: leave in backlog, do not fold into Phase 30.

</deferred>

---

*Phase: 30-Corpus Import Resolve Workflow*
*Context gathered: 2026-07-10*
