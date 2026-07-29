# Phase 36: Click-to-copy extracted values design pattern - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 6 new/modified files
**Analogs found:** 5 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/src/lib/components/CopyableExtractedValue.svelte` | component | event-driven browser capability | Native buttons and local UI state in `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | partial; no existing clipboard component |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | component | form readout / event-driven copy | Existing extracted hint rows in the same file | exact integration seam |
| `app/src/lib/components/ResolveCard.svelte` | component | row-oriented form / event-driven copy | Existing editable title hint branch in the same file | exact integration seam |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | route component | form request-response / event-driven copy | Existing speaker title hint in the same file | exact integration seam |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | route component | server-loaded readout / event-driven copy | Existing parsed-output values and docket pill in the same file | exact integration seam |
| `CLAUDE.md` | project guide | durable implementation convention | Existing Svelte/frontend constraints in the same guide | exact guide-insertion analog |

No server load file, API route, database file, or package manifest needs modification. All values are already supplied to the four consumers.

## Pattern Assignments

### `app/src/lib/components/CopyableExtractedValue.svelte` (component, event-driven)

**Analog:** native stateful buttons in `app/src/routes/admin/pipeline/[job_id]/+page.svelte`; there is no clipboard-specific analog.

**Svelte 5 component convention** (`ArgumentDetailsCard.svelte`, lines 1-4 and 36-42):

```svelte
<script lang="ts">
	import { enhance } from '$app/forms';
	import { tick } from 'svelte';
	import DocketPillInput from '$lib/components/DocketPillInput.svelte';

	let { savedValues, hints, action, readonly = false, form = null }: ArgumentDetailsCardProps = $props();
</script>
```

Follow this typed `$props()` / rune-era style. The new component should accept the final visible `value: string | null | undefined`, a field-specific `copyLabel: string`, and a small visual `variant: 'text' | 'pill'` defaulting to text. Do not accept raw and formatted values separately.

**Native button/state convention** (`pipeline/[job_id]/+page.svelte`, lines 183-191 and 482-495):

```svelte
let deleteConfirming = $state(false);

<button
	type="button"
	onclick={() => { deleteConfirming = false; }}
>
	Cancel
</button>
```

Use `button type="button"`, `onclick`, and component-local `$state`. Implement `idle | copied | error`, retain one timeout handle, clear it before every attempt and on component destruction, and reset success after exactly 1,500ms. Clipboard access belongs only inside the activation handler:

```ts
if (!navigator.clipboard) throw new Error('Clipboard unavailable');
await navigator.clipboard.writeText(value);
```

Catch failures without exposing exception details. Render local `Couldn't copy.` feedback with `role="alert"`; render success as `Copied` in a local `aria-live="polite"` region. A later success clears the error.

**Focus and sizing convention** (`app/src/app.css`, lines 28-32):

```css
*:focus-visible {
	outline: 2px solid #93c5fd;
	outline-offset: 3px;
	border-radius: 4px;
}
```

Do not override the global focus indicator. The whole visible value plus a trailing decorative 16px SVG is one inline-flex target with at least 36px height and 8px horizontal padding. Use native `disabled` for missing/empty values, display `N/A`, set `title="Nothing extracted to copy."`, omit it from tab order through native semantics, and use muted `#94a3b8` / `#334155` styling with no hover accent.

### `app/src/lib/components/ArgumentDetailsCard.svelte` (component, form readout)

**Analog/integration seam:** extracted docket hints, lines 114-142; question/date hints, lines 172-184 and 213-225.

```svelte
<span style="font-size: 14px; font-weight: 400; color: #94a3b8;">Extracted:</span>
{#if hints.dockets.length > 0}
	{#each hints.dockets as hintDocket}
		<span style="display: inline-flex; ... height: 24px;">{hintDocket}</span>
	{/each}
{:else}
	<span style="... font-style: italic;">N/A</span>
{/if}
```

Import through `$lib/components/CopyableExtractedValue.svelte`, matching the existing alias convention. Preserve the caller-owned `Extracted:` prefix and flex wrapping. Replace each docket span with a separate pill-variant instance (`copyLabel="Copy docket"`) so each click copies only one docket. Replace the empty branch with one disabled pill instance. Replace only the value portions of question/date paragraphs with text instances; use field-specific labels (`Copy question number`, `Copy argued date`) and pass the exact displayed strings already in `hints`.

### `app/src/lib/components/ResolveCard.svelte` (component, row-oriented form)

**Analog/integration seam:** editable title branch, lines 639-644.

```svelte
<p style="margin: 4px 0 0 0; font-size: 13px; color: #94a3b8; {!row.title_hint ? 'font-style: italic;' : ''}">
	Extracted: {row.title_hint ?? 'N/A'}
</p>
{:else}
	<span>{row.title ?? '—'}</span>
```

