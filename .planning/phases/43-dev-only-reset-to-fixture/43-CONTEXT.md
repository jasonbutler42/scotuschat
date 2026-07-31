# Phase 43: Dev-Only Reset to Fixture - Context

**Gathered:** 2026-07-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 43 delivers a dev-only "Reset to Fixture" action, triggered from the admin panel, that:

1. Fully wipes the local database — every argument, utterance, person, court tenure, argument_participant, and the cases/pipeline_runs/admin_jobs rows that reference them.
2. Reseeds exactly Phase 41's four confirmed fixtures (FIXTURES.md) through the real `import-convokit` path (not a hand-rolled seeder), so Phase 42's importer fixes flow through automatically.
3. Lands the three "state-variety" fixtures in distinct, intended publish/pipeline states (not all left at the generic freshly-imported default).
4. Refuses to execute against a real/production environment, demonstrated by an actual attempt, not just asserted from the code.
5. Requires an explicit operator confirmation step before anything is deleted.

This is how the DB gets returned to a known state between corpus/resolve iteration attempts — not a general-purpose data-management tool.

</domain>

<decisions>
## Implementation Decisions

### Full-wipe deletion method
- **D-01:** Wipe via direct TRUNCATE of the full table set (roles/lookup tables excluded) in a single transaction, rather than looping Phase 42's `scripts/delete_fixture_argument.py` per-argument cascade-delete across every row. It's a total wipe, not a scoped delete, so there's nothing to preserve and no FK-cascade-order problem to solve — TRUNCATE sidesteps it entirely. `delete_fixture_argument.py` explicitly scopes court_tenures/people out of its cascade today; extending it to cover those would be extra work for no benefit here. — **Reversibility:** reversible — this only governs the reset script's internal SQL; nothing external depends on which mechanism performs the wipe.

### Environment gate
- **D-02:** Add a new required `environment: str` setting to `api/core/config.py`, with no default — the app fails to start without it set, exactly like `admin_token` today. The gate is allow-list, not block-list: it checks `settings.environment == "development"`, so an unset, misconfigured, or unknown value refuses by default rather than accidentally passing. This replaces the earlier idea of sniffing `DATABASE_URL` (too fragile — a dev DB hosted anywhere else, or a prod DB matching a dev-like host pattern, would break the gate silently). — **Reversibility:** costly — every deployed environment (dev, staging if any, and the DO production app) must have `ENVIRONMENT` set before this ships, or the app won't boot; rolling this out requires coordinating env-var config across all deployment targets first.

