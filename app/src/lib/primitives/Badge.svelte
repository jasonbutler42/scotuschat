<script lang="ts">
	// lib/primitives/Badge.svelte — D-17 shared primitive. Generalized from the
	// border-only pill shape already used for the Resolve row cue tag
	// (ResolveCard.svelte's rowCueTag pill: border-radius 4px, padding 2px 8px,
	// font-size 11-12px, border-and-text colored by state) and
	// CopyableExtractedValue's `.pill` variant.
	//
	// Surface-agnostic: this file must never import from the public or admin
	// component directories. The five lifecycle `tone` values below (published / draft /
	// unpublished / warning / archived) ARE admin-only vocabulary — a public
	// surface must never pass one. Badge itself has no way to know which
	// surface is calling it; the actual enforcement is the API-side structural
	// leak ban (api/tests/test_trust_public_leak_ban.py), which governs what
	// ever reaches a public response model in the first place. This comment is
	// a signpost, not a gate.
	//
	// `label` is a REQUIRED prop (no default, no `?`) so constructing a Badge
	// without one is a TypeScript compile error, not a rendered empty pill
	// (UI-SPEC E4 "empty" row).
	// Three admin vocabularies, one shape: an argument's publish lifecycle, a
	// record's trust tier, and where it sits in the review queue. They were
	// near-identical helper functions duplicated across five files
	// (51-ADMIN-ARTIFACTS.md D-01/D-03) until the operator ruled them here. The
	// union lives in badge-tone.ts so call sites can type their mappings.
	import type { BadgeTone } from './badge-tone';

	interface BadgeProps {
		label: string;
		tone?: BadgeTone;
	}

	let { label, tone = 'neutral' }: BadgeProps = $props();

	// Neutral reuses --color-text-secondary — the same "muted, non-signal"
	// token ResolveCard's manually-matched cue tag already uses for a
	// disclosure that is neither a warning nor a success signal.
	const TONE_COLOR: Record<BadgeTone, string> = {
		published: 'var(--color-status-published)',
		draft: 'var(--color-status-draft)',
		unpublished: 'var(--color-status-unpublished)',
		warning: 'var(--color-status-warning)',
		archived: 'var(--color-status-archived)',
		neutral: 'var(--color-text-secondary)',
		verified: 'var(--color-tier-verified)',
		trusted: 'var(--color-tier-trusted)',
		provisional: 'var(--color-tier-provisional)',
		uncertain: 'var(--color-tier-uncertain)',
		unreviewed: 'var(--color-review-unreviewed)',
		'needs-review': 'var(--color-review-needs-review)',
		confirmed: 'var(--color-review-confirmed)',
		edited: 'var(--color-review-edited)',
		discrepancy: 'var(--color-review-discrepancy)',
		unknown: 'var(--color-review-unknown)'
	};

	let color = $derived(TONE_COLOR[tone]);

	// A tint DERIVED FROM THE TONE, not an opaque colour picked per screen.
	// The helpers this primitive replaced each hardcoded a background — six sites
	// chose --color-bg and eleven chose --color-surface — because an opaque fill
	// forces the badge to know what it is sitting on, and each file guessed
	// separately. Wrong guess, and the badge reads as a dark well on a card or as
	// no fill at all on the page. A translucent tint composites correctly over
	// either, so the badge stops caring. Border and text stay at full strength,
	// so contrast is unchanged. Where color-mix is unsupported this resolves to
	// an invalid value and the background falls back to transparent — the
	// border-only shape this component shipped with.
	let fill = $derived(`color-mix(in srgb, ${color} 14%, transparent)`);
</script>

<span
	style="
		display: inline-block;
		max-width: 100%;
		border: 1px solid {color};
		background-color: {fill};
		border-radius: 4px;
		padding: var(--space-xs) var(--space-sm);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.02em;
		color: {color};
		white-space: normal;
		overflow-wrap: anywhere;
	"
>{label}</span>
