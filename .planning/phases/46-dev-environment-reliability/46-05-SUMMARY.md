---
phase: 46-dev-environment-reliability
plan: 05
subsystem: infra
tags: [wsl2, bash, dev-tooling, uvicorn, vite, powershell, postgres, setsid]

# Dependency graph
requires:
  - phase: 46-01
    provides: rootdir conftest.py TEST_DATABASE_URL redirect + fail-closed sibling guards
  - phase: 46-02
    provides: WSL-native Python 3.12 venv + Windows PostgreSQL 18 service reachable from WSL
  - phase: 46-03
    provides: proven WSL->Windows-Postgres reachability, .env cutover, both DBs at Alembic head 0025
  - phase: 46-04
    provides: repository relocated to native ext4 at /home/jason/scotuschat/project, WSL-native venv/node_modules rebuilt there
provides:
  - "scripts/dev-start.sh -- WSL-native start/stop entry point with dynamic host-IP resolution, .env host self-heal/refuse, a bash /dev/tcp PostgreSQL reachability probe naming all three access gates, an Alembic migration gate, setsid -w process-group launches for uvicorn and vite, real HTTP health polling, a trap-based teardown, and a --stop path"
  - "scripts/dev-start.ps1 -- reduced to an 18-line share-path-aware wsl.exe wrapper deriving the WSL repo root from its own \\\\wsl.localhost\\ location"
  - "app/vite.config.ts -- explicit server block (all-interfaces bind, port 5173, strict port), no watcher-polling workaround"
  - ".gitignore entries for .dev-logs/ and .env.bak"
  - "Task 1's fast-forward: DST's git history caught up to the pre-relocation checkout (SRC) HEAD with proven zero divergence"
affects: [46-06]

# Actuals (#2632)
actuals:
  tokens: 2575
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "setsid -w (not bare setsid) for reliable process-group capture: util-linux's setsid, invoked as a plain backgrounded job with no options, forks internally and exits immediately -- verified empirically on this machine that a background `setsid sleep 5 &` produces a different PID for the actual sleep process than bash's own $! reports, which would silently break group-kill teardown. `setsid -w PROG` execs directly with no internal fork, so $! == PID == PGID == SID of PROG itself, and `kill -TERM -- \"-$!\"` correctly reaches the whole group -- confirmed directly with ps and a live kill test before writing it into the script."
    - "Append `|| true` to any `$(cmd | grep ...)` pipeline whose grep is expected to legitimately find nothing (e.g. probing for a not-yet-running listener) when the script runs under `set -euo pipefail` -- otherwise grep's own exit 1 aborts the whole script silently, with pipefail promoting it past the assignment. Applies to stop_ports' pid lookup and _extract_env_host's/resolve_win_host_ip's equivalent expressions."

key-files:
  created:
    - scripts/dev-start.sh
  modified:
    - scripts/dev-start.ps1
    - app/vite.config.ts
    - .gitignore

key-decisions:
  - "Task 1's rsync catch-up of untracked .planning/ material used -rt (content/mtime comparison only) with --no-perms/--no-owner/--no-group instead of a plain archive-mode rsync, after a dry run showed every SRC file (mounted via 9p/DrvFs) reports permissions as rwxrwxrwx -- an unmodified archive-mode rsync would have propagated that onto every already-correct tracked file at DST, which core.filemode=true (corrected in plan 46-04) would then have registered as a modified executable bit across the entire tracked .planning/ tree. A second dry run confirmed only genuinely new content (an untracked verify-scripts __pycache__ directory) was picked up once this was fixed; the actual transfer moved only that."
  - "Fixed two real bugs in scripts/dev-start.sh before committing (Rule 1 auto-fix), both the same underlying class -- a `set -e`/`pipefail` abort on a pipeline whose rightmost failing stage (grep, when it finds nothing) is expected and benign: (1) empirically confirmed setsid's fork behavior with a live ps test (see tech-stack pattern above) and switched every launch from bare `setsid` to `setsid -w`; (2) `./scripts/dev-start.sh --stop` was run before commit and observed to print nothing and exit 1 instead of the expected 'nothing listening' message -- root-caused to stop_ports' `ss | grep -oE 'pid=...' | cut | sort` pipeline aborting the script under pipefail when grep matched nothing, fixed by appending `|| true`, and re-verified `--stop` then printed the correct message and exited 0."
  - "Task 3 (the live start/stop smoke and reload proof) is a blocking checkpoint requiring the operator's own WSL-connected editor, a real Windows-side browser round trip, and live judgment of reload timing -- not simulated by the executor, per explicit instruction. This SUMMARY is written and committed now, with Tasks 1-2 complete, so a fresh continuation agent has the full record without re-deriving it. STATE.md/ROADMAP.md are intentionally left unchanged in this commit, per the orchestrator's instruction that they are updated only if the entire plan completes without pausing at a checkpoint -- it has not."

