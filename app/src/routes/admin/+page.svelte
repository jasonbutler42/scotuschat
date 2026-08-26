<script lang="ts">
	import StatCard from '$lib/components/StatCard.svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';

	let { data, form } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Types (mirror +page.server.ts's return shape)
	// ──────────────────────────────────────────────────────────────────────────

	interface ResetFixtureItem {
		conversation_id: string;
		case_name: string;
		role: string;
		argument_id: number;
		argument_status: string;
		// Phase 50 (D-14/D-19, PD-05) — mirrors api/schemas/admin_dev.py's
		// ResetFixtureItem.latest_import_run_step; there is no AdminJob for a
		// corpus fixture anymore.
		latest_import_run_step: string;
	}

	// Phase 49 (D-33a) — mirrors api/schemas/admin_dev.py::SeedUnresolvedSpeakerResponse.
	interface SeedUnresolvedSpeakerResult {
		argument_id: number;
		participant_id: number;
		raw_speaker_label: string;
		trust_tier: string;
		already_seeded: boolean;
	}

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

	// ──────────────────────────────────────────────────────────────────────────
	// Dev-tools "Reset to Fixture" control (Phase 43, D-05/D-06). Five states
	// driving one control: Idle -> Confirming -> Running -> Success | Error.
	// Mirrors the deleteConfirming/deleteSubmitting convention from the
	// arguments detail page's Danger Zone section.
	// ──────────────────────────────────────────────────────────────────────────
	let resetConfirming = $state(false);
	let resetRunning = $state(false);
	let resetResult = $state<ResetFixtureItem[] | null>(null);

	// ──────────────────────────────────────────────────────────────────────────
	// Dev-tools unresolved-speaker seeder control (Phase 49, D-33a). Single-step —
	// no confirm gate, since this is additive and single-row, not destructive.
	// ──────────────────────────────────────────────────────────────────────────
	let seedSubmitting = $state(false);
	let seedResult = $state<SeedUnresolvedSpeakerResult | null>(null);
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
		     STAT-CARD GRID (Arguments / People / Utterances / Pipeline runs /
		     Review queue) — Phase 49 (D-30) widens this from 4 to 5 columns;
		     the UI-SPEC's claim that the existing grid "absorbs the fifth
		     card without change" is contradicted by the four-column literal
		     this grid used to declare — source wins (RESEARCH Pitfall 3).

		     49-08 (G-49-5a): the fixed five-column form overflowed the page
		     body at a 375px viewport (UAT sub-item 7), while UAT sub-item 5
		     required all five cards to stay in one row at desktop width — a
		     conflict that exists only under a FIXED column count. The content
		     region is max-width: 860px with 24px side padding, so the desktop
		     inner width is 812px; five tracks at a 120px floor and a 32px gap
		     need 5x120 + 4x32 = 728px and therefore fit, and with exactly
		     five items every track is filled and stretches to 1fr, giving
		     (812 - 128) / 5 = 136.8px per card — the same width the fixed
		     five-column form produced. At a 375px viewport the inner width is
		     327px, which fits two tracks at 147.5px each. The 120px floor is
		     load-bearing: a 180px floor would fit only three tracks at 812px
		     and would silently break UAT sub-item 5.
		     ═══════════════════════════════════════════════════════════════════ -->
		<div
			style="
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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

			<!-- Phase 49 (D-30) — the review queue's dashboard entry point.
			     At exactly 0 the card renders non-link muted text instead of
			     an accent link (49-05 <planner_decisions> E8 empty) — the
			     dashboard never advertises work that does not exist. The
			     link text pluralizes (E8 zero-one-many). -->
			<StatCard title="Review queue">
				{#snippet children()}
					<p style="font-size: 32px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
						{formatCount(data.reviewStats.total)}
					</p>
					{#if data.reviewStats.total === 0}
						<p style="font-size: 16px; color: #94a3b8; margin: 0;">
							No items need review
						</p>
					{:else}
						<a
							href="/admin/review"
							style="display: inline-flex; align-items: center; min-height: 44px; font-size: 16px; color: #93c5fd; text-decoration: none;"
						>
							{data.reviewStats.total === 1
								? '1 item needs review'
								: `${formatCount(data.reviewStats.total)} items need review`} →
						</a>
					{/if}
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

		<!-- ═══════════════════════════════════════════════════════════════════
		     DEV TOOLS (Phase 43, D-05/D-06/D-07) — last section on the page.
		     The conditional block below is the client-side complement of a
		     server decision (+page.server.ts's isDevelopment field), never the
		     gate itself — this markup is genuinely absent from production HTML
		     because the server never returns isDevelopment: true outside dev.
		     ═══════════════════════════════════════════════════════════════════ -->
		{#if data.isDevelopment}
			<section
				style="
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
					margin-top: 48px;
				"
			>
				<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
					Dev Tools
					<span
						style="
							display: inline-flex;
							align-items: center;
							gap: 4px;
							border: 1px solid #fbbf24;
							border-radius: 4px;
							padding: 2px 8px;
							font-size: 14px;
							font-weight: 400;
							color: #fbbf24;
							background-color: #1e293b;
							margin-left: 8px;
							vertical-align: middle;
						"
					>
						DEV ONLY
					</span>
				</h2>

				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 16px 0;">
					Wipes every argument, utterance, person, court tenure, and participant in this
					database, then reseeds exactly the four confirmed fixtures (see FIXTURES.md)
					through the corpus importer.
				</p>

				{#if resetRunning}
					<!-- Running state: replaces the button/confirm row in place. -->
					<div style="display: flex; align-items: center; gap: 8px; min-height: 44px;">
						<span
							aria-hidden="true"
							style="display: inline-block; animation: spin 1s linear infinite;"
						>◌</span>
						<span style="font-size: 16px; color: #94a3b8;">Resetting to fixture…</span>
					</div>
				{:else if resetConfirming}
					<!-- Confirming state: two-step Yes/No, no type-to-confirm input (D-05). -->
					<p style="font-size: 16px; color: #e2e8f0; margin: 0 0 8px 0;">
						This will permanently delete <span style="font-weight: 600;">every</span> argument,
						utterance, person, court tenure, and participant record — not just the fixtures.
						It cannot be undone.
					</p>
					<div style="display: flex; gap: 8px;">
						<form
							method="POST"
							action="?/resetToFixture"
							style="flex: 1;"
							use:enhance={() => {
								resetRunning = true;
								return async ({ result, update }) => {
									resetRunning = false;
									if (
										result.type === 'success' &&
										result.data &&
										Array.isArray((result.data as { resetFixtures?: unknown }).resetFixtures)
									) {
										resetResult = (result.data as { resetFixtures: ResetFixtureItem[] })
											.resetFixtures;
										resetConfirming = false;
										await invalidateAll();
									} else {
										// Error branch: control returns to Idle (not Confirming) and any
										// stale success list is cleared so it never sits above a fresh error.
										resetResult = null;
										resetConfirming = false;
										await update();
									}
								};
							}}
						>
							<button
								type="submit"
								disabled={resetRunning}
								style="
									display: block;
									width: 100%;
									min-height: 44px;
									background: transparent;
									border: 1px solid #ef4444;
									border-radius: 6px;
									font-size: 16px;
									font-weight: 600;
									color: #ef4444;
									cursor: pointer;
								"
							>
								Confirm reset
							</button>
						</form>
						<button
							type="button"
							disabled={resetRunning}
							onclick={() => {
								resetConfirming = false;
							}}
							style="
								flex: 1;
								min-height: 44px;
								background: transparent;
								border: 1px solid #334155;
								border-radius: 6px;
								font-size: 16px;
								font-weight: 400;
								color: #94a3b8;
								cursor: pointer;
							"
						>
							Cancel
						</button>
					</div>
				{:else}
					<!-- Idle state: type="button" only toggles state; it never submits. -->
					<button
						type="button"
						onclick={() => {
							resetConfirming = true;
						}}
						style="
							display: block;
							width: 100%;
							min-height: 44px;
							background: transparent;
							border: 1px solid #ef4444;
							border-radius: 6px;
							font-size: 16px;
							font-weight: 600;
							color: #ef4444;
							cursor: pointer;
						"
					>
						Reset to Fixture
					</button>
				{/if}

				{#if resetResult}
					<!-- Success state: badge + one line per reseeded fixture, natural wrap. -->
					<div style="margin-top: 16px;">
						<span
							style="
								display: inline-flex;
								align-items: center;
								border: 1px solid #4ade80;
								color: #4ade80;
								background-color: #1e293b;
								border-radius: 4px;
								padding: 2px 8px;
								font-size: 14px;
								font-weight: 400;
							"
						>
							✓ Reset complete
						</span>
						<div style="margin-top: 8px;">
							{#each resetResult as fixture (fixture.conversation_id)}
								<p style="font-size: 16px; color: #e2e8f0; margin: 0 0 4px 0;">
									{fixture.case_name} — {fixture.role}
								</p>
							{/each}
						</div>
					</div>
				{/if}

				<!-- Error state: role=alert, same treatment as the existing form?.deleteError precedent. -->
				{#if form?.resetError}
					<p
						role="alert"
						style="color: #ef4444; font-size: 14px; font-weight: 400; margin: 8px 0 0 0;"
					>{form.resetError}</p>
				{/if}

				<!-- Unresolved-speaker seeder (Phase 49, D-33a): additive, single-row, not
				     destructive — secondary/muted treatment, no two-step confirm. -->
				<div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #334155;">
					<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
						Nulls the resolved speaker on one advocate row of the Complexity fixture, so the
						unresolved-speaker case can be produced on demand.
					</p>
					<form
						method="POST"
						action="?/seedUnresolvedSpeaker"
						use:enhance={() => {
							seedSubmitting = true;
							return async ({ result, update }) => {
								seedSubmitting = false;
								if (
									result.type === 'success' &&
									result.data &&
									(result.data as { seedResult?: unknown }).seedResult
								) {
									seedResult = (result.data as { seedResult: SeedUnresolvedSpeakerResult })
										.seedResult;
									await invalidateAll();
								} else {
									seedResult = null;
									await update();
								}
							};
						}}
					>
						<button
							type="submit"
							disabled={seedSubmitting}
							style="
								display: block;
								width: 100%;
								min-height: 44px;
								background: transparent;
								border: 1px solid #334155;
								border-radius: 6px;
								font-size: 16px;
								font-weight: 600;
								color: #94a3b8;
								cursor: pointer;
							"
						>
							{seedSubmitting ? 'Seeding…' : 'Seed unresolved speaker'}
						</button>
					</form>

					{#if seedResult}
						<p style="font-size: 16px; color: #e2e8f0; margin: 8px 0 0 0;">
							Argument #{seedResult.argument_id} — "{seedResult.raw_speaker_label}" — trust tier:
							{seedResult.trust_tier}{seedResult.already_seeded ? ' (already seeded)' : ''}
						</p>
					{/if}

					{#if form?.seedError}
						<p
							role="alert"
							style="color: #ef4444; font-size: 14px; font-weight: 400; margin: 8px 0 0 0;"
						>{form.seedError}</p>
					{/if}
				</div>
			</section>
		{/if}
	</div>
</main>

<style>
	@keyframes spin {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}
</style>
