# Phase 1: Foundation + Proof of Concept - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 1-Foundation + Proof of Concept
**Areas discussed:** Parse prompt spike, Dev environment setup, Side assignment in Phase 1, Hand-picked case, Structured output approach, Pipeline CLI design, SvelteKit route structure for Phase 1, FastAPI scaffolding depth

---

## Parse Prompt Spike

| Option | Description | Selected |
|--------|-------------|----------|
| Spike first, then plan | Run /gsd:spike before Phase 1 planning; finalize schema from real results | ✓ |
| Bake spike into Phase 1 execution | First plan = prompt experiments + schema finalization | |
| Build with a reasonable default, iterate later | Pick a sensible schema now, adjust if wrong | |

**User's choice:** Spike first, then plan

---

| Option | Description | Selected |
|--------|-------------|----------|
| Schema only | Spike produces only a validated ParsedUtterance schema | |
| Schema + prompt template | Spike produces schema AND a working prompt template | |
| Schema + prompt + failure taxonomy | Spike also catalogs LLM failure types for PIPE-06 retry logic design | ✓ |

**User's choice:** Schema + prompt + failure taxonomy

---

| Option | Description | Selected |
|--------|-------------|----------|
| Use the hand-picked PoC case + 2–3 others | Test with the actual target case plus others for variety | ✓ |
| Use 4–5 diverse cases regardless of PoC selection | Maximize variety independent of PoC choice | |
| You decide | Let the spike researcher pick | |

**User's choice:** Use the hand-picked PoC case + 2–3 others

---

| Option | Description | Selected |
|--------|-------------|----------|
| Haiku 4.5 (fast, cheap) | claude-haiku-4-5-20251001 — best cost for batch parse | ✓ |
| Sonnet 4.6 (default balance) | More accurate, higher cost | |
| Spike with Sonnet, run with Haiku | Validate with Sonnet, test Haiku matches quality | |

**User's choice:** Haiku 4.5

---

| Option | Description | Selected |
|--------|-------------|----------|
| Full transcript as one prompt | Send full session text in one LLM call | ✓ |
| Chunk by page or section | Split into chunks, merge across boundaries | |
| Spike determines chunking strategy | Spike tests both approaches | |

**User's choice:** Full transcript as one prompt

---

## Dev Environment Setup

**Context:** User clarified they do not have admin access on their Windows work laptop. Docker Desktop requires admin rights for WSL 2 / Hyper-V configuration, so Docker is not viable without IT involvement.

| Option | Description | Selected |
|--------|-------------|----------|
| Native per-user install (no admin needed) | PostgreSQL portable ZIP, Python per-user, Node.js per-user | ✓ |
| Ask IT for Docker Desktop | One-time admin install, then docker compose up | |
| Remote dev box (Digital Ocean droplet) | $6/mo Linux droplet, full admin via SSH | |

**User's choice:** Native per-user install

---

| Option | Description | Selected |
|--------|-------------|----------|
| Three separate terminals, manual start each | Open 3 terminals, run each service independently | |
| A single dev script (e.g., start.ps1 or Makefile) | One command starts all three services | ✓ |
| You decide | Let planner pick | |

**User's choice:** Single dev script

---

| Option | Description | Selected |
|--------|-------------|----------|
| Inside the project repo (/data/pgdata), git-ignored | Self-contained, easy to nuke and recreate | ✓ |
| Separate directory outside the repo (~/pgdata) | Persists across repo clones/deletes | |
| You decide | Let planner pick | |

**User's choice:** Inside the repo, gitignored

---

## Side Assignment in Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Parse step outputs a side field | LLM assigns BENCH/ADVOCATE/UNKNOWN at parse time; stored in DB | ✓ |
| UI derives side from raw label at render time | Frontend checks for "JUSTICE" prefix; no DB field needed in Phase 1 | |
| You decide | Let planner pick | |

**User's choice:** Parse step outputs a side field

---

| Option | Description | Selected |
|--------|-------------|----------|
| BENCH / ADVOCATE / UNKNOWN | Three-value enum; UNKNOWN covers stage directions and ambiguous labels | ✓ |
| BENCH / ADVOCATE only | Force binary assignment; stage directions excluded separately | |
| You decide | Let planner pick | |

**User's choice:** BENCH / ADVOCATE / UNKNOWN

---

## Hand-Picked Case

**Context:** User revealed that Obergefell v. Hodges is what originally inspired this project. It is not just a convenient test case — it is the origin case.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, I have one in mind | User specifies the case | ✓ (via free text) |
| Let the planner pick | Researcher picks a well-structured recent case | |

**User's choice:** Obergefell v. Hodges (the project's origin case)
**Notes:** User said "What started this project was Obergefell v. Hodges." Confirmed it's a good choice; noted the consolidated docket aspect (4 dockets, exercises INFRA-02) and the two-session structure.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Use both sessions as one argument | Full argument (Q1 + Q2); exercises consolidated-docket schema fully | |
| Use Q1 session only for the PoC | First 90-minute session; simpler, faster to validate | ✓ |
| Let the planner decide | Researcher picks one or both sessions | |

**User's choice:** Q1 session only for Phase 1 PoC

---

## Structured Output Approach

**Notes:** User said "I don't have a preference, you decide." Claude chose `instructor` because it is already declared in the project stack (CLAUDE.md lists "Anthropic SDK, instructor, tenacity" for the pipeline). No reason to ignore a declared dependency.

**Claude's decision:** Use `instructor` library wrapping the Anthropic SDK for structured LLM output.

---

## Pipeline CLI Design

| Option | Description | Selected |
|--------|-------------|----------|
| Python package with -m flag | `python -m pipeline ingest --url ...` — no install needed | ✓ |
| Named CLI entrypoint (e.g. `scotus`) | `scotus ingest ...` — requires `pip install -e .` | |
| Standalone scripts | `python pipeline/ingest.py --url ...` — no packaging | |

**User's choice:** Python package with -m flag

---

CLI flag design deferred to planner (user: "you decide").

---

## SvelteKit Route Structure for Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Final URL structure now | `/cases/[slug]/arguments/[id]` — same as Phase 3 target | ✓ |
| Simple placeholder route | `/argument/[id]` or `/` for the PoC; refactor later | |
| You decide | Let planner pick | |

**User's choice:** Final URL structure from day one

---

## FastAPI Scaffolding Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Just the one endpoint, minimal structure | Single router file, no service layer | |
| Full router/service pattern, one endpoint wired | `routers/`, `services/`, `schemas/` with Phase 1 endpoint as first example | ✓ |
| You decide | Let planner pick | |

**User's choice:** Full router/service pattern

---

## Claude's Discretion

- **Structured output library:** `instructor` (already in declared stack — not a real choice)
- **CLI flags for ingest/parse:** planner designs for ergonomics and data needs
- **`tenacity` retry config:** planner configures retry count and backoff for instructor + parse step

## Deferred Ideas

- Obergefell Q2 session — not part of Phase 1 PoC; can be loaded after Phase 1 is validated
- Additional cases beyond Obergefell — pipeline handles them after Phase 1 proves the concept
- Docker Compose setup — deferred due to no admin access; may revisit if dev machine changes