patterns-established:
  - "setsid -w over bare setsid whenever a backgrounded process's PGID must be captured reliably via $! for later negative-PID group-kill teardown."

requirements-completed: []

coverage:
  - id: D1
    description: "DST's git history is fast-forwarded to the pre-relocation checkout's (SRC) HEAD with proven zero divergence, no leftover temporary remote, and untracked .planning/ catch-up material mirrored without permission corruption"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "git rev-parse HEAD identical at SRC and DST (b5b069752bc1068af35f3c3fbf3e4b127a546307); git remote prints exactly origin; git status --porcelain -uno empty; git fsck --no-dangling exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/dev-start.sh exists, is committed with the executable bit (mode 100755), passes bash -n, and correctly supports --help/--stop/--badflag argument handling"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "bash -n scripts/dev-start.sh exit 0; git ls-files -s scripts/dev-start.sh reports 100755; ./scripts/dev-start.sh --help exit 0; ./scripts/dev-start.sh --stop exit 0 reporting nothing found; ./scripts/dev-start.sh --badflag exit 2"
        status: pass
    human_judgment: false
  - id: D3
    description: "app/vite.config.ts has an explicit server block (all-interfaces bind, port 5173, strict port) with no watcher-polling configuration, and the frontend still builds cleanly"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "sed -n '/server: {/,/}/p' app/vite.config.ts contains strictPort: true and port: 5173; grep for usePolling/watch: both absent; cd app && npx vite build --logLevel warn exits 0"
        status: pass
    human_judgment: false
  - id: D4
    description: "scripts/dev-start.ps1 is reduced to a sub-35-line share-path-aware wsl.exe wrapper with no PowerShell job machinery or in-repository database handling"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "wc -l scripts/dev-start.ps1 = 18; grep for wsl.exe and wsl.localhost both present; grep for Start-Job and pg_ctl both absent"
        status: pass
    human_judgment: false
  - id: D5
    description: ".dev-logs/ and .env.bak are gitignored"
    requirement: "D-03"
    verification:
      - kind: integration
        ref: "git check-ignore -q .dev-logs/api-out.log and git check-ignore -q .env.bak both succeed"
        status: pass
    human_judgment: false
  - id: D6
    description: "Two consecutive live start/stop cycles leave zero surviving processes, the Windows-side browser reaches both services, and a save from a WSL-connected editor triggers HMR/reload with no polling workaround"
    requirement: "D-03"
    verification: []
    human_judgment: true
    rationale: "This is Task 3's live smoke test -- requires the operator's own WSL-connected editor, a real Windows-side browser round trip, and live judgment of reload timing. Not simulated by the executor per explicit instruction. Checkpoint reached, not yet approved -- see the Task 3 section below."

# Metrics
duration: ~50min (Tasks 1-2 this session; Task 3 checkpoint pending)
completed: 2026-08-14
status: halted
---

# Phase 46 Plan 05: WSL-Native Start/Stop Entry Point Summary (Tasks 1-2 complete, Task 3 checkpoint pending)

