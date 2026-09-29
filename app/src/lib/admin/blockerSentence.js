/**
 * Blocked-publish blocker-code -> operator-readable sentence (Phase 48 D-19,
 * extended Phase 53 D-18).
 *
 * Extracted from three byte-identical copies (`admin/arguments/[id]/+page.svelte`,
 * `admin/arguments/+page.svelte`, `admin/review/+page.svelte`) into one tested
 * module, following the `resetOutcome.js` precedent — pure, unit-tested with
 * `node --test`, so the three admin surfaces can never drift from each other.
 * A bare tier name gives the operator nothing to act on; each sentence names
 * what dragged the tier down, with a count. An unrecognised code (a future
 * blocker added server-side) falls back to naming the raw code rather than
 * vanishing silently.
 *
 * @typedef {{ code: string, count: number, percent?: number }} TierBlocker
 */

/**
 * @param {TierBlocker} blocker
 * @returns {string}
 */
export function blockerSentence(blocker) {
	const { code, count } = blocker;
	const plural = count === 1 ? '' : 's';

	if (code === 'majority_undetermined_speaker') {
		// D-18: the percent is printed exactly as the backend sent it — no
		// client-side rounding or recomputation. A blocker that arrives
		// without a numeric percent degrades to the generic unknown-code
		// sentence below rather than inventing copy (e.g. `undefined%`).
		if (typeof blocker.percent === 'number' && Number.isFinite(blocker.percent)) {
			return `${blocker.percent}% of turns have an undetermined speaker (more than half).`;
		}
	}
	if (code === 'unresolved_utterance_speaker') {
		return `${count} utterance${plural} ${count === 1 ? 'has' : 'have'} no resolved speaker`;
	}
	if (code === 'unresolved_participant') {
		return `${count} participant${plural} ${count === 1 ? 'is' : 'are'} unresolved`;
	}
	if (code === 'llm_corrective_utterance') {
		return `${count} utterance${plural} came from the LLM corrective pass`;
	}
	if (code === 'uncertain_participant') {
		return `${count} participant${plural} ${count === 1 ? 'has' : 'have'} unverified provenance`;
	}
	if (code === 'no_constituents') {
		return 'this argument has no utterances yet';
	}
	return `${count} occurrence${plural} of "${code}"`;
}
