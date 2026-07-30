---
phase: 42-corpus-import-fidelity-diff-fix
reviewed: 2026-07-30T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - pipeline/__main__.py
  - pipeline/commands/import_convokit.py
  - pipeline/corpus/apolitical.py
  - pipeline/corpus/loader.py
  - pipeline/tests/test_corpus_loader.py
  - pipeline/tests/test_delete_fixture_argument.py
  - pipeline/tests/test_diff_corpus_fixture.py
  - pipeline/tests/test_import_convokit_bench_tenure.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_import_convokit_utterances.py
  - scripts/delete_fixture_argument.py
  - scripts/diff_corpus_fixture.py
findings:
  critical: 1
  warning: 4
  info: 0
  total: 5
status: issues_found
---

# Phase 42: Code Review Report

**Reviewed:** 2026-07-30
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

All 82 tests across the six modified/added test files pass locally (verified
by running each suite through `./.venv/Scripts/python.exe -m pytest`), and
the implementation matches its own test suite closely. Cascade-delete safety
(`scripts/delete_fixture_argument.py`) is solid: every statement is scoped by
a looked-up integer `argument_id`/`case_id`, the whole routine runs inside
`pipeline.db.get_session()`'s single commit/rollback boundary (confirmed by
reading `pipeline/db.py`), it defaults to report-only, and the rollback test
proves a mid-cascade failure undoes earlier steps of the same cascade. The
`--conversation-id` scoped-import path (`pipeline/__main__.py`,
`pipeline/commands/import_convokit.py`) correctly narrows both the
conversations dict and the utterances streaming pass to exactly one
conversation before any DB write happens, so no full-term or full-corpus
import is triggered as a side effect. The apolitical hard constraint holds
for the six named `FORBIDDEN_FIELDS` in both the importer (verified by
`test_apolitical_fields_never_persisted_to_any_column`) and the diff
generator (verified by `test_every_forbidden_field_sentinel_value_is_absent`).

