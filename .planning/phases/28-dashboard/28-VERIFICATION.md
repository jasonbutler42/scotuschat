---
phase: 28-dashboard
verified: 2026-07-11T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Load /admin/ in a browser against a populated dev DB and visually confirm the page reads as a calm, intentionally-designed dashboard (DASH-05) — Needs Attention section above the stat-card grid, the Web Traffic placeholder visually distinct (dashed border / reduced opacity / separate row), and the four stat cards visually neutral (no color-coded urgency)."
    expected: "Needs Attention section renders first and reads as the primary focal point; stat cards are visually calm/uniform; the Web Traffic placeholder is unmistakably inactive/placeholder; overall the page does not read as a generic table dump."
    why_human: "DASH-05 ('visual hierarchy guides the operator') and D-10 (no urgency color-coding) are subjective visual-quality judgments that source/grep checks cannot fully certify — the code matches the UI-SPEC token-for-token (confirmed by source assertions and a clean svelte-check + npm run build), but actual rendered visual hierarchy needs a human look."

  - test: "Trigger a live fetch failure for one of the seven dashboard endpoints (e.g. stop the FastAPI backend or block one route) and confirm the dashboard still renders with 'N/A' stat values and normal empty-state copy for affected Needs Attention sub-lists, never a hard error page."
    expected: "Page renders normally; failed stat fields show 'N/A'; failed sub-lists show their empty-state copy; no 500/crash."
    why_human: "The degrade-gracefully code path (try/catch per fetch, null sentinel, empty-array fallback) is present and source-verified, but no automated test exercises an actual network failure against the live SvelteKit load() — this is a runtime behavior best confirmed by briefly disabling one endpoint and reloading the page."
---

# Phase 28: Dashboard Verification Report

