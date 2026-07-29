# Phase 32: Fix CourtTenure FK bookkeeping gap in merge/delete person service paths - Context

**Gathered:** 2026-07-13
**Status:** Ready for planning

<domain>
## Phase Boundary

`CourtTenure.person_id` is `nullable=False` with a plain `ForeignKeyConstraint` (no `ON DELETE CASCADE`), but none of `get_merge_preview`, `merge_people`, or `delete_person_if_orphan` (`api/services/admin_people.py`) account for `CourtTenure` rows. Merging or deleting any Bench person with tenure rows currently raises an unhandled `IntegrityError` (500).

This phase adds `CourtTenure` as a 5th FK table to the existing 4-table pattern (`Utterance`, `SpeakerAlias`, `CaseAppearance`, `ArgumentParticipant`) already handled in these three functions, plus the two frontend surfaces that read the merge-preview response. Nothing beyond this bookkeeping gap is in scope.

</domain>

<decisions>
## Implementation Decisions

### CourtTenure treatment (locked by REQUIREMENTS.md PADM-05 + roadmap Success Criteria)
- **D-01:** `CourtTenure` is a **blocking** FK table, not an "intrinsic, auto-delete" one. It follows the `Utterance`/`CaseAppearance`/`ArgumentParticipant` pattern (counted, and if count > 0 → delete is blocked with 409), **not** the `SpeakerAlias` pattern (deleted unconditionally before the orphan check, since aliases are "intrinsic to the person"). This is settled by Success Criteria #3 ("returns the documented graceful non-orphan response") and #4 ("genuinely orphaned" = zero tenure rows).
- **D-02:** `get_merge_preview` gets a 5th counted table (`CourtTenure`), mirroring the existing `for key, model, col in [...]` loop exactly.
- **D-03:** `merge_people` transfers `CourtTenure` rows via the same `UPDATE ... execution_options(synchronize_session=False)` pattern used for the other 4 tables, inside the same atomic transaction (single `db.commit()` at the end).
- **D-04:** `delete_person_if_orphan`'s counted-table loop (`Utterance`/`CaseAppearance`/`ArgumentParticipant`) gains `CourtTenure` as a 4th entry. The `SpeakerAlias`-first-unconditional-delete step is untouched.

### Frontend scope
- **D-05 (discussed):** This phase **includes** frontend sync, not backend-only. Two files read the merge-preview response and must be updated to include the new tenure count:
  - `app/src/routes/admin/people/[id]/+page.svelte` — the merge-preview breakdown line (currently "N utterance(s) · N alias(es) · N appearance(s) · N argument participant(s)") and its all-zero check (`mergePreview.utterances === 0 && ...`).
  - `app/src/routes/admin/people/[id]/+page.server.ts` — `can_delete`/`delete_block_count`, computed client-side from the merge-preview response as defense-in-depth. Per D-01, the new tenure count joins `utterances`/`appearances`/`argument_participants` in this check (blocking), and is **excluded** from it exactly like `aliases` currently is only if a future need arises — for this fix, tenures block, so they belong in the same bucket as utterances/appearances/argument_participants, not the aliases bucket.
  - Rationale: the client-side check is defense-in-depth only (server-side COUNT is authoritative, D-06/T-12-ORPHAN) — but leaving it stale means the delete button could show "enabled" for a Justice with tenure rows until the 409 comes back from the server, which is a worse operator experience than fixing it now, and this is the same merge-preview response contract being changed anyway.

