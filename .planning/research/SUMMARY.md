# Project Research Summary

**Project:** SCOTUS Chat v1.2 — Pre-Launch Polish
**Domain:** Admin tooling + public content site (SCOTUS oral argument viewer)
**Researched:** 2026-06-18
**Confidence:** HIGH

## Executive Summary

SCOTUS Chat v1.2 is a polish milestone that completes admin tooling and enriches the public experience before the first deployment. The existing stack (SvelteKit 2 + Svelte 5 Runes, FastAPI 0.115+, PostgreSQL 16, SQLAlchemy 2.0 async, Alembic, DO Spaces via boto3) is fully validated and requires only two net-new dependencies: `bits-ui ^2.18.1` (Svelte 5-native headless Popover for the speaker card) and `Pillow >=11.0` (image validation and resize on the FastAPI side). All other v1.2 features are built on patterns already established in the codebase.

The recommended approach follows a strict dependency order: the Alembic migration that adds structured name fields and appointing president/party columns to `people` must land first because it unblocks both the speaker popover (public feature) and the updated admin edit form. Unified navigation is the second priority — zero data dependencies, highest perceived polish gain, and it automatically benefits every subsequent admin page added in this milestone. People admin improvements (image upload, delete, merge) and argument metadata editing are then built in parallel, with merge deferred to last because it is the highest-complexity operation. The speaker popover closes out the milestone once the data pipeline has been populated.

The top risks are: (1) people merge atomicity — all four FK tables (`utterances`, `speaker_alias`, `case_appearances`, `argument_participants`) must transfer in a single transaction or partial state is unrecoverable without a backup; (2) client-side fetch for speaker popover data, which would expose `FASTAPI_BASE_URL` and break SSR — all popover data must be pre-loaded in `+page.server.ts`; (3) the apolitical framing constraint — party affiliation must not appear in the public popover, only in admin metadata.

## Key Findings

### Recommended Stack

The existing stack requires no structural changes. Two additions are needed: `bits-ui` for the Popover component (the only Svelte 5-native headless option after `@skeletonlabs/floating-ui-svelte` was archived October 2025), and `Pillow` for server-side image validation and resize.

**Core technologies:**
- `bits-ui ^2.18.1`: Headless Popover for speaker card — Svelte 5 Runes native, wraps Floating UI, handles ARIA and collision detection automatically
- `Pillow >=11.0`: Image validation + resize before Spaces upload — standard FastAPI image upload companion
- `boto3` (existing): DO Spaces image upload via `asyncio.to_thread` — same pattern as PDF upload
- SQLAlchemy 2.0 async (existing): People merge via `async with db.begin()` — all FK updates + DELETE in one transaction
- Alembic hand-written migrations (existing): Migration 0006 adds 6 nullable columns to `people`; `full_name` preserved as resolution anchor

### Expected Features

**Must have (table stakes) — all required for v1.2:**
- Unified top navigation — prerequisite for "done" perception
- Ingestion flow polish (progress indicators, typeahead, incomplete toggle)
- Argument metadata editing (pre-resolve) — no path exists today to correct pipeline-derived names
- People data model migration (structured names + appointing president/party) — unblocks speaker popover
- People delete (orphaned records)
- Image upload to DO Spaces

**Should have (differentiators) — also required for v1.2:**
- Speaker popover card (bench only) — primary public-facing differentiator
- People merge (utterance transfer) — resolve creates duplicate person records

**Defer (v2+):**
- Image crop in upload flow
- Post-resolve metadata editing with explicit reset action
- Automated enrichment from Oyez/FJC API
- Speaker statistics across arguments (apolitical constraint makes this high-risk)

### Architecture Approach

The architecture is additive: one Alembic migration, two new SvelteKit routes, five new/modified FastAPI endpoints, two new Svelte components, and three new FastAPI service modules. Core data flow constraints are unchanged.

