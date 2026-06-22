---
phase: "11"
plan: "04"
subsystem: admin-pipeline-ui
tags: [argument-preview, job-detail, ready-to-publish, cta, svelte, fastapi]
status: complete

requires: ["11-02"]
provides: ["argument-preview-card", "ready-to-publish-cta"]
affects: ["admin-pipeline-job-detail"]

tech_stack:
  added: []
  patterns:
    - "Separate argument fetch in SvelteKit load (not embedded in AdminJobResponse) — RESEARCH Pattern 5"
    - "Graceful degrade: try/catch defaults argument to null; job view renders regardless"
    - "Status badge: Published (#4ade80) / Resolved (#a78bfa) / Pending (#94a3b8)"
    - "toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }) for date display"

key_files:
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte

decisions:
  - "ArgumentPreview interface added to +page.server.ts — subset of ArgumentDetail (id, case_name, docket_number, argued_date, resolved_at, published_at)"
  - "Argument fetch only fires when job.argument_id != null — no wasted requests for jobs without an argument"
  - "Ready-to-publish CTA guards: data.job.status === 'completed' && arg.published_at == null — handles resolved-but-not-published and unresolved-not-published equally"
  - "Argument preview uses inline @const helpers for status derivation — consistent with existing job detail page patterns"

metrics:
  duration_minutes: 2
  completed_date: "2026-06-22"
  tasks_completed: 2
  files_modified: 2
---

# Phase 11 Plan 04: Argument Metadata Preview on Job Detail Page Summary

**One-liner:** Job detail page now surfaces argument preview card (case title, docket, argued date, status badge, edit link) and a "Ready to publish" CTA when the job is completed but the argument is unpublished.

---

## What Was Built

Extended the existing `/admin/pipeline/[job_id]` route with two additions:

**`+page.server.ts`** — Added `ArgumentPreview` interface and a conditional fetch to `GET /api/admin/arguments/{argument_id}` when `job.argument_id != null`. The fetch is wrapped in try/catch; on any error or non-OK response `argument` defaults to `null` so the existing page still renders. The load return object now includes `argument` alongside `job`, `people`, `peopleLoadError`, and `participants`.

**`+page.svelte`** — Added two new sections inside `{#if data.argument}`, inserted above the existing step timeline:

1. **Argument preview card** (bg `#1e293b`, border `#334155`, radius 8px, padding 24px): rows for Case title, Docket, Argued (formatted `MMM D, YYYY`), Status (badge with Published/Resolved/Pending colors), and an `<a href="/admin/arguments/{id}">Edit argument metadata</a>` anchor link.

2. **Ready to publish CTA** (border `1px solid #93c5fd`, radius 8px, padding 24px): heading "Ready to publish", body copy, and a `<a href="/admin/arguments/{id}">Go to argument editor</a>` link (min-height 44px). Rendered only when `data.job.status === 'completed' && arg.published_at == null`.

---

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 1 | Extend job detail load to fetch argument metadata | cc3a3f0 |
| 2 | Render argument preview card and Ready-to-publish CTA | e23c09b |

---

## Acceptance Criteria Verification

- [x] Load fetches `/api/admin/arguments/${job.argument_id}` only when `job.argument_id != null`
- [x] Argument fetch wrapped in try/catch; defaults `argument` to null on failure
- [x] Load return includes `argument` alongside `job`, `people`, `peopleLoadError`, `participants`
- [x] `svelte-check` reports no errors (0 errors, 11 warnings — warnings pre-existing)
- [x] Argument preview card renders only inside `{#if data.argument}` — above step timeline
- [x] Card contains `<a href="/admin/arguments/{data.argument.id}">Edit argument metadata</a>`
- [x] "Ready to publish" CTA renders only when `data.job.status === 'completed'` and `data.argument.published_at == null`
- [x] CTA link text is "Go to argument editor" pointing to the argument editor
- [x] Existing resolve card, polling effect, and participant section unchanged
- [x] Copywriting verbatim from UI-SPEC Copywriting Contract

---

## Threat Mitigations Verified

| Threat ID | Mitigation Applied |
|-----------|-------------------|
| T-11-ENV2 | `FASTAPI_BASE_URL` and `ADMIN_TOKEN` imported from `$env/static/private`; never client-exposed |
| T-11-DEGRADE | try/catch defaults `argument = null`; existing job view renders regardless of argument fetch outcome |
| T-11-XSS2 | `{arg.case_name}`, `{arg.docket_number}` rendered as Svelte text interpolation — auto-escaped; no `{@html}` used |

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None. Both sections are wired to live data returned from the server load (`data.argument`).

---

## Threat Flags

None. No new network endpoints, auth paths, or schema changes introduced. The argument fetch is server-side with the existing `X-Admin-Token` pattern.

---

## Self-Check

Files exist:
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — modified
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — modified

Commits exist: cc3a3f0, e23c09b
