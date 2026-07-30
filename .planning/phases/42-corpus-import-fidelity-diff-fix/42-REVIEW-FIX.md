---
phase: 42-corpus-import-fidelity-diff-fix
fixed_at: 2026-07-30T20:55:00Z
review_path: .planning/phases/42-corpus-import-fidelity-diff-fix/42-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 42: Code Review Fix Report

**Fixed at:** 2026-07-30T20:55:00Z
**Source review:** .planning/phases/42-corpus-import-fidelity-diff-fix/42-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, WR-03, WR-04 — `fix_scope: critical_warning`)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Fidelity diff falsely reports a dead/unused raw field as "Faithful"

**Files modified:** `scripts/diff_corpus_fixture.py`
**Commit:** `3b00419c`
**Applied fix:** Changed `_CASE_DESTINATIONS["advocates"]` from `("... consumed transiently ...", "Faithful")` to a `"Dropped"` verdict with a corrected note explaining that the case-level `advocates` dict is extracted by `extract_case_fields` but never read by `import_convokit.py` (only the conversation-level `advocates` dict, from `extract_conversation_fields`, feeds the advocate-resolution loop). Added a `_CASE_DEAD_KEYS = {"advocates"}` set and updated `_build_cases_rows` to emit a `"dead key"` classification with an explanatory reason for this field, mirroring how the conversation-level `conversation_id` dead key is already documented.

### WR-01: Module docstring overstates the redaction guarantee for non-forbidden dropped fields

**Files modified:** `scripts/diff_corpus_fixture.py`
**Commit:** `5e6bf9ad`
**Applied fix:** Chose option (b) from the review (closing the gap in code rather than weakening the docstring). Added a new fixed marker `NOT_ALLOWLISTED`. `_proposed_dropped_row` no longer embeds the literal raw value for any field that is dropped before it reaches an apolitical extractor's returned dict — it now always renders `NOT_ALLOWLISTED` regardless of the raw value passed in (the `raw_value` parameter is accepted-and-ignored via `del raw_value` to avoid a signature-shape change at the single call site). This makes the module docstring's existing claim ("every other key's value column prints a fixed redaction marker, never the real value, even for a name already known to be forbidden") actually true for every dropped-before-the-allowlist field, not just the six named `FORBIDDEN_FIELDS`.

### WR-02: `--conversation-id` term derivation accepts a case_id with no underscore and silently derives a bogus term

**Files modified:** `pipeline/commands/import_convokit.py`
**Commit:** `3499acc2`
**Applied fix:** In `_resolve_scoped_conversation`, added an explicit `if "_" not in case_id_str` check before splitting on `"_"`, raising a targeted `argparse.ArgumentTypeError` naming both the `--conversation-id` value and the malformed `case_id` when no `<term>_<docket>` prefix separator exists, instead of letting `int(term_prefix)` silently succeed on the whole (numeric-looking) string. The pre-existing "missing case_id" test (`test_raises_when_case_id_is_missing`, which only matches the conversation id `"15169"` in the raised message, not exact wording) and the "non-numeric-prefix" test (`test_raises_when_case_id_has_no_parseable_term_prefix`, whose `"not-a-term_642"` fixture still contains an underscore and falls through unchanged to the pre-existing `ValueError` branch) both continue to pass unmodified.
**Note:** This finding is a logic-correctness fix (input-validation branch), not purely mechanical — flagging as `fixed: requires human verification` per the reviewer's own guidance on logic-shaped fixes, even though all cited/existing tests pass. The specific "case_id with no underscore" scenario this fix targets has no dedicated regression test in the current suite (per REVIEW.md's own observation); a human should confirm the new error message and branch ordering read correctly before relying on it in production runs. The commit tool (`gsd-tools query commit`) reported `{"committed": false, "reason": "commit_failed"}` for this one fix despite `git log`/`git status` confirming the commit landed cleanly (`3499acc2`, clean working tree) — noted here for transparency, but treated as fixed since the git state is unambiguous.

### WR-03: Conversation-level `FORBIDDEN_FIELDS` reporting is incomplete relative to the cases-table section

**Files modified:** `scripts/diff_corpus_fixture.py`
**Commit:** `eada7f50`
**Applied fix:** Added a `raw_conversation: dict` parameter to `_build_arguments_rows` (and threaded `raw["raw_conversation"]` through from the single call site in `_build_document`). Replaced the hardcoded `for forbidden_name in sorted(apolitical.FORBIDDEN_FIELDS): if forbidden_name in ("win_side", "votes_side")` loop with a data-driven sweep over `raw_conversation.keys()` — mirroring `_build_cases_rows`'s sweep over `raw_case.keys()` exactly: any of the six `FORBIDDEN_FIELDS` names actually present on the raw conversation record is redacted (fixed `REDACTED` marker, never the real value) and reported with the `"apolitical allow-list exclusion"` classification; a name not present on a given record is simply absent from that record's report, consistent with how the cases section already behaves. Verified the existing `win_side`/`votes_side` sentinel-value and classification tests (`TestApoliticalRedaction`) still pass unchanged, since the shared test fixture's raw conversation dict literally carries those two keys.

### WR-04: Destructive-delete report omits the `admin_jobs` nullification from its pre-flight inventory

**Files modified:** `scripts/delete_fixture_argument.py`
**Commit:** `f065f02a`
**Applied fix:** Added an explicit `AdminJob` count query and `print` statement immediately after the existing `DEPENDENT_MODELS` reporting loop (and before the report-only/destructive branch), so the operator sees `admin_jobs (argument_id set NULL, not deleted): N` in the pre-flight inventory in both report-only and destructive mode, honoring the script's own docstring promise of "identical inventory ... printed BEFORE any delete statement runs." `AdminJob` was intentionally left out of `DEPENDENT_MODELS` itself since that list drives the destructive hard-delete loop and `AdminJob` rows are nullified, not deleted.

## Skipped Issues

None — all findings in scope were fixed.

---

**Verification:** After each fix, ran `./.venv/Scripts/python.exe -m pytest pipeline/tests/test_diff_corpus_fixture.py pipeline/tests/test_import_convokit_core.py pipeline/tests/test_delete_fixture_argument.py -q` from the fix worktree. Result held steady at `13 passed, 40 skipped` (skips are pre-existing DB-dependent tests not runnable in this sandbox) across the baseline and every subsequent fix, with no regressions introduced by any of the five commits.

_Fixed: 2026-07-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
