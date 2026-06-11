# Research Summary: SCOTUS Chat

## Executive Summary

SCOTUS Chat transforms flat Supreme Court oral argument transcripts into a conversational, two-sided chat interface. The dominant competitor is Oyez.org — it owns audio+transcript sync and an 8,300-argument corpus — but renders transcripts as dense text walls with no visual differentiation between the Bench and advocates. The differentiating bet is presentation: chat-style layout, speaker avatars, uniform bio cards for every participant, and semantically distinct stage direction rendering. None of this requires novel technology. It requires a well-structured pipeline that produces clean, attributed utterance rows, and a frontend that renders them thoughtfully.

The architecture is a three-tier system with a hard separation of concerns: an offline Python pipeline (PDF ingest → LLM parse → speaker resolution → enrichment → citation extraction) that owns all writes; a read-only FastAPI layer that serves the structured results; and a SvelteKit frontend that renders the chat UI. The pipeline and API are decoupled at the database layer — the pipeline writes directly to PostgreSQL and the API reads from it; neither talks to the other over HTTP.

---

## Recommended Stack

| Technology | Version | Purpose | Critical notes |
|---|---|---|---|
| Svelte / SvelteKit | 5.x / 2.x | Frontend; SSR, routing | Use Runes (`$state`, `$derived`, `$effect`); do not use Svelte 4 store patterns |
| `@sveltejs/adapter-node` | latest | Node.js deploy target | Required for DO App Platform — `adapter-auto` and `adapter-static` break the SSR proxy pattern |
| TypeScript | 5.x | Type safety | SvelteKit scaffolds this by default |
| Python | 3.12 | Runtime | Mature, broadly library-supported |
| FastAPI | 0.115.x+ | API layer | Install via `fastapi[standard]` — pulls in Pydantic v2, uvicorn |
| Pydantic | v2 (bundled) | Schema validation | `model_validate` replaces `from_orm`; 5–10x faster than v1 |
| SQLAlchemy | 2.0+ (async API) | ORM | `expire_on_commit=False` is mandatory — omitting it causes `MissingGreenlet` in async context |
| asyncpg | 0.29.x | Async PG driver (API) | **Requires `statement_cache_size=0` when behind DO PgBouncer Transaction mode** — silent failure otherwise |
| psycopg2-binary | 2.9.x | Sync driver (Alembic only) | Alembic autogenerate works better with sync engine |
| psycopg3 + psycopg_pool | latest | Sync driver (pipeline CLI) | Pipeline is a CLI process; sync pool of 1–5 connections is sufficient |
| Alembic | 1.13.x | Migrations | Single DDL authority; never use `Base.metadata.create_all` anywhere |
| Gunicorn 22.x + UvicornWorker | — | Production process manager | `--workers 2` for DO starter tier |
| Anthropic SDK | 0.40.x+ | Claude API client | Use `AsyncAnthropic` for async pipeline steps |
| instructor | latest | Structured LLM output | Wraps Anthropic SDK; adds Pydantic validation + auto-retry on schema failures |
| pdfplumber | 0.11.x | PDF extraction | Layout-aware; better than pypdf for SCOTUS transcript formatting |
| tenacity | 8.x | Outer retry (rate limits) | Handles HTTP 429/503; separate from instructor's inner schema-validation retry |
| httpx | 0.27.x | External HTTP (Oyez, FJC) | Async-native |
| PostgreSQL | 16 (DO Managed) | Primary data store | Use PgBouncer; Transaction mode; `statement_cache_size=0` in asyncpg |

---

## Table Stakes Features for v1

**Must have at launch:**
1. Per-utterance speaker attribution with name and role label
2. Chat-style two-sided layout — Bench one side, advocates the other
3. Stage direction rendering as distinct visual components (not speech bubbles)
4. Speaker avatars with initials fallback when no photo is available
5. Uniform bio card schema for every speaker — same fields, same depth for all
6. Argument-at-a-glance header: case name, docket number, date argued, speaker roster
7. Stable shareable URLs: `/cases/{slug}/arguments/{id}` pattern
8. Open Graph metadata for social unfurl previews
9. Mobile-responsive layout tested at 375px viewport
10. Keyboard navigation throughout
11. WCAG 2.1 AA color contrast; speaker side differentiated by layout position, not color alone

**Should have (differentiators over Oyez):**
- Argument section navigation (Petitioner → Respondent → Rebuttal → Amicus)
- Citation callout styling — raw citation strings as distinct inline text
- Re-argument awareness — multiple sessions for same case clearly labeled

**Defer to v2+:**
- Within-argument text search, full-text cross-case search, audio playback (link to Oyez), user accounts, AI-generated summaries (violates apolitical framing — hard no)

---

## Architecture and Build Order

**Three non-negotiable architecture decisions:**

1. **Pipeline writes directly to PostgreSQL; FastAPI is read-only.** The pipeline never calls FastAPI. FastAPI never triggers pipeline steps. LLM operations must never block live user requests.

2. **All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions.** `FASTAPI_BASE_URL` is a server-only env var (not a `PUBLIC_` variable). Eliminates CORS and keeps internal API URL out of browser JS bundles.

