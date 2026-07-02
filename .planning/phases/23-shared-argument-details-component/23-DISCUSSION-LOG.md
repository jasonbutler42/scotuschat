# Phase 23: Shared Argument Details Component - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-02
**Phase:** 23-Shared Argument Details Component
**Areas discussed:** Shared component structure, Docket pill/tag UX, Hints visual treatment

---

## Shared Component Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Component owns the form (Recommended) | The component renders `<form method="POST" use:enhance>` internally and takes an `action` prop (e.g. `?/saveJobMetadata` vs. `?/save`). Phase 26 reuse is plug-in: same component, different action prop. | ✓ |
| Fieldset only — parent page owns the form | The component renders fields only; each parent page wraps them in its own `<form>`. More flexible for pages with multiple forms, but Phase 26 must duplicate the form wrapper setup. | |
| You decide | Claude picks the cleanest approach based on the codebase patterns. | |

**User's choice:** Component owns the form (Recommended)
**Notes:** None

---

**Question: Does the component replace or coexist with the existing form on pipeline/[id]?**

| Option | Description | Selected |
|--------|-------------|----------|
| Replace the existing form entirely (Recommended) | The current pipeline/[id] Argument Metadata section gets replaced by the new component. Cleaner — one form, no duplication. | ✓ |
| Coexist — keep old form, add component alongside | Old form stays; new component added as a second card. Would create duplication. | |

**User's choice:** Replace the existing form entirely (Recommended)

---

**Question: How does data reach the component?**

| Option | Description | Selected |
|--------|-------------|----------|
| Props from the parent page (Recommended) | Parent +page.server.ts loads data; passes as props: `<ArgumentDetailsCard savedValues={...} hints={...} action="..." />`. | ✓ |
| Component fetches its own data via an API endpoint | Component makes a fetch call internally. Violates architecture rule. | |

**User's choice:** Props from the parent page (Recommended)

---

## Docket Pill/Tag UX

| Option | Description | Selected |
|--------|-------------|----------|
| Type + press Enter to add (Recommended) | Operator types a docket number and presses Enter. Field clears, docket appears as pill. Fast for keyboard users. | ✓ |
| Type + click an Add button | Operator types and clicks a visible "Add" button. More discoverable for mouse users. | |
| Both — Enter OR click Add | Both interactions work. Most forgiving, slightly more implementation complexity. | |

**User's choice:** Type + press Enter to add (Recommended)

---

**Question: How do pill values serialize on form submit?**

| Option | Description | Selected |
|--------|-------------|----------|
| One hidden input per pill (Recommended) | Each docket pill adds `<input type="hidden" name="docket[]" value="...">`. Server reads `FormData.getAll('docket[]')`. | ✓ |
| Single comma-joined hidden input | All dockets joined as "22-111,22-222" in a single hidden field. Server splits on comma. | |
| JSON-encoded single hidden input | Dockets encoded as JSON array string. More robust but adds server-side complexity. | |

**User's choice:** One hidden input per pill (Recommended)

---

**Question: After a failed save, how is pill state restored?**

| Option | Description | Selected |
|--------|-------------|----------|
| Restore to what the operator entered (Recommended) | On form error, component reads submitted dockets from `form` prop and restores pill state. Operator doesn't lose work. | ✓ |
| Reset to last-saved value | On error, component re-reads from `savedValues` props. Operator loses unsaved pill changes. | |

**User's choice:** Restore to what the operator entered (Recommended)

---

## Hints Visual Treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Below the input, small muted text (Recommended) | Each field: Label → input → small muted hint line. Clean, linear, narrow-screen compatible. | ✓ |
| Inline to the right of the input | Hint to the right of the input on same row. Breaks on narrow/mobile. | |
| Second column — Editable / Extracted side by side | Two columns. Complex grid layout, especially with docket pills. | |

**User's choice:** Below the input, small muted text (Recommended)

---

**Question: How is the hint labeled?**

| Option | Description | Selected |
|--------|-------------|----------|
| "Extracted: [value]" prefix (Recommended) | Example: "Extracted: 22-111" or "Extracted: N/A". Clear provenance signal. | ✓ |
| "From PDF: [value]" prefix | Example: "From PDF: 22-111". More specific, slightly wordier. | |
| No prefix — just the value in muted text | Example: "22-111" in gray. Minimal but loses provenance signal. | |

**User's choice:** "Extracted: [value]" prefix (Recommended)

---

**Question: For docket hints with multiple extracted dockets, how do they display?**

| Option | Description | Selected |
|--------|-------------|----------|
| Comma-joined inline (Recommended) | "Extracted: 22-111, 22-222" — all dockets on one line. Compact. | |
| One per line as small pills/tags | Each extracted docket gets its own mini pill in the hint area. More visual. | ✓ |
| Count only when multiple | "Extracted: 22-111, 22-222 (2 dockets)" or count only. Unnecessarily verbose. | |

**User's choice:** One per line as small pills/tags

---

## Claude's Discretion

- Component and prop naming (`ArgumentDetailsCard`, prop shapes for `savedValues` and `hints`)
- Whether `savedValues` and `hints` are separate props or a merged prop — researcher determines cleanest shape given `cover_metadata` JSONB structure
- Parse stat card backend additions — researcher audits what API fields are available and what needs adding for PJOB-10

## Deferred Ideas

None — discussion stayed within phase scope.
