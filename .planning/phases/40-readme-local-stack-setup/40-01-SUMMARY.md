---
phase: 40-readme-local-stack-setup
plan: 01
subsystem: documentation
tags: [environment, fastapi, sveltekit, postgresql]
requires: []
provides:
  - Backend-only root environment example
  - Server-private SvelteKit environment example
  - Portable PostgreSQL binary ignore coverage
affects: [40-02, 40-03, README]
tech-stack:
  added: []
  patterns: [runtime-specific environment contracts, placeholder-only examples]
key-files:
  created: [app/.env.example]
  modified: [.env.example, .gitignore]
decisions:
  - Keep ADMIN_TOKEN duplicated across runtime env files with an explicit exact-match contract.
  - Keep all five SvelteKit variables server-private and document optional backend settings by operating concern.
metrics:
  duration: 10m
  completed: 2026-07-14
status: complete
---

# Phase 40 Plan 01: Runtime Environment Contracts Summary

Backend and SvelteKit now have separate placeholder-only environment contracts, with portable PostgreSQL binaries excluded from version control.

## Accomplishments

- Reworked the root example around the minimum FastAPI/PostgreSQL settings and clearly labeled optional test database, LLM, object-storage, and diagnostics settings.
- Added a SvelteKit example containing exactly the five server-private runtime keys and an explicit shared `ADMIN_TOKEN` invariant.
- Added directory-level ignore coverage for the documented `data/pgsql/` portable PostgreSQL installation.

## Task Commits

1. **Task 1: Split backend and SvelteKit environment examples** - `c938598a`
2. **Task 2: Ignore the documented portable PostgreSQL installation** - `4b371655`

## Files Created/Modified

- `.env.example` - Backend and PostgreSQL environment contract with optional groups.
- `app/.env.example` - SvelteKit server-private environment contract.
- `.gitignore` - Portable PostgreSQL binary directory exclusion.

## Decisions Made

- The shared admin token uses the same descriptive placeholder in both files so its exact-match ownership is visible before README setup instructions refer to it.
- `DEBUG` is isolated as a deployment diagnostics setting and defaults to `false`; object-storage credentials remain an optional backend-only group.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `.env.example` and `app/.env.example` intentionally contain angle-bracket placeholders. These are safe checked-in templates that operators must replace in their ignored runtime `.env` files; they are not application stubs.

## Verification

- Confirmed required root and app keys, rejected app public prefixes, and confirmed the app example contains exactly five runtime keys.
- Confirmed no SvelteKit-only keys remain in the root example and no concrete provider key or generated secret pattern is present.
- Confirmed `data/pgsql/` content is ignored while `app/.env.example` remains trackable.
- `git diff --check` passed.

## Self-Check: PASSED

- All three scoped files exist.
- Task commits `c938598a` and `4b371655` exist in repository history.
