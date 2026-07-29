---
phase: 33
slug: metadata-update-unique-constraint-guard
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-14
---

# Phase 33 — Validation Strategy

> Retroactive Nyquist validation contract for the metadata-update unique-constraint guard.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest; SvelteKit `svelte-check` |
| **Config file** | `pytest.ini`; `app/svelte.config.js`; `app/tsconfig.json` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_question_number_nullable.py -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_question_number_nullable.py pipeline/tests/test_ingest.py pipeline/tests/test_import_convokit_core.py pipeline/tests/test_parse.py -q; npm --prefix app run check` |
| **Estimated runtime** | ~97 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task's focused pytest file.
- **After every plan wave:** Run the full Phase 33 suite and `npm --prefix app run check`.
- **Before `$gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 120 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | PIPE-27 | T-33-01 | Final-pair pre-check, self exclusion, NULL semantics, and structured named-constraint classification | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py -q` | ✅ | ✅ green |
| 33-01-02 | 01 | 1 | PIPE-27 | T-33-02 | Pre-check and race return the same sanitized 409; unrelated constraints stay distinct | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_routes.py -q` | ✅ | ✅ green |
| 33-02-01 | 02 | 2 | PIPE-27 | T-33-04 / T-33-05 | Ingest treats only the named pair violation as a duplicate | unit | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_ingest.py -q` | ✅ | ✅ green |
| 33-02-02 | 02 | 2 | PIPE-27 | T-33-05 / T-33-06 | ConvoKit counts and reports only named pair collisions | unit | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_convokit_core.py -q` | ✅ | ✅ green |
| 33-02-03 | 02 | 2 | PIPE-27 | T-33-04 / T-33-05 | Parse guards eligible NULL docket fills, preserves operator values, and classifies races narrowly | integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_parse.py -q` | ✅ | ✅ green |
| 33-03-01 | 03 | 1 | PIPE-27 | T-33-07 / T-33-08 | Both actions validate structured conflicts and preserve attempted values | source contract | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` | ✅ | ✅ green |
| 33-03-02 | 03 | 1 | PIPE-27 | T-33-07 / T-33-09 | Shared alert restores values, focuses after update/tick, and constructs an isolated numeric link | source contract + type check | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q; npm --prefix app run check` | ✅ | ✅ green |
| 33-04-01 | 04 | 2 | PIPE-27 | T-33-10 / T-33-11 / T-33-12 | Pre-check/race copy is identical and the recovery phrase has one safe owner | unit + source contract | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_routes.py api/tests/test_question_number_nullable.py -q; npm --prefix app run check` | ✅ | ✅ green |

---

## Wave 0 Requirements

Existing infrastructure and committed test locations cover all phase requirements. No Wave 0 additions are required.

---

## Manual-Only Verifications

All Phase 33 behaviors have automated verification. The two-route keyboard and new-tab behavior was also exercised in Phase 33 UAT; it is supplementary rather than the sole coverage for a requirement.

---

## Validation Audit 2026-07-14

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Evidence run: 101 focused Python tests passed in 31.81 seconds; `svelte-check` completed with 0 errors and 16 pre-existing warnings.

## Validation Sign-Off

- [x] All tasks have automated verification.
- [x] Sampling continuity: no three consecutive tasks lack automated verification.
- [x] Existing infrastructure covers all required test references.
- [x] No watch-mode flags.
- [x] Feedback latency is below 120 seconds.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved 2026-07-14
