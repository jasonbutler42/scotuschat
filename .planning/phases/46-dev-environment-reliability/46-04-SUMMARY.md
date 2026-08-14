---
phase: 46-dev-environment-reliability
plan: 04
subsystem: infra
tags: [wsl2, ext4, rsync, git, relocation, dev-environment, venv, node_modules]

# Dependency graph
requires:
  - phase: 46-01
    provides: rootdir conftest.py TEST_DATABASE_URL redirect + fail-closed sibling guards
  - phase: 46-02
    provides: WSL-native Python 3.12 venv + Windows PostgreSQL 18 service reachable from WSL
  - phase: 46-03
    provides: proven WSL→Windows-Postgres reachability, .env cutover, both DBs at Alembic head 0025, empirical dev-DB-wipe regression proof
provides:
  - "The working repository relocated off the 9p/DrvFs mount onto native WSL ext4 at /home/jason/scotuschat/project, with git history proven byte-faithful (identical HEAD SHA, identical commit count, clean fsck, intact origin remote)"
  - "46-RELOCATION.md — the durable evidence record: both absolute paths, the rsync exclude list with reasons, the integrity comparison table, the three .git/config filesystem-semantics corrections, and the rebuilt-toolchain proof"
  - "A WSL-native Python 3.12.13 venv and a lockfile-exact app/node_modules rebuilt at the new location (never copied), with the full stack proved working from there: Alembic head on both databases, WSL→Windows-Postgres reachability, pytest isolation, the full suite, and the frontend build"
  - "Operator cutover confirmation of Task 3's checkpoint (general affirmation) plus an independent orchestrator read-only re-verification at the new location"
affects: [46-05, 46-06]

# Actuals (#2632)
actuals:
  tokens: 4700
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Copy-then-verify-then-correct for a cross-filesystem repository relocation: rsync with an explicit exclude list (never move), integrity proven against pre-flight-recorded values (HEAD SHA, commit count, origin URL, clean fsck) before anything downstream depends on the copy, then filesystem-semantics git-config values (core.filemode/core.symlinks/core.ignorecase) corrected only after re-confirming the zero-executable-bit/zero-symlink/zero-case-collision preconditions that made the flip safe."
    - "Rebuild-not-copy for host-baked toolchain artifacts: a venv's console-script shebangs and node_modules' native platform binaries are excluded from the copy and reconstructed from pinned manifests (requirements*.txt, package-lock.json) at the new path, then the rebuilt venv's own shebang is asserted to name the new path rather than the old one — proving it points at itself."

key-files:
  created:
    - .planning/phases/46-dev-environment-reliability/46-RELOCATION.md
  modified: []
  # /home/jason/scotuschat/project itself (the relocated repo, its .venv, and its app/node_modules)
  # is a new directory tree outside the SRC repo and is not a tracked file in this repository.

