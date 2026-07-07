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

<div style="margin-top: 12px;">
	<!-- role="alert" scoped to the immediate failure summary only, not the raw details block -->
	<p role="alert" style="font-size: 16px; font-weight: 400; color: #e2e8f0; margin: 0 0 12px 0;">
		{guidanceText}
	</p>

	<a href={recoveryHref} style="font-size: 16px; color: #93c5fd; text-decoration: underline;">
		Start a new run
	</a>

	{#if rawError}
		<details style="margin-top: 16px;">
			<summary style="font-size: 14px; font-weight: 400; color: #94a3b8; cursor: pointer;">
				Technical details
			</summary>
			<p
				style="
					margin-top: 8px;
					margin-bottom: 0;
					font-size: 14px;
					color: #ef4444;
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
