<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { enhance } from '$app/forms';

	let { data, form } = $props();

	// ──────────────────────────────────────────────────────────────────────────
	// Types
	// ──────────────────────────────────────────────────────────────────────────

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

	interface Job {
		id: number;
		status: string;
		current_step: string;
		error_message?: string | null;
		discrepancies?: Discrepancy[] | null;
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Polling (D-15/D-16 — Pattern 1 from RESEARCH.md)
	// Effect re-runs when data.job.status changes — restarts polling after
	// Continue Resolve flips paused → running.
	// ──────────────────────────────────────────────────────────────────────────

	$effect(() => {
		const TERMINAL = new Set(['completed', 'failed', 'paused']);
		if (TERMINAL.has(data.job.status)) return;

		const interval = setInterval(async () => {
			await invalidateAll();
		}, 2500);

		return () => clearInterval(interval);
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Discrepancy review state
	// Keyed by raw_speaker_label; tracks { person_id, disposition: 'confirmed' | 'corrected' | null }
	// ──────────────────────────────────────────────────────────────────────────

	interface RowState {
		person_id: number | null;
		disposition: 'confirmed' | 'corrected' | null;
		correcting: boolean; // dropdown is open
		addingPerson: boolean; // AddNewPersonForm visible
		extraCandidates: Candidate[]; // people added via addPerson
		submittingNewPerson: boolean;
		newPersonName: string;
		newPersonRole: string;
		newPersonError: string | null;
	}

	let rowStates = $state<Record<string, RowState>>({});

	// Initialise row states when discrepancies arrive (status=paused).
	// Only initialise for rows not already tracked (preserve in-progress work on re-renders).
	// HIT rows (auto_resolved === true) start pre-dispositioned as 'confirmed' so no
	// explicit Confirm click is required ([07-07] Gap 1a fix).
	$effect(() => {
		const disc = data.job.discrepancies;
		if (!disc) return;
		for (const row of disc) {
			if (!(row.raw_speaker_label in rowStates)) {
				const isHit = row.auto_resolved === true;
				rowStates[row.raw_speaker_label] = {
					person_id: row.auto_match_id ?? null,
					disposition: isHit ? 'confirmed' : null,
					correcting: false,
					addingPerson: false,
					extraCandidates: [],
					submittingNewPerson: false,
					newPersonName: '',
					newPersonRole: '',
					newPersonError: null,
				};
			}
		}
	});

	// All rows dispositioned → show Continue Resolve button.
	// Requires both disposition set AND person_id resolved (not null),
	// so a "Confirm" with no auto_match_id cannot prematurely enable the button.
	let allDispositioned = $derived.by(() => {
		const disc = data.job.discrepancies;
		if (!disc || disc.length === 0) return false;
		return disc.every((row: Discrepancy) => {
			const s = rowStates[row.raw_speaker_label];
			return s?.disposition !== null && s?.disposition !== undefined && s?.person_id !== null;
		});
	});

	// Build the JSON matches array for the hidden form field.
	let matchesJson = $derived.by(() => {
		const disc = data.job.discrepancies;
		if (!disc) return '[]';
		const arr = disc
			.map((row: Discrepancy) => {
				const s = rowStates[row.raw_speaker_label];
				if (!s || s.person_id === null) return null;
				return { raw_speaker_label: row.raw_speaker_label, person_id: s.person_id };
			})
			.filter(Boolean);
		return JSON.stringify(arr);
	});

	// ──────────────────────────────────────────────────────────────────────────
	// Step card helpers
	// ──────────────────────────────────────────────────────────────────────────

	type StepName = 'ingest' | 'parse' | 'resolve';

	const STEP_ORDER: StepName[] = ['ingest', 'parse', 'resolve'];
	const STEP_LABELS: Record<StepName, string> = {
		ingest: 'Ingest',
		parse: 'Parse',
		resolve: 'Resolve',
	};

	function stepStatus(step: StepName, job: Job): string {
		const current = job.current_step?.toLowerCase() as StepName;
		const currentIdx = STEP_ORDER.indexOf(current);
		const thisIdx = STEP_ORDER.indexOf(step);

		if (job.status === 'completed') return 'completed';
		if (job.status === 'failed' && step === current) return 'failed';
		if (job.status === 'failed' && thisIdx < currentIdx) return 'completed';
		if (job.status === 'failed' && thisIdx > currentIdx) return 'pending';
		if (job.status === 'paused' && step === 'resolve') return 'paused';
		if (job.status === 'paused' && thisIdx < currentIdx) return 'completed';
		if (job.status === 'paused' && thisIdx > currentIdx) return 'pending';
		if (thisIdx < currentIdx) return 'completed';
		if (thisIdx === currentIdx) return job.status === 'running' ? 'running' : 'pending';
		return 'pending';
	}

	const BADGE_COLOR: Record<string, string> = {
		pending: '#94a3b8',
		running: '#93c5fd',
		completed: '#4ade80',
		paused: '#fbbf24',
		failed: '#ef4444',
	};

	const BADGE_GLYPH: Record<string, string> = {
		pending: '–',
		running: '◌',
		completed: '✓',
		paused: '⏸',
		failed: '✗',
	};

	const BADGE_LABEL: Record<string, string> = {
		pending: 'Pending',
		running: 'Running',
		completed: 'Completed',
		paused: 'Needs review',
		failed: 'Failed',
	};

	function cardBorderStyle(status: string): string {
		if (status === 'running') return 'border-left: 3px solid #93c5fd;';
		if (status === 'paused') return 'border-left: 3px solid #fbbf24;';
		if (status === 'failed') return 'border-left: 3px solid #ef4444;';
		return '';
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Continue Resolve submit state
	// ──────────────────────────────────────────────────────────────────────────

	let continueSubmitting = $state(false);

	// ──────────────────────────────────────────────────────────────────────────
	// Row action handlers
	// ──────────────────────────────────────────────────────────────────────────

	function handleConfirm(label: string, row: Discrepancy) {
		const s = rowStates[label];
		if (!s) return;
		// Use auto_match_id as the resolved person_id.
		s.person_id = row.auto_match_id ?? null;
		s.disposition = 'confirmed';
		s.correcting = false;
	}

	function handleCorrect(label: string) {
		const s = rowStates[label];
		if (!s) return;
		s.correcting = true;
		s.disposition = null;
		s.addingPerson = false;
	}

	function handleSelectPerson(label: string, value: string) {
		const s = rowStates[label];
		if (!s) return;

		if (value === '__add_new__') {
			s.addingPerson = true;
			s.disposition = null;
			return;
		}

		const personId = parseInt(value, 10);
		if (!isNaN(personId)) {
			s.person_id = personId;
			s.disposition = 'corrected';
			s.correcting = true; // keep dropdown visible but frozen
			s.addingPerson = false;
		}
	}

	function getRowCandidates(row: Discrepancy, label: string): Candidate[] {
		const extra = rowStates[label]?.extraCandidates ?? [];
		// Merge the full people roster (loaded by the server) so HIT rows also have a
		// populated typeahead when the operator clicks Change ([07-07] Gap 1b fix).
		// De-duplicate by id — row.candidates (empty for HITs) takes precedence via the
		// Set filter below; data.people provides the broad roster.
		const allCandidates = [...(data.people ?? []), ...row.candidates, ...extra];
		const seen = new Set<number>();
		return allCandidates.filter((c) => {
			if (seen.has(c.id)) return false;
			seen.add(c.id);
			return true;
		});
	}
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			Run #{data.job.id}
		</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		<!-- Step cards container — aria-live polite so screen readers announce step changes -->
		<div
			aria-live="polite"
			style="display: flex; flex-direction: column; gap: 16px;"
		>
			{#each STEP_ORDER as step}
				{@const status = stepStatus(step, data.job)}
				{@const color = BADGE_COLOR[status]}
				{@const glyph = BADGE_GLYPH[status]}
				{@const label = BADGE_LABEL[status]}
				{@const borderOverride = cardBorderStyle(status)}

				<div
					style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; {borderOverride}"
				>
					<!-- Step card header row -->
					<div style="display: flex; align-items: center; justify-content: space-between;">
						<span style="font-size: 16px; font-weight: 400; color: #e2e8f0;">
							{STEP_LABELS[step]}
						</span>

						<!-- StatusBadge: colored border + text on #1e293b surface, never filled -->
						<span
							aria-label={status === 'running' ? 'Running' : undefined}
							style="
								border: 1px solid {color};
								border-radius: 4px;
								padding: 2px 8px;
								font-size: 14px;
								font-weight: 400;
								color: {color};
								background-color: #1e293b;
								display: inline-flex;
								align-items: center;
								gap: 4px;
							"
						>
							{#if status === 'running'}
								<!-- Spinner glyph with aria-label on parent span -->
								<span
									aria-hidden="true"
									style="display: inline-block; animation: spin 1s linear infinite;"
								>◌</span>
							{:else}
								<span aria-hidden="true">{glyph}</span>
							{/if}
							{label}
						</span>
					</div>

					<!-- Discrepancy review (D-11–D-14): only when resolve step is paused -->
					{#if step === 'resolve' && data.job.status === 'paused' && data.peopleLoadError}
						<p role="alert" style="margin-top: 12px; font-size: 13px; color: #fbbf24; font-family: monospace;">
							Warning: could not load people list — typeahead may be incomplete. ({data.peopleLoadError})
						</p>
					{/if}
					{#if step === 'resolve' && data.job.status === 'paused' && data.job.discrepancies?.length}
						<table
							style="width: 100%; border-collapse: collapse; margin-top: 16px;"
						>
							<thead>
								<tr>
									<th
										scope="col"
										style="
											font-size: 14px;
											font-weight: 400;
											color: #94a3b8;
											border-bottom: 1px solid #334155;
											padding: 8px 0;
											text-align: left;
											width: 35%;
										"
									>Raw label</th>
									<th
										scope="col"
										style="
											font-size: 14px;
											font-weight: 400;
											color: #94a3b8;
											border-bottom: 1px solid #334155;
											padding: 8px 0;
											text-align: left;
											width: 45%;
										"
									>Resolved as</th>
									<th
										scope="col"
										style="
											font-size: 14px;
											font-weight: 400;
											color: #94a3b8;
											border-bottom: 1px solid #334155;
											padding: 8px 0;
											text-align: left;
											width: 20%;
										"
									>Action</th>
								</tr>
							</thead>
							<tbody>
								{#each data.job.discrepancies as row (row.raw_speaker_label)}
									{@const rowKey = row.raw_speaker_label}
									{@const s = rowStates[rowKey]}

									<tr>
										<!-- Column 1: Raw label -->
										<td
											style="
												font-size: 16px;
												color: #e2e8f0;
												border-bottom: 1px solid #334155;
												padding: 12px 0;
												padding-right: 12px;
											"
										>
											{row.raw_speaker_label}
										</td>

										<!-- Column 2: Resolved as / dropdown / confirmed display -->
										<td
											style="
												font-size: 16px;
												color: #e2e8f0;
												border-bottom: 1px solid #334155;
												padding: 12px 0;
												padding-right: 12px;
											"
										>
											{#if s?.disposition === 'confirmed'}
												<span style="color: #4ade80;">✓ Confirmed</span>
												{#if row.auto_match_name}
													{@const confirmedPerson = s?.person_id != null ? (data.people ?? []).find((p: { id: number; full_name: string; role_name: string | null }) => p.id === s.person_id) : null}
													{@const confirmedRole = confirmedPerson?.role_name ?? row.auto_match_role ?? null}
													<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">
														{row.auto_match_name}{confirmedRole ? ` (${confirmedRole})` : ''}
													</span>
												{/if}
											{:else if s?.disposition === 'corrected' && !s?.addingPerson}
												<span style="color: #4ade80;">✓ Corrected</span>
												{@const allCandidates = getRowCandidates(row, rowKey)}
												{@const selectedPerson = allCandidates.find((c) => c.id === s.person_id)}
												{#if selectedPerson}
													<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">
														{selectedPerson.full_name}{selectedPerson.role_name ? ` (${selectedPerson.role_name})` : ''}
													</span>
												{/if}
											{:else if s?.correcting}
												<!-- Typeahead combobox: text input + datalist for filter-as-you-type -->
												{@const listId = `candidates-${rowKey.replace(/\s+/g, '-')}`}
												<input
													list={listId}
													type="text"
													placeholder="Type to search—"
													aria-label="Search for speaker"
													style="
														background-color: #0f1117;
														border: 1px solid #93c5fd;
														border-radius: 6px;
														padding: 6px 10px;
														font-size: 16px;
														color: #e2e8f0;
														width: 100%;
													"
													oninput={(e) => {
														const val = (e.target as HTMLInputElement).value;
														const allC = getRowCandidates(row, rowKey);
														const match = allC.find(c => {
															const display = c.role_name ? `${c.full_name} (${c.role_name})` : c.full_name;
															return display === val;
														});
														if (match) {
															handleSelectPerson(rowKey, match.id.toString());
														} else if (val === '— Add new person —') {
															handleSelectPerson(rowKey, '__add_new__');
														}
													}}
												/>
												<datalist id={listId}>
													{#each getRowCandidates(row, rowKey) as candidate (candidate.id)}
														<option value={candidate.role_name ? `${candidate.full_name} (${candidate.role_name})` : candidate.full_name}></option>
													{/each}
													<option value="— Add new person —"></option>
												</datalist>

												<!-- AddNewPersonForm: inline below dropdown when Add new person selected.
												     Uses use:enhance so SvelteKit handles devalue deserialization
												     automatically ([07-07] Gap 2 fix). -->
												{#if s.addingPerson}
													<div style="margin-top: 12px; padding: 12px; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px;">
														<form
															method="POST"
															action="?/addPerson"
															use:enhance={() => {
																const label = rowKey;
																const st = rowStates[label];
																if (st) {
																	st.submittingNewPerson = true;
																	st.newPersonError = null;
																}
																return async ({ result }) => {
																	const st2 = rowStates[label];
																	if (!st2) return;
																	if (result.type === 'failure') {
																		st2.newPersonError = (result.data as { error?: string })?.error ?? 'Could not create person. Please try again.';
																	} else if (result.type === 'success') {
																		// use:enhance devalue-deserializes result.data automatically
																		const person = (result.data as { person?: { id: number; full_name: string; role_name?: string | null } })?.person;
																		if (person) {
																			st2.extraCandidates = [...st2.extraCandidates, { id: person.id, full_name: person.full_name, role_name: person.role_name ?? null }];
																			st2.person_id = person.id;
																			st2.disposition = 'corrected';
																			st2.addingPerson = false;
																			st2.newPersonName = '';
																			st2.newPersonRole = '';
																		}
																	}
																	st2.submittingNewPerson = false;
																	// Do NOT call update() with reset — that wipes rowStates
																};
															}}
														>
															<div style="margin-bottom: 8px;">
																<label
																	for="new-person-name-{rowKey}"
																	style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
																>
																	Full name
																</label>
																<input
																	id="new-person-name-{rowKey}"
																	name="full_name"
																	type="text"
																	bind:value={s.newPersonName}
																	style="
																		background-color: #0f1117;
																		border: 1px solid #334155;
																		border-radius: 6px;
																		padding: 8px 12px;
																		font-size: 16px;
																		color: #e2e8f0;
																		width: 100%;
																		box-sizing: border-box;
																	"
																/>
															</div>
															<div style="margin-bottom: 12px;">
																<label
																	for="new-person-role-{rowKey}"
																	style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
																>
																	Role
																</label>
																<input
																	id="new-person-role-{rowKey}"
																	name="role_name"
																	type="text"
																	bind:value={s.newPersonRole}
																	style="
																		background-color: #0f1117;
																		border: 1px solid #334155;
																		border-radius: 6px;
																		padding: 8px 12px;
																		font-size: 16px;
																		color: #e2e8f0;
																		width: 100%;
																		box-sizing: border-box;
																	"
																/>
															</div>
															{#if s.newPersonError}
																<p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
																	{s.newPersonError}
																</p>
															{/if}
															<button
																type="submit"
																disabled={s.submittingNewPerson || !s.newPersonName.trim()}
																style="
																	font-size: 14px;
																	font-weight: 600;
																	color: #e2e8f0;
																	background: transparent;
																	border: 1px solid #93c5fd;
																	border-radius: 6px;
																	padding: 8px 16px;
																	min-height: 36px;
																	cursor: pointer;
																"
															>
																{s.submittingNewPerson ? 'Saving…' : 'Save person'}
															</button>
														</form>
													</div>
												{/if}
											{:else}
												<!-- Default: show auto-resolved match name -->
												{#if row.auto_match_name}
													{row.auto_match_name}{row.auto_match_role ? ` (${row.auto_match_role})` : ''}
												{:else}
													<span style="color: #94a3b8;">—</span>
												{/if}
											{/if}
										</td>

										<!-- Column 3: Action buttons -->
										<td
											style="
												font-size: 16px;
												color: #e2e8f0;
												border-bottom: 1px solid #334155;
												padding: 12px 0;
											"
										>
											{#if row.auto_resolved === true}
												<!-- HIT row: single Change button — operator clicks to re-pick from full roster ([07-07] Gap 1a) -->
												<button
													type="button"
													onclick={() => handleCorrect(rowKey)}
													style="
														font-size: 14px;
														font-weight: 400;
														color: #e2e8f0;
														background: transparent;
														border: 1px solid #334155;
														border-radius: 4px;
														padding: 6px 12px;
														cursor: pointer;
														min-height: 32px;
													"
												>
													Change
												</button>
											{:else if s?.disposition !== null && s?.disposition !== undefined}
												<!-- MISS row is dispositioned — Change reopens the typeahead correction flow -->
												<button
													type="button"
													onclick={() => handleCorrect(rowKey)}
													style="
														font-size: 14px;
														font-weight: 400;
														color: #e2e8f0;
														background: transparent;
														border: 1px solid #334155;
														border-radius: 4px;
														padding: 6px 12px;
														cursor: pointer;
														min-height: 32px;
													"
												>
													Change
												</button>
											{:else}
												<!-- MISS row not yet dispositioned — Confirm (if auto_match_id) + Correct -->
												<div style="display: flex; gap: 8px; flex-wrap: wrap;">
													{#if row.auto_match_id}
														<button
															type="button"
															onclick={() => handleConfirm(rowKey, row)}
															style="
																font-size: 14px;
																font-weight: 400;
																color: #e2e8f0;
																background: transparent;
																border: 1px solid #334155;
																border-radius: 4px;
																padding: 6px 12px;
																cursor: pointer;
																min-height: 32px;
															"
														>
															Confirm
														</button>
													{/if}
													<button
														type="button"
														onclick={() => handleCorrect(rowKey)}
														style="
															font-size: 14px;
															font-weight: 400;
															color: #e2e8f0;
															background: transparent;
															border: 1px solid #334155;
															border-radius: 4px;
															padding: 6px 12px;
															cursor: pointer;
															min-height: 32px;
														"
													>
														Correct
													</button>
												</div>
											{/if}
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Continue Resolve button (D-14): only when paused AND all rows dispositioned -->
		{#if data.job.status === 'paused' && allDispositioned}
			<form
				method="POST"
				action="?/resolve"
				use:enhance={() => {
					continueSubmitting = true;
					return async ({ result, update }) => {
						if (result.type === 'failure') {
							continueSubmitting = false;
							// error is displayed via form prop below
							await update();
						} else {
							// success: invalidateAll restarts polling and re-fetches job state
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
			{#if form?.error}
				<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
					{form.error}
				</p>
			{/if}
		{/if}

		<!-- Error panel (D-17): when status=failed; error_message rendered verbatim; no retry -->
		{#if data.job.status === 'failed'}
			<div
				style="
					margin-top: 24px;
					background-color: #1e293b;
					border: 1px solid #ef4444;
					border-radius: 8px;
					padding: 24px;
				"
			>
				<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 12px 0;">
					This run failed.
				</h2>
				{#if data.job.error_message}
					<p
						role="alert"
						style="font-size: 16px; color: #ef4444; margin: 0 0 16px 0; font-family: monospace; white-space: pre-wrap; word-break: break-word;"
					>
						Error: {data.job.error_message}
					</p>
				{/if}
				<a
					href="/admin/pipeline"
					style="font-size: 16px; color: #93c5fd; text-decoration: underline;"
				>
					Start a new run
				</a>
			</div>
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
