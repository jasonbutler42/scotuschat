<script lang="ts">
	import { enhance } from '$app/forms';

	let { data, form } = $props();

	// Passive trust-tier badge helpers — copied verbatim from
	// admin/arguments/+page.svelte (tierBadgeStyle/tierLabel) per this
	// plan's read_first instruction, so both pages render the tier badge
	// identically.
	function tierBadgeStyle(tier: string): string {
		let color: string;
		if (tier === 'verified') {
			color = '#38bdf8';
		} else if (tier === 'trusted') {
			color = '#34d399';
		} else if (tier === 'provisional') {
			color = '#facc15';
		} else if (tier === 'uncertain') {
			color = '#f87171';
		} else {
			color = '#64748b';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 400; background-color: #0f1117; color: ${color}; display: inline-block;`;
	}

	function tierLabel(tier: string): string {
		if (tier === 'verified') return 'Verified';
		if (tier === 'trusted') return 'Trusted';
		if (tier === 'provisional') return 'Provisional';
		if (tier === 'uncertain') return 'Uncertain';
		return tier;
	}

	function formatDate(iso: string | null): string {
		if (!iso) return '—';
		try {
			const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
			return new Date(y, m - 1, d).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
			});
		} catch {
			return iso;
		}
	}
</script>

<svelte:head>
	<title>Review — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">Review</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		{#if form?.error}
			<p role="alert" style="font-size: 14px; font-weight: 600; color: #ef4444; margin: 0 0 16px 0;">
				{form.error}
			</p>
		{/if}

		{#if data.items.length === 0}
			<div
				style="
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
					text-align: center;
				"
			>
				<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 4px 0;">
					All caught up
				</p>
				<p style="font-size: 16px; color: #94a3b8; margin: 0;">
					No arguments currently need review.
				</p>
			</div>
		{:else}
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th scope="col" style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px 12px; border-bottom: 1px solid #334155;">Tier</th>
						<th scope="col" style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px 12px; border-bottom: 1px solid #334155;">Case</th>
						<th scope="col" style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px 12px; border-bottom: 1px solid #334155;">Docket</th>
						<th scope="col" style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px 12px; border-bottom: 1px solid #334155;">Argued</th>
						<th scope="col" style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px 12px; border-bottom: 1px solid #334155;">Needs attention</th>
					</tr>
				</thead>
				<tbody>
					{#each data.items as item (item.id)}
						<tr>
							<td style="padding: 12px; border-bottom: 1px solid #334155; vertical-align: top;">
								<span style={tierBadgeStyle(item.trust_tier)}>{tierLabel(item.trust_tier)}</span>
							</td>
							<td style="padding: 12px; border-bottom: 1px solid #334155; vertical-align: top; color: #e2e8f0; font-size: 16px;">
								{item.case_name}
							</td>
							<td style="padding: 12px; border-bottom: 1px solid #334155; vertical-align: top; color: #94a3b8; font-size: 14px;">
								{item.docket_number}
							</td>
							<td style="padding: 12px; border-bottom: 1px solid #334155; vertical-align: top; color: #94a3b8; font-size: 14px;">
								{formatDate(item.argued_date)}
							</td>
							<td style="padding: 12px; border-bottom: 1px solid #334155; vertical-align: top;">
								{#if item.constituents.length === 0}
									<span style="color: #94a3b8; font-size: 14px;">
										{item.attention_count} constituent{item.attention_count === 1 ? '' : 's'} need review
									</span>
								{:else}
									{#each item.constituents as constituent (constituent.participant_id)}
										<div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
											<span style="color: #e2e8f0; font-size: 14px;">{constituent.display_name}</span>
											{#if constituent.person_id === null}
												<!--
													Unresolved speaker (person_id IS NULL) — Confirm cannot
													clear this leg (tracer feedback gate defect 2), so this
													links to the real person-search/assign flow instead of
													rendering a Confirm button.
												-->
												<a
													href={item.admin_job_id !== null
														? `/admin/pipeline/${item.admin_job_id}`
														: `/admin/arguments/${item.id}`}
													style="
														font-size: 14px;
														font-weight: 600;
														color: #93c5fd;
														text-decoration: none;
													"
												>Resolve speaker &rarr;</a>
											{:else if constituent.review_state === 'needs_review'}
												<form method="POST" action="?/confirm" use:enhance>
													<input type="hidden" name="participant_id" value={constituent.participant_id} />
													<button
														type="submit"
														style="
															min-height: 36px;
															padding: 4px 12px;
															font-size: 14px;
															font-weight: 600;
															cursor: pointer;
															border: 1px solid #93c5fd;
															background-color: transparent;
															color: #93c5fd;
															border-radius: 6px;
														"
													>Confirm</button>
												</form>
											{/if}
										</div>
									{/each}
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</main>
