---
phase: 1
slug: foundation-proof-of-concept
created: 2026-06-11
---

# Phase 1 — Walking Skeleton

> The thinnest possible end-to-end slice. When this skeleton is working, the core concept is provably runnable: PDF → parsed utterances → API → chat view in a browser.

---

## What "Done" Looks Like for the Skeleton

An operator runs four commands from the project root:

```powershell
# 1. Start Postgres + run migrations
.\scripts\dev-start.ps1

# 2. Ingest Obergefell Q1
python -m pipeline ingest `
  --url "https://www.supremecourt.gov/oral_arguments/argument_transcripts/2014/14-556q1_l5gm.pdf" `
  --dockets 14-562 14-571 14-574 `
  --case-name "Obergefell v. Hodges" `
  --argued-date 2015-04-28

# 3. Parse utterances
python -m pipeline parse --run-id 1

# 4. Open browser
# Navigate to: http://localhost:5173/cases/obergefell-v-hodges/arguments/1
```

The browser shows Obergefell v. Hodges as a two-sided chat — Justices on the right, advocates on the left, stage directions visually distinct. No speaker resolution yet (`raw_speaker_label` displayed verbatim). 377 utterances, 8 stage directions.

---

## Architectural Decisions (Locked in Phase 1)

These decisions propagate to all future phases without renegotiation.

### Framework & Runtime

| Layer | Decision | Rationale |
|-------|----------|-----------|
| Frontend | SvelteKit 2.x + Svelte 5 (Runes) | Locked by project stack; SSR + TypeScript |
| Backend | FastAPI 0.115+ + Pydantic v2 | Locked by project stack; async-native |
| Database | PostgreSQL 16 (portable ZIP, no admin) | No Docker; portable per D-06 |
| ORM | SQLAlchemy 2.0 async (`asyncpg`) | FastAPI; `asyncio.run()` for pipeline |
| Migrations | Alembic 1.13+ async template | Sole DDL authority — no `create_all` ever |
| Pipeline driver | psycopg2-binary (Alembic only) | Alembic offline mode requires sync driver |
| LLM | Anthropic SDK + `instructor` Mode.TOOLS | D-14; structured output with Pydantic validation |
| Retry | `tenacity` (outer) + instructor `max_retries=2` (inner) | Two-layer PIPE-06 failure handling |
| PDF extraction | `pdfplumber` `extract_text(layout=False)` | Spike-validated on 4 transcripts |

### Database Schema

10 tables in one initial Alembic migration (`0001_initial_schema.py`):

```
people          — speaker records (person_id, full_name, role_id)
roles           — role definitions (Associate Justice, Petitioner's Counsel, etc.)
court_tenures   — justice tenure dates (person_id, seat, start_date, end_date)
cases           — case records (docket_number UNIQUE, case_name, term_year, slug)
arguments       — argument sessions (argued_date, question_number)
case_arguments  — M:M join (case_id, argument_id, is_lead) — INFRA-02
case_appearances — counsel of record per case
argument_participants — speakers per argument (raw_speaker_label, side)
pipeline_runs   — ingest/parse/resolve run records with status state machine
utterances      — parsed utterance rows (BigInteger PK, UNIQUE on arg+run+seq)
```

Key invariants:
- `case_arguments` composite PK prevents duplicate consolidated dockets
- `utterances.person_id` is NULL at parse time; Phase 2 populates it
- `utterances.side` is `BENCH | ADVOCATE | UNKNOWN` (assigned at parse time from `assign_side()`)
- `pipeline_run.status` state machine: `pending → running → completed | failed | needs_review`

### Directory Layout (Canonical for All Phases)

