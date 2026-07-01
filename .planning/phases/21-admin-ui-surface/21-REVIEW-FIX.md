---
phase: 21-admin-ui-surface
fixed_at: 2026-07-01T00:00:00Z
review_path: .planning/phases/21-admin-ui-surface/21-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 9
skipped: 2
status: partial
---

# Phase 21: Code Review Fix Report

**Fixed at:** 2026-07-01T00:00:00Z
**Source review:** .planning/phases/21-admin-ui-surface/21-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (4 Critical + 7 Warning)
- Fixed: 9
- Skipped: 2

## Fixed Issues

### CR-01: `delete_argument` checks `status == PUBLISHED` but published arguments use `published_at`, not necessarily `status`

**Files modified:** `api/services/admin_arguments.py`
**Commit:** c56b493a
**Applied fix:** Changed the guard from `argument.status == ArgumentStatusEnum.PUBLISHED` to `argument.published_at is not None`, making the delete block use the authoritative `published_at` timestamp instead of the potentially drifted `status` column.

---

### CR-02: `update_argument_metadata` condition bug — always writes `argued_date` even when input is empty/None

**Files modified:** `api/services/admin_arguments.py`
**Commit:** 942b2133
**Applied fix:** Changed the condition from `if body.argued_date is not None or parsed_date is not None` to `if parsed_date is not None`. Now `argued_date` is only written to the database when the parsed date is an actual date object, preventing empty-string input from NULLing the existing value.

---

### CR-03: Client-side polling fetches the page URL, not a data-only endpoint — may trigger HTML response or infinite state loop

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte`
**Commit:** 0c4b857f
**Applied fix:** Wrapped `await res.json()` in a try/catch block that returns early on parse failure, guarding against malformed responses. The `fresh` variable is now typed explicitly as `typeof liveJob | null`. Note: the four-request fan-out design concern remains open as a follow-up — it requires a dedicated lightweight poll endpoint.

---

### CR-04: `upload_person_photo` URL path — operator-supplied URL fetched server-side without allowlist (SSRF)

**Files modified:** `api/routers/admin.py`
**Commit:** 606884bc
**Applied fix:** Added HTTPS scheme enforcement via `urlparse` before the fetch — raises HTTP 422 if `scheme != 'https'`. Also changed `follow_redirects=True` to `follow_redirects=False` to eliminate redirect-based SSRF bypass vectors.

---

### WR-01: `test_service_file_has_synchronize_session_false` — structural guard counts `update(Argument)` calls only, misses `delete()` and `update(AdminJob)` calls

**Files modified:** `api/tests/test_admin_arguments_service.py`
**Commit:** b7edd146
**Applied fix:** Replaced the `source.count("update(Argument)")` count with a `re.findall(r'\b(update|delete)\(', source)` count. The test now counts all SQLAlchemy Core `update()` and `delete()` calls in the service file and asserts that `synchronize_session=False` appears at least as many times.

---

### WR-02: `update_argument` — `ValueError` from `datetime.date.fromisoformat()` leaks the raw exception message to the HTTP client

**Files modified:** `api/services/admin_arguments.py`
**Commit:** 87b114c4
**Applied fix:** Wrapped `datetime.date.fromisoformat(body.argued_date)` in a try/except in `update_argument`, re-raising as `ValueError("invalid_date_format")` — a controlled error string consistent with the project's other collision error patterns (`"slug_collision"`, `"docket_collision"`).

---

### WR-03: `+page.server.ts` (pipeline detail) — `approve` action fetches the job a second time to get `argument_id`, creating a TOCTOU window

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
**Commit:** c177a394
**Applied fix:** Changed the silent `// Continue` catch to `return fail(502, { approveError: 'Could not load job. Try again.' })` in both the non-OK response branch and the catch block. The job fetch failure now surfaces a user-visible error rather than silently proceeding to approve with a null `argument_id`.

---

### WR-04: `+layout.svelte` — renders `TopNav` with `variant="public"` for all admin pages

**Files modified:** `app/src/routes/admin/+layout.svelte`
**Commit:** fa6bc318
**Applied fix:** Removed the `<TopNav variant="public" />` line and its import from the admin layout. The `AdminSubNav` alone is sufficient for admin pages. Also fixed the login route check to use `page.route.id !== '/admin/login'` (more robust than pathname string comparison), addressing IN-02 as a bonus.

---

### WR-05: `delete_argument` — `status == PUBLISHED` check diverges from `unpublish_argument` which checks `published_at`

**Files modified:** `api/services/admin_arguments.py`
**Commit:** c56b493a _(fixed together with CR-01 — same line change)_
**Applied fix:** The CR-01 fix (`published_at is not None` guard) resolves this finding simultaneously, making `delete_argument` consistent with `unpublish_argument`'s guard pattern.

---

### WR-06: `+page.svelte` (argument detail) — `select` element uses `value={participant.side}` but Svelte 5 `<select>` controlled value requires `bind:value` or `selected` attribute

**Files modified:** `app/src/routes/admin/arguments/[id]/+page.svelte`
**Commit:** c626edc8
**Applied fix:** Removed `value={participant.side}` from the `<select>` element and added `selected={participant.side === 'X'}` to each `<option>`. The correct option is now pre-selected on render and after form re-renders.

---

## Skipped Issues

### WR-07: `get_argument_detail` — N+1 query in tenure gap check issues one EXISTS subquery per bench participant

**File:** `api/services/admin_arguments.py:143-165`
**Reason:** The fix requires consolidating the sequential EXISTS loop into a single LEFT JOIN aggregate query — a substantial rewrite of the query logic that requires careful correctness verification across edge cases (NULL `end_date`, multiple tenures per Justice, etc.). The reviewer explicitly flagged this as WARNING rather than blocker and noted performance is out of v1 scope. Skipping to avoid introducing a regression in correctness without proper testing. Recommend addressing in a dedicated follow-up with tests for each tenure edge case.
**Original issue:** For each bench participant, an individual EXISTS query is issued (O(n) round-trips). Should be consolidated into a single query with LEFT JOIN and aggregate.

---

_Fixed: 2026-07-01T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
