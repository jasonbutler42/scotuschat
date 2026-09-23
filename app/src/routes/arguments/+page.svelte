<script lang="ts">
	// D-14/D-15/D-16 (Phase 51 plan 51-08): the term index. Replaces the
	// transitional flat listing plan 51-02 shipped against `/cases`. Focal
	// points per 51-UI-SPEC.md: the term identifier is primary, the
	// published-argument count is secondary, all chrome is deliberately
	// quiet. No CTA by design (D-14) — a row IS the action.
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
		<h1
			style="
				font-size: var(--font-size-heading);
				font-weight: var(--font-weight-semibold);
				line-height: var(--line-height-heading);
				color: var(--color-text-primary);
				margin: 0;
			"
		>
			Arguments
		</h1>
	</header>

	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: var(--space-3xl) var(--space-xl);
		"
	>
		{#if !data.terms || data.terms.length === 0}
			<h2
				style="
					font-size: var(--font-size-heading);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					margin: 0 0 var(--space-sm) 0;
				"
			>
				No arguments published yet
			</h2>
			<p
				style="
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0;
					line-height: var(--line-height-body);
				"
			>
				Check back soon — new oral arguments are added regularly.
			</p>
		{:else}
			{#each data.terms as term (term.term_year)}
				<a
					href="/arguments/term/{term.term_year}"
					style="
						background-color: var(--color-surface);
						border: 1px solid var(--color-border);
						border-radius: 6px;
						padding: var(--space-lg);
						margin-bottom: var(--space-lg);
						display: block;
						text-decoration: none;
					"
				>
					<span
						style="
							font-size: var(--font-size-lead);
							font-weight: var(--font-weight-semibold);
							color: var(--color-text-primary);
							display: block;
							margin-bottom: var(--space-xs);
						"
					>
						October Term {term.term_year}
					</span>
					<span
						style="
							font-size: var(--font-size-caption);
							font-weight: var(--font-weight-regular);
							color: var(--color-text-secondary);
						"
					>
						{formatArgumentCount(term.argument_count)}
					</span>
				</a>
			{/each}
		{/if}
	</div>
</main>
