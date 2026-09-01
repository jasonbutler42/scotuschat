<svelte:head>
	<title>Pipeline Runner — SCOTUS Chat Admin</title>
</svelte:head>

<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import DocketPillInput from '$lib/admin/DocketPillInput.svelte';

	let { data, form } = $props();

	// IncompleteToggle state — mirrors the server-side incomplete flag (D-11, D-13).
	// $derived keeps it in sync when the load re-runs after navigation.
	let incomplete = $derived(data.incomplete ?? false);

	function handleToggle() {
		if (incomplete) {
			goto('/admin/pipeline');
		} else {
			goto('/admin/pipeline?incomplete=1');
		}
	}

	// Mode toggle state: 'url' or 'upload'. Defaults to URL mode.
	let mode = $state<'url' | 'upload'>('url');

	// Submitting state: used to disable the Start Run button and change its label.
	let submitting = $state(false);

	// Docket preflight state (D-03/D-04/D-05/D-06)
	let questionInput = $state('1');
	let duplicateWarning = $state<{ argumentId: number; docket: string; question: string } | null>(null);
	let preflightCleared = $state(false);
	let formEl: HTMLFormElement;

	// Poll unconditionally — we need to detect runs started in other tabs, so we can't
	// guard on data.jobs (which only updates after an invalidation we'd never start).
	$effect(() => {
		const interval = setInterval(async () => {
			await invalidateAll();
		}, 1000);

		return () => clearInterval(interval);
	});

	// On bfcache restore (Back after a form-action redirect), reload page data
	// so the job list reflects the current state without a manual refresh.
	$effect(() => {
		async function onPageShow(e: PageTransitionEvent) {
			if (!e.persisted) return;
			await invalidateAll();
		}
		window.addEventListener('pageshow', onPageShow);
		return () => window.removeEventListener('pageshow', onPageShow);
	});

	function setMode(m: 'url' | 'upload') {
		mode = m;
	}

	async function handleSubmit(e: SubmitEvent) {
		// Read pill values from the form's hidden inputs (Pitfall 4) — docketInput no
		// longer exists in this scope after the DocketPillInput extraction.
		const pillValues = [
			...(formEl.querySelectorAll('input[name="docket[]"]') as NodeListOf<HTMLInputElement>)
		].map((i) => i.value);

		// If no pills OR preflight already cleared → let the form submit normally
		if (pillValues.length === 0 || preflightCleared) {
			submitting = true;
			return;
		}

		// One or more pills present and not yet cleared — run per-pill preflight
		e.preventDefault();

		for (const docket of pillValues) {
			try {
				const res = await fetch(
					`/admin/pipeline/check-duplicate?docket=${encodeURIComponent(docket)}&question=${encodeURIComponent(questionInput)}`
				);
				// WR-02: check res.ok before parsing — a non-OK response (e.g. 400, 502) returns
				// a JSON body without 'exists', which is falsy and would silently bypass the duplicate gate.
				if (!res.ok) {
					console.warn('[preflight] check-duplicate returned', res.status, '— proceeding');
					preflightCleared = true;
					(e.target as HTMLFormElement).requestSubmit();
					return;
				}
				const data = await res.json();
				if (data.exists) {
					duplicateWarning = { argumentId: data.argument_id, docket, question: questionInput };
					return; // stop on first match — banner names this specific docket (D-09)
				}
			} catch {
				// Network error — allow submit to proceed so the operator is not blocked
				preflightCleared = true;
				(e.target as HTMLFormElement).requestSubmit();
				return;
			}
		}

		// All pills cleared preflight with no match
		preflightCleared = true;
		(e.target as HTMLFormElement).requestSubmit();
	}

	// StatusBadge helper: returns inline style string for a given job status.
	// Phase 26 gap closure (PLIST-05): isArchived takes precedence, mirroring
	// RunStatusCard.svelte's already_created override (grey --color-status-archived).
	function badgeStyle(status: string, isArchived: boolean = false): string {
		if (isArchived) {
			return `border: 1px solid var(--color-status-archived); border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-surface); color: var(--color-status-archived); display: inline-block;`;
		}
		const colors: Record<string, string> = {
			pending: 'var(--color-text-secondary)',
			running: 'var(--color-accent)',
			completed: 'var(--color-status-published)',
			paused: 'var(--color-status-warning)',
			failed: 'var(--color-destructive)',
		};
		const color = colors[status] ?? 'var(--color-text-secondary)';
		return `border: 1px solid ${color}; border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-surface); color: ${color}; display: inline-block;`;
	}

	// Compound badge (D-13/D-15/D-16): combines current_step and status, e.g. "Parse · Running".
	// "paused" maps to operator-friendly label "Needs Review".
	// Phase 26 gap closure (PLIST-05): isArchived takes precedence over the
	// compound step/status label, mirroring RunStatusCard.svelte's Archived override.
	function badgeLabel(
		status: string,
		currentStep: string | null | undefined,
		isArchived: boolean = false,
	): string {
		if (isArchived) {
			return 'Archived';
		}
		const statusLabels: Record<string, string> = {
			pending: 'Pending',
			running: 'Running',
			completed: 'Completed',
			paused: 'Needs Review',
			failed: 'Failed',
		};
		const stepLabels: Record<string, string> = {
			ingest: 'Ingest',
			parse: 'Parse',
			resolve: 'Resolve',
		};
		const statusLabel = statusLabels[status] ?? status;
		if (status === 'completed' || !currentStep) {
			return statusLabel;
		}
		const stepLabel = stepLabels[currentStep] ?? currentStep;
		return stepLabel + ' · ' + statusLabel;
	}

	// sourceTagStyle/sourceLabel: renders "PDF" or "Corpus" as a quiet, neutral tag
	// distinct from the semantic-color compound status badge (Phase 30 gap closure).
	function sourceLabel(source: 'pdf' | 'corpus'): string {
		return source === 'corpus' ? 'Corpus' : 'PDF';
	}

	function sourceTagStyle(): string {
		return `border: 1px solid var(--color-text-secondary); border-radius: 4px; padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); background-color: var(--color-bg); color: var(--color-text-secondary); display: inline-block;`;
	}

	// Format ISO date string for display (date only — time detail not needed in history).
	function formatDate(iso: string): string {
		try {
			const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
			return new Date(y, m - 1, d).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return iso;
		}
	}
