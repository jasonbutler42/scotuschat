---
phase: 32
slug: fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-14
updated: 2026-07-14
---

# Phase 32 — Validation Strategy

> Retroactive Nyquist validation contract for CourtTenure merge/delete bookkeeping and frontend synchronization.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 9.1.0 |
| **Backend config** | `pytest.ini`, `requirements-dev.txt`, repository `.venv` |
| **Frontend framework** | SvelteKit / svelte-check |
| **Quick run command** | `& '.\.venv\Scripts\python.exe' -m pytest -q -k tenure` |
| **Full backend command** | `& '.\.venv\Scripts\python.exe' -m pytest -q` |
| **Frontend command** | `Push-Location app; npm run check; Pop-Location` |
| **Observed quick runtime** | ~9 seconds (28 passed, 423 deselected) |

The repository-root virtual environment is canonical. Running the ambient `python` is not equivalent: the ambient Python 3.14 installation does not contain pytest. Full configured collection is required for database bootstrap through `tests/conftest.py`; passing an explicit `api/tests/...` path bypasses that bootstrap and causes DB-guarded tests to skip.

---

## Sampling Rate

- **After backend task commits:** Run `& '.\.venv\Scripts\python.exe' -m pytest -q -k tenure`.
- **After frontend task commits:** Run `Push-Location app; npm run check; Pop-Location`.
- **After every plan wave:** Run both the full backend and frontend commands above.
- **Before `$gsd-verify-work`:** Both suites must be green.
- **Max observed targeted feedback latency:** 23 seconds including backend and frontend checks.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | PADM-05 | T-32-ATOMIC / T-32-ORPHAN | Schema requires `tenures`; merge transfers tenure rows atomically; delete blocks when tenure rows exist and preserves orphan deletion | integration | `& '.\.venv\Scripts\python.exe' -m pytest -q -k tenure` | ✅ `api/tests/test_admin_people_merge.py` | ✅ green |
| 32-01-02 | 01 | 1 | PADM-05 | T-32-ATOMIC / T-32-ORPHAN | Preview count, blocked delete, merge transfer, and zero-tenure behavior have executable regression coverage | integration | `& '.\.venv\Scripts\python.exe' -m pytest -q -k tenure` | ✅ `api/tests/test_admin_people_merge.py` | ✅ green |
| 32-02-01 | 02 | 1 | PADM-05 | T-32F-STALE / T-32F-CONTRACT | Server-load type and delete blocking calculation consume `tenures` | static/type | `Push-Location app; npm run check; Pop-Location` | ✅ `app/src/routes/admin/people/[id]/+page.server.ts` | ✅ green |
| 32-02-02 | 02 | 1 | PADM-05 | T-32F-CONTRACT | Component type, all-zero guard, and merge breakdown consume and render `tenures` | static/type | `Push-Location app; npm run check; Pop-Location` | ✅ `app/src/routes/admin/people/[id]/+page.svelte` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure and test files cover all Phase 32 requirements. No Wave 0 test generation or dependency installation is required.

---

## Manual-Only Verifications

None. The prior browser UAT is recorded as passed in `32-UAT.md`; all PADM-05 behaviors also have automated verification.

---

## Validation Audit 2026-07-14

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

The apparent gap was an incorrect interpreter/collection scope, not a missing test. The ambient interpreter reported `No module named pytest`; the repository `.venv` ran the targeted full-collection selection successfully: `28 passed, 423 deselected in 8.71s`. Frontend validation completed with 0 errors and 16 pre-existing warnings.

---

## Validation Sign-Off

- [x] All tasks have automated verification commands.
- [x] Sampling continuity has no three-task gap.
- [x] Existing infrastructure covers all references; no Wave 0 work remains.
- [x] No watch-mode flags are used.
- [x] Targeted feedback latency is below 30 seconds.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved 2026-07-14
