---
phase: 38-full-name-vs-name-parts-rethink
reviewed: 2026-07-27T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - api/domain/docket_values.py
  - api/tests/fixtures/docket_value_cases.json
  - api/tests/test_docket_values.py
  - api/routers/admin.py
  - api/tests/test_docket_arg_safety.py
  - pipeline/commands/ingest.py
  - pipeline/tests/test_ingest.py
  - app/src/lib/docketValues.ts
  - api/tests/test_docket_ui_contract.py
  - app/src/lib/components/DocketPillInput.svelte
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/+page.server.ts
  - api/tests/test_question_number_nullable.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 38: Gap Closure Code Review Report (G-38-6)

**Reviewed:** 2026-07-27
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found (no blockers — warnings/info only)

## Summary

This is a focused security gap-closure review of plans 38-07 through 38-10, which close UAT gap G-38-6: an authenticated-admin path-traversal / arbitrary-file-write primitive where an unvalidated `primary_docket`/`source_dockets` value could reach `Path("data/pdfs") / f"{primary_docket}-q{n}.pdf"` in `pipeline/commands/ingest.py`.

**The vulnerability is closed.** I traced the fix adversarially across all three layers and could not construct a bypass:

- **Domain rule** (`api/domain/docket_values.py`): `DOCKET_VALUE_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_-]*$"` is a strict allow-list (not a blocklist) — no `/`, `\`, `.`, quote, whitespace, or control character (including NUL) can ever match, and the pattern is anchored with `re.fullmatch`, so a trailing newline cannot slip past. This alone independently blocks POSIX-absolute paths, Windows drive-letter paths, `..` traversal, and CLI-flag-like leading hyphens (first char must be alphanumeric) — verified against every case in `docket_value_cases.json`, including the raw UAT-reported string.
- **API boundary** (`api/routers/admin.py::_normalize_dockets`): calls `normalize_docket_value` on every `primary_docket`/`source_dockets` entry before `create_job` ever creates an `AdminJob` row or spawns the ingest subprocess. Fails closed (422) with a bounded, `!r`-escaped error message (no raw control-character/log-injection surface, no secret leakage).
- **Pipeline second layer** (`pipeline/commands/ingest.py::_validate_docket_value` + the `resolved_pdf_path.parent != resolved_pdf_dir` containment assertion): re-validates independently of FastAPI, so a direct CLI invocation that bypasses the API entirely is still covered. The containment assertion is a genuine second backstop — I confirmed it is evaluated on the fully resolved path *before* any of the four download branches (existing-file skip, local-file copy, Spaces download, HTTP download) can execute, and I confirmed via `pipeline/db.py::get_session` that any `ValueError` raised mid-transaction during the later per-docket Case-row loop triggers a full `session.rollback()` — there is no partial-write window.
- **UI layer** (`docketValues.ts` + `DocketPillInput.svelte` + `+page.server.ts`): explicitly documented and implemented as advisory-only; the SvelteKit server action re-validates every `docket[]` value server-side (a forged hidden input bypasses the browser check but not this layer), and this in turn is still gated by the two backend layers above. Pattern/length-cap parity between Python and TypeScript is locked by `test_docket_ui_contract.py`'s source-extraction-plus-replay strategy, which I verified actually extracts the live literals rather than hand-copying them.

I also independently verified the two claims underpinning the fix's scope decision (not just trusted the comments): `ArgumentUpdate.docket_number` and `MetadataUpdate.source_docket` (post-ingest edit paths, intentionally left untightened) really do terminate at `Case.docket_number`/`Argument.source_docket` column writes in `api/services/admin_arguments.py::update_argument` — `Case.slug` is derived only from `case_name`, never from `docket_number`, on both the DRAFT and frozen-slug branches. So the "post-ingest editing never reaches a filesystem path" premise holds and the narrower scope is sound, not a hidden hole.

The `api/tests/test_question_number_nullable.py` diff (lines 166–174) was re-checked line-for-line against the new `DocketPillInput.svelte` state: `hasError = $derived(!readonly && (invalid || Boolean(shapeError)))` and the `describedByIds` composition are asserted verbatim and match the component exactly. The updated assertions still meaningfully prove the pre-existing `aria-invalid`/`aria-describedby` contract holds (they reduce to the original behavior whenever `shapeError` is inactive, which is the case for every caller besides the Pipeline Runner).

No Critical/Blocker findings. A small number of Warning/Info items follow — none of them reopen the path-traversal class.

## Warnings

### WR-01: No end-to-end test exercises the pipeline guard through the full ingest flow

**File:** `pipeline/tests/test_ingest.py:120-213`
**Issue:** Coverage for the G-38-6 pipeline-layer guard is unit-level (`_validate_docket_value` called directly with hazardous values) plus two static "is the call present in source" assertions (`test_docket_guard_invoked_inside_run_ingest_inner`, `test_containment_assertion_present_inside_run_ingest_inner`). No test actually drives `_run_ingest_inner`/`run_ingest` end-to-end (even under the existing `async_session`/DB-required test tier) with a hazardous `primary_docket` or consolidated docket to prove the ValueError surfaces *through* the real call path — with the session rollback actually exercised — rather than only proving the helper function and the call-site string both individually exist. A future refactor that calls `_validate_docket_value` but silently swallows its exception (e.g. an errant `try/except: pass` introduced elsewhere in `_run_ingest_inner`) would not be caught by either existing test.
**Fix:** Add one DB-gated test (mirroring the pattern already used by `test_ingest_creates_pipeline_run`) that calls `run_ingest`/`_run_ingest_inner` with `primary_docket="../../../tmp/evil"` (or similar) and asserts (a) the call raises, (b) no `PipelineRun`/`Case`/`Argument` rows were persisted, and (c) `pdf_path.exists()` is `False` for the malicious target.

## Info

### IN-01: T-24-08 leading-hyphen message is not mirrored client-side

**File:** `api/routers/admin.py:177-182` vs. `app/src/lib/docketValues.ts:75-98`
**Issue:** `_normalize_dockets` raises a bespoke 422 ("`Docket value '-1' cannot start with '-'.`") for leading-hyphen values via its own `startswith("-")` pre-check, independent of `normalize_docket_value`. `normalizeDocketValue` (TS) has no equivalent pre-check — a leading-hyphen docket typed into `DocketPillInput` or resubmitted through `+page.server.ts` instead surfaces the generic `docketValueErrorMessage('invalid_characters')` copy ("Dockets may only use letters, numbers, hyphens, and underscores."). Both layers reject the value (no security gap — the domain regex's `[A-Za-z0-9]` leading-character requirement already subsumes this class on its own), this is copy-only.
**Fix:** Low priority; if operator-facing wording consistency matters, add a `startswith('-')` pre-check to the TS mirror with the matching message, or drop the API's bespoke branch now that the domain rule alone covers it.

### IN-02: Unreachable `'empty'` branch at two call sites

**File:** `app/src/lib/components/DocketPillInput.svelte:80-99`, `api/routers/admin.py:173-182`
**Issue:** In `DocketPillInput.addPill()`, the `enforceShape` branch's `if (!v || pills.includes(v)) return;` guard runs before `normalizeDocketValue(v)` is ever called, so the `'empty'` `DocketValueError` code (and its corresponding `docketValueErrorMessage` case) can never actually be thrown from this call site. Symmetrically, `_normalize_dockets._add` in `admin.py` filters `if not stripped ... return` before calling `normalize_docket_value`, so its `'empty'` code path is likewise unreachable there. Harmless (both guards are logically correct, just redundant with the shared module's own blank-check), but worth knowing when reasoning about test coverage for the `'empty'` code — it is only exercised directly against `normalize_docket_value`/`normalizeDocketValue`, never through either UI/API call site.
**Fix:** None required. Optional: a one-line comment at each site noting the guard makes the module's own `'empty'` branch unreachable there, to save a future reader the trace.

### IN-03: `_validate_docket_value`'s structural checks use platform-dependent `PurePath`

**File:** `pipeline/commands/ingest.py:63-124`
**Issue:** `_validate_docket_value` uses `PurePath` (which resolves to `PurePosixPath` or `PureWindowsPath` depending on the host OS) for its `is_absolute()`/`.parts` structural backstop. On a POSIX deployment (this project's stated DO App Platform / Linux target per `CLAUDE.md`) this is correct and the check is in any case redundant with the character allow-list, which already forbids `/`, `\`, and `:` outright — so there is no exploitable gap today. If this pipeline command were ever run on Windows (e.g. a developer laptop performing a direct CLI ingest), `PurePath("C:\\Windows\\evil.pdf").is_absolute()` would evaluate as `PureWindowsPath` semantics rather than `PurePosixPath`, which is actually the *more* correct behavior for that platform — so this is a non-issue, noted only for completeness since the docstring's phrasing ("Uses PurePath rather than the module-level Path... for testability") could be read as implying deliberate POSIX-only reasoning.
**Fix:** None required.

---

_Reviewed: 2026-07-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
