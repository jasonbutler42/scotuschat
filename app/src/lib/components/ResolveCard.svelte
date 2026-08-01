<script lang="ts">
	import { enhance } from '$app/forms';
	import CopyableExtractedValue from '$lib/components/CopyableExtractedValue.svelte';
	import CreatePersonPopover from '$lib/components/CreatePersonPopover.svelte';

	// Phase 25 — Restructured Resolve card (D-10 through D-19, D-21, PJOB-14 through PJOB-19, PJOB-21).
	// Phase 44 (RESOLVE-01/D-03/D-04) — five-column rework: the Action column is deleted and
	// its two person-matching buttons fold into a single combobox entry point inside Resolved
	// As; Descriptor (renamed from Title, Phase 44 Plan 01) now always renders instead of
	// disappearing for bench/gated rows.
	// Locked column order: Raw Label, Resolved As, Bench/Advocate, Argument Role, Descriptor.
	//
	// Two backend data sources are merged by raw_speaker_label:
	//  - resolveRows (GET .../resolve-rows, Plan 25-02): the authoritative side/descriptor/
	//    argument_role/bench_role/missing_tenure/editable state for every participant.
	//  - discrepancies (AdminJobResponse.discrepancies, pre-Phase-25): only populated
	//    while jobStatus === 'paused' — carries auto-match candidates for the operator's
	//    person-matching flow that ArgumentParticipant.person_id has not yet committed.
	//
	// Side/descriptor edits submit immediately per-row via ?/saveResolveRow (T-25-16: job_id
	// is the only trust boundary; participant ownership is re-verified server-side).
	// Person-matching (search/select/create person) accumulates client-side and submits
	// as a batch via ?/resolve when "Continue Resolve" is clicked (existing pipeline
	// resolve-step contract, unchanged by Phase 25).

	interface Candidate {
		id: number;
		full_name: string;
		role_name?: string | null;
	}

	interface Discrepancy {
		raw_speaker_label: string;
		auto_match_id?: number | null;
		auto_match_name?: string | null;
		auto_match_role?: string | null;
		auto_resolved?: boolean | null;
		candidates: Candidate[];
	}

	interface ResolveRow {
		participant_id: number;
		raw_speaker_label: string;
		person_id: number | null;
		full_name: string | null;
		photo_url: string | null;
		side: string;
		argument_role: string | null;
		descriptor: string | null;
		descriptor_hint: string | null;
		bench_role: string | null;
		missing_tenure: boolean;
		person_edit_href: string | null;
		editable: boolean;
	}

	interface ResolveCardProps {
		resolveRows: ResolveRow[];
		discrepancies: Discrepancy[] | null;
		people: Candidate[];
		peopleLoadError?: string | null;
		jobStatus: string;
		readonlyMode: boolean;
		resolveFormError?: string | null;
	}

	let {
		resolveRows,
		discrepancies = null,
		people = [],
		peopleLoadError = null,
		jobStatus,
		readonlyMode,
		resolveFormError = null,
	}: ResolveCardProps = $props();

	let isPaused = $derived(jobStatus === 'paused');
	let interactive = $derived(!readonlyMode);

	interface MergedRow extends ResolveRow {
		discrepancy: Discrepancy | null;
	}

	let mergedRows = $derived.by<MergedRow[]>(() => {
		const discMap = new Map<string, Discrepancy>();
		for (const d of discrepancies ?? []) {
			discMap.set(d.raw_speaker_label, d);
		}
		return resolveRows.map((r) => ({
			...r,
			discrepancy: discMap.get(r.raw_speaker_label) ?? null,
		}));
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Side/descriptor inline save (saveResolveRow) — per-row hidden form, submitted
	// programmatically via requestSubmit() so the select/input controls (which
	// live in different <td> cells) can share one form via the HTML `form=`
	// attribute rather than nesting a <form> inside table cells.
	// ──────────────────────────────────────────────────────────────────────────

	let formRefs: Record<number, HTMLFormElement> = {};
	let saveState = $state<Record<number, { saving: boolean; error: string | null }>>({});
	let pendingSideOverrides = $state<Record<number, string>>({});
	let sideGateConfirmed = $state<Record<number, boolean>>({});

	function rowFormId(participantId: number): string {
		return `resolve-row-form-${participantId}`;
	}

	function submitRow(participantId: number) {
		formRefs[participantId]?.requestSubmit();
	}

	function effectiveSide(row: MergedRow): string {
		return pendingSideOverrides[row.participant_id] ?? row.side;
	}

	// D-11/PJOB-18: rows needing intervention (no auto-resolved match while paused)
	// must have Bench/Advocate confirmed before the person typeahead activates.
	// Auto-matched rows stay complete and skip this gating.
	function needsSideGate(row: MergedRow): boolean {
		if (!isPaused) return false;
		if (!row.discrepancy) return false;
		if (row.discrepancy.auto_resolved === true) return false;
		return !sideGateConfirmed[row.participant_id];
	}

	function confirmSide(row: MergedRow, choice: 'BENCH' | 'ADVOCATE') {
		const value = choice === 'BENCH' ? 'BENCH' : 'UNKNOWN';
		pendingSideOverrides[row.participant_id] = value;
		sideGateConfirmed[row.participant_id] = true;
		submitRow(row.participant_id);
	}

	function onSideChange(row: MergedRow, value: string) {
		pendingSideOverrides[row.participant_id] = value;
		submitRow(row.participant_id);
	}

	const SIDE_LABEL: Record<string, string> = {
		BENCH: 'Bench',
		PETITIONER: "Petitioner's Counsel",
		RESPONDENT: "Respondent's Counsel",
		AMICUS: 'Amicus Curiae',
		UNKNOWN: 'Counsel',
		ADVOCATE: 'Counsel', // legacy — never produced going forward
	};

	// ──────────────────────────────────────────────────────────────────────────
	// Person-matching flow (only while isPaused) — adapted from the pre-Phase-25
	// discrepancy review table, relocated into the "Resolved as"/Action columns.
	// ──────────────────────────────────────────────────────────────────────────

	interface RowMatchState {
		personId: number | null;
		disposition: 'confirmed' | 'corrected' | null;
		correcting: boolean;
		extraCandidates: Candidate[];
		comboQuery: string;
		comboOpen: boolean;
		comboHighlight: number;
	}

	let rowMatchStates = $state<Record<string, RowMatchState>>({});

	$effect(() => {
		if (!isPaused) return;
		const disc = discrepancies ?? [];
		const incomingKeys = new Set(disc.map((d) => d.raw_speaker_label));
		for (const key of Object.keys(rowMatchStates)) {
			if (!incomingKeys.has(key)) {
				delete rowMatchStates[key];
			}
		}
		for (const d of disc) {
			if (!(d.raw_speaker_label in rowMatchStates)) {
				const isHit = d.auto_resolved === true;
				rowMatchStates[d.raw_speaker_label] = {
					personId: d.auto_match_id ?? null,
					disposition: isHit ? 'confirmed' : null,
					correcting: false,
					extraCandidates: [],
					comboQuery: '',
					comboOpen: false,
					comboHighlight: -1,
				};
			}
		}
	});

	let allDispositioned = $derived.by(() => {
		if (!isPaused) return false;
		const disc = discrepancies ?? [];
		// WR-04: an empty discrepancy list while paused means every speaker was
		// already resolved (auto-match or inline saveResolveRow) — there is
		// nothing left to disposition, so "Continue Resolve" must still render
		// rather than being permanently stuck behind a vacuously-false check.
		if (disc.length === 0) return true;
		return disc.every((d) => {
			const s = rowMatchStates[d.raw_speaker_label];
			return s?.disposition != null && s?.personId != null;
		});
	});

	let matchesJson = $derived.by(() => {
		const disc = discrepancies ?? [];
		const arr = disc
			.map((d) => {
				const s = rowMatchStates[d.raw_speaker_label];
				if (!s || s.personId == null) return null;
				return { raw_speaker_label: d.raw_speaker_label, person_id: s.personId };
			})
			.filter(Boolean);
		return JSON.stringify(arr);
	});

	let continueSubmitting = $state(false);

	function getRowCandidates(discrepancy: Discrepancy, label: string): Candidate[] {
		const extra = rowMatchStates[label]?.extraCandidates ?? [];
		const all = [...(people ?? []), ...discrepancy.candidates, ...extra];
		const seen = new Set<number>();
		return all.filter((c) => {
			if (seen.has(c.id)) return false;
			seen.add(c.id);
			return true;
		});
	}

	function handleConfirm(label: string, discrepancy: Discrepancy) {
		const s = rowMatchStates[label];
		if (!s) return;
		s.personId = discrepancy.auto_match_id ?? null;
		s.disposition = 'confirmed';
		s.correcting = false;
	}

	function handleCorrect(label: string) {
		const s = rowMatchStates[label];
		if (!s) return;
		s.correcting = true;
		s.disposition = null;
	}

	function handleSelectPerson(label: string, personId: number) {
		const s = rowMatchStates[label];
		if (!s) return;
		s.personId = personId;
		s.disposition = 'corrected';
		s.correcting = true;
	}

	function handlePersonCreated(label: string, participantId: number, person: Candidate, side: string) {
		const s = rowMatchStates[label];
		if (!s) return;
		s.extraCandidates = [...s.extraCandidates, person];
		s.personId = person.id;
		s.disposition = 'corrected';
		s.correcting = true;
		pendingSideOverrides[participantId] = side;
		submitRow(participantId);
	}

	// Svelte action — close the combobox dropdown on outside click.
	function comboOutsideClick(container: HTMLElement, rowKey: string) {
		function handleClick(e: MouseEvent) {
			if (!container.contains(e.target as Node)) {
				const s = rowMatchStates[rowKey];
				if (s) {
					s.comboOpen = false;
				}
			}
		}
		$effect(() => {
			document.addEventListener('click', handleClick);
			return () => {
				document.removeEventListener('click', handleClick);
			};
		});
		return {
			destroy() {
				document.removeEventListener('click', handleClick);
			},
		};
	}

	function getInitials(name: string): string {
		const parts = name.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	}
</script>

{#snippet rawLabelBadge(label: string)}
	<span
		style="
			background-color: #0f1117;
			border: 1px solid #334155;
			border-radius: 4px;
			padding: 4px 10px;
			font-size: 14px;
			font-weight: 400;
			color: #e2e8f0;
			text-transform: uppercase;
			letter-spacing: 0.02em;
			display: inline-block;
			white-space: normal;
		"
	>
		{label}
	</span>
{/snippet}

{#snippet descriptorCell(row: MergedRow, side: string, rowEditable: boolean)}
	{#if side === 'BENCH'}
		<span style="color: #94a3b8;">–</span>
	{:else if rowEditable}
		<input
			form={rowFormId(row.participant_id)}
			name="descriptor"
			type="text"
			value={row.descriptor ?? ''}
			onblur={() => submitRow(row.participant_id)}
			placeholder="e.g. Attorney, Location, or Affiliation"
			style="
				background-color: #0f1117;
				border: 1px solid #334155;
				border-radius: 6px;
				padding: 8px 12px;
				font-size: 16px;
				color: #e2e8f0;
				min-height: 36px;
				width: 100%;
				box-sizing: border-box;
				overflow: hidden;
				text-overflow: ellipsis;
				white-space: nowrap;
			"
		/>
		<div style="margin: 4px 0 0 0;">
			<!-- Phase 38 (D-19/D-20): descriptor_hint has no independently stored raw/confidence
			     (admin_arguments.py D-06 — descriptor and descriptor_hint source the same column), so
			     the exact extracted text itself is the raw source and confidence uses an
			     explicit qualitative fallback rather than a fabricated figure. -->
			<CopyableExtractedValue
				value={row.descriptor_hint}
				copyLabel="Copy descriptor"
				confidence="Medium"
				raw={row.descriptor_hint}
			/>
		</div>
	{:else}
		<span>{row.descriptor ?? '–'}</span>
	{/if}
{/snippet}

{#snippet personDisplay(fullName: string | null, photoUrl: string | null, roleLabel: string | null)}
	{#if fullName}
		<span style="display: inline-flex; align-items: center; gap: 8px;">
			<span
				style="
					width: 28px;
					height: 28px;
					border-radius: 50%;
					background-color: #334155;
					display: inline-flex;
					align-items: center;
					justify-content: center;
					font-size: 12px;
					color: #e2e8f0;
					overflow: hidden;
					flex-shrink: 0;
				"
			>
				{#if photoUrl}
					<img src={photoUrl} alt="" style="width: 100%; height: 100%; object-fit: cover;" />
				{:else}
					{getInitials(fullName)}
				{/if}
			</span>
			<span style="font-size: 16px; color: #e2e8f0;">
				{fullName}{#if roleLabel}<span style="color: #94a3b8; font-size: 14px; margin-left: 4px;">({roleLabel})</span>{/if}
			</span>
		</span>
	{:else}
		<span style="color: #94a3b8;">—</span>
	{/if}
{/snippet}

<div
	style="
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
		margin-bottom: 24px;
	"
>
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
		Resolve
	</h2>

	{#if peopleLoadError}
		<p role="alert" style="margin-bottom: 12px; font-size: 13px; color: #fbbf24; font-family: monospace;">
			Warning: could not load people list — typeahead may be incomplete. ({peopleLoadError})
		</p>
	{/if}

	<!-- Hidden per-row save forms — inputs elsewhere in the table reference these via form="..." -->
	{#each mergedRows as row (row.participant_id)}
		<form
			id={rowFormId(row.participant_id)}
			bind:this={formRefs[row.participant_id]}
			method="POST"
			action="?/saveResolveRow"
			style="display: none;"
			use:enhance={() => {
				saveState[row.participant_id] = { saving: true, error: null };
				return async ({ result, update }) => {
					if (result.type === 'failure') {
						saveState[row.participant_id] = {
							saving: false,
							error: (result.data as { resolveRowError?: string })?.resolveRowError ?? 'Could not save.',
						};
					} else {
						saveState[row.participant_id] = { saving: false, error: null };
						await update({ reset: false });
					}
				};
			}}
		>
			<input type="hidden" name="participant_id" value={row.participant_id} />
		</form>
	{/each}

	<!-- Responsive contract: horizontally scrollable wrapper avoids overflow/overlap at 860px (T-25-13) -->
	<div style="overflow-x: auto;">
		<table style="width: 100%; border-collapse: collapse; min-width: 720px;">
			<thead>
				<tr>
					<th scope="col" style="font-size: 14px; font-weight: 400; color: #94a3b8; border-bottom: 1px solid #334155; padding: 8px 0; padding-right: 12px; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Raw Label</th>
					<th scope="col" style="font-size: 14px; font-weight: 400; color: #94a3b8; border-bottom: 1px solid #334155; padding: 8px 0; padding-right: 12px; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Resolved As</th>
					<th scope="col" style="font-size: 14px; font-weight: 400; color: #94a3b8; border-bottom: 1px solid #334155; padding: 8px 0; padding-right: 12px; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Bench/Advocate</th>
					<th scope="col" style="font-size: 14px; font-weight: 400; color: #94a3b8; border-bottom: 1px solid #334155; padding: 8px 0; padding-right: 12px; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Argument Role</th>
					<th scope="col" style="font-size: 14px; font-weight: 400; color: #94a3b8; border-bottom: 1px solid #334155; padding: 8px 0; text-align: left; text-transform: uppercase; letter-spacing: 0.04em;">Descriptor</th>
				</tr>
			</thead>
			<tbody>
				{#each mergedRows as row (row.participant_id)}
					{@const label = row.raw_speaker_label}
					{@const s = rowMatchStates[label]}
					{@const gated = needsSideGate(row)}
					{@const side = effectiveSide(row)}
					{@const rowEditable = interactive && row.editable}

					<tr>
						<!-- Column 1: Raw Label -->
						<td style="font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding: 12px 0; padding-right: 12px;">
							{@render rawLabelBadge(row.raw_speaker_label)}
						</td>

						<!-- Column 2: Resolved as -->
						<td style="font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding: 12px 0; padding-right: 12px;">
							{#if isPaused && row.discrepancy}
								{#if gated}
									<span style="color: #94a3b8; font-size: 14px;">Select Bench or Advocate to continue</span>
								{:else if s?.disposition === 'confirmed'}
									<span style="color: #4ade80;">✓ Confirmed</span>
									{#if row.discrepancy.auto_match_name}
										<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">
											{row.discrepancy.auto_match_name}{row.discrepancy.auto_match_role ? ` (${row.discrepancy.auto_match_role})` : ''}
										</span>
									{/if}
								{:else if s?.correcting}
									{@const comboId = `listbox-${label.replace(/\s+/g, '-')}`}
									{@const candidates = getRowCandidates(row.discrepancy, label)}
									{@const filteredCandidates = candidates.filter((c) => {
										const text = c.role_name ? `${c.full_name} ${c.role_name}` : c.full_name;
										return text.toLowerCase().includes((s.comboQuery ?? '').toLowerCase());
									})}
									{#if s.disposition === 'corrected'}
										{@const selectedPerson = candidates.find((c) => c.id === s.personId)}
										<div style="margin-bottom: 8px;">
											<span style="color: #4ade80;">✓ Corrected</span>
											{#if selectedPerson}
												<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">
													{selectedPerson.full_name}{selectedPerson.role_name ? ` (${selectedPerson.role_name})` : ''}
												</span>
											{/if}
										</div>
									{/if}
									<div style="position: relative; width: 100%;" use:comboOutsideClick={label}>
										<input
											type="text"
											role="combobox"
											aria-expanded={s.comboOpen}
											aria-haspopup="listbox"
											aria-controls={comboId}
											aria-autocomplete="list"
											aria-label="Search for speaker"
											placeholder="Type to search…"
											value={s.comboQuery}
											style="
												background-color: #0f1117;
												border: 1px solid #93c5fd;
												border-radius: 6px;
												padding: 6px 10px;
												font-size: 16px;
												color: #e2e8f0;
												width: 100%;
												box-sizing: border-box;
											"
											onfocus={() => {
												s.comboOpen = true;
												s.comboHighlight = -1;
											}}
											oninput={(e) => {
												s.comboQuery = (e.target as HTMLInputElement).value;
												s.comboOpen = true;
												s.comboHighlight = -1;
											}}
											onkeydown={(e) => {
												if (e.key === 'ArrowDown') {
													e.preventDefault();
													s.comboHighlight = Math.min(s.comboHighlight + 1, filteredCandidates.length - 1);
												} else if (e.key === 'ArrowUp') {
													e.preventDefault();
													s.comboHighlight = Math.max(s.comboHighlight - 1, -1);
												} else if (e.key === 'Enter') {
													e.preventDefault();
													if (s.comboHighlight >= 0 && s.comboHighlight < filteredCandidates.length) {
														const picked = filteredCandidates[s.comboHighlight];
														s.comboQuery = picked.full_name;
														handleSelectPerson(label, picked.id);
														s.comboOpen = false;
													}
												} else if (e.key === 'Escape') {
													s.comboQuery = '';
													s.comboOpen = false;
													s.comboHighlight = -1;
												}
											}}
										/>
										{#if s.comboOpen}
											<ul
												id={comboId}
												role="listbox"
												style="
													position: absolute;
													top: 100%;
													left: 0;
													width: 100%;
													margin: 4px 0 0 0;
													background-color: #1e293b;
													border: 1px solid #334155;
													border-radius: 6px;
													padding: 4px 0;
													max-height: 240px;
													overflow-y: auto;
													z-index: 10;
													list-style: none;
												"
											>
												{#each filteredCandidates as candidate, idx (candidate.id)}
													<li
														role="option"
														aria-selected={false}
														style="
															padding: 8px 12px;
															font-size: 16px;
															color: #e2e8f0;
															cursor: pointer;
															background-color: {s.comboHighlight === idx ? '#334155' : '#1e293b'};
														"
														onmouseenter={() => {
															s.comboHighlight = idx;
														}}
														onclick={() => {
															s.comboQuery = candidate.full_name;
															handleSelectPerson(label, candidate.id);
															s.comboOpen = false;
														}}
													>
														{candidate.full_name}{#if candidate.role_name}<span style="font-size: 14px; color: #94a3b8; margin-left: 4px;">({candidate.role_name})</span>{/if}
													</li>
												{/each}
											</ul>
										{/if}
									</div>
									<div style="margin-top: 8px;">
										<CreatePersonPopover
											rawSpeakerLabel={label}
											defaultAdvocateSide={side !== 'BENCH' ? side : 'UNKNOWN'}
											onCreated={(person, createdSide) =>
												handlePersonCreated(label, row.participant_id, person, createdSide)}
										/>
									</div>
								{:else if row.discrepancy.auto_match_name}
									{row.discrepancy.auto_match_name}{row.discrepancy.auto_match_role ? ` (${row.discrepancy.auto_match_role})` : ''}
								{:else}
									<span style="color: #94a3b8;">—</span>
								{/if}
							{:else}
								{@render personDisplay(row.full_name, row.photo_url, row.argument_role)}
							{/if}
						</td>

						<!-- Column 3: Bench/Advocate — also the D-11/PJOB-18 side-first gate for intervention rows -->
						<td style="font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding: 12px 0; padding-right: 12px;">
							{#if gated}
								<div style="display: flex; gap: 8px;">
									<button
										type="button"
										onclick={() => confirmSide(row, 'BENCH')}
										style="font-size: 14px; font-weight: 400; color: #e2e8f0; background: transparent; border: 1px solid #334155; border-radius: 4px; padding: 6px 12px; cursor: pointer; min-height: 36px;"
									>
										Bench
									</button>
									<button
										type="button"
										onclick={() => confirmSide(row, 'ADVOCATE')}
										style="font-size: 14px; font-weight: 400; color: #e2e8f0; background: transparent; border: 1px solid #334155; border-radius: 4px; padding: 6px 12px; cursor: pointer; min-height: 36px;"
									>
										Advocate
									</button>
								</div>
							{:else if rowEditable}
								<select
									form={rowFormId(row.participant_id)}
									name="side"
									value={side}
									onchange={(e) => onSideChange(row, (e.target as HTMLSelectElement).value)}
									style="
										background-color: #0f1117;
										border: 1px solid #334155;
										border-radius: 6px;
										padding: 8px 12px;
										font-size: 16px;
										font-weight: 400;
										color: #e2e8f0;
										min-height: 36px;
										width: 100%;
										cursor: pointer;
									"
								>
									<option value="BENCH">Bench</option>
									<option value="PETITIONER">Petitioner's Counsel</option>
									<option value="RESPONDENT">Respondent's Counsel</option>
									<option value="AMICUS">Amicus Curiae</option>
									<option value="UNKNOWN">Counsel</option>
								</select>
							{:else}
								<span style="font-size: 14px; color: #94a3b8;">{SIDE_LABEL[side] ?? side}</span>
							{/if}
							{#if saveState[row.participant_id]?.error}
								<p role="alert" style="margin: 4px 0 0 0; font-size: 13px; color: #ef4444;">
									{saveState[row.participant_id]?.error}
								</p>
							{/if}
						</td>

						<!-- Column 4: Argument Role — bench tenure-derived role / Missing tenure, or advocate label -->
						<td style="font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding: 12px 0; padding-right: 12px;">
							{#if gated}
								<span style="color: #94a3b8;">—</span>
							{:else if side === 'BENCH'}
								{#if row.missing_tenure}
									<span style="color: #fbbf24; font-size: 14px;">Missing tenure</span>
									{#if row.person_edit_href}
										<a href={row.person_edit_href} style="margin-left: 8px; font-size: 14px; color: #93c5fd; text-decoration: underline;">
											Edit person
										</a>
									{/if}
								{:else}
									<span style="font-size: 16px; color: #e2e8f0;">{row.bench_role ?? row.argument_role ?? '—'}</span>
								{/if}
							{:else}
								<span style="font-size: 16px; color: #e2e8f0;">{row.argument_role ?? '—'}</span>
							{/if}
						</td>

						<!-- Column 5: Descriptor (renamed from Title, Phase 44 RESOLVE-04) — always renders -->
						<td style="font-size: 16px; color: #e2e8f0; border-bottom: 1px solid #334155; padding: 12px 0;">
							{@render descriptorCell(row, side, rowEditable)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Continue Resolve — moved into the Resolve card footer (PJOB-21); only when all rows dispositioned -->
	{#if isPaused && allDispositioned}
		<form
			method="POST"
			action="?/resolve"
			use:enhance={() => {
				continueSubmitting = true;
				return async ({ result, update }) => {
					if (result.type === 'failure') {
						continueSubmitting = false;
						await update();
					} else {
						continueSubmitting = false;
						await update({ reset: false });
					}
				};
			}}
			style="margin-top: 24px;"
		>
			<input type="hidden" name="matches" value={matchesJson} />
			<button
				type="submit"
				disabled={continueSubmitting}
				style="
					width: 100%;
					min-height: 44px;
					font-size: 16px;
					font-weight: 600;
					color: #e2e8f0;
					background: transparent;
					border: 1px solid #93c5fd;
					border-radius: 6px;
					padding: 12px 24px;
					cursor: pointer;
				"
			>
				{continueSubmitting ? 'Submitting…' : 'Continue Resolve'}
			</button>
		</form>
		{#if resolveFormError}
			<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
				{resolveFormError}
			</p>
		{/if}
	{/if}
</div>
