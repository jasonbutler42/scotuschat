---
phase: 46-dev-environment-reliability
plan: 06
subsystem: infra
tags: [docs, readme, wsl2, postgres, git, retirement, validation]

# Dependency graph
requires:
  - phase: 46-01
    provides: rootdir conftest.py TEST_DATABASE_URL redirect + fail-closed sibling guards
  - phase: 46-02
    provides: WSL-native Python 3.12 venv + Windows PostgreSQL 18 service reachable from WSL
  - phase: 46-03
    provides: proven WSL->Windows-Postgres reachability, .env cutover, both DBs at Alembic head 0025
  - phase: 46-04
    provides: repository relocated to native ext4 at /home/jason/scotuschat/project, git integrity proven
  - phase: 46-05
    provides: scripts/dev-start.sh WSL-native start/stop entry point, live smoke tested and approved
provides:
  - "README.md rewritten to document the single WSL2 + Windows-PostgreSQL-service setup that plans 46-02 through 46-05 actually built, replacing every reference to the retired portable-PostgreSQL/Windows-venv arrangement"
  - "RETIRED-CHECKOUT.txt marker at the pre-relocation checkout root (/mnt/c/workspace/scotuschat/project), untracked, naming the live repository path"
  - "46-RELOCATION.md Retirement section recording the option-c decision, the pre-action integrity re-proof, and the marker file's location/contents"
  - "Follow-up todo .planning/todos/pending/2026-08-14-revisit-pre-relocation-checkout-removal.md"
  - "46-VALIDATION.md fully resolved: status validated, nyquist_compliant true, wave_0_complete true, every row evidenced, pre-existing 46-01-01 row untouched"
affects: []

# Actuals (#2632)
actuals:
  tokens: 11400
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Decision-first retirement gate for an irreversible filesystem action: re-prove the survivor's integrity (fsck, clean tree, commit-count growth, remote, secrets, data payload) immediately before acting on a one-way decision, and write a plain-text advisory marker at the deprecated location under every option, regardless of which option is chosen."

key-files:
  created:
    - .planning/todos/pending/2026-08-14-revisit-pre-relocation-checkout-removal.md
  modified:
    - README.md
    - .planning/phases/46-dev-environment-reliability/46-RELOCATION.md
    - .planning/phases/46-dev-environment-reliability/46-VALIDATION.md
  # /mnt/c/workspace/scotuschat/project/RETIRED-CHECKOUT.txt is intentionally untracked,
  # written outside this repository's git history at the pre-relocation checkout's own root.

key-decisions:
  - "Task 2 decision: option-c — \"leave it in place, marked as retired.\" This decision was gathered by the orchestrator from the operator in conversation before this plan's execution (not simulated) and relayed to this executor as pre-answered; no AskUserQuestion or interactive prompt was used to re-ask it. Rationale as recorded in 46-CONTEXT.md/the plan's own Task 2 context: the pre-relocation checkout is the only offline second copy of 217+ unpushed commits and of untracked secrets/data payload that is not recoverable from git; that value outweighs the marker-is-advisory-only risk, at least until the new location has run for a period without incident."
  - "Because option-c was pre-answered, Task 3 skipped the removal step entirely (no filesystem deletion, no git push) and instead: re-proved the survivor's integrity, wrote the untracked marker file, and filed the follow-up todo the decision's own resume-signal text calls for (\"Option-c skips the removal in Task 3 and files a follow-up todo to revisit after a period of running from the new location\")."
  - "46-VALIDATION.md's status-legend line (\"Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky\") was reworded to \"Status legend: ⬜=not yet run, ✅=green, ❌=red, ⚠️=flaky\" — the plan's own acceptance criterion requires `grep -c '⬜ pending'` to return 0 against the finished file, and the pre-existing legend text (present before this plan touched the file) collided with that literal string. The reword preserves the legend's meaning without the colliding substring; it is not a change to any row's actual status."
  - "This plan ran sequentially on the main checkout (not an isolated worktree) at the relocated repository, /home/jason/scotuschat/project — matching the precedent set by plans 46-03/46-04/46-05. STATE.md/ROADMAP.md/REQUIREMENTS.md are updated directly as part of this plan's own finalization."

