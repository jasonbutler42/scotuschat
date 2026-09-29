import { test } from 'node:test';
import assert from 'node:assert/strict';

import { blockerSentence } from '../src/lib/admin/blockerSentence.js';

test('majority_undetermined_speaker with percent 68 -> locked D-18 sentence', () => {
	assert.equal(
		blockerSentence({ code: 'majority_undetermined_speaker', count: 100, percent: 68 }),
		'68% of turns have an undetermined speaker (more than half).',
	);
});

test('majority_undetermined_speaker with percent 50 -> locked D-18 sentence', () => {
	assert.equal(
		blockerSentence({ code: 'majority_undetermined_speaker', count: 100, percent: 50 }),
		'50% of turns have an undetermined speaker (more than half).',
	);
});

test('majority_undetermined_speaker with no percent key -> generic unknown-code fallback', () => {
	assert.equal(
		blockerSentence({ code: 'majority_undetermined_speaker', count: 100 }),
		'100 occurrences of "majority_undetermined_speaker"',
	);
});

test('unresolved_utterance_speaker, count 1 -> singular', () => {
	assert.equal(
		blockerSentence({ code: 'unresolved_utterance_speaker', count: 1 }),
		'1 utterance has no resolved speaker',
	);
});

test('unresolved_utterance_speaker, count 2 -> plural', () => {
	assert.equal(
		blockerSentence({ code: 'unresolved_utterance_speaker', count: 2 }),
		'2 utterances have no resolved speaker',
	);
});

test('unresolved_participant, count 1 -> singular', () => {
	assert.equal(
		blockerSentence({ code: 'unresolved_participant', count: 1 }),
		'1 participant is unresolved',
	);
});

test('unresolved_participant, count 2 -> plural', () => {
	assert.equal(
		blockerSentence({ code: 'unresolved_participant', count: 2 }),
		'2 participants are unresolved',
	);
});

test('llm_corrective_utterance, count 1 -> singular', () => {
	assert.equal(
		blockerSentence({ code: 'llm_corrective_utterance', count: 1 }),
		'1 utterance came from the LLM corrective pass',
	);
});

test('llm_corrective_utterance, count 2 -> plural', () => {
	assert.equal(
		blockerSentence({ code: 'llm_corrective_utterance', count: 2 }),
		'2 utterances came from the LLM corrective pass',
	);
});

test('uncertain_participant, count 1 -> singular', () => {
	assert.equal(
		blockerSentence({ code: 'uncertain_participant', count: 1 }),
		'1 participant has unverified provenance',
	);
});

test('uncertain_participant, count 2 -> plural', () => {
	assert.equal(
		blockerSentence({ code: 'uncertain_participant', count: 2 }),
		'2 participants have unverified provenance',
	);
});

test('no_constituents -> fixed sentence regardless of count', () => {
	assert.equal(
		blockerSentence({ code: 'no_constituents', count: 0 }),
		'this argument has no utterances yet',
	);
});

test('unknown code -> generic fallback naming the raw code, singular', () => {
	assert.equal(
		blockerSentence({ code: 'some_future_code', count: 1 }),
		'1 occurrence of "some_future_code"',
	);
});

test('unknown code -> generic fallback naming the raw code, plural', () => {
	assert.equal(
		blockerSentence({ code: 'some_future_code', count: 3 }),
		'3 occurrences of "some_future_code"',
	);
});
