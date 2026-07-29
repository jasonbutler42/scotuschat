# Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 37-tenure-seat-as-chief-associate-toggle
**Areas discussed:** Seat representation, Existing-data migration, Editor behavior, Displayed wording

---

## Seat representation

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Underlying representation | Role plus optional seat number; binary role only; one constrained combined value | Binary Chief/Associate only |
| Elevation history | Separate periods; latest role only; one continuous row with current role | Separate Associate and Chief periods |
| Required value | Require Chief/Associate; allow unset; add Unknown | Require Chief or Associate |
| Enforcement boundary | Every write path; editor only; editor and API only | Every write path |

**User's choice:** Remove numbered-seat distinctions from the active model and enforce a required binary office universally.
**Notes:** The user questioned whether retaining a seat number would create more tenure rows. After clarification that it would be a property rather than a row, the user still chose the simpler binary model. Elevation remains the event that creates a separate tenure period.

---

## Existing-data migration

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Numbered values | Normalize with audit; normalize silently; manual review | Normalize to Associate with audit |
| Blank/unrecognized values | Stop for resolution; infer; default Associate | Stop for explicit resolution |
| Execution workflow | Dry run then execute; preview/confirm in one run; schema-upgrade automation | Required dry run then separate execute |
| Failure policy | Roll back everything; keep successes; batch commits | Atomic rollback |

**User's choice:** Use a traceable, fail-closed migration with a mandatory dry run and atomic execution.
**Notes:** The audit must retain original values for changed rows. No ambiguous value may be guessed.

---

## Editor behavior

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| New-row default | Associate; no selection; copy previous tenure | Associate |
| Invalid stored value | Show and block; coerce to Associate; leave blank and allow unrelated saves | Show original and block profile save |
| Persistence | Existing profile Save; immediate save; per-tenure Save | Existing profile Save |
| Active-segment click | Keep selected; allow deselection; confirmation before clear | Keep selected |

**User's choice:** Use an always-valid binary control integrated into the existing atomic profile form.
**Notes:** Data drift remains visible and must be explicitly corrected rather than silently normalized by the editor.

---

## Displayed wording

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Toggle labels | Chief/Associate; full titles; mixed labels | Chief / Associate |
| Read-only wording | Full titles; short labels; context-dependent | Chief Justice / Associate Justice |
| Field label | Role; Seat; Office | Office |
| Rename boundary | End to end; UI only; transitional API alias | End-to-end `seat` to `office` rename |

**User's choice:** Use Office throughout the model, short toggle labels in the editor, and formal titles in read-only views.
**Notes:** The user specifically chose “Office” to avoid reusing “role,” which they want reserved for argument-specific roles.

---

## the agent's Discretion

- Exact constraint/enum implementation, audit-report format, command names, and low-level segmented-control styling.

## Deferred Ideas

None.