Add the shared component import next to the `$lib/components/CreatePersonPopover.svelte` import (lines 1-4). In the `row.editable` title-input branch, preserve the paragraph/prefix and replace only the hint value with `CopyableExtractedValue`, using `value={row.title_hint}` and `copyLabel="Copy title"`. Keep the non-editable branch unchanged: it has no operator-editable destination and therefore does not meet D-13.

### `app/src/routes/admin/arguments/[id]/+page.svelte` (route component, form request-response)

**Analog/integration seam:** imports at lines 2-3 and speaker title hint at lines 480-490.

```svelte
import { enhance } from '$app/forms';
import ArgumentDetailsCard from '$lib/components/ArgumentDetailsCard.svelte';

<p style="font-size: 14px; ... {!speaker.title_hint ? 'font-style: italic;' : ''}">
	Extracted: {speaker.title_hint ?? 'N/A'}
</p>
```

Import the shared component through `$lib/components`. Preserve the inline speaker form and `Extracted:` prefix; replace only the title-hint value with the text variant using `copyLabel="Copy title"`. The argument details docket/question/date coverage arrives through the existing `ArgumentDetailsCard` import and must not be duplicated at page level.

### `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (route component, server-loaded readout)

**Analog/integration seam:** component imports at lines 2-7; parse readouts at lines 287-373.

```svelte
{#if ps.argued_date}
	<span style="font-size: 16px; color: #e2e8f0;">{formatDate(ps.argued_date)}</span>
{:else}
	<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
{/if}
```

Import the shared component beside the other `$lib/components` imports. Adopt it only for:

- `ps.case_name` with `Copy case name`;
- the final string `formatDate(ps.argued_date)` with `Copy argued date` (never copy the raw ISO value);
- `ps.primary_docket` using the pill variant and `Copy docket`;
- `ps.question_number` converted/passed as the exact rendered string with `Copy question number`.

Leave utterance, bench, advocate, and total speaker counts plain. They have no operator-editable destination. Preserve the existing `ArgumentDetailsCard` and `ResolveCard` consumers, which gain their behavior through their own integrations.

### `CLAUDE.md` (project guide, durable convention)

**Analog/integration seam:** the existing frontend architecture bullets that require SvelteKit 2.x, Svelte 5 runes, server-load data flow, and preservation of global project constraints.

Add the D-13 convention adjacent to those frontend/Svelte rules rather than creating a disconnected phase-history section. State both halves together: extracted fields with an operator-editable destination receive the shared click-to-copy control by default unless a phase explicitly opts out; read-only extracted values without an operator-editable destination remain excluded. Name `CopyableExtractedValue` as the reuse target. Insert only this concise convention and preserve every unrelated guide rule verbatim.

## Shared Patterns

### Imports and component ownership

Use `$lib/components/...` aliases as all four consumers already do. Formatting and scope selection remain caller-owned; `CopyableExtractedValue` owns only clipboard activation, timer/error state, semantics, SVG, and styles.

### Exact display-string boundary

Pass one final display string and use it for both Svelte text interpolation and `navigator.clipboard.writeText`. Do not trim, normalize, concatenate docket arrays, or independently format inside the component. In particular, the pipeline argued date must be formatted once at the caller boundary.

### Local feedback and errors

The repository already locates errors beside their owning control (for example `ArgumentDetailsCard.svelte`, lines 240-261, uses `role="alert"`). Keep clipboard success/failure per component instance; do not add a page toast, shared store, or cross-instance live region.

### Native accessibility

Use native button keyboard and disabled behavior. Retain the global focus-visible rule. The SVG is decorative (`aria-hidden="true"`); the button's accessible name reflects the current field-specific action or copied state. Disabled `N/A` remains visible but is skipped by Tab.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/src/lib/components/CopyableExtractedValue.svelte` | component | event-driven browser capability | No shared clipboard helper, tooltip wrapper, or transient-copy control exists; use the approved UI/research contract plus native button and Svelte 5 conventions. |

## Verification Conventions

No frontend test harness exists in `app/package.json` (lines 5-10); do not add one or install packages in this phase. Run:

```powershell
Set-Location app
npm run check
npm run build
```

Then browser-UAT exact copied payloads, individual dockets, repeated-click timer restart, local clipboard rejection, disabled Tab behavior, Enter/Space activation, `Copied`/error announcements, 36px targets, narrow-width wrapping, and unchanged non-editable count readouts.

## Metadata

**Analog search scope:** `app/src/lib/components`, `app/src/routes/admin`, `app/src/app.css`, `app/package.json`, `CLAUDE.md`
**Files scanned deeply:** 7
**Pattern extraction date:** 2026-07-14

