# Phase 30: Corpus Import Resolve Workflow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-10
**Phase:** 30-Corpus Import Resolve Workflow
**Areas discussed:** Job creation trigger, Universal pause vs. flagged-only, Bulk review tooling, Resolve UI reuse vs. new UI

---

## Job Creation Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| import-convokit creates one immediately per argument | The importer creates the AdminJob row right when it creates the Argument — every batch already has paused jobs waiting the moment the import finishes. | ✓ |
| Separate backfill command, run after import | import-convokit stays unchanged; a new one-off command scans for corpus-imported arguments with no AdminJob and creates them in bulk. | |
| Lazy — created on-demand when an operator opens the argument | No AdminJob until an operator navigates to the argument; requires new routing/UI logic. | |

**User's choice:** import-convokit creates one immediately per argument.

**Follow-up: what about the term-1955 data already imported (no AdminJob rows exist)?**

| Option | Description | Selected |
|--------|-------------|----------|
| One-time backfill for already-imported arguments, then the importer handles all future ones | A small one-off script creates the missing rows for the 163 existing arguments. | |
| Wipe and re-run the term-1955 import instead | Since the DB has already been wiped/re-imported multiple times this session for validation, just re-run once the importer creates jobs itself. | ✓ |

**User's choice:** Wipe and re-run term 1955 instead of writing a separate backfill path.

---

## Universal Pause vs. Flagged-Only

| Option | Description | Selected |
|--------|-------------|----------|
| Every single argument pauses, no exceptions | Even zero-flag, cleanly-matched arguments sit paused until an operator explicitly reviews and completes resolve. Queue could reach ~7,800 items across the full corpus. | ✓ |
| Only pause when something was flagged | Zero-flag arguments resolve automatically at import time; only flagged ones enter the review queue. Smaller queue, but relies on flagging logic being complete. | |

**User's choice:** Every single argument pauses, no exceptions — matches the user's own earlier framing ("they should probably all be sitting in the paused state").

---

## Bulk Review Tooling

| Option | Description | Selected |
|--------|-------------|----------|
| Not yet — one at a time is fine for now | Build the paused/resolve routing first, validate against the small term-1955 batch. Bulk-approve is its own feature with its own hard questions. | ✓ |
| Yes — build a basic bulk-approve action now | Add a simple "approve all with zero flags" action so the operator isn't stuck clicking through thousands one at a time. Adds real scope to this phase. | |

**User's choice:** Not yet — deferred to a future phase once the review flow is validated against real volume.

---

## Resolve UI Reuse vs. New UI

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse the existing Resolve card exactly as-is | Same columns, same person re-matching affordances; rows arrive pre-populated instead of blank, but the operator interacts with them identically. | ✓ |
| New/adapted view distinguishing corpus-sourced review from PDF-pipeline resolve | A different presentation (e.g. read-only summary, edit-in-place only on flagged rows) to reduce friction across thousands of reviews. | |

**User's choice:** Reuse the existing Resolve card exactly as-is.

---

## Claude's Discretion

- Exact mechanism/ordering for creating the AdminJob row inside `import_convokit.py`'s `_import_conversation` (relative to the PipelineRun row, exact query/insert shape).
- Whether `resolve_job()`/`update_resolve_row_for_job()` need any corpus-specific branching, or already generalize correctly — left for the researcher to verify against the real code before planning locks an approach.

## Deferred Ideas

- **Bulk/batch-approve tooling** — "approve all with zero flags in this term/batch." Revisit as its own future phase once this phase has shipped and been used against a larger term range.
- **Edit affordance on utterances and speaker popover** (pending todo, reviewed a third time — declined again, unrelated public-UI scope).