key-decisions:
  - "Operator approved Task 3's cutover checkpoint with a general affirmation (\"from what I can tell, everything seems correct\") rather than a point-by-point walkthrough of each how-to-verify step. Recorded honestly as a general approval — this SUMMARY does not assert the operator definitively confirmed opening a WSL-connected editor with the green WSL remote badge, nor that every Windows-side shortcut was definitively repointed, because the operator did not state those specifics."
  - "Because the operator's confirmation was general rather than itemized, the orchestrator independently re-verified the mechanical, read-only parts of the checkpoint at DST after approval: git history match, clean tracked tree, filesystem type, core.ignorecase, and presence/readability of the raw data directories. This is recorded as orchestrator-verified, distinct from operator-verified, in the Task 3 section below."
  - "During that independent verification, git status --porcelain -uno at DST surfaced one file (README.md) as modified before going clean again on git add — a classic 'racy git' stat-cache false positive: content was confirmed byte-identical to HEAD throughout via cmp and git cat-file before staging. This was index metadata catching up to the operator's own blank-line-add-then-remove test from step 3 of the plan's how-to-verify, not a real change. Benign, already explained; not a defect."
  - "Correction to the plan's own anticipated hand-off gap: Task 3's write-up anticipated DST would be exactly one commit behind SRC at hand-off (missing only this plan's eventual SUMMARY commit). Independent read-only inspection of DST's actual HEAD (94f178a7) shows it predates BOTH of this plan's own evidence-recording commits (1bbcba33 for Task 1, c3c5f30c for Task 2) — both of which, like the SUMMARY commit, were written and committed at SRC after the rsync copy had already been taken. DST was therefore two commits behind at hand-off, not one, and this SUMMARY's own commit widens that to three. The substance of the plan's gap note is unaffected: none of these are hand-fixed here, and plan 46-05 Task 1's fast-forward gate is what closes the entire gap (however many commits it turns out to be) while also proving the two checkouts never diverged."
  - "This plan ran sequentially on the main checkout (not an isolated worktree), so per the 46-03 precedent, STATE.md/ROADMAP.md are updated directly as part of this plan's own finalization rather than by a separate orchestrator step. REQUIREMENTS.md was checked and requires no edit — D-01/D-02/D-04 are 46-CONTEXT.md decision IDs, not formal REQUIREMENTS.md requirement entries (confirmed via grep, no matches), so there is no checkbox to mark there."

patterns-established:
  - "When an operator's checkpoint approval is a general affirmation rather than an itemized walkthrough, the SUMMARY records exactly that — general approval — and any further mechanical verification needed to substantiate specific acceptance-criteria bullets is performed independently (read-only) and labeled as such, never folded into or presented as the operator's own words."

requirements-completed: [D-01, D-02, D-04]

coverage:
  - id: D1
    description: "The working repository exists at /home/jason/scotuschat/project on native ext4 with byte-identical git history (same HEAD SHA, same total commit count) and an intact origin remote"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "46-RELOCATION.md integrity table: rev-parse HEAD 94f178a71... identical SRC/DST, rev-list --all --count 1579 identical, origin URL identical, git fsck --no-dangling exit 0, git status --porcelain -uno empty at DST"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every untracked-but-load-bearing file (.env, app/.env, data/corpus, data/pdfs, data/uploads, memory/, .claude/, untracked .planning/ notes) is present at DST, and the two secret files are byte-identical to their originals and owner-only (0600)"
    requirement: "D-04"
    verification:
      - kind: integration
        ref: "46-RELOCATION.md: cmp -s .env / app/.env byte-identical, stat -c '%a' both 600; load-bearing payload (data/corpus, data/pdfs, data/uploads, memory, .planning/intel, .claude/settings.local.json) confirmed present at DST"
        status: pass
    human_judgment: false
  - id: D3
    description: "A WSL-native Python 3.12 venv and a WSL-native node_modules exist at DST, rebuilt from the pinned manifests rather than copied"
    requirement: "D-01"
    verification:
      - kind: integration
        ref: "46-RELOCATION.md Rebuilt toolchain section: .venv/bin/python --version 3.12.13, pytest shebang names DST not SRC, requirements*.txt and app/package-lock.json installed with no manifest drift, app/node_modules/.bin/vite present and executable"
        status: pass
    human_judgment: false
  - id: D4
    description: "From DST, a WSL-native process still reaches the Windows PostgreSQL 18 service over the dynamically-resolved gateway and both databases still report Alembic head"
    requirement: "D-02"
    verification:
      - kind: integration
        ref: "46-RELOCATION.md: alembic current reports 0025 (head) on DATABASE_URL and TEST_DATABASE_URL from DST; tests/test_wsl_postgres_reachability.py and tests/test_pytest_isolation_invocation_shapes.py both pass from DST; full suite reproduces exactly the 5 pre-existing deferred-items.md failures with dev-DB row counts unchanged before/after"
        status: pass
    human_judgment: false
  - id: D5
    description: "The operator has cut their own tooling over to DST — WSL-connected editor open, a save round-trips, and every Windows-side entry point that pointed at SRC has been repointed or confirmed not to exist"
    requirement: "D-04"
    verification: []
    human_judgment: true
    rationale: "The operator's Task 3 response was a general affirmation (\"from what I can tell, everything seems correct\") rather than an itemized confirmation of each how-to-verify step. No specific statement was made about the editor/remote arrangement used or which Windows-side entry points were repointed, so this deliverable cannot be auto-passed from the operator's own words. The orchestrator's independent read-only re-verification (git history match, clean tree, ext4, core.ignorecase=false, data directories present) substantiates the mechanical half of this checkpoint but not the operator-only half (editor arrangement, shortcut repointing), which remains a human-judgment item for the record."

