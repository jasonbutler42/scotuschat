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
- `.planning/phases/25-pipeline-job-detail-page/25-UAT.md` — UAT session where this was raised, including two related confirmed issues (missing create/switch-person trigger, WR-04 Continue Resolve visibility) and a cosmetic gap (no spacing between the Resolve status card and the resolve table card).

## Notes

Captured via one-shot seed capture during Phase 25 UAT. Enrich with trigger, why, and scope once the user's written requirements are available.
