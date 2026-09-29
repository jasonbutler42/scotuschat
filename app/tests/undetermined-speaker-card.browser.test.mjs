/**
 * Phase 53 Plan 04 (SPEAKER-02, D-01/D-14/D-15/D-16) — Treatment D's
 * interaction: a dashed `?` avatar in both rails, revealed together on
 * hover, keyboard focus or touch, either opening the explanation card in
 * the shared popover.
 *
 * Task 1 covers hover + click: both avatars invisible at rest, both reveal
 * together on hover, either opens `.undetermined-card` anchored to the
 * activated side, Escape dismisses, the bubble body itself is inert, and
 * the shared popover switches cleanly between the explanation card and the
 * ordinary speaker-bio card.
 *
 * Task 2 extends this file with keyboard focus, touch tap and the D-15
 * lost-words first-paragraph swap.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import { openTranscriptPage, waitForExpression } from './helpers/transcript-page.mjs';

const ARGUMENT_SLUG = 'fixture-v-undetermined-card';

function argumentPayload() {
	return {
		argument: {
			argument_id: 5401,
			case_name: 'Fixture v. Undetermined Card',
			docket_number: '24-401',
			argued_date: '2024-11-06',
			question_number: 1,
			oyez_transcript_id: null,
		},
		utterances: [
			{
				id: 101,
				sequence: 1,
				argument_id: 5401,
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
				id: 202,
				sequence: 2,
				argument_id: 5401,
				import_run_id: 1,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: null,
				speaker_role: null,
				speaker_initials: null,
				text: 'A turn the record could not attribute to anyone.',
				is_stage_direction: false,
				section_hint: null,
				speaker_undetermined: true,
				is_inaudible_marker: false,
			},
			{
				id: 303,
				sequence: 3,
				argument_id: 5401,
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

const CARD_PARAGRAPH_1_ORDINARY =
	'The words here were captured clearly. What the record does not say is which person spoke them.';
const CARD_PARAGRAPH_2 =
	'Oyez attributes each turn by listening to the argument audio. Where a voice could not be matched to a participant, the turn is left unattributed rather than guessed.';
const CARD_PARAGRAPH_3 =
	'Everyone who spoke was present in the courtroom that day — the record simply does not identify which of them this was.';

/** Retries a click until it registers — hydration may not have attached
 *  listeners yet on the first attempt, matching the existing tests' pattern. */
async function clickUntilEffect(cdp, selector, checkExpression, attempts = 40) {
	for (let i = 0; i < attempts; i++) {
		await cdp.evaluate(`document.querySelector(${JSON.stringify(selector)})?.click()`);
		if (await cdp.evaluate(checkExpression)) return;
		await new Promise((resolve) => setTimeout(resolve, 100));
	}
	throw new Error(`Timed out waiting for click effect: ${selector} / ${checkExpression}`);
}

