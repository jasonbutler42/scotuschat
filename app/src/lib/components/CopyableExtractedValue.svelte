<script lang="ts">
	// Phase 38 (D-19–D-23): optional stacked provenance mode layered on top of the
	// Phase 36 clipboard state machine. Legacy value-only/text/pill consumers that
	// never pass `confidence`/`raw` render exactly as before — this file must stay
	// a strict superset, never a replacement, of the Phase 36 contract.
	type CopyState = 'idle' | 'copied' | 'error';
	type ConfidenceBand = 'High' | 'Medium' | 'Low';
	type CopyableExtractedValueProps = {
		value: string | null | undefined;
		copyLabel: string;
		variant?: 'text' | 'pill';
		/** Optional Phase 38 stacked-mode props — presence of either (even `null`) opts into the two-line layout. */
		confidence?: ConfidenceBand | null;
		raw?: string | null;
	};

	let { value, copyLabel, variant = 'text', confidence, raw }: CopyableExtractedValueProps = $props();
	let state = $state<CopyState>('idle');
	let resetTimer: ReturnType<typeof setTimeout> | undefined;
	let generation = 0;
	let isEmpty = $derived(value === null || value === undefined || value === '');
	let displayValue = $derived(isEmpty ? 'N/A' : value);

	// Stacked mode activates only when the caller explicitly supplies confidence
	// and/or raw (even `null`); omitting both props entirely preserves the exact
	// Phase 36 single-line rendering for every existing consumer.
	let isStacked = $derived(confidence !== undefined || raw !== undefined);
	let hasRaw = $derived(raw !== null && raw !== undefined && raw !== '');
	// D-22: confidence is always one of High/Medium/Low text, never a percentage.
	// Invalid/omitted input falls back to an explicit qualitative band rather than
	// a fabricated figure; an empty interpreted value is always presented as Low
	// per the 38-UI-SPEC raw-without-interpretation contract.
	function isValidConfidenceBand(input: unknown): input is ConfidenceBand {
		return input === 'High' || input === 'Medium' || input === 'Low';
	}
	let effectiveBand = $derived.by<ConfidenceBand>(() => {
		if (isEmpty) return 'Low';
		return isValidConfidenceBand(confidence) ? confidence : 'Medium';
	});
	// Omit a meaningless second line when there is no raw source text to show.
	let showProvenanceLine = $derived(isStacked && hasRaw);

	function invalidateFeedback() {
		generation += 1;
		if (resetTimer !== undefined) {
			clearTimeout(resetTimer);
			resetTimer = undefined;
		}
		state = 'idle';
	}

	$effect(() => {
		// Reading value/copyLabel/confidence/raw makes the feedback lifecycle
		// belong to this exact payload+provenance combination.
		value;
		copyLabel;
		confidence;
		raw;
		invalidateFeedback();
		return invalidateFeedback;
	});

	async function copyValue() {
		if (isEmpty || value === null || value === undefined) return;

		invalidateFeedback();
		const attemptGeneration = generation;

		try {
			if (!navigator.clipboard) throw new Error('Clipboard unavailable');
			// Copy exactly the displayed interpreted value — never the raw source
			// text or any prefix/confidence text (T-38-13).
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

{#snippet copyButton()}
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
{/snippet}

{#if isStacked}
	<span class="copyable-value stacked" class:pill={variant === 'pill'}>
		<span class="line1">
			<span class="prefix">Extracted:</span>
			{@render copyButton()}
		</span>
		{#if state === 'error'}
			<span class="error" role="alert">Couldn't copy.</span>
		{/if}
		{#if showProvenanceLine}
			<!-- D-20/D-21: raw is untrusted extracted text rendered as plain Svelte
			     interpolation only — never {@html} — and is never included in the
			     clipboard payload above (T-38-14). -->
			<span class="line2">{effectiveBand} confidence · Raw: {raw}</span>
		{/if}
	</span>
{:else}
	<span class="copyable-value" class:pill={variant === 'pill'}>
		{@render copyButton()}
		{#if state === 'error'}
			<span class="error" role="alert">Couldn't copy.</span>
		{/if}
	</span>
{/if}

<style>
	.copyable-value {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
	}

	.copyable-value.stacked {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 4px;
		max-width: 100%;
	}

	.line1 {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 4px;
		max-width: 100%;
	}

	.prefix {
		font-size: 14px;
		font-weight: 400;
		color: #94a3b8;
	}

	.line2 {
		font-size: 14px;
		font-weight: 400;
		color: #94a3b8;
		overflow-wrap: anywhere;
		max-width: 100%;
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
