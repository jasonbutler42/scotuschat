---
created: 2026-08-12T00:00:00.000Z
resolved: 2026-08-15T00:00:00.000Z
resolves_phase: 46
title: pytest explicit-path invocations bypass DB test isolation and can wipe the dev DB
area: dev-environment
priority: high
files:
  - tests/conftest.py
  - api/tests/conftest.py
  - pytest.ini
---

## Resolution (Phase 46, plan 46-01)

Fixed via this todo's own suggested option 2/3: the `TEST_DATABASE_URL` redirect
and row-count tripwire were relocated to the rootdir `conftest.py` via a
`pytest_configure` sentinel (fires for every invocation shape regardless of
collected paths), with both sibling conftests (`api/tests/`, `pipeline/tests/`)
failing closed with a loud `AssertionError` if the sentinel didn't fire.
Regression-pinned by `tests/test_pytest_isolation_invocation_shapes.py` (all
three invocation shapes). The exact scenario this todo describes — a full
suite run PLUS the literal explicit-path command that wiped the dev DB during
Phase 45 — was re-run with dev-DB row counts proven byte-identical, and
independently re-verified twice more since (46-03 finalization, and Phase 46's
own goal-verification agent). See `46-VERIFICATION.md` and `46-SECURITY.md`
(T-46-01-01/02, threat register) for the full evidence trail.

## Problem

`tests/conftest.py` (root-level) is the ONLY place that redirects `DATABASE_URL`
to `TEST_DATABASE_URL` before any test module imports `api.core.config.settings`.
It relies on pytest discovering it as an ancestor conftest of every collected
test file — which only happens when pytest's default `testpaths` (`tests
pipeline/tests api/tests`, from `pytest.ini`) drives collection, i.e. when
`pytest` is invoked bare with no path arguments.

Any invocation that passes explicit paths under `api/tests/` or
`pipeline/tests/` (e.g. `pytest api/tests/test_foo.py`, or
`pytest api/tests -q`) never walks up into the sibling `tests/` directory,
so `tests/conftest.py` is never imported, the redirect never fires, and
every "DB-gated" test in that run executes directly against the real,
shared dev `DATABASE_URL` — including tests that insert/delete/wipe rows
as part of their own setup/teardown.

`tests/conftest.py` also has a `pytest_sessionstart`/`pytest_sessionfinish`
guard meant to catch exactly this (snapshot dev-DB row counts, fail loudly
if they change) — but that guard has the identical single point of failure:
it only runs when `tests/conftest.py` itself gets loaded, which is precisely
the condition being violated.

## Impact (observed during Phase 45)

This is very likely the root cause of the "no data in local dev" issue
reported mid-Phase-45: the dev database was found completely empty (0 rows
across `cases`/`arguments`/`people`/`utterances`) at the start of Phase 45's
checkpoint verification. It happened a second time, mid-session, immediately
after running `pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`
(explicit paths) — the dev DB, freshly re-seeded minutes earlier, was wiped
back to 0 rows by that single invocation.

A bare `pytest -q` run — the only one that actually engages the isolation
guard — surfaced its own `pytest_sessionfinish` assertion failure in a
related experiment: `AssertionError: Shared dev DB row counts changed
during this pytest session — a test leaked writes into the real database
instead of the isolated test DB (people: before=12 after=0)`. That specific
run's own `os.environ["DATABASE_URL"]` had been pre-set by an ad-hoc script
before invoking pytest, which may itself be a confound — this needs a clean
re-investigation, not just this todo's narrative, before deciding the fix.

## Suggested fix (not applied — out of Phase 45 scope)

Options to evaluate:
1. Move the `TEST_DATABASE_URL` redirect (and the row-count guard) into a
   `conftest.py` at the actual rootdir (or duplicate the redirect logic into
   `api/tests/conftest.py` and `pipeline/tests/conftest.py`) so it fires
   regardless of how pytest is invoked, not just when `tests/` is in the
   collected path set.
2. Add a `pytest_addoption`/`pytest_configure` hook (which DOES run for
   every invocation regardless of collected paths, since it fires at the
   `Config` level before collection) to perform the redirect — this is the
   more robust fix, since `pytest_configure` in ANY discovered conftest.py
   along the actual invocation's real rootdir runs before collection,
   whereas module-level code in a specific file only runs if that file is
   imported.
3. Fail closed: if `TEST_DATABASE_URL` is configured but the redirect can be
   shown not to have fired (e.g. via an early `pytest_configure` sentinel),
   refuse to run any DB-gated test rather than silently falling through to
   the real dev DB.
4. Shorter-term mitigation: document in CLAUDE.md / a CONTRIBUTING note that
   `pytest` must always be invoked bare (no explicit file paths) to keep the
   DB-isolation guard active, and update this repo's own test-running
   convention (SUMMARY.md verification commands in past phases used
   explicit paths).

Route this into the already-planned "fix the local dev environment" phase
(agreed with the operator after Phase 45's checkpoint) — this todo is the
most safety-critical item for the outcome of that phase, since it is
actively destroying local data, not merely an inconvenience.
