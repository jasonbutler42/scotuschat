---
phase: 23-shared-argument-details-component
reviewed: 2026-07-02T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - api/schemas/admin_arguments.py
  - api/schemas/admin_jobs.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - app/src/lib/components/ArgumentDetailsCard.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-07-02
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 23 delivered the `ArgumentDetailsCard` shared component and wired it into the pipeline job detail page via the `saveJobMetadata` action. The backend schemas and services for both arguments and jobs are well-structured with clear mass-assignment guards and IDOR protections.

Two blockers were found. The first is an unguarded `datetime.date.fromisoformat()` call in `update_argument_metadata` that raises an unhandled `ValueError` — and therefore a 500 — when a malformed date string reaches it; the parallel `update_argument` function wraps the same call in a try/except and raises a proper `ValueError("invalid_date_format")`, making the inconsistency clear. The second is a silent multi-docket data-loss bug: the `saveJobMetadata` action forwards only `dockets[0]` to the API even when the operator has added multiple docket pills, silently discarding everything beyond the first.

Three warnings were found: a dead `saveMetadata` action that was superseded by `saveJobMetadata` but not removed, a missing `case_name` field in the `saveJobMetadata` PATCH payload that causes the field update path in the service to be permanently dead from this caller, and a mismatched `form` key that causes success and error feedback from `saveJobMetadata` to be invisible in `ArgumentDetailsCard`.

---

## Critical Issues

### CR-01: Unguarded `fromisoformat` in `update_argument_metadata` — 500 on bad date input

**File:** `api/services/admin_arguments.py:534-538`

**Issue:** `update_argument_metadata` calls `datetime.date.fromisoformat(body.argued_date)` in a bare ternary expression with no try/except. A malformed date string from the form (e.g. `"not-a-date"`, or a partial value) raises `ValueError` that propagates uncaught through the service, causing the FastAPI router to return a 500. The analogous function `update_argument` (line 262-267) wraps the same call in a try/except and re-raises a descriptive `ValueError("invalid_date_format")` which the router can catch and return as a 422. This function needs the same treatment. The `saveJobMetadata` action in the SvelteKit server sends the raw `argued_date` string from `FormData.get('argued_date')` without any client-side format validation, so a browser with JS disabled or a crafted request can reach this path with invalid data.

**Fix:**
```python
# api/services/admin_arguments.py — lines 533-538
# b. Parse argued_date from ISO string if provided
parsed_date: datetime.date | None = None
if body.argued_date:
    try:
        parsed_date = datetime.date.fromisoformat(body.argued_date)
    except ValueError:
        raise ValueError("invalid_date_format")
```

---

### CR-02: Multi-docket data loss — `saveJobMetadata` silently drops all pills after the first

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:461-463`

**Issue:** `saveJobMetadata` reads all `docket[]` pills from the form (`dockets` is a `string[]`) but sends only `dockets[0] ?? ''` to the PATCH endpoint. When the operator adds two or more docket pills, every pill except the first is silently discarded. The API's `MetadataUpdate.source_docket` is a single nullable string, so multiple dockets cannot be sent in one call, but the bug is the silent drop: the UI pill control allows multiple entries, and the server component accepts them all via `getAll('docket[]')` — the operator is given no feedback that extras were ignored.

There are two parts to this fix:
1. Either constrain the UI to a single docket pill (if source_docket is intentionally a single value), or
2. Detect multiple dockets before the PATCH and return a validation error.

The minimal safe fix consistent with the current schema (single `source_docket` column):

```typescript
// +page.server.ts — saveJobMetadata action, after dockets is computed (line ~421)
if (dockets.length > 1) {
    return fail(400, {
        saveError: 'Only one docket number is supported. Please remove the extra entries.',
        dockets,
    });
}
```

If multiple dockets are a legitimate future requirement, this is a schema-level change (`source_docket` → array or a separate table) that needs a migration; the current silent truncation is incorrect regardless.

---

## Warnings

### WR-01: Dead `saveMetadata` action — superseded by `saveJobMetadata` but not removed

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:364-407`

**Issue:** The `saveMetadata` action (lines 364-407) was the previous metadata save handler. It is never invoked from any form in the current `+page.svelte` (the `ArgumentDetailsCard` uses `action="?/saveJobMetadata"`). The dead action accepts `case_name`, `source_docket`, and `argued_date` from form data; it is reachable by a POST to `?/saveMetadata` with a custom form, creating an ambiguous second write path to `/api/admin/arguments/{id}/metadata` that bypasses the docket-pill serialization and `question_number` logic added in Phase 23. It should be removed before shipping.

