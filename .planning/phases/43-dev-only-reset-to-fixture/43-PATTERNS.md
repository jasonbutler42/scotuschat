# Phase 43: Dev-Only Reset to Fixture - Pattern Map

**Mapped:** 2026-07-31
**Files analyzed:** 9 new/modified files
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/core/config.py` (+ `environment: str` field) | config | request-response (startup validation) | `api/core/config.py` `admin_token` field (same file) | exact |
| `api/routers/admin_dev.py` (new) | router/controller | request-response | `api/routers/admin.py` (router construction + auth dependency) | exact |
| `api/services/admin_dev.py` (new) | service | batch (TRUNCATE + reseed loop + state transitions) | `api/services/admin_jobs.py` / `api/services/admin_arguments.py` (service-layer orchestration) | role-match |
| `api/schemas/admin_dev.py` (new) | model (Pydantic schema) | request-response | existing `api/schemas/admin_*.py` response schemas | role-match |
| `api/main.py` (+ conditional include_router) | config/wiring | request-response | `api/main.py` (same file, existing `app.include_router(...)` block) | exact |
| `app/src/routes/admin/+page.server.ts` (+ `isDevelopment`, `resetToFixture` action) | route/server-load | request-response | same file (existing `load` + `actions.logout`), and `admin/arguments/[id]/+page.server.ts` (`actions.updateParticipantSide` fetch-to-backend pattern) | exact |
| `app/src/routes/admin/+page.svelte` (+ Dev Tools section) | component | request-response (form submit) | `admin/arguments/[id]/+page.svelte` Danger Zone section (lines 608-674) | exact |
| `api/tests/test_admin_dev_routes.py` (new) | test | request-response / integration | existing `api/tests/test_admin_dashboard_routes.py` pattern (httpx AsyncClient + ASGITransport) | role-match |
| `tests/test_admin_dev_router_gate.py` (new) | test | unit (module re-import) | `tests/test_admin_router.py::test_api_main_imports_without_error` (lines 202-229) | exact |

## Pattern Assignments

### `api/core/config.py` (config)

**Analog:** same file, `admin_token` field.

**Pattern to copy** (lines 29-33):
```python
# Required — set via ADMIN_TOKEN env var (D-13).
# No default value: app refuses to start without this set (fail-fast, T-05-02).
# Do NOT log or expose this value in any endpoint response.
admin_token: str
```
Add `environment: str` immediately following this same style — no default, plain `str` (per CONTEXT.md discretion note, a constrained enum is optional but not required). Comment should note the allow-list comparison contract (`settings.environment == "development"`) lives in the router-mount check in `api/main.py`, not in this file.

**Pitfall carried over (Pitfall 5 from RESEARCH.md):** `Settings()` is constructed at module scope, so every test/script/uvicorn run that imports `api.core.config` without `ENVIRONMENT` set will now fail pydantic validation — must add `ENVIRONMENT=development` to the project-root `.env` as a setup step, exactly like `ADMIN_TOKEN` already requires.

---

### `api/routers/admin_dev.py` (new router)

**Analog:** `api/routers/admin.py` lines 103-124 (auth dependency + router construction).

**Auth + router construction pattern** (lines 103-124):
```python
async def verify_admin_token(x_admin_token: str = Header(...)) -> None:
    """..."""
    if not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```

For `admin_dev.py`: reuse `verify_admin_token` by importing it from `api.routers.admin` (do not redefine it), construct a **separate** `APIRouter` with its own prefix:
```python
from api.routers.admin import verify_admin_token

