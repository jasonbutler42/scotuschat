# Phase 24: Pipeline List Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 24-pipeline-list-page
**Areas discussed:** Multi-docket new run behavior, Docket pill component strategy, Runs table show-all approach, Compound badge + table column layout, Question number field constraints

---

## Multi-docket new run behavior

| Option | Description | Selected |
|--------|-------------|----------|
| First pill = primary_docket; extras wait | First pill becomes primary_docket. Operator adds extras later via ArgumentDetailsCard on job detail. Server action stays simple. | |
| First pill = primary_docket; extras auto-saved | First pill becomes primary_docket. After run created, SvelteKit action immediately PATCHes argument with all pills before redirecting. | ✓ |
| Single-pill UX only (visual, no multi-docket) | Pill UI adopted for visual consistency but form functionally sends only one docket. | |

**User's choice:** First pill = primary_docket; extras auto-saved
**Notes:** The server action needs a second round-trip after run creation to persist additional docket pills onto the new argument.

### Follow-up: Multi-docket preflight

| Option | Description | Selected |
|--------|-------------|----------|
| Check all pills (warn if any match) | Preflight runs once per pill. If any docket+question matches, show the warning. | ✓ |
| Check first pill only | Only primary docket (first pill) is checked for duplicates. | |
| You decide | Let researcher/planner determine. | |

**User's choice:** Check all pills (warn if any match)
**Notes:** `duplicateWarning` state should include which specific docket triggered the match.

---

## Docket pill component strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Extract shared DocketPillInput.svelte | New sub-component used by both ArgumentDetailsCard and the New Run form. Requires refactoring Phase 23's component. | ✓ |
| Inline in +page.svelte (Recommended) | Copy pill pattern directly into the page. No Phase 23 refactor. | |
| You decide | Let researcher assess. | |

**User's choice:** Extract shared DocketPillInput.svelte
**Notes:** ArgumentDetailsCard.svelte must be refactored to import the new sub-component. Behavior must be identical post-refactor.

---

## Runs table — show all approach

| Option | Description | Selected |
|--------|-------------|----------|
| Remove limit entirely (Recommended) | Set limit=None or remove .limit() clause. Rename section "All Runs". No pagination. | ✓ |
| Set a very large pragmatic limit | Raise to 500 or 1000. Effectively all runs without changing the service signature dramatically. | |
| Add server-side pagination | Add offset/page param to API. Show N rows with prev/next controls. | |

**User's choice:** Remove limit entirely
**Notes:** Section heading changes from "Recent Runs" to "All Runs".

---

## Compound badge + table column layout

| Option | Description | Selected |
|--------|-------------|----------|
| Compound badge replaces Status; Step column removed (Recommended) | Badge shows "Parse · Running" etc. Step column disappears. Table: Status (compound) | Created | View. | ✓ |
| Compound badge in Status column; keep Step column | Status gets compound label; Step column kept for raw step name. | |

**User's choice:** Compound badge replaces Status; Step column removed
**Notes:** "Completed" needs no step prefix. Table simplifies to 3 data columns + View link.

---

## Question number field constraints

| Option | Description | Selected |
|--------|-------------|----------|
| Plain text input, no constraints (Recommended) | type="text", no min/max/pattern. FastAPI int coercion handles validation. | ✓ |
| type="number" with min=1 | Browser enforces numeric-only. | |
| You decide | Let planner pick. | |

**User's choice:** Plain text input, no constraints
**Notes:** Default value should pre-fill as "1" (matching old select default).

---

## Claude's Discretion

- `DocketPillInput.svelte` exact prop interface beyond `initialValues` and `name`
- Whether pill preflight checks fire in parallel (Promise.all) or sequentially
- How to PATCH additional dockets — existing `ArgumentUpdate` endpoint or new endpoint (researcher audits)

## Deferred Ideas

None — discussion stayed within phase scope.
