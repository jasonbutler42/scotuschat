---
phase: 35
slug: rerun-job-local-upload-no-ingest
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-15
---

# Phase 35 — Validation Strategy

> Retroactive Nyquist audit of the completed pipeline-job rerun capability removal.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest, Svelte Check, Vite production build |
| **Config file** | `pytest.ini`; `app/svelte.config.js`; `app/vite.config.ts` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_phase35.py api/tests/test_admin_jobs_phase35_frontend.py api/tests/test_admin_jobs_phase25.py -q` |
| **Full phase command** | Quick run with repository `.env`, then `npm --prefix app run check` and `npm --prefix app run build` |
| **Estimated runtime** | ~35 seconds |

---

## Sampling Rate

- **After backend removal commits:** Compile the changed modules and run the retired-symbol absence scan.
- **After frontend removal commits:** Run the focused frontend structural regressions and Svelte Check.
- **After regression-test commits:** Run the configured focused Phase 35/25 matrix.
- **Before `$gsd-verify-work`:** Run the full pytest suite, Svelte Check, and production build.
- **Max focused feedback latency:** approximately 5 seconds; frontend check and build approximately 30 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 1 | PIPE-29 | T-35-01, T-35-02, T-35-03 | Remove backend recreation ownership without changing authenticated creation, recovery, PDF delivery, or durable history. | compile/absence plus integration | Compile and exact-symbol scan; `test_admin_jobs_phase35.py` | ✅ | ✅ green |
| 35-01-02 | 01 | 1 | PIPE-29 | T-35-02, T-35-04 | Align active wording while preserving schemas, step-specific recovery guidance, and legitimate PipelineRun semantics. | compile/semantic scan plus unit | Compile and classified broad scan; `test_admin_jobs_phase25.py` | ✅ | ✅ green |
| 35-02-01 | 02 | 1 | PIPE-29 | T-35-05, T-35-06 | Remove the hidden SvelteKit recreation action while preserving authenticated proxy boundaries and unrelated actions. | source contract/diagnostic | `npm --prefix app run check`; retired-contract scan | ✅ | ✅ green |
| 35-02-02 | 02 | 1 | PIPE-29 | T-35-07, T-35-08 | Preserve historical detail loading, failed recovery, and local source-PDF composition without retired metadata. | source contract | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_phase35_frontend.py -q` | ✅ | ✅ green |
| 35-03-01 | 03 | 2 | PIPE-29 | T-35-09, T-35-10, T-35-11 | Prove authenticated 404-by-absence and independently verify creation, persistence, recovery, and sanitized PDF delivery. | integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_phase35.py -q` | ✅ | ✅ green |
| 35-03-02 | 03 | 2 | PIPE-29 | T-35-12, T-35-13 | Preserve recovery semantics and validate the removal contract across focused, API, full, and frontend matrices. | integration/regression/build | Configured focused pytest; full pytest; Svelte Check; Vite build | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing pytest and Svelte/Vite infrastructure plus the committed Phase 35 regression modules cover every task and `PIPE-29`; no Wave 0 additions are required.

---

## Manual-Only Verifications

All Phase 35 requirement behaviors have automated verification. No manual-only checks remain.

---

## Validation Audit 2026-07-15

| Metric | Count |
|--------|-------|
| Requirements audited | 1 |
| Tasks mapped | 6 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Current audit evidence:

- Configured focused pytest matrix: 41 passed.
- Svelte diagnostics: 0 errors, 16 pre-existing warnings.
- Vite production build: passed.
- Initial database-free sampling: 22 passed, 19 expected database-gated skips; the configured rerun executed all 41 tests.

---

## Validation Sign-Off

- [x] All tasks have automated verification commands.
- [x] Sampling continuity has no three-task gap without automated verification.
- [x] Existing infrastructure covers all references; no Wave 0 stubs are missing.
- [x] No watch-mode flags are used.
- [x] Focused feedback latency is bounded and the complete phase matrix remains practical.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved 2026-07-15
