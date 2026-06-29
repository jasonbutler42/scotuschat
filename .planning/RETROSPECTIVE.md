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

## Milestone: v1.1 — Operator Admin Interface

**Shipped:** 2026-06-18
**Phases:** 4 (5–8) | **Plans:** 19 | **Timeline:** 4 days (2026-06-15 → 2026-06-18)
**Commits:** 155 | **Files changed:** 120 | **Net lines:** +23,277 / -1,410

### What Was Built

- HMAC stateless session auth — `hooks.server.ts` sole checkpoint, dark-theme login page with `timingSafeEqual`, logout action (AUTH-01/02/03)
- FastAPI admin router with `X-Admin-Token` auth dependency, admin_jobs service (schemas, boto3 DO Spaces upload, detached subprocess spawn, atomic advance guards)
- Three pipeline commands made job-aware: `--job-id` writes RUNNING/COMPLETED/FAILED; resolve replaces terminal prompts with discrepancy JSONB + PAUSED state
- Pipeline Runner UI: two-mode start page (URL/upload), fire-and-poll step cards at 2.5s, discrepancy review with HIT/MISS rows, inline add-person, resumable across sessions
- `arguments.resolved_at` visibility gate (Alembic migration 0004) — cases hidden from `/cases/` until resolve completes
- People directory (filterable by missing metadata), person edit form (bio/photo/tenures/roles), per-argument participant review (Alembic migration 0005)
- 3 gap-closure plans within Phase 7 (07-06, 07-07, 07-08) addressing UAT gaps found post-execution

### What Worked

- **Phase dependency order enforced by design** — 5 before 6 before 7 before 8; each prerequisite delivered exactly what the dependent phase needed
- **Fire-and-poll architecture** — HTTP returns `{job_id}` immediately, client polls every 2.5s, stops on terminal states; no timeout risk, no SSE complexity
- **Atomic advance guards** — `rowcount == 1` without `RETURNING` prevents double-spawn races in concurrent polling
- **Debug session framework** — structured diagnosis of 3 complex client-side bugs led to precise fixes; all root causes confirmed before any code was written
- **Gap-closure as separate plans** — treating UAT failures as distinct plans with SUMMARY files gave full traceability from gap to fix to verification

### What Was Inefficient

- **Debug sessions left in "diagnosed" status** — all 3 were diagnosed and fixed 2 days before milestone close; should close them when the fix lands
- **Phase 7 UAT not re-run after gap closure** — fixes were human-verified in 07-07 but UAT wasn't formally re-run; Phase 8 10/10 pass was indirect confirmation only
- **REQUIREMENTS.md AUTH checkboxes** — same lesson as v1.0: AUTH-01/02/03 remained unchecked after Phase 6 completed; required correction at milestone close
- **`07-VERIFICATION.md` human_needed with "no gaps" Gaps Summary** — status not updated after behavioral human checks were complete

### Patterns Established

- `use:enhance` vs raw fetch — raw fetch needs BOTH `Accept: application/json` AND `deserialize(await res.text())`; `use:enhance` handles both; always prefer `use:enhance` for SvelteKit actions
- `x-sveltekit-action: true` alone is insufficient — SvelteKit checks `Accept` header, not `x-sveltekit-action`
- `resolved_at` visibility gate — nullable timestamp column (NULL = hidden) cleaner than boolean `is_published`
- `select-before-insert` for idempotent seeding — safe for pipeline re-runs without unique constraint errors
- Job state in DB only — DO container filesystem is ephemeral; module-level Maps are wiped on every deploy
- `rowcount == 1` without `RETURNING` — `RETURNING` nullifies rowcount on some PG driver versions

### Key Lessons

1. **Close debug sessions when fixes land** — don't leave `status: diagnosed` after the fix commits
2. **Re-run UAT after any gap-closure plan** — passing Phase N+1 UAT is only indirect confirmation
3. **Mark requirements complete at phase transition** — AUTH-01/02/03 should have been checked off with 06-03-SUMMARY
4. **Update VERIFICATION.md when Gaps Summary says "no gaps"** — `human_needed` with a clean Gaps Summary creates false-positive audit flags
5. **`use:enhance` is the correct pattern for all SvelteKit form actions** — the devalue deserialization trap will catch raw fetch every time

### Cost Observations

- Model mix: Sonnet primary throughout
- Sessions: ~10 sessions over 4 days
- Notable: Phase 7 required 3 gap-closure sub-plans — complex UI state (client-side rowStates + SvelteKit devalue + pipeline JSONB) is hard to verify statically

---

## Milestone: v1.3 — Speaker Accuracy + Pipeline Confidence

**Shipped:** 2026-06-29
**Phases:** 3 (15–17) | **Plans:** 9 | **Timeline:** 5 days (2026-06-25 → 2026-06-29)
**Commits:** 84 | **Files changed:** 73 | **Net lines:** +11,791 / -177

### What Was Built

