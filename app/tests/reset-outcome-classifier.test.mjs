import { test } from 'node:test';
import assert from 'node:assert/strict';

import { classifyFixtureStateOutcome } from '../src/lib/admin/resetOutcome.js';

const EXPECTED = {
	'15169': { status: 'candidate', latest_import_run_step: 'parse' },
	'13015': { status: 'draft', latest_import_run_step: 'parse' },
	'18897': { status: 'published', latest_import_run_step: 'parse' },
	'22372': { status: 'candidate', latest_import_run_step: 'reconcile' },
};

/** All four fixtures in their expected end states. */
const landed = () =>
	Object.entries(EXPECTED).map(([conversation_id, e]) => ({
		conversation_id,
		present: true,
		status: e.status,
		latest_import_run_step: e.latest_import_run_step,
	}));

test('all four landed with no reset in flight -> full-success', () => {
	const state = { fixtures: landed(), progress: null };
	assert.equal(classifyFixtureStateOutcome(state, EXPECTED), 'full-success');
});

test('a reset still in flight -> in-progress, NOT partial', () => {
	// The regression. Fixtures are mid-write and therefore incomplete, but the
	// backend is reporting progress — the operation has not failed, it has not
	// finished. Reported live on 2026-09-25 as "do not use it until you run
	// Reset to Fixture again" over a database that turned out to be perfect.
	const midFlight = landed();
	midFlight[2] = { ...midFlight[2], present: false, status: null, latest_import_run_step: null };
	midFlight[3] = { ...midFlight[3], present: false, status: null, latest_import_run_step: null };
	const state = { fixtures: midFlight, progress: { step: 'reseeding_fixture_3', completed: 2, total: 4 } };
	assert.equal(classifyFixtureStateOutcome(state, EXPECTED), 'in-progress');
});

test('progress wins even when every fixture already looks right', () => {
	// The last poll before completion: rows are all in place but the operation
	// has not cleared its progress record. Claiming success here would race the
	// final state-realization step.
	const state = { fixtures: landed(), progress: { step: 'reseeding_fixture_4', completed: 4, total: 4 } };
	assert.equal(classifyFixtureStateOutcome(state, EXPECTED), 'in-progress');
});

test('a genuinely partial reseed with nothing in flight -> partial', () => {
	const broken = landed();
	broken[1] = { ...broken[1], present: false, status: null, latest_import_run_step: null };
	const state = { fixtures: broken, progress: null };
	assert.equal(classifyFixtureStateOutcome(state, EXPECTED), 'partial');
});

test('a fixture present but in the wrong end state -> partial', () => {
	const wrong = landed();
	wrong[2] = { ...wrong[2], status: 'draft' }; // Published fixture left as draft
	const state = { fixtures: wrong, progress: null };
	assert.equal(classifyFixtureStateOutcome(state, EXPECTED), 'partial');
});

test('no evidence obtained -> inconclusive', () => {
	assert.equal(classifyFixtureStateOutcome(null, EXPECTED), 'inconclusive');
	assert.equal(classifyFixtureStateOutcome({ fixtures: [], progress: null }, EXPECTED), 'inconclusive');
	assert.equal(
		classifyFixtureStateOutcome({ fixtures: landed().slice(0, 3), progress: null }, EXPECTED),
		'inconclusive',
	);
});
