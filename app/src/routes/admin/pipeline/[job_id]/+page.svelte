<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { enhance } from '$app/forms';
	import ArgumentDetailsCard from '$lib/admin/ArgumentDetailsCard.svelte';
	import CopyableExtractedValue from '$lib/admin/CopyableExtractedValue.svelte';
	import RunStatusCard from '$lib/admin/RunStatusCard.svelte';
	import ResolveCard from '$lib/admin/ResolveCard.svelte';
	import FailedStepGuidance from '$lib/admin/FailedStepGuidance.svelte';

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
		// Phase 44 Plan 07 (RESOLVE-10): the job's real ingestion provenance
		// (api/schemas/admin_jobs.py), threaded into the Resolve card below.
		// Optional so a poll tick or fixture that omits this still type-checks.
		source?: 'pdf' | 'corpus';
	}

	// Standalone script-level date formatter — reusable from any template scope
	// (including the {#each STEP_ORDER} loop). NOT the same as the {@const formatArgDate}
	// scoped inside {#if data.argument} (Pitfall 5 — that one is not accessible here).
	function formatDate(iso: string | null | undefined): string {
		if (!iso) return '—';
		const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
		if (!match) return iso;
		return match[2] + '/' + match[3] + '/' + match[1];
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
			// On terminal transition, refresh data.argument/participants/readiness/
			// failedRecovery/resolveRows — those props come from the server load and
			// are not covered by job polling.
			if (TERMINAL.has(fresh.status)) {
				await invalidateAll();
			}
		}, 1000);

		return () => clearInterval(interval);
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

	// Phase 25 (D-01, PJOB-01): source PDF link surfaces in the run status card,
	// derived the same way the pre-Phase-25 Ingest step card link was derived.
	let pdfHref = $derived(
		liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename
			? `/admin/pipeline/${liveJob.id}/pdf`
			: null,
	);
</script>

