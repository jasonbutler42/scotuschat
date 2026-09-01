<script lang="ts">
	// Phase 25 — Failed-step recovery guidance (D-05 through D-08, PJOB-08, PJOB-22 supersession).
	// Renders inside the failed step card. Human guidance shown first; raw technical
	// error lives in an expandable details block (T-25-11: information disclosure mitigation).

	interface FailedStepRecovery {
		step: string | null;
		guidance: string;
		href: string;
		raw_error: string | null;
	}

	interface FailedStepGuidanceProps {
		failedRecovery: FailedStepRecovery | null;
		fallbackErrorMessage?: string | null;
	}

	let { failedRecovery, fallbackErrorMessage = null }: FailedStepGuidanceProps = $props();

	// Fallback copy matches 25-UI-SPEC.md's "Unknown" failed-step guidance row —
	// used only if the backend readiness fetch degraded to null (Plan 25-03 load() contract).
	let guidanceText = $derived(
		failedRecovery?.guidance ?? 'Correct the issue, then start a new run from the pipeline page.',
	);
	let recoveryHref = $derived(failedRecovery?.href ?? '/admin/pipeline');
	let rawError = $derived(failedRecovery?.raw_error ?? fallbackErrorMessage ?? null);
</script>

<div style="margin-top: var(--space-md);">
	<h3 style="font-size: var(--font-size-body); font-weight: var(--font-weight-semibold); color: var(--color-text-primary); margin: 0 0 var(--space-sm) 0;">This run failed</h3>
	<!-- role="alert" scoped to the immediate failure summary only, not the raw details block -->
	<p role="alert" style="font-size: var(--font-size-body); font-weight: var(--font-weight-regular); color: var(--color-text-primary); margin: 0 0 var(--space-md) 0;">
		{guidanceText}
	</p>

	<a href={recoveryHref} style="font-size: var(--font-size-body); color: var(--color-accent); text-decoration: underline;">
		Start a new run
	</a>

	{#if rawError}
		<details style="margin-top: var(--space-lg);">
			<summary style="font-size: var(--font-size-caption); font-weight: var(--font-weight-regular); color: var(--color-text-secondary); cursor: pointer;">
				Technical details
			</summary>
			<p
				style="
					margin-top: var(--space-sm);
					margin-bottom: 0;
					font-size: var(--font-size-caption);
					color: var(--color-destructive);
					font-family: monospace;
					white-space: pre-wrap;
					word-break: break-word;
				"
			>
				{rawError}
			</p>
		</details>
	{/if}
</div>
