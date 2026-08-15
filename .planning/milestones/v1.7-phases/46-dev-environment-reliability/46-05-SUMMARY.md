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
  tokens: 8000
  tasks: 3
  commits: 4

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
  - "Task 3's live smoke test surfaced two real, previously-unknown problems rather than confirming a clean pass on the first try: a script bug (wait_for_http misread Vite's legitimate 404 on the bare '/' route as unhealthy, since this app has no page at that path) and a genuine Windows-side environmental gotcha (an orphaned pre-relocation node.exe process intercepting Windows' own localhost:5173, which broke the WSL2 port-forwarding relay as a second-order effect). The first was fixed and committed (Rule 1); the second is documented in full and flagged for 46-06's README troubleshooting section rather than coded around, since neither dev-start.sh nor dev-start.ps1 caused it or could detect it."
  - "This SUMMARY distinguishes operator-observed facts (browser page load, the CSS live-update via DevTools, general verbal approval) from orchestrator-independently-verified facts (ps/ss process/port evidence, curl status codes captured directly, including a final live re-check at SUMMARY-write time) -- and explicitly does not claim 'two consecutive clean start/stop cycles with zero surviving processes' as directly observed this session, since that specific claim was not separately itemized with before/after ps/ss output beyond what is quoted in the Task 3 section. The plan's Task 2 <verify> block already independently exercised --stop-with-nothing-running at commit time; that stands on its own."

patterns-established:
  - "setsid -w over bare setsid whenever a backgrounded process's PGID must be captured reliably via $! for later negative-PID group-kill teardown."

requirements-completed: [D-01, D-03, D-04]

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
    description: "Live start/stop smoke and reload proof: real bugs found and fixed during the operator's live session, the Windows-side browser reaches both services, and a save from a WSL-connected editor triggers a live update"
    requirement: "D-03"
    verification:
      - kind: manual
        ref: "Operator ran the live stack from a WSL shell; orchestrator independently captured ps -eo pid,pgid,cmd and ss -ltnp showing real WSL-native uvicorn (911649) and npm/vite (911663/911678/911679) processes bound to 0.0.0.0:8000 and *:5173; curl from WSL confirmed 200 on /health and /cases and a real SvelteKit 404 on bare '/'; curl.exe/browser from Windows confirmed 200 on both services after Bug 2's rogue process was killed; operator confirmed the Windows-side browser loaded http://localhost:5173/cases and gave general approval (\"everything looks great and is working as I expected\"); the CSS-variable live-update (D-04 reload proof) was confirmed via DevTools inspection, then reverted (git diff app/src/app.css empty)."
        status: pass
    human_judgment: true
    rationale: "Task 3's live smoke test is not simulated by the executor -- it requires the operator's own WSL-connected editor, a real Windows-side browser round trip, and live judgment of reload timing. Approved after an eventful debugging session that surfaced two real bugs (see Task 3 writeup below): a script bug in wait_for_http (fixed, committed) and a Windows-side orphaned-process environmental gotcha (documented, no code change needed in this plan). Coverage here is honest and partial by design -- see 'What Was and Was Not Directly Observed' below for exactly which claims are operator-observed vs. orchestrator-independently-verified, and which of the plan's 9 how-to-verify steps were not separately itemized this session."

# Metrics
duration: ~50min (Tasks 1-2, prior session) + ~1h operator debugging session (Task 3)
completed: 2026-08-14
status: complete
---

# Phase 46 Plan 05: WSL-Native Start/Stop Entry Point Summary

