# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-06-15
**Phases:** 4 | **Plans:** 15 | **Timeline:** 4 days (2026-06-11 → 2026-06-15)

### What Was Built

- End-to-end pipeline: PDF ingest → LLM parse (pdfplumber + instructor/tenacity) → speaker resolution → PostgreSQL
- Read-only FastAPI backend with two endpoints (`GET /arguments/{id}/utterances`, `GET /cases`) serving structured utterances with resolved speaker names
- Full SvelteKit 2 + Svelte 5 Runes UI: case list, slug routing with SSR, CSS Grid argument layout, avatar initials, SectionRail scroll-spy, MobileNavBar
- WCAG 2.1 AA compliance throughout: global focus ring, ARIA semantics, HTML5 landmarks, color contrast corrections

### What Worked

- **Vertical-slice phasing** — each phase delivered usable value (Phase 1: runnable end-to-end; Phase 2: resolved speakers; Phase 3: full UI; Phase 4: accessible). Never had a phase of pure infrastructure with nothing to show.
- **Spike findings carried forward** — the pre-project spike on PDF extraction patterns directly informed the parse state machine design; no rework needed in Phase 1.
- **Svelte 5 Runes-only constraint** — prohibiting `export let` and `$:` blocks from day one prevented the mixed-paradigm confusion that typically emerges when Runes are adopted gradually on an existing codebase.
- **Test-gate discipline** — Wave 0 static-analysis tests (e.g., checking `PUBLIC_` prefix absence, no `create_all`) caught constraint violations before they were committed and caught by humans later.
- **PgBouncer constraint surfaced early** — `statement_cache_size=0` in `connect_args` was identified and hardened in Phase 1, Plan 05, before any production infrastructure existed. Zero rework needed at deploy time.

### What Was Inefficient

- **REQUIREMENTS.md checkboxes not backfilled during phase completion** — Phase 2 and Phase 4 requirements remained unchecked in REQUIREMENTS.md even after those phases completed. Required manual audit at milestone close to confirm all 28 requirements were actually shipped.
- **VERIFICATION.md `human_needed` status not updated after human UAT** — Verification files retained stale `human_needed` status even after human UAT was completed per separate UAT files and commits. Created false-positive audit flags at milestone close.
- **Traceability table in REQUIREMENTS.md never updated** — The table had "Pending" for most items despite those requirements being complete. Inconsistency required reconciliation at milestone close.
- **Stale milestone audit omitted** — No `/gsd-audit-milestone` was run before starting `/gsd-complete-milestone`. Running the audit proactively would have surfaced the stale status issues earlier.

### Patterns Established

- `statement_cache_size=0` goes in `connect_args` dict (asyncpg), NOT as a top-level engine kwarg — top-level kwarg silently has no effect under PgBouncer Transaction mode
- SQLAlchemy Row tuples from JOINs require explicit dict assembly; `from_attributes=True` cannot pull labeled columns from Row tuples
- `expire_on_commit=False` on `async_sessionmaker` is mandatory for async SQLAlchemy — prevents `MissingGreenlet` on attribute access after commit
- FastAPI lifespan context manager (not `@app.on_event`) — the on_event decorator is deprecated since FastAPI 0.93+
- Roster derived client-side from utterances via `$derived.by()` — no separate API call needed
- IntersectionObserver `browser` guard from `$app/environment` is required for SSR safety in SvelteKit

### Key Lessons

1. **Update REQUIREMENTS.md at phase completion, not milestone close.** Checking off requirements and updating the traceability table should be part of the plan summary / state advance step — not a retrospective reconciliation.
2. **Update VERIFICATION.md status after human UAT.** When a UAT file reaches `passed`, the corresponding VERIFICATION.md should be updated to `verified` in the same commit to prevent stale flags.
3. **Run `/gsd-audit-milestone` before `/gsd-complete-milestone`.** The audit catches cross-phase integration issues and surfaces stale docs before the close ceremony starts.
4. **`asyncpg` connect_args trap is production-critical.** Any project using asyncpg behind a connection pooler (PgBouncer, pgpool) in transaction mode must verify this is in `connect_args`, not the engine kwargs. Silently fails otherwise.
5. **Svelte 5 Runes-only is a viable constraint for new projects.** The productivity cost was zero — no Rune/legacy confusion, clean component interfaces, no `export let` sprawl.

### Cost Observations

- Model mix: balanced profile (Sonnet primary)
- Sessions: ~8 sessions across 4 days
- Notable: The spike work done before Phase 1 paid dividends — parse state machine design was correct on the first implementation pass

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 MVP | 4 | 15 | First milestone; established baseline patterns |

### Cumulative Quality

| Milestone | Test Files | Zero-Dep Additions | WCAG Compliance |
|-----------|------------|-------------------|-----------------|
| v1.0 MVP | 6 | 0 (no new npm/pip beyond initial setup) | AA across all pages |

### Top Lessons (Verified Across Milestones)

1. Keep requirements checked off in real time — stale checkboxes create reconciliation work at milestone close
2. Run the milestone audit before the milestone close ceremony
