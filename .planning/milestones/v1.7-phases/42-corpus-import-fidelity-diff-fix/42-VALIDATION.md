---
phase: 42
slug: corpus-import-fidelity-diff-fix
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-30
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest>=8.0 with pytest-asyncio>=0.23 (both pinned in `requirements-dev.txt`) |
| **Config file** | `pytest.ini` (repo root) — `asyncio_mode = auto`, `testpaths = tests pipeline/tests api/tests`, `pythonpath = .` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_convokit_core.py -x` (Windows terminal — matches `workflow.test_command` in `.planning/config.json`) |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest` |
| **Estimated runtime** | Not measured this research pass — existing pipeline suite is small/synthetic-fixture-based per `test_import_convokit_core.py`'s `_write_corpus_fixture` pattern, expected seconds not minutes |

**Environment note (carried from RESEARCH.md):** WSL system Python has neither `pip` nor any project dependency installed, and the real dev Postgres is Windows-loopback-only (unreachable from WSL). Any DB-touching test/verification task in this phase's plans must be explicitly assigned to either the Windows terminal (`.venv` + portable Postgres already work there) or a bootstrapped WSL venv + ephemeral `pgserver` — never assumed to "just work" wherever the executing agent happens to run.

---

## Sampling Rate

- **After every task commit:** Run the targeted test file for whichever importer function was touched (e.g. `pytest pipeline/tests/test_import_convokit_core.py -x` after an `apolitical.py`/`_resolve_and_link_participant` change)
- **After every plan wave:** `pytest pipeline/tests/` (full pipeline suite)
- **Before `/gsd-verify-work`:** Full suite green, PLUS the actual fixture re-import against a real (or ephemeral) Postgres — the automated suite alone cannot verify Success Criterion 4 (exact utterance count/speaker roster/docket-set match against the REAL 479-row fixture, as opposed to synthetic test fixtures)
- **Max feedback latency:** Not measured — flag if any single test file exceeds ~30s during execution

---

## Per-Task Verification Map

*Populated once PLAN.md tasks exist (planner assigns Task IDs). Interim requirement-level mapping from RESEARCH.md's Architecture Patterns / Validation Architecture section below stands in until then.*

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORPUS-13 | Diff document correctly classifies a known schema-absent field (`decided_date`/`citation`/`court`) | unit (assert on the diff script's own output, or a documentation-only artifact review — no DB needed) | New test target TBD by planner; existing precedent: `pipeline/tests/test_corpus_apolitical.py` tests `apolitical.py`'s extractors directly | ❌ Wave 0 (new diff script has no tests yet) |
| CORPUS-13 | Diff document correctly flags the Marshall bench-misclassification scenario using a synthetic fixture shaped like the real one | unit, using `_write_corpus_fixture`'s established pattern with a synthetic speaker whose `type=="J"` but whose case's `argued_date` precedes any `CourtTenure` for that Person | ❌ Wave 0 | ❌ Wave 0 |
| CORPUS-14 | After the `section_hint` fix, a re-imported fixture's utterances have non-null `section_hint` values matching the advocate side transitions | Extends existing `pipeline/tests/test_import_convokit_utterances.py` patterns | `pytest pipeline/tests/test_import_convokit_utterances.py -x` | ✅ (file exists; new test cases needed inside it) |
| CORPUS-14 | Re-importing the fixture after ALL fixes reproduces exact utterance count (479), speaker roster, and source-docket set — no dropped/duplicated/merged turns | integration, against the delete-then-reimport lifecycle RESEARCH.md defines | New test target TBD by planner — likely a dedicated fixture-specific integration test, since no existing test targets this exact real fixture | ❌ Wave 0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] A new diff-generation script under `scripts/` (no test file exists yet — mirrors `scripts/select_corpus_fixtures.py`'s precedent of being a standalone, testable script, not a pipeline CLI subcommand)
- [ ] A new delete-and-reimport routine/script (no test file exists yet — must NOT reuse `admin_arguments.py::delete_argument`)
- [ ] Test coverage for the Marshall-misclassification scenario specifically (no existing test constructs a speaker whose `type` disagrees with their actual role at the argument's date)
- [ ] Test coverage confirming `section_hint` gets populated by any importer fix (check whether `pipeline/tests/test_import_convokit_utterances.py` currently asserts `section_hint is None`, which would need updating rather than just extending)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Re-imported transcript page shows section-jump navigation anchors after the `section_hint` fix | CORPUS-14 | Frontend rendering behavior (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`) — visual confirmation the anchors actually render, not just that the column is non-null | Load the fixture's transcript page after re-import; confirm Petitioner/Respondent/Rebuttal section-jump links appear and navigate correctly |
| Full diff document review and per-gap classification approval (D-05/D-06) | CORPUS-13, CORPUS-14 | Explicit operator judgment call by design — Claude does not self-approve real-defect-vs-intentional-exclusion classifications | Operator reviews the complete `.planning/`-committed diff document in one batch and approves/adjusts each classification before any fix is applied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
