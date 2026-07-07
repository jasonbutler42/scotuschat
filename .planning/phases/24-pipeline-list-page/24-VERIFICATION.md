---
phase: 24-pipeline-list-page
verified: 2026-07-07T00:00:00Z
status: gaps_found
score: 4/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "All submitted docket pills are forwarded from SvelteKit to FastAPI and persisted through ingest into Argument.source_dockets — reliably, for any operator-entered docket string"
    status: failed
    reason: "24-REVIEW.md CR-01 (unresolved, no follow-up fix commit exists): _normalize_dockets() in api/routers/admin.py only trims/dedupes and never rejects values starting with '-' or '--'. A docket pill value like '--url' or '--dockets' is passed straight into _dockets_to_ingest_args() and then into the spawned `python -m pipeline ingest ...` subprocess argv, where argparse raises SystemExit(2) before run_ingest() executes. Because pipeline_spawn.py launches the subprocess with stdout=DEVNULL, stderr=DEVNULL, this failure is completely invisible: the admin_jobs row created just before spawn is left at PENDING/INGEST forever, never transitioning to FAILED (the ingest.py try/except that would set FAILED never runs, since the process exits before entering Python's ingest logic). The operator sees a job silently stuck with zero error signal. This is reachable via ordinary operator typo, not just malicious input."
    artifacts:
      - path: "api/routers/admin.py"
        issue: "_normalize_dockets (lines 111-134) does not reject values starting with '-'; no HTTPException guard exists anywhere in the file for this case"
      - path: "api/services/pipeline_spawn.py"
        issue: "subprocess spawned with stdout=DEVNULL, stderr=DEVNULL (lines 33-34) — an argparse-level crash before run_ingest() executes produces no FAILED status and no operator-visible error"
    missing:
      - "Reject docket pill values that begin with '-' in _normalize_dockets (422 at the API boundary), and/or insert '--' as an argparse separator before variadic docket values in pipeline/__main__.py so they can never be misinterpreted as flags"
      - "Capture subprocess stderr to a bounded buffer/log file, or add a startup guard that persists a best-effort FAILED status even for argparse-level failures, so a malformed docket value never produces a silently-stuck job"
deferred: []
---

# Phase 24: Pipeline List Page Verification Report

**Phase Goal:** The pipeline list page at `/admin/pipeline/` has a free-text question number field, a docket pill/tag input consistent with Phase 23, a complete runs table, the "show incomplete only" toggle, and accurate compound status badges
**Verified:** 2026-07-07
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can type any free text into the question number field (not a dropdown) | ✓ VERIFIED | `app/src/routes/admin/pipeline/+page.svelte:351-367` — `<input type="text" name="question_number" id="question_number" bind:value={questionInput}>`; no `<select>`, no `<option>`, no `pattern`/`min`/`max`/`type="number"` constraints. `questionInput = $state('1')` pre-fills "1" (line 30). |
| 2 | Operator can add multiple docket numbers as pills and remove individual pills before submitting — matching Phase 23 component behavior | ⚠️ PARTIAL (UI mechanics verified; downstream persistence has an unmitigated critical defect) | UI mechanics: `DocketPillInput.svelte` add-on-Enter (`addPill()`, lines 19-26), remove-on-click (`removePill()`, lines 28-30), one hidden `docket[]` input per pill (lines 34-36) — all confirmed present and correctly wired into `+page.svelte:340` (`<DocketPillInput initialValues={[]} name="docket[]" id="primary_docket" />`) and into the shared `ArgumentDetailsCard.svelte` (Phase 23 consistency, Plan 03). However, 24-REVIEW.md CR-01 is unresolved (see Gaps below): a docket value starting with `-`/`--` silently breaks the spawned ingest subprocess with zero operator-visible failure, undermining "add pills ... before submitting" as a reliable end-to-end truth. |
| 3 | Runs table shows all pipeline runs, not just recent ones | ✓ VERIFIED | `api/services/admin_jobs.py:204-227` `list_jobs(db, incomplete=False)` — no `limit` parameter, no `.limit()` clause, docstring states "Return all AdminJob rows, newest first." `api/routers/admin.py:315` calls `jobs_service.list_jobs(db, incomplete=incomplete)` with no limit arg. Source assertions from Plan 01 re-run and pass (`service OK`, `router OK`). |
| 4 | "Show incomplete only" toggle is present and functional | ✓ VERIFIED | `+page.svelte:454-493` — `role="switch"`, `aria-checked={incomplete}`, `onclick={handleToggle}` which calls `goto('/admin/pipeline?incomplete=1')` / `goto('/admin/pipeline')`; `+page.server.ts:6-10` reads `?incomplete=1` and forwards `incomplete=true` to FastAPI; backend filter (`AdminJob.status.in_([PAUSED, FAILED])`) unchanged and confirmed present at `admin_jobs.py:215-218`. |
| 5 | Status badges display compound labels (e.g. "Parse · Running", "Resolve · Needs Review", "Completed") reflecting current stage and status | ✓ VERIFIED | `+page.svelte:122-141` `badgeLabel(status, currentStep)`: `stepLabels` map (`ingest`/`parse`/`resolve`), `statusLabels` map with `paused` → `"Needs Review"` (capital R). Returns bare status label when `status === 'completed'` or `!currentStep`; otherwise `stepLabel + ' · ' + statusLabel`. Template call `badgeLabel(job.status, job.current_step)` at line 625. Matches UI-SPEC and RESEARCH Pattern 4 exactly. |

