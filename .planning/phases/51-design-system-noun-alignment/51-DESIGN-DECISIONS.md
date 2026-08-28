---
phase: 51-design-system-noun-alignment
plan: 01
type: design-decisions
created: 2026-08-28
decisions: [D-16, D-18, E4]
---

# Phase 51 — Design Decisions

Produced by plan 51-01. Records the Figma deliverable D-05 puts ahead of code, and
the three operator decisions that plans 51-04, 51-06 and 51-08 are blocked on.

## Figma deliverable (D-05, D-06, D-07)

| Field | Value |
|---|---|
| File | `SCOTUS Chat Design System` |
| URL | https://www.figma.com/design/KICu66PtMLHk4fmxJYPggx |
| Team | **Jason Butler's team** (personal, Full seat) — `team::987360705165943187` |
| Pages | `Tokens`, `Primitives`, `Public`, `Admin` |

Seat precondition re-confirmed with `whoami` at execution time, not assumed:
handle `Jason Butler` / `jasonbutler42@gmail.com`, **Full** on *Jason Butler's team*,
**View-only** on *Offen Petroleum Design Team*. Nothing was written to the Offen team
— this is a personal project, not Offen work (D-07).

### Which path was taken: Figma frames at term scale

**The documented scale fallback was NOT taken.** No static HTML mocks were produced,
and `mocks/` was never created. The Figma MCP populated both D-16 variants at the full
150 rows on the first attempt, so the comparison happened in Figma as D-05 intends.
No Figma call failed.

- `arguments-term-detail-variant-A` — 150 rows, 13,360px tall
- `arguments-term-detail-variant-B` — 150 rows, 16,828px tall (~26% more scroll)
- `d16-comparison` — a readable side-by-side slice (rows 12–27) built because the
  full frames are 13,000–17,000px tall and a whole-frame render alone cannot support
  a judgment about row treatment.

### Token architecture (D-02)

Two variable collections, as Figma **Variables** (not Styles), so they export to CSS
custom properties with no translation layer:

| Collection | Count | Contents |
|---|---|---|
| `primitive` | 14 | Raw palette. Referenced only by the semantic layer, never by a component. |
| `semantic` | 37 | 16 colour roles + 7 spacing + 5 type sizes + 5 line heights + 2 weights + 2 touch targets. |

Verified programmatically at build time: **all 16 semantic colour roles resolve through
a `VARIABLE_ALIAS` to a member of the `primitive` collection**, and no semantic colour
entry holds a literal hex of its own. `color-accent` and `color-side-advocate` are kept
as two distinct names on the shared `blue-300` primitive so a future divergence is a
one-line change.

Dark values only ship. The collection structure — not a second mode — is what makes a
light theme a contained addition later (D-02).

**Plan 51-03 consumes the `semantic` names verbatim** as `app/src/app.css :root` custom
properties. **Plan 51-06 consumes the `Primitives` frame names verbatim** as
`app/src/lib/primitives/*.svelte` filenames.

### Apolitical binding (P-01, P-03)

Swept every text node on all four pages against banned derived-statistic vocabulary:
**0 hits**. Verified programmatically rather than by eye.

Transcript parity checked the same way: across all 6 bench and advocate turns in
`arguments-transcript`, distinct type sizes = `[18]` and distinct weights =
`["Regular"]`. A Justice turn and an advocate turn are typographically identical; the
only difference is the neutral side-indicator colour, which encodes side as a factual
attribute and never as importance.

---

## Term-row variant (D-16)

**Decision: Variant A — minimal row.** Case name, argued date, docket number.

Operator's reason: the minimal row is enough to recognise a case, and it keeps the
listing endpoint free of a join and an index migration this phase does not need.

### The advocate join is DEFERRED, not discarded

Per D-16's deferral clause, Variant B's idea and its query work are deferred to a later
phase, not rejected on merit. The apolitical check explicitly permits advocate names —
advocates and justices receive identical treatment — so nothing about the constraint
blocks revisiting it. Adding the advocate line later is an additive join plus one row
line, with no URL or schema breakage.

