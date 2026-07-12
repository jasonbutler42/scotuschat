---
phase: 25
slug: pipeline-job-detail-page
status: approved
shadcn_initialized: false
preset: none
created: 2026-07-07
---

# Phase 25 - UI Design Contract

> Visual and interaction contract for the Pipeline Job Detail Page phase. Generated inline by Codex from `$gsd-ui-phase 25`, using the same researcher/checker gates because subagent dispatch was not available under the current runtime policy.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | bits-ui available; use only if a popover/dialog primitive is needed |
| Icon library | none currently established; do not add a new icon package for this phase |
| Font | inherit existing admin/system font |

### Visual Direction

This is an operator workflow screen, not a marketing page. The page should feel dense, calm, and work-focused: clear status, compact guidance, predictable controls, and no decorative hero treatment.

Preserve the existing admin dark interface:

- Page background: `#0f1117`
- Card surface: `#1e293b`
- Card border: `#334155`
- Primary text: `#e2e8f0`
- Muted text: `#94a3b8`
- Subtle muted text: `#64748b`

Use semantic color as restrained status language, not decoration.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Extracted hint gaps, badge inner gap, helper text margin |
| sm | 8px | Compact row gaps, button pairs, table cell micro-spacing |
| md | 16px | Default field/card child spacing, card heading bottom margin |
| lg | 24px | Card padding, page horizontal padding, footer action spacing |
| xl | 32px | Separation before secondary sections when needed |
| 2xl | 48px | Page top padding and major section breaks |
| 3xl | 64px | Reserved; avoid unless the page needs a large empty-state gap |

Exceptions:

- Status badges may use `2px 8px` padding to match existing implementation.
- Dense table controls may use 36px minimum height when embedded in rows; primary card actions remain 44px minimum height.

### Layout Contract

- Page container remains `max-width: 860px`, centered, with `padding: 48px 24px`.
- Do not nest cards inside cards. The run status card, Argument Details card, step cards, resolve card, failed card, participant/provenance sections, and Danger Zone are sibling cards.
- Run status card is the first workflow card after the page header.
- Danger Zone remains the final card on the page in every state.
- Primary actions live inside the relevant card:
  - `Create Argument` lives in the run status card.
  - `Continue Resolve` lives at the bottom of the resolve card.
  - Failed-run recovery guidance lives inside the failed step card.
- Already-created pages are read-only provenance pages. No metadata, resolve, or rerun editing controls should remain visible.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.5 |
| Label | 14px | 400 | 1.4 |
| Heading | 20px | 600 | 1.2 |
| Display | not used | not used | not used |

### Typography Rules

- Do not introduce hero-scale typography on this screen.
- Card headings use 20px / 600 and should stay short: `Run status`, `Argument Details`, `Resolve`, `Danger Zone`.
- Table column labels use 14px muted text.
- Helper text and extracted hints use 14px muted text.
- Raw error details use monospace only inside the expandable technical details block.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0f1117` | Page background |
| Secondary (30%) | `#1e293b` | Card surfaces, buttons that must blend with cards |
| Accent (10%) | `#93c5fd` | Primary CTA border/text, focused links, active/running status |
| Destructive | `#ef4444` | Failed status, raw error label, delete confirmation only |

Additional semantic colors:

| Role | Value | Usage |
|------|-------|-------|
| Success | `#4ade80` | Completed status, saved confirmation |
| Warning | `#fbbf24` | Needs review, Missing tenure warning |
| Muted | `#94a3b8` | Secondary copy, labels, historical/provenance text |
| Border | `#334155` | Default card/input/table borders |

Accent reserved for:

- `Create Argument`
- `Continue Resolve`
- Argument editor link in already-created state
- Source PDF link
- Active/running status
- Focus borders where the existing implementation already uses accent treatment

