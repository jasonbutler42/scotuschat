# Phase 29: Historical Corpus Import - Research

**Researched:** 2026-07-09
**Domain:** Bulk offline data import (Python/SQLAlchemy/Alembic) from a third-party research corpus into an existing chat-transcript schema
**Confidence:** HIGH (codebase patterns, schema, migration conventions), MEDIUM (ConvoKit ecosystem facts — cross-checked against official docs), LOW (exact CSV name-formatting reconciliation — flagged as open question)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Guiding principle:** Where the corpus gives us information our current schema/UI has no rendering policy for yet (stage directions, sentence/paragraph boundaries), the repeated decision was: preserve the data losslessly now, defer the display/rendering decision to a future phase.

**Justice Roster Prerequisite (absorbs backlog Phase 999.10)**
- D-01: Fold Phase 999.10 (bulk justice CSV import) into this phase as step zero — not a separate phase that must land first.
- D-02: Dedup match strategy for justices against the 13 already-seeded Person rows: exact `Person.full_name` string match (same precedent as `seed_aliases.py`) — not structured first/middle/last/suffix comparison.
- D-03: The 13 Person rows already seeded by `pipeline/commands/seed_aliases.py` (pre-Phase-22 model: no `court_tenures`, no `is_justice`, uses old `role_id`) get upgraded in place — matched by name, then backfilled with `is_justice=true` and their `court_tenures` row(s) from the CSV. Not left as-is.
- D-04: Justices in both CSV sections (Rehnquist, Rutledge — elevated justices) get both `court_tenures` rows auto-created, not flagged for manual review.
- D-05 (verified): CSV `Party` column values map cleanly onto Phase 27 D-16's curated `appointing_president_party` dropdown. No value-mapping work needed.

**Rollout / Publish Status / Batching**
- D-06: Imported arguments land as `draft` status (not auto-published).
- D-07: Import is staged with checkpoints, batched by October Term (not one shot for the whole corpus).
- D-08: Import is resumable/idempotent — check-before-insert per argument (matches `seed_aliases.py`).
- D-09: Each imported argument gets real `pipeline_runs` rows (`strategy="convokit_import"`) — `Utterance.pipeline_run_id` is NOT NULL regardless, so this is the audit trail.

**October Term Sourcing**
- D-15: `Case.term_year` = `cases.jsonl`'s `"year"` field, taken directly — never derived from `argued_date`'s calendar year (SCOTUS terms span the Oct/Dec calendar boundary).

**External ID Preservation (new schema addition)**
- D-10: Add nullable columns via new Alembic migration: `Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id`.
- D-11: `Person.oyez_speaker_id` becomes the primary re-run match key for corpus-sourced people; falls back to `full_name` only when no ID is stored yet.

**Advocate Identity QA**
- D-12: No automated QA gate on advocate name-matching per batch — import everything, relying on D-06's draft-status as the review gate.
- D-13: Advocate dedup against pre-existing manually-entered Person rows uses the same exact `full_name` string match as D-02.
- D-14: Print a per-batch summary report at the end of each term/batch run.

**Stage Directions**
- D-16: Split stage directions into separate `Utterance` rows (`is_stage_direction=true`, `raw_speaker_label=None`) at import time.
- D-17: Marker detection uses a curated vocabulary match (`Inaudible`, `Laughter`/`Laughs`/`Laugh`, `Voice Overlap`, `Recess`, `Luncheon Recess`, `Cross Talk` — case-insensitive, typo-tolerant) inside either `[brackets]` or `(parens)` — not a blind bracket/paren regex. Parens cannot be skipped (37,883 `(Inaudible)` vs 6,054 `[Inaudible]` occurrences).

**Multi-Sentence Utterance / Paragraph Handling**
- D-18: Store each ConvoKit "utterance" as one `Utterance` row, with `\n`-delimited sentence/segment boundaries preserved verbatim inside `Text` — not collapsed to spaces, not pre-split into multiple rows. Bubble-splitting granularity explicitly deferred, not resolved.

**Consolidated Docket Companions**
- D-19: Accept lead-docket-only for this phase (corpus/Oyez only track the lead docket).

**Source File Handling**
- D-20: Copy the needed source files into the project repo (e.g. under `/data`) before the import command runs.
- D-21: Only copy `utterances.jsonl` (900MB), `conversations.json` (3.8MB), `speakers.json` (0.6MB), `cases.jsonl` (13MB), and the justices tenure CSV. Do NOT copy `info.arcs.jsonl` (1.2GB), `info.parsed.jsonl` (5.8GB), `info.tokens.jsonl` (0.5GB).

**Attribution / Licensing**
- D-22: Attribution appears in three places: public footer/about, per-argument note on corpus-sourced arguments, codebase/README.
- D-23: Credit Oyez.org, Cornell ConvoKit, and SCDB — even though SCDB's vote/outcome data is excluded from import.
- D-24 (verified): Oyez.org's oral-argument transcripts/audio are licensed CC BY-NC 4.0. ConvoKit requests two academic citations (Danescu-Niculescu-Mizil et al. WWW 2012; Chang et al. SIGDIAL 2020).
- D-25 (project-level constraint, already added to PROJECT.md): Oyez's NonCommercial license creates tension with PROJECT.md's monetization stance — flagged, not resolved.
- D-26: Build the dedicated Attributions/License page in this phase (small, static).

### Claude's Discretion
- Exact wording/placement of the per-argument attribution note (D-22).
- Exact per-batch summary report format (D-14) — console output shape, exact fields.
- Exact `.planning/ROADMAP.md` bookkeeping for marking Phase 999.10 superseded/absorbed (D-01) — mechanical cleanup.

