# Phase 36: Click-to-copy extracted values design pattern - Research

**Researched:** 2026-07-14
**Domain:** Svelte 5 reusable clipboard interaction for operator-facing extracted values
**Confidence:** HIGH

## User Constraints

### Locked Decisions

#### Copy target and value rules
- **D-01:** Copy exactly the value the operator sees, even when that differs from the raw stored value.
- **D-02:** For extracted docket pills, clicking a pill copies only that individual docket.
- **D-03:** The value text and copy icon are one generous clickable target.
- **D-04:** The icon sits immediately after the value as a trailing affordance.

#### Copy feedback
- **D-05:** Use field-specific hover text such as “Copy docket.”
- **D-06:** On successful copy, the affordance briefly changes to “Copied” and then returns to the field label.
- **D-07:** Repeated clicks while the success state is visible restart the brief success timer.
- **D-08:** Copy failures stay local and explanatory, using a short message like “Couldn't copy.” Do not escalate to a toast.

#### Disabled `N/A` state
- **D-09:** When nothing was extracted, keep the slot visible with a disabled copy affordance instead of hiding it or converting it to plain text.
- **D-10:** The disabled-state tooltip is “Nothing extracted to copy.”
- **D-11:** Disabled copy affordances are not focusable in the tab order.
- **D-12:** Disabled state styling is muted text/icon with no hover accent.

#### Scope rule
- **D-13:** Default policy for future phases: if a field is specified as extracted and has an operator-editable destination, it gets click-to-copy unless the phase explicitly says otherwise.

### Agent's Discretion
- Exact shared abstraction shape for the reusable interaction, as long as the interaction stays identical across pipeline and argument-editor surfaces.
- Exact copied-state timing, provided it remains brief and visually obvious.
- Whether read-only extracted readouts without an operator-editable destination are intentionally excluded from the default rule.

### Deferred Ideas

None — discussion stayed within phase scope.

## Summary

Phase 36 is a frontend-only refactor/addition around existing data. The strongest implementation seam is a new leaf component such as `CopyableExtractedValue.svelte`, consumed by the shared `ArgumentDetailsCard`, `ResolveCard`, the argument editor speaker rows, and the pipeline job detail parsed-output readouts. The component should receive the already-formatted display string and a field-specific copy label; it must not know about raw API data, formatting, forms, or page load contracts. This makes D-01 structural: callers pass exactly the rendered value, and the component writes that same string. [VERIFIED: codebase inspection of the four Phase 36 surfaces]

Use the platform Clipboard API directly. `navigator.clipboard.writeText()` returns a Promise, may reject, and is restricted to secure contexts/user activation; a native button click supplies the intended activation, while the component must catch both a missing API and a rejected Promise and render local failure feedback. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText] [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API]

No external package or backend change is warranted. The approved UI contract already fixes the visual state machine, 1,500ms success duration, native-button semantics, SVG icon, copy strings, included/excluded fields, and cleanup behavior. [VERIFIED: `36-UI-SPEC.md`]

**Primary recommendation:** Build one presentation-agnostic Svelte 5 copy control around the displayed string, then replace only the in-scope extracted readouts at all four consumers and validate compile, keyboard/accessibility states, exact clipboard payloads, timer restart, and failure handling.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Clipboard state machine | Shared Svelte component | Browser Clipboard API | One implementation owns idle/success/failure/disabled behavior. |
| Display formatting | Existing caller | Shared component | Dates, docket strings, and titles are already formatted at their surfaces; pass the final visible string unchanged. |
| Field-specific copy name | Existing caller | Shared component | Caller knows whether the value is a docket, title, case name, question number, or argued date. |
| Docket collection iteration | Existing caller | Shared component per item | D-02 requires one component/button and one clipboard call per displayed docket. |
| Feedback and announcements | Shared component | Native HTML semantics | Local `aria-live`/alert feedback prevents unrelated instances from announcing state. |
| Extracted data loading | Existing server load paths | Existing API models | This phase does not alter extraction, schemas, or server payloads. |

## Standard Stack

### Core

| Library/API | Version | Purpose | Why Standard |
|-------------|---------|---------|--------------|
| Svelte | `^5.30.0` | Component state, props, lifecycle cleanup | Already installed and used with runes throughout the app. [VERIFIED: `app/package.json`] |
| SvelteKit | `^2.21.0` | Existing application framework | All target surfaces are existing SvelteKit admin routes/components. [VERIFIED: `app/package.json`] |
| Clipboard API | Browser platform | Write the displayed string | The approved contract explicitly requires `navigator.clipboard.writeText(displayValue)`. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText] |
| Native HTML button | Browser platform | Keyboard activation and disabled semantics | Preserves Enter/Space activation and removes disabled controls from normal interaction without custom handlers. [VERIFIED: `36-UI-SPEC.md`] |

### Supporting

| Library/API | Version | Purpose | When to Use |
|-------------|---------|---------|-------------|
| Inline SVG | Local markup | 16px trailing copy icon | Use inside the unified button with `aria-hidden="true"`; no icon package. |
| Global focus CSS | Existing | Visible keyboard focus | `app/src/app.css` already supplies the required 2px `#93c5fd` outline and 3px offset. [VERIFIED: codebase inspection] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Platform Clipboard API | Clipboard package or `document.execCommand` fallback | Adds dependency or deprecated/custom behavior contrary to the UI contract. |
| Native `title` plus inline state | Tooltip library | Adds unnecessary machinery; Bits UI is installed but explicitly not required here. |
| One shared component | Page-local handlers | Duplicates timers, error semantics, icon, accessibility, and styles across four surfaces. |

**Installation:** None.

## Package Legitimacy Audit

Not applicable. This phase must not install any package; it uses the existing Svelte stack and browser APIs. [VERIFIED: `36-UI-SPEC.md`]

## Architecture Patterns

### System Architecture Diagram

```text
existing server load / existing component props
                    |
                    v
caller formats/selects visible extracted value
                    |
          value + field-specific label
                    v
       CopyableExtractedValue component
          |                       |
    enabled button          disabled N/A button
          |                       |
          v                       +--> no clipboard call
navigator.clipboard.writeText(displayValue)
          |
    +-----+------+
    |            |
 success       rejection/unavailable
    |            |
 "Copied"     "Couldn't copy."
 1500ms         local alert
    |
 reset/restart timer on next activation
```

### Recommended Project Structure

```text
app/src/
├── lib/components/
│   ├── CopyableExtractedValue.svelte   # shared copy state machine and presentation
│   ├── ArgumentDetailsCard.svelte      # docket/question/date hint consumer
│   └── ResolveCard.svelte              # editable title-hint consumer
└── routes/admin/
    ├── arguments/[id]/+page.svelte     # speaker title-hint consumer
    └── pipeline/[job_id]/+page.svelte  # parsed-output consumer
```

### Pattern 1: Final-display-string boundary

**What:** The component accepts a nullable `value` that is already the exact text shown to the operator, plus an action label such as `Copy docket`.

**When to use:** Every extracted display with an operator-editable destination. Do formatting at the caller, then pass the same string once for rendering and copying.

```svelte
<CopyableExtractedValue value={formatDate(ps.argued_date)} copyLabel="Copy argued date" />
```

This is especially important on the pipeline parsed-output argued date: copying the raw ISO source would violate D-01 because the page currently renders `formatDate(ps.argued_date)`. [VERIFIED: `app/src/routes/admin/pipeline/[job_id]/+page.svelte`]

### Pattern 2: Per-instance finite state and restartable timer

**What:** Each instance owns `idle | copied | error` feedback plus one timeout handle. Activation clears the prior timeout, attempts the clipboard write, clears prior errors on success, enters copied state, and schedules reset after exactly 1,500ms. Component destruction clears the timeout.

**When to use:** Every instance, including each docket pill. Do not share a page-level copied field identifier; local state is simpler and satisfies local announcements.

