# Phase 33: `update_argument_metadata` unique-constraint guard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 33-metadata-update-unique-constraint-guard
**Areas discussed:** HTTP conflict contract, Operator feedback, Guard consistency

---

## HTTP conflict contract

### HTTP status

| Option | Description | Selected |
|--------|-------------|----------|
| 409 Conflict | Values are valid but conflict with an existing argument; preserves current status | ✓ |
| 422 Unprocessable Entity | Treat the collision like form validation | |
| Agent decides | Delegate status choice | |

**User's choice:** `409 Conflict`.

### Response content

| Option | Description | Selected |
|--------|-------------|----------|
| Stable code plus clear message | `duplicate_argument` plus docket/question copy | ✓ |
| Clear message only | Human-readable text without a machine-stable code | |
| Agent decides | Delegate payload detail | |

**User's choice:** Stable code plus clear message.

### Conflicting record identity

| Option | Description | Selected |
|--------|-------------|----------|
| Include `conflicting_argument_id` | Enables a direct link to the existing record | ✓ |
| Omit the ID | Return only code, message, docket, and question | |
| Agent decides | Delegate identifier inclusion | |

**User's choice:** Include `conflicting_argument_id`.
**Notes:** User specified that the id must be rendered as a link to the conflicting admin record and open in a new tab.

### Payload shape

| Option | Description | Selected |
|--------|-------------|----------|
| Structured `detail` object | FastAPI-conventional `detail` containing code, message, and conflicting id | ✓ |
| Top-level fields | Put code/message/id at the response root | |
| Agent decides | Delegate response envelope | |

**User's choice:** Structured `detail` object.

---

## Operator feedback

### Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Shared card alert | Reuse the existing `role="alert"` inside `ArgumentDetailsCard.svelte` | ✓ |
| Page-level banner | Add a separate error banner above the card | |
| Agent decides | Delegate placement | |

**User's choice:** Shared card alert.

### Message copy

| Option | Description | Selected |
|--------|-------------|----------|
| Clear pair plus link | “An argument already uses docket {docket}, question {number}. Open conflicting argument.” | ✓ |
| Short generic copy | “Duplicate argument metadata.” plus link | |
| Agent decides | Delegate wording | |

**User's choice:** Clear docket/question copy with “Open conflicting argument” as the link.

### Failed-save values

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve all values | Keep dockets, question number, and argued date | ✓ |
| Preserve only dockets | Match current failure payload | |
| Reset | Restore last persisted values | |

**User's choice:** Preserve every submitted value.

### Keyboard focus

| Option | Description | Selected |
|--------|-------------|----------|
| Focus the alert | Announce the error and place its link in immediate context | ✓ |
| Leave focus on Save | Rely only on `role="alert"` announcement | |
| Agent decides | Delegate focus behavior | |

**User's choice:** Move focus to the collision alert.

---

## Guard consistency

### Layering

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-check plus fallback | Precise normal response plus race-safe database fallback | ✓ |
| Fallback only | Catch `IntegrityError` without proactive lookup | |
| Pre-check only | Precise response without race protection | |

**User's choice:** Pre-write check plus `IntegrityError` fallback.

### Partial updates

| Option | Description | Selected |
|--------|-------------|----------|
| Final combined pair | Combine submitted and stored values; exclude current argument | ✓ |
| Both fields only | Check only when docket and question arrive together | |
| Agent decides | Delegate partial-PATCH behavior | |

**User's choice:** Check the final pair and exclude self.

### Writer coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Audit every writer | Common predicate with channel-specific outcomes | ✓ |
| Metadata only | Do not audit other source_docket/question writers | |
| Identical handling everywhere | Force HTTP-style wording onto all channels | |

**User's choice:** Audit every writer against the same predicate while preserving channel-specific behavior.

### Constraint identification

| Option | Description | Selected |
|--------|-------------|----------|
| Named constraint only | Map `uq_arguments_source_docket_question` to `duplicate_argument`; sanitize others separately | ✓ |
| Every constraint is duplicate | Treat all integrity failures as the same collision | |
| Other constraints become 500 | Cleanly handle only the known unique violation | |

**User's choice:** Map only the named unique constraint and sanitize other failures separately.

---

## Agent's Discretion

- Exact shared-helper placement and internal function names.
- Sanitized internal logging structure for non-duplicate constraint failures.
- Test organization, subject to the locked behavioral coverage in `33-CONTEXT.md`.

## Deferred Ideas

- “Edit affordance on utterances and speaker popover” was moved from the recurring pending-todo queue to backlog Phase 999.9 for later prioritization; it is not part of Phase 33.