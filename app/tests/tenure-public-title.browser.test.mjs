/**
 * Phase 37 Plan 04 — public read-only tenure title regression (D-15/D-17).
 * Retargeted to /arguments/{slug} (Phase 51 plan 51-02, D-10/D-12).
 *
 * Exercises the real public argument view (/arguments/[slug]) end to
 * end against a mock FASTAPI backend: clicks a bench speaker's avatar to open
 * SpeakerPopover.svelte and asserts the rendered tenure line is the formal
 * "Chief Justice"/"Associate Justice" title immediately preceding the unchanged
 * start–end year range, for both a chief and an associate fixture — and that
 * neither the raw canonical office string ("chief"/"associate") nor the old
 * generic "Justice" fallback ever renders.
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync } from 'node:fs';
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

const ARGUMENT_ID = 7;
const ARGUMENT_SLUG = 'fixture-v-example';

function argumentPayload() {
	return {
		utterances: [
			{
				sequence: 0,
				argument_id: ARGUMENT_ID,
				person_id: 1,
				side: 'BENCH',
				speaker_name: 'Fixture Chief',
				raw_speaker_label: 'FIXTURE CHIEF',
				speaker_role: null,
				text: 'Please proceed, counsel.',
				is_stage_direction: false,
				section_hint: null,
			},
			{
				sequence: 1,
				argument_id: ARGUMENT_ID,
				person_id: 2,
				side: 'BENCH',
				speaker_name: 'Fixture Associate',
				raw_speaker_label: 'FIXTURE ASSOCIATE',
				speaker_role: null,
				text: 'Thank you, counsel.',
				is_stage_direction: false,
				section_hint: null,
			},
		],
		argument: {
			argument_id: ARGUMENT_ID,
			case_name: 'Fixture v. Example',
			docket_number: '24-100',
			argued_date: '2024-10-01',
			question_number: 1,
			oyez_transcript_id: null,
		},
	};
}

function speakersPayload() {
	return [
		{
			person_id: 1,
			full_name: 'Fixture Chief',
			role_name: null,
			photo_url: null,
			appointing_president: null,
			// office is the canonical storage value; the popover projects it to
			// the formal title (D-15) — this fixture never carries a formal
			// title itself, so a passing test proves the render layer did it.
			tenure: [{ office: 'chief', start_date: '2005-09-29', end_date: null }],
			side: 'BENCH',
		},
		{
			person_id: 2,
			full_name: 'Fixture Associate',
			role_name: null,
			photo_url: null,
			appointing_president: null,
			tenure: [{ office: 'associate', start_date: '1994-08-03', end_date: '2005-09-01' }],
			side: 'BENCH',
		},
	];
}

test('public argument view renders formal Chief/Associate Justice titles, never raw office or generic fallback', { timeout: 120_000 }, async () => {
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
		profile = await mkdtemp(path.join(tmpdir(), 'scotus-tenure-title-browser-'));
		const executable = browserExecutable();
		assert.ok(executable, NO_BROWSER_MESSAGE);

		vite = spawn(process.execPath, [
			VITE_BIN,
			'--host', '127.0.0.1', '--port', String(appPort), '--strictPort',
		], {
			cwd: APP_DIR,
			env: {
				...process.env,
				ADMIN_USERNAME: 'phase37-admin',
				ADMIN_PASSWORD: 'phase37-password',
				ADMIN_TOKEN: 'phase37-test-token',
				SESSION_SECRET: 'phase37-test-session-secret-at-least-32-characters',
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
		await waitForExpression(cdp, `document.querySelector('h1')?.textContent === 'Fixture v. Example'`);

		// Neither avatar's aria-label nor page text ever exposes the raw
		// canonical office string before any popover has been opened. innerText
		// (not textContent) so SvelteKit's inline hydration <script> JSON —
		// which legitimately carries the raw "chief"/"associate" values for
		// client-side reactivity — isn't mistaken for rendered page text.
		const preOpen = await cdp.evaluate(`document.body.innerText`);
		assert.doesNotMatch(preOpen, /\bchief\b/);
		assert.doesNotMatch(preOpen, /\bassociate\b/);

		async function openPopoverAndReadTenureLine(ariaLabel) {
			// SSR markup (including the h1 waited on above) is present before Svelte's
			// client-side hydration attaches event listeners, and a cold vite dev
			// server's first module transform can take longer than any fixed pause
			// would predict. Retry the click until the popover actually appears
			// (bounded below) instead of guessing a delay.
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
			// The name renders as the popover's one <p>; the tenure office title
			// and its date range render as two side-by-side <span> elements in a
			// flex row (SpeakerPopover.svelte's tenure-list block), not as a
			// single combined <p> — querying `.popover-card p` alone (as this
			// test originally did) silently misses the tenure line entirely,
			// stale since whichever pass split the tenure row into a two-column
			// flex layout. This fixture has no role pill, no birth/death line,
			// and no appointed_by/reason_left second row, so exactly one <p> and
			// exactly two <span>s render — deterministic, not a loosened match.
			return cdp.evaluate(`(() => {
				const name = document.querySelector('.popover-card p')?.textContent.trim() ?? null;
				const spans = [...document.querySelectorAll('.popover-card span')].map((s) => s.textContent.trim());
				return { name, officeTitle: spans[0] ?? null, tenureRange: spans[1] ?? null };
			})()`);
		}

		async function closePopover() {
			await cdp.evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
			await waitForExpression(cdp, `!document.querySelector('.popover-card')`);
		}

		// Chief fixture — formal title, unchanged open-ended range, in the two
		// dedicated tenure-row cells (not concatenated into one string).
		const chief = await openPopoverAndReadTenureLine('View Fixture Chief details');
		// Month + year with a spaced en dash, not the year-only form this test
		// was written against in 37-04. Plan 39-08 deliberately changed it to
		// follow the mockup (see SpeakerPopover.formatMonthYear's comment: the
		// UI-SPEC copywriting row had frozen year-only, and the plan overrode
		// it because mockup fidelity was the gap being closed). That commit
		// should have retired this expectation with the behaviour it pinned;
		// it could not, because no browser was ever found to run the test.
		assert.deepEqual(chief, { name: 'Fixture Chief', officeTitle: 'Chief Justice', tenureRange: 'Sep 2005 – present' });
		assert.doesNotMatch(chief.officeTitle, /\bchief\b/, 'raw canonical office value must not render');
		assert.doesNotMatch(chief.officeTitle, /^Justice\b/, 'must not fall back to the generic "Justice" title');
		await closePopover();

		// Associate fixture — formal title, unchanged closed range.
		const associate = await openPopoverAndReadTenureLine('View Fixture Associate details');
		assert.deepEqual(associate, { name: 'Fixture Associate', officeTitle: 'Associate Justice', tenureRange: 'Aug 1994 – Sep 2005' });
		assert.doesNotMatch(associate.officeTitle, /\bassociate\b/, 'raw canonical office value must not render');
		assert.doesNotMatch(associate.officeTitle, /^Justice\b/, 'must not fall back to the generic "Justice" title');
	} finally {
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi.closeAllConnections();
		await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
	}
});