router = APIRouter(
    prefix="/api/admin/dev",
    tags=["admin-dev"],
    dependencies=[Depends(verify_admin_token)],
)
```
This is RESEARCH.md's Pattern 1 — the key structural requirement (D-07): a brand-new `APIRouter` in its own file so it can be conditionally mounted without gating the rest of `/api/admin`.

**Route handler shape** — follow the existing route style in `api/routers/admin.py` (docstring stating auth is inherited from the router-level dependency, thin handler delegating to a service function, e.g. lines 463, 483, 505, 595, 620 in that file all show `"""... Auth inherited from router-level verify_admin_token dependency. ..."""` immediately followed by a call into `arguments_service`/`jobs_service`).

---

### `api/services/admin_dev.py` (new service)

**Analogs:** `pipeline/tests/conftest.py` (TRUNCATE statement), `api/services/admin_jobs.py::approve_job` (lines 547-591), `api/services/admin_arguments.py::publish_argument` (lines 569-615).

**TRUNCATE pattern** (`pipeline/tests/conftest.py` lines 110-128 — note this fixture's list truncates `roles` too, which Phase 43 must NOT do per D-01; use it only as the CASCADE/table-family template, not verbatim):
```python
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
Deliberately omit `roles` (D-01 explicitly excludes lookup tables) and `case_appearances`/`speaker_alias`/`argument_status_log` (reached transitively via `CASCADE` — do not list unless the plan prefers maximal explicitness; either way `CASCADE` makes the result identical).

**State-transition reuse pattern — call, never reimplement** (`api/services/admin_jobs.py` lines 547-591 `approve_job`, `api/services/admin_arguments.py` lines 569-615 `publish_argument`):
```python
# approve_job(db, job_id) — PIPELINE → DRAFT
await db.execute(
    update(Argument)
    .where(Argument.id == job.argument_id)
    .values(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
    .execution_options(synchronize_session=False)
)
db.add(ArgumentStatusLog(argument_id=job.argument_id, status=ArgumentStatusEnum.DRAFT))

# publish_argument(db, argument_id) — DRAFT → PUBLISHED
await db.execute(
    update(Argument)
    .where(Argument.id == argument_id)
    .values(status=ArgumentStatusEnum.PUBLISHED, published_at=sqlfunc.now())
    .execution_options(synchronize_session=False)
)
db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.PUBLISHED))
await db.commit()
await db.refresh(argument)  # Phase 31 fix — required after synchronize_session=False updates
```
`api/services/admin_dev.py::reset_to_fixture` calls `jobs_service.approve_job(db, job_id)` for the DRAFT-target fixture and `arguments_service.publish_argument(db, argument_id)` for the Published-target fixture — never a direct `UPDATE argument SET status = ...`. The one exception (D-04/Pitfall 3): the Mid-pipeline fixture's `AdminJob.status = RUNNING` flip has no service function precedent and is a direct column write — that is the correct, D-03-consistent choice (D-03 only covers *Argument* status transitions, not `AdminJob.status`).

**In-process pipeline import call** (`api/services/admin_jobs.py` line 51 shows the existing cross-import precedent):
```python
from pipeline.commands.import_convokit import PIPELINE_RUN_STRATEGY
```
`admin_dev.py` follows this same cross-import precedent to call `run_import_convokit` directly (RESEARCH.md Pattern 2), using `types.SimpleNamespace(conversation_id=..., corpus_dir=None)` as the fake args object — `run_import_convokit` reads all attributes via `getattr(args, "x", None)`, never `args.x`, specifically to support this.

---

### `api/main.py` (conditional router mount)

**Analog:** same file, existing `app.include_router(...)` block (lines 27-30).

**Existing pattern** (lines 1-30):
```python
from api.routers import admin as admin_router
from api.routers import arguments as arguments_router
from api.routers import cases as cases_router
from api.routers import people as people_router

app = FastAPI(...)

app.include_router(arguments_router.router)
app.include_router(cases_router.router)
app.include_router(people_router.router)
app.include_router(admin_router.router)
```

**New pattern to add:**
```python
from api.core.config import settings
from api.routers import admin_dev as admin_dev_router

if settings.environment == "development":
    app.include_router(admin_dev_router.router)
```
Place this after the existing unconditional includes, mirroring their order/style. This is the D-07 "genuinely absent, not merely refused" requirement — a request to `/api/admin/dev/*` in production 404s because the route was never registered, not because a handler returned 403.

