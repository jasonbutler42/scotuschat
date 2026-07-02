# Phase 22: Schema Foundations - Context

**Gathered:** 2026-07-02
**Status:** Ready for planning

<domain>
## Phase Boundary

All new database migrations and pipeline data changes required by v1.5 UI phases — four discrete schema changes that downstream phases depend on before building any UI. This phase delivers migrations only; no UI, no API endpoints, no admin screens.

Changes:
1. Add `unpublished` to `argument_status` PG enum (ALIST-01)
2. Create `argument_status_log` table with backfill (AEDIT-02)
3. Add `argument_participants.title` VARCHAR + parse step TOC extraction (PJOB-13)
4. Move `appointed_by` + `appointing_president_party` from `people` to `court_tenures` (PEDIT-10)

</domain>

<decisions>
## Implementation Decisions

### Migration Structure
- **D-01:** Two separate migrations — `0012` and `0013` — not one combined migration.
- **D-02:** Migration `0012` covers: `unpublished` enum expansion + `argument_status_log` table creation.
- **D-03:** Migration `0013` covers: `argument_participants.title` column + move `appointed_by`/`appointing_president_party` from `people` to `court_tenures`.
- **D-04:** Within `0012`, enum expansion must run first (COMMIT + ALTER TYPE ADD VALUE), then CREATE TABLE `argument_status_log` — PG requires the enum value to exist before the table can reference it.

### argument_status_log Schema
- **D-05:** Minimal schema: `id PK`, `argument_id FK → arguments.id`, `status argument_status`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **D-06:** No `previous_status`, no `notes`, no `triggered_by` — the current status value at each timestamped entry is sufficient for Phase 26's timeline display.
- **D-07:** Backfill: existing arguments each get one `created` log entry. Use `resolved_at` as the `created_at` timestamp when available; fall back to `CURRENT_TIMESTAMP` for rows where `resolved_at IS NULL`.

### Appointed-by Column Move
- **D-08:** No data backfill — existing `people.appointed_by` and `people.appointing_president_party` data is incorrect/test data. Add both columns to `court_tenures` as nullable (no default), drop from `people`, leave all new court_tenures rows NULL. Operator fills via Phase 27 UI.
- **D-09:** Drop `people.appointed_by` and `people.appointing_president_party` in the same migration `0013` — do not stage the drop in a later migration.

### Advocate Title Extraction
- **D-10:** `argument_participants.title` captures the subtitle line from the TOC immediately following the advocate name line — e.g., "Solicitor General", "Counsel of Record", "Attorney General of [State]". Not the name-line prefix/suffix (ESQ., GEN.).
- **D-11:** Extraction failure is silent NULL — never raise on missing subtitle. Parse step continues normally. NULL means "not found"; operator can fill via Phase 23 UI later.
- **D-12:** Title extraction logic lives in `cover_extractor.py` as a new function alongside `extract_advocate_sides`. TOC parsing runs once; both functions share the same TOC read. Parse step calls both.

### Claude's Discretion
- Migration ordering within `0012` (enum first, then log table) — technically mandated by PG constraints, confirmed as correct approach.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Schema and Migrations
- `alembic/versions/0008_side_enum_and_argument_status.py` — established pattern for `COMMIT` + `ALTER TYPE ADD VALUE`; downgrade() does NOT attempt to remove enum values (PG limitation). MUST follow this pattern in `0012`.
- `alembic/versions/0011_add_source_docket_cover_metadata.py` — most recent migration template; shows column add patterns, nullable handling, and downgrade() reversal order.
- `api/models/models.py` — full current ORM schema; `ArgumentStatusEnum`, `ArgumentParticipant`, `CourtTenure`, `Person` models all affected by Phase 22 changes.

### Pipeline — Parse Step
- `pipeline/commands/parse.py` — parse step entry point; calls `extract_advocate_sides` from `cover_extractor.py`; `_update_participant_sides` shows how TOC data flows into `argument_participants`. Title extraction will follow the same pattern.
- `pipeline/parser/cover_extractor.py` — contains `extract_advocate_sides`, `_parse_toc_sides`, and the TOC line regex patterns. New `extract_advocate_titles` function goes here.

### Requirements
- `.planning/REQUIREMENTS.md` — ALIST-01, AEDIT-02, PJOB-13, PEDIT-10 are the four requirements this phase satisfies.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cover_extractor.py:extract_advocate_sides` — parses TOC advocate lines (name + side attribution). New title extraction function should share the same TOC page read to avoid double PDF I/O.
- `alembic/versions/0008_side_enum_and_argument_status.py` — downgrade() template for enum migrations (does not attempt to remove enum values).
- `pipeline/commands/parse.py:_update_participant_sides` (line ~431) — template for `_update_participant_titles`: same loop structure, same `argument_id` scope.

### Established Patterns
- **PG enum expansion**: `op.execute(sa.text("COMMIT"))` → `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'` — established in 0008; must be followed exactly in 0012.
- **Nullable new columns**: All Phase 22 new columns are nullable with no server default (except `created_at` on log table). Pattern from 0011.
- **`statement_cache_size=0` in asyncpg `connect_args`**: Already in engine config; no change needed.
- **`cover_extractor.py` fail-safe**: Any exception returns empty dict/None; parse step never fails due to cover extraction. Same for title extraction.

### Integration Points
- `api/models/models.py`: Add `title` to `ArgumentParticipant`, add `appointed_by`/`appointing_president_party` to `CourtTenure`, remove from `Person`, add `UNPUBLISHED` to `ArgumentStatusEnum`.
- `api/models/models.py`: New `ArgumentStatusLog` model (Table 13, BigInteger or Integer PK).
- `pipeline/commands/parse.py`: Import and call new `extract_advocate_titles` from `cover_extractor.py`; new `_update_participant_titles` function to write results to DB.
- Any service that reads `person.appointing_president` or `person.appointing_president_party` will break after `0013` drops those columns — researcher should audit usages before planning.

</code_context>

<specifics>
## Specific Ideas

- The existing `_parse_toc_sides` function's "last name collision" note applies equally to title extraction — if two advocates share the same last name, the title for the second one overwrites the first in the mapping. This is accepted behavior (same as side detection).
- The `argument_status_log` backfill uses `COALESCE(resolved_at, CURRENT_TIMESTAMP)` per-row — this is a SQL-level UPDATE, not application code.
- `people.appointed_by` and `people.appointing_president_party` are currently populated with test/incorrect data — no loss from dropping without backfill.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 22-Schema Foundations*
*Context gathered: 2026-07-02*