```ts
// Source: Clipboard behavior from MDN; timing/state fixed by 36-UI-SPEC.md
async function copyVisibleValue() {
  clearTimeout(resetTimer);
  try {
    if (!navigator.clipboard) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(value);
    state = 'copied';
    resetTimer = setTimeout(() => (state = 'idle'), 1500);
  } catch {
    state = 'error';
  }
}
```

### Pattern 3: Native button semantics for all states

**What:** Render the value and icon inside one `button type="button"`. For a null/empty extracted value, render `N/A` in the same component with native `disabled`, the specified muted styling, and `title="Nothing extracted to copy."`.

**When to use:** Both ordinary text and docket-pill visual variants. The component likely needs a small `variant`/class-style prop (`text` versus `pill`) rather than separate behavior components, because docket pills retain a bordered compact appearance while sharing state and semantics.

### Pattern 4: Caller-owned scope filtering

**What:** Apply the component only where the readout feeds an editable destination.

**When to use:** The pipeline parsed-output card includes many values, but only case name, formatted argued date, primary docket, and question number are in scope. Utterance, bench, advocate, and total counts remain plain readouts because there is no operator-editable destination. [VERIFIED: `36-UI-SPEC.md` and route inspection]

### Anti-Patterns to Avoid

- **Copying raw backing data:** Passing `ps.argued_date` while rendering `formatDate(ps.argued_date)` violates D-01.
- **One copy control for multiple dockets:** Iteration belongs outside the component; each docket gets its own instance and payload.
- **Page-level toast or shared live region:** Feedback must stay beside the activated value and announcements must not leak across instances.
- **Icon-only target:** The visible text and icon must be one 36px-minimum button with 8px horizontal padding.
- **Focusable pseudo-disabled state:** Use native `disabled`; do not emulate it with only `aria-disabled` or muted CSS.
- **Copying editor input values:** The feature attaches to extracted hints/readouts, not the destination inputs or saved values.
- **Truthiness that loses valid display strings:** Normalize only absent extracted values to disabled `N/A`; do not accidentally disable a legitimate formatted string such as `"0"`.
- **Global timer/shared state:** Multiple controls can coexist and operate independently; each instance must clean up its own timeout.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Clipboard access | Hidden textarea plus selection or `execCommand` fallback | `navigator.clipboard.writeText` | Required platform API is asynchronous and exposes rejection for local error handling. |
| Keyboard activation | Clickable spans with custom key handlers | Native `button type="button"` | Enter, Space, focus, and disabled behavior come built in. |
| Tooltip system | Portal/positioning engine | Field-specific `title` and visible state text | The approved contract requires no tooltip dependency. |
| Icon dependency | New icon library | Local 16px SVG | One simple decorative glyph does not justify package surface. |
| Cross-page clipboard store | Shared rune/store | Component-local state | Feedback is transient, per-instance, and must remain local. |

**Key insight:** The reusable value is the behavior boundary, not the data boundary. Existing pages keep responsibility for deciding and formatting what is visible; the shared component owns only copy interaction, semantics, feedback, and styles.

## Existing Surface Inventory

| Surface | Current shape | Required change |
|---------|---------------|-----------------|
| `ArgumentDetailsCard.svelte` docket hints | Each extracted docket is a 24px plain pill; absent list is italic `N/A` | Render one pill-variant copy component per docket; use disabled `N/A` component when empty; enlarge interactive target to 36px without losing pill appearance. |
| `ArgumentDetailsCard.svelte` question/date hints | Plain `<p>` containing `Extracted: value-or-N/A` | Keep prefix outside; replace only value with text-variant component. This automatically covers both argument editor and pipeline job consumers. |
| `ResolveCard.svelte` title hint | Plain `Extracted: {row.title_hint ?? 'N/A'}` below an editable title input for editable advocate rows | Keep prefix outside and use shared component only in the editable branch. |
| Argument editor speaker title hint | Plain extracted hint below title input | Use identical title component/state as ResolveCard. |
| Pipeline parsed-output case name | Plain formatted/readout text or `N/A` | Add copy/disabled component because case name has an editable destination in argument details. |
| Pipeline parsed-output argued date | `formatDate(ps.argued_date)` or `N/A` | Compute/pass the formatted result so clipboard equals visible text. |
| Pipeline parsed-output docket | One plain pill from `ps.primary_docket` or `N/A` | Use pill variant. Current parsed stats expose one primary docket, while shared argument hints already support an array. |
| Pipeline parsed-output question number | Plain text or `N/A` | Use text variant. |
| Pipeline counts | Plain numbers/`N/A` | Intentionally unchanged: no editable destination. |