### Deferred Ideas (OUT OF SCOPE)
- Public-facing browse-by-October-Term navigation.
- Outbound linking to oyez.org case/justice pages using `oyez_case_id`/`oyez_speaker_id`.
- Public argument-page toggle between inline-merged and split-out stage-direction rendering.
- Bubble-splitting granularity for multi-sentence utterances (one bubble per `\n` boundary vs. coarser grouping) — a future phase must resolve this before any paragraph-splitting rendering ships.
- Consolidated-docket companion sourcing (e.g. Obergefell's 14-562/571/574).
- "Edit affordance on utterances and speaker popover" todo — explicitly reviewed and declined for this phase (unrelated public-UI feature).
</user_constraints>

## Summary

Phase 29 is ~90% backend/pipeline work (a one-time, resumable, term-batched bulk-import CLI command) and ~10% frontend (a static Attributions page + a one-line per-argument note, both already fully specified in `29-UI-SPEC.md`). The target schema already exists and needs only 3 new nullable columns; no structural schema changes are needed beyond that plus the justice-roster upgrade-in-place migration data-work.

The critical technical finding is that the Cornell ConvoKit **pip package's `Corpus.load()` should NOT be used** — it expects `corpus.json` and `index.json` files that ConvoKit itself generates via `dump()`, neither of which exist in the raw `supreme-corpus` download this project has copies of. The correct approach is to parse `utterances.jsonl`, `conversations.json`, and `speakers.json` directly with the Python stdlib `json` module (streaming line-by-line for the 900MB `utterances.jsonl`), skipping the `convokit` package as a runtime dependency entirely. `cases.jsonl` and the justices CSV are not ConvoKit files at all and were always going to be hand-parsed.

The second critical finding is a **repo-size trap in D-20's "copy into project repo"**: GitHub hard-blocks any single file over 100 MiB (confirmed via GitHub's own docs) and warns above 50 MiB. `utterances.jsonl` at 900MB will be rejected outright if `git add`-ed. The existing project convention already solves this correctly for PDFs (`data/pdfs/*.pdf` is gitignored; only `data/pdfs/.gitkeep` is tracked) — the same pattern (a new `data/corpus/` directory, tracked via `.gitkeep`, large source files gitignored) must be applied here. "Copy into the repo" should be read as "copy into the project's local filesystem tree" for reproducibility of *running the import*, not "commit to git."

Everything else is a direct extension of existing, well-established codebase patterns: `pipeline/db.py:get_session()` (reuse as-is), `pipeline/commands/seed_aliases.py`'s check-before-insert idempotency (reuse and extend), `pipeline/commands/ingest.py`'s `_derive_slug()` and `docket_number_norm` helpers (reuse as-is), and hand-written Alembic migrations following the exact structure of migrations 0013/0016 (simple nullable `ADD COLUMN`, no backfill).

