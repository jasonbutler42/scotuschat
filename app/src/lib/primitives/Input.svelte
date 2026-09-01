<script lang="ts">
	// lib/primitives/Input.svelte — D-17 shared primitive. Copies the admin
	// DocketPillInput component's validation contract rather than inventing a
	// parallel one: an `invalid` boolean, `descriptionId`/`aria-describedby`
	// wiring, and a `role="alert"` element for error text colored
	// `var(--color-destructive)`.
	//
	// DocketPillInput itself splits ownership of that contract across two
	// tracks: a caller-driven `invalid`/`descriptionId` pair (the caller
	// renders the actual alert text elsewhere, e.g. ArgumentDetailsCard's own
	// `<p id="argument-details-alert" role="alert">`) and its own
	// internally-driven `shapeError` (which DocketPillInput renders itself, in
	// its own `<p role="alert">`). Input is a general-purpose standalone
	// control, not a compound pill-list widget, so it collapses that split
	// into one: when `invalid` is true and `errorMessage` is supplied, Input
	// renders its own `role="alert"` paragraph and wires `aria-describedby` to
	// it directly. When the caller wants to render the error text itself
	// elsewhere (matching DocketPillInput's external-track shape exactly),
	// pass `describedBy` instead of `errorMessage` and Input only wires the
	// attribute, rendering nothing of its own — this is how
	// DocketPillInput's own adoption below composes both tracks.
	//
	// Surface-agnostic: this file must never import from the public or admin
	// component directories.
	interface InputProps {
		value?: string;
		placeholder?: string;
		type?: string;
		id?: string;
		name?: string;
		disabled?: boolean;
		readonly?: boolean;
		required?: boolean;
		invalid?: boolean;
		// Caller-owned error text elsewhere in the DOM (DocketPillInput's
		// external-track shape) — Input only wires aria-describedby to it.
		describedBy?: string;
		// Input-owned error text (rendered here, in a role="alert" element).
		errorMessage?: string | null;
		errorId?: string;
		ref?: HTMLInputElement | null;
		onkeydown?: (event: KeyboardEvent) => void;
		oninput?: (event: Event) => void;
		onblur?: (event: FocusEvent) => void;
	}

	let {
		value = $bindable(''),
		placeholder,
		type = 'text',
		id,
		name,
		disabled = false,
		readonly = false,
		required = false,
		invalid = false,
		describedBy,
		errorMessage = null,
		errorId,
		ref = $bindable(null),
		onkeydown,
		oninput,
		onblur
	}: InputProps = $props();

	let ownErrorId = $derived(errorId ?? (id ? `${id}-error` : undefined));
	let hasOwnError = $derived(invalid && Boolean(errorMessage) && Boolean(ownErrorId));
	// Compose both tracks, mirroring DocketPillInput's describedByIds pattern —
	// either or both may be present.
	let resolvedDescribedBy = $derived(
		[describedBy, hasOwnError ? ownErrorId : undefined].filter(Boolean).join(' ') || undefined
	);
</script>

<input
	bind:this={ref}
	{id}
	{name}
	{type}
	{placeholder}
	{disabled}
	{readonly}
	{required}
	bind:value
	aria-invalid={invalid ? 'true' : undefined}
	aria-describedby={resolvedDescribedBy}
	{onkeydown}
	{oninput}
	{onblur}
	style="
		display: block;
		width: 100%;
		min-height: var(--touch-target);
		box-sizing: border-box;
		background-color: var(--color-bg);
		border: 1px solid {invalid ? 'var(--color-destructive)' : 'var(--color-border)'};
		border-radius: 6px;
		padding: var(--space-sm) var(--space-lg);
		font-family: inherit;
		font-size: var(--font-size-body);
		color: var(--color-text-primary);
	"
/>
{#if hasOwnError}
	<p
		id={ownErrorId}
		role="alert"
		style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			color: var(--color-destructive);
			margin: var(--space-xs) 0 0 0;
		"
	>
		{errorMessage}
	</p>
{/if}
