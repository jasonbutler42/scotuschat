# Phase 29: Historical Corpus Import - Pattern Map

**Mapped:** 2026-07-09
**Files analyzed:** 10
**Analogs found:** 9 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pipeline/commands/import_justices_csv.py` | service (CLI command) | batch/CRUD | `pipeline/commands/seed_aliases.py` | exact (idempotency + Person/CourtTenure upgrade pattern) |
| `pipeline/commands/import_convokit.py` | service (CLI command) | batch/file-I/O + CRUD | `pipeline/commands/ingest.py` | role-match (Case/Argument/PipelineRun creation, idempotency) |
| `pipeline/corpus/loader.py` | utility | streaming file-I/O | none in codebase (new pattern) | no analog — see below |
| `pipeline/corpus/stage_directions.py` | utility | transform | none in codebase (new pattern) | no analog — see below |
| `pipeline/corpus/apolitical.py` | utility | transform | `pipeline/commands/ingest.py` (allowlist Argument() construction, lines 402-407) | partial-match (explicit-field pattern, not a dedicated allowlist module yet) |
| `pipeline/__main__.py` (modified) | route/config (argparse registration) | request-response (CLI) | itself — extend existing subparser pattern | exact |
| `alembic/versions/00XX_add_oyez_external_ids.py` | migration | transform (DDL) | `alembic/versions/0016_add_person_birthdate.py` | exact |
| `app/src/routes/attributions/+page.svelte` | component (static page) | request-response | `app/src/routes/cases/+page.svelte` (styling/header conventions) | partial-match (static content, no `+page.server.ts` needed) |
| `app/src/lib/components/ChatBubble.svelte` (modified, attribution note) | component | request-response | itself, lines 95-105 (existing `<p>` text render block) | exact |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` (modified — attribution visibility gate) | route (server load) | request-response | existing file itself (not read this pass — planner should read directly; Architecture Rule 2 requires the `oyez_transcript_id != null` check happen here, server-side) | role-match |

## Pattern Assignments

### `pipeline/commands/import_justices_csv.py` (service, batch/CRUD)

**Analog:** `pipeline/commands/seed_aliases.py` (full file read — 194 lines, small enough for one pass)

**Imports pattern** (lines 19-22):
```python
from sqlalchemy import select

from api.models.models import Person, Role, SpeakerAlias
from pipeline.db import get_session
```
For the new script, swap `SpeakerAlias` for `CourtTenure`, and add `csv`, `pathlib.Path`, `dateutil.parser`.

**Core idempotency pattern** (lines 122-158, `run_seed_aliases`):
```python
for full_name, role_name, _labels in _JUSTICES:
    result = await session.execute(
        select(Person).where(Person.full_name == full_name)
    )
    existing_person = result.scalar_one_or_none()

    if existing_person is not None:
        person_map[full_name] = existing_person
    else:
        role = role_map[role_name]
        new_person = Person(
            full_name=full_name,
            role_id=role.id,
        )
        session.add(new_person)
        await session.flush()
        person_map[full_name] = new_person
```
**Extend for D-03's "upgrade in place":** when `existing_person is not None`, this new script must ALSO set `existing_person.is_justice = True` and check-before-insert the matching `CourtTenure` row(s) (see Pitfall 1 in RESEARCH.md — exact `full_name` reconstruction from CSV parts is the fragile step; unit-test against the 13 literal names in `_JUSTICES` above before trusting the dedup).

**Docstring/module-header convention to copy** (lines 1-17): module docstring states purpose, idempotency guarantee, and `Usage: python -m pipeline <command>` — copy this shape verbatim for the new command's docstring.

**Summary-print convention** (lines 186-193):
```python
print(
    f"Done — {alias_rows_created} alias rows created "
    f"({total_labels - alias_rows_created} already existed / verified)."
)
```
Reuse this shape for D-14's per-batch summary reporting (extend with counts of arguments/utterances/people/flagged/skipped).

---

### `pipeline/commands/import_convokit.py` (service, batch/file-I/O + CRUD)

**Analog:** `pipeline/commands/ingest.py` (467 lines — read in full this pass)

