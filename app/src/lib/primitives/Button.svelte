<script lang="ts">
	// lib/primitives/Button.svelte — D-17 shared primitive. No standalone
	// Button component existed before this phase; padding/cursor/border-radius
	// values are drawn from the inline <button> blocks already in the codebase
	// (public: ChatBubble's avatar button, SectionRail's nav buttons; admin:
	// the argument-detail page's Save/Cancel/Delete buttons), the touch-target
	// and accessible-name contract come directly from 51-UI-SPEC.md.
	//
	// Surface-agnostic: this file must never import from the public or admin
	// component directories, and carries no bench/advocate or admin/public
	// knowledge.
	//
	// UI-SPEC E4: the shared primitive carries the loading/pending variant
	// (operator ruling, see 51-DESIGN-DECISIONS.md "Button loading variant") —
	// not an admin-only wrapper. Public callers simply never pass `loading`;
	// the state is reachable only from admin form submissions today.
	//
	// Accessible-name contract (mandatory, UI-SPEC "Visual Hierarchy & Icon
	// Accessibility"): an icon-only control (no visible text `children`) MUST
	// carry a programmatic name via `label`, `ariaLabel`, or `ariaLabelledby`.
	// This is enforced by the TYPE below, not by convention — a `<Button
	// icon={X} />` with none of the three is a compile error (see the
	// AccessibleName union). A `title` attribute is never used as a substitute
	// (WCAG 2.1 AA — unreliable across screen readers, invisible to touch).
	// The icon element itself is always `aria-hidden="true"`, since by
	// construction the control is always named some other way (visible text,
	// or one of the three aria paths) before an icon can render at all.
	import type { Component, Snippet } from 'svelte';
	import type { LucideIcon } from '@lucide/svelte';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';

	type ButtonVariant = 'primary' | 'destructive' | 'neutral';

	// Each branch requires exactly one accessible-name prop; the other two are
	// `?: never` so all three keys are always present (as optional) across the
	// union, which is what makes plain object destructuring below type-check.
	type AccessibleName =
		| { label: string; ariaLabel?: never; ariaLabelledby?: never }
		| { label?: never; ariaLabel: string; ariaLabelledby?: never }
		| { label?: never; ariaLabel?: never; ariaLabelledby: string };

	// Icon-only: no visible text content, so an accessible name MUST come from
	// one of the three aria paths above.
	type IconOnlyButtonProps = { icon: LucideIcon; children?: never } & AccessibleName;

	// Labeled: visible text content is the control's accessible name by
	// ordinary HTML semantics; an icon here is purely decorative, and the
	// three aria props are optional extras (e.g. a more specific announced
	// name than the visible text), never required.
	type TextButtonProps = {
		icon?: LucideIcon;
		children: Snippet;
		label?: string;
		ariaLabel?: string;
		ariaLabelledby?: string;
	};

	type ButtonProps = (IconOnlyButtonProps | TextButtonProps) & {
		variant?: ButtonVariant;
		dense?: boolean;
		loading?: boolean;
		type?: 'button' | 'submit' | 'reset';
		disabled?: boolean;
		onclick?: (event: MouseEvent) => void;
	};

	let {
		icon: Icon,
		children,
		label,
		ariaLabel,
		ariaLabelledby,
		variant = 'neutral',
		dense = false,
		loading = false,
		type = 'button',
		disabled = false,
		onclick
	}: ButtonProps = $props();

	const VARIANT_COLOR: Record<ButtonVariant, string> = {
		primary: 'var(--color-accent)',
		destructive: 'var(--color-destructive)',
		neutral: 'var(--color-text-secondary)'
	};

	let color = $derived(VARIANT_COLOR[variant]);
	let isDisabled = $derived(disabled || loading);
	// A visible `label` prop doubles as the accessible name when the control
	// has no visible text `children` (the icon-only branch) — an
	// `aria-label` on top of already-visible text would be redundant, so it
	// is applied only in that case.
	let resolvedAriaLabel = $derived(!children ? (ariaLabel ?? label) : ariaLabel);
</script>

<button
	{type}
	disabled={isDisabled}
	aria-busy={loading ? 'true' : undefined}
	aria-label={resolvedAriaLabel}
	aria-labelledby={ariaLabelledby}
	{onclick}
	style="
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: var(--space-sm);
		min-height: {dense ? 'var(--touch-target-dense)' : 'var(--touch-target)'};
		padding: {dense ? 'var(--space-xs) var(--space-sm)' : 'var(--space-sm) var(--space-md)'};
		background: transparent;
		border: 1px solid {color};
		border-radius: 6px;
		font-family: inherit;
		font-size: var(--font-size-body);
		font-weight: var(--font-weight-semibold);
		line-height: var(--line-height-body);
		color: {color};
		cursor: {isDisabled ? 'not-allowed' : 'pointer'};
		opacity: {isDisabled ? 0.7 : 1};
		white-space: normal;
	"
>
	{#if loading}
		<LoaderCircle aria-hidden="true" size={16} class="primitive-button-spinner" />
	{:else if Icon}
		<Icon aria-hidden="true" size={16} />
	{/if}
	{#if children}
		{@render children()}
	{/if}
</button>

<style>
	@keyframes primitive-button-spin {
		to {
			transform: rotate(360deg);
		}
	}

	:global(.primitive-button-spinner) {
		animation: primitive-button-spin 0.8s linear infinite;
	}

	@media (prefers-reduced-motion: reduce) {
		:global(.primitive-button-spinner) {
			animation-duration: 2.4s;
		}
	}
</style>