- Tenure-aware speaker popovers — `_tenure_role_name()` date-range lookup for Justices; ADVOCATE_LABEL_MAP for per-argument advocate roles; approve action transitions pipeline→draft
- PDF cover-page metadata extraction — `cover_extractor.py` regex extraction of argued_date and case_name; TOC-based advocate side detection seeding argument_participants.side
- Pipeline UI polish — original_filename stored at ingest; ParseStats COUNT queries; same-origin PDF proxy with ADMIN_TOKEN server-side throughout

### What Worked

- **Phase 15 TDD discipline** — 16 unit tests for `_tenure_role_name` written before implementation (RED/GREEN); all boundary cases (boundary dates, open-ended tenure, None argued_date, outside-all-windows fallback) caught in tests rather than production
- **Cover extractor as isolated module** — `cover_extractor.py` separated from `extractor.py`; pdfplumber I/O runs before async DB session (Pitfall 1 guard); fail-safe `try/except → {}` on all public functions prevented parse failures from non-standard PDFs
- **Gap closure as first-class plan** — Plan 17-03 (PDF card gate fix) was a single-line change discovered via UAT; treating it as a separate plan gave it a SUMMARY.md and commit trail, making the fix fully traceable
- **Atomic approve flow** — double-approve guard via ArgumentStatusEnum.PIPELINE pre-check (T-15-02-RACE) + IDOR-scoped PATCH (argument_id AND participant_id) — no additional bugs discovered in human testing

### What Was Inefficient

- **ROADMAP.md Phase 15 checkbox not updated after 15-04 completed** — 15-04-SUMMARY.md confirmed completion but the ROADMAP.md checkbox was never marked [x]; caused a false "in-progress" reading at milestone close
- **v1.2 close workflow never ran** — v1.2 was marked shipped in ROADMAP.md/STATE.md but no archive files were created; Phase 9-14 details remained inline in ROADMAP.md, requiring retroactive archival at v1.3 close
- **Phase 15 has no VERIFICATION.md** — Phase 15 had SUMMARY.md files for each plan but no phase-level VERIFICATION.md; verification status relied on per-plan self-checks and UAT notes

### Patterns Established

- `op.execute("COMMIT")` as first statement in Alembic upgrade() before any `ALTER TYPE ... ADD VALUE` call — PG forbids ADD VALUE inside transaction block; this guard is now a required pattern for all future enum expansions
- `each_key_duplicate` in Svelte — always use the table PK as the each-key (participant_id), never a FK that can repeat (person_id) across rows in the same argument
- Cover/TOC extraction before async DB session — synchronous pdfplumber I/O belongs outside `async with get_session()` block; locals computed synchronously, then used inside the session after the dry-run gate
- PDF proxy: `redirect:'manual'` + opaque redirect fallback re-fetch pattern — standard pattern for passing pre-signed storage URLs through SvelteKit without transiting the token or PDF bytes

### Key Lessons

1. **Mark ROADMAP.md checkboxes at plan completion, not milestone close.** The 15-04 inconsistency required investigation at close to confirm the plan was actually done. Should be updated in the same commit as the SUMMARY.md.
2. **Run the prior milestone close before starting the next one.** v1.2 close was deferred; archiving it retroactively at v1.3 close added friction and created a gap in MILESTONES.md history.
3. **Phase VERIFICATION.md should be created even if all verification is in plan SUMMARYs.** Phase 15 had no VERIFICATION.md; the phase-level verification artifact is what the audit tool checks.
4. **UAT the gap closure as a named plan.** 17-03 was a one-line fix found during UAT — wrapping it in a plan (with SUMMARY.md + commit) gave it full traceability and prevented the fix from being an anonymous hot-patch.

### Cost Observations

- Model mix: Sonnet primary throughout
- Sessions: ~6 sessions over 5 days
- Notable: Phase 16 (parser extraction) was the most self-contained — isolated module, TDD, all tests green first attempt; Phase 15 was the most complex (schema + service + 2 UI plans + IDOR threat model)

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 MVP | 4 | 15 | First milestone; established baseline patterns |
| v1.1 Operator Admin Interface | 4 | 19 | First admin/auth work; fire-and-poll pattern; gap-closure plans as first-class artifacts |
| v1.2 Pre-Launch Polish | 6 | 21 | Largest milestone; UI-heavy (5/6 phases had UI hints); bits-ui introduced; milestone close deferred |
| v1.3 Speaker Accuracy + Pipeline Confidence | 3 | 9 | TDD applied to tenure logic; cover extractor module; gap-closure plan (17-03) as named artifact |

### Cumulative Quality

| Milestone | Test Files | Zero-Dep Additions | WCAG Compliance |
|-----------|------------|-------------------|-----------------|
| v1.0 MVP | 6 | 0 | AA across all pages |
| v1.1 Admin Interface | 8+ | boto3, @types/node | AA maintained; admin UI dark theme |

### Top Lessons (Verified Across Milestones)

1. Keep requirements checked off in real time — stale checkboxes create reconciliation work at milestone close (v1.0 + v1.1)
2. Run the milestone audit before the milestone close ceremony — surfaces stale artifacts early
3. Close debug sessions and update verification status when the fix lands — not at milestone close
