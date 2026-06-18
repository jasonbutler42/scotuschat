---
plan: "06"
phase: "08"
status: complete
completed: 2026-06-18
---

# Phase 08 Plan 06 Summary: Gap Fix — ArgumentParticipant Population

## One-liner

Added Step 7b to `pipeline/commands/parse.py` that collects unique speaker labels from the parsed utterances and INSERTs one `ArgumentParticipant` row per label (`person_id=NULL`) immediately after the utterance flush, so `resolve.py`'s Step 5 `UPDATE` finds rows to update and `list_participants_for_job` returns a populated list.

## What Was Done

### Task 1 — Insert ArgumentParticipant rows in parse step

**File:** `pipeline/commands/parse.py`

After the utterance `session.flush()` (Step 7, line ~251), added a new Step 7b block:

- Imports `ArgumentParticipant` into the existing model imports.
- Collects unique `(raw_speaker_label, side)` pairs from all parsed utterances, excluding stage directions and null labels.
- Performs a select-before-insert to find labels already present in `argument_participants` for this argument (safe on parse re-runs).
- INSERTs only the new rows, each with `person_id=None`; the Resolve step's existing `UPDATE` populates `person_id` from there.
- Prints a seeding count for operator visibility in pipeline logs.

## Root Cause Closed

`resolve.py` Step 5 was running `UPDATE argument_participants SET person_id = ...` against rows that were never created — the parse step had no INSERT for `ArgumentParticipant`. Every UPDATE was a no-op, `list_participants_for_job` always returned `[]`, and the participants section never rendered on the job detail page.

## Verification

- `git show de099bb` confirms `ArgumentParticipant` imported and Step 7b block present.
- UAT Test 9 re-run after fix: new pipeline runs show the "N resolved participants" section on completed job detail pages.
- Select-before-insert guard prevents duplicate rows on parse re-runs.
- No frontend changes; Svelte check unaffected.
