---
phase: 33-metadata-update-unique-constraint-guard
verified: 2026-07-14T16:15:00Z
status: passed
score: 10/10 (post-fix — see stale-record correction note below)
overrides_applied: 0
gaps:
  - id: CR-01
    severity: blocker
    status: resolved
    resolved_by: "commit b41d6693 (2026-07-28), \"fix: preserve operator-set source_docket when extracted cover metadata conflicts\""
    resolved_date: 2026-07-28
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

**Stale-record correction (2026-07-29):** This file's `status: gaps_found` was never updated after CR-01 was fixed. Commit `b41d6693` (2026-07-28) — made outside the formal Phase 33 plan sequence (33-01–33-04 were already complete) — moved the `find_argument_by_pair` pre-check inside the same `argument_row.source_docket is None` guard as the subsequent update, exactly per this file's own "Required Next Action" below, and added `pipeline/tests/test_parse.py::test_parse_preserves_operator_docket_when_extracted_pair_conflicts`, a behavioral regression test that constructs a target Argument with an existing `source_docket`, an unrelated conflicting Argument sharing the extracted `(docket, question_number)` pair, runs real `run_parse`, and asserts both that no conflict is raised and that the operator's original docket is preserved unchanged. Re-read against the current source tree 2026-07-29 (during Phase 40.1's reconciliation, see `.planning/phases/40.1-sanitize-docket-input-to-close-path-traversal-arbitrary-file/40.1-SUMMARY.md`): `pipeline/commands/parse.py` now reads `if argument_row is not None and argument_row.source_docket is None:` wrapping both the lookup and the update — confirmed fixed. Truths 6 and 7 below, and the PIPE-27 coverage row, are corrected accordingly; original gap details preserved above as the audit trail of what was found.

# Phase 33: Metadata Update Unique-Constraint Guard Verification

**Phase goal:** Guard metadata updates against the `(source_docket, question_number)` unique constraint across the admin service and every offline writer, returning exact sanitized recovery instead of an unhandled 500.

**Status:** `resolved` — Plan 33-04 closed the duplicate-copy UAT defect (2026-07-14); commit `b41d6693` closed the CR-01 parse-writer defect (2026-07-28). Both confirmed fixed in the current source tree as of 2026-07-29.

## Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A colliding admin metadata save returns a structured, sanitized 409 rather than an unhandled 500. | VERIFIED | `admin_arguments.py` checks the final pair with self-exclusion; `admin.py` maps pre-check and exact named-constraint races to the same structured response. |
| 2 | A unique, partial, unchanged, self, or NULL-pair metadata save continues to follow PostgreSQL uniqueness semantics. | VERIFIED | Service tests cover final-pair construction, self-exclusion, unchanged values, and NULL short-circuit behavior. |
| 3 | Only the exact named database constraint enters duplicate recovery. | VERIFIED | `argument_uniqueness.py` reads structured constraint metadata and tests reject message-only and unrelated failures. |
| 4 | Ingest handles only the named pair violation as a duplicate. | VERIFIED | The shared classifier controls the duplicate channel; unrelated integrity errors are re-raised and behaviorally tested. |
| 5 | ConvoKit preserves its counter/rollback behavior only for the named collision. | VERIFIED | Named and non-target paths are separated and behaviorally tested. |
| 6 | Parse pre-checks only a docket fill that can occur and preserves an existing operator docket. | **VERIFIED (fixed by commit b41d6693, 2026-07-28)** | `pipeline/commands/parse.py` now guards both the `find_argument_by_pair` lookup and the update inside `if argument_row is not None and argument_row.source_docket is None:` — confirmed by direct re-read 2026-07-29. `test_parse_preserves_operator_docket_when_extracted_pair_conflicts` proves an existing operator docket survives a conflicting extracted value. |
| 7 | Parse excludes self, permits NULL question, and classifies a raced named violation narrowly. | VERIFIED | The shared lookup receives `exclude_argument_id`; NULL is handled by the helper; the flush catch uses the exact classifier. Truth 6's blocker is resolved, so this is no longer conditional. |
| 8 | Both SvelteKit actions validate the duplicate shape and preserve attempted metadata on failures. | VERIFIED | Both actions validate code/message/positive numeric id and return docket/question/date values through failure branches. |
| 9 | The shared alert preserves focus and safe numeric new-tab recovery behavior. | VERIFIED | Source contracts pass, and UAT confirmed both routes, keyboard focus/navigation, retained values, and `window.opener === null`. |
| 10 | Duplicate recovery copy appears exactly once with identical factual pre-check/race messages. | VERIFIED | Plan 33-04 removed link wording from both API builders; exact route and composed-copy regressions pass. |

