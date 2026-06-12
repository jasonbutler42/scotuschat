---
phase: 3
slug: full-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (Python backend); no frontend test framework installed |
| **Config file** | `pytest.ini` (or default test discovery in `tests/` directory) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~3 seconds (static analysis + schema tests; no live DB required) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q` + manual browser check
- **Before `/gsd:verify-work`:** Full suite green + 5 manual checks (see Manual-Only Verifications)
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| cases-router | API | 1 | API-02 | — | `GET /cases` registered in main.py; path defined in router; no `create_all` in cases files | static analysis | `pytest tests/test_cases_api.py -x -q` | ❌ W0 | ⬜ pending |
| cases-service | API | 1 | API-02 | — | `is_lead=True` filter prevents duplicate consolidated docket rows | unit | `pytest tests/test_cases_api.py -x -q` | ❌ W0 | ⬜ pending |
| case-list-page | UI | 2 | UI-07 | — | N/A (manual) | manual-only | — | N/A | ⬜ pending |
| argument-header | UI | 2 | UI-04 | — | N/A (manual) | manual-only | — | N/A | ⬜ pending |
| avatar-circle | UI | 2 | UI-05 | — | N/A (manual) | manual-only | — | N/A | ⬜ pending |
| section-rail | UI | 2 | UI-08 | — | N/A (manual) | manual-only | — | N/A | ⬜ pending |
| ssr-check | UI | 2 | UI-06 | — | Hard refresh at argument URL returns 200 with SSR content | manual | `curl -s http://localhost:5173/cases/obergefell-v-hodges/arguments/3 \| grep -c 'data-sveltekit'` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_cases_api.py` — static analysis stubs: (1) `cases` router is registered in `api/main.py`; (2) `GET /cases` path defined in `api/routers/cases.py`; (3) no `create_all` call in `api/routers/cases.py` or `api/services/cases.py`; (4) `is_lead=True` filter present in `api/services/cases.py`

*Existing infrastructure (`tests/test_schema.py`, `tests/test_models_import.py`) covers schema-level concerns. Only the new Wave 0 file is required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Case list page renders all loaded cases | UI-07 | Browser rendering; no frontend test framework | Open `http://localhost:5173/cases`; verify Obergefell appears with docket and argued date |
| Argument header shows two-column speaker roster | UI-04 | CSS layout; no frontend test framework | Open argument view; verify Bench column (left) and Advocates column (right) below docket line |
| Avatar circle shows initials, no broken images | UI-05 | Visual; no frontend test framework | Verify each bubble has a 32px colored circle with 1–2 initial characters; no `<img>` 404s |
| Section rail shows Petitioner section and scrolls on click | UI-08 | Browser interaction; IntersectionObserver behavior | Open argument; click "Petitioner" in sidebar; verify page scrolls to first Petitioner utterance |
| Hard refresh at argument URL renders correctly (SSR) | UI-06 | Browser behavior | Navigate directly to `/cases/obergefell-v-hodges/arguments/3` in address bar; verify full page loads without hydration error |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
