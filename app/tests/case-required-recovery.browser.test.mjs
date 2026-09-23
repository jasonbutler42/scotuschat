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

const TEST_USER = 'phase34-admin';
const TEST_PASSWORD = 'phase34-password';

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
		if (await cdp.evaluate(expression)) return;
		await delay(50);
	}
	throw new Error(`Timed out waiting for browser expression: ${expression}`);
}

/**
 * Clears both required fields and submits, repeating until the enhanced
 * alert renders — i.e. until Svelte's oninvalid handler is actually attached.
 * See the call site for why a fixed delay cannot replace this.
 */
async function submitClearedUntilEnhanced(cdp, timeoutMs = 30_000) {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		await cdp.evaluate(`(() => {
			for (const id of ['case_name', 'docket_number']) { const input = document.getElementById(id); input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
			document.getElementById('case_name').closest('form').requestSubmit();
		})()`);
		await delay(250);
		if (await cdp.evaluate(`document.querySelectorAll('#case-form-alert span').length === 2`)) return;
	}
	throw new Error('Timed out waiting for the enhanced required-field alert to render');
}

function argumentDetail() {
	return {
		id: 7,
		argued_date: '2024-10-01',
		case_name: 'Original Case',
		docket_number: '24-1',
		resolved_at: '2024-10-01T12:00:00Z',
		published_at: null,
		status: 'draft',
		slug: 'original-case',
		consolidated_dockets: [],
		participants: [],
		tenure_gap_warnings: [],
		status_log: [],
		speakers: [],
		source_docket: '24-1',
		source_dockets: ['24-1'],
		cover_metadata: {},
		question_number: null,
	};
}

