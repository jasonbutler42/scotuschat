# Phase 30: Corpus Import Resolve Workflow - Research

**Researched:** 2026-07-10
**Domain:** Internal backend wiring (SQLAlchemy/FastAPI/SvelteKit) — reusing an existing `AdminJob` state machine from a second write path. No new external libraries, no new schema.
**Confidence:** HIGH (all claims below are verified via direct read of the actual source files at their current committed state — see Sources)

## Summary

Phase 30 is not primarily an "integrate two systems" problem — it is a **write-path bug fix** in `pipeline/commands/import_convokit.py` plus a small, additive `AdminJob` insert. Two facts drive the entire plan:

1. **`Argument.status` must be `PIPELINE` at corpus-import creation time, not `DRAFT`.** Every read path this phase depends on (`list_resolve_rows_for_job`'s `editable` flag, `update_resolve_row_for_job`'s guard, the job-detail page's `readonlyMode` in `+page.server.ts`) computes editability as `argument.status == ArgumentStatusEnum.PIPELINE`. Today `import_convokit.py` sets `status=ArgumentStatusEnum.DRAFT` at line 398 (Phase 29 D-06). If this is left unchanged, every corpus-imported Resolve card renders **permanently read-only from the moment it's created** — directly contradicting D-01/D-03/D-05 (operator must be able to review and correct). This single write-path change is the crux of the whole phase.
2. **`AdminJob.discrepancies` (JSONB) must be populated at creation, mirroring `pipeline/commands/resolve.py`'s HIT-row shape**, or the ResolveCard's person re-matching affordances (Confirm/Select/Create person — D-05's explicit requirement) never render for corpus jobs. The Action column and the "Continue Resolve" disposition-tracking logic in `ResolveCard.svelte` are driven entirely by `AdminJobResponse.discrepancies`, not by `resolveRows` alone. An empty/`null` `discrepancies` list still lets "Continue Resolve" appear (via an existing `allDispositioned` fallback — see Pitfall 2), so the job *can* still be resolved, but the operator gets **no way to correct a wrongly-matched person** through the UI, which is the one thing D-03's "review and fix... speaker attributions" language is explicitly about.

Everything else genuinely works unmodified: `resolve_job()`, `get_run_id_for_step()`, `get_job_readiness()`, `create_person_for_job()`, `approve_job()`, and the nullable `argument_id` semantics all tolerate an `AdminJob` created directly at `PAUSED`/`RESOLVE` with `argument_id` pre-set, with zero PDF-ingest-specific assumptions that block the corpus path — **once (1) and (2) above are fixed.**

**Primary recommendation:** In `import_convokit.py`'s `_import_conversation`, after `_import_utterances()` returns (so every `ArgumentParticipant` for the argument — both advocates-dict-sourced and utterance-discovered bench speakers — already exists in the `resolved_participants` cache), (a) change the `Argument(...)` constructor's `status=` to `ArgumentStatusEnum.PIPELINE`, and (b) insert one new `AdminJob(status=PAUSED, current_step=RESOLVE, argument_id=argument.id, discrepancies=<built from resolved_participants.values()>)` row via `session.add()` — no separate commit, no separate idempotency check needed (it rides the same per-conversation transaction and the same idempotency gate `import_convokit.py` already has via the `oyez_transcript_id` dedup check earlier in the function).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `AdminJob` row creation for a corpus-imported argument | Pipeline (offline CLI) | — | `import_convokit.py` writes directly to Postgres via SQLAlchemy; per CLAUDE.md, FastAPI never triggers pipeline steps and the pipeline never calls the API |
| Argument.status lifecycle (`pipeline` → `draft`) | API / Backend (`api/services/admin_jobs.py`) | — | `resolve_job()`/`approve_job()` already own this transition for the PDF path; corpus path must land in the same state machine, not a parallel one |
| Resolve review UI (ResolveCard, RunStatusCard) | Frontend Server (SvelteKit `+page.server.ts`/`+page.svelte`) | API (read-only endpoints) | Reused completely unchanged per D-05 — no tier change needed |
| Pipeline list "Source" tag (PDF vs Corpus) | API / Backend (`list_jobs()`/`get_job()` derived field) | Frontend Server (display only) | Mirrors the existing `is_archived` derived-field pattern; the derivation must live in the query layer, not be computed client-side |
| Publish gate (`resolved_at IS NOT NULL`) | API / Backend (`admin_arguments.py`) | — | Unchanged — this phase's entire purpose is to make this gate reachable for corpus arguments, not to modify the gate itself |

## User Constraints

<user_constraints>
### Locked Decisions

- **D-01:** `import-convokit` creates the `AdminJob` row (status=paused, current_step=resolve, argument_id=<new argument's id>) immediately, as part of creating each `Argument` row — not a separate backfill command, not lazy/on-demand creation.
- **D-02:** No backfill path for the term-1955 data already imported without `AdminJob` rows. Simplest fix: wipe and re-run `import-justices` + `import-convokit` for term 1955 once this phase ships. No separate one-off migration/backfill script needed. **(Research note: this re-run is now confirmed necessary for a second reason beyond missing `AdminJob` rows — see Summary point 1. Existing term-1955 `Argument` rows were also written with `status=DRAFT`, which this phase's fix changes to `status=PIPELINE`. There is no way to "fix in place" without a data migration, so the existing wipe-and-rerun plan already covers this correctly.)**
- **D-03:** EVERY corpus-imported argument pauses for review, with no exceptions — even one with zero flagged speakers and perfectly clean auto-matched people still sits at `status=paused`/`resolved_at=NULL` until an operator explicitly completes resolve. No conditional "only pause if something was flagged" logic.
- **D-04:** No bulk/batch-approve tooling in this phase. Operator reviews one `AdminJob` at a time via the existing per-job Resolve UI.
- **D-05:** The existing Resolve card UI (`ResolveCard` on `/admin/pipeline/[id]`) is reused completely unchanged for corpus-imported jobs — same columns, same person re-matching affordances (Confirm/Select/Create person), same `?/resolve` batch action. Corpus-imported rows arrive already populated (advocates/bench resolved via Phase 29's `_resolve_person`/`_resolve_and_link_participant`) instead of starting blank.

### Claude's Discretion

- Exact mechanism for creating the `AdminJob` row inside `import_convokit.py`'s `_import_conversation` (before/after the `PipelineRun` row, exact insert shape) — **resolved by this research: insert after `_import_utterances()` returns, using `session.add()`, no separate commit; see Summary and Code Examples.**
- Whether `resolve_job()`/`update_resolve_row_for_job()` need corpus-specific branching — **resolved by this research: no branching needed in either function. The only required changes are in `import_convokit.py`'s write path (Argument.status, AdminJob.discrepancies), not in the reused service functions.**

### Deferred Ideas (OUT OF SCOPE)

- **Bulk/batch-approve tooling** (D-04) — deferred to a future phase once the review flow has been validated against real volume.
- **Edit affordance on utterances and speaker popover** — unrelated public-facing UI feature, explicitly declined for this phase (third phase in a row).
</user_constraints>

<phase_requirements>
## Phase Requirements

No phase requirement IDs are mapped yet (ROADMAP.md lists "Requirements: TBD" for Phase 30). The existing requirement family this phase must not diverge from is **REQUIREMENTS.md § "Pipeline Job Detail (`/admin/pipeline/[id]`)"**, specifically:

| ID | Description | Research Support |
|----|-------------|------------------|
| PJOB-01 | Run status card: status badge + source file linked to PDF | Confirmed null-safe already — `+page.svelte` only renders the PDF link block when `spaces_key \|\| pdf_url \|\| original_filename` is truthy (lines 196-197, 376). All three are `None` for corpus jobs; the block simply doesn't render. No change needed. |
| PJOB-02 | Run status card: Not ready / Ready / Already created states | `get_job_readiness()` works unmodified for corpus jobs **once Argument.status starts at `PIPELINE`** (see Summary point 1) — it derives state purely from `argument.status`, docket/question_number/argued_date presence, and unresolved-participant count, none of which are PDF-specific. |
| PJOB-14 | Resolve card: Not ready + Ready states fully editable; Already created is read-only | This is the exact contract broken by the current `status=DRAFT` write in `import_convokit.py` — see Summary point 1 and Pitfall 1. |
| PJOB-15 | Resolve card columns (Raw label / Resolved as / Bench-Advocate / Argument Role / Title / Action) | Unchanged, reused verbatim per D-05. |
| PJOB-18 | Person selection: operator confirms side first, then typeahead | Only applies to true "MISS" rows (no `discrepancy` gate for HIT-shaped corpus rows) — see Pitfall 2 for why corpus rows should be built as HIT-shaped discrepancies, not MISS-shaped. |
| PJOB-19 | New person mini-form in resolve (Name + Bench/Advocate toggle) | Reused unchanged — `create_person_for_job()` requires `job.status == PAUSED`, which is true for corpus jobs by construction (D-01). |
| PJOB-20 | "Create Argument" CTA lives in run status card | Unchanged — this is the `approve_job()` step that finally transitions `Argument.status` from `PIPELINE` → `DRAFT` for corpus arguments too (see Summary/Pattern 1). |
| PJOB-21 | "Continue Resolve" action at bottom of resolve card when all rows dispositioned | Works for corpus jobs via the existing `allDispositioned` fallback (empty-or-populated `discrepancies` both resolve to a renderable button) — see Pitfall 2. |
</phase_requirements>

## Standard Stack

No new libraries. This phase is a pure internal wiring change across three already-present modules:

| Component | File | Role in this phase |
|-----------|------|---------------------|
| `AdminJob` / `AdminJobStatus` / `AdminJobStep` ORM models | `api/models/models.py` | Reused unchanged — no migration |
| `resolve_job`, `get_job_readiness`, `update_resolve_row_for_job`, `create_person_for_job`, `approve_job`, `get_run_id_for_step`, `list_jobs`, `get_job` | `api/services/admin_jobs.py` | Reused unchanged (service layer) |
| `list_resolve_rows_for_job` | `api/services/admin_people.py` (lines 773+) | Reused unchanged — computes `editable` from `argument.status == PIPELINE` |
| `_import_conversation`, `_resolve_and_link_participant`, `_import_utterances` | `pipeline/commands/import_convokit.py` | **Modified** — write-path fix (Argument.status) + new AdminJob insert |
| `normalize_label` | `pipeline/commands/resolve.py` | Reused import (already imported this way by `admin_jobs.py`) — needed if the corpus AdminJob's discrepancies include a `normalized` key for parity with the PDF shape (cosmetic; not read by the Svelte UI) |
| `ResolveCard.svelte`, `RunStatusCard.svelte` | `app/src/lib/components/` | Reused unchanged (D-05) |
| `+page.server.ts` (job detail) | `app/src/routes/admin/pipeline/[job_id]/` | Reused unchanged — `readonlyMode` derivation already correct once Argument.status is fixed |

**Installation:** none — no new packages.

## Package Legitimacy Audit

**Not applicable.** This phase introduces zero new external packages (npm or PyPI). All work is a write-path fix and one new row-insert against existing SQLAlchemy models.

## Architecture Patterns

### System Architecture Diagram

```
                          ┌─────────────────────────────────────────┐
                          │   pipeline/commands/import_convokit.py   │
                          │        (offline CLI, per-conversation)   │
                          └───────────────────┬───────────────────────┘
                                              │
   1. dedup check (oyez_transcript_id)         │  early-return if already imported
   2. Case / CaseArgument scaffolding           │  (idempotency gate — covers AdminJob too)
   3. Argument row created                     │  ★ status = PIPELINE (was DRAFT — FIX)
   4. PipelineRun row created (step="parse",    │
      strategy="convokit_import")               │
   5. advocates-dict speaker resolution →       │
      ArgumentParticipant rows (person_id set)  │
   6. utterance streaming →                     │
      additional bench ArgumentParticipant rows │  resolved_participants{} accumulates
      + Utterance rows                          │  EVERY participant across steps 5+6
                                              │
                          ┌───────────────────▼───────────────────────┐
                          │  ★ NEW: AdminJob row inserted here          │
                          │  status=PAUSED, current_step=RESOLVE,      │
                          │  argument_id=argument.id,                  │
                          │  discrepancies=<HIT-shaped list built      │
                          │  from resolved_participants.values()>      │
                          └───────────────────┬───────────────────────┘
                                              │  (single commit — get_session() context manager)
                                              ▼
                          ┌─────────────────────────────────────────┐
                          │        Postgres: admin_jobs row           │
                          │        status=paused / current_step=resolve│
                          └───────────────────┬───────────────────────┘
                                              │
                          ┌───────────────────▼───────────────────────┐
                          │  Operator opens /admin/pipeline/[job_id]   │
                          │  (existing FastAPI + SvelteKit path,       │
                          │   completely unmodified — D-05)            │
                          │                                             │
                          │  ResolveCard renders EDITABLE rows          │
                          │  (readonlyMode=false because Argument      │
                          │   .status == 'pipeline')                    │
                          │  Action column shows Confirm/Change/Create  │
                          │  person (because discrepancies populated)  │
                          └───────────────────┬───────────────────────┘
                                              │  operator clicks "Continue Resolve"
                                              ▼
                          ┌─────────────────────────────────────────┐
                          │  POST /jobs/{id}/resolve → resolve_job()  │
                          │  job.status → COMPLETED                   │
                          │  Argument.resolved_at → now()              │
                          │  Argument.status STILL 'pipeline'          │
                          └───────────────────┬───────────────────────┘
                                              │  readiness recomputed → "ready"
                                              ▼
                          ┌─────────────────────────────────────────┐
                          │  Operator clicks "Create Argument" CTA    │
                          │  POST /jobs/{id}/approve → approve_job()  │
                          │  Argument.status → DRAFT (D-09)            │
                          └───────────────────┬───────────────────────┘
                                              │
                                              ▼
                          ┌─────────────────────────────────────────┐
                          │  publish_argument() gate now satisfiable  │
                          │  (resolved_at IS NOT NULL) — original      │
                          │  phase goal achieved                       │
                          └─────────────────────────────────────────┘
```

### Recommended Project Structure

No new files. Changes are confined to:
```
pipeline/
└── commands/
    └── import_convokit.py     # MODIFIED: Argument.status fix + AdminJob insert + discrepancies builder

api/
├── services/
│   └── admin_jobs.py          # MODIFIED (small): list_jobs()/get_job() gain a `source` derived field
└── schemas/
    └── admin_jobs.py           # MODIFIED (small): AdminJobResponse gains `source: Literal["pdf","corpus"]`

app/src/routes/admin/pipeline/
└── +page.svelte                # MODIFIED (small): new Source column/tag per 30-UI-SPEC.md
```

### Pattern 1: Two-step resolve → approve lifecycle (must apply identically to corpus jobs)

**What:** The PDF-ingest pipeline never marks an `Argument` as `DRAFT` inside the resolve step itself. `resolve_job()` only stamps `resolved_at` and completes the `AdminJob`; a **separate** operator action (`approve_job()`, fired by the "Create Argument" CTA once `get_job_readiness()` reports `"ready"`) is what flips `Argument.status` from `PIPELINE` to `DRAFT`.

**When to use:** This is not optional for corpus jobs — it is the mechanism that makes D-03's "operator explicitly completes resolve" meaningful as a two-stage gate (resolve, then approve) rather than one click doing everything silently.

**Example (existing code, confirmed unmodified-compatible):**
```python
# Source: api/services/admin_jobs.py:360-479 (resolve_job) — direct code read
# Step 3 of resolve_job(): completes the JOB, stamps resolved_at, but
# never touches Argument.status. This is correct and must not change.
await db.execute(
    update(AdminJob)
    .where(AdminJob.id == job_id)
    .values(status=AdminJobStatus.COMPLETED)
    .execution_options(synchronize_session=False)
)
if job.argument_id is not None:
    await db.execute(
        update(Argument)
        .where(Argument.id == job.argument_id)
        .values(resolved_at=func.now())
        .execution_options(synchronize_session=False)
    )
```
```python
# Source: api/services/admin_jobs.py:487-541 (approve_job) — direct code read
# This is the ONLY place Argument.status transitions PIPELINE -> DRAFT.
# Corpus jobs must go through this exact same function via the same
# "Create Argument" CTA the operator already knows from PDF jobs.
if argument.status != ArgumentStatusEnum.PIPELINE:
    raise ValueError(...)  # double-approve guard — also protects corpus jobs
await db.execute(
    update(Argument)
    .where(Argument.id == job.argument_id)
    .values(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
    .execution_options(synchronize_session=False)
)
```

### Pattern 2: Building HIT-shaped `discrepancies` for an already-resolved corpus row

**What:** `pipeline/commands/resolve.py` (PDF path) writes one dict per resolved raw label into `AdminJob.discrepancies` even when auto-resolved via `SpeakerAlias` (a "HIT"), specifically so the browser can still show the auto-match for confirmation/correction. Corpus-imported `ArgumentParticipant` rows are conceptually all "HITs" (already resolved via `_resolve_person`/`_resolve_and_link_participant`), so this phase must synthesize the same shape.

**When to use:** Immediately when building the new `AdminJob` row in `_import_conversation`, after `_import_utterances()` returns.

**Example:**
```python
# Source: pipeline/commands/resolve.py:245-255 — the exact HIT shape to mirror.
# discrepancies.append({
#     "raw_speaker_label": raw_label,
#     "normalized": normalized,
#     "candidates": [],  # HIT rows need no candidates — operator confirms or overrides
#     "auto_match_id": person_id,
#     "auto_match_name": person.full_name,
#     "auto_match_role": auto_match_role,
#     "auto_resolved": True,
# })

# Recommended for import_convokit.py (new helper, direct analog):
from pipeline.commands.resolve import normalize_label

def _build_discrepancies(participants: list[ArgumentParticipant]) -> list[dict]:
    """One HIT-shaped dict per already-resolved corpus participant (D-05 parity)."""
    return [
        {
            "raw_speaker_label": p.raw_speaker_label,
            "normalized": normalize_label(p.raw_speaker_label),
            "candidates": [],
            "auto_match_id": p.person_id,
            # full_name IS raw_speaker_label for corpus rows (see
            # _resolve_and_link_participant: raw_speaker_label = full_name) —
            # no extra Person query needed.
            "auto_match_name": p.raw_speaker_label,
            "auto_match_role": None,  # corpus Person rows never set role_id
            "auto_resolved": True,
        }
        for p in participants
        if p.person_id is not None
    ]
```

### Pattern 3: `AdminJob` insertion point inside `_import_conversation`

**What:** Insert AFTER `_import_utterances(...)` returns, not right after the `PipelineRun` row.

**Why this order matters:** `advocates` dict resolution (Task 3, runs before utterance streaming) only covers petitioner/respondent/amicus counsel. Bench (Justice) participants are discovered **only** while streaming utterances (`_import_utterances` calls `_resolve_and_link_participant` for each new `turn["speaker"]`). Both code paths write into the *same* `resolved_participants` dict passed by reference, so by the time `_import_utterances()` returns, `resolved_participants.values()` holds every `ArgumentParticipant` (or `None` for unattributed sentinels) created for this argument — exactly the population `_build_discrepancies()` needs. Building this list any earlier would silently omit every bench Justice.

```python
# Source: pipeline/commands/import_convokit.py:394-483 (_import_conversation) —
# recommended insertion point, direct code read confirms this is the last
# statement of the function today.
argument = Argument(
    argued_date=argued_date,
    question_number=next_question_number,
    source_docket=case_fields["docket_no"],
    status=ArgumentStatusEnum.PIPELINE,  # Phase 30 fix — was DRAFT (D-06 superseded)
    oyez_transcript_id=conversation_id,
)
...
await _import_utterances(
    session=session, argument_id=argument.id, pipeline_run_id=run.id,
    strategy=run.strategy, turns=turns, speakers_index=speakers_index,
    resolved_participants=resolved_participants, counters=counters,
)

# --- Phase 30: pause every corpus-imported argument for operator review (D-01, D-03) ---
resolved = [p for p in resolved_participants.values() if p is not None]
session.add(
    AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
        discrepancies=_build_discrepancies(resolved),
    )
)
# No separate commit/flush needed — get_session()'s context manager commits
# the whole per-conversation transaction (Case/Argument/PipelineRun/
# ArgumentParticipant/Utterance/AdminJob) atomically on clean exit.
```

### Anti-Patterns to Avoid

- **Do not reuse `api/services/admin_jobs.py`'s `create_job()` helper for the corpus path.** It defaults to `status=PENDING`/`current_step=INGEST` and calls `await db.commit()` internally — an early commit mid-`_import_conversation` would break the per-conversation atomicity Phase 29 relies on (T-29-05b resilience: one malformed conversation must not partially commit). Construct the `AdminJob` row directly with `session.add()`, matching how `Case`/`Argument`/`PipelineRun` are already created in this file.
- **Do not add a "skip pause if zero flags" shortcut**, even though `pipeline/commands/resolve.py`'s own PDF path has exactly this shortcut (skips straight to `COMPLETED` when there are no misses). D-03 is an explicit, deliberate override of that precedent for the corpus path — mirroring it here would silently violate a locked decision.
- **Do not add a second `select()`-before-insert idempotency check for `AdminJob`.** It is unnecessary and would duplicate an already-covered gate: `_import_conversation` already returns early (`counters["skipped_existing"] += 1`) if `Argument.oyez_transcript_id == conversation_id` already exists, **before** any row (including the new `AdminJob`) is created. A re-run of an already-imported term never reaches the `AdminJob` insertion at all.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Paused review queue / operator gate | A new corpus-specific "review" table or status flag | The existing `AdminJob` PAUSED/RESOLVE state machine (`api/services/admin_jobs.py`) | It already has readiness derivation, resolve mutation, person creation, and approve — building a parallel mechanism would duplicate ~500 lines of tested logic for zero benefit |
| Corpus-vs-PDF source badge | A new `source` column + migration | Derived field via `outerjoin`/`exists()` on `PipelineRun.strategy == "convokit_import"`, mirroring the shipped `is_archived` pattern (`admin_jobs.py:219-255`) | Alembic is the sole DDL authority (CLAUDE.md) and no schema change is actually needed — the signal already exists in `PipelineRun.strategy` |
| Person re-match UI for corpus rows | A new "corpus resolve" Svelte component | `ResolveCard.svelte` unchanged, fed via the existing `discrepancies` JSONB contract | D-05 explicitly requires this; the component already generalizes over "already resolved" (HIT) rows because the PDF pipeline already produces HIT rows for auto-matched aliases |

**Key insight:** Every piece of machinery this phase needs already exists and was built generically enough (Phase 25) to not require corpus-specific branches — the only thing missing is that `import_convokit.py` (Phase 29) never fed that machinery in the shape it expects. This is a **producer-side bug fix**, not a consumer-side feature build.

## Runtime State Inventory

**Trigger check:** This phase changes the write-path of a rename-adjacent field (`Argument.status` default for the corpus path) and introduces a new row for existing production data (term 1955 already imported without `AdminJob` rows). Runtime State Inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Term-1955 `Argument` rows exist today with `status=DRAFT`, `resolved_at=NULL`, and **no** corresponding `AdminJob` row. These arguments are currently permanently stuck (unreachable publish gate) and, after this phase ships, would ALSO be permanently stuck in read-only Resolve-card mode if left as-is (status=DRAFT ≠ PIPELINE). | **Data migration required — but D-02 already specifies it:** wipe term-1955 `Argument`/`Case`/`CaseArgument`/`PipelineRun`/`ArgumentParticipant`/`Utterance` rows and re-run `import-justices` + `import-convokit --term 1955` after this phase ships. No separate one-off script — the same idempotent import path produces correct rows (status=PIPELINE + paired AdminJob) once patched. Confirm the wipe step deletes in FK-safe order (Utterance → ArgumentParticipant → CaseArgument → PipelineRun → Argument → Case, matching the documented `delete_argument` cascade order in STATE.md's v1.4 decisions) or simply re-uses whatever wipe mechanism the operator already has for this (not building a new one is in scope discretion). |
| Live service config | None — no n8n/Datadog/Tailscale/Cloudflare config touches this phase. | None. |
| OS-registered state | None — `import-convokit` is an ad hoc operator-run CLI command, not a scheduled task. | None. |
| Secrets/env vars | None — no new env vars, no key renames. | None. |
| Build artifacts | None — no package/dependency changes. | None. |

## Common Pitfalls

### Pitfall 1: Leaving `Argument.status=DRAFT` on corpus creation silently defeats the entire phase

**What goes wrong:** The Resolve card renders with every row `editable=false` from the instant it's created (because `list_resolve_rows_for_job` and the job-detail page's `readonlyMode` both key on `argument.status == 'pipeline'`), and `update_resolve_row_for_job` (the PATCH endpoint backing per-row Side/Title edits) raises `ValueError` on every call. The job still shows up in the Pipeline list as "Needs Review" (job.status=PAUSED), creating the illusion of a working review queue while the review UI is inert.

**Why it happens:** Phase 29's D-06 ("draft status is the review gate") predates Phase 30's decision to route through the `AdminJob` state machine instead. The two decisions are mutually incompatible; Phase 30 supersedes D-06 for the `Argument.status` write, without CONTEXT.md explicitly saying so (it only flagged the *symptom* — `resolved_at` never gets set — not this root cause).

**How to avoid:** Change the `Argument(...)` constructor in `_import_conversation` to `status=ArgumentStatusEnum.PIPELINE` (or simply omit `status=` entirely, since `PIPELINE` is the model's own column default). Confirm no other corpus-specific code path (e.g. `list_arguments()`'s admin directory filter) depends on corpus arguments being immediately visible as `DRAFT` — verified: `list_arguments()` already excludes `PIPELINE`-status rows from the admin arguments list, exactly matching pre-existing PDF-ingest behavior (an argument mid-pipeline is invisible in that list until `approve_job()` promotes it). No divergence introduced.

**Warning signs:** After implementing, manually load a fresh corpus job's detail page and confirm the Side `<select>`/Title `<input>` render as editable controls, not plain text — this is the fastest smoke test that the fix landed.

### Pitfall 2: Leaving `AdminJob.discrepancies` unpopulated silently drops the person-rematch UI (but NOT the "Continue Resolve" button — easy to miss in testing)

**What goes wrong:** `ResolveCard.svelte`'s Action column renders `—` (nothing) for every row when `row.discrepancy` is `null` (i.e., no matching entry in `discrepancies`). This looks correct in a quick test because the "Continue Resolve" button **still appears and still works** — `allDispositioned` has a fallback (`WR-04` in the component's own comments): `if (disc.length === 0) return true`, i.e. an empty discrepancies list is treated as "nothing left to disposition." So a tester who only checks "can I click through resolve" will see success even with zero `discrepancies` — the missing Confirm/Change/Create-person affordance (D-05's explicit requirement) is easy to miss without specifically checking for it.

**Why it happens:** `discrepancies` is a JSONB passthrough field that only the PDF-ingest `resolve.py` script currently populates; nothing about the field's existence or purpose is visible from `admin_jobs.py`'s service layer (it just carries whatever JSON was written).

**How to avoid:** Populate `discrepancies` with one HIT-shaped dict per resolved `ArgumentParticipant`, exactly mirroring `resolve.py`'s HIT branch (see Pattern 2 above). This makes every row start in the `'confirmed'` disposition state client-side (because `auto_resolved: True`), which is also what makes `allDispositioned` become `true` immediately and the "Continue Resolve" button work — for the *right* reason instead of the fallback's coincidental empty-list handling.

**Warning signs:** In manual testing, open a corpus job's detail page and check the Action column specifically — if every row shows `—` instead of a "Change" button, `discrepancies` was not populated.

### Pitfall 3: Assuming `get_run_id_for_step(db, job_id, "parse")` needs a corpus-specific branch

**What goes wrong (if you assume this and "fix" it unnecessarily):** Someone reviewing `resolve_job()`'s reliance on a `PipelineRun` with `step == "parse"` to scope its `Utterance`/`ArgumentParticipant` UPDATE statements might assume the corpus path (which has no separate ingest/parse/resolve subprocesses) needs a new step value or a bypass.

**Why it's actually fine:** Phase 29-08 (STATE.md decision log) already relabeled `import_convokit.py`'s single per-argument `PipelineRun.step` from `"ingest"` to `"parse"` *specifically* to satisfy this exact contract (`admin_jobs.py`'s `get_run_id_for_step`/`get_argument_with_utterances`'s established `step == "parse"` read convention). Confirmed via direct read of `import_convokit.py:434-449`: the corpus `PipelineRun` row is created with `step="parse"`. `resolve_job()`'s query (`select(PipelineRun.id).where(argument_id=..., step="parse").order_by(created_at desc()).limit(1)`) will find this row correctly with zero changes.

**How to avoid:** Do not add a corpus-specific step value or branch in `resolve_job()`/`get_run_id_for_step()`. This was already fixed proactively in Phase 29 gap-closure.

### Pitfall 4: `cover_metadata`-derived hint text will show "N/A" for corpus jobs — cosmetic only, not a blocker

**What goes wrong:** `ArgumentDetailsCard`'s "Extracted: ..." hint text (sourced from `Argument.cover_metadata` JSONB, populated only by the PDF cover-page extractor) will always read "N/A" for corpus jobs, since `import_convokit.py` never writes `cover_metadata`. Likewise `get_job()`'s `parse_stats.case_name`/`argued_date`/`primary_docket` will be `None` (though `utterance_count`/`bench_count`/`advocate_count` will populate correctly since those come from live `Utterance`/`ArgumentParticipant` COUNT queries, not `cover_metadata`).

**Why it happens:** `cover_metadata` is architecturally a "what did we extract from a PDF cover page" field — corpus imports have no PDF cover page.

**How to avoid:** Nothing to fix — the real (non-hint) values (`Argument.argued_date`, `source_docket`, `question_number`) are populated directly from corpus data and render correctly in the editable fields themselves; only the parenthetical "Extracted:" preview text is blank. This is arguably more honest than fabricating a hint. Do not spend effort backfilling `cover_metadata` for corpus jobs — out of scope and not requested by any decision.

## Code Examples

### Deriving `source: Literal["pdf","corpus"]` for `list_jobs()` (UI-SPEC's open Data Contract Note)

The 30-UI-SPEC.md's recommended approach (outerjoin mirroring `is_archived`) needs one adjustment: `is_archived`'s outerjoin is `AdminJob → Argument` (1:1 by FK, safe to join directly). The proposed `source` derivation is `AdminJob → Argument → PipelineRun`, which is **1:many** (an argument can have multiple `PipelineRun` rows across reruns/step-advances) — a raw `outerjoin` risks duplicate `AdminJob` rows in the result set if more than one linked `PipelineRun` matched the filter. Use `exists()` instead, which is duplication-safe regardless of how many `PipelineRun` rows an argument accumulates over time:

```python
# Source: adapted from api/services/admin_jobs.py:219-255 (list_jobs, is_archived
# pattern) — direct code read confirmed the existing 1:1 outerjoin shape; this
# is a necessary adjustment for the 1:many Argument->PipelineRun relationship.
from sqlalchemy import exists

from pipeline.commands.import_convokit import PIPELINE_RUN_STRATEGY  # "convokit_import"

is_corpus_subq = exists(
    select(PipelineRun.id).where(
        PipelineRun.argument_id == AdminJob.argument_id,
        PipelineRun.strategy == PIPELINE_RUN_STRATEGY,
    )
)

query = select(AdminJob, Argument.status, is_corpus_subq.label("is_corpus")).outerjoin(
    Argument, AdminJob.argument_id == Argument.id
)
...
for job, arg_status, is_corpus in rows:
    job.__dict__["source"] = "corpus" if is_corpus else "pdf"
```

**Note on `PIPELINE_RUN_STRATEGY` import:** `pipeline/commands/import_convokit.py` is pipeline-layer code; `api/services/admin_jobs.py` is API-layer code. CLAUDE.md's architecture rules don't prohibit importing a constant across these layers (this codebase already does the reverse — `admin_jobs.py` imports `normalize_label` from `pipeline.commands.resolve`, and `admin_arguments.py` imports `_derive_slug` from `pipeline.commands.ingest`) — this is an established, precedented cross-layer import pattern in this codebase, not a new one. Alternatively, hardcode the literal string `"convokit_import"` in `admin_jobs.py` with a comment cross-referencing the constant, if the planner prefers not to import from the pipeline package into the API package for this specific case — either is consistent with existing precedent since both directions already occur elsewhere in the codebase.

**`get_job()` also needs this field** (UI-SPEC's open question #5, confirmed): while `get_job()` currently defaults `is_archived` to `False` unconditionally (with a comment explaining the detail page derives its archived signal from the *readiness* endpoint instead), there is no equivalent alternate source for `source` on the detail page — nothing else tells the operator "this is a corpus job" on `/admin/pipeline/[job_id]` itself. Add the same `exists()`-based single-row derivation to `get_job()` for parity (a single extra scalar subquery on an already-narrow single-row query — negligible cost, and the 30-UI-SPEC.md's scope is currently written for the list page only; extending to the detail page is a small, low-risk addition worth doing in the same task since the underlying data derivation is identical).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Corpus imports write `Argument.status=DRAFT` directly, bypassing any review gate (Phase 29 D-06) | Corpus imports write `Argument.status=PIPELINE` and pair every argument with a `PAUSED`/`RESOLVE` `AdminJob`, routing through the same review gate as PDF ingests | This phase (30) | D-06 (Phase 29) is superseded for the `Argument.status` write; `resolved_at` becomes reachable for the first time for this import path |
| `PipelineRun.step` for corpus imports was `"ingest"` | Relabeled to `"parse"` | Phase 29-08 (prior gap-closure, already shipped) | Prerequisite that makes `resolve_job()`'s `get_run_id_for_step(..., "parse")` call work unmodified for corpus jobs — already done, nothing further needed here |

**Deprecated/outdated:** Phase 29 CONTEXT.md's D-06 ("draft status is the review gate") for the `Argument.status` write in `import_convokit.py` — the "review gate" role is now played by the `AdminJob` PAUSED/RESOLVE state (`resolved_at` + eventual `approve_job()`), not by an immediate `DRAFT` status.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The wipe-and-rerun mechanism for term-1955 data (D-02) is an operator-run manual step with no existing dedicated script beyond re-invoking `import-justices`/`import-convokit` — no separate deletion tooling exists yet and the planner may need to write ad hoc SQL or a small throwaway script for the wipe itself. | Runtime State Inventory | If a deletion helper already exists elsewhere in the pipeline CLI that this research missed, the planner may duplicate effort; low risk since D-02 already anticipated a manual wipe. |
| A2 | Corpus-created `Person` rows never populate `role_id`, so `auto_match_role` in the synthesized `discrepancies` should always be `None` (mirroring `resolve.py`'s own `None` fallback when `role_id` is unset). Verified directly against `_resolve_person`'s `Person(...)` constructor (no `role_id` argument), but not exhaustively checked against every code path that might later backfill `role_id` for corpus people. | Pattern 2 / Code Examples | Low — if a role_id backfill is later added, `auto_match_role` would just stay `None` in the discrepancies snapshot, which only affects a cosmetic label already tolerant of `None` in the Svelte component. |

## Open Questions

1. **Exact wipe mechanism for term-1955 re-import (D-02)**
   - What we know: D-02 says "wipe and re-run" with no separate migration script; the FK-safe delete order likely mirrors the documented `delete_argument` cascade (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob → Argument, per STATE.md's v1.4 decision), but no corpus-specific bulk-delete-by-term tool currently exists in the pipeline CLI.
   - What's unclear: Whether the planner should write a small one-off SQL script/pipeline subcommand for this wipe, or whether it's expected to be done via ad hoc `psql`/DBeaver by the operator outside of any committed code.
   - Recommendation: Treat this as a planning-time decision, not a research gap — confirm with the user during planning whether a throwaway wipe script belongs in this phase's plan or is truly meant to be manual/ad hoc (D-02's exact wording, "no separate one-off migration/backfill script needed," suggests manual `psql` is acceptable, but the planner should make this explicit as a task either way).

2. **Whether `get_job()`'s new `source` field should also drive anything on the job-detail page's `+page.svelte` beyond what 30-UI-SPEC.md scopes**
   - What we know: 30-UI-SPEC.md explicitly scopes the Source tag to the **list** page only, and explicitly says the detail page (`RunStatusCard`, `ResolveCard`) is unchanged.
   - What's unclear: Whether adding `source` to `AdminJobResponse`/`get_job()` (recommended above, for API consistency between `list_jobs()` and `get_job()`) implies the detail page's `+page.svelte`/`+page.server.ts` should also display it, or whether the field should exist in the schema/service layer but simply go unused by the detail page's UI for now.
   - Recommendation: Add the field to the schema/service layer (cheap, consistent, and avoids a future phase needing to retrofit it), but do NOT add any new detail-page UI element for it — 30-UI-SPEC.md's explicit "Out of Scope Confirmation (D-05)" section already forecloses new detail-page UI surfaces this phase.

## Environment Availability

Skipped — this phase has no new external dependencies (no new CLI tools, no new services, no new package managers). All required tooling (Python 3.12, PostgreSQL 16, SQLAlchemy 2.0 async, existing pipeline CLI) is already in continuous use by Phase 29's shipped code.

## Validation Architecture

Skipped — `.planning/config.json` has `workflow.nyquist_validation: false`.

## Security Domain

This phase touches no new attack surface: it does not add a new API endpoint, does not change authentication/authorization, and reuses the existing `X-Admin-Token`-gated admin router unchanged. The one behavioral change with security-adjacent shape is the `Argument.status` write-path fix — this makes previously-DRAFT (implicitly visible-once-published-eligible-looking, but actually gate-blocked) corpus arguments instead start in `PIPELINE` state, which is *already* the state every PDF-ingested argument starts in and is already excluded from the public `/cases/` surface and the admin arguments directory list until explicitly promoted. This is a narrowing of exposure during the pipeline window, not a widening — no new ASVS category applies beyond what Phase 25's original `AdminJob` design already satisfied.

## Sources

### Primary (HIGH confidence — direct code read, current repository state)
- `api/services/admin_jobs.py` (full file) — `resolve_job`, `get_job_readiness`, `update_resolve_row_for_job`, `create_person_for_job`, `approve_job`, `get_run_id_for_step`, `list_jobs`, `get_job`, `create_job`
- `api/models/models.py` (full file) — `AdminJob`, `Argument`, `PipelineRun`, `ArgumentParticipant`, all enums
- `api/services/admin_arguments.py` (lines 1-90, 460-500) — `list_arguments`, `publish_argument`
- `api/services/admin_people.py` (lines 200-330, 773-833) — `list_resolve_rows_for_job`
- `api/schemas/admin_jobs.py` (full file) — `AdminJobResponse`, `RunReadiness`, `ResolveRowUpdate`
- `pipeline/commands/import_convokit.py` (full file) — `_import_conversation`, `_resolve_person`, `_resolve_and_link_participant`, `_import_utterances`, `PIPELINE_RUN_STRATEGY`
- `pipeline/commands/resolve.py` (lines 140-400) — HIT/MISS `discrepancies` shape, PAUSED-vs-COMPLETED gating on `misses`
- `pipeline/db.py` (full file) — `get_session()` commit-on-exit transaction boundary
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (full file) — `readonlyMode` derivation, all form actions
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (relevant excerpts) — PDF-link null-safety
- `app/src/lib/components/ResolveCard.svelte` (full file) — `discrepancies`-driven Action column, `allDispositioned` fallback
- `app/src/routes/admin/pipeline/+page.svelte` (full file) — list page badge/table structure
- `.planning/phases/30-corpus-import-resolve-workflow/30-CONTEXT.md`, `30-UI-SPEC.md`
- `.planning/REQUIREMENTS.md` § "Pipeline Job Detail"
- `.planning/STATE.md` — Phase 25/26/29 decision log entries confirming the `PipelineRun.step` relabel (29-08) and `is_archived` derivation pattern (26-06)
- `.planning/config.json` — `nyquist_validation: false` confirmed

**Methodology note on confidence tagging:** This phase's research questions are 100% internal-codebase-mechanics questions (does function X make assumption Y), not external library/API documentation questions. The `gsd-tools query research-plan`/`classify-confidence` seam's provider waterfall (`context7`/`exa`/`tavily`/`websearch`/etc.) models external documentation sources only — it has no "direct codebase read" provider tier. Per this project's own source hierarchy definition ("VERIFIED = confirmed via tool AND from an authoritative source"), a direct `Read`/`Grep` of the actual, currently-committed source file **is** the authoritative source for these claims, and the `Read`/`Grep` tool calls are the verifying tool. All claims above are tagged HIGH/`[VERIFIED: direct code read]` on that basis; no `[ASSUMED]` claims requiring separate user confirmation exist in this research beyond the two items in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external libraries involved; internal APIs directly read
- Architecture: HIGH — full state-machine trace confirmed via direct read of every function in the resolve/approve/readiness lifecycle
- Pitfalls: HIGH — both major pitfalls (Argument.status, discrepancies) were confirmed by tracing the exact conditional logic in the consuming Svelte component and service functions, not inferred

**Research date:** 2026-07-10
**Valid until:** No expiry driver (internal codebase research, not a fast-moving external ecosystem) — re-verify only if `api/services/admin_jobs.py`, `api/services/admin_people.py`, or `pipeline/commands/import_convokit.py` change materially before this phase is planned/executed.
