<script lang="ts">
	// D-14/D-15/D-16 (Phase 51 plan 51-08): term detail. Focal points per
	// 51-UI-SPEC.md: the case name on each row is primary, argued date then
	// docket number secondary, row affordances deliberately quiet. All of a
	// term's arguments render on one page — no pagination control (D-14).
	import TermRow from '$lib/public/TermRow.svelte';
	import { formatArgumentCount } from '$lib/formatting';

	let { data } = $props();
</script>

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header
		style="
			background-color: var(--color-surface);
			border-bottom: 1px solid var(--color-border);
			padding: var(--space-lg) var(--space-xl);
		"
	>
		<a
			href="/arguments"
			style="
				font-size: var(--font-size-caption);
				font-weight: var(--font-weight-regular);
				color: var(--color-accent);
				text-decoration: none;
			"
		>
			&larr; Arguments
		</a>
		<h1
			style="
				font-size: var(--font-size-display);
				font-weight: var(--font-weight-semibold);
				line-height: var(--line-height-display);
				color: var(--color-text-primary);
				margin: var(--space-sm) 0 0 0;
			"
		>
			October Term {data.termYear}
		</h1>
		{#if data.arguments && data.arguments.length > 0}
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: var(--space-xs) 0 0 0;
				"
			>
				{formatArgumentCount(data.arguments.length)}
			</p>
		{/if}
	</header>

	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: var(--space-3xl) var(--space-xl);
		"
	>
		{#if !data.arguments || data.arguments.length === 0}
			<p
				style="
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0;
					line-height: var(--line-height-body);
				"
			>
				No arguments published for October Term {data.termYear} yet.
			</p>
		{:else}
			{#each data.arguments as arg (arg.argument_id)}
				<TermRow
					slug={arg.slug}
					caseName={arg.case_name}
					docketNumber={arg.docket_number}
					argued_date={arg.argued_date}
				/>
			{/each}
		{/if}
	</div>
</main>
