---
phase: 19-pipeline-reliability
verified: 2026-07-01T12:00:00Z
status: human_needed
score: 7/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Hint text from cover extraction — field shows 'Extracted: [value]' when stored value differs"
    expected: "For a job where the PDF cover extractor found a docket or date different from what is currently stored, the relevant field shows faint hint text 'Extracted: 14-556'. Fields where extracted and stored values match, or where cover_metadata is null, show no hint text."
    why_human: "UAT test 7 was skipped — no job with differing extracted vs. stored values was available at test time. The code logic is present and wired (optional-chaining null guards confirmed). Requires a live job where cover_metadata.primary_docket differs from Argument.source_docket."
  - test: "Start anyway — operator navigated to new job detail page (not logged out)"
    expected: "After Plan 05 fix: clicking Start anyway sets preflightCleared=true, calls formEl.requestSubmit(), handleSubmit hits the early-return branch, sets submitting=true, returns without preventDefault — native multipart POST completes and operator is navigated to new job detail page."
    why_human: "UAT test 5 failed before Plan 05. Plan 05 made three targeted code changes (formEl bound, onclick updated, document.querySelector removed). The fix is in the code. A human must re-run the Start anyway test to confirm the browser-level navigation outcome."
orphaned_requirements:
  - id: PIPE-DUP-05
    note: "Referenced in 19-05-PLAN.md and 19-05-SUMMARY.md but does not exist in REQUIREMENTS.md. This is an internal gap-closure sub-requirement tracking the Start anyway fix. Its intent is covered under PIPE-25 (duplicate prevention + UI warning). Not a blocker — the underlying behavior is addressed."
---

# Phase 19: Pipeline Reliability — Verification Report

**Phase Goal:** The pipeline cannot silently create duplicate arguments, and argument metadata extracted from the PDF cover is visible to the operator without manual entry
**Verified:** 2026-07-01T12:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Truths derived from ROADMAP.md Success Criteria plus PLAN frontmatter must_haves merged.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The database enforces a unique constraint on arguments such that re-running ingest for the same source cannot produce a second Argument row | VERIFIED | `UNIQUE CONSTRAINT uq_arguments_source_docket_question on (source_docket, question_number)` confirmed in both migration 0011 and `Argument.__table__.constraints` output at runtime. IntegrityError catch in ingest.py raises ValueError with readable message. |
| 2 | Operator sees a warning in the pipeline start UI before submitting if a matching argument already exists | VERIFIED | check-duplicate proxy +server.ts exists and wired correctly. +page.svelte contains the preflight fetch, duplicateWarning $state, and the role="alert" banner with "⚠ Argument already exists" heading. Banner shows docket/question and Cancel/Start anyway buttons. |
| 3 | After a pipeline run completes parse, case name, docket, and argued date fields are pre-populated from cover extraction results without the operator typing them manually | VERIFIED | Block C (cover_metadata unconditional write) and Block D (source_docket conditional write with .is_(None) guard) confirmed in parse.py. Block A WHERE clause includes `Argument.argued_date.is_(None)`. Metadata card in [job_id]/+page.svelte pre-populates inputs from data.argument values loaded from FastAPI ArgumentDetail which now includes source_docket and cover_metadata. |
| 4 | Operator can still override any pre-populated metadata field before publishing | VERIFIED | saveMetadata form action in [job_id]/+page.server.ts PATCHes FastAPI PATCH /api/admin/arguments/{id}/metadata. update_argument_metadata service updates Argument.argued_date, Argument.source_docket, and lead Case.case_name. Parse conditional logic (`.is_(None)`) ensures operator-entered values are never overwritten. |
| 5 | Migration 0011 adds source_docket, cover_metadata JSONB, makes argued_date nullable, and adds unique constraint | VERIFIED | All four operations confirmed in 0011_add_source_docket_cover_metadata.py. Runtime confirmation: Argument.__table__.c includes source_docket and cover_metadata; UniqueConstraint on source_docket + question_number confirmed. argued_date nullable confirmed. |
| 6 | cover_extractor.extract_cover_metadata extracts primary_docket key via DOCKET_RE | VERIFIED | DOCKET_RE = `re.compile(r'No\.\s+(\d{1,2}-\d+)', re.IGNORECASE)` at module level in cover_extractor.py. primary_docket extraction block in for-raw-in-raws loop confirmed. All four new docket tests pass (`test_docket_re_matches_alderson_format`, `test_docket_re_matches_longer_number`, `test_docket_re_no_match_when_absent`, `test_extract_cover_metadata_still_failsafe`). |
| 7 | Start anyway fix: clicking "Start anyway" submits the form without getting stuck in "Starting…" or logging the operator out | VERIFIED (code, behavior human-needed) | Plan 05 confirmed: `let formEl: HTMLFormElement` declared; `bind:this={formEl}` on form element; Start anyway onclick is `preflightCleared = true; duplicateWarning = null; formEl.requestSubmit()`. `document.querySelector` no longer present anywhere in +page.svelte. Structural correctness confirmed. Browser-level navigation outcome requires human re-test — see Human Verification section. |
| 8 | Hint text 'Extracted: [value]' appears below a field only when cover_metadata contains a value differing from the current field value | PRESENT_BEHAVIOR_UNVERIFIED | Code confirmed: optional-chaining null guards in +page.svelte; conditional render only when `cover_metadata.primary_docket != null && cover_metadata.primary_docket !== argument.source_docket` (same pattern for case_name and argued_date). UAT test 7 was skipped — no suitable test job available. Logic is present and wired; runtime rendering requires human verification. |

