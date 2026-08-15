# Phase 43: Dev-Only Reset to Fixture - Research

**Researched:** 2026-07-31
**Domain:** FastAPI/SvelteKit admin tooling — destructive DB reset gated by environment, reusing existing corpus-import and argument-lifecycle service functions
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Full-wipe deletion method**
- **D-01:** Wipe via direct TRUNCATE of the full table set (roles/lookup tables excluded) in a single transaction, rather than looping Phase 42's `scripts/delete_fixture_argument.py` per-argument cascade-delete across every row. It's a total wipe, not a scoped delete, so there's nothing to preserve and no FK-cascade-order problem to solve — TRUNCATE sidesteps it entirely. `delete_fixture_argument.py` explicitly scopes court_tenures/people out of its cascade today; extending it to cover those would be extra work for no benefit here. — **Reversibility:** reversible — this only governs the reset script's internal SQL; nothing external depends on which mechanism performs the wipe.

**Environment gate**
- **D-02:** Add a new required `environment: str` setting to `api/core/config.py`, with no default — the app fails to start without it set, exactly like `admin_token` today. The gate is allow-list, not block-list: it checks `settings.environment == "development"`, so an unset, misconfigured, or unknown value refuses by default rather than accidentally passing. This replaces the earlier idea of sniffing `DATABASE_URL` (too fragile — a dev DB hosted anywhere else, or a prod DB matching a dev-like host pattern, would break the gate silently). — **Reversibility:** costly — every deployed environment (dev, staging if any, and the DO production app) must have `ENVIRONMENT` set before this ships, or the app won't boot; rolling this out requires coordinating env-var config across all deployment targets first.
- **D-07:** A handler-level check alone is not enough — this capability must not be *present* in a production deployment, not just refuse when called. Both the backend route and the frontend control are conditionally registered/rendered based on `environment`, not just checked inside the handler body:
  - **Backend:** the reset endpoint's router is only mounted on the FastAPI app (in `api/main.py`, alongside the existing `app.include_router(...)` calls) when `settings.environment == "development"`. In production it is genuinely absent — a request to it 404s, it is not merely refused by a 403.
  - **Frontend:** the new dev-tools section on `/admin` (D-06) is only rendered when the environment is development. Per Architecture Rule 2, this must be checked server-side (a `+page.server.ts`/`+layout.server.ts` load function reading a server-only env var — never exposed as `PUBLIC_`) and the section omitted from the response entirely for production, not hidden client-side with CSS/JS.
  - Same codebase, no separate build artifact for prod vs dev — the gate is evaluated at app-startup/request-time based on the `environment` setting, consistent with D-02. — **Reversibility:** reversible — purely additive gating logic around D-02/D-06; removing it later just means the route/section become unconditional again.