# Metrics
duration: ~35min (Task 3 finalization only; Tasks 1-2 executed in a prior session)
completed: 2026-08-14
status: complete
---

# Phase 46 Plan 04: Repository Relocation to Native ext4 Summary

**Repository copied intact (217 unpushed commits, all untracked secrets/data) from the 9p/DrvFs mount to `/home/jason/scotuschat/project` on native ext4, with a rebuilt WSL-native venv/node_modules proving the full stack works from there, and the operator's general cutover approval independently substantiated by orchestrator read-only re-verification.**

## Performance

- **Duration:** ~35 min (this finalization session covering Task 3 and plan close-out; Tasks 1-2 were executed and committed in a prior session)
- **Tasks:** 3 (2 executed with commits in a prior session, 1 checkpoint approved this session)
- **Files modified:** 1 (`46-RELOCATION.md`, across the two prior-session commits) + this SUMMARY + STATE.md/ROADMAP.md in the finalization commit

## Accomplishments

- A byte-faithful copy of the repository — identical HEAD SHA (`94f178a7118375e3fac071153d7011fd5e903c67`), identical total commit count (`1579`), identical `origin` remote, clean `git fsck --no-dangling` — now lives on native ext4 at `/home/jason/scotuschat/project` (**DST**), copied from `/mnt/c/workspace/scotuschat/project` (**SRC**), with SRC left completely untouched as the rollback path.
- Every untracked-but-load-bearing file (`.env`, `app/.env`, `data/corpus/`, `data/pdfs/`, `data/uploads/`, `memory/`, `.claude/` minus worktrees, the untracked `.planning/` material) transferred; both secret files are byte-identical to their originals and tightened to owner-only `0600` at DST.
- The three filesystem-semantics `.git/config` values (`core.filemode`, `core.symlinks`, `core.ignorecase`) were corrected from the 9p-mount-appropriate values to ext4-appropriate ones (`false→true`, `false→true`, `true→false`) with zero spurious modification surfaced.
- A WSL-native Python 3.12.13 venv and a lockfile-exact `app/node_modules` were rebuilt (not copied) at DST; the rebuilt venv's own console-script shebang names DST, not SRC.
- The full stack was proved working from DST: Alembic head `0025` on both the dev and test databases, both regression tests (WSL-Postgres reachability, pytest isolation) green, the full bare suite reproducing exactly the 5 pre-existing `deferred-items.md` failures with dev-DB row counts unchanged before/after, and `npx vite build` exiting 0.
- Task 3's cutover checkpoint was approved by the operator (general affirmation) and independently re-verified read-only by the orchestrator at DST — see the dedicated section below for what each party actually confirmed.

## Task Commits

Tasks 1 and 2 were executed and committed in a prior session, before this finalization began:

1. **Task 1: Copy the repository to native ext4 and prove the copy is faithful (tracer)** — `1bbcba33` (docs) — `docs(46-04): record repository relocation to native ext4 (D-04)`
2. **Task 2: Rebuild the WSL-native toolchain at the new path and prove the stack works from there** — `c3c5f30c` (docs) — `docs(46-04): record rebuilt WSL-native toolchain proof at new location`
3. **Task 3: Cut over — confirm the new location is workable from your own tooling (checkpoint:human-verify)** — no commit of its own; approved this session, its evidence captured in this SUMMARY