**Fix:** Delete the entire `saveMetadata` action block (lines 364-407). Verify no other route or component references `?/saveMetadata`.

---

### WR-02: `saveJobMetadata` does not send `case_name` — the field's service code path is permanently dead from this caller

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:460-465`

**Issue:** `saveJobMetadata` sends `source_docket`, `argued_date`, and `question_number` in the PATCH body but never sends `case_name`. `MetadataUpdate.case_name` defaults to `None`, so the service's update path for `Case.case_name` (lines 564-578 of `admin_arguments.py`) is never reached from this caller. `ArgumentDetailsCard` has no `case_name` input field either — it accepts only dockets, question number, and argued date. If `case_name` editing from the job detail page is intentional per the spec, this field is missing from both the component and the action. If it is not required from this page, `MetadataUpdate.case_name` should be documented as only usable from the legacy `saveMetadata` action (which will be removed per WR-01), and the service should be updated to reflect that.

**Fix (if case_name is not needed from this page):** Add a comment to `update_argument_metadata` and `MetadataUpdate` noting that `case_name` is only populated from the argument edit page (`/admin/arguments/{id}`), and remove it from `MetadataUpdate` or mark it deprecated. If it is required, add a `case_name` field and text input to `ArgumentDetailsCard`.

---

### WR-03: Form feedback keys mismatch — `ArgumentDetailsCard` reads `form.saved`/`form.saveError` but `saveJobMetadata` returns `{ saved: true }` only on success and `{ saveError: ... }` only on failure; the `metadataSaved`/`metadataError` keys from `saveMetadata` (the dead action) are misnamed and ignored

**File:** `app/src/lib/components/ArgumentDetailsCard.svelte:310-331` and `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:476, 436, 439, 445, 469, 473`

**Issue:** `ArgumentDetailsCard` displays success feedback when `form?.saved` is truthy (line 310) and error feedback when `form?.saveError` is set (line 321). `saveJobMetadata` correctly returns `{ saved: true }` on success and `{ saveError: ..., dockets: [...] }` on failure, so the success and error paths in the card *do* match for `saveJobMetadata`. However, the dead `saveMetadata` action (WR-01) returns `{ metadataSaved: true }` on success and `{ metadataError: ... }` on failure — keys the component never reads. This confirms the two actions are inconsistently keyed. If `saveMetadata` is kept (contrary to WR-01), its return values must be updated to use `{ saved: true }` and `{ saveError: ... }`. More importantly, when the `form` prop is from a *different* action (e.g., `approve`, `rerun`, `delete`), `form?.saved` and `form?.saveError` will be `undefined` but this is harmless — those actions use distinct keys.

The substantive risk is that if `saveMetadata` is invoked from any path, the operator gets no success or error feedback in the card at all. Removing `saveMetadata` (WR-01) eliminates this risk.

**Fix:** After removing `saveMetadata` (WR-01 fix), this inconsistency is fully resolved. No code change needed in `ArgumentDetailsCard` itself.

---

## Info

### IN-01: `AdvocateParticipant.side` typed as `str` instead of `SideEnum`

**File:** `api/schemas/admin_arguments.py:99`

**Issue:** `AdvocateParticipant.side` is typed as `str` with a comment `# SideEnum value as string`. The service serializes it as `row.side.value` (admin_arguments.py:190), which is correct. However, the schema type allows any string to be set in this field if the schema is ever used for input. The comment acknowledges the deliberate choice, but Pydantic v2 can coerce `SideEnum` → string automatically via `model_config = {"use_enum_values": True}`, making the type safer with no downstream change. This is a minor type safety gap, not a current bug.

**Fix:** Change `side: str` to `side: SideEnum` and add `use_enum_values: True` to `AdvocateParticipant`'s `model_config`, or keep `str` but add a `field_validator` to enforce enum membership.

---

### IN-02: Polling endpoint reads `liveJob.id` which is from the initial server load — stale if the job is replaced by a rerun

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:83`

**Issue:** The poll loop fetches `/admin/pipeline/${liveJob.id}` — `liveJob.id` is initialized from `data.job` which is the server-load value. After a successful `rerun` the browser is redirected to the new job's page (line 283 of `+page.server.ts`), so the stale-id scenario can only arise if `invalidateAll()` fires and somehow re-sets `liveJob` to a different id, which SvelteKit's current re-hydration does not do. This is a theoretical concern with the `$effect(() => { liveJob = data.job; })` sync at line 76, but in practice the redirect prevents it. Noting for awareness.

**Fix:** No immediate action required. If the redirect behavior changes in future, consider deriving the poll URL from `data.job.id` rather than `liveJob.id`.

---

_Reviewed: 2026-07-02_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
