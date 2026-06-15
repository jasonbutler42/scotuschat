# Milestones

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
