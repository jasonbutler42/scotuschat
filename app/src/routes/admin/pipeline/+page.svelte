<svelte:head>
	<title>Pipeline Runner — SCOTUS Chat Admin</title>
</svelte:head>

<script lang="ts">
	let { data, form } = $props();

	// Mode toggle state: 'url' or 'upload'. Defaults to URL mode.
	let mode = $state<'url' | 'upload'>('url');

	// Submitting state: used to disable the Start Run button and change its label.
	let submitting = $state(false);

	function setMode(m: 'url' | 'upload') {
		mode = m;
	}

	function handleSubmit() {
		submitting = true;
	}

	// StatusBadge helper: returns inline style string for a given job status.
	function badgeStyle(status: string): string {
		const colors: Record<string, string> = {
			pending: '#94a3b8',
			running: '#93c5fd',
			completed: '#4ade80',
			paused: '#fbbf24',
			failed: '#ef4444',
		};
		const color = colors[status] ?? '#94a3b8';
		return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
	}

	// Copywriting: "paused" maps to operator-friendly label "Needs review".
	function badgeLabel(status: string): string {
		const labels: Record<string, string> = {
			pending: 'Pending',
			running: 'Running',
			completed: 'Completed',
			paused: 'Needs review',
			failed: 'Failed',
		};
		return labels[status] ?? status;
	}

	// Format ISO date string for display (date only — time detail not needed in history).
	function formatDate(iso: string): string {
		try {
			return new Date(iso).toLocaleDateString('en-US', {
				year: 'numeric',
				month: 'short',
				day: 'numeric',
			});
		} catch {
			return iso;
		}
	}
</script>