**Primary recommendation:** Parse the corpus files directly with stdlib `json`/`csv` (no `convokit` package dependency), add `python-dateutil` for date parsing, build one new `import-convokit --term`/`--term-range` argparse subcommand that reuses `get_session()` and the seed_aliases check-before-insert pattern, and gitignore the large source files under a new `data/corpus/` directory exactly like `data/pdfs/`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Justice CSV import (roster upgrade) | Pipeline CLI | Database | One-time data-mutation script; no HTTP surface (CLAUDE.md: pipeline is offline only) |
| Corpus JSONL/JSON parsing | Pipeline CLI | — | Pure Python file I/O; no framework needed |
| Bulk import orchestration (batching, resumability) | Pipeline CLI | Database | New argparse subcommand under `pipeline/__main__.py`, same tier as `ingest`/`parse`/`resolve` |
| Schema changes (3 new nullable columns) | Database | — | Alembic hand-written migration; sole DDL authority per CLAUDE.md |
| Draft-status review gate | Database + API/Backend | Admin UI (existing, reused) | Existing publish/unpublish machinery (Phase 26) requires zero new code — arguments simply land at `status=draft` |
| Attributions/License static page | Frontend (SvelteKit) | — | New static route, no server load function required |
| Per-argument attribution note | Frontend Server (SSR) | Frontend (Browser) | Visibility condition (`oyez_transcript_id IS NOT NULL`) must be resolved server-side in `+page.server.ts`, matching Architecture Rule 2 (FASTAPI_BASE_URL server-only) |
| Batch summary reporting | Pipeline CLI | — | `print()` to console/stdout; no persistence requirement beyond the `pipeline_runs` audit trail (D-09) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.12 (bundled) | Parse `conversations.json`, `speakers.json`, and stream `utterances.jsonl` line-by-line | No dependency needed; `json.loads()` per-line on JSONL is the standard streaming pattern — avoids loading 900MB into memory [VERIFIED: npm registry N/A — stdlib] |
| Python stdlib `csv` | 3.12 (bundled) | Parse the 126-row justices tenure CSV | Already used implicitly across the codebase's Python tooling conventions; no need for pandas for a 126-row file |
| `sqlalchemy` (async) | already 2.0+ pinned in `requirements.txt` | ORM writes to Case/Argument/Person/CourtTenure/Utterance/PipelineRun | Existing project stack — no change |
| `alembic` | already 1.13+ pinned | New migration for 3 nullable columns | Sole DDL authority per CLAUDE.md — no change |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dateutil` | 2.9.0.post0 (latest on PyPI, confirmed via `pip index versions`) | Parse `cases.jsonl`'s embedded date strings (e.g. `"Oral Argument - November 15, 1955"`) and CSV date columns without hand-writing multiple `strptime` format strings | Not currently a project dependency — must be added to `requirements.txt`. `dateutil.parser.parse(text, fuzzy=True)` handles free-text-embedded dates; this is the standard, well-known approach and is safer than hand-rolled regex date extraction given the corpus's date-string variability |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `json` streaming | `convokit` pip package's `Corpus.load()` | Rejected — requires `corpus.json`/`index.json` that don't exist in the raw download (D-20/D-21 only copies 3 of ConvoKit's 5 expected files); would force either fabricating those 2 files or restructuring the copied directory to satisfy ConvoKit's loader, adding a real dependency and an unnecessary abstraction layer for a one-time linear read |
| `python-dateutil` | Hand-written `datetime.strptime` with multiple format strings | Viable if the corpus's date strings turn out to follow exactly one consistent format after inspection — but `dateutil` handles the fuzzy "Oral Argument - November 15, 1955" prefix-stripping case for free and is a single well-known dependency; recommended default |
| stdlib `json` | `ijson` (true incremental/streaming JSON parser) | Not needed — `utterances.jsonl` is JSON-Lines (one JSON object per line), so `for line in f: json.loads(line)` already streams without loading the whole file; `ijson` would only be needed if the file were one giant JSON array/object, which it is not |

**Installation:**
```bash
pip install python-dateutil
# then add "python-dateutil>=2.9" to requirements.txt
```

**Version verification:** `pip index versions python-dateutil` confirmed `2.9.0.post0` as latest (also `2.9.0`, `2.8.2`, ... going back to 1.4). No other new runtime dependency is required — `convokit` is deliberately NOT added.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| python-dateutil | PyPI | published metadata dated 2024-03-01 (2.9.0.post0); package itself has existed since ~2003 | Unknown to the legitimacy-check tool (no PyPI download-count signal available) | github.com/dateutil/dateutil | SUS (reason: `unknown-downloads`) | Approved with note — see below |

**Note on the SUS verdict:** `python-dateutil` is a foundational, extremely widely-used Python package (a transitive dependency of pandas, matplotlib, botocore, and thousands of others — `botocore` itself, already vendored in this repo's `data/pgsql/pgAdmin 4` bundle, depends on it). The `SUS` verdict here is driven entirely by the checker's `unknown-downloads` signal (it has no PyPI download-stats source configured), not by any genuine legitimacy concern — it has a real GitHub source repo, is not newly published, and is not deprecated. Per protocol this is still flagged rather than silently waved through: **the planner should add a lightweight `checkpoint:human-verify` step before `pip install python-dateutil`** (a one-line sanity check: confirm the package name and PyPI page match `github.com/dateutil/dateutil` before installing), but this is a formality given the package's ubiquity, not a substantive risk.

**Packages removed due to `[SLOP]` verdict:** none.
**Packages flagged as suspicious `[SUS]`:** `python-dateutil` (see note above — low actual risk, checkpoint is a formality).

*The `convokit` pip package itself was considered but is explicitly NOT recommended for use (see Standard Stack / Alternatives Considered) — it was not run through the legitimacy checker since the research recommendation is not to install it.*

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md entries exist yet for Phase 29 (it sits outside the v1.5 requirement set). Recommended requirement codes for the planner to add to REQUIREMENTS.md under a new "Historical Corpus Import" section:

| ID | Description | Research Support |
|----|-------------|------------------|
| CORPUS-01 | Bulk-import all historical justices from the tenure CSV; dedup by exact `full_name` match against the 13 existing seed_aliases Person rows; upgrade those 13 rows in place (`is_justice=true`, `court_tenures` backfill); auto-create both tenure rows for elevated justices (Rehnquist, Rutledge) | D-01–D-05; `seed_aliases.py` upgrade analysis (Architecture Patterns, Common Pitfalls below) |
| CORPUS-02 | Alembic migration adding nullable `Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id` | D-10; migration convention confirmed via migrations 0013/0016 |
| CORPUS-03 | New `import-convokit` pipeline CLI subcommand: parses corpus files directly (no `convokit` package), staged/batched by October Term via `--term`/`--term-range`, resumable/idempotent (check-before-insert per argument), writes real `pipeline_runs` rows (`strategy="convokit_import"`), lands arguments at `status=draft` | D-06–D-09, D-15, D-19; Architecture Patterns section |
| CORPUS-04 | Source file handling: copy the 5 needed files into the repo's local filesystem under a new gitignored `data/corpus/` directory (mirroring `data/pdfs/` convention); explicitly exclude the 3 NLP-annotation files | D-20, D-21; Common Pitfalls (GitHub 100MB limit) |
| CORPUS-05 | Advocate/bench speaker identity resolution: `oyez_speaker_id` as primary re-run match key, `full_name` exact-match fallback; import everything with no automated QA gate; apolitical field stripping (never persist `win_side`/`votes_side`/`scdb_docket_id`) | D-11–D-13; Common Pitfalls (apolitical stripping) |
| CORPUS-06 | Stage-direction detection and row-splitting: curated vocabulary match (typo-tolerant) inside `[brackets]` or `(parens)`, split into separate `Utterance` rows with `is_stage_direction=true` | D-16, D-17 |
| CORPUS-07 | Multi-sentence utterance storage: one `Utterance` row per ConvoKit turn, `\n`-delimited segment boundaries preserved verbatim in `Text` | D-18; confirmed current `ChatBubble.svelte` collapses `\n` harmlessly (see Common Pitfalls) |
| CORPUS-08 | Per-batch summary report printed at the end of each term/batch run (counts created/skipped/flagged) | D-14 |
| CORPUS-09 | Attributions/License static page (`/attributions`) crediting Oyez.org, Cornell ConvoKit, and SCDB; states CC BY-NC 4.0 license fact | D-22–D-26; fully specified in `29-UI-SPEC.md` |
| CORPUS-10 | Per-argument attribution note visible only on corpus-sourced arguments, linking to the Attributions page | D-22; `29-UI-SPEC.md` |
| CORPUS-11 | Roadmap bookkeeping: mark Phase 999.10 superseded/absorbed in `.planning/ROADMAP.md` | D-01 (Claude's Discretion) |
</phase_requirements>

## Architecture Patterns

### System Architecture Diagram

```
CSV file (justices)          supreme-corpus/                    cases.jsonl
      |                      {utterances.jsonl (streamed),            |
      |                       conversations.json,                     |
      |                       speakers.json}                          |
      |                            |                                  |
      v                            v                                  v
 [Step 0: justice roster    [Step N: term-batch loop]           (joined by
  upgrade — one-time,       for term in range(--term or         case_id / docket
  runs first]                --term-range):                     during Step N]
      |                        1. Filter conversations.json
      |                           by case_id prefix "{term}_"
      |                        2. For each conversation:
      |                           - Look up case metadata
      |                             from cases.jsonl (by
      |                             matching docket/case_id)
      |                           - check-before-insert Case
      |                             (docket_number, term_year
      |                             from cases.jsonl "year")
      |                           - check-before-insert Argument
      |                             (status=draft, oyez_transcript_id
      |                             = conversation_id)
      |                           - create PipelineRun row
      |                             (strategy="convokit_import")
      |                           - Look up speaker records from
      |                             speakers.json; resolve/create
      |                             Person rows (oyez_speaker_id
      |                             primary key, full_name fallback)
      |                           - Stream matching rows out of
      |                             utterances.jsonl (by
      |                             conversation_id), in sequence:
      |                               * detect stage-direction
      |                                 markers -> split row
      |                               * else -> one Utterance row,
      |                                 \n-joined text preserved
      |                        3. Print per-batch summary (D-14)
      v                            v
 court_tenures / people      cases / arguments / case_arguments /
 (upgraded + new rows)       argument_participants / utterances /
                             pipeline_runs
                                     |
                                     v
                          (existing) Admin UI: operator reviews
                          draft arguments via existing publish
                          flow — NO new admin screens this phase
                                     |
                                     v
                          Public site: /attributions (new static
                          page) + per-argument attribution note
                          (new, gated on oyez_transcript_id != null)
