<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { enhance } from '$app/forms';
	import ArgumentDetailsCard from '$lib/components/ArgumentDetailsCard.svelte';

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

	interface ParseStats {
		utterance_count: number;
		speaker_count: number;
		// Expanded fields from Plan 23-01 (PJOB-10)
		bench_count?: number | null;
		advocate_count?: number | null;
		total_speaker_count?: number | null;
		case_name?: string | null;
		argued_date?: string | null;
		primary_docket?: string | null;
		question_number?: number | null;
	}

	interface Job {
		id: number;
		status: string;
		current_step: string;
		error_message?: string | null;
		discrepancies?: Discrepancy[] | null;
		pdf_url?: string | null;
		spaces_key?: string | null;
		original_filename?: string | null;
		parse_stats?: ParseStats | null;
	}

	// Standalone script-level date formatter — reusable from any template scope
	// (including the {#each STEP_ORDER} loop). NOT the same as the {@const formatArgDate}
	// scoped inside {#if data.argument} (Pitfall 5 — that one is not accessible here).
	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '—';
		const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
		return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	// ──────────────────────────────────────────────────────────────────────────
	// Polling (D-15/D-16 — Pattern 1 from RESEARCH.md)
	// liveJob mirrors data.job but is updated by direct 1s fetch polling.
	// invalidateAll() has a known latency in propagating prop changes in this
	// project (CR-03); direct $state + fetch bypasses that entirely.
	// ──────────────────────────────────────────────────────────────────────────

	// PIPE-18 (D-03): last-known-step fallback — when current_step is null during
	// a running→running step transition, the badge stays on the last known step
	// rather than flashing all badges to pending.
	let lastKnownStep = $state<string | null>(data?.job?.current_step ?? null);

	// liveJob: $state copy of the job that polling updates directly.
	// The sync effect below keeps it in step with SvelteKit load re-runs (Ctrl+R, nav).
	let liveJob = $state(data.job);
	$effect(() => { liveJob = data.job; });

	$effect(() => {
		const TERMINAL = new Set(['completed', 'failed', 'paused']);
		if (!liveJob?.status || TERMINAL.has(liveJob.status)) return;

		const interval = setInterval(async () => {
			const res = await fetch(`/admin/pipeline/${liveJob.id}`, {
				headers: { Accept: 'application/json' },
			});
			if (!res.ok) return;
			let fresh: typeof liveJob | null = null;
			try {
				fresh = await res.json();
			} catch {
				return; // malformed response — skip this tick
			}
			if (!fresh) return;
			liveJob = fresh;
			// PIPE-18 (D-02): diagnostic log — captures null current_step transitions
			console.debug('[poll]', { status: liveJob.status, current_step: liveJob.current_step });
			// PIPE-18 (D-03): update lastKnownStep whenever current_step is non-null
			if (liveJob.current_step !== null && liveJob.current_step !== undefined) {
				lastKnownStep = liveJob.current_step;
			}
			// On terminal transition, refresh data.argument and data.participants —
			// those props come from the server load and are not covered by job polling.
			if (TERMINAL.has(fresh.status)) {
				await invalidateAll();
			}
		}, 1000);

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
		// PIPE-19: custom combobox state
		comboQuery: string;
		comboOpen: boolean;
		comboHighlight: number; // index into filteredCandidates (-1 = none)
	}

	let rowStates = $state<Record<string, RowState>>({});

	// Initialise row states when discrepancies arrive (status=paused).
	// Evict stale keys first (CR-04: labels from a prior resolve attempt that are
	// no longer in the current discrepancy set) so outdated dispositions cannot
	// persist into a new resolve run.
	// Only initialise for rows not already tracked (preserve in-progress work on re-renders).
	// HIT rows (auto_resolved === true) start pre-dispositioned as 'confirmed' so no
	// explicit Confirm click is required ([07-07] Gap 1a fix).
	$effect(() => {
		const disc = liveJob.discrepancies;
		if (!disc) return;
		const incomingKeys = new Set(disc.map((r: Discrepancy) => r.raw_speaker_label));
		for (const key of Object.keys(rowStates)) {
			if (!incomingKeys.has(key)) {
				delete rowStates[key];
			}
		}
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
					// PIPE-19: custom combobox state
					comboQuery: '',
					comboOpen: false,
					comboHighlight: -1,
				};
			}
		}
	});

	// All rows dispositioned → show Continue Resolve button.
	// Requires both disposition set AND person_id resolved (not null),
	// so a "Confirm" with no auto_match_id cannot prematurely enable the button.
	let allDispositioned = $derived.by(() => {
		const disc = liveJob.discrepancies;
		if (!disc || disc.length === 0) return false;
		return disc.every((row: Discrepancy) => {
			const s = rowStates[row.raw_speaker_label];
			return s?.disposition !== null && s?.disposition !== undefined && s?.person_id !== null;
		});
	});

	// Build the JSON matches array for the hidden form field.
	let matchesJson = $derived.by(() => {
		const disc = liveJob.discrepancies;
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
		const current = job.current_step?.toLowerCase() as StepName | undefined;
		const currentIdx = current !== undefined ? STEP_ORDER.indexOf(current) : -1;
		const thisIdx = STEP_ORDER.indexOf(step);

		if (job.status === 'completed') return 'completed';
		if (job.status === 'failed') {
			// WR-03: when current_step is null (job failed before any step wrote it),
			// show the first step as failed and the rest as pending rather than all pending.
			if (currentIdx === -1) return step === STEP_ORDER[0] ? 'failed' : 'pending';
			if (step === current) return 'failed';
			return thisIdx < currentIdx ? 'completed' : 'pending';
		}
		if (job.status === 'paused' && step === 'resolve') return 'paused';
		if (job.status === 'paused') return thisIdx < currentIdx ? 'completed' : 'pending';
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
	// Phase 15: Advocate role selection state (D-08)
	// Keyed by participant_id (string); values are SideEnum strings.
	// Initialized from data.participants when available.
	// ──────────────────────────────────────────────────────────────────────────

	const ADVOCATE_LABEL_MAP: Record<string, string> = {
		PETITIONER: "Petitioner's Counsel",
		RESPONDENT: "Respondent's Counsel",
		AMICUS: 'Amicus Curiae',
		UNKNOWN: 'Counsel',
		ADVOCATE: 'Counsel', // legacy
	};

	// Initialized from loaded participants; updated on change.
	let advocateSides = $state<Record<string, string>>(
		Object.fromEntries(
			(data.participants ?? [])
				.filter((p: { side: string | null; participant_id: number }) => p.side && p.side !== 'BENCH')
				.map((p: { participant_id: number; side: string | null }) => [
					String(p.participant_id),
					p.side ?? 'UNKNOWN',
				]),
		),
	);

	// Phase 15: Approve form submit state
	let approveSubmitting = $state(false);

	// Phase 15: Re-run two-step confirm state (D-10)
	let rerunConfirming = $state(false);
	let rerunSubmitting = $state(false);

	// ──────────────────────────────────────────────────────────────────────────
	// Phase 21 Plan 02: Delete run two-step confirm state (ADMIN-02)
	// Pitfall 7: $effect resets state when navigating between job pages.
	// ──────────────────────────────────────────────────────────────────────────

	let deleteConfirming = $state(false);
	let deleteSubmitting = $state(false);

	$effect(() => {
		// Reference data.job.id so this effect re-runs on soft navigation to a different job.
		data.job.id;
		deleteConfirming = false;
		deleteSubmitting = false;
	});

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

	// Phase 15: Determine if a discrepancy row resolves to a BENCH participant (Justice).
	// Returns true if the row's resolved person_id maps to a BENCH side in data.participants.
	function isRowBench(personId: number | null): boolean {
		if (personId == null) return false;
		const participant = (data.participants ?? []).find(
			(p: { person_id: number; side: string | null }) => p.person_id === personId,
		);
		return participant?.side === 'BENCH';
	}

	// PIPE-19: Svelte action — close combobox dropdown when operator clicks outside the container.
	function comboOutsideClick(container: HTMLElement, rowKey: string) {
		function handleClick(e: MouseEvent) {
			if (!container.contains(e.target as Node)) {
				const s = rowStates[rowKey];
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
			}
		};
	}
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			Run #{liveJob.id}
		</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		<!-- Argument Details card (D-02, AEDIT-04, PJOB-03/04/05/06) — replaces old Argument Metadata form -->
		<!-- ArgumentDetailsCard owns its own form; action prop drives save target (D-01) -->
		<!-- data.savedValues/hints are guaranteed non-null when data.argument != null (load() contract) -->
		{#if data.argument != null}
			<ArgumentDetailsCard
				savedValues={data.savedValues!}
				hints={data.hints!}
				action="?/saveJobMetadata"
				form={form}
			/>
		{/if}

		<!-- Ready to publish CTA: shown when run is completed and argument is in draft status -->
		{#if data.argument && liveJob.status === 'completed'}
			{@const arg = data.argument}
			{@const argStatus = arg.status ?? (arg.published_at != null ? 'published' : arg.resolved_at != null ? 'draft' : 'pipeline')}
			{#if argStatus === 'draft'}
				<div
					style="
						border: 1px solid #93c5fd;
						border-radius: 8px;
						padding: 24px;
						margin-bottom: 24px;
					"
				>
					<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0; line-height: 1.2;">
						Ready to publish
					</h2>
					<p style="font-size: 16px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
						This argument has been resolved. Review and publish it from the argument editor.
					</p>
					<a
						href="/admin/arguments/{arg.id}"
						style="
							display: inline-block;
							font-size: 14px;
							font-weight: 400;
							color: #e2e8f0;
							background: transparent;
							border: 1px solid #93c5fd;
							border-radius: 6px;
							padding: 10px 20px;
							min-height: 44px;
							text-decoration: none;
							box-sizing: border-box;
						"
					>
						Go to argument editor
					</a>
				</div>
			{/if}
		{/if}

		<!-- Step cards container — aria-live polite so screen readers announce step changes -->
		<div
			aria-live="polite"
			style="display: flex; flex-direction: column; gap: 16px;"
		>
			{#each STEP_ORDER as step}
				{@const effectiveJob = (liveJob.status === 'running' && liveJob.current_step === null)
					? { ...liveJob, current_step: lastKnownStep }
					: liveJob}
				{@const status = stepStatus(step, effectiveJob as Job)}
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

					<!-- Parse stat rows (D-10/PIPE-21, PJOB-10/11/12) — only when parse completed -->
					{#if step === 'parse' && status === 'completed' && liveJob.parse_stats}
						{@const ps = liveJob.parse_stats}
						<div style="margin-top: 12px; display: flex; flex-direction: column;">
							<!-- Utterances — never N/A (PJOB-11) -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Utterances</span>
								<span style="font-size: 16px; color: #e2e8f0;">{ps.utterance_count}</span>
							</div>
							<!-- Bench speakers (PJOB-10) — N/A when null -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Bench speakers</span>
								{#if ps.bench_count != null}
									<span style="font-size: 16px; color: #e2e8f0;">{ps.bench_count}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Advocate speakers (PJOB-10) — N/A when null -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Advocate speakers</span>
								{#if ps.advocate_count != null}
									<span style="font-size: 16px; color: #e2e8f0;">{ps.advocate_count}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Total speakers (PJOB-10) — N/A when null -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Total speakers</span>
								{#if ps.total_speaker_count != null}
									<span style="font-size: 16px; color: #e2e8f0;">{ps.total_speaker_count}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Case name from cover_metadata (PJOB-10/12) — NOT data.argument.case_name (Pitfall 7) -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Case name</span>
								{#if ps.case_name}
									<span style="font-size: 16px; color: #e2e8f0;">{ps.case_name}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Argued date from cover_metadata (PJOB-10/12) — formatted via formatDate -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Argued</span>
								{#if ps.argued_date}
									<span style="font-size: 16px; color: #e2e8f0;">{formatDate(ps.argued_date)}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Docket(s) from cover_metadata (PJOB-10/12) — read-only pill or N/A -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Docket(s)</span>
								{#if ps.primary_docket}
									<span
										style="
											display: inline-flex;
											align-items: center;
											background-color: #0f1117;
											border: 1px solid #334155;
											border-radius: 4px;
											padding: 2px 8px;
											font-size: 14px;
											font-weight: 400;
											color: #94a3b8;
											height: 24px;
										"
									>{ps.primary_docket}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
							<!-- Question number from Argument.question_number (PJOB-10/12) — N/A when null -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Question number</span>
								{#if ps.question_number != null}
									<span style="font-size: 16px; color: #e2e8f0;">{ps.question_number}</span>
								{:else}
									<span style="font-size: 16px; color: #94a3b8; font-style: italic;">N/A</span>
								{/if}
							</div>
						</div>
					{/if}

					<!-- View source PDF link (PJOB-09): inside Ingest card only -->
					{#if step === 'ingest' && (liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename)}
						<div style="margin-top: 12px;">
							<a
								href="/admin/pipeline/{liveJob.id}/pdf"
								style="font-size: 14px; color: #93c5fd; text-decoration: none;"
							>View source PDF</a>
						</div>
					{/if}

					<!-- Discrepancy review (D-11–D-14): only when resolve step is paused -->
					{#if step === 'resolve' && liveJob.status === 'paused' && data.peopleLoadError}
						<p role="alert" style="margin-top: 12px; font-size: 13px; color: #fbbf24; font-family: monospace;">
							Warning: could not load people list — typeahead may be incomplete. ({data.peopleLoadError})
						</p>
					{/if}
					{#if step === 'resolve' && liveJob.status === 'paused' && liveJob.discrepancies?.length}
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
											width: 28%;
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
											width: 39%;
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
											width: 18%;
										"
									>Role</th>
									<th
										scope="col"
										style="
											font-size: 14px;
											font-weight: 400;
											color: #94a3b8;
											border-bottom: 1px solid #334155;
											padding: 8px 0;
											text-align: left;
											width: 15%;
										"
									>Action</th>
								</tr>
							</thead>
							<tbody>
								{#each liveJob.discrepancies as row (row.raw_speaker_label)}
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
												<!-- PIPE-19: custom combobox — replaces native datalist typeahead -->
												{@const comboId = `listbox-${rowKey.replace(/\s+/g, '-')}`}
												{@const candidates = getRowCandidates(row, rowKey)}
												{@const filteredCandidates = candidates.filter(c => {
													const text = c.role_name ? `${c.full_name} ${c.role_name}` : c.full_name;
													return text.toLowerCase().includes((s.comboQuery ?? '').toLowerCase());
												})}
												<div
													style="position: relative; width: 100%;{s.addingPerson ? ' display: none;' : ''}"
													use:comboOutsideClick={rowKey}
												>
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
																s.comboHighlight = Math.min(s.comboHighlight + 1, filteredCandidates.length);
															} else if (e.key === 'ArrowUp') {
																e.preventDefault();
																s.comboHighlight = Math.max(s.comboHighlight - 1, -1);
															} else if (e.key === 'Enter') {
																e.preventDefault();
																if (s.comboHighlight === filteredCandidates.length) {
																	// "Add new person" highlighted
																	handleSelectPerson(rowKey, '__add_new__');
																	s.comboOpen = false;
																} else if (s.comboHighlight >= 0 && s.comboHighlight < filteredCandidates.length) {
																	const picked = filteredCandidates[s.comboHighlight];
																	s.comboQuery = picked.full_name;
																	handleSelectPerson(rowKey, picked.id.toString());
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
																margin-top: 4px;
																background-color: #1e293b;
																border: 1px solid #334155;
																border-radius: 6px;
																padding: 4px 0;
																max-height: 240px;
																overflow-y: auto;
																z-index: 10;
																list-style: none;
																margin: 4px 0 0 0;
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
																	onmouseenter={() => { s.comboHighlight = idx; }}
																	onclick={() => {
																		s.comboQuery = candidate.full_name;
																		handleSelectPerson(rowKey, candidate.id.toString());
																		s.comboOpen = false;
																	}}
																>
																	{candidate.full_name}{#if candidate.role_name}<span style="font-size: 14px; color: #94a3b8; margin-left: 4px;">({candidate.role_name})</span>{/if}
																</li>
															{/each}
															<!-- "Add new person" always last, regardless of query -->
															<li
																role="option"
																aria-selected={false}
																style="
																	padding: 8px 12px;
																	font-size: 14px;
																	color: #93c5fd;
																	cursor: pointer;
																	background-color: {s.comboHighlight === filteredCandidates.length ? '#334155' : '#1e293b'};
																"
																onmouseenter={() => { s.comboHighlight = filteredCandidates.length; }}
																onclick={() => {
																	handleSelectPerson(rowKey, '__add_new__');
																	s.comboOpen = false;
																}}
															>
																Add new person
															</li>
														</ul>
													{/if}
												</div>

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

										<!-- Column 3: Advocate role dropdown (Phase 15 D-08) -->
										<!-- Only shown for non-BENCH participants while argument is in pipeline state -->
										<td
											style="
												font-size: 16px;
												color: #e2e8f0;
												border-bottom: 1px solid #334155;
												padding: 12px 0;
												padding-right: 12px;
											"
										>
											{#if data.argument?.status === 'pipeline' && !isRowBench(s?.person_id ?? null)}
												{@const pid = (data.participants ?? []).find((p: { person_id: number; participant_id: number }) => p.person_id === s?.person_id)?.participant_id}
												{#if pid != null}
													<select
														value={advocateSides[String(pid)] ?? 'UNKNOWN'}
														onchange={(e) => {
															advocateSides[String(pid)] = (e.target as HTMLSelectElement).value;
														}}
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
														<option value="PETITIONER">Petitioner's Counsel</option>
														<option value="RESPONDENT">Respondent's Counsel</option>
														<option value="AMICUS">Amicus Curiae</option>
														<option value="UNKNOWN">Counsel</option>
													</select>
												{:else}
													<span style="color: #94a3b8; font-size: 14px;">—</span>
												{/if}
											{:else if data.argument?.status !== 'pipeline'}
												<!-- Post-approval: read-only role label -->
												{@const pid2 = (data.participants ?? []).find((p: { person_id: number; participant_id: number }) => p.person_id === s?.person_id)?.participant_id}
												{@const currentSide = pid2 != null ? (advocateSides[String(pid2)] ?? 'UNKNOWN') : null}
												{#if currentSide != null && !isRowBench(s?.person_id ?? null)}
													<span style="font-size: 14px; color: #94a3b8;">
														{ADVOCATE_LABEL_MAP[currentSide] ?? 'Counsel'}
													</span>
												{/if}
											{/if}
										</td>

										<!-- Column 4: Action buttons -->
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
												<!-- MISS row not yet dispositioned — Confirm (if auto_match_id) + Select -->
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
														Select
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
		{#if liveJob.status === 'paused' && allDispositioned}
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
							// Reset before update so re-render sees correct state even if
							// invalidateAll is slow to flip liveJob.status (CR-03 race fix)
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
			{#if form?.error}
				<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
					{form.error}
				</p>
			{/if}
		{/if}

		<!-- Phase 15 D-09: Create Argument button — visible while argument is in pipeline state -->
		{#if data.argument?.status === 'pipeline'}
			<form
				method="POST"
				action="?/approve"
				use:enhance={({ formData }) => {
					// Inject advocate side assignments into FormData at submit time
					for (const [pid, side] of Object.entries(advocateSides)) {
						formData.append(`participant_side[${pid}]`, side);
					}
					approveSubmitting = true;
					return async ({ result, update }) => {
						approveSubmitting = false;
						if (result.type === 'failure') {
							await update();
						} else {
							await update({ reset: false });
						}
					};
				}}
				style="margin-top: 24px;"
			>
				<button
					type="submit"
					disabled={approveSubmitting}
					style="
						width: 100%;
						min-height: 44px;
						font-size: 16px;
						font-weight: 600;
						color: #e2e8f0;
						background-color: #1e293b;
						border: 1px solid #93c5fd;
						border-radius: 6px;
						padding: 12px 24px;
						cursor: pointer;
						{approveSubmitting ? 'opacity: 0.7; cursor: not-allowed;' : ''}
					"
				>
					{approveSubmitting ? 'Creating…' : 'Create Argument'}
				</button>
			</form>
			{#if form?.approveError}
				<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
					{form.approveError}
				</p>
			{/if}
		{/if}

		<!-- Phase 15 D-10: Post-approval read-only state — notice + Re-run button -->
		{#if data.argument != null && data.argument.status !== 'pipeline'}
			<div style="margin-top: 24px;">
				<p style="font-size: 16px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
					This run has been approved. The argument is now in draft.
				</p>
				<!-- Re-run two-step confirm (D-10) -->
				{#if rerunConfirming}
					<div style="display: flex; align-items: center; gap: 16px;">
						<form
							method="POST"
							action="?/rerun"
							use:enhance={() => {
								rerunSubmitting = true;
								return async ({ result, update }) => {
									rerunSubmitting = false;
									rerunConfirming = false;
									if (result.type === 'failure') {
										await update();
									} else {
										await update({ reset: false });
									}
								};
							}}
						>
							<button
								type="submit"
								disabled={rerunSubmitting}
								style="
									font-size: 14px;
									font-weight: 400;
									color: #e2e8f0;
									background-color: #1e293b;
									border: 1px solid #334155;
									border-radius: 6px;
									padding: 8px 16px;
									min-height: 36px;
									cursor: pointer;
									{rerunSubmitting ? 'opacity: 0.7; cursor: not-allowed;' : ''}
								"
							>
								{rerunSubmitting ? 'Starting…' : 'Confirm re-run — this starts a new pipeline run'}
							</button>
						</form>
						<button
							type="button"
							onclick={() => { rerunConfirming = false; }}
							style="
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								background: transparent;
								border: none;
								padding: 0;
								cursor: pointer;
							"
						>
							Cancel
						</button>
					</div>
				{:else}
					<button
						type="button"
						onclick={() => { rerunConfirming = true; }}
						style="
							font-size: 14px;
							font-weight: 400;
							color: #e2e8f0;
							background-color: #1e293b;
							border: 1px solid #334155;
							border-radius: 6px;
							padding: 8px 16px;
							min-height: 36px;
							cursor: pointer;
						"
					>
						Re-run with same source
					</button>
				{/if}
				{#if form?.rerunError}
					<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
						{form.rerunError}
					</p>
				{/if}
			</div>
		{/if}

		<!-- Error panel (D-17): when status=failed; error_message rendered verbatim; no retry -->
		{#if liveJob.status === 'failed'}
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
				{#if liveJob.error_message}
					<p
						role="alert"
						style="font-size: 16px; color: #ef4444; margin: 0 0 16px 0; font-family: monospace; white-space: pre-wrap; word-break: break-word;"
					>
						Error: {liveJob.error_message}
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

		<!-- ParticipantList (PEOPLE-04, D-02, D-03): only when completed AND participants exist -->
		{#if liveJob.status === 'completed' && data.participants.length > 0}
			<div
				style="
					margin-top: 32px;
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
				"
			>
				<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
					{data.participants.length} resolved participant{data.participants.length === 1 ? '' : 's'}
				</h2>
				<ul style="list-style: none; padding: 0; margin: 0 0 16px 0;">
					{#each data.participants as p, i (p.participant_id)}
						<li
							style="
								display: flex;
								align-items: center;
								font-size: 16px;
								color: #e2e8f0;
								padding: 8px 0;
								{i < data.participants.length - 1 ? 'border-bottom: 1px solid #334155;' : ''}
							"
						>
							<span style="flex: 1;">{p.full_name}{#if p.role_name}<span style="color: #94a3b8; font-size: 14px; margin-left: 8px;">({p.role_name})</span>{/if}</span>
							{#if p.side !== 'BENCH'}
								{#if data.argument?.status === 'pipeline'}
									<select
										value={advocateSides[String(p.participant_id)] ?? 'UNKNOWN'}
										onchange={(e) => { advocateSides[String(p.participant_id)] = (e.currentTarget as HTMLSelectElement).value; }}
										style="margin-left: 12px; background-color: #1e3a5f; color: #e2e8f0; border: 1px solid #334155; border-radius: 4px; padding: 4px 8px; font-size: 14px;"
									>
										<option value="PETITIONER">Petitioner's Counsel</option>
										<option value="RESPONDENT">Respondent's Counsel</option>
										<option value="AMICUS">Amicus Curiae</option>
										<option value="UNKNOWN">Counsel</option>
									</select>
								{:else}
									<span style="color: #94a3b8; font-size: 14px; margin-left: 12px;">{ADVOCATE_LABEL_MAP[advocateSides[String(p.participant_id)] ?? (p.side ?? 'UNKNOWN')] ?? 'Counsel'}</span>
								{/if}
							{/if}
						</li>
					{/each}
				</ul>
				<a
					href="/admin/people?incomplete=1"
					style="
						display: inline-block;
						font-size: 14px;
						font-weight: 400;
						color: #93c5fd;
						border: 1px solid #334155;
						border-radius: 6px;
						padding: 8px 16px;
						text-decoration: none;
					"
				>
					Review people →
				</a>
			</div>
		{/if}

		<!-- Danger Zone — pipeline run delete section (ADMIN-02, D-09) -->
		<!-- Last card on the page per UI-SPEC Layout Contract. -->
		<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
			<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
				Danger Zone
			</h2>

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
					Delete run
				</button>
			{/if}

			<!-- Delete error (returned by fail() from the delete action) -->
			{#if form?.deleteError}
				<p
					role="alert"
					style="color: #ef4444; font-size: 14px; font-weight: 400; margin: 8px 0 0 0;"
				>{form.deleteError}</p>
			{/if}
		</div>

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
