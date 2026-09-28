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

/**
 * Mirrors api/services/admin_dev.py's FIXTURE_SET and the exact per-fixture
 * end state its state-realization step leaves behind on a FULLY successful
 * reset (Phase 52-05, D-16). Shared by the server action's D-14 re-read and
 * the page's own post-still-running poll, so both judge completion by one
 * definition.
 *
 * @type {Record<string, ExpectedEndState>}
 */
export const EXPECTED_FIXTURE_END_STATES = {
	'15169': { status: 'candidate', latest_import_run_step: 'parse' },
	'13015': { status: 'draft', latest_import_run_step: 'parse' },
	'18897': { status: 'published', latest_import_run_step: 'parse' },
	'22372': { status: 'candidate', latest_import_run_step: 'reconcile' },
};

export const RESET_MID_ERROR =
	'Reset failed partway through — the database may be in an inconsistent state. Check server logs before retrying.';

// The re-read confirms a genuine partial reseed — some but not all fixtures
// present, or one in an unexpected state.
export const RESET_PARTIAL_ERROR =
	'Reset failed partway through. A follow-up check found the database only partially reseeded — do not use it until you run Reset to Fixture again.';

/**
 * Maps a full-success fixture-state snapshot to the `resetFixtures` shape the
 * Success markup renders.
 *
 * @param {FixtureStateResponse} state
 */
export function toResetFixtures(state) {
	return state.fixtures.map((fixture) => ({
		conversation_id: fixture.conversation_id,
		case_name: /** @type {any} */ (fixture).case_name,
		role: /** @type {any} */ (fixture).role,
		argument_id: /** @type {number} */ (/** @type {any} */ (fixture).argument_id),
		argument_status: /** @type {string} */ (fixture.status),
		latest_import_run_step: /** @type {string} */ (fixture.latest_import_run_step),
	}));
}
