/**
 * Phase 51 Plan 51-08 — first real-browser coverage of the public
 * arguments listing (D-14/D-15/D-16). Modeled directly on
 * tenure-public-title.browser.test.mjs's harness (spawn vite, spawn a
 * real browser over CDP, drive it against a mock FASTAPI backend).
 *
 * Six distinct test cases share one vite + browser session (via
 * before/after hooks) against seeded data:
 *   1. the term index renders a term row and its published-argument count
 *   2. the term index's singular and plural count forms are both correct
 *   3. a click from a term row navigates through to /arguments/term/{year}
 *   4. a click from an argument row navigates through to /arguments/{slug}
 *   5. the term-scoped empty state renders for a real-but-empty term
 *   6. an out-of-range year 404s
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { after, before, describe, test } from 'node:test';
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
			returnByValue: true
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

const TERM_2019_ARGUMENT_COUNT = 3;
const TERM_2018_ARGUMENT_COUNT = 1;
const ARGUMENT_SLUG = 'fixture-v-example';

// A case name at the length real consolidated cases reach. Synthetic, but sized
// from the corpus: the longest real title is 194 characters and the longest
// published one is 164, while the D-04 measurement pass only ever reached 96.
// The fixture and every assertion below read this same constant, so the test
// cannot silently drift from the data it is asserting against.
const LONG_CASE_NAME =
  'Fixture Amalgamated Association of Street, Electric Railway and Motor Coach ' +
  'Employees of America, Division 1287 v. Second Fixture Holding Company of the ' +
  'Eastern District';
const LONG_CASE_SLUG = 'fixture-amalgamated-v-second-holding';
const LONG_CASE_DOCKET = '24-1287';
const PHONE = { width: 375, height: 812 };

function termsPayload() {
	return {
		terms: [
			{ term_year: 2019, argument_count: TERM_2019_ARGUMENT_COUNT },
			{ term_year: 2018, argument_count: TERM_2018_ARGUMENT_COUNT }
		]
	};
}

function termArgumentsPayload(termYear) {
	if (termYear === 2019) {
		return {
			term_year: 2019,
			arguments: [
				{
					argument_id: 1,
					slug: ARGUMENT_SLUG,
					case_name: 'Fixture v. Example',
					docket_number: '24-100',
					term_year: 2019,
					argued_date: '2019-10-01',
					question_number: 1
				},
				{
					argument_id: 2,
					slug: 'fixture-v-second',
					case_name: 'Fixture v. Second',
					docket_number: '24-200',
					term_year: 2019,
					argued_date: '2019-11-05',
					question_number: 1
				},
				{
					argument_id: 4,
					slug: LONG_CASE_SLUG,
					case_name: LONG_CASE_NAME,
					docket_number: LONG_CASE_DOCKET,
					term_year: 2019,
					argued_date: '2019-11-06',
					question_number: 1
				}
			]
		};
	}
	if (termYear === 2018) {
		return {
			term_year: 2018,
			arguments: [
				{
					argument_id: 3,
					slug: 'fixture-v-third',
					case_name: 'Fixture v. Third',
					docket_number: '23-999',
					term_year: 2018,
					argued_date: '2018-12-01',
					question_number: 1
				}
			]
		};
	}
	// A real, in-range term with nothing published.
	return { term_year: termYear, arguments: [] };
}

function argumentUtterancesPayload() {
	return {
		utterances: [
			{
				sequence: 0,
				argument_id: 1,
				person_id: null,
				side: 'BENCH',
				speaker_name: null,
				raw_speaker_label: 'THE CHIEF JUSTICE',
				speaker_role: null,
				text: 'Please proceed, counsel.',
				is_stage_direction: false,
				section_hint: null
			}
		],
		argument: {
			argument_id: 1,
			case_name: 'Fixture v. Example',
			docket_number: '24-100',
			argued_date: '2019-10-01',
			question_number: 1,
			oyez_transcript_id: null
		}
	};
}

describe('public arguments listing (term index + term detail)', { timeout: 120_000 }, () => {
	let mockApi;
	let vite;
	let browser;
	let cdp;
	let profile;
	let appPort;

	before(async () => {
		mockApi = createServer((request, response) => {
			response.setHeader('content-type', 'application/json');
			const url = new URL(request.url, 'http://mock-fastapi');

			if (request.method === 'GET' && url.pathname === '/arguments/terms') {
				response.end(JSON.stringify(termsPayload()));
				return;
			}

			const termMatch = url.pathname.match(/^\/arguments\/term\/(.+)$/);
			if (request.method === 'GET' && termMatch) {
				const rawYear = termMatch[1];
				const yearNum = Number(rawYear);
				const isValidYear = /^\d+$/.test(rawYear) && yearNum >= 1789 && yearNum <= 2200;
				if (!isValidYear) {
					response.statusCode = 422;
					response.end(JSON.stringify({ detail: 'bad year' }));
					return;
				}
				response.end(JSON.stringify(termArgumentsPayload(yearNum)));
				return;
			}

			if (request.method === 'GET' && url.pathname === `/arguments/by-slug/${ARGUMENT_SLUG}/utterances`) {
				response.end(JSON.stringify(argumentUtterancesPayload()));
				return;
			}

			if (request.method === 'GET' && url.pathname === `/arguments/by-slug/${ARGUMENT_SLUG}/speakers`) {
				response.end(JSON.stringify([]));
				return;
			}

			response.statusCode = 404;
			response.end(JSON.stringify({ detail: 'not found' }));
		});

		const apiPort = await listen(mockApi);
		appPort = await freePort();
		const debugPort = await freePort();
		profile = await mkdtemp(path.join(tmpdir(), 'scotus-arguments-listing-browser-'));
		const executable = browserExecutable();
		assert.ok(executable, NO_BROWSER_MESSAGE);

		vite = spawn(
			process.execPath,
			[
				VITE_BIN,
				'--host',
				'127.0.0.1',
				'--port',
				String(appPort),
				'--strictPort'
			],
			{
				cwd: APP_DIR,
				env: {
					...process.env,
					ADMIN_USERNAME: 'phase51-admin',
					ADMIN_PASSWORD: 'phase51-password',
					ADMIN_TOKEN: 'phase51-test-token',
					SESSION_SECRET: 'phase51-test-session-secret-at-least-32-characters',
					FASTAPI_BASE_URL: `http://127.0.0.1:${apiPort}`
				},
				stdio: 'ignore',
				windowsHide: true
			}
		);
		await waitFor(`http://127.0.0.1:${appPort}/arguments`);

		browser = spawn(
			executable,
			[
				'--headless=new',
				'--disable-gpu',
				'--no-first-run',
				'--no-default-browser-check',
				'--remote-allow-origins=*',
				`--remote-debugging-port=${debugPort}`,
				`--user-data-dir=${profile}`,
				`http://127.0.0.1:${appPort}/arguments`
			],
			{ stdio: 'ignore', windowsHide: true }
		);
		const targetsResponse = await waitFor(
			`http://127.0.0.1:${debugPort}/json/list`,
			async (response) => (await response.clone().json()).some((target) => target.type === 'page')
		);
		const targets = await targetsResponse.json();
		cdp = new CdpClient(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
		await cdp.open();
		await cdp.call('Runtime.enable');
		await waitForExpression(cdp, `document.querySelector('h1')?.textContent === 'Arguments'`);
	});

	after(async () => {
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi?.closeAllConnections();
		if (mockApi) await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
	});

	test('1. term index renders a term row and its published-argument count', async () => {
		const indexText = await cdp.evaluate('document.body.innerText');
		assert.match(indexText, /October Term 2019/);
		assert.match(indexText, new RegExp(`${TERM_2019_ARGUMENT_COUNT} arguments`));
	});

	test('2. term index renders singular and plural count forms correctly', async () => {
		const indexText = await cdp.evaluate('document.body.innerText');
		assert.match(indexText, /October Term 2018/);
		assert.match(indexText, /1 argument\b/);
		assert.doesNotMatch(indexText, /1 arguments\b/);
	});

	test('3. clicking a term row navigates through to /arguments/term/{year}', async () => {
		await cdp.evaluate(`document.querySelector('a[href="/arguments/term/2019"]')?.click()`);
		await waitForExpression(cdp, `document.querySelector('h1')?.textContent === 'October Term 2019'`);
		assert.equal(
			await cdp.evaluate('location.pathname'),
			'/arguments/term/2019',
			'clicking a term row must navigate to /arguments/term/{year}'
		);
		const termDetailText = await cdp.evaluate('document.body.innerText');
		assert.match(termDetailText, /Fixture v\. Example/);
		assert.match(termDetailText, /Fixture v\. Second/);
		assert.match(termDetailText, /24-100/);
		assert.match(termDetailText, /24-200/);
	});

	test('4. clicking an argument row navigates through to /arguments/{slug}', async () => {
		await cdp.evaluate(`document.querySelector('a[href="/arguments/${ARGUMENT_SLUG}"]')?.click()`);
		await waitForExpression(cdp, `document.querySelector('h1')?.textContent === 'Fixture v. Example'`);
		assert.equal(
			await cdp.evaluate('location.pathname'),
			`/arguments/${ARGUMENT_SLUG}`,
			'clicking an argument row must navigate to /arguments/{slug}'
		);
	});

	test('5. term-scoped empty state renders for a real-but-empty term', async () => {
		await cdp.evaluate(`(() => { location.href = '/arguments/term/1799'; })()`);
		await waitForExpression(
			cdp,
			`document.body.innerText.includes('No arguments published for October Term 1799 yet.')`
		);
	});

	test('6. an out-of-range year 404s', async () => {
		const response = await fetch(`http://127.0.0.1:${appPort}/arguments/term/99999`);
		assert.equal(response.status, 404);
	});

	// P-06 says no shipped surface may visually truncate, clip or ellipsise
	// content. Until now that was checked by eye, because no fixture carried a
	// name long enough to stress it — the operator's 51-10 walkthrough is where
	// it was first looked at, on a 164-character corpus case. This pins it.
	//
	// Asserting the rendered geometry rather than the markup is the point: a
	// source-text check would pass against a row whose name is clipped, which is
	// the failure mode the Testing Policy exists to prevent.
	test('7. a very long case name wraps intact at 375px, docket still fully visible', async () => {
		await cdp.call('Emulation.setDeviceMetricsOverride', {
			width: PHONE.width, height: PHONE.height, deviceScaleFactor: 1, mobile: true
		});
		try {
			await cdp.evaluate(`(() => { location.href = '/arguments/term/2019'; })()`);
			await waitForExpression(
				cdp,
				`location.pathname === '/arguments/term/2019' && !!document.querySelector('a[href="/arguments/${LONG_CASE_SLUG}"]')`
			);

			const seen = await cdp.evaluate(`(() => {
				const row = document.querySelector('a[href="/arguments/${LONG_CASE_SLUG}"]');
				const inner = row.innerText;
				// The element actually holding the name: the deepest one whose text
				// is the whole name, so we measure the name's own box, not the row's.
				const nameEl = [...row.querySelectorAll('*')]
					.filter((el) => el.textContent.trim() === ${JSON.stringify(LONG_CASE_NAME)})
					.pop() || row;
				const docketText = 'No. ' + ${JSON.stringify(LONG_CASE_DOCKET)};
				const docketEl = [...row.querySelectorAll('*')]
					.filter((el) => el.textContent.includes(docketText))
					.pop();
				const box = (el) => { const r = el.getBoundingClientRect();
					return { l: r.left, r: r.right, w: r.width, h: r.height }; };
				const rowRect = box(row);
				return {
					fullNamePresent: inner.includes(${JSON.stringify(LONG_CASE_NAME)}),
					docketPresent: inner.includes(docketText),
					nameOverflows: nameEl.scrollWidth > nameEl.clientWidth + 1,
					nameEllipsised: getComputedStyle(nameEl).textOverflow === 'ellipsis',
					nameWrapped: box(nameEl).h > parseFloat(getComputedStyle(nameEl).lineHeight || '0') * 1.5,
					docketWithinRow: docketEl
						? box(docketEl).r <= rowRect.r + 1 && box(docketEl).l >= rowRect.l - 1
						: false,
					docketClipped: docketEl ? docketEl.scrollWidth > docketEl.clientWidth + 1 : true,
					bodyScrollsSideways: document.documentElement.scrollWidth > window.innerWidth + 1
				};
			})()`);

			// The name survives in full — not shortened, not ellipsised, not clipped.
			assert.equal(seen.fullNamePresent, true, 'the whole case name should be in the rendered text');
			assert.equal(seen.nameEllipsised, false, 'the case name must not be ellipsised (P-06)');
			assert.equal(seen.nameOverflows, false, 'the case name must not overflow its own box (P-06)');
			assert.equal(seen.nameWrapped, true, 'a 164-character name at 375px should wrap to several lines');

			// The docket is the value D-04 found being starved by a long neighbour.
			assert.equal(seen.docketPresent, true, 'the docket number should be rendered');
			assert.equal(seen.docketWithinRow, true, 'the docket number must stay inside its row');
			assert.equal(seen.docketClipped, false, 'the docket number must not be clipped');

			// A long name must not push the page itself sideways.
			assert.equal(seen.bodyScrollsSideways, false, 'the page body must not scroll horizontally');
		} finally {
			await cdp.call('Emulation.clearDeviceMetricsOverride');
		}
	});
});
