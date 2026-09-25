/**
 * Reset-to-fixture outcome classification (Phase 52-05, D-14).
 *
 * Extracted from `+page.server.ts` so it can be unit-tested directly. It is
 * pure — evidence in, outcome out, no I/O — and it decides what the operator
 * is told after a destructive operation, which is exactly the kind of logic
 * that should not have been untestable.
 *
 * It shipped untested, and a real defect followed: the original version read
 * only `fixtures` and never `progress`, so an AbortSignal that fired while the
 * server was still working yielded a legitimately incomplete snapshot that was
 * reported as a partial reseed — telling the operator not to use a database
 * that was, in fact, completely correct.
 *
 * @typedef {{ status: string, latest_import_run_step: string }} ExpectedEndState
 * @typedef {{
 *   conversation_id: string,
 *   present: boolean,
 *   status: string | null,
 *   latest_import_run_step: string | null,
 * }} FixtureStateItem
 * @typedef {{
 *   fixtures: FixtureStateItem[],
 *   progress: { step: string, completed: number, total: number } | null,
 * }} FixtureStateResponse
 */

/**
 * @param {FixtureStateResponse | null} state
 * @param {Record<string, ExpectedEndState>} expected
 * @returns {'in-progress' | 'full-success' | 'partial' | 'inconclusive'}
 */
export function classifyFixtureStateOutcome(state, expected) {
	if (!state || !Array.isArray(state.fixtures) || state.fixtures.length !== 4) {
		return 'inconclusive';
	}

	// Checked BEFORE the fixtures are judged, and deliberately so: while a reset
	// is in flight the fixture rows are a moving target, so an incomplete
	// snapshot is expected rather than evidence of failure. Reading `fixtures`
	// first is what let a still-running reset be reported as a partial one.
	if (state.progress !== null && state.progress !== undefined) {
		return 'in-progress';
	}

	const allLandedAsExpected = state.fixtures.every((fixture) => {
		const want = expected[fixture.conversation_id];
		return (
			want !== undefined &&
			fixture.present === true &&
			fixture.status === want.status &&
			fixture.latest_import_run_step === want.latest_import_run_step
		);
	});

	return allLandedAsExpected ? 'full-success' : 'partial';
}
