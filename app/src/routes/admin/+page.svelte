<script lang="ts">
	import StatCard from '$lib/admin/StatCard.svelte';
	import { enhance } from '$app/forms';
	import { invalidateAll } from '$app/navigation';
	import { onDestroy } from 'svelte';

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

	// Phase 52-05 (D-15): the Running state's per-fixture progress line.
	// Mirrors api/schemas/admin_dev.py::ResetProgress's `step` machine token
	// ("seeding_justices" | "reseeding_fixture_N") -- this component owns the
	// 52-UI-SPEC.md Copywriting Contract's five literal strings and maps the
	// backend's token to them, so the two layers can't drift independently.
	interface ResetProgress {
		step: string;
		completed: number;
		total: number;
	}

	const RESET_PROGRESS_STEP_1_COPY = 'Seeding justices…';

	let resetProgressText = $state(RESET_PROGRESS_STEP_1_COPY);
	let resetPollHandle: ReturnType<typeof setInterval> | null = null;

	// Maps a backend progress token to its 52-UI-SPEC.md literal. Returns
	// null for anything unrecognised (including no progress in flight) so
	// the caller can leave the last-observed text on screen rather than
	// clearing or guessing at a step that has not been reported.
	function fixtureProgressCopy(step: string | null | undefined): string | null {
		if (step === 'seeding_justices') return RESET_PROGRESS_STEP_1_COPY;
		const match = /^reseeding_fixture_(\d)$/.exec(step ?? '');
		if (match) return `Reseeding fixture ${match[1]} of 4…`;
		return null;
	}

	function stopResetPolling() {
		if (resetPollHandle !== null) {
			clearInterval(resetPollHandle);
			resetPollHandle = null;
		}
	}

	// Never advances the label on a timer or optimistically (D-15
	// prohibition) -- only ever writes a step the backend has actually
	// reported this poll. A poll failure, a null `progress` (reset not yet
	// started or already finished), or an unrecognised token all leave the
	// last-observed text in place rather than clearing or guessing.
	async function pollResetProgress() {
		try {
			const res = await fetch('/admin/dev-fixture-state', { cache: 'no-store' });
			if (!res.ok) return;
			const body: { progress?: ResetProgress | null } = await res.json();
			const copy = fixtureProgressCopy(body.progress?.step);
			if (copy) resetProgressText = copy;
		} catch {
			// Network hiccup mid-poll -- keep showing the last observed step.
		}
	}

	onDestroy(stopResetPolling);

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