test(
	'hovering an undetermined bubble reveals both dashed avatars, and either opens the explanation card',
	{ timeout: 120_000 },
	async () => {
		let harness;
		try {
			harness = await openTranscriptPage({
				slug: ARGUMENT_SLUG,
				argumentPayload: argumentPayload(),
				speakersPayload: speakersPayload(),
				viewport: { width: 1280, height: 900 },
				// Headless Chromium always reports hover:none/pointer:coarse on this
				// host (see helpers/transcript-page.mjs) — this test's very first
				// assertion is matchMedia('(hover: hover)').matches, so it needs a
				// real windowed browser to mean anything.
				realPointer: true,
			});
			const { cdp } = harness;

			await waitForExpression(cdp, `document.querySelectorAll('[role="article"]').length >= 3`);

			// matchMedia asserted first: a hover-media miss is diagnosable rather
			// than reading as a silent reveal failure downstream.
			const hoverMediaMatches = await cdp.evaluate(`matchMedia('(hover: hover)').matches`);
			assert.equal(hoverMediaMatches, true, 'expected (hover: hover) to match in the headless page');

			// === Rest: both avatars invisible, in the DOM, in tab order =========

			const restState = await cdp.evaluate(`
				(() => {
					const buttons = [...document.querySelectorAll('.undetermined-avatar')];
					return buttons.map((btn) => ({
						opacity: getComputedStyle(btn).opacity,
						ariaLabel: btn.getAttribute('aria-label'),
						text: btn.textContent.trim(),
						tabIndex: btn.tabIndex,
						displayNone: getComputedStyle(btn).display === 'none',
						ariaHidden: btn.getAttribute('aria-hidden'),
						borderStyle: getComputedStyle(btn.firstElementChild).borderStyle,
						hasSpeakerClass: btn.className.includes('speaker-'),
					}));
				})()
			`);
			assert.equal(restState.length, 2, `expected exactly 2 undetermined avatars, got ${restState.length}`);
			for (const btn of restState) {
				assert.equal(btn.opacity, '0', 'avatar should be invisible at rest');
				assert.equal(btn.ariaLabel, 'Undetermined speaker details');
				assert.equal(btn.text, '?');
				assert.ok(btn.tabIndex >= 0, 'avatar button must be in tab order');
				assert.equal(btn.displayNone, false, 'avatar must not use display:none to hide');
				assert.notEqual(btn.ariaHidden, 'true', 'the button itself must not be aria-hidden');
				assert.equal(btn.borderStyle, 'dashed');
				assert.equal(btn.hasSpeakerClass, false, 'avatar must carry no speaker-identity class');
			}

			// === Geometry: avatar sits at the rail edge nearest the bubble =======

			const geometry = await cdp.evaluate(`
				(() => {
					const row = document.querySelector('.undetermined-row');
					const bubble = row.children[1];
					const leftAvatar = row.querySelector('.undetermined-rail-left .undetermined-avatar');
					const rightAvatar = row.querySelector('.undetermined-rail-right .undetermined-avatar');
					const bubbleRect = bubble.getBoundingClientRect();
					const leftRect = leftAvatar.getBoundingClientRect();
					const rightRect = rightAvatar.getBoundingClientRect();
					return {
						leftGap: bubbleRect.left - leftRect.right,
						rightGap: rightRect.left - bubbleRect.right,
					};
				})()
			`);
			assert.ok(
				Math.abs(geometry.leftGap - geometry.rightGap) <= 1,
				`avatar-to-bubble distance not equal: left ${geometry.leftGap}, right ${geometry.rightGap}`
			);

			// === Hover reveals both together ======================================

			const rowBox = await cdp.evaluate(`
				(() => {
					const row = document.querySelector('.undetermined-row');
					const rect = row.getBoundingClientRect();
					return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
				})()
			`);
			await cdp.call('Input.dispatchMouseEvent', {
				type: 'mouseMoved',
				x: rowBox.x,
				y: rowBox.y,
			});
			await waitForExpression(
				cdp,
				`[...document.querySelectorAll('.undetermined-avatar')].every((b) => getComputedStyle(b).opacity === '1')`
			);

			await cdp.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 0, y: 0 });
			await waitForExpression(
				cdp,
				`[...document.querySelectorAll('.undetermined-avatar')].every((b) => getComputedStyle(b).opacity === '0')`
			);

			// Re-hover so the avatars are clickable for the activation checks below.
			await cdp.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rowBox.x, y: rowBox.y });
			await waitForExpression(
				cdp,
				`[...document.querySelectorAll('.undetermined-avatar')].every((b) => getComputedStyle(b).opacity === '1')`
			);

			// === Activate: left avatar opens the card, anchored near the left ====

			await clickUntilEffect(
				cdp,
				'.undetermined-rail-left .undetermined-avatar',
				`!!document.querySelector('.undetermined-card')`
			);

			const cardAfterLeft = await cdp.evaluate(`
				(() => {
					const card = document.querySelector('.undetermined-card');
					const title = [...card.querySelectorAll('p')][0]?.textContent.trim();
					const paragraphs = [...card.querySelectorAll('p')].slice(1).map((p) => p.textContent.trim());
					const popoverCard = document.querySelector('.popover-card');
					const cardRect = card.getBoundingClientRect();
					const leftAvatar = document.querySelector('.undetermined-rail-left .undetermined-avatar');
					const rightAvatar = document.querySelector('.undetermined-rail-right .undetermined-avatar');
					const leftAvatarRect = leftAvatar.getBoundingClientRect();
					const rightAvatarRect = rightAvatar.getBoundingClientRect();
					const cardCentre = cardRect.left + cardRect.width / 2;
					return {
						title,
						paragraphs,
						hasPopoverCard: !!popoverCard,
						distToLeft: Math.abs(cardCentre - (leftAvatarRect.left + leftAvatarRect.width / 2)),
						distToRight: Math.abs(cardCentre - (rightAvatarRect.left + rightAvatarRect.width / 2)),
					};
				})()
			`);
			assert.equal(cardAfterLeft.title, 'Undetermined speaker');
			assert.deepEqual(cardAfterLeft.paragraphs, [
				CARD_PARAGRAPH_1_ORDINARY,
				CARD_PARAGRAPH_2,
				CARD_PARAGRAPH_3,
			]);
			assert.equal(cardAfterLeft.hasPopoverCard, false, 'the bio card must not render alongside the explanation card');
			assert.ok(
				cardAfterLeft.distToLeft < cardAfterLeft.distToRight,
				'card should be nearer the left avatar after activating it'
			);

			// === Escape dismisses, right avatar reopens nearer the right ==========

			await cdp.call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape' });
			await waitForExpression(cdp, `!document.querySelector('.undetermined-card')`);

			await cdp.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rowBox.x, y: rowBox.y });
			await waitForExpression(
				cdp,
				`[...document.querySelectorAll('.undetermined-avatar')].every((b) => getComputedStyle(b).opacity === '1')`
			);
			await clickUntilEffect(
				cdp,
				'.undetermined-rail-right .undetermined-avatar',
				`!!document.querySelector('.undetermined-card')`
			);
			const cardAfterRight = await cdp.evaluate(`
				(() => {
					const card = document.querySelector('.undetermined-card');
					const cardRect = card.getBoundingClientRect();
					const leftAvatar = document.querySelector('.undetermined-rail-left .undetermined-avatar');
					const rightAvatar = document.querySelector('.undetermined-rail-right .undetermined-avatar');
					const leftAvatarRect = leftAvatar.getBoundingClientRect();
					const rightAvatarRect = rightAvatar.getBoundingClientRect();
					const cardCentre = cardRect.left + cardRect.width / 2;
					return {
						distToLeft: Math.abs(cardCentre - (leftAvatarRect.left + leftAvatarRect.width / 2)),
						distToRight: Math.abs(cardCentre - (rightAvatarRect.left + rightAvatarRect.width / 2)),
					};
				})()
			`);
			assert.ok(
				cardAfterRight.distToRight < cardAfterRight.distToLeft,
				'card should be nearer the right avatar after activating it'
			);
			await cdp.call('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Escape', code: 'Escape' });
			await waitForExpression(cdp, `!document.querySelector('.undetermined-card')`);

			// === Bubble body click opens nothing ===================================

			const bubbleCentre = await cdp.evaluate(`
				(() => {
					const bubble = document.querySelector('.undetermined-row').children[1];
					const rect = bubble.getBoundingClientRect();
					return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
				})()
			`);
			for (const type of ['mousePressed', 'mouseReleased']) {
				await cdp.call('Input.dispatchMouseEvent', {
					type,
					x: bubbleCentre.x,
					y: bubbleCentre.y,
					button: 'left',
					clickCount: 1,
				});
			}
			await new Promise((resolve) => setTimeout(resolve, 200));
			const cardAfterBubbleClick = await cdp.evaluate(`!!document.querySelector('.undetermined-card')`);
			assert.equal(cardAfterBubbleClick, false, 'clicking the bubble body must not open the card');

			// === Popover mode switching: bio card <-> explanation card ============

			await clickUntilEffect(
				cdp,
				'[aria-label="View Justice Fixture details"]',
				`!!document.querySelector('.popover-card')`
			);
			const afterBioOpen = await cdp.evaluate(`
				({ hasPopoverCard: !!document.querySelector('.popover-card'), hasUndeterminedCard: !!document.querySelector('.undetermined-card') })
			`);
			assert.equal(afterBioOpen.hasPopoverCard, true);
			assert.equal(afterBioOpen.hasUndeterminedCard, false);

			await cdp.call('Input.dispatchMouseEvent', { type: 'mouseMoved', x: rowBox.x, y: rowBox.y });
			await waitForExpression(
				cdp,
				`[...document.querySelectorAll('.undetermined-avatar')].every((b) => getComputedStyle(b).opacity === '1')`
			);
			await clickUntilEffect(
				cdp,
				'.undetermined-rail-left .undetermined-avatar',
				`!!document.querySelector('.undetermined-card') && !document.querySelector('.popover-card')`
			);
			const afterUndeterminedReopen = await cdp.evaluate(`
				({ hasPopoverCard: !!document.querySelector('.popover-card'), hasUndeterminedCard: !!document.querySelector('.undetermined-card') })
			`);
			assert.equal(afterUndeterminedReopen.hasPopoverCard, false);
			assert.equal(afterUndeterminedReopen.hasUndeterminedCard, true);
		} finally {
			await harness?.close();
		}
	}
);
