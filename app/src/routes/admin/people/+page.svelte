<script lang="ts">
	import { goto } from '$app/navigation';

	let { data } = $props();

	// IncompleteToggle state — mirrors the server-side incomplete flag (D-05).
	// Use a derived to keep it in sync when the load function re-runs after navigation.
	let checked = $derived(data.incomplete ?? false);

	function handleToggle() {
		if (checked) {
			goto('/admin/people');
		} else {
			goto('/admin/people?incomplete=1');
		}
	}

	// TenureGapsToggle state — mirrors the server-side tenure_gaps flag (D-15).
	let tenureGaps = $derived(data.tenure_gaps ?? false);

	function handleTenureGapsToggle() {
		if (tenureGaps) {
			goto('/admin/people');
		} else {
			goto('/admin/people?tenure_gaps=1');
		}
	}
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			People Directory
		</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">

		<!-- Filter toggles row -->
		<div style="display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
			<!-- IncompleteToggle (D-05) -->
			<div style="display: flex; align-items: center; gap: 8px;">
				<button
					role="switch"
					aria-checked={checked}
					aria-label="Show incomplete only"
					onclick={handleToggle}
					style="
						position: relative;
						width: 44px;
						height: 24px;
						border-radius: 12px;
						border: 1px solid {checked ? '#93c5fd' : '#334155'};
						background-color: {checked ? 'rgba(147,197,253,0.2)' : '#0f1117'};
						cursor: pointer;
						padding: 0;
						flex-shrink: 0;
					"
				>
					<span
						style="
							position: absolute;
							top: 50%;
							transform: translateY(-50%) translateX({checked ? '22px' : '2px'});
							width: 18px;
							height: 18px;
							border-radius: 50%;
							background-color: {checked ? '#93c5fd' : '#94a3b8'};
						"
					></span>
				</button>
				<span style="font-size: 14px; font-weight: 400; color: #94a3b8;">Show incomplete only</span>
			</div>

			<!-- TenureGapsToggle (D-15) -->
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

		<!-- PeopleTable (D-06) -->
		{#if data.people.length > 0}
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th
							scope="col"
							style="
								width: 40%;
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Name</th>
						<th
							scope="col"
							style="
								width: 25%;
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Role</th>
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
							>{person.full_name}</td>
							<td
								style="
									font-size: 16px;
									color: #94a3b8;
									border-bottom: 1px solid #334155;
									padding: 12px 0;
								"
							>{person.role_name ?? '—'}</td>
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
											<span
												style="
													display: inline-block;
													background-color: rgba(245,158,11,0.15);
													border: 1px solid #f59e0b;
													color: #f59e0b;
													border-radius: 4px;
													padding: 4px 8px;
													font-size: 14px;
													font-weight: 400;
													line-height: 1.4;
												"
											>{field}</span>
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
				{#if data.tenure_gaps}
					<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0;">
						No Justices with tenure gaps found.
					</p>
				{:else if data.incomplete}
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						No incomplete records
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						All people have complete metadata. Turn off the filter to see everyone.
					</p>
				{:else}
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						No people yet
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						People are added during pipeline resolve. Run a pipeline to populate this directory.
					</p>
				{/if}
			</div>
		{/if}

	</div>
</main>
