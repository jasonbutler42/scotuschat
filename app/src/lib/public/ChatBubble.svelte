<script lang="ts">
	// D-19 (Style B2 — avatar in an outside rail): the avatar and speaker name
	// used to live inside this component's own header row. They no longer do.
	// The avatar moved entirely to the outside rail the transcript route
	// renders once per RUN (a run is the structural unit — consecutive
	// utterances by the same speaker — grouped by the route before layout,
	// per 51-DESIGN-DECISIONS.md D-19). This component now renders exactly
	// one bubble: the speaker name (only on the first bubble of a run, via
	// `showSpeakerName`) and the utterance text, nothing else.
	//
	// `position` drives the D-19 corner-rounding table (amended to 2px): a
	// corner facing an adjacent bubble in the same run softens to 2px; the
	// run's outer corners stay 6px; a single-utterance run keeps all four
	// at 6px.
	type RunPosition = 'single' | 'first' | 'middle' | 'last';

	let { utterance, position = 'single', showSpeakerName = true } = $props<{
		utterance: {
			person_id: number | null;
			side: string;
			speaker_name: string | null;
			raw_speaker_label: string | null;
			speaker_role: string | null;
			text: string;
			is_stage_direction: boolean;
		};
		position?: RunPosition;
		showSpeakerName?: boolean;
	}>();

	const isBench = utterance.side === 'BENCH';
	// D-05: BENCH: left-aligned; ADVOCATE or UNKNOWN: right-aligned.
	// Side is encoded only via position (handled by the route's row layout)
	// and this neutral speaker-label colour — never via size or weight (P-03).
	function resolveLabelColor(bench: boolean): string {
		if (bench) return 'var(--color-side-bench)';
		return 'var(--color-side-advocate)';
	}
	const labelColor = resolveLabelColor(isBench);
	const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
	const displayRole = utterance.speaker_role ?? null;

	// D-19 corner-rounding table (2px amendment). CSS border-radius shorthand
	// order is top-left top-right bottom-right bottom-left; every row here has
	// bottom-right === bottom-left, so the shorthand is unambiguous.
	const RADIUS_BY_POSITION: Record<RunPosition, string> = {
		single: '6px 6px 6px 6px',
		first: '6px 6px 2px 2px',
		middle: '2px 2px 2px 2px',
		last: '2px 2px 6px 6px'
	};
	function resolveRadius(pos: RunPosition): string {
		return RADIUS_BY_POSITION[pos];
	}
	const borderRadius = resolveRadius(position);
</script>

<div
	style="
		max-width: min(72%, 68ch);
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: {borderRadius};
		padding: var(--space-sm) var(--space-md);
	"
>
	{#if showSpeakerName}
		<!-- Speaker name row — appears once per run, on the first bubble only. -->
		<div
			style="
				display: flex;
				align-items: baseline;
				gap: var(--space-sm);
				margin-bottom: var(--space-sm);
			"
		>
			<span
				style="
					font-size: var(--font-size-caption);
					font-weight: var(--font-weight-semibold);
					color: {labelColor};
				"
			>
				{displayName}
			</span>{#if displayRole}<span style="font-size: var(--font-size-caption); color: var(--color-text-secondary);">{displayRole}</span>{/if}
		</div>
	{/if}

	<!-- Utterance text. Lead (18px/400/1.6) — reserved for the public reading
	     layer (D-09). Identical size, weight, and line-height on both sides;
	     P-03 forbids any typographic difference by speaker side. Wraps, never
	     truncates (P-06). -->
	<p
		style="
			font-size: var(--font-size-lead);
			color: var(--color-text-primary);
			font-weight: var(--font-weight-regular);
			line-height: var(--line-height-lead);
			margin: 0;
		"
	>
		{utterance.text}
	</p>
</div>
