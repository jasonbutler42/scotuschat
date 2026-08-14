---
phase: 46-dev-environment-reliability
fixed_at: 2026-08-14T21:25:57Z
review_path: .planning/phases/46-dev-environment-reliability/46-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 46: Code Review Fix Report

**Fixed at:** 2026-08-14T21:25:57Z
**Source review:** .planning/phases/46-dev-environment-reliability/46-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (2 critical, 4 warning; `fix_scope: critical_warning` — the 2 Info findings, IN-01 and IN-02, were intentionally left unfixed)
- Fixed: 6
- Skipped: 0

**Verification environment:** All fixes were applied and verified inside an isolated git worktree at `/home/jason/scotuschat/project/.claude/worktrees/rf-46-954035-1786741919` (branch `gsd-reviewfix/46-954035`, forked from `main`), per this workflow's transactional worktree protocol. Test-suite verification (`pytest`) was run from inside that worktree using the main checkout's `.venv` interpreter (`/home/jason/scotuschat/project/.venv/bin/python -m pytest`) — the worktree itself has no `.venv` of its own (gitignored, not created by `git worktree add`). This is reproducible from the main checkout at `/home/jason/scotuschat/project` once the worktree's commits are fast-forwarded onto `main` by this workflow's cleanup tail.

## Fixed Issues

### CR-01: `clean_db` truncates whatever `DATABASE_URL` resolves to — the shared dev DB — with none of `_reset_test_db`'s safety guard

**Files modified:** `pipeline/tests/conftest.py`
**Commit:** `730c3571`
**Applied fix:** Hardened `test_db_url` to match `_reset_test_db`'s documented "HARD SAFETY GUARD (T-31-01)" pattern in the same file: it now reads `TEST_DATABASE_URL` only (never falls back to `DATABASE_URL`) and additionally requires `make_url(url).database == "scotus_test"`, calling `pytest.skip()` in either failure case instead of silently proceeding. Since `engine`, `async_session`, and `clean_db` all build on top of `test_db_url`'s return value, this single choke point closes the path by which `clean_db` could previously TRUNCATE the shared dev DB.

**Verification:** `python3 -c "import ast; ast.parse(...)"` passed; re-read the modified fixture; ran the full `pipeline/tests/` suite (`227 passed, 5 xfailed`, no new failures) inside the worktree using the main checkout's venv.

### CR-02: Unvalidated `WIN_HOST_IP` is interpolated into a `bash -c` string and a `sed` script — command injection

**Files modified:** `scripts/dev-start.sh`
**Commit:** `feaf7476`
**Applied fix:** `resolve_win_host_ip` now validates the resolved value against `^([0-9]{1,3}\.){3}[0-9]{1,3}$` and exits with a clear error if it doesn't match, before the value is ever used by the downstream `sed -i` or `bash -c` /dev/tcp probe sinks. Also capped route selection to the first line (`awk 'NR==1{print $3}'`), which additionally addresses the related multi-default-route scenario described in IN-02 (left otherwise out of scope).

**Verification:** `bash -n` syntax check passed. Functionally reproduced the reviewer's injection PoC (`WIN_HOST_IP='127.0.0.1/1; touch /tmp/pwned #'`) against the patched function and confirmed it now exits 1 with a clear error instead of executing the injected command.

### WR-01: Dev-DB leak-detection guard only watches 2 of the 10 tables `clean_db`/`_reset_test_db` touch

**Files modified:** `conftest.py`
**Commit:** `ded0c2a6`
**Applied fix:** Extracted a `_WATCHED_TABLES` tuple mirroring `pipeline/tests/conftest.py`'s truncate-table list exactly (all 10 tables), and a shared `_query_watched_table_counts` async helper used by both `pytest_sessionstart` and `pytest_sessionfinish`. The snapshot/compare logic and per-table mismatch message format are unchanged — only the table coverage was extended from `("people", "arguments")` to the full list.