```

### Recommended Project Structure
```
pipeline/
├── commands/
│   ├── import_justices_csv.py   # NEW — Step 0, absorbs backlog 999.10 (D-01)
│   ├── import_convokit.py       # NEW — the term-batched bulk importer (D-07)
│   └── seed_aliases.py          # UNCHANGED (still seeds current-era aliases at fresh-DB setup)
├── corpus/                      # NEW — shared parsing helpers, not a "commands" module
│   ├── loader.py                # streaming JSONL reader, conversations/speakers loaders
│   ├── stage_directions.py      # curated-vocabulary marker detection (D-17)
│   └── apolitical.py            # explicit allowlist copy helpers (never persists win_side/votes_side/scdb_docket_id)
├── db.py                        # UNCHANGED — reuse get_session() as-is
└── __main__.py                  # add 2 new subparsers: import-justices, import-convokit

data/
└── corpus/                      # NEW — gitignored except .gitkeep, mirrors data/pdfs/ convention
    ├── .gitkeep
    ├── utterances.jsonl          # gitignored (900MB)
    ├── conversations.json        # gitignored (3.8MB) — small enough it COULD be committed,
    ├── speakers.json              # gitignored (0.6MB)   but consistency with the 900MB file argues
    ├── cases.jsonl                # gitignored (13MB)    for gitignoring the whole directory's contents
    └── justices_tenure.csv        # gitignored

alembic/versions/
└── 00XX_add_oyez_external_ids.py # NEW — 3 nullable ADD COLUMN, no backfill (D-10)

app/src/routes/
└── attributions/
    └── +page.svelte              # NEW — static Attributions page (29-UI-SPEC.md)
```

### Pattern 1: Idempotent check-before-insert (extend `seed_aliases.py`'s pattern)
**What:** `select()` → `scalar_one_or_none()` → skip-or-create-and-flush, for every entity type touched (Case, Argument, Person, CourtTenure, ArgumentParticipant, Utterance).
**When to use:** Every write in both the justice-CSV importer and the corpus importer — this is what makes D-08's resumability requirement work for free (a crashed/interrupted batch can simply be re-run).
**Example (existing pattern, `pipeline/commands/seed_aliases.py`):**
```python
# Source: pipeline/commands/seed_aliases.py (existing codebase pattern to replicate)
result = await session.execute(
    select(Person).where(Person.full_name == full_name)
)
existing_person = result.scalar_one_or_none()

if existing_person is not None:
    person_map[full_name] = existing_person
else:
    new_person = Person(full_name=full_name, role_id=role.id)
    session.add(new_person)
    await session.flush()
    person_map[full_name] = new_person
```
**For the corpus importer, the match key changes per D-11** — check `oyez_speaker_id` first, fall back to `full_name`:
```python
result = await session.execute(
    select(Person).where(Person.oyez_speaker_id == speaker_id)
)
existing = result.scalar_one_or_none()
if existing is None:
    result = await session.execute(
        select(Person).where(Person.full_name == full_name)
    )
    existing = result.scalar_one_or_none()
```

### Pattern 2: Reuse `_derive_slug()` and docket normalization from `ingest.py`
**What:** `pipeline/commands/ingest.py` already contains a battle-tested slug-derivation function and the exact `docket_number_norm` convention this phase's Case rows must also use.
**When to use:** Every new Case row created by the corpus importer.
**Example:**
```python
# Source: pipeline/commands/ingest.py:85-101, 383-389 (existing codebase pattern to reuse verbatim)
def _derive_slug(case_name: str) -> str:
    slug = case_name.lower()
    slug = slug.replace("'", "")
    slug = slug.replace("&", "and")
    slug = slug.replace("/", "-")
    slug = slug.replace("(", "").replace(")", "")
    slug = slug.replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")

new_case = Case(
    docket_number=docket,
    docket_number_norm=docket.replace("-", ""),
    case_name=effective_case_name,
    term_year=term_year,          # D-15: from cases.jsonl "year" field directly
    slug=case_slug,
    oyez_case_id=oyez_case_id,    # NEW column (D-10)
)
```
**Import this function** from `pipeline.commands.ingest` (it's a private-by-convention `_derive_slug` — the planner should decide whether to import it directly or promote it to a shared `pipeline/slugs.py` module; either is reasonable, flagged as a planner discretion point, not a blocking decision).

### Pattern 3: Streaming JSONL read (new — 900MB file)
**What:** Read `utterances.jsonl` one line at a time; do not call `.readlines()` or `json.load()` on the whole file.
**When to use:** Any pass over `utterances.jsonl`. Because the importer batches by term, and `utterances.jsonl` has no term/case ordering guarantee documented, the simplest correct approach is either (a) one full streaming pass per term-batch filtering by `conversation_id` membership in that term's conversation set, or (b) one single streaming pass building an index of `conversation_id -> [utterance dicts]` for the requested term range only, held in memory only for the terms currently being imported (not the whole file). Given 7,817 total conversations across 65 terms, a single term's utterance subset is small even though the full file is 900MB — a per-term filtered streaming pass (option a) is simplest and matches D-07's batch-oriented design.
```python
# Standard streaming JSONL pattern — stdlib only, no new dependency
import json
from pathlib import Path

def iter_utterances_for_conversations(path: Path, wanted_conversation_ids: set[str]):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["conversation_id"] in wanted_conversation_ids:
                yield row