**WSL-native `scripts/dev-start.sh` with dynamic host resolution, a `/dev/tcp` PostgreSQL probe, `setsid -w` process-group launches, real HTTP health polling, and trap-based teardown; a share-path-aware PowerShell wrapper; an explicit Vite server block -- committed and passing every automated check, with the plan's own live human-verify checkpoint (Task 3) reached but not yet run.**

## Performance

- **Duration:** ~50 min (Tasks 1-2 this session; Task 3 not started)
- **Tasks:** 2 of 3 complete
- **Files modified:** 4 (`scripts/dev-start.sh` created, `scripts/dev-start.ps1`/`app/vite.config.ts`/`.gitignore` modified)

## Accomplishments

- **Task 1 (fast-forward continuity gate):** Confirmed this session's working directory is `/home/jason/scotuschat/project` on `ext4` (not the pre-relocation `/mnt/c/workspace/scotuschat/project` 9p mount). Fetched `main` from the pre-relocation checkout as a one-shot local remote and fast-forwarded 4 commits with zero divergence -- both checkouts' HEADs are identical (`b5b069752bc1068af35f3c3fbf3e4b127a546307`), `git remote` still lists only `origin`, `git status --porcelain -uno` is clean, and `git fsck --no-dangling` exits 0. Mirrored the one piece of untracked `.planning/` catch-up material found at the old checkout (a stray `__pycache__` directory under `phases/43-dev-only-reset-to-fixture/verify-scripts/`) via a permission-safe rsync.
- **Task 2 (dev-start.sh / dev-start.ps1 / vite.config.ts / .gitignore):** Built the full WSL-native start/stop entry point per the plan's spec -- dynamic `ip route`-based host resolution, a `.env` host self-heal/refuse function scoped to the WSL2 NAT private range, a zero-install `/dev/tcp` PostgreSQL reachability probe naming all three access gates, an Alembic fail-fast gate, `setsid -w` launches for uvicorn and vite (see key-decisions for why `-w` matters), real HTTP health polling with no fixed warm-up sleep, a trap-based teardown, and a `--stop` path. Reduced `scripts/dev-start.ps1` to an 18-line share-path-aware `wsl.exe` wrapper. Added an explicit `server` block to `app/vite.config.ts`. Added `.dev-logs/` and `.env.bak` to `.gitignore`.
- Confirmed nothing is already listening on 8000 or 5173 (`./scripts/dev-start.sh --stop` then `ss -ltn | grep -E ':(8000|5173)'` returns nothing) -- the pre-Task-3-handoff check the plan requires.
- Ran the plan's full literal Task 2 `<verify>` block end-to-end (`bash -n`, `test -x`, `--help`, `--stop`, both `git check-ignore` checks, and `cd app && npx vite build --logLevel warn`) -- all pass, exit 0.

## Task Commits