---

### `app/src/routes/admin/+page.server.ts` (isDevelopment + resetToFixture action)

**Analog:** same file's existing `load` function (lines 1-173) for the env-var-read pattern, and `admin/arguments/[id]/+page.server.ts` `actions.updateParticipantSide` (lines 156-188) for the fetch-to-backend action pattern.

**Env-var read pattern** (same file, line 4):
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
```
Extend to:
```typescript
import { ADMIN_TOKEN, ENVIRONMENT, FASTAPI_BASE_URL } from '$env/static/private';
// ...
return { ...existingLoadFields, isDevelopment: ENVIRONMENT === 'development' };
```
Note (Pitfall 4): `app/.env`'s `ENVIRONMENT` is an independent value from the project-root `.env` read by `api/core/config.py` — both must be set to `development` for the feature to be fully visible+functional in dev; a setup/checkpoint step must call this out explicitly.

**Fetch-to-backend action pattern** (`admin/arguments/[id]/+page.server.ts` lines 162-188, `updateParticipantSide`):
```typescript
updateParticipantSide: async ({ request, params, fetch }) => {
    const formData = await request.formData();
    // ... extract fields ...
    let res: Response;
    try {
        res = await fetch(
            `${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/participants/${participant_id}`,
            {
                method: 'PATCH',
                headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
                body: JSON.stringify({ side, title }),
            },
        );
    } catch {
        return fail(502, { roleError: 'Could not save role. Try again.' });
    }
    if (!res.ok) {
        return fail(422, { roleError: 'Could not save role. Try again.' });
    }
    throw redirect(303, '/admin/arguments/' + params.id);
},
```
Adapt for a new `resetToFixture` action in `admin/+page.server.ts`'s `actions` block: `POST` to `${FASTAPI_BASE_URL}/api/admin/dev/reset-to-fixture` with the `X-Admin-Token` header; on success return the JSON body (fixture list) directly to the form result rather than redirecting, since the UI-SPEC's Success state renders inline on the same page (per Pattern 4 in RESEARCH.md, matching the Danger Zone's `use:enhance` + `update()` flow, not the `updateParticipantSide` redirect flow).

---

### `app/src/routes/admin/+page.svelte` (Dev Tools section)

**Analog:** `app/src/routes/admin/arguments/[id]/+page.svelte` Danger Zone section, lines 608-674.

**Two-step confirm pattern to copy** (lines 615-657):
```svelte
{#if deleteConfirming}
  <div style="display: flex; gap: 8px;">
    <form
      method="POST"
      action="?/delete"
      style="flex: 1;"
      use:enhance={() => {
        deleteSubmitting = true;
        return async ({ update }) => {
          deleteSubmitting = false;
          await update();
        };
      }}
    >
      <button type="submit" disabled={deleteSubmitting}>
        {deleteSubmitting ? 'Deleting…' : 'Confirm delete'}
      </button>
    </form>
    <button type="button" onclick={() => { deleteConfirming = false; }}>
      Cancel
    </button>
  </div>
{:else}
  <button type="button" onclick={() => { deleteConfirming = true; }}>
    Delete argument
  </button>
{/if}
```
Adapt directly for `resetConfirming`/`resetRunning`/`resetResult` state and `action="?/resetToFixture"`, gated by `{#if data.isDevelopment}` around the whole section (never CSS-hidden — per D-07/Architecture Rule 2, the section must be server-omitted when not development, and this Svelte-level `{#if}` is the client-side complement to `+page.server.ts` only returning `isDevelopment: true` in dev). Error display follows the same `{#if form?.deleteError}` → `{#if form?.resetError}` pattern (lines 659-665).

---

### `api/tests/test_admin_dev_routes.py` (new integration test)

**Analog:** existing `api/tests/test_admin_dashboard_routes.py` (httpx `AsyncClient` + `ASGITransport` pattern used across all `api/tests/test_admin_*_routes.py` files) — confirmed as the established test-client pattern per RESEARCH.md's Standard Stack table. Must run against `TEST_DATABASE_URL`/`scotus_test`, never the shared dev DB (Phase 31 `pytest_sessionfinish` guard already enforces row-count invariants for `people`/`arguments`).

---

### `tests/test_admin_dev_router_gate.py` (new unit test)

**Analog:** `tests/test_admin_router.py::test_api_main_imports_without_error` (lines 202-229) — exact module-re-import technique.

**Pattern to copy verbatim (adapted):**
```python
import importlib
import sys
import os

os.environ["ENVIRONMENT"] = "production"
for mod in list(sys.modules.keys()):
    if mod.startswith("api."):
        del sys.modules[mod]
main = importlib.import_module("api.main")
assert not any(r.path.startswith("/api/admin/dev") for r in main.app.routes)
```
Also add the inverse assertion (route present) with `ENVIRONMENT=development` set, to positively confirm the mount happens in dev.

## Shared Patterns

### Auth (admin token)
**Source:** `api/routers/admin.py` lines 103-124 (`verify_admin_token` + router-level `dependencies=[Depends(verify_admin_token)]`)
**Apply to:** `api/routers/admin_dev.py` — import and reuse `verify_admin_token` unchanged; do not duplicate the HMAC-compare logic. The environment gate is additive to this auth, never a replacement.

### Fail-fast required Settings field
**Source:** `api/core/config.py` `admin_token: str` (lines 29-33)
**Apply to:** the new `environment: str` field — same no-default, fail-at-import-time contract; same operational rollout cost (every deployed env must set it before this ships).

### Service-layer state transitions (never direct column writes)
**Source:** `api/services/admin_jobs.py::approve_job` (lines 547-591), `api/services/admin_arguments.py::publish_argument` (lines 569-615)
**Apply to:** `api/services/admin_dev.py::reset_to_fixture` — call these functions for DRAFT/PUBLISHED transitions; only the Mid-pipeline fixture's `AdminJob.status` flip is a direct write (no service-layer precedent exists for it, and none is required by D-03's scope).

### Two-step inline confirm + SvelteKit form action
**Source:** `app/src/routes/admin/arguments/[id]/+page.svelte` lines 608-674 (Danger Zone)
**Apply to:** `app/src/routes/admin/+page.svelte`'s new Dev Tools section — identical `xConfirming`/`xSubmitting` boolean-state + two-button-row shape, no modal/dialog library (none exists in this codebase).

### Server-only env var → page data gate
**Source:** `app/src/routes/admin/+page.server.ts` line 4 (`$env/static/private` import pattern already used for `ADMIN_TOKEN`/`FASTAPI_BASE_URL`)
**Apply to:** new `ENVIRONMENT` import in the same file, threaded into `load`'s return value as `isDevelopment`; consumed by `+page.svelte`'s `{#if data.isDevelopment}`.

## No Analog Found

None — every file in this phase has a strong (exact or role-match) analog in the existing codebase, per RESEARCH.md's own finding that this phase is "entirely an internal-codebase integration problem, not a new-technology problem."

## Metadata

**Analog search scope:** `api/core/`, `api/routers/`, `api/services/`, `api/main.py`, `pipeline/tests/conftest.py`, `pipeline/commands/import_convokit.py`, `app/src/routes/admin/`, `tests/test_admin_router.py`, `api/tests/test_admin_dashboard_routes.py`
**Files scanned:** 12 (config.py, main.py, admin.py, admin_jobs.py, admin_arguments.py, conftest.py [pipeline], +page.server.ts [admin], +page.svelte [arguments/[id]], +page.server.ts [arguments/[id]], test_admin_router.py, admin_dev context from RESEARCH.md/CONTEXT.md)
**Pattern extraction date:** 2026-07-31
