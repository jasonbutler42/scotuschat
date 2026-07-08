<script lang="ts">
	import { enhance } from '$app/forms';

	// Phase 25 — Run status card (D-01 through D-04, D-18, D-20, D-21, PJOB-01, PJOB-02, PJOB-20).
	// Receives readiness/status data via props; does not fetch its own data.

	interface ReadinessBlocker {
		code: string;
		message: string;
	}

	interface Readiness {
		state: 'not_ready' | 'ready' | 'already_created';
		blockers: ReadinessBlocker[];
		argument_edit_href: string | null;
	}

	interface RunStatusCardProps {
		jobStatus: string;
		pdfHref: string | null;
		readiness: Readiness | null;
		approveError?: string | null;
	}

	let { jobStatus, pdfHref, readiness, approveError = null }: RunStatusCardProps = $props();

	// T-25-10: badges include text labels and derive from server-provided status, not color alone.
	const BADGE_COLOR: Record<string, string> = {
		pending: '#94a3b8',
		running: '#93c5fd',
		completed: '#4ade80',
		paused: '#fbbf24',
		failed: '#ef4444',
	};

	const BADGE_LABEL: Record<string, string> = {
		pending: 'Pending',
		running: 'Running',
		completed: 'Completed',
		paused: 'Needs review',
		failed: 'Failed',
	};

	// Archived override: an already-created run is settled/read-only and reads
	// differently from a still-processing "Completed" badge (folded Phase-25-UAT todo).
	let badgeColor = $derived(
		readiness?.state === 'already_created' ? '#cbd5e1' : BADGE_COLOR[jobStatus] ?? '#94a3b8',
	);
	let badgeLabel = $derived(
		readiness?.state === 'already_created' ? 'Archived' : BADGE_LABEL[jobStatus] ?? jobStatus,
	);

	let approveSubmitting = $state(false);
</script>

<div
	style="
		background-color: #1e293b;
		border: 1px solid #334155;
		border-radius: 8px;
		padding: 24px;
		margin-bottom: 24px;
	"
>
	<div
		style="
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: 16px;
		"
	>
		<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0; line-height: 1.2;">
			Run status
		</h2>
		<span
			aria-label={jobStatus === 'running' ? 'Running' : undefined}
			style="
				border: 1px solid {badgeColor};
				border-radius: 4px;
				padding: 2px 8px;
				font-size: 14px;
				font-weight: 400;
				color: {badgeColor};
				background-color: #1e293b;
				display: inline-flex;
				align-items: center;
				gap: 4px;
			"
		>
			{badgeLabel}
		</span>
	</div>

	<!-- Source PDF link — present in every state per UI-SPEC Interaction Contract -->
	{#if pdfHref}
		<div style="margin-bottom: 16px;">
			<a
				href={pdfHref}
				target="_blank"
				rel="noopener noreferrer"
				style="font-size: 14px; color: #93c5fd; text-decoration: none;"
			>
				View source PDF
			</a>
		</div>
	{/if}

	{#if readiness == null}
		<!-- Backend readiness fetch degraded to null (Plan 25-03 load() contract) -->
		<p style="font-size: 14px; color: #94a3b8; font-style: italic; margin: 0;">
			Readiness information is unavailable.
		</p>
	{:else if readiness.state === 'already_created'}
		<h3 style="font-size: 16px; font-weight: 400; color: #e2e8f0; margin: 0 0 4px 0;">
			Argument created
		</h3>
		<p style="font-size: 16px; font-weight: 400; color: #94a3b8; margin: 0 0 16px 0;">
			This run is preserved as the source history for the argument.
		</p>
		{#if readiness.argument_edit_href}
			<a
				href={readiness.argument_edit_href}
				style="font-size: 16px; color: #93c5fd; text-decoration: underline;"
			>
				Open argument editor
			</a>
		{/if}
	{:else if readiness.state === 'not_ready'}
		<h3 style="font-size: 16px; font-weight: 400; color: #e2e8f0; margin: 0 0 4px 0;">
			Not ready to create argument
		</h3>
		<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 12px 0;">
			Resolve these items before creating the argument.
		</p>
		<ul style="margin: 0; padding-left: 20px;">
			{#each readiness.blockers as blocker (blocker.code)}
				<li style="font-size: 16px; color: #e2e8f0; margin-bottom: 4px;">{blocker.message}</li>
			{/each}
		</ul>
	{:else}
		<h3 style="font-size: 16px; font-weight: 400; color: #e2e8f0; margin: 0 0 16px 0;">
			Ready to create argument
		</h3>
		<form
			method="POST"
			action="?/approve"
			use:enhance={() => {
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
	{/if}

	{#if approveError}
		<p role="alert" style="margin-top: 8px; color: #ef4444; font-size: 14px;">
			{approveError}
		</p>
	{/if}
</div>