**Verification:** `python3 -c "import ast; ast.parse(...)"` passed; re-read both hook functions; ran the full repo-root `pytest` suite (see WR-04 below — verified together with WR-04's commit) with no new failures introduced.

### WR-02: `probe_postgres` validates the wrong host when `SCOTUS_DEV_NO_ENV_SYNC=1` is set

**Files modified:** `scripts/dev-start.sh`
**Commit:** `e63c4576`
**Applied fix:** `sync_env_db_host` now sets a `PROBE_HOST` global on every return path — the untouched `.env` host (`${db_host:-$test_host}`) when `SCOTUS_DEV_NO_ENV_SYNC` skipped the rewrite, or `WIN_HOST_IP` in the other two paths (no change needed / rewrite just performed) — and `probe_postgres` now checks `PROBE_HOST` instead of `WIN_HOST_IP` directly, so the reachability check and its success/failure messages describe the host actually in effect for `.env`.

**Verification:** `bash -n` syntax check passed. Functionally exercised both branches by sourcing the relevant functions with a synthetic `.env`: confirmed `PROBE_HOST` resolves to the untouched `.env` host under `SCOTUS_DEV_NO_ENV_SYNC=1`, and to `WIN_HOST_IP` when no drift/sync is needed.

### WR-03: Hardcoded 172.16.0.0/12 assumption breaks under WSL2 mirrored networking or a custom `.wslconfig` subnet

**Files modified:** `scripts/dev-start.sh`
**Commit:** `423f29a5`
**Applied fix:** Extracted the hardcoded `^172\.(1[6-9]|2[0-9]|3[01])\.` regex into a `SCOTUS_DEV_HOST_PATTERN` env var (default unchanged, so existing behavior is preserved for the common case), which a contributor on WSL2 mirrored networking or a custom subnet can override without editing the script. The error message now names the env var and its current value.

**Verification:** `bash -n` syntax check passed. Functionally verified: (1) the default pattern still rejects an out-of-range host exactly as before; (2) setting `SCOTUS_DEV_HOST_PATTERN` to a custom regex allows a previously-rejected mirrored-networking-style subnet through.

### WR-04: `_db_configured` placeholder-detection logic is duplicated verbatim across `conftest.py` and `api/tests/conftest.py`

**Files modified:** `conftest.py`, `api/tests/conftest.py`, `tests/_db_guard.py` (new)
**Commit:** `3b4d7f8c`
**Applied fix:** Created `tests/_db_guard.py::is_db_configured` as the single source of truth for the placeholder-detection logic (`bool(url) and "sk-ant" not in url and url != <.env.example placeholder DSN>`). Both `conftest.py` (root) and `api/tests/conftest.py` now import and use it instead of each defining their own copy. `pipeline/tests/conftest.py`'s `test_db_url` was deliberately left as-is here — it was just hardened for CR-01 with a different, stricter guard (must name `scotus_test` exactly) and is separately verified end-to-end; folding the placeholder check into it is a reasonable follow-up but a distinct, lower-priority change better made deliberately rather than as a side effect of this dedup.

**Verification:** `python3 -c "import ast; ast.parse(...)"` passed for all three files; re-read the import sites in both conftest files; ran the full repo-root `pytest` suite (`1022 passed, 8 skipped, 5 xfailed, 4 failed`) — the 4 failures are pre-existing and unrelated (`api/tests/test_phase44_argument_role_roundtrip.py`, a Pydantic v2 enum-coercion assertion issue in that test file, byte-for-byte identical to the pre-fix `b30340ae` baseline). One additional pre-existing, unrelated failure (`tests/test_schema.py::test_no_create_all_in_codebase`, a false-positive substring match against its own docstring/assertion text in `api/tests/test_phase44_descriptor_rename.py`) was deselected for this run and separately confirmed present at the pre-fix baseline via a detached-HEAD checkout of `b30340ae`.

## Skipped Issues

None — all 6 in-scope findings were fixed.

## Out of Scope (not attempted)

- **IN-01** (`dev-start.sh` silently overwrites `.env.bak`) — Info tier, excluded by `fix_scope: critical_warning`.
- **IN-02** (`resolve_win_host_ip` doesn't guard against multiple default routes) — Info tier, excluded by `fix_scope: critical_warning`. Note: the CR-02 fix's `awk 'NR==1{print $3}'` change happens to also address this case, as the review itself anticipated ("The `NR==1` guard also fixes the related multi-default-route case noted in IN-02 below"), but IN-02 was not separately investigated or marked resolved.

---

_Fixed: 2026-08-14T21:25:57Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
