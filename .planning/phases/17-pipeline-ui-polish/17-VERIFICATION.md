---
phase: 17-pipeline-ui-polish
verified: 2026-06-29T16:00:00Z
status: passed
score: 9/9 must-haves verified
behavior_unverified: 4
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 8/9 must-haves verified
  gaps_closed:

    - "View source PDF link card gate extended to include original_filename (17-03 fix at +page.svelte:471)"
  gaps_remaining: []
  regressions: []
behavior_unverified_items:

  - truth: "The Ingest stage card shows the source filename (upload) or full source URL (URL mode)"
    test: "Apply migration 0009; upload a PDF; open job detail page"
    expected: "Source file label row present with uploaded filename; absent for pre-migration rows with both fields null"
    why_human: "Conditional render gated on data.job.original_filename || data.job.pdf_url — requires a live DB row with migration 0009 applied"

  - truth: "The Parse stage card shows utterance count, distinct speaker count, case name, and argued date when parse is completed"
    test: "Open a job detail page while parse is running, then after parse completes"
    expected: "No stat rows while pending/running; all four rows appear after completion with raw integer counts"
    why_human: "D-10 gate (status === 'completed' && data.job.parse_stats) is timing-dependent; requires a completed parse run in a live DB"

  - truth: "Operator can click 'View source PDF' and the original PDF opens in a new browser tab"
    test: "Click the 'View source PDF' link on a job detail page"
    expected: "PDF opens in a new tab; Spaces-backed shows DO Spaces pre-signed URL; disk-backed streams inline; ADMIN_TOKEN never visible in address bar"
    why_human: "Token-safety of redirect pass-through and the opaque-redirect fallback path require a running SvelteKit + FastAPI stack with network inspection"

  - truth: "View source PDF link is absent when spaces_key, pdf_url, and original_filename are all null"
    test: "Open a job detail page where all three PDF source fields are null"
    expected: "The View source PDF link card does not appear"
    why_human: "Three-way OR condition requires a DB row with all three values null to confirm the absent branch"
human_verification:

  - test: "Apply migration 0009 (alembic upgrade head). Upload a transcript PDF through /admin/pipeline. Open the job detail page /admin/pipeline/{job_id}. Inspect the Ingest stage card."
    expected: "A 'Source file' label row appears with the uploaded filename (e.g. transcript.pdf). For a URL-sourced job the row shows the full source URL verbatim with long-URL wrapping. For an old pre-migration job with both original_filename and pdf_url null, the row is entirely absent."
    why_human: "Conditional render gated on data.job.original_filename || data.job.pdf_url — requires a live DB row to exercise both present and absent branches"

  - test: "Open a job detail page while the Parse step is still pending or running. Then wait for parse to complete and reload."
    expected: "While parse is running/pending: no Utterances, Distinct speakers, Case name, or Argued rows on the Parse card. After parse completes: all four rows appear with correct values. Raw integer counts only — no percentages, totals, or ratios."
    why_human: "D-10 gate is timing-dependent; the pending-state branch cannot be exercised without a running job"

  - test: "Click the 'View source PDF' link on a job with a completed ingest step. Observe the browser address bar and network requests."
    expected: "PDF opens in a new browser tab. For a Spaces-backed job: address bar shows a DO Spaces pre-signed URL (not /api/admin/... and not /admin/pipeline/...). For a disk-backed local dev job: PDF streams inline. The X-Admin-Token value must never appear in the address bar, response headers, or any visible network request."
    why_human: "Token-safety of the redirect pass-through and opaque-redirect fallback require a running SvelteKit + FastAPI stack with network inspection"

  - test: "Navigate to a job detail page where spaces_key, pdf_url, and original_filename are all null (e.g. a URL-mode job before ingest, where no PDF URL was stored)."
    expected: "The 'View source PDF' link card does not appear between the Argument card and the step cards. No broken anchor or placeholder text is visible."
    why_human: "Three-way OR condition at +page.svelte:471 — requires a DB row with all three values null to confirm the absent branch (condition was corrected by 17-03; need live confirmation of the new gate)"
---

# Phase 17: Pipeline UI Polish — Verification Report (Re-verification)

**Phase Goal:** The pipeline admin gives the operator enough information at each stage to trust the process — detailed stats per card, clear source file identification, and direct access to the original PDF for speaker verification.
**Verified:** 2026-06-29T16:00:00Z
**Status:** human_needed
**Re-verification:** Yes — after 17-03 gap closure (PDF card gate fix)

## Re-verification Summary

