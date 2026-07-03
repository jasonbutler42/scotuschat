---
phase: 23-shared-argument-details-component
plan: "04"
subsystem: frontend/admin + backend/api
tags: [sveltekit, svelte5, fastapi, gap-closure, pipeline-job-detail, admin-ui]
status: complete

dependency_graph:
  requires:
    - "23-01-PLAN.md (MetadataUpdate.source_docket schema)"
    - "23-02-PLAN.md (ArgumentDetailsCard.svelte component)"
    - "23-03-PLAN.md (saveJobMetadata action; savedValues/hints wired)"
  provides:
    - "Gap 1 closed: View Source PDF card removed from pipeline job detail page"
    - "Gap 2 closed: Static Argument metadata preview card removed; standalone Ready-to-publish CTA"
    - "Gap 3 closed: Clearing all docket pills now persists NULL to DB"
    - "Gap 4 closed: hints.question_number always null → ArgumentDetailsCard renders italic N/A"
    - "Gap 5 closed: Docket instruction moved from placeholder to always-visible static label"
  affects:
    - "api/services/admin_arguments.py"
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
    - "app/src/lib/components/ArgumentDetailsCard.svelte"

tech_stack:
  added: []
  patterns:
    - "Empty-string sentinel pattern: frontend sends '' → backend converts with `or None` → DB stores NULL"
    - "Standalone CTA block with own const declarations — not nested inside parent guard that has the consts"

key_files:
  created: []
  modified:
    - "api/services/admin_arguments.py"
    - "app/src/routes/admin/pipeline/[job_id]/+page.server.ts"
    - "app/src/routes/admin/pipeline/[job_id]/+page.svelte"
    - "app/src/lib/components/ArgumentDetailsCard.svelte"

decisions:
  - "Empty string sentinel (not null) chosen to distinguish 'operator cleared all pills' from 'field not submitted'; service converts '' to None via `body.source_docket or None`"
  - "hints.question_number frozen to null in load() — Argument.question_number is the operator-editable column, not an immutable extraction; using it as a hint made the hint mutable"
  - "Standalone CTA block given its own arg/argStatus const declarations — extracted from the deleted outer {#if data.argument} guard to be self-contained"

metrics:
  duration: "10m"
  completed_date: "2026-07-03"
  tasks_completed: 5
  tasks_total: 5
  files_modified: 4
---

# Phase 23 Plan 04: Gap Closure — Pipeline Job Detail Page Summary

**One-liner:** Closed all five Phase 23 UAT failures: removed two orphaned UI cards, fixed silent docket-clear bug via empty-string sentinel, froze question_number hint to null, and promoted docket instruction from placeholder to always-visible static label.

## What Was Built

### Task 1 — Backend: source_docket clear fix (committed d8a657cb)

**`api/services/admin_arguments.py`:**
- Changed `values_to_set["source_docket"] = body.source_docket` to `values_to_set["source_docket"] = body.source_docket or None`
- The `or None` converts the empty-string sentinel `''` to Python `None`, which SQLAlchemy writes as DB NULL
- Non-empty strings pass through unchanged; truly-omitted fields (Python None from Pydantic default) still skip the key entirely via the `is not None` outer guard
- No schema changes — `MetadataUpdate.source_docket` remains `Optional[str] = None`

### Task 2 — Server: empty-string sentinel + frozen hint (committed a1f41371)

**`app/src/routes/admin/pipeline/[job_id]/+page.server.ts`:**
- `saveJobMetadata` action: changed `dockets[0] ?? null` → `dockets[0] ?? ''` so empty dockets array sends empty string instead of null (Gap 3)
- `hints.question_number` in `load()`: changed from `argument.question_number != null ? String(argument.question_number) : null` → `null` literal, eliminating the mutable hint source (Gap 4)
- `savedValues.question_number` (pre-population line) unchanged — that behavior is correct

### Task 3 — Page: remove orphaned cards + standalone CTA (committed 4278c9fb)

**`app/src/routes/admin/pipeline/[job_id]/+page.svelte`:**
- Deleted entire "Argument metadata preview card" block (comment + `{#if data.argument}` guard + static div card with Case title/Docket/Argued/Status/Edit link rows) — Gap 2
- Deleted entire "View source PDF link card" block (Gap 1)
- Replaced the orphaned CTA fragment with a fully self-contained standalone block that declares its own `arg` and `argStatus` consts, nested as `{#if data.argument && liveJob.status === 'completed'}{@const ...}{#if argStatus === 'draft'}...{/if}{/if}`
- ArgumentDetailsCard block placement unchanged; standalone CTA appears immediately after it

### Task 4 — Component: static docket instruction label (committed 5ac10e1a)

**`app/src/lib/components/ArgumentDetailsCard.svelte`:**
- Removed `placeholder="Add docket and press Enter…"` attribute from docket input element
- Added `<p>` element immediately above the input: "Type a docket number and press Enter to add it." (always visible, no conditional guard)

### Task 5 — Verification: svelte-check gate

- `cd app && npx svelte-check --tsconfig ./tsconfig.json` → 788 files, 0 errors, 18 warnings
- All 18 warnings are pre-existing (state_referenced_locally, a11y_autofocus, node_invalid_placement_ssr, a11y_click_events_have_key_events) — none introduced by this plan

## Deviations from Plan

None — plan executed exactly as written. All four files modified as specified. All five success criteria verified.

## Threat Mitigations Applied

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-23-04-01 | Mitigated | Empty-string sentinel converted to None server-side before write; never stored in DB as empty string |
| T-23-04-02 | Accept | View Source PDF card removed from page UI; /admin/pipeline/[id]/pdf route still exists and is admin-gated (not touched by this plan) |
| T-23-04-03 | Mitigated | Task 5 svelte-check gate passed: 0 errors |

## Known Stubs

None — all data paths live. Docket clear, question_number hint, and CTA logic all wired end-to-end.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundaries. All changes are UI/service-layer fixes to existing functionality.

## Self-Check

Task commits:
- d8a657cb: fix(23-04): treat empty-string source_docket as intentional clear-to-NULL
- a1f41371: fix(23-04): empty-string docket sentinel + freeze hints.question_number
- 4278c9fb: fix(23-04): remove orphaned Argument card + View Source PDF card; add standalone CTA
- 5ac10e1a: fix(23-04): replace docket placeholder with always-visible static label

Success criteria verification:
- Gap 1: grep "View source PDF" → 0 PASSED
- Gap 2: grep "Argument metadata preview card" → 0 PASSED; grep "Ready to publish" → 2 (comment + H2 in one block) PASSED
- Gap 3: grep "source_docket: dockets[0] ?? ''" → line 462 PASSED; grep "body.source_docket or None" → line 547 PASSED
- Gap 4: grep "question_number: null," → line 132 PASSED
- Gap 5: grep "placeholder" in ArgumentDetailsCard.svelte → 0 PASSED; static instruction label at line 169 PASSED
- svelte-check: 788 files, 0 errors PASSED

## Self-Check: PASSED
