<script lang="ts">
	// lib/primitives/Card.svelte — D-17 shared primitive. Generalized from the
	// admin StatCard component, which was already exactly the card pattern
	// applied identically everywhere in the codebase (CONTEXT.md): surface
	// background, 1px border, 8px radius, 24px padding. StatCard now delegates
	// to this component instead of duplicating the pattern.
	//
	// Surface-agnostic: this file must never import from the public or admin
	// component directories, and carries no bench/advocate or admin/public
	// knowledge.
	//
	// `title` is OPTIONAL — when absent, no heading element renders at all,
	// not an empty one (UI-SPEC E4 "empty" row). `children` is also optional;
	// when it renders nothing the card still renders its own box rather than
	// collapsing, and when the snippet itself is entirely absent we skip
	// calling it (never invoke an undefined snippet).
	import type { Snippet } from 'svelte';

	interface CardProps {
		title?: string;
		children?: Snippet;
	}

	let { title, children }: CardProps = $props();
</script>

<div
	style="
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: var(--space-xl);
	"
>
	{#if title}
		<h2
			style="
				font-size: var(--font-size-heading);
				font-weight: var(--font-weight-semibold);
				line-height: var(--line-height-heading);
				color: var(--color-text-primary);
				margin: 0 0 var(--space-lg) 0;
			"
		>
			{title}
		</h2>
	{/if}
	{#if children}
		{@render children()}
	{/if}
</div>