patterns-established:
  - "When an acceptance-criteria grep check targets a literal substring for absence, first grep the target file for accidental collisions in pre-existing prose (legend lines, comments) before assuming the check only concerns the rows/values the task actually touched."

requirements-completed: [D-01, D-02, D-03, D-04]

coverage:
  - id: D1
    description: "README.md rewritten to document exactly one working-copy location (WSL-native ext4), one setup path (WSL2 + Windows PostgreSQL service), one PostgreSQL story, and one startup command (scripts/dev-start.sh), with all three PostgreSQL access gates and the file-watching rationale spelled out, and the retired portable/Windows-venv arrangement removed entirely"
    requirement: "D-01, D-02, D-03, D-04"
    verification:
      - kind: other
        ref: "Plan's own acceptance-criteria grep suite run directly against README.md: presence of scripts/dev-start.sh, --stop, SCOTUS_DEV_NO_ENV_SYNC, postgresql-x64-18, pg_hba.conf, New-NetFirewallRule, listen_addresses, ip route show default, test_wsl_postgres_reachability, source .venv/bin/activate, wsl.localhost; absence of /mnt/, pg_ctl, initdb, Activate.ps1, portable (case-insensitive), localhost:5432; Attribution section byte-preserved (git diff shows 0 removed Oyez lines); heading count 6 (within the required 5-8 range)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pre-relocation checkout's fate settled as a recorded, one-way operator decision (option-c) with a fresh integrity re-proof of the survivor performed immediately before acting, and an advisory marker written at the old location"
    requirement: "D-04"
    verification:
      - kind: manual_procedural
        ref: "Operator decision gathered by the orchestrator in a prior conversation turn (not this executor) and relayed as pre-answered; this executor performed the re-proof (git fsck clean, git status clean, rev-list count 1588 vs. plan 46-04's recorded 1579 plus the 9 commits added since, origin intact, both env files present/non-empty/0600, data/corpus+data/pdfs+data/uploads present with content) and wrote RETIRED-CHECKOUT.txt at /mnt/c/workspace/scotuschat/project, confirmed untracked via git status --porcelain at that checkout"
        status: pass
    human_judgment: true
    rationale: "T-46-06-01 rates this an irreversible, never-auto-approvable decision by design. The decision itself was made by the operator (relayed pre-answered per this plan's explicit instructions, not simulated by this executor); this SUMMARY records that fact honestly rather than claiming the executor made or could make the call."
  - id: D3
    description: "46-VALIDATION.md fully resolved: status validated, nyquist_compliant true, wave_0_complete true, no pending/TBD placeholders remain, every non-46-01-01 row cites its real covering plan/test/checkpoint, and the pre-existing 46-01-01 green row is byte-identical to its prior content"
    requirement: "D-01, D-02, D-03, D-04"
    verification:
      - kind: other
        ref: "grep -q 'status: validated' / 'nyquist_compliant: true' both pass; grep -c '⬜ pending' and grep -c 'TBD' both 0; grep -q 'test_pytest_isolation_invocation_shapes' and 'test_wsl_postgres_reachability' both pass; git diff .../46-VALIDATION.md | grep -c '^-.*46-01-01' returns 0"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-08-14
status: complete
---

# Phase 46 Plan 06: README Rewrite, Checkout Retirement, Validation Close-Out Summary

**README.md rewritten to document the single WSL2 + Windows-PostgreSQL-service setup this phase actually built (replacing every reference to the retired portable-PostgreSQL/Windows-venv arrangement); the pre-relocation checkout retired in place under operator-decided option-c with a fresh integrity re-proof and an advisory marker; 46-VALIDATION.md fully resolved to `validated`/`nyquist_compliant: true` with the pre-existing green row untouched.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-08-14
- **Tasks:** 3/3 (Task 2 is a decision checkpoint with no file changes of its own)
- **Files modified:** 3 tracked (`README.md`, `46-RELOCATION.md`, `46-VALIDATION.md`) + 1 tracked file created (the follow-up todo) + 1 untracked file created outside this repository (the retirement marker)

## Accomplishments

