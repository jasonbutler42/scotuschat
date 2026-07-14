---
phase: 33-metadata-update-unique-constraint-guard
verified: 2026-07-14T16:15:00Z
status: gaps_found
score: 9/10
overrides_applied: 0
gaps:
  - id: CR-01
    severity: blocker
    truth: "Parse pre-checks only a docket fill that can actually occur, preserves an existing operator docket, excludes self, permits NULL question, and remains race-safe."
    reason: "pipeline/commands/parse.py performs find_argument_by_pair for every extracted primary docket before testing whether the current argument already has source_docket. A conflict can therefore fail parsing even though the subsequent source_docket IS NULL update would be a no-op."
    artifacts:
      - path: "pipeline/commands/parse.py"
        issue: "The pre-check at lines 374-387 is not conditional on argument_row.source_docket being None."
      - path: "pipeline/tests/test_parse.py"
        issue: "The Phase 33 test only inspects source text and does not execute the existing-operator-docket control flow."
    missing:
      - "Gate both the pair pre-check and conditional write on the current source_docket being NULL."
      - "Add a behavioral regression proving an extracted conflicting docket does not fail or replace an existing operator docket."
---

# Phase 33: Metadata Update Unique-Constraint Guard Verification

**Phase goal:** Guard metadata updates against the `(source_docket, question_number)` unique constraint across the admin service and every offline writer, returning exact sanitized recovery instead of an unhandled 500.

**Status:** `gaps_found` — Plan 33-04 closes the duplicate-copy UAT defect, but the parse offline writer still rejects a harmless extracted conflict when its guarded docket write cannot occur.

## Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A colliding admin metadata save returns a structured, sanitized 409 rather than an unhandled 500. | VERIFIED | `admin_arguments.py` checks the final pair with self-exclusion; `admin.py` maps pre-check and exact named-constraint races to the same structured response. |
| 2 | A unique, partial, unchanged, self, or NULL-pair metadata save continues to follow PostgreSQL uniqueness semantics. | VERIFIED | Service tests cover final-pair construction, self-exclusion, unchanged values, and NULL short-circuit behavior. |
| 3 | Only the exact named database constraint enters duplicate recovery. | VERIFIED | `argument_uniqueness.py` reads structured constraint metadata and tests reject message-only and unrelated failures. |
| 4 | Ingest handles only the named pair violation as a duplicate. | VERIFIED | The shared classifier controls the duplicate channel; unrelated integrity errors are re-raised and behaviorally tested. |
| 5 | ConvoKit preserves its counter/rollback behavior only for the named collision. | VERIFIED | Named and non-target paths are separated and behaviorally tested. |
| 6 | Parse pre-checks only a docket fill that can occur and preserves an existing operator docket. | **FAILED (BLOCKER)** | At `pipeline/commands/parse.py:374-387`, the lookup runs whenever an extracted docket exists. It does not first require `argument_row.source_docket is None`; the SQL update at lines 389-393 does require NULL and would otherwise be a no-op. |
| 7 | Parse excludes self, permits NULL question, and classifies a raced named violation narrowly. | VERIFIED, subject to Truth 6 | The shared lookup receives `exclude_argument_id`; NULL is handled by the helper; the flush catch uses the exact classifier. |
| 8 | Both SvelteKit actions validate the duplicate shape and preserve attempted metadata on failures. | VERIFIED | Both actions validate code/message/positive numeric id and return docket/question/date values through failure branches. |
| 9 | The shared alert preserves focus and safe numeric new-tab recovery behavior. | VERIFIED | Source contracts pass, and UAT confirmed both routes, keyboard focus/navigation, retained values, and `window.opener === null`. |
| 10 | Duplicate recovery copy appears exactly once with identical factual pre-check/race messages. | VERIFIED | Plan 33-04 removed link wording from both API builders; exact route and composed-copy regressions pass. |

## CR-01 Validation

CR-01 is **confirmed**, not refuted. The current order is:

1. Load the argument and its question number.
2. Look up the extracted `(docket, question)` pair and raise on conflict.
3. Attempt an update guarded by `Argument.source_docket.is_(None)`.

For an argument whose operator docket is already non-NULL, step 3 cannot write anything. Nevertheless, step 2 can raise because another argument owns the *extracted* pair. This violates the plan truth that parse performs a conditional docket fill while preserving operator-entered data and means the all-writers portion of the phase goal is not achieved.

`pipeline/tests/test_parse.py::test_parse_docket_fill_uses_pair_precheck_and_named_race_classification` only checks that strings occur in `_run_parse_inner`; it does not prove the necessary ordering or execute this state transition. Passing suites therefore do not override the observable control-flow defect.

## Artifact and Wiring Check

- The shared uniqueness helper exists, is substantive, and is wired into the admin service plus ingest, ConvoKit, and parse.
- Admin pre-check/race recovery is wired through both SvelteKit actions to the shared card.
- Plan 33-04 is substantive and correctly gives the component sole ownership of `Open conflicting argument`.
- Parse is wired to the helper, but its wiring is semantically too broad because the lookup is outside the existing-docket guard.

## Verification Evidence

| Check | Result |
|---|---|
| Focused Plan 33-04 checks | 14 passed, 8 skipped; Svelte check 0 errors |
| Full configured regression suite | 445 passed, 5 xfailed |
| Two-route browser UAT before 33-04 | Value retention, focus, keyboard navigation, numeric new tab, and opener isolation passed; duplicated copy was reported and then fixed by 33-04 |
| Adversarial source review | CR-01 reproduced by direct control-flow inspection; no behavioral regression covers it |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| PIPE-27 | **BLOCKED** | The primary admin requirement is handled, but the phase contract and roadmap success criterion require consistency across every pair-writing path. Parse can still reject a no-op metadata fill. |

## Required Next Action

Create and execute a gap-closure plan that moves the parse pre-check and update inside an `argument_row.source_docket is None` guard, retains the named-constraint race catch, and adds a behavioral test for an existing operator docket plus a conflicting extracted docket. Re-run Phase 33 verification afterward.

## Disconfirmation Pass

- **Partially met requirement:** all writers import the shared helper, but parse invokes it when no write is eligible.
- **Misleading passing test:** `test_parse_docket_fill_uses_pair_precheck_and_named_race_classification` verifies tokens, not control flow.
- **Uncovered error path:** existing non-NULL operator docket + extracted docket owned by another argument.

---
*Verifier: Codex generic-agent workaround for gsd-verifier*
