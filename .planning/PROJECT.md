# SCOTUS Chat

## What This Is

A website that displays Supreme Court oral arguments as a chat-style interface — formatted like a group conversation between the Justices and whoever is arguing before the Court. The goal is accessibility: making dense legal transcripts easy to follow for anyone who wants to understand who said what, who each speaker is, and what's at stake — without editorial framing or political commentary.

## Core Value

Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Chat UI renders an oral argument as a conversation — bench on one side, advocates on the other
- [ ] Each utterance is attributed to a named speaker with an avatar
- [ ] Avatars link to factual, uniformly-formatted bios (same schema for every person)
- [ ] Stage directions (e.g., "(Laughter.)") rendered distinctly from spoken content
- [ ] Offline pipeline ingests a transcript PDF and produces structured utterances in the database
- [ ] Pipeline step 1: Ingest — download PDF, create case/argument/pipeline_run records
- [ ] Pipeline step 2: Parse — LLM extracts utterances from raw transcript text
- [ ] Pipeline step 3: Resolve — match raw speaker names to people records
- [ ] Pipeline step 4: Enrich — populate bio, photo, tenure data from external sources
- [ ] Pipeline step 5: Extract Citations — capture legal citations as raw text strings
- [ ] A small set of hand-picked cases is loaded and viewable to prove the concept

### Out of Scope

- Citation resolution (linking raw citation text to case records) — deferred, schema supports it
- Topic / subject tagging — deferred; non-partisan framing requires careful thought
- Pre-2000 transcript parsing — different strategy needed; pipeline modularity accommodates later
- Cross-case analysis (query utterances by person across cases) — schema supports it, not building yet
- Public user accounts or contributions — not in initial scope
- Monetization — not a driving goal; not excluded for future

## Context

- Owner has existing SvelteKit experience and an active Digital Ocean account
- The pipeline runs offline (not as part of the live app); it populates the database from raw PDFs
- Raw source PDFs are treated as immutable historical documents — never modified after ingest
- Each pipeline step reads from and writes to the database independently; steps are re-runnable in isolation
- Utterances belong to argument records (not cases directly) to correctly handle re-arguments
- Soft references: citations are stored as raw text at parse time, with no requirement for a resolved target to exist
- Speaker resolution uses LLM-assisted matching with case metadata as context
- Oyez Project API, Federal Judicial Center, and supremecourt.gov are the primary external enrichment sources
- Repo will be public on GitHub from the start

## Constraints

- **Tech stack**: SvelteKit (frontend), FastAPI/Python (backend + pipeline), PostgreSQL (database) — decided and not up for revision
- **Hosting**: Digital Ocean App Platform + managed Postgres — owner has existing account
- **Framing**: Apolitical and non-editorial is a hard constraint — every speaker gets identical schema, depth, and treatment
- **Schema forward-compatibility**: Architectural decisions must not block future features (citation resolution, cross-case queries, topic tagging) even when those features aren't being built

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SvelteKit for frontend | Clean syntax for content-focused UI, handles routing + SSR in one framework, owner has experience | — Pending |
| FastAPI (Python) for backend | Pipeline uses Python for LLM calls and PDF processing; keeps server-side in one language | — Pending |
| PostgreSQL on Digital Ocean | Relational model fits entity/relationship structure; native integration with App Platform | — Pending |
| Utterances belong to arguments, not cases | Supports re-arguments (same case, multiple argument events) without schema contortion | — Pending |
| Capture citations now, resolve later | Avoids blocking parse step on resolution; citations stored as raw text strings | — Pending |
| Pipeline is offline | Transcript processing is not a live-request operation; keeps app server simple | — Pending |
| Raw PDFs are immutable | Transcripts are historical documents; all derived data can be regenerated from source | — Pending |
| Re-running a step produces new rows linked to new pipeline_run_id | Old rows preserved until new run is promoted; supports safe re-processing and auditing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-11 after initialization*