**Plan metadata:** the STATE.md/ROADMAP.md finalization commit, made immediately after this SUMMARY's own commit — see `final_commit` below for both hashes.

## Both Absolute Paths (verbatim)

- **Pre-relocation path (SRC):** `/mnt/c/workspace/scotuschat/project`
- **Current path (DST):** `/home/jason/scotuschat/project`

Both are recorded in full in `46-RELOCATION.md`'s "Both absolute paths" section, which plans 46-05 and 46-06 read from rather than carrying a second copy.

## Integrity Values (from 46-RELOCATION.md, Tasks 1/2)

| Check | SRC | DST | Match |
|---|---|---|---|
| `git rev-parse HEAD` | `94f178a7118375e3fac071153d7011fd5e903c67` | `94f178a7118375e3fac071153d7011fd5e903c67` | Yes |
| `git rev-list --all --count` | `1579` | `1579` | Yes |
| `git remote get-url origin` | `https://github.com/jasonbutler42/scotuschat` | `https://github.com/jasonbutler42/scotuschat` | Yes |
| `git fsck --no-dangling` | — | exit `0` (~12.5s) | Yes |
| `git status --porcelain -uno` | empty | empty | Yes |
| `cmp -s .env` / `cmp -s app/.env` | — | byte-identical, both `0600` | Yes |
| `core.filemode` / `core.symlinks` / `core.ignorecase` | `false`/`false`/`true` (unchanged) | `true`/`true`/`false` (corrected) | Intentional divergence — filesystem-appropriate |

**Rebuilt toolchain (Task 2), also from `46-RELOCATION.md`:**
- Interpreter: `/home/jason/.local/bin/python3.12` → `.venv/bin/python --version` reports `Python 3.12.13`; pytest shebang names DST.
- Both requirement sets and `npm ci` (from the committed `package-lock.json`) installed with zero manifest/lockfile drift.
- Alembic: `0025 (head)` on both `DATABASE_URL` and `TEST_DATABASE_URL` from DST.
- Regression tests: `tests/test_wsl_postgres_reachability.py` + `tests/test_pytest_isolation_invocation_shapes.py` → 5 passed.
- Full suite: `5 failed, 1024 passed, 6 skipped, 5 xfailed in 166.09s` — exactly the 5 pre-existing `deferred-items.md` failures, no new ones.
- Dev-DB row counts before/after the full-suite run: `people=36, arguments=4, cases=4, utterances=1001` — unchanged.
- `npx vite build` from `app/` exited `0`.

## Task 3: Cutover Checkpoint — Operator Approval vs. Orchestrator Verification

These two are recorded separately and deliberately not conflated.

**Operator-verified (Task 3 approval):** The operator's response to the checkpoint was a general affirmation — *"from what I can tell, everything seems correct."* This is recorded honestly as a general approval, not as an itemized confirmation. This SUMMARY does **not** assert that the operator definitively opened a WSL-connected editor and observed the green WSL remote-indicator badge, nor that they definitively repointed every Windows-side shortcut/terminal profile/pinned window — the operator did not state those specifics, and inventing them would misrepresent the record.

**Orchestrator-verified (independent, read-only, at DST):**
- `git log --oneline -3` at DST matches SRC's history as it stood at the time of the copy.
- `git status --porcelain -uno` at DST is clean, after resolving one benign "racy git" stat-cache false positive on `README.md` via `git add README.md` — the file's content was confirmed byte-identical to `HEAD` throughout (via `cmp`/`git cat-file`, checked *before* staging). This was **not** a real change; it was index metadata catching up to the operator's own blank-line-add-then-remove test described in step 3 of the plan's how-to-verify. Benign and already explained here — not a defect.
- `findmnt -no FSTYPE --target` at DST reports `ext4`.
- `git config core.ignorecase` at DST reports `false`.
- `data/corpus`, `data/pdfs`, `data/uploads` are present and readable at DST.

