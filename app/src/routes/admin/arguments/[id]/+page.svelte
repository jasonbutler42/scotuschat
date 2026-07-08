<script lang="ts">
	import { enhance } from '$app/forms';

	let { data, form } = $props();

	// Submitting state per named action.
	let savingState = $state(false);
	let publishingState = $state(false);
	let unpublishingState = $state(false);

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
			color = '#94a3b8';
		}
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
	}

	function badgeLabel(status: string): string {
		if (status === 'published') return 'Published';
		if (status === 'draft') return 'Draft';
		if (status === 'unpublished') return 'Unpublished';
		return 'Pipeline';
	}

	// Speakers section — per-participant save state keyed by participant_id.
	let savingSpeakerId = $state<number | null>(null);

	// Convert ISO timestamp or date string to value compatible with <input type="date"> (YYYY-MM-DD).
	function toDateInputValue(iso: string | null): string {
		if (!iso) return '';
		// Take only the date portion (first 10 chars of ISO 8601)
		return iso.slice(0, 10);
	}

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

		<!-- Card 1: Argument Details — save form -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 24px;
				margin-bottom: 16px;
			"
		>
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 24px 0;">
				Argument Details
			</h2>

			<form
				method="POST"
				action="?/save"
				use:enhance={() => {
					savingState = true;
					return async ({ update }) => {
						savingState = false;
						await update();
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
						type="text"
						id="case_name"
						name="case_name"
						value={data.argument.case_name}
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
						"
					/>
				</div>

				<!-- Docket number field — plain text per Date Format Contract (NOT a date input) -->
				<div style="margin-bottom: 16px;">
					<label
						for="docket_number"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Docket number</label>
					<input
						type="text"
						id="docket_number"
						name="docket_number"
						value={data.argument.docket_number}
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
						"
					/>
				</div>

				<!-- Argued date field — date input per Date Format Contract -->
				<div style="margin-bottom: {data.argument.consolidated_dockets.length > 0 ? '16px' : '0'};">
					<label
						for="argued_date"
						style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 8px;"
					>Argued date</label>
					<input
						type="date"
						id="argued_date"
						name="argued_date"
						value={toDateInputValue(data.argument.argued_date)}
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

				<!-- Form-level error slot — role=alert for screen reader announcement (WCAG) -->
				{#if form?.error}
					<p
						role="alert"
						style="
							color: #ef4444;
							font-size: 16px;
							font-weight: 400;
							line-height: 1.5;
							margin: 16px 0 0 0;
						"
					>{form.error}</p>
				{/if}

				<!-- Save changes button — full-width, accent border, 44px min-height -->
				<button
					type="submit"
					disabled={savingState}
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
						cursor: {savingState ? 'not-allowed' : 'pointer'};
						margin-top: 24px;
						opacity: {savingState ? 0.7 : 1};
					"
				>
					{savingState ? 'Saving…' : 'Save changes'}
				</button>
			</form>
		</div>

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
				<span style={badgeStyle(data.argument.status ?? 'pipeline')}>
					{badgeLabel(data.argument.status ?? 'pipeline')}
				</span>
			</div>

			{#if data.argument.resolved_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					Created {formatDate(data.argument.resolved_at)}
				</p>
			{/if}

			{#if data.argument.published_at}
				<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
					Published {formatDate(data.argument.published_at)}
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
					<div style="padding: 8px 0; display: flex; align-items: center; gap: 8px;">
						<span style={badgeStyle(entry.status)}>
							{index === 0 && entry.status === 'draft' ? 'Created' : badgeLabel(entry.status)}
						</span>
						<span style="font-size: 14px; color: #94a3b8;">
							— {formatDateTime(entry.created_at)}
						</span>
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
				All participants in this argument. Advocates: set the role and title they held here. Changing a role or title here does not affect other arguments.
			</p>

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
								{#if !speaker.is_bench}
									<!-- Advocate row: single form spans Role + Title + Save (D-04) -->
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
											<div style="flex: 1; min-width: 160px;">
												<select
													name="side"
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
													"
												>
													<option value="PETITIONER" selected={speaker.side === 'PETITIONER'}>Petitioner's Counsel</option>
													<option value="RESPONDENT" selected={speaker.side === 'RESPONDENT'}>Respondent's Counsel</option>
													<option value="AMICUS" selected={speaker.side === 'AMICUS'}>Amicus Curiae</option>
												</select>
											</div>
											<div style="flex: 1; min-width: 160px;">
												<input
													type="text"
													name="title"
													value={speaker.title ?? ''}
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
													"
												/>
												<p
													style="
														font-size: 14px;
														font-weight: 400;
														color: #94a3b8;
														margin: 4px 0 0 0;
														{!speaker.title_hint ? 'font-style: italic;' : ''}
													"
												>
													Extracted: {speaker.title_hint ?? 'N/A'}
												</p>
											</div>
											<div style="white-space: nowrap; padding-top: 6px; font-size: 14px; color: #94a3b8;">
												{speaker.utterance_count}
											</div>
											<button
												type="submit"
												disabled={savingSpeakerId === speaker.participant_id}
												style="
													min-height: 36px;
													padding: 8px 16px;
													background-color: #1e293b;
													border: 1px solid #93c5fd;
													border-radius: 6px;
													font-size: 14px;
													font-weight: 400;
													color: #e2e8f0;
													cursor: {savingSpeakerId === speaker.participant_id ? 'not-allowed' : 'pointer'};
													opacity: {savingSpeakerId === speaker.participant_id ? 0.7 : 1};
													white-space: nowrap;
												"
											>
												{savingSpeakerId === speaker.participant_id ? 'Saving…' : 'Save'}
											</button>
										</form>
									</td>
								{:else}
									<!-- Bench row: read-only tenure-derived role or missing-tenure warning -->
									<td style="padding: 8px; font-size: 14px; vertical-align: top;">
										{#if speaker.missing_tenure}
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
									</td>
									<td style="padding: 8px; font-size: 14px; color: #94a3b8; vertical-align: top;">—</td>
									<td style="padding: 8px; font-size: 14px; color: #94a3b8; vertical-align: top; white-space: nowrap;">
										{speaker.utterance_count}
									</td>
									<td style="padding: 8px; font-size: 14px; color: #94a3b8; vertical-align: top;">—</td>
								{/if}
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
