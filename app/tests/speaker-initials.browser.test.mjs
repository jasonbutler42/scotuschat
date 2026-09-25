/**
 * Phase 52 Plan 02 (D-12/D-13, JUSTICE-06) — avatar initials regression.
 *
 * Exercises the real public argument view (/arguments/[slug]) end to end
 * against a mock FASTAPI backend, proving the server-computed initials field
 * is what renders — not a client-side name-string split. Copies the harness
 * shape of tenure-public-title.browser.test.mjs verbatim (free-port
 * allocation, mock FASTAPI server, Vite spawn, CDP connection).
 *
 * Covers:
 *   1. Transcript avatar for "John Marshall Harlan, II" renders "JH" (the
 *      JI -> JH fix), not derived client-side from the name string.
 *   2. Opening that speaker's popover shows "JH" on the fallback avatar
 *      (photo absent).
 *   3. "Oliver W. Holmes, Jr." renders "OH" in both places — the trailing
 *      suffix token is never mistaken for a surname.
 *   4. An utterance with no resolved person and no server-computed initials
 *      renders the existing "?" glyph — never a blank circle, never a
 *      fabricated letter.
 *   5. Reassigning the popover's `speaker` prop to a second person updates
 *      the initials shown — the value does not freeze on the first speaker
 *      picked (the $derived, not const, prop-capture discipline).
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';
import { browserExecutable, NO_BROWSER_MESSAGE } from './helpers/browser-executable.mjs';
import { APP_DIR, VITE_BIN } from './helpers/paths.mjs';

function listen(server) {
	return new Promise((resolve, reject) => {
		server.once('error', reject);
		server.listen(0, '127.0.0.1', () => resolve(server.address().port));
	});
}

async function freePort() {
	const server = createServer();
	const port = await listen(server);
	await new Promise((resolve) => server.close(resolve));
	return port;
}

async function waitFor(url, predicate = (response) => response.ok, timeoutMs = 20_000) {
	const deadline = Date.now() + timeoutMs;
	let lastError;
	while (Date.now() < deadline) {
		try {
			const response = await fetch(url);
			if (await predicate(response)) return response;
		} catch (error) {
			lastError = error;
		}
		await delay(100);
	}
	throw new Error(`Timed out waiting for ${url}: ${lastError ?? 'condition not met'}`);
}

async function terminateTree(child) {
	if (!child || child.exitCode !== null) return;
	const exited = new Promise((resolve) => child.once('exit', resolve));
	child.kill('SIGTERM');
	await Promise.race([exited, delay(5_000)]);
}

class CdpClient {
	constructor(url) {
		this.socket = new WebSocket(url);
		this.nextId = 1;
		this.pending = new Map();
	}

	async open() {
		await new Promise((resolve, reject) => {
			this.socket.addEventListener('open', resolve, { once: true });
			this.socket.addEventListener('error', reject, { once: true });
		});
		this.socket.addEventListener('message', (event) => {
			const message = JSON.parse(event.data);
			if (!message.id) return;
			const waiter = this.pending.get(message.id);
			if (!waiter) return;
			this.pending.delete(message.id);
			if (message.error) waiter.reject(new Error(message.error.message));
			else waiter.resolve(message.result);
		});
	}

	call(method, params = {}) {
		const id = this.nextId++;
		return new Promise((resolve, reject) => {
			this.pending.set(id, { resolve, reject });
			this.socket.send(JSON.stringify({ id, method, params }));
		});
	}

	async evaluate(expression) {
		const result = await this.call('Runtime.evaluate', {
			expression,
			awaitPromise: true,
			returnByValue: true,
		});
		if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
		return result.result.value;
	}

	close() {
		this.socket.close();
	}
}

async function waitForExpression(cdp, expression, timeoutMs = 15_000) {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		if (await cdp.evaluate(expression)) return true;
		await delay(50);
	}
	throw new Error(`Timed out waiting for browser expression: ${expression}`);
}

// Fixture data ---------------------------------------------------------------

const ARGUMENT_ID = 52;
const ARGUMENT_SLUG = 'fixture-v-initials';

const HARLAN_NAME = 'John Marshall Harlan, II';
const HOLMES_NAME = 'Oliver W. Holmes, Jr.';

function argumentPayload() {
	return {
		utterances: [
			{
				sequence: 0,
				argument_id: ARGUMENT_ID,
				person_id: 1,
				side: 'BENCH',
				speaker_name: HARLAN_NAME,
				raw_speaker_label: 'JUSTICE HARLAN',
				speaker_role: null,
				speaker_initials: 'JH',
				text: 'Please proceed, counsel.',
				is_stage_direction: false,
				section_hint: null,
			},
			{
				sequence: 1,
				argument_id: ARGUMENT_ID,
				person_id: 2,
				side: 'BENCH',
				speaker_name: HOLMES_NAME,
				raw_speaker_label: 'JUSTICE HOLMES',
				speaker_role: null,
				speaker_initials: 'OH',
				text: 'Thank you, counsel.',
				is_stage_direction: false,
				section_hint: null,
			},
			// Neither a person_id nor a server-computed speaker_initials value
			// — the "?" path (JUSTICE-06 / empty). raw_speaker_label is also
			// blank so the roster and the transcript aria-label both degrade
			// to an empty display name, exactly as an unresolved speaker
			// renders today.
			{
				sequence: 2,
				argument_id: ARGUMENT_ID,
				person_id: null,
				side: 'UNKNOWN',
				speaker_name: null,
				raw_speaker_label: null,
				speaker_role: null,
				speaker_initials: null,
				text: '[inaudible]',
				is_stage_direction: false,
				section_hint: null,
			},
		],
		argument: {
			argument_id: ARGUMENT_ID,
			case_name: 'Fixture v. Initials',
			docket_number: '24-200',
			argued_date: '2024-10-02',
			question_number: 1,
			oyez_transcript_id: null,
		},
	};
}

function speakersPayload() {
	return [
		{
			person_id: 1,
			full_name: HARLAN_NAME,
			role_name: null,
			photo_url: null,
			initials: 'JH',
			tenure: [{ office: 'associate', start_date: '1955-03-28', end_date: '1971-09-23' }],
			side: 'BENCH',
		},
		{
			person_id: 2,
			full_name: HOLMES_NAME,
			role_name: null,
			photo_url: null,
			initials: 'OH',
			tenure: [{ office: 'associate', start_date: '1902-12-08', end_date: '1932-01-12' }],
			side: 'BENCH',
		},
	];
}

test('avatar initials render the server-computed value, including the JI -> JH fix, in a real browser', { timeout: 120_000 }, async () => {
	const mockApi = createServer((request, response) => {
		response.setHeader('content-type', 'application/json');
		if (request.method === 'GET' && request.url === `/arguments/by-slug/${ARGUMENT_SLUG}/utterances`) {
			response.end(JSON.stringify(argumentPayload()));
			return;
		}
		if (request.method === 'GET' && request.url === `/arguments/by-slug/${ARGUMENT_SLUG}/speakers`) {
			response.end(JSON.stringify(speakersPayload()));
			return;
		}
		response.statusCode = 404;
		response.end(JSON.stringify({ detail: 'not found' }));
	});

	let vite;
	let browser;
	let cdp;
	let profile;
	try {
		const apiPort = await listen(mockApi);
		const appPort = await freePort();
		const debugPort = await freePort();
		profile = await mkdtemp(path.join(tmpdir(), 'scotus-speaker-initials-browser-'));
		const executable = browserExecutable();
		assert.ok(executable, NO_BROWSER_MESSAGE);

		vite = spawn(process.execPath, [
			VITE_BIN,
			'--host', '127.0.0.1', '--port', String(appPort), '--strictPort',
		], {
			cwd: APP_DIR,
			env: {
				...process.env,
				ADMIN_USERNAME: 'phase52-admin',
				ADMIN_PASSWORD: 'phase52-password',
				ADMIN_TOKEN: 'phase52-test-token',
				SESSION_SECRET: 'phase52-test-session-secret-at-least-32-characters',
				FASTAPI_BASE_URL: `http://127.0.0.1:${apiPort}`,
			},
			stdio: 'ignore',
			windowsHide: true,
		});
		const casePath = `/arguments/${ARGUMENT_SLUG}`;
		await waitFor(`http://127.0.0.1:${appPort}${casePath}`);

		browser = spawn(executable, [
			'--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
			'--remote-allow-origins=*',
			`--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
			`http://127.0.0.1:${appPort}${casePath}`,
		], { stdio: 'ignore', windowsHide: true });
		const targetsResponse = await waitFor(
			`http://127.0.0.1:${debugPort}/json/list`,
			async (response) => (await response.clone().json()).some((target) => target.type === 'page'),
		);
		const targets = await targetsResponse.json();
		cdp = new CdpClient(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
		await cdp.open();
		await cdp.call('Runtime.enable');
		await waitForExpression(cdp, `document.querySelector('h1')?.textContent === 'Fixture v. Initials'`);

		// --- 1/3/4: transcript avatars, in render order (one run per utterance,
		// since each has a distinct raw_speaker_label) -----------------------
		// SSR markup (including the h1 waited on above) is present before
		// hydration attaches listeners; retry the read until all three runs
		// have mounted instead of guessing a fixed delay.
		const transcriptInitials = await (async () => {
			const deadline = Date.now() + 15_000;
			let values;
			while (Date.now() < deadline) {
				values = await cdp.evaluate(
					`[...document.querySelectorAll('[role="article"] .speaker-fill')].map((el) => el.textContent.trim())`
				);
				if (values.length === 3) return values;
				await delay(150);
			}
			throw new Error(`Timed out waiting for 3 transcript avatars, saw: ${JSON.stringify(values)}`);
		})();
		assert.deepEqual(transcriptInitials, ['JH', 'OH', '?']);

		// --- 2/5: popover reads the server-computed value, and updates when
		// the speaker prop is reassigned to a second person ------------------
		async function openPopoverAndReadInitials(ariaLabel) {
			const clickExpression = `(() => {
				const button = [...document.querySelectorAll('[role="article"] button[aria-label]')]
					.find((el) => el.getAttribute('aria-label') === ${JSON.stringify(ariaLabel)});
				button?.click();
				return !!button;
			})()`;
			const deadline = Date.now() + 15_000;
			let opened = false;
			while (Date.now() < deadline) {
				await cdp.evaluate(clickExpression);
				if (await cdp.evaluate(`!!document.querySelector('.popover-card')`)) {
					opened = true;
					break;
				}
				await delay(150);
			}
			assert.ok(opened, `popover never opened for ${ariaLabel} after retried clicks`);
			return cdp.evaluate(`document.querySelector('.popover-card .speaker-fill')?.textContent.trim() ?? null`);
		}

		async function closePopover() {
			await cdp.evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
			await waitForExpression(cdp, `!document.querySelector('.popover-card')`);
		}

		const harlanInitials = await openPopoverAndReadInitials(`View ${HARLAN_NAME} details`);
		assert.equal(harlanInitials, 'JH');
		await closePopover();

		// Reassigning `speaker` to a second person must update the rendered
		// initials — proves the $derived (not const) discipline: a stale
		// const would still read "JH" here.
		const holmesInitials = await openPopoverAndReadInitials(`View ${HOLMES_NAME} details`);
		assert.equal(holmesInitials, 'OH');
		await closePopover();
	} finally {
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi.closeAllConnections();
		await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
	}
});
