# Phase 47: Provenance Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-17
**Phase:** 47-provenance-foundation
**Areas discussed:** Migration mechanic, Backfill safety, admin_jobs scope, utterance.strategy, Backfill intent (post-reveal)

---

## Migration mechanic (pipeline_runs → import_run)

| Option | Description | Selected |
|--------|-------------|----------|
| Rename in place, keep per-step grain | ALTER pipeline_runs → import_run, preserve row counts + FKs | |
| New table, collapse to per-argument | Fresh import_run at per-argument grain, repoint FKs, drop old | |
| Let researcher recommend | Defer mechanic to research/planner | |

**User's choice:** Superseded — "There is no data in the project database that needs to be retained so I'm not concerned about anything being lost."
**Notes:** This reveal nullified the row-count-preservation constraint and reframed the whole migration as a clean rebuild (see "Backfill intent" below).

---

## Backfill safety (NULL / unrecognized strategy rows)

| Option | Description | Selected |
|--------|-------------|----------|
| Fail-closed on unmapped values | Abort migration on any strategy not in the known set | |
| Default unmapped to a sentinel | Fall to a documented default, never block | |
| Let researcher enumerate the real data first | Query live data / code emission before locking the mapping | ✓ |

**User's choice:** Let researcher enumerate the real data first — reinterpreted post-reveal as: enumerate what the **import paths emit** going forward (legacy rows are disposable).
**Notes:** Combined with the clean-rebuild pivot, "enumerate real data" now means catalog the (source, method, step, external_id) combinations the import code produces.

---

## admin_jobs scope

| Option | Description | Selected |
|--------|-------------|----------|
| Defer admin_jobs to path-rework phase | Phase 47 delivers only import_run + provenance + backfill + nullable PDF + utterance FK | ✓ |
| Re-point admin_jobs now | Generalize the whole run/job model in one pass | |

**User's choice:** Defer admin_jobs to path-rework phase.
**Notes:** Keeps the keystone migration tight.

---

## utterance.strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it, retire later | Keep utterance.strategy populated this phase | |
| Drop it in this migration | Remove the redundant column now | ✓ |

**User's choice:** Drop it in this migration.
**Notes:** Utterance inherits provenance from its import_run; the column is redundant.

---

## Backfill intent (post-reveal reconciliation of PROV-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Clean rebuild, no backfill code | Drop + recreate, provenance in go-forward code, flag PROV-05 for later sign-off | |
| Keep backfill logic anyway | Implement deterministic backfill even though DB is disposable | |
| Reframe PROV-05 as go-forward provenance | Rewrite requirement to write-time stamping, verified by fixture re-seed + read | ✓ |

**User's choice:** Reframe PROV-05 as go-forward provenance (Option 3), after requesting a pros/cons comparison of Options 1 and 3.
**Notes:** Chosen because the build is identical to Option 1 but it replaces a stale
requirement + deferred sign-off with a concrete, testable acceptance criterion that
matches the disposable-DB reality. Guardrail added (D-06): the fixture re-seed must
exercise all provenance combinations (corpus/direct, pdf/rule_based,
pdf/llm_corrective).

---

## Claude's Discretion

- Enum representation for `source`/`method` (native PG enum vs. varchar+CHECK) —
  technical implementation detail left to research/planning.
- `import_run` grain (per-step vs. per-argument) — the row-count constraint that
  would have forced per-step is gone; now an open modeling choice for research.

## Deferred Ideas

- `admin_job → import_run` re-point + corpus-writes-import_run-directly → later "Path rework" phase.
- `trust_tier`, `candidate` status, publish gate → Phase 48.
- `review_state`, discrepancy recording, operator review queue → Phase 49.
- Optional `import_batch` grouping for corpus term-range runs → possible later grouping.
