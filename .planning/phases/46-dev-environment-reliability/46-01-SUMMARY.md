---
phase: 46-dev-environment-reliability
plan: 01
subsystem: testing
tags: [pytest, conftest, database-isolation, data-loss-fix]

# Dependency graph
requires: []
provides:
  - "Root-level conftest.py at the pytest rootdir carrying the TEST_DATABASE_URL redirect and the dev-DB row-count tripwire, collected for every pytest invocation shape"
  - "pytest_configure sentinel (config._scotus_redirect_fired) that sibling conftests can assert on"
  - "Fail-closed autouse fixtures in api/tests/conftest.py and pipeline/tests/conftest.py that refuse to run DB-gated tests if the rootdir redirect did not fire"
  - "Permanent regression coverage: tests/test_pytest_isolation_invocation_shapes.py (subprocess-based, 3 invocation shapes) plus api/tests/test_db_isolation_probe.py and pipeline/tests/test_db_isolation_probe.py"
  - "CLAUDE.md invariant documenting where invocation-shape-independent pytest hooks must live"
affects: [46-02, 46-03, 46-04, 46-05]

# Actuals (#2632)
actuals:
  tokens: 4055
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Invocation-shape-independent pytest hooks (redirects, session tripwires) belong in the rootdir conftest.py, never a subdirectory conftest — the rootdir is the only location guaranteed to be an ancestor of every testpaths entry regardless of invocation shape."
    - "Fail-closed fixture guard wired as an explicit first-parameter dependency of the fixture it must precede (not relying on autouse declaration order) to make ordering deterministic rather than incidental."

key-files:
  created:
    - conftest.py
    - tests/test_pytest_isolation_invocation_shapes.py
    - api/tests/test_db_isolation_probe.py
    - pipeline/tests/test_db_isolation_probe.py
  modified:
    - api/tests/conftest.py
    - pipeline/tests/conftest.py
    - CLAUDE.md

key-decisions:
  - "Deleted tests/conftest.py entirely (git rm) rather than leaving an empty placeholder — its contents are relocated verbatim to the new rootdir conftest.py, not duplicated."
  - "Ran verification via the main repo's Windows venv at its absolute path (/mnt/c/workspace/scotuschat/project/.venv/Scripts/python.exe) instead of a worktree-local ./.venv/Scripts/python.exe, because .venv is gitignored and per-worktree, and a symlink to the main repo's .venv broke Windows-side pathlib.stat() with WinError 1920 on the WSL-created symlink reparse point. Functionally identical interpreter; pytest rootdir is still the worktree (determined by invocation cwd, not the interpreter's location)."
  - "The plan's negative-control acceptance criterion (temporarily rename conftest.py to conftest.py.off, expect non-zero exit) does not reproduce as literally specified in this environment, because TEST_DATABASE_URL in this repo is only present via .env — removing conftest.py also removes its load_dotenv() call, so the probe correctly pytest.skip()s (exit 0) rather than failing, since it genuinely cannot see TEST_DATABASE_URL. Re-ran the negative control with a one-off harness script that calls load_dotenv() itself before invoking pytest as a subprocess (simulating TEST_DATABASE_URL being present via a real shell-exported env var, independent of the now-missing conftest's own dotenv call) — see 'Negative Control' section below for the actual recorded failure."

patterns-established:
  - "Fail-closed conftest guard: an autouse fixture asserting a sentinel fired, declared as the first parameter of the fixture it must precede, so pytest resolves it before that fixture's body runs."

requirements-completed: [D-03, TODO-PYTEST-ISO]

coverage:
  - id: D1
    description: "conftest.py relocated to the pytest rootdir; tests/conftest.py deleted; all three pytest invocation shapes (bare, explicit single file, explicit multi-path) redirect DATABASE_URL to TEST_DATABASE_URL correctly"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "tests/test_pytest_isolation_invocation_shapes.py#test_pytest_isolation_fires_for_every_invocation_shape (3 parametrized cases)"
        status: pass
      - kind: integration
        ref: "api/tests/test_db_isolation_probe.py#test_db_isolation_probe"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_db_isolation_probe.py#test_db_isolation_probe"
        status: pass
    human_judgment: false
  - id: D2
    description: "Both sibling conftests (api/tests, pipeline/tests) fail closed with a loud AssertionError if TEST_DATABASE_URL is set but the rootdir sentinel did not fire, wired as an explicit fixture dependency of _api_lifespan and _reset_test_db"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "manual grep + collection check: grep -c '_require_root_conftest_redirect' api/tests/conftest.py (>=2), grep -c '_require_root_conftest_redirect' pipeline/tests/conftest.py (>=2), pytest --collect-only -q (exit 0, 1038 tests collected)"
        status: pass
    human_judgment: false
  - id: D3
    description: "CLAUDE.md records the rootdir-conftest invariant referencing D-03 and the regression test by name"
    requirement: "TODO-PYTEST-ISO"
    verification:
      - kind: unit
        ref: "grep -q 'test_pytest_isolation_invocation_shapes' CLAUDE.md && sed -n '/## Key Constraints/,/^## /p' CLAUDE.md | grep -q conftest"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-08-12