**Score:** 7/8 truths verified (1 present, behavior-unverified — hint text conditional rendering)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0011_add_source_docket_cover_metadata.py` | Migration with 4 operations + downgrade | VERIFIED | All 4 upgrade ops confirmed. Downgrade reverses in correct order. |
| `api/models/models.py` (Argument model) | source_docket, cover_metadata, argued_date nullable, UniqueConstraint | VERIFIED | Runtime column list: ['id', 'argued_date', 'question_number', 'resolved_at', 'published_at', 'status', 'source_docket', 'cover_metadata']. UniqueConstraint on source_docket + question_number confirmed. |
| `pipeline/parser/cover_extractor.py` | DOCKET_RE at module level; primary_docket extraction in loop | VERIFIED | Both present. Early-exit condition is `len(result) == 3`. Fail-safe `except Exception: pass` unchanged. |
| `pipeline/tests/test_cover_extractor.py` | 4 new docket test functions | VERIFIED | All 4 tests collected and passing. |
| `pipeline/commands/ingest.py` | IntegrityError import; source_docket on Argument; nullable argued_date; try/except wrapping flush | VERIFIED | All confirmed via grep. `IntegrityError` imported. `argued_date=date.fromisoformat(argued_date) if argued_date else None`. `source_docket=primary_docket or None`. IntegrityError raises ValueError with "Duplicate argument: docket" message. |
| `pipeline/commands/parse.py` | Block A conditional WHERE; Block C cover_metadata; Block D source_docket conditional | VERIFIED | All confirmed via grep. Block A WHERE includes `Argument.argued_date.is_(None)`. Block C unconditional cover_metadata UPDATE. Block D conditional with `Argument.source_docket.is_(None)`. All use `.execution_options(synchronize_session=False)`. |
| `api/schemas/admin_arguments.py` | MetadataUpdate class; ArgumentDetail.source_docket + cover_metadata; Optional argued_date | VERIFIED | Runtime: MetadataUpdate fields `['case_name', 'source_docket', 'argued_date']`. ArgumentDetail includes source_docket and cover_metadata fields. argued_date is not required (Optional). |
| `api/services/admin_arguments.py` | check_duplicate_argument; update_argument_metadata; get_argument_detail extended | VERIFIED | Both functions import successfully. get_argument_detail return dict includes "source_docket" and "cover_metadata" keys confirmed in source. |
| `api/routers/admin.py` | MetadataUpdate imported; GET /arguments/check-duplicate before {argument_id}; PATCH /arguments/{id}/metadata | VERIFIED | Runtime route list confirms check-duplicate at index before {argument_id}. PATCH /arguments/{argument_id}/metadata present. MetadataUpdate imported. |
| `app/src/routes/admin/pipeline/check-duplicate/+server.ts` | Server-only GET proxy; ADMIN_TOKEN from $env/static/private | VERIFIED | File exists. ADMIN_TOKEN imported from `$env/static/private`. error(400) on null params. error(502) on fetch failure. json(await res.json(), Cache-Control no-store) on success. |
| `app/src/routes/admin/pipeline/+page.svelte` | docketInput, duplicateWarning, preflightCleared, formEl state; preflight fetch; banner; formEl.requestSubmit() in Start anyway | VERIFIED | All $state variables confirmed. fetch to `/admin/pipeline/check-duplicate` confirmed. Banner with role="alert" and "⚠ Argument already exists" confirmed. Start anyway onclick uses `formEl.requestSubmit()`. No `document.querySelector` in file. |
| `app/src/routes/admin/pipeline/+page.server.ts` | Reads primary_docket and question_number; passes to ingest in both branches | VERIFIED | Both FormData reads confirmed. Forwarded in both url and upload branches. primary_docket only appended when non-null. |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Argument Metadata card; saveMetadata form action; hint text with optional chaining | VERIFIED (hint text behavior human-needed) | "Argument Metadata" heading confirmed. `form action="?/saveMetadata"`. All three inputs (case_name, source_docket, argued_date). Optional-chaining null guards on cover_metadata confirmed. |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | ArgumentPreview extended with source_docket + cover_metadata; saveMetadata action | VERIFIED | Both fields in ArgumentPreview interface. saveMetadata action present with correct fail(400)/fail(502)/fail(422)/success return pattern. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| +page.svelte preflight | check-duplicate/+server.ts | fetch to `/admin/pipeline/check-duplicate` | WIRED | Confirmed in handleSubmit |
| check-duplicate/+server.ts | FastAPI GET /api/admin/arguments/check-duplicate | FASTAPI_BASE_URL + X-Admin-Token header | WIRED | Confirmed in +server.ts |
| FastAPI check-duplicate | check_duplicate_argument service | arguments_service.check_duplicate_argument(db, docket, question) | WIRED | Confirmed in admin.py |
| check_duplicate_argument | Argument.source_docket DB query | SQLAlchemy select with parameterized WHERE | WIRED | Confirmed in service function |
| Start anyway onclick | handleSubmit early-return branch | preflightCleared=true + formEl.requestSubmit() | WIRED | formEl bound via bind:this; onclick confirmed |
| saveMetadata action | FastAPI PATCH /api/admin/arguments/{id}/metadata | FASTAPI_BASE_URL + X-Admin-Token + JSON body | WIRED | Confirmed in [job_id]/+page.server.ts |
| FastAPI metadata PATCH | update_argument_metadata service | arguments_service.update_argument_metadata(db, argument_id, body) | WIRED | Confirmed in admin.py |
| check-duplicate route ordering | check-duplicate registered before {argument_id} | FastAPI literal segment resolution | WIRED | Runtime router inspection: check-duplicate at index 1, {argument_id} at index 2 in arguments sub-routes |
| parse.py Block C | Argument.cover_metadata column | UPDATE Argument WHERE id==source_run.argument_id .values(cover_metadata=...) | WIRED | Confirmed in parse.py |
| parse.py Block D | Argument.source_docket column | UPDATE Argument WHERE id==source_run.argument_id AND source_docket.is_(None) | WIRED | Confirmed in parse.py |
| [job_id]/+page.svelte hint text | cover_metadata JSONB data | data.argument?.cover_metadata?.primary_docket optional chain | WIRED | Code present; runtime rendering requires human verification |
| ADMIN_TOKEN server isolation | $env/static/private | Never in PUBLIC_ env; only in +server.ts and server actions | WIRED | Confirmed in check-duplicate/+server.ts and [job_id]/+page.server.ts |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| DOCKET_RE matches Alderson format | `pytest -k test_docket_re_matches_alderson_format` | PASSED | PASS |
| DOCKET_RE matches longer number | `pytest -k test_docket_re_matches_longer_number` | PASSED | PASS |
| DOCKET_RE no match when absent | `pytest -k test_docket_re_no_match_when_absent` | PASSED | PASS |
| Fail-safe preserved | `pytest -k test_extract_cover_metadata_still_failsafe` | PASSED | PASS |
| Model imports correctly | Runtime import of Argument model | source_docket, cover_metadata columns present; UniqueConstraint confirmed | PASS |
| Schema fields correct | Runtime import of MetadataUpdate, ArgumentDetail | MetadataUpdate has 3 fields; ArgumentDetail has source_docket + cover_metadata; argued_date not required | PASS |
| Service functions importable | Runtime import of check_duplicate_argument, update_argument_metadata | Exit 0 | PASS |
| Route ordering | Runtime router inspection | check-duplicate before {argument_id} in route list | PASS |
| Start anyway fix — document.querySelector removed | grep for document.querySelector in +page.svelte | No matches found | PASS |
| Start anyway fix — formEl bound | grep for bind:this in +page.svelte | bind:this={formEl} present on form element | PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| PIPE-25 | 19-01, 19-02, 19-03, 19-04 | System enforces a unique DB constraint preventing duplicate arguments; UI warns operator before starting a new run if matching argument exists | SATISFIED | Migration 0011 unique constraint confirmed. IntegrityError handling in ingest confirmed. check-duplicate endpoint and UI preflight/banner confirmed. |
| PIPE-26 | 19-01, 19-02, 19-03, 19-04 | Argument metadata pre-populated from cover extraction results visible to operator during/after pipeline run | SATISFIED | cover_extractor DOCKET_RE extraction confirmed. parse.py Blocks C/D confirmed. ArgumentDetail.source_docket + cover_metadata confirmed. Job detail Metadata card confirmed. Hint text logic wired — runtime rendering human-needed. |
| PIPE-DUP-05 | 19-05 (gap closure) | Start anyway button proceeds without causing stuck "Starting…" state or logout | ORPHANED in REQUIREMENTS.md — intent covered by PIPE-25 | Fix code confirmed: formEl bound, onclick updated, document.querySelector removed. Runtime outcome human-needed. |

**Orphaned requirement PIPE-DUP-05:** This ID appears in 19-05-PLAN.md and 19-05-SUMMARY.md but is absent from REQUIREMENTS.md. It was created as an internal gap-closure tracking ID during phase execution. The behavioral intent is subsumed within PIPE-25 (duplicate prevention UI). This is not a blocker — the fix exists in code. The REQUIREMENTS.md does not need retroactive update unless the team wants to formally document the sub-requirement.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | No TBD/FIXME/XXX markers in any modified file. No stub implementations. No hardcoded empty returns in render paths. |

### Human Verification Required

#### 1. Start anyway — Navigation Outcome

**Test:** Navigate to `/admin/pipeline`. Enter the docket number and question of an argument that already exists. Click Start Run. Confirm the amber duplicate warning banner appears. Click "Start anyway".

**Expected:** The button label briefly shows "Starting…" and the page navigates to a new pipeline job detail page. The operator is NOT redirected to the login page and the button does NOT remain stuck as "Starting…".

**Why human:** This tests browser-level form submission behavior and navigation outcome after Plan 05 applied the `formEl.requestSubmit()` fix. The structural code change is confirmed (formEl bound, onclick updated, document.querySelector removed). The actual navigation result requires a running app with a live browser session. UAT test 5 previously failed; this re-tests the gap closure.

#### 2. Hint text from cover extraction — Conditional Display

**Test:** Find (or ingest) a job where `cover_metadata.primary_docket` differs from `Argument.source_docket`, or where `cover_metadata.argued_date` differs from `Argument.argued_date`. Navigate to that job's detail page.

**Expected:** The relevant field shows faint hint text "Extracted: [value]" below the input. Fields where the extracted and stored values match, or where `cover_metadata` is null, show no hint text.

**Why human:** UAT test 7 was skipped because no suitable test job was available during UAT. The conditional rendering code (`cover_metadata.primary_docket != null && cover_metadata.primary_docket !== argument.source_docket`) and optional-chaining null guards are present in the codebase. The conditional display requires a live argument with divergent values to exercise the actual render path.

---

## Gaps Summary

No hard gaps (BLOCKER status) found. All ROADMAP Success Criteria have substantive implementation confirmed in the codebase:

1. Unique DB constraint: migration 0011 confirmed, IntegrityError handling confirmed.
2. Operator UI warning: check-duplicate proxy, preflight logic, and duplicate banner all confirmed.
3. Metadata pre-population: cover extractor docket extraction confirmed, parse write-back confirmed, metadata card confirmed.
4. Operator override: saveMetadata action and update_argument_metadata service confirmed, conditional write (IS NULL guard) prevents overwriting operator-entered values.

Two items require human verification before phase can be marked fully passed:
- UAT test 5 (Start anyway navigation) — gap closure code confirmed but browser outcome unverified.
- UAT test 7 (hint text conditional display) — code confirmed but requires a job with differing extracted vs. stored values to exercise.

---

_Verified: 2026-07-01T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