<!-- Page background (--color-bg) — matches existing page pattern -->
<main style="background-color: var(--color-bg); min-height: 100vh;">
	<!-- Header bar: --color-surface bg, border-bottom --color-border -->
	<header
		style="
			background-color: var(--color-surface);
			border-bottom: 1px solid var(--color-border);
			padding: var(--space-lg) var(--space-xl);
		"
	>
		<h1
			style="
				font-size: var(--font-size-heading);
				font-weight: var(--font-weight-semibold);
				color: var(--color-text-primary);
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
			padding: var(--space-3xl) var(--space-xl);
		"
	>
		<!-- ═══════════════════════════════════════════════════════════════════
		     NEEDS ATTENTION (D-09: renders first, above the stat-card grid)
		     ═══════════════════════════════════════════════════════════════════ -->
		<section
			style="
				background-color: var(--color-surface);
				border: 1px solid var(--color-border);
				border-radius: 8px;
				padding: var(--space-xl);
			"
		>
			<h2 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0;">
				Needs Attention
			</h2>

			{#if allCaughtUp}
				<div>
					<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						All caught up
					</p>
					<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
						Nothing needs your attention right now.
					</p>
				</div>
			{:else}
				<!-- People sub-list (combined bench+advocate, D-05 amendment) -->
				<div style="margin-bottom: var(--space-lg);">
					<h3 style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						People
					</h3>
					{#if data.incompletePeople.length === 0}
						<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">
							No people currently have missing fields.
						</p>
					{:else}
						{#each data.incompletePeople as person (person.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 var(--space-sm) 0;">
								<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">{person.full_name}</span>
								<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">{missingFieldsLabel(person.missing)}</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/people"
						style="
							display: inline-flex;
							align-items: center;
							min-height: var(--touch-target);
							font-size: var(--font-size-caption);
							color: var(--color-accent);
							text-decoration: none;
						"
					>
						View all →
					</a>
				</div>

				<!-- Justices sub-list (bench-only tenure gaps, D-06) -->
				<div style="margin-bottom: var(--space-lg);">
					<h3 style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						Justices
					</h3>
					{#if data.tenureGapJustices.length === 0}
						<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">
							No tenure gaps found.
						</p>
					{:else}
						{#each data.tenureGapJustices as justice (justice.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 var(--space-sm) 0;">
								<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">{justice.full_name}</span>
								<span style="font-size: var(--font-size-caption); color: var(--color-status-warning);">Missing tenure</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/people?tab=bench&tenure_gaps=1"
						style="
							display: inline-flex;
							align-items: center;
							min-height: var(--touch-target);
							font-size: var(--font-size-caption);
							color: var(--color-accent);
							text-decoration: none;
						"
					>
						View all →
					</a>
				</div>

				<!-- Drafts sub-list (all drafts, no age threshold, D-03) -->
				<div>
					<h3 style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						Drafts
					</h3>
					{#if data.draftsList.length === 0}
						<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">
							No draft arguments.
						</p>
					{:else}
						{#each data.draftsList as draft (draft.id)}
							<div style="display: flex; justify-content: space-between; align-items: baseline; margin: 0 0 var(--space-sm) 0;">
								<span style="font-size: var(--font-size-body); color: var(--color-text-primary);">{draft.case_name}</span>
								<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">{draft.docket_number}</span>
							</div>
						{/each}
					{/if}
					<a
						href="/admin/arguments?status=draft"
						style="
							display: inline-flex;
							align-items: center;
							min-height: var(--touch-target);
							font-size: var(--font-size-caption);
							color: var(--color-accent);
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
				gap: var(--space-2xl);
				margin-top: var(--space-2xl);
			"
		>
			<StatCard title="Arguments">
				{#snippet children()}
					<p style="font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0; line-height: 1.2;">
						{formatCount(data.argumentStats.total)}
					</p>
					<div style="display: flex; flex-direction: column; gap: var(--space-sm);">
						<a
							href="/admin/arguments?status=published"
							style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-status-published); text-decoration: none;"
						>
							{formatCount(data.argumentStats.published)} Published
						</a>
						<a
							href="/admin/arguments?status=draft"
							style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-status-draft); text-decoration: none;"
						>
							{formatCount(data.argumentStats.draft)} Draft
						</a>
						<a
							href="/admin/arguments?status=unpublished"
							style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-status-unpublished); text-decoration: none;"
						>
							{formatCount(data.argumentStats.unpublished)} Unpublished
						</a>
					</div>
				{/snippet}
			</StatCard>

			<StatCard title="People">
				{#snippet children()}
					<p style="font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0; line-height: 1.2;">
						{formatCount(data.peopleStats.total)}
					</p>
					<a
						href="/admin/people"
						style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-accent); text-decoration: none;"
					>
						{formatCount(data.peopleStats.incomplete)} missing fields → Review
					</a>
				{/snippet}
			</StatCard>

			<StatCard title="Utterances">
				{#snippet children()}
					<p style="font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0; line-height: 1.2;">
						{formatCount(data.utteranceCount.total)}
					</p>
				{/snippet}
			</StatCard>

			<StatCard title="Pipeline runs">
				{#snippet children()}
					<p style="font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-xs) 0; line-height: 1.2;">
						{formatCount(data.pipelineStats.recent_count)}
						<span style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary);">(last 30 days)</span>
					</p>
					<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-lg) 0;">
						Last activity: {formatDate(data.pipelineStats.last_activity_at)}
					</p>
					<a
						href="/admin/pipeline"
						style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-accent); text-decoration: none;"
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
					<p style="font-size: var(--font-size-display); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0; line-height: 1.2;">
						{formatCount(data.reviewStats.total)}
					</p>
					{#if data.reviewStats.total === 0}
						<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
							No items need review
						</p>
					{:else}
						<a
							href="/admin/review"
							style="display: inline-flex; align-items: center; min-height: var(--touch-target); font-size: var(--font-size-body); color: var(--color-accent); text-decoration: none;"
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
				border: 1px dashed var(--color-border);
				border-radius: 8px;
				padding: var(--space-xl);
				margin-top: var(--space-3xl);
				opacity: 0.7;
			"
		>
			<h2 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
				Web Traffic
			</h2>
			<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0;">Coming soon</p>
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
					background-color: var(--color-surface);
					border: 1px solid var(--color-border);
					border-radius: 8px;
					padding: var(--space-xl);
					margin-top: var(--space-3xl);
				"
			>
				<h2 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0; line-height: 1.2;">
					Dev Tools
					<span
						style="
							display: inline-flex;
							align-items: center;
							gap: var(--space-xs);
							border: 1px solid var(--color-status-warning);
							border-radius: 4px;
							padding: var(--space-xs) var(--space-sm);
							font-size: var(--font-size-caption);
							font-weight: var(--font-weight-regular);
							color: var(--color-status-warning);
							background-color: var(--color-surface);
							margin-left: var(--space-sm);
							vertical-align: middle;
						"
					>
						DEV ONLY
					</span>
				</h2>

				<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-lg) 0;">
					Wipes every argument, utterance, person, court tenure, and participant in this
					database, then reseeds exactly the four confirmed fixtures (see FIXTURES.md)
					through the corpus importer.
				</p>

				{#if resetRunning}
					<!-- Running state: replaces the button/confirm row in place. Same flex row,
					     spinner glyph/animation and text styling as before (Phase 43) -- only the
					     text content now advances through D-15's five per-fixture progress steps,
					     driven by pollResetProgress polling the backend's actual progress record. -->
					<div style="display: flex; align-items: center; gap: var(--space-sm); min-height: var(--touch-target);">
						<span
							aria-hidden="true"
							style="display: inline-block; animation: spin 1s linear infinite;"
						>◌</span>
						<span style="font-size: var(--font-size-body); color: var(--color-text-secondary);">{resetProgressText}</span>
					</div>
				{:else if resetConfirming}
					<!-- Confirming state: two-step Yes/No, no type-to-confirm input (D-05). -->
					<p style="font-size: var(--font-size-body); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">
						This will permanently delete <span style="font-weight: var(--font-weight-semibold);">every</span> argument,
						utterance, person, court tenure, and participant record — not just the fixtures.
						It cannot be undone.
					</p>
					<div style="display: flex; gap: var(--space-sm);">
						<form
							method="POST"
							action="?/resetToFixture"
							style="flex: 1;"
							use:enhance={() => {
								resetRunning = true;
								resetProgressText = RESET_PROGRESS_STEP_1_COPY;
								stopResetPolling();
								resetPollHandle = setInterval(pollResetProgress, 1000);
								return async ({ result, update }) => {
									stopResetPolling();
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
									min-height: var(--touch-target);
									background: transparent;
									border: 1px solid var(--color-destructive);
									border-radius: 6px;
									font-size: var(--font-size-body);
									font-weight: var(--font-weight-semibold);
									color: var(--color-destructive);
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
								min-height: var(--touch-target);
								background: transparent;
								border: 1px solid var(--color-border);
								border-radius: 6px;
								font-size: var(--font-size-body);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
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
							min-height: var(--touch-target);
							background: transparent;
							border: 1px solid var(--color-destructive);
							border-radius: 6px;
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-semibold);
							color: var(--color-destructive);
							cursor: pointer;
						"
					>
						Reset to Fixture
					</button>
				{/if}

				{#if resetResult}
					<!-- Success state: badge + one line per reseeded fixture, natural wrap. -->
					<div style="margin-top: var(--space-lg);">
						<span
							style="
								display: inline-flex;
								align-items: center;
								border: 1px solid var(--color-status-published);
								color: var(--color-status-published);
								background-color: var(--color-surface);
								border-radius: 4px;
								padding: var(--space-xs) var(--space-sm);
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
							"
						>
							✓ Reset complete
						</span>
						<div style="margin-top: var(--space-sm);">
							{#each resetResult as fixture (fixture.conversation_id)}
								<p style="font-size: var(--font-size-body); color: var(--color-text-primary); margin: 0 0 var(--space-xs) 0;">
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
						style="color: var(--color-destructive); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); margin: var(--space-sm) 0 0 0;"
					>{form.resetError}</p>
				{/if}

				<!-- Unresolved-speaker seeder (Phase 49, D-33a): additive, single-row, not
				     destructive — secondary/muted treatment, no two-step confirm. -->
				<div style="margin-top: var(--space-xl); padding-top: var(--space-lg); border-top: 1px solid var(--color-border);">
					<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-sm) 0;">
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
								min-height: var(--touch-target);
								background: transparent;
								border: 1px solid var(--color-border);
								border-radius: 6px;
								font-size: var(--font-size-body);
								font-weight: var(--font-weight-semibold);
								color: var(--color-text-secondary);
								cursor: pointer;
							"
						>
							{seedSubmitting ? 'Seeding…' : 'Seed unresolved speaker'}
						</button>
					</form>

					{#if seedResult}
						<p style="font-size: var(--font-size-body); color: var(--color-text-primary); margin: var(--space-sm) 0 0 0;">
							Argument #{seedResult.argument_id} — "{seedResult.raw_speaker_label}" — trust tier:
							{seedResult.trust_tier}{seedResult.already_seeded ? ' (already seeded)' : ''}
						</p>
					{/if}

					{#if form?.seedError}
						<p
							role="alert"
							style="color: var(--color-destructive); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); margin: var(--space-sm) 0 0 0;"
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
