---
phase: 19
plan: "04"
subsystem: frontend
tags:
  - sveltekit
  - admin
  - pipeline
  - duplicate-prevention
  - metadata-card
  - preflight
  - server-proxy
dependency_graph:
  requires:
    - 19-02 (pipeline ingest accepts --primary-docket and --question args)
    - 19-03 (GET /api/admin/arguments/check-duplicate, PATCH /api/admin/arguments/{id}/metadata, ArgumentDetail.source_docket/cover_metadata)
  provides:
    - GET /admin/pipeline/check-duplicate (SvelteKit server-only proxy)
    - Docket + question fields on pipeline start form with JS preflight
    - Duplicate warning banner (Component 3) with Cancel / Start anyway
    - Argument Metadata card (Component 4) on job detail page
    - saveMetadata form action
  affects:
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
tech_stack:
  added: []
  patterns:
    - T-12-TOKENLEAK: ADMIN_TOKEN server-only via $env/static/private (check-duplicate proxy mirrors merge-preview pattern)
    - Svelte 5 Runes $state for preflight UI (docketInput, questionInput, duplicateWarning, preflightCleared)
    - JS preflight intercept via onsubmit/preventDefault before form submission
    - Optional chaining on all cover_metadata access (null-guard per Pitfall 9)
    - saveMetadata two-step pattern: fetch job → get argument_id → PATCH metadata
key_files:
  created:
    - app/src/routes/admin/pipeline/check-duplicate/+server.ts
  modified:
    - app/src/routes/admin/pipeline/+page.svelte
    - app/src/routes/admin/pipeline/+page.server.ts
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
    - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
decisions:
  - "[19-04]: check-duplicate proxy mirrors merge-preview pattern exactly — GET RequestHandler with ADMIN_TOKEN from $env/static/private, error(400) on missing params, error(502) on fetch failure/non-ok, json(await res.json(), { headers: { 'Cache-Control': 'no-store' } }) on success"
  - "[19-04]: preflightCleared $state prevents double preflight after 'Start anyway' — once set, handleSubmit skips the fetch and lets the form submit normally"
  - "[19-04]: When preflight fetch fails (network error), preflightCleared is set and form submits — operator is not blocked by infrastructure failure"
  - "[19-04]: Cancel resets both duplicateWarning and preflightCleared so operator can fix docket and retry preflight"
  - "[19-04]: Metadata card placed in new {#if data.argument} block after existing argument preview block — avoids scoping conflict with {@const} variables in the existing block"
  - "[19-04]: primary_docket and question_number forwarded as FormData fields to FastAPI POST /api/admin/jobs in both url and upload branches"
metrics:
  duration: 30
  completed: "2026-06-30"
status: complete
---

# Phase 19 Plan 04: SvelteKit UI Layer Summary

**One-liner:** SvelteKit UI for Phase 19 — server-only check-duplicate proxy (T-12-TOKENLEAK pattern), pipeline start form docket/Q# fields with JS preflight and duplicate warning banner, and job detail Argument Metadata card with cover_metadata hint text and saveMetadata action.

## What Was Built

### Task 1: check-duplicate proxy +server.ts

New file `app/src/routes/admin/pipeline/check-duplicate/+server.ts` — a server-only GET handler that proxies to FastAPI's `GET /api/admin/arguments/check-duplicate` endpoint, keeping `ADMIN_TOKEN` server-side at all times (T-19-04-01 / T-12-TOKENLEAK pattern).

Structure mirrors `merge-preview/+server.ts` exactly:
- `ADMIN_TOKEN` and `FASTAPI_BASE_URL` imported from `$env/static/private` only
- `GET: RequestHandler` extracts `docket` and `question` from `url.searchParams`
- Returns `error(400)` when either param is null
- Fetches `FASTAPI_BASE_URL/api/admin/arguments/check-duplicate?docket=...&question=...` with `X-Admin-Token: ADMIN_TOKEN`
- Returns `error(502)` on fetch exception or non-OK response
- Returns `json(await res.json(), { headers: { 'Cache-Control': 'no-store' } })` on success

The browser calls `/admin/pipeline/check-duplicate?docket=X&question=N` (same-origin, no token). SvelteKit proxies to FastAPI. `ADMIN_TOKEN` never reaches the browser.

