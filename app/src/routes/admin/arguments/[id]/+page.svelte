<script lang="ts">
	import { enhance } from '$app/forms';
	import { tick } from 'svelte';
	import ArgumentDetailsCard from '$lib/components/ArgumentDetailsCard.svelte';
	import CopyableExtractedValue from '$lib/components/CopyableExtractedValue.svelte';
	// G-49-3/D-35 (plan 49-10): the bucket rule, the boundary-crossing
	// predicate, and the operator-visible role labels are shared with
	// ResolveCard.svelte — both cards import from the single source of
	// truth rather than each declaring their own copy.
	import { SIDE_LABEL, sideBucket, crossesSideBoundary } from '$lib/participantSide';

	let { data, form } = $props();

	// Submitting state per named action.
	let savingState = $state(false);
	let publishingState = $state(false);
	let unpublishingState = $state(false);
	let caseNameInput: HTMLInputElement | null = $state(null);
	let docketNumberInput: HTMLInputElement | null = $state(null);
	let nativeCaseNameRequired = $state(false);
	let nativeDocketRequired = $state(false);
	let caseNameRequired = $derived(nativeCaseNameRequired || form?.caseNameRequired === true);
	let docketRequired = $derived(nativeDocketRequired || form?.docketRequired === true);

	async function focusFirstRequired() {
		await tick();
		if (caseNameRequired) caseNameInput?.focus();
		else if (docketRequired) docketNumberInput?.focus();
	}

	function handleCaseInvalid(event: Event) {
		event.preventDefault();
		const formElement = (event.currentTarget as HTMLInputElement).form;
		nativeCaseNameRequired = !(formElement?.elements.namedItem('case_name') as HTMLInputElement)?.validity.valid;
		nativeDocketRequired = !(formElement?.elements.namedItem('docket_number') as HTMLInputElement)?.validity.valid;
		void focusFirstRequired();
	}

	// Format ISO date string for display — identical to list page formatDate.
	function formatDate(iso: string): string {
		try {
			const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
			return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return iso;
		}
	}

	// Format ISO timestamp string with date + time — used by Status history rows only.
	function formatDateTime(iso: string): string {
		try {
			return new Date(iso).toLocaleString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
				hour: 'numeric',
				minute: '2-digit',
			});
		} catch {
			return iso;
		}
	}

	// StatusBadge helpers — reads argument.status enum (Phase 26: pipeline/draft/published/unpublished).
	function badgeStyle(status: string): string {
		let color: string;
		if (status === 'published') {
			color = '#4ade80';
		} else if (status === 'draft') {
			color = '#a78bfa';
		} else if (status === 'unpublished') {
			color = '#fb923c';
		} else {
			// candidate (Phase 48 D-01) and any unrecognised value share the
			// retired born state's grey token — Phase 51 owns the palette.
			color = '#94a3b8';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
	}

	function badgeLabel(status: string): string {
		if (status === 'published') return 'Published';
		if (status === 'draft') return 'Draft';
		if (status === 'unpublished') return 'Unpublished';
		// candidate (Phase 48 D-01) and any unrecognised value get the born
		// state's own label rather than the retired 'Pipeline' one.
		return 'Candidate';
	}

	// Blocked-publish blocker-code -> operator-readable sentence (Phase 48 D-19).
	// A bare tier name gives the operator nothing to act on; each sentence names
	// what dragged the tier down, with a count, so they know what to fix. An
	// unrecognised code (a future blocker added server-side) falls back to
	// naming the raw code rather than vanishing silently.
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

	// Speakers section — per-participant save state keyed by participant_id.
	let savingSpeakerId = $state<number | null>(null);

	// Published lock (D-35): "If an argument is currently published, the
	// data for that argument is locked." api/services/admin_arguments.py's
	// update_participant_side (Task 2 of this plan) is the AUTHORITY — this
	// flag exists only so the operator is never offered a control that will
	// be refused. Uses the same `data.argument.status === 'published'`
	// idiom already used below at the Danger Zone / unpublish branch.
	const speakersLocked = data.argument.status === 'published';

	// Per-row side state, keyed by participant_id (T-26-14, AEDIT-06). Every
	// speaker row seeds its own side state now (G-49-3/D-35, plan 49-10) —
	// bench rows are no longer filtered out, since the converged control
	// below reaches BENCH too. Non-standard sides (UNKNOWN, legacy ADVOCATE)
	// collapse to the 'UNKNOWN' sentinel so an unresolved row shows the
	// explicit placeholder rather than the browser silently defaulting to
	// the first option. Because the page reloads via redirect(303) after a
	// successful save, this seed is refreshed on each successful load.
	const VALID_SIDES = new Set(['BENCH', 'PETITIONER', 'RESPONDENT', 'AMICUS']);
	let speakerSideById = $state<Record<number, string>>(
		Object.fromEntries(
			(data.argument.speakers ?? [])
				.map((s) => [s.participant_id, VALID_SIDES.has(s.side) ? s.side : 'UNKNOWN'])
		)
	);

	// Boundary-crossing confirm state (G-49-3/D-35, plan 49-10 Task 3),
	// keyed by participant_id. Purpose-port of the Resolve card's side gate
	// (needsSideGate/confirmSide) — not a copy of its mechanism, because
	// this surface has no person picker to gate and each row is its own
	// POST rather than a batch form. A change that crosses the Bench<->
	// Advocate boundary (crossesSideBoundary, $lib/participantSide) needs
	// an explicit second click; a change among specific advocate roles
	// (or resolving UNKNOWN to one) does not.
	let sideConfirming = $state<Record<number, boolean>>({});

	// Danger Zone delete state (ADMIN-01).
	// Two-step confirm: first click sets deleteConfirming = true; second click submits form.
	// Pitfall 7: $effect resets state when argument id changes (SvelteKit soft nav reuses component).
	let deleteConfirming = $state(false);
	let deleteSubmitting = $state(false);

	$effect(() => {
		// Reference data.argument.id so this effect re-runs on soft navigation to a different argument.
		data.argument.id;
		deleteConfirming = false;
		deleteSubmitting = false;
		// Pitfall 7 (plan 49-10): the side-boundary confirm state must reset
		// on soft navigation too, same reason as the Danger Zone's own reset.
		sideConfirming = {};
	});
</script>

<svelte:head>
	<title>{data.argument.case_name} — SCOTUS Chat Admin</title>
</svelte:head>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header
		style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;"
	>
		<!-- Back navigation per UI-SPEC -->
		<a
			href="/admin/arguments"
			style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none; display: block; margin-bottom: 8px;"
		>← Arguments</a>
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			{data.argument.case_name}
		</h1>
	</header>

	<div style="max-width: 640px; margin: 0 auto; padding: 48px 24px;">

		<!-- D-35a: whole-argument lock notice (operator, 2026-08-24). Stated ONCE,
		     at page level, covering the Case card and the Argument Details card
		     together — card-agnostic on purpose, since under D-35a both cards are
		     inside the same lock. 49-09's Speakers-card line stays where it is
		     (it names a control-specific remedy); this notice does not replace it. -->
		{#if speakersLocked}
			<p
				role="status"
				style="
					font-size: 14px;
					font-weight: 400;
					color: #94a3b8;
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 16px;
					margin: 0 0 16px 0;
				"
			>
				This argument is published, so its data is read-only. Unpublish it in the
				Status card below to edit the case, argument details, or speakers.
			</p>
		{/if}

		<!-- Card 1: Case — case title + Case docket number + consolidated dockets (D-03) -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 24px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 24px 0;">
				Case
			</h2>

			<form
				method="POST"
				action="?/save"
				use:enhance={() => {
					nativeCaseNameRequired = false;
					nativeDocketRequired = false;
					savingState = true;
					return async ({ update }) => {
						savingState = false;
						await update();
						await tick();
						if (form?.caseNameRequired || form?.docketRequired) await focusFirstRequired();
					};
				}}
			>
				<!-- Case title field -->
				<div style="margin-bottom: 16px;">
					<label
						for="case_name"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Case title</label>
					<input
						bind:this={caseNameInput}
						type="text"
						id="case_name"
						name="case_name"
						value={form && 'case_name' in form ? form.case_name : data.argument.case_name}
						required
						disabled={speakersLocked}
						oninvalid={handleCaseInvalid}
						aria-invalid={caseNameRequired ? 'true' : undefined}
						aria-describedby={caseNameRequired ? 'case-form-alert' : undefined}
						style="
							display: block;
							width: 100%;
							background-color: #0f1117;
							border: 1px solid {caseNameRequired ? '#ef4444' : '#334155'};
							border-radius: 6px;
							padding: 8px 12px;
							font-size: 16px;
							color: #e2e8f0;
							box-sizing: border-box;
						"
					/>
				</div>

				<!-- Case docket number field — plain text per Date Format Contract (NOT a date input) -->
				<!-- D-01/D-02: labeled "Case docket number" to disambiguate Case.docket_number
				     from the source_dockets pill field in the ArgumentDetailsCard immediately below. -->
				<div style="margin-bottom: {data.argument.consolidated_dockets.length > 0 ? '16px' : '0'};">
					<label
						for="docket_number"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Case docket number</label>
					<input
						bind:this={docketNumberInput}
						type="text"
						id="docket_number"
						name="docket_number"
						value={form && 'docket_number' in form ? form.docket_number : data.argument.docket_number}
						required
						disabled={speakersLocked}
						oninvalid={handleCaseInvalid}
						aria-invalid={docketRequired ? 'true' : undefined}
						aria-describedby={docketRequired ? 'case-form-alert' : undefined}
						style="
							display: block;
							width: 100%;
							background-color: #0f1117;
							border: 1px solid {docketRequired ? '#ef4444' : '#334155'};
							border-radius: 6px;
							padding: 8px 12px;
							font-size: 16px;
							color: #e2e8f0;
							box-sizing: border-box;
						"
					/>
				</div>

				<!-- Consolidated dockets — read-only, shown only when more than one case (D-10) -->
				{#if data.argument.consolidated_dockets.length > 0}
					<div style="margin-bottom: 0;">
						<p
							style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 8px 0;"
						>Consolidated dockets</p>
						<ul style="margin: 0; padding-left: 20px;">
							{#each data.argument.consolidated_dockets as docket}
								<li style="font-size: 14px; color: #94a3b8; padding: 2px 0;">
									{docket.docket_number}
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<!-- Form-level error slot — role=alert for screen reader announcement (WCAG).
				     `form` is shared across every action on this page. `?/save` is the
				     ONLY action that owns this slot and it returns an untagged `error`
				     (no `source` key) — so this card renders `form?.error` only when
				     `form.source` is absent. A positive test (`!form.source`) rather than
				     a growing negative list (`!== 'publish' && !== 'unpublish' && ...`)
				     is deliberate: it stays correct if a future action is added without
				     anyone having to remember to extend this exclusion. Publish and
				     unpublish errors are tagged `source: 'publish'` / `source: 'unpublish'`
				     and rendered in the Status card instead, next to their own controls,
				     where the operator is actually looking. -->
				{#if caseNameRequired || docketRequired || (form?.error && !form.source)}
					<p
						id="case-form-alert"
						role="alert"
						style="
							color: #ef4444;
							font-size: 16px;
							font-weight: 400;
							line-height: 1.5;
							margin: 16px 0 0 0;
						"
					>
						{#if caseNameRequired}<span style="display: block;">Case name is required.</span>{/if}
						{#if docketRequired}<span style="display: block;">Add at least one docket.</span>{/if}
						{#if form?.error && !form.source}<span style="display: block;">{form.error}</span>{/if}
					</p>
				{/if}

				<!-- Save changes button — full-width, accent border, 44px min-height.
				     D-35a: disabled under speakersLocked too, ADDED to the pre-existing
				     submitting-state condition, never substituted for it. -->
				<button
					type="submit"
					disabled={speakersLocked || savingState}
					style="
						display: block;
						width: 100%;
						min-height: 44px;
						background-color: #1e293b;
						border: 1px solid #93c5fd;
						border-radius: 6px;
						font-size: 16px;
						font-weight: 600;
						color: #e2e8f0;
						cursor: {(speakersLocked || savingState) ? 'not-allowed' : 'pointer'};
						margin-top: 24px;
						opacity: {(speakersLocked || savingState) ? 0.7 : 1};
					"
				>
					{savingState ? 'Saving…' : 'Save changes'}
				</button>
			</form>
		</div>

		<!-- Card 1b: Argument Details — shared ArgumentDetailsCard, second consumer (AEDIT-04) -->
		<!-- Owns its own card chrome (24px bottom margin baked in) — not wrapped in an extra div. -->
		<!-- D-35/D-35a (operator, 2026-08-24): REVERSES the prior decision recorded
		     at this call site, which held that this card's fields stay editable
		     no matter the argument's publish status. The operator's D-35 rule
		     ("if an argument is currently published, the data for that argument
		     is locked") was answered, on 2026-08-24, as applying to the WHOLE
		     argument — the Case card and this card too, not participant data
		     alone. This is a deliberate, visible reversal, not a silent flip: the
		     previously-hardcoded editable prop below is replaced with 49-09's
		     single published-lock flag (speakersLocked), the SAME flag the
		     Speakers card already consults. The server-side guards on both
		     argument-data writers (api/services/admin_arguments.py::
		     update_argument / update_argument_metadata) are the authority while
		     this flag exists — it exists only so the operator is never offered
		     a control that will be refused. -->
		<ArgumentDetailsCard
			savedValues={data.savedValues}
			hints={data.hints}
			action="?/saveArgumentDetails"
			readonly={speakersLocked}
			{form}
		/>

		<!-- Card 2: Status — current badge + resolved/published dates + slug preview -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">
				Status
			</h2>

			<div style="margin-bottom: 12px;">
				<span style={badgeStyle(data.argument.status ?? 'candidate')}>
					{badgeLabel(data.argument.status ?? 'candidate')}
				</span>
			</div>

			{#if data.argument.resolved_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					<!-- formatDateTime (not formatDate) — matches the Status History
					     list further down this same card, which already shows times.
					     Label: `Argument` has no creation-timestamp column (see
					     .planning/todos/pending/2026-08-20-argument-status-card-labels-resolved-at-as-created.md).
					     This value is when the resolve pipeline step completed, not
					     when the argument was created — labelled "Resolved" so it
					     states what it actually is. The Status History list further
					     down this same card already carries the authoritative birth
					     record (every writer has logged a birth transition since
					     plan 48-05), so no second, differently-sourced date is added
					     here. -->
					Resolved {formatDateTime(data.argument.resolved_at)}
				</p>
			{/if}

			{#if data.argument.published_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					<!-- D-02 retains published_at after unpublish for the audit trail;
					     once status stopped being the sole visibility authority (48-10),
					     the bare "Published" label became misleading for an argument
					     that is no longer publicly visible. formatDateTime (not
					     formatDate) for the same reason as the Created row above. -->
					{data.argument.status === 'published' ? 'Published' : 'Last published'} {formatDateTime(data.argument.published_at)}
				</p>
			{/if}

			<p style="font-size: 14px; color: #94a3b8; margin: 0 0 16px 0;">
				Slug: {data.argument.slug}
			</p>

			<!-- Publish/Unpublish control lives with the Status card (D-07 layout simplification) -->
			{#if data.argument.status === 'draft' || data.argument.status === 'unpublished'}
				<form
					method="POST"
					action="?/publish"
					use:enhance={() => {
						publishingState = true;
						return async ({ update }) => {
							publishingState = false;
							await update();
						};
					}}
				>
					<button
						type="submit"
						disabled={publishingState}
						style="
							display: block;
							width: 100%;
							min-height: 44px;
							background-color: #1e293b;
							border: 1px solid #93c5fd;
							border-radius: 6px;
							font-size: 16px;
							font-weight: 600;
							color: #e2e8f0;
							cursor: {publishingState ? 'not-allowed' : 'pointer'};
							opacity: {publishingState ? 0.7 : 1};
						"
					>
						{publishingState ? 'Publishing…' : 'Publish'}
					</button>
				</form>

				<!-- Blocked-publish panel (Phase 48 D-19/D-20): the operator's explicit
				     requirement is that this names WHAT dragged the tier down, with a
				     count, not a bare tier name — that gives them nothing to act on. -->
				{#if form?.publishBlocked}
					<div
						style="
							margin-top: 16px;
							padding: 16px;
							border: 1px solid #fb923c;
							border-radius: 6px;
							background-color: #1e293b;
						"
					>
						<p style="font-size: 16px; font-weight: 600; color: #fb923c; margin: 0 0 8px 0;">
							Publish blocked
							{#if form.trustTier}
								<span
									style="border: 1px solid #94a3b8; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: #94a3b8; display: inline-block;"
								>{form.trustTier}</span>
							{/if}
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

						{#if form?.overrideReasonRequired}
							<p role="alert" style="font-size: 14px; font-weight: 600; color: #ef4444; margin: 0 0 12px 0;">
								A non-empty reason is required — your submission was blank or only whitespace.
							</p>
						{/if}

						<form
							method="POST"
							action="?/publish"
							use:enhance={() => {
								publishingState = true;
								return async ({ update }) => {
									publishingState = false;
									await update();
								};
							}}
						>
							<label
								for="override_reason"
								style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
							>Reason for publishing anyway</label>
							<!-- `required` is defense-in-depth only (D-17) — the server's own
							     .strip() check on override_reason is the single authority;
							     a whitespace-only submission is still rejected server-side. -->
							<textarea
								id="override_reason"
								name="override_reason"
								required
								rows="3"
								style="
									display: block;
									width: 100%;
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
								disabled={publishingState}
								style="
									display: block;
									width: 100%;
									min-height: 44px;
									background-color: #1e293b;
									border: 1px solid #fb923c;
									border-radius: 6px;
									font-size: 16px;
									font-weight: 600;
									color: #e2e8f0;
									cursor: {publishingState ? 'not-allowed' : 'pointer'};
									opacity: {publishingState ? 0.7 : 1};
								"
							>
								{publishingState ? 'Publishing…' : 'Publish anyway with this reason'}
							</button>
						</form>
					</div>
				{/if}
			{:else if data.argument.status === 'published'}
				<form
					method="POST"
					action="?/unpublish"
					use:enhance={() => {
						unpublishingState = true;
						return async ({ update }) => {
							unpublishingState = false;
							await update();
						};
					}}
				>
					<button
						type="submit"
						disabled={unpublishingState}
						style="
							display: block;
							width: 100%;
							min-height: 44px;
							background-color: #1e293b;
							border: 1px solid #334155;
							border-radius: 6px;
							font-size: 16px;
							font-weight: 600;
							color: #e2e8f0;
							cursor: {unpublishingState ? 'not-allowed' : 'pointer'};
							opacity: {unpublishingState ? 0.7 : 1};
						"
					>
						{unpublishingState ? 'Unpublishing…' : 'Unpublish'}
					</button>
				</form>
			{/if}

			<!-- Non-overridable publish/unpublish error (resolve-incomplete gate,
			     the already-published guard, or an unpublish failure, D-14): the
			     server returns a plain-string `error` with no `publishBlocked` flag
			     for any of these, so NO reason field is offered here — neither gate
			     is overridable. Placed AFTER the draft/unpublished-vs-published
			     branch above (not inside either arm) because it must render next to
			     whichever control — Publish or Unpublish — is actually visible for
			     the argument's current status; a publish error can only occur while
			     the Publish button is shown, and an unpublish error only while the
			     Unpublish button is shown, but the guard itself doesn't need to
			     duplicate that branching. Guarded by `form.source` being either tag
			     so it never renders for an unrelated action's error on this shared
			     `form` prop, and never renders in the case-metadata card's alert
			     slot, which is where both messages were previously and silently
			     discarded. -->
			{#if form?.error && (form.source === 'publish' || form.source === 'unpublish') && !form.publishBlocked}
				<p
					role="alert"
					style="
						color: #ef4444;
						font-size: 14px;
						font-weight: 400;
						line-height: 1.5;
						margin: 12px 0 0 0;
					"
				>{form.error}</p>
			{/if}
		</div>

		<!-- Card 2b: Status history — full timestamped log, oldest first (AEDIT-02) -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">
				Status history
			</h2>

			{#if data.argument.status_log && data.argument.status_log.length > 0}
				{#each data.argument.status_log as entry, index}
					<div style="padding: 8px 0;">
						<div style="display: flex; align-items: center; gap: 8px;">
							<span style={badgeStyle(entry.status)}>
								{index === 0 && entry.status === 'draft' ? 'Created' : badgeLabel(entry.status)}
							</span>
							<span style="font-size: 14px; color: #94a3b8;">
								— {formatDateTime(entry.created_at)}
							</span>
						</div>
						<!-- A logged override nobody can read is not an audit trail (Phase 48 D-15). -->
						{#if entry.override_reason}
							<p style="font-size: 14px; color: #e2e8f0; margin: 4px 0 0 0;">
								Override reason: "{entry.override_reason}"
								{#if entry.trust_tier_at_transition}
									(tier at the time: {entry.trust_tier_at_transition})
								{/if}
							</p>
						{/if}
					</div>
				{/each}
			{:else}
				<p style="font-size: 14px; color: #94a3b8; font-style: italic; margin: 0;">
					Status history is unavailable.
				</p>
			{/if}
		</div>

		<!-- Card 3: Speakers — unified bench+advocate rows (D-05, D-07, AEDIT-05/06/07) -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">
				Speakers
			</h2>
			<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 24px 0;">
				All participants in this argument. Advocates: set the role and descriptor they held here. Changing a role or descriptor here does not affect other arguments.
			</p>

			{#if speakersLocked}
				<!-- D-35: card-level lock notice, applies identically to bench and advocate
				     rows below — no per-class difference in treatment (CLAUDE.md apolitical
				     constraint). Defence in depth: api/services/admin_arguments.py's
				     update_participant_side published guard is the authority. -->
				<p style="font-size: 14px; font-weight: 400; color: #fbbf24; margin: 0 0 16px 0;">
					This argument is published, so participant data is read-only. Unpublish it first to edit roles or descriptors.
				</p>
			{/if}

			{#if data.argument.speakers && data.argument.speakers.length > 0}
				<table style="width: 100%; border-collapse: collapse;">
					<thead>
						<tr style="border-bottom: 1px solid #334155;">
							<th style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px; white-space: nowrap;">Name</th>
							<th style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px;">Role</th>
							<th style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px;">Title</th>
							<th style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px; white-space: nowrap;">Utterances</th>
							<th style="text-align: left; font-size: 14px; font-weight: 400; color: #94a3b8; padding: 8px;">Action</th>
						</tr>
					</thead>
					<tbody>
						{#each data.argument.speakers as speaker}
							<tr style="border-bottom: 1px solid #334155;">
								<td style="padding: 8px; font-size: 14px; color: #e2e8f0; vertical-align: top;">
									{speaker.full_name ?? '—'}
								</td>
								<!-- G-49-3/D-35 (plan 49-10): ONE row template serves bench and advocate —
								     the previous per-class branch on the row's stored bench flag is
								     deliberately removed so the two classes of speaker cannot diverge in
								     affordance depth (CLAUDE.md
								     apolitical constraint). The bench companion below follows the
								     operator's CURRENT selection (speakerSideById), not the stored
								     is_bench, so it appears the instant Bench is picked rather than only
								     after save — the companion should follow what the operator is
								     choosing, not what was last saved. The confirm gate is the
								     purpose-port of ResolveCard's side gate (needsSideGate/confirmSide) —
								     not a copy of its mechanism, because this surface has no person
								     picker to gate and each row is its own POST, not a batch form. -->
								<td colspan="3" style="padding: 8px; vertical-align: top;">
									<form
										method="POST"
										action="?/updateParticipantSide"
										use:enhance={() => {
											savingSpeakerId = speaker.participant_id;
											return async ({ update }) => {
												savingSpeakerId = null;
												await update();
											};
										}}
										style="display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap;"
									>
										<input type="hidden" name="participant_id" value={speaker.participant_id} />
										<!-- RESOLVE-13 round-trip guard (plan 49-10): tells the server action
										     whether this row's stored side was BENCH, so it can omit the
										     descriptor key rather than submit a blank value that would clobber
										     the preserved-but-hidden stored descriptor. -->
										<input type="hidden" name="committed_side" value={speaker.side} />
										<div style="flex: 1; min-width: 160px;">
											<select
												name="side"
												disabled={speakersLocked}
												bind:value={speakerSideById[speaker.participant_id]}
												onchange={() => { sideConfirming[speaker.participant_id] = false; }}
												style="
													width: 100%;
													background-color: #0f1117;
													border: 1px solid #334155;
													border-radius: 6px;
													padding: 8px 12px;
													font-size: 16px;
													font-weight: 400;
													color: #e2e8f0;
													min-height: 36px;
													cursor: {speakersLocked ? 'not-allowed' : 'auto'};
													opacity: {speakersLocked ? 0.7 : 1};
												"
											>
												<option value="UNKNOWN">Unresolved — choose a role</option>
												<option value="BENCH">{SIDE_LABEL.BENCH}</option>
												<option value="PETITIONER">{SIDE_LABEL.PETITIONER}</option>
												<option value="RESPONDENT">{SIDE_LABEL.RESPONDENT}</option>
												<option value="AMICUS">{SIDE_LABEL.AMICUS}</option>
											</select>
											{#if speakerSideById[speaker.participant_id] === 'BENCH'}
												<!-- Bench companion (T-49-10-strand): three distinct states, keyed
												     on person_id FIRST — not on missing_tenure — so a bench row
												     with NO linked person is never confused with one whose person
												     merely lacks covering tenure. Before this task a null-person
												     bench row rendered a bare em-dash with no warning and no link;
												     that one-way trap becomes reachable by operator action once a
												     row can be moved into Bench, so it is closed here. -->
												<div style="margin: 4px 0 0 0; font-size: 14px;">
													{#if speaker.person_id == null}
														<span style="color: #94a3b8;">No person linked</span>
													{:else if speaker.missing_tenure}
														<span style="color: #fbbf24;">Missing tenure</span>
														{#if speaker.person_edit_href}
															<a
																href={speaker.person_edit_href}
																style="color: #93c5fd; text-decoration: underline; margin-left: 4px;"
															>Edit person</a>
														{/if}
													{:else}
														<span style="color: #e2e8f0;">{speaker.bench_role ?? '—'}</span>
													{/if}
												</div>
											{/if}
										</div>
										<div style="flex: 1; min-width: 160px;">
											<!-- Descriptor stays MOUNTED (never wrapped in a bench-only {#if}) and
											     is only DISABLED while the selected side is Bench — unmounting it
											     would destroy a typed-but-unsaved value on a toggle, the defect
											     ResolveCard.svelte's lastDescriptorValue (:155-165) exists to
											     prevent, avoided here by construction instead of a second
											     remembering mechanism. -->
											<input
												type="text"
												name="descriptor"
												disabled={speakersLocked || speakerSideById[speaker.participant_id] === 'BENCH'}
												value={speaker.descriptor ?? ''}
												style="
													display: block;
													width: 100%;
													background-color: #0f1117;
													border: 1px solid #334155;
													border-radius: 6px;
													padding: 8px 12px;
													font-size: 16px;
													color: #e2e8f0;
													box-sizing: border-box;
													min-height: 36px;
													cursor: {speakersLocked || speakerSideById[speaker.participant_id] === 'BENCH' ? 'not-allowed' : 'auto'};
													opacity: {speakersLocked || speakerSideById[speaker.participant_id] === 'BENCH' ? 0.7 : 1};
												"
											/>
											<div
												style="
													margin: 4px 0 0 0;
												"
											>
												<!-- Phase 38 (D-19/D-20): descriptor_hint has no independently stored
												     raw/confidence (admin_arguments.py D-06 — descriptor and descriptor_hint
												     source the same column), so the exact extracted text itself is
												     the raw source and confidence uses an explicit qualitative
												     fallback rather than a fabricated figure. Kept rendered even while
												     Bench is selected — copying is a read, not a write. -->
												<CopyableExtractedValue
													value={speaker.descriptor_hint}
													copyLabel="Copy descriptor"
													confidence="Medium"
													raw={speaker.descriptor_hint}
												/>
											</div>
										</div>
										<div style="white-space: nowrap; padding-top: 6px; font-size: 14px; color: #94a3b8;">
											{speaker.utterance_count}
										</div>
										{#if crossesSideBoundary(sideBucket(speaker.side), speakerSideById[speaker.participant_id])}
											{#if sideConfirming[speaker.participant_id]}
												<div style="display: flex; gap: 8px;">
													<button
														type="submit"
														disabled={speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN'}
														style="
															min-height: 36px;
															padding: 8px 16px;
															background-color: #1e293b;
															border: 1px solid #93c5fd;
															border-radius: 6px;
															font-size: 14px;
															font-weight: 400;
															color: #e2e8f0;
															cursor: {speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN' ? 'not-allowed' : 'pointer'};
															opacity: {speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN' ? 0.7 : 1};
															white-space: nowrap;
														"
													>
														{savingSpeakerId === speaker.participant_id ? 'Saving…' : 'Confirm move'}
													</button>
													<button
														type="button"
														onclick={() => { sideConfirming[speaker.participant_id] = false; }}
														style="
															min-height: 36px;
															padding: 8px 16px;
															background: transparent;
															border: 1px solid #334155;
															border-radius: 6px;
															font-size: 14px;
															font-weight: 400;
															color: #94a3b8;
															cursor: pointer;
															white-space: nowrap;
														"
													>
														Cancel
													</button>
												</div>
											{:else}
												<button
													type="button"
													disabled={speakersLocked}
													onclick={() => { sideConfirming[speaker.participant_id] = true; }}
													style="
														min-height: 36px;
														padding: 8px 16px;
														background-color: #1e293b;
														border: 1px solid #93c5fd;
														border-radius: 6px;
														font-size: 14px;
														font-weight: 400;
														color: #e2e8f0;
														cursor: {speakersLocked ? 'not-allowed' : 'pointer'};
														opacity: {speakersLocked ? 0.7 : 1};
														white-space: nowrap;
													"
												>
													Move to {SIDE_LABEL[speakerSideById[speaker.participant_id]]}
												</button>
											{/if}
										{:else}
											<button
												type="submit"
												disabled={speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN'}
												style="
													min-height: 36px;
													padding: 8px 16px;
													background-color: #1e293b;
													border: 1px solid #93c5fd;
													border-radius: 6px;
													font-size: 14px;
													font-weight: 400;
													color: #e2e8f0;
													cursor: {speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN' ? 'not-allowed' : 'pointer'};
													opacity: {speakersLocked || savingSpeakerId === speaker.participant_id || speakerSideById[speaker.participant_id] === 'UNKNOWN' ? 0.7 : 1};
													white-space: nowrap;
												"
											>
												{savingSpeakerId === speaker.participant_id ? 'Saving…' : 'Save'}
											</button>
										{/if}
									</form>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>

				<!-- Role error message (shown on form.roleError) -->
				{#if form?.roleError}
					<p
						role="alert"
						style="
							color: #ef4444;
							font-size: 14px;
							font-weight: 400;
							margin: 8px 0 0 0;
						"
					>{form.roleError}</p>
				{/if}
			{:else}
				<p style="font-size: 14px; color: #94a3b8; margin: 0;">
					No speakers recorded for this argument.
				</p>
			{/if}
		</div>

		<!-- Danger Zone — argument delete section (ADMIN-01, D-03) -->
		<!-- Last card on the page per UI-SPEC Layout Contract (delete section position). -->
		<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px; margin-top: 16px;">
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
				Danger Zone
			</h2>

			{#if data.can_delete}
				{#if deleteConfirming}
					<!-- State 2: Two-button row — replaces delete button in-place (D-02) -->
					<!-- No layout shift; same row height as the initial button. -->
					<div style="display: flex; gap: 8px;">
						<form
							method="POST"
							action="?/delete"
							style="flex: 1;"
							use:enhance={() => {
								deleteSubmitting = true;
								return async ({ update }) => {
									deleteSubmitting = false;
									await update();
								};
							}}
						>
							<button
								type="submit"
								disabled={deleteSubmitting}
								style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #ef4444; border-radius: 6px; font-size: 16px; font-weight: 600; color: #ef4444; cursor: {deleteSubmitting ? 'not-allowed' : 'pointer'}; opacity: {deleteSubmitting ? 0.7 : 1};"
							>
								{deleteSubmitting ? 'Deleting…' : 'Confirm delete'}
							</button>
						</form>
						<button
							type="button"
							onclick={() => { deleteConfirming = false; }}
							style="flex: 1; min-height: 44px; background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px; font-weight: 400; color: #94a3b8; cursor: pointer;"
						>
							Cancel
						</button>
					</div>
				{:else}
					<!-- State 1: Initial delete button — first click sets deleteConfirming (no submit) -->
					<button
						type="button"
						onclick={() => { deleteConfirming = true; }}
						style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #ef4444; border-radius: 6px; font-size: 16px; font-weight: 600; color: #ef4444; cursor: pointer;"
					>
						Delete argument
					</button>
				{/if}

				<!-- Delete error (returned by fail() from the delete action) -->
				{#if form?.deleteError}
					<p
						role="alert"
						style="color: #ef4444; font-size: 14px; font-weight: 400; margin: 8px 0 0 0;"
					>{form.deleteError}</p>
				{/if}
			{:else}
				<!-- Blocked state — argument is published; disable button + tooltip (D-04, T-21-01-PUB) -->
				<button
					disabled
					aria-describedby="delete-tip"
					style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #334155; border-radius: 6px; font-size: 16px; font-weight: 600; color: #94a3b8; cursor: not-allowed; opacity: 0.7;"
				>
					Delete argument
				</button>
				<p
					id="delete-tip"
					style="font-size: 14px; color: #94a3b8; margin-top: 8px; text-align: center;"
				>
					Published and unpublished arguments cannot be deleted. Only drafts can be removed.
				</p>
			{/if}
		</div>

	</div>
</main>
