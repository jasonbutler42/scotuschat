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

<!-- Page background (#0f1117) — only rendered for multi-argument cases; single-argument cases redirect in server load -->
<div style="background-color: #0f1117; min-height: 100vh;">
	<!-- Header bar: full-width, #1e293b, border-bottom #334155 -->
	<div
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<!-- Heading: "Arguments for {caseName}" — 20px, weight 600, #e2e8f0 -->
		<h1
			style="
				font-size: 20px;
				font-weight: 600;
				color: #e2e8f0;
				margin: 0;
				line-height: 1.2;
			"
		>
			Arguments for {data.caseName}
		</h1>
	</div>

	<!-- Content area: max-width 860px, centered, padding 48px 24px -->
	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: 48px 24px;
		"
	>
		<!-- Argument picker: each argument as a card linking to its argument view -->
		{#each data.arguments as arg (arg.argument_id)}
			<a
				href="/cases/{data.slug}/arguments/{arg.argument_id}"
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
				<!-- "Question {n} — Argued {date}" — 16px, weight 400, #e2e8f0 -->
				<span
					style="
						font-size: 16px;
						font-weight: 400;
						color: #e2e8f0;
					"
				>
					Question {arg.question_number} — Argued {formatDate(arg.argued_date)}
				</span>
			</a>
		{/each}
	</div>
</div>