3. **Alembic is the sole DDL authority.** Neither the pipeline nor FastAPI calls `Base.metadata.create_all`. Both import from the same shared `db/models.py`.

**Recommended build order:**

```
1. Database schema + Alembic migrations
   ← M:M case-argument and pipeline_run_id must be correct from day one

2. Pipeline Step 1: Ingest
   ← Establishes state machine; proves DB writes work; stores PDF locally

3. Pipeline Step 2: Parse (LLM utterance extraction)
   ← Core value; validates LLM integration; produces utterance rows

4. FastAPI read routes (/cases, /arguments/{id}/utterances, /people/{id})
   ← Once live, SvelteKit has real endpoints to develop against

5. SvelteKit chat UI
   ← Builds against real FastAPI data; all MVP table-stakes features

6. Pipeline Step 3: Resolve (speaker → people matching)
   ← Requires utterances from Step 2

7. Pipeline Step 4: Enrich (bio/photo from Oyez, FJC)
   ← Requires people records from Step 3

8. Pipeline Step 5: Citations (raw text extraction)
   ← Last because display-only; no downstream dependencies

9. End-to-end: run full pipeline on 5–10 real cases; verify UI; production smoke test
```

---

## Critical Pitfalls (top 7, most important first)

**1. LLM retry loops treating structural failures as transient — data corruption risk**
Separate by failure type: tenacity handles HTTP 429/503 (transient); instructor handles schema failures (2-retry max then halt). Track `retry_count` and `failure_reason` on `pipeline_run`. Retry rate above 5% on Parse is the warning sign. Address before first end-to-end run.

**2. Pre-2004 transcripts use "QUESTION" for all Justice speech — silent parse failure**
The Court suppressed Justice names until October Term 2003. Fix: tag `transcript_format_version` at Ingest; hard-error on pre-2004 transcripts. Must be wired at Ingest, not retrofitted.

**3. Fixed-token transcript chunking breaks speaker turn continuity**
Most SCOTUS transcripts (20–40K tokens) fit in Claude's 200K context window — use single-call parsing when possible. When chunking is required, split on speaker-turn boundaries with 2–3 turn overlap. Never split on character count.

**4. Speaker resolution fails on surname-only and role-only labels**
Pre-seed a `speaker_alias` table with known Justice rosters and SG patterns. Provide LLM with full case metadata (term year, docket, counsel of record). Gate low-confidence matches as `needs_review` — never auto-commit a guess. Disallow automatic creation of new person records.

**5. Consolidated cases require M:M from day one — cannot retrofit**
~10–15% of SCOTUS arguments cover multiple dockets. The `argument` ↔ `case` relationship must be many-to-many from the initial schema. A FK on `argument` is wrong. Retrofitting M:M after data exists requires a migration and re-parse of affected transcripts.

**6. PgBouncer Transaction mode conflicts with asyncpg prepared statement cache**
Digital Ocean exposes PgBouncer in Transaction mode by default. Fix: `connect_args={"statement_cache_size": 0}` in `create_async_engine`. One-line fix, must be in initial engine config — discovered late, causes intermittent production failures with no obvious error message.

**7. Asymmetric bio depth breaks the apolitical framing constraint**
Justice bios are easily sourced; advocate bios are often sparse. Define the bio schema (fields, character limits, required vs optional) before building the Enrich step. No Justice bio field should be populated unless the equivalent advocate field is also populated or confirmed unavailable.

---

## Cross-Cutting Themes

**Pipeline data quality gates everything downstream.** The chat UI, bio cards, and avatars are all rendering pipeline output. Pipeline errors produce faithfully rendered wrong data — the UI has no layer for correction. Invest in pipeline validation before building UI components.

**The apolitical constraint is architectural, not editorial.** It shapes what the pipeline is allowed to produce and what the UI is allowed to display. Every feature request involving derived insight (summaries, sentiment, statistics) should be evaluated against this constraint — it is a hard scope boundary.

**Re-runnability requires schema discipline.** The `pipeline_run_id` pattern (new rows per run; a promotion step swaps the active run) protects audit history. Any shortcut that shares state across steps or overwrites prior run rows destroys this property.

**Test both SSR and client-side navigation for API integration.** SvelteKit server load functions bypass CORS; client-side navigation after hydration is subject to CORS. SSR-only testing misses client-side failures. Configure FastAPI CORSMiddleware explicitly for the production SvelteKit origin.

---

## Spikes Recommended Before Planning

- **LLM parse prompt design** — 2–4 hours against 3–5 real SCOTUS PDFs to validate Claude structured output quality before finalizing the `ParsedUtterance` schema
- **`speaker_alias` seed data completeness** — source full patterns from FJC and `walkerdb/supreme_court_transcripts` before Phase 5 (Resolve) planning
- **Oyez API current schema** — no official docs; validate live response shape before Enrich step schema is finalized
- **Section detection reliability** — test argument block boundary detection (Petitioner/Respondent/Rebuttal/Amicus) against 10–20 transcripts to confirm whether section nav ships in MVP

---
*Synthesized from STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md*
*Date: 2026-06-11*