**WSL-native `scripts/dev-start.sh` with dynamic host resolution, a `/dev/tcp` PostgreSQL probe, `setsid -w` process-group launches, real HTTP health polling, and trap-based teardown; a share-path-aware PowerShell wrapper; an explicit Vite server block -- live-smoke-tested by the operator, who found and the executor fixed a real health-check bug (Bug 1) and surfaced a genuine Windows-side environmental gotcha (Bug 2, flagged for 46-06's README).**

## Performance

- **Duration:** ~50 min (Tasks 1-2, prior session) + ~1h operator debugging session (Task 3, this session)
- **Tasks:** 3 of 3 complete
- **Files modified:** 4 (`scripts/dev-start.sh` created + one Task 3 fix, `scripts/dev-start.ps1`/`app/vite.config.ts`/`.gitignore` modified)

## Accomplishments

- **Task 1 (fast-forward continuity gate):** Confirmed this session's working directory is `/home/jason/scotuschat/project` on `ext4` (not the pre-relocation `/mnt/c/workspace/scotuschat/project` 9p mount). Fetched `main` from the pre-relocation checkout as a one-shot local remote and fast-forwarded 4 commits with zero divergence -- both checkouts' HEADs are identical (`b5b069752bc1068af35f3c3fbf3e4b127a546307`), `git remote` still lists only `origin`, `git status --porcelain -uno` is clean, and `git fsck --no-dangling` exits 0. Mirrored the one piece of untracked `.planning/` catch-up material found at the old checkout (a stray `__pycache__` directory under `phases/43-dev-only-reset-to-fixture/verify-scripts/`) via a permission-safe rsync.
- **Task 2 (dev-start.sh / dev-start.ps1 / vite.config.ts / .gitignore):** Built the full WSL-native start/stop entry point per the plan's spec -- dynamic `ip route`-based host resolution, a `.env` host self-heal/refuse function scoped to the WSL2 NAT private range, a zero-install `/dev/tcp` PostgreSQL reachability probe naming all three access gates, an Alembic fail-fast gate, `setsid -w` launches for uvicorn and vite (see key-decisions for why `-w` matters), real HTTP health polling with no fixed warm-up sleep, a trap-based teardown, and a `--stop` path. Reduced `scripts/dev-start.ps1` to an 18-line share-path-aware `wsl.exe` wrapper. Added an explicit `server` block to `app/vite.config.ts`. Added `.dev-logs/` and `.env.bak` to `.gitignore`.
- Confirmed nothing is already listening on 8000 or 5173 (`./scripts/dev-start.sh --stop` then `ss -ltn | grep -E ':(8000|5173)'` returns nothing) -- the pre-Task-3-handoff check the plan requires.
- Ran the plan's full literal Task 2 `<verify>` block end-to-end (`bash -n`, `test -x`, `--help`, `--stop`, both `git check-ignore` checks, and `cd app && npx vite build --logLevel warn`) -- all pass, exit 0.
- **Task 3 (live smoke, this session):** the operator ran the real stack, hit two real problems, and both were root-caused and resolved live rather than assumed. See the full writeup below for the evidence, the fix, and what is operator-observed vs. orchestrator-verified.

## Task Commits

1. **Task 1: Cutover continuity gate** -- no commit (verification-only + a fast-forward merge, which moves the branch pointer without creating a new commit; the plan's own file spec is "no tracked file is created or edited"). Outcome recorded above and in the fast-forward record below.
2. **Task 2: Build the WSL-native start/stop entry point, wrapper, and Vite server block** -- `82b14b7f` (feat) -- `feat(46-05): WSL-native dev-start.sh, share-path PS1 wrapper, explicit Vite server block`
3. **Task 3: Live start/stop smoke and reload proof** -- `3443b267` (fix) -- `fix(46-05): wait_for_http accepts any non-000 HTTP status, not just 2xx` -- the single code change to land from the live smoke test (Bug 1 below).

**Plan metadata:** this SUMMARY's own commit follows immediately after this file (see the completion message for its hash). The intermediate halt-state commit was `145da10f` (`docs(46-05): record Tasks 1-2 completion and Task 3 checkpoint handoff`).

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

**3. [Rule 1 - Bug] `wait_for_http` misread Vite's legitimate 404 on `/` as "not up yet"**
- **Found during:** Task 3, the operator's live smoke test -- `./scripts/dev-start.sh` burned all 30 retries against a fully healthy Vite because `curl -sf` treats any non-2xx response as failure, and this app's SvelteKit routing has no page at the bare root `/` (only `/cases`, `/attributions`, `/admin` exist).
- **Issue:** See "Bug 1" in the Task 3 writeup above for the full diagnosis, including the verbose-curl evidence (real `x-sveltekit-page: true` headers, 14965-byte real HTML body) that ruled out a genuinely broken Vite.
- **Fix:** `wait_for_http` now captures the HTTP status code via `curl -s -o /dev/null -w '%{http_code}'` and accepts any non-`000` code as proof the HTTP layer is alive, rather than requiring 2xx on a specific route.
- **Files modified:** `scripts/dev-start.sh` (the `wait_for_http` function).
- **Verification:** Re-run end to end after the fix -- `./scripts/dev-start.sh` reached the ready banner reporting `Vite is up (http://127.0.0.1:5173/, HTTP 404)`; `--stop` then cleanly terminated both process groups. Independently re-confirmed by this executor via live `curl` at SUMMARY-write time (`health:200`, `root:404`, `cases:200`).
- **Committed in:** `3443b267` (Task 3 commit).

---

**Total deviations:** 3 auto-fixed (all Rule 1 -- bugs). The first two share the same underlying `set -e`/`pipefail`-on-expected-empty-result class; the third is a distinct health-check-semantics bug surfaced only by live traffic against the real app.
**Impact on plan:** All three fixes are essential for the script's core correctness claims (reliable teardown, deterministic `--stop`, and a health check that doesn't false-fail against a healthy server). No scope creep -- all three stayed inside `scripts/dev-start.sh`, the file the plan already scoped.

**Bug 2** (the orphaned Windows-native `node.exe` intercepting the WSL2 localhost-forwarding relay) is **not** a deviation from this plan's code -- it is a pre-existing environmental artifact from before the relocation, documented in full in the Task 3 writeup above and flagged for plan 46-06's README, with no fix applied to `scripts/dev-start.sh` or `scripts/dev-start.ps1` because neither script caused it or could have detected it.

## Issues Encountered

- `npx vite build --logLevel warn` from `app/` took roughly 100 seconds end to end on this machine (confirmed via `time`) -- not a hang, and not caused by this plan's changes (the only edit to `vite.config.ts` was the additive `server` block). Noted here only because a shorter ad hoc timeout during verification made it look like a hang at first; re-run with adequate time confirmed a clean exit 0 with only the pre-existing Svelte a11y/reactivity lint warnings already known from plan 46-04.
- No other issues.

## User Setup Required

None -- no external service configuration required. Task 3 used the operator's own WSL-connected editor and a Windows-side browser, both pre-existing tools, not a new setup step.

## Task 3: Live Smoke Test -- Approved

Task 3 (`checkpoint:human-verify`, `gate="blocking"`) is the plan's live start/stop smoke test and the D-04 reload proof. The operator ran the checkpoint personally and it surfaced two real, previously-unknown problems -- neither simulated, neither assumed. Both were found, diagnosed, and resolved live during this session.

### Bug 1 -- `wait_for_http` false-failed on Vite's legitimate 404 (script bug, fixed and committed)

`wait_for_http` used `curl -sf`, which treats any non-2xx HTTP response as "not up yet." This app's SvelteKit routing has no page at the bare root `/` -- only `/cases`, `/attributions`, and `/admin` exist under `app/src/routes/` (confirmed by directly inspecting the routes directory: `admin/`, `attributions/`, `cases/`, `+layout.svelte` -- no route at `/`). So `/` legitimately returns a real, well-formed SvelteKit `404` (verified via verbose curl during the debugging session: genuine `x-sveltekit-page: true` response headers and a 14965-byte real HTML body), and `curl -sf` misread that as failure, burning all 30 retries even though Vite was fully healthy the entire time.

**Fix (committed `3443b267`):** `wait_for_http` now captures the HTTP status code directly via `curl -s -o /dev/null --max-time 2 -w '%{http_code}'` and accepts any code other than `000` as proof the HTTP layer is alive -- not that a specific route returns 2xx. This still correctly requires FastAPI's `/health` to be reachable (which does return `200`) and now also correctly accepts Vite's legitimate `404` on `/`.

**Re-verified by the orchestrator, independently, after the fix landed:**
- A full `./scripts/dev-start.sh` run reached the ready banner cleanly, reporting `Vite is up (http://127.0.0.1:5173/, HTTP 404)`.
- `./scripts/dev-start.sh --stop` then cleanly terminated both process groups with zero leftover processes.
- A live capture taken directly by this executor at SUMMARY-write time (after the operator's session, stack still running) confirms the fixed behavior end to end:
  ```
  $ curl -s -o /dev/null -w 'health:%{http_code}\n' http://127.0.0.1:8000/health
  health:200
  $ curl -s -o /dev/null -w 'root:%{http_code}\n' http://127.0.0.1:5173/
  root:404
  $ curl -s -o /dev/null -w 'cases:%{http_code}\n' http://127.0.0.1:5173/cases
  cases:200
  ```
  The `404` on `/` and `200` on `/cases` and `/health` is exactly the pattern Bug 1 describes -- Vite is healthy, `wait_for_http` now correctly accepts it, and the app's real routes serve `200`.

### Bug 2 -- orphaned Windows-native `node.exe` intercepting `localhost:5173` (environmental gotcha, not a script bug; no code change in this plan)

Not a bug in `scripts/dev-start.sh`. An orphaned Windows-native `node.exe` process (PID 37180, path `C:\nvm4w\nodejs\node.exe`) -- a leftover from an old, pre-relocation `Start-Process -WindowStyle Hidden cmd.exe /c npm run dev` launched against the **old** `C:\workspace\scotuschat\project\app` path -- was still listening on `[::1]:5173` on **Windows' own network stack** (confirmed via `netstat.exe`/`Get-NetTCPConnection` run from WSL through Windows interop). This intercepted the Windows-side browser's `localhost:5173` requests entirely, serving stale content from the old checkout, while the orchestrator's WSL-internal `curl` correctly reached the new WSL-native Vite instance the whole time -- which is why the evidence looked contradictory at first (browser: broken/stale; WSL curl: `200`).

Root cause of a second-order effect: WSL2's automatic Windows-to-WSL localhost port-forwarding relay for port 5173 apparently failed to establish while that rogue process held Windows' own port 5173 at the moment Vite first bound inside WSL (port 8000/FastAPI was unaffected -- nothing was contending for it on the Windows side).

**Resolution:** killed the rogue process via `powershell.exe -Command "Stop-Process -Id 37180 -Force"`, then restarted the WSL-native dev stack (fresh bind), which re-established the forwarding relay correctly -- confirmed via `curl.exe`/browser both reaching FastAPI and Vite with `200` afterward, and `netstat.exe` showing the relay's `ESTABLISHED` connections.

**Disposition:** documented here, not fixed in code, and **flagged prominently for plan 46-06's README rewrite** to surface in its troubleshooting section -- this is exactly the class of "the browser and the terminal disagree" confusion a future operator (or the same operator, months later) will hit again if a stray Windows-side dev-server process from before the relocation is ever left running. The concrete signature to document: Windows-side browser fails/serves stale content while WSL-internal `curl` succeeds; check for a Windows-native `node.exe` (or similar) still bound to the port via `netstat.exe`/`Get-NetTCPConnection`, kill it, and restart the WSL-native stack to re-establish the WSL2 localhost-forwarding relay.

### Evidence -- what is operator-observed vs. orchestrator-independently-verified

**Orchestrator-independently-verified (captured directly, not operator-reported):**
- `ps -eo pid,pgid,cmd` showed real WSL-native `uvicorn` and `npm run dev`/`vite` processes with real PIDs.
- `ss -ltnp` showed both `0.0.0.0:8000` and `*:5173` genuinely `LISTEN` with those PIDs attached.
- WSL-internal `curl`: `http://127.0.0.1:8000/health` -> `200`; `http://127.0.0.1:5173/cases` -> `200` (real page, 15965-byte body with SvelteKit/Tailwind markup).
- Windows-side (after killing the rogue process and restarting): `curl.exe` to `http://localhost:8000/health` -> `200`; to `http://localhost:5173/cases` -> `200`.
- This executor's own final independent check at SUMMARY-write time (see Bug 1 above): live `curl` confirms `health:200`, `root:404`, `cases:200`.
- `git diff app/src/app.css` is empty -- the operator's live CSS test edit (`--color-bg: red;`) was confirmed reverted.

**Operator-observed (reported by the operator, not independently re-run by the orchestrator):**
- The Windows-side browser loaded `http://localhost:5173/cases` successfully.
- **Reload proof (D-04):** the operator made a live edit to `app/src/app.css` (`--color-bg: red;`, a visible test), and confirmed via browser DevTools that the CSS custom property value updated live without a manual page refresh -- the reload mechanism genuinely fired. The operator's initial impression that "nothing visibly changed" was a red herring: the variable itself updated correctly per DevTools inspection; whether `--color-bg` is the actually-rendered background token is a separate, non-blocking cosmetic question, not a reload-mechanism failure.
- General approval, in the operator's own words: **"everything looks great and is working as I expected."** This is recorded as a general confirmation, not an itemized checklist reply -- the operator did not walk through and paste output for every one of the plan's 9 numbered `<how-to-verify>` steps individually and in order. The orchestrator's own captured evidence above (ps/ss/curl) independently covers most of what those steps intended to prove; nothing in this SUMMARY asserts the operator personally executed every step verbatim.

**Explicit coverage gap -- read honestly, not rounded up:** two full clean start/stop cycles were not separately itemized with verbatim before/after `ps`/`ss` output in this session's transcript beyond what is captured above. This SUMMARY does **not** claim "two consecutive clean cycles with zero surviving processes" as a directly-observed fact of this session; it claims what the evidence above actually supports -- a working, healthy, WSL-native stack reachable from both WSL and Windows, a real bug found and fixed, a real environmental gotcha found and documented, and the operator's own general approval. The Task 2 commit's `<verify>` block (run at commit time, see Task Commits above) already independently exercised `--stop`-with-nothing-running and the `--help`/`--badflag` argument paths; that coverage stands on its own and is not being re-claimed as part of Task 3's live-cycle evidence.

At SUMMARY-write time, the stack was still running (left up by the operator's session) -- confirmed directly:
```
$ ps -eo pid,pgid,cmd | grep -E 'uvicorn|vite|npm' | grep -v grep
 911649  911649 /home/jason/scotuschat/project/.venv/bin/python /home/jason/scotuschat/project/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude .claude/worktrees/* --reload-exclude .planning/* --reload-exclude .dev-logs/*
 911663  911663 npm run dev
 911678  911663 sh -c vite dev
 911679  911663 node /home/jason/scotuschat/project/app/node_modules/.bin/vite dev
$ ss -ltn | grep -E ':(8000|5173)'
LISTEN 0      2048         0.0.0.0:8000      0.0.0.0:*
LISTEN 0      511                *:5173            *:*
```
These are the same PIDs (911649 API; 911663/911678/911679 frontend) named in the operator's session evidence -- this is the final, orchestrator-captured live state, not a fresh run staged for this SUMMARY. `.dev-logs/*.log` files are present and non-empty, consistent with a live session (not checked for secrets before quoting -- none quoted here). The stack was left running rather than torn down as part of writing this SUMMARY, since no teardown was requested and the operator's own dev session was in progress.

### `POST /api/admin/dev/reset-to-fixture` gate (T-46-05-01)

Not independently re-run by the orchestrator during this SUMMARY pass (it requires `$ADMIN_TOKEN` and is destructive against dev data). The plan's acceptance criterion for this step was covered during the operator's live session per the objective's evidence; recorded here as operator-covered rather than fabricated with a specific response body this executor never saw. The allow-list gate itself (`settings.environment == "development"` in `api/main.py`) was unchanged by this plan and was re-verified structurally in plan 46-02 Task 3 -- this plan only changed the network binding the endpoint is reachable on, never the gate logic.

## Next Phase Readiness

- All three tasks are complete and committed: Task 1 (fast-forward, no commit), Task 2 (`82b14b7f`), Task 3's fix (`3443b267`).
- `scripts/dev-start.sh` passes every automated check in the plan's Task 2 `<verify>` block, run in full end to end, and its Task 3 fix (Bug 1) is independently re-verified live (see above).
- Bug 2 (orphaned Windows-native process intercepting the WSL2 localhost-forwarding relay) is documented in full above and flagged for plan 46-06's README troubleshooting section -- no code changes needed in this plan.
- Plan 46-06 (README rewrite, retiring the pre-relocation checkout) is now unblocked.
- STATE.md and ROADMAP.md are updated in this same completion pass, now that the plan has completed without a further pause.
- No blockers. SRC (`/mnt/c/workspace/scotuschat/project`) remains untouched and available as a rollback path per plan 46-04's precedent; retiring it is plan 46-06's explicit, gated decision.

---
*Phase: 46-dev-environment-reliability*
*Session recorded: 2026-08-14 (Tasks 1-2 prior session; Task 3 this session, approved)*

## Self-Check: PASSED

All claimed files verified present on disk (`scripts/dev-start.sh`, `scripts/dev-start.ps1`, `app/vite.config.ts`, `.gitignore`, this SUMMARY) and the Task 2 (`82b14b7f`) and Task 3 fix (`3443b267`) commit hashes verified present in `git log --oneline --all`. Live `ps`/`ss`/`curl` evidence quoted above was captured directly by this executor immediately before writing this section, not reconstructed from memory.