## CR-01 Validation

**Original finding (2026-07-14):** CR-01 was confirmed, not refuted. The order at the time was: (1) load the argument and its question number, (2) look up the extracted `(docket, question)` pair and raise on conflict, (3) attempt an update guarded by `Argument.source_docket.is_(None)`. For an argument whose operator docket was already non-NULL, step 3 couldn't write anything, yet step 2 could still raise because another argument owned the *extracted* pair — violating the plan truth that parse performs a conditional docket fill while preserving operator-entered data.

**Fix (commit b41d6693, 2026-07-28):** Step 2's lookup was moved inside the same `argument_row.source_docket is None` guard as step 3, so an already-set operator docket short-circuits before the lookup ever runs — no conflict can be raised for a fill that was never going to write anything. `pipeline/tests/test_parse.py::test_parse_docket_fill_uses_pair_precheck_and_named_race_classification` (the original token-only test flagged below as misleading) was also strengthened to assert `"argument_row.source_docket is None"` appears in the guarded source. A new behavioral test, `test_parse_preserves_operator_docket_when_extracted_pair_conflicts`, exercises the actual state transition: constructs a target Argument with an existing operator docket and a separate conflicting Argument sharing the extracted `(docket, question_number)` pair, runs real `run_parse`, and asserts no exception is raised and the operator's docket is unchanged afterward.

## Artifact and Wiring Check

- The shared uniqueness helper exists, is substantive, and is wired into the admin service plus ingest, ConvoKit, and parse.
- Admin pre-check/race recovery is wired through both SvelteKit actions to the shared card.
- Plan 33-04 is substantive and correctly gives the component sole ownership of `Open conflicting argument`.
- Parse's wiring was semantically too broad (lookup outside the existing-docket guard) at original verification time; commit `b41d6693` (2026-07-28) narrowed it to match, confirmed by direct re-read 2026-07-29.

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
| PIPE-27 | **SATISFIED** | The admin requirement was already handled at original verification. CR-01 (the offline parse-writer consistency gap) is now also resolved by commit `b41d6693` — confirmed by direct source re-read 2026-07-29. Consistency across every pair-writing path is achieved. |

## Required Next Action (resolved)

~~Create and execute a gap-closure plan that moves the parse pre-check and update inside an `argument_row.source_docket is None` guard, retains the named-constraint race catch, and adds a behavioral test for an existing operator docket plus a conflicting extracted docket. Re-run Phase 33 verification afterward.~~ Done via commit `b41d6693` (2026-07-28), outside the formal plan sequence. No further action needed.

## Disconfirmation Pass (original, 2026-07-14 — superseded by the fix above)

- **Partially met requirement:** all writers import the shared helper, but parse invokes it when no write is eligible. *(Fixed: parse now short-circuits before invoking it when no write is eligible.)*
- **Misleading passing test:** `test_parse_docket_fill_uses_pair_precheck_and_named_race_classification` verifies tokens, not control flow. *(Strengthened, and supplemented with a real behavioral test — see CR-01 Validation above.)*
- **Uncovered error path:** existing non-NULL operator docket + extracted docket owned by another argument. *(Now covered by `test_parse_preserves_operator_docket_when_extracted_pair_conflicts`.)*

---
*Verifier: Codex generic-agent workaround for gsd-verifier*
