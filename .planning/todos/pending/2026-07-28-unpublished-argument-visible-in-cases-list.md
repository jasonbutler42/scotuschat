---
created: 2026-07-28T23:26:54.000Z
title: Unpublished argument still visible and directly accessible in /cases/ list
area: bug
resolves_phase: 45
files:

  - app/src/routes/cases/+page.server.ts (or equivalent /cases listing loader — not yet investigated)
  - api routes/services governing argument publish status (not yet investigated)

---

## Problem

Discovered during Phase 39's live-stack operator checkpoint (39-06), unrelated to that phase's scope (bench popover / birthdate / death date / reason-left work).

An argument that has not been published still appears in the public `/cases/` list, and can be opened directly by URL. Published/unpublished status should gate both listing visibility and direct access.

## Solution

TBD — not investigated yet. Needs:
- Confirming which layer leaks the unpublished argument: the `/cases/` list query itself, the argument detail route's own guard, or both.
- Deciding the correct behavior for direct URL access to an unpublished argument (404, redirect, or an explicit "not published" state) versus just filtering it from the list.
