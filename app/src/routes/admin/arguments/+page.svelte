<script lang="ts">
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';

	type Blocker = { code: string; count: number };

	let { data, form } = $props();

	// Per-row Publish submitting state (Phase 48 plan 10), keyed by argument
	// id since this page holds many rows behind one shared `form` prop —
	// mirrors the detail page's `publishingState` pattern (plan 48-08).
	let publishingId = $state<number | null>(null);

	// Cancel affordance for the block panel (Phase 48 plan 10 follow-up).
	// The panel is driven entirely by server `form` state, which this page
	// shares across every row — mutating `form` itself to "dismiss" it would
	// either lose the row's identity or affect a different row, so dismissal
	// is tracked with its own local Rune instead. `form` is a NEW object on
	// every action result (SvelteKit reassigns it after each submission), so
	// comparing by reference — rather than by argumentId — means clicking
	// Publish again on the same row produces a form the dismissal no longer
	// matches, and the panel reappears correctly without any extra reset
	// logic. Because only one row's panel can ever be visible at a time (one
	// shared `form` reflects only the most recent submission), dismissing
	// one row's panel can never affect a different row's.
	//
	// MUST be `$state.raw`, never plain `$state`: assigning an object to a
	// `$state` variable wraps it in a deep reactive proxy, so `dismissedForm`
	// would hold a PROXY of `form` rather than `form` itself and the
	// `form !== dismissedForm` guard below would always be true — the panel
	// would never dismiss. `$state.raw` stores the reference as-is, which is
	// exactly what the reference comparison above depends on. This shipped
	// broken once (G-48-11); the structural contract tests grep source text
	// and cannot catch it, so the invariant lives here.
	let dismissedForm: unknown = $state.raw(null);

	// Segmented status filter (DASH-02, D-05, D-06) — one-param goto() round-trip,
	// same idiom as the People page's Bench/Advocate toggle.
	function selectStatus(value: 'all' | 'draft' | 'published' | 'unpublished') {
		if (value === 'all') {
			goto('/admin/arguments');
		} else {
			goto('/admin/arguments?status=' + value);
		}
	}

	function clearFilter() {
		goto('/admin/arguments');
	}

	function statusLabel(status: string): string {
		if (status === 'draft') return 'Draft';
		if (status === 'published') return 'Published';
		if (status === 'unpublished') return 'Unpublished';
		return status;
	}

	// Selected-state fill per UI-SPEC — each option uses its own semantic color.
	function filterButtonStyle(active: boolean, selectedColor: string): string {
		return `
			min-height: 44px;
			padding: 8px 16px;
			font-size: 16px;
			font-weight: 600;
			cursor: pointer;
			border: 1px solid ${active ? selectedColor : '#334155'};
			background-color: ${active ? selectedColor : '#1e293b'};
			color: ${active ? '#0f1117' : '#e2e8f0'};
		`;
	}

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

	// Passive trust-tier badge helpers (Phase 48 plan 10, operator-approved
	// enhancement, D-19/D-20). Purely informational — never wired to any
	// control, never disables the Publish button (explicitly rejected
	// alternative). Colors are visually distinct from the status badge's
	// palette above; this is inline styling only, not a design-system
	// dependency (Phase 51 owns the palette).
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

	// Blocked-publish blocker-code -> operator-readable sentence (Phase 48
	// D-19), duplicated verbatim from the detail page's own helper
	// ([id]/+page.svelte, plan 48-08) so both pages degrade identically for
	// any future blocker code added server-side. A bare tier name gives the
	// operator nothing to act on; each sentence names what dragged the tier
	// down, with a count.
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
		if (code === 'no_constituents') {
			return 'this argument has no utterances yet';
		}
		return `${count} occurrence${plural} of "${code}"`;
	}
</script>

