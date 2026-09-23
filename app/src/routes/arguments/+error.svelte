<script lang="ts">
	// Shared error boundary for the /arguments subtree (Phase 51 plan 51-08).
	// Rule 2 addition: the plan's Copywriting Contract requires the generic
	// listing error copy to render with no HTTP status number and no error
	// detail reaching a public reader (T-51-08-01) — SvelteKit's built-in
	// fallback error page renders the raw status code in its heading, which
	// would violate that contract, so a route-tree +error.svelte is required
	// to intercept it. A genuine 404 (unknown slug, bad/out-of-range term
	// year) still renders as a 404 — only the status *code* is preserved,
	// never the upstream detail string a non-404 error carries.
	import { page } from '$app/state';
</script>

<main
	style="
		background-color: var(--color-bg);
		min-height: 100vh;
		display: flex;
		align-items: center;
		justify-content: center;
	"
>
	<div
		style="
			max-width: 480px;
			margin: 0 auto;
			padding: var(--space-3xl) var(--space-xl);
			text-align: center;
		"
	>
		{#if page.status === 404}
			<h1
				style="
					font-size: var(--font-size-heading);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					margin: 0 0 var(--space-sm) 0;
				"
			>
				Not found
			</h1>
			<p
				style="
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0;
					line-height: var(--line-height-body);
				"
			>
				This page does not exist.
			</p>
		{:else}
			<p
				style="
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0;
					line-height: var(--line-height-body);
				"
			>
				Unable to load arguments right now. Try refreshing the page.
			</p>
		{/if}
	</div>
</main>
