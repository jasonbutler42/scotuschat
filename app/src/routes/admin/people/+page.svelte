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

	// Phase 38 (D-12, D-13): "Name review" reuses the exact same click-to-filter
	// pill/indicator mechanism as every other missing-field pill above — the
	// underlying filter value stays the lowercase "name review" vocabulary
	// admin_people.py's missing_filters allow-list expects (togglePillFilter,
	// data.missing comparisons), but the visible/accessible text is the
	// locked Title Case copy from 38-UI-SPEC.md's copywriting contract. No
	// new UI surface (dashboard queue, job re-execution control) is introduced — this is
	// strictly additive to the existing People-directory attention pattern.
	function pillLabel(field: string): string {
		return field === 'name review' ? 'Name review' : field;
	}
</script>

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header
		style="background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: var(--space-lg) var(--space-xl);"
	>
		<div
			style="
				max-width: 860px;
				margin: 0 auto;
				display: flex;
				align-items: center;
				justify-content: space-between;
				flex-wrap: wrap;
				gap: var(--space-lg);
			"
		>
			<div style="display: flex; align-items: center; gap: var(--space-lg); flex-wrap: wrap;">
				<h1 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0;">People</h1>

				<!-- Bench/Advocate segmented toggle (D-01, D-02, D-03) -->
				<div style="display: flex; gap: 0;">
					<button
						type="button"
						aria-pressed={data.tab === 'bench'}
						aria-label="Bench tab"
						onclick={() => switchTab('bench')}
						style="
							min-height: var(--touch-target);
							padding: var(--space-sm) var(--space-lg);
							border: 1px solid {data.tab === 'bench' ? 'var(--color-accent)' : 'var(--color-border)'};
							border-radius: 6px 0 0 6px;
							background-color: {data.tab === 'bench' ? 'var(--color-accent)' : 'var(--color-surface)'};
							color: {data.tab === 'bench' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-semibold);
							cursor: pointer;
						"
					>Bench</button>
					<button
						type="button"
						aria-pressed={data.tab === 'advocate'}
						aria-label="Advocate tab"
						onclick={() => switchTab('advocate')}
						style="
							min-height: var(--touch-target);
							padding: var(--space-sm) var(--space-lg);
							border: 1px solid {data.tab === 'advocate' ? 'var(--color-accent)' : 'var(--color-border)'};
							border-left: none;
							border-radius: 0 6px 6px 0;
							background-color: {data.tab === 'advocate' ? 'var(--color-accent)' : 'var(--color-surface)'};
							color: {data.tab === 'advocate' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-semibold);
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
					min-height: var(--touch-target);
					padding: var(--space-sm) var(--space-lg);
					background: transparent;
					border: 1px solid var(--color-accent);
					border-radius: 6px;
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					text-decoration: none;
					box-sizing: border-box;
				"
			>Create person</a>
		</div>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: var(--space-3xl) var(--space-xl);">

		<!-- TenureGapsToggle (PDIR-06) — Bench tab only -->
		{#if data.tab === 'bench'}
			<div style="display: flex; flex-wrap: wrap; gap: var(--space-lg); margin-bottom: var(--space-lg);">
				<div style="display: flex; align-items: center; gap: var(--space-sm);">
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
							border: 1px solid {tenureGaps ? 'var(--color-accent)' : 'var(--color-border)'};
							background-color: {tenureGaps ? 'rgba(147,197,253,0.2)' : 'var(--color-bg)'};
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
								background-color: {tenureGaps ? 'var(--color-accent)' : 'var(--color-text-secondary)'};
							"
						></span>
					</button>
					<span style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary);">Justices with tenure gaps</span>
				</div>
			</div>
		{/if}

		<!-- Filtering by / Clear filter (UI-SPEC Interaction Contract) -->
		{#if data.missing || tenureGaps}
			<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-lg) 0;">
				Filtering by: {data.missing ? pillLabel(data.missing) : 'Justices with tenure gaps'} ·
				<button
					type="button"
					onclick={clearFilter}
					aria-label="Clear missing-field filter"
					style="
						background: none;
						border: none;
						padding: 0;
						margin: 0;
						color: var(--color-accent);
						text-decoration: underline;
						font-size: var(--font-size-caption);
						font-weight: var(--font-weight-regular);
						cursor: pointer;
					"
				>Clear filter</button>
			</p>
		{/if}

		<!-- PeopleTable (per-tab columns, PDIR-03/PDIR-04) -->
		{#if data.people.length > 0}
			<!-- G-49-18 (operator, 2026-08-25, 49-UAT test 49): this list table was one of the
			     two admin tables 49-12 measured overflowing at 375px and deliberately scoped out
			     (/admin/people reached 403px at a 375px viewport). Left unwrapped it pushes the PAGE into
			     horizontal scroll rather than scrolling itself, breaking 49-UI-SPEC's
			     no-horizontal-scroll must_have. Same remedy as 49-08's review-queue tables and
			     G-49-17's Speakers table: the table scrolls inside its own container. No column
			     is truncated and no media query is introduced (49-UI-SPEC E1/E2). -->
			<div style="overflow-x: auto;">
				<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th
							scope="col"
							style="
								width: {data.tab === 'bench' ? '30%' : '40%'};
								text-align: left;
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
								border-bottom: 1px solid var(--color-border);
								padding: var(--space-sm) 0;
							"
						>Name</th>
						{#if data.tab === 'bench'}
							<th
								scope="col"
								style="
									width: 20%;
									text-align: left;
									font-size: var(--font-size-caption);
									font-weight: var(--font-weight-regular);
									color: var(--color-text-secondary);
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-sm) var(--space-sm);
								"
							>Tenure coverage</th>
							<th
								scope="col"
								style="
									width: 15%;
									text-align: left;
									font-size: var(--font-size-caption);
									font-weight: var(--font-weight-regular);
									color: var(--color-text-secondary);
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-sm) var(--space-sm);
								"
							>Tenure gap</th>
						{:else}
							<th
								scope="col"
								style="
									width: 20%;
									text-align: right;
									font-size: var(--font-size-caption);
									font-weight: var(--font-weight-regular);
									color: var(--color-text-secondary);
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-sm) var(--space-sm);
								"
							>Argument count</th>
						{/if}
						<th
							scope="col"
							style="
								width: {data.tab === 'bench' ? '20%' : '25%'};
								text-align: left;
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
								border-bottom: 1px solid var(--color-border);
								padding: var(--space-sm) var(--space-sm);
							"
						>Missing fields</th>
						<th
							scope="col"
							style="
								width: 15%;
								text-align: right;
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
								border-bottom: 1px solid var(--color-border);
								padding: var(--space-sm) 0;
							"
						></th>
					</tr>
				</thead>
				<tbody>
					{#each data.people as person}
						<tr>
							<td
								style="
									font-size: var(--font-size-body);
									color: var(--color-text-primary);
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-md) 0;
								"
							>{person.full_name}{#if person.is_justice}<span style="display: inline-block; background-color: rgba(147,197,253,0.15); border: 1px solid var(--color-accent); color: var(--color-accent); border-radius: 4px; padding: var(--space-xs) var(--space-xs); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); line-height: 1.4; margin-left: var(--space-sm);">Justice</span>{/if}</td>
							{#if data.tab === 'bench'}
								<td
									style="
										font-size: var(--font-size-body);
										color: {person.tenure_coverage ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
										border-bottom: 1px solid var(--color-border);
										padding: var(--space-md) var(--space-sm);
									"
								>{person.tenure_coverage ?? 'No tenure'}</td>
								<td
									style="
										font-size: var(--font-size-body);
										color: {person.has_tenure_gap ? 'var(--color-status-warning)' : 'var(--color-text-secondary)'};
										border-bottom: 1px solid var(--color-border);
										padding: var(--space-md) var(--space-sm);
									"
								>{person.has_tenure_gap ? '⚠ Gap' : '—'}</td>
							{:else}
								<td
									style="
										font-size: var(--font-size-body);
										color: var(--color-text-secondary);
										text-align: right;
										border-bottom: 1px solid var(--color-border);
										padding: var(--space-md) var(--space-sm);
									"
								>{person.argument_count ?? 0}</td>
							{/if}
							<td
								style="
									font-size: var(--font-size-body);
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-md) var(--space-sm);
								"
							>
								{#if person.missing.length > 0}
									<!-- MissingFieldChip group — aria-label summarises all chips for screen readers.
									     "name review" (Phase 38, D-12) reuses this exact mechanism; only its
									     display/accessible text is the locked Title Case "Name review" copy. -->
									<span
										aria-label="Missing: {person.missing.map(pillLabel).join(', ')}"
										style="display: flex; gap: var(--space-xs); flex-wrap: wrap;"
									>
										{#each person.missing as field}
											<button
												type="button"
												class="pill"
												class:pill-active={data.missing === field}
												aria-pressed={data.missing === field}
												aria-label="Filter by {pillLabel(field)}"
												onclick={() => togglePillFilter(field)}
											>{pillLabel(field)}</button>
										{/each}
									</span>
								{/if}
							</td>
							<td
								style="
									font-size: var(--font-size-caption);
									text-align: right;
									border-bottom: 1px solid var(--color-border);
									padding: var(--space-md) 0;
								"
							>
								<a
									href={'/admin/people/' + person.id}
									style="color: var(--color-accent); text-decoration: underline;"
								>Edit person</a>
							</td>
						</tr>
					{/each}
				</tbody>
				</table>
			</div>
		{:else}
			<!-- Empty states (UI-SPEC Copywriting Contract) -->
			<div
				style="
					background-color: var(--color-surface);
					border: 1px solid var(--color-border);
					border-radius: 8px;
					padding: var(--space-xl);
					text-align: center;
				"
			>
				{#if tenureGaps}
					<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0;">
						No Justices with tenure gaps found.
					</p>
				{:else if data.missing === 'name review'}
					<!-- Phase 38 (D-12, D-13) — exact locked UI-SPEC empty-state copy for
					     the Name review filter, distinct from the generic missing-field
					     empty state below. -->
					<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						No people need name review
					</p>
					<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
						Ambiguous legacy names will appear here for review.
					</p>
				{:else if data.missing}
					<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						No matches for this filter.
					</p>
					<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
						Clear the filter to see everyone on this tab.
					</p>
				{:else if data.tab === 'bench'}
					<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						No Justices yet.
					</p>
					<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
						Justices are added automatically during pipeline resolve, or you can create one directly.
					</p>
				{:else}
					<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						No advocates yet.
					</p>
					<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
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
		min-height: var(--touch-target-dense);
		background-color: color-mix(in srgb, var(--color-status-warning) 15%, transparent);
		border: 1px solid var(--color-status-warning);
		color: var(--color-status-warning);
		border-radius: 4px;
		padding: var(--space-xs) var(--space-sm);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-regular);
		line-height: 1.4;
		cursor: pointer;
	}
	.pill:hover,
	.pill:focus-visible {
		box-shadow: 0 0 0 1px var(--color-status-warning) inset;
	}
	.pill-active {
		background-color: var(--color-status-warning);
		color: var(--color-bg);
		font-weight: var(--font-weight-semibold);
	}
</style>