**Score:** 4/5 truths verified (1 partial/failed due to an unmitigated critical code-review finding)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/services/admin_jobs.py` | `list_jobs()` with no `.limit()` clause | ✓ VERIFIED | Confirmed via direct read + re-run source assertion |
| `api/routers/admin.py` GET /jobs | Calls `list_jobs` without a limit arg | ✓ VERIFIED | `list_jobs(db, incomplete=incomplete)` |
| `app/src/lib/components/DocketPillInput.svelte` | Shared pill component, 4 props, no internal `<label>` | ✓ VERIFIED | Props `initialValues`/`name`/`readonly`/`id`; hidden inputs render even when `readonly`; remove button hidden when `readonly` |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | Consumes `DocketPillInput`, preserves failed-save restore + `reset:false` | ✓ VERIFIED | `import DocketPillInput`; `{#key effectiveDockets.join('')}`; `reset: false` retained (WR-02 notes a low-severity join-collision edge case, not a functional break) |
| `app/src/routes/admin/pipeline/+page.svelte` | Free-text question, DocketPillInput, compound badge, "All Runs" heading, Step column removed | ✓ VERIFIED | All confirmed via direct read; no `<select name="question_number">`, no `Step` column, heading reads "All Runs" |
| `app/src/routes/admin/pipeline/+page.server.ts` | Forwards every `docket[]` pill as repeated `source_dockets` | ✓ VERIFIED | `data.getAll('docket[]')`, normalized, appended as repeated `source_dockets` FormData fields in both URL and upload branches |
| `alembic/versions/0015_add_admin_job_source_dockets.py` | Adds nullable `admin_jobs.source_dockets` | ✓ VERIFIED | `down_revision = "0014"`; adds `ARRAY(VARCHAR(50))` nullable column; downgrade drops it |
| `api/models/models.py` | `AdminJob.source_dockets` column | ✓ VERIFIED | Line 398 |
| `api/schemas/admin_jobs.py` | `AdminJobResponse.source_dockets` | ✓ VERIFIED | Line 53 |
| `pipeline/commands/ingest.py` | Writes `Argument.source_dockets` alongside `source_docket` | ✓ VERIFIED | Line 405-406: `source_docket=primary_docket or (all_dockets[0] if all_dockets else None)`, `source_dockets=all_dockets or None` |
| `api/routers/admin.py` `_normalize_dockets` / `_dockets_to_ingest_args` | Normalize + build ingest args | ⚠️ VERIFIED BUT INCOMPLETE | Functions exist and correctly trim/dedupe/order (lines 111-148), but do not guard against argparse-flag-like docket values — see CR-01 gap |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `DocketPillInput` hidden inputs | Parent `<form>` | `FormData.getAll('docket[]')` | ✓ WIRED | Confirmed in both `+page.server.ts:40` and `ArgumentDetailsCard.svelte` consumption |
| `+page.svelte handleSubmit` | `formEl.querySelectorAll('input[name="docket[]"]')` | Per-pill duplicate preflight | ✓ WIRED | Lines 63-65, loop at 76-100, stops on first match naming the specific docket (D-09) |
| `badgeLabel(job.status, job.current_step)` | Compound badge text | Template interpolation | ✓ WIRED | Line 625 |
| SvelteKit action | FastAPI `POST /api/admin/jobs` | Repeated `source_dockets` FormData field | ✓ WIRED | `+page.server.ts:65-67, 102-104` |
| FastAPI router | `jobs_service.create_job(..., source_dockets=...)` | Normalized list | ✓ WIRED | `admin.py:212-214` |
| FastAPI router | Spawned `pipeline ingest` subprocess argv | `_dockets_to_ingest_args()` | ⚠️ WIRED BUT UNSAFE | Wired correctly for well-formed docket values; **not defended** against values that argparse would interpret as flags (CR-01) |
| `pipeline/commands/ingest.py` | `Argument.source_dockets` / `Argument.source_docket` | ORM write on Argument creation | ✓ WIRED | Lines 405-406 |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/routers/admin.py` | 111-134 (`_normalize_dockets`) | Missing input validation (no rejection of `-`/`--`-prefixed docket values) | 🛑 Blocker (per 24-REVIEW.md CR-01, unresolved) | Operator typo can silently strand a job in PENDING/INGEST forever with no error surfaced anywhere |
| `api/services/pipeline_spawn.py` | 33-34 | `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` | 🛑 Blocker (compounds CR-01) | Any subprocess-level crash before `run_ingest()` executes is completely invisible; no FAILED status is ever written |
| `app/src/routes/admin/pipeline/+page.server.ts` | 12 | Stale comment: `// Fetch the 10 most recent pipeline jobs...` | ℹ️ Info (24-REVIEW.md IN-01) | Misdescribes now-uncapped behavior; will mislead future readers, no functional impact |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | 89 | `{#key effectiveDockets.join('')}` (empty-string separator can theoretically collide across distinct docket arrays) | ⚠️ Warning (24-REVIEW.md WR-02) | Low-probability collision given `NN-NNN` docket shape; would cause stale pill display after a metadata edit in the rare collision case |
| `app/src/routes/admin/pipeline/+page.svelte` | 351-367 | `question_number` free-text field has no client-side numeric validation | ⚠️ Warning (24-REVIEW.md WR-03) | Non-numeric input round-trips to a generic 422 error message (compounds WR-01) |

No `TODO`/`FIXME`/`XXX` debt markers found in any phase-24-modified file.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PLIST-01 | 24-04 | Question number free text | ✓ SATISFIED | `<input type="text" name="question_number">`, no dropdown |
| PLIST-02 | 24-02, 24-03, 24-04 | Docket pill/tag UI, multi-docket, add/remove | ⚠️ PARTIALLY SATISFIED | Pill UI is fully implemented and correctly shared with Phase 23 (`ArgumentDetailsCard`); however, the full-persistence data path this requirement's must_haves explicitly commit to ("All submitted docket pills are forwarded from SvelteKit to FastAPI and persisted through ingest") is undermined by CR-01 — a plausible operator input silently breaks persistence with a stuck, unrecoverable job and zero error signal |
| PLIST-03 | 24-01 | Runs table shows all runs | ✓ SATISFIED | `list_jobs()` has no limit; confirmed via source assertion |
| PLIST-04 | 24-04 | Show incomplete only toggle retained | ✓ SATISFIED | Toggle present, wired, backend filter unchanged |
| PLIST-05 | 24-04 | Compound status badges | ✓ SATISFIED | `badgeLabel()` compound logic matches spec |

No orphaned requirements — all five PLIST-* IDs mapped to Phase 24 in REQUIREMENTS.md are claimed by at least one of the four plans' frontmatter `requirements` fields.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `list_jobs` has no limit clause/param | `python -c "assert '.limit(limit)' not in src..."` | `service OK` | ✓ PASS |
| Router no longer passes `limit=10` | `python -c "assert 'list_jobs(db, limit=10' not in src..."` | `router OK` | ✓ PASS |
| svelte-check across all phase-24 files | `npx svelte-check --tsconfig ./tsconfig.json --threshold error` | `0 ERRORS 19 WARNINGS` (pre-existing baseline, unrelated to this phase) | ✓ PASS |
| `_normalize_dockets` rejects flag-like docket values | Manual code read of `admin.py:111-134` | No rejection logic present — `stripped.startswith("-")` guard from the review's suggested fix is absent | ✗ FAIL (confirms CR-01 is unfixed) |
| Subprocess stdio captures failures | `grep stdout=/stderr= api/services/pipeline_spawn.py` | `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL` | ✗ FAIL (confirms CR-01 compounding factor is unfixed) |

Full test suite was not re-run (per plan 04's own SUMMARY, `api/tests/test_admin_jobs_service.py`/`pipeline/tests/test_ingest.py` have 5 pre-existing environment-caused failures unrelated to this phase, reproduced against pre-change state). No new full-suite run was needed since the targeted source checks above directly settle the CR-01 question.

### Human Verification Required

None required — the CR-01 gap is deterministically confirmed by direct source inspection (absence of the rejection guard and presence of `DEVNULL` stdio), not a matter of runtime ambiguity requiring human judgment.

### Gaps Summary

Four of five Phase 24 success criteria are fully and robustly met: the free-text question field, the complete (uncapped) runs table, the incomplete-only toggle, and the compound status badges are all correctly implemented, wired, and match their specs with no reservations.

The docket pill success criterion (SC-2 / PLIST-02) is **partially** met. The pill add/remove/serialize UI mechanics themselves are excellent and correctly shared between the pipeline list page and the Phase 23 `ArgumentDetailsCard` component — this part of the work is solid. However, Plan 04's own must-haves explicitly commit to full persistence of "all submitted docket pills ... through ingest into Argument.source_dockets," and the phase's own code review (24-REVIEW.md, already committed) found this persistence path has a **Critical, unresolved** defect: an operator-entered docket pill beginning with `-` or `--` (an easy typo, e.g. accidentally pasting `--dockets`) causes the spawned `pipeline ingest` subprocess to fail at the argparse level before any Python ingest logic executes. Because the subprocess is spawned with `stdout=DEVNULL, stderr=DEVNULL`, this failure produces **no FAILED status transition and no operator-visible error of any kind** — the job silently and permanently sticks at "Pending · Ingest" in the very runs table this phase built. This is not a hypothetical: it was demonstrated with a concrete reproduction in 24-REVIEW.md, and there is no commit after the review (`5a90fb5e docs(24): add code review report` is the tip of history for the reviewed files) that addresses it.

Given the review explicitly calls this "exploitable by an ordinary operator typo" with a "silent hang" failure mode, this is judged a genuine gap against the phase goal rather than an acceptable residual risk — it directly compromises the reliability of the docket-pill workflow that PLIST-02 requires, using the exact UI surface this phase shipped.

**This looks like an oversight, not an intentional deviation** — the review already prescribed a specific, small fix (reject `-`-prefixed values in `_normalize_dockets`, plus capturing subprocess stderr). No override is suggested because the gap is straightforward to close.

---

_Verified: 2026-07-07_
_Verifier: Claude (gsd-verifier)_
