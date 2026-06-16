<script lang="ts">
	import { invalidateAll } from '$app/navigation';

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
	$effect(() => {
		const disc = data.job.discrepancies;
		if (!disc) return;
		for (const row of disc) {
			if (!(row.raw_speaker_label in rowStates)) {
				rowStates[row.raw_speaker_label] = {
					person_id: row.auto_match_id ?? null,
					disposition: null,
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

	async function handleAddPerson(label: string) {
		const s = rowStates[label];
		if (!s) return;

		s.submittingNewPerson = true;
		s.newPersonError = null;

		const fd = new FormData();
		fd.append('full_name', s.newPersonName);
		fd.append('role_name', s.newPersonRole);

		try {
			const res = await fetch(`?/addPerson`, {
				method: 'POST',
				body: fd,
			});
			const result = await res.json();

			if (!res.ok || result?.type === 'failure') {
				s.newPersonError = result?.data?.error ?? 'Could not create person. Please try again.';
				s.submittingNewPerson = false;
				return;
			}

			// Success — add new person to extraCandidates and select them.
			const person = result?.data?.person ?? result?.person;
			if (person) {
				s.extraCandidates = [...s.extraCandidates, { id: person.id, full_name: person.full_name, role_name: person.role_name ?? null }];
				s.person_id = person.id;
				s.disposition = 'corrected';
				s.addingPerson = false;
				s.newPersonName = '';
				s.newPersonRole = '';
			}
		} catch {
			s.newPersonError = 'Could not create person. Please try again.';
		} finally {
			s.submittingNewPerson = false;
		}
	}

	function getRowCandidates(row: Discrepancy, label: string): Candidate[] {
		const extra = rowStates[label]?.extraCandidates ?? [];
		return [...row.candidates, ...extra];
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
													<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">
														{row.auto_match_name}{row.auto_match_role ? ` (${row.auto_match_role})` : ''}
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
												<!-- PersonSearchDropdown: options are ONLY this row's candidates + Add new person -->
												<select
													style="
														background-color: #0f1117;
														border: 1px solid #93c5fd;
														border-radius: 6px;
														padding: 6px 10px;
														font-size: 16px;
														color: #e2e8f0;
														width: 100%;
													"
													onchange={(e) => handleSelectPerson(rowKey, (e.target as HTMLSelectElement).value)}
												>
													<option value="">— Select person —</option>
													{#each getRowCandidates(row, rowKey) as candidate (candidate.id)}
														<option value={candidate.id.toString()} selected={s.person_id === candidate.id}>
															{candidate.full_name}{candidate.role_name ? ` (${candidate.role_name})` : ''}
														</option>
													{/each}
													<option value="__add_new__">— Add new person —</option>
												</select>

												<!-- AddNewPersonForm: inline below dropdown when Add new person selected -->
												{#if s.addingPerson}
													<div style="margin-top: 12px; padding: 12px; background-color: #0f1117; border: 1px solid #334155; border-radius: 6px;">
														<div style="margin-bottom: 8px;">
															<label
																for="new-person-name-{rowKey}"
																style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;"
															>
																Full name
															</label>
															<input
																id="new-person-name-{rowKey}"
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
															type="button"
															disabled={s.submittingNewPerson || !s.newPersonName.trim()}
															onclick={() => handleAddPerson(rowKey)}
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
											{#if s?.disposition !== null && s?.disposition !== undefined}
												<!-- Row is dispositioned — show nothing (status shown in col 2) -->
											{:else}
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
			<form method="POST" action="?/resolve" style="margin-top: 24px;">
				<input type="hidden" name="matches" value={matchesJson} />
				<button
					type="submit"
					disabled={continueSubmitting}
					onclick={() => (continueSubmitting = true)}
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
