<script lang="ts">
	// lib/public/TermRow.svelte — D-16 Variant A (the operator's locked
	// choice, 51-DESIGN-DECISIONS.md "Term-row variant (D-16)"). Exactly
	// three identification fields: case name, argued date, docket number.
	// No advocate line, no argument_participants -> people join (deferred,
	// not built — see the decisions doc). No computed aggregate, no badge,
	// no curated marker (P-01, P-02).
	//
	// Long-text contract (UI-SPEC E2): the case name wraps and never
	// truncates or clips — no CSS truncation declaration of any kind
	// (an overflow-eliding text-overflow value, a webkit line-clamp
	// property) anywhere here. The docket number lives on its own
	// secondary line below the case name (never sharing inline space with
	// it), so a long case name wrapping to multiple lines can never push
	// the docket off-screen or squeeze it out.
	import { formatDate } from '$lib/formatting';

	interface TermRowProps {
		slug: string;
		caseName: string;
		docketNumber: string;
		argued_date: string | null | undefined;
	}

	let { slug, caseName, docketNumber, argued_date }: TermRowProps = $props();
</script>

<a
	href="/arguments/{slug}"
	style="
		background-color: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 6px;
		padding: var(--space-lg);
		margin-bottom: var(--space-lg);
		display: block;
		text-decoration: none;
	"
>
	<span
		style="
			font-size: var(--font-size-lead);
			font-weight: var(--font-weight-semibold);
			line-height: var(--line-height-lead);
			color: var(--color-text-primary);
			display: block;
			margin-bottom: var(--space-xs);
			overflow-wrap: anywhere;
		"
	>
		{caseName}
	</span>
	<span
		style="
			font-size: var(--font-size-caption);
			font-weight: var(--font-weight-regular);
			line-height: var(--line-height-caption);
			color: var(--color-text-secondary);
			display: block;
		"
	>
		Argued {formatDate(argued_date)} · No. {docketNumber}
	</span>
</a>