No server load/action change is needed: all included values are already present in component props or page data. [VERIFIED: target route/component inspection]

## Common Pitfalls

### Pitfall 1: Clipboard works locally but fails in deployed/non-secure contexts

**Why it happens:** `writeText` requires a secure context and can reject for permissions/browser policy.

**How to avoid:** Feature-detect `navigator.clipboard`, await the Promise, catch every failure, and show the specified local error. Do not assume a button click guarantees success. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText]

### Pitfall 2: Rendering and copying use two transformations

**Why it happens:** A caller passes raw data and the component formats only its visible text, or performs copy-specific trimming.

**How to avoid:** Pass one final display string and use it for both text content and `writeText`. Do not trim or normalize inside the component.

### Pitfall 3: Repeated clicks create racing reset timers

**Why it happens:** Each success schedules a timer without cancelling the previous timer, so the first timer clears a later success early.

**How to avoid:** Clear before every attempt and before scheduling; retain exactly one timeout per instance; clean it up on destroy.

### Pitfall 4: Disabled tooltips are treated as the accessibility mechanism

**Why it happens:** Native disabled elements do not reliably expose hover/title content across inputs.

**How to avoid:** Keep visible `N/A`, native disabled semantics, muted appearance, and the specified title as supplemental help. [VERIFIED: `36-UI-SPEC.md`]

### Pitfall 5: Shared component breaks dense layout

**Why it happens:** A single block-level style is inserted inside paragraphs, pills, table cells, and wrapping rows.

**How to avoid:** Use inline-flex, preserve caller labels/prefixes, keep value/icon together, allow long values to wrap, and make pill styling a visual variant without branching behavior.

### Pitfall 6: Scope expands to unrelated parsed stats

**Why it happens:** A mechanical replacement targets every `N/A` on the pipeline page.

**How to avoid:** Use the UI contract inventory, not text search alone. Speaker/utterance totals have no destination and are explicitly excluded.

## Testing and Verification Strategy

The frontend currently declares only `dev`, `build`, `preview`, and `check` scripts and has no committed Vitest/Playwright/component-test files found by repository search. [VERIFIED: `app/package.json` and repository file search] Do not silently introduce a test framework in this phase; the plan should pair compile/static verification with focused browser UAT unless the project separately approves testing infrastructure.

### Automated gates

```powershell
Set-Location app
npm run check
npm run build
```

- `svelte-check` must report zero errors from component props, browser globals, timers, and markup.
- Production build must complete, catching SSR/browser-boundary mistakes. Clipboard access must occur only inside the user event handler, never at module initialization or during SSR.
- Use targeted source assertions/review to confirm all four consumers import the shared component and that no third-party clipboard/tooltip/icon package was added.

### Browser UAT matrix

1. On both `ArgumentDetailsCard` consumers, activate docket, question, and date values by mouse and keyboard; paste and confirm the payload exactly equals displayed text.
2. For multiple docket hints, copy each individually and verify no combined payload.
3. On pipeline parsed output, verify case name, formatted argued date, docket, and question number copy; verify all count fields remain noninteractive.
4. On `ResolveCard` and the argument editor speaker row, verify editable title hints copy and absent hints render disabled `N/A`.
5. Verify success changes locally to `Copied`, is announced politely, clears after 1,500ms, and repeated activation restarts the full interval.
6. Stub/deny `navigator.clipboard.writeText` and verify `Couldn't copy.` appears locally with alert semantics; a later successful retry clears it.
7. Tab through the page: enabled controls receive the existing focus outline, disabled controls are skipped, and Enter/Space activate enabled controls.
8. Inspect wrapping/target dimensions at narrow width: text/icon remain one target, long text is not truncated, docket appearance remains compact, and interactive height is at least 36px.

