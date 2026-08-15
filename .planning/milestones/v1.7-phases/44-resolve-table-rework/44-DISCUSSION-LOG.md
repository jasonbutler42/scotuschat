# Phase 44: Resolve Table Rework - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-01
**Phase:** 44-Resolve Table Rework
**Areas discussed:** Argument Role dropdown scope, Confirm/Select flow inside Resolved As, Descriptor rename scope, Segmented toggle reuse for side-gate, Extracted/hint treatment across columns

---

## Argument Role dropdown scope

| Option | Description | Selected |
|--------|-------------|----------|
| 3 real options (Petitioner's/Respondent's Counsel + Amicus Curiae) | Matches full backend support (SideEnum.AMICUS) | ✓ |
| 2 options only, per mockup literally | Amicus rows would have no way to set role from this dropdown | |

**User's choice:** 3 real options.

| Option | Description | Selected |
|--------|-------------|----------|
| Both UNKNOWN and legacy ADVOCATE map to a placeholder | Operator must actively pick a role | ✓ (with wording override) |
| Show "Counsel" as a selected (non-placeholder) value | Reuses existing fallback label as if selected | |

**User's choice:** Placeholder option, but with custom wording — **"Select case role"** instead of the suggested "Select role."
**Notes:** User corrected the placeholder copy directly rather than picking a listed option verbatim.

---

## Confirm/Select flow inside Resolved As

| Option | Description | Selected |
|--------|-------------|----------|
| Show suggested match inline, 'Confirm' + 'Search instead' links | Preserves two-path behavior | |
| Auto-match becomes pre-filled search value; one entry point | Collapses to a single "Select person..." interaction | ✓ |

**User's choice:** Collapsed single entry point.

**Follow-up:** Whether untouched pre-fill still needs an explicit disposition action.

| Option | Description | Selected |
|--------|-------------|----------|
| Untouched pre-fill = accepted | Matches today's auto_resolved fast path | ✓ |
| Still requires one explicit action | Preserves explicit human-confirmation step | |

**User's choice:** Untouched pre-fill = accepted.

---

## Descriptor rename scope

| Option | Description | Selected |
|--------|-------------|----------|
| UI copy only | Zero backend risk, matches "frontend-only" roadmap framing | |
| Full rename through the stack | Migration + backend + all call sites | ✓ |

**User's choice:** Full rename through the stack.

**Follow-up:** Exact naming + phase-scope confirmation (given this expands beyond the roadmap's frontend-only estimate).

| Option | Description | Selected |
|--------|-------------|----------|
| descriptor / descriptor_hint | Literal 1:1 rename matching new UI label | ✓ |
| Something else | — | |

| Option | Description | Selected |
|--------|-------------|----------|
| Absorb into Phase 44 | Avoids UI/API mismatch during the phase | ✓ |
| Split into a separate phase/todo | Keeps Phase 44 small | |

**User's choice:** `descriptor`/`descriptor_hint`, absorbed into Phase 44.
**Notes:** Confirmed touches models.py + new Alembic migration, 3 schema files, 3 service files, routers/admin.py, pipeline/commands/parse.py.

---

## Segmented toggle reuse for side-gate

| Option | Description | Selected |
|--------|-------------|----------|
| Same component, reused as-is | One toggle everywhere; gate = same toggle unselected | ✓ |
| Keep them visually distinct | Gate keeps plain-button "unlock" treatment | |

**User's choice:** Same component, reused as-is.

---

## Extracted/hint treatment across columns

Initial finding: no genuine "originally extracted" `side` value exists distinct from the current committed value (same structural gap as `title_hint`, which already just re-reads `participant.title`).

| Option | Description | Selected (round 1) |
|--------|-------------|------|
| Show hint anyway, same pattern as title_hint | Cosmetic-but-consistent, matches RESOLVE-05 | |
| Omit hint on Bench/Advocate and Argument Role | Avoids implying a distinct extraction event | ✓ (round 1, later revised) |

**Round 1 choice:** Omit — but this directly conflicted with ROADMAP.md's own success criterion 5 (all 4 columns must show the hint). Flagged back to user.

| Option | Description | Selected (round 2) |
|--------|-------------|------|
| Omit anyway — amend the success criterion | Keeps the round-1 decision, notes the criterion as amended | |
| Show hint on all 4 columns as originally written | Reverts to matching the literal roadmap criterion | (superseded by round 3) |

**User's round-2 answer (free text):** Wanted hints on all 4 columns (matching mockup/criterion 5), but worded to indicate the value came from an import rather than a genuine extraction event — anticipating future PDF-ingest work will eventually produce genuine per-field extraction.

**Round 3 — uniform vs. detected wording:**

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform wording now ("Imported: ..."), real detection later | No new plumbing needed; accurate for corpus-imported fixtures | ✓ |
| Detect and vary by real per-row origin | Needs new provenance plumbing (no such field exists today) | |

**User's choice:** Uniform wording now.

**Final scope confirmation:** Applies to all 4 columns uniformly (not just the 2 new ones) — requires adding an optional prefix-label prop to the shared `CopyableExtractedValue.svelte` component (default `"Extracted"` unchanged elsewhere in the app; `ResolveCard` passes `"Imported"`).

**User's choice:** Confirmed — yes, that's right.

---

## Claude's Discretion

- Exact internal implementation of the pre-filled-combobox pattern (component structure, visual distinction of top suggestion)
- Whether the Alembic migration for the Descriptor rename is a simple `alter_column` or needs additional handling

## Deferred Ideas

- Real per-row extraction provenance (PDF-parsed vs. corpus-imported) so hint wording/values can differ correctly in the future — not built this phase
- Capturing genuinely distinct raw/extracted values for `side` and argument role at parse time (no shadow/history column exists today)
- Both previously-pending todos (`2026-07-28-unpublished-argument-visible-in-cases-list.md`, `2026-07-29-popover-scrollbar-outside-card.md`) reviewed but not folded — already assigned to Phase 45 (BUG-01/BUG-02)
