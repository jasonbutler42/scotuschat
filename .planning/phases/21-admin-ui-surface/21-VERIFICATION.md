---
phase: 21-admin-ui-surface
verified: 2026-07-01T23:00:00Z
status: human_needed
score: 12/13 must-haves verified
behavior_unverified: 3
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 9/13
  gaps_closed:
    - "On every /admin/* route except /admin/login the operator sees the public TopNav row on top and a distinct admin sub-nav row directly below it — Plan 21-04 added TopNav import + render to admin/+layout.svelte"
    - "The public TopNav (Cases + Admin link) is always visible in the admin area, matching public navigation style — TopNav variant=public now renders inside admin layout login guard"
    - "admin/+layout.svelte switches from <TopNav variant=admin> to <TopNav variant=public/><AdminSubNav/> (D-14, D-15) — key link now wired"
  gaps_remaining: []
  regressions: []
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
    why_human: "State-transition rationale: live browser required to observe the deleteConfirming toggle, in-flight deleteSubmitting state, and post-delete redirect"
human_verification:
  - test: "ADMIN-01: Verify the two-step confirm interaction on an unpublished argument"
    expected: "Click 'Delete argument' → Confirm + Cancel appear in-place; click Confirm → argument gone from /admin/arguments list; redirect occurs"
    why_human: "State transitions and redirect require live browser"
  - test: "ADMIN-01: Verify the blocked state tooltip on a published argument"
    expected: "Delete argument button is disabled and aria-describedby='delete-tip' tooltip 'Published arguments cannot be deleted. Unpublish first.' is accessible to screen readers and visible"
    why_human: "Accessibility and tooltip rendering requires browser with assistive tech or dev tools inspection"
  - test: "ADMIN-02: Verify the two-step confirm interaction on a pipeline run"
    expected: "Click 'Delete run' → Confirm + Cancel appear in-place; click Confirm → run gone from /admin/pipeline list; argument and its utterances still exist at /admin/arguments"
    why_human: "State transitions, cross-table data survival, and redirect require live browser + database"
---

# Phase 21: Admin UI Surface — Verification Report (Re-Verification)

**Phase Goal:** Deliver admin UI surface features — argument delete, pipeline run delete, and unified admin navigation (two-row nav with public TopNav + AdminSubNav)
**Verified:** 2026-07-01T23:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 21-04)

## Gap Closure Summary

The three NAV-02 gaps from the initial verification (2026-07-01T21:00:00Z) have been closed by Plan 21-04.

**What changed:** `app/src/routes/admin/+layout.svelte` now imports `TopNav` from `$lib/components/TopNav.svelte` and renders `<TopNav variant="public" />` immediately before `<AdminSubNav />` inside the existing `page.route.id !== '/admin/login'` guard. The root layout's `/admin/*` exclusion guard (`!page.url.pathname.startsWith('/admin')`) remains intact, ensuring the root layout does not contribute a TopNav on admin pages — exactly one TopNav renders on admin pages (from the admin layout), satisfying the two-row nav requirement with no double-render.

