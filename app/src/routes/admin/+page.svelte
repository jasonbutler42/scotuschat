<script lang="ts">
	import StatCard from '$lib/components/StatCard.svelte';

	let { data } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Types (mirror +page.server.ts's return shape)
	// ──────────────────────────────────────────────────────────────────────────

	interface RecentDraft {
		id: number;
		case_name: string;
		docket_number: string;
	}

	interface IncompletePerson {
		id: number;
		full_name: string;
		missing: string[];
	}

	interface TenureGapJustice {
		id: number;
		full_name: string;
	}

	// N/A convention (UI-SPEC "Load-failure state"): a null stat value means the
	// fetch failed, distinct from a genuine 0. Never render a bare 0 for a failed
	// fetch, and never use an em-dash placeholder character.
	function formatCount(n: number | null): string {
		return n === null ? 'N/A' : String(n);
	}

	function formatDate(iso: string | null): string {
		if (!iso) return 'N/A';
		const d = new Date(iso);
		if (Number.isNaN(d.getTime())) return 'N/A';
		return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	function missingFieldsLabel(missing: string[]): string {
		const count = missing.length;
		return `${count} missing field${count === 1 ? '' : 's'}`;
	}

	// Whole-section empty state (UI-SPEC): renders only when all three
	// Needs Attention sub-lists are empty.
	const allCaughtUp = $derived(
		data.incompletePeople.length === 0 &&
			data.tenureGapJustices.length === 0 &&
			data.draftsList.length === 0,
	);
</script>

<svelte:head>
	<title>Admin — SCOTUS Chat</title>
</svelte:head>

<!-- Page background (#0f1117) — matches existing page pattern -->
<main style="background-color: #0f1117; min-height: 100vh;">
	<!-- Header bar: #1e293b bg, border-bottom #334155 -->
	<header
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<h1
			style="
				font-size: 20px;
				font-weight: 600;
				color: #e2e8f0;
				margin: 0;
				line-height: 1.2;
			"
		>
			Admin
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
		<!-- ═══════════════════════════════════════════════════════════════════
		     NEEDS ATTENTION (D-09: renders first, above the stat-card grid)
		     ═══════════════════════════════════════════════════════════════════ -->
		<section
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">
				Needs Attention
			</h2>

			{#if allCaughtUp}
				<div>
					<p style="font-size: 16px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						All caught up
					</p>
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						Nothing needs your attention right now.
					</p>
				</div>
			{:else}
				<!-- People sub-list (combined bench+advocate, D-05 amendment) -->
				<div style="margin-bottom: 16px;">
					<h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						People
					</h3>
					{#if data.incompletePeople.length === 0}
						<p style="font-size: 14px; color: #94a3b8; margin: 0;">
							No people currently have missing fields.
						</p>
					{:else}
						{#each data.incompletePeople as person (person.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 8px 0;">
								<span style="font-size: 16px; color: #e2e8f0;">{person.full_name}</span>
								<span style="font-size: 14px; color: #94a3b8;">{missingFieldsLabel(person.missing)}</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/people"
						style="
							display: inline-flex;
							align-items: center;
							min-height: 44px;
							font-size: 14px;
							color: #93c5fd;
							text-decoration: none;
						"
					>
						View all →
					</a>
				</div>

				<!-- Justices sub-list (bench-only tenure gaps, D-06) -->
				<div style="margin-bottom: 16px;">
					<h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						Justices
					</h3>
					{#if data.tenureGapJustices.length === 0}
						<p style="font-size: 14px; color: #94a3b8; margin: 0;">
							No tenure gaps found.
						</p>
					{:else}
						{#each data.tenureGapJustices as justice (justice.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 8px 0;">
								<span style="font-size: 16px; color: #e2e8f0;">{justice.full_name}</span>
								<span style="font-size: 14px; color: #fbbf24;">Missing tenure</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/people?tab=bench&tenure_gaps=1"
						style="
							display: inline-flex;
							align-items: center;
							min-height: 44px;
							font-size: 14px;
							color: #93c5fd;
							text-decoration: none;
						"
					>
						View all →
					</a>
				</div>

				<!-- Drafts sub-list (all drafts, no age threshold, D-03) -->
				<div>
					<h3 style="font-size: 14px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
						Drafts
					</h3>
					{#if data.draftsList.length === 0}
						<p style="font-size: 14px; color: #94a3b8; margin: 0;">
							No draft arguments.
						</p>
					{:else}
						{#each data.draftsList as draft (draft.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 8px 0;">
								<span style="font-size: 16px; color: #e2e8f0;">{draft.case_name}</span>
								<span style="font-size: 14px; color: #94a3b8;">{draft.docket_number}</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/arguments?status=draft"
						style="
							display: inline-flex;
							align-items: center;
							min-height: 44px;
							font-size: 14px;
							color: #93c5fd;
							text-decoration: none;
						"
					>
						View all →
					</a>
				</div>
			{/if}
		</section>

		<!-- ═══════════════════════════════════════════════════════════════════
		     STAT-CARD GRID (Arguments / People / Utterances / Pipeline runs)
		     ═══════════════════════════════════════════════════════════════════ -->
		<div
			style="
				display: grid;
				grid-template-columns: repeat(4, 1fr);
				gap: 32px;
				margin-top: 32px;
			"
		>
			<StatCard title="Arguments">
				{#snippet children()}
					<p style="font-size: 32px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
						{formatCount(data.argumentStats.total)}
					</p>
					<div style="display: flex; flex-direction: column; gap: 8px;">
						<a
							href="/admin/arguments?status=published"
							style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #4ade80; text-decoration: none;"
						>
							{formatCount(data.argumentStats.published)} Published
						</a>
						<a
							href="/admin/arguments?status=draft"
							style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #a78bfa; text-decoration: none;"
						>
							{formatCount(data.argumentStats.draft)} Draft
						</a>
						<a
							href="/admin/arguments?status=unpublished"
							style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #fb923c; text-decoration: none;"
						>
							{formatCount(data.argumentStats.unpublished)} Unpublished
						</a>
					</div>
				{/snippet}
			</StatCard>

			<StatCard title="People">
				{#snippet children()}
					<p style="font-size: 32px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
						{formatCount(data.peopleStats.total)}
					</p>
					<a
						href="/admin/people"
						style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #93c5fd; text-decoration: none;"
					>
						{formatCount(data.peopleStats.incomplete)} missing fields → Review
					</a>
				{/snippet}
			</StatCard>

			<StatCard title="Utterances">
				{#snippet children()}
					<p style="font-size: 32px; font-weight: 600; color: #e2e8f0; margin: 0; line-height: 1.2;">
						{formatCount(data.utteranceCount.total)}
					</p>
				{/snippet}
			</StatCard>

			<StatCard title="Pipeline runs">
				{#snippet children()}
					<p style="font-size: 32px; font-weight: 600; color: #e2e8f0; margin: 0 0 4px 0; line-height: 1.2;">
						{formatCount(data.pipelineStats.recent_count)}
						<span style="font-size: 14px; font-weight: 400; color: #94a3b8;">(last 30 days)</span>
					</p>
					<p style="font-size: 14px; color: #94a3b8; margin: 0 0 16px 0;">
						Last activity: {formatDate(data.pipelineStats.last_activity_at)}
					</p>
					<a
						href="/admin/pipeline"
						style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #93c5fd; text-decoration: none;"
					>
						View all runs →
					</a>
				{/snippet}
			</StatCard>
		</div>

		<!-- ═══════════════════════════════════════════════════════════════════
		     WEB TRAFFIC placeholder (DASH-04, D-11, D-12) — own row, never
		     mixed into the 4-card grid above.
		     ═══════════════════════════════════════════════════════════════════ -->
		<div
			style="
				border: 1px dashed #334155;
				border-radius: 8px;
				padding: 24px;
				margin-top: 48px;
				opacity: 0.7;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
				Web Traffic
			</h2>
			<p style="font-size: 14px; color: #94a3b8; margin: 0;">Coming soon</p>
		</div>
	</div>
</main>