### Task 2: Pipeline start form (docket + Q# + preflight + duplicate banner)

**`+page.svelte` changes:**

Four new Svelte 5 Runes `$state` declarations:
- `docketInput = $state('')`
- `questionInput = $state('1')`
- `duplicateWarning = $state<{ argumentId: number; docket: string; question: string } | null>(null)`
- `preflightCleared = $state(false)`

`handleSubmit` extended with async preflight logic:
- If `docketInput.trim()` is empty OR `preflightCleared` is true → set `submitting = true` and return (native form proceeds)
- Otherwise: call `e.preventDefault()`, fetch `/admin/pipeline/check-duplicate?docket=...&question=...`
- If `data.exists` is true: set `duplicateWarning` with the returned argument data
- If `data.exists` is false: set `preflightCleared = true`, call `(e.target as HTMLFormElement).requestSubmit()`
- On network error: set `preflightCleared = true` and submit (operator not blocked by infra failure)

Three new form elements inserted between the URL/upload input and the Start Run button:
- **Docket number field** (`name="primary_docket"`, placeholder `"e.g. 14-556 (optional)"`, `bind:value={docketInput}`, not required)
- **Question number selector** (`name="question_number"`, options Q1/Q2, `bind:value={questionInput}`, default "1")
- **Duplicate warning banner** (`role="alert"`, amber border `#fbbf24`, `"⚠ Argument already exists"` heading, docket/question body copy, Cancel and Start anyway buttons)

Cancel resets both `duplicateWarning` and `preflightCleared` so the operator can fix the docket and retry. Start anyway sets `preflightCleared = true` then calls `document.querySelector('form')?.requestSubmit()`.

**`+page.server.ts` changes:**

`primary_docket` and `question_number` read from FormData in the default action (before the url/upload branch split). Both appended to the FormData body sent to `POST /api/admin/jobs` in both the URL and upload branches. `primary_docket` only appended when non-null.

### Task 3: Job detail Argument Metadata card

**`[job_id]/+page.server.ts` changes:**

`ArgumentPreview` interface extended with two new optional fields:
- `source_docket: string | null`
- `cover_metadata: Record<string, unknown> | null`

New `saveMetadata` form action added alongside existing actions:
- Reads `case_name`, `source_docket`, `argued_date` from FormData (each trimmed or null)
- Fetches the job to get `argument_id` (same two-step pattern as `approve` action)
- Returns `fail(400, { metadataError: 'No argument linked to this job yet.' })` when `argument_id` is null
- PATCHes `FASTAPI_BASE_URL/api/admin/arguments/{argumentId}/metadata` with JSON body
- Returns `fail(502, { metadataError: 'Could not save metadata...' })` on network error
- Returns `fail(422, { metadataError: 'Could not save metadata...' })` on non-OK response
- Returns `{ metadataSaved: true }` on success

**`[job_id]/+page.svelte` changes:**

New `{#if data.argument != null}` block inserted between the existing Argument preview block and the View source PDF card (per UI-SPEC Page Layout Contract).

Card structure (Component 4):
- `#1e293b` background, `#334155` border, `24px` padding, `24px` bottom margin
- `"Argument Metadata"` heading (20px/600/1.2)
- `<form method="POST" action="?/saveMetadata" use:enhance>`

Three field groups (Components 5, 6, 7):
- **Case name**: `input[name="case_name"]` pre-populated from `data.argument.case_name`; hint text shown when `cover_metadata.case_name` differs from current value
- **Docket**: `input[name="source_docket"]` pre-populated from `data.argument.source_docket`; hint text shown when `cover_metadata.primary_docket` differs
- **Argued date**: `input[type="date"][name="argued_date"]`; value sliced to 10 chars when non-null, `""` when null (D-11); hint text when `cover_metadata.argued_date` differs

All `cover_metadata` access uses optional chaining (`data.argument?.cover_metadata?.field`) — null-guarded per Pitfall 9 in RESEARCH.md.

Success/error messages:
- `{#if form?.metadataSaved}` — green "Metadata saved." paragraph
- `{#if form?.metadataError}` — red `role="alert"` paragraph

