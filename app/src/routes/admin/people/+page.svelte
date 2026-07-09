<script lang="ts">
	import { goto } from '$app/navigation';

	let { data } = $props();

	// Bench/Advocate tabs (D-01, D-02, D-03) — one-param goto() round-trip, same
	// idiom as the removed incomplete/tenure_gaps toggles. Switching tabs clears
	// any active missing/tenure_gaps filter since both are tab-scoped concepts.
	function switchTab(tab: 'bench' | 'advocate') {
		goto('/admin/people?tab=' + tab);
	}

	// TenureGapsToggle (PDIR-06) — Bench tab only; preserves the tab param.
	let tenureGaps = $derived(data.tenure_gaps ?? false);
	function handleTenureGapsToggle() {
		if (tenureGaps) {
			goto('/admin/people?tab=' + data.tab);
		} else {
			goto('/admin/people?tab=' + data.tab + '&tenure_gaps=1');
		}
	}

	// Click-to-filter missing-field pills (D-04) — single-select, toggle behavior:
	// clicking the active pill again clears the filter.
	function togglePillFilter(field: string) {
		if (data.missing === field) {
			goto('/admin/people?tab=' + data.tab);
		} else {
			goto('/admin/people?tab=' + data.tab + '&missing=' + encodeURIComponent(field));
		}
	}

	function clearFilter() {
		goto('/admin/people?tab=' + data.tab);
	}
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<div
			style="
				max-width: 860px;
				margin: 0 auto;
				display: flex;
				align-items: center;
				justify-content: space-between;
				flex-wrap: wrap;
				gap: 16px;
			"
		>
			<div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
				<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">People</h1>

				<!-- Bench/Advocate segmented toggle (D-01, D-02, D-03) -->
				<div style="display: flex; gap: 0;">
					<button
						type="button"
						aria-pressed={data.tab === 'bench'}
						aria-label="Bench tab"
						onclick={() => switchTab('bench')}
						style="
							min-height: 44px;
							padding: 8px 16px;
							border: 1px solid {data.tab === 'bench' ? '#93c5fd' : '#334155'};
							border-radius: 6px 0 0 6px;
							background-color: {data.tab === 'bench' ? '#93c5fd' : '#1e293b'};
							color: {data.tab === 'bench' ? '#0f1117' : '#e2e8f0'};
							font-size: 16px;
							font-weight: 600;
							cursor: pointer;
						"
					>Bench</button>
					<button
						type="button"
						aria-pressed={data.tab === 'advocate'}
						aria-label="Advocate tab"
						onclick={() => switchTab('advocate')}
						style="
							min-height: 44px;
							padding: 8px 16px;
							border: 1px solid {data.tab === 'advocate' ? '#93c5fd' : '#334155'};
							border-left: none;
							border-radius: 0 6px 6px 0;
							background-color: {data.tab === 'advocate' ? '#93c5fd' : '#1e293b'};
							color: {data.tab === 'advocate' ? '#0f1117' : '#e2e8f0'};
							font-size: 16px;
							font-weight: 600;
							cursor: pointer;
						"
					>Advocate</button>
				</div>
			</div>

			<!-- Create person (PDIR-07) -->
			<a
				href="/admin/people/new"
				style="
					display: inline-flex;
					align-items: center;
					justify-content: center;
					min-height: 44px;
					padding: 8px 16px;
					background: transparent;
					border: 1px solid #93c5fd;
					border-radius: 6px;
					font-size: 16px;
					font-weight: 600;
					color: #e2e8f0;
					text-decoration: none;
					box-sizing: border-box;
				"
			>Create person</a>
		</div>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">

		<!-- TenureGapsToggle (PDIR-06) — Bench tab only -->
		{#if data.tab === 'bench'}
			<div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
				<div style="display: flex; align-items: center; gap: 8px;">
					<button
						role="switch"
						aria-checked={tenureGaps}
						aria-label="Justices with tenure gaps"
						onclick={handleTenureGapsToggle}
						style="
							position: relative;
							width: 44px;
							height: 24px;
							border-radius: 12px;
							border: 1px solid {tenureGaps ? '#93c5fd' : '#334155'};
							background-color: {tenureGaps ? 'rgba(147,197,253,0.2)' : '#0f1117'};
							cursor: pointer;
							padding: 0;
							flex-shrink: 0;
						"
					>
						<span
							style="
								position: absolute;
								top: 50%;
								transform: translateY(-50%) translateX({tenureGaps ? '22px' : '2px'});
								width: 18px;
								height: 18px;
								border-radius: 50%;
								background-color: {tenureGaps ? '#93c5fd' : '#94a3b8'};
							"
						></span>
					</button>
					<span style="font-size: 14px; font-weight: 400; color: #94a3b8;">Justices with tenure gaps</span>
				</div>
			</div>
		{/if}

		<!-- Filtering by / Clear filter (UI-SPEC Interaction Contract) -->
		{#if data.missing || tenureGaps}
			<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
				Filtering by: {data.missing ?? 'Justices with tenure gaps'} ·
				<button
					type="button"
					onclick={clearFilter}
					aria-label="Clear missing-field filter"
					style="
						background: none;
						border: none;
						padding: 0;
						margin: 0;
						color: #93c5fd;
						text-decoration: underline;
						font-size: 14px;
						font-weight: 400;
						cursor: pointer;
					"
				>Clear filter</button>
			</p>
		{/if}

		<!-- PeopleTable (per-tab columns, PDIR-03/PDIR-04) -->
		{#if data.people.length > 0}
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th
							scope="col"
							style="
								width: {data.tab === 'bench' ? '30%' : '40%'};
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Name</th>
						{#if data.tab === 'bench'}
							<th
								scope="col"
								style="
									width: 20%;
									text-align: left;
									font-size: 14px;
									font-weight: 400;
									color: #94a3b8;
									border-bottom: 1px solid #334155;
									padding: 8px 0;
								"
							>Tenure coverage</th>
							<th
								scope="col"
								style="
									width: 15%;
									text-align: left;
									font-size: 14px;
									font-weight: 400;
									color: #94a3b8;
									border-bottom: 1px solid #334155;
									padding: 8px 0;
								"
							>Tenure gap</th>
						{:else}
							<th
								scope="col"
								style="
									width: 20%;
									text-align: right;
									font-size: 14px;
									font-weight: 400;
									color: #94a3b8;
									border-bottom: 1px solid #334155;
									padding: 8px 0;
								"
							>Argument count</th>
						{/if}
						<th
							scope="col"
							style="
								width: {data.tab === 'bench' ? '20%' : '25%'};
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Missing fields</th>
						<th
							scope="col"
							style="
								width: 15%;
								text-align: right;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						></th>
					</tr>
				</thead>
				<tbody>
					{#each data.people as person}
						<tr>
							<td
								style="
									font-size: 16px;
									color: #e2e8f0;
									border-bottom: 1px solid #334155;
									padding: 12px 0;
								"
							>{person.full_name}{#if person.is_justice}<span style="display: inline-block; background-color: rgba(147,197,253,0.15); border: 1px solid #93c5fd; color: #93c5fd; border-radius: 4px; padding: 2px 6px; font-size: 14px; font-weight: 400; line-height: 1.4; margin-left: 8px;">Justice</span>{/if}</td>
							{#if data.tab === 'bench'}
								<td
									style="
										font-size: 16px;
										color: {person.tenure_coverage ? '#e2e8f0' : '#94a3b8'};
										border-bottom: 1px solid #334155;
										padding: 12px 0;
									"
								>{person.tenure_coverage ?? 'No tenure'}</td>
								<td
									style="
										font-size: 16px;
										color: {person.has_tenure_gap ? '#fbbf24' : '#94a3b8'};
										border-bottom: 1px solid #334155;
										padding: 12px 0;
									"
								>{person.has_tenure_gap ? '⚠ Gap' : '—'}</td>
							{:else}
								<td
									style="
										font-size: 16px;
										color: #94a3b8;
										text-align: right;
										border-bottom: 1px solid #334155;
										padding: 12px 0;
									"
								>{person.argument_count ?? 0}</td>
							{/if}
							<td
								style="
									font-size: 16px;
									border-bottom: 1px solid #334155;
									padding: 12px 0;
								"
							>
								{#if person.missing.length > 0}
									<!-- MissingFieldChip group — aria-label summarises all chips for screen readers -->
									<span
										aria-label="Missing: {person.missing.join(', ')}"
										style="display: flex; gap: 4px; flex-wrap: wrap;"
									>
										{#each person.missing as field}
											<button
												type="button"
												class="pill"
												class:pill-active={data.missing === field}
												aria-pressed={data.missing === field}
												aria-label="Filter by {field}"
												onclick={() => togglePillFilter(field)}
											>{field}</button>
										{/each}
									</span>
								{/if}
							</td>
							<td
								style="
									font-size: 14px;
									text-align: right;
									border-bottom: 1px solid #334155;
									padding: 12px 0;
								"
							>
								<a
									href={'/admin/people/' + person.id}
									style="color: #93c5fd; text-decoration: underline;"
								>Edit person</a>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<!-- Empty states (UI-SPEC Copywriting Contract) -->
			<div
				style="
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
					text-align: center;
				"
			>
				{#if tenureGaps}
					<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0;">
						No Justices with tenure gaps found.
					</p>
				{:else if data.missing}
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						No matches for this filter.
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						Clear the filter to see everyone on this tab.
					</p>
				{:else if data.tab === 'bench'}
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						No Justices yet.
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						Justices are added automatically during pipeline resolve, or you can create one directly.
					</p>
				{:else}
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						No advocates yet.
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						Advocates are added automatically during pipeline resolve, or you can create one directly.
					</p>
				{/if}
			</div>
		{/if}

	</div>
</main>

<style>
	.pill {
		display: inline-flex;
		align-items: center;
		min-height: 36px;
		background-color: rgba(245, 158, 11, 0.15);
		border: 1px solid #f59e0b;
		color: #f59e0b;
		border-radius: 4px;
		padding: 4px 8px;
		font-size: 14px;
		font-weight: 400;
		line-height: 1.4;
		cursor: pointer;
	}
	.pill:hover,
	.pill:focus-visible {
		box-shadow: 0 0 0 1px #f59e0b inset;
	}
	.pill-active {
		background-color: #f59e0b;
		color: #0f1117;
		font-weight: 600;
	}
</style>
