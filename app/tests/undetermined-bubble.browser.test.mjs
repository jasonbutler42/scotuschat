/**
 * Phase 53 Plan 03 (SPEAKER-01/06/07, D-01/D-02/D-12/D-13) — Treatment D and
 * the whole-turn inaudible body, proven end to end against the real public
 * argument view (`/arguments/[slug]`) over a mock FASTAPI backend, using the
 * shared `openTranscriptPage` harness lifted from
 * `speaker-initials.browser.test.mjs` into `helpers/transcript-page.mjs`.
 *
 * Task 1 covers Treatment D at rest: a source-unattributed turn renders as a
 * centred bubble between two empty 40px rails, two consecutive unattributed
 * turns stay separate (S5), and no source sentinel string reaches the page —
 * even when a fixture row deliberately carries one in `raw_speaker_label`.
 *
 * Task 2 extends the same fixture and file with the whole-turn inaudible
 * body treatment (D-12/D-13): identical italic/muted-ink styling wherever a
 * whole-turn marker body appears — an ordinary attributed bubble or a
 * Treatment D bubble alike — driven only by the stored `is_inaudible_marker`
 * fact, never by matching the body text.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { openTranscriptPage, waitForExpression } from './helpers/transcript-page.mjs';

const ARGUMENT_SLUG = 'fixture-v-undetermined';

// The source's own "no identifiable speaker" sentinel form (D-05). Used only
// here, in a fixture row, to prove the page never echoes it back as visible
// text — app/src never quotes this literal (Task 1's <objective> note).
const SENTINEL_LABEL = '<INAUDIBLE>';

// A body long enough that Treatment D's max-width cap actually binds, rather
// than the bubble merely shrinking to short content.
const LONG_BODY =
	'These words were spoken clearly, but the record does not preserve which participant in the ' +
	'courtroom that day actually produced them, so the turn is left honestly unattributed rather ' +
	'than guessed at by anyone reading the transcript after the fact, today or a century from now.';

function argumentPayload() {
	return {
		argument: {
			argument_id: 5301,
			case_name: 'Fixture v. Undetermined',
			docket_number: '24-301',
			argued_date: '2024-11-05',
			question_number: 1,
			oyez_transcript_id: null,
		},
		utterances: [
			{
				id: 1,
				sequence: 1,
				argument_id: 5301,
				import_run_id: 1,
				person_id: 1,
				side: 'BENCH',
				speaker_name: 'Justice Fixture',
				raw_speaker_label: 'JUSTICE FIXTURE',
				speaker_role: null,
				speaker_initials: 'JF',
				text: 'Please proceed, counsel.',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: false,
				is_inaudible_marker: false,
			},
			{
				id: 2,
				sequence: 2,
				argument_id: 5301,
				import_run_id: 1,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: SENTINEL_LABEL,
				speaker_role: null,
				speaker_initials: null,
				text: LONG_BODY,
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: true,
				is_inaudible_marker: false,
			},
			{
				id: 3,
				sequence: 3,
				argument_id: 5301,
				import_run_id: 1,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: null,
				speaker_role: null,
				speaker_initials: null,
				text: 'A second, separate turn the record could not attribute to anyone.',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: true,
				is_inaudible_marker: false,
			},
			{
				id: 4,
				sequence: 4,
				argument_id: 5301,
				import_run_id: 1,
				person_id: 2,
				side: 'ADVOCATE',
				speaker_name: 'Advocate Fixture',
				raw_speaker_label: 'MR. FIXTURE',
				speaker_role: null,
				speaker_initials: 'AF',
				text: 'Thank you, Your Honor.',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: false,
				is_inaudible_marker: false,
			},
			{
				id: 5,
				sequence: 5,
				argument_id: 5301,
				import_run_id: 1,
				person_id: 2,
				side: 'ADVOCATE',
				speaker_name: 'Advocate Fixture',
				raw_speaker_label: 'MR. FIXTURE',
				speaker_role: null,
				speaker_initials: 'AF',
				text: '(Inaudible)',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: false,
				is_inaudible_marker: true,
			},
			{
				id: 6,
				sequence: 6,
				argument_id: 5301,
				import_run_id: 1,
				person_id: 1,
				side: 'BENCH',
				speaker_name: 'Justice Fixture',
				raw_speaker_label: 'JUSTICE FIXTURE',
				speaker_role: null,
				speaker_initials: 'JF',
				text: '(Inaudible)',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: false,
				is_inaudible_marker: true,
			},
			{
				id: 7,
				sequence: 7,
				argument_id: 5301,
				import_run_id: 1,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: null,
				speaker_role: null,
				speaker_initials: null,
				text: '(Inaudible)',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: true,
				is_inaudible_marker: true,
			},
			{
				id: 8,
				sequence: 8,
				argument_id: 5301,
				import_run_id: 1,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: null,
				speaker_role: null,
				speaker_initials: null,
				text: '(Laughter)',
				is_stage_direction: true,
				section_hint: null,
				speaker_undetermined: false,
				is_inaudible_marker: false,
			},
		],
	};
}

function speakersPayload() {
	return [
		{
			person_id: 1,
			full_name: 'Justice Fixture',
			role_name: null,
			photo_url: null,
			initials: 'JF',
			tenure: [],
			side: 'BENCH',
		},
		{
			person_id: 2,
			full_name: 'Advocate Fixture',
			role_name: null,
			photo_url: null,
			initials: 'AF',
			tenure: [],
			side: 'ADVOCATE',
		},
	];
}

test(
	'an undetermined turn renders as Treatment D, consecutive ones stay separate, no sentinel string reaches the page, and a whole-turn inaudible body reads identically everywhere',
	{ timeout: 120_000 },
	async () => {
		let harness;
		try {
			harness = await openTranscriptPage({
				slug: ARGUMENT_SLUG,
				argumentPayload: argumentPayload(),
				speakersPayload: speakersPayload(),
				viewport: { width: 1280, height: 900 },
			});
			const { cdp, setViewport } = harness;

			// Wait for hydration: every run/undetermined top-level item mounted.
			// Runs: [seq1 bench] [seq4+seq5 advocate] [seq6 bench] = 3 runs.
			// Plus 2 undetermined rows (seq2, seq3) and 1 more undetermined row
			// (seq7) = 3 undetermined rows. Total role="article" = 6.
			await waitForExpression(cdp, `document.querySelectorAll('[role="article"]').length >= 6`);

			// === Task 1: Treatment D at rest =====================================

			const undeterminedRows = await cdp.evaluate(`
				[...document.querySelectorAll('[role="article"][aria-label="Undetermined speaker"]')]
					.map((el) => el.textContent)
			`);
			assert.equal(undeterminedRows.length, 3, 'expected three separate Treatment D rows (S5)');
			for (const text of undeterminedRows) {
				assert.ok(text.includes('undetermined speaker'), `row text missing label: ${text}`);
			}

			const bodyText = await cdp.evaluate('document.body.innerText');
			assert.ok(!bodyText.includes('<INAUDIBLE>'), 'sentinel <INAUDIBLE> leaked into rendered text');
			assert.ok(!bodyText.includes('<UNKNOWN>'), 'sentinel <UNKNOWN> leaked into rendered text');

			const rosterNames = await cdp.evaluate(`
				[...document.querySelectorAll('p')]
					.filter((el) => (el.getAttribute('style') || '').includes('font-size:var(--font-size-body)'))
					.map((el) => el.textContent.trim())
			`);
			assert.equal(rosterNames.length, 2, `expected exactly 2 roster names, got: ${JSON.stringify(rosterNames)}`);
			for (const name of rosterNames) {
				assert.ok(name.length > 0, 'roster contained a blank name');
			}
			assert.deepEqual([...rosterNames].sort(), ['Advocate Fixture', 'Justice Fixture']);

			const geometry = await cdp.evaluate(`
				(() => {
					const rows = [...document.querySelectorAll('.undetermined-row')];
					return rows.map((row) => {
						const leftRail = row.querySelector('.undetermined-rail-left');
						const rightRail = row.querySelector('.undetermined-rail-right');
						const bubble = row.children[1];
						const rowRect = row.getBoundingClientRect();
						const leftRect = leftRail.getBoundingClientRect();
						const rightRect = rightRail.getBoundingClientRect();
						const bubbleRect = bubble.getBoundingClientRect();

						function effectiveOpacity(el, rail) {
							let node = el;
							let product = 1;
							while (node && node !== rail.parentElement) {
								product *= parseFloat(getComputedStyle(node).opacity || '1');
								node = node.parentElement;
							}
							return product;
						}
						const leftVisible = [...leftRail.querySelectorAll('*')].some((el) => effectiveOpacity(el, leftRail) > 0);
						const rightVisible = [...rightRail.querySelectorAll('*')].some((el) => effectiveOpacity(el, rightRail) > 0);

						return {
							rowWidth: rowRect.width,
							leftRailWidth: leftRect.width,
							rightRailWidth: rightRect.width,
							leftGap: bubbleRect.left - leftRect.right,
							rightGap: rightRect.left - bubbleRect.right,
							bubbleWidth: bubbleRect.width,
							leftHasVisibleDescendant: leftVisible,
							rightHasVisibleDescendant: rightVisible,
						};
					});
				})()
			`);

			assert.equal(geometry.length, 3);
			for (const row of geometry) {
				assert.ok(Math.abs(row.leftRailWidth - 40) < 0.5, `left rail not 40px: ${row.leftRailWidth}`);
				assert.ok(Math.abs(row.rightRailWidth - 40) < 0.5, `right rail not 40px: ${row.rightRailWidth}`);
				assert.ok(
					Math.abs(row.leftGap - row.rightGap) <= 1,
					`bubble not centred: left gap ${row.leftGap}, right gap ${row.rightGap}`
				);
				assert.equal(row.leftHasVisibleDescendant, false, 'left rail has a visible descendant at rest');
				assert.equal(row.rightHasVisibleDescendant, false, 'right rail has a visible descendant at rest');
			}
			const longRow = geometry[0]; // seq 2, the ~300-char body, is the first Treatment D row rendered
			assert.ok(
				longRow.bubbleWidth <= longRow.rowWidth * 0.67 + 1,
				`long-body bubble width ${longRow.bubbleWidth} exceeds 0.67 x row width ${longRow.rowWidth}`
			);

			const labelStyle = await cdp.evaluate(`
				(() => {
					const label = [...document.querySelectorAll('.undetermined-row span')]
						.find((el) => el.textContent.trim() === 'undetermined speaker');
					if (!label) return null;
					const style = getComputedStyle(label);
					return { fontStyle: style.fontStyle, opacity: style.opacity, fontWeight: style.fontWeight };
				})()
			`);
			assert.ok(labelStyle, 'undetermined speaker label not found');
			assert.equal(labelStyle.fontStyle, 'italic');
			assert.equal(labelStyle.opacity, '0.7');
			assert.equal(labelStyle.fontWeight, '400');

			const speakerClassCount = await cdp.evaluate(`
				[...document.querySelectorAll('.undetermined-row .speaker-fill, .undetermined-row .speaker-ink, .undetermined-row .speaker-stroke')].length
			`);
			assert.equal(speakerClassCount, 0);

			await setViewport(390, 844);
			await new Promise((resolve) => setTimeout(resolve, 150)); // let layout settle after resize
			const mobileGeometry = await cdp.evaluate(`
				(() => {
					const scrollWidth = document.documentElement.scrollWidth;
					const innerWidth = window.innerWidth;
					const rows = [...document.querySelectorAll('.undetermined-row')].map((row) => {
						const rightRail = row.querySelector('.undetermined-rail-right');
						const bubble = row.children[1];
						return {
							bubbleRight: bubble.getBoundingClientRect().right,
							rightRailLeft: rightRail.getBoundingClientRect().left,
						};
					});
					return { scrollWidth, innerWidth, rows };
				})()
			`);
			assert.ok(
				mobileGeometry.scrollWidth <= mobileGeometry.innerWidth,
				`horizontal overflow at 390px: scrollWidth ${mobileGeometry.scrollWidth} > innerWidth ${mobileGeometry.innerWidth}`
			);
			for (const row of mobileGeometry.rows) {
				assert.ok(
					row.bubbleRight <= row.rightRailLeft + 0.5,
					`bubble right edge (${row.bubbleRight}) not left of right rail's left edge (${row.rightRailLeft}) at 390px`
				);
			}
			await setViewport(1280, 900);
			await new Promise((resolve) => setTimeout(resolve, 150));

			// === Task 2: whole-turn inaudible body, identical everywhere =========
			//
			// Render order of bodies via `.utterance-body`: seq1 (ordinary bench),
			// seq2 (undetermined, ordinary body), seq3 (undetermined, ordinary
			// body), seq4 (ordinary advocate, run start), seq5 (inaudible,
			// continues seq4's run), seq6 (inaudible, bench), seq7 (inaudible,
			// undetermined). seq8 is a stage direction — StageDirection.svelte's
			// own paragraph, not `.utterance-body`.
			const bodies = await cdp.evaluate(`
				[...document.querySelectorAll('.utterance-body')].map((el) => {
					const style = getComputedStyle(el);
					return {
						text: el.textContent.trim(),
						fontStyle: style.fontStyle,
						color: style.color,
						fontSize: style.fontSize,
						lineHeight: style.lineHeight,
					};
				})
			`);
			assert.equal(bodies.length, 7, `expected 7 utterance bodies, got: ${JSON.stringify(bodies)}`);
			const [seq1, seq2, seq3, seq4, seq5, seq6, seq7] = bodies;

			const stageDirectionColor = await cdp.evaluate(`
				getComputedStyle(document.querySelector('[role="note"] p')).color
			`);
			const h1Color = await cdp.evaluate(`getComputedStyle(document.querySelector('h1')).color`);

			// Ordinary bodies: normal style, ink equal to the page h1's ink
			// (both --color-text-primary).
			for (const ordinary of [seq1, seq4]) {
				assert.equal(ordinary.fontStyle, 'normal');
				assert.equal(ordinary.color, h1Color);
			}
			assert.equal(seq2.fontStyle, 'normal', 'undetermined ordinary body should not be italic');
			assert.equal(seq3.fontStyle, 'normal', 'undetermined ordinary body should not be italic');

			// Whole-turn inaudible bodies (seq5 attributed, seq6 attributed, seq7
			// undetermined): italic, same colour as the stage-direction body,
			// same lead size/line-height as an ordinary body.
			for (const [label, body] of [['seq5', seq5], ['seq6', seq6], ['seq7', seq7]]) {
				assert.equal(body.fontStyle, 'italic', `${label} body should be italic`);
				assert.equal(body.color, stageDirectionColor, `${label} body colour should match stage-direction ink`);
			}
			assert.equal(seq5.fontSize, seq4.fontSize);
			assert.equal(seq5.lineHeight, seq4.lineHeight);
			assert.equal(seq7.fontSize, seq4.fontSize);
			assert.equal(seq7.lineHeight, seq4.lineHeight);

			// The run containing seq4+seq5 still shows the advocate's name once
			// and one avatar with the advocate's initials; seq6's run shows the
			// bench speaker's name and avatar.
			const runNamesAndInitials = await cdp.evaluate(`
				[...document.querySelectorAll('[role="article"]:not([aria-label="Undetermined speaker"])')].map((row) => ({
					ariaLabel: row.getAttribute('aria-label'),
					nameCount: row.querySelectorAll('.speaker-ink').length,
					initials: [...row.querySelectorAll('.speaker-fill')].map((el) => el.textContent.trim()),
				}))
			`);
			const advocateRun = runNamesAndInitials.find((r) => r.ariaLabel.includes('Advocate Fixture'));
			assert.ok(advocateRun, 'advocate run not found');
			assert.equal(advocateRun.nameCount, 1, 'advocate name should render once for the whole run');
			assert.deepEqual(advocateRun.initials, ['AF']);

			const benchRunWithInaudible = runNamesAndInitials.filter((r) => r.ariaLabel.includes('Justice Fixture'));
			assert.ok(benchRunWithInaudible.length >= 1, 'bench run(s) not found');
			for (const run of benchRunWithInaudible) {
				assert.deepEqual(run.initials, ['JF']);
			}

			// Stage direction body is still italic.
			const stageDirectionStyle = await cdp.evaluate(`
				getComputedStyle(document.querySelector('[role="note"] p')).fontStyle
			`);
			assert.equal(stageDirectionStyle, 'italic');
		} finally {
			await harness?.close();
		}
	}
);
