---
phase: 48-trust-lifecycle
plan: 06
subsystem: pipeline
tags: [pipeline-cli, trust-tier, drift-repair, verification-vehicle, pytest]

requires:
  - phase: 48-trust-lifecycle
    plan: 01
    provides: "api.services.trust.recompute_argument_tier(db, argument_id) — the single non-committing service every writer (and now this CLI) calls"
provides:
  - "python -m pipeline recompute-trust --all / --argument-id / --dry-run — the offline drift-repair tool and D-21 falsifiable verification vehicle (0 rows changed after a fresh reseed proves every writer stamped correctly)"
  - "pipeline/__main__.py's import-convokit help text now names the born candidate state instead of the retired pipeline state"
affects: ["48-09 (runs recompute-trust --all against a freshly reseeded fixture as the phase's positive proof that every writer path stamped trust_tier correctly)"]

actuals:
  tokens: 5110
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Offline CLI command follows the existing sub.add_parser(...) + elif args.command == ...: asyncio.run(...) dispatch shape (seed-aliases/import-convokit precedent), imports api.services.trust the same way pipeline/commands/ingest.py already does"
    - "One get_session() transaction per argument in the --all loop (not one session for the whole scan) — a mid-scan failure leaves earlier repairs durable, matching the plan's flagged-assumption rationale"
    - "--dry-run computes the real recompute_argument_tier() write then calls session.rollback() before the context manager's own commit, rather than adding a separate no-write code path"

key-files:
  created:
    - pipeline/commands/recompute_trust.py
    - pipeline/tests/test_recompute_trust.py
  modified:
    - pipeline/__main__.py

key-decisions:
  - "Test file bootstraps api.core.database.AsyncSessionLocal via a module-local FastAPI-lifespan fixture (mirroring api/tests/conftest.py::_api_lifespan) so it can import and reuse plan 48-01's _seed_argument/_teardown_argument helper unmodified, rather than duplicating the seeding logic — pipeline/tests/ has no equivalent autouse fixture of its own since pipeline commands normally never touch AsyncSessionLocal."
  - "Added a function-scoped, genuinely committed TRUNCATE fixture (mirroring pipeline/tests/conftest.py's session-scoped _reset_test_db hard safety guard verbatim, including the TEST_DATABASE_URL==scotus_test check) so --all's whole-table scan is deterministic per test. pipeline/tests/conftest.py's own clean_db fixture was evaluated and rejected for this purpose: its TRUNCATE runs inside async_session's own transaction, which that fixture rolls back at teardown — invisible to, and undone before, any other engine's session (recompute-trust uses pipeline.db.get_session(), a separate engine) ever reads it."
  - "run_recompute_trust() branches on args.argument_id is not None rather than args.all — functionally identical given argparse's required mutually-exclusive group guarantees exactly one is set, and it lets the test suite invoke the function with a plain argparse.Namespace without needing to set an unused all=False on single-argument calls."

requirements-completed: [TRUST-01, TRUST-02]

coverage:
  - id: D1
    description: "recompute-trust --all scans every argument, recomputes each through the shared api.services.trust.recompute_argument_tier service, and reports an accurate scanned/unchanged/changed summary plus one line per changed argument naming its id, old tier, and new tier."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_recompute_trust.py::test_recompute_all_repairs_drifted_tier"
        status: pass
    human_judgment: false
  - id: D2
    description: "Re-running --all after a repair reports changed == 0 — the idempotence/adjacency edge plan 48-09's verification depends on."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_recompute_trust.py::test_recompute_all_is_idempotent"
        status: pass
    human_judgment: false
  - id: D3
    description: "--dry-run reports what would change without writing it — the stored tier is provably untouched afterward."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_recompute_trust.py::test_recompute_dry_run_reports_without_writing"
        status: pass
    human_judgment: false
  - id: D4
    description: "--argument-id scopes the repair to exactly one argument, leaving a second corrupted argument's tier untouched."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_recompute_trust.py::test_recompute_single_argument_scopes_to_that_argument"
        status: pass
    human_judgment: false
  - id: D5
    description: "--argument-id for a nonexistent id raises ValueError naming the id rather than reporting a vacuous success; --all against an empty database reports scanned == 0, changed == 0 rather than failing or reporting success vacuously (the unclassified TRUST-02 edge probe's detector)."
    requirement: "TRUST-02"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_recompute_trust.py::test_recompute_unknown_argument_id_raises, test_recompute_all_on_empty_database_reports_zero"
        status: pass
    human_judgment: false
  - id: D6
    description: "The command derives nothing of its own (imports api.services.trust, no re-derivation logic) and has no HTTP surface — offline CLI only per CLAUDE.md."
    requirement: "TRUST-01"
    verification:
      - kind: other
        ref: "AST check: 'api.services.trust' in the module's ImportFrom targets, no fastapi import; grep -rn recompute api/routers/ returns no lines"
        status: pass
    human_judgment: false
  - id: D7
    description: "Full-repo test suite remains green with exactly the one pre-existing known-expected failure (test_admin_detail_contract_does_declare_trust_tier, resolves at 48-07) and zero new/unexpected failures."
    requirement: "TRUST-02"
    verification:
      - kind: other
        ref: "./.venv/bin/python -m pytest api/tests pipeline/tests tests -q -> 1 failed (known-expected), 1146 passed, 5 xfailed, 0 unexpected"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-08-19
status: complete
---

# Phase 48 Plan 06: Offline recompute-trust CLI Summary