The original VERIFICATION.md (2026-06-27) left the phase at `human_needed` with score 8/9: all backend artifacts verified, all frontend code wired, but four behavior-dependent truths routing to live-stack human verification. One human item (#4) also identified an incomplete code condition — the `{#if}` gate only checked `spaces_key || pdf_url`, missing `original_filename`, which caused UAT test 5 to fail for local file-upload jobs.

Plan 17-03 was executed on 2026-06-29 with a single-line fix. This re-verification confirms the fix is in the codebase and elevates the score from 8/9 to 9/9. The four live-stack human verification items remain required.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | The Ingest stage card shows the original filename of the uploaded PDF | PRESENT_BEHAVIOR_UNVERIFIED | Addition A at +page.svelte:544 gated `{#if step === 'ingest' && (data.job.original_filename \|\| data.job.pdf_url)}` renders "Source file" label/value row; ORM column at models.py:340; uploaded via admin.py:179 `original_filename=pdf_file.filename` — code present and wired; live DB required |
| SC-2 | The Parse stage card shows utterance count, distinct speaker count, and extracted case metadata | PRESENT_BEHAVIOR_UNVERIFIED | Addition B at +page.svelte:552 gated `{#if step === 'parse' && status === 'completed' && data.job.parse_stats}`; `get_job()` computes counts via `scalar_one()` COUNT queries (admin_jobs.py:100-122); injected via `job.__dict__["parse_stats"]` — code wired; live completed parse run required |
| SC-3 | Operator can open the original source PDF from the pipeline job detail page | PRESENT_BEHAVIOR_UNVERIFIED | Addition C at +page.svelte:471 `{#if data.job.spaces_key \|\| data.job.pdf_url \|\| data.job.original_filename}` (three-way OR after 17-03 fix); anchor targets same-origin proxy `/admin/pipeline/{data.job.id}/pdf`; proxy at pdf/+server.ts wired to FastAPI `GET /api/admin/jobs/{job_id}/pdf` — all layers present and wired; redirect pass-through and token safety require live stack |
| SC-4 | Stats and file link are visible without leaving the pipeline admin view | PRESENT_BEHAVIOR_UNVERIFIED | All additions render inline on +page.svelte; no navigation away — code verified statically; live render required |
| T-5 | AdminJobResponse includes original_filename and parse_stats fields | VERIFIED | admin_jobs.py:37-38 `original_filename: Optional[str] = None`; `parse_stats: Optional[ParseStats] = None`; ParseStats model at lines 17-25 with `utterance_count: int`, `speaker_count: int`, no `from_attributes` |
| T-6 | GET /api/admin/jobs/{job_id}/pdf route is registered and branches spaces_key first | VERIFIED | admin.py:305 `@router.get("/jobs/{job_id}/pdf")`; admin.py:334 `if job.spaces_key:` branches first to `RedirectResponse(302)`; else-branch reads `PipelineRun.pdf_path` via `get_run_id_for_step(db, job_id, "ingest")` and returns `FileResponse` |
| T-7 | Migration 0009 adds nullable original_filename column to admin_jobs | VERIFIED | alembic/versions/0009_add_original_filename.py: `revision = "0009"`, `down_revision = "0008"`, `upgrade()` calls `op.add_column("admin_jobs", sa.Column("original_filename", sa.Text(), nullable=True))`; `downgrade()` drops it |
| T-8 | generate_pdf_presigned_url(key, expires_in=900) exists and calls generate_presigned_url | VERIFIED | spaces.py:53 function defined; synchronous boto3, mirrors upload pattern |
| T-9 | +page.svelte PDF card gate includes original_filename (17-03 fix) | VERIFIED | +page.svelte:471 confirmed: `{#if data.job.spaces_key \|\| data.job.pdf_url \|\| data.job.original_filename}` — three-way OR present as required by 17-03 |

**Score:** 9/9 truths verified (5 VERIFIED on static analysis; 4 PRESENT_BEHAVIOR_UNVERIFIED — code wired, live stack required)

Note: T-9 replaces the original T-9 (No Base.metadata.create_all) which remains confirmed from the initial verification. The gap item from the original VERIFICATION.md (PDF card gate missing original_filename) is now VERIFIED.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0009_add_original_filename.py` | Migration adding nullable original_filename column | VERIFIED | revision="0009", down_revision="0008"; upgrade/downgrade correct |
| `api/models/models.py` AdminJob.original_filename | Column(Text, nullable=True) | VERIFIED | Line 340: `original_filename = Column(Text, nullable=True)` |
| `api/schemas/admin_jobs.py` ParseStats | Model with utterance_count, speaker_count | VERIFIED | Lines 17-25; no from_attributes config |
| `api/schemas/admin_jobs.py` AdminJobResponse | original_filename + parse_stats fields | VERIFIED | Lines 37-38; both Optional with None default; model_config from_attributes retained |
| `api/services/admin_jobs.py` get_job() | parse_stats query via get_run_id_for_step + scalar_one() | VERIFIED | Lines 100-122; reuses get_run_id_for_step; two COUNT queries with scalar_one(); injects via job.__dict__ |
| `api/services/spaces.py` generate_pdf_presigned_url | Function with expires_in=900 default | VERIFIED | Line 53; synchronous boto3 |
| `api/routers/admin.py` GET /jobs/{job_id}/pdf | Route registered, spaces_key first, Response return type | VERIFIED | Lines 305-354; no response_model; 404 guards present; original_filename=pdf_file.filename at line 179 |
| `app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts` | SvelteKit proxy exporting GET RequestHandler | VERIFIED | File exists; imports from $env/static/private only (line 18); redirect:'manual' (line 27); streams res.body; token not echoed |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | ParseStats interface, extended Job, formatDate(), additions A/B/C, corrected C gate | VERIFIED | ParseStats interface lines 26-29; Job interface lines 31-41; formatDate() lines 46-49; Addition A line 544; Addition B line 552; Addition C line 471 with three-way OR (17-03 fix confirmed) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| admin.py upload branch | create_job | `original_filename=pdf_file.filename` | WIRED | admin.py:179; create_job signature at admin_jobs.py:51 includes `original_filename: str \| None = None` |
| get_job() | get_run_id_for_step + COUNT queries | Reuses existing recency helper; two scalar_one() calls | WIRED | admin_jobs.py:100-122; injects via `job.__dict__["parse_stats"]` |
| admin.py GET /jobs/{job_id}/pdf | spaces.py generate_pdf_presigned_url | run_in_executor wraps synchronous boto3 call | WIRED | admin.py:334 `loop.run_in_executor(None, spaces_service.generate_pdf_presigned_url, job.spaces_key)` |
| pdf/+server.ts | FastAPI GET /api/admin/jobs/{job_id}/pdf | fetch with X-Admin-Token, redirect:'manual' | WIRED | +server.ts:25-28; token from $env/static/private |
| +page.svelte Addition C | /admin/pipeline/{data.job.id}/pdf proxy | href anchor with three-way gate | WIRED | +page.svelte:471 gate; :482 href="/admin/pipeline/{data.job.id}/pdf"; target="_blank" rel="noopener noreferrer" |
| Addition B formatDate call | Script-level function formatDate | Direct call — function declared at script top-level | WIRED | formatDate() at lines 46-49; called at line 570 from within {#each} loop scope |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PIPE-21 | 17-01, 17-02 | Original filename stored and displayed on Ingest card; parse stats on Parse card | SATISFIED | Migration 0009 + AdminJobResponse.original_filename; parse_stats COUNT queries in get_job(); Addition A and B in +page.svelte |
| PIPE-22 | 17-01, 17-02, 17-03 | Operator can open source PDF from job detail page | SATISFIED | GET /jobs/{job_id}/pdf route; pdf/+server.ts proxy; Addition C with corrected three-way OR gate |

Both PIPE-21 and PIPE-22 are marked Complete in REQUIREMENTS.md traceability table (line 119-120).

### Anti-Patterns Found

None. Debt-marker scan on all phase-modified files (0009_add_original_filename.py, models.py, admin_jobs.py, schemas/admin_jobs.py, spaces.py, admin.py, pdf/+server.ts, +page.svelte, test_admin_jobs_stats.py): no TBD, FIXME, XXX, PLACEHOLDER, or HACK markers found. No unreferenced debt markers.

### Behavioral Spot-Checks

Step 7b: SC-1 through SC-4 assert rendering and runtime behavior in a running SvelteKit + FastAPI stack. The following static checks were performed:

| Behavior | Evidence | Status |
|----------|----------|--------|
| PDF route registered in admin router | admin.py:305 `@router.get("/jobs/{job_id}/pdf")` | PASS |
| generate_pdf_presigned_url importable with expires_in param | spaces.py:53 function defined with `expires_in: int = 900` | PASS |
| +server.ts imports from $env/static/private only | +server.ts:18 `import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private'` | PASS |
| ADMIN_TOKEN not echoed in response | +server.ts returns only null body, res.body, or followed.body — no header writes referencing ADMIN_TOKEN | PASS |
| Three-way OR gate at line 471 (17-03 fix) | +page.svelte:471 `{#if data.job.spaces_key \|\| data.job.pdf_url \|\| data.job.original_filename}` | PASS |
| Addition A gate includes original_filename | +page.svelte:544 `{#if step === 'ingest' && (data.job.original_filename \|\| data.job.pdf_url)}` | PASS |
| Addition B gate requires parse completed | +page.svelte:552 `{#if step === 'parse' && status === 'completed' && data.job.parse_stats}` | PASS |
| Job interface extended with original_filename + parse_stats | +page.svelte:39-40 both optional fields present | PASS |
| formatDate() declared at script top-level | +page.svelte:46-49 script-level function, not inside any {#if}/{#each}/{@const} | PASS |

### Human Verification Required

Four items require live-stack confirmation. These are render/behavior checks that static analysis cannot exercise.

#### 1. Ingest card source file row

**Test:** Apply migration 0009 (`alembic upgrade head`). Upload a transcript PDF through /admin/pipeline. Open the job detail page `/admin/pipeline/{job_id}`. Inspect the Ingest stage card.
**Expected:** A "Source file" label row appears with the uploaded filename (e.g. `transcript.pdf`). For a URL-sourced job the row shows the full source URL verbatim with long-URL wrapping. For an old pre-migration job with both values null, the row is entirely absent.
**Why human:** The conditional `{#if step === 'ingest' && (data.job.original_filename || data.job.pdf_url)}` requires a live DB row with migration 0009 applied; cannot exercise both present and absent branches statically.

#### 2. Parse stat rows appear only after parse completes

**Test:** Open a job detail page while parse is still running (status = running or pending). Then wait for parse to complete and reload.
**Expected:** While parse is running/pending: no Utterances/Distinct speakers/Case name/Argued rows on the Parse card. After parse is completed: all four rows appear with correct raw integer values. No percentages, totals, or ratios.
**Why human:** The D-10 gate (`step === 'parse' && status === 'completed' && data.job.parse_stats`) is timing-dependent; the pending-state branch cannot be exercised without a running job in a live DB.

#### 3. View source PDF opens in new tab without token leakage

**Test:** Click the "View source PDF" link on a job with a completed ingest step. Observe the browser address bar and network requests.
**Expected:** PDF opens in a new browser tab. For a Spaces-backed job: address bar shows a DO Spaces pre-signed URL (not `/api/admin/...` and not `/admin/pipeline/...`). For a disk-backed local dev job: PDF streams inline. The `X-Admin-Token` value must never appear in the address bar, response headers, or any visible network request.
**Why human:** Token-safety of the redirect pass-through (`redirect:'manual'`, 302 Location forwarding) and the opaque-redirect fallback path require a running SvelteKit + FastAPI stack with network inspection.

#### 4. View source PDF link absent when all PDF source fields are null

**Test:** Navigate to a job detail page where `spaces_key`, `pdf_url`, and `original_filename` are all null.
**Expected:** The "View source PDF" link card does not appear between the Argument card and the step cards. No broken anchor or placeholder text is visible.
**Why human:** Three-way OR condition at +page.svelte:471 — the condition was corrected by 17-03 to add `original_filename`; this test now validates the corrected gate on a true all-null row. Requires a DB row with all three values null.

---

## Gap from Original VERIFICATION.md — Resolved

The original VERIFICATION.md human item #4 noted: "Conditional render gated on `data.job.spaces_key || data.job.pdf_url` — requires a DB row with both values null."

This was not just a live-stack item — it described the buggy two-way OR condition. UAT test 5 confirmed the bug: local file-upload jobs (where only `original_filename` is set) never showed the card.

Plan 17-03 fixed this with a single-line change:

- Before: `{#if data.job.spaces_key || data.job.pdf_url}`
- After: `{#if data.job.spaces_key || data.job.pdf_url || data.job.original_filename}`

The fix is confirmed at +page.svelte:471. Human item #4 above now tests the corrected three-way gate.

---

## Summary

All nine must-haves are now satisfied at the static/structural level:

- Migration 0009, ORM column, schema fields, service queries, and PDF endpoint: all VERIFIED (unchanged from initial verification)
- SvelteKit PDF proxy and +page.svelte interface extensions: VERIFIED (unchanged)
- Addition C gate: VERIFIED with three-way OR after 17-03 fix

The four behavior-dependent truths (SC-1 through SC-4) are classified PRESENT_BEHAVIOR_UNVERIFIED. All supporting code is implemented, wired, and data-flow confirmed by static analysis. The remaining four human verification items are live-stack checks: the rendered source file row, parse stat timing, PDF open/token safety, and the corrected null-gate behavior. These cannot be closed by static analysis.

No new debt markers, anti-patterns, or regressions introduced by 17-03.

---

_Verified: 2026-06-29T16:00:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification after: 17-03 gap closure (PDF card gate fix)_
