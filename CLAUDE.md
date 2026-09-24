# SCOTUS Chat — Project Guide

## Project

A read-only website that displays Supreme Court oral arguments as a chat-style interface. The pipeline is an offline operator-only CLI tool. The website is never interactive for end users.

See `.planning/PROJECT.md` for full context.

## GSD Workflow

This project uses the Get Shit Done (GSD) workflow. Always follow the phase-gate process:

```
/gsd:discuss-phase N   → gather context and clarify approach
/gsd:plan-phase N      → create an executable plan
/gsd:execute-phase N   → implement the plan
/gsd:verify-work N     → verify phase goal was achieved
```

**Current state:** See `.planning/STATE.md`
**Roadmap:** See `.planning/ROADMAP.md`
**Requirements:** See `.planning/REQUIREMENTS.md`

## Key Constraints

- **Apolitical framing is a hard constraint.** The project never asserts a conclusion about a speaker; it presents the record and lets the reader draw their own. No summaries, sentiment, statistics, aggregation, ranking, or characterisation — for anyone.
  - **Identical treatment, not identical content.** Every speaker renders through the same component, section order, and visual weight. Sections vary with the data that exists, never with who the person is. A Justice's card is longer because more is on the record, not because the design grants them more room.
  - **Absent data renders as absent.** No filler, no placeholder, no "not available" row — the section is omitted and the rest closes up. Never invent plausible-looking data to balance a layout.
  - **Faithful-and-uniform is legal; amplified is not.** A design crosses the line when it makes a disparity easier to read than it was in the room — scaling by speaking time, reordering by participation, persisting a "most active" emphasis. Full doctrine: `.planning/seeds/SEED-002-scotus-teams-video-call-presentation.md`.
- **Pipeline is offline only.** Ingest/parse/resolve are CLI scripts. Never expose pipeline steps as HTTP endpoints or user-facing features.
- **Raw PDFs are immutable.** Never modify source files after ingest. All derived data can be regenerated.
- **Alembic is the sole DDL authority.** Never call `Base.metadata.create_all` anywhere.
- **asyncpg requires `statement_cache_size=0`** when behind Digital Ocean PgBouncer (Transaction mode). This must be in the initial engine config.
- **Invocation-shape-independent pytest hooks belong in the repository-root `conftest.py`.** Any pytest hook or module-level side effect that must fire regardless of which subset of tests is invoked (e.g. the `TEST_DATABASE_URL` redirect) must live in the repo-root `conftest.py` beside `pytest.ini`, never in a subdirectory conftest — a conftest in `tests/`, `api/tests/`, or `pipeline/tests/` only loads when that directory is in the collected path set, and putting the redirect there is what let explicit-path invocations wipe the shared dev database twice during Phase 45 (D-03). See the regression test `tests/test_pytest_isolation_invocation_shapes.py`.

## Defect Policy

Established 2026-08-27 by the operator. This governs which defects reach the operator
and which get fixed silently. It overrides GSD's default checkpoint/UAT instincts.

**The line: is the correct behavior already determined, or does it need the operator's taste?**

### Claude's, always — fix it, don't ask

Anything where *what should happen* is already settled and only the implementation is
in question. Fix it in the phase it's found, commit it, report it in one line in the
phase summary. No `AskUserQuestion`, no checkpoint, no options table, no UAT item.

- Race conditions, transaction boundaries, lock ordering, concurrency
- Idempotency, double-import, replay, retry semantics
- FK cascades, orphan rows, constraint violations, NULL handling
- Failing tests — a red test is a bug report, not a decision request
- Stale-flag / stale-prop bugs, reactivity bugs, invalidation bugs
- Off-by-one, ordering, sort stability, pagination
- Error handling, fail-closed defaults, input validation
- Anything contradicting a constraint in **Key Constraints** or a locked decision
  in a phase `*-CONTEXT.md`

The operator is a UX practitioner. The correct amount of attention for them to spend
on the above is approximately zero. Bringing one of these forward as a question is
itself a defect in how the work is being done.