**A new `python -m pipeline recompute-trust` command (`--all` / `--argument-id` / `--dry-run`) that re-derives every argument's `trust_tier` through the same `recompute_argument_tier` service every writer calls, reports an accurate scanned/unchanged/changed count, and is now the phase's falsifiable drift-repair-and-verification vehicle for plan 48-09.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2/2 complete
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `pipeline/commands/recompute_trust.py` (NEW) — `run_recompute_trust(args)`: builds a deterministic id list (`select(Argument.id).order_by(Argument.id)` for `--all`, or a single validated id for `--argument-id`), opens one `get_session()` transaction per argument (so a mid-scan failure leaves earlier repairs durable), calls `recompute_argument_tier` per row, and prints a per-changed-argument line plus a final `scanned/unchanged/changed` summary — stating the changed count explicitly even when it is zero, which is the exact assertion plan 48-09 reads. `--dry-run` computes the real recompute and then rolls the session back before the context manager's own commit, so the report is accurate but nothing is written. An unknown `--argument-id` raises `ValueError` naming the missing id before any recompute work runs.
- `pipeline/__main__.py` — wired the `recompute-trust` subparser (required mutually exclusive `--all`/`--argument-id` group plus standalone `--dry-run`), the `elif args.command == "recompute-trust"` dispatch branch, the import, and a module-docstring subcommand entry; also corrected `import-convokit`'s help text, which previously named the retired `status=pipeline` born state, to name the current `status=candidate` state (48-RESEARCH.md's low-priority accuracy pass, owned by this plan since it touches this same file).
- `pipeline/tests/test_recompute_trust.py` (NEW) — 6 DB-gated tests covering repair, an accurate changed count, idempotence on re-run, dry-run's no-write guarantee, `--argument-id` scoping, the unknown-id `ValueError`, and the empty-database edge. Reuses plan 48-01's `_seed_argument`/`_teardown_argument` helper from `api/tests/test_trust_recompute.py` rather than duplicating the seeding logic, bootstrapping `AsyncSessionLocal` via a module-local FastAPI-lifespan fixture since `pipeline/tests/` has no equivalent of `api/tests/conftest.py`'s autouse `_api_lifespan`. Adds a function-scoped, genuinely committed TRUNCATE fixture (mirroring `pipeline/tests/conftest.py`'s session-scoped `_reset_test_db` hard safety guard) so `--all`'s whole-table scan is deterministic regardless of what else ran earlier in the same pytest session.
- Full-repo suite: 1 failed (the pre-existing, tracked, known-expected `test_admin_detail_contract_does_declare_trust_tier`, resolves at 48-07), 1146 passed, 5 xfailed, 0 unexpected failures.

## Task Commits

Each task was committed atomically:

1. **Task 1: The recompute-trust command and its CLI wiring** - `97325ce72` (feat)
2. **Task 2: Coverage for repair, change-counting, idempotence, and the empty case** - `9cc2f5b8c` (test)

## Files Created/Modified
- `pipeline/commands/recompute_trust.py` - `run_recompute_trust(args)` (Task 1)
- `pipeline/__main__.py` - `recompute-trust` subparser + dispatch + docstring entry; import-convokit help-text fix (Task 1)
- `pipeline/tests/test_recompute_trust.py` - 6-test DB-gated suite + two module-local fixtures (Task 2)

## Decisions Made
See `key-decisions` in frontmatter for the lifespan-bootstrap fixture, the committed-TRUNCATE fixture rejection of `clean_db`, and the `args.argument_id is not None` branch choice.

## Deviations from Plan

None - plan executed exactly as written. No Rule 1/2/3 auto-fixes were needed; the implementation matched `api/services/trust.py`'s actual signature and `pipeline/db.py`'s actual commit-on-clean-exit contract on the first pass, verified by every acceptance criterion in the plan passing without modification.

## TDD Gate Compliance

Task 2 carried `tdd="true"`, but this plan's own task ordering places the implementation (Task 1, `feat`) before the test task (Task 2, `test`) — the reverse of the strict RED-then-GREEN commit order the TDD gate normally checks for. This is a plan-authored ordering, not an executor deviation: Task 1's `<action>` builds the command and Task 2's `<action>` explicitly says to write tests "as written in Task 1" against the already-existing implementation, mirroring plan 48-01's own Task 2/3 pattern (pure/DB-gated coverage written after an already-approved Task 1 implementation). Both commits exist (`97325ce72` feat, `9cc2f5b8c` test) and all 6 tests passed on their first run against the already-correct implementation — there was no RED phase to observe because there was no unimplemented behavior at test-writing time.

## Issues Encountered

None. Every plan-specified acceptance criterion (CLI help text, argparse mutual-exclusivity error, AST import checks, HTTP-surface grep, docstring checks, born-state text check, `compileall`, and all pytest runs) passed without modification on first execution.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `python -m pipeline recompute-trust --all` is ready for plan 48-09 to run against a freshly reseeded fixture as the phase's positive, falsifiable proof that every one of the phase's writer paths (48-01 through 48-05, plus whatever 48-07/48-08 add) stamped `Argument.trust_tier` correctly at write time.
- `--argument-id` and `--dry-run` are available for ad-hoc operator drift inspection/repair outside the verification flow.
- No HTTP surface was added anywhere in this plan (AST + grep criteria both confirm) — the pipeline-offline-only constraint (CLAUDE.md) is intact.
- Full-repo suite baseline for subsequent plans: 1 failed (known-expected, resolves at 48-07), 1146 passed, 5 xfailed, 0 unexpected.

## Self-Check: PASSED

- FOUND: pipeline/commands/recompute_trust.py
- FOUND: pipeline/tests/test_recompute_trust.py
- FOUND: pipeline/__main__.py (modified)
- FOUND commit: 97325ce72
- FOUND commit: 9cc2f5b8c

---
*Phase: 48-trust-lifecycle*
*Completed: 2026-08-19*