**State realization for the 3 variety fixtures**
- **D-03:** Drive the DRAFT and Published target fixtures to their end states through the real service functions — the same resolve-completion path `api/services/admin_jobs.py` uses to move PIPELINE→DRAFT, and `admin_arguments.py::publish_argument` for DRAFT→PUBLISHED — never direct column writes. This guarantees `ArgumentStatusLog` rows, `resolved_at`/`published_at` timestamps, and any other side effects stay consistent with what a real operator action would produce, with no drift as the service layer evolves.
- **D-04 (Claude's discretion, user deferred):** What distinguishes "Mid-pipeline" (conversation 22372) from the generic freshly-imported default (status=PIPELINE, AdminJob PAUSED/RESOLVE — which is also where the Complexity fixture, 15169, stays) is left to Claude/planner judgment. Recommended default absent a stronger reason: flip the AdminJob to RUNNING instead of PAUSED — the simplest change that's still genuinely distinguishable, with no participant-level resolve work required. The heavier alternative (partially resolving some ArgumentParticipant rows, leaving others untouched) was raised as more useful for Phase 44's Resolve Table Rework testing but more implementation effort; only switch to it if research/planning finds a concrete reason the simple version won't serve Phase 44.

**Confirmation UX & placement**
- **D-05:** Confirmation is a simple Yes/No dialog (not type-to-confirm) — Confirm / Cancel buttons, with the dialog stating exactly what will be wiped before the action runs (per DEVTOOL-01/success criterion 3).
- **D-06:** The "Reset to Fixture" control lives as a new section on the existing `/admin` dashboard (the current stat-card landing page at `app/src/routes/admin/+page.svelte`) rather than a new dedicated route — clearly marked as a dev-tools/destructive section, not a new page.

### Claude's Discretion
- Exact "Mid-pipeline" mechanics (D-04 above) — user explicitly said "you decide."
- Full table list included in the TRUNCATE (D-01) — the roadmap names arguments/utterances/people/court_tenures/argument_participants explicitly; cases, case_arguments, pipeline_runs, and admin_jobs also need clearing since the reseed recreates them fresh via import-convokit, but the exact statement ordering/grouping is an implementation detail for planning, not a user decision.
- Whether the new `environment` setting is a free-form string or a constrained enum — D-02 only locks the allow-list comparison behavior (`== "development"`), not the Python type.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-------------------|
| DEVTOOL-01 | Operator can trigger a "Reset to Fixture" action from the admin panel that wipes all arguments, utterances, people, court_tenures, and argument_participants, then reseeds exactly the CORPUS-12 fixture set (all 4 arguments) plus their associated people | Proven `TRUNCATE ... CASCADE` statement (Code Examples), in-process `run_import_convokit` call pattern (Pattern 2), two-step confirm UI pattern (Pattern 4, matches 43-UI-SPEC.md), and the exact `approve_job`/`publish_argument`/AdminJob-flip sequence for state realization (Architecture Patterns, Pitfall 3) |
| DEVTOOL-02 | The reset action is hard-gated so it cannot execute against a real/production environment (e.g. explicit environment check), given its fully destructive nature | New required fail-fast `environment` setting mirroring `admin_token` (Pitfall 5), separate conditionally-mounted router (Pattern 1 — the key structural finding of this research), server-only SvelteKit env var gate (Pattern 3), and the module-re-import test technique for proving route absence (Code Examples, Validation Architecture) |
</phase_requirements>

## Summary

Phase 43 is entirely an internal-codebase integration problem, not a new-technology problem — every piece it needs already exists in the repo: a proven `TRUNCATE ... CASCADE` statement over the exact table set (`pipeline/tests/conftest.py`), a callable async entry point for corpus import that never needs the CLI (`pipeline.commands.import_convokit.run_import_convokit`), the two state-transition service functions D-03 calls for (`approve_job`, `publish_argument`), a proven fail-fast-required-setting pattern (`admin_token`) to copy for the new `environment` setting, and a proven module-re-import test technique already used to smoke-test `api/main.py` after a settings change. No new third-party packages are needed anywhere in this phase.

The single biggest structural finding that changes how this should be planned: **the existing `/api/admin` router in `api/routers/admin.py` is one flat `APIRouter` mounted once in `api/main.py` and carries every admin endpoint** (arguments, people, jobs, dashboard). D-07 requires the reset endpoint's router to be *absent* in production — that is impossible to satisfy by adding a route to the existing router, since gating the whole `admin.router` would also 404 login, people-editing, and every other admin feature in production. The reset endpoint must live in a **new, separate `APIRouter`** (its own file, its own prefix), and only that new router is conditionally included in `api/main.py`.

The second structural finding: Postgres's `TRUNCATE ... CASCADE` **transitively reaches every table with an FK pointing at any table in the statement**, not just the tables named in it. CONTEXT.md's D-01 table list (arguments, utterances, people, court_tenures, argument_participants, cases, case_arguments, pipeline_runs, admin_jobs) omits three real tables that also FK-reference this table set — `case_appearances` (→ cases, people, roles), `speaker_alias` (→ people), and `argument_status_log` (→ arguments) — but none of these needs to be listed explicitly: `CASCADE` reaches all three automatically the moment `people`, `cases`, and `arguments` are in the `TRUNCATE` statement. `roles` is correctly never touched, because nothing in the wipe set has an FK that `roles` needs to cascade through (roles is upstream of `people`/`case_appearances`, not downstream).

**Primary recommendation:** Add a new `api/routers/admin_dev.py` (own `APIRouter(prefix="/api/admin/dev", dependencies=[Depends(verify_admin_token)])`) conditionally included in `api/main.py` only when `settings.environment == "development"`; back it with `api/services/admin_dev.py` that runs one `TRUNCATE ... CASCADE` (root tables: `arguments, cases, people, court_tenures`, plus explicitly listing `utterances, argument_participants, case_arguments, pipeline_runs, admin_jobs` for readability), then calls `pipeline.commands.import_convokit.run_import_convokit` in-process (via `SimpleNamespace(conversation_id=..., corpus_dir=None)`, no subprocess) once per fixture conversation ID, then calls `admin_jobs.approve_job` and `admin_arguments.publish_argument` on the two state-variety fixtures that need to move further than the freshly-imported PIPELINE/PAUSED default.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Full-DB TRUNCATE | API / Backend (new service module) | Database | Destructive SQL must run inside a backend-owned transaction, never from the frontend or a shell script the operator runs by hand |
| Reseed via corpus importer | API / Backend (calls into `pipeline/` in-process) | — | `pipeline.commands.import_convokit.run_import_convokit` is an importable async function already used in-process elsewhere in the codebase (`admin_jobs.py` already imports from this module) — no new subprocess boundary needed |
| State realization (DRAFT/PUBLISHED/Mid-pipeline) | API / Backend (existing services) | — | `approve_job`/`publish_argument` already own this logic; the reset service is a caller, not a reimplementer |
| Environment gate — route existence | API / Backend | — | Router inclusion is decided once at FastAPI app construction (`api/main.py`), before any request is routed |
| Environment gate — control visibility | Frontend Server (SSR) | — | `+page.server.ts` load function reads a server-only SvelteKit env var and passes a boolean into page data; `+page.svelte` conditionally renders based on that boolean (never CSS-hidden) |
| Confirm/Cancel + Running/Success/Error UI | Browser / Client (Svelte component state) | Frontend Server (form action) | Two-step inline confirm is local `$state`; the actual destructive call is a SvelteKit form action (`use:enhance`) that proxies to the backend, matching the two existing "Danger Zone" delete precedents exactly |

## Standard Stack

### Core
No new libraries. This phase is 100% composition of existing dependencies already declared in `requirements.txt` [VERIFIED: requirements.txt] — `fastapi[standard]>=0.115`, `sqlalchemy>=2.0`, `asyncpg>=0.29`, `pydantic-settings>=2.0` — and existing SvelteKit primitives (`$env/static/private`, `$app/forms`, `$app/navigation`) already used elsewhere in `app/src/routes/admin/`.

### Supporting
| Component | Purpose | Why Standard (already in this codebase) |
|-----------|---------|------------------------------------------|
| `sqlalchemy.text()` + raw `TRUNCATE ... CASCADE` | Full-wipe DDL-adjacent statement | Already the proven pattern in `pipeline/tests/conftest.py`'s `clean_db`/`_reset_test_db` fixtures — same table family, same CASCADE keyword [VERIFIED: pipeline/tests/conftest.py] |
| `pipeline.commands.import_convokit.run_import_convokit` | Reseed path | Already an importable, awaitable async function (not CLI-only) — `api/services/admin_jobs.py` already imports `PIPELINE_RUN_STRATEGY` from this same module, proving cross-import between `api/` and `pipeline/` is an established pattern [VERIFIED: api/services/admin_jobs.py, pipeline/commands/import_convokit.py] |
| `types.SimpleNamespace` | Fake CLI-args object for `run_import_convokit` | `run_import_convokit`/`_resolve_scoped_conversation`/`_resolve_corpus_dir` all read `args` via `getattr(args, "attr", None)`, never `args.attr` directly, specifically so non-CLI callers can pass a minimal object [VERIFIED: pipeline/commands/import_convokit.py lines 221, 257] |
| `httpx.AsyncClient` + `ASGITransport` | Test client for the new dev router | Already the established pattern in every `api/tests/test_admin_*_routes.py` file [VERIFIED: api/tests/test_admin_dashboard_routes.py] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process `run_import_convokit` call | `subprocess.Popen(["python", "-m", "pipeline", "import-convokit", "--conversation-id", ...])` via `api/services/pipeline_spawn.py`'s existing helper | Rejected: `spawn_pipeline_step` is explicitly fire-and-forget (never awaits completion) — wrong shape for a synchronous request the UI-SPEC's "Running" state expects to block on; would also require 4 sequential subprocess launches plus polling, adding real complexity for zero benefit since the function is already safely importable |
| Explicit per-table `DELETE` cascade (like `scripts/delete_fixture_argument.py`) | Loop the fixture-delete script 4×, or extend it to cover court_tenures/people | Rejected by CONTEXT D-01 already — this is a full wipe, not a scoped delete; TRUNCATE has no FK-order problem to solve, `DELETE` does |
| Fetching `environment` from FastAPI at SvelteKit request time (new lightweight endpoint) | A new unauthenticated `GET /api/environment` the load function calls | Rejected: adds a network round-trip and a new failure mode to a page whose load function already degrades gracefully on partial backend failure (UI-SPEC/dashboard precedent) for something that's just a static per-deployment string — a second static env var (matching `FASTAPI_BASE_URL`/`ADMIN_TOKEN` precedent) is simpler and has no runtime dependency on the backend being reachable |

**Installation:** none — no new packages.

## Package Legitimacy Audit

Not applicable — this phase introduces zero new external dependencies. Every module used (`sqlalchemy`, `fastapi`, `pydantic-settings`, `httpx`) is already installed and already imported elsewhere in this codebase.

## Architecture Patterns

### System Architecture Diagram

```
Operator clicks "Reset to Fixture" on /admin
        │
        ▼
+page.svelte (Confirming state) ──Confirm reset──▶ <form action="?/resetToFixture"> (use:enhance)
        │                                                     │
        │                                                     ▼
        │                                    +page.server.ts `actions.resetToFixture`
        │                                                     │  fetch(FASTAPI_BASE_URL + "/api/admin/dev/reset-to-fixture",
        │                                                     │        { headers: { X-Admin-Token } })
        │                                                     ▼
        │                                    api/routers/admin_dev.py  (only mounted if
        │                                    settings.environment == "development" — 404 otherwise)
        │                                                     │
        │                                                     ▼
        │                                    api/services/admin_dev.py :: reset_to_fixture(db)
        │                                                     │
        │                                    ┌────────────────┼─────────────────────────────┐
        │                                    ▼                ▼                             ▼
        │                       1. TRUNCATE arguments,   2. for each of 4 fixture   3. approve_job() on
        │                          cases, people,           conversation_ids:          the DRAFT-target
        │                          court_tenures, ...           run_import_convokit(      fixture's AdminJob;
        │                          CASCADE  (own db          SimpleNamespace(            publish_argument()
        │                          session/commit)           conversation_id=id))        on the Published-
        │                                                     (pipeline's own              target argument;
        │                                                     get_session() per            direct AdminJob
        │                                                     conversation)                 .status=RUNNING
        │                                                                                    flip on the
        │                                                                                    Mid-pipeline
        │                                                                                    fixture's job
        │                                                     │
        ◀─────────────────────── JSON { fixtures: [...] } ────┘
        ▼
Success state renders list; on mount, invalidateAll() re-runs
+page.server.ts `load` → refreshes stat cards / Needs Attention
```

### Recommended Project Structure
```
api/
├── core/config.py            # + `environment: str` field (D-02)
├── routers/
│   ├── admin.py               # UNCHANGED — existing flat admin router
│   └── admin_dev.py           # NEW — separate router, conditionally mounted
├── schemas/
│   └── admin_dev.py           # NEW — ResetToFixtureResponse (fixtures: list[{conversation_id, case_name, role}])
├── services/
│   └── admin_dev.py           # NEW — reset_to_fixture(db) orchestration
└── main.py                    # + conditional include_router for admin_dev.router

app/src/routes/admin/
├── +page.server.ts            # + ENVIRONMENT read, + `resetToFixture` action
└── +page.svelte               # + "Dev Tools" section (gated on data.isDevelopment)
```

### Pattern 1: Separate router for a conditionally-mounted endpoint
**What:** A brand-new `APIRouter` in its own file, never added to the existing `admin.router`.
**When to use:** Any time a subset of admin functionality must be structurally absent (not just auth-refused) in some environments, while the rest of `/api/admin` stays mounted everywhere.
**Example:**
```python
# api/routers/admin_dev.py — Source: mirrors api/routers/admin.py's own router construction
from fastapi import APIRouter, Depends
from api.core.config import settings
from api.routers.admin import verify_admin_token  # reuse, don't duplicate
from api.services import admin_dev as admin_dev_service

router = APIRouter(
    prefix="/api/admin/dev",
    tags=["admin-dev"],
    dependencies=[Depends(verify_admin_token)],  # still requires the operator token
)

@router.post("/reset-to-fixture")
async def reset_to_fixture(db: AsyncSession = Depends(get_db)):
    return await admin_dev_service.reset_to_fixture(db)
```
```python
# api/main.py
from api.core.config import settings
from api.routers import admin_dev as admin_dev_router

if settings.environment == "development":
    app.include_router(admin_dev_router.router)
```

### Pattern 2: Calling a pipeline command function in-process (no subprocess)
**What:** `run_import_convokit` reads every CLI-only attribute via `getattr(args, "x", None)`, never `args.x` — this is intentional so a non-argparse caller can pass a minimal stand-in object.
**When to use:** Any backend code that needs to invoke a `pipeline/commands/*.py` entry point without shelling out.
**Example:**
```python
# Source: pipeline/commands/import_convokit.py — _resolve_scoped_conversation (line 221),
# _resolve_corpus_dir (line 257), both already use getattr() defensively.
from types import SimpleNamespace
from pipeline.commands.import_convokit import run_import_convokit

for conversation_id in FIXTURE_CONVERSATION_IDS:  # ["15169", "13015", "18897", "22372"]
    await run_import_convokit(SimpleNamespace(conversation_id=conversation_id, corpus_dir=None))
```
Each call opens its own `pipeline.db.get_session()` (a separate engine/pool from FastAPI's `AsyncSessionLocal`, but the same Postgres database via the same `DATABASE_URL`) and commits per-conversation — already proven safe since `admin_jobs.py` already imports from this same module today [VERIFIED: api/services/admin_jobs.py line 51].

### Pattern 3: Server-only environment flag threaded into page data (D-07 frontend gate)
**What:** SvelteKit's `$env/static/private` is the existing mechanism for server-only config (`ADMIN_TOKEN`, `FASTAPI_BASE_URL` — both read this way in every `+page.server.ts` under `/admin`) [VERIFIED: app/src/routes/admin/+page.server.ts line 4]. No `+layout.server.ts` exists anywhere under `/admin` today, and D-06 only needs the section on the dashboard page itself — so the simplest correct fix is reading the new var directly in the existing `admin/+page.server.ts`, not adding a new layout server file.
**Example:**
```typescript
// app/src/routes/admin/+page.server.ts
import { ADMIN_TOKEN, ENVIRONMENT, FASTAPI_BASE_URL } from '$env/static/private';
// ...
return { /* existing stat fields */, isDevelopment: ENVIRONMENT === 'development' };
```
```svelte
<!-- app/src/routes/admin/+page.svelte -->
{#if data.isDevelopment}
  <section><!-- Dev Tools section, per 43-UI-SPEC.md --></section>
{/if}
```
This requires a **second, independent** `ENVIRONMENT` value in `app/.env` (SvelteKit's own env file — confirmed separate from the repo-root `.env` the Python API reads [VERIFIED: app/.env exists as a distinct file from the project-root .env]). The two are not shared at runtime; both must be set and kept in sync manually (see Pitfall 4).

### Pattern 4: Two-step inline confirm + form action (D-05/D-06, matches existing precedent exactly)
**What:** No modal/dialog library exists anywhere in this codebase — every destructive action uses a hand-rolled `deleteConfirming`-style boolean plus a SvelteKit form action with `use:enhance`.
**When to use:** This exact shape, reused for "Reset to Fixture" per 43-UI-SPEC.md's Interaction & State Contract.
**Example:**
```svelte
<!-- Source: app/src/routes/admin/arguments/[id]/+page.svelte lines 615-665 (Danger Zone precedent) -->
{#if resetConfirming}
  <div style="display: flex; gap: 8px;">
    <form method="POST" action="?/resetToFixture" style="flex: 1;"
      use:enhance={() => {
        resetRunning = true;
        return async ({ result }) => {
          resetRunning = false;
          if (result.type === 'success') { resetResult = result.data; await invalidateAll(); }
        };
      }}>
      <button type="submit" disabled={resetRunning}>Confirm reset</button>
    </form>
    <button type="button" onclick={() => resetConfirming = false}>Cancel</button>
  </div>
{:else}
  <button type="button" onclick={() => resetConfirming = true}>Reset to Fixture</button>
{/if}
```

### Anti-Patterns to Avoid
- **Adding the reset route to `api/routers/admin.py`'s existing router:** Would force gating (or splitting) the *entire* `/api/admin` prefix in production, breaking every other admin feature. Always use a separate router file for anything that must be structurally absent per-environment.
- **Reimplementing DRAFT/PUBLISHED state writes as direct column updates:** D-03 already forbids this — always call `approve_job`/`publish_argument` so `ArgumentStatusLog` rows and timestamps stay correct. (The Mid-pipeline fixture's `AdminJob.status = RUNNING` flip is the one narrow exception — see Pitfall 3.)
- **Treating CONTEXT.md's 9-table D-01 list as the literal, exhaustive `TRUNCATE` argument list without `CASCADE`:** would raise a live FK violation the first time Postgres hits `case_appearances`, `speaker_alias`, or `argument_status_log` referencing a row being removed. `CASCADE` is not optional here.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FK-safe full-table wipe | A manually-ordered sequence of `DELETE FROM ...` statements | `TRUNCATE TABLE ... CASCADE` (single statement, order-independent) | Already proven in `pipeline/tests/conftest.py`; TRUNCATE sidesteps the entire FK-ordering problem CONTEXT.md D-01 already flags as unnecessary here |
| Reseeding corpus data | A bespoke seeder script duplicating `_import_conversation`'s Case/Argument/Participant/Utterance logic | `pipeline.commands.import_convokit.run_import_convokit`, called in-process | This is the explicit point of D-CONTEXT's phase boundary #2 — Phase 42's importer fixes must flow through automatically |
| PIPELINE→DRAFT / DRAFT→PUBLISHED transitions | Direct `UPDATE arguments SET status = ...` | `admin_jobs.approve_job(db, job_id)` / `admin_arguments.publish_argument(db, argument_id)` | Both already write the matching `ArgumentStatusLog` row and stamp `resolved_at`/`published_at`; a raw UPDATE would silently skip the audit trail |
| Confirm-dialog component | A new modal/dialog library or component | The existing hand-rolled `xConfirming` boolean + two-button row pattern | Zero dialog/modal libraries exist in this codebase; 43-UI-SPEC.md explicitly locks onto this precedent (bits-ui's `Popover` is present but unused for this section) |

**Key insight:** Every piece of this phase's "hard part" already has a proven, working implementation somewhere in this exact codebase. The research risk here isn't "what library solves this" — it's "which existing function/pattern already solves this, and where exactly does it live."

## Runtime State Inventory

Not applicable in the standard rename/refactor/migration sense — Phase 43 does not rename or migrate anything. However, since its entire purpose is stored-state manipulation, the equivalent audit is: **what stored state exists in tables outside CONTEXT.md's named list that a `TRUNCATE ... CASCADE` over the named list will still reach, and what state exists that will NOT be touched at all.**

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Tables not named in D-01 but reached anyway via `CASCADE` | `case_appearances` (FK→cases, people, roles), `speaker_alias` (FK→people), `argument_status_log` (FK→arguments) [VERIFIED: alembic/versions/0001_initial_schema.py, 0002_add_speaker_alias.py, 0012_unpublished_enum_and_status_log.py] | No code change needed — `CASCADE` on the D-01 root tables (`people`, `cases`, `arguments`) already truncates these transitively. Document this in the service module's own comment so a future reader isn't confused by an apparently-incomplete table list. |
| Tables correctly left untouched | `roles` — nothing in the wipe set has an FK `roles` must cascade through (roles is the parent of `people.role_id`/`case_appearances.role_id`, not a child) | None — matches CONTEXT.md D-01's explicit exclusion of lookup tables. |
| Pre-seeded data destroyed with no re-seed step | `speaker_alias` rows created by `pipeline/commands/seed_aliases.py` (Justice label variants, seeded independently of any argument import) are wiped by CASCADE and **not** restored by this reset (`import_convokit.py`'s `_resolve_person` never reads/writes `speaker_alias` — it resolves via `oyez_speaker_id`/`full_name` directly) [VERIFIED: pipeline/commands/import_convokit.py `_resolve_person`, pipeline/commands/admin_jobs.py `resolve_job`] | No action required for this phase's scope (corpus reseed doesn't need `speaker_alias`), but flag in the plan/PR description so nobody is surprised that a later PDF-pipeline resolve step on a brand-new non-corpus argument starts from an empty alias table after a reset. Out of scope to re-run `seed_aliases.py` automatically. |
| Alembic migration state | Repo is "believed to be at alembic head `0024`" per STATE.md; not independently re-verified this session (no live DB connection available in this research pass) | Plan should include `alembic current` as a pre-flight check before relying on schema shape, per STATE.md's existing standing note. |

**Nothing found in category:** No OS-registered state, no secrets/env-var renames, and no build-artifact staleness apply to this phase — it neither renames anything nor changes any package/script name.

## Common Pitfalls

### Pitfall 1: Treating the reset as one atomic transaction
**What goes wrong:** A developer assumes the whole reset (TRUNCATE + 4 reseeds + 2 state transitions) rolls back cleanly on any failure.
**Why it happens:** The TRUNCATE runs on FastAPI's own `AsyncSessionLocal`-backed session; each `run_import_convokit` call opens and commits its own session via `pipeline.db.get_session()` (a *separate* engine/pool, same database); `approve_job`/`publish_argument` commit on yet another session reference. These are three independently-committing units, not one transaction.
**How to avoid:** Design for this explicitly — this is exactly what 43-UI-SPEC.md's "mid-reset failure" error copy already assumes ("the database may be in an inconsistent state"). Don't attempt to wrap everything in a single external transaction; instead make the failure mode visible and recoverable by re-running the whole reset (TRUNCATE is idempotent-safe to re-invoke from any partial state).
**Warning signs:** A plan task that says "wrap the whole reset in `async with db.begin():`" spanning across the `run_import_convokit` calls — that session boundary doesn't extend into pipeline's own engine and won't do what it looks like it does.

### Pitfall 2: Forgetting `CASCADE` (or naming an incomplete table list) on the TRUNCATE
**What goes wrong:** `TRUNCATE TABLE arguments, cases, people, court_tenures, ...` without `CASCADE` raises `cannot truncate a table referenced in a foreign key constraint` the first time Postgres notices `case_appearances`/`speaker_alias`/`argument_status_log`/`admin_jobs` still hold rows referencing the tables being truncated.
**Why it happens:** CONTEXT.md D-01's named table list (copied from the roadmap) is not actually exhaustive over the live schema — it predates a careful FK-graph walk.
**How to avoid:** Always include `CASCADE`; treat the explicit table list as documentation/readability, not as the mechanism that guarantees FK safety.
**Warning signs:** A `ForeignKeyViolation`/`ForeignKeyError` naming any of `case_appearances`, `speaker_alias`, or `argument_status_log` during manual testing of the reset endpoint.

### Pitfall 3: Reading D-03's "never direct column writes" as covering the Mid-pipeline fixture's AdminJob flip
**What goes wrong:** Someone tries to find or invent a service function for "pause a resolve job back to running," when D-03 is scoped to *Argument* status transitions (DRAFT/PUBLISHED), not to the synthetic `AdminJob.status` value D-04 recommends flipping to distinguish the Mid-pipeline fixture.
**Why it happens:** D-03 and D-04 sit next to each other in CONTEXT.md and are easy to conflate.
**How to avoid:** `ArgumentStatusLog` only ever logs `Argument.status` changes [VERIFIED: api/models/models.py `ArgumentStatusLog`] — there is no equivalent audit table for `AdminJob.status`, and no existing service function performs a PAUSED→RUNNING flip for this reason (the real step-advance guards `try_advance_ingest_to_parse`/`try_advance_parse_to_resolve` handle different state pairs entirely). A direct `UPDATE admin_jobs SET status = 'running' WHERE id = ...` for the one Mid-pipeline fixture's job is the correct, D-03-consistent choice — it is not a "the same principle should apply here too" violation.
**Warning signs:** A plan task trying to reuse `try_advance_parse_to_resolve` (wrong step pair) or blocked on "no service function exists for this."

### Pitfall 4: Two independent `ENVIRONMENT` values drifting out of sync
**What goes wrong:** The Python API's `.env` gets `ENVIRONMENT=development` but `app/.env` (SvelteKit's own, separate env file) does not, or vice versa — the dev-tools section either shows in the UI while the backend 404s it (confusing "the button doesn't work" bug report), or the backend allows it while the UI never shows the control (harmless, but the operator can't find the feature).
**Why it happens:** `app/.env` and the project-root `.env` are two files with no shared source; there is no existing mechanism in this codebase that keeps any variable in sync between them (each of `ADMIN_TOKEN`/`FASTAPI_BASE_URL` is *also* independently duplicated today, so this isn't a new problem, but it's a new instance of it).
**How to avoid:** The plan's setup/checkpoint steps must explicitly instruct adding `ENVIRONMENT=development` to *both* files, and the plan's manual-verification step should check both.
**Warning signs:** UAT step "click Reset to Fixture" returns 404 despite the button being visible, or the button never appears despite the backend endpoint working via curl.

### Pitfall 5: Adding a new required `Settings` field breaks every test/local run that doesn't already have it
**What goes wrong:** `environment: str` with no default, like `admin_token`, means `Settings()` raises a `pydantic.ValidationError` at import time (`api/core/config.py` line 77 constructs `settings = Settings()` at module scope) — this breaks pytest collection, any script that imports `api.core.config`, and local `uvicorn` startup, everywhere `ENVIRONMENT` isn't already set.
**Why it happens:** `admin_token` already has this exact failure mode, and the fix is the same: the developer's local `.env` and CI-equivalent test setup must both carry the var. The existing `test_api_main_imports_without_error` test already demonstrates the correct workaround for a **test-local** override (`os.environ.setdefault("ADMIN_TOKEN", "test-smoke-import")` before a forced re-import) [VERIFIED: tests/test_admin_router.py lines 202-229].
**How to avoid:** Add `ENVIRONMENT=development` to the project-root `.env` as a required setup step (not just to code); if a test needs to exercise the "not development" 404 path, follow the exact `test_api_main_imports_without_error` pattern — set `os.environ["ENVIRONMENT"]` to a non-development value, delete cached `api.*` modules from `sys.modules`, re-import `api.main`, assert the route now 404s (or is absent from `app.routes`).
**Warning signs:** Every existing test in the suite suddenly failing with a `pydantic_settings` validation error immediately after this phase's config change lands — that means `.env` wasn't updated, not that the code is wrong.

### Pitfall 6: Assuming `data/corpus/` is a given
**What goes wrong:** The reset silently fails with `FileNotFoundError` if `data/corpus/` (the gitignored, operator-populated directory of raw ConvoKit files) is missing or incomplete on the machine running the reset.
**Why it happens:** `_resolve_corpus_dir` requires the directory to exist and `run_import_convokit` requires all four raw files (`conversations.json`, `cases.jsonl`, `speakers.json`, `utterances.jsonl`) to be present before any import starts [VERIFIED: pipeline/commands/import_convokit.py lines 1228-1236].
**How to avoid:** Confirmed present on this development machine today (see Environment Availability below), but the plan/error copy should surface a clear message distinguishing "corpus files missing" from a generic mid-reset failure, since this is a pre-flight condition, not a partial-completion state.
**Warning signs:** The Running state hangs briefly then immediately errors before any TRUNCATE side effect is even visible (in which case there was no partial-failure to clean up at all — an important distinction from Pitfall 1's scenario, worth a distinct error message if the plan wants to be precise, though the UI-SPEC's existing generic "mid-reset failure" copy is an acceptable minimum).

## Code Examples

### The exact proven TRUNCATE statement to adapt (Environment Availability: verified working today)
```python
# Source: pipeline/tests/conftest.py `clean_db`/`_reset_test_db` fixtures — same table
# family Phase 43 needs, already exercised routinely by the test suite against
# scotus_test. Phase 43's version adds admin_jobs explicitly (CONTEXT D-01) and
# drops roles (must NOT be wiped, per D-01) and case_appearances (reached via
# CASCADE anyway, but harmless to also name explicitly for readability).
await db.execute(
    text(
        """
        TRUNCATE TABLE
            utterances,
            pipeline_runs,
            case_arguments,
            argument_participants,
            arguments,
            cases,
            court_tenures,
            people,
            admin_jobs
        CASCADE
        """
    )
)
await db.commit()
```
Note: `case_appearances`, `speaker_alias`, and `argument_status_log` are deliberately **not** named — `CASCADE` reaches them because each has an FK into `people`, `people`, and `arguments` respectively. Naming them too is harmless (TRUNCATE accepts a table already implied by CASCADE without erroring) if the plan prefers maximal explicitness.

### The exact fixture set to reseed (from `.planning/FIXTURES.md`, CONFIRMED status)
```python
# api/services/admin_dev.py — module-level constant, single source of truth
# for both the reseed loop and the success-response case names.
FIXTURE_SET = [
    {"conversation_id": "15169", "case_name": "Baltimore & Ohio Railroad Company v. United States", "role": "Complexity"},
    {"conversation_id": "13015", "case_name": "Archawski v. Hanioti", "role": "Draft"},
    {"conversation_id": "18897", "case_name": "Anderson v. Liberty Lobby, Inc.", "role": "Published"},
    {"conversation_id": "22372", "case_name": "Abbott v. United States", "role": "Mid-pipeline"},
]
```

### Module-re-import test technique for the environment gate (already proven in this repo)
```python
# Source: tests/test_admin_router.py::test_api_main_imports_without_error (lines 202-229)
# Adaptable directly to prove admin_dev.router is absent when environment != "development".
import importlib, sys, os

os.environ["ENVIRONMENT"] = "production"
for mod in list(sys.modules.keys()):
    if mod.startswith("api."):
        del sys.modules[mod]
main = importlib.import_module("api.main")
assert not any(r.path.startswith("/api/admin/dev") for r in main.app.routes)
```

## State of the Art

Not applicable in the usual "framework version drifted" sense — this phase uses only stable, already-pinned internal patterns. No deprecated approach is being replaced; there is no prior "Reset to Fixture" implementation to supersede.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The repo's dev database is at Alembic head `0024`, per STATE.md's own note ("believed to be", not independently re-verified with a live `alembic current` this session, since this research pass had no DB connection available) | Runtime State Inventory | If actually behind, the TRUNCATE table list could be missing/extra columns relative to what the plan assumes — low risk since TRUNCATE doesn't touch columns, only rows, but the plan should still run `alembic current` as a pre-flight step per STATE.md's own standing guidance |
| A2 | `app/.env` and the project-root `.env` are genuinely independent at runtime (no build step merges them) | Pattern 3, Pitfall 4 | If some SvelteKit/adapter config actually reads the root `.env` too, the "two independent values" pitfall is overstated — worth a 30-second sanity check at plan/implementation time (e.g. checking `svelte.config.js`/`vite.config.ts` for any explicit envDir override), since this research pass did not have permission to read `app/.env.example`'s exact contents |

## Open Questions

1. **Should the TRUNCATE explicitly list `case_appearances`, `speaker_alias`, and `argument_status_log`, or rely purely on CASCADE?**
   - What we know: CASCADE alone is functionally sufficient and correct (verified via the FK graph derived from every `alembic/versions/*.py` migration).
   - What's unclear: Whether the plan should optimize for "reads as an exhaustive, self-documenting list" (name all 12 tables) vs. "reads as the true minimal root set with a comment explaining CASCADE's reach" (name only `arguments, cases, people, court_tenures` + the join/log tables for clarity).
   - Recommendation: Name all tables CONTEXT.md's D-01 already calls out (9 tables) explicitly in the `TRUNCATE` statement for readability/audit-ability, keep `CASCADE`, and add one code comment naming the 3 additionally-reached tables so a future reader isn't confused about why the wipe reaches further than the literal list. This is a documentation choice, not a correctness question — either way, `CASCADE` makes the outcome identical.

2. **Does `run_import_convokit`'s per-conversation resilience (catches and logs, doesn't raise, on a per-conversation basis) mean a fixture import "failure" is silently swallowed rather than surfaced as the UI-SPEC's mid-reset error state?**
   - What we know: `run_import_convokit`'s outer loop catches `Exception` per conversation and increments `conversations_errored`, printing a warning rather than raising [VERIFIED: pipeline/commands/import_convokit.py lines 1299-1306].
   - What's unclear: Whether the reset service needs to inspect the returned counters (if it captured them) to detect a same-request "fixture didn't actually import" failure that wouldn't otherwise raise an exception the FastAPI handler could catch — `run_import_convokit` currently returns `None`, it doesn't return the counters dict to its caller.
   - Recommendation: The reset service should verify each fixture's `Argument` row actually exists (by `oyez_transcript_id`) after calling `run_import_convokit`, and treat "argument not found post-import" as a mid-reset failure requiring the UI-SPEC's error state — don't rely solely on an exception propagating.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `data/corpus/` raw ConvoKit files (`conversations.json`, `cases.jsonl`, `speakers.json`, `utterances.jsonl`) | Reseed step (`run_import_convokit`) | ✓ | present, last modified 2026-07-09 | none — this is a hard precondition; the reset cannot function without it on the machine it runs on |
| PostgreSQL (dev DB via `DATABASE_URL`) | TRUNCATE + reseed | Assumed ✓ (not independently connected this research pass) | Alembic head believed `0024` per STATE.md | — |
| Windows `.venv` (`.venv/Scripts/python.exe`) | Running the API/pipeline locally via WSL interop, per project memory note | ✓ | present | — |

**Missing dependencies with no fallback:** none identified this pass.

**Missing dependencies with fallback:** none identified this pass.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (`asyncio_mode = auto`) [VERIFIED: pytest.ini] |
| Config file | `pytest.ini` (project root) |
| Quick run command | `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py -x` (new file; matches `test_command` in `.planning/config.json`) |
| Full suite command | `./.venv/Scripts/python.exe -m pytest` (per `.planning/config.json`'s `test_command`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEVTOOL-01 | Reset wipes all named tables and reseeds exactly the 4 fixtures + their people | integration | `pytest api/tests/test_admin_dev_routes.py::test_reset_wipes_and_reseeds_fixtures -x` (against `scotus_test` via `TEST_DATABASE_URL`) | ❌ Wave 0 |
| DEVTOOL-01 | Draft/Published/Mid-pipeline fixtures land in their labeled state after reset | integration | `pytest api/tests/test_admin_dev_routes.py::test_reset_realizes_state_variety -x` | ❌ Wave 0 |
| DEVTOOL-02 | Reset endpoint is absent (404, not 403) when `environment != "development"` | unit (module re-import) | `pytest tests/test_admin_dev_router_gate.py::test_dev_router_absent_outside_development -x` | ❌ Wave 0 |
| DEVTOOL-02 | Dev Tools section is absent from `/admin` HTML response when `environment != "development"` | integration (SvelteKit) | `npm run test -- admin-dev-tools-visibility` (or manual UAT if no frontend test harness exists for `/admin` today — verify at plan time) | ❌ Wave 0 (frontend test harness for `/admin` not yet confirmed to exist) |
| DEVTOOL-01 | Confirm/Cancel two-step dialog states behave per 43-UI-SPEC.md | manual UAT | n/a (visual/interaction) | manual-only |

### Sampling Rate
- **Per task commit:** `./.venv/Scripts/python.exe -m pytest api/tests/test_admin_dev_routes.py -x`
- **Per wave merge:** `./.venv/Scripts/python.exe -m pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`, run against `scotus_test` (never the shared dev DB — Phase 31's `pytest_sessionfinish` row-count guard already enforces this automatically for `people`/`arguments`, and this phase's own tests must set `TEST_DATABASE_URL` for any test that actually calls `reset_to_fixture`).

### Wave 0 Gaps
- [ ] `api/tests/test_admin_dev_routes.py` — new file, covers DEVTOOL-01 (reset behavior) and the auth-still-required check on the new router
- [ ] `tests/test_admin_dev_router_gate.py` — new file (root-level `tests/`, matching where `test_admin_router.py`'s re-import smoke test already lives), covers DEVTOOL-02's route-absence behavior via the module re-import technique
- [ ] Confirm whether a frontend test harness exists for `/admin` pages at all (none found under `app/tests/` for `/admin` specifically during this research pass — verify at plan time before committing to an automated frontend test for the Dev Tools section's visibility gate; manual UAT is an acceptable fallback for DEVTOOL-02's frontend half)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | yes | Existing `verify_admin_token` dependency (HMAC-safe `hmac.compare_digest` header check) — reused unchanged on the new router, not reimplemented |
| V3 Session Management | no (delegated) | The SvelteKit `/admin` session-cookie gate (`hooks.server.ts`) already protects the entire `/admin` subtree before this section's own environment check even runs |
| V4 Access Control | yes | The environment allow-list check (`== "development"`, not a block-list) is itself the primary access-control mechanism for this feature — D-02 already chose the correct fail-closed default over the rejected `DATABASE_URL`-sniffing approach |
| V5 Input Validation | n/a | The reset endpoint takes no operator-supplied input (fixture set is a hardcoded constant, per D-CONTEXT) — there is no injectable surface here beyond the fixed conversation IDs already baked into the code |
| V6 Cryptography | no | Not applicable — no new secrets/crypto introduced |
| V1 Architecture (destructive-action isolation) | yes | Router-level absence (not just handler-level refusal) is the ASVS-aligned defense-in-depth choice already locked by D-07 — a request to a genuinely-unmounted route cannot be probed for its refusal reason the way a 403 could |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Accidental production data loss via misconfigured `ENVIRONMENT` | Tampering / Denial of Service (self-inflicted) | Fail-fast, no-default required setting (D-02) + allow-list comparison (`== "development"`) means any unset/misconfigured/typo'd value refuses by default rather than silently passing |
| Route enumeration revealing a destructive endpoint exists in production | Information Disclosure | Router-level conditional mount (D-07) — the route is genuinely absent (404), not merely 403-refused, from any client probing `/api/admin/dev/*` in production |
| Stale admin session reaching a destructive action | Elevation of Privilege | Existing `verify_admin_token` dependency still gates the new router — the environment gate is additive, never a replacement for existing auth |

## Sources

### Primary (HIGH confidence — direct codebase reads this session)
- `api/models/models.py` — full FK graph for all 13 tables
- `alembic/versions/0001_initial_schema.py`, `0002_add_speaker_alias.py`, `0003_add_admin_jobs.py`, `0012_unpublished_enum_and_status_log.py` — every `ForeignKeyConstraint` in the schema's history
- `pipeline/tests/conftest.py` — proven `TRUNCATE ... CASCADE` statement over this exact table family
- `pipeline/commands/import_convokit.py` — `run_import_convokit`, `_resolve_scoped_conversation`, `_resolve_corpus_dir` (getattr-based args handling)
- `pipeline/__main__.py` — exact `--conversation-id` mutually-exclusive-group argparse wiring
- `api/services/admin_jobs.py` — `approve_job` (PIPELINE→DRAFT), `resolve_job`
- `api/services/admin_arguments.py` — `publish_argument` (DRAFT→PUBLISHED)
- `api/core/config.py` — `admin_token` fail-fast pattern to mirror for `environment`
- `api/main.py` — current single flat-router-inclusion structure
- `api/routers/admin.py` — `verify_admin_token`, single-router-covers-everything structure
- `app/src/routes/admin/+page.server.ts`, `+page.svelte`, `+layout.svelte` — `$env/static/private` precedent, dashboard layout, no existing `+layout.server.ts`
- `app/src/routes/admin/arguments/[id]/+page.svelte` — two-step inline confirm precedent (Danger Zone)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — spinner/StatusBadge precedent
- `tests/conftest.py` — `pytest_sessionfinish` shared-dev-DB row-count guard
- `tests/test_admin_router.py` — module re-import smoke-test technique
- `.planning/FIXTURES.md` — confirmed 4-fixture set (conversation IDs, case names, roles)
- `.planning/phases/43-dev-only-reset-to-fixture/43-UI-SPEC.md` — approved UI contract (already answers most UX-shape questions)
- `.planning/phases/43-dev-only-reset-to-fixture/43-CONTEXT.md` — locked decisions
- `.planning/STATE.md` — Phase 30/31 carry-forward invariants

### Secondary (MEDIUM confidence)
- None — no web/external documentation lookups were needed for this phase; every claim is grounded directly in this repository's own code and prior-phase artifacts.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, every pattern already proven in this exact codebase
- Architecture: HIGH — the separate-router requirement and the CASCADE/FK-graph analysis are both derived directly from reading the actual source files, not inferred
- Pitfalls: HIGH — every pitfall traces to a specific line/file already read this session, not speculation

**Research date:** 2026-07-31
**Valid until:** 30 days (stable internal codebase; only invalidated by an unrelated schema migration adding a new table with an FK into this wipe set, or by a change to the admin router structure)
