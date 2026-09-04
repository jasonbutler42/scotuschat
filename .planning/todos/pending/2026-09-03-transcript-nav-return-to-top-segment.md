---
created: 2026-09-03
kind: idea
source: operator, Phase 51 plan 51-10 Task 3 walkthrough (stop 01)
resolves_phase: null
priority: low
---

# Transcript navigation needs a "return to top" segment

Operator: *"I think the navigation should have a segment for returning to the top. Maybe
'top' or 'title' or 'head'... needs to be workshopped."*

An argument transcript is long — the published fixture runs 157 utterances and ~49k
characters — and the section rail currently moves the reader *through* the argument with no
affordance for getting back to its head.

**The name is explicitly unsettled and is the operator's call.** "Top" is a scroll position,
"Title" is the case identity, "Head" is neither; the right word depends on whether the
destination is understood as the top of the page or the case's own header. Workshop the
label before building the control.

## Constraints it must respect

- P-02: nothing that encodes editorial prominence.
- P-05: 44px touch target, and a programmatic accessible name if it ends up icon-only.
- It sits in the section rail, which already has a defined visual language — this is an
  addition to that system, not a new one.
