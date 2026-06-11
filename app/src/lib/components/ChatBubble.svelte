<script lang="ts">
	let { utterance } = $props();

	const isBench = utterance.side === 'BENCH';
	// BENCH: right-aligned; ADVOCATE or UNKNOWN: left-aligned (apolitical framing — identical backgrounds)
	const labelColor = isBench ? '#94a3b8' : '#93c5fd';
</script>

<div
	style="
		display: flex;
		justify-content: {isBench ? 'flex-end' : 'flex-start'};
	"
>
	<div
		style="
			max-width: 72%;
			background-color: #1e293b;
			border-top: 1px solid #334155;
			border-right: 1px solid #334155;
			border-bottom: 1px solid #334155;
			border-left: 3px solid #334155;
			border-radius: 0 6px 6px 6px;
			padding: 12px 16px;
		"
	>
		<!-- Bubble header row: sequence number + speaker label -->
		<div
			style="
				display: flex;
				align-items: center;
				gap: 4px;
				margin-bottom: 8px;
			"
		>
			<span
				style="
					font-size: 13px;
					color: #475569;
					font-weight: 400;
					padding-right: 4px;
				"
			>
				{utterance.sequence}
			</span>
			<span
				style="
					font-size: 13px;
					font-weight: 600;
					color: {labelColor};
				"
			>
				{utterance.raw_speaker_label}
			</span>
		</div>

		<!-- Utterance text -->
		<p
			style="
				font-size: 16px;
				color: #e2e8f0;
				font-weight: 400;
				line-height: 1.6;
				margin: 0;
			"
		>
			{utterance.text}
		</p>
	</div>
</div>
