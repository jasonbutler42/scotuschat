---
phase: 29-historical-corpus-import
plan: 01
subsystem: database
tags: [alembic, sqlalchemy, python-dateutil, oyez, convokit]

requires: []
provides:
  - "Three nullable oyez_* external-ID columns (cases.oyez_case_id, arguments.oyez_transcript_id, people.oyez_speaker_id) via migration 0017"
  - "data/corpus/ directory scaffolding (tracked via .gitkeep, source files gitignored)"
  - "python-dateutil>=2.9 declared and installed as a project dependency"
affects: [29-02, 29-03, 29-04, 29-05, 29-06]

tech-stack:
  added: [python-dateutil>=2.9]
  patterns: [oyez_* external-ID columns follow the existing nullable-no-backfill migration pattern from 0016]

key-files:
  created:
    - alembic/versions/0017_add_oyez_external_ids.py
    - data/corpus/.gitkeep
    - data/corpus/.gitignore
  modified:
    - requirements.txt
    - .gitignore
    - api/models/models.py

key-decisions:
  - "down_revision for 0017 confirmed as 0016 via live `alembic heads` at execute time (matched research, no Phase 28 migration landed ahead of it)"
  - "python-dateutil approved via blocking human-verify checkpoint (PyPI page + github.com/dateutil/dateutil source repo confirmed, exact package name confirmed, not a typosquat)"
  - "convokit package deliberately NOT added as a dependency (D-20/D-21) — only python-dateutil is needed for free-text date parsing"

patterns-established:
  - "External-ID columns for corpus-sourced rows are nullable, string-typed, and added with no backfill — same discipline as migration 0016's birthdate column"

requirements-completed: [CORPUS-02, CORPUS-04]

coverage:
  - id: D1
    description: "data/corpus/ directory exists in the repo, tracked only via .gitkeep, with corpus file types (*.jsonl/*.json/*.csv) gitignored exactly like data/pdfs/"
    requirement: "CORPUS-02"
    verification:
      - kind: manual_procedural
        ref: "test -f data/corpus/.gitkeep && test -f data/corpus/.gitignore && git status --porcelain data/corpus/ (only .gitkeep/.gitignore staged)"
        status: pass
    human_judgment: false
  - id: D2
    description: "python-dateutil declared in requirements.txt and importable in the project venv"
    requirement: "CORPUS-04"
    verification:
      - kind: unit
        ref: "grep python-dateutil requirements.txt && .venv/Scripts/python.exe -c \"import dateutil.parser\""
        status: pass
    human_judgment: false
  - id: D3
    description: "Migration 0017 adds three nullable oyez_* columns (cases.oyez_case_id, arguments.oyez_transcript_id, people.oyez_speaker_id), verified against the live database, with ORM models matching and a clean downgrade/upgrade round-trip"
    requirement: "CORPUS-02"
    verification:
      - kind: integration
        ref: "alembic upgrade head; information_schema.columns live-DB assertion for all 3 columns (is_nullable=YES); alembic downgrade -1 && alembic upgrade head round-trip"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-09
status: complete
---

# Phase 29 Plan 01: Historical Corpus Import — Schema & Filesystem Foundation Summary

**Migration 0017 adds three nullable oyez_* external-ID columns (cases, arguments, people) and data/corpus/ + python-dateutil are staged for the Cornell ConvoKit/Oyez historical importer.**

## Performance

- **Duration:** ~15 min (Task 1 checkpoint resolved by user in a prior session turn; Tasks 2-3 executed this session)
- **Started:** 2026-07-09T22:51:05Z (per STATE.md session start)
- **Completed:** 2026-07-09T22:57:07Z
- **Tasks:** 3 (1 checkpoint + 2 auto)
- **Files modified:** 6

