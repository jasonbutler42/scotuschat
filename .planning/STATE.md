---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Pre-Launch Polish
status: planning
last_updated: "2026-06-18"
last_activity: 2026-06-18
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-18 after v1.2 milestone start)

**Core value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.
**Current focus:** v1.2 Pre-Launch Polish — Phase 9 ready to plan

## Current Position

Phase: 9 of 14 (People Data Model Migration)
Plan: — of —
Status: Ready to plan
Last activity: 2026-06-18 — Roadmap created for v1.2; Phase 9 is next

Progress: [░░░░░░░░░░] 0%

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

## Accumulated Context

### Decisions

Full log in PROJECT.md Key Decisions table. Key decisions for v1.2:

- [Research]: `bits-ui ^2.18.1` chosen for speaker popover — only Svelte 5-native headless popover after `@skeletonlabs/floating-ui-svelte` archived Oct 2025
- [Research]: `Pillow >=11.0` needed for server-side image validation + resize before Spaces upload
- [Research]: `full_name` stays as resolution anchor throughout v1.2 — Alembic migration 0006 adds 6 nullable columns; never replace `full_name` in queries while rows may be null
- [Research]: People merge must transfer all 4 FK tables (utterances, speaker_alias, case_appearances, argument_participants) in single `async with db.begin()` — no commit mid-transfer
- [Research]: Speaker popover data pre-loaded in `+page.server.ts` — no client-side fetch, no `PUBLIC_FASTAPI_BASE_URL`
- [Research]: `appointing_party` is admin-only — public popover shows "Appointed by [president]" with no party affiliation

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

Last session: 2026-06-18
Stopped at: v1.2 roadmap created — 6 phases (9–14), 16/16 requirements mapped
Resume file: None

## Operator Next Steps

- `/gsd-discuss-phase 9` — gather context for People Data Model Migration
