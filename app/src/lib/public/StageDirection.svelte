<script lang="ts">
	let { utterance } = $props();
</script>

<!-- Stage direction: full-width, amber accent, distinct from chat bubbles -->
<div
	role="note"
	style="
		background-color: #1e293b;
		border-top: 1px solid #334155;
		border-right: 1px solid #334155;
		border-bottom: 1px solid #334155;
		border-left: 3px solid #d97706;
		border-radius: 4px;
		padding: 12px 16px;
		margin-top: 48px;
		margin-bottom: 48px;
		width: 100%;
	"
>
	<p
		style="
			font-size: 14px;
			font-weight: 400;
			color: #fcd34d;
			font-style: italic;
			line-height: 1.4;
			margin: 0;
		"
	>
		{utterance.text}
	</p>
</div>
