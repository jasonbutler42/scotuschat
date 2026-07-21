---
phase: 37-tenure-seat-as-chief-associate-toggle
plan: "04"
subsystem: api,ui
tags: [fastapi, pydantic, sveltekit, svelte5, formal-title-projection]

requires:
  - phase: 37-03
    provides: CourtTenure.office ORM column, OFFICE_CHIEF/OFFICE_ASSOCIATE/VALID_OFFICES constants, office_title() formal-title helper, admin-people strict-write/tolerant-read schema split
provides:
  - Office-based TenureEntry response contract (api/schemas/speakers.py)
  - _tenure_role_name projecting through office_title() with unchanged date-window/D-14-fallback semantics
  - Public route/popover TenureRow.office typing with formal-title rendering in SpeakerPopover.svelte
  - app/tests/tenure-public-title.browser.test.mjs regression fixture/spec
affects: [37-05]

tech-stack:
  added: []
  patterns: [single exhaustive canonical-to-display title helper reused at every read boundary, mirrored frontend/backend title map kept intentionally separate per language]

key-files:
  created:
    - app/tests/tenure-public-title.browser.test.mjs
  modified:
    - api/schemas/speakers.py
    - api/services/speakers.py
    - api/tests/test_speakers_service.py
    - api/tests/test_admin_arguments_service.py
    - app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
    - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
    - app/src/lib/components/SpeakerPopover.svelte

key-decisions:
  - "api/services/admin_arguments.py required zero source changes: it never accesses CourtTenure.seat/office directly — it consumes _bench_role_and_missing_tenure() (already converted to office_title() in 37-03) and only reads CourtTenure.start_date/end_date for the tenure-gap-warning date-window check. Only its DB fixture test needed CourtTenure(seat=...) -> CourtTenure(office=...)."
  - "SpeakerPopover.svelte defines its own small, exhaustive OFFICE_TITLES map / officeTitle() function rather than importing a shared frontend/backend constant — Python and Svelte/TS have no natural shared-module boundary in this repo, so the mapping is intentionally duplicated (mirroring api/models/models.py's OFFICE_TITLES) rather than invented as a new cross-layer dependency for a two-entry map."
  - "TenureEntry / the public route's TenureRow / SpeakerPopover's TenureRow all carry the raw canonical office value (not a pre-formatted title) end to end; only SpeakerPopover.svelte's officeTitle() projects to the formal display string at the final render boundary — keeping the wire contract canonical and the formal-title decision a pure display concern, consistent with 37-03's canonical-vs-display split."

patterns-established:
  - "Frontend formal-title projection: officeTitle() is an exhaustive lookup over exactly the two canonical values with no default branch beyond empty string for defensive null/unexpected input — it never falls back to a generic label, matching D-15's 'no generic Justice fallback for valid records' requirement."

requirements-completed: [PEOPLE-08]

coverage:
  - id: D1
    description: "api/services/speakers.py's _tenure_role_name and api/services/admin_arguments.py's bench projection (via admin_people._bench_role_and_missing_tenure) resolve to formal 'Chief Justice'/'Associate Justice' titles from canonical office, preserving the exact inclusive date-window match and D-14 most-recent fallback algorithm, with no valid record ever falling back to the generic 'Justice' label."
    requirement: PEOPLE-08
    verification:
      - kind: unit
        ref: "api/tests/test_speakers_service.py::TestTenureRoleName (11 cases: empty/window/boundary/open-ended/before-fallback/after-fallback/none-date/no-start-date/D-15-exhaustive-matrix)"
        status: pass
      - kind: unit
        ref: "api/tests/test_admin_arguments_service.py::test_list_argument_speakers_bench_advocate_and_utterance_counts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Public route types (+page.server.ts, +page.svelte) and SpeakerPopover.svelte render office end to end and project to the formal 'Chief Justice'/'Associate Justice' title at the final render boundary, with no raw canonical string ('chief'/'associate') or generic 'Justice' fallback ever appearing in the popover for a valid record."
    requirement: PEOPLE-08
    verification:
      - kind: e2e
        ref: "app/tests/tenure-public-title.browser.test.mjs::'public argument view renders formal Chief/Associate Justice titles, never raw office or generic fallback'"
        status: unknown
      - kind: other
        ref: "npm run check --prefix app (svelte-check, executed via WSL-native node to work around the environment's broken Windows-side app/node_modules — see Issues Encountered)"
        status: pass
    human_judgment: true
    rationale: "The real headless-browser (CDP) portion of tenure-public-title.browser.test.mjs could not be executed to completion in this sandboxed session: the Windows-side app/node_modules is present but empty/permission-denied for npm install (only a stray 0-byte nested folder, EACCES on npm ci), while the WSL/Linux side has a fully working app/node_modules (installed by user 'jason', not visible to native Windows processes) but no installed browser binary and no passwordless sudo to install one; and WSL cannot reach a Windows-launched msedge.exe's remote-debugging port even with --remote-debugging-address=0.0.0.0 (only Windows->WSL localhost forwarding works, not the reverse). In lieu of the CDP click-and-assert run, verification instead traced the full SSR data path live: a real vite dev server (WSL-native node_modules) served the exact chief/associate mock-API fixtures from the test file, and curl confirmed both fixtures' server-rendered avatar buttons (aria-label=\"View Fixture Chief details\" / \"View Fixture Associate details\") and argument metadata render correctly — proving the +page.server.ts -> +page.svelte data plumbing this test depends on is correct. SpeakerPopover.svelte's officeTitle() logic was additionally verified by full manual line trace against the D-15 contract. A human (or an environment with a working Windows-side app/node_modules and a reachable browser) should run `node app/tests/tenure-public-title.browser.test.mjs` for full end-to-end confidence."
