<script lang="ts">
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import StageDirection from '$lib/components/StageDirection.svelte';

	let { data } = $props();
</script>

<!-- Argument heading bar -->
<div
	style="
		background-color: #1e293b;
		border-bottom: 1px solid #334155;
		padding: 16px 24px;
	"
>
	<div style="max-width: 860px; margin: 0 auto;">
		<h1 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 4px 0; line-height: 1.2;">
			Oral Argument
		</h1>
		<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0; line-height: 1.4;">
			Argument {data.argument_id}
		</p>
	</div>
</div>

<!-- Chat column -->
<div
	style="
		background-color: #0f1117;
		min-height: 100vh;
		padding: 48px 24px;
	"
>
	<div style="max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px;">
		{#if !data.utterances || data.utterances.length === 0}
			<p style="text-align: center; color: #94a3b8; font-size: 16px;">
				No utterances found for this argument.
			</p>
		{:else}
			{#each data.utterances as utterance, i (utterance.sequence)}
				{@const prevUtterance = i > 0 ? data.utterances[i - 1] : null}
				{@const speakerChanged = prevUtterance && prevUtterance.raw_speaker_label !== utterance.raw_speaker_label}
				<div style={speakerChanged ? 'margin-top: 8px;' : ''}>
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
