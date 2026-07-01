---
phase: 21-admin-ui-surface
verified: 2026-07-01T21:00:00Z
status: gaps_found
score: 9/13 must-haves verified
behavior_unverified: 3
overrides_applied: 0
gaps:
  - truth: "On every /admin/* route except /admin/login the operator sees the public TopNav row on top and a distinct admin sub-nav row directly below it"
    status: failed
    reason: "The root layout (app/src/routes/+layout.svelte) explicitly excludes TopNav from all /admin/* routes via `{#if !page.url.pathname.startsWith('/admin')}`. The admin layout (app/src/routes/admin/+layout.svelte) only renders AdminSubNav — no TopNav is present on any admin page. SUMMARY.md and the Plan 03 acceptance-criteria self-check incorrectly claim this criterion passed."
    artifacts:
      - path: "app/src/routes/+layout.svelte"
        issue: "Suppresses <TopNav> for ALL /admin/* routes — no admin page sees TopNav"
      - path: "app/src/routes/admin/+layout.svelte"
        issue: "Renders only <AdminSubNav />, NOT <TopNav variant='public' /><AdminSubNav /> as the plan required"
    missing:
      - "Either: render <TopNav variant='public' /> before <AdminSubNav /> inside the admin layout guard, AND remove the /admin/* exclusion from the root layout"
      - "Or: accept this deviation (operator sees AdminSubNav only, not a two-row nav) via an override if the intent is satisfied by AdminSubNav alone"
  - truth: "The public TopNav (Cases + Admin link) is always visible in the admin area, matching public navigation style"
    status: failed
    reason: "Same root cause as above: the root layout gate `!page.url.pathname.startsWith('/admin')` prevents TopNav from rendering on admin pages. The Cases and Admin links visible on the public site are NOT visible in the admin area."
    artifacts:
      - path: "app/src/routes/+layout.svelte"
        issue: "Line 8: `{#if !page.url.pathname.startsWith('/admin')}` — TopNav excluded for all admin routes"
    missing:
      - "TopNav must be rendered on admin pages, either by removing the /admin/* exclusion from the root layout or by importing and rendering it in admin/+layout.svelte"
  - truth: "admin/+layout.svelte switches from <TopNav variant=admin> to <TopNav variant=public/><AdminSubNav/> (D-14, D-15)"
    status: failed
    reason: "Key link not wired as specified. The admin layout imports AdminSubNav but does not import or render TopNav at all. The two-row nav structure (TopNav + AdminSubNav) is not present."
    artifacts:
      - path: "app/src/routes/admin/+layout.svelte"
        issue: "No import of TopNav; no <TopNav variant='public' /> element; only <AdminSubNav /> is rendered"
    missing:
      - "Add `import TopNav from '$lib/components/TopNav.svelte';` to admin/+layout.svelte"
      - "Add `<TopNav variant='public' />` before `<AdminSubNav />` inside the login guard block"
      - "Remove or amend the /admin/* exclusion in app/src/routes/+layout.svelte"
behavior_unverified_items:
  - truth: "Clicking Delete once reveals Confirm delete + Cancel in-place; second click deletes and redirects to /admin/arguments"
    test: "Navigate to an unpublished argument edit page, click 'Delete argument', observe the button row changes to Confirm + Cancel without layout shift, then click Confirm delete"
    expected: "deleteConfirming state switches to true on first click, replacing the initial button in-place with the two-button row; on Confirm click, deleteSubmitting becomes true, the DELETE request fires, and the browser redirects to /admin/arguments"
    why_human: "State transitions (deleteConfirming toggle and deleteSubmitting during in-flight request) require a live browser; the redirect is a server-action result that grep cannot exercise"
  - truth: "D-02: Confirm delete + Cancel replace the original delete button in-place — no layout shift or new elements stacking"
    test: "On the argument edit page, observe the container height before and after clicking 'Delete argument'"
    expected: "The Danger Zone card height does not change when switching from the initial button state to the two-button confirm row (both states use identical flex containers with min-height: 44px)"
    why_human: "Visual layout behavior (pixel-level height comparison, no reflow) requires browser rendering; source analysis confirms matching heights but cannot rule out browser-specific layout differences"
  - truth: "D-02 (ADMIN-02): Clicking Delete once reveals Confirm delete + Cancel in-place, replacing the original delete button — no layout shift or new elements stacking; second click deletes the run and redirects to /admin/pipeline"
    test: "Navigate to a pipeline run detail page (/admin/pipeline/[job_id]), click 'Delete run', verify two-button row appears in-place, then confirm and verify redirect"
    expected: "deleteConfirming toggles on first click; Confirm delete submits the DELETE /api/admin/jobs/{job_id} request; browser redirects to /admin/pipeline"
    why_human: "Same state-transition rationale as ADMIN-01: live browser required to observe the deleteConfirming toggle, in-flight deleteSubmitting state, and post-delete redirect"