### State realization for the 3 variety fixtures
- **D-03:** Drive the DRAFT and Published target fixtures to their end states through the real service functions — the same resolve-completion path `api/services/admin_jobs.py` uses to move PIPELINE→DRAFT, and `admin_arguments.py::publish_argument` for DRAFT→PUBLISHED — never direct column writes. This guarantees `ArgumentStatusLog` rows, `resolved_at`/`published_at` timestamps, and any other side effects stay consistent with what a real operator action would produce, with no drift as the service layer evolves.
- **D-04 (Claude's discretion, user deferred):** What distinguishes "Mid-pipeline" (conversation 22372) from the generic freshly-imported default (status=PIPELINE, AdminJob PAUSED/RESOLVE — which is also where the Complexity fixture, 15169, stays) is left to Claude/planner judgment. Recommended default absent a stronger reason: flip the AdminJob to RUNNING instead of PAUSED — the simplest change that's still genuinely distinguishable, with no participant-level resolve work required. The heavier alternative (partially resolving some ArgumentParticipant rows, leaving others untouched) was raised as more useful for Phase 44's Resolve Table Rework testing but more implementation effort; only switch to it if research/planning finds a concrete reason the simple version won't serve Phase 44.

### Confirmation UX & placement
- **D-05:** Confirmation is a simple Yes/No dialog (not type-to-confirm) — Confirm / Cancel buttons, with the dialog stating exactly what will be wiped before the action runs (per DEVTOOL-01/success criterion 3).
- **D-06:** The "Reset to Fixture" control lives as a new section on the existing `/admin` dashboard (the current stat-card landing page at `app/src/routes/admin/+page.svelte`) rather than a new dedicated route — clearly marked as a dev-tools/destructive section, not a new page.

### Claude's Discretion
- Exact "Mid-pipeline" mechanics (D-04 above) — user explicitly said "you decide."
- Full table list included in the TRUNCATE (D-01) — the roadmap names arguments/utterances/people/court_tenures/argument_participants explicitly; cases, case_arguments, pipeline_runs, and admin_jobs also need clearing since the reseed recreates them fresh via import-convokit, but the exact statement ordering/grouping is an implementation detail for planning, not a user decision.
- Whether the new `environment` setting is a free-form string or a constrained enum — D-02 only locks the allow-list comparison behavior (`== "development"`), not the Python type.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Fixture set (reseed target)
- `.planning/FIXTURES.md` — the confirmed four-fixture set (15169 complexity, 13015 DRAFT-target, 18897 Published-target, 22372 Mid-pipeline-target), and the "State-variety roles are Phase 43 targets" section explaining these are targets to realize, not states present in the raw corpus data.

### Prior-phase invariants this phase must not break
- `.planning/STATE.md` — Phase 30 note: corpus-imported arguments must land at `status=PIPELINE` paired with a PAUSED/RESOLVE `AdminJob`, or they're unpublishable; a reseed that skips this reproduces the bug Phase 30 fixed. Phase 29 CR-01 note: `question_number` is derived per-docket via `select(func.max(...))`, never hardcoded. Phase 31 note: the test suite's `pytest_sessionfinish` hook fails any run that changes shared-dev-DB row counts — this reset must never be exercised against the shared dev DB from a test.

### Prior art for the deletion/import mechanics
- `scripts/delete_fixture_argument.py` — Phase 42's proven FK-cascade-order fix (including the `argument_status_log` bug this phase's blocker note calls out); read for the cascade order even though Phase 43 uses TRUNCATE instead of this script's per-row loop.
- `pipeline/commands/import_convokit.py` — the real import path the reseed must go through; Phase 42 added a `--conversation-id` flag (joins the existing `--term`/`--term-range` mutually-exclusive group) for scoping a single conversation, which the reseed will need to call once per fixture.

### Service functions for state realization (D-03)
- `api/services/admin_jobs.py` — resolve-completion function (PIPELINE→DRAFT transition, ~line 577-591).
- `api/services/admin_arguments.py::publish_argument` (~line 569) — DRAFT→PUBLISHED transition.

### Known blocker relevant to this phase
- `.planning/STATE.md` "Blockers/Concerns" — `api/services/admin_arguments.py::delete_argument` omits `argument_status_log` from its FK cascade; irrelevant once TRUNCATE is used (D-01), but confirms why `delete_fixture_argument.py` added that defensive step.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/commands/import_convokit.py --conversation-id` (Phase 42) — scoped single-conversation import; the reseed step calls this once per fixture conversation ID.
- `api/services/admin_jobs.py` resolve-completion path and `api/services/admin_arguments.py::publish_argument` — reused as-is to drive state transitions (D-03), not reimplemented.

### Established Patterns
- Fail-fast required settings with no default (`admin_token` in `api/core/config.py`) — D-02's new `environment` setting follows this exact pattern.
- `_db_configured`-style placeholder guards (`scripts/cleanup_leaked_test_rows.py`, `api/tests/conftest.py`) — considered and rejected in favor of D-02's explicit setting; noted here so planning doesn't re-derive the rejected option from scratch.

### Integration Points
- `app/src/routes/admin/+page.svelte` — existing stat-card admin dashboard; D-06 adds a new section here rather than a new route.
- `ArgumentStatusEnum` / `AdminJobStatus` / `AdminJobStep` enums in `api/models/models.py` (~lines 46-72) — the state values D-03/D-04 operate over.

</code_context>

<specifics>
## Specific Ideas

No particular visual/UX references beyond D-05/D-06 above — a simple Yes/No confirm dialog on a new dev-tools section of the existing admin dashboard.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 43-Dev-Only Reset to Fixture*
*Context gathered: 2026-07-31*
