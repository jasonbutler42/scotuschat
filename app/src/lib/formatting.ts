/**
 * Shared display-formatting helpers for the public arguments listing
 * (Phase 51 plan 51-08, D-14/D-15/D-16). One definition site for each rule
 * so `/arguments` (term index) and `/arguments/term/{year}` (term detail)
 * never drift from each other.
 */

/**
 * Format an argued_date string (e.g. "2015-04-28") as "April 28, 2015".
 * Uses Intl.DateTimeFormat per the UI-SPEC Copywriting Contract.
 * The date comes from the API as a date string (YYYY-MM-DD). We append
 * T00:00:00 to force local-date parsing and avoid UTC midnight roll-back
 * on systems west of UTC.
 *
 * Moved out of the transitional `/arguments/+page.svelte` listing (plan
 * 51-02), unchanged, so both listing routes share one definition.
 */
export function formatDate(dateStr: string | null | undefined): string {
	if (!dateStr) return 'Date unknown';
	const date = new Date(dateStr + 'T00:00:00');
	return new Intl.DateTimeFormat('en-US', {
		month: 'long',
		day: 'numeric',
		year: 'numeric'
	}).format(date);
}

/**
 * Format a published-argument count as "1 argument" / "12 arguments".
 * A count of records only (P-01) — never a derived per-speaker statistic.
 */
export function formatArgumentCount(count: number): string {
	return count === 1 ? '1 argument' : `${count} arguments`;
}
