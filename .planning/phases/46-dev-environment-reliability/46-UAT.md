---
status: complete
phase: 46-dev-environment-reliability
source: [46-01-SUMMARY.md, 46-02-SUMMARY.md, 46-03-SUMMARY.md, 46-04-SUMMARY.md, 46-05-SUMMARY.md, 46-06-SUMMARY.md]
started: 2026-08-14T21:45:10Z
updated: 2026-08-15T00:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Rootdir conftest.py redirects every pytest invocation shape
expected: conftest.py relocated to the pytest rootdir; tests/conftest.py deleted; all three pytest invocation shapes (bare, explicit single file, explicit multi-path) redirect DATABASE_URL to TEST_DATABASE_URL correctly
result: pass
source: automated
coverage_id: D1

### 2. Sibling conftests fail closed if the rootdir redirect didn't fire
expected: Both sibling conftests (api/tests, pipeline/tests) fail closed with a loud AssertionError if TEST_DATABASE_URL is set but the rootdir sentinel did not fire
result: pass
source: automated
coverage_id: D2

### 3. CLAUDE.md documents the rootdir-conftest invariant
expected: CLAUDE.md records the rootdir-conftest invariant referencing D-03 and the regression test by name
result: pass
source: automated
coverage_id: D3

### 4. WSL-native Python 3.12 venv with pinned deps
expected: .venv is WSL-native Python 3.12 with pinned deps installed; test_command repointed; plan 46-01's regression test passes under the new interpreter
result: pass
source: automated
coverage_id: T2

### 5. Dev-only admin router gate intact after cutover
expected: Dev-only admin router allow-list gate re-verified intact after the environment cutover
result: pass
source: automated
coverage_id: T3

### 6. Windows PostgreSQL 18 service reachable from WSL
expected: postgresql-x64-18 service running, TCP-reachable from WSL on 5432, scoped to the live WSL subnet; scotus/scotus_test databases exist
result: pass
coverage_id: T1

### 7. WSL-native process reaches Windows Postgres over dynamic gateway
expected: A WSL-native process opens a real connection to the Windows Postgres service using the dynamically-resolved Windows host IP and gets a result back from SELECT 1
result: pass
source: automated
coverage_id: D1

### 8. Stale .env host fails loudly with a corrected DSN
expected: A stale Windows host IP in .env fails loudly with the corrected value (password-redacted, copy-pasteable DSN), proven by a recorded negative control rather than asserted from code
result: pass
source: automated
coverage_id: D2

### 9. Schema at Alembic head, no Base.metadata.create_all anywhere
expected: The schema on the new service is at Alembic head and scotus_test is provisioned, without any use of Base.metadata.create_all
result: pass
source: automated
coverage_id: D3

### 10. Dev DB seeded through the supported reset-to-fixture path
expected: The dev database is seeded with fixture data through the existing supported POST /api/admin/dev/reset-to-fixture path, with resulting row counts recorded
result: pass
source: automated
coverage_id: D4

### 11. Full suite green with dev-DB row counts unchanged, fail-closed control proven
expected: |
  The full suite is green under bare `pytest -q` AND the exact explicit-path invocation
  that wiped the dev DB during Phase 45, with dev-DB row counts byte-identical across
  every invocation shape, and a fail-closed control proving the guard aborts when the
  rootdir redirect is absent. This is the priority bug this phase exists to close.
  Already approved by the operator during 46-03 execution on this exact row-count/
  fail-closed evidence, and independently re-verified twice since (46-03 finalization,
  and again just now by the phase's goal-verification agent, which re-ran the literal
  Phase 45 wipe command and confirmed row counts unchanged). Confirming here closes the loop.
result: pass
coverage_id: D5

### 12. Repository relocated to native ext4 with byte-identical git history
expected: The working repository exists at /home/jason/scotuschat/project on native ext4 with byte-identical git history (same HEAD SHA, same total commit count) and an intact origin remote
result: pass
source: automated
coverage_id: D1