**Imports pattern** (lines 37-57):
```python
import io
import os
import urllib.parse
from datetime import date
from pathlib import Path

import httpx
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from api.models.models import (
    AdminJob, AdminJobStatus, AdminJobStep,
    Argument, Case, CaseArgument, PipelineRun, PipelineRunStatus,
)
from pipeline.db import get_session
```
For the new command: drop `httpx`/`AdminJob*` (no HTTP fetch, no admin-job-driven mode for a one-time bulk import), add `json`, `pipeline.corpus.loader`, `pipeline.corpus.apolitical`, `pipeline.corpus.stage_directions`, and `Person`/`CourtTenure`/`ArgumentParticipant`/`Utterance`/`SideEnum`.

**Slug helper — reuse verbatim, import don't reimplement** (lines 85-101):
```python
def _derive_slug(case_name: str) -> str:
    import re
    slug = case_name.lower()
    slug = slug.replace("'", "")
    slug = slug.replace("&", "and")
    slug = slug.replace("/", "-")
    slug = slug.replace("(", "").replace(")", "")
    slug = slug.replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")
```
RESEARCH.md flags this as a planner-discretion point (import directly from `pipeline.commands.ingest` vs. promote to a shared `pipeline/slugs.py`) — either is fine, but do NOT rewrite the logic a second time.

**Case idempotent-create pattern** (lines 365-394) — directly analogous, add `oyez_case_id=oyez_case_id` (new column, D-10):
```python
result = await session.execute(
    select(Case).where(Case.docket_number == docket)
)
existing_case = result.scalar_one_or_none()

if existing_case is not None:
    print(f"Case {docket} already exists (id={existing_case.id}) — reusing.")
    cases.append(existing_case)
else:
    new_case = Case(
        docket_number=docket,
        docket_number_norm=docket.replace("-", ""),
        case_name=effective_case_name,
        term_year=term_year,          # D-15: from cases.jsonl "year" directly, NOT argued_date
        slug=case_slug,
        oyez_case_id=oyez_case_id,    # NEW column
    )
    session.add(new_case)
    cases.append(new_case)

await session.flush()
```

**Argument dedup via IntegrityError catch** (lines 402-414):
```python
argument = Argument(
    argued_date=date.fromisoformat(argued_date) if argued_date else None,
    question_number=args.question,
    source_docket=primary_docket or (all_dockets[0] if all_dockets else None),
    source_dockets=all_dockets or None,
    status=ArgumentStatusEnum.DRAFT,       # D-06: land as draft, not published/pipeline
    oyez_transcript_id=oyez_transcript_id, # NEW column (D-10)
)
session.add(argument)
try:
    await session.flush()
except IntegrityError:
    raise ValueError(f"Duplicate argument: docket {primary_docket!r} Q{args.question} already exists.")
```
Note: for D-08 resumability, prefer a `select()`-before-insert check on `oyez_transcript_id` (the natural corpus-native idempotency key) ahead of relying on the `IntegrityError` catch, since a resumed batch should skip cleanly rather than throw-and-catch on every re-run.

**PipelineRun creation** (lines 432-440) — copy shape, set `strategy="convokit_import"` per D-09:
```python
run = PipelineRun(
    argument_id=argument.id,
    step="ingest",                 # or a new step value — planner to confirm convention
    status=PipelineRunStatus.COMPLETED,
    strategy="convokit_import",    # D-09
)
session.add(run)
await session.flush()
```

**CaseArgument idempotent-link pattern** (lines 416-430) — copy verbatim for lead-docket-only (D-19) cases.

