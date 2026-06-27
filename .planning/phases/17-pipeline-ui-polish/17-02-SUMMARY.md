---
phase: 17-pipeline-ui-polish
plan: "02"
subsystem: frontend
status: complete
tags: [frontend, svelte, proxy, admin-pipeline, pdf-serving, typescript]
dependency_graph:
  requires: [17-01-PLAN.md (AdminJobResponse.original_filename + parse_stats + GET /api/admin/jobs/{job_id}/pdf)]
  provides: [pdf proxy +server.ts, ParseStats interface, extended Job interface, formatDate(), ingest source row, parse stat rows, View source PDF link card]
  affects: [app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts, app/src/routes/admin/pipeline/[job_id]/+page.svelte]
tech_stack:
  added: []
  patterns: [same-origin-proxy, redirect-manual, stream-body, $env/static/private, svelte5-runes-conditional]
key_files:
  created:
    - app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts
  modified:
    - app/src/routes/admin/pipeline/[job_id]/+page.svelte
decisions:
  - "PDF proxy uses redirect:'manual' to pass FastAPI 302 (Spaces pre-signed URL) through to the browser without the token transiting SvelteKit"
  - "Opaque redirect fallback: re-fetch with redirect:'follow' and stream body when Location header is unreadable (CORS-mode fetch behavior)"
  - "formatDate() declared as script-level function (not {@const}) to be accessible from the {#each STEP_ORDER} loop scope (Pitfall 5)"
  - "ParseStats interface mirrors 17-01 Pydantic model field names exactly: utterance_count / speaker_count (not utterances/speakers)"
  - "View source PDF anchor targets same-origin SvelteKit proxy /admin/pipeline/{id}/pdf, NOT /api/admin/... (CLAUDE.md Architecture Rule 2 — browser has no direct FastAPI route; token must stay server-side)"
metrics:
  duration_minutes: 15
  completed: "2026-06-27"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 2
---

# Phase 17 Plan 02: Frontend Pipeline UI Polish Summary

SvelteKit PDF proxy route and full pipeline job detail page polish: same-origin PDF proxy that keeps ADMIN_TOKEN server-side, extended Job TypeScript interfaces, and three template additions that render the source file identifier, parse stats, and a View source PDF link card.

## What Was Built

### Task 1: SvelteKit PDF proxy route +server.ts

Created `app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts` exporting a typed `GET: RequestHandler`:

- Imports `ADMIN_TOKEN` and `FASTAPI_BASE_URL` exclusively from `$env/static/private` (T-17-TOKENLEAK)
- Fetches FastAPI server-side with `redirect: 'manual'` and `X-Admin-Token` header
- Handles readable 302 (Spaces case): extracts `Location` header, returns same-origin `302` to browser — pre-signed Spaces URL lands in address bar without token
- Handles opaque redirect (status 0): re-fetches with `redirect: 'follow'` and streams the resolved response body
- Handles 200 FileResponse (disk case): streams `res.body` via `new Response(res.body, {...})` — no buffering
- Non-OK/non-redirect: throws `error(404|502, 'Source PDF not available')`
- Auth guard inherited from `hooks.server.ts` (all `/admin/*` including `+server.ts` endpoints protected)
- Token never echoed to any response header or body

### Task 2: Extend Job interface + add standalone formatDate() in +page.svelte

Added to `<script lang="ts">` block of `+page.svelte`:

- `ParseStats` interface: `utterance_count: number; speaker_count: number;` (mirrors 17-01 Pydantic model)
- Extended `Job` interface with: `pdf_url?: string | null`, `spaces_key?: string | null`, `original_filename?: string | null`, `parse_stats?: ParseStats | null` — so `data.job.*` type-checks (Pitfall 4)
- Script-level `function formatDate(iso: string | null | undefined): string` using `toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })` with `'—'` fallback — accessible from `{#each STEP_ORDER}` loop scope (Pitfall 5)
- Pre-existing `{@const formatArgDate}` inside `{#if data.argument}` untouched

### Task 3: Render Ingest source row, Parse stat rows, and View source PDF link card

Three template additions to `+page.svelte`:

**Addition A — Ingest source identifier row** (inside `{#each STEP_ORDER as step}` loop, after step card header):
- Gated `{#if step === 'ingest' && (data.job.original_filename || data.job.pdf_url)}`
- Renders a "Source file" label/value row with `word-break: break-all` on the value span
- Shows `original_filename` for upload-mode jobs; falls back to `pdf_url` for URL-mode jobs; absent when both are null

