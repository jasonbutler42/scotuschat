---
plan: 02-02
phase: 02-speaker-resolution
status: complete
completed_at: 2026-06-12
---

# Plan 02-02 Summary: seed-aliases + resolve pipeline commands

## What was built

- `pipeline/commands/seed_aliases.py` — `async def run_seed_aliases(args)`: seeds 4 roles, 13 Justice people rows, and 15 speaker_alias label variants using check-before-insert idempotency. Idempotent — safe to re-run.
- `pipeline/commands/resolve.py` — `def normalize_label(raw: str) -> str` (D-02 implementation: strip, rstrip colon, upper) and `async def run_resolve(args)`: loads parse run (read-only), creates a new resolve PipelineRun, collects unique non-null non-stage-direction labels, auto-resolves via alias table or prompts operator interactively, bulk-UPDATEs utterances.person_id and argument_participants.person_id, sets status=COMPLETED on success or NEEDS_REVIEW on KeyboardInterrupt.
- `pipeline/__main__.py` — Extended with `resolve` (requires `--run-id`) and `seed-aliases` subcommands, including top-level `try/except KeyboardInterrupt` wrapper for resolve (Pitfall 4 guard).
- `pipeline/tests/test_resolve.py` — 5 test stubs covering PIPE-07/PIPE-09; `test_normalize_label` and `test_resolve_interrupt_sets_needs_review` are implemented and passing.
- `pipeline/tests/test_seed_aliases.py` — 2 DB integration test stubs covering PIPE-08.

## Key decisions / deviations

- **Labels query moved inside try block**: The unique labels `SELECT` (Step 3) was initially outside the `try/except KeyboardInterrupt`, causing interrupts raised at that point to propagate uncaught. Moved inside the `try:` block to ensure all DB-touching resolve operations are guarded.
- **`test_resolve_interrupt_sets_needs_review` implemented as unit test**: Uses a plain async function for `session.execute` side-effect (not `AsyncMock(side_effect=KeyboardInterrupt)`) to ensure `KeyboardInterrupt` is raised as a real coroutine-level exception that the `except` block can catch. `fake_flush` only mutates the resolve_run id on the first call (subsequent calls are no-ops to preserve status mutations).
- **All Pitfall guards implemented**: Pitfall 1 (parse_run.status never mutated), Pitfall 2 (raw_label for UPDATE, normalized for alias lookup), Pitfall 3 (`.execution_options(synchronize_session=False)` on all update() calls), Pitfall 7 (argument_participants.person_id also updated during resolve).

## Verification results

```
# 7 stubs collected:
pytest pipeline/tests/test_resolve.py pipeline/tests/test_seed_aliases.py --collect-only -q
  7 tests collected in 0.01s

# test_normalize_label passes (GREEN):
pytest pipeline/tests/test_resolve.py::test_normalize_label -x -q
  1 passed in 0.03s

# test_resolve_interrupt_sets_needs_review passes (GREEN):
pytest pipeline/tests/test_resolve.py::test_resolve_interrupt_sets_needs_review -x -q
  1 passed

# --help output:
python -m pipeline --help
  {ingest,parse,resolve,seed-aliases}
  resolve   Interactively resolve speaker labels for a parse run
  seed-aliases  Pre-seed Justice people records and speaker_alias rows

python -m pipeline resolve --help
  --run-id RUN_ID  pipeline_run.id from a prior PARSE step

# Pitfall guards:
grep "synchronize_session=False" pipeline/commands/resolve.py  -> 2 code matches (+ 1 in docstring)
grep "parse_run.status" pipeline/commands/resolve.py           -> 0 code matches (2 comment-only)
```

## Files modified

- `pipeline/commands/seed_aliases.py` — created
- `pipeline/commands/resolve.py` — created
- `pipeline/__main__.py` — updated with resolve + seed-aliases subcommands
- `pipeline/tests/test_seed_aliases.py` — created
- `pipeline/tests/test_resolve.py` — created
