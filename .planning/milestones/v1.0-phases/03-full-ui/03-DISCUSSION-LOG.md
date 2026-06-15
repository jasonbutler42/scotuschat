# Phase 3: Full UI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 3-full-ui
**Areas discussed:** Section rail placement, Avatar placement, Case list navigation model, Speaker roster in argument header

---

## Section Rail Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Sticky sidebar | Two-column layout: nav rail (~180px) left, chat column right. Always visible while reading. | ✓ |
| Sticky bar below header | Horizontal pill row sticky below header. Single-column stays intact. | |
| Inline at top, no sticky | Pills as first item in chat column — scrolls away. | |

**User's choice:** Sticky sidebar

---

### Section Rail — Active State

| Option | Description | Selected |
|--------|-------------|----------|
| Section labels + scroll-spy active | Labels + active highlight as user scrolls; click to scroll. | ✓ |
| Section labels only, click to scroll | Same labels, no active state while reading. | |
| Section labels + utterance count | Labels show "(42)" count; same scroll-spy. | |

**User's choice:** Section labels + scroll-spy active

---

### Section Rail — Mobile

| Option | Description | Selected |
|--------|-------------|----------|
| Hide on mobile, chat full-width | Sidebar hidden below ~768px. Chat spans full width. | ✓ |
| Collapse to top pills on mobile | Sidebar converts to horizontal sticky pills at narrow widths. | |
| You decide | Leave responsive behavior to planner. | |

**User's choice:** Hide on mobile, chat full-width

---

### Section Rail — Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| Derive from section_hint on utterances | Client-side from existing utterances response. No new API endpoint. | ✓ |
| New API endpoint for sections | GET /arguments/{id}/sections. Cleaner contract, extra work. | |
| You decide | Leave to planner. | |

**User's choice:** Derive from section_hint on utterances

---

## Avatar Placement

*User requested mockups before answering. ASCII mockups presented in chat for Options A/B/C.*

| Option | Description | Selected |
|--------|-------------|----------|
| A — Per-bubble only | 32px avatar in every chat bubble. Header stays minimal. | ✓ |
| B — Header roster only | Larger avatars in header as speaker roster row. Bubbles name-only. | |
| C — Both (header + per-bubble) | Roster in header AND avatar in every bubble. | |

**User's choice:** A — Per-bubble only
**Notes:** User requested a mockup before deciding (first time AskUserQuestion was rejected for clarification). Mockups presented as plain text ASCII; user selected Option A after viewing.

---

### Avatar — Background Color

| Option | Description | Selected |
|--------|-------------|----------|
| Match side color | Bench = #94a3b8, advocate = #93c5fd. Consistent with existing label colors. | ✓ |
| Single neutral color | All avatars same background (#334155). More apolitical. | |
| You decide | Leave to planner. | |

**User's choice:** Match side color

---

## Case List Navigation Model

### Navigation Target

| Option | Description | Selected |
|--------|-------------|----------|
| Directly to argument | Link to /cases/[slug]/arguments/[id]. First argument for multi-argument cases. | |
| Intermediate /cases/[slug] page | Case detail page listing all arguments. | |
| You decide | Leave to planner. | ✓ |

**User's choice:** You decide
**Notes:** Planner must handle multi-argument cases (Obergefell Q1 + Q2).

---

### Case List — Metadata per Case

| Option | Description | Selected |
|--------|-------------|----------|
| Case name + term year | Primary label + year. Clean and scannable. | |
| Case name + docket + argued date | More detail; full identification. | ✓ |
| You decide | Leave to planner. | |

**User's choice:** Case name + docket + argued date

---

## Speaker Roster in Argument Header

### Roster Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Two-column: Bench left, Advocates right | Spatial separation matching chat layout. Apolitical. | ✓ |
| Chips / pill row | All speakers as chips in a single row. No side differentiation in roster. | |
| Collapsible panel | Header stays minimal; expand to see roster. | |

**User's choice:** Two-column: Bench left, Advocates right

---

### Roster — Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| Extend GET /arguments/{id}/utterances | Derive unique speakers client-side. No new API endpoint. | ✓ |
| New GET /arguments/{id}/participants endpoint | Dedicated endpoint. Extra roundtrip. | |
| You decide | Leave to planner. | |

**User's choice:** Extend GET /arguments/{id}/utterances (derive client-side)

---

## Claude's Discretion

- Case list navigation model (direct vs. intermediate page) — deferred to planner with constraint to handle multi-argument cases
- Exact pixel sizing for roster two-column layout within header bar
- Scroll-spy implementation (IntersectionObserver vs. scroll event)
- CSS breakpoint value for mobile sidebar hide
- `GET /cases` response shape (fields beyond name, docket, argued date)

## Deferred Ideas

- Obergefell Q2 session load — after Phase 3 validates case list
- `photo_url` avatars — enrichment pipeline (ENRICH-01) deferred to v2
- Mobile section nav (horizontal pills at narrow widths) — Phase 4 candidate
- Case list filtering by term year (DISC-02) — v2
- Open Graph metadata (DISC-01) — v2
