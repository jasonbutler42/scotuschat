---
phase: 1
slug: foundation-proof-of-concept
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — Wave 0 installs |
| **Quick run command** | `pytest pipeline/tests/ -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest pipeline/tests/ -x -q`
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green + manual browser verification of Obergefell chat view
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-schema | TBD | 1 | INFRA-01 | — | N/A | smoke | `alembic upgrade head && pytest tests/test_schema.py -x` | ❌ W0 | ⬜ pending |
| 1-consolidated | TBD | 1 | INFRA-02 | — | N/A | unit | `pytest tests/test_ingest.py::test_consolidated_dockets -x` | ❌ W0 | ⬜ pending |
| 1-ingest | TBD | 1 | PIPE-01 | SSRF | URL validated against supremecourt.gov before httpx call | unit | `pytest pipeline/tests/test_ingest.py -x` | ❌ W0 | ⬜ pending |
| 1-parse-rows | TBD | 2 | PIPE-03 | LLM injection | Transcript pre-cleaned; instructor schema rejects malformed output | unit | `pytest pipeline/tests/test_parse.py -x` | ❌ W0 | ⬜ pending |
| 1-run-id | TBD | 2 | PIPE-04 | — | N/A | unit | `pytest pipeline/tests/test_parse.py::test_run_id_strategy -x` | ❌ W0 | ⬜ pending |
| 1-stage-dirs | TBD | 2 | PIPE-05 | — | N/A | unit | `pytest pipeline/tests/test_parse.py::test_stage_directions -x` | ❌ W0 | ⬜ pending |
| 1-llm-failures | TBD | 2 | PIPE-06 | — | N/A | unit | `pytest pipeline/tests/test_parse.py::test_llm_failure_modes -x` | ❌ W0 | ⬜ pending |
| 1-state-machine | TBD | 2 | PIPE-10 | — | N/A | unit | `pytest pipeline/tests/test_pipeline_run.py::test_state_machine -x` | ❌ W0 | ⬜ pending |
| 1-rerun | TBD | 2 | PIPE-11 | — | N/A | unit | `pytest pipeline/tests/test_pipeline_run.py::test_rerun -x` | ❌ W0 | ⬜ pending |
| 1-api | TBD | 3 | API-01 | SQL injection | SQLAlchemy ORM parameterizes all queries | integration | `pytest api/tests/test_arguments.py -x` | ❌ W0 | ⬜ pending |
| 1-chat-ui | TBD | 3 | UI-01, UI-02, UI-03 | PUBLIC_ leak | FASTAPI_BASE_URL uses `$env/static/private` only | manual | `npm run dev` → browser inspection | manual only | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_schema.py` — verifies all 10 tables exist after migration
- [ ] `pipeline/tests/test_ingest.py` — ingest command unit tests
- [ ] `pipeline/tests/test_parse.py` — parser unit tests (state machine, stage dirs, section hints)
- [ ] `pipeline/tests/test_pipeline_run.py` — state machine and re-run behavior
- [ ] `api/tests/test_arguments.py` — endpoint integration tests
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest.ini_options]` — test runner config
- [ ] `conftest.py` — shared fixtures (test DB, async session, factory functions)
- [ ] Framework install via `requirements-dev.txt`: `pytest`, `pytest-asyncio`, `httpx`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chat renders with Justice bubbles on bench side, advocate bubbles on advocate side | UI-01 | Requires browser visual inspection; layout cannot be asserted via pytest | `npm run dev` → navigate to `/cases/obergefell-v-hodges/arguments/{id}` → visually confirm two-sided layout |
| Speaker name + role label appear on each bubble | UI-02 | Visual rendering; `person_id` is null at Phase 1 — label comes from raw speaker label | Inspect bubble header text for "JUSTICE KENNEDY:", "MR. OLSON:", etc. |
| Stage directions render as distinct component (not speech bubble) | UI-03 | CSS-driven; requires visual confirmation | Confirm "(Laughter.)" and "(Brief pause.)" render without speaker side styling |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
