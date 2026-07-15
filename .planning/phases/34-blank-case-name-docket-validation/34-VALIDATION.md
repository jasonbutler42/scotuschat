---
phase: 34
slug: blank-case-name-docket-validation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-15
---

# Phase 34 — Validation Strategy

> Retroactive Nyquist audit of the completed blank case-name and docket-number validation phase.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest, Node built-in test runner, Svelte Check |
| **Config file** | `pytest.ini`; `app/svelte.config.js`; `app/tsconfig.json` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py api/tests/test_question_number_nullable.py -q` |
| **Full phase command** | Quick run, then `node --test app/tests/case-required-recovery.browser.test.mjs`, then `npm run check` from `app/` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After backend task commits:** Run the focused pytest file or files named by the task.
- **After frontend task commits:** Run `api/tests/test_question_number_nullable.py` and `npm run check` from `app/`.
- **After lifecycle changes:** Run `node --test app/tests/case-required-recovery.browser.test.mjs`.
- **Before `$gsd-verify-work`:** The full configured regression suite must be green.
- **Max focused feedback latency:** approximately 15 seconds; browser lifecycle verification approximately 20 seconds.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 34-01-01 | 01 | 1 | PIPE-28 | T-34-01 | Reject explicit null, blank, whitespace-only, and empty normalized required values while preserving PATCH omission. | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py -q` | ✅ | ✅ green |
| 34-01-02 | 01 | 1 | PIPE-28 | T-34-01, T-34-02 | Block invalid direct requests before service execution and persist one normalized canonical docket representation. | unit/integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py api/tests/test_admin_arguments_routes.py -q` | ✅ | ✅ green |
| 34-02-01 | 02 | 2 | PIPE-28 | T-34-04, T-34-05 | Parse structured validation locations and preserve complete raw attempts in argument actions. | source contract | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` | ✅ | ✅ green |
| 34-02-02 | 02 | 2 | PIPE-28 | T-34-04, T-34-05 | Apply the same loc-driven, presence-preserving recovery contract in pipeline metadata actions. | source contract | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q` | ✅ | ✅ green |
| 34-03-01 | 03 | 3 | PIPE-28 | T-34-07, T-34-08 | Accumulate native Case failures, expose accessible error state, and focus the first invalid field. | source contract/diagnostic | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q`; `npm run check` | ✅ | ✅ green |
| 34-03-02 | 03 | 3 | PIPE-28 | T-34-07, T-34-09 | Cancel empty editable docket-pill submissions and expose focus/invalid-state wiring without changing readonly behavior. | source contract/diagnostic | `.\.venv\Scripts\python.exe -m pytest api/tests/test_question_number_nullable.py -q`; `npm run check` | ✅ | ✅ green |
| 34-04-01 | 04 | 4 | PIPE-28 | T-34-10, T-34-11 | Clear stale native-only required state at valid enhanced submit while retaining current server-required state. | browser/unit/diagnostic | `node --test app/tests/case-required-recovery.browser.test.mjs`; focused pytest; `npm run check` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure and committed test files cover all Phase 34 tasks and `PIPE-28`; no Wave 0 additions are required.

---

## Manual-Only Verifications

These checks supplement automated requirement coverage with visual and operator-clarity judgment; they are not Nyquist gaps.

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Single-field native Case feedback and browser-bubble suppression | PIPE-28 | Exact visual presentation for each single-invalid-field combination requires browser judgment. | Submit with only case name blank, only docket blank, and both blank; inspect copy, focus, ARIA, borders, and absence of native bubbles. |
| Empty docket pills on both editable surfaces and readonly comparison | PIPE-28 | Automated source contracts cover wiring, but the two-consumer visual focus transition remains an operator UAT check. | Remove all pills in the argument editor and pipeline metadata forms, submit, inspect cancellation/focus/error styling, then confirm readonly behavior is unchanged. |
| Corrected submission followed by a non-required failure | PIPE-28 | The browser regression automates DOM state; final error clarity remains human judgment. | Correct previously invalid Case fields, force a collision or generic failure, and confirm only the current failure remains visible and understandable. |

---

## Validation Audit 2026-07-15

| Metric | Count |
|--------|-------|
| Requirements audited | 1 |
| Tasks mapped | 7 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Current audit evidence:

- Focused pytest: 75 passed, 24 skipped.
- Edge/CDP lifecycle regression: 1 passed.
- Svelte diagnostics: 0 errors, 16 pre-existing warnings.

---

## Validation Sign-Off

- [x] All tasks have automated verification commands.
- [x] Sampling continuity has no three-task gap without automated verification.
- [x] Existing infrastructure covers all references; no Wave 0 stubs are missing.
- [x] No watch-mode flags are used.
- [x] Focused feedback latency remains bounded; the isolated browser lifecycle is under 30 seconds.
- [x] `nyquist_compliant: true` is set in frontmatter.

**Approval:** approved 2026-07-15
