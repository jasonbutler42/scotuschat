---
phase: 37
slug: tenure-seat-as-chief-associate-toggle
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-14
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest via `pytest.ini`; Svelte static checking plus Node browser tests |
| **Config file** | `pytest.ini`, `app/package.json` |
| **Quick run command** | `focused pytest module for the active seam; npm run check --prefix app for frontend changes` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest` followed by `npm run check --prefix app` |
| **Estimated runtime** | Measure during Wave 0; focused checks should remain under 30 seconds where possible |

---

## Sampling Rate

- **After every task commit:** Run the focused automated command named in that task.
- **After every plan wave:** Run the affected pytest modules and `npm run check --prefix app` when frontend files changed.
- **Before `$gsd-verify-work`:** Run the full pytest suite, frontend check, migration preflight/round-trip, and stale-identifier audit.
- **Max feedback latency:** 30 seconds for focused checks where possible; long DB migration checks run at wave boundaries.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 37-W0-01 | TBD | 0 | PEOPLE-08 | T-37-01 | Dry run is non-writing; unresolved values block; execution is atomic and drift-safe | DB integration | `.\.venv\Scripts\python.exe -m pytest tests/test_migrate_tenure_offices.py -x` | ❌ W0 | ⬜ pending |
| 37-W0-02 | TBD | 0 | PEOPLE-08 | Invalid legacy state cannot be silently coerced or submitted | browser/static | `node app/tests/tenure-office.browser.test.mjs` | ❌ W0 | ⬜ pending |
| 37-API | TBD | TBD | PEOPLE-08 | Only canonical office values are writable and round-trip | unit/integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py -x` | ✅ update | ⬜ pending |
| 37-IMPORT | TBD | TBD | PEOPLE-08 | Imports map both offices canonically and preserve elevation periods | DB integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_justices_csv.py -x` | ✅ update | ⬜ pending |
| 37-PROJECTION | TBD | TBD | PEOPLE-08 | Date-window projections retain semantics and expose formal titles | unit/integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py api/tests/test_admin_arguments_service.py -x` | ✅ update | ⬜ pending |
| 37-UI | TBD | TBD | PEOPLE-08 | Office selection, Associate default, invalid-state focus, and failed-state recovery are accessible | browser/static | `node app/tests/tenure-office.browser.test.mjs; npm run check --prefix app` | ❌ W0 / ✅ config | ⬜ pending |
| 37-AUDIT | TBD | final | PEOPLE-08 | Active contracts contain no stale `seat` identifier | static audit | `rg -n "\bseat\b" api pipeline app tests` | command gate | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_migrate_tenure_offices.py` — recognized formal/numbered values, blank/unrecognized blocking, non-writing dry run, explicit resolution, drift abort, rollback, and audit fields.
- [ ] `app/tests/tenure-office.browser.test.mjs` — Office semantics, selection/idempotence/keyboard behavior, Associate default, invalid-original message, first-invalid focus, and submitted-state recovery.
- [ ] Disposable migration fixture/helper covering the pre-Phase-37 revision through staged rename, normalization utility, final constraint, and safe downgrade ordering.

---

## Manual-Only Verifications

All Phase 37 behaviors should have automated coverage. A final operator smoke test may supplement, but must not replace, the browser/accessibility and migration tests.

---

## Validation Sign-Off

- [x] All prospective task areas have an automated verify or Wave 0 dependency
- [x] Sampling continuity requires an automated check after every task
- [x] Wave 0 identifies every missing test artifact found during research
- [x] No watch-mode flags
- [x] Focused feedback target is under 30 seconds where possible
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-14