human_verification:
  - test: "ADMIN-01: Verify the two-step confirm interaction on an unpublished argument"
    expected: "Click 'Delete argument' → Confirm + Cancel appear in-place; click Confirm → argument gone from /admin/arguments list; redirect occurs"
    why_human: "State transitions and redirect require live browser"
  - test: "ADMIN-01: Verify the blocked state tooltip on a published argument"
    expected: "Delete argument button is disabled and aria-describedby='delete-tip' tooltip 'Published arguments cannot be deleted. Unpublish first.' is accessible to screen readers and visible"
    why_human: "Accessibility and tooltip rendering requires browser with assistive tech or dev tools"
  - test: "ADMIN-02: Verify the two-step confirm interaction on a pipeline run"
    expected: "Click 'Delete run' → Confirm + Cancel appear in-place; click Confirm → run gone from /admin/pipeline list; argument and its utterances still exist at /admin/arguments"
    why_human: "State transitions and cross-table survival verification require live database + browser"
---

# Phase 21: Admin UI Surface — Verification Report

**Phase Goal:** Deliver admin UI surface operations — argument delete (ADMIN-01), pipeline run delete (ADMIN-02), and admin sub-navigation unification (NAV-02).
**Verified:** 2026-07-01T21:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Operator sees a Delete argument button on the argument edit page for unpublished arguments | VERIFIED | `+page.svelte` line 472: `{#if data.can_delete}` gates the initial "Delete argument" button; `can_delete` derived in `+page.server.ts` from `argument.status !== 'published'` |
| 2 | Clicking Delete once reveals Confirm delete + Cancel in-place; second click deletes and redirects to /admin/arguments | PRESENT_BEHAVIOR_UNVERIFIED | `deleteConfirming = $state(false)` wired; `onclick` sets `deleteConfirming = true`; form `action="?/delete"` with `use:enhance` wired to server action; `throw redirect(303, '/admin/arguments')` on success. State transitions require live browser. |
| 3 | D-02: Confirm delete + Cancel replace the original delete button in-place — no layout shift or new elements stacking | PRESENT_BEHAVIOR_UNVERIFIED | `{#if deleteConfirming}` / `{:else}` renders mutually exclusive branches in same container with identical flex layout; min-height: 44px on both states. Visual layout verification requires browser. |
| 4 | A published argument shows a disabled Delete argument button with a tooltip and cannot be deleted | VERIFIED | `{:else}` branch at +page.svelte line 524: `disabled` button, `aria-describedby="delete-tip"`, paragraph with exact text "Published arguments cannot be deleted. Unpublish first." Service returns False on `published_at is not None` → router 409 |
| 5 | Deleting an argument removes it plus all utterances, pipeline_runs, argument_participants, case_arguments; the argument is gone from /admin/arguments | VERIFIED | `delete_argument` in admin_arguments.py lines 437-507: FK-ordered cascade (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → AdminJob NULL → Argument); 4/4 structural tests pass |
| 6 | admin_jobs rows that referenced the deleted argument survive with argument_id NULL (no FK violation) | VERIFIED | Line 494-499: `update(AdminJob).where(AdminJob.argument_id == argument_id).values(argument_id=None)` executes BEFORE `delete(Argument)`; structural test `test_delete_argument_admin_job_nulled_before_argument_deleted` confirms ordering |
| 7 | D-09: Operator sees a Delete run button on the pipeline job detail page (/admin/pipeline/[job_id]) only — not on the pipeline list page | VERIFIED | Danger Zone card at +page.svelte line 1500-1557 on job detail page; no Danger Zone or delete button found on pipeline list page (`/admin/pipeline/+page.svelte`) |
| 8 | D-02: Clicking Delete once reveals Confirm delete + Cancel in-place; second click deletes the run and redirects to /admin/pipeline | PRESENT_BEHAVIOR_UNVERIFIED | `deleteConfirming = $state(false)`, `deleteSubmitting = $state(false)` wired; form `action="?/delete"` with `throw redirect(303, '/admin/pipeline')`; state transitions require live browser |
| 9 | Deleting a run removes only the admin_job row — the linked argument, its pipeline_run step rows, and its utterances are all unaffected | VERIFIED | `delete_job` in admin_jobs.py line 79-101: single `delete(AdminJob).where(AdminJob.id == job_id)` only; `test_delete_job_only_deletes_admin_jobs` structural test passes confirming no other table touched |
| 10 | On every /admin/* route except /admin/login the operator sees the public TopNav row on top and a distinct admin sub-nav row directly below it | FAILED | Root layout (app/src/routes/+layout.svelte) line 8: `{#if !page.url.pathname.startsWith('/admin')}` — TopNav is excluded from ALL admin pages. Admin layout renders only `<AdminSubNav />`. No two-row nav exists on admin pages. |
| 11 | The admin sub-nav row shows Pipeline Runner, Arguments, People Editor links and a right-aligned Log out button | VERIFIED | AdminSubNav.svelte: `<a href="/admin/pipeline">Pipeline Runner</a>`, `<a href="/admin/arguments">Arguments</a>`, `<a href="/admin/people">People Editor</a>`, `<form ... action="/admin?/logout">Log out</form>` all confirmed |
| 12 | The public TopNav (Cases + Admin link) is always visible in the admin area, matching public navigation style | FAILED | TopNav is NOT rendered on any admin page. Root layout's `/admin/*` guard prevents it. Admin layout has no TopNav import or usage. |
| 13 | The /admin/login page shows neither the TopNav nor the AdminSubNav | VERIFIED | Root layout: `!page.url.pathname.startsWith('/admin')` — login page does not get TopNav. Admin layout: `{#if page.route.id !== '/admin/login'}` — login page does not get AdminSubNav. |

**Score:** 9/13 truths verified (3 present, behavior-unverified; 3 failed)

### Root Cause of NAV-02 Gap

The SUMMARY.md for Plan 21-03 incorrectly claimed the acceptance criterion "`+layout.svelte` contains `<TopNav variant='public' />` and `<AdminSubNav />`" was verified. The actual codebase shows:

- `app/src/routes/+layout.svelte` (root layout): renders `<TopNav>` only when `!page.url.pathname.startsWith('/admin')` — TopNav is suppressed on all admin pages.
- `app/src/routes/admin/+layout.svelte` (admin layout): imports and renders ONLY `<AdminSubNav />` — no TopNav is present.

The plan required replacing `<TopNav variant="admin">` with `<TopNav variant="public"><AdminSubNav />`. Instead, the implementation routes the two nav bars through two separate layout files with a guard that prevents co-rendering on admin pages.

**What IS working correctly:** AdminSubNav contains the correct links and logout form; the dead `variant="admin"` branch was properly removed from TopNav; the login page shows no nav (both guards work); svelte-check passes.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_arguments.py::delete_argument` | FK-ordered cascade delete function | VERIFIED | Lines 437-507; correct delete order confirmed |
| `DELETE /api/admin/arguments/{argument_id}` in `api/routers/admin.py` | 200/404/409 endpoint | VERIFIED | Lines 775-808; 404 on None, 409 on False, 200 on True |
| `delete form action + can_delete` in `app/src/routes/admin/arguments/[id]/+page.server.ts` | Server-side gate + delete action | VERIFIED | Lines 54-56 (can_delete), lines 199-220 (delete action) |
| `Danger Zone delete section` in `app/src/routes/admin/arguments/[id]/+page.svelte` | Two-step confirm UI | VERIFIED | Lines 465-539 |
| `api/services/admin_jobs.py::delete_job` | Single-row admin_job delete | VERIFIED | Lines 79-101; only deletes AdminJob row |
| `DELETE /api/admin/jobs/{job_id}` in `api/routers/admin.py` | 200/404 endpoint | VERIFIED | Lines 903-927; 404 on False, 200 on True |
| `delete form action` in `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Delete action with redirect | VERIFIED | Lines 309-325 |
| `Danger Zone delete section` in `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Two-step confirm UI | VERIFIED | Lines 1500-1557 |
| `app/src/lib/components/AdminSubNav.svelte` (new component) | Admin nav row | VERIFIED | File exists; all links/logout confirmed |
| `app/src/routes/admin/+layout.svelte` renders TopNav variant=public + AdminSubNav | Two-row nav layout | FAILED | Only `<AdminSubNav />` present; no TopNav import or render |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| FK delete order: utterances before pipeline_runs | `delete_argument` body | Sequential execute calls in correct order | VERIFIED | Utterance delete at line 469, PipelineRun delete at line 475 |
| AdminJob.argument_id NULLed before argument delete | `delete_argument` body | `update(AdminJob).values(argument_id=None)` before `delete(Argument)` | VERIFIED | update at line 494, delete(Argument) at line 501 |
| `can_delete = argument.status !== 'published'` gates button server-side | `+page.server.ts` load | `const can_delete = argument.status !== 'published'` returned from load | VERIFIED | Line 54-56 |
| `delete_job` touches ONLY admin_jobs — no cascade into argument/pipeline_runs/utterances | `admin_jobs.py::delete_job` | Single `delete(AdminJob)` statement; no other table in function body | VERIFIED | Structural test `test_delete_job_only_deletes_admin_jobs` passes |
| Post-delete redirect to /admin/pipeline (D-12) | `+page.server.ts delete action` | `throw redirect(303, '/admin/pipeline')` | VERIFIED | Line 324 |
| admin/+layout.svelte switches from `<TopNav variant=admin>` to `<TopNav variant=public/><AdminSubNav/>` | Root layout + admin layout | Root layout suppresses TopNav for /admin/*; admin layout adds only AdminSubNav | FAILED | TopNav is not rendered on admin pages; only AdminSubNav appears |
| TopNav.svelte variant=admin branch removed only after confirming dead code | TopNav.svelte | grep gate + prop narrowed to 'public' | VERIFIED | `grep -rn 'variant="admin"' app/src` returns no matches; prop type is `'public'` only |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| delete_argument structural tests | `.venv/Scripts/pytest api/tests/test_admin_arguments_service.py -x -q -k delete_argument` | 4 passed, 1 skipped (DB-guarded) | PASS |
| delete_job structural tests | `.venv/Scripts/pytest api/tests/test_admin_jobs_service.py -x -q -k delete_job` | 3 passed, 2 skipped (DB-guarded) | PASS |
| No variant="admin" usages in app/src | `grep -rn 'variant="admin"' app/src` | Zero matches | PASS |
| TopNav in admin layout | `grep -n 'TopNav' app/src/routes/admin/+layout.svelte` | No matches | FAIL — TopNav not imported or rendered in admin layout |
| Root layout admin exclusion | `grep -n 'startsWith' app/src/routes/+layout.svelte` | Line 8: `!page.url.pathname.startsWith('/admin')` | FAIL — confirms TopNav excluded from admin |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ADMIN-01 | 21-01-PLAN.md | Operator can delete a mis-created argument from the admin UI (with confirmation; blocked if published) | VERIFIED (behavior truths pending human) | delete_argument service, DELETE endpoint, two-step UI, can_delete gate all present and wired |
| ADMIN-02 | 21-02-PLAN.md | Operator can delete a pipeline run from the admin UI (with confirmation) | VERIFIED (behavior truths pending human) | delete_job service, DELETE endpoint, two-step UI all present and wired |
| NAV-02 | 21-03-PLAN.md | Admin header navigation unified with public navigation in style and component structure | PARTIAL | AdminSubNav component built and wired; dead variant=admin removed from TopNav; but public TopNav is NOT rendered on admin pages — two-row nav not achieved |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None in project source files | — | — | No TBD/FIXME/XXX markers found in api/ or app/src/ |

### Human Verification Required

#### 1. ADMIN-01: Two-step delete confirm interaction — argument

**Test:** Navigate to an unpublished argument edit page at `/admin/arguments/{id}`. Click the "Delete argument" button.
**Expected:** The button is replaced in-place by a two-button row: "Confirm delete" (red border) and "Cancel". No layout shift. Click "Confirm delete" — the argument disappears and the browser redirects to `/admin/arguments` without the deleted row.
**Why human:** `deleteConfirming` state transition and post-delete redirect require a live browser with a real database connection.

#### 2. ADMIN-01: Published argument blocked state accessibility

**Test:** Navigate to a published argument's edit page. Observe the Danger Zone section.
**Expected:** The delete button is disabled, visually muted, and the tooltip "Published arguments cannot be deleted. Unpublish first." is rendered (id="delete-tip") and announced by screen readers via aria-describedby.
**Why human:** Accessibility behavior (screen reader announcement) requires assistive technology or dev tools inspection.

#### 3. ADMIN-02: Two-step delete confirm interaction — pipeline run

**Test:** Navigate to a pipeline run detail page at `/admin/pipeline/{job_id}`. Click "Delete run".
**Expected:** Button replaced in-place by Confirm + Cancel row. Clicking "Confirm delete" removes only the admin_job row, redirects to `/admin/pipeline`. Navigate to the argument that was linked to the deleted run — argument and its utterances must still exist.
**Why human:** State transitions, cross-table data survival, and redirect require live browser + database.

### Gaps Summary

**NAV-02 root cause:** The Plan 03 implementation took a different architectural approach than specified. Instead of rendering `<TopNav variant="public" /><AdminSubNav />` inside the admin layout, the implementation:
1. Added a guard to the root layout (`+layout.svelte`) that suppresses `<TopNav>` for all `/admin/*` routes.
2. Added only `<AdminSubNav />` to the admin layout.

The net result: admin pages show ONE nav bar (`AdminSubNav`) instead of TWO (public TopNav + AdminSubNav). The public "Cases" and "Admin" links are NOT visible from any admin page.

This violates two must-have truths and one key link from the NAV-02 plan, and is inconsistent with the ROADMAP Phase 21 Success Criterion 3 ("the admin header navigation matches the public navigation in visual style"), which implies both navigation contexts are visible.

The SUMMARY.md acceptance-criteria self-check for Plan 03 is incorrect — it claimed the two-nav structure was verified when the code shows only one nav bar on admin pages.

**Fix options:**
1. **Full fix:** In `admin/+layout.svelte`, add `import TopNav from '$lib/components/TopNav.svelte';` and render `<TopNav variant="public" /><AdminSubNav />`. Remove the `/admin/*` exclusion from the root `+layout.svelte`.
2. **Override (if intent is met):** If the design intent of NAV-02 is satisfied by a single unified admin nav bar (AdminSubNav alone, styled consistently with the public nav), add an override to this VERIFICATION.md documenting that the two-row structure was intentionally replaced with a single row.

---

_Verified: 2026-07-01T21:00:00Z_
_Verifier: Claude (gsd-verifier)_