**Addition B — Parse stat rows** (inside loop, after Addition A):
- Gated `{#if step === 'parse' && status === 'completed' && data.job.parse_stats}` (D-10: only when completed)
- Binds `{@const ps = data.job.parse_stats}` for cleaner access
- Four label/value rows: "Utterances" (`ps.utterance_count`), "Distinct speakers" (`ps.speaker_count`), then nested in `{#if data.argument}`: "Case name" (`data.argument.case_name || '—'`), "Argued" (`formatDate(data.argument.argued_date)`)
- Raw counts only — no derived insight or ratios (apolitical constraint honored)
- Uses script-level `formatDate()`, NOT the `{@const formatArgDate}` scoped inside `{#if data.argument}`

**Addition C — View source PDF link card** (between argument card closing `{/if}` and step cards container):
- Gated `{#if data.job.spaces_key || data.job.pdf_url}`
- Surface card (`background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;`)
- Anchor copy "View source PDF", `target="_blank"`, `rel="noopener noreferrer"`, link style token (`font-size:14px; color:#93c5fd; text-decoration:underline`)
- `href="/admin/pipeline/{data.job.id}/pdf"` — same-origin SvelteKit proxy (NOT `/api/admin/...`; CLAUDE.md Architecture Rule 2 enforced)

## Decisions Made

- `redirect: 'manual'` is mandatory so a FastAPI 302 is not followed server-side — the pre-signed Spaces URL goes directly to the browser (keeps PDF bytes off SvelteKit, acceptable per 17-RESEARCH Security Domain)
- Opaque redirect fallback re-fetches with `redirect: 'follow'` rather than erroring — necessary because some fetch environments produce `type: 'opaqueredirect'` where Location is unreadable
- `formatDate` is a script-level function (not `{@const}`) because `{@const}` declarations inside `{#if}` blocks are scoped to that block and are not accessible from sibling `{#each}` loops
- PDF link anchor targets the same-origin SvelteKit proxy `/admin/pipeline/{id}/pdf`, not `/api/admin/jobs/{id}/pdf` directly — the browser has no proxy to FastAPI and the admin token must stay server-side (CLAUDE.md Architecture Rule 2; architecture_note in plan)
- Parse stat rows use `{@const ps = data.job.parse_stats}` inside the `{#if}` guard to avoid repeated `data.job.parse_stats?.` chaining and satisfy the TypeScript narrowed type

## Deviations from Plan

None — all three tasks executed exactly as specified. The `checkpoint:human-verify` gate in Task 3 was approved by the operator; implementation proceeded without deviation.

## Threat Surface Scan

- T-17-TOKENLEAK: mitigated — `ADMIN_TOKEN` imported only from `$env/static/private`; injected into server-side fetch header; never written to a response header/body; anchor targets same-origin proxy, not FastAPI directly
- T-17-AUTHZ: mitigated — route lives under `/admin/*`; `hooks.server.ts` guards every `/admin/*` request before the handler runs
- T-17-OPENREDIRECT: mitigated — `Location` value sourced from FastAPI's own response (server-controlled pre-signed Spaces URL), never from a client-supplied query param
- T-17-PRESIGN: accepted — URL visible to operator only, admin-only flow, 15-minute TTL (inherited from 17-01)
- T-17-XSS: accepted — Svelte auto-escapes all interpolated text (`{...}`); `original_filename`, `pdf_url`, `case_name`, counts rendered as text content, not unsanitized HTML — no injection vector

## Self-Check

- [x] `app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts` exists
- [x] Exports `GET: RequestHandler` typed from `./$types`
- [x] Imports from `$env/static/private` only
- [x] `redirect: 'manual'` on FastAPI fetch
- [x] `res.body` streamed (not buffered) in disk case
- [x] Token never appears in any returned header or body
- [x] `ParseStats` interface: `utterance_count: number`, `speaker_count: number`
- [x] `Job` interface extended with all four optional fields
- [x] `function formatDate(...)` declared at script top level (not inside any `{#if}/{#each}/{@const}`)
- [x] `formatArgDate` {@const} untouched
- [x] Addition A: `{#if step === 'ingest' && (data.job.original_filename || data.job.pdf_url)}` with Source file label/value row
- [x] Addition B: `{#if step === 'parse' && status === 'completed' && data.job.parse_stats}` with four stat rows; Case name/Argued nested in `{#if data.argument}`
- [x] Addition C: `{#if data.job.spaces_key || data.job.pdf_url}` link card with `href="/admin/pipeline/{data.job.id}/pdf"`, `target="_blank"`, `rel="noopener noreferrer"`
- [x] All link/label/value styles use only existing palette tokens — no new color values introduced
- [x] `npx tsc --noEmit` clean for all modified files
- [x] Commits present: c0c8b2c2 (Task 1), de2dc848 (Task 2), a459c768 (Task 3)

## Self-Check: PASSED