### Claude's Discretion
- **New field name** for the tenure count in `MergePreview` (schema) and the counts dict (`get_merge_preview`): use `tenures` (matches existing naming convention elsewhere in this module — `tenure_coverage`, `has_tenure_gap`, `tenure_gaps` all say "tenure," not "court_tenure").
- **Merge-preview breakdown copy** (e.g., "N tenure(s)") and its position in the joined string: append after "argument participant(s)," matching existing sentence order (roughly mirrors table declaration order).
- **Delete-blocked tooltip copy**: no change needed — the existing text ("Cannot delete — this person has associated records and cannot be removed") is already generic across all blocking tables; no per-table wording exists today and none needs to be added for tenures.
- Test coverage depth: mirror the existing rigor in `api/tests/test_admin_people_merge.py` (preview count, transfer, blocked-delete, still-succeeds-when-orphan) — same shape as the existing 4-table tests, just for the 5th table.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` (PADM-05) — "Merging or deleting a Justice with CourtTenure rows no longer raises an unhandled 500 (CourtTenure counted in merge preview, transferred on merge, checked on delete)"
- `.planning/ROADMAP.md` §"Phase 32" — full goal statement and 4 Success Criteria (this is the authoritative scope statement; nothing here should be re-litigated as a gray area)

### Code (backend)
- `api/services/admin_people.py` — the 3 functions to modify: `get_merge_preview` (lines ~558-581), `merge_people` (lines ~584-630), `delete_person_if_orphan` (lines ~633-672). Module docstring (lines 1-20) documents the project-wide `synchronize_session=False` guard convention that must be followed for the new statements.
- `api/schemas/admin_people.py` — `MergePreview` (lines 212-224) needs the new `tenures: int` field.
- `api/routers/admin.py` — `DELETE /people/{person_id}` (lines 890-912) — no router changes expected; the 409 message stays generic.

### Code (frontend — in scope per D-05)
- `app/src/routes/admin/people/[id]/+page.svelte` — merge-preview breakdown display (lines ~112-116 for the `mergePreview` state type, ~741-752 for the rendered breakdown + all-zero check).
- `app/src/routes/admin/people/[id]/+page.server.ts` — `can_delete`/`delete_block_count` derivation (lines ~93-114), which calls the merge-preview endpoint server-side.

### Tests (existing pattern to mirror)
- `api/tests/test_admin_people_merge.py` — existing tests for `merge_people`/`delete_person_if_orphan`/preview counts across the 4 current FK tables; this phase's tests should follow the same structure for the 5th (`CourtTenure`).

No external specs/ADRs beyond REQUIREMENTS.md and ROADMAP.md — requirements are fully captured in the roadmap goal + decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The 4-table loop pattern in `get_merge_preview` and `merge_people` (a `for key/model/col in [...]` list) is designed to be extended — adding `CourtTenure` is a one-line addition to each list, not a new code path.
- `_replace_tenures` (lines 122-160) already shows the codebase's established `CourtTenure` CRUD conventions (delete-then-insert, `synchronize_session=False`) — useful reference for date/field handling, though not directly reused here since merge/delete only need person_id reassignment/counting, not full row manipulation.

### Established Patterns
- **Two-tier FK handling in `delete_person_if_orphan`:** intrinsic-and-unconditionally-deleted (`SpeakerAlias`) vs. counted-and-blocking (`Utterance`/`CaseAppearance`/`ArgumentParticipant`). `CourtTenure` joins the blocking tier (D-01).
- **Merge-preview response is a fixed-shape dict/schema**, not a dynamic list — the frontend hardcodes each field name, so schema + service + both frontend files must be updated together or the new count silently won't render.
- **Client-side `can_delete` deliberately diverges from the raw merge-preview response** — it excludes `aliases` from the block count (aliases don't block, they're auto-deleted). Any dev extending this must not naively sum all merge-preview fields.

### Integration Points
- `+page.server.ts`'s server load function calls the merge-preview endpoint (`GET /api/admin/people/{id}/merge-preview`) to derive `can_delete` — this is the single connection point between the backend schema change and the frontend disabled-state logic.

</code_context>

<specifics>
## Specific Ideas

No specific UI/copy requests — user confirmed the recommended approach (include frontend sync) and deferred field-naming/copy choices to Claude's discretion.

</specifics>

<deferred>
## Deferred Ideas

- **Known leaked duplicate Justice rows** ("Ketanji Brown Jackson" x5, `is_justice=true`, flagged in Phase 31 findings) may exist partly because merging them previously 500'd due to this exact bug. Once this phase ships, an operator could clean these up via the People Editor's merge UI instead of (or in addition to) Phase 31's raw-DELETE cleanup script. Not folded into this phase — Phase 31's cleanup script already bypasses this service layer and is unaffected either way. Worth a manual follow-up check after this phase ships, not a scope item.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 32-fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se*
*Context gathered: 2026-07-13*