<!-- Page layout per 07-UI-SPEC /admin/pipeline Page Layout Contract -->
<main style="background-color: #0f1117; min-height: 100vh;">
	<!-- Page header bar -->
	<header
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<h1
			style="
				font-size: 20px;
				font-weight: 600;
				color: #e2e8f0;
				margin: 0;
				line-height: 1.2;
			"
		>
			Pipeline Runner
		</h1>
	</header>

	<!-- Inner content container -->
	<div style="max-width: 860px; margin: 0 auto; padding: 48px 24px;">

		<!-- New Run card -->
		<div
			style="
				background-color: #1e293b;
				border: 1px solid #334155;
				border-radius: 8px;
				padding: 32px;
			"
		>
			<h2
				style="
					font-size: 20px;
					font-weight: 600;
					color: #e2e8f0;
					margin: 0 0 24px 0;
					line-height: 1.2;
				"
			>
				New Run
			</h2>

			<!-- ModeToggle: "Enter URL" / "Upload File" per 07-UI-SPEC Component Inventory -->
			<div
				style="
					background-color: #0f1117;
					border: 1px solid #334155;
					border-radius: 6px;
					padding: 4px;
					display: inline-flex;
					margin-bottom: 24px;
				"
			>
				<button
					type="button"
					aria-pressed={mode === 'url'}
					onclick={() => setMode('url')}
					style="
						font-size: 14px;
						padding: 8px 16px;
						border: none;
						cursor: pointer;
						min-height: 36px;
						border-radius: 4px;
						background-color: {mode === 'url' ? '#1e293b' : 'transparent'};
						color: {mode === 'url' ? '#e2e8f0' : '#94a3b8'};
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
						font-size: 14px;
						padding: 8px 16px;
						border: none;
						cursor: pointer;
						min-height: 36px;
						border-radius: 4px;
						background-color: {mode === 'upload' ? '#1e293b' : 'transparent'};
						color: {mode === 'upload' ? '#e2e8f0' : '#94a3b8'};
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
			>
				<!-- Hidden mode field — read by actions.default in +page.server.ts -->
				<input type="hidden" name="mode" value={mode} />

				{#if mode === 'url'}
					<!-- URL input -->
					<div style="margin-bottom: 16px;">
						<label
							for="pdf_url"
							style="
								display: block;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								margin-bottom: 8px;
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
				{:else}
					<!-- File input — only rendered in upload mode so inactive field is not submitted -->
					<div style="margin-bottom: 16px;">
						<label
							for="pdf_file"
							style="
								display: block;
								font-size: 14px;
								font-weight: 400;
								color: #94a3b8;
								margin-bottom: 8px;
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
				{/if}

				<!-- Form error: role=alert so screen readers announce it immediately (T-07-13) -->
				{#if form?.error}
					<p
						role="alert"
						style="
							color: #ef4444;
							font-size: 16px;
							font-weight: 400;
							line-height: 1.5;
							margin: 0 0 16px 0;
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
						min-height: 44px;
						background-color: #1e293b;
						border: 1px solid #334155;
						border-radius: 6px;
						font-size: 16px;
						font-weight: 600;
						color: #e2e8f0;
						cursor: {submitting ? 'not-allowed' : 'pointer'};
						margin-top: 8px;
						opacity: {submitting ? 0.7 : 1};
					"
				>
					{submitting ? 'Starting…' : 'Start Run'}
				</button>
			</form>
		</div>

		<!-- Recent Runs history section -->
		<div style="margin-top: 32px;">
			<h2
				style="
					font-size: 20px;
					font-weight: 600;
					color: #e2e8f0;
					margin: 0 0 16px 0;
					line-height: 1.2;
				"
			>
				Recent Runs
			</h2>

			{#if !data.jobs || data.jobs.length === 0}
				<!-- Empty state per 07-UI-SPEC Copywriting Contract -->
				<div
					style="
						background-color: #1e293b;
						border: 1px solid #334155;
						border-radius: 8px;
						padding: 32px;
						text-align: center;
					"
				>
					<p
						style="
							font-size: 16px;
							font-weight: 600;
							color: #e2e8f0;
							margin: 0 0 8px 0;
						"
					>
						No runs yet
					</p>
					<p
						style="
							font-size: 16px;
							font-weight: 400;
							color: #94a3b8;
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
										font-size: 14px;
										font-weight: 400;
										color: #94a3b8;
										text-align: left;
										padding: 8px 0;
										border-bottom: 1px solid #334155;
									"
								>
									Status
								</th>
								<th
									scope="col"
									style="
										font-size: 14px;
										font-weight: 400;
										color: #94a3b8;
										text-align: left;
										padding: 8px 0;
										border-bottom: 1px solid #334155;
									"
								>
									Step
								</th>
								<th
									scope="col"
									style="
										font-size: 14px;
										font-weight: 400;
										color: #94a3b8;
										text-align: left;
										padding: 8px 0;
										border-bottom: 1px solid #334155;
									"
								>
									Created
								</th>
								<th
									scope="col"
									style="
										font-size: 14px;
										font-weight: 400;
										color: #94a3b8;
										text-align: left;
										padding: 8px 0;
										border-bottom: 1px solid #334155;
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
											font-size: 16px;
											color: #e2e8f0;
											padding: 12px 0;
											border-bottom: 1px solid #334155;
										"
									>
										<span style={badgeStyle(job.status)}>
											{badgeLabel(job.status)}
										</span>
									</td>
									<td
										style="
											font-size: 14px;
											color: #94a3b8;
											padding: 12px 0;
											border-bottom: 1px solid #334155;
										"
									>
										{job.current_step ?? '—'}
									</td>
									<td
										style="
											font-size: 14px;
											color: #94a3b8;
											padding: 12px 0;
											border-bottom: 1px solid #334155;
										"
									>
										{formatDate(job.created_at)}
									</td>
									<td
										style="
											font-size: 14px;
											padding: 12px 0;
											border-bottom: 1px solid #334155;
											text-align: right;
										"
									>
										<a
											href="/admin/pipeline/{job.id}"
											style="
												color: #93c5fd;
												text-decoration: underline;
												font-size: 14px;
												font-weight: 400;
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
