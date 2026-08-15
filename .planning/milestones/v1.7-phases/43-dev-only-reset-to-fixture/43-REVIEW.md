---
phase: 43-dev-only-reset-to-fixture
reviewed: 2026-07-31T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - api/core/config.py
  - api/main.py
  - api/routers/admin_dev.py
  - api/schemas/admin_dev.py
  - api/services/admin_dev.py
  - api/tests/test_admin_dev_routes.py
  - app/src/routes/admin/+page.server.ts
  - app/src/routes/admin/+page.svelte
  - tests/test_admin_dev_frontend_gate.py
  - tests/test_admin_dev_router_gate.py
findings:
  critical: 0
  warning: 6
  info: 2
  total: 8
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2026-07-31T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the dev-only "Reset to Fixture" feature end to end: the backend gate
(`api/main.py`'s conditional `include_router`), the destructive service
(`api/services/admin_dev.py`), the router/schema layer, the frontend gate
(`+page.server.ts`/`+page.svelte`), and both gate-proof test suites.

**No SQL injection risk was found.** `TRUNCATE_SQL` is a static, hand-authored
string with no request-derived interpolation, and the test-only `corpus_dir`
keyword argument only ever reaches `pathlib.Path` existence checks and a
`SimpleNamespace` passed to the pipeline importer — never a SQL string.

**The environment gate is correctly implemented as an allow-list on both
sides**, and both are proven independently: `test_dev_router_absent_for_
allowlist_near_misses` covers the backend for `""`, `"Development"`, and
`"DEVELOPMENT"`; the frontend uses the same `=== 'development'` strict
comparison in both the `load()` visibility gate and the `resetToFixture`
action gate. Auth (`verify_admin_token`, `hmac.compare_digest`) is unchanged
from the existing admin router and is correctly applied at the router level
for the new dev router.

The issues found are concentrated in two areas: (1) how failure detail is
surfaced back to an HTTP client once the destructive path is reached, and (2)
robustness of the multi-step, non-atomic reset sequence under partial or
concurrent failure. None of these rise to a security bypass or an
info-disclosure vector reachable without both the `development` environment
value AND a valid admin token already presented — but several degrade the
"never leak internals" and "always report the true failure state" guarantees
that this module's own extensive comments claim to provide.

## Warnings

### WR-01: Raw exception `repr()` is returned verbatim in the 500 response body

**File:** `api/services/admin_dev.py:197-200`, surfaced via `api/routers/admin_dev.py:48-51`
**Issue:** When `run_import_convokit` raises for a fixture, the service wraps it as:
```python
raise ResetIncompleteError(
    f"Conversation {conversation_id!r} failed to import — "
    f"reset is incomplete ({exc!r})."
) from exc
```
The router then does `raise HTTPException(status_code=500, detail=str(exc)) from exc`,
which puts the *original* exception's `repr()` directly in the JSON response body
sent to the client. Depending on what actually failed, `exc` could be a
SQLAlchemy/asyncpg error whose `repr()` embeds the failing SQL statement text
and/or bound parameter values (e.g. a `UniqueViolationError` detail line), or a
`FileNotFoundError` with an absolute server filesystem path. This is reachable
only with a valid admin token in a `development`-gated environment, so the
practical exposure is limited to an already-privileged operator — but it is
still an internal-detail leak into an HTTP response body, and the same
`{exc!r}`-into-`detail` pattern is easy to copy into a future, less-gated
endpoint.
**Fix:** Log the full exception server-side (`logger.exception(...)`) and
return a sanitized, fixed-shape message to the client, e.g.:
```python
except CorpusUnavailableError as exc:
    raise HTTPException(status_code=503, detail="Corpus unavailable — see server logs.") from exc
except ResetIncompleteError as exc:
    logger.exception("reset_to_fixture failed: %s", exc)
    raise HTTPException(status_code=500, detail="Reset failed partway through — see server logs.") from exc
```

### WR-02: `CorpusUnavailableError` embeds the raw server filesystem path

**File:** `api/services/admin_dev.py:138`, `:147`
**Issue:**
```python
raise CorpusUnavailableError(f"Corpus directory not found: {corpus_dir}")
...
raise CorpusUnavailableError(f"Required corpus file not found: {required}")
```
`corpus_dir` defaults to `pipeline.commands.import_convokit.DEFAULT_CORPUS_DIR`
(`data/corpus`, resolved relative to the process cwd) and is echoed into the
503 `detail` returned by the router. This discloses server-local directory
layout to the client. Same mitigation as WR-01 applies (log the path, return
a generic message).
**Fix:** Return a fixed message ("Corpus files unavailable — see server
logs.") and log the resolved path server-side only.

### WR-03: State-realization calls are not guarded the way the reseed loop is

**File:** `api/services/admin_dev.py:249-260`
**Issue:** The reseed loop wraps `run_import_convokit` in `try/except Exception`
specifically so an unexpected failure always surfaces as `ResetIncompleteError`
(the module's own docstring states "this module always verifies... A short
`fixtures` list is never a valid 200"). The subsequent state-realization step
does not carry that same guarantee:
```python
await jobs_service.approve_job(db, draft_job_id)
...
await jobs_service.approve_job(db, published_job_id)
await arguments_service.publish_argument(db, published_argument_id)
```
Both `approve_job` and `publish_argument` raise plain `ValueError` for a
handful of documented preconditions (job/argument not found, wrong status,
"resolve step not yet complete", "Already published"). None of those
`ValueError`s are caught here or in `api/routers/admin_dev.py`, so any of them
propagates as an unhandled exception, bypassing the module's own
`ResetIncompleteError`/`CorpusUnavailableError` contract and returning
FastAPI's generic unhandled-exception response instead of the documented,
sanitized failure path. This is most likely to trigger if the reset is
re-entered while a previous partial run left an argument in a non-`PIPELINE`
state (see WR-04) — exactly the "any failure, re-run the whole reset"
recovery path the module's top comment recommends.
**Fix:** Wrap the state-realization block the same way the reseed loop is
wrapped, translating any `ValueError` from `approve_job`/`publish_argument`
into `ResetIncompleteError` so the failure contract is consistent end to end.

### WR-04: No guard against overlapping/concurrent `reset-to-fixture` invocations

**File:** `api/services/admin_dev.py` (whole function, `reset_to_fixture`)
**Issue:** The module's own test suite documents that Postgres's `TRUNCATE`
takes `ACCESS EXCLUSIVE` and will block/deadlock against any other open
transaction touching the same tables (see the comment above `await
db.commit()` in `test_reset_is_repeatable`). Nothing in `reset_to_fixture`
itself (or the router) prevents two overlapping HTTP requests to
`/api/admin/dev/reset-to-fixture` — e.g. two operators, two browser tabs, or
a doubled click that lands before the button is swapped out client-side.
Two concurrent invocations can interleave their `TRUNCATE`/reseed/
state-realization phases, producing a genuinely inconsistent end state (or a
lock wait/deadlock) that the "just re-run it" recovery advice does not
cleanly resolve, since a second run started mid-flight of a first is not the
same as a clean re-run against a finished (or untouched) database.
**Fix:** Serialize invocations — e.g. a Postgres advisory lock
(`pg_advisory_xact_lock`) acquired at the top of `reset_to_fixture`, held for
the duration of the whole operation, with a fast-fail (409) response if the
lock is already held.

### WR-05: Frontend collapses auth failures into the "database may be inconsistent" copy

**File:** `app/src/routes/admin/+page.server.ts:245-251`
**Issue:**
```ts
if (res.status === 404) {
    return fail(404, { resetError: RESET_ENV_ERROR });
}
if (!res.ok) {
    return fail(502, { resetError: RESET_MID_ERROR });
}
```
Any non-404, non-2xx backend response — including a `401` from
`verify_admin_token` (e.g. `ADMIN_TOKEN` drift between the two independently
configured `.env` files that `api/core/config.py`'s own comments call out as
a manually-synced value) — is mapped to `RESET_MID_ERROR`: "the database may
be in an inconsistent state. Check server logs before retrying." A 401 is
rejected by the FastAPI dependency *before* the handler body runs, so the
database was never touched; telling an operator to worry about DB
consistency for what is actually a token-mismatch/auth problem is misleading
and could send them investigating the wrong thing. (The two-copy error
contract itself is an intentional UI-SPEC lock, so this isn't a request to
add a third copy — just to avoid asserting something false in the existing
one.)
**Fix:** Special-case `401`/`403` (or any status the backend can only return
before mutating anything) with wording that doesn't imply partial data loss,
or log the distinguishing status server-side so on-call operators aren't
misdirected.

### WR-06: Auth-gate test is skipped in environments without `TEST_DATABASE_URL`, even though it never touches the DB

**File:** `api/tests/test_admin_dev_routes.py:290-298`
**Issue:**
```python
async def test_reset_requires_admin_token(client):
    """POST without a valid X-Admin-Token returns non-200/non-5xx and does
    not mutate the database. Runs without needing a corpus dir at all."""
    _require_test_db()

    resp = await client.post("/api/admin/dev/reset-to-fixture")
    assert resp.status_code != 200
    assert resp.status_code < 500
```
The docstring itself notes this test "runs without needing a corpus dir at
all" — it only needs an unauthenticated POST, which is rejected by
`verify_admin_token` before any DB session is touched. Calling
`_require_test_db()` unconditionally means this auth-gate regression test is
silently skipped in any CI/dev environment where `TEST_DATABASE_URL` isn't
configured, even though nothing about the assertion requires a database at
all — reducing coverage of the one test that proves the destructive endpoint
still enforces auth.
**Fix:** Drop the `_require_test_db()` call from this specific test (or move
it after the assertion, as a documented no-op) since the test provably never
reaches a DB-touching code path.

## Info

### IN-01: `disabled={resetRunning}` is dead code in the Confirming branch

**File:** `app/src/routes/admin/+page.svelte:424`, `:443`
**Issue:** The three states are rendered as mutually exclusive branches:
`{#if resetRunning} ... {:else if resetConfirming} ... {:else} ... {/if}`.
Inside the `resetConfirming` branch, both the "Confirm reset" and "Cancel"
buttons carry `disabled={resetRunning}` — but `resetRunning` can never be
`true` while this branch is the one being rendered (if it were, the `{#if
resetRunning}` branch would render instead). The attribute is always `false`
in practice; it's leftover pattern-matching from the referenced
`deleteConfirming`/`deleteSubmitting` precedent, which may not have used
mutually-exclusive branches the same way.
**Fix:** Remove the dead `disabled={resetRunning}` from both buttons in the
`resetConfirming` branch, or add a code comment noting it's intentionally
defensive/unreachable if kept for parity with the referenced pattern.

### IN-02: Unreachable fallback in the final response build

**File:** `api/services/admin_dev.py:314`
**Issue:** `"admin_job_status": admin_job.status.value if admin_job else "",`
— by this point in the function, every fixture's `AdminJob` row has already
been confirmed to exist (the `if admin_job is None: raise
ResetIncompleteError(...)` check earlier in the same function, before
`fixture_rows.append(...)`), and nothing in the state-realization step
deletes `AdminJob` rows. The `else ""` branch is therefore dead defensive
code that can't currently be exercised.
**Fix:** No action required; harmless. Consider a comment noting it's
deliberately defensive if kept, so a future reader doesn't assume it's
reachable and start debugging why the schema calls for a nullable-looking
string.

---

_Reviewed: 2026-07-31T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
