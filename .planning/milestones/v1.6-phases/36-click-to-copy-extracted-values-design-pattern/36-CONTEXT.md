# Phase 36: Click-to-copy extracted values design pattern - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish one reusable click-to-copy pattern for extracted values shown on operator-facing pipeline run pages and argument editor pages. The default rule is: if a field is explicitly marked as extracted and there is an operator-editable destination for that value, the extracted display should include click-to-copy unless a phase explicitly opts out. The pattern must behave identically everywhere it appears, including extracted docket number pills, and it must keep the `N/A` state visible but disabled.

This phase does not change which values are extracted, how extraction works, or any operator-editable schemas. It only standardizes the affordance and feedback around already-extracted values.

</domain>

<decisions>
## Implementation Decisions

### Copy target and value rules
- **D-01:** Copy exactly the value the operator sees, even when that differs from the raw stored value.
- **D-02:** For extracted docket pills, clicking a pill copies only that individual docket.
- **D-03:** The value text and copy icon are one generous clickable target.
- **D-04:** The icon sits immediately after the value as a trailing affordance.

### Copy feedback
- **D-05:** Use field-specific hover text such as “Copy docket.”
- **D-06:** On successful copy, the affordance briefly changes to “Copied” and then returns to the field label.
- **D-07:** Repeated clicks while the success state is visible restart the brief success timer.
- **D-08:** Copy failures stay local and explanatory, using a short message like “Couldn't copy.” Do not escalate to a toast.

### Disabled `N/A` state
- **D-09:** When nothing was extracted, keep the slot visible with a disabled copy affordance instead of hiding it or converting it to plain text.
- **D-10:** The disabled-state tooltip is “Nothing extracted to copy.”
- **D-11:** Disabled copy affordances are not focusable in the tab order.
- **D-12:** Disabled state styling is muted text/icon with no hover accent.

### Scope rule
- **D-13:** Default policy for future phases: if a field is specified as extracted and has an operator-editable destination, it gets click-to-copy unless the phase explicitly says otherwise.

### Agent's Discretion
- Exact shared abstraction shape for the reusable interaction, as long as the interaction stays identical across pipeline and argument-editor surfaces.
- Exact copied-state timing, provided it remains brief and visually obvious.
- Whether read-only extracted readouts without an operator-editable destination are intentionally excluded from the default rule.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/ROADMAP.md` §"Phase 36: Click-to-copy extracted values design pattern" — authoritative phase goal, scope, and success criteria.
- `.planning/REQUIREMENTS.md` §"UX-01" — extracted-value displays must offer a consistent click-to-copy affordance, disabled when the value is `N/A`.

### Existing operator-facing extracted-value displays
- `app/src/lib/components/ArgumentDetailsCard.svelte` — shared argument-details card already renders extracted dockets, question number, and argued date, plus the existing inline alert/focus pattern.
- `app/src/lib/components/ResolveCard.svelte` — resolve rows already render extracted title hints and are part of the pipeline run surfaces.
- `app/src/routes/admin/arguments/[id]/+page.svelte` — argument-editor surface already renders extracted title hints for speakers.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — pipeline job detail surface already renders multiple extracted readouts and `N/A` states.
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — server load path that supplies the job detail page data.
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — server load path that supplies the argument editor data.

No external specs or ADRs — requirements are fully captured by the roadmap, UX-01, and the decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ArgumentDetailsCard.svelte` already centralizes the extracted docket/question/date readouts for both the argument editor and the pipeline job detail page, so it is the strongest candidate for the reusable copy affordance around editable fields.
- The shared admin surfaces already use a consistent dark card and inline-feedback pattern, which keeps copy affordances and disabled `N/A` states visually aligned without introducing a new page-level component style.
- `ResolveCard.svelte` already contains an extracted-title hint readout in the same visual language as the other admin surfaces.

### Established Patterns
- Extracted-value readouts are currently rendered as plain text or `N/A` spans and paragraphs, so the new interaction will be an additive wrapper rather than a replacement for a complex existing control.
- Existing admin form behavior already favors preserving submitted values and showing inline feedback near the relevant control; the copy affordance should follow that local, inline model.
- The codebase currently has no shared clipboard helper or tooltip wrapper in the scanned admin surfaces, so the reusable abstraction is likely to be introduced as part of this phase.
- Docket pills are already a distinct editable control; the copy affordance should attach to extracted displays that feed those editable fields, not to the editor input itself.

### Integration Points
- The pipeline job detail page's extracted docket/question/count readouts and the argument editor's extracted docket/question/date readouts are the primary display sites for the new affordance.
- The resolve screen's extracted title hints should use the same copy pattern if they are considered operator-facing extracted values during planning, so the abstraction should not be hard-coded to one page.
- Any phase that introduces a new extracted field should decide up front whether it has an operator-editable destination; that decision determines whether the default click-to-copy rule applies.

</code_context>

<specifics>
## Specific Ideas

- The copied text must be exactly what the operator sees.
- The tooltip copy text should be field-specific, not generic.
- The success state should be transient and restart on repeated clicks.
- `N/A` should remain visible, muted, and disabled rather than disappearing.
- The user explicitly wants the rule documented as a default: extracted + operator-editable means click-to-copy unless a phase says otherwise.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 36-click-to-copy-extracted-values-design-pattern*
*Context gathered: 2026-07-14*
