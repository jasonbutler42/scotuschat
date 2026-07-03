---
phase: 23-shared-argument-details-component
fixed_at: 2026-07-02T00:00:00Z
review_path: .planning/phases/23-shared-argument-details-component/23-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 23: Code Review Fix Report

**Fixed at:** 2026-07-02
**Source review:** .planning/phases/23-shared-argument-details-component/23-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (2 Critical, 3 Warning)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Unguarded `fromisoformat` in `update_argument_metadata`

**Files modified:** `api/services/admin_arguments.py`
**Commit:** 45675823
**Applied fix:** Replaced the bare ternary `datetime.date.fromisoformat(body.argued_date) if body.argued_date else None` with a guarded `if body.argued_date: try/except ValueError: raise ValueError("invalid_date_format")` block, matching the identical pattern already used in `update_argument` at line 263. A malformed date string now raises a descriptive ValueError that the router converts to a 422 instead of propagating as a 500.

---

### WR-01: Dead `saveMetadata` action removed

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
**Commit:** ee7fc92a
**Applied fix:** Deleted the entire `saveMetadata` action block (52 lines, the comment block through the closing `},`). The action was never invoked by any form in `+page.svelte` and created a shadow write path to `/api/admin/arguments/{id}/metadata` bypassing the docket-pill serialization and `question_number` logic from Phase 23. No other route or component referenced `?/saveMetadata`.

---

### CR-02: Multi-docket fail-fast guard added to `saveJobMetadata`

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
**Commit:** ee7fc92a
**Applied fix:** Added a guard immediately after dockets are parsed that returns `fail(400, { saveError: 'Only one docket number is supported. Please remove the extra entries.', dockets })` when `dockets.length > 1`. The operator now receives an explicit error rather than having extra docket pills silently discarded. The existing `dockets[0] ?? ''` forwarding to the PATCH body is retained unchanged, as the schema constraint (`source_docket` is a single string column) remains in place.

---

### WR-02: `case_name` omission documented in `saveJobMetadata` PATCH body

**Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
**Commit:** ee7fc92a
**Applied fix:** Added a three-line comment inside the `JSON.stringify(...)` PATCH body block noting that `case_name` is intentionally absent from this caller because it is not editable from the job detail page — case_name edits are handled via the argument edit page (`/admin/arguments/{id}`) only. This documents the intentional gap so the permanently-dead service code path for `case_name` is not mistaken for a bug during future maintenance.

---

### WR-03: Form feedback keys mismatch (resolved by WR-01)

**Files modified:** none (resolved transitively)
**Commit:** ee7fc92a (WR-01 fix)
**Applied fix:** WR-03 resolved automatically when the dead `saveMetadata` action was removed (WR-01). The inconsistent `{ metadataSaved: true }` / `{ metadataError: ... }` keys that were never read by `ArgumentDetailsCard` no longer exist. The only active action (`saveJobMetadata`) correctly uses `{ saved: true }` and `{ saveError: ... }` which match the component's `form?.saved` / `form?.saveError` checks.

---

_Fixed: 2026-07-02_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