1. **Task 1: Cutover continuity gate** -- no commit (verification-only + a fast-forward merge, which moves the branch pointer without creating a new commit; the plan's own file spec is "no tracked file is created or edited"). Outcome recorded above and in the fast-forward record below.
2. **Task 2: Build the WSL-native start/stop entry point, wrapper, and Vite server block** -- `82b14b7f` (feat) -- `feat(46-05): WSL-native dev-start.sh, share-path PS1 wrapper, explicit Vite server block`

**Plan metadata:** this SUMMARY's own commit follows immediately after this file (see the completion message for its hash).

## Fast-Forward Record (Task 1)

| | Value |
|---|---|
| DST HEAD before this plan | `94f178a7118375e3fac071153d7011fd5e903c67` |
| SRC HEAD (pre-relocation checkout) | `b5b069752bc1068af35f3c3fbf3e4b127a546307` |
| DST HEAD after fast-forward | `b5b069752bc1068af35f3c3fbf3e4b127a546307` (matches SRC exactly) |
| Commits fast-forwarded | 4 |
| Merge type | fast-forward-only (`git merge --ff-only`) -- no divergence, nothing to reconcile |
| Temporary remote left behind | None -- fetched via a one-shot path argument to `git fetch`, never registered as a named remote; `git remote` shows only `origin` throughout |
| Untracked `.planning/` catch-up | One item: `phases/43-dev-only-reset-to-fixture/verify-scripts/__pycache__/*.cpython-314.pyc` (harmless bytecode cache from prior ad hoc script runs at SRC) |

The 4 fast-forwarded commits carried `.planning/phases/46-dev-environment-reliability/46-RELOCATION.md` and `46-04-SUMMARY.md` (both previously missing at DST, confirmed by a `Read` failure before Task 1 ran) plus `ROADMAP.md`/`STATE.md` updates recording plan 46-04's completion.

## Files Created/Modified

- `scripts/dev-start.sh` (created, mode `100755`) -- the WSL-native start/stop entry point.
- `scripts/dev-start.ps1` (modified, 63 lines -> 18 lines) -- share-path-aware `wsl.exe` wrapper.
- `app/vite.config.ts` (modified) -- explicit `server` block added alongside the pre-existing `plugins` array.
- `.gitignore` (modified) -- `.dev-logs/` and `.env.bak` entries added under a labelled comment.
- `.planning/phases/46-dev-environment-reliability/46-05-SUMMARY.md` (this file).

## Decisions Made

See `key-decisions` in the frontmatter above for the full list. In brief: the Task 1 rsync catch-up was run with permission propagation explicitly disabled after a dry run showed it would otherwise flip every tracked `.planning/` file's executable bit at DST; two real `set -e`/`pipefail` bugs in the new script (setsid's fork behavior, and an expected-empty `grep` inside a pipeline) were found by literally running the script's flag paths before commit and fixed under Rule 1; and this SUMMARY is written now, before Task 3 resolves, so a continuation agent has the full record.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `setsid` (without `-w`) does not give bash's `$!` the actual process-group ID**
- **Found during:** Task 2, before committing -- ran a live test (`setsid sleep 5 &`, then `ps -o pid,ppid,pgid,sid` on both `$!` and the actual `sleep` process) rather than trusting the plan's literal wording alone.
- **Issue:** util-linux's `setsid`, invoked as a plain backgrounded command with no options, forks a child internally and the outer `setsid` process exits immediately -- confirmed empirically: `$!` named a PID that had already exited, while the real `sleep` process ran under a completely different PID/PGID/SID. Had this shipped as originally drafted (bare `setsid uvicorn ... &`), `cleanup`'s `kill -TERM -- "-$API_PGID"` would have targeted a process group that no longer existed, silently failing to tear down the actual uvicorn/vite processes -- exactly the untraceable-orphan failure mode D-01 exists to eliminate.
- **Fix:** Switched both launches to `setsid -w PROG` (`--wait`), which execs directly with no internal fork; re-verified with the same live `ps` test that `$!`, `PID`, `PGID`, and `SID` are now all identical, and that `kill -TERM -- "-$!"` correctly kills the group.
- **Files modified:** `scripts/dev-start.sh` (2 occurrences: the uvicorn launch and the `npm run dev` launch).
- **Verification:** Live `ps`-based test before writing the fix into the script; re-confirmed after.
- **Committed in:** `82b14b7f` (Task 2 commit).

**2. [Rule 1 - Bug] `stop_ports`' pid-lookup pipeline aborted the whole script under `pipefail` when nothing was listening**
- **Found during:** Task 2, running `./scripts/dev-start.sh --stop` before committing -- it printed nothing and exited 1 instead of the expected "nothing listening" message.
- **Issue:** `ss -ltnpH "sport = :${port}" | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u`, assigned directly to a local variable, has `grep` exit 1 whenever no listener matches (the expected, common case). Under `set -euo pipefail`, that non-zero exit propagates through the pipeline and aborts the script at the assignment -- silently, with no error message, before `stop_ports` ever reached its own "nothing listening" branch. The same class of bug existed in `_extract_env_host` (whose internal `grep` can also legitimately match nothing) and in `resolve_win_host_ip`'s `ip route` pipeline.
- **Fix:** Appended `|| true` to all four affected pipelines (both `stop_ports` occurrences, `_extract_env_host`, and `resolve_win_host_ip`), so a benign "found nothing" result becomes an empty string instead of a script-ending abort.
- **Files modified:** `scripts/dev-start.sh` (4 occurrences).
- **Verification:** Re-ran `bash -n`, then `--stop`, `--help`, and `--badflag` -- all now behave correctly (`--stop` prints "Port 8000: nothing listening." / "Port 5173: nothing listening." / "Nothing found listening on 8000 or 5173." and exits 0).
- **Committed in:** `82b14b7f` (Task 2 commit).

