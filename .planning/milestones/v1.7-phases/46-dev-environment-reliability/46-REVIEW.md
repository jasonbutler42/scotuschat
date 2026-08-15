---
phase: 46-dev-environment-reliability
reviewed: 2026-08-14T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .env.example
  - .gitignore
  - CLAUDE.md
  - README.md
  - api/tests/conftest.py
  - api/tests/test_db_isolation_probe.py
  - app/vite.config.ts
  - conftest.py
  - pipeline/tests/conftest.py
  - pipeline/tests/test_db_isolation_probe.py
  - scripts/dev-start.ps1
  - scripts/dev-start.sh
  - tests/test_pytest_isolation_invocation_shapes.py
  - tests/test_wsl_postgres_reachability.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-08-14
**Depth:** standard
**Files Reviewed:** 13 (`scripts/dev-start.ps1` was reviewed at its current on-disk revision; the copy encountered under `/mnt/c/workspace/...` was a stale pre-relocation mirror and was discarded in favor of the repo at `/home/jason/scotuschat/project`, which matches the phase's own git history)
**Status:** issues_found

## Summary

This phase's core deliverables are the WSL-native `scripts/dev-start.sh`/`dev-start.ps1` pair, the rootdir `conftest.py` relocation with its fail-closed sibling guards in `api/tests/conftest.py` and `pipeline/tests/conftest.py`, the WSL-gateway reachability probe (`tests/test_wsl_postgres_reachability.py`), and supporting doc/config updates. The fail-closed invocation-shape guard itself (`_scotus_redirect_fired`, D-03) is well constructed and the regression tests for it are genuinely hermetic.

However, two BLOCKER-level issues remain. First, `pipeline/tests/conftest.py`'s pre-existing `clean_db`/`test_db_url` fixtures still lack the "resolved database must be named `scotus_test`" guard that the phase-31 `_reset_test_db` fixture (in the same file) already carries as a documented hard safety invariant (T-31-01) — meaning the exact class of bug this phase and phase 45 exist to close (a stray `TRUNCATE` reaching the shared dev DB) is still reachable through a sibling fixture in a file this phase touched. Second, `scripts/dev-start.sh` interpolates the network-derived `WIN_HOST_IP` value into a `bash -c` string and a `sed` replacement without ever validating its shape, which is a demonstrated command-injection primitue if `ip route show default` ever produces anything other than a bare IPv4 address.

Four WARNING-level robustness/quality gaps and two INFO-level items are also documented below.

## Critical Issues

### CR-01: `clean_db` truncates whatever `DATABASE_URL` resolves to — the shared dev DB — with none of `_reset_test_db`'s safety guard

**File:** `pipeline/tests/conftest.py:36-52` (`test_db_url`) and `pipeline/tests/conftest.py:95-128` (`clean_db`)

**Issue:** `test_db_url` resolves `TEST_DATABASE_URL` **or falls back to `DATABASE_URL`** (line 46: `os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")`). `engine`/`async_session`/`clean_db` all build on top of that URL with no further check. `clean_db` then executes an unconditional `TRUNCATE TABLE utterances, pipeline_runs, case_arguments, case_appearances, argument_participants, arguments, cases, court_tenures, people, roles CASCADE` against whatever that URL points to.

Contrast this with `_reset_test_db` (same file, lines 159-218), which runs the identical TRUNCATE list but is explicitly guarded: it reads `TEST_DATABASE_URL` directly (never falling back to `DATABASE_URL`) and additionally requires `make_url(test_url).database == "scotus_test"` before truncating anything — a guard the docstring calls out by name as "HARD SAFETY GUARD (T-31-01): this fixture must never TRUNCATE the shared dev DB."

`clean_db` has no such guard. Any contributor who runs `pytest pipeline/tests/ -k <test using clean_db>` with only `DATABASE_URL` configured (no dedicated `TEST_DATABASE_URL` — a state the suite otherwise treats as completely normal and unconfigured-but-safe everywhere else) will TRUNCATE the real shared dev database the moment that test executes, full stop. Whether the truncate is durable depends on whether the enclosing `async_session` ever commits before its own teardown rollback (currently: no test in scope calls `commit()`, so today it happens to roll back) — but `clean_db` is documented as a generic "opt-in fixture — only add to tests that need a truly empty DB," i.e. it is designed to be composed into future tests, several of which may legitimately need to `commit()` mid-test (to test cross-transaction behavior, for example). The very first such test silently wipes the dev DB — exactly the D-02/D-03 incident class (Phase 45) this phase's regression tests exist to prevent, reachable through a fixture this phase's own review scope includes but did not harden.

**Fix:** Give `test_db_url` (or `clean_db` directly) the same guard `_reset_test_db` already has — require `TEST_DATABASE_URL` to be set and its database name to be `scotus_test` before truncating, and `pytest.skip()` (not silently proceed against `DATABASE_URL`) otherwise:

```python
@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip(
            "TEST_DATABASE_URL not configured — skipping DB-dependent tests. "
            "clean_db/async_session must never fall back to DATABASE_URL (T-31-01)."
        )
    from sqlalchemy.engine import make_url
    if make_url(url).database != "scotus_test":
        pytest.skip("TEST_DATABASE_URL does not target scotus_test — refusing to run.")
    return url
```

At minimum, add the same assertion directly inside `clean_db` before its `TRUNCATE`, mirroring `_reset_test_db`'s check.

### CR-02: Unvalidated `WIN_HOST_IP` is interpolated into a `bash -c` string and a `sed` script — command injection

**File:** `scripts/dev-start.sh:78-85` (`resolve_win_host_ip`), `scripts/dev-start.sh:125-128` (`sync_env_db_host`'s `sed -i`), `scripts/dev-start.sh:134` (`probe_postgres`)

**Issue:** `resolve_win_host_ip()` sets `WIN_HOST_IP` from `ip route show default | awk '{print $3}'` and only checks that the result is non-empty — it never checks that the value is actually a well-formed IPv4 address. That unchecked value is later interpolated, unescaped, into:

```bash
timeout 5 bash -c "exec 3<>/dev/tcp/${WIN_HOST_IP}/5432" 2>/dev/null
```

and into a `sed -i -E` replacement string. I reproduced this concretely: setting `WIN_HOST_IP='127.0.0.1/1; touch /tmp/pwned #'` and running the exact `bash -c "exec 3<>/dev/tcp/${WIN_HOST_IP}/5432"` line from this file executes the injected `touch` command. `ip route`'s output is not attacker-supplied over the network in the common case, but it is not a value the script controls either — a second default route (common with a corporate VPN client, which this environment's Offen-managed laptop is likely to run), a locale/format change in `ip route`'s output, or a compromised/misconfigured routing table can all feed non-IP text into this exact code path, and the current code has no validation gate at all before it fans out to two separate injection-shaped sinks.

**Fix:** Validate the resolved value once, at the source, before any use:

```bash
resolve_win_host_ip() {
  WIN_HOST_IP="$(ip route show default | awk 'NR==1{print $3}')"
  if [[ ! "$WIN_HOST_IP" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
    echo "ERROR: 'ip route show default' did not resolve to a plain IPv4 address (got: '${WIN_HOST_IP}')." >&2
    exit 1
  fi
  echo "Resolved Windows host IP: ${WIN_HOST_IP}"
}
```

The `NR==1` guard also fixes the related multi-default-route case noted in IN-02 below. With this validation in place at the single point of origin, both the `sed` and `bash -c` call sites become safe by construction.

## Warnings

### WR-01: Dev-DB leak-detection guard only watches 2 of the 10 tables `clean_db`/`_reset_test_db` touch

**File:** `conftest.py:100-136` (`pytest_sessionstart`), `conftest.py:161-205` (`pytest_sessionfinish`)

**Issue:** The row-count tripwire that is supposed to catch a test leaking writes into the shared dev DB only snapshots and re-checks `people` and `arguments`. `pipeline/tests/conftest.py`'s own truncate list (`clean_db`, `_reset_test_db`) names ten tables: `utterances, pipeline_runs, case_arguments, case_appearances, argument_participants, arguments, cases, court_tenures, people, roles`. A leak confined to any of the other eight tables (e.g. `utterances`, `roles`, `cases`) would pass this guard silently even though real dev data was destroyed or mutated.

**Fix:** Extend the snapshot/compare to the full table list (or at least a representative superset), while keeping the failure message per-table so it stays as legible as the current two-table version:

```python
_WATCHED_TABLES = ("people", "arguments", "cases", "utterances", "roles",
                    "court_tenures", "case_arguments", "case_appearances",
                    "argument_participants", "pipeline_runs")
```

### WR-02: `probe_postgres` validates the wrong host when `SCOTUS_DEV_NO_ENV_SYNC=1` is set

**File:** `scripts/dev-start.sh:92-131` (`sync_env_db_host`), `scripts/dev-start.sh:133-148` (`probe_postgres`)

**Issue:** `sync_env_db_host` deliberately skips rewriting `.env` when `SCOTUS_DEV_NO_ENV_SYNC` is set, precisely so a legitimately different DB host (README: "legitimately point somewhere other than the resolved WSL2 gateway (rare)") is left alone. But `probe_postgres()` unconditionally checks reachability of `WIN_HOST_IP` — the just-resolved gateway — never the host actually left in `.env`. In the `SCOTUS_DEV_NO_ENV_SYNC=1` escape-hatch case, the script can print "PostgreSQL reachable at ${WIN_HOST_IP}:5432" and proceed, while the host Alembic/uvicorn will actually use (the untouched `.env` value) was never checked at all — the success message is about a different server than the one about to be used.

**Fix:** When `SCOTUS_DEV_NO_ENV_SYNC` is set, probe the host actually extracted from `.env` (`db_host`/`test_host` from `_extract_env_host`) instead of `WIN_HOST_IP`.

### WR-03: Hardcoded 172.16.0.0/12 assumption breaks under WSL2 mirrored networking or a custom `.wslconfig` subnet

**File:** `scripts/dev-start.sh:114-120`

**Issue:** `sync_env_db_host`'s drift check only accepts a differing `.env` host if it matches `^172\.(1[6-9]|2[0-9]|3[01])\.` (the default WSL2 NAT range) or already equals `WIN_HOST_IP`; anything else is a hard `exit 1` ("does not look like a WSL2 NAT gateway address"). WSL2's "mirrored" networking mode (and any `.wslconfig` with a custom `networkingMode`/subnet) can legitimately resolve the gateway to an address outside 172.16.0.0/12, which would make this script refuse to run even though the resolved `WIN_HOST_IP` is completely correct for that machine.

**Fix:** Either drop this range check (the `db_host == WIN_HOST_IP` short-circuit above it already covers the "no change needed" case) or make it configurable, e.g. an env var listing acceptable CIDR prefixes, rather than a single hardcoded default-mode assumption baked into a script this README documents as the verified path for every contributor's machine.

### WR-04: `_db_configured` placeholder-detection logic is duplicated verbatim across `conftest.py` and `api/tests/conftest.py`

**File:** `conftest.py:61-63`, `api/tests/conftest.py:21-24`

**Issue:** Both files independently define a `_db_configured` helper with identical logic (`bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"`), one taking `url` as a parameter, the other reading `os.environ` directly. `pipeline/tests/conftest.py`'s `test_db_url` implements a third, looser variant of the same "is this actually configured" concept with no placeholder check at all. A future change to the placeholder-DSN literal or the addition of a new sentinel pattern is easy to apply in one copy and miss in the others, silently reopening the exact "ran against a fake/placeholder DB" gap this guard exists to close.

**Fix:** Extract this into a single shared helper (e.g. `tests/_db_guard.py` or a `conftest`-adjacent module imported by all three) so the placeholder rules live in one place.

## Info

### IN-01: `dev-start.sh` silently overwrites the previous `.env.bak` on every re-sync

**File:** `scripts/dev-start.sh:122-123`

**Issue:** `cp "$env_file" "${env_file}.bak"` unconditionally overwrites any existing `.env.bak`, every time `sync_env_db_host` decides a rewrite is needed. If `.env` was already broken by a prior bad edit and a good `.env.bak` from an earlier run exists, the next drift-triggered sync destroys that last-known-good backup without any warning.

**Fix:** Skip the copy if `.env.bak` already exists and is newer than the last known-good `.env` state, or rotate backups (`.env.bak.1`, `.env.bak.2`), or at minimum print a note when an existing backup is about to be replaced.

### IN-02: `resolve_win_host_ip` doesn't guard against multiple default routes

**File:** `scripts/dev-start.sh:78-85`

**Issue:** `ip route show default | awk '{print $3}'` prints one gateway per matching line. If more than one default route exists (a common side effect of a corporate VPN client adding a second default route at a different metric), `WIN_HOST_IP` ends up containing multiple IP addresses joined by newlines instead of a single address, which then flows into the `sed` substitution, the `bash -c` probe, and the printed corrected-DSN messages elsewhere in the suite (`tests/test_wsl_postgres_reachability.py`). The CR-02 fix (`awk 'NR==1{print $3}'` plus an IPv4-shape assertion) also resolves this by construction.

---

_Reviewed: 2026-08-14_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
