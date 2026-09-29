<script lang="ts">
	// D-14: the explanation card for a Treatment D bubble's dashed avatar.
	// Title + three fixed paragraphs only — no avatar, name, role pill or
	// tenure list, because there is no person here (SPEAKER-02). The three
	// paragraph strings are held as module constants so a later swap (D-15:
	// the lost-words first-paragraph substitution) replaces one reference,
	// not markup.
	const PARAGRAPH_1_ORDINARY =
		'The words here were captured clearly. What the record does not say is which person spoke them.';
	const PARAGRAPH_2 =
		'Oyez attributes each turn by listening to the argument audio. Where a voice could not be matched to a participant, the turn is left unattributed rather than guessed.';
	const PARAGRAPH_3 =
		'Everyone who spoke was present in the courtroom that day — the record simply does not identify which of them this was.';
</script>

<div class="undetermined-card">
	<p style="
			font-size: var(--font-size-body);
			font-weight: var(--font-weight-semibold);
			color: var(--color-text-primary);
			margin: 0;
		">Undetermined speaker</p>

	<p style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			line-height: var(--line-height-body);
			color: var(--color-text-secondary);
			border-top: 1px solid var(--color-border);
			margin-top: var(--space-lg);
			padding-top: var(--space-lg);
		">{PARAGRAPH_1_ORDINARY}</p>

	<p style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			line-height: var(--line-height-body);
			color: var(--color-text-secondary);
			border-top: 1px solid var(--color-border);
			margin-top: var(--space-lg);
			padding-top: var(--space-lg);
		">{PARAGRAPH_2}</p>

	<p style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			line-height: var(--line-height-body);
			color: var(--color-text-secondary);
			border-top: 1px solid var(--color-border);
			margin-top: var(--space-lg);
			padding-top: var(--space-lg);
		">{PARAGRAPH_3}</p>
</div>

<style>
	.undetermined-card {
		padding: var(--space-xl);
		display: block;
	}
</style>