The orchestrator's checks substantiate the mechanical, filesystem/git-level half of Task 3's acceptance criteria. They do **not** substitute for the operator-only half (which specific editor/remote arrangement was settled on, which Windows-side entry points were actually repointed) — that half is marked `human_judgment: true` in this SUMMARY's `coverage` block above, for exactly that reason.

## Files Created/Modified

- `.planning/phases/46-dev-environment-reliability/46-RELOCATION.md` (created, Task 1, commit `1bbcba33`; appended to, Task 2, commit `c3c5f30c`) — the full evidence record: both paths, exclude list with reasons, integrity comparisons, git-config corrections, secret-permission normalization, and the rebuilt-toolchain proof.
- `.planning/phases/46-dev-environment-reliability/46-04-SUMMARY.md` (this file).
- `.planning/STATE.md`, `.planning/ROADMAP.md` (updated in this plan's finalization commit — see below).
- Outside this repository: `/home/jason/scotuschat/project` (new directory tree — the relocated working repository, its rebuilt `.venv`, and its rebuilt `app/node_modules`). Not a tracked artifact of this repo.

## Decisions Made

See `key-decisions` in the frontmatter above for the full list. In brief: the operator's general (not itemized) approval is recorded as such; the orchestrator's independent read-only re-verification is labeled distinctly from the operator's words; the benign README.md racy-git resolution is explained plainly rather than flagged as a defect; the plan's anticipated "one commit behind" hand-off gap is corrected to two commits (soon three, after this SUMMARY's own commit) based on direct inspection of DST's actual HEAD, without changing the outcome — plan 46-05 Task 1's fast-forward gate closes the gap regardless of its exact size; and STATE.md/ROADMAP.md are updated directly in this plan's own finalization, matching the 46-03 precedent for plans executed sequentially on the main checkout.

## Deviations from Plan

None that required a code or evidence-record fix. One documentation correction, captured above as a key-decision rather than a Rule 1-3 auto-fix (it corrects this SUMMARY's own narrative, not a bug in prior committed work): the plan's Task 3 write-up anticipated DST would be exactly one commit behind SRC at hand-off; independent inspection of DST's actual `HEAD` (`94f178a7`) shows it is two commits behind at hand-off (predating both `1bbcba33` and `c3c5f30c`, both of which — like this SUMMARY's own commit — were written and committed at SRC after the rsync copy had already been taken). Plan 46-05 Task 1's fast-forward gate closes this gap regardless of its exact size, so nothing here is hand-fixed.

## Issues Encountered

None caused by this plan's own changes. The single anomaly encountered during Task 3's independent orchestrator verification — a "racy git" stat-cache false positive on `README.md` at DST — was investigated, confirmed benign (byte-identical content throughout, explained above), and resolved by staging it; it required no code change and reflects the operator's own blank-line test from the how-to-verify, not a defect introduced by this plan.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- D-01, D-02, and D-04 are all closed for this plan's scope: the repository is relocated and proven byte-faithful, the WSL-native toolchain is rebuilt and proven working end to end from the new location, and the operator has approved the cutover (with the orchestrator's independent read-only checks substantiating the mechanical half of that approval).
- Plan 46-05 (single WSL-native start/stop entry point, live smoke test, native-inotify reload proof) can proceed from DST. Its Task 1 fast-forward gate is the explicit, designed mechanism for closing the commit gap between SRC and DST described above — it must run before any other 46-05 work, exactly as the plan already specifies.
- Plan 46-06 (README rewrite, retiring the pre-relocation checkout) still depends on 46-05 completing first; SRC remains fully intact and is the rollback path until 46-06's explicit, gated, one-way decision.
- No blockers. The two pre-existing/unrelated test failures from `deferred-items.md` remain open for a future phase/session and do not block 46-05 or 46-06.

---
*Phase: 46-dev-environment-reliability*
*Completed: 2026-08-14*
