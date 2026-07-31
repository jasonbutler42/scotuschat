# Phase 43: Dev-Only Reset to Fixture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-31
**Phase:** 43-Dev-Only Reset to Fixture
**Areas discussed:** Full-wipe deletion approach, Environment gate mechanism, State realization for the 3 variety fixtures, Confirmation UX & placement

---

## Full-wipe deletion approach

| Option | Description | Selected |
|--------|-------------|----------|
| TRUNCATE directly | Single transaction, TRUNCATE ... CASCADE (or explicit FK-ordered TRUNCATEs) across the full table set. Sidesteps FK-cascade-order problem entirely since it's a total wipe. | ✓ |
| Extend delete_fixture_argument.py's loop | Reuse the proven per-argument cascade order, iterate across every existing argument. Would need extending to cover court_tenures/people, which that script scopes out today. | |
| You decide | Claude picks based on simplest/safest. | |

**User's choice:** TRUNCATE directly (recommended option)
**Notes:** None — user followed the recommendation without further discussion; declined to explore table-inclusion specifics further ("Next area").

---

## Environment gate mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| New required ENVIRONMENT setting | Add `environment: str` to config, no default (fails fast like admin_token) or defaults to non-development. Allow-list gate: `environment == "development"`. | ✓ |
| DATABASE_URL heuristic | Reuse existing placeholder-guard pattern; require host/dbname to match dev conventions. No new env var, but fragile. | |
| You decide | Claude picks the safer option. | |

**User's choice:** New required ENVIRONMENT setting (recommended option)
**Notes:** Follow-up question asked whether the setting should have a default or fail fast.

| Option | Description | Selected |
|--------|-------------|----------|
| No default — fail fast | App refuses to start without ENVIRONMENT set, exactly like admin_token. | ✓ |
| Defaults to "production" | Fail-closed for the gate specifically, but app still boots without the var set. | |
| You decide | Claude picks based on safety/disruption tradeoff. | |

**User's choice:** No default — fail fast (recommended option)
**Notes:** None further; user moved to next area.

---

## State realization for the 3 variety fixtures

| Option | Description | Selected |
|--------|-------------|----------|
| Real service functions | Drive transitions through admin_jobs.py's resolve-completion and admin_arguments.py::publish_argument — same code paths the admin UI uses. | ✓ |
| Direct DB writes | Set status/AdminJob columns directly, bypassing the service layer. | |

**User's choice:** Real service functions (recommended option)
**Notes:** Locked without further discussion.

Follow-up: what distinguishes "Mid-pipeline" (22372) from the generic freshly-imported default state (which the Complexity fixture, 15169, also keeps)?

| Option | Description | Selected |
|--------|-------------|----------|
| AdminJob RUNNING, not PAUSED | Simplest distinguishable signal; no participant-level changes needed. | |
| Partially resolved participants | Actually resolve some ArgumentParticipant rows, leave others untouched — more useful for Phase 44's Resolve Table Rework testing, more implementation work. | |
| You decide | Claude picks the simplest option that's still genuinely distinguishable. | ✓ |

**User's choice:** You decide (deferred to Claude)
**Notes:** Recorded in CONTEXT.md as Claude's Discretion (D-04), with "AdminJob RUNNING" noted as the recommended default absent a stronger reason surfaced during research/planning.

---

## Confirmation UX & placement

| Option | Description | Selected |
|--------|-------------|----------|
| Type-to-confirm | Modal requires typing a confirmation phrase (e.g. "RESET") before the action activates. | |
| Simple Yes/No dialog | Modal states what will be wiped, Confirm/Cancel buttons. | ✓ |
| You decide | Claude picks based on existing UI patterns. | |

**User's choice:** Simple Yes/No dialog (user declined the type-to-confirm recommendation)
**Notes:** None given.

| Option | Description | Selected |
|--------|-------------|----------|
| New section on existing /admin dashboard | Add a marked "Dev Tools" section to the current stat-card landing page. | ✓ |
| New dedicated route | e.g. /admin/dev-tools — keeps the destructive action off the main dashboard. | |
| You decide | Claude picks based on existing UI patterns. | |

**User's choice:** New section on existing /admin dashboard (recommended option)
**Notes:** None given.

---

## Claude's Discretion

- D-04: Exact mechanics distinguishing "Mid-pipeline" state (22372) from the default freshly-imported state — user deferred, recommended default is AdminJob RUNNING.
- Full table list included in the TRUNCATE beyond the roadmap-named tables (cases, case_arguments, pipeline_runs, admin_jobs) — implementation detail, not surfaced as a user decision.
- Whether the new `environment` setting is a free-form string or constrained enum — only the allow-list comparison behavior was locked.

## Deferred Ideas

None — discussion stayed within phase scope.
