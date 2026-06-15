<script lang="ts">
	let { data } = $props();

	/**
	 * Format an argued_date string (e.g. "2015-04-28") as "April 28, 2015".
	 * Uses Intl.DateTimeFormat per the UI-SPEC Copywriting Contract.
	 * The date comes from the API as a date string (YYYY-MM-DD).
	 * We append T00:00:00 to force local-date parsing and avoid UTC midnight
	 * roll-back on systems west of UTC.
	 */
	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return 'Date unknown';
		const date = new Date(dateStr + 'T00:00:00');
		return new Intl.DateTimeFormat('en-US', {
			month: 'long',
			day: 'numeric',
			year: 'numeric'
		}).format(date);
	}
</script>

<!-- Page background (#0f1117) -->
<main style="background-color: #0f1117; min-height: 100vh;">
	<!-- Header bar: full-width, #1e293b, border-bottom #334155 -->
	<header
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<!-- Page heading: "Cases" — 20px, weight 600, #e2e8f0 -->
		<h1
			style="
				font-size: 20px;
				font-weight: 600;
				color: #e2e8f0;
				margin: 0;
				line-height: 1.2;
			"
		>
			Cases
		</h1>
	</header>

	<!-- Content area: max-width 860px, centered, padding 48px 24px -->
	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: 48px 24px;
		"
	>
		{#if !data.cases || data.cases.length === 0}
			<!-- Empty state per UI-SPEC copywriting contract -->
			<h2
				style="
					font-size: 20px;
					font-weight: 600;
					color: #e2e8f0;
					margin: 0 0 12px 0;
				"
			>
				No cases loaded
			</h2>
			<p
				style="
					font-size: 16px;
					font-weight: 400;
					color: #94a3b8;
					margin: 0;
					line-height: 1.6;
				"
			>
				No arguments have been ingested yet. Run the ingest and parse pipeline steps to add cases.
			</p>
		{:else}
			<!-- Case list: each case as a card linking to /cases/{slug} -->
			{#each data.cases as c (c.id)}
				<a
					href="/cases/{c.slug}"
					style="
						background-color: #1e293b;
						border: 1px solid #334155;
						border-radius: 6px;
						padding: 16px;
						margin-bottom: 16px;
						display: block;
						text-decoration: none;
					"
				>
					<!-- Case name: 20px, weight 600, #e2e8f0 -->
					<span
						style="
							font-size: 20px;
							font-weight: 600;
							color: #e2e8f0;
							display: block;
							margin-bottom: 4px;
						"
					>
						{c.case_name}
					</span>
					<!-- Subline: docket + argued date — 14px, weight 400, #94a3b8 -->
					<span
						style="
							font-size: 14px;
							font-weight: 400;
							color: #94a3b8;
						"
					>
						No. {c.docket_number} · Argued {formatDate(c.argued_date)}
					</span>
				</a>
			{/each}
		{/if}
	</div>
</main>
