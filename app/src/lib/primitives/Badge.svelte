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
	// Four admin vocabularies, one shape: an argument's publish lifecycle, a
	// record's trust tier, where it sits in the review queue, and a pipeline
	// job's run state. They were
	// near-identical helper functions duplicated across five files
	// (51-ADMIN-ARTIFACTS.md D-01/D-03) until the operator ruled them here. The
	// union lives in badge-tone.ts so call sites can type their mappings.
	import type { Snippet } from 'svelte';
	import { type BadgeTone, TONE_COLOR } from './badge-tone';

	interface BadgeProps {
		label: string;
		tone?: BadgeTone;
		// An optional glyph rendered before the label — the pipeline step card's
		// spinner (D-03). Present only where a badge carries a live affordance;
		// without it the badge stays `inline-block`, which the min-content
		// reasoning at the bottom of this file depends on.
		leading?: Snippet;
		// Accessible name for a badge whose visible text is not the whole story
		// (again the spinner: the glyph is aria-hidden, so the pill needs a name).
		ariaLabel?: string;
	}

	let { label, tone = 'neutral', leading, ariaLabel }: BadgeProps = $props();

	// Neutral reuses --color-text-secondary — the same "muted, non-signal"
	// token ResolveCard's manually-matched cue tag already uses for a
	// disclosure that is neither a warning nor a success signal.

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

	// WHY nowrap, and why no max-width — this cost a real regression on
	// /admin/review, so it is written down rather than left to be rediscovered.
	//
	// This component shipped with `max-width: 100%; white-space: normal;
	// overflow-wrap: anywhere`, intended as long-text protection. But
	// `overflow-wrap: anywhere` REDUCES an element's min-content contribution —
	// that is its defining difference from `break-word` — so a table using
	// automatic layout sized the badge column as though the label could break at
	// any character. The cell itself is `white-space: nowrap` (G-49-5a: this
	// table's no-wrap cells deliberately pin a min-content width wider than the
	// viewport so the container scrolls rather than the page). Two inline-blocks
	// that cannot wrap, inside a column sized for a broken one, overflowed 76px
	// into the next column. The labels were also wrapping mid-word inside the
	// pill, which is what a 42px-tall badge beside a 26px one looks like.
	//
	// A badge label is short, controlled vocabulary — never the unbreakable URL
	// or identifier `anywhere` exists for. So it does not wrap, and it does not
	// cap its width; it contributes its true min-content size and lets the
	// container decide. That is the same contract the surrounding table already
	// relies on, and it keeps the no-truncation rule (49-UI-SPEC E1/E2) intact:
	// nothing here is clipped or ellipsised, it scrolls.
</script>

<span
	aria-label={ariaLabel}
	style="
		display: {leading ? 'inline-flex' : 'inline-block'};
		align-items: center;
		gap: var(--space-xs);
		border: 1px solid {color};
		background-color: {fill};
		border-radius: 4px;
		padding: var(--space-xs) var(--space-sm);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.02em;
		color: {color};
		white-space: nowrap;
	"
>{#if leading}{@render leading()}{/if}{label}</span>
