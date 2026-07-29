# Phase 38: Figma Design References

**Status:** Approved
**Approved:** 2026-07-15
**Figma project:** SCOTUS Chat

## Canonical design

- [SCOTUS Chat - Phase 38 Docket Pill Provenance](https://www.figma.com/design/uTVus1lzc9GrkWUTXOKSiq) - source Figma file.
- [Docket Pill component set](https://www.figma.com/design/uTVus1lzc9GrkWUTXOKSiq?node-id=3-140) - canonical reusable component and variants.
- [Docket Pill review sheet](https://www.figma.com/design/uTVus1lzc9GrkWUTXOKSiq?node-id=3-2) - approved examples and edge states in context.
- [`mockups/docket-pill-provenance-approved.png`](mockups/docket-pill-provenance-approved.png) - approved fallback snapshot for offline review. The editable Figma component remains authoritative.

## Component inventory

### Docket Pill

- **Figma file key:** `uTVus1lzc9GrkWUTXOKSiq`
- **Component-set node:** `3:140`
- **Review-sheet node:** `3:2`
- **Implementation target:** `app/src/lib/components/DocketPillInput.svelte`
- **Related shared presentation:** `app/src/lib/components/CopyableExtractedValue.svelte`

The approved component covers:

- `High`, `Medium`, and `Low` qualitative confidence bands.
- Editable and read-only modes.
- Interpreted docket value as the primary pill content.
- Exact raw source text in the subordinate provenance line.
- Copy affordance and copied feedback.
- Remove affordance in editable mode only.
- Single and multiple docket layouts.
- Mixed-confidence docket groups.
- Long raw-source wrapping without hiding provenance.

## Authority and implementation notes

- Use the Figma component and review sheet as the visual source of truth for Docket pills.
- Preserve the locked Phase 38 semantic contract: interpreted value, qualitative confidence, and exact raw source text are distinct facts.
- Confidence must be communicated by text as well as color.
- The PNG is a durable review fallback, not a replacement for inspecting the editable Figma component.
- The Phase 38 `UI-SPEC.md` and `PLAN.md` must cite this file and translate the approved states into accessible responsive behavior; they should not infer measurements solely from the PNG.
- If the design changes after implementation planning begins, update the Figma component first, refresh the approved PNG, and record the approval change here.