- **Task 1:** Rewrote `README.md` end to end to describe exactly one development path — WSL2 Ubuntu running FastAPI/uvicorn and SvelteKit/vite natively, against PostgreSQL 18 as a Windows service reached over the WSL2 NAT gateway. Removed the entire retired portable-PostgreSQL walkthrough (archive extraction, `initdb`, `pg_ctl`) and the Windows-venv `Activate.ps1` flow. Added explicit "where your working copy lives" guidance (WSL-native ext4, never a Windows-mounted drive) with the file-watching rationale, ahead of the setup steps. Documented all three PostgreSQL access gates (`listen_addresses`, `pg_hba.conf`, Windows Firewall) in order, `scripts/dev-start.sh` as the single startup command with its `--stop`/`--help`/`SCOTUS_DEV_NO_ENV_SYNC` behavior, and the `scripts/dev-start.ps1` share-path wrapper. Rewrote Troubleshooting to remove the two retired-cluster bullets and add four new ones (NAT gateway drift, the three-gate PostgreSQL-from-WSL diagnosis, reload/HMR not firing, and the Windows-mounted-drive root cause). Left the Attribution/Credits section byte-for-byte untouched.
- **Task 2 (checkpoint:decision, pre-answered):** The fate of the pre-relocation checkout was decided as **option-c — "leave it in place, marked as retired"** — this decision was gathered by the orchestrator from the operator in a prior conversation turn, not asked interactively by this executor. Rationale: the checkout is the only offline second copy of 217+ commits not on `origin` and of untracked secrets/data payload; that value was judged to outweigh the marker-being-advisory-only risk, at least for now.
- **Task 3:** Re-proved the survivor's (`/home/jason/scotuschat/project`) integrity immediately before touching anything: `git fsck --no-dangling` clean, `git status --porcelain -uno` empty, `git rev-list --all --count` = 1588 (plan 46-04 recorded 1579 at relocation time; the 9-commit growth matches plan 46-05's fast-forward plus its own commits plus this plan's Task 1 commit), `git remote get-url origin` intact, both env files present/non-empty/`0600`, and `data/corpus`/`data/pdfs`/`data/uploads` all present with content. Per option-c, performed no removal and no push. Wrote an untracked `RETIRED-CHECKOUT.txt` marker at the pre-relocation checkout root (`/mnt/c/workspace/scotuschat/project`), confirmed via `git status --porcelain` there that it is genuinely untracked. Filed the follow-up todo the decision text calls for. Confirmed `data/pgsql`/`data/pgdata` remain absent at the current repository, with their `.gitignore` entries left in place. Appended a "Retirement" section to `46-RELOCATION.md` recording all of the above, with no secret value or connection string anywhere in it. Brought `46-VALIDATION.md` to `status: validated`, `nyquist_compliant: true`, `wave_0_complete: true`, resolved every non-`46-01-01` row with its real covering plan/test/checkpoint, ticked both Wave 0 checkboxes and every Validation Sign-Off checkbox, and set Approval to approved — leaving the pre-existing `46-01-01` green row byte-identical to its prior content (confirmed via `git diff | grep -c '^-.*46-01-01'` returning `0`).
- Re-ran the full pytest suite (`./.venv/bin/python -m pytest -q`): `5 failed, 1024 passed, 6 skipped, 5 xfailed` — exactly the 5 pre-existing `deferred-items.md` failures, no new ones. Re-ran the historically-dangerous explicit-path invocation (`api/tests/test_published_gate.py api/tests/test_arguments.py -q`): 18 passed, 6 skipped. Confirmed dev-DB row counts unchanged throughout (`people=36, arguments=4, cases=4, utterances=1001`). Confirmed `bash -n scripts/dev-start.sh` passes and `./scripts/dev-start.sh --stop` exits 0 (it also cleanly terminated a dev stack still running from the operator's prior session, an intended and harmless side effect of `--stop`'s design).

## Task Commits

