<script lang="ts">
	import { enhance } from '$app/forms';

	let { data } = $props();

	// Format ISO date string for display — matches pipeline/+page.svelte formatDate pattern.
	function formatDate(iso: string): string {
		try {
			const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
			return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return iso;
		}
	}

	// StatusBadge helpers — reads argument.status enum (Phase 15: draft/published).
	// Pipeline-state arguments are excluded from this list (D-02).
	function badgeStyle(status: string): string {
		let color: string;
		if (status === 'published') {
			color = '#4ade80'; // Published — green
		} else if (status === 'draft') {
			color = '#a78bfa'; // Draft — violet
		} else if (status === 'unpublished') {
			color = '#fb923c'; // Unpublished — orange
		} else {
			color = '#94a3b8'; // Pipeline — muted (fallback, should not appear in this list)
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
	}

	function badgeLabel(status: string): string {
		if (status === 'published') return 'Published';
		if (status === 'draft') return 'Draft';
		if (status === 'unpublished') return 'Unpublished';
		return 'Pipeline';
	}
</script>

<svelte:head>
	<title>Arguments — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">Arguments</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		{#if data.arguments.length === 0}
			<!-- Empty state per UI-SPEC Copywriting Contract -->
			<div
				style="
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
					text-align: center;
				"
			>
				<p style="font-size: 16px; color: #94a3b8; margin: 0;">
					No arguments yet. Start a pipeline run to ingest a transcript.
				</p>
			</div>
		{:else}
			<!-- ArgumentsTable — WCAG 1.3.1: th scope=col for all column headers -->
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th
							scope="col"
							style="
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Status</th>
						<th
							scope="col"
							style="
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 8px;
							"
						>Case Title</th>
						<th
							scope="col"
							style="
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 8px;
							"
						>Docket</th>
						<th
							scope="col"
							style="
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 8px;
							"
						>Argued</th>
						<th
							scope="col"
							style="
								text-align: left;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 8px;
							"
						>Created</th>
						<th
							scope="col"
							style="
								text-align: right;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								border-bottom: 1px solid #334155;
								padding: 8px 0;
							"
						>Publish</th>
					</tr>
				</thead>
				<tbody>
					{#each data.arguments as arg}
						<tr>
							<td
								style="
									padding: 12px 0;
									border-bottom: 1px solid #334155;
									white-space: nowrap;
								"
							>
								<span style={badgeStyle(arg.status ?? 'pipeline')}>
									{badgeLabel(arg.status ?? 'pipeline')}
								</span>
							</td>
							<td
								style="
									font-size: 14px;
									color: #94a3b8;
									padding: 12px 8px;
									border-bottom: 1px solid #334155;
								"
							>{arg.case_name}</td>
							<td
								style="
									font-size: 14px;
									color: #94a3b8;
									padding: 12px 8px;
									border-bottom: 1px solid #334155;
									white-space: nowrap;
								"
							>{arg.docket_number}</td>
							<td
								style="
									font-size: 14px;
									color: #94a3b8;
									padding: 12px 8px;
									border-bottom: 1px solid #334155;
									white-space: nowrap;
								"
							>{arg.argued_date ? formatDate(arg.argued_date) : '—'}</td>
							<td
								style="
									font-size: 14px;
									color: #94a3b8;
									padding: 12px 8px;
									border-bottom: 1px solid #334155;
									white-space: nowrap;
								"
							>{arg.resolved_at ? formatDate(arg.resolved_at) : '—'}</td>
							<td
								style="
									padding: 12px 0;
									border-bottom: 1px solid #334155;
									text-align: right;
								"
							>
								<div style="display: flex; gap: 8px; justify-content: flex-end; align-items: center;">
									{#if arg.status === 'draft' || arg.status === 'unpublished'}
										<!-- Publish toggle — Draft or Unpublished both go to Published -->
										<form method="POST" action="?/publish" use:enhance>
											<input type="hidden" name="argument_id" value={arg.id} />
											<button
												type="submit"
												style="
													min-height: 44px;
													font-size: 14px;
													font-weight: 400;
													color: #93c5fd;
													background: transparent;
													border: 1px solid #93c5fd;
													border-radius: 6px;
													padding: 8px 12px;
													cursor: pointer;
												"
											>Publish</button>
										</form>
									{:else if arg.status === 'published'}
										<!-- Unpublish toggle — only when already published -->
										<form method="POST" action="?/unpublish" use:enhance>
											<input type="hidden" name="argument_id" value={arg.id} />
											<button
												type="submit"
												style="
													min-height: 44px;
													font-size: 14px;
													font-weight: 400;
													color: #94a3b8;
													background: transparent;
													border: 1px solid #334155;
													border-radius: 6px;
													padding: 8px 12px;
													cursor: pointer;
												"
											>Unpublish</button>
										</form>
									{/if}
									<!-- Edit link per row -->
									<a
										href={'/admin/arguments/' + arg.id}
										style="font-size: 14px; color: #93c5fd; text-decoration: underline;"
									>Edit</a>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
</main>
