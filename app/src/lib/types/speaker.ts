/**
 * Shared speaker types — the single declaration site for `TenureRow` and
 * `SpeakerDetail`. Previously declared byte-for-byte identically in both
 * `SpeakerPopover.svelte` and `app/src/routes/arguments/[slug]/+page.svelte`
 * (surfaced by Phase 45's code review as IN-02/IN-03, folded into Phase 51's
 * scope). Extracted verbatim, field for field — no shape change.
 *
 * No framework imports; follows the same framework-free shared-module
 * convention as `app/src/lib/participantSide.ts`.
 */

export interface TenureRow {
	// Canonical "chief"/"associate" storage value (Phase 37 D-15/D-17) — formal
	// title projection happens in SpeakerPopover.svelte, not here.
	office: string | null;
	start_date: string | null;
	end_date: string | null;
	// Canonical "retired"/"died"/"promoted" storage value, or null when the
	// tenure has no recorded reason (open tenure, or unknown historical row —
	// Phase 39 D-01/D-02) — formal title projection happens in
	// SpeakerPopover.svelte, not here.
	reason_left: string | null;
	// Phase 39 (D-13, promote not add-alongside): per-tenure appointing
	// president, replacing the retired top-level appointing_president field.
	appointed_by: string | null;
	// Phase 39 (D-11/D-12, reverses T-14-02): factual historical record about
	// the appointing president, not the Justice. Rendered identically for
	// every tenure entry — never styled or ordered by its value.
	appointing_president_party: string | null;
}

export interface SpeakerDetail {
	person_id: number;
	full_name: string;
	role_name: string | null;
	photo_url_full: string | null;
	is_bench: boolean;
	tenure: TenureRow[];
	// Phase 39 (D-13): the top-level appointing_president field retired here
	// — the concept moved onto each TenureRow as appointed_by (see above).
	birthdate: string | null;
	death_date: string | null;
	bio_text: string | null;
}
