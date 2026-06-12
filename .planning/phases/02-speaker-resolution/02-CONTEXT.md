# Phase 2: Speaker Resolution - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 delivers a working speaker resolution pipeline step: an interactive CLI command that maps every raw speaker label in a parsed argument to a real `Person` record in the database. Justices auto-resolve against a pre-seeded alias table; unrecognised labels prompt the operator interactively. Once resolved, every utterance carries a `person_id` and the chat view displays the real speaker name and role label instead of the raw transcript label.

**Phase 2 deliverables:**
1. Alembic migration adding the `speaker_alias` table
2. `python -m pipeline seed-aliases` command — pre-seeds current + historical SCOTUS Justices
3. `python -m pipeline resolve --run-id <N>` — interactive resolve step (PIPE-07, PIPE-08, PIPE-09)
4. `GET /people/{id}` FastAPI endpoint (API-03)
5. `GET /arguments/{id}/utterances` extended to embed `speaker_name` + `speaker_role` per utterance
6. Chat view updated to display resolved speaker name and role label

**Pre-Phase 2 prerequisite (fix before planning):**
- Em dash → `&shy;` (U+00AD soft hyphen) corruption in parsed transcript text. Fix in the parse step text normalization (`pipeline/parser/extractor.py` or `state_machine.py`), then re-parse Obergefell. This is a standalone patch, not part of Phase 2 proper.

</domain>

<decisions>
## Implementation Decisions

### Alias Table Schema
- **D-01:** `speaker_alias` uses exact string matching — each row stores a normalized label (e.g., `"JUSTICE KAGAN"`) mapped to a `person_id`. No regex patterns. Simple, fast, predictable.
- **D-02:** Labels are normalized before lookup: uppercase + strip trailing colon + trim whitespace. Example: `"Justice Kagan:"` → `"JUSTICE KAGAN"`. Normalization applied consistently at resolve time and when saving new alias rows.

### Seed Data
- **D-03:** Pre-seed Justices via `python -m pipeline seed-aliases`. Includes all current Justices (Roberts, Thomas, Alito, Sotomayor, Kagan, Gorsuch, Kavanaugh, Barrett, Jackson) and recent historical Justices needed for Phase 2 case (Scalia, Kennedy, Ginsburg, Breyer). Common label variants included: `"CHIEF JUSTICE"` → Roberts, `"JUSTICE [SURNAME]"` for each Justice.
- **D-04:** Counsel records are NOT pre-seeded. They are created interactively during the first resolve run and persisted to the alias table for future auto-resolution.

### Resolve Algorithm
- **D-05:** Resolve step is an interactive CLI command. For each unique normalized `raw_speaker_label` in the argument (non-stage-directions only), the step checks the `speaker_alias` table first:
  - **Hit:** auto-resolve — set `person_id` on all utterances with that label, no operator input required.
  - **Miss:** prompt operator interactively with a numbered list of existing `people` records + a "Create new person" option.
- **D-06:** Every operator-resolved mapping is immediately saved to `speaker_alias` so the same label auto-resolves on all future arguments.
- **D-07:** `pipeline_run.status` reaches `COMPLETED` only when every unique non-null `raw_speaker_label` in the argument has a resolved `person_id`. The step does not complete with any label unresolved (no skipping allowed).
- **D-08:** Creating new `people` records during the interactive session is allowed — requires operator confirmation at the prompt (not automatic). This supersedes the strict reading of PIPE-09; the "never auto-creates" constraint still holds; interactive creation is explicitly allowed.
- **D-09:** If the operator interrupts mid-session (Ctrl+C), the `pipeline_run` status is set to `needs_review` to indicate partial resolution. The operator can re-run to continue — already-resolved labels auto-skip via alias table; only the remaining unresolved labels prompt again.

### API — Speaker Data Embedding
- **D-10:** `GET /arguments/{id}/utterances` is extended to JOIN `people` and `roles` tables and embed `speaker_name: Optional[str]` and `speaker_role: Optional[str]` directly in each `UtteranceResponse`. The SvelteKit chat view gets everything it needs from a single API call. No per-speaker frontend calls.
- **D-11:** `GET /people/{id}` (API-03) is implemented in Phase 2 with `{id, full_name, role_name}`. `photo_url` is not added until Phase 3 when avatar rendering is needed.

### Claude's Discretion
- Exact `speaker_alias` table column names (e.g., `id`, `normalized_label`, `person_id`, `created_at`, `notes` — design for ergonomics)
- Whether `argument_participants.person_id` is also updated during resolve (in addition to `utterances.person_id`)
- Seed data file format and exact `seed-aliases` CLI implementation details
- Interactive terminal prompt display (numbering format, paging for large people lists)
- How `role_name` is derived — join `people → roles` via `person.role_id`
- `people` table `full_name` format (e.g., "Elena Kagan" vs. "Kagan, Elena") — pick the natural display format

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition
- `.planning/PROJECT.md` — Core value, constraints, out-of-scope items (apolitical framing hard constraint)
- `.planning/REQUIREMENTS.md` — PIPE-07, PIPE-08, PIPE-09 (resolve step), API-03 (GET /people/{id}); also UI-02 (speaker name + role in chat view)
- `.planning/ROADMAP.md` — Phase 2 goal, success criteria, and dependency on Phase 1