test('native required state clears before later enhanced failures', { timeout: 120_000 }, async () => {
	let responseMode = 'required';
	let patchCount = 0;
	const mockApi = createServer((request, response) => {
		response.setHeader('content-type', 'application/json');
		if (request.method === 'GET' && request.url === '/api/admin/arguments/7') {
			response.end(JSON.stringify(argumentDetail()));
			return;
		}
		if (request.method === 'PATCH' && request.url === '/api/admin/arguments/7') {
			patchCount += 1;
			if (responseMode === 'required') {
				response.statusCode = 422;
				response.end(JSON.stringify({ detail: [
					{ loc: ['body', 'case_name'], msg: 'required', type: 'value_error' },
					{ loc: ['body', 'docket_number'], msg: 'required', type: 'value_error' },
				] }));
				return;
			}
			response.statusCode = 422;
			response.end(JSON.stringify(responseMode === 'collision'
				? { detail: 'slug_collision' }
				: { detail: 'unexpected_failure' }));
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
		profile = await mkdtemp(path.join(tmpdir(), 'scotus-phase34-browser-'));
		const executable = browserExecutable();
		assert.ok(executable, NO_BROWSER_MESSAGE);

		vite = spawn(process.execPath, [
			VITE_BIN,
			'--host', '127.0.0.1', '--port', String(appPort), '--strictPort',
		], {
			cwd: APP_DIR,
			env: {
				...process.env,
				ADMIN_USERNAME: TEST_USER,
				ADMIN_PASSWORD: TEST_PASSWORD,
				ADMIN_TOKEN: 'phase34-test-token',
				SESSION_SECRET: 'phase34-test-session-secret-at-least-32-characters',
				FASTAPI_BASE_URL: `http://127.0.0.1:${apiPort}`,
			},
			stdio: 'ignore',
			windowsHide: true,
		});
		await waitFor(`http://127.0.0.1:${appPort}/admin/login`);

		browser = spawn(executable, [
			'--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
			'--remote-allow-origins=*',
			`--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
			`http://127.0.0.1:${appPort}/admin/login`,
		], { stdio: 'ignore', windowsHide: true });
		const targetsResponse = await waitFor(
			`http://127.0.0.1:${debugPort}/json/list`,
			async (response) => (await response.clone().json()).some((target) => target.type === 'page'),
		);
		const targets = await targetsResponse.json();
		cdp = new CdpClient(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
		await cdp.open();
		await cdp.call('Runtime.enable');
		await waitForExpression(cdp, `location.pathname === '/admin/login' && !!document.querySelector('input[name=username]')`);
		await cdp.evaluate(`(() => {
			const set = (name, value) => { const input = document.querySelector('[name="' + name + '"]'); input.value = value; input.dispatchEvent(new Event('input', { bubbles: true })); };
			set('username', ${JSON.stringify(TEST_USER)}); set('password', ${JSON.stringify(TEST_PASSWORD)});
			document.querySelector('form').requestSubmit();
		})()`);
		await waitForExpression(cdp, `location.pathname === '/admin'`);
		await cdp.call('Page.navigate', { url: `http://127.0.0.1:${appPort}/admin/arguments/7` });
		await waitForExpression(cdp, `location.pathname === '/admin/arguments/7' && !!document.querySelector('#case_name')`);
		// The selector is present in SSR HTML before Svelte attaches the
		// invalid/enhance handlers, so the submit below has to wait for
		// hydration. A fixed sleep cannot do that: `invalid` fires once, and if
		// it fires before the handler is attached nothing re-fires it, so the
		// enhanced alert never renders and the wait below burns its full
		// deadline against a page that is working correctly. That is exactly
		// how this test failed — for 500ms on a cold vite dev server, where
		// hydration lands well past a second.
		//
		// Re-submitting until the alert renders removes the race at any machine
		// speed. It is safe to repeat: native validation blocks the request, so
		// no PATCH is issued — `patchCount === 0` is asserted immediately below
		// and would catch it if that ever stopped being true.
		await submitClearedUntilEnhanced(cdp);
		const invalid = await cdp.evaluate(`(() => ({
			messages: [...document.querySelectorAll('#case-form-alert span')].map((node) => node.textContent.trim()),
			aria: ['case_name', 'docket_number'].map((id) => document.getElementById(id).getAttribute('aria-invalid')),
			borders: ['case_name', 'docket_number'].map((id) => getComputedStyle(document.getElementById(id)).borderColor),
			focus: document.activeElement.id,
		}))()`);
		assert.equal(patchCount, 0);
		assert.deepEqual(invalid.messages, ['Case name is required.', 'Add at least one docket.']);
		assert.deepEqual(invalid.aria, ['true', 'true']);
		assert.deepEqual(invalid.borders, ['rgb(239, 68, 68)', 'rgb(239, 68, 68)']);
		assert.equal(invalid.focus, 'case_name');

		async function submitCorrected(expectedPatchCount) {
			await cdp.evaluate(`(() => {
				const values = { case_name: 'Corrected Case', docket_number: '24-2' };
				for (const [id, value] of Object.entries(values)) { const input = document.getElementById(id); input.value = value; input.dispatchEvent(new Event('input', { bubbles: true })); }
				const form = document.getElementById('case_name').closest('form');
				const submitter = form.querySelector('button[type=submit]');
				submitter.focus();
				form.requestSubmit(submitter);
			})()`);
			const deadline = Date.now() + 10_000;
			while (patchCount < expectedPatchCount && Date.now() < deadline) await delay(25);
			assert.equal(patchCount, expectedPatchCount);
			await delay(100);
		}

		await submitCorrected(1);
		assert.deepEqual(await cdp.evaluate(`[...document.querySelectorAll('#case-form-alert span')].map((node) => node.textContent.trim())`),
			['Case name is required.', 'Add at least one docket.']);

		responseMode = 'collision';
		await submitCorrected(2);
		const collision = await cdp.evaluate(`(() => ({
			text: document.getElementById('case-form-alert')?.textContent.trim(),
			required: document.getElementById('case-form-alert')?.textContent.includes('required') ?? false,
			aria: ['case_name', 'docket_number'].map((id) => document.getElementById(id).getAttribute('aria-invalid')),
			borders: ['case_name', 'docket_number'].map((id) => getComputedStyle(document.getElementById(id)).borderColor),
			focus: document.activeElement.id,
		}))()`);
		assert.equal(collision.text, 'This title generates a URL slug that conflicts with an existing case. Choose a different title.');
		assert.equal(collision.required, false);
		assert.deepEqual(collision.aria, [null, null]);
		assert.deepEqual(collision.borders, ['rgb(51, 65, 85)', 'rgb(51, 65, 85)']);
		assert.notEqual(collision.focus, 'case_name');
		assert.notEqual(collision.focus, 'docket_number');

		responseMode = 'generic';
		await submitCorrected(3);
		const generic = await cdp.evaluate(`(() => ({
			text: document.getElementById('case-form-alert')?.textContent.trim(),
			aria: ['case_name', 'docket_number'].map((id) => document.getElementById(id).getAttribute('aria-invalid')),
			borders: ['case_name', 'docket_number'].map((id) => getComputedStyle(document.getElementById(id)).borderColor),
		}))()`);
		assert.equal(generic.text, 'Could not save changes. Check your inputs and try again.');
		assert.deepEqual(generic.aria, [null, null]);
		assert.deepEqual(generic.borders, ['rgb(51, 65, 85)', 'rgb(51, 65, 85)']);
	} finally {
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi.closeAllConnections();
		await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
	}
});
