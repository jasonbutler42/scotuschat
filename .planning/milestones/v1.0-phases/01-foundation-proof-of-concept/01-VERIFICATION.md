---
phase: 01-foundation-proof-of-concept
verified: 2026-06-11T00:00:00Z
status: human_needed
score: 4/5
overrides_applied: 0
gaps:
  - truth: "Operator runs the ingest CLI command with a PDF URL and the database contains case, argument, and pipeline_run records with status `pending`"
    status: partial
    reason: "pipeline_run is created with status=COMPLETED by ingest, not `pending`. The ROADMAP SC wording is incorrect — REQUIREMENTS.md PIPE-01 correctly documents status=COMPLETED (ingest is synchronous). Case and argument records ARE created. The functional intent is met; the SC wording contradicts the requirements doc."
    artifacts:
      - path: "pipeline/commands/ingest.py"
        issue: "Line 186: `status=PipelineRunStatus.COMPLETED` — ingest creates pipeline_run with COMPLETED, not pending"
    missing:
      - "Either update ROADMAP.md SC 1 to say 'status `completed`' instead of 'status `pending`', or acknowledge this as a wording error in the roadmap"
human_verification:
  - test: "Navigate to http://localhost:5173/cases/obergefell-v-hodges/arguments/1 after running ingest + parse"
    expected: "The page renders the Obergefell oral argument as a two-sided chat: Justice utterances are right-aligned on the bench side, advocate utterances are left-aligned, stage directions (e.g. '(Laughter.)') appear as amber-bordered full-width blocks visually distinct from speech bubbles"
    why_human: "Cannot verify visual rendering, layout position, or chat appearance programmatically; requires a browser with Postgres running + ingest + parse completed"
  - test: "Verify heading bar shows correct case metadata"
    expected: "Heading bar shows 'Obergefell v. Hodges', docket 'No. 14-556', 'Argued April 28, 2015', 'Question 1'"
    why_human: "Requires live data from a real ingest run to confirm API returns correct metadata and the UI renders it"
---

# Phase 1: Foundation + Proof of Concept — Verification Report

**Phase Goal:** An operator can ingest a real SCOTUS transcript PDF, run the parse step, hit a live API endpoint, and see the oral argument rendered as a two-sided chat in a browser — proving the core concept end-to-end on a single hand-picked case.
**Verified:** 2026-06-11T00:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator runs ingest and DB contains case, argument, and pipeline_run records | PARTIAL | Case and argument rows ARE created. pipeline_run created with status=COMPLETED (not `pending` as ROADMAP SC 1 states). REQUIREMENTS.md PIPE-01 correctly says status=COMPLETED. ROADMAP wording is incorrect. |
| 2 | Operator runs parse and DB contains ordered utterance rows with pipeline_run_id, is_stage_direction classified, person_id null | VERIFIED | pipeline/commands/parse.py writes Utterance rows with pipeline_run_id=run.id, is_stage_direction from state machine STAGE_DIR_RE, person_id=None explicitly |
| 3 | Re-running parse produces new rows linked to new pipeline_run_id; prior rows not deleted | VERIFIED | parse.py creates new Utterance rows per run, no DELETE statements in pipeline source; PIPE-11 enforced |
| 4 | GET /arguments/{id}/utterances returns ordered utterances in a running FastAPI server | VERIFIED | api/routers/arguments.py wires GET /{argument_id}/utterances; service queries Utterance ORDER BY sequence.asc(); max completed parse run filtering correct in api/services/arguments.py |
| 5 | Browser at SvelteKit dev server renders two-sided chat with stage directions visually distinct | UNCERTAIN | Code paths are fully implemented and wired. Requires human browser verification with live data. |