Do not use accent for every interactive element. Secondary actions use neutral borders.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Create Argument` |
| Resolve CTA | `Continue Resolve` |
| Already-created heading | `Argument created` |
| Already-created body | `This run is preserved as the source history for the argument.` |
| Already-created link | `Open argument editor` |
| Not-ready heading | `Not ready to create argument` |
| Not-ready blocker intro | `Resolve these items before creating the argument.` |
| Ready heading | `Ready to create argument` |
| Failed heading | `This run failed` |
| Failed default body | `Correct the issue, then start a new run from the pipeline page.` |
| Raw error disclosure | `Technical details` |
| Missing tenure label | `Missing tenure` |
| Missing tenure action | `Edit person` |
| Create person action | `Create new person` |
| Create person dialog heading | `Create person` |
| Create person dialog helper | `Add the minimum details needed to finish resolve. Complete the profile later in People.` |
| Delete action | `Delete run` |
| Destructive confirmation | `Delete run: this removes the admin job record only. The argument and pipeline data remain.` |

### Failed-Step Guidance Copy

Use step-specific guidance when `current_step` is known:

| Failed step | Guidance |
|-------------|----------|
| Ingest | `Check the PDF source or upload, then start a new run.` |
| Parse | `Check whether the transcript format is supported. If the source is correct, start a new run after adjusting the input.` |
| Resolve | `Check speaker aliases and people records, then start a new run if the underlying data has changed.` |
| Unknown | `Correct the issue, then start a new run from the pipeline page.` |

Important: do not present `Re-run with same source` as the primary recovery action. Phase 25 context supersedes the older PJOB-22 wording that mentioned rerun. Failed-state recovery should guide the operator to start a corrected new run.

---

## Interaction Contract

### Run Status Card

The card has three states:

| State | Required UI |
|-------|-------------|
| Not ready | Status badge, source PDF link when available, blocker checklist, no enabled `Create Argument` button |
| Ready | Status badge, source PDF link, no blockers, primary `Create Argument` CTA |
| Already created | Status badge, source PDF link, `Argument created` copy, `Open argument editor` link, no rerun action |

Strict blockers for `Create Argument`:

- Linked argument exists
- Docket present
- Question number present
- Argued date present
- Resolve rows are dispositioned
- No failed step
- No currently running step

### Resolve Card

Column order is locked:

1. Raw label
2. Resolved as (avatar plus name)
3. Bench/Advocate
4. Argument Role
5. Title (advocates only)
6. Action

Rules:

- Preserve automatic matching. Auto-resolved rows should look complete but remain changeable.
- Rows needing intervention should guide side selection before person selection without making the whole table feel manual.
- Do not show a separate confirmation checkmark column.
- `Continue Resolve` appears in the resolve card footer only when all rows are dispositioned.
- In Already created state, the resolve card is read-only.

### Person Creation Popover

The create-person flow is a mini popover/dialog, not a full editor.

Fields:

- Name
- Bench/Advocate segmented control or radio group

Effects:

- Bench sets `is_justice=true` on the person record and `side=BENCH` on the participant.
- Advocate sets `is_justice=false` on the person record and the appropriate non-bench participant side selected in the row.
- Full bio/photo/tenure/person metadata is completed later in People Admin.

Popover layout:

- Use a focused dialog/popover surface over the current row context.
- Keep width between 360px and 480px on desktop.
- On mobile, width is `calc(100vw - 32px)`.
- Primary action: `Create person`.
- Secondary action: `Cancel`.

### Advocate Role and Title Editing

- Advocate Argument Role and Title must be editable before Create Argument.
- Extracted hints must be visible for Title, following the same provenance style as `ArgumentDetailsCard`: `Extracted: [value]` or `Extracted: N/A`.
- Inline table controls are preferred. Edit-on-demand is allowed only if inline controls make the row too dense.

### Bench Tenure Role

- Bench role is derived from tenure at argued date.
- If no tenure matches, show `Missing tenure` in warning color plus `Edit person`.
- Do not add inline tenure editing in this phase.
- After Argument Details save, refresh resolve-card data immediately so tenure-derived roles update without a manual page reload.

### Historical / Already Created Page

Once argument status is no longer `pipeline`:

- Treat the page as read-only provenance.
- Hide metadata editing controls.
- Hide resolve editing controls.
- Hide rerun controls.
- Keep source PDF link, status, step cards/results, relevant failure/details sections, argument editor link, and Danger Zone.

---

## Component Contract

### Existing Components to Preserve

- `ArgumentDetailsCard.svelte`: preserve API and extracted hint behavior. Phase 25 may add callbacks/refresh integration but must not redesign the component.
- `DocketPillInput.svelte`: preserve pill input behavior.

### New or Refactored UI Units

Recommended decomposition:

- `RunStatusCard.svelte`
- `ResolveCard.svelte`
- `FailedStepGuidance.svelte`
- `CreatePersonPopover.svelte`
- `StatusBadge.svelte` or local helper if extraction is too much for this phase

Components must receive data from `+page.server.ts` / parent props. They should not fetch their own data.

---

## Responsive Contract

Desktop:

- Resolve rows can use table layout with the locked column order.
- Keep row controls compact and aligned.
- Avoid horizontal overflow at `max-width: 860px`; if necessary, use a horizontally scrollable table wrapper with visible focus outlines.

Mobile:

- Resolve table may collapse rows into stacked field groups.
- Preserve the same information order: Raw label, Resolved as, Bench/Advocate, Argument Role, Title, Action.
- Primary actions remain full-width within their cards.
- Popover/dialog must not exceed viewport width.

---

## Accessibility Contract

- All buttons and links have visible focus outlines.
- Source PDF and argument editor links are real links, not buttons.
- Status badges cannot rely on color alone; include text labels.
- Failed guidance uses `role="alert"` only for the immediate failure summary, not for the entire technical detail block.
- Raw technical errors use `white-space: pre-wrap` and `word-break: break-word`.
- Popover/dialog traps focus while open and returns focus to the trigger on close.
- Segmented/radio controls for Bench/Advocate must be keyboard operable.
- Minimum target size is 44px for primary and destructive actions. Dense table secondary controls may be 36px minimum only when visually grouped in rows.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party blocks | none | not allowed for this phase |

Do not install a registry block or visual component library for this phase. If a dialog/popover primitive is needed, use the existing `bits-ui` dependency or implement with native Svelte/HTML semantics.

---

## Requirement Tension

PJOB-22 says `"Re-run" action lives inside the failed step card`. Phase 25 user context supersedes that older wording:

- Failed card should not offer rerun-same-source as primary recovery.
- Already-created historical pages should not show rerun.
- Recovery should guide the operator to start a corrected new run from `/admin/pipeline/`.

Planner should treat this as an intentional requirement clarification, not a design gap.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-07-07
