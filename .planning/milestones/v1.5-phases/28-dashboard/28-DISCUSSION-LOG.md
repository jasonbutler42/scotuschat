# Phase 28: Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 28-Dashboard
**Areas discussed:** Needs Attention composition, Stat card CTA destinations, Visual design source, Web traffic placeholder card

---

## Todo Cross-Reference (pre-discussion)

| Todo | Match score | Folded? |
|------|-------------|---------|
| Edit affordance on utterances and speaker popover | 0.9 (keyword false-positive) | No — left in backlog, operator confirmed it's unrelated to the dashboard |

---

## Needs Attention Composition

| Option | Description | Selected |
|--------|-------------|----------|
| Capped with "View all" | Top 5-10 items inline; link to full filtered list | ✓ |
| Unbounded | Show every item on the dashboard directly | |

**User's choice:** Capped with "View all"

| Option | Description | Selected |
|--------|-------------|----------|
| Separate sub-lists by type | Three labeled groups (People/Justices/Drafts) | ✓ |
| Single interleaved feed | One list sorted by urgency/age regardless of type | |

**User's choice:** Separate sub-lists by type

| Option | Description | Selected |
|--------|-------------|----------|
| All drafts | Every draft counts, no age qualifier | ✓ |
| Age-threshold drafts only | Only drafts older than N days | |

**User's choice:** All drafts

| Option | Description | Selected |
|--------|-------------|----------|
| 5 per sub-list | Max 15 items total across 3 sub-lists | ✓ |
| 10 per sub-list | More visible before clicking through | |

**User's choice:** 5 per sub-list
**Notes:** None of the four questions surfaced disagreement with the recommended option.

---

## Stat Card CTA Destinations

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-filtered list | People CTA lands with click-to-filter pill state applied | (superseded — see follow-up below) |
| Plain list, no filter | No filter applied | |

**User's choice (initial):** Pre-filtered list — later refined by a follow-up question once the Phase 27 filter-model gap was surfaced.

| Option | Description | Selected |
|--------|-------------|----------|
| Per-status deep-links | Each Arguments status count links to its own filtered view | ✓ |
| One card-level link | Whole card links to unfiltered list | |

**User's choice:** Per-status deep-links

| Option | Description | Selected |
|--------|-------------|----------|
| Plain pipeline list | CTA links to unfiltered /admin/pipeline | ✓ |
| Filtered to incomplete/in-progress runs | Pre-applies the existing "incomplete only" toggle | |

**User's choice:** Plain pipeline list

**Follow-up (integration gap):** Phase 27 removed the generic "incomplete only" filter on `/admin/people`, replacing it with per-specific-field pill click-to-filter. The dashboard's aggregate "N people missing fields" count doesn't map to any single pill.

| Option | Description | Selected |
|--------|-------------|----------|
| Land unfiltered, pills visible | CTA goes to the tab with no filter; pills render inline as they already do | ✓ |
| Add a new "any missing field" filter mode | Reintroduces an aggregate filter just for this CTA | |

**User's choice:** Land unfiltered, pills visible
**Notes:** This resolved the initial "Pre-filtered list" answer for the People CTA specifically — the final decision (D-05 in CONTEXT.md) supersedes the first answer once the gap was identified.

---

## Visual Design Source

| Option | Description | Selected |
|--------|-------------|----------|
| Design directly from DESIGN-SYSTEM.md | No mockup; Claude designs from existing tokens/patterns | ✓ |
| Sketch it first with /gsd-sketch | Pause discussion, produce a throwaway mockup first | |

**User's choice:** Design directly from DESIGN-SYSTEM.md
**Notes:** Contrasts with Phase 27, which used operator-provided mockups. Explicit choice not to repeat that pattern here.

| Option | Description | Selected |
|--------|-------------|----------|
| Needs Attention first | Actionable items lead the page | ✓ |
| Stat cards first | Overview numbers lead (typical dashboard convention) | |

**User's choice:** Needs Attention first

| Option | Description | Selected |
|--------|-------------|----------|
| Neutral stat cards | Uniform styling; urgency lives only in Needs Attention | ✓ |
| Urgency-coded stat cards | Cards get accent colors when their count includes attention items | |

**User's choice:** Neutral stat cards

---

## Web Traffic Placeholder Card

| Option | Description | Selected |
|--------|-------------|----------|
| Bare labeled card | Title + muted "Coming soon" label, no fake chart | ✓ |
| Skeleton chart placeholder | Greyed-out chart shape behind the label | |

**User's choice:** Bare labeled card

| Option | Description | Selected |
|--------|-------------|----------|
| Set apart, clearly inactive | Visually distinct from the 4 real stat cards | ✓ |
| Same grid as stat cards | Sits inline as a 5th card | |

**User's choice:** Set apart, clearly inactive

---

## Claude's Discretion

- Exact visual treatment distinguishing the placeholder card from real stat cards (dashed border vs. separate row vs. reduced opacity).
- Exact icon (if any) on the Web Traffic placeholder card.
- Whether the Needs Attention "People" sub-list spans both Bench and Advocate tabs combined, or is itself split — not explicitly discussed; recommended in CONTEXT.md as one combined list.
- Exact scope of "Utterances (total)" — all utterances vs. only published-argument utterances — no explicit preference surfaced.
- Definition of "recent" for the Pipeline runs stat card (e.g. last N runs vs. last N days) — no existing precedent in the codebase; left for research/planning.
- Whether this phase introduces a shared `StatCard`/`Card` Svelte component or continues each admin page's existing inline-card pattern.
- Whether the dashboard's data aggregation is one new FastAPI endpoint or the SvelteKit `load()` calling multiple existing/new endpoints in parallel.

## Deferred Ideas

None — discussion stayed within phase scope. The one adjacent-scope item raised was a todo cross-reference match (edit affordance on utterances/speaker popover), which the operator confirmed should stay in the backlog rather than being folded in or deferred to a specific future phase.
