# Phase 31: Audit stale DB-gated test fixtures + fix real data leakage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 31-audit-stale-db-gated-test-fixtures
**Areas discussed:** Isolation mechanism, Existing leaked-row cleanup, db_session fixture consolidation, Row-count verification mechanism

---

## Isolation Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated test DB | Point TEST_DATABASE_URL at a new scotus_test database; tests commit freely against a throwaway DB | ✓ |
| Savepoint-based nested transaction | Wrap each test in an outer transaction with app commits releasing only a SAVEPOINT | |
| Snapshot/restore per test | pg_dump/pg_restore a clean snapshot before/after each test run | |

**User's choice:** Dedicated test DB (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-reset each run | Session-scoped fixture TRUNCATEs all tables at the start of each pytest session | ✓ |
| Manual reset via documented command | Documented psql/Makefile command run occasionally by operators | |

**User's choice:** Auto-reset each run (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Manual one-time setup + README | Document CREATE DATABASE + alembic upgrade head steps in README/CONTRIBUTING | |
| Scripted setup | Add a script/Makefile target that creates the DB and runs migrations automatically | ✓ |

**User's choice:** Scripted setup
**Notes:** Local Postgres is a native install (data/pgsql/), not Docker — provisioning a second DB is a one-line CREATE DATABASE, not a new container. pipeline/tests/conftest.py already prefers TEST_DATABASE_URL over DATABASE_URL as a fallback chain, so no test-code changes are needed there — just setting the env var and provisioning the DB.

---

## Existing Leaked-Row Cleanup

| Option | Description | Selected |
|--------|-------------|----------|
| One-time reviewed cleanup script | Scoped, reviewed script identifies exact duplicates and synthetic rows, dry-run then confirm-to-delete | ✓ |
| Manual DELETE now, no scripted tooling | Operator runs ad-hoc SQL outside this phase; phase only fixes root cause | |
| Out of scope — already handled | Treat cleanup as done/separate from Phase 31 | |

**User's choice:** One-time reviewed cleanup script (Recommended)
**Notes:** A live psql check during this discussion confirmed the leak is NOT already handled — 5 duplicate "Ketanji Brown Jackson" Person rows (ids 116, 959, 1097, 1204, 1285) are currently present in the dev DB, all `is_justice = true`. Baseline counts at check time: 352 people, 211 arguments.

| Option | Description | Selected |
|--------|-------------|----------|
| Broad sweep | Check Person for any duplicate full_name, and Argument for test-fixture-pattern names/orphaned rows | ✓ |
| Narrow — known duplicates only | Script only targets the 5 confirmed Ketanji Brown Jackson rows | |

**User's choice:** Broad sweep (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| pipeline/ CLI subcommand | `python -m pipeline audit-leaked-rows [--apply]` alongside existing pipeline commands | |
| Standalone scripts/ file | A one-off scripts/cleanup_leaked_test_rows.py run directly with python | ✓ |

**User's choice:** Standalone scripts/ file
**Notes:** Chosen despite the pipeline-CLI-subcommand option being the "Recommended" label — user judged this as one-time remediation, not a recurring pipeline step, so it doesn't need to live inside the pipeline package.

---

## db_session Fixture Consolidation

| Option | Description | Selected |
|--------|-------------|----------|
| Consolidate into api/tests/conftest.py | Move db_session into shared conftest.py, delete 7 duplicate local definitions | ✓ |
| Patch each of the 7 copies in place | Keep duplication, update each file's local fixture individually | |

**User's choice:** Consolidate into api/tests/conftest.py (Recommended)
**Notes:** Fixture is duplicated across 7 files (grep found 7, not 8 as initially estimated during presentation): test_admin_dashboard_stats.py, test_admin_jobs_source.py, test_admin_jobs_stats.py, test_admin_jobs_list.py, test_argument_oyez_field.py, test_admin_people_phase25.py, test_admin_jobs_phase25.py.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep separate, both fixed independently | api/tests keeps db_session, pipeline/tests keeps async_session, no forced coupling | ✓ |
| Unify into one name across both suites | Shared fixture name/module across both test suites | |

**User's choice:** Keep separate, both fixed independently (Recommended)

---

## Row-Count Verification Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Automated pytest session hook | pytest_sessionstart/pytest_sessionfinish hook snapshots and asserts Person/Argument counts unchanged | ✓ |
| Standalone verification script | Manual script/Makefile target operators run after a full-suite pass | |

**User's choice:** Automated pytest session hook (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Person + Argument only | Matches success criterion exactly; the two tables confirmed leaked in the actual incident | ✓ |
| All pipeline-relevant tables | Reuse the full clean_db table list for defense-in-depth | |

**User's choice:** Person + Argument only (Recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Skip silently | No DATABASE_URL means no shared dev DB to protect; hook no-ops | ✓ |
| Fail loudly | Missing DATABASE_URL treated as a hard error | |

**User's choice:** Skip silently (Recommended)

---

## Claude's Discretion

- Exact script filenames/locations beyond what's specified (e.g., whether provisioning is a Makefile target or a plain Python script) — noted in CONTEXT.md as planner's call.
- Sequencing of cleanup work vs. isolation-mechanism work within the phase plan — a planning concern, not a discussion decision.

## Deferred Ideas

- `2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md` — reviewed via todo cross-reference (score 0.5, UI area), not folded into this phase. Out of scope for a DB test-infra audit phase; remains unassigned for a future UI phase.