Save metadata button (Component 8): full-width, `min-height: 44px`, `border: 1px solid #93c5fd`.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All new UI elements are wired to real data:
- Docket input bound to `docketInput` and forwarded in FormData
- Preflight fetches live check-duplicate proxy endpoint
- Metadata card fields pre-populated from `data.argument` (loads from FastAPI)
- saveMetadata action PATCHes real FastAPI endpoint

## Threat Surface Scan

No new network surface beyond what the plan's threat model documents.

| Threat ID | Mitigation Verified |
|-----------|---------------------|
| T-19-04-01 | ADMIN_TOKEN read from $env/static/private in +server.ts only; browser fetch hits SvelteKit same-origin URL — no token in browser |
| T-19-04-02 | DB UNIQUE constraint is authoritative backstop; preflight is UX convenience only; no bypass is a security issue |
| T-19-04-03 | cover_metadata values rendered as Svelte text interpolation (not innerHTML) — no XSS vector |
| T-19-04-04 | Operator explicitly chooses Start anyway; DB constraint is backstop |

## Self-Check

| Artifact | Status |
|----------|--------|
| app/src/routes/admin/pipeline/check-duplicate/+server.ts | FOUND — committed at d170e084 |
| +server.ts imports ADMIN_TOKEN from $env/static/private | FOUND — verified via grep |
| +server.ts exports GET: RequestHandler | FOUND |
| +server.ts error(400) when params null | FOUND |
| +server.ts error(502) on fetch failure | FOUND |
| +server.ts json(await res.json(), Cache-Control no-store) | FOUND |
| +page.svelte docketInput $state | FOUND — committed at 7f6c8f2c |
| +page.svelte duplicateWarning $state | FOUND |
| +page.svelte preflightCleared $state | FOUND |
| +page.svelte fetch to /admin/pipeline/check-duplicate | FOUND |
| +page.svelte input name=primary_docket placeholder optional | FOUND |
| +page.svelte select name=question_number Q1/Q2 | FOUND |
| +page.svelte role=alert duplicate banner | FOUND |
| +page.svelte Cancel resets duplicateWarning and preflightCleared | FOUND |
| +page.svelte Start anyway sets preflightCleared + requestSubmit | FOUND |
| +page.server.ts reads primary_docket from FormData | FOUND |
| +page.server.ts reads question_number from FormData | FOUND |
| +page.server.ts forwards both fields in url and upload branches | FOUND |
| [job_id]/+page.server.ts ArgumentPreview.source_docket | FOUND — committed at 88e29ed1 |
| [job_id]/+page.server.ts ArgumentPreview.cover_metadata | FOUND |
| [job_id]/+page.server.ts saveMetadata action | FOUND |
| saveMetadata fail(400) when argument_id null | FOUND |
| saveMetadata fail(502) on network error | FOUND |
| saveMetadata { metadataSaved: true } on success | FOUND |
| [job_id]/+page.svelte Argument Metadata heading | FOUND |
| [job_id]/+page.svelte form action=?/saveMetadata | FOUND |
| [job_id]/+page.svelte name=case_name, source_docket, argued_date | FOUND |
| [job_id]/+page.svelte Extracted: hint text with optional chaining | FOUND |
| [job_id]/+page.svelte metadataSaved success message | FOUND |
| [job_id]/+page.svelte metadataError role=alert | FOUND |
| [job_id]/+page.svelte Save metadata button min-height 44px, border #93c5fd | FOUND |
| [job_id]/+page.svelte Metadata card between argument preview and PDF card | FOUND |
| npm run build in app/ exits 0, no TypeScript errors | VERIFIED — build succeeded in 16.79s |

## Self-Check: PASSED

## Commits

| Task | Commit | Message |
|------|--------|---------|
| Task 1: check-duplicate +server.ts | d170e084 | feat(19-04): create check-duplicate proxy +server.ts |
| Task 2: Pipeline start form | 7f6c8f2c | feat(19-04): pipeline start form — docket input, Q# selector, preflight, duplicate warning banner |
| Task 3: Argument Metadata card | 88e29ed1 | feat(19-04): job detail Argument Metadata card — saveMetadata action, ArgumentPreview extended, metadata card with hint text |