**Score:** 4/5 truths verified (SC 1 partially met — implementation correct, ROADMAP wording is the error)

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/core/database.py` | Async engine, lifespan, get_db | VERIFIED | statement_cache_size=0 in connect_args dict (line 38); lifespan context manager; get_db raises RuntimeError if AsyncSessionLocal is None |
| `api/core/config.py` | pydantic-settings Settings | VERIFIED | BaseSettings with database_url, anthropic_api_key, debug fields; env_file=".env" |
| `api/main.py` | FastAPI app with lifespan, routers | VERIFIED | lifespan=lifespan, include_router(arguments_router.router), /health endpoint |
| `api/models/models.py` | 10 ORM models, no create_all | VERIFIED | All 10 tables defined; no create_all in file (confirmed by grep); Alembic-only DDL |
| `api/routers/arguments.py` | GET /{argument_id}/utterances | VERIFIED | Router with 404 handling, argument_id: int path param (SQL injection mitigation) |
| `api/schemas/utterance.py` | UtteranceResponse, ArgumentMetadataResponse, ArgumentUtterancesResponse | VERIFIED | All three schemas present; from_attributes=True on UtteranceResponse |
| `api/services/arguments.py` | get_argument_with_utterances, latest completed parse run | VERIFIED | Queries pipeline_runs WHERE step='parse' AND status=COMPLETED for max run ID; orders utterances by sequence ASC |
| `alembic/env.py` | Async migration runner | VERIFIED | async_engine_from_config + asyncio.run(); imports Base from api.models.models |
| `alembic/versions/0001_initial_schema.py` | Hand-written migration, 10 tables | VERIFIED | All 10 tables in FK-dependency order; enum types created; indexes on utterances |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | Server load with FASTAPI_BASE_URL from $env/static/private | VERIFIED | Line 1: `import { FASTAPI_BASE_URL } from '$env/static/private'`; no PUBLIC_ prefix anywhere in app/src/ |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | Chat rendering with Runes | VERIFIED | `let { data } = $props()`; {#each data.utterances}; dispatches to StageDirection/ChatBubble; turn-gap logic |
| `app/src/lib/components/ChatBubble.svelte` | $props(), apolitical framing | VERIFIED | `let { utterance } = $props()`; no export let; no $: reactive; identical bubble backgrounds; null-safe `{utterance.raw_speaker_label ?? ''}` |
| `app/src/lib/components/StageDirection.svelte` | $props() | VERIFIED | `let { utterance } = $props()`; amber left border (#d97706); visually distinct from chat bubbles |
| `pipeline/__main__.py` | argparse CLI entry point | VERIFIED | ingest and parse subcommands; asyncio.run(run_ingest/run_parse) |
| `pipeline/commands/ingest.py` | URL validation, idempotent download | VERIFIED | _validate_url() called before httpx; scheme=https + netloc.endswith("supremecourt.gov"); pdf_path.write_bytes only when file doesn't exist |
| `pipeline/commands/parse.py` | PDF extract → state machine → LLM → utterance rows | VERIFIED | Calls extract_pages, parse_transcript, parse_with_llm; writes Utterance rows with pipeline_run_id, strategy, person_id=None |
| `pipeline/db.py` | Async engine, get_session | VERIFIED | statement_cache_size=0 in connect_args (line 41); get_session async context manager with commit/rollback |
| `pipeline/parser/extractor.py` | pdfplumber page extraction | VERIFIED | extract_pages skips cover/TOC pages, stops at word-index, strips line numbers and headers |
| `pipeline/parser/state_machine.py` | Rule-based parser, F04 fix, cascade fix | VERIFIED | TOC_SECTION_RE includes ON\s+BEHALF\s+OF (F04 fix); two-variable pending_section_hint / current_section_hint (cascade fix) |
| `pipeline/parser/llm_pass.py` | instructor/Claude LLM corrective pass | VERIFIED | instructor.from_anthropic with AsyncAnthropic(max_retries=0); tenacity outer layer for transient errors; instructor inner layer for schema validation |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `+page.server.ts` | FASTAPI_BASE_URL | `$env/static/private` | WIRED | Line 1 confirmed: `import { FASTAPI_BASE_URL } from '$env/static/private'` |
| `+page.server.ts` | FastAPI `/arguments/${params.id}/utterances` | fetch in load function | WIRED | Line 6: `fetch(\`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances\`)` |
| `+page.svelte` | ChatBubble | import + `{#each}` dispatch | WIRED | Imports ChatBubble; renders when `!utterance.is_stage_direction` |
| `+page.svelte` | StageDirection | import + `{#each}` dispatch | WIRED | Imports StageDirection; renders when `utterance.is_stage_direction` |
| `api/routers/arguments.py` | `api/services/arguments.py` | `argument_service.get_argument_with_utterances(db, argument_id)` | WIRED | Import confirmed; service called with db dependency |
| `api/services/arguments.py` | ORM models (Argument, Case, CaseArgument, PipelineRun, Utterance) | SQLAlchemy select queries | WIRED | All models imported; queries verified for max-run-id pattern |
| `pipeline/commands/parse.py` | `pipeline/parser/extractor.py` | `extract_pages(pdf_path)` | WIRED | Import and call confirmed |
| `pipeline/commands/parse.py` | `pipeline/parser/state_machine.py` | `parse_transcript(pages)` | WIRED | Import and call confirmed |
| `pipeline/commands/parse.py` | `pipeline/parser/llm_pass.py` | `await parse_with_llm(pages_text)` | WIRED | Import and call confirmed; LLM failure falls back gracefully |
| `scripts/dev-start.ps1` | `api/main.py` | `uvicorn api.main:app --reload --port 8000` | WIRED | Line 33 confirmed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `+page.svelte` | `data.utterances` | `+page.server.ts` → FastAPI GET /arguments/{id}/utterances → SQLAlchemy query | SQLAlchemy select(Utterance).where(...).order_by(sequence.asc()) against live Postgres | FLOWING |
| `+page.svelte` | `data.argument` (case_name, docket_number, argued_date, question_number) | `+page.server.ts` → service layer → Case + Argument ORM rows | Joins Case + CaseArgument + Argument; uses is_lead=True for lead case | FLOWING |
| `ChatBubble.svelte` | `utterance` prop | Parent `+page.svelte` passes each utterance object | Real utterance from API response | FLOWING |
| `StageDirection.svelte` | `utterance` prop | Parent `+page.svelte` passes each stage-direction utterance | Real utterance from API response | FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — API server requires a running Postgres instance and live data. Cannot test API endpoints without an external service. Health endpoint could be tested in isolation but is not load-bearing for goal verification.

### Probe Execution

No probes declared in PLAN files. Step 7c: SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | Plan 02 | Alembic migrations, no create_all | SATISFIED | 0001_initial_schema.py creates all 10 tables; grep for create_all in api/, alembic/, pipeline/ returns no results |
| INFRA-02 | Plan 02 | Consolidated argument schema | SATISFIED | case_arguments M:M join table with composite PK; is_lead boolean |
| INFRA-03 | Plan 01 | Local dev environment | SATISFIED | scripts/dev-start.ps1 starts Postgres + alembic upgrade head + uvicorn + npm run dev |
| PIPE-01 | Plan 03 | Ingest CLI command | SATISFIED | pipeline/commands/ingest.py; SSRF validation; idempotent Case rows; PDF immutability |
| PIPE-02 | Plan 03 | Immutable PDFs | SATISFIED | pdf_path.write_bytes only when file doesn't exist |
| PIPE-03 | Plan 04 | Parse CLI command | SATISFIED | pdfplumber + state machine + LLM pass fully implemented |
| PIPE-04 | Plan 04 | pipeline_run_id and strategy on utterance rows | SATISFIED | Every Utterance insert sets pipeline_run_id=run.id and strategy=run.strategy |
| PIPE-05 | Plan 04 | is_stage_direction classification | SATISFIED | STAGE_DIR_RE, TERMINAL_STAGE_RE in state machine; LLM ParsedUtterance has is_stage_direction field |
| PIPE-06 | Plan 04 | LLM failure classification | SATISFIED | tenacity for transient (RateLimitError, APIConnectionError); instructor max_retries=2 for structural; failure recorded via _fail_run |
| PIPE-10 | Plan 04 | pipeline_run state machine | SATISFIED | pending→running at start; running→completed on success; running→failed on error |
| PIPE-11 | Plan 04 | Re-run creates new rows, no deletion | SATISFIED | No DELETE statements; pipeline_run_id links each utterance to its producing run; API queries max COMPLETED run |
| API-01 | Plan 05 | GET /arguments/{id}/utterances | SATISFIED | Router + service + schemas fully implemented |
| UI-01 | Plan 05 | Two-sided chat rendering | SATISFIED (code) | ChatBubble side alignment (BENCH right, ADVOCATE left); requires human browser confirmation |
| UI-02 | Plan 05 | Speaker label in bubbles | SATISFIED (code) | raw_speaker_label displayed in ChatBubble header row |
| UI-03 | Plan 05 | Stage directions visually distinct | SATISFIED (code) | StageDirection component: amber border, italic amber text, full-width, 48px vertical margin |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found in production source | — | — | — | — |

No `TBD`, `FIXME`, `XXX`, `TODO`, or `HACK` markers found in any production source file (api/, pipeline/, app/src/). All debt markers appear only in planning docs and test files where they are appropriate.

Note: The REVIEW.md (01-REVIEW.md) identified 5 critical issues. All 5 are confirmed FIXED in the actual source:
- CR-01 (get_db NPE): Fixed — `if AsyncSessionLocal is None: raise RuntimeError(...)` in database.py lines 61-67
- CR-02 (null speaker label): Fixed — `{utterance.raw_speaker_label ?? ''}` in ChatBubble.svelte line 53
- CR-03 (dry-run RUNNING stuck): Fixed — `run.status = PipelineRunStatus.PENDING` in parse.py line 166
- CR-04 (wrong MAX query): Fixed — queries pipeline_runs WHERE step='parse' AND status=COMPLETED in services/arguments.py lines 84-91
- CR-05 (grep on Windows): Fixed — uses pathlib.Path.rglob in tests/test_schema.py lines 139-143

### Hard Constraint Verification

| Constraint | Status | Evidence |
|------------|--------|---------|
| No `Base.metadata.create_all` in api/, pipeline/, alembic/ | VERIFIED | Grep returns 0 matches in all three source directories |
| `statement_cache_size=0` inside `connect_args` dict in api/core/database.py | VERIFIED | database.py line 38: `connect_args={"statement_cache_size": 0}` |
| `statement_cache_size=0` inside `connect_args` dict in pipeline/db.py | VERIFIED | pipeline/db.py line 41: `connect_args={"statement_cache_size": 0}` |
| `FASTAPI_BASE_URL` from `$env/static/private` only, never PUBLIC_ | VERIFIED | +page.server.ts line 1: `from '$env/static/private'`; grep for PUBLIC_ in app/src/ returns 0 matches |
| Svelte 5 Runes — $props() not export let, no $: reactive | VERIFIED | All three Svelte components use `let { ... } = $props()`; grep for `export let` and `$:` in app/src/ returns 0 matches |
| Pipeline offline only — no pipeline steps as HTTP endpoints | VERIFIED | api/routers/ contains only arguments.py (GET /arguments/{id}/utterances); no ingest/parse/resolve endpoints |

### Human Verification Required

#### 1. End-to-End Chat Rendering

**Test:** With Postgres running, run:
```
python -m pipeline ingest --url "https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf" --primary-docket 14-556 --dockets 14-562 14-571 14-574 --case-name "Obergefell v. Hodges" --argued-date 2015-04-28
python -m pipeline parse --run-id 1
```
Then navigate to `http://localhost:5173/cases/obergefell-v-hodges/arguments/1` with the SvelteKit dev server running.

**Expected:** Page renders Obergefell oral argument as a two-sided chat:
- Justice utterances right-aligned (bench side)
- Advocate utterances left-aligned (advocate side)
- Stage directions (e.g., "(Laughter.)") rendered as full-width amber-bordered italic blocks with 48px vertical margin above and below
- Heading bar shows "Obergefell v. Hodges", "No. 14-556", "Argued April 28, 2015", "Question 1"
- Dark theme: page background #0f1117, bubbles #1e293b

**Why human:** Visual rendering, layout position, and chat appearance cannot be verified programmatically. Requires Postgres with live data.

#### 2. ROADMAP SC 1 Wording Discrepancy

**Test:** Review ROADMAP.md Phase 1 Success Criterion 1 which says pipeline_run records with status `pending`. Compare against actual ingest behavior which creates status `completed`.

**Expected:** Developer acknowledges this is a ROADMAP wording error (the implementation is correct per REQUIREMENTS.md PIPE-01 which says status=COMPLETED). Update ROADMAP.md SC 1 to reflect actual behavior.

**Why human:** This is a documentation consistency issue requiring a human judgment call on whether to fix the roadmap wording or adjust the implementation.

### Gaps Summary

**SC 1 wording mismatch (partial, not a blocker):** ROADMAP.md Phase 1 Success Criterion 1 states that after ingest, the database contains pipeline_run records "with status `pending`". The actual implementation creates the pipeline_run with `status=COMPLETED` immediately (ingest is a synchronous operation). This was an intentional design decision documented in the SUMMARY (Plan 03, key-decisions section). REQUIREMENTS.md PIPE-01 correctly says "status=COMPLETED". The implementation is correct; the ROADMAP wording needs updating.

This is classified as a WARNING, not a BLOCKER. The functional goal is met — records exist in the database after ingest. The status value (COMPLETED vs pending) is consistent with the requirements document. Only the ROADMAP SC wording is inconsistent.

**Action required:** Update ROADMAP.md Phase 1 SC 1 to say "pipeline_run record with status `completed`" instead of `pending`, or add a note clarifying that the ingest run itself completes synchronously.

---

_Verified: 2026-06-11T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
