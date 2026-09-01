<script lang="ts">
	let { utterance } = $props();
</script>

<!-- Stage direction: full-width, centered treatment — belongs to neither side.
     D-09 reading polish: quieter than an utterance bubble, still legible, via
     var(--color-stage-accent) for the bracket and var(--color-stage-text) for
     the body, both at var(--font-size-caption). -->
<div
	role="note"
	style="
		background-color: var(--color-surface);
		border-top: 1px solid var(--color-border);
		border-right: 1px solid var(--color-border);
		border-bottom: 1px solid var(--color-border);
		border-left: 3px solid var(--color-stage-accent);
		border-radius: 4px;
		padding: var(--space-sm) var(--space-lg);
		margin-top: var(--space-3xl);
		margin-bottom: var(--space-3xl);
		width: 100%;
	"
>
	<p
		style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			color: var(--color-stage-text);
			font-style: italic;
			line-height: var(--line-height-caption);
			margin: 0;
		"
	>
		{utterance.text}
	</p>
</div>