**Phase Goal:** The `/admin/` dashboard presents intentionally designed stat cards with actionable CTAs, a "needs attention" section surfacing real operator tasks, and a web traffic placeholder card — giving the operator an at-a-glance view of the admin state on every login
**Verified:** 2026-07-11
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Stat cards show Arguments (total/published/draft/unpublished), People (total/incomplete), Utterances (total), Pipeline runs (recent count + last activity date) | ✓ VERIFIED | `get_argument_stats`/`get_people_stats`/`get_utterance_count`/`get_pipeline_stats` in `api/services/{admin_arguments,admin_people,admin_jobs}.py`, exposed via 7 GET routes in `api/routers/admin.py`, rendered in `app/src/routes/admin/+page.svelte` lines 224-291 inside 4 `StatCard` instances. Backend behavior proven by live DB-gated tests (delta assertions against ~7,800-row corpus DB) — `pytest tests/conftest.py api/tests/test_admin_dashboard_stats.py api/tests/test_admin_dashboard_routes.py` → **18 passed** (re-run by verifier, not just trusted from SUMMARY). |
| 2 | Each applicable stat card has an inline CTA linking to the relevant admin screen | ✓ VERIFIED | Arguments: 3 deep-links (`?status=published/draft/unpublished`, lines 230-247); People: `{n} missing fields → Review` → `/admin/people` (line 257-262); Pipeline: `View all runs →` → `/admin/pipeline` (line 283-288); Utterances: intentionally no CTA per UI-SPEC ("no linked admin screen exists") — satisfies "each **applicable** card." |
| 3 | Needs Attention section shows incomplete people, tenure-gap Justices, draft arguments; unpublished excluded | ✓ VERIFIED | `get_recent_drafts` filters `Argument.status == ArgumentStatusEnum.DRAFT` only (admin_arguments.py:136-160) — UNPUBLISHED rows structurally cannot appear. `get_incomplete_people`/`get_tenure_gap_justices` delegate to existing `list_people()` unchanged. Rendered in `+page.svelte` lines 93-211 (People/Justices/Drafts sub-lists, each capped at 5, "View all →" links). Whole-section "All caught up" empty state present (lines 105-113). |
| 4 | Web traffic placeholder card present, labelled "coming soon" | ✓ VERIFIED | `+page.svelte` lines 297-310: `<h2>Web Traffic</h2>` + `<p>Coming soon</p>`, `border: 1px dashed #334155`, `opacity: 0.7`, `margin-top: 48px`, in its own div below (not inside) the 4-card grid. |
| 5 | Dashboard layout intentionally designed, not a generic table dump; visual hierarchy guides operator to urgent items | ✓ VERIFIED (code-level) / routed to human review for rendered visual confirmation | Needs Attention section renders before the stat-card grid in file order (D-09, confirmed lines 93 vs. 216); StatCard component (`app/src/lib/components/StatCard.svelte`) is the first shared card component in the codebase, fixed neutral container style (no conditional/ternary background-color found via source scan); Display-size (32px/600) primary numbers vs. Body/Label sizing for breakdowns per UI-SPEC typography scale; `npx svelte-check` (0 errors) and `npm run build` (succeeds) both re-run and confirmed by verifier. Visual-quality/hierarchy judgment itself needs a human look (see Human Verification below). |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/schemas/admin_dashboard.py` | 7 Pydantic response models, no apolitical-field leakage | ✓ VERIFIED | All 7 classes present (`ArgumentStats`, `RecentDraft`, `PeopleStats`, `IncompletePerson`, `TenureGapJustice`, `PipelineStats`, `UtteranceCount`); no `win_side`/`votes_side`/`scdb_docket_id` strings found. |
| `api/services/admin_arguments.py` | `get_argument_stats`, `get_recent_drafts`, `get_utterance_count` | ✓ VERIFIED | All 3 present, grouped-COUNT / LIMIT / whole-table-COUNT queries confirmed by reading source. |
| `api/services/admin_jobs.py` | `get_pipeline_stats` | ✓ VERIFIED | 30-day `func.count()` window + unbounded `func.max()` confirmed. |
| `api/services/admin_people.py` | `get_people_stats`, `get_incomplete_people`, `get_tenure_gap_justices` | ✓ VERIFIED | All 3 present; `list_people()` signature unchanged (verified no new parameter added). |
| `api/routers/admin.py` | 7 new GET routes, literal-before-`{id}` ordering | ✓ VERIFIED | Grep-confirmed line-order: `/arguments/stats`(947)/`/arguments/recent-drafts`(963)/`/utterances/count`(979) all precede `/arguments/{argument_id}`(994); `/people/stats`(680)/`/people/incomplete`(695)/`/people/tenure-gaps`(711) precede `/people/{person_id}`(727); `/jobs/stats`(348) precedes `/jobs/{job_id}`(363). |
| `app/src/lib/components/StatCard.svelte` | Shared card component, Svelte 5 runes, fixed neutral style | ✓ VERIFIED | Uses `$props()`, no `export let`; fixed inline style, no conditional color. (Note: WR-01 from code review — props are untyped, missing `Snippet` type for `children` — a maintainability warning, not a functional gap.) |
| `app/src/routes/admin/+page.server.ts` | `load()` with 7 sequential fetches, logout preserved | ✓ VERIFIED | 7 distinct fetches, each own try/catch, null-sentinel/`[]` defaults, no `Promise.all` (grep count 0), `actions.logout` present and unmodified (cookie delete + redirect to `/admin/login`). |
| `app/src/routes/admin/+page.svelte` | Needs Attention → stat grid → placeholder, in that order | ✓ VERIFIED | Confirmed by line-order read of the file (section at line 93, grid at line 216, placeholder at line 297). |
| `api/tests/test_admin_dashboard_stats.py` | DB-gated tests, delta/marker-scoped assertions | ✓ VERIFIED | Re-run by verifier: passes against live corpus DB. No bare absolute-count assertions found (grep audit of all `assert ... ==` lines). |
| `api/tests/test_admin_dashboard_routes.py` | DB-gated 200-not-422 route tests | ✓ VERIFIED | Re-run by verifier: passes against live corpus DB. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `+page.server.ts` `load()` | 7 `api/admin/*` endpoints | `fetch()` with `X-Admin-Token` header, `FASTAPI_BASE_URL` from `$env/static/private` | ✓ WIRED | All 7 URLs present, each with the auth header; env vars imported server-side only (no `PUBLIC_`, no leakage into `+page.svelte`). |
| `+page.svelte` | `+page.server.ts` `load()` return | `let { data } = $props()` | ✓ WIRED | `data.argumentStats`, `data.peopleStats`, `data.pipelineStats`, `data.utteranceCount`, `data.draftsList`, `data.incompletePeople`, `data.tenureGapJustices` all consumed. |
| Router handlers | Plan 01 service functions | direct async call, wrapped in Pydantic schema | ✓ WIRED | Confirmed for all 7 (`get_argument_stats_route` → `arguments_service.get_argument_stats`, etc.). |
| `get_incomplete_people`/`get_tenure_gap_justices`/`get_people_stats` | `list_people()` | direct delegation, no new SQL filter param | ✓ WIRED | Confirmed — `list_people` signature (`db, is_justice=None, missing=None, tenure_gaps=False`) unchanged from pre-phase-28 shape. |
| CTA hrefs in `+page.svelte` | Phase 26/27 query-param contracts | literal hrefs `?status=`, `?tab=bench&tenure_gaps=1` | ✓ WIRED | Reuses existing contracts verbatim, no new query-param surface invented. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DASH-01 | 28-01, 28-02, 28-03 | Stat cards: Arguments/People/Utterances/Pipeline counts | ✓ SATISFIED | Backend functions + routes + rendered cards, all confirmed above. |
| DASH-02 | 28-03 | Inline CTAs per applicable card | ✓ SATISFIED | 3 Arguments deep-links, People CTA, Pipeline CTA; Utterances intentionally has none. |
| DASH-03 | 28-01, 28-02, 28-03 | Needs Attention (incomplete people, tenure-gap Justices, drafts), excludes unpublished | ✓ SATISFIED | Confirmed via source read of `get_recent_drafts`'s DRAFT-only filter and the rendered sub-lists. |
| DASH-04 | 28-03 | Web traffic placeholder, "coming soon" | ✓ SATISFIED | Confirmed rendered markup. |
| DASH-05 | 28-03 | Intentional design, not a generic table dump | ✓ SATISFIED (code-level); visual confirmation requested | Layout order, StatCard component, UI-SPEC-token compliance all confirmed by source; final visual read routed to human verification. |

No orphaned requirements — REQUIREMENTS.md maps only DASH-01 through DASH-05 to Phase 28, and all five are claimed across the three plans' `requirements:` frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/lib/components/StatCard.svelte:10` | `$props()` untyped | ℹ️ INFO (from 28-REVIEW.md WR-01) | Low — no compile-time safety if a future caller forgets the `children` snippet; does not affect current phase's correctness. |
| `api/tests/test_admin_dashboard_stats.py:58-71` | Fixture calls `rollback()` inside an active `session.begin()` context | ℹ️ INFO (from 28-REVIEW.md WR-02) | Low in this file specifically (no functions under test call `db.commit()`), but echoes a project-wide test-fixture pattern already flagged in memory as an ESCALATED risk (999.19). Not a Phase 28 regression — pre-existing pattern reused, not introduced. |

No TBD/FIXME/XXX/HACK/PLACEHOLDER debt markers found in any of the 6 files this phase modified/created (confirmed by grep audit). The literal string "placeholder"/"coming soon" appearances are all expected UI copy per DASH-04, not debt markers.

### Behavioral Spot-Checks / Test Re-Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 28's own DB-gated backend test suite passes against the live corpus-scale dev DB | `pytest tests/conftest.py api/tests/test_admin_dashboard_stats.py api/tests/test_admin_dashboard_routes.py -q` | `18 passed in 6.80s` | ✓ PASS (re-run by verifier, not just SUMMARY claim) |
| Frontend type-checks cleanly | `npx svelte-check --tsconfig ./tsconfig.json` | `0 ERRORS, 16 WARNINGS` (all 16 warnings are in pre-existing files unrelated to Phase 28; none in `StatCard.svelte`, `+page.server.ts`, or `+page.svelte`) | ✓ PASS (re-run by verifier) |
| Frontend production build succeeds | `npm run build` | `✓ built in 13.27s` | ✓ PASS (re-run by verifier) |
| Route-shadowing regression check (literal routes precede `{id}` siblings) | grep line-number ordering across `api/routers/admin.py` | All 7 literal routes at lower line numbers than their `{id}` siblings | ✓ PASS |
| No absolute-count test brittleness against ~7,800-row corpus DB | grep audit of `assert ... ==` in `test_admin_dashboard_stats.py` | All whole-table assertions are `after == baseline + delta`; all top-5 list assertions use marker-token filtering | ✓ PASS |

Full-repo `pytest -q` regression status (31 pre-existing failures) was not re-run by the verifier in full — the task's own "Known context" states this was already confirmed pre-existing and isolated-file-reproducible (backlog 999.19), and Phase 28's own two new test files were independently re-executed above and pass cleanly. No evidence found that Phase 28's changes touch any of the failing files (`pipeline/tests/*`, or pre-existing `api/tests/test_admin_jobs_*`/`test_admin_arguments_service.py`/`test_arguments.py`/`test_argument_oyez_field.py`).

## Deferred Items

None — no gaps were pushed to a later phase.

## Human Verification Required

### 1. Visual hierarchy and calm-design confirmation (DASH-05, D-09, D-10)

**Test:** Load `/admin/` in a browser against a populated dev DB. Confirm the Needs Attention section reads as the primary focal point above the stat-card grid, the four stat cards look visually neutral/uniform (no urgency color-coding), and the Web Traffic placeholder is unmistakably distinct from the real cards.
**Expected:** The page reads as an intentionally designed, calm, task-oriented dashboard — not a generic table dump.
**Why human:** Visual-quality and hierarchy judgments are outside what source/grep verification can certify. All underlying code matches the UI-SPEC design contract token-for-token (colors, spacing, ordering, copy) and both `svelte-check` and `npm run build` pass cleanly, but the final "does this feel calm and task-oriented" call needs a human look.

### 2. Load-failure degrade-gracefully behavior (UI-SPEC Load-failure state)

**Test:** Temporarily stop/break one of the seven FastAPI dashboard endpoints (or the whole API) and reload `/admin/`.
**Expected:** The page still renders; affected stat values show "N/A"; affected Needs Attention sub-lists show their normal empty-state copy; no hard error/500 page.
**Why human:** The try/catch + null-sentinel/`[]`-default code path is present and source-verified in every one of the seven fetch blocks, but no automated test in this phase exercises a genuine network failure against the live `load()` function — this is a runtime behavior best confirmed by actually breaking one endpoint and observing the page.

## Gaps Summary

No gaps found. All 5 ROADMAP success criteria and all 5 requirement IDs (DASH-01 through DASH-05) are backed by real, wired, delta-tested code — not placeholders or stubs. Both this phase's DB-gated test suites were independently re-executed by the verifier (not just trusted from SUMMARY.md) and pass against the live corpus-scale dev database. `svelte-check` and `npm run build` were also independently re-executed and pass. The only open items are two human-verification checks (visual-hierarchy confirmation and a live load-failure smoke test) that are inherently outside static/automated verification — these do not indicate a defect, only an outstanding UAT step before this phase can be considered fully closed out.

---

*Verified: 2026-07-11*
*Verifier: Claude (gsd-verifier)*