**Major components:**
1. `NavHeader.svelte` (NEW) — shared nav with `variant: 'public' | 'admin'` prop; replaces duplicate inline markup
2. `SpeakerPopover.svelte` (NEW) — floating card with data pre-loaded server-side; no client-side fetch
3. Alembic migration 0006 (NEW) — 6 nullable columns on `people`; `full_name` preserved as resolution anchor
4. `services/admin_arguments.py` (NEW) — `ArgumentUpdate` schema excludes `resolved_at` by design
5. `upload_image_to_spaces` (NEW in `spaces.py`) — magic bytes + 5MB limit + Pillow resize + Spaces upload
6. `merge_people` (NEW in `admin_people.py`) — 4 FK tables + DELETE in single `async with db.begin()`

### Critical Pitfalls

1. **Non-atomic people merge (W1+W2)** — All four FK tables must transfer in one `async with db.begin()` block. Never commit mid-transfer.
2. **Client-side speaker popover fetch (W7)** — Pre-load bench person details in `+page.server.ts`. No `PUBLIC_FASTAPI_BASE_URL` anywhere.
3. **full_name corrupted by migration auto-split (W5+W6)** — `full_name` remains the resolution anchor throughout v1.2. Never replace it in queries while rows are still null.
4. **resolved_at gate bypassed via schema inclusion (W9+W10)** — `ArgumentUpdate` must never include `resolved_at`. Server rejects writes to docket/date fields when `resolved_at IS NOT NULL`.
5. **Appointing party in public popover (W14)** — `appointing_party` is admin-only. Public popover shows "Appointed by [president]" only — no party affiliation.

## Implications for Roadmap

### Suggested Phase Order (6 phases, continuing from Phase 8)

| Phase | Name | Rationale |
|-------|------|-----------|
| 9 | People Data Model Migration | Foundation — 5 of 6 clusters depend on new `people` columns |
| 10 | Unified Navigation | Zero dependencies; benefits all subsequent admin pages |
| 11 | Argument Metadata Editing | Independent; no schema changes; unblocks pre-publish correction |
| 12 | People Admin Improvements | Delete → image upload → merge (ascending complexity) |
| 13 | Ingestion Flow Polish | Fixes known polling gaps; parallelizable with Phase 12 |
| 14 | Speaker Popover Card | Final; depends on Phase 9 data and Phase 12 photos |

### Research Flags

Standard patterns (skip research-phase during planning): Phases 9, 10, 11, 13

May benefit from targeted planning research:
- **Phase 12 (Merge):** Enumerate all FK constraints from `people.id` via codebase inspection before writing merge code
- **Phase 14 (Popover):** Review bits-ui 2.x Popover API + WCAG focus-trap requirements before implementation

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM | bits-ui/Pillow are new; DO Spaces ACL has a known intermittent ignore issue |
| Features | HIGH | Derived from direct codebase inspection; all six clusters well-scoped |
| Architecture | HIGH | Direct codebase inspection of models, services, routes, layout files |
| Pitfalls | HIGH | 15 v1.2-specific pitfalls from codebase inspection |

**Overall confidence:** HIGH

### Open Gaps

- **DO Spaces ACL:** Enable bucket-level public access for `people/` prefix; verify with test upload
- **`photo_url` format:** Decide before Phase 12 — store Spaces key or full URL
- **bits-ui z-index in chat layout:** Two-column layout may create stacking contexts; verify during Phase 14
- **Name backfill quality:** SQL `split_part` is approximate; operator must audit all `people` rows after Phase 9

## Sources

### Primary (direct codebase inspection)
- `api/models/models.py`, `api/services/admin_people.py`, `api/services/spaces.py`
- `app/src/routes/admin/+layout.svelte`, `app/src/routes/+layout.svelte`
- `.planning/PROJECT.md`

### Secondary
- bits-ui.com/docs/components/popover
- pillow.readthedocs.io
- alembic.sqlalchemy.org, docs.sqlalchemy.org
- docs.digitalocean.com/products/spaces

---
*Research completed: 2026-06-18*
*Ready for roadmap: yes*
