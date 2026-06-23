---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Pre-Launch Polish
current_phase: 12
current_phase_name: people-admin-improvements
status: executing
stopped_at: Completed 12-02-PLAN.md HTTP endpoints
last_updated: "2026-06-23T22:12:16.434Z"
last_activity: 2026-06-23
last_activity_desc: Phase 12 execution started
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 12
  completed_plans: 10
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-18 after v1.2 milestone start)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 12 — people-admin-improvements

## Current Position

Phase: 12 (people-admin-improvements) — EXECUTING
Plan: 3 of 4
Status: Ready to execute
Last activity: 2026-06-23 — Phase 12 execution started

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity (v1.1 baseline):**

- Total plans completed (v1.1): 23
- Average duration: ~40 min/plan
- Phases 5–8 completed in 4 days

**By Phase (v1.1):**

| Phase | Plans | Notes |
|-------|-------|-------|
| 05 | 2 | Admin foundation |
| 06 | 3 | Auth |
| 07 | 8 | Pipeline runner |
| 08 | 6 | People editor |

*Updated after each plan completion*
| Phase 09 P01 | 97 | 3 tasks | 3 files |
| Phase 09 P02 | 119 | 3 tasks | 2 files |
| Phase 09 P03 | 92 | 2 tasks | 2 files |
| Phase 09 P03 | 92 | 3 tasks | 2 files |
| Phase 10 P01 | 2 | 3 tasks | 3 files |
| Phase 11 P02 | 3 | 3 tasks | 5 files |
| Phase 11 P03 | 10 | 3 tasks | 5 files |
| Phase 11 P04 | 2 | 2 tasks | 2 files |
| Phase 12 P01 | 35 | 2 tasks | 4 files |
| Phase 12 P02 | 25 | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Full log in PROJECT.md Key Decisions table. Key decisions for v1.2:

- [Research]: `bits-ui ^2.18.1` chosen for speaker popover — only Svelte 5-native headless popover after `@skeletonlabs/floating-ui-svelte` archived Oct 2025
- [Research]: `Pillow >=11.0` needed for server-side image validation + resize before Spaces upload
- [Research]: `full_name` stays as resolution anchor throughout v1.2 — Alembic migration 0006 adds 6 nullable columns; never replace `full_name` in queries while rows may be null
- [Research]: People merge must transfer all 4 FK tables (utterances, speaker_alias, case_appearances, argument_participants) in single `async with db.begin()` — no commit mid-transfer
- [Research]: Speaker popover data pre-loaded in `+page.server.ts` — no client-side fetch, no `PUBLIC_FASTAPI_BASE_URL`
- [Research]: `appointing_party` is admin-only — public popover shows "Appointed by [president]" with no party affiliation
- [09-01]: Migration 0006 adds six nullable columns to people (D-01); full_name NOT NULL preserved as resolution anchor (D-02); no backfill (D-03)
- [09-01]: PersonUpdate mass-assignment allow-list extended with six new fields — only path to write first_name, last_name, middle_name, name_suffix, appointing_president, appointing_president_party (T-09-01 mitigated)
- [Phase ?]: [09-02]: _derive_full_name requires BOTH first_name AND last_name non-empty (D-04/D-05 deviation, Pitfall 3 — prevents anchor corruption)
- [Phase ?]: [09-02]: get_person_detail return dict explicitly includes all six new keys (Pitfall 2 — missing keys would silently reload as None)
- [Phase ?]: [09-03]: PersonDetail TS interface, save action, and PATCH body extended with six new people fields; form extended with name-parts grid and Appointment section (PEOP-01, PEOP-02 closed)
- [Phase ?]: [10-01]: TopNav accepts variant prop; each layout passes its own value — component stays URL-unaware (D-03/D-04)
- [Phase ?]: [10-01]: Login guard stays in admin layout (not TopNav) to keep component URL-unaware; root layout admin guard preserved to prevent double-nav stacking
- [Phase ?]: [11-01] D-05 complete
- [Phase ?]: [11-01]: Migration 0007 adds nullable published_at to arguments; resolved_at unchanged — D-05 complete
- [Phase ?]: [11-01]: get_cases() public gate swapped to published_at.isnot(None); no other service uses resolved_at.isnot — D-06 complete
- [Phase ?]: [11-02]: ArgumentUpdate allow-list is exactly {case_name, docket_number, argued_date} — published_at never PATCH-writable (T-11-MASS)
- [Phase ?]: [11-02]: slug freeze — re-derive only when argument.published_at IS None; when published only case_name updates (D-11)
- [Phase ?]: [11-02]: publish_argument enforces resolved_at IS NOT NULL server-side (T-11-PUBGATE / Pitfall 1)
- [Phase ?]: [11-03]: Arguments list load degrades to [] on non-OK
- [Phase ?]: [11-03]: Edit page save parses 422 body to discriminate slug_collision vs docket_collision
- [Phase ?]: [11-03]: toDateInputValue() slices first 10 chars of ISO string for date input compatibility
- [Phase ?]: [12-01]: upload_photo_to_spaces mirrors upload_pdf_to_spaces with caller-supplied content_type; no ACL arg (deferred)
- [Phase ?]: [12-01]: merge_people uses single async with db.begin() — no inner db.commit() (D-10, T-12-ATOMIC)
- [Phase ?]: [12-01]: delete_person_if_orphan returns False (not raises) when FK rows exist — router translates to 409 (D-06)
- [Phase ?]: [12-01]: get_merge_preview takes only source_id — target_id not needed for counts (D-09)
- [Phase ?]: [12-02]: img.format read before img.verify() — Pillow verify() exhausts the image object (Pitfall 2)
- [Phase ?]: [12-02]: StaticFiles mount placed after router includes — API routes take precedence; harmless when Spaces is active
- [Phase ?]: [12-02]: target_id accepted as query param for merge-preview but counts derive from source only (D-09 confirmed)

### Pending Todos

None yet.

### Blockers/Concerns

- `BODY_SIZE_LIMIT` default 512KB blocks real SCOTUS PDFs — must set `BODY_SIZE_LIMIT=10M` in DO App Platform env (carried from v1.1)
- `ORIGIN` env var missing on DO causes silent CSRF 403 at login — set `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER` (carried from v1.1)
- `admin.scotuschat.com` DNS entry must be created before deployment smoke test (carried from v1.1)
- DO Spaces ACL: enable bucket-level public access for `people/` prefix; verify with test upload before Phase 12
- Decide `photo_url` format before Phase 12: store Spaces key or full URL

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| verification | 01-VERIFICATION.md | human_needed (stale — human UAT completed per commits) | 2026-06-15 |
| verification | 03-VERIFICATION.md | human_needed (stale — 03-HUMAN-UAT.md: complete) | 2026-06-15 |
| verification | 04-VERIFICATION.md | human_needed (stale — 04-UAT.md: passed) | 2026-06-15 |

## Session Continuity

Last session: 2026-06-23T22:12:16.426Z
Stopped at: Completed 12-02-PLAN.md HTTP endpoints
Resume file: 

- `/gsd-discuss-phase 11` — gather context for Argument Metadata Editing
- `/gsd-plan-phase 11` — plan directly if context already gathered
