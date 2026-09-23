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
		/** Phase 44 D-09 addition: overrides the stacked-mode line-1 prefix text.
		 * Defaults to 'Extracted' so every pre-existing call site (which omits this
		 * prop) renders identically to before. */
		prefixLabel?: string;
	};

	let {
		value,
		copyLabel,
		variant = 'text',
		confidence,
		raw,
		prefixLabel = 'Extracted',
	}: CopyableExtractedValueProps = $props();
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
			<span class="prefix">{prefixLabel}:</span>
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
		gap: var(--space-xs);
	}

	.copyable-value.stacked {
		display: inline-flex;
		flex-direction: column;
		align-items: flex-start;
		gap: var(--space-xs);
		max-width: 100%;
	}

	.line1 {
		display: inline-flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--space-xs);
		max-width: 100%;
	}

	.prefix {
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-regular);
		color: var(--color-text-secondary);
	}

	.line2 {
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-regular);
		color: var(--color-text-secondary);
		overflow-wrap: anywhere;
		max-width: 100%;
	}

	button {
		display: inline-flex;
		align-items: center;
		gap: var(--space-xs);
		min-height: var(--touch-target-dense);
		max-width: 100%;
		padding: 0 var(--space-sm);
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
		color: var(--color-accent);
	}

	.pill button {
		border-color: var(--color-border);
		background-color: var(--color-bg);
		font-size: var(--font-size-caption);
	}

	.pill button:hover:not(:disabled) {
		border-color: var(--color-accent);
	}

	button:disabled {
		color: var(--color-text-secondary);
		cursor: default;
	}

	button:disabled svg {
		color: var(--color-text-secondary);
	}

	.empty {
		font-style: italic;
	}

	.success {
		color: var(--color-status-published);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-regular);
	}

	.error {
		color: var(--color-destructive);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-regular);
	}
</style>