```
**Note on Windows constraint:** The Windows `ProactorEventLoop` guard in `pipeline/__main__.py` (`asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`) exists solely because `asyncpg` is incompatible with the default Windows event loop — it has no bearing on synchronous file I/O. Reading `utterances.jsonl` with plain `open()`/`for line in f` is unaffected by this guard either way; **confirmed, not a constraint on the file-reading approach.**

### Pattern 4: Alembic migration for the 3 new nullable columns (D-10)
**What:** Simple, hand-written `ADD COLUMN ... NULLABLE`, no backfill, matching migrations 0013 and 0016 exactly in style.
**When to use:** This phase's schema migration.
```python
# Source: pattern replicated from alembic/versions/0016_add_person_birthdate.py
"""Add oyez_case_id, oyez_transcript_id, oyez_speaker_id — external ID columns for ConvoKit/Oyez-sourced records.

Revision ID: 00XX
Revises: <current head>
Create Date: 2026-07-XX

Adds:
  - cases.oyez_case_id VARCHAR NULL           (e.g. "1955_71")
  - arguments.oyez_transcript_id VARCHAR NULL (e.g. "13127" — ConvoKit conversation_id)
  - people.oyez_speaker_id VARCHAR NULL       (e.g. "j__earl_warren")

No backfill — all existing rows remain NULL. Only rows created by the new
import-convokit command populate these columns going forward.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "00XX"
down_revision: Union[str, None] = "<current head>"  # confirm actual head at plan time
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("oyez_case_id", sa.String(50), nullable=True))
    op.add_column("arguments", sa.Column("oyez_transcript_id", sa.String(50), nullable=True))
    op.add_column("people", sa.Column("oyez_speaker_id", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("people", "oyez_speaker_id")
    op.drop_column("arguments", "oyez_transcript_id")
    op.drop_column("cases", "oyez_case_id")
```
**Planner must confirm the actual current Alembic head** (run `alembic heads` at plan/execute time) before hardcoding `down_revision` — migration 0016 is the newest one found during this research, but a Phase 28 migration may land first depending on execution order.

### Anti-Patterns to Avoid
- **Using the `convokit` pip package's `Corpus.load()`:** requires `corpus.json`/`index.json` that don't exist in the copied files (see Summary). Don't add it as a dependency.
- **Loading `utterances.jsonl` fully into memory** (`json.load()` on the whole 900MB file, or `.readlines()` then parsing): will consume gigabytes of RAM unnecessarily. Stream line-by-line.
- **Passing the raw `conversations.json`/`cases.jsonl` dicts directly into ORM model constructors via `**row`:** this is the single most dangerous anti-pattern in this phase — both source files carry `win_side`/`votes_side`/`scdb_docket_id` (and `cases.jsonl` also carries `win_side_detail`/`votes`/`votes_detail`) that must NEVER be persisted (apolitical constraint, hard project rule). Always build an explicit allowlist dict of only the fields being written; never `Model(**source_dict)`.
- **Committing `data/corpus/utterances.jsonl` to git:** GitHub blocks pushes of files over 100MiB outright (confirmed via GitHub's own docs). Gitignore it, matching `data/pdfs/*.pdf`'s existing pattern.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing free-text embedded dates (`"Oral Argument - November 15, 1955"`) | Custom regex extracting month/day/year | `dateutil.parser.parse(text, fuzzy=True)` | Handles the "prefix text before the actual date" case out of the box; hand-rolled regex is a maintenance burden for a one-time script that still needs to be correct across 7,748 rows |
| Streaming very large JSONL files | Custom buffered chunk-reader | Plain `for line in open(path): json.loads(line)` | Python's built-in file iteration already reads lazily line-by-line; no library needed, and it's the simplest possible correct implementation |
| ConvoKit corpus object model (Corpus/Conversation/Speaker/Utterance Python classes) | N/A — not recommended to build a parallel object model | Direct `dict` access from `json.loads()` results | The importer only needs to read 3 flat JSON structures once and translate them into this project's own SQLAlchemy models — introducing ConvoKit's own object model (or a hand-rolled equivalent) adds an unnecessary translation layer for a single linear import pass |

**Key insight:** This phase's "hand-rolling" risk is not in choosing the wrong library — it's in accidentally re-deriving logic that already exists in this codebase (slug derivation, docket normalization, idempotency checking) instead of importing/reusing it from `ingest.py` and `seed_aliases.py`.

## Runtime State Inventory

> Included because D-01/D-02/D-03 require "upgrading" the 13 existing seed_aliases Person rows in place — this is real migration-adjacent data work, not a greenfield insert.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 13 `Person` rows in PostgreSQL created by `pipeline/commands/seed_aliases.py` (pre-Phase-22 model: `role_id` set, `is_justice` defaults to `false` server-side, no `court_tenures` rows at all). Also: `Role` rows ("Chief Justice", "Associate Justice") and `SpeakerAlias` rows tied to those 13 people — both must be left untouched by the upgrade (D-03 only adds `is_justice`/`court_tenures`, it does not touch `role_id` or aliases). | **Data migration** (not a code-only change): for each of the 13 names, `UPDATE people SET is_justice = true WHERE full_name = ?` and `INSERT INTO court_tenures (...)` from the CSV rows matching that name. This is application-level data work done by the new `import_justices_csv.py` script itself at runtime (via the ORM, inside the same idempotent check-before-insert loop) — not a one-off Alembic data migration, since it depends on CSV content the migration framework shouldn't embed. |
| Live service config | None — this project has no live external service configuration (no n8n workflows, no Datadog dashboards, no Cloudflare Tunnel names) that reference justice names, "seed_aliases," or corpus terms. | None. |
| OS-registered state | None — the pipeline runs as a one-off CLI invocation (`python -m pipeline import-convokit ...`), not a registered service, scheduled task, or daemon. No Windows Task Scheduler / pm2 / launchd entries reference this phase's work. | None. |
| Secrets/env vars | None new. The importer reuses `DATABASE_URL` (already required by `pipeline/db.py`) and needs no new secret or API key — everything is sourced from local files, not a live API. | None. |
| Build artifacts | None — no compiled binaries or `.egg-info` directories are affected by adding 2 new pipeline command modules; this is plain Python source added to an already-installed package (`pipeline/` is imported via `pythonpath = .` in `pytest.ini`, not pip-installed as a package). | None. |

**Nothing found in 4 of 5 categories** — the only real runtime-state item this phase touches is the 13 existing `Person`/soon-`CourtTenure` rows in PostgreSQL, which requires an explicit application-level upgrade pass (not a schema migration, not a code-only rename) at the start of the justice-import step.

## Common Pitfalls

### Pitfall 1: `full_name` string-format mismatch breaks D-02/D-03's exact-match dedup
**What goes wrong:** The 13 existing seeded justices use a specific full-name format (e.g. `"John G. Roberts, Jr."`, `"Samuel A. Alito, Jr."`, `"Clarence Thomas"` — first name, middle initial + period, last name, comma + suffix when present). The CSV has separate `First Name` / `Middle Name or Initial` / `Last Name` / `Suffix` columns. If the importer's name-reconstruction logic doesn't produce byte-identical strings to what `seed_aliases.py` originally wrote, D-02's "exact string match" dedup silently fails and creates duplicate Person rows for the same justice instead of upgrading the existing one.
**Why it happens:** String concatenation from structured parts is fragile — punctuation placement (`"Jr."` vs `", Jr."`), whether a middle initial gets a trailing period, and whether missing-middle-name cases omit an extra space are all easy off-by-one-character bugs.
**How to avoid:** Before writing the reconstruction function, print out `full_name` for all 13 existing seeded rows and manually derive the exact concatenation rule that reproduces every one of them from CSV-shaped parts, with unit tests asserting the reconstructed string for each of the 13 names matches the seed_aliases.py literal. Treat any justice name that doesn't reconstruct identically as a manual-override case, not a silent duplicate.
**Warning signs:** After a test run, `SELECT full_name, COUNT(*) FROM people WHERE is_justice GROUP BY full_name HAVING COUNT(*) > 1` — any row with count > 1 for one of the original 13 names indicates the reconstruction logic drifted.

### Pitfall 2: Passing forbidden apolitical fields straight through via dict unpacking
**What goes wrong:** `conversations.json` carries `win_side`/`votes_side`, and `cases.jsonl` carries `win_side`/`win_side_detail`/`votes`/`votes_detail`/`votes_side`/`scdb_docket_id`. If any code path does `Argument(**conversation_row)` or logs/persists the raw source dict anywhere (including in `cover_metadata` JSONB, which is otherwise a reasonable place to stash "extra extracted data"), these forbidden fields leak into the database — a direct violation of the apolitical framing hard constraint.
**Why it happens:** JSONB columns like `Argument.cover_metadata` are tempting dumping grounds for "everything else we extracted" — but this phase's source data specifically contains outcome/vote data that must never be stored anywhere, not even in a metadata blob.
**How to avoid:** Write an explicit allowlist function (`pipeline/corpus/apolitical.py` suggested) that extracts only the named fields being persisted from each source row; never store the raw parsed dict anywhere, including debug logging of full rows to files that might get committed.
**Warning signs:** Any `**row` or `row.copy()` pattern touching a `conversations.json` or `cases.jsonl` dict; any JSONB column write that isn't an explicit field-by-field dict literal.

### Pitfall 3: GitHub's 100MB hard file-size limit vs. D-20's "copy into the repo"
**What goes wrong:** `utterances.jsonl` at 900MB will be rejected outright by GitHub if `git add`-ed and pushed (confirmed via GitHub's own docs: hard block above 100 MiB, warning above 50 MiB). D-20 says "copy the needed source files into the project repo (e.g. under `/data`)" for reproducibility — this must mean "onto the local filesystem tree that lives inside the repo directory," not "commit to git," or the push will fail.
**Why it happens:** "Repo" is ambiguous between "the git-tracked history" and "the project's root directory on disk" — the existing `data/pdfs/` convention already resolves this ambiguity correctly (directory tracked via `.gitkeep`, actual PDF files gitignored) but a new contributor could miss that precedent and `git add -A` the whole `data/corpus/` directory by habit.
**How to avoid:** Add a `.gitignore` entry for the new `data/corpus/` directory's file contents (mirroring `data/pdfs/*.pdf`), and track only a `.gitkeep` placeholder. Document in the import command's docstring/README where an operator must obtain and place the 5 source files locally before running the command (since they won't come from git).
**Warning signs:** `git status` showing `utterances.jsonl` as a new untracked or staged file; any CI/deploy step that assumes the corpus files exist purely because "they're checked into git."

### Pitfall 4: `ChatBubble.svelte`'s `<p>` tag and embedded `\n` — confirmed safe, but worth a smoke-test line item
**What goes wrong (verified NOT to happen, documented so the planner doesn't need to re-derive it):** D-18 stores `\n`-delimited sentence boundaries verbatim inside `Utterance.Text`. Read `app/src/lib/components/ChatBubble.svelte:95-105` — the utterance text is rendered inside a plain `<p>` element with no `white-space` CSS property set anywhere in that component (grepped the codebase's `white-space` usages; none apply to `ChatBubble.svelte`). The browser default for `<p>` is `white-space: normal`, which collapses all whitespace including `\n` into a single space at render time. **Confirmed: the current template does NOT display literal `\n` characters and does NOT break visually** — it silently (and harmlessly) collapses the sentence-boundary information at display time, exactly matching the "acceptable for now, rendering policy deferred" outcome the guiding principle calls for. No code change is required in `ChatBubble.svelte` this phase.
**Why flag it anyway:** This confirms there is no "don't break existing display" acceptance criterion needed this phase — but the planner should still add a one-line smoke-test/manual-check item confirming a corpus-imported argument's multi-sentence utterances render as a single flowing line with no visible `\n` or double-spacing artifacts, since this was verified by static code reading, not by rendering a real imported argument in a browser.
**Warning signs:** If a future refactor of `ChatBubble.svelte` adds `white-space: pre-line` or similar without also resolving the deferred bubble-splitting decision, `\n` boundaries would start rendering as line breaks unintentionally.

### Pitfall 5: October Term batching requires joining across 3 differently-keyed files
**What goes wrong:** `conversations.json`'s `case_id` format is `<term>_<docket>` (e.g. `"1955_71"`), which conveniently makes per-term filtering a simple string-prefix check — but `cases.jsonl` case metadata (title, decided_date, citation) must be joined in separately by matching docket/case_id, and `speakers.json` is a flat global dict (not scoped by term) that must be looked up per-speaker as advocates/justices are encountered within a term's conversations. Assuming any one file alone is sufficient for a term batch will produce incomplete records.
**Why it happens:** The three files have three different natural keys (`case_id` prefix, docket number, speaker slug) and none of them is a strict foreign key into the others without light data massaging.
**How to avoid:** Build the per-term import as: (1) filter `conversations.json` entries by `case_id.startswith(f"{term}_")`; (2) for each, resolve the matching `cases.jsonl` row (join key: docket number embedded in `case_id`, cross-checked against `cases.jsonl`'s own docket field); (3) resolve each advocate/justice via `speakers.json` by the speaker id embedded in `conversations.json`'s `advocates` dict / `utterances.jsonl`'s `speaker` field.
**Warning signs:** Arguments created with `case_name = None` or missing `oyez_case_id` for terms where `cases.jsonl` join failed to match — this should surface in D-14's per-batch summary report as a flagged/skipped count, not fail silently.

## Code Examples

### Streaming JSONL read with a term-scoped conversation-id filter
```python
# Pattern verified via stdlib docs — no external dependency
import json
from pathlib import Path

def load_conversations_for_term(conversations_path: Path, term: int) -> dict:
    """Filter conversations.json to just this term's entries (case_id = '<term>_<docket>')."""
    with conversations_path.open("r", encoding="utf-8") as f:
        all_conversations = json.load(f)  # conversations.json is 3.8MB — safe to load whole
    prefix = f"{term}_"
    return {
        cid: conv for cid, conv in all_conversations.items()
        if cid.startswith(prefix)
    }

