---
phase: 23-shared-argument-details-component
plan: "07"
subsystem: admin-pipeline
tags: [multi-docket, migration, schema, service, sveltekit, gap-closure]
dependency_graph:
  requires: [23-05, 23-06]
  provides: [multi-docket-support, source_dockets-array-column]
  affects: [admin-pipeline-job-detail, argument-details-card, argument-metadata-patch]
tech_stack:
  added: [postgresql-array, sqlalchemy-array-column]
  patterns: [D-MULTI-DOCKET, WR-01-null-when-cleared, T-23-07-normalize-trim-dedup]
key_files:
  created:
    - alembic/versions/0014_add_source_dockets_array.py
  modified:
    - api/models/models.py
    - api/schemas/admin_arguments.py
    - api/services/admin_arguments.py
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/lib/components/ArgumentDetailsCard.svelte
decisions:
  - "D-MULTI-DOCKET: source_docket retained as canonical dedup key (= dockets[0]); source_dockets[] added as ordered list — join table rejected as unnecessary ripple through ingest/parse"
  - "WR-01 NULL semantics: empty docket array stored as NULL in both source_dockets and source_docket (cleared state)"
  - "Service normalizes source_dockets on write: strip, drop empties, de-duplicate order-preserving — T-23-07-01 mitigation"
metrics:
  duration_minutes: 12
  completed_date: "2026-07-06"
  tasks_completed: 3
  tasks_total: 3
  files_changed: 6
status: complete
---

# Phase 23 Plan 07: Multi-Docket Array Support Summary

Full-stack multi-docket support: operators can now record multiple docket numbers for consolidated SCOTUS cases — stored in a new `source_dockets text[]` column while `source_docket` is retained as the canonical UNIQUE-constraint dedup key.

## What Was Built

### Task 1 — Migration 0014 + ORM Model (commit 872ab771)

Created `alembic/versions/0014_add_source_dockets_array.py`:
- `upgrade()`: `op.add_column` adds `arguments.source_dockets ARRAY(VARCHAR(50)) NULL`; then `op.execute` backfills `ARRAY[source_docket]` for all non-NULL rows.
- `downgrade()`: drops `source_dockets` column only — `source_docket` and `uq_arguments_source_docket_question` constraint untouched.

Updated `api/models/models.py`:
- Added `from sqlalchemy.dialects.postgresql import ARRAY, JSONB` (combined import).
- Added `source_dockets = Column(ARRAY(String(50)), nullable=True)` immediately after `source_docket` with comment explaining D-MULTI-DOCKET sync invariant.
- `source_docket` column and `__table_args__` UNIQUE constraint unchanged.

### Task 2 — API Schema + Service (commit e14e71da)

`api/schemas/admin_arguments.py`:
- `ArgumentDetail`: added `source_dockets: list[str] = []` alongside `source_docket`.
- `MetadataUpdate`: added `source_dockets: Optional[list[str]] = None`; docstring updated to list it in the mass-assignment allowlist (T-23-07).

`api/services/admin_arguments.py`:
- `get_argument_detail`: added `"source_dockets": argument.source_dockets or []` after `"source_docket"` key.
- `update_argument_metadata`: when `body.source_dockets is not None`, normalizes (strip/dedup/drop-empty order-preserving), sets `source_dockets = normalized or None` and `source_docket = normalized[0] if normalized else None`. Falls back to existing `elif body.source_docket is not None` branch for backward compatibility.
- `check_duplicate_argument` left unchanged — uses singular `source_docket` for dedup.

### Task 3 — SvelteKit (commit 91ebc759)

`app/src/routes/admin/pipeline/[job_id]/+page.server.ts`:
- `ArgumentPreview` interface: added `source_dockets: string[] | null`.
- `load()`: `savedValues.dockets` now prefers `argument.source_dockets` with fallback to `[argument.source_docket]` for not-yet-migrated rows.
- Removed entire `if (dockets.length > 1) fail(400)` guard block (the CR-02 single-docket rejection).
- PATCH body: `source_dockets: dockets` (full array) instead of `source_docket: dockets[0] ?? ''`.

`app/src/lib/components/ArgumentDetailsCard.svelte`:
- `addPill()`: removed `if (pills.length >= 1) return` cap; duplicate/empty guard retained.
- Input `disabled`: changed from `disabled={readonly || pills.length >= 1}` to `disabled={readonly}`.
- Enter handler: `if (!readonly && pills.length < 1) addPill()` → `if (!readonly) addPill()`.
- Removed `{#if pills.length >= 1 && !readonly}` "Remove the existing entry..." helper block.
- `$effect` pill restore from `form.dockets` and `docket[]` hidden-input serialization unchanged.

## Verification Results

- Task 1: `ast.parse` passes for both files; `grep` confirms `source_dockets`, `ARRAY`, `down_revision.*0013`.
- Task 2: `ast.parse` passes for both files; `source_dockets` present in schema and service; `normalized[0]` sync confirmed.
- Task 3: `npx svelte-check` — 788 files, 0 errors; rejection string absent; `pills.length >= 1` cap removed; `source_dockets` present in server file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrupted em-dash in CR-02 comment blocked Edit match**
- **Found during:** Task 3 — first Edit attempt on the guard block failed because the em-dash character in the comment was a replacement character (U+FFFD), not an actual em-dash.
- **Fix:** Removed the guard block in two steps: first the `if (dockets.length > 1)` block (matching from the `if` line, avoiding the corrupted comment), then used Python regex to strip the dangling orphaned comment line.
- **Files modified:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts`
- **Commit:** 91ebc759

## Known Stubs

None — all data paths are wired. `source_dockets` flows from DB → service → schema → server → component (pills) → hidden inputs → PATCH → service write → DB.

## Operator Setup Required

After deploying this code, the operator must run:

```bash
alembic upgrade head
```

This applies migration 0014 which adds `source_dockets text[]` to the `arguments` table and backfills from existing `source_docket` values. The app will not reflect multi-docket values until this migration is applied.

## Threat Surface Scan

No new network endpoints or auth paths introduced. The PATCH endpoint `/api/admin/arguments/{id}/metadata` already existed; its body now accepts an additional `source_dockets` field covered by the existing `MetadataUpdate` mass-assignment allowlist. T-23-07-01 (input normalization) and T-23-07-03 (dedup constraint integrity via `source_docket[0]`) mitigations are implemented in the service layer.

## Self-Check: PASSED

- `alembic/versions/0014_add_source_dockets_array.py` exists
- `api/models/models.py` contains `source_dockets`
- `api/schemas/admin_arguments.py` contains `source_dockets`
- `api/services/admin_arguments.py` contains `source_dockets` and `normalized[0]` sync
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` contains `source_dockets` and lacks rejection string
- `app/src/lib/components/ArgumentDetailsCard.svelte` lacks `pills.length >= 1` cap
- Commits 872ab771, e14e71da, 91ebc759 all present in git log
