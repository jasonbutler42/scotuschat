---
plan: 02-01
phase: 02-speaker-resolution
status: complete
completed_at: 2026-06-12
---

# Plan 02-01 Summary: Alembic migration 0002_add_speaker_alias + SpeakerAlias ORM

## What was built

- `alembic/versions/0002_add_speaker_alias.py`: Hand-written Alembic migration that creates the `speaker_alias` table with 5 columns (id, normalized_label, person_id, created_at, notes), a FK constraint to `people.id`, a unique constraint `uq_speaker_alias_label` on `normalized_label`, and an index `ix_speaker_alias_normalized_label`. Downgrade drops the index then the table.
- `api/models/models.py`: `SpeakerAlias` ORM class added after `Utterance` (the last existing model). Uses only imports already present in the file — no new imports added. No relationship() declarations per project convention.
- `tests/test_schema.py`: `"speaker_alias"` added to `EXPECTED_TABLES` (now 11 entries); module docstring and `test_all_tables_exist` docstring updated from "10" to "11".

## Key decisions / deviations

- No PgENUM columns on `speaker_alias` — the table has no enum-typed columns, so no DO-block enum creation was needed in the migration.
- All imports (`String`, `Text`, `DateTime`, `ForeignKey`) were already present in `models.py`; no duplicates added.
- The venv at `.venv/` was used to run all commands (`alembic`, `python`, `pytest`) since neither `alembic` nor `pytest` were on the system PATH.
- `pytest` and `pytest-asyncio` were not installed in the venv; installed them to satisfy the test run requirement.

## Verification results

```
alembic upgrade head:
  INFO Running upgrade 0001 -> 0002, Add speaker_alias table.
  (exit 0)

alembic current:
  0002 (head)

SpeakerAlias import check:
  SpeakerAlias importable: speaker_alias

alembic downgrade base -> upgrade head:
  INFO Running downgrade 0002 -> 0001, Add speaker_alias table.
  INFO Running downgrade 0001 -> , Initial schema — all 10 tables.
  INFO Running upgrade  -> 0001, Initial schema — all 10 tables.
  INFO Running upgrade 0001 -> 0002, Add speaker_alias table.
  (both exit 0)

pytest tests/test_schema.py::test_no_create_all_in_codebase -x -q:
  1 passed in 0.03s
```

## Files modified

- `alembic/versions/0002_add_speaker_alias.py` — created
- `api/models/models.py` — SpeakerAlias class added; docstring updated (10 -> 11 tables)
- `tests/test_schema.py` — speaker_alias added to EXPECTED_TABLES; docstrings updated (10 -> 11 tables)