<svelte:head>
	<title>Arguments — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<div style="display: flex; align-items: center; gap: 16px; flex-wrap: wrap;">
			<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">Arguments</h1>

			<!-- Status segmented filter control (DASH-02, D-05) -->
			<div style="display: flex; gap: 0;">
				<button
					type="button"
					aria-pressed={!data.status}
					aria-label="All arguments"
					onclick={() => selectStatus('all')}
					style="{filterButtonStyle(!data.status, '#93c5fd')} border-radius: 6px 0 0 6px;"
				>All</button>
				<button
					type="button"
					aria-pressed={data.status === 'draft'}
					aria-label="Draft arguments"
					onclick={() => selectStatus('draft')}
					style="{filterButtonStyle(data.status === 'draft', '#a78bfa')} border-left: none;"
				>Draft</button>
				<button
					type="button"
					aria-pressed={data.status === 'published'}
					aria-label="Published arguments"
					onclick={() => selectStatus('published')}
					style="{filterButtonStyle(data.status === 'published', '#4ade80')} border-left: none;"
				>Published</button>
				<button
					type="button"
					aria-pressed={data.status === 'unpublished'}
					aria-label="Unpublished arguments"
					onclick={() => selectStatus('unpublished')}
					style="{filterButtonStyle(data.status === 'unpublished', '#fb923c')} border-left: none; border-radius: 0 6px 6px 0;"
				>Unpublished</button>
			</div>
		</div>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		<!-- Active-filter indicator (D-05) — only for a specific status, never "All" -->
		{#if data.status === 'draft' || data.status === 'published' || data.status === 'unpublished'}
			<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
				Showing: {statusLabel(data.status)} arguments ·
				<button
					type="button"
					onclick={clearFilter}
					aria-label="Clear status filter"
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
				{#if data.status === 'draft' || data.status === 'published' || data.status === 'unpublished'}
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						No {statusLabel(data.status)} arguments.
					</p>
				{:else}
					<p style="font-size: 16px; color: #94a3b8; margin: 0;">
						No arguments yet. Start a pipeline run to ingest a transcript.
					</p>
				{/if}
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
								<span style={tierBadgeStyle(arg.trust_tier)} title="Trust tier">
									{tierLabel(arg.trust_tier)}
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
										<!-- Publish toggle — Draft or Unpublished both go to Published.
										     The button is NEVER disabled based on trust tier or block
										     state (operator-rejected alternative, Phase 48 plan 10) —
										     only while THIS row's own submission is in flight. -->
										<form
											method="POST"
											action="?/publish"
											use:enhance={() => {
												publishingId = arg.id;
												return async ({ update }) => {
													publishingId = null;
													await update();
												};
											}}
										>
											<input type="hidden" name="argument_id" value={arg.id} />
											<button
												type="submit"
												disabled={publishingId === arg.id}
												style="
													min-height: 44px;
													font-size: 14px;
													font-weight: 400;
													color: #93c5fd;
													background: transparent;
													border: 1px solid #93c5fd;
													border-radius: 6px;
													padding: 8px 12px;
													cursor: {publishingId === arg.id ? 'not-allowed' : 'pointer'};
													opacity: {publishingId === arg.id ? 0.7 : 1};
												"
											>{publishingId === arg.id ? 'Publishing…' : 'Publish'}</button>
										</form>
									{:else if arg.status === 'published'}
										<!-- Unpublish toggle — only when already published. Tracks
										     the same per-row `publishingId` submitting state as the
										     Publish button above (CR-03, 48-REVIEW.md) — a double-click
										     or slow round-trip can no longer submit this action twice
										     before the first navigation completes. -->
										<form
											method="POST"
											action="?/unpublish"
											use:enhance={() => {
												publishingId = arg.id;
												return async ({ update }) => {
													publishingId = null;
													await update();
												};
											}}
										>
											<input type="hidden" name="argument_id" value={arg.id} />
											<button
												type="submit"
												disabled={publishingId === arg.id}
												style="
													min-height: 44px;
													font-size: 14px;
													font-weight: 400;
													color: #94a3b8;
													background: transparent;
													border: 1px solid #334155;
													border-radius: 6px;
													padding: 8px 12px;
													cursor: {publishingId === arg.id ? 'not-allowed' : 'pointer'};
													opacity: {publishingId === arg.id ? 0.7 : 1};
												"
											>{publishingId === arg.id ? 'Unpublishing…' : 'Unpublish'}</button>
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
							<!-- Row-scoped, visible error shared by BOTH mutating actions on
							     this page: publish's non-overridable-gate failure / already-
							     published guard (Phase 48 plan 10, Defect 1's second half), and
							     unpublish's failure path (CR-01, 48-REVIEW.md). Neither action
							     ever sets form.publishBlocked on this branch, so the guard below
							     is safe to share — no reason field is offered for either (D-14;
							     unpublish has no override concept at all). Before plan 10, a
							     plain-string 422 was logged to the server console only and never
							     reached the operator on this page; before CR-01's fix, unpublish
							     didn't even check the response and always redirected as if it
							     had succeeded. -->
						{#if form?.error && form.argumentId === arg.id && !form.publishBlocked}
							<tr>
								<td colspan="6" style="padding: 0 0 12px 0; border-bottom: 1px solid #334155;">
									<p
										role="alert"
										style="
											margin: 0;
											padding: 8px 0;
											color: #ef4444;
											font-size: 14px;
											font-weight: 400;
										"
									>{form.error}</p>
								</td>
							</tr>
						{/if}
							<!-- Blocked-publish panel (Phase 48 plan 10, mirroring the detail
							     page's block panel, plan 48-08) — addressed to THIS row only via
							     form.argumentId, since this page shares one `form` prop across
							     every row (T-48-10-ROWMISMATCH). Rendered as its own full-width
							     row so it does not distort the table's column layout. -->
						{#if form?.publishBlocked && form.argumentId === arg.id && form !== dismissedForm}
							<tr>
								<td colspan="6" style="padding: 0 0 12px 0; border-bottom: 1px solid #334155;">
									<div
										style="
											margin: 0;
											padding: 16px;
											border: 1px solid #fb923c;
											border-radius: 6px;
											background-color: #1e293b;
										"
									>
										<p style="font-size: 16px; font-weight: 600; color: #fb923c; margin: 0 0 8px 0; display: flex; align-items: center; justify-content: space-between; gap: 8px;">
											<span>
												Publish blocked
												{#if form.trustTier}
													<span style={tierBadgeStyle(form.trustTier)}>{tierLabel(form.trustTier)}</span>
												{/if}
											</span>
											<!-- Dismisses the WHOLE panel, not just the reason textarea —
											     the operator can always click Publish again to bring it
											     back, so there's nothing worth preserving in a partial
											     dismiss. A plain text "Cancel" button (not an icon-only
											     "x") matches this file's and the detail page's existing
											     convention (the Danger Zone's two-step delete confirm
											     uses the same bare "Cancel" wording and styling). Local
											     Rune only — never mutates `form`. -->
											<button
												type="button"
												onclick={() => { dismissedForm = form; }}
												style="
													background: none;
													border: none;
													padding: 4px 8px;
													margin: 0;
													color: #94a3b8;
													font-size: 14px;
													font-weight: 400;
													text-decoration: underline;
													cursor: pointer;
													flex-shrink: 0;
												"
											>Cancel</button>
										</p>

										{#if form.blockMessage}
											<p style="font-size: 14px; color: #e2e8f0; margin: 0 0 8px 0;">
												{form.blockMessage}
											</p>
										{/if}

										{#if form.blockers && form.blockers.length > 0}
											<ul style="margin: 0 0 16px 0; padding-left: 20px;">
												{#each form.blockers as b}
													<li style="font-size: 14px; color: #94a3b8; padding: 2px 0;">
														{blockerSentence(b.code, b.count)}
													</li>
												{/each}
											</ul>
										{/if}

										{#if form?.overrideReasonRequired && form.argumentId === arg.id}
											<p role="alert" style="font-size: 14px; font-weight: 600; color: #ef4444; margin: 0 0 12px 0;">
												A non-empty reason is required — your submission was blank or only whitespace.
											</p>
										{/if}

										<form
											method="POST"
											action="?/publish"
											use:enhance={() => {
												publishingId = arg.id;
												return async ({ update }) => {
													publishingId = null;
													await update();
												};
											}}
										>
											<input type="hidden" name="argument_id" value={arg.id} />
											<label
												for={'override_reason_' + arg.id}
												style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
											>Reason for publishing anyway</label>
											<!-- `required` is defense-in-depth only (D-17) — the server's
											     own .strip() check on override_reason is the single
											     authority; a whitespace-only submission is still rejected
											     server-side. -->
											<textarea
												id={'override_reason_' + arg.id}
												name="override_reason"
												required
												rows="3"
												style="
													display: block;
													width: 100%;
													max-width: 480px;
													box-sizing: border-box;
													background-color: #0f1117;
													border: 1px solid #334155;
													border-radius: 6px;
													color: #e2e8f0;
													font-size: 14px;
													padding: 8px 12px;
													margin-bottom: 12px;
												"
											></textarea>
											<button
												type="submit"
												disabled={publishingId === arg.id}
												style="
													min-height: 44px;
													background-color: #1e293b;
													border: 1px solid #fb923c;
													border-radius: 6px;
													font-size: 14px;
													font-weight: 600;
													color: #e2e8f0;
													padding: 8px 16px;
													cursor: {publishingId === arg.id ? 'not-allowed' : 'pointer'};
													opacity: {publishingId === arg.id ? 0.7 : 1};
												"
											>{publishingId === arg.id ? 'Publishing…' : 'Publish anyway with this reason'}</button>
										</form>
									</div>
								</td>
							</tr>
						{/if}
						{/each}
				</tbody>
			</table>
		{/if}
	</div>
</main>
