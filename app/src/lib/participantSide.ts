/**
 * Single source of truth for argument-participant side values, shared by
 * BOTH the Resolve card (app/src/lib/components/ResolveCard.svelte) and the
 * argument-detail Speakers card (app/src/routes/admin/arguments/[id]/
 * +page.svelte). Created for G-49-3/D-35 (plan 49-10): the operator's rule —
 * "if an argument is currently published the data is locked, otherwise I
 * expect it to be editable and have almost the exact interface" — requires
 * both editing surfaces to reach the same five stored side values through
 * the same bucket/label logic, so that logic can only live in one place.
 *
 * The bench/advocate bucket rule (`sideBucket`) originates in RESOLVE-09: the
 * Resolve card's person-candidate pools for BENCH and for the three specific
 * advocate roles are disjoint, so a person matched under one bucket must
 * never silently carry over to the other — only a real Bench<->Advocate
 * boundary crossing matters, never a change among PETITIONER/RESPONDENT/
 * AMICUS. Both cards need the identical rule to reason about that boundary.
 *
 * This module has no framework imports and no write path of its own — it is
 * pure display/derivation logic. The backend (api/services/admin_arguments.py
 * ::update_participant_side and api/services/admin_jobs.py::
 * update_resolve_row_for_job) remains the sole persistence authority.
 */

// ---------------------------------------------------------------------------
// Canonical side values, in the order the converged control presents them:
// the unresolved sentinel first (matching today's Speakers-card placeholder
// position), then the bench value, then the three specific advocate roles.
// ---------------------------------------------------------------------------

export const UNRESOLVED_SIDE = 'UNKNOWN';
export const BENCH_SIDE = 'BENCH';
export const ADVOCATE_SIDES = ['PETITIONER', 'RESPONDENT', 'AMICUS'] as const;

export type AdvocateSide = (typeof ADVOCATE_SIDES)[number];
export type SideBucket = 'BENCH' | 'ADVOCATE';

/** All five canonical side values a converged control can offer, in display order. */
export const SIDE_VALUES = [UNRESOLVED_SIDE, BENCH_SIDE, ...ADVOCATE_SIDES] as const;

/**
 * Operator-facing display labels — byte-identical to ResolveCard.svelte's
 * pre-extraction SIDE_LABEL map, including the two legacy fall-throughs
 * (UNKNOWN and the retired ADVOCATE literal both display as plain
 * "Counsel"). Task 3 (the Speakers card) renders its advocate option labels
 * from this map rather than a second hardcoded list, so the two cards can
 * never silently drift in operator-visible copy.
 */
export const SIDE_LABEL: Record<string, string> = {
	BENCH: 'Bench',
	PETITIONER: "Petitioner's Counsel",
	RESPONDENT: "Respondent's Counsel",
	AMICUS: 'Amicus Curiae',
	UNKNOWN: 'Counsel',
	ADVOCATE: 'Counsel', // legacy — never produced going forward
};

/**
 * Returns the specific advocate role (PETITIONER/RESPONDENT/AMICUS) a raw
 * side value represents, or null for BENCH/UNKNOWN/the legacy ADVOCATE
 * literal. Byte-equivalent to ResolveCard.svelte's pre-extraction
 * specificAdvocateRole.
 */
export function specificAdvocateRole(value: string): AdvocateSide | null {
	return value === 'PETITIONER' || value === 'RESPONDENT' || value === 'AMICUS' ? value : null;
}

/**
 * Collapses any side value onto the two-value BENCH/ADVOCATE bucket
 * (RESOLVE-09). Byte-equivalent to ResolveCard.svelte's pre-extraction
 * sideBucket: BENCH is special-cased, every other value (UNKNOWN,
 * PETITIONER, RESPONDENT, AMICUS, and the legacy ADVOCATE literal) collapses
 * to the single ADVOCATE bucket, so switching among specific advocate roles
 * never looks like a boundary crossing.
 */
export function sideBucket(value: string): SideBucket {
	return value === 'BENCH' ? 'BENCH' : 'ADVOCATE';
}

/**
 * Pure boundary-crossing predicate: does moving to `newSide` cross the
 * Bench<->Advocate boundary relative to `previousBucket`? The
 * first-observation case (no previous bucket recorded yet, i.e. `undefined`)
 * is reported as NOT a crossing — the same rule
 * ResolveCard.svelte's clearPersonOnSideBucketChange already implements, so
 * initial load/seeding is never mistaken for an operator-driven switch. Both
 * cards consume this: the Resolve card to decide whether to clear a pending
 * person pick, the Speakers card (Task 3) to decide whether a change needs
 * the two-step confirm.
 */
export function crossesSideBoundary(previousBucket: SideBucket | undefined, newSide: string): boolean {
	if (previousBucket === undefined) return false;
	return previousBucket !== sideBucket(newSide);
}
