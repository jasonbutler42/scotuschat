# Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
**Areas discussed:** Frontend scope

---

## Frontend scope

| Option | Description | Selected |
|--------|-------------|----------|
| Include frontend sync | Update `+page.svelte`'s breakdown line and `+page.server.ts`'s `can_delete`/`delete_block_count` to include tenures — matches Success Criterion #1 literally and keeps the UI accurate the moment the API changes. | ✓ |
| Backend/API-only | Fix the three service functions and `MergePreview` schema only. Frontend keeps under-reporting tenure counts and could show "Delete person" as enabled for a Justice with tenure rows (client-side check is defense-in-depth only — server 409 still blocks it, so no data-loss risk) until a follow-up phase. | |

**User's choice:** Include frontend sync (recommended)
**Notes:** No further rationale requested — the two frontend files (`+page.svelte`, `+page.server.ts`) were confirmed in scope alongside the three backend service functions.

---

## Claude's Discretion

- New field name for the tenure count in `MergePreview`/counts dict: `tenures` (matches existing `tenure_coverage`/`has_tenure_gap`/`tenure_gaps` naming convention).
- Merge-preview breakdown copy wording and position in the joined string.
- Delete-blocked tooltip copy — confirmed no change needed (existing message is already generic across all blocking tables).
- Test coverage depth — mirror the existing rigor in `api/tests/test_admin_people_merge.py` for the 5th (CourtTenure) table.

## Deferred Ideas

- Known leaked duplicate "Ketanji Brown Jackson" `Person` rows (Phase 31 findings) may be a downstream symptom of this exact bug (merge previously 500'd on Justices with tenure rows). Not folded into this phase's scope — Phase 31's cleanup script uses raw scoped DELETE and bypasses this service layer entirely, so it's unaffected either way. Flagged as a manual follow-up check after this phase ships, not a phase deliverable.
