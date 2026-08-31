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
	type BadgeTone = 'published' | 'draft' | 'unpublished' | 'warning' | 'archived' | 'neutral';

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
		neutral: 'var(--color-text-secondary)'
	};

	let color = $derived(TONE_COLOR[tone]);
</script>

<span
	style="
		display: inline-block;
		max-width: 100%;
		border: 1px solid {color};
		border-radius: 4px;
		padding: 2px var(--space-sm);
		font-size: var(--font-size-caption);
		font-weight: var(--font-weight-semibold);
		letter-spacing: 0.02em;
		color: {color};
		white-space: normal;
		overflow-wrap: anywhere;
	"
>{label}</span>
