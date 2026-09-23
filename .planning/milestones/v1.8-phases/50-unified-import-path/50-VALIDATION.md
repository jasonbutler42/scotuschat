---
phase: 50
slug: unified-import-path
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-25
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `50-RESEARCH.md` § Validation Architecture. Per-task map is filled by `/gsd-validate-phase`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (project-pinned) |
| **Config file** | `pytest.ini` + repo-root `conftest.py` (CLAUDE.md: invocation-shape-independent hooks live there — the `TEST_DATABASE_URL` redirect) |
| **Quick run command** | `./.venv/bin/python -m pytest pipeline/tests/test_import_convokit_core.py api/tests/test_authority_matrix.py -x` |
| **Full suite command** | `./.venv/bin/python -m pytest` |
| **Estimated runtime** | ~quick: seconds · full: minutes (measure at Wave 0) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above, scoped to the writer/reconcile files that task touched
- **After every plan wave:** Run `./.venv/bin/python -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green **plus** the D-09 live double-import walkthrough performed and observed (D-09 is explicit that automated tests alone do not close IMPORT-04)
- **Max feedback latency:** quick run must stay under 60s

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | REQ-{XX} | T-{N}-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement → Test Map (from RESEARCH.md)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMPORT-01 | Corpus import writes `import_run` directly, no PDF artifacts | unit + negative-space | `pytest pipeline/tests/test_import_run_provenance.py -x` | ✅ (extend) |
| IMPORT-03 | No `admin_job` created by corpus batch; `admin_job` references an existing `import_run` | structural/behavioral (D-24: not a grep) | new test asserting zero `AdminJob` rows after a fresh corpus import | ❌ Wave 0 |
| IMPORT-04 | Re-import idempotent; operator edits survive | automated matrix + live human-observed (D-09) | `pytest pipeline/tests/test_import_convokit_reconcile.py -x` (new) + live `reset_to_fixture` double-import diff walkthrough | ❌ Wave 0 (automated half) |
| IMPORT-05 | Authority ordering governs every writer | unit (exhaustive) + real-writer tests for the two PDF legs (D-22, Phase 47 split) | `pytest api/tests/test_authority_matrix.py -x` (extend with pipeline-writer delegation cases) | ✅ (extend) |

### Authority-rung verification split (Phase 47 precedent, per D-22)

| Rung | Verified by |
|------|-------------|
| `operator` | Live corpus flow — operator edit via `update_participant_side`/`update_person`, then a disagreeing re-import |
| `corpus` | Live double-import (D-09) — byte-identical no-op proof + operator-edit-survival walkthrough |
| `pdf_pipeline/rule_based` | Real-writer test with the LLM monkeypatched — `parse.py` writer delegating to the gate |
| `pdf_pipeline/llm_corrective` | Real-writer test with the LLM monkeypatched — `parse.py` LLM branch delegating to the gate |

---

## Wave 0 Requirements

- [ ] Reconcile-specific test module (e.g. `pipeline/tests/test_import_convokit_reconcile.py`) covering D-01 → D-13 mechanics — placement at planner discretion
- [ ] Explicit disposition for `pipeline/tests/test_import_convokit_adminjob.py` (rewrite vs. retire) — must not be left silently red or silently deleted
- [ ] Test coverage for the `api/services/admin_dev.py::reset_to_fixture` rework (check `api/tests/test_admin_dev*.py` at plan time)
- [ ] Negative-space test: a fresh corpus import creates zero `AdminJob` rows

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Double-import diff walkthrough — re-import is a byte-identical no-op and operator edits survive | IMPORT-04 | D-09 states explicitly that automated tests alone do not close this; Phase 48's three real defects were all found live, none by the suite | Drive `reset_to_fixture` to a known state, import, snapshot; edit an operator-authored value; re-import; diff and observe that the corpus value did not clobber it and a discrepancy was recorded |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] D-09 live double-import walkthrough performed and observed
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