</script>

<!-- Page layout per 07-UI-SPEC /admin/pipeline Page Layout Contract -->
<main style="background-color: var(--color-bg); min-height: 100vh;">
	<!-- Page header bar -->
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
			Pipeline Runner
		</h1>
	</header>

	<!-- Inner content container -->
	<div style="max-width: 860px; margin: 0 auto; padding: var(--space-3xl) var(--space-xl);">

		<!-- New Run card -->
		<div
			style="
				background-color: var(--color-surface);
				border: 1px solid var(--color-border);
				border-radius: 8px;
				padding: var(--space-2xl);
			"
		>
			<h2
				style="
					font-size: var(--font-size-heading);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					margin: 0 0 var(--space-xl) 0;
					line-height: 1.2;
				"
			>
				New Run
			</h2>

			<!-- ModeToggle: "Enter URL" / "Upload File" per 07-UI-SPEC Component Inventory -->
			<div
				style="
					background-color: var(--color-bg);
					border: 1px solid var(--color-border);
					border-radius: 6px;
					padding: var(--space-xs);
					display: inline-flex;
					margin-bottom: var(--space-xl);
				"
			>
				<button
					type="button"
					aria-pressed={mode === 'url'}
					onclick={() => setMode('url')}
					style="
						font-size: var(--font-size-caption);
						padding: var(--space-sm) var(--space-lg);
						border: none;
						cursor: pointer;
						min-height: var(--touch-target-dense);
						border-radius: 4px;
						background-color: {mode === 'url' ? 'var(--color-surface)' : 'transparent'};
						color: {mode === 'url' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
						font-weight: {mode === 'url' ? 600 : 400};
					"
				>
					Enter URL
				</button>
				<button
					type="button"
					aria-pressed={mode === 'upload'}
					onclick={() => setMode('upload')}
					style="
						font-size: var(--font-size-caption);
						padding: var(--space-sm) var(--space-lg);
						border: none;
						cursor: pointer;
						min-height: var(--touch-target-dense);
						border-radius: 4px;
						background-color: {mode === 'upload' ? 'var(--color-surface)' : 'transparent'};
						color: {mode === 'upload' ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
						font-weight: {mode === 'upload' ? 600 : 400};
					"
				>
					Upload File
				</button>
			</div>

			<!-- Single form for both modes. enctype=multipart/form-data works for URL
			     and file modes. Hidden input carries the active mode so the server action
			     can branch on it (mode: 'url' | 'upload'). -->
			<form
				method="POST"
				enctype="multipart/form-data"
				onsubmit={handleSubmit}
				bind:this={formEl}
			>
				<!-- Hidden mode field — read by actions.default in +page.server.ts -->
				<input type="hidden" name="mode" value={mode} />

				{#if mode === 'url'}
					<!-- URL input -->
					<div style="margin-bottom: var(--space-lg);">
						<label
							for="pdf_url"
							style="
								display: block;
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
								margin-bottom: var(--space-sm);
							"
						>
							Transcript PDF URL
						</label>
						<input
							type="url"
							name="pdf_url"
							id="pdf_url"
							required
							placeholder="https://www.supremecourt.gov/..."
							style="
								display: block;
								width: 100%;
								background-color: var(--color-bg);
								border: 1px solid var(--color-border);
								border-radius: 6px;
								padding: var(--space-sm) var(--space-md);
								font-size: var(--font-size-body);
								color: var(--color-text-primary);
								box-sizing: border-box;
							"
						/>
					</div>
				{:else}
					<!-- File input — only rendered in upload mode so inactive field is not submitted -->
					<div style="margin-bottom: var(--space-lg);">
						<label
							for="pdf_file"
							style="
								display: block;
								font-size: var(--font-size-caption);
								font-weight: var(--font-weight-regular);
								color: var(--color-text-secondary);
								margin-bottom: var(--space-sm);
							"
						>
							PDF File
						</label>
						<input
							type="file"
							name="pdf_file"
							id="pdf_file"
							accept="application/pdf"
							required
							style="
								display: block;
								width: 100%;
								background-color: var(--color-bg);
								border: 1px solid var(--color-border);
								border-radius: 6px;
								padding: var(--space-sm) var(--space-md);
								font-size: var(--font-size-body);
								color: var(--color-text-primary);
								box-sizing: border-box;
							"
						/>
					</div>
				{/if}

				<!-- Docket pill input (PLIST-02, D-05/D-06, UI-SPEC Component 1) — optional; triggers preflight when filled -->
				<div style="margin-bottom: var(--space-lg);">
					<label
						for="primary_docket"
						style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
					>
						Docket number
					</label>
					<DocketPillInput initialValues={[]} name="docket[]" id="primary_docket" enforceShape />
				</div>

				<!-- Question number free-text field (PLIST-01, D-01/D-02, UI-SPEC Component 1) -->
				<div style="margin-bottom: var(--space-lg);">
					<label
						for="question_number"
						style="display: block; font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin-bottom: var(--space-sm);"
					>
						Question number
					</label>
					<input
						type="text"
						name="question_number"
						id="question_number"
						bind:value={questionInput}
						style="
							background-color: var(--color-bg);
							border: 1px solid var(--color-border);
							border-radius: 6px;
							padding: var(--space-sm) var(--space-md);
							font-size: var(--font-size-body);
							color: var(--color-text-primary);
							min-height: var(--touch-target);
							width: 100%;
							box-sizing: border-box;
						"
					/>
				</div>

				<!-- Duplicate warning banner (D-04/D-05/D-06, UI-SPEC Component 3) — shown when preflight finds a match -->
				{#if duplicateWarning}
					<div role="alert" style="background-color: var(--color-surface); border: 1px solid var(--color-status-warning); border-radius: 8px; padding: var(--space-lg); margin-bottom: var(--space-lg);">
						<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">⚠ Argument already exists</p>
						<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); margin: 0 0 var(--space-md) 0;">
							Docket {duplicateWarning.docket} Q{duplicateWarning.question} already has an argument.
							<a href="/admin/arguments/{duplicateWarning.argumentId}" style="color: var(--color-accent); text-decoration: underline;">View existing argument →</a>
						</p>
						<div style="display: flex; gap: var(--space-sm);">
							<button
								type="button"
								onclick={() => { duplicateWarning = null; preflightCleared = false; }}
								style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); background: transparent; border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) var(--space-lg); min-height: var(--touch-target-dense); cursor: pointer;"
							>
								Cancel
							</button>
							<button
								type="button"
								onclick={() => { preflightCleared = true; duplicateWarning = null; formEl.requestSubmit(); }}
								style="font-size: var(--font-size-caption); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); background: transparent; border: 1px solid var(--color-accent); border-radius: 6px; padding: var(--space-sm) var(--space-lg); min-height: var(--touch-target-dense); cursor: pointer;"
							>
								Start anyway
							</button>
						</div>
					</div>
				{/if}

				<!-- Form error: role=alert so screen readers announce it immediately (T-07-13) -->
				{#if form?.error}
					<p
						role="alert"
						style="
							color: var(--color-destructive);
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-regular);
							line-height: 1.5;
							margin: 0 0 var(--space-lg) 0;
						"
					>
						{form.error}
					</p>
				{/if}

				<!-- Start Run: full-width, 44px min-height (WCAG 2.5.5).
				     disabled attribute is a real attribute (not just opacity) while submitting. -->
				<button
					type="submit"
					disabled={submitting}
					style="
						display: block;
						width: 100%;
						min-height: var(--touch-target);
						background-color: var(--color-surface);
						border: 1px solid var(--color-border);
						border-radius: 6px;
						font-size: var(--font-size-body);
						font-weight: var(--font-weight-semibold);
						color: var(--color-text-primary);
						cursor: {submitting ? 'not-allowed' : 'pointer'};
						margin-top: var(--space-sm);
						opacity: {submitting ? 0.7 : 1};
					"
				>
					{submitting ? 'Starting…' : 'Start Run'}
				</button>
			</form>
		</div>

		<!-- All Runs history section -->
		<div style="margin-top: var(--space-2xl);">
			<!-- Section header row: h2 left, incomplete toggle right (D-13, 13-UI-SPEC §Layout Contract) -->
			<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-lg);">
				<h2
					style="
						font-size: var(--font-size-heading);
						font-weight: var(--font-weight-semibold);
						color: var(--color-text-primary);
						margin: 0;
						line-height: 1.2;
					"
				>
					All Runs
				</h2>

				<!-- IncompleteToggle (PIPE-20) — mirrors /admin/people pattern exactly -->
				<div style="display: flex; align-items: center; gap: var(--space-sm);">
					<button
						role="switch"
						aria-checked={incomplete}
						aria-label="Show incomplete only"
						onclick={handleToggle}
						style="
							position: relative;
							width: 44px;
							height: 24px;
							min-height: var(--touch-target);
							border-radius: 12px;
							border: 1px solid {incomplete ? 'var(--color-accent)' : 'var(--color-border)'};
							background-color: {incomplete ? 'rgba(147,197,253,0.2)' : 'var(--color-bg)'};
							cursor: pointer;
							padding: 0;
							flex-shrink: 0;
						"
					>
						<span
							style="
								position: absolute;
								top: 50%;
								transform: translateY(-50%) translateX({incomplete ? '22px' : '2px'});
								width: 18px;
								height: 18px;
								border-radius: 50%;
								background-color: {incomplete ? 'var(--color-accent)' : 'var(--color-text-secondary)'};
							"
						></span>
					</button>
					<span
						style="
							font-size: var(--font-size-caption);
							font-weight: var(--font-weight-regular);
							color: {incomplete ? 'var(--color-text-primary)' : 'var(--color-text-secondary)'};
						"
					>Show incomplete only</span>
				</div>
			</div>

			<!-- Phase 50 (D-19): this screen is honestly PDF-only now that the
			     corpus importer mints no AdminJob at all (plan 50-01) — a corpus
			     source tag can never render here by construction. -->
			<p
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-regular);
					color: var(--color-text-secondary);
					margin: 0 0 var(--space-lg) 0;
				"
			>
				This screen shows PDF-pipeline jobs only. Corpus arguments are
				reached through /admin/arguments and /admin/review.
			</p>

			{#if incomplete && (!data.jobs || data.jobs.length === 0)}
				<!-- Filter-on empty state: no paused/failed jobs (13-UI-SPEC §Component Inventory 3) -->
				<div
					style="
						background-color: var(--color-surface);
						border: 1px solid var(--color-border);
						border-radius: 8px;
						padding: var(--space-2xl);
						text-align: center;
					"
				>
					<p
						style="
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-semibold);
							color: var(--color-text-primary);
							margin: 0 0 var(--space-sm) 0;
						"
					>
						No jobs need attention
					</p>
					<p
						style="
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-regular);
							color: var(--color-text-secondary);
							margin: 0;
						"
					>
						All recent runs completed or are running. Toggle off to see the full history.
					</p>
				</div>
			{:else if !data.jobs || data.jobs.length === 0}
				<!-- Default empty state per 07-UI-SPEC Copywriting Contract -->
				<div
					style="
						background-color: var(--color-surface);
						border: 1px solid var(--color-border);
						border-radius: 8px;
						padding: var(--space-2xl);
						text-align: center;
					"
				>
					<p
						style="
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-semibold);
							color: var(--color-text-primary);
							margin: 0 0 var(--space-sm) 0;
						"
					>
						No runs yet
					</p>
					<p
						style="
							font-size: var(--font-size-body);
							font-weight: var(--font-weight-regular);
							color: var(--color-text-secondary);
							margin: 0;
						"
					>
						Start a new run above to begin ingesting a transcript.
					</p>
				</div>
			{:else}
				<!-- HistoryTable: status badge | step | created date | View link -->
				<!-- aria-live=polite: screen readers announce row changes during polling -->
				<div aria-live="polite">
					<table
						style="
							width: 100%;
							border-collapse: collapse;
						"
					>
						<thead>
							<tr>
								<th
									scope="col"
									style="
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-regular);
										color: var(--color-text-secondary);
										text-align: left;
										padding: var(--space-sm) 0;
										border-bottom: 1px solid var(--color-border);
									"
								>
									Status
								</th>
								<th
									scope="col"
									style="
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-regular);
										color: var(--color-text-secondary);
										text-align: left;
										padding: var(--space-sm) 0;
										border-bottom: 1px solid var(--color-border);
									"
								>
									Source
								</th>
								<th
									scope="col"
									style="
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-regular);
										color: var(--color-text-secondary);
										text-align: left;
										padding: var(--space-sm) 0;
										border-bottom: 1px solid var(--color-border);
									"
								>
									Created
								</th>
								<th
									scope="col"
									style="
										font-size: var(--font-size-caption);
										font-weight: var(--font-weight-regular);
										color: var(--color-text-secondary);
										text-align: left;
										padding: var(--space-sm) 0;
										border-bottom: 1px solid var(--color-border);
									"
								>
									<!-- intentionally empty — View links are in this column -->
								</th>
							</tr>
						</thead>
						<tbody>
							{#each data.jobs as job}
								<tr>
									<td
										style="
											font-size: var(--font-size-body);
											color: var(--color-text-primary);
											padding: var(--space-md) 0;
											border-bottom: 1px solid var(--color-border);
										"
									>
										<span style={badgeStyle(job.status, job.is_archived)}>
											{badgeLabel(job.status, job.current_step, job.is_archived)}
										</span>
									</td>
									<td
										style="
											font-size: var(--font-size-body);
											color: var(--color-text-primary);
											padding: var(--space-md) 0;
											border-bottom: 1px solid var(--color-border);
										"
									>
										<span style={sourceTagStyle()}>
											{sourceLabel(job.source)}
										</span>
									</td>
									<td
										style="
											font-size: var(--font-size-caption);
											color: var(--color-text-secondary);
											padding: var(--space-md) 0;
											border-bottom: 1px solid var(--color-border);
										"
									>
										{formatDate(job.created_at)}
									</td>
									<td
										style="
											font-size: var(--font-size-caption);
											padding: var(--space-md) 0;
											border-bottom: 1px solid var(--color-border);
											text-align: right;
										"
									>
										<a
											href="/admin/pipeline/{job.id}"
											data-sveltekit-reload
											style="
												color: var(--color-accent);
												text-decoration: underline;
												font-size: var(--font-size-caption);
												font-weight: var(--font-weight-regular);
											"
										>
											View
										</a>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>

	</div>
</main>