### Hard Constraints
- `CLAUDE.md` — Alembic-only DDL (no `create_all`), pipeline offline-only, apolitical framing (every speaker identical schema/treatment), `asyncpg` `statement_cache_size=0`

### Existing Code (read before planning — changes needed here)
- `api/models/models.py` — ORM models; `speaker_alias` table to be added here; `Person` and `Role` models are the resolve step's targets
- `alembic/versions/0001_initial_schema.py` — existing migration; Phase 2 adds `0002_add_speaker_alias.py`
- `pipeline/__main__.py` — CLI entry point; `resolve` and `seed-aliases` subcommands to be added
- `api/schemas/utterance.py` — `UtteranceResponse` to gain `speaker_name` and `speaker_role` optional fields
- `api/services/arguments.py` — `get_argument_with_utterances()` to JOIN people + roles

### Patterns to Follow
- `pipeline/commands/ingest.py` and `pipeline/commands/parse.py` — async SQLAlchemy + argparse pattern for `resolve.py`
- `api/routers/arguments.py` + `api/services/arguments.py` — router/service/schema pattern for new `people` router
- `pipeline/db.py` — async database session utilities

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/db.py` — `get_db()` async session factory; `resolve.py` and `seed_aliases.py` follow the same pattern as `ingest.py`
- `api/core/database.py` — async engine and session for the API; `people` router uses the same setup as `arguments` router
- `api/models/models.py` — `Person`, `Role`, `Utterance`, `ArgumentParticipant`, `PipelineRun` all in scope for Phase 2; no new ORM models beyond `SpeakerAlias`
- `api/routers/arguments.py` — structural template for the new `api/routers/people.py`

### Established Patterns
- **Alembic-only DDL:** New `speaker_alias` table must go through `alembic/versions/0002_...py` — never `Base.metadata.create_all`
- **`python -m pipeline <command>`:** `resolve` and `seed-aliases` follow the existing argparse subcommand pattern in `__main__.py`
- **FastAPI router → service → schema:** `people` endpoint follows same 3-layer split as `arguments`
- **Async SQLAlchemy sessions:** `async with AsyncSession` pattern throughout; `expire_on_commit=False` already set (01-05 decision)
- **`instructor` library:** NOT needed for Phase 2 — resolve is lookup-based + interactive, not LLM-driven

### Integration Points
- `Utterance.person_id` — null at Phase 1; resolve step writes FK to `people.id` here
- `ArgumentParticipant.person_id` — same FK; may also be updated during resolve
- `PipelineRun.status` — `needs_review` value (already in enum) used when operator interrupts mid-session
- `UtteranceResponse.person_id` — already in schema (returns null); Phase 2 adds `speaker_name` and `speaker_role` alongside it
- Chat view (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`) — `raw_speaker_label` display replaced by resolved name + role

</code_context>

<specifics>
## Specific Ideas

- The interactive resolve prompt should present existing people in the DB as a numbered list so the operator can type a number rather than a full name. "Create new person" is always listed as the last option.
- The `speaker_alias` seed for Justices should cover both surname-only variants (`"JUSTICE KAGAN"`) and the Chief Justice role label (`"CHIEF JUSTICE"` → Roberts). Role-only labels like `"GENERAL"` (Solicitor General) are NOT pre-seeded — they require interactive resolution since multiple people hold that role across cases.
- The resolve step should display progress clearly: "Resolving 13 unique labels — 9 auto-matched from alias table, 4 need input."
- Phase 2 is scoped to Obergefell only. The seed and interactive resolve together must handle the full Obergefell speaker set before Phase 2 is complete.

</specifics>

<deferred>
## Deferred Ideas

- **LLM-assisted matching** — PIPE-07 originally specified LLM-assisted matching with case metadata as context. Replaced with interactive-first approach. LLM matching could be revisited in a future milestone when batch-processing many transcripts makes interactive resolution impractical.
- **`photo_url` on Person** — needed for Phase 3 avatars (UI-05). Deferred to Phase 3 migration.
- **Obergefell Q2 session** — deferred from Phase 1; can be ingested and resolved after Phase 2 validates the pipeline.
- **Additional cases beyond Obergefell** — pipeline supports them; not in Phase 2 scope.

</deferred>

---

*Phase: 2-Speaker Resolution*
*Context gathered: 2026-06-12*
