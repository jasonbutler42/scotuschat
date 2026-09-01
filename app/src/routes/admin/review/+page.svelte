<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';

	let { data, form } = $props();

	// Row-expand state (E1 populated / "Show details"/"Hide details") — a
	// text-only toggle controlling a full-width <tr> beneath the trigger
	// row, the exact technique already used for the publish-blocked panel
	// on admin/arguments/+page.svelte. Deliberately NOT a native disclosure
	// element (it cannot legally wrap a <tr>).
	let expandedIds = $state(new Set<number>());
	function toggleExpand(id: number) {
		const next = new Set(expandedIds);
		if (next.has(id)) {
			next.delete(id);
		} else {
			next.add(id);
		}
		expandedIds = next;
	}

	// ── Filter/tab navigation — every filter, tab, and action is a full-page
	// goto()/form POST round trip; there is no client-side filter state
	// (E3/loading). Filters compose as URL query params so they are
	// back-button-safe and linkable (D-07).
	function gotoWithParams(overrides: {
		status?: string | null;
		tier?: string | null;
		review_state?: string | null;
	}) {
		const params = new URLSearchParams();
		params.set('tab', data.tab);
		const status = overrides.status !== undefined ? overrides.status : data.status;
		const tier = overrides.tier !== undefined ? overrides.tier : data.tier;
		const review_state =
			overrides.review_state !== undefined ? overrides.review_state : data.review_state;
		if (status) params.set('status', status);
		if (tier) params.set('tier', tier);
		if (review_state) params.set('review_state', review_state);
		goto('/admin/review?' + params.toString());
	}

	function switchTab(tab: 'arguments' | 'people') {
		goto('/admin/review?tab=' + tab);
	}

	// ── Form-action URLs (G-50-4a).
	//
	// A bare action="?/name" REPLACES the page's query string, so the server
	// action saw url.search === "?/name" and redirect(303, ...) dropped the
	// operator's tab and filters — after every approve/confirm/reflag they
	// landed back on the unfiltered top of the queue. Carrying the live
	// filter query in the action URL is what lets filterRedirect() in
	// +page.server.ts send them back where they were.
	//
	// $derived, NOT a plain const off `data`: each action redirects and the
	// load re-runs, replacing `data`. A captured const would freeze these
	// action URLs at their first-render values — the stale-prop-capture
	// class this codebase has been bitten by before.
	const filterQuery = $derived.by(() => {
		const params = new URLSearchParams();
		params.set('tab', data.tab);
		if (data.status) params.set('status', data.status);
		if (data.tier) params.set('tier', data.tier);
		if (data.review_state) params.set('review_state', data.review_state);
		return params.toString();
	});

	function actionUrl(name: string) {
		return `?${filterQuery}&/${name}`;
	}

	function selectStatus(value: string) {
		gotoWithParams({ status: value === 'all' ? null : value });
	}

	function onSelectTier(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		gotoWithParams({ tier: value === '' ? null : value });
	}

	function onSelectReviewState(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		gotoWithParams({ review_state: value === '' ? null : value });
	}

	function clearFilter() {
		goto('/admin/review?tab=' + data.tab);
	}

	// ── Label/style helpers ──────────────────────────────────────────────

	// Selected-state fill per UI-SPEC (copied verbatim from
	// admin/arguments/+page.svelte's filterButtonStyle).
	function filterButtonStyle(active: boolean, selectedColor: string): string {
		return `
			min-height: var(--touch-target);
			padding: var(--space-sm) var(--space-lg);
			font-size: var(--font-size-body);
			font-weight: var(--font-weight-semibold);
			cursor: pointer;
			border: 1px solid ${active ? selectedColor : 'var(--color-border)'};
			background-color: ${active ? selectedColor : 'var(--color-surface)'};
			color: ${active ? 'var(--color-bg)' : 'var(--color-text-primary)'};
		`;
	}

	function statusLabel(status: string): string {
		if (status === 'candidate') return 'Candidate';
		if (status === 'draft') return 'Draft';
		if (status === 'published') return 'Published';
		if (status === 'unpublished') return 'Unpublished';
		return status;
	}

	// StatusBadge helpers — the [id] detail page's Candidate-aware
	// convention (badgeLabel falls back to 'Candidate', not 'Pipeline'),
	// per this plan's explicit citation of that file over the arguments
	// list page's own version.
	function badgeStyle(status: string): string {
		let color: string;
		if (status === 'published') {
			color = 'var(--color-status-published)';
		} else if (status === 'draft') {
			color = 'var(--color-status-draft)';
		} else if (status === 'unpublished') {
			color = 'var(--color-status-unpublished)';
		} else {
			color = 'var(--color-text-secondary)';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-surface); color: ${color}; display: inline-block;`;
	}

	function badgeLabel(status: string): string {
		if (status === 'published') return 'Published';
		if (status === 'draft') return 'Draft';
		if (status === 'unpublished') return 'Unpublished';
		return 'Candidate';
	}

	// Passive trust-tier badge helpers — copied verbatim from
	// admin/arguments/+page.svelte.
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
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-bg); color: ${color}; display: inline-block;`;
	}

	function tierLabel(tier: string): string {
		if (tier === 'verified') return 'Verified';
		if (tier === 'trusted') return 'Trusted';
		if (tier === 'provisional') return 'Provisional';
		if (tier === 'uncertain') return 'Uncertain';
		return tier;
	}

	// review_state / discrepancy badge — the existing tierBadgeStyle
	// formula verbatim, only the color lookup differs (UI-SPEC § Color).
	function reviewStateBadgeStyle(state: string): string {
		let color: string;
		if (state === 'unreviewed') {
			color = '#475569';
		} else if (state === 'needs_review') {
			color = 'var(--color-status-warning)';
		} else if (state === 'operator_confirmed') {
			color = '#2dd4bf';
		} else if (state === 'operator_edited') {
			color = '#e879f9';
		} else {
			color = '#64748b';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-bg); color: ${color}; display: inline-block;`;
	}

	function reviewStateLabel(state: string): string {
		if (state === 'unreviewed') return 'Unreviewed';
		if (state === 'needs_review') return 'Needs review';
		if (state === 'operator_confirmed') return 'Confirmed';
		if (state === 'operator_edited') return 'Edited';
		return state;
	}

	function discrepancyBadgeStyle(): string {
		const color = '#fb7185';
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-bg); color: ${color}; display: inline-block;`;
	}

	// Bench/Advocate side-role hint — the exact formula ResolveCard.svelte
	// already uses for the same participant `side` vocabulary.
	function sideRoleHint(side: string): string {
		return side === 'BENCH' ? 'Bench' : 'Advocate';
	}

	// Attention-count copy (E1 populated/partial) — no count text at all
	// when N is 0 (the row is queued solely via the degraded-tier leg).
	// Domain noun and subject-verb agreement (G-49-4b/G-49-5b): the shape
	// is copied verbatim from admin/+page.svelte's Review-queue StatCard
	// so the two surfaces cannot disagree again.
	function attentionCountText(n: number): string {
		return n === 1 ? '1 participant needs review' : `${n} participants need review`;
	}

	// Discrepancy value display (E6 partial backstop) — an absent side
	// renders the literal "(none)", never an empty pair of quotes.
	function discrepancyValueDisplay(value: string | null): string {
		return value === null ? '(none)' : `"${value}"`;
	}

	// Blocked-publish blocker-code -> operator-readable sentence, copied
	// verbatim from admin/arguments/+page.svelte so a zero-flagged-
	// constituent degraded row's expanded panel reads identically to the
	// existing publish-blocked panel (49-05 <planner_decisions> E5 empty).
	function blockerSentence(code: string, count: number): string {
		const plural = count === 1 ? '' : 's';
		if (code === 'unresolved_utterance_speaker') {
			return `${count} utterance${plural} ${count === 1 ? 'has' : 'have'} no resolved speaker`;
		}
		if (code === 'unresolved_participant') {
			return `${count} participant${plural} ${count === 1 ? 'is' : 'are'} unresolved`;
		}
		if (code === 'llm_corrective_utterance') {
			return `${count} utterance${plural} came from the LLM corrective pass`;
		}
		if (code === 'uncertain_participant') {
			return `${count} participant${plural} ${count === 1 ? 'has' : 'have'} unverified provenance`;
		}
		if (code === 'no_constituents') {
			return 'this argument has no utterances yet';
		}
		return `${count} occurrence${plural} of "${code}"`;
	}

	function argumentEditHref(item: { admin_job_id: number | null; id: number }): string {
		return item.admin_job_id !== null
			? `/admin/pipeline/${item.admin_job_id}`
			: `/admin/arguments/${item.id}`;
	}

	// The row action label must branch on the same condition as
	// argumentEditHref immediately above (G-49-4a) — a static "Edit" label
	// served two destinations and could only ever be right about one. The
	// operator supplied the "Edit pipeline" phrasing (completed here to
	// name the destination noun) and explicitly rejected a lifecycle-state
	// label such as "Edit draft".
	function argumentEditLabel(item: { admin_job_id: number | null }): string {
		return item.admin_job_id !== null ? 'Edit pipeline run' : 'Edit argument';
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

	// Active-filter indicator (E10) — names whichever of the up-to-three
	// filters are set; tier/status only apply to the Arguments tab.
	const activeFilterLabels = $derived(
		[
			data.tab === 'arguments' && data.status ? statusLabel(data.status) : null,
			data.tab === 'arguments' && data.tier ? tierLabel(data.tier) + ' tier' : null,
			data.review_state ? reviewStateLabel(data.review_state) : null,
		].filter((label): label is string => label !== null),
	);

	const items = $derived(data.tab === 'arguments' ? data.argumentItems : data.personItems);
</script>

<svelte:head>
	<title>Review — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: var(--color-bg); min-height: 100vh;">
	<header style="background-color: var(--color-surface); border-bottom: 1px solid var(--color-border); padding: var(--space-lg) var(--space-xl);">
		<div style="max-width: 860px; margin: 0 auto; display: flex; align-items: center; gap: var(--space-lg); flex-wrap: wrap;">
			<h1 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-accent); margin: 0;">Review</h1>

			<div style="display: flex; gap: 0;">
				<button
					type="button"
					aria-pressed={data.tab === 'arguments'}
					aria-label="Arguments tab"
					onclick={() => switchTab('arguments')}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-lg);
						border: 1px solid {data.tab === 'arguments' ? 'var(--color-accent)' : 'var(--color-border)'};
						border-radius: 6px 0 0 6px;
						background-color: {data.tab === 'arguments' ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {data.tab === 'arguments' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						cursor: pointer;
					"
				>Arguments</button>
				<button
					type="button"
					aria-pressed={data.tab === 'people'}
					aria-label="People tab"
					onclick={() => switchTab('people')}
					style="
						min-height: var(--touch-target);
						padding: var(--space-sm) var(--space-lg);
						border: 1px solid {data.tab === 'people' ? 'var(--color-accent)' : 'var(--color-border)'};
						border-left: none;
						border-radius: 0 6px 6px 0;
						background-color: {data.tab === 'people' ? 'var(--color-accent)' : 'var(--color-surface)'};
						color: {data.tab === 'people' ? 'var(--color-bg)' : 'var(--color-text-primary)'};
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						cursor: pointer;
					"
				>People</button>
			</div>
		</div>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: var(--space-3xl) var(--space-xl);">
		{#if form?.error}
			<p role="alert" style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-destructive); margin: 0 0 var(--space-lg) 0;">
				{form.error}
			</p>
		{/if}

		<!-- Filter row (E3) -->
		<div style="display: flex; flex-wrap: wrap; gap: var(--space-lg); align-items: center; margin-bottom: var(--space-lg);">
			{#if data.tab === 'arguments'}
				<!-- G-49-5a: the status segment group's ~480px min-content width
				     (five 44px-min-height, 16px-font buttons with no flex-wrap)
				     overflows the 327px inner content width at a 375px viewport
				     independently of the queue tables. min-width: 0 on this outer
				     wrapper is load-bearing: a flex item's default min-width: auto
				     resolves to its content's min-content size, so without it the
				     horizontal-scroll declaration below never engages. width:
				     max-content on the inner group keeps the five segments at their natural
				     widths (no flex-wrap — a wrapped second line would show a
				     detached, half-rounded fragment given the first/last button's
				     one-sided border-radius and the middle four's border-left: none). -->
				<div style="min-width: 0; overflow-x: auto;">
				<div style="display: flex; gap: 0; width: max-content;">
					<button
						type="button"
						aria-pressed={!data.status}
						aria-label="All statuses"
						onclick={() => selectStatus('all')}
						style="{filterButtonStyle(!data.status, 'var(--color-accent)')} border-radius: 6px 0 0 6px;"
					>All</button>
					<button
						type="button"
						aria-pressed={data.status === 'candidate'}
						aria-label="Candidate arguments"
						onclick={() => selectStatus('candidate')}
						style="{filterButtonStyle(data.status === 'candidate', 'var(--color-text-secondary)')} border-left: none;"
					>Candidate</button>
					<button
						type="button"
						aria-pressed={data.status === 'draft'}
						aria-label="Draft arguments"
						onclick={() => selectStatus('draft')}
						style="{filterButtonStyle(data.status === 'draft', 'var(--color-status-draft)')} border-left: none;"
					>Draft</button>
					<button
						type="button"
						aria-pressed={data.status === 'published'}
						aria-label="Published arguments"
						onclick={() => selectStatus('published')}
						style="{filterButtonStyle(data.status === 'published', 'var(--color-status-published)')} border-left: none;"
					>Published</button>
					<button
						type="button"
						aria-pressed={data.status === 'unpublished'}
						aria-label="Unpublished arguments"
						onclick={() => selectStatus('unpublished')}
						style="{filterButtonStyle(data.status === 'unpublished', 'var(--color-status-unpublished)')} border-left: none; border-radius: 0 6px 6px 0;"
					>Unpublished</button>
				</div>
				</div>

				<label style="display: flex; align-items: center; gap: var(--space-sm); font-size: var(--font-size-caption); color: var(--color-text-secondary);">
					Trust tier
					<select
						value={data.tier ?? ''}
						onchange={onSelectTier}
						style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) var(--space-md); font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
					>
						<option value="">All tiers</option>
						<option value="verified">Verified</option>
						<option value="trusted">Trusted</option>
						<option value="provisional">Provisional</option>
						<option value="uncertain">Uncertain</option>
					</select>
				</label>
			{/if}

			<label style="display: flex; align-items: center; gap: var(--space-sm); font-size: var(--font-size-caption); color: var(--color-text-secondary);">
				Review state
				<select
					value={data.review_state ?? ''}
					onchange={onSelectReviewState}
					style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) var(--space-md); font-size: var(--font-size-body); color: var(--color-text-primary); box-sizing: border-box;"
				>
					<option value="">All review states</option>
					<option value="unreviewed">Unreviewed</option>
					<option value="needs_review">Needs review</option>
					<option value="operator_confirmed">Confirmed</option>
					<option value="operator_edited">Edited</option>
				</select>
			</label>
		</div>

		<!-- Active-filter indicator (E10) -->
		{#if activeFilterLabels.length > 0}
			<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-lg) 0;">
				Showing: {activeFilterLabels.join(', ')} ·
				<button
					type="button"
					onclick={clearFilter}
					aria-label="Clear filter"
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

		{#if items.length === 0}
			<!-- Empty state (E1/E2/E9) — filtered-empty reuses the same copy -->
			<div
				style="
					background-color: var(--color-surface);
					border: 1px solid var(--color-border);
					border-radius: 8px;
					padding: var(--space-xl);
					text-align: center;
				"
			>
				<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-xs) 0;">
					All caught up
				</p>
				<p style="font-size: var(--font-size-body); color: var(--color-text-secondary); margin: 0;">
					{data.tab === 'arguments'
						? 'No arguments currently need review.'
						: 'No people currently need review.'}
				</p>
			</div>
		{:else if data.tab === 'arguments'}
			<!-- G-49-5a: this table's twelve no-wrap cells pin a min-content
			     width wider than the 327px inner content width at a 375px
			     viewport, so it scrolls inside this container rather than
			     pushing the page body sideways. Those cells and the
			     no-truncation rule (49-UI-SPEC E1/E2 long-text) are deliberately
			     left intact — nothing here is clipped or ellipsised. -->
			<div style="overflow-x: auto;">
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Tier / Status</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border);">Case name</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Docket</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Argued date</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border);">Needs-attention</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Expand</th>
					</tr>
				</thead>
				<tbody>
					{#each data.argumentItems as item (item.id)}
						<tr>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; white-space: nowrap;">
								<span style={tierBadgeStyle(item.trust_tier)}>{tierLabel(item.trust_tier)}</span>
								<span style="display: inline-block; width: 4px;"></span>
								<span style={badgeStyle(item.status)}>{badgeLabel(item.status)}</span>
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-primary); font-size: var(--font-size-body);">
								{item.case_name}
								{#if item.argument_discrepancies.length > 0}
									<span style="display: inline-block; width: 4px;"></span>
									<span style={discrepancyBadgeStyle()}>Discrepancy</span>
								{/if}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-secondary); font-size: var(--font-size-caption); white-space: nowrap;">
								{item.docket_number}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-secondary); font-size: var(--font-size-caption); white-space: nowrap;">
								{formatDate(item.argued_date)}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-secondary); font-size: var(--font-size-caption);">
								{#if item.attention_count > 0}
									{attentionCountText(item.attention_count)}
								{/if}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; white-space: nowrap;">
								<button
									type="button"
									aria-expanded={expandedIds.has(item.id)}
									onclick={() => toggleExpand(item.id)}
									style="
										background: none;
										border: none;
										padding: 0;
										margin: 0;
										color: var(--color-accent);
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-regular);
										cursor: pointer;
										text-decoration: underline;
									"
								>{expandedIds.has(item.id) ? 'Hide details' : 'Show details'}</button>
							</td>
						</tr>
						{#if expandedIds.has(item.id)}
							<tr>
								<td colspan="6" style="padding: 0 0 var(--space-lg) 0; border-bottom: 1px solid var(--color-border);">
									{#if item.argument_discrepancies.length > 0}
										<div style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-lg); margin: var(--space-xs) var(--space-md) var(--space-lg) var(--space-md);">
											<div style="display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; margin-bottom: var(--space-sm);">
												<span style="color: var(--color-text-primary); font-size: var(--font-size-body);">This argument's own values and its lead case's</span>
												<span style={discrepancyBadgeStyle()}>Discrepancy</span>
											</div>
											{#each item.argument_discrepancies as d (d.id)}
												<p style="font-size: var(--font-size-caption); margin: var(--space-xs) 0;">
													<span style="color: var(--color-text-secondary);">{d.field}: existing</span>
													<span style="color: var(--color-text-primary);"> {discrepancyValueDisplay(d.existing_value)}</span>
													<span style="color: var(--color-text-secondary);"> ({d.existing_source ?? '—'}/{d.existing_method ?? '—'}) — incoming</span>
													<span style="color: var(--color-text-primary);"> {discrepancyValueDisplay(d.incoming_value)}</span>
													<span style="color: var(--color-text-secondary);"> ({d.incoming_source ?? '—'}/{d.incoming_method ?? '—'})</span>
												</p>
											{/each}
										</div>
									{/if}
									{#if item.constituents.length > 0}
										<div style="display: flex; flex-direction: column; gap: var(--space-lg); padding: var(--space-xs) var(--space-md) 0 var(--space-md);">
											{#each item.constituents as constituent (constituent.participant_id)}
												<div style="background-color: var(--color-surface); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-lg);">
													<div style="display: flex; align-items: center; gap: var(--space-sm); flex-wrap: wrap; margin-bottom: var(--space-sm);">
														<span style="color: var(--color-text-primary); font-size: var(--font-size-body);">
															{constituent.person_id === null ? 'Unresolved speaker' : constituent.display_name}
														</span>
														<span style="color: var(--color-text-secondary); font-size: var(--font-size-caption);">({sideRoleHint(constituent.side)})</span>
														<span style={reviewStateBadgeStyle(constituent.review_state)}>{reviewStateLabel(constituent.review_state)}</span>
														{#if constituent.has_open_discrepancy}
															<span style={discrepancyBadgeStyle()}>Discrepancy</span>
														{/if}
													</div>

													{#if constituent.has_open_discrepancy}
														<div style="margin-bottom: var(--space-md);">
															{#each constituent.discrepancies as d (d.id)}
																<p style="font-size: var(--font-size-caption); margin: var(--space-xs) 0;">
																	<span style="color: var(--color-text-secondary);">{d.field}: existing</span>
																	<span style="color: var(--color-text-primary);"> {discrepancyValueDisplay(d.existing_value)}</span>
																	<span style="color: var(--color-text-secondary);"> ({d.existing_source ?? '—'}/{d.existing_method ?? '—'}) — incoming</span>
																	<span style="color: var(--color-text-primary);"> {discrepancyValueDisplay(d.incoming_value)}</span>
																	<span style="color: var(--color-text-secondary);"> ({d.incoming_source ?? '—'}/{d.incoming_method ?? '—'})</span>
																</p>
															{/each}
														</div>
													{/if}

													<div style="display: flex; gap: var(--space-sm); flex-wrap: wrap;">
														{#if constituent.person_id !== null && constituent.review_state === 'needs_review'}
															<form method="POST" action={actionUrl('confirm')} use:enhance>
																<input type="hidden" name="id" value={constituent.participant_id} />
																<button
																	type="submit"
																	style="min-height: var(--touch-target-dense); padding: var(--space-xs) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); cursor: pointer; border: 1px solid var(--color-accent); background-color: transparent; color: var(--color-accent); border-radius: 6px;"
																>Confirm</button>
															</form>
														{/if}
														{#if constituent.person_id === null}
															<form method="POST" action={actionUrl('confirmUnattributable')} use:enhance>
																<input type="hidden" name="id" value={constituent.participant_id} />
																<button
																	type="submit"
																	style="min-height: var(--touch-target-dense); padding: var(--space-xs) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); cursor: pointer; border: 1px solid var(--color-border); background-color: transparent; color: var(--color-text-secondary); border-radius: 6px;"
																>Confirm as unattributable</button>
															</form>
														{/if}
														<a
															href={argumentEditHref(item)}
															style="display: inline-flex; align-items: center; font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: underline;"
														>{argumentEditLabel(item)}</a>
														{#if constituent.review_state === 'operator_confirmed' || constituent.review_state === 'operator_edited'}
															<form method="POST" action={actionUrl('reflag')} use:enhance>
																<input type="hidden" name="id" value={constituent.participant_id} />
																<button
																	type="submit"
																	style="background: none; border: none; padding: 0; margin: 0; display: inline-flex; align-items: center; color: var(--color-text-secondary); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); cursor: pointer; text-decoration: underline;"
																>Re-flag for review</button>
															</form>
														{/if}
													</div>
												</div>
											{/each}
										</div>
									{:else}
										<div style="padding: var(--space-md) var(--space-md) 0 var(--space-md);">
											<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-sm) 0;">
												No flagged participants — this argument is queued because:
											</p>
											<ul style="margin: 0; padding-left: 20px;">
												{#each item.blockers as blocker}
													<li style="font-size: var(--font-size-caption); color: var(--color-text-secondary); padding: 2px 0;">
														{blockerSentence(blocker.code, blocker.count)}
													</li>
												{/each}
											</ul>
										</div>
									{/if}
									{#if item.status === 'candidate'}
										<!-- Argument-scoped Approve (D-14/D-19/PD-12) — the only new
										     per-argument action on this screen; deliberately rendered
										     once per argument OUTSIDE the each-block/blockers-fallback
										     pair above so it always appears for a CANDIDATE argument
										     regardless of whether any flagged participant exists — a
										     candidate argument queued solely via a degraded-tier or
										     argument/case-discrepancy leg still needs to be
										     approvable. Absent for every other status (D-19). -->
										<div style="display: flex; gap: var(--space-sm); flex-wrap: wrap; padding: var(--space-md) var(--space-md) 0 var(--space-md);">
											<form method="POST" action={actionUrl('approve')} use:enhance>
												<input type="hidden" name="id" value={item.id} />
												<button
													type="submit"
													style="min-height: var(--touch-target-dense); padding: var(--space-xs) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); cursor: pointer; border: 1px solid var(--color-accent); background-color: transparent; color: var(--color-accent); border-radius: 6px;"
												>Approve — move to Draft</button>
											</form>
										</div>
									{/if}
								</td>
							</tr>
						{/if}
					{/each}
				</tbody>
			</table>
			</div>
		{:else}
			<!-- G-49-5a: same horizontal-scroll containment as the Arguments
			     table above. -->
			<div style="overflow-x: auto;">
			<table style="width: 100%; border-collapse: collapse;">
				<thead>
					<tr>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Review state</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border);">Full name</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border);">Provenance note</th>
						<th scope="col" style="text-align: left; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); padding: var(--space-sm) var(--space-md); border-bottom: 1px solid var(--color-border); white-space: nowrap;">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each data.personItems as person (person.id)}
						<tr>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; white-space: nowrap;">
								<span style={reviewStateBadgeStyle(person.review_state)}>{reviewStateLabel(person.review_state)}</span>
								{#if person.has_open_discrepancy}
									<span style="display: inline-block; width: 4px;"></span>
									<span style={discrepancyBadgeStyle()}>Discrepancy</span>
								{/if}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-primary); font-size: var(--font-size-body);">
								{person.full_name}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; color: var(--color-text-secondary); font-size: var(--font-size-caption);">
								{person.provenance_note}
							</td>
							<td style="padding: var(--space-md); border-bottom: 1px solid var(--color-border); vertical-align: top; white-space: nowrap;">
								<div style="display: flex; gap: var(--space-sm); flex-wrap: wrap;">
									{#if person.review_state === 'needs_review' || person.review_state === 'unreviewed'}
										<form method="POST" action={actionUrl('confirm')} use:enhance>
											<input type="hidden" name="kind" value="person" />
											<input type="hidden" name="id" value={person.id} />
											<button
												type="submit"
												style="min-height: var(--touch-target-dense); padding: var(--space-xs) var(--space-md); font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); cursor: pointer; border: 1px solid var(--color-accent); background-color: transparent; color: var(--color-accent); border-radius: 6px;"
											>Confirm</button>
										</form>
									{/if}
									<a
										href={`/admin/people/${person.id}`}
										style="display: inline-flex; align-items: center; font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: underline;"
									>Edit</a>
									{#if person.review_state === 'operator_confirmed' || person.review_state === 'operator_edited'}
										<form method="POST" action={actionUrl('reflag')} use:enhance>
											<input type="hidden" name="kind" value="person" />
											<input type="hidden" name="id" value={person.id} />
											<button
												type="submit"
												style="background: none; border: none; padding: 0; margin: 0; display: inline-flex; align-items: center; color: var(--color-text-secondary); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); cursor: pointer; text-decoration: underline;"
											>Re-flag for review</button>
										</form>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
			</div>
		{/if}
	</div>
</main>
