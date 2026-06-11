<script lang="ts">
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import StageDirection from '$lib/components/StageDirection.svelte';

	let { data } = $props();

	/**
	 * Format an argued_date string (e.g. "2015-04-28") as "April 28, 2015".
	 * Uses Intl.DateTimeFormat per the UI-SPEC Copywriting Contract.
	 * The date comes from the API as a date string (YYYY-MM-DD).
	 * We append T00:00:00 to force local-date parsing and avoid UTC midnight
	 * roll-back on systems west of UTC.
	 */
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr + 'T00:00:00');
		return new Intl.DateTimeFormat('en-US', {
			month: 'long',
			day: 'numeric',
			year: 'numeric'
		}).format(date);
	}
</script>

<!-- Page background (#0f1117) -->
<div style="background-color: #0f1117; min-height: 100vh;">
	<!-- Argument heading bar: full-width, #1e293b, border-bottom #334155 -->
	<div
		style="
			background-color: #1e293b;
			border-bottom: 1px solid #334155;
			padding: 16px 24px;
		"
	>
		<div style="max-width: 860px; margin: 0 auto;">
			<!-- Case name: 20px, weight 600, #e2e8f0 -->
			<h1
				style="
					font-size: 20px;
					font-weight: 600;
					color: #e2e8f0;
					margin: 0 0 4px 0;
					line-height: 1.2;
				"
			>
				{data.argument.case_name}
			</h1>
			<!-- Subline: "No. {docket} · Argued {date} · Question {n}" — 14px, #94a3b8 -->
			<p
				style="
					font-size: 14px;
					font-weight: 400;
					color: #94a3b8;
					margin: 0;
					line-height: 1.4;
				"
			>
				No. {data.argument.docket_number} · Argued {formatDate(data.argument.argued_date)} · Question {data.argument.question_number}
			</p>
		</div>
	</div>

	<!-- Chat column: max-width 860px, centered, padding top/bottom 48px -->
	<div
		style="
			max-width: 860px;
			margin: 0 auto;
			padding: 48px 24px;
		"
	>
		{#if !data.utterances || data.utterances.length === 0}
			<!-- Empty state -->
			<p
				style="
					text-align: center;
					color: #94a3b8;
					font-size: 16px;
				"
			>
				No utterances found for this argument.
			</p>
		{:else}
			<!-- Utterance stream with turn-gap logic:
				 same speaker → lg gap (24px); different speaker → xl gap (32px) -->
			{#each data.utterances as utterance, i (utterance.sequence)}
				{@const prevUtterance = i > 0 ? data.utterances[i - 1] : null}
				{@const sameSpeaker =
					prevUtterance !== null &&
					prevUtterance.raw_speaker_label === utterance.raw_speaker_label}
				<div style={i === 0 ? '' : sameSpeaker ? 'margin-top: 24px;' : 'margin-top: 32px;'}>
					{#if utterance.is_stage_direction}
						<StageDirection {utterance} />
					{:else}
						<ChatBubble {utterance} />
					{/if}
				</div>
			{/each}
		{/if}
	</div>
</div>
