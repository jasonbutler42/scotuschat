---
phase: 2
slug: speaker-resolution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-12
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pytest.ini` or inferred from `pyproject.toml` |
| **Quick run command** | `pytest pipeline/tests/test_resolve.py -x -q` |
| **Full suite command** | `pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest pipeline/tests/test_resolve.py -x -q` (or the relevant test file for that task)
- **After every plan wave:** Run `pytest -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| normalize_label unit | 02 | 1 | PIPE-07 / D-02 | N/A | unit | `pytest pipeline/tests/test_resolve.py::test_normalize_label -x -q` | ❌ W0 | ⬜ pending |
| alias hit auto-resolve | 02 | 1 | PIPE-07 | N/A | integration | `pytest pipeline/tests/test_resolve.py::test_resolve_alias_hit -x -q` | ❌ W0 | ⬜ pending |
| interactive prompt | 02 | 1 | PIPE-07 | N/A | unit (mocked input) | `pytest pipeline/tests/test_resolve.py::test_resolve_interactive_prompt -x -q` | ❌ W0 | ⬜ pending |
| seed creates Justices | 02 | 1 | PIPE-08 | N/A | integration | `pytest pipeline/tests/test_seed_aliases.py::test_seed_creates_justices -x -q` | ❌ W0 | ⬜ pending |
| seed idempotent | 02 | 1 | PIPE-08 | N/A | integration | `pytest pipeline/tests/test_seed_aliases.py::test_seed_idempotent -x -q` | ❌ W0 | ⬜ pending |
| interrupt → needs_review | 02 | 1 | PIPE-09 | N/A | unit (mocked interrupt) | `pytest pipeline/tests/test_resolve.py::test_resolve_interrupt_sets_needs_review -x -q` | ❌ W0 | ⬜ pending |
| resume after interrupt | 02 | 1 | PIPE-09 | N/A | integration | `pytest pipeline/tests/test_resolve.py::test_resolve_resumes_after_interrupt -x -q` | ❌ W0 | ⬜ pending |
| GET /people/{id} 200 | 03 | 2 | API-03 | person_id: int rejects non-integer (422) | unit + integration | `pytest api/tests/test_people.py -x -q` | ❌ W0 | ⬜ pending |
| GET /people/99999 404 | 03 | 2 | API-03 | N/A | unit | `pytest api/tests/test_people.py::test_get_person_404 -x -q` | ❌ W0 | ⬜ pending |
| utterances embed speaker_name/role | 03 | 2 | D-10 | N/A | integration | `pytest api/tests/test_arguments.py::test_utterances_have_speaker_name_after_resolve -x -q` | ❌ W0 | ⬜ pending |
| speaker_alias table in schema | 01 | 1 | PIPE-08 | N/A | integration | `pytest tests/test_schema.py -x -q` | ✅ (update EXPECTED_TABLES) | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `pipeline/tests/test_resolve.py` — stubs for PIPE-07, PIPE-09, normalize_label unit tests
- [ ] `pipeline/tests/test_seed_aliases.py` — stubs for PIPE-08 seeding and idempotency
- [ ] `api/tests/test_people.py` — stubs for API-03 (GET /people/{id})
- [ ] Update `tests/test_schema.py` EXPECTED_TABLES to include `"speaker_alias"` after migration

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Interactive resolve session handles Obergefell counsel labels correctly | PIPE-07 | Requires live DB + running terminal interaction; cannot mock all label variants without knowing exact parsed output | Run `python -m pipeline resolve --run-id 1` after seeding; verify that Justice labels auto-match and counsel labels prompt correctly |
| Chat view renders resolved speaker name and role label (not raw label) | UI-02 (Phase 2 extension) | Requires browser + live data after resolve step completes | Navigate to `http://localhost:5173/cases/obergefell-v-hodges/arguments/1`; verify all bubbles show resolved names (e.g., "Elena Kagan" not "JUSTICE KAGAN:") and role labels |
| Ctrl+C mid-resolve sets pipeline_run status to needs_review | PIPE-09 | KeyboardInterrupt behavior in asyncio is environment-dependent | Run resolve, press Ctrl+C partway through; verify `SELECT status FROM pipeline_runs WHERE step='resolve' ORDER BY id DESC LIMIT 1` returns `needs_review` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