<main style="background-color: #0f1117; min-height: 100vh;">
	<header style="background-color: #1e293b; border-bottom: 1px solid #334155; padding: 16px 24px;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0;">
			Run #{liveJob.id}
		</h1>
	</header>

	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">
		<!-- Phase 25: Run status card — first workflow card after the page header (D-01 through D-04, D-18,
		     D-20, D-21, PJOB-01, PJOB-02, PJOB-20). Replaces the old floating Create Argument button and
		     the old "Ready to publish" / post-approval provenance panels below. -->
		<RunStatusCard
			jobStatus={liveJob.status}
			{pdfHref}
			readiness={data.readiness}
			approveError={form?.approveError}
		/>

		<!-- Argument Details card (D-02, AEDIT-04, PJOB-03/04/05/06) — replaces old Argument Metadata form -->
		<!-- ArgumentDetailsCard owns its own form; action prop drives save target (D-01) -->
		<!-- data.savedValues/hints are guaranteed non-null when data.argument != null (load() contract) -->
		<!-- Phase 25 (D-18, D-19): readonly once the linked argument has left the pipeline status -->
		{#if data.argument != null}
			<ArgumentDetailsCard
				savedValues={data.savedValues!}
				hints={data.hints!}
				action="?/saveJobMetadata"
				readonly={data.metadataReadonly}
				form={form}
			/>
		{/if}

		<!-- Step cards container — aria-live polite so screen readers announce step changes -->
		<div
			aria-live="polite"
			style="display: flex; flex-direction: column; gap: 16px; margin-bottom: 24px;"
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
							<!--
								Phase 38 (D-19/D-20/D-21): these four readouts have no independently
								stored raw/confidence — cover_metadata pass-through and the
								Argument.question_number column carry only the interpreted value
								(PJOB-10/12). Confidence uses an explicit "Medium" qualitative
								fallback (never a fabricated figure) and raw uses the exact
								underlying source text, which genuinely differs from the displayed
								interpretation for argued date (raw ISO string vs. formatted date).
							-->
							<!-- Case name from cover_metadata (PJOB-10/12) — NOT data.argument.case_name (Pitfall 7) -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Case name</span>
								<CopyableExtractedValue value={ps.case_name} copyLabel="Copy case name" confidence="Medium" raw={ps.case_name} />
							</div>
							<!-- Argued date from cover_metadata (PJOB-10/12) — formatted via formatDate; raw is the exact ISO source -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Argued</span>
								<CopyableExtractedValue value={ps.argued_date ? formatDate(ps.argued_date) : null} copyLabel="Copy argued date" confidence="Medium" raw={ps.argued_date} />
							</div>
							<!-- Docket(s) from cover_metadata (PJOB-10/12) — read-only pill or N/A -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Docket(s)</span>
								<CopyableExtractedValue value={ps.primary_docket} copyLabel="Copy docket" variant="pill" confidence="Medium" raw={ps.primary_docket} />
							</div>
							<!-- Question number from Argument.question_number (PJOB-10/12) — N/A when null -->
							<div style="margin-bottom: 12px;">
								<span style="display: block; font-size: 14px; font-weight: 400; color: #94a3b8; margin-bottom: 4px;">Question number</span>
								<CopyableExtractedValue value={ps.question_number != null ? String(ps.question_number) : null} copyLabel="Copy question number" confidence="Medium" raw={ps.question_number != null ? String(ps.question_number) : null} />
							</div>
						</div>
					{/if}

					<!-- View source PDF link (PJOB-09): inside Ingest card only -->
					{#if step === 'ingest' && (liveJob.spaces_key || liveJob.pdf_url || liveJob.original_filename)}
						<div style="margin-top: 12px;">
							<a
								href="/admin/pipeline/{liveJob.id}/pdf"
								target="_blank"
								rel="noopener noreferrer"
								style="font-size: 14px; color: #93c5fd; text-decoration: none;"
							>View source PDF</a>
						</div>
					{/if}

					<!-- Phase 25 (D-05 through D-08, PJOB-08, PJOB-22 supersession): failed-step
					     recovery guidance lives inside the failed step's own card, replacing the
					     old standalone bottom error panel. -->
					{#if status === 'failed'}
						<FailedStepGuidance
							failedRecovery={data.failedRecovery}
							fallbackErrorMessage={liveJob.error_message}
						/>
					{/if}
				</div>
			{/each}
		</div>

		<!-- Phase 25: Restructured Resolve card (D-10 through D-19, D-21, PJOB-14 through 18, 21).
		     Replaces the old inline discrepancy review table, advocate side dropdowns, and the
		     resolved-participants listing below. Only rendered once the job's argument has
		     participant rows to resolve. -->
		{#if data.resolveRows && data.resolveRows.length > 0}
			<ResolveCard
				resolveRows={data.resolveRows}
				discrepancies={liveJob.discrepancies ?? null}
				people={data.people ?? []}
				peopleLoadError={data.peopleLoadError}
				jobStatus={liveJob.status}
				readonlyMode={data.resolveCardReadonly}
				resolveFormError={form?.error}
				source={data.job.source ?? 'pdf'}
				jobId={liveJob.id}
			/>
		{/if}

		<!-- Provenance/participant summary — link to the People directory's incomplete-metadata
		     filter. Per-participant name/role/side detail now lives in the Resolve card above;
		     this stays a lightweight pointer rather than a duplicate listing. -->
		{#if liveJob.status === 'completed' && data.participants.length > 0}
			<div
				style="
					margin-top: 32px;
					background-color: #1e293b;
					border: 1px solid #334155;
					border-radius: 8px;
					padding: 24px;
					margin-bottom: 24px;
				"
			>
				<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
					{data.participants.length} resolved participant{data.participants.length === 1 ? '' : 's'}
				</h2>
				<a
					href="/admin/people?tab=bench&missing=name%20review"
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

		<!-- Danger Zone — pipeline run delete section (ADMIN-02, D-09, D-22) -->
		<!-- Last card on the page in every state per UI-SPEC Layout Contract. -->
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
