# Milestones

## v1.1 Operator Admin Interface (Shipped: 2026-06-18)

**Phases completed:** 4 phases (5–8), 19 plans, 33 tasks
**Timeline:** 2026-06-15 → 2026-06-18 (4 days)
**Commits:** 155 (v1.0 → v1.1) | **Files changed:** 120 | **Net lines:** +23,277 / -1,410

**Key accomplishments:**

- Operator admin area secured end-to-end — HMAC stateless session cookie (`node:crypto`), `hooks.server.ts` sole auth checkpoint, dark-theme login page with constant-time credential validation, logout action, AUTH-01/02/03 all verified
- FastAPI admin router at `/api/admin` with router-level `X-Admin-Token` dependency, admin_jobs service layer (Pydantic schemas, atomic step-advance guards, boto3 DO Spaces upload, detached subprocess spawn)
- Three pipeline commands (ingest, parse, resolve) made job-aware via `--job-id`: each writes RUNNING/COMPLETED/FAILED to admin_jobs; resolve replaces terminal prompts with discrepancy JSONB + PAUSED state
- Pipeline Runner UI — two-mode start page (URL/file upload), live step cards polling every 2.5s, auto-advance on clean resolve, pauses for discrepancy review; fire-and-poll pattern survives browser close (PIPE-17)
- Discrepancy review workflow — HIT rows pre-confirmed with single Change button, MISS rows with Correct/Override; people-backed typeahead (full roster via server-loaded data); inline add-new-person via `use:enhance` for reliable devalue deserialization
- `arguments.resolved_at` visibility gate — cases hidden from `/cases/` until resolve completes; no placeholder metadata leaks publicly (Alembic migration 0004)
- People directory at `/admin/people` — filterable by incomplete metadata, edit form with bio text / photo URL / tenure dates / role create (Alembic migration 0005); per-argument participant review after pipeline run

---

## v1.0 MVP (Shipped: 2026-06-15)

**Phases completed:** 4 phases (1–4), 15 plans, 76 commits
**Timeline:** 2026-06-11 → 2026-06-15 (4 days)
**Lines of code:** ~4,895 (TypeScript + Svelte + Python) across 146 files

**Key accomplishments:**

- SvelteKit 2 + Svelte 5 Runes scaffold with adapter-node, final route `/cases/[slug]/arguments/[id]` from day one, stub ChatBubble/StageDirection components, Python dependencies, pytest config, PowerShell dev startup script
- 10-table PostgreSQL schema via hand-written Alembic migration — people/roles/tenures/cases/arguments/case_arguments/appearances/participants/pipeline_runs/utterances — supporting M:M consolidated dockets and idempotent re-runs via `pipeline_run_id`
- Async pipeline CLI: `ingest` (SSRF-validated PDF download, immutable storage) + `parse` (pdfplumber extraction, rule-based state machine, instructor/tenacity LLM corrective pass)
- Speaker resolution: `speaker_alias` table + `resolve` step + `GET /people/{id}` API; ChatBubble displays resolved names with role labels and raw-label fallback
- FastAPI `GET /arguments/{id}/utterances` with PgBouncer-safe async engine (`statement_cache_size=0` in `connect_args`), max-pipeline-run-id filtering, and full chat layout in SvelteKit
- Full browseable UI: SSR case list, slug routing with 307 redirect, CSS Grid argument layout, avatar initials circles, SectionRail scroll-spy
- WCAG 2.1 AA accessibility: global focus ring, ARIA article semantics, HTML5 landmarks on all pages, MobileNavBar for narrow viewports; `#475569` eliminated from entire `app/src/` tree

**Known deferred items at close:** 4 (see STATE.md Deferred Items — stale verification status markers; human UAT completed per commits)

---