## Accomplishments
- Added `python-dateutil>=2.9` to requirements.txt and confirmed it installed and importable in the project's `.venv` (already present, matching version)
- Created `data/corpus/` tracked via `.gitkeep`, with a scoped `.gitignore` ignoring `*.jsonl`/`*.json`/`*.csv`, plus a top-level `.gitignore` `data/corpus/*.jsonl` entry for defense-in-depth against the 900MB `utterances.jsonl` file ever being committed
- Created Alembic migration `0017_add_oyez_external_ids.py` adding three nullable external-ID columns: `cases.oyez_case_id` (VARCHAR(50)), `arguments.oyez_transcript_id` (VARCHAR(50)), `people.oyez_speaker_id` (VARCHAR(100)) — no backfill, matching D-10
- Added matching ORM columns to `Case`, `Argument`, and `Person` in `api/models/models.py`
- Verified live database state via `information_schema.columns` (all 3 columns present, `is_nullable = YES`) and confirmed a clean `alembic downgrade -1` / `alembic upgrade head` round-trip, ending at head `0017`

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy gate — verify python-dateutil before install** - resolved via `checkpoint:human-action` in a prior executor turn (no code changes; see Deviations/Checkpoint section below)
2. **Task 2: Add python-dateutil dependency and create data/corpus/ source directory** - `4be91dd5` (feat)
3. **Task 3: Migration 0017 — add the 3 nullable oyez external-ID columns and matching model fields** - `981c40a4` (feat)

_Note: Task 1 required no commit — it was a blocking human-verify checkpoint with no file changes._

## Files Created/Modified
- `requirements.txt` - Added `python-dateutil>=2.9`
- `.gitignore` - Added `data/corpus/*.jsonl` defense-in-depth entry
- `data/corpus/.gitkeep` - Empty tracked file so the directory exists in git
- `data/corpus/.gitignore` - Ignores `*.jsonl`/`*.json`/`*.csv`, documents the 900MB `utterances.jsonl` constraint
- `alembic/versions/0017_add_oyez_external_ids.py` - Migration adding 3 nullable oyez_* columns, down_revision confirmed against live `alembic heads` (0016)
- `api/models/models.py` - Added `Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id` ORM columns matching the migration exactly

## Decisions Made
- Confirmed `alembic heads` returned `0016` (single head, matching RESEARCH.md) before writing migration 0017 with `down_revision = "0016"` — no branched history to reconcile
- `python-dateutil` was already installed in the project's `.venv` at the required version (2.9.0.post0); `pip install` was a no-op confirmation rather than a fresh install

## Deviations from Plan

None - plan executed exactly as written.

### Checkpoint Resolution (Task 1)

Task 1 was a `checkpoint:human-action` (package legitimacy gate, `gate="blocking-human"`) for `python-dateutil`, flagged `[SUS]` in RESEARCH.md solely due to an `unknown-downloads` signal (no substantive concern). This checkpoint was resolved by the user in a prior conversation turn before this continuation began:
1. Confirmed PyPI homepage/source repository resolves to `github.com/dateutil/dateutil`
2. Confirmed latest version is `2.9.0.post0` or newer, not yanked/deprecated
3. Confirmed the exact package name `python-dateutil` (not a typosquat)

User responded "Approved." No further action was needed — Task 2 proceeded with the install as planned.

## Issues Encountered
None.

## User Setup Required

**External services require manual configuration.** Per this plan's `user_setup` block:
- Copy `utterances.jsonl`, `conversations.json`, `speakers.json`, `cases.jsonl`, and the justices tenure CSV into `data/corpus/` (these are NOT committed to git — `utterances.jsonl` alone is ~900MB). Do NOT copy `info.arcs.jsonl` / `info.parsed.jsonl` / `info.tokens.jsonl`.
- This must happen before any later plan in this phase (justice importer, corpus importer) can run against real source data.

## Next Phase Readiness
- Schema foundation is complete and verified against the live database: `alembic current` reports `0017`, and all three `oyez_*` columns exist and are nullable.
- `data/corpus/` is ready to receive source files without git contamination risk (verified `git status --porcelain data/corpus/` shows only `.gitkeep`/`.gitignore`).
- `python-dateutil` is available for any later plan needing free-text date parsing of `cases.jsonl`.
- Blocker for later plans: the operator must manually place the 5 ConvoKit/Oyez source files into `data/corpus/` (see User Setup Required above) before the importer plans (29-02 onward) can be executed against real data.

---
*Phase: 29-historical-corpus-import*
*Completed: 2026-07-09*

## Self-Check: PASSED