```
project/
├── api/
│   ├── core/
│   │   ├── config.py          # pydantic-settings Settings
│   │   └── database.py        # async engine, sessionmaker, get_db dependency
│   ├── models/
│   │   └── models.py          # SQLAlchemy ORM (shared with pipeline)
│   ├── routers/
│   │   └── arguments.py       # GET /arguments/{id}/utterances
│   ├── schemas/
│   │   └── utterance.py       # Pydantic response models
│   ├── services/
│   │   └── arguments.py       # query logic
│   └── main.py                # FastAPI app, lifespan, include_router
├── pipeline/
│   ├── __main__.py            # python -m pipeline <cmd>
│   ├── commands/
│   │   ├── ingest.py          # ingest command
│   │   └── parse.py           # parse command
│   ├── parser/
│   │   ├── extractor.py       # pdfplumber (copied from spike)
│   │   ├── state_machine.py   # rule-based parser (copied from spike + F04 fix)
│   │   └── llm_pass.py        # instructor corrective pass
│   └── db.py                  # async engine for pipeline
├── app/                       # SvelteKit root
│   └── src/
│       ├── routes/
│       │   ├── +layout.svelte
│       │   └── cases/[slug]/arguments/[id]/
│       │       ├── +page.server.ts
│       │       └── +page.svelte
│       └── lib/components/
│           ├── ChatBubble.svelte
│           └── StageDirection.svelte
├── alembic/
│   ├── versions/0001_initial_schema.py
│   ├── env.py
│   └── alembic.ini
├── data/
│   ├── pgdata/       # gitignored
│   └── pdfs/         # gitignored
├── scripts/
│   └── dev-start.ps1
├── tests/
│   └── test_schema.py
├── pipeline/tests/
│   ├── conftest.py
│   ├── test_ingest.py
│   ├── test_parse.py
│   └── test_pipeline_run.py
├── api/tests/
│   └── test_arguments.py
├── .env                       # DATABASE_URL, ANTHROPIC_API_KEY
├── .env.example
├── requirements.txt
├── requirements-dev.txt
└── pytest.ini
```

### API Contract (Phase 1 → Phase 3 stable)

`GET /arguments/{id}/utterances` returns:

```json
{
  "utterances": [
    {
      "id": 1,
      "sequence": 1,
      "raw_speaker_label": "CHIEF JUSTICE ROBERTS",
      "text": "We'll hear argument...",
      "is_stage_direction": false,
      "side": "BENCH",
      "section_hint": "petitioner",
      "person_id": null,
      "strategy": "rule_based"
    }
  ]
}
```

`person_id` is null in Phase 1. Phase 2 populates it via speaker resolution.

### SvelteKit Integration Contract

- All FastAPI calls go through `+page.server.ts` only
- `FASTAPI_BASE_URL` uses `$env/static/private` — never `PUBLIC_`
- Route: `/cases/[slug]/arguments/[id]` from day one (D-17)
- Svelte components: Runes only (`$props`, `$state`, `$derived`) — no legacy stores

### Critical Config (Locked — Never Change)

- `asyncpg`: `connect_args={"statement_cache_size": 0}` (not a top-level engine arg)
- `async_sessionmaker(expire_on_commit=False)` (prevents MissingGreenlet in async)
- `AsyncAnthropic(max_retries=0)` (tenacity owns transient retries; avoid double-retry)
- `Alembic`: `Base.metadata.create_all()` NEVER appears anywhere in the codebase

### Side Assignment (D-09 / D-10)

Side is assigned deterministically at parse time via `assign_side(raw_speaker_label, is_stage_direction)`:
- `CHIEF JUSTICE.*` | `JUSTICE.*` | `QUESTION` → `BENCH`
- `MR.` | `MS.` | `MRS.` | `GENERAL.*` → `ADVOCATE`
- Stage directions or unrecognized labels → `UNKNOWN`

Phase 2 (Speaker Resolution) may correct side values but does not introduce the field.

---

## Phase 1 → Phase 2 Handoff

| Field | Phase 1 State | Phase 2 Action |
|-------|--------------|----------------|
| `utterances.person_id` | NULL | Resolve step populates via speaker_alias lookup |
| `utterances.side` | Assigned (deterministic) | Resolve step may correct |
| `argument_participants.person_id` | NULL | Resolve step populates |
| `speaker_alias` table | Empty | Seeded in Phase 2 before resolve step |

---

## Execution Order (Phase 1 Plans)

```
Wave 1 (parallel):
  01-PLAN-01: Dev environment scaffold
  01-PLAN-02: Schema + Alembic migration

Wave 2 (depends on Wave 1):
  01-PLAN-03: Pipeline ingest command + test infrastructure

Wave 3 (parallel, depends on Wave 2):
  01-PLAN-04: Pipeline parse command
  01-PLAN-05: FastAPI endpoint + SvelteKit chat view
```