duration: 50min
completed: 2026-07-21
status: complete
---

# Phase 37 Plan 04: Formal Office Title Projection Summary

**Speaker/admin-argument read projections and the public argument view/popover now render `Chief Justice`/`Associate Justice` from canonical `office`, with date-window and D-14 fallback selection algorithms byte-for-byte unchanged**

## Performance

- **Duration:** 50 min
- **Completed:** 2026-07-21
- **Tasks:** 2
- **Files modified:** 7 (1 created)

## Accomplishments

- `api/schemas/speakers.py`'s `TenureEntry.seat` renamed to `office` (canonical `chief`/`associate` storage value carried end to end on the wire; formal-title projection deferred to the render boundary).
- `api/services/speakers.py`'s `_tenure_role_name` now imports and calls `office_title()` at both its covering-window return and its D-14 most-recent-tenure fallback return, so every valid record resolves to `"Chief Justice"`/`"Associate Justice"` — never the old raw seat string or a generic `"Justice"` label. The two tenure dict-building blocks in `get_argument_speakers` were renamed `seat` -> `office`.
- `api/services/admin_arguments.py` needed **no source changes** — confirmed by grep and full read that it never accesses `CourtTenure.seat`/`.office` directly, only the already-converted `_bench_role_and_missing_tenure()` helper (from 37-03) and `CourtTenure.start_date`/`end_date` for the tenure-gap-warning date check. Only its DB-fixture test required an `office=` update.
- `api/tests/test_speakers_service.py` fully converted to canonical `office` dict keys and formal-title assertions, plus a new exhaustive `test_valid_records_never_return_generic_justice_fallback` covering both canonical values across window-match, none-date, and before-fallback paths (D-15). `api/tests/test_admin_arguments_service.py`'s one `CourtTenure(seat=...)` fixture and its two `"Associate Justice Seat 3"` assertions were updated to `office="associate"` / `"Associate Justice"`.
- Renamed the public route/popover `TenureRow.seat` type to `office` in `+page.server.ts` and `+page.svelte` (typing only — neither file renders tenure text itself).
- `SpeakerPopover.svelte` gained a small exhaustive `OFFICE_TITLES`/`officeTitle()` mapping (mirroring `api/models/models.py`'s `OFFICE_TITLES`/`office_title()`) and now renders `{officeTitle(t.office)} — {startYear}–{endYear}` instead of `{t.seat ?? 'Justice'} — ...` — removing the generic valid-record fallback and never exposing the raw `"chief"`/`"associate"` string, per D-15/UI-SPEC.
- Added `app/tests/tenure-public-title.browser.test.mjs`, a real headless-browser regression (modeled on `case-required-recovery.browser.test.mjs`'s mock-API + vite-dev-server + CDP pattern) that serves chief and associate fixtures through a mock FASTAPI backend, opens `SpeakerPopover` via the public argument view for each, and asserts the exact rendered `<p>` text (`"Chief Justice — 2005–present"`, `"Associate Justice — 1994–2005"`) with negative assertions against the raw canonical string and the generic `"Justice"` fallback.

## Task Commits

Each task was committed atomically:

1. **Task 1: Convert speaker and admin-argument projections** - `39bf2b3f` (feat)
2. **Task 2: Convert public route types and popover display** - `417cd8c8` (feat)

## Files Created/Modified

- `api/schemas/speakers.py` - `TenureEntry.seat` -> `office` (canonical value, formal projection deferred to render boundary).
- `api/services/speakers.py` - `_tenure_role_name` projects through `office_title()` at both return paths; tenure dict-building renamed `seat` -> `office`.
- `api/tests/test_speakers_service.py` - Full canonical-`office`/formal-title conversion of the date-window/fallback matrix; added D-15 exhaustive no-generic-fallback test.
- `api/tests/test_admin_arguments_service.py` - `CourtTenure(seat=...)` fixture and `bench_role`/`argument_role` assertions converted to `office="associate"` / `"Associate Justice"`.
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` - `RawSpeaker.tenure[].seat` -> `office` (typing only).
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` - `TenureRow.seat` -> `office` (typing only; no render logic here).
- `app/src/lib/components/SpeakerPopover.svelte` - `TenureRow.office` typing, new `OFFICE_TITLES`/`officeTitle()` helper, tenure line now renders the formal title with no generic fallback.
- `app/tests/tenure-public-title.browser.test.mjs` - New real-browser regression covering both public tenure display surfaces.

## Decisions Made

- Left `api/services/admin_arguments.py` completely untouched (no diff) since it has no `.seat`/`.office` reference of its own — documented explicitly in the plan's task rather than treated as a silent no-op, per its own `files_modified` listing (the file was `read_first`-verified, not blindly skipped).
- Kept the canonical `office` value (not a pre-formatted title) on every wire schema (`TenureEntry`, both frontend `TenureRow` types) and pushed the one formal-title projection for the *public popover per-tenure-row display* into `SpeakerPopover.svelte` alone, since that is the only file in this plan's scope that actually renders individual tenure rows — `+page.svelte` only carries the type for its `SpeakerDetail`/`TenureRow` interfaces and never iterates `tenure` itself.
- Duplicated the two-entry `office -> formal title` map in `SpeakerPopover.svelte` (TypeScript) rather than inventing a shared Python/TS module for two constants — the repo has no existing cross-language shared-constants mechanism, and creating one for this would be a disproportionate architectural change for a 2-key map (Rule 4 territory the plan didn't ask for).

## Deviations from Plan

None — plan executed exactly as written. `api/services/admin_arguments.py` requiring zero changes was explicitly investigated and documented above/in Decisions Made rather than silently skipped; it is not a deviation since the plan's own action text anticipated this file might only need pattern-matching verification (its files_modified listing exists to route the task, not to guarantee a diff).

## Issues Encountered

- **Windows-side `app/node_modules` is broken in this sandboxed session (environment limitation, not a plan/implementation defect):** The dispatch's environment notes state `app/node_modules` is "already installed," and this repo's other `*.browser.test.mjs` files assume invocation from repo root via `node app/tests/<file>.browser.test.mjs` against a Windows-native npm install (matching this plan's own `<verify>` line and PowerShell-based conventions in `34-04-PLAN.md`/`36-03-PLAN.md`). In this session, `C:\workspace\scotuschat\project\app\node_modules` (as seen by native `powershell.exe`/Windows `node.exe`) contains only a stray empty nested folder — `npm ci` there fails with `EACCES: permission denied, mkdir '...\node_modules\@alloc\quick-lru'`. A fully separate, fully-installed `app/node_modules` exists on the WSL/Linux side (owned by user `jason`, dated today) and IS usable from `bash` — confirmed by successfully running `svelte-check` via WSL-native `node` (`0 ERRORS, 16 pre-existing warnings`, none introduced by this plan's changes) and by running a real `vite` dev server that correctly served this plan's mock fixtures.
- **`tenure-public-title.browser.test.mjs` could not be executed end-to-end in this session:** the CDP (headless-browser) portion requires either (a) a Windows-native `app/node_modules` to run `vite`+browser fully inside Windows (blocked by the `EACCES` above), or (b) a Linux browser binary for the WSL side (none installed; `sudo` requires interactive auth, so no `apt install chromium` was possible), or (c) launching Windows' `msedge.exe` against a WSL-hosted vite server and having WSL's `node` reach back into that browser's CDP debug port — tested directly and confirmed **one-directional only** (Windows -> WSL `127.0.0.1` HTTP works via WSL2 localhost forwarding; WSL -> Windows `127.0.0.1`/gateway-IP does not reach a Windows-bound listener, including with `--remote-debugging-address=0.0.0.0`). Given all three paths are blocked, the test file was verified via: `node --check` (syntax-valid), a full manual trace against `SpeakerPopover.svelte`'s actual DOM structure (confirming the test's `.popover-card p` selector assumptions — exactly 2 `<p>` elements per fixture since `role_name`/`appointing_president` are both `null`), and a live partial run of the data path — a real WSL-native `vite` dev server served this test's exact mock-API fixtures, and `curl` against the SSR'd page confirmed both fixtures' `aria-label="View Fixture Chief/Associate details"` avatar buttons and argument metadata render correctly end to end. This proves the `+page.server.ts` -> `+page.svelte` data plumbing the test depends on is correct; only the client-side click-to-open-popover interaction and the `officeTitle()` render output remain unverified by an actual JS-executing browser in this specific session. See the `D2` coverage entry's `rationale` for the full detail and the recommended follow-up command.
- **Local git identity:** as in 37-03, this environment's git config has no `user.name`/`user.email`; commits were made with `GIT_AUTHOR_NAME`/`EMAIL`/`GIT_COMMITTER_NAME`/`EMAIL` environment variables matching the existing repo history's identity (Jason Butler <jason.butler@offenpetro.com>), with no git config file modified.
- **Pre-existing unrelated working-tree state:** consistent with 37-03's summary, the working tree contains substantial pre-existing modified content unrelated to this plan (many `.planning/*` files, plus an apparent whole-file CRLF/LF line-ending diff on `api/services/admin_arguments.py` that predates this session and was never touched by this plan). Every commit in this plan staged only the exact files named in its own commit message, verified via `git diff --cached --stat` before each commit.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 37-05 can proceed with the frontend Office-radio editor (`app/src/routes/admin/people/[id]/+page.svelte` and `+page.server.ts`), `api/tests/test_admin_dashboard_stats.py`'s `CourtTenure(seat=...)` fixtures, and the final repo-wide stale-`seat`-identifier audit — confirmed via `rg -n "\bseat\b" api pipeline app` that every remaining active-code hit is exactly and only in those 37-05-owned files (plus historical/prose mentions of the D-17 rename, and `tenure-office.browser.test.mjs`'s own intentional negative assertions against the word `seat`).
- The same Windows-side `app/node_modules`/CDP-reachability environment limitation documented above will block 37-05's frontend browser test (`app/tests/tenure-office.browser.test.mjs`, already a static-source regex test rather than a real-DOM test, so lower risk) and any other real-browser test 37-05 introduces, if run in this same sandboxed session. Recommend flagging to the operator before 37-05 executes, or running frontend verification from an environment where the Windows-native `npm install` for `app/` actually succeeds.

## Self-Check: PASSED

- All 7 modified/created files listed in `key-files` exist and contain the expected changes.
- Task commits `39bf2b3f` and `417cd8c8` both exist in `git log --oneline`.
- `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py api/tests/test_admin_arguments_service.py -x -q` (run via PowerShell per the plan's own `<verify>` line): **68 passed, 16 skipped** (skips are pre-existing DB-gated tests unrelated to this plan, per `_db_configured()`/`skipif`).
- `svelte-check --tsconfig ./tsconfig.json` (run via WSL-native `node` after confirming the Windows-native path is broken in this session): **0 ERRORS**, 16 pre-existing warnings (none newly introduced — `SpeakerPopover.svelte`'s one warning is a pre-existing `$props` reactivity note unrelated to this plan's `office`/`officeTitle` changes).
- `rg -n "\bseat\b"` against this plan's 8 scoped files returns exactly one hit: a prose D-17 rationale comment in `api/schemas/speakers.py` ("There is no `seat` compatibility alias") — zero active `seat` identifiers, keys, or field names remain in this plan's scope.

---
*Phase: 37-tenure-seat-as-chief-associate-toggle*
*Completed: 2026-07-21*
