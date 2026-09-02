/**
 * The tone vocabulary `Badge` understands, extracted from the component so call
 * sites can type their own mapping functions against it.
 *
 * That matters more than it looks: these tones are four separate admin domain
 * vocabularies — an argument's publish lifecycle, a record's trust tier, its
 * review state, and a pipeline job's run state — and before D-01 each screen
 * carried its own copy of the mapping
 * as a style-string builder. With the union exported, a screen that maps a domain
 * value to a tone that does not exist is a compile error rather than a badge that
 * silently renders in the fallback colour.
 */
export type BadgeTone =
	| 'published'
	| 'draft'
	| 'unpublished'
	| 'warning'
	| 'archived'
	| 'neutral'
	| 'verified'
	| 'trusted'
	| 'provisional'
	| 'uncertain'
	| 'unreviewed'
	| 'needs-review'
	| 'confirmed'
	| 'edited'
	| 'discrepancy'
	| 'unknown'
	// Pipeline job run state (D-03, folded into D-01 by the operator's ruling).
	// `pending` maps to `neutral` and `completed` to `published`, which the
	// retired BADGE_COLOR lookup already resolved to the same tokens; only
	// these two had no existing member.
	| 'running'
	| 'failed';

/**
 * The single tone -> token table. `Badge` renders from it, and so does anything
 * that must colour-match a badge without being one — the pipeline step card's
 * `border-left` accent (D-03: the `borderLeft` helper carried its own third
 * copy of the run-state vocabulary). Exported so those stay in lockstep by
 * construction rather than by two lists agreeing.
 */
export const TONE_COLOR: Record<BadgeTone, string> = {
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
	unknown: 'var(--color-review-unknown)',
	running: 'var(--color-accent)',
	failed: 'var(--color-destructive)'
};