def stream_utterances_for_conversation_ids(
    utterances_path: Path, wanted_ids: set[str]
):
    """Stream utterances.jsonl (900MB) line-by-line, yielding only matching rows."""
    with utterances_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("conversation_id") in wanted_ids:
                yield row
```

### CLI subcommand argparse pattern (`--term` / `--term-range`)
```python
# Source: pattern extends pipeline/__main__.py's existing subparser style
import_p = sub.add_parser(
    "import-convokit",
    help="Bulk-import historical arguments from the ConvoKit supreme-corpus",
    description=(
        "Import oral arguments for one term or a term range from the "
        "Cornell ConvoKit supreme-corpus dataset, bypassing PDF/LLM parsing."
    ),
)
term_group = import_p.add_mutually_exclusive_group(required=True)
term_group.add_argument("--term", type=int, help="Single October Term year, e.g. 1955")
term_group.add_argument(
    "--term-range",
    type=str,
    help="Inclusive term range, e.g. 1955-1960",
)

def _parse_term_range(value: str) -> tuple[int, int]:
    start_str, _, end_str = value.partition("-")
    start, end = int(start_str), int(end_str)
    if start > end:
        raise argparse.ArgumentTypeError(f"start term {start} is after end term {end}")
    return start, end
```

### Justice CSV row -> CourtTenure mapping
```python
# Column mapping confirmed against 29-CONTEXT.md's canonical_refs CSV column list
# and existing court_tenures schema (migration 0013)
tenure = CourtTenure(
    person_id=person.id,
    start_date=dateutil.parser.parse(row["Judicial Oath Taken"]).date(),
    end_date=(
        dateutil.parser.parse(row["Date Service Terminated"]).date()
        if row["Date Service Terminated"].strip()
        else None  # currently active — matches existing CourtTenure.end_date nullable semantics
    ),
    appointed_by=row["Appointed by"].strip() or None,
    appointing_president_party=row["Party"].strip() or None,
    # seat: CSV has no direct "seat" column; section (Chief/Associate) from
    # which the row was read is the natural source — planner to confirm
    # exact seat string convention against existing court_tenures.seat data
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| PDF download + pdfplumber + LLM corrective parse (existing pipeline, terms 2020+) | Direct bulk import from a pre-structured research corpus (this phase, terms 1955-2019) | This phase (2026-07) | Two parallel, permanently-coexisting ingestion paths for different eras — not a migration or replacement of the PDF pipeline |

**Deprecated/outdated:** Nothing in this phase deprecates existing pipeline code — `ingest`/`parse`/`resolve`/`seed-aliases` subcommands remain fully in place and continue to be the path for 2020+ terms.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | ConvoKit's `Corpus.load()` requires `corpus.json`+`index.json` in addition to the 3 files this project copies, making the `convokit` package unsuitable here | Summary, Standard Stack, Anti-Patterns | LOW — sourced from ConvoKit's own official documentation (convokit.cornell.edu), cross-checked in this session via WebSearch; if the actual pip package version behaves differently, worst case the planner discovers this at implementation time when `Corpus.load()` throws a missing-file error, which is a cheap, early, obvious failure to detect |
| A2 | Advocate side codes in `conversations.json` are exactly 0=respondent/1=petitioner/2=amicus/3=unknown | Standard Stack cross-check | LOW — matches CONTEXT.md's own D-scoping (already verified during discuss-phase via direct data scan) AND independently confirmed via ConvoKit's official Supreme Court Corpus docs page in this session |
| A3 | The exact `full_name` string-concatenation rule needed to reproduce the 13 existing seed_aliases justices from CSV name-parts is not yet derived — flagged as Pitfall 1 and Open Question 1 below, not resolved by this research | Common Pitfalls, Open Questions | MEDIUM — if the planner doesn't add an explicit reconciliation/unit-test step, silent duplicate Person rows are the likely failure mode (not a crash, so easy to miss) |
| A4 | `python-dateutil` is not currently a project dependency (confirmed via `requirements.txt`/`requirements-dev.txt` read and codebase grep for `dateutil` usage — no hits outside the unrelated bundled pgAdmin venv) | Standard Stack | LOW — directly verified by reading the actual files, not assumed |

## Open Questions

1. **Exact `full_name` reconstruction rule from CSV name-parts**
   - What we know: The 13 existing seeded justices use a specific concatenation format (e.g. `"John G. Roberts, Jr."`); the CSV provides separate First/Middle/Last/Suffix columns.
   - What's unclear: The precise punctuation/spacing rule that reproduces all 13 existing names byte-for-byte from CSV parts has not been derived in this research pass (would require pulling the actual CSV row data for all 13 names and diffing against `seed_aliases.py`'s literals).
   - Recommendation: Planner/implementer should do this diff as an early task in Plan 1, with a unit test asserting reconstruction correctness for all 13 known names before writing any insert logic — treat any mismatch as a manual override list, not a blocking redesign.