---

**Total deviations:** 2 auto-fixed (both Rule 1 -- bugs, both the same underlying `set -e`/`pipefail`-on-expected-empty-result class).
**Impact on plan:** Both fixes are essential for the script's core correctness claim (reliable teardown, deterministic `--stop`). No scope creep -- both fixes stayed inside `scripts/dev-start.sh`, the file the plan already scoped.

## Issues Encountered

- `npx vite build --logLevel warn` from `app/` took roughly 100 seconds end to end on this machine (confirmed via `time`) -- not a hang, and not caused by this plan's changes (the only edit to `vite.config.ts` was the additive `server` block). Noted here only because a shorter ad hoc timeout during verification made it look like a hang at first; re-run with adequate time confirmed a clean exit 0 with only the pre-existing Svelte a11y/reactivity lint warnings already known from plan 46-04.
- No other issues.

## User Setup Required

None -- no external service configuration required. Task 3, when it runs, requires the operator's own WSL-connected editor and a Windows-side browser, which are pre-existing tools, not a new setup step.

## Task 3: Checkpoint Reached, Not Yet Run

Task 3 (`checkpoint:human-verify`, `gate="blocking"`) is the plan's live start/stop smoke test and the D-04 reload proof. It requires the operator to personally run the stack, observe two consecutive clean start/stop cycles from a WSL shell, confirm the Windows-side browser reaches both services, and observe a save from their own WSL-connected editor triggering both a browser HMR update and an API reloader restart. Per explicit instruction, this was not simulated or faked by the executor.

Before handing off, `./scripts/dev-start.sh --stop` was run and `ss -ltn | grep -E ':(8000|5173)'` confirmed to return nothing -- the pre-condition the plan's `<what-built>` section requires before Task 3 begins.

## Next Phase Readiness

- Tasks 1 and 2 are complete and committed (`82b14b7f`). `scripts/dev-start.sh` passes every automated check in the plan's Task 2 `<verify>` block, run in full end to end.
- Task 3 is the phase's functional gate and remains open -- the live smoke test, the D-04 reload proof, the `POST /api/admin/dev/reset-to-fixture` re-verification against an all-interfaces-bound server (threat T-46-05-01), and the verbatim `ps`/`ss` teardown evidence all still need to be captured by a continuation agent once the operator runs through the plan's `<how-to-verify>` steps.
- Plan 46-06 (README rewrite, retiring the pre-relocation checkout) depends on this plan completing -- it is blocked until Task 3 is approved and this SUMMARY is re-finalized with `status: complete`.
- STATE.md and ROADMAP.md are intentionally **not** updated by this commit -- per instruction, they are only updated once the entire plan (all 3 tasks) completes without pausing at a checkpoint. This plan paused.
- No blockers beyond Task 3 itself. SRC (`/mnt/c/workspace/scotuschat/project`) remains untouched and available as a rollback path per plan 46-04's precedent; retiring it is plan 46-06's explicit, gated decision.

---
*Phase: 46-dev-environment-reliability*
*Session recorded: 2026-08-14 (Tasks 1-2; Task 3 checkpoint pending)*

## Self-Check: PASSED

All claimed files verified present on disk (`scripts/dev-start.sh`, `scripts/dev-start.ps1`, `app/vite.config.ts`, `.gitignore`, this SUMMARY) and the Task 2 commit hash (`82b14b7f`) verified present in `git log --oneline --all`.