status: complete
---

# Phase 46 Plan 1: pytest DB-isolation bypass fix (D-03) Summary

**Relocated the TEST_DATABASE_URL redirect and dev-DB row-count tripwire from a sibling `tests/conftest.py` to a root-level `conftest.py` at the pytest rootdir, closing the sibling-directory blind spot that wiped the shared dev database twice during Phase 45, and backed the fix with a subprocess-based regression test plus fail-closed guards in both sibling conftests.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-08-12T23:02:25-05:00 (last task commit)
- **Tasks:** 3/3
- **Files modified:** 7 (4 created, 3 modified — see Files Created/Modified)

## Accomplishments
- Root-level `conftest.py` created at the pytest rootdir (alongside `pytest.ini`), carrying the `_REAL_DATABASE_URL` capture, the `TEST_DATABASE_URL` → `DATABASE_URL` redirect, and both `pytest_sessionstart`/`pytest_sessionfinish` dev-DB row-count tripwire hooks — relocated verbatim from `tests/conftest.py`, which is now deleted.
- New `pytest_configure(config)` hook sets `config._scotus_redirect_fired = True`, a sentinel other conftests can assert on.
- Two hermetic probe tests (`api/tests/test_db_isolation_probe.py`, `pipeline/tests/test_db_isolation_probe.py`) and one subprocess-based regression test (`tests/test_pytest_isolation_invocation_shapes.py`, 3 parametrized invocation shapes) prove the redirect fires for bare, explicit-single-file, and explicit-multi-path pytest invocations — the last being the exact `pytest <file> <file> -q` shape that wiped the dev DB during Phase 45.
- Fail-closed guards added: `_require_root_conftest_redirect` autouse fixture in `api/tests/conftest.py` (function-scoped, wired as the first parameter of `_api_lifespan`) and in `pipeline/tests/conftest.py` (session-scoped, wired as the first parameter of `_reset_test_db`) — both assert the rootdir sentinel fired and `DATABASE_URL == TEST_DATABASE_URL` before any DB-gated test runs, no-op when `TEST_DATABASE_URL` is unset.
- `CLAUDE.md`'s Key Constraints section now documents the rootdir-conftest invariant, referencing D-03 and `tests/test_pytest_isolation_invocation_shapes.py` by name.
- Re-verified the fix against the literal historically-dangerous invocation from the folded todo (`pytest api/tests/test_published_gate.py api/tests/test_arguments.py -q`) — passes cleanly with no `pytest_sessionfinish` leak-detection failure.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relocate the redirect + tripwire to the pytest rootdir and prove it fires for every invocation shape** - `736b28d4` (feat)
2. **Task 2: Fail closed in both sibling conftests when the rootdir redirect did not fire** - `fc00ac02` (feat)
3. **Task 3: Record the rootdir-conftest invariant in CLAUDE.md so the bug class cannot be re-created** - `05f31051` (docs)

_Note: Task 1 is `tdd="true"` and `type="tracer"`; its own automated `<verify>` already covers RED/GREEN in one shot (the regression test is the proof the fix works, not a separate failing-then-passing cycle against pre-existing production code) — see Deviations for the tracer-gate handling._

## Files Created/Modified
- `conftest.py` (new, repo root) - pytest rootdir redirect + tripwire + `pytest_configure` sentinel
- `tests/conftest.py` (deleted) - contents relocated to `conftest.py`, not duplicated
- `tests/test_pytest_isolation_invocation_shapes.py` (new) - subprocess-based regression test, 3 invocation shapes
- `api/tests/test_db_isolation_probe.py` (new) - hermetic probe asserting the redirect fired
- `pipeline/tests/test_db_isolation_probe.py` (new) - hermetic probe asserting the redirect fired
- `api/tests/conftest.py` (modified) - added `_require_root_conftest_redirect` fail-closed guard, corrected stale docstring reference to deleted `tests/conftest.py`
- `pipeline/tests/conftest.py` (modified) - added session-scoped `_require_root_conftest_redirect` fail-closed guard
- `CLAUDE.md` (modified) - one new Key Constraints bullet on the rootdir-conftest invariant