That said, adversarial review of `scripts/diff_corpus_fixture.py` — the one
module whose entire purpose is to be a trustworthy fidelity report — found a
provable **factual misclassification** (a raw field the importer never reads
is reported as "Faithful"/consumed), plus a **docstring/behavior mismatch**
that overstates the tool's redaction guarantee for fields outside the
literal `FORBIDDEN_FIELDS` list. Both weaken exactly the kind of review this
document exists to support (Phase 42's D-05/D-06 operator batch review). Two
further, lower-severity gaps are noted in `import_convokit.py`'s term
derivation and `delete_fixture_argument.py`'s reporting completeness.

## Critical Issues

### CR-01: Fidelity diff falsely reports a dead/unused raw field as "Faithful"

**File:** `scripts/diff_corpus_fixture.py:405-432` (`_CASE_DESTINATIONS["advocates"]`), consumed by `_build_cases_rows` at `scripts/diff_corpus_fixture.py:454-477`

**Issue:** `_CASE_DESTINATIONS` classifies the raw case-level `advocates` field as:
```python
"advocates": (
    "(not persisted verbatim -- consumed transiently by the advocate-resolution loop)",
    "Faithful",
),
```
This is factually wrong. `pipeline.corpus.apolitical.extract_case_fields` does extract a case-level `"advocates"` key (`pipeline/corpus/apolitical.py:68`), but `pipeline/commands/import_convokit.py` never reads it — grepping the whole module confirms `case_fields.get("advocates")` / `case_fields["advocates"]` appears nowhere. The actual advocate-resolution loop reads only the **conversation-level** advocates dict:
```python
advocates = conversation.get("advocates") or {}   # import_convokit.py:570
```
(`conversation` here is `apolitical.extract_conversation_fields(raw_conversation)`'s output, a completely different dict from `case_fields`.)

So the case-level `advocates` field extracted by `extract_case_fields` is dead — extracted but never consumed anywhere in the codebase — yet the diff tool tells the operator it is "Faithful" and "consumed." This is exactly the class of silent-drop the fidelity diff exists to surface (compare the tool's own correct handling of the conversation-level `conversation_id` dead key at `scripts/diff_corpus_fixture.py:509-523`, which IS flagged as a dead key). A false "Faithful" verdict here could cause the operator to sign off during the D-06 batch review without ever learning that this field is a no-op, defeating the purpose of CORPUS-13.

**Fix:**
```python
"advocates": (
    "(no column -- case-level `advocates` dict is extracted by "
    "extract_case_fields but never read anywhere; only the "
    "CONVERSATION-level `advocates` dict, from extract_conversation_fields, "
    "is consumed by the advocate-resolution loop)",
    "Dropped",
),
```
and give it a `classification` (e.g. `"dead key"` or `"schema-absent field"`) and `reason` string in `_build_cases_rows`, mirroring how the conversation-level `conversation_id` dead key is already documented.

## Warnings

### WR-01: Module docstring overstates the redaction guarantee for non-forbidden dropped fields

**File:** `scripts/diff_corpus_fixture.py:19-31` (module docstring) vs. `scripts/diff_corpus_fixture.py:205-222` (`_proposed_dropped_row`) and `:437-481` (`_build_cases_rows`)

**Issue:** The module docstring states:
> "the corresponding VALUE is only ever emitted when the key survives into the extractor's returned dict; every other key's value column prints a fixed redaction marker, never the real value, even for a name already known to be forbidden."

That is not what the code does. `_build_cases_rows` redacts a raw key only when it is literally in `apolitical.FORBIDDEN_FIELDS` (`scripts/diff_corpus_fixture.py:441-452`, correctly verified by `test_every_forbidden_field_sentinel_value_is_absent`). For any OTHER raw key that is neither forbidden nor read by `extract_case_fields` — e.g. `is_eq_divided` (called out by `pipeline/corpus/apolitical.py:19-31`'s own "Documentation-completeness note" as a real, currently-unlisted outcome-adjacent field the raw corpus carries), or any future field the raw corpus adds before anyone updates `FORBIDDEN_FIELDS` — `_proposed_dropped_row(raw_key, raw_case[raw_key])` embeds the **literal raw value** into the generated document. `pipeline/tests/test_diff_corpus_fixture.py`'s own fixture (`_sentinel_case_fields`'s `"url"` field, `TestProposalClassification`) exercises this exact path and only asserts the row is `PROPOSED`, never asserts the value is hidden — confirming this is the actual, intended (if inaccurately documented) behavior.

Given this script's documented usage is `python scripts/diff_corpus_fixture.py --conversation-id 15169 --out .planning/CORPUS-FIDELITY-DIFF.md` (a path that gets committed), this is a real defense-in-depth gap for the apolitical hard constraint: the literal, named `FORBIDDEN_FIELDS` are correctly protected, but the module's own stated design principle ("Raw corpus dicts must NEVER be passed into ORM constructors ... except through the functions defined here", `pipeline/corpus/apolitical.py:1-17`) is not actually honored by this reporting tool for any raw field the maintainers haven't yet thought to enumerate.

**Fix:** Either (a) correct the docstring to say "every **forbidden** key's value column..." so it accurately describes current behavior, or (b) — preferable given the stated hard constraint — redact the raw value for every key that is not in the extractor's own allowlisted output, printing only the field NAME plus a "not on the allowlist" marker, never the literal raw value, for every dropped-before-the-allowlist row (not just forbidden ones).

### WR-02: `--conversation-id` term derivation accepts a case_id with no underscore and silently derives a bogus term

**File:** `pipeline/commands/import_convokit.py:232-240` (`_resolve_scoped_conversation`)

**Issue:**
```python
case_id = raw_conversation.get("case_id")
term_prefix = str(case_id).split("_", 1)[0] if case_id else ""
try:
    term = int(term_prefix)
except ValueError:
    raise argparse.ArgumentTypeError(...)
```
If `case_id` is a malformed value with no underscore at all but is still numeric-looking (e.g. `"642"` instead of `"1966_642"`), `split("_", 1)[0]` returns the whole string, `int("642")` succeeds, and the function silently returns `term=642` — an invalid October Term — instead of raising a clear, targeted error about the malformed `case_id`. The bad input is only caught later, indirectly, inside `run_import_convokit` as `"--conversation-id ... was not found among term 642's conversations after narrowing"` (`pipeline/commands/import_convokit.py:1262-1267`), which misattributes the root cause (looks like a term-filtering miss, not a malformed `case_id`). The existing test suite only covers the non-numeric-prefix case (`"not-a-term_642"`), not the no-underscore case, so this path is untested.

**Fix:**
```python
case_id_str = str(case_id) if case_id else ""
if "_" not in case_id_str:
    raise argparse.ArgumentTypeError(
        f"--conversation-id {conversation_id!r} has a case_id {case_id!r} "
        "with no '<term>_<docket>' prefix -- cannot derive its October Term."
    )
term_prefix = case_id_str.split("_", 1)[0]
```

### WR-03: Conversation-level `FORBIDDEN_FIELDS` reporting is incomplete relative to the cases-table section

**File:** `scripts/diff_corpus_fixture.py:580-592` (`_build_arguments_rows`)

**Issue:** `_build_cases_rows` iterates every key actually present in `raw_case` and redacts any that match `FORBIDDEN_FIELDS` (`scripts/diff_corpus_fixture.py:440-452`) — a complete, data-driven sweep. `_build_arguments_rows`, by contrast, hardcodes only two of the six forbidden field names for the conversation-level report:
```python
for forbidden_name in sorted(apolitical.FORBIDDEN_FIELDS):
    if forbidden_name in ("win_side", "votes_side"):
        rows.append(...)
```
If a raw conversation record also carries `win_side_detail`, `votes`, `votes_detail`, or `scdb_docket_id` at the top level, this section never mentions them at all (neither leaked nor documented as excluded) — an asymmetric, incomplete accounting compared to the cases section, and a gap relative to the stated design goal of a complete field-by-field inventory.

**Fix:** Iterate `raw_conversation.keys()` the same way `_build_cases_rows` iterates `raw_case.keys()`, so every forbidden field actually present at the conversation level is reported consistently, regardless of which of the six names it happens to be.

### WR-04: Destructive-delete report omits the `admin_jobs` nullification from its pre-flight inventory

**File:** `scripts/delete_fixture_argument.py:80-86` (`DEPENDENT_MODELS`), `:159-163` (reporting loop), `:204-209` (destructive `AdminJob` update)

**Issue:** The script's docstring promises identical, complete reporting in both report-only and destructive mode ("Reporting: identical inventory in both report-only and destructive mode, printed BEFORE any delete statement runs", line 157-158), and step 6 of its own documented cascade order is "`admin_jobs.argument_id` set NULL." However, `DEPENDENT_MODELS` (the list the reporting loop iterates) only contains the five hard-delete tables — `AdminJob` is never counted or printed before the operator decides whether to pass `--yes`. An operator relying on the printed report to judge blast radius sees nothing about how many paused resolve-admin-job rows will be detached from this argument.

**Fix:** Add an explicit count-and-print step for `AdminJob` rows matching `argument_id` alongside the `DEPENDENT_MODELS` loop, e.g.:
```python
admin_job_count = await session.execute(
    select(func.count()).select_from(AdminJob).where(AdminJob.argument_id == argument_id)
)
print(f"  admin_jobs (argument_id set NULL, not deleted): {admin_job_count.scalar_one()}")
```

---

_Reviewed: 2026-07-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
