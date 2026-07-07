---
id: SEED-001
status: dormant
planted: 2026-07-07
planted_during: 25-pipeline-job-detail-page
trigger_when: when relevant
scope: unknown
---

# SEED-001: Rework the Resolve card/table beyond what Phase 25 delivered

## Why This Matters

Surfaced during Phase 25 UAT (`.planning/phases/25-pipeline-job-detail-page/25-UAT.md`). The user noted the Resolve table "still needs more work, but it's getting closer" and intends to write up detailed requirements for further changes to `ResolveCard.svelte` / the resolve-row workflow as part of this milestone. This is explicitly a placeholder — the actual requirements have not been written yet.

## When to Surface

**Trigger:** when relevant

This seed will surface during `/gsd-new-milestone` when the milestone scope matches, or sooner if the user runs `/gsd-capture --seed --enrich SEED-001` once the requirements write-up is ready.

## Scope Estimate

**Unknown** — run `/gsd-capture --seed --enrich SEED-001` to estimate effort once requirements are written.

## Breadcrumbs

- `app/src/lib/components/ResolveCard.svelte` — the current Resolve card implementation from Phase 25.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — step-cards loop (line ~235) and where `ResolveCard` is composed as a sibling after it (line ~404).
- `.planning/phases/25-pipeline-job-detail-page/25-UAT.md` — UAT session where this was raised, including two related confirmed issues (missing create/switch-person trigger, WR-04 Continue Resolve visibility, both resolved as a test-precondition gap) and a cosmetic spacing/header gap (fixed 2026-07-07, commit c126ef5b).
- `.planning/phases/25-pipeline-job-detail-page/25-UI-SPEC.md` (Layout Contract) and `25-04-SUMMARY.md` key-decisions — the locked Phase 25 decision that the pipeline "Resolve" step-status card and `ResolveCard`'s "Resolve" workflow card are intentional separate siblings (D-05/D-20), not a naming collision.

## Open Design Question (added 2026-07-07)

User reviewed a live screenshot and pushed back on the Phase 25 sibling-card decision above: two cards both titled "Resolve" stacked directly on top of each other reads as one broken/malformed card, not two purposeful ones, regardless of the underlying "step status vs. workflow" conceptual split. When this seed is worked, consider whether the pipeline step-status treatment (badge, "Needs review" pill, etc.) for the Resolve step specifically should be folded into the top of `ResolveCard` itself, superseding D-05/D-20 — while leaving Ingest/Parse as plain step-status cards (they have no equivalent "workflow" card of their own).

## Notes

Captured via one-shot seed capture during Phase 25 UAT. Enrich with trigger, why, and scope once the user's written requirements are available.