## Decisions Made
- Deleted `tests/conftest.py` outright (no empty placeholder) — everything it provided is now provided by the rootdir `conftest.py`, which is also an ancestor of `tests/`.
- Verification ran via the main repo's Windows venv at its absolute path rather than a worktree-local `.venv`, since `.venv` is gitignored/per-worktree and a symlink to the main repo's venv broke Windows-side `pathlib.stat()` (WinError 1920) when accessed through WSL interop. Same interpreter, same result — pytest's rootdir is determined by invocation cwd (the worktree), not the interpreter's own location.
- Re-derived the negative control's intent (TEST_DATABASE_URL genuinely present but the rootdir redirect missing) using a one-off harness script, since this repo's `TEST_DATABASE_URL` lives only in `.env` and is invisible without the (deliberately-removed) conftest's own `load_dotenv()` call — see below for the actual recorded result.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree has no local `.venv`; symlink to main repo's `.venv` broke under Windows interop**
- **Found during:** Task 1 verification
- **Issue:** `.venv/` is gitignored and per-worktree; the plan's literal verify command `./.venv/Scripts/python.exe -m pytest ...` had no interpreter to invoke. A symlink (`ln -s /mnt/c/.../project/.venv .venv`) resolved fine from WSL but caused the Windows-native `python.exe` (invoked via WSL interop) to fail collection entirely with `OSError: [WinError 1920] The file cannot be accessed by the system` when pytest's collection-ignore logic stat'd the symlinked directory.
- **Fix:** Removed the symlink; invoked the interpreter by its absolute path (`/mnt/c/workspace/scotuschat/project/.venv/Scripts/python.exe`) with cwd remaining the worktree root for every verification command in this plan. No code changes; verification-only workaround.
- **Files modified:** None (verification tooling only).
- **Verification:** All plan `<verify>`/acceptance-criteria commands re-ran successfully with the absolute-path invocation; results recorded below.
- **Committed in:** N/A (no file change to commit).

**Total deviations:** 1 auto-fixed (1 blocking, verification-tooling only — no production code affected).
**Impact on plan:** None on scope or correctness; purely a local verification-environment workaround specific to running a Windows venv from inside a WSL git worktree.

## Issues Encountered

**Negative control ran differently than the plan's literal text expected, but confirmed the intended safety property.**

The plan's acceptance criterion says: rename `conftest.py` to `conftest.py.off`, run `pytest api/tests/test_db_isolation_probe.py -q`, expect a non-zero exit. When run literally, this exited 0 with `1 skipped` — because `TEST_DATABASE_URL` in this repo is populated only via `.env`, and with `conftest.py` (and its `load_dotenv()` call) removed, the probe genuinely cannot see `TEST_DATABASE_URL` in `os.environ`, so it correctly `pytest.skip()`s per its own spec ("calls `pytest.skip` when `os.environ.get('TEST_DATABASE_URL')` is falsy").

To faithfully reproduce the scenario the negative control is meant to prove (TEST_DATABASE_URL genuinely configured, but the rootdir redirect did not fire), a one-off harness script called `load_dotenv()` itself, then invoked `pytest api/tests/test_db_isolation_probe.py -q` as a subprocess with `conftest.py` still renamed away. Recorded result:

```
EXIT CODE: 1
FAILED api/tests/test_db_isolation_probe.py::test_db_isolation_probe - AssertionError: The rootdir conftest.py's pytest_configure hook did not fire — the TEST_DATABASE_URL redirect (D-03) is not guaranteed to have run for this invocation. See root conftest.py and tests/test_pytest_isolation_invocation_shapes.py.
assert False
 +  where False = getattr(<_pytest.config.Config object at 0x...>, '_scotus_redirect_fired', False)
1 failed in 2.72s
```

`conftest.py` was restored immediately afterward and `test -f conftest.py` re-confirmed before continuing to Task 2. No production files or committed test files reference this harness script — it was a throwaway file (`_scratch_neg_control.py`), deleted before the corresponding commit.

## Next Phase Readiness
- D-03 (pytest DB-isolation bypass) is fully closed for this repo's current three test directories (`tests/`, `api/tests/`, `pipeline/tests/`) — any future sibling test directory automatically inherits the fix since the rootdir conftest is an ancestor of everything.
- No blockers for 46-02 (WSL-native venv/Node) or 46-03 (Windows Postgres service cutover) — this plan's fix is self-contained in test configuration and does not touch runtime DB connectivity, which remains out of reach from this WSL worktree until 46-03 lands.
- Full-suite green (`pytest -q`) was deliberately not gated in this plan per 46-RESEARCH.md (port 5432 unreachable from WSL until the Postgres cutover) — all four of this plan's `<verification>` items are hermetic and passed without needing a live DB connection.

---
*Phase: 46-dev-environment-reliability*
*Completed: 2026-08-12*

## Self-Check: PASSED

All created files confirmed present (`conftest.py`, `tests/test_pytest_isolation_invocation_shapes.py`, `api/tests/test_db_isolation_probe.py`, `pipeline/tests/test_db_isolation_probe.py`, `.planning/phases/46-dev-environment-reliability/46-01-SUMMARY.md`), `tests/conftest.py` confirmed deleted, and all four task commits (`736b28d4`, `fc00ac02`, `05f31051`, plus this summary's own `e55c8d6a`) confirmed present in `git log`.
