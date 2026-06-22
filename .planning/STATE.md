---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Pre-Launch Polish
current_phase: 10
current_phase_name: Unified Navigation
status: executing
stopped_at: Phase 10 UI-SPEC approved
last_updated: "2026-06-22T16:34:38.258Z"
last_activity: 2026-06-22
last_activity_desc: Phase 09 complete, transitioned to Phase 10
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 3
  completed_plans: 3
  percent: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-18 after v1.2 milestone start)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** Phase 10 — unified-navigation

## Current Position

Phase: 10 — Unified Navigation
Plan: Not started
Status: Ready to execute
Last activity: 2026-06-22 — Phase 09 complete, transitioned to Phase 10

Progress: [███░░░░░░░] 33%

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

Last session: 2026-06-22T16:19:02.457Z
Stopped at: Phase 10 UI-SPEC approved
Resume file: .planning/phases/10-unified-navigation/10-UI-SPEC.md

## Operator Next Steps

- `/gsd-discuss-phase 10` — gather context for Unified Navigation
- `/gsd-plan-phase 10` — plan directly if context already gathered
