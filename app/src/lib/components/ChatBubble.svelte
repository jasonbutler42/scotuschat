<script lang="ts">
	let { utterance } = $props();

	const isBench = utterance.side === 'BENCH';
	// D-05: BENCH: left-aligned; ADVOCATE or UNKNOWN: right-aligned
	const labelColor = isBench ? '#94a3b8' : '#93c5fd';
	const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
	const displayRole = utterance.speaker_role ?? null;
	const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
	const initials = (() => {
		const parts = displayName.trim().split(/\s+/).filter(Boolean);
		if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
		if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
		return '?';
	})();
</script>

<div
	role="article"
	aria-label="{isBench ? 'Bench' : 'Advocate'}: {displayName}"
	style="
		display: flex;
		justify-content: {isBench ? 'flex-start' : 'flex-end'};
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
		<!-- Bubble header row: avatar circle + speaker label -->
		<div
			style="
				display: flex;
				align-items: center;
				gap: 8px;
				margin-bottom: 8px;
			"
		>
			<div aria-hidden="true" style="
				width: 32px; height: 32px; border-radius: 50%;
				background-color: {avatarBg};
				display: flex; align-items: center; justify-content: center;
				font-size: 12px; font-weight: 600; color: #0f1117;
				flex-shrink: 0;
			">{initials}</div>
<span
				style="
					font-size: 13px;
					font-weight: 600;
					color: {labelColor};
				"
			>
				{displayName}
			</span>{#if displayRole}<span style="font-size: 11px; color: #94a3b8;">{displayRole}</span>{/if}
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
