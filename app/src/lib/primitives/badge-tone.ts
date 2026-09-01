/**
 * The tone vocabulary `Badge` understands, extracted from the component so call
 * sites can type their own mapping functions against it.
 *
 * That matters more than it looks: these tones are three separate admin domain
 * vocabularies — an argument's publish lifecycle, a record's trust tier, and its
 * review state — and before D-01 each screen carried its own copy of the mapping
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
	| 'unknown';