2. **`court_tenures.seat` value for CSV-imported justices**
   - What we know: The CSV has Chief/Associate sections but no explicit numbered-seat column; existing `court_tenures.seat` data (Phase 27) stores free-text like `"Associate Justice Seat 3"`.
   - What's unclear: What seat-string value the corpus/CSV-derived tenure rows should use, given no numbered-seat source data exists for historical justices in this CSV.
   - Recommendation: Use `"Chief Justice"` or `"Associate Justice"` (the section header) as the seat value for CSV-imported rows — this is consistent with the CSV's own available granularity and doesn't block Phase 999.16's future seat-representation rework, since that phase already anticipates reconciling numbered vs. non-numbered seat data.

3. **Where advocate/justice speaker matching draws its "side" for `argument_participants` when the corpus lacks a clean signal**
   - What we know: `conversations.json`'s `advocates` dict gives side per-advocate at the case level; justices are `BENCH`.
   - What's unclear: Whether every justice appearing in `utterances.jsonl` for a given conversation is guaranteed to also appear correctly in `speakers.json` with a `type` field distinguishing justice from advocate, for all 1955-2019 rows without exception.
   - Recommendation: Treat `speakers.json`'s speaker `type` field as authoritative for BENCH vs. ADVOCATE classification (not name-pattern matching); flag any speaker with an ambiguous/missing type in the per-batch summary report (D-14) rather than guessing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Pipeline CLI | ✓ | 3.12 (project-pinned) | — |