What was measured, for whoever picks this up:

- The dev database currently holds **4 arguments**, so no corpus-scale measurement was
  possible. The figures below are plan shape plus projection, and are labelled as such.
- `argument_participants` has **no index on `argument_id`** — only a primary key on `id`.
- The advocate join therefore plans as `Seq Scan on argument_participants` with
  `Filter: (person_id IS NOT NULL) AND (side = 'ADVOCATE')` feeding a hash join.
- At the current ratio of 9.5 participants per argument, a ~7,800-argument corpus
  projects to roughly **74,100 participant rows scanned per listing request**.
- In absolute terms that is still only a few milliseconds, so scan cost alone was never
  the reason to decline Variant B. **If Variant B is revived, add an index on
  `argument_participants(argument_id, side)` in the same plan.** Cheap DDL, and permitted
  — Alembic remains the sole DDL authority.

Consequence for plan 51-08: `TermRow.svelte` ships the three-field shape. The advocate
line and its join do not ship.
Consequence for plan 51-04: the term-detail list endpoint needs no participant join.

---

## Icon library (D-18)

**Decision: `lucide-svelte`.**

Operator's reason: at 6–7 distinct icons the project is past the point where
hand-rolled SVG stays proportionate, and a shared sizing and stroke convention is worth
one dependency.

### The icon count that informed it

Measured in the codebase, not estimated:

| Source | Count | Detail |
|---|---|---|
| Already hand-rolled today | 2 | copy (`CopyableExtractedValue.svelte`), lock (`ResolveCard.svelte`) — 3 `<svg>` occurrences across 2 files |
| Needed by the Phase 51 surfaces | 4 | disclosure chevron (term index + both term-detail variants), close/X (popover), nav hamburger (`MobileNavBar`), external-link arrow (attributions) |
| **Subtotal** | **6** | above the UI-SPEC's ~5 threshold, which is where its own non-binding lean turns |
| Added by the E4 decision below | 1 | loading spinner, now shipping on the shared primitive |
| **Total** | **7** | |

`lucide-svelte` is MIT, tree-shakable per icon (bundle cost scales with what is
imported), actively maintained, and has zero CSS-framework coupling — which fits the
post-Tailwind D-01 direction. It matches the one-SVG-per-icon shape the two existing
hand-rolled sites already use.

**Blocking prerequisite:** this install must clear the blocking package-legitimacy
checkpoint in plan 51-06 (threat T-51-SC) before it lands. No RESEARCH.md Package
Legitimacy Audit exists for this phase, so the fallback policy treats the candidate as
`[ASSUMED]` until that gate passes. Do not install ahead of it.

`bits-ui` is unaffected and stays. It is already proven on `SpeakerPopover` for focus
management, keyboard navigation and ARIA state under the WCAG 2.1 AA commitment. Do not
hand-roll a second focus trap.

### Accessible-name rule binds regardless

The icon-only control contract in `51-UI-SPEC.md` binds `lucide-svelte` exactly as it
would bind hand-rolled SVG, and is annotated directly on the `Button` frame: a visible
text label where space allows, else `aria-label`, else `aria-labelledby` pointing at
existing visible text; the icon itself `aria-hidden="true"` once named; `title` is not
an acceptable substitute; 44px target unchanged (36px only for dense in-table admin
rows), with an undersized icon getting padding rather than a smaller hit area.

---

## Button loading variant (UI-SPEC E4)

**Decision: a loading variant on the shared primitive.**

Operator's reason: one implementation with a simpler component API is preferable to two
code paths, even though the public site has nothing to submit and will never reach the
state.

Consequence for plan 51-06: `Button.svelte` carries the loading/pending state in the
shared primitive under `app/src/lib/primitives/`, not in an admin-only wrapper. The
spinner is the 7th icon and comes from `lucide-svelte` per the decision above. Public
callers simply never pass the prop — the state is reachable only from admin form
submissions, which are the only submissions that exist.
