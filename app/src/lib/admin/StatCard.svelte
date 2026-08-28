<script lang="ts">
	// Shared admin stat-card container (Phase 28, DASH-01/02/05).
	// First shared card component in the codebase — every other admin page
	// previously rolled its own inline card markup (28-PATTERNS.md).
	//
	// Phase 51 (D-17): delegates to $lib/primitives/Card, which is now the
	// single definition site for the card surface/border/radius/padding.
	// StatCard keeps its existing public prop shape unchanged so every
	// current call site (admin/+page.svelte) works untouched.
	//
	// D-10: the container style below is a FIXED literal — never conditional
	// on counts/urgency. Do not branch on card type inside this component;
	// each card's differently-shaped breakdown body is composed by the caller
	// via the `children` snippet.
	import Card from '$lib/primitives/Card.svelte';
	import type { Snippet } from 'svelte';

	interface StatCardProps {
		title: string;
		children: Snippet;
	}

	let { title, children }: StatCardProps = $props();
</script>

<Card {title}>
	{@render children()}
</Card>