**Error handling / job-status wrapper** (lines 201-218, `run_ingest`) — **NOT directly applicable**: this command has no `admin_jobs`-driven mode (it's operator-invoked bulk CLI, not spawned by the admin UI). Do not copy the `AdminJob` FAILED-status wrapper; instead rely on D-14's per-batch summary + per-row try/except (per RESEARCH.md's Common Pitfalls / Security Domain V5 guidance) so one bad row doesn't abort the whole term-batch.

---

### `pipeline/corpus/loader.py`, `stage_directions.py` (utility, streaming file-I/O / transform)

**No existing codebase analog** — these are new patterns (streaming JSONL reads, curated-vocabulary marker detection) not previously present in this codebase. RESEARCH.md's "Code Examples" section already contains the concrete implementation to use directly:
```python
import json
from pathlib import Path

def stream_utterances_for_conversation_ids(utterances_path: Path, wanted_ids: set[str]):
    with utterances_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("conversation_id") in wanted_ids:
                yield row
```
See 29-RESEARCH.md lines 432-460 for the full streaming pattern and 489-506 for the CSV-row-to-CourtTenure mapping.

---

### `pipeline/corpus/apolitical.py` (utility, transform)

**Analog:** `pipeline/commands/ingest.py` lines 402-407 — the existing convention of building ORM objects from named/explicit fields rather than `Model(**row)`. There is no dedicated allowlist module yet in this codebase; this is a new pattern extending an existing implicit convention.
```python
# Existing implicit convention (ingest.py) — never Model(**source_dict):
argument = Argument(
    argued_date=date.fromisoformat(argued_date) if argued_date else None,
    question_number=args.question,
    source_docket=primary_docket or (all_dockets[0] if all_dockets else None),
    source_dockets=all_dockets or None,
)
```
**Apply explicitly and exhaustively** for every `conversations.json`/`cases.jsonl` row touched — these carry `win_side`/`votes_side`/`scdb_docket_id`/`win_side_detail`/`votes`/`votes_detail` that must NEVER be persisted (hard apolitical constraint). Write one function per source-row-type that returns a plain dict of only the allowed fields; never pass raw source dicts into `Model()` constructors or JSONB columns.

---

### `pipeline/__main__.py` (modified — new subparsers)

**Analog:** itself, existing subparser blocks (lines 105-238) plus dispatch (lines 260-270)

**Subparser registration pattern** (lines 105-171, `ingest_p` block) — copy structure for `import-justices` and `import-convokit`:
```python
ingest_p = sub.add_parser(
    "ingest",
    help="Download PDF and create pipeline records",
    description=(...),
)
ingest_p.add_argument("--url", required=False, default=None, help="...")
```
**Mutually-exclusive `--term`/`--term-range` group** — use RESEARCH.md's Code Examples section (lines 462-487) directly:
```python
term_group = import_p.add_mutually_exclusive_group(required=True)
term_group.add_argument("--term", type=int, help="Single October Term year, e.g. 1955")
term_group.add_argument("--term-range", type=str, help="Inclusive term range, e.g. 1955-1960")
```

**Dispatch pattern to extend** (lines 260-270):
```python
if args.command == "ingest":
    asyncio.run(run_ingest(args))
elif args.command == "parse":
    asyncio.run(run_parse(args))
elif args.command == "resolve":
    ...
elif args.command == "seed-aliases":
    asyncio.run(run_seed_aliases(args))
```
Add `elif args.command == "import-justices": asyncio.run(run_import_justices_csv(args))` and `elif args.command == "import-convokit": asyncio.run(run_import_convokit(args))`.

**Windows event loop guard** (lines 28-31) — already in place at module top, unchanged, applies automatically to the new subcommands (no code change needed here, confirmed by RESEARCH.md Pattern 3 note).

---

### `alembic/versions/00XX_add_oyez_external_ids.py` (migration)

**Analog:** `alembic/versions/0016_add_person_birthdate.py` (full file, 46 lines)

**Full pattern to replicate exactly** (docstring style, revision header, upgrade/downgrade shape):
```python
"""Add oyez_case_id, oyez_transcript_id, oyez_speaker_id — external ID columns.

Revision ID: 00XX
Revises: <current head — confirm via `alembic heads`>
Create Date: 2026-07-XX

No backfill — all existing rows remain NULL.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "00XX"
down_revision: Union[str, None] = "<current head>"
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
**Critical: planner/implementer must run `alembic heads` at execute time** to get the real `down_revision` — as of this research pass, `0016_add_person_birthdate.py` is the newest migration found, but a Phase 28 migration may have landed first.

**Corresponding model changes** (add to `api/models/models.py`):
```python
# Case (after slug, line 157):
oyez_case_id = Column(String(50), nullable=True)

# Argument (after cover_metadata, line 198):
oyez_transcript_id = Column(String(50), nullable=True)

# Person (after birthdate, line 119):
oyez_speaker_id = Column(String(100), nullable=True)
```

---

### `app/src/routes/attributions/+page.svelte` (static page)

**Analog:** `app/src/routes/cases/+page.svelte` (header/style conventions only — full content spec lives in `29-UI-SPEC.md`, read that directly for exact copy)

**Header bar / heading style pattern** (lines 1-40):
```svelte
<script lang="ts">
	let { data } = $props();
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0; line-height: 1.2;">
			Attributions
		</h1>
	</header>
	<!-- body content per 29-UI-SPEC.md -->
</main>
```
This page needs **no `+page.server.ts`** — it's fully static per RESEARCH.md's Architectural Responsibility Map ("Frontend (SvelteKit) — New static route, no server load function required").

---

### `app/src/lib/components/ChatBubble.svelte` (modified — per-argument attribution note)

**Analog:** itself, lines 94-105 (existing utterance-text render block)

**Existing render pattern to extend, NOT replace:**
```svelte
<p style="font-size: 16px; color: #e2e8f0; font-weight: 400; line-height: 1.6; margin: 0;">
	{utterance.text}
</p>
```
**Confirmed safe (Pitfall 4, RESEARCH.md lines 419-422):** this `<p>` has no `white-space` CSS override anywhere in the component, so D-18's verbatim `\n`-preserved text collapses harmlessly to a single flowing line under the browser's `white-space: normal` default — no code change required in this block for the `\n` preservation decision itself. The attribution note is a separate, new UI element (see `29-UI-SPEC.md` for exact placement/wording), gated server-side (see below), not a change to this existing render block.

---

### `+page.server.ts` for argument detail (attribution visibility gate)

**No excerpt extracted this pass** — file not read in this pattern-mapping session (budget-constrained; 5 strong analogs already found). Planner/implementer must read `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` directly before implementing. Per RESEARCH.md's Architectural Responsibility Map: the `oyez_transcript_id IS NOT NULL` visibility check for the attribution note "must be resolved server-side ... matching Architecture Rule 2 (FASTAPI_BASE_URL server-only)" — i.e., compute the boolean in the load function and pass it to the page, do not fetch/check in browser code.

## Shared Patterns

### Idempotent check-before-insert
**Source:** `pipeline/commands/seed_aliases.py` lines 122-158; `pipeline/commands/ingest.py` lines 365-394, 416-430
**Apply to:** every entity write in both new commands (Case, Argument, Person, CourtTenure, ArgumentParticipant, Utterance) — `select()` → `scalar_one_or_none()` → skip-or-create-and-flush. This is what makes D-08's resumability requirement work "for free."

### DB session lifecycle
**Source:** `pipeline/db.py` — `get_session()` async context manager
**Apply to:** both new command modules, used exactly as-is (`async with get_session() as session: ...`). Mandatory `statement_cache_size=0` is already baked into the singleton engine — no per-command change needed.

### Apolitical field-stripping (explicit allowlist, never `Model(**row)`)
**Source:** new convention, extending the implicit pattern in `ingest.py` lines 402-407 (Argument built from named fields, not raw dict unpacking)
**Apply to:** every read of `conversations.json` and `cases.jsonl` rows — hard project constraint, not optional. See RESEARCH.md Common Pitfalls #2 and Security Domain (Information Disclosure threat).

### Argparse subcommand registration + Windows event-loop guard
**Source:** `pipeline/__main__.py` lines 24-31 (guard, unchanged), 105-171 (subparser shape), 260-270 (dispatch)
**Apply to:** the two new `import-justices` / `import-convokit` subcommands.

### Draft-status gate reused unchanged
**Source:** existing `ArgumentStatusEnum` / publish-unpublish machinery (Phase 15/26) — no new code, just set `status=ArgumentStatusEnum.DRAFT` on Argument creation (D-06).
**Apply to:** `import_convokit.py`'s Argument creation only.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `pipeline/corpus/loader.py` | utility | streaming file-I/O | No prior streaming-JSONL code exists in this codebase; use RESEARCH.md's Code Examples section directly (stdlib `json` + `for line in f`) rather than searching further for an analog |
| `pipeline/corpus/stage_directions.py` | utility | transform | No prior curated-vocabulary text-classification code exists; implement fresh per D-17's spec (vocabulary list + bracket/paren regex), no codebase precedent to copy from |

## Metadata

**Analog search scope:** `pipeline/commands/`, `pipeline/__main__.py`, `pipeline/db.py`, `alembic/versions/`, `api/models/models.py`, `app/src/routes/`, `app/src/lib/components/ChatBubble.svelte`
**Files scanned:** 10 (all read in full — none exceeded 2,000 lines)
**Pattern extraction date:** 2026-07-09
