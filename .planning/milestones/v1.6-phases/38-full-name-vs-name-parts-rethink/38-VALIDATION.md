---
phase: 38
slug: full-name-vs-name-parts-rethink
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-15
---

# Phase 38 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest for API/pipeline; Svelte compiler/type checks for frontend |
| **Config file** | repository pytest configuration; `app/package.json` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_person_names.py -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest`; then `Push-Location app; npm run check; Pop-Location` |
| **Estimated runtime** | Target under 60 seconds per task command; full-suite timing measured during execution |

## Sampling Rate

- **After every task commit:** Run the task's focused `<automated>` command.
- **After every plan wave:** Run all focused suites introduced or modified in that wave.
- **Before `$gsd-verify-work`:** Full pytest suite and `npm run check` must be green.
- **Max feedback latency:** 60 seconds for focused task checks.

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 38-01-01 | 01 | 1 | PEOPLE-09 | T-38-01 | Canonical formatting rejects empty authority without rewriting authored parts | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_person_names.py -q` | ❌ W0 | ⬜ pending |
| 38-01-02 | 01 | 1 | PEOPLE-09 | T-38-01 | All writers receive one normalized server-side contract | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_person_names.py -q` | ❌ W0 | ⬜ pending |
| 38-01-03 | 01 | 1 | PEOPLE-09 | T-38-02 | Ambiguous legacy names remain byte-for-byte preserved and reviewable | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_person_names.py -q` | ❌ W0 | ⬜ pending |
| 38-05-01 | 05 | 1 | PEOPLE-09 | T-38-UI-01 | Provenance text and copy state are escaped and accessible | static/component | `.\.venv\Scripts\python.exe -m pytest api/tests/test_phase38_extracted_value_contract.py -q; Push-Location app; npm run check; Pop-Location` | ❌ W0 | ⬜ pending |
| 38-05-02 | 05 | 1 | PEOPLE-09 | T-38-UI-01 | Approved Docket Pill states preserve source transparency | static/component | `.\.venv\Scripts\python.exe -m pytest api/tests/test_phase38_extracted_value_contract.py -q; Push-Location app; npm run check; Pop-Location` | ❌ W0 | ⬜ pending |
| 38-05-03 | 05 | 1 | PEOPLE-09 | T-38-UI-01 | Every editable-destination consumer exposes the same safe provenance contract | static/component | `.\.venv\Scripts\python.exe -m pytest api/tests/test_phase38_extracted_value_contract.py -q; Push-Location app; npm run check; Pop-Location` | ❌ W0 | ⬜ pending |
| 38-02-01 | 02 | 2 | PEOPLE-09 | T-38-02 | Upgrade and downgrade preserve ambiguous and authored names | migration integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_migration_0022_person_name_authority.py -q` | ❌ W0 | ⬜ pending |
| 38-02-02 | 02 | 2 | PEOPLE-09 | T-38-02 | Review state and provenance persist independently from operator values | migration/unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_migration_0022_person_name_authority.py api/tests/test_person_names.py -q` | ❌ W0 | ⬜ pending |
| 38-03-01 | 03 | 3 | PEOPLE-09 | T-38-03 | API ignores client compatibility values and derives them server-side | service/API integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py api/tests/test_admin_people.py -q` | ✅ extend | ⬜ pending |
| 38-03-02 | 03 | 3 | PEOPLE-09 | T-38-03 | Job mini-create retains existing authorization and dedup guards | integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_phase25.py -q` | ✅ extend | ⬜ pending |
| 38-04-01 | 04 | 3 | PEOPLE-09 | T-38-04 | Justice imports use structured authority without duplicating people | integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_justices_csv.py -q` | ✅ extend | ⬜ pending |
| 38-04-02 | 04 | 3 | PEOPLE-09 | T-38-04 | ConvoKit extraction preserves uncertain provenance without overwriting saved values | integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_convokit_core.py pipeline/tests/test_import_convokit_adminjob.py -q` | ✅ extend | ⬜ pending |
| 38-04-03 | 04 | 3 | PEOPLE-09 | T-38-04 | Seed reruns remain idempotent under structured fixtures | integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_seed_aliases.py pipeline/tests/test_import_justices_csv.py -q` | ✅ extend | ⬜ pending |
| 38-06-01 | 06 | 4 | PEOPLE-09 | T-38-UI-02 | Browser preview mirrors server formatting without becoming authoritative | contract/type | `.\.venv\Scripts\python.exe -m pytest api/tests/test_phase38_people_ui_contract.py -q; Push-Location app; npm run check; Pop-Location` | ❌ W0 | ⬜ pending |
| 38-06-02 | 06 | 4 | PEOPLE-09 | T-38-UI-02 | Create/edit submit structured parts and expose generated state accessibly | contract/type | `.\.venv\Scripts\python.exe -m pytest api/tests/test_phase38_people_ui_contract.py -q; Push-Location app; npm run check; Pop-Location` | ❌ W0 | ⬜ pending |
| 38-06-03 | 06 | 4 | PEOPLE-09 | T-38-UI-02 | Name-review records are filterable without exposing a generic dashboard queue | integration/type | focused Phase 38 suites plus `npm run check` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `api/tests/test_person_names.py` — canonical formatter, conservative splitter, and provenance transition fixtures.
- [ ] `api/tests/test_migration_0022_person_name_authority.py` — upgrade/downgrade preservation and review-state coverage.
- [ ] `api/tests/test_phase38_extracted_value_contract.py` — shared stacked-provenance consumer and accessibility contract.
- [ ] `api/tests/test_phase38_people_ui_contract.py` — generated preview, form submission, and Name review contract.
- [ ] Extend existing API/job/import/seed suites named in the task map before their production changes.

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Responsive stacked provenance and clipboard feedback | PEOPLE-09 | Compiler/type checks cannot prove layout or live clipboard feedback | Compare against `38-FIGMA.md` and approved snapshots at narrow Suffix and wide Last Name/docket widths; keyboard-test copy success, error, and N/A states. |
| Legacy migration dry-run evidence | PEOPLE-09 | Real-row distribution and preserved ambiguous values require operator-readable evidence | Run the migration against a disposable database snapshot; record confident/ambiguous counts and spot-check preserved originals before production use. |

## Validation Sign-Off

- [x] All tasks have `<automated>` verification or Wave 0 dependencies.
- [x] Sampling continuity: no 3 consecutive tasks without automated verification.
- [x] Wave 0 covers all MISSING references.
- [x] No watch-mode flags.
- [x] Focused feedback latency target is under 60 seconds.
- [x] `nyquist_compliant: true` set in frontmatter.

**Approval:** approved 2026-07-15 for planning; execution statuses remain pending.
