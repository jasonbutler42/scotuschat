---
phase: 46
slug: dev-environment-reliability
status: verified
threats_open: 0
asvs_level: 1
created: 2026-08-15
---

# Phase 46 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| WSL ↔ Windows-hosted PostgreSQL | A WSL-native process (pytest, uvicorn, alembic) reaches a PostgreSQL 18 service running on the Windows host over the dynamically-resolved gateway IP | DB connection string (host, credentials), query traffic |
| Dev-only admin router ↔ HTTP surface | `admin_dev_router` (dev/test-only reset-to-fixture endpoint) mounted on the same FastAPI app as production routes | Fixture reset requests, DB row-count responses |
| Operator's `.env` / `.env.bak` ↔ shell scripts | `scripts/dev-start.sh` reads and rewrites `.env` DB host values, and interpolates network-derived and `.env`-derived host strings into shell/`sed` commands | DB host strings, DSNs (password-redacted in all logged output) |
| Pre-relocation checkout ↔ relocated repo | Two on-disk copies of the same git history exist post-relocation (D-04); one is retired but still holds untracked secrets/data | `.env`, `app/.env`, `data/corpus`, `data/pdfs`, `data/uploads` |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-46-01-01 | Tampering (destructive write) | conftest.py (rootdir) | high | mitigate | Rootdir conftest.py redirect + `pytest_configure` sentinel fires for every invocation shape | closed |
| T-46-01-02 | Tampering (silent fail-open) | api/tests/conftest.py, pipeline/tests/conftest.py | high | mitigate | Sibling conftests fail closed (loud `AssertionError`) if the rootdir sentinel didn't fire; wired as explicit fixture dependency | closed |
| T-46-01-03 | Tampering (regression) | CLAUDE.md | medium | mitigate | Invariant documented by name, citing the regression test | closed |
| T-46-01-04 | Information Disclosure | tests/test_pytest_isolation_invocation_shapes.py | low | mitigate | Only synthetic DSNs used in test fixtures; no real credentials | closed |
| T-46-02-01 | Info Disclosure / EoP | Windows PostgreSQL 18 service | high | mitigate | `pg_hba.conf` scoped to the WSL subnet CIDR with `scram-sha-256`; Windows Firewall rule scoped to the same CIDR; no `0.0.0.0/0`, no `trust` | closed |
| T-46-02-02 | Elevation of Privilege | api/main.py (admin_dev_router) | high | mitigate | Router mount gated behind `settings.environment == "development"`, single occurrence | closed |
| T-46-02-03 | Information Disclosure | 46-WINDOWS-POSTGRES-SETUP.md | medium | mitigate | Credentials never recorded in plaintext in evidence docs; prompted password creation | closed |
| T-46-02-04 | Information Disclosure | postgresql.conf (`listen_addresses = '*'`) | medium | accept | NAT-subnet volatility makes a narrower bind fragile; compensating controls are the pg_hba.conf + firewall scoping (T-46-02-01) | closed (accepted) |
| T-46-03-01 | Tampering (destructive write) | Dev DB / pytest invocation shapes | high | mitigate | Row-count table across bare/explicit-path/fail-closed-control invocations, all byte-identical; the literal Phase-45 wipe command re-run and confirmed safe | closed |
| T-46-03-02 | Information Disclosure | tests/test_wsl_postgres_reachability.py | high | mitigate | `hide_password=True` on every rendered DSN; `.env`/`app/.env` gitignored and untracked | closed |
| T-46-03-03 | Tampering (DDL authority) | Alembic migrations | medium | mitigate | Zero real `Base.metadata.create_all` invocations repo-wide (grep-verified) | closed |
| T-46-03-04 | Denial of Service (self-inflicted) | .env DB host drift | medium | mitigate | Negative-control regression test proves a stale host fails loudly with a corrected DSN | closed |
| T-46-03-05 | Elevation of Privilege | api/main.py (admin_dev_router) | medium | mitigate | Same gate as T-46-02-02 | closed |
| T-46-04-01 | Denial of Service (history loss) | Repository relocation | critical | mitigate | Byte-identical HEAD SHA and commit count at both locations; origin remote intact; source tree never deleted | closed |
| T-46-04-02 | Information Disclosure | .env, app/.env at new location | high | mitigate | Both files mode 0600 at destination | closed |
| T-46-04-03 | Tampering (wrong checkout) | .venv, node_modules | high | mitigate | venv shebang names the new path; toolchain rebuilt (not copied) at destination; ext4 confirmed | closed |
| T-46-04-04 | Tampering (stale worktree) | git worktree state | medium | mitigate | Only one worktree registered post-relocation | closed |
| T-46-04-05 | Repudiation (divergence) | git history fast-forward | medium | mitigate | `git merge --ff-only`, zero divergence, no stray remote | closed |
| T-46-04-06 | Tampering (core.* flip) | git config | medium | mitigate | `core.filemode`/`core.symlinks`/`core.ignorecase` confirmed correct; clean tree | closed |
| T-46-05-01 | Elevation of Privilege | scripts/dev-start.sh (`--host 0.0.0.0`) | high | mitigate | Admin router gate (T-46-02-02) unchanged and still singular despite all-interfaces bind | closed |
| T-46-05-02 | Information Disclosure | .dev-logs/ | high | mitigate | Gitignored, `git check-ignore` confirms | closed |
| T-46-05-03 | Tampering (.env clobber) | scripts/dev-start.sh (sync_env_db_host) | medium | mitigate | Loud refusal on non-matching host; `.env.bak` created mode 0600 before rewrite; opt-out via SCOTUS_DEV_NO_ENV_SYNC | closed |
| T-46-05-04 | Information Disclosure | scripts/dev-start.sh (host-drift message) | medium | mitigate | Only host printed on drift, never full DSN | closed |
| T-46-05-05 | Denial of Service (orphaned procs) | scripts/dev-start.sh (setsid/cleanup/--stop) | medium | mitigate | `setsid` + negative-PGID TERM→KILL; `--stop` targets by port via `ss`; empirically verified `$!` is the correct PGID | closed |
| T-46-05-06 | Repudiation | scripts/dev-start.sh (--stop output) | low | mitigate | Terminated PIDs named in output | closed |
| T-46-05-07 | Tampering (wrong root) | scripts/dev-start.ps1 | low | mitigate | Refuses to run unless invoked from the expected WSL share path | closed |
| T-46-06-01 | Denial of Service (irreversible destruction) | Pre-relocation checkout retirement | critical | mitigate | Option-C selected (leave in place, marked retired); no filesystem deletion performed; RETIRED-CHECKOUT.txt marker written | closed |
| T-46-06-02 | Info Disclosure / EoP | README.md (setup instructions) | high | mitigate | All three PostgreSQL access gates documented; explicit warning against unscoped CIDR / passwordless auth | closed |
| T-46-06-03 | Information Disclosure | README.md (credential creation) | medium | mitigate | Prompted password creation documented; no credentials in any phase-46 doc | closed |
| T-46-06-04 | Information Disclosure | Pre-relocation checkout (untracked secrets) | medium | transfer | Decision and rationale (why not deleted) recorded in 46-RELOCATION.md; disclosure risk surfaced to operator, not silently accepted | closed (transferred) |
| T-46-06-05 | Repudiation | Retired checkout | medium | mitigate | RETIRED-CHECKOUT.txt names the authoritative path | closed |
| T-46-06-06 | Repudiation | 46-VALIDATION.md | medium | mitigate | Every row cites concrete verifying commands | closed |
| T-46-01-SC, T-46-02-SC, T-46-03-SC, T-46-04-SC, T-46-05-SC, T-46-06-SC | Supply Chain | Dependency manifests | low | accept | "No new package introduced" — independently verified: zero commits across the phase touch requirements.txt, requirements-dev.txt, app/package.json, or app/package-lock.json | closed (accepted) |
| CR-01 | Tampering (destructive write) | pipeline/tests/conftest.py (test_db_url/clean_db) | high | mitigate | Post-hoc code-review finding, not in the original plan-time registers. `test_db_url` now requires `TEST_DATABASE_URL` naming `scotus_test`, no `DATABASE_URL` fallback, `pytest.skip()` otherwise. Commit `730c3571`. | closed |
| CR-02 | Command Injection | scripts/dev-start.sh (resolve_win_host_ip) | high | mitigate | Post-hoc code-review finding. `WIN_HOST_IP` validated as a plain IPv4 address at the point of resolution, before either the `sed` or `bash -c` sink sees it. Commit `feaf7476`. | closed |
| CR-02-R | Command Injection | scripts/dev-start.sh (sync_env_db_host / PROBE_HOST) | medium | mitigate | Security-audit finding: the WR-02 fix (probe the host actually left in `.env`) introduced a second, unvalidated producer for the same `bash -c` `/dev/tcp` sink CR-02 closed, reachable when `SCOTUS_DEV_NO_ENV_SYNC=1` is set. Same IPv4-shape guard now applied at the point of assignment. Commit `5891b436`. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `high` (workflow.security_block_on) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party / operator decision)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-46-01 | T-46-02-04 | `listen_addresses = '*'` on the Windows PostgreSQL service — a narrower bind is fragile against WSL2 NAT-subnet renumbering across host reboots; the pg_hba.conf + firewall CIDR scoping (T-46-02-01) is the compensating control | Operator (via 46-WINDOWS-POSTGRES-SETUP.md) | 2026-08-13 |
| AR-46-02 | T-46-01-SC..T-46-06-SC | No new third-party package/dependency introduced anywhere in Phase 46 (verified: zero commits touch any dependency manifest) | Operator (implicit — no new dependency proposed) | 2026-08-15 |
| AR-46-03 | T-46-06-04 | Pre-relocation checkout retained (not deleted) as the only offline second copy of unpushed history and untracked secrets/data; disclosure risk transferred to the operator's own physical/access security of that machine rather than mitigated by deletion | Operator (option-c decision, relayed pre-answered per 46-06-PLAN.md) | 2026-08-14 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-15 | 39 | 39 | 0 | gsd-security-auditor (opus) + orchestrator fix (CR-02-R) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-15