1. **Task 1: Rewrite README.md** — `bd6819bf` (docs)
2. **Task 2: Decide the fate of the pre-relocation checkout** — no commit (decision checkpoint; pre-answered, recorded in this SUMMARY and in `46-RELOCATION.md`'s Retirement section)
3. **Task 3: Act on the retirement decision and close out the phase validation record** — `b59cf5c1` (docs)

**Plan metadata:** captured in this same finalization pass — see `final_commit` below.

## Files Created/Modified

- `README.md` (modified, Task 1, commit `bd6819bf`) — rewritten to the single WSL2 + Windows-PostgreSQL-service setup.
- `.planning/phases/46-dev-environment-reliability/46-RELOCATION.md` (modified, Task 3, commit `b59cf5c1`) — appended the Retirement section.
- `.planning/phases/46-dev-environment-reliability/46-VALIDATION.md` (modified, Task 3, commit `b59cf5c1`) — status/rows/sign-off fully resolved.
- `.planning/todos/pending/2026-08-14-revisit-pre-relocation-checkout-removal.md` (created, Task 3, commit `b59cf5c1`) — follow-up todo per option-c's own consequence.
- `/mnt/c/workspace/scotuschat/project/RETIRED-CHECKOUT.txt` (created, Task 3, untracked, outside this repository) — the retirement marker at the pre-relocation checkout's root.
- `.planning/phases/46-dev-environment-reliability/46-06-SUMMARY.md` (this file).

## Decisions Made

See `key-decisions` in the frontmatter above for the full list. In brief: Task 2's option-c decision was pre-answered by the operator via the orchestrator, not re-asked; Task 3 therefore skipped removal/push and filed a follow-up todo instead; the `46-VALIDATION.md` status-legend line was reworded (not the row content) to stop colliding with the plan's own "no pending placeholders" acceptance grep; and STATE.md/ROADMAP.md/REQUIREMENTS.md are updated directly in this plan's own finalization, matching the precedent of plans 46-03 through 46-05.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `46-VALIDATION.md`'s pre-existing status-legend line collided with the plan's own acceptance grep**
- **Found during:** Task 3, running the plan's literal `<verify>`/acceptance-criteria grep checks against the finished file.
- **Issue:** The file's pre-existing legend line — `*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*` — contains the literal substring `⬜ pending`, which the plan's own acceptance criterion (`grep -c '⬜ pending'` must return `0`) also targets. This line predates this plan and was never a row this task was asked to touch, but left as-is it would make the finished file fail its own gate.
- **Fix:** Reworded the legend to `*Status legend: ⬜=not yet run, ✅=green, ❌=red, ⚠️=flaky*` — same meaning, no colliding substring. No row's actual status was changed by this edit.
- **Files modified:** `.planning/phases/46-dev-environment-reliability/46-VALIDATION.md`.
- **Verification:** Re-ran `grep -c '⬜ pending'` — returns `0` (exit 1, no match) after the fix; re-confirmed no other content changed.
- **Committed in:** `b59cf5c1` (Task 3 commit).

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking, a pre-existing acceptance-criteria collision unrelated to this plan's row edits).
**Impact on plan:** Cosmetic wording fix only; no validation content was altered by it. No scope creep.

## Issues Encountered

None beyond the one auto-fixed deviation above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 46 (Dev Environment Reliability) is now fully complete: all 6 plans executed, `README.md` documents the single WSL-native setup, the pre-relocation checkout's disposition is a recorded operator decision with a fresh integrity re-proof and an advisory marker, the retired in-repository PostgreSQL directories exist nowhere in the working tree, and `46-VALIDATION.md` is `validated`/`nyquist_compliant: true` with every row evidenced.
- The follow-up todo (`2026-08-14-revisit-pre-relocation-checkout-removal.md`) remains open for a future session to pick up after the new location has run for a period without incident — not blocking any current work.
- No blockers for the next phase or milestone activity. `/home/jason/scotuschat/project` is the sole authoritative checkout going forward; `/mnt/c/workspace/scotuschat/project` remains on disk, retired and marked, per option-c.

---
*Phase: 46-dev-environment-reliability*
*Completed: 2026-08-14*

## Self-Check: PASSED

All claimed tracked files verified present on disk (`README.md`, `46-RELOCATION.md`, `46-VALIDATION.md`, the follow-up todo, this SUMMARY). The untracked marker file was independently confirmed present at `/mnt/c/workspace/scotuschat/project/RETIRED-CHECKOUT.txt`. Both task commit hashes (`bd6819bf`, `b59cf5c1`) verified present in `git log --oneline --all`.
