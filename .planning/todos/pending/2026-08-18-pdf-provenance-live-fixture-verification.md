---
created: 2026-08-18T00:00:00.000Z
title: Verify pdf_pipeline provenance legs through a live fixture reseed (deferred with PDF route)
area: pipeline
severity: minor
resolves_phase:
files:

  - pipeline/tests/test_import_run_provenance.py
  - api/services/admin_dev.py (reset_to_fixture, FIXTURE_SET)
  - .planning/phases/47-provenance-foundation/47-VERIFICATION.md

audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
---

## Problem

Phase 47's Success Criterion 4 asks that all three provenance combinations be
proven "by re-seeding a fixture and reading it directly off the rows". Only
`corpus/direct` was proven that way — through a real `reset_to_fixture` re-seed
against the live dev database.

The two PDF legs (`pdf_pipeline/rule_based`, `pdf_pipeline/llm_corrective`) are
proven instead by pytest tests in `pipeline/tests/test_import_run_provenance.py`
that monkeypatch `parse_with_llm` and drive the real `run_parse` writer against
`TEST_DATABASE_URL` inside a rolled-back transaction. The engineering claim —
every writer stamps the correct source/method, decided by the branch the code
actually took and never caller-supplied — IS proven end-to-end for all three.
What is missing is only the live-reseed *vehicle* for the two PDF legs, because
no PDF fixture exists anywhere in the repository.

## Why this is deferred, not a gap to close now

Operator scope decision, 2026-08-18: the corpus import path is the focus until
it can properly import and reconcile details. The PDF upload route is
explicitly deferred and will be picked up as its own effort afterward. Building
a synthetic PDF fixture purely to satisfy the wording of a verification
criterion would be work spent on the deprioritized path.

Phase 47 was accepted with an operator override on SC-4 on this basis.

## What to do when the PDF route comes back

1. Add a synthetic PDF fixture (apolitical, synthetic content only — never a
   real customer/vendor identifier, per project conventions).
2. Extend `reset_to_fixture` / `FIXTURE_SET` so it can seed a `pdf_pipeline`
   argument through the real ingest→parse→resolve path.
3. Re-seed and read `source`/`method` directly off the resulting live
   `import_run` rows for both the `rule_based` and `llm_corrective` branches.
4. Retire the SC-4 override in `47-VERIFICATION.md` and record the literal
   verification.

## Related

- `.planning/phases/47-provenance-foundation/47-CONTEXT.md` D-06 (composition rationale)
- `.planning/phases/47-provenance-foundation/47-PROVENANCE-EVIDENCE.md` ("D-06 composition")
- `.planning/phases/47-provenance-foundation/47-REVIEW.md` WR-02 — `parse.py::_fail_run`
  is dead code on the PDF parse path; worth closing in the same effort.
