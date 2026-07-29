---
phase: 33-metadata-update-unique-constraint-guard
reviewed: 2026-07-14T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - api/routers/admin.py
  - api/services/admin_arguments.py
  - api/services/argument_uniqueness.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_question_number_nullable.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_ingest.py
  - pipeline/tests/test_parse.py
findings:
  critical: 1
  warning: 0
  info: 0
  total: 1
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-07-14T00:00:00Z
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The named-constraint classification and admin metadata race handling are narrowly scoped and avoid exposing database errors. However, the parse-side preflight applies the extracted docket conflict check before honoring the existing write-if-null condition. This can fail an otherwise valid parse even though no conflicting metadata write would occur.

## Narrative Findings (AI reviewer)

## Critical Issues

### CR-01: Parse rejects extracted docket conflicts even when the docket is not writable

**File:** `pipeline/commands/parse.py:374-387`

**Issue:** Block D is documented and implemented as a conditional write that must preserve an operator-entered `Argument.source_docket`. The new conflict lookup nevertheless runs whenever the cover contains `primary_docket`, regardless of whether the argument already has a docket. If an argument already stores docket `A` and the cover extracts docket `B`, and another argument owns `(B, question_number)`, `find_argument_by_pair` returns that other argument and the parse raises `ValueError`. The subsequent SQL update would have been a no-op because of `Argument.source_docket.is_(None)`, so this turns harmless extracted metadata into a pipeline failure and violates the operator-value preservation contract.

**Fix:** Fetch the argument first and perform both the precheck and conditional update only when its current `source_docket` is `None`. Keep the database constraint catch for the race between the precheck and update. For example:

```python
argument_row = await session.get(Argument, source_run.argument_id)
if argument_row is not None and argument_row.source_docket is None:
    question_number = argument_row.question_number
    conflict_id = await find_argument_by_pair(
        session,
        cover_meta["primary_docket"],
        question_number,
        exclude_argument_id=source_run.argument_id,
    )
    if conflict_id is not None:
        raise ValueError("Parse metadata conflict: ...")
    # Execute the guarded update and retain the IntegrityError race classifier.
```

Add a behavioral regression test where the source argument already has an operator docket, the extracted docket conflicts with another argument, and parsing continues without changing the operator docket. The current `inspect.getsource` test in `pipeline/tests/test_parse.py:25-31` cannot detect this control-flow error.

---

_Reviewed: 2026-07-14T00:00:00Z_
_Reviewer: the agent (gsd-code-reviewer; generic-agent workaround)_
_Depth: standard_