### The operator's — ask before deciding

Anything where *what should happen* is a product, design, or domain judgment.

- What a screen shows, in what order, with what words
- Whether a state is reachable at all ("can a published argument be edited?")
- Whether a condition blocks an action or merely flags it
- Domain semantics ("is a per-Person lock the right granularity?")
- Scope: whether a newly discovered requirement belongs in this phase, a later
  phase, or the backlog
- Anything that would make previously-approved visual work look different

### Test for the line

If the answer lives in a spec, a locked decision, or a correctness argument — it's
Claude's. If it needs the operator's taste — it's the operator's. When genuinely
ambiguous, do everything that doesn't depend on the answer, then ask one precise
question.

### Reporting fixed defects

One line each. What broke, what fixed it, which test proves it. Do not narrate the
investigation, do not enumerate the alternatives considered, do not preserve
deviation archaeology for a reader who does not exist.

## Testing Policy

Established 2026-08-27 by the operator, alongside the debridement pass.

- **This is a solo project.** There is no hand-off, no second reviewer, and no
  auditor. Tests exist to catch regressions, not to document intent to a stranger.
- **No static source-text contract tests for frontend behavior.** Asserting that a
  string appears in a `.svelte` file proves a declaration is present and proves
  nothing about the rendered page. This pattern produced 28 green tests against a
  fully broken button (Phase 44) and let G-49-5c ship past a green suite (Phase 49).
  Frontend behavior is verified by the operator's eye or a real browser, or it is
  not verified.
  - Narrow exception: a **structural ban** sweep — proving a forbidden identifier
    reaches no public surface — stays legitimate, because absence across a computed
    file set is exactly what source text *can* prove. See
    `api/tests/test_trust_public_leak_ban.py`, which guards the apolitical
    constraint.
- **Tests retire with the behavior they pinned.** When a phase supersedes behavior,
  delete that behavior's tests in the same commit. A test asserting a superseded
  contract is worse than no test: it still costs maintenance and it lies about
  coverage.
- **No phase-numbered test files for new work.** Name test modules after the unit
  under test (`test_admin_review_service.py`), not the phase that added them
  (`test_phase49_review_ui_contract.py`). Phase numbering is what let the suite
  accrete 20+ files that nobody could evaluate for relevance.
- **Target ratio: under 2:1 test LOC to production LOC.** A guideline, not a gate.
  The ratio is a proxy; the real question is the one to ask before adding any
  tooling: **does this make sense for the developers actually on this project?**
  Right now that is one person who is not going to hand this off. Tooling that
  earns its place on a team of eight — coverage gates, contract suites,
  handoff documentation — can be pure cost here. Add deliberately, and say why.

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | SvelteKit 2.x / Svelte 5 (Runes — no legacy stores) |
| Backend | FastAPI 0.115+ with Pydantic v2 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 async, Alembic migrations |
| Pipeline | Python 3.12, pdfplumber, Anthropic SDK, instructor, tenacity |
| Hosting (v2) | Digital Ocean App Platform |

## Repository Structure

```
/app        — SvelteKit frontend
/api        — FastAPI backend
/pipeline   — Preprocessing scripts (ingest, parse, resolve, enrich, extract)
/data       — Raw ingested PDF files (immutable)
```

## Spike Findings

- **Spike findings for scotuschat** (PDF extraction patterns, ParsedUtterance schema, parse state machine, failure taxonomy, LLM prompt template) → `Skill("spike-findings-scotuschat")`

## Architecture Rules

1. FastAPI is read-only — the pipeline writes directly to PostgreSQL; the API never triggers pipeline steps
2. All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions — `FASTAPI_BASE_URL` is a server-only env var, never `PUBLIC_`
3. Re-running a pipeline step produces new rows under a new `pipeline_run_id` — prior rows are not deleted until the new run is promoted
4. An extracted field with an operator-editable destination uses `CopyableExtractedValue` by default unless its phase explicitly opts out; a read-only extracted value without an operator-editable destination remains plain.
