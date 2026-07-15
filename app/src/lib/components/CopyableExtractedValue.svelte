<script lang="ts">
	type CopyState = 'idle' | 'copied' | 'error';
	type CopyableExtractedValueProps = {
		value: string | null | undefined;
		copyLabel: string;
		variant?: 'text' | 'pill';
	};

	let { value, copyLabel, variant = 'text' }: CopyableExtractedValueProps = $props();
	let state = $state<CopyState>('idle');
	let resetTimer: ReturnType<typeof setTimeout> | undefined;
	let generation = 0;
	let isEmpty = $derived(value === null || value === undefined || value === '');
	let displayValue = $derived(isEmpty ? 'N/A' : value);

	function invalidateFeedback() {
		generation += 1;
		if (resetTimer !== undefined) {
			clearTimeout(resetTimer);
			resetTimer = undefined;
		}
		state = 'idle';
	}

	$effect(() => {
		// Reading both props makes the feedback lifecycle belong to this payload.
		value;
		copyLabel;
		invalidateFeedback();
		return invalidateFeedback;
	});

	async function copyValue() {
		if (isEmpty || value === null || value === undefined) return;

		invalidateFeedback();
		const attemptGeneration = generation;

		try {
			if (!navigator.clipboard) throw new Error('Clipboard unavailable');
			await navigator.clipboard.writeText(value);
			if (attemptGeneration !== generation) return;
			state = 'copied';
			resetTimer = setTimeout(() => {
				if (attemptGeneration !== generation) return;
				state = 'idle';
				resetTimer = undefined;
			}, 1500);
		} catch {
			if (attemptGeneration !== generation) return;
			state = 'error';
		}
	}
</script>

<span class="copyable-value" class:pill={variant === 'pill'}>
	<button
		type="button"
		disabled={isEmpty}
		title={isEmpty ? 'Nothing extracted to copy.' : copyLabel}
		aria-label={isEmpty ? 'Nothing extracted to copy.' : copyLabel}
		onclick={copyValue}
	>
		<span class:empty={isEmpty}>{displayValue}</span>
		{#if state === 'copied'}
			<span class="success" aria-live="polite">Copied</span>
		{:else if !isEmpty}
			<svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="9" y="9" width="11" height="11" rx="2"></rect>
				<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
			</svg>
		{/if}
	</button>
	{#if state === 'error'}
		<span class="error" role="alert">Couldn't copy.</span>
	{/if}
</span>

<style>
	.copyable-value {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
	}

	button {
		display: inline-flex;
		align-items: center;
		gap: 4px;
		min-height: 36px;
		max-width: 100%;
		padding: 0 8px;
		border: 1px solid transparent;
		border-radius: 4px;
		background: transparent;
		color: inherit;
		font: inherit;
		line-height: inherit;
		text-align: left;
		cursor: pointer;
	}

	button > span:first-child {
		min-width: 0;
		overflow-wrap: anywhere;
	}

	svg,
	.success {
		flex: 0 0 auto;
	}

	button:hover:not(:disabled) {
		color: #93c5fd;
	}

	.pill button {
		border-color: #334155;
		background-color: #0f1117;
		font-size: 12px;
	}

	.pill button:hover:not(:disabled) {
		border-color: #93c5fd;
	}

	button:disabled {
		color: #94a3b8;
		cursor: default;
	}

	button:disabled svg {
		color: #94a3b8;
	}

	.empty {
		font-style: italic;
	}

	.success {
		color: #4ade80;
		font-size: 14px;
		font-weight: 400;
	}

	.error {
		color: #ef4444;
		font-size: 14px;
		font-weight: 400;
	}
</style>
