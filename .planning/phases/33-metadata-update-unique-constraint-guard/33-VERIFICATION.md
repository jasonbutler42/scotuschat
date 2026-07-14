---
phase: 33-metadata-update-unique-constraint-guard
verified: 2026-07-14T13:04:31Z
status: human_needed
score: 9/9 automated must-haves verified
behavior_unverified: 1
overrides_applied: 0
human_verification:
  - "Exercise duplicate metadata saves through both admin routes and confirm value retention, alert focus, and safe new-tab navigation."
---

# Phase 33: Metadata Update Unique-Constraint Guard Verification

**Phase goal:** Guard metadata updates against the `(source_docket, question_number)` unique constraint across the admin service and every offline writer, returning exact sanitized recovery instead of an unhandled 500.

**Status:** `human_needed` — implementation and automated behavior pass; one planned browser accessibility check remains.

## Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A colliding admin metadata save returns a structured 409 rather than an unhandled 500. | VERIFIED | `api/services/admin_arguments.py` computes the final pair with self-exclusion and raises `DuplicateArgumentError`; `api/routers/admin.py` maps both the pre-check and exact named-constraint race to `duplicate_argument` 409 payloads. Route tests cover both paths and sanitization. |
| 2 | A unique metadata save continues to succeed. | VERIFIED | The existing update path remains intact after the pre-check and commits normally; `test_admin_arguments_service.py` exercises non-colliding/NULL/self cases and the focused suite passes. |
| 3 | The canonical predicate matches PostgreSQL NULL semantics and excludes the row being edited. | VERIFIED | `api/services/argument_uniqueness.py::find_argument_by_pair` returns early for either NULL and adds `Argument.id != exclude_argument_id` when supplied. |
| 4 | Only the exact named database constraint enters duplicate recovery. | VERIFIED | `is_argument_pair_violation` walks structured `constraint_name`/`diag.constraint_name` data and exception chains cycle-safely; raw message text is not classified. Tests prove message-only and unrelated constraints do not match. |
| 5 | Ingest handles only the named pair violation as a duplicate. | VERIFIED | `pipeline/commands/ingest.py` classifies `IntegrityError` with the shared helper and re-raises unrelated failures. |
| 6 | ConvoKit handles only the named race through its conflict counter/channel. | VERIFIED | `pipeline/commands/import_convokit.py` uses the shared classifier, rolls back and increments `docket_question_conflict` only for the named constraint, and re-raises unrelated failures. |
| 7 | Parse guards its conditional docket write with final-pair/self semantics and exact race classification. | VERIFIED | `pipeline/commands/parse.py` combines extracted docket with stored question, excludes the current id, flushes the conditional update, and maps only the named race to sanitized `ValueError`. |
| 8 | Both SvelteKit actions accept only the validated duplicate shape and preserve all attempted metadata on every failure. | VERIFIED | Both `+page.server.ts` actions require `duplicate_argument`, a non-empty message, and a positive integer conflict id; all failure branches return docket/question/date attempted values. Focused source-contract tests pass. |
| 9 | The shared card renders one accessible recovery alert and a locally constructed safe conflict link. | VERIFIED | `ArgumentDetailsCard.svelte` uses one `role=alert` with `tabindex=-1`, runs `update()` then `tick()` then focus, and builds `/admin/arguments/{numeric id}` with `_blank` plus `noopener noreferrer`. `svelte-check` reports 0 errors. |

## Artifact and Wiring Verification

- `api/services/argument_uniqueness.py` is substantive and imported by the admin service and all three offline commands.
- `api/services/admin_arguments.py` wires final-pair calculation to the shared lookup and preserves the raced pair on `IntegrityError` for post-rollback recovery.
- `api/routers/admin.py` performs rollback before winner lookup and never exposes raw database text.
- Both admin form actions consume the FastAPI contract and feed the same `ArgumentDetailsCard.svelte` recovery surface.
- A repository-wide writer scan found the production pair writers in ingest, ConvoKit, parse, and the admin metadata service; each is covered by this implementation. Other matches are models, reads, or tests.

The automated artifact parser could not interpret the plans' free-form artifact strings (`No must_haves.artifacts found in frontmatter`), so artifact existence, substance, and wiring were verified directly from source.

## Verification Runs

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py pipeline/tests/test_ingest.py pipeline/tests/test_import_convokit_core.py pipeline/tests/test_parse.py api/tests/test_question_number_nullable.py -q` | `99 passed in 38.83s` |
| `npm --prefix app run check` | `0 errors, 16 warnings`; warnings are outside the Phase 33 behavior and include pre-existing reactive-state/a11y warnings. |

## Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| PIPE-27 | SATISFIED, pending human UI check | All three roadmap success criteria and all plan truths are implemented and covered by the passing focused suites. |

## Human Verification Required

### Duplicate recovery through both admin routes

**Test:** In a running admin UI, submit the same colliding docket/question pair once from the pipeline job page and once from the direct argument page.

**Expected:** Both routes preserve dockets, question number, and argued date; focus lands on the single inline alert; its link is keyboard reachable, opens the numeric conflicting argument in a new tab, and the opener is isolated.

**Why human:** The source contract and type-check prove the wiring, but browser focus movement, value presentation, and new-tab behavior require an actual browser interaction.

## Disconfirmation Pass

- Partial requirement sought: no production pair writer was found outside the four guarded paths; global assignment/constructor scanning found only those paths plus models/tests.
- Misleading test sought: the frontend tests are source-contract assertions rather than browser behavior, so they are not used to claim the remaining focus/new-tab behavior is fully proven.
- Uncovered error path sought: unrelated `IntegrityError` paths are explicitly tested for the backend and offline writers; malformed/non-OK/network frontend responses are sanitized and retain attempted values, but final browser presentation remains the human item above.

## Gaps Summary

No implementation gaps found. Phase 33 is automated-verification complete, with one non-blocking human UAT item required before a fully `passed` verdict.

---
*Verifier: Codex generic-agent workaround for gsd-verifier*
