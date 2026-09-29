/**
 * Phase 53 Plan 03 Task 1 (SPEAKER-01, D-01/D-02) — Treatment D, proven end
 * to end against the real public argument view (`/arguments/[slug]`) over a
 * mock FASTAPI backend, using the shared `openTranscriptPage` harness lifted
 * from `speaker-initials.browser.test.mjs` into `helpers/transcript-page.mjs`.
 *
 * A source-unattributed turn renders as a centred bubble between two empty
 * 40px rails, two consecutive unattributed turns stay separate (S5), and no
 * source sentinel string reaches the page — even when a fixture row
 * deliberately carries one in `raw_speaker_label`.
 *
 * RED run against the pre-fix route (this test, `git checkout --` on
 * app.css/+page.svelte, `UndeterminedBubble.svelte` removed): the sentinel
 * `<INAUDIBLE>` leaked through two paths — the roster's Bench-column name
 * `<p>` and the transcript row's speaker-name `<span class="speaker-ink">`
 * (ChatBubble's `speaker_name ?? raw_speaker_label` fallback) — confirming
 * Pitfall 6 before the fix below closed both by construction.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { openTranscriptPage, waitForExpression } from './helpers/transcript-page.mjs';

const ARGUMENT_SLUG = 'fixture-v-undetermined';

// The source's own "no identifiable speaker" sentinel form (D-05). Used only
// here, in a fixture row, to prove the page never echoes it back as visible
// text — app/src never quotes this literal (Pitfall 6).
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
	'an undetermined turn renders as Treatment D, consecutive ones stay separate, and no sentinel string reaches the page',
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

			// Wait for hydration: all four top-level render items mounted
			// (2 attributed runs + 2 Treatment D rows = 4 `role="article"`).
			await waitForExpression(cdp, `document.querySelectorAll('[role="article"]').length >= 4`);

			// --- S5 + row shape: exactly two separate Treatment D rows, each
			// carrying the label -------------------------------------------------
			const undeterminedRows = await cdp.evaluate(`
				[...document.querySelectorAll('[role="article"][aria-label="Undetermined speaker"]')]
					.map((el) => el.textContent)
			`);
			assert.equal(undeterminedRows.length, 2, 'expected exactly two separate Treatment D rows (S5)');
			for (const text of undeterminedRows) {
				assert.ok(text.includes('undetermined speaker'), `row text missing label: ${text}`);
			}

			// --- No sentinel string reaches the page as visible text ------------
			const bodyText = await cdp.evaluate('document.body.innerText');
			assert.ok(!bodyText.includes('<INAUDIBLE>'), 'sentinel <INAUDIBLE> leaked into rendered text');
			assert.ok(!bodyText.includes('<UNKNOWN>'), 'sentinel <UNKNOWN> leaked into rendered text');

			// --- Roster: exactly two names, none blank ---------------------------
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

			// --- Geometry at 1280x900 ---------------------------------------------
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

			assert.equal(geometry.length, 2);
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

			// --- Label computed style ----------------------------------------------
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

			// --- No speaker-identity class anywhere inside a Treatment D row -------
			const speakerClassCount = await cdp.evaluate(`
				[...document.querySelectorAll('.undetermined-row .speaker-fill, .undetermined-row .speaker-ink, .undetermined-row .speaker-stroke')].length
			`);
			assert.equal(speakerClassCount, 0);

			// --- Mobile (390x844): no horizontal overflow, bubble stays inside rails
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
		} finally {
			await harness?.close();
		}
	}
);