### 13. Untracked load-bearing files present and byte-identical at new location
expected: Every untracked-but-load-bearing file (.env, app/.env, data/corpus, data/pdfs, data/uploads, memory/, .claude/, untracked .planning/ notes) is present at the new location, and the two secret files are byte-identical to their originals and owner-only (0600)
result: pass
source: automated
coverage_id: D2

### 14. WSL-native venv and node_modules rebuilt, not copied
expected: A WSL-native Python 3.12 venv and a WSL-native node_modules exist at the new location, rebuilt from the pinned manifests rather than copied
result: pass
source: automated
coverage_id: D3

### 15. Windows Postgres still reachable from the relocated repo
expected: From the new location, a WSL-native process still reaches the Windows PostgreSQL 18 service over the dynamically-resolved gateway and both databases still report Alembic head
result: pass
source: automated
coverage_id: D4

### 16. Operator has cut their own tooling over to the new location
expected: |
  The operator has cut their own tooling over to /home/jason/scotuschat/project — a
  WSL-connected editor is open there, a save round-trips, and every Windows-side entry
  point that pointed at the old location (/mnt/c/workspace/scotuschat/project) has been
  repointed or confirmed not to exist.
result: pass
coverage_id: D5

### 17. Repo fast-forwarded to pre-relocation HEAD with zero divergence
expected: The relocated repo's git history is fast-forwarded to the pre-relocation checkout's HEAD with proven zero divergence, no leftover temporary remote, and untracked .planning/ catch-up material mirrored without permission corruption
result: pass
source: automated
coverage_id: D1

### 18. dev-start.sh committed executable, supports --help/--stop/bad-flag
expected: scripts/dev-start.sh exists, is committed with the executable bit (mode 100755), passes bash -n, and correctly supports --help/--stop/--badflag argument handling
result: pass
source: automated
coverage_id: D2

### 19. Vite dev server has explicit config, no polling, builds cleanly
expected: app/vite.config.ts has an explicit server block (all-interfaces bind, port 5173, strict port) with no watcher-polling configuration, and the frontend still builds cleanly
result: pass
source: automated
coverage_id: D3

### 20. dev-start.ps1 reduced to a thin wsl.exe wrapper
expected: scripts/dev-start.ps1 is reduced to a sub-35-line share-path-aware wsl.exe wrapper with no PowerShell job machinery or in-repository database handling
result: pass
source: automated
coverage_id: D4

### 21. Dev logs and .env.bak gitignored
expected: .dev-logs/ and .env.bak are gitignored
result: pass
source: automated
coverage_id: D5

### 22. Live start/stop smoke test and reload proof
expected: |
  Running scripts/dev-start.sh brings up both services live; a Windows-side browser
  reaches both (http://localhost:5173 and the API); and a save from a WSL-connected
  editor triggers a live reload. Already approved by the operator during 46-05
  execution — that session surfaced and fixed two real bugs (a wait_for_http script
  bug, and a documented Windows-side orphaned-process gotcha). Confirming here closes
  the loop on the single reliable start/stop entry point this phase set out to deliver.
result: pass
coverage_id: D6

### 23. README documents exactly one setup path
expected: README.md rewritten to document exactly one working-copy location (WSL-native ext4), one setup path (WSL2 + Windows PostgreSQL service), one PostgreSQL story, and one startup command (scripts/dev-start.sh), with the retired portable/Windows-venv arrangement removed entirely
result: pass
source: automated
coverage_id: D1

### 24. Validation record fully resolved, no placeholders
expected: 46-VALIDATION.md fully resolved — status validated, nyquist_compliant true, wave_0_complete true, no pending/TBD placeholders remain, every row cites its real covering plan/test/checkpoint
result: pass
source: automated
coverage_id: D3

### 25. Pre-relocation checkout's fate settled as an explicit decision
expected: |
  The pre-relocation checkout's fate is settled as a recorded, one-way operator
  decision (option-c: "leave it in place, marked as retired"), with a fresh integrity
  re-proof of the survivor performed immediately before acting, and an advisory marker
  (RETIRED-CHECKOUT.txt) written at the old location (/mnt/c/workspace/scotuschat/project).
  This decision was relayed pre-answered by the operator in an earlier conversation turn.
result: pass
coverage_id: D2

## Summary

total: 25
passed: 25
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