**No regressions found:** delete_argument (4 passed, 1 skipped) and delete_job (3 passed, 2 skipped) structural tests continue to pass. No anti-pattern debt markers found in Plan 21-04's modified file.

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Operator sees a Delete argument button on the argument edit page for unpublished arguments | VERIFIED | `+page.svelte` line 472: `{#if data.can_delete}` gates the initial "Delete argument" button; `can_delete` derived in `+page.server.ts` from `argument.status !== 'published'` |
| 2  | Clicking Delete once reveals Confirm delete + Cancel in-place; second click deletes and redirects to /admin/arguments | PRESENT_BEHAVIOR_UNVERIFIED | `deleteConfirming = $state(false)` wired; `onclick` sets `deleteConfirming = true`; form `action="?/delete"` with `use:enhance` wired to server action; `throw redirect(303, '/admin/arguments')` on success. State transitions require live browser. |
| 3  | D-02: Confirm delete + Cancel replace the original delete button in-place — no layout shift or new elements stacking | PRESENT_BEHAVIOR_UNVERIFIED | `{#if deleteConfirming}` / `{:else}` renders mutually exclusive branches in same container with identical flex layout; min-height: 44px on both states. Visual layout verification requires browser. |
| 4  | A published argument shows a disabled Delete argument button with a tooltip and cannot be deleted | VERIFIED | `{:else}` branch at +page.svelte line 524: `disabled` button, `aria-describedby="delete-tip"`, paragraph with exact text "Published arguments cannot be deleted. Unpublish first." Service returns False on published → router 409 |
| 5  | Deleting an argument removes it plus all utterances, pipeline_runs, argument_participants, case_arguments | VERIFIED | `delete_argument` in admin_arguments.py lines 437-507: FK-ordered cascade (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → AdminJob NULL → Argument); 4/4 structural tests pass |
| 6  | admin_jobs rows that referenced the deleted argument survive with argument_id NULL (no FK violation) | VERIFIED | `update(AdminJob).where(AdminJob.argument_id == argument_id).values(argument_id=None)` executes before `delete(Argument)`; structural test `test_delete_argument_admin_job_nulled_before_argument_deleted` confirms ordering |
| 7  | D-09: Operator sees a Delete run button on the pipeline job detail page only — not on the pipeline list page | VERIFIED | Danger Zone card on job detail page confirmed; no Danger Zone or delete button on pipeline list page (`/admin/pipeline/+page.svelte`) |
| 8  | D-02 (ADMIN-02): Clicking Delete once reveals Confirm delete + Cancel in-place; second click deletes the run and redirects to /admin/pipeline | PRESENT_BEHAVIOR_UNVERIFIED | `deleteConfirming = $state(false)`, `deleteSubmitting = $state(false)` wired; form `action="?/delete"` with `throw redirect(303, '/admin/pipeline')`; state transitions require live browser |
| 9  | Deleting a run removes only the admin_job row — the linked argument, its pipeline_run step rows, and its utterances are all unaffected | VERIFIED | `delete_job` in admin_jobs.py line 79-101: single `delete(AdminJob).where(AdminJob.id == job_id)` only; `test_delete_job_only_deletes_admin_jobs` structural test passes confirming no other table touched |
| 10 | On every /admin/* route except /admin/login the operator sees the public TopNav row on top and a distinct admin sub-nav row directly below it | VERIFIED | admin/+layout.svelte (after Plan 21-04): `{#if page.route.id !== '/admin/login'}` guards `<TopNav variant="public" />` then `<AdminSubNav />`; root layout suppresses its own TopNav for /admin/* so exactly one TopNav renders from admin layout |
| 11 | The admin sub-nav row shows Pipeline Runner, Arguments, People Editor links and a right-aligned Log out button | VERIFIED | AdminSubNav.svelte: `<a href="/admin/pipeline">Pipeline Runner</a>`, `<a href="/admin/arguments">Arguments</a>`, `<a href="/admin/people">People Editor</a>`, `<form ... action="/admin?/logout">Log out</form>` all confirmed |
| 12 | The public TopNav (Cases + Admin link) is always visible in the admin area, matching public navigation style | VERIFIED | TopNav.svelte (variant: 'public' only) contains `<a href="/cases">Cases</a>` and `<a href="/admin">Admin</a>`; admin layout renders `<TopNav variant="public" />` on all admin routes except /admin/login |
| 13 | The /admin/login page shows neither the TopNav nor the AdminSubNav | VERIFIED | Root layout: `!page.url.pathname.startsWith('/admin')` — login page does not get root-layout TopNav. Admin layout: `{#if page.route.id !== '/admin/login'}` — login page excluded from both `<TopNav>` and `<AdminSubNav>`. Both guards work independently. |

**Score:** 10/13 truths code-verified; 3 truths present and wired but behavior not exercised by automated tests

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_arguments.py::delete_argument` | FK-ordered cascade delete function | VERIFIED | Lines 437-507; correct delete order confirmed |
| `DELETE /api/admin/arguments/{argument_id}` in `api/routers/admin.py` | 200/404/409 endpoint | VERIFIED | Line 775; 404 on None, 409 on False, 200 on True |
| `delete form action + can_delete` in `app/src/routes/admin/arguments/[id]/+page.server.ts` | Server-side gate + delete action | VERIFIED | can_delete computed from argument.status; delete action issues DELETE with X-Admin-Token |
| `Danger Zone delete section` in `app/src/routes/admin/arguments/[id]/+page.svelte` | Two-step confirm UI | VERIFIED | deleteConfirming/deleteSubmitting $state; $effect reset; two-step confirm and blocked state present |
| `api/services/admin_jobs.py::delete_job` | Single-row admin_job delete | VERIFIED | Lines 79-101; only deletes AdminJob row |
| `DELETE /api/admin/jobs/{job_id}` in `api/routers/admin.py` | 200/404 endpoint | VERIFIED | Line 903; 404 on False, 200 on True |
| `delete form action` in `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Delete action with redirect | VERIFIED | DELETE call with X-Admin-Token; redirect(303, '/admin/pipeline') on success |
| `Danger Zone delete section` in `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Two-step confirm UI | VERIFIED | deleteConfirming/deleteSubmitting $state; $effect reset; two-step confirm (no blocked state for jobs) |
| `app/src/lib/components/AdminSubNav.svelte` (new component) | Admin nav row | VERIFIED | aria-label="Admin navigation"; all three nav links + logout form present; padding: 12px 24px |
| `app/src/routes/admin/+layout.svelte` renders TopNav variant=public + AdminSubNav | Two-row nav layout | VERIFIED | Plan 21-04: imports TopNav; renders `<TopNav variant="public" />` then `<AdminSubNav />` inside login guard |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| FK delete order: utterances before pipeline_runs | `delete_argument` body | Sequential execute calls | VERIFIED | Utterance delete at line 469, PipelineRun delete at line 475 — correct ordering |
| AdminJob.argument_id NULLed before argument delete | `delete_argument` body | `update(AdminJob).values(argument_id=None)` before `delete(Argument)` | VERIFIED | update at line 494, delete(Argument) at line 501 |
| `can_delete = argument.status !== 'published'` gates button server-side | `+page.server.ts` load | `const can_delete = argument.status !== 'published'` returned from load | VERIFIED | Server-side gate confirmed; no extra API call |
| `delete_job` touches ONLY admin_jobs — no cascade into argument/pipeline_runs/utterances | `admin_jobs.py::delete_job` | Single `delete(AdminJob)` statement; no other table in function body | VERIFIED | Structural test `test_delete_job_only_deletes_admin_jobs` passes |
| Post-delete redirect to /admin/pipeline (D-12) | `+page.server.ts delete action` | `throw redirect(303, '/admin/pipeline')` | VERIFIED | Confirmed in delete action |
| admin/+layout.svelte renders `<TopNav variant=public/><AdminSubNav/>` | admin layout + admin-layout login guard | `import TopNav`; `<TopNav variant="public" />` before `<AdminSubNav />` inside login guard | VERIFIED | Plan 21-04 gap closure; both elements confirmed in correct order at lines 5, 10-11 of admin/+layout.svelte |
| Root +layout.svelte /admin/* exclusion guard prevents double TopNav render | `app/src/routes/+layout.svelte` line 8 | `{#if !page.url.pathname.startsWith('/admin')}` wraps root-layout TopNav | VERIFIED | Root layout confirmed unchanged; exactly one TopNav renders on admin pages (from admin layout) |
| TopNav.svelte variant=admin branch removed only after confirming dead code | TopNav.svelte | grep gate + prop narrowed to 'public' | VERIFIED | `grep -rn 'variant="admin"' app/src` returns no matches; prop type is `'public'` only |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| delete_argument structural tests | `.venv/Scripts/pytest api/tests/test_admin_arguments_service.py -x -q -k delete_argument` | 4 passed, 1 skipped (DB-guarded) | PASS |
| delete_job structural tests | `.venv/Scripts/pytest api/tests/test_admin_jobs_service.py -x -q -k delete_job` | 3 passed, 2 skipped (DB-guarded) | PASS |
| No variant="admin" usages in app/src | `grep -rn 'variant="admin"' app/src` | NO_ADMIN_VARIANT_USAGES | PASS |
| TopNav in admin layout | `grep -n 'TopNav' app/src/routes/admin/+layout.svelte` | Line 5 (import) + Line 10 (`<TopNav variant="public" />`) | PASS — gap closed by Plan 21-04 |
| Root layout admin exclusion guard unchanged | `grep -n 'startsWith' app/src/routes/+layout.svelte` | Line 8: `!page.url.pathname.startsWith('/admin')` | PASS — guard present; prevents double TopNav |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ADMIN-01 | 21-01-PLAN.md | Operator can delete a mis-created argument from the admin UI (with confirmation; blocked if published) | VERIFIED (3 behavior truths pending human) | delete_argument service, DELETE endpoint, two-step UI, can_delete gate all present and wired; structural tests pass |
| ADMIN-02 | 21-02-PLAN.md | Operator can delete a pipeline run from the admin UI (with confirmation) | VERIFIED (1 behavior truth pending human) | delete_job service, DELETE endpoint, two-step UI all present and wired; structural tests pass |
| NAV-02 | 21-03-PLAN.md + 21-04-PLAN.md | Admin header navigation unified with public navigation in style and component structure | VERIFIED | AdminSubNav component built; TopNav variant=admin dead code removed; admin layout now renders both TopNav variant=public and AdminSubNav inside login guard; two-row nav structure achieved |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None | No TBD/FIXME/XXX markers found in any Plan 21-04 modified file | — | — |

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

---

_Verified: 2026-07-01T23:00:00Z_
_Verifier: Claude (gsd-verifier)_
