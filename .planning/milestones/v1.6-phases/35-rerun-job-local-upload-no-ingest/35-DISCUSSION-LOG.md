# Phase 35: Remove pipeline job rerun capability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 35-Remove pipeline job rerun capability
**Areas discussed:** API retirement, Cleanup breadth, Failed-job guidance, Regression coverage

---

## API retirement

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Response to an old rerun request | Normal 404; explicit 410; agent discretion | Normal 404 |
| Backend support | Remove route and service; retain internal service; agent discretion | Remove completely |
| Historical data | No migration; annotate provenance; agent discretion | No migration |
| API regression proof | 404 plus neighboring endpoints; symbol removal only; agent discretion | 404 plus neighboring endpoints |

**User's choice:** Complete removal with normal 404 behavior and no historical-data rewrite.
**Notes:** Neighboring creation and recovery behavior must be covered.

---

## Cleanup breadth

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Reference cleanup | Active code/tests; entire repository; executable code only | Active code/tests |
| Unrelated terminology | Preserve legitimate uses; rename every occurrence; agent discretion | Preserve legitimate uses |
| SvelteKit action | Remove action and error contract; remove visible UI only; agent discretion | Remove both completely |
| Reusable test coverage | Rewrite useful coverage; delete rerun-named tests; agent discretion | Rewrite useful coverage |

**User's choice:** Remove the capability comprehensively from active code and tests without rewriting history or unrelated pipeline-run terminology.
**Notes:** Valuable general coverage should survive under non-rerun tests.

---

## Failed-job guidance

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Recovery wording | Keep "start a new run"; remove restart guidance; use "create a new job" | Keep "start a new run" |
| Step specificity | Preserve per-step guidance; use generic guidance; agent discretion | Preserve per-step guidance |
| Recovery destination | `/admin/pipeline/`; current job page; agent discretion | `/admin/pipeline/` |
| Same-source guard | Keep and rename; remove; agent discretion | Keep and rename |

**User's choice:** Preserve current recovery behavior and its protection against recommending same-source reruns.
**Notes:** Rename the test so it describes the behavioral invariant rather than a supported rerun feature.

---

## Regression coverage

| Decision | Alternatives considered | Selected |
|----------|-------------------------|----------|
| Creation path | Service/route tests; full browser flow; existing tests only | Service/route tests |
| Source-PDF access | Focused existing-job test; structural check; existing suite only | Focused route test |
| Historical job view | Detail-load test; service lookup only; existing suite only | Detail-load test |
| Final verification | Targeted plus broad suites; targeted only; broad suites only | Targeted plus broad suites |

**User's choice:** Focused regressions for every preserved neighboring flow, followed by broad backend/frontend verification.
**Notes:** No new broad browser/E2E flow is required.

---

## the agent's Discretion

None.

## Deferred Ideas

None.