## Security Considerations

- Clipboard writes are initiated only by an explicit operator button activation; there is no background or automatic clipboard mutation. [CITED: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API]
- The payload is plain text derived from an already-rendered string. Do not use HTML clipboard formats, `innerHTML`, or dynamic SVG markup.
- Clipboard errors may differ by browser/permission state; expose only the fixed local message, not raw exception details.
- No API endpoint, database write, authentication change, user-facing public interaction, or external dependency is introduced.
- The surface is authenticated/operator-facing, but the component should remain safe if reused: it receives text as Svelte content and writes the string, rather than interpreting it as markup.

### ASVS relevance

This phase has no authentication, authorization, session, validation, database, file, or network interface change. The relevant browser-client concerns are safe output rendering and controlled use of a browser capability. Preserve Svelte text interpolation, avoid HTML injection, require direct activation, and handle denied capability access locally. [VERIFIED: phase boundary and codebase architecture]

## Project Constraints

No `AGENTS.md` exists at the repository root, and no project-local `.codex/skills` or `.agents/skills` directory was found during discovery. [VERIFIED: filesystem inspection]

From `CLAUDE.md`, the planner must preserve these applicable constraints:

- Use SvelteKit 2.x and Svelte 5 runes; do not introduce legacy stores.
- Keep FastAPI read-only and keep pipeline operations offline; this phase needs neither API nor pipeline changes.
- Route backend data through existing server load functions; do not introduce browser-side API calls.
- Preserve apolitical, symmetric treatment; the generic component must not encode speaker-role-specific behavior.
- Do not touch database schema or Alembic; this phase has no persistence work.

## Plan Guidance

A compact two-plan wave is appropriate:

1. **Shared primitive plus shared-card adoption:** create the copy component/state machine and integrate `ArgumentDetailsCard`, with static/build validation and focused UAT of enabled/disabled, exact payload, timer restart, cleanup, keyboard, failure, and pill variants.
2. **Remaining surface adoption:** integrate `ResolveCard`, argument-editor speaker titles, and only the four eligible pipeline parsed-output readouts; verify excluded counts stay plain and run full frontend checks/build plus cross-surface UAT.

Plan 2 should depend on Plan 1. The planner should name every included/excluded surface explicitly, because a broad `N/A` replacement would over-scope the phase. No backend, server load, schema, package-install, or public-interface task belongs in either plan.

## Sources

### Primary

- Phase context and locked decisions: `.planning/phases/36-click-to-copy-extracted-values-design-pattern/36-CONTEXT.md`
- Approved interaction/visual contract: `.planning/phases/36-click-to-copy-extracted-values-design-pattern/36-UI-SPEC.md`
- Existing component and route code: `ArgumentDetailsCard.svelte`, `ResolveCard.svelte`, argument editor, pipeline job detail [VERIFIED: codebase inspection]
- Clipboard `writeText` behavior and errors: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard/writeText
- Clipboard security/user activation overview: https://developer.mozilla.org/en-US/docs/Web/API/Clipboard_API

### Secondary

- Existing frontend versions and scripts: `app/package.json`
- Existing global focus treatment: `app/src/app.css`
- Project architecture constraints: `CLAUDE.md`

## Metadata

**Confidence breakdown:**
- Existing code and integration seams: HIGH — directly inspected.
- Clipboard behavior: HIGH — verified against current MDN platform documentation.
- Visual/accessibility behavior: HIGH — fixed by the approved Phase 36 UI contract and existing global CSS.
- Testing approach: HIGH for current repository capability; no frontend test harness was found, so browser UAT is required unless separate infrastructure is authorized.

**Research date:** 2026-07-14
**Valid until:** 2026-08-13 (browser-platform and local-code assumptions should be rechecked after material dependency or UI changes)
