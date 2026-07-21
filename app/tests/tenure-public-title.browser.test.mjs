/**
 * Phase 37 Plan 04 — public read-only tenure title regression (D-15/D-17).
 *
 * Exercises the real public argument view (/cases/[slug]/arguments/[id]) end to
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

function browserExecutable() {
	const candidates = process.platform === 'win32'
		? [
			'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
			'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
			'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
			'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
		]
		: ['/usr/bin/microsoft-edge', '/usr/bin/google-chrome', '/usr/bin/chromium'];
	return candidates.find((candidate) => existsSync(candidate));
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

test('public argument view renders formal Chief/Associate Justice titles, never raw office or generic fallback', { timeout: 60_000 }, async () => {
	const mockApi = createServer((request, response) => {
		response.setHeader('content-type', 'application/json');
		if (request.method === 'GET' && request.url === `/arguments/${ARGUMENT_ID}/utterances`) {
			response.end(JSON.stringify(argumentPayload()));
			return;
		}
		if (request.method === 'GET' && request.url === `/arguments/${ARGUMENT_ID}/speakers`) {
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
		assert.ok(executable, 'Microsoft Edge or Google Chrome must be installed for this fail-closed test');

		vite = spawn(process.execPath, [
			path.resolve('app/node_modules/vite/bin/vite.js'),
			'--host', '127.0.0.1', '--port', String(appPort), '--strictPort',
		], {
			cwd: path.resolve('app'),
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
		const casePath = `/cases/fixture-v-example/arguments/${ARGUMENT_ID}`;
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
		// canonical office string before any popover has been opened.
		const preOpen = await cdp.evaluate(`document.body.textContent`);
		assert.doesNotMatch(preOpen, /\bchief\b/);
		assert.doesNotMatch(preOpen, /\bassociate\b/);

		async function openPopoverAndReadTenureLine(ariaLabel) {
			await cdp.evaluate(`(() => {
				const button = [...document.querySelectorAll('button[aria-label]')]
					.find((el) => el.getAttribute('aria-label') === ${JSON.stringify(ariaLabel)});
				button.click();
			})()`);
			await waitForExpression(cdp, `!!document.querySelector('.popover-card')`);
			return cdp.evaluate(`(() => {
				const paragraphs = [...document.querySelectorAll('.popover-card p')];
				return paragraphs.map((p) => p.textContent.trim());
			})()`);
		}

		async function closePopover() {
			await cdp.evaluate(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))`);
			await waitForExpression(cdp, `!document.querySelector('.popover-card')`);
		}

		// Chief fixture — formal title precedes the unchanged open-ended range.
		const chiefParagraphs = await openPopoverAndReadTenureLine('View Fixture Chief details');
		assert.deepEqual(chiefParagraphs, ['Fixture Chief', 'Chief Justice — 2005–present']);
		assert.doesNotMatch(chiefParagraphs[1], /\bchief\b/, 'raw canonical office value must not render');
		assert.doesNotMatch(chiefParagraphs[1], /^Justice\b/, 'must not fall back to the generic "Justice" title');
		await closePopover();

		// Associate fixture — formal title precedes the unchanged closed range.
		const associateParagraphs = await openPopoverAndReadTenureLine('View Fixture Associate details');
		assert.deepEqual(associateParagraphs, ['Fixture Associate', 'Associate Justice — 1994–2005']);
		assert.doesNotMatch(associateParagraphs[1], /\bassociate\b/, 'raw canonical office value must not render');
		assert.doesNotMatch(associateParagraphs[1], /^Justice\b/, 'must not fall back to the generic "Justice" title');
	} finally {
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi.closeAllConnections();
		await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
	}
});
