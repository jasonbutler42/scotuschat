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
		pending: 'var(--color-text-secondary)',
		running: 'var(--color-accent)',
		completed: 'var(--color-status-published)',
		paused: 'var(--color-status-warning)',
		failed: 'var(--color-destructive)',
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
		readiness?.state === 'already_created' ? 'var(--color-status-archived)' : BADGE_COLOR[jobStatus] ?? 'var(--color-text-secondary)',
	);
	let badgeLabel = $derived(
		readiness?.state === 'already_created' ? 'Archived' : BADGE_LABEL[jobStatus] ?? jobStatus,
	);

	let approveSubmitting = $state(false);
</script>

<div
	style="
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 8px;
		padding: var(--space-xl);
		margin-bottom: var(--space-xl);
	"
>
	<div
		style="
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: var(--space-lg);
		"
	>
		<h2 style="font-size: var(--font-size-heading); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0; line-height: 1.2;">
			Run status
		</h2>
		<span
			aria-label={jobStatus === 'running' ? 'Running' : undefined}
			style="
				border: 1px solid {badgeColor};
				border-radius: 4px;
				padding: 2px var(--space-sm);
				font-size: var(--font-size-caption);
				font-weight: var(--font-weight-regular);
				color: {badgeColor};
				background-color: var(--color-surface);
				display: inline-flex;
				align-items: center;
				gap: var(--space-xs);
			"
		>
			{badgeLabel}
		</span>
	</div>

	<!-- Source PDF link — present in every state per UI-SPEC Interaction Contract -->
	{#if pdfHref}
		<div style="margin-bottom: var(--space-lg);">
			<a
				href={pdfHref}
				target="_blank"
				rel="noopener noreferrer"
				style="font-size: var(--font-size-caption); color: var(--color-accent); text-decoration: none;"
			>
				View source PDF
			</a>
		</div>
	{/if}

	{#if readiness == null}
		<!-- Backend readiness fetch degraded to null (Plan 25-03 load() contract) -->
		<p style="font-size: var(--font-size-caption); color: var(--color-text-secondary); font-style: italic; margin: 0;">
			Readiness information is unavailable.
		</p>
	{:else if readiness.state === 'already_created'}
		<h3 style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-primary); margin: 0 0 var(--space-xs) 0;">
			Argument created
		</h3>
		<p style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-lg) 0;">
			This run is preserved as the source history for the argument.
		</p>
		{#if readiness.argument_edit_href}
			<a
				href={readiness.argument_edit_href}
				style="font-size: var(--font-size-body); color: var(--color-accent); text-decoration: underline;"
			>
				Open argument editor
			</a>
		{/if}
	{:else if readiness.state === 'not_ready'}
		<h3 style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-primary); margin: 0 0 var(--space-xs) 0;">
			Not ready to create argument
		</h3>
		<p style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); margin: 0 0 var(--space-md) 0;">
			Resolve these items before creating the argument.
		</p>
		<ul style="margin: 0; padding-left: 20px;">
			{#each readiness.blockers as blocker (blocker.code)}
				<li style="font-size: var(--font-size-body); color: var(--color-text-primary); margin-bottom: var(--space-xs);">{blocker.message}</li>
			{/each}
		</ul>
	{:else}
		<h3 style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-primary); margin: 0 0 var(--space-lg) 0;">
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
					min-height: var(--touch-target);
					font-size: var(--font-size-body);
					font-weight: var(--font-weight-semibold);
					color: var(--color-text-primary);
					background-color: var(--color-surface);
					border: 1px solid var(--color-accent);
					border-radius: 6px;
					padding: var(--space-md) var(--space-xl);
					cursor: pointer;
					{approveSubmitting ? 'opacity: 0.7; cursor: not-allowed;' : ''}
				"
			>
				{approveSubmitting ? 'Creating…' : 'Create Argument'}
			</button>
		</form>
	{/if}

	{#if approveError}
		<p role="alert" style="margin-top: var(--space-sm); color: var(--color-destructive); font-size: var(--font-size-caption);">
			{approveError}
		</p>
	{/if}
</div>
