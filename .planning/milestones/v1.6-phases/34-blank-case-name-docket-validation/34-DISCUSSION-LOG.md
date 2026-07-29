# Phase 34: Blank case_name/docket_number validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 34-blank-case-name-docket-validation
**Areas discussed:** Docket-array behavior, Whitespace handling, Operator error feedback, API error contract

---

## Docket-array behavior

| Decision | Options considered | User's choice |
|----------|--------------------|---------------|
| Minimum nonblank entries | Require one; validate legacy field only; agent decides | Agent discretion within strict PIPE-28 boundary |
| Mixed blank and valid entries | Drop blanks; reject whole request; agent decides | Drop blanks when valid entries remain |
| Explicit null | Reject; preserve null-clearing; agent decides | Reject explicit null; omission is unchanged |
| Singular/array disagreement | Reject mismatch; array wins; agent decides | Agent discretion |
| Duplicate entries | De-duplicate; reject; agent decides | De-duplicate in first-seen order |
| Blank entries before first valid | First remaining becomes canonical; reject; agent decides | First remaining valid becomes canonical |
| Failed empty attempt | Preserve empty attempt; restore saved docket; agent decides | Preserve empty attempt |
| Client-side empty check | Pill-control check plus backend; backend only; agent decides | Client and backend validation |

**Notes:** The live shared form sends `source_dockets`, so the collection path must be protected rather than validating only legacy `source_docket`.

---

## Whitespace handling

| Decision | Options considered | User's choice |
|----------|--------------------|---------------|
| Edge whitespace | Trim and accept; reject surrounding whitespace; agent decides | Trim and accept valid result |
| Internal whitespace | Preserve; collapse runs; agent decides | Preserve exactly |
| Blank character set | Python `str.strip`; ASCII space only; agent decides | Python `str.strip` semantics |
| Normalization owner | Schema validator; service layer; agent decides | Schema validator returns stripped value |

---

## Operator error feedback

| Decision | Options considered | User's choice |
|----------|--------------------|---------------|
| Error placement | Existing alert; beside fields; both | Existing inline `role="alert"` |
| Copy | Field-specific; generic; raw API text | Field-specific required copy |
| Focus | First invalid field; alert; unchanged | First invalid field |
| Failed values | Preserve all; reload saved; preserve only valid | Preserve entire attempted submission |

---

## API error contract

| Decision | Options considered | User's choice |
|----------|--------------------|---------------|
| Response contract | Standard Pydantic 422; custom codes; generic 422 | Standard structured Pydantic 422 |
| Invalid representations | Same required class; separate messages; agent decides | Same required classification |
| Multiple failures | Show all; first only; generic combined | Show all and focus first |
| Frontend matching | Structured `loc`; message strings; treat every 422 alike | Structured `loc` matching |

---

## Agent's Discretion

- Exact enforcement point for the minimum nonblank `source_dockets` rule, provided neither save path can clear the canonical docket.
- Deterministic handling when both singular and array docket fields are supplied but disagree.
- Internal helper placement, focus mechanics, and test organization.

## Deferred Ideas

None.
