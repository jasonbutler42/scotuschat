---
phase: 41
slug: canonical-corpus-fixture-selection
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-29
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (project-wide, `pytest.ini` at repo root) — not exercised by this phase's own deliverable, since no importer/API/model code changes |
| **Config file** | `pytest.ini` (existing) |
| **Quick run command** | N/A for this phase's own script (no pytest suite needed for a throwaway analysis script) |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest` (existing project-wide command, per `.planning/config.json`) — run only to confirm this phase's changes (a new `scripts/*.py` file + a new `.planning/FIXTURES.md`) did not accidentally touch anything under `api/`, `pipeline/`, or `app/` that the suite covers |
| **Estimated runtime** | Not phase-relevant — this phase adds no tests to the suite |

---

## Sampling Rate

- **After every task commit:** `git status` / `git diff --stat` sanity check that no `api/`, `pipeline/commands/`, `pipeline/corpus/`, or `alembic/` file was modified (success criterion 5)
- **After every plan wave:** Same check, plus confirm `.planning/FIXTURES.md` exists at project root (not nested under the phase directory, per D-08) with all 4 fixtures and all required fields present
- **Before `/gsd-verify-work`:** Operator's explicit confirmation (or redirect) of the 4-fixture set IS the phase gate — no automated check substitutes for it
- **Max feedback latency:** Immediate (`git diff --stat` is instant; no long-running suite gates this phase)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | CORPUS-12 | — / — | N/A | manual/checkpoint | `git diff --stat` (confirm only `scripts/*.py` + `.planning/FIXTURES.md` changed — nothing under `api/`, `pipeline/`, `alembic/`) | N/A — documentation/checkpoint deliverable, not app code | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*None: Existing infrastructure covers all phase requirements — this phase adds no testable runtime code.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Ranked shortlist + recommendation presented; operator explicitly confirms (or redirects) the 4-fixture set | CORPUS-12 | This is a decision-gate — success criterion 3 requires explicit human confirmation; no automated test can substitute for the operator's judgment call | Run the scoring script; review the printed top-5 shortlist (with path-coverage annotations) and the 3 proposed state-variety candidates; present via a checkpoint/AskUserQuestion; record the confirmed set into `.planning/FIXTURES.md` with all required fields |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s (git diff --stat only)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