| PostgreSQL 16 + asyncpg | Database writes | ✓ | existing project stack | — |
| `python-dateutil` | Date parsing | ✗ (not yet installed) | 2.9.0.post0 available on PyPI | Hand-written `strptime` with fixed format strings if the corpus's date strings prove to follow one consistent format (unlikely to be simpler in practice) |
| Disk space for `/data/corpus/` | Source file storage | Unverified — requires ~918MB free (900+13+3.8+0.6+CSV) on the dev machine | — | None — this is a hard requirement; flag if disk space is constrained |
| Git LFS | NOT required if gitignore approach (Pitfall 3) is followed | N/A | — | If the team ever wants the 900MB file actually version-controlled, Git LFS would be the standard tool, but this research recommends gitignoring instead, consistent with `data/pdfs/` convention |

**Missing dependencies with no fallback:** none blocking — `python-dateutil` has a viable stdlib fallback if truly needed, disk space is an operator-verifiable prerequisite, not a code dependency.

**Missing dependencies with fallback:** `python-dateutil` (fallback: hand-written strptime); disk space (fallback: none — operator must free space, this is not a code-path decision).

## Security Domain

`security_enforcement` is not explicitly disabled in `.planning/config.json` — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase adds no new HTTP endpoints or auth surface — it's an offline CLI tool, consistent with CLAUDE.md's "pipeline is offline only" rule |
| V3 Session Management | No | Same as above |
| V4 Access Control | No | No new admin-UI screens or API routes; the existing publish/unpublish gate (already access-controlled) is reused unchanged for reviewing draft imports |
| V5 Input Validation | Yes | Validate `--term`/`--term-range` CLI args are well-formed integers/ranges before using them to build filenames or filter data (defense against malformed operator input, not an external attacker surface since this is operator-only offline tooling); validate that parsed JSONL/JSON rows have the expected shape (`conversation_id`, `speaker`, `text` keys present) before writing to the DB, raising a clear per-row error rather than an unhandled `KeyError` mid-batch |
| V6 Cryptography | No | No new cryptographic operations in this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Apolitical-constraint data leakage — `win_side`/`votes_side`/`scdb_docket_id` accidentally persisted via dict-unpacking or JSONB dumping of raw source rows | Information Disclosure | Explicit allowlist extraction function (never `Model(**row)`); code review checklist item specifically calling this out; consider a unit test that asserts these keys are absent from every DB write this phase produces |
| Resource exhaustion / OOM from loading the 900MB `utterances.jsonl` fully into memory | Denial of Service (of the operator's own machine, not a remote attacker — but still a real reliability risk for a batch job that must be resumable per D-08) | Streaming line-by-line reads (see Architecture Patterns Pattern 3); never `.read()`/`json.load()` the whole file |
| Malformed/unexpected row shape from a 900MB/7,748-row/9,651-row set of externally-sourced files causing a mid-batch crash that leaves partial writes | Tampering (data integrity) — not a security attack, but the reliability equivalent | Idempotent check-before-insert (Pattern 1) makes partial-batch crashes safely resumable; per-row try/except with the error surfaced in D-14's per-batch summary rather than aborting the whole batch on one bad row, IF the planner chooses that resilience level (recommended, though not explicitly locked by CONTEXT.md D-12's "import everything, no automated QA gate" — that decision is about identity-matching QA, not about crash-safety, so it doesn't preclude per-row error handling) |
| Repo/CI bloat or outright push rejection from a 900MB file entering git history | N/A (operational risk, not STRIDE) | Gitignore the large source files (Pitfall 3) |

## Sources

### Primary (HIGH confidence)
- Direct codebase reads: `pipeline/db.py`, `pipeline/commands/seed_aliases.py`, `pipeline/commands/ingest.py`, `pipeline/__main__.py`, `api/models/models.py`, `alembic/versions/0013_*.py`, `alembic/versions/0016_*.py`, `app/src/lib/components/ChatBubble.svelte`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `pytest.ini`, `.planning/config.json`, `.planning/PROJECT.md`, `.planning/ROADMAP.md` — all read in full during this research session.
- `pip index versions python-dateutil` — direct CLI verification of current PyPI version (2.9.0.post0).

### Secondary (MEDIUM confidence)
- [Data Format — ConvoKit 4.1.2 documentation](https://convokit.cornell.edu/documentation/data_format.html) — confirms `corpus.json`/`index.json` requirement for `Corpus.load()`.
- [Corpus — ConvoKit 4.1.0 documentation](https://convokit.cornell.edu/documentation/corpus.html)
- [Supreme Court Oral Arguments Corpus — ConvoKit 4.1.1 documentation](https://convokit.cornell.edu/documentation/supreme.html) — confirms advocate side codes 0/1/2/3.
- [About large files on GitHub — GitHub Docs](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) — confirms 100 MiB hard block / 50 MiB warning.
- [parser — dateutil stable documentation](https://dateutil.readthedocs.io/en/stable/parser.html) — confirms `fuzzy=True` free-text date parsing behavior.

### Tertiary (LOW confidence)
- None — all findings in this research were either directly verified against the codebase/CLI or cross-checked against official documentation.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib-only recommendation directly verified; `python-dateutil` version verified via `pip index versions`; ConvoKit-package rejection reasoning cross-checked against official docs
- Architecture: HIGH — every reusable pattern (get_session, seed_aliases idempotency, ingest.py slug/docket helpers, Alembic migration style) was read directly from the actual codebase, not inferred
- Pitfalls: HIGH for GitHub file-size limit and `\n`/ChatBubble rendering (both independently verified this session); MEDIUM for the full_name reconstruction pitfall (real risk correctly identified, but exact fix requires CSV data the researcher didn't have direct access to reconcile against the 13 literal names)

**Research date:** 2026-07-09
**Valid until:** 30 days (stable domain — stdlib Python, existing internal codebase conventions, and a static third-party dataset are all low-churn; re-verify only if the `convokit` package or GitHub's file-size policy change, which is unlikely within this window)
