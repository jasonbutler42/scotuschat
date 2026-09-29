/**
 * Shared mock-API + Vite + headless-Chromium + CDP harness for the public
 * argument transcript route (`/arguments/[slug]`).
 *
 * Lifted from `speaker-initials.browser.test.mjs` (Phase 52 Plan 02), which
 * carried this exact shape inline. Extracted here so Phase 53's Treatment D
 * test (and any future transcript browser test) does not duplicate free-port
 * allocation, mock FASTAPI serving, Vite spawn env, headless launch, and CDP
 * wiring a fourth time — the same "one helper, not N textual copies" lesson
 * `browser-executable.mjs`'s own header records.
 *
 * `speaker-initials.browser.test.mjs` itself is left untouched — this module
 * is purely additive.
 */
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import { browserExecutable, NO_BROWSER_MESSAGE } from './browser-executable.mjs';
import { APP_DIR, VITE_BIN } from './paths.mjs';

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

/** Polls `expression` in the page until it is truthy, or throws on timeout. */
export async function waitForExpression(cdp, expression, timeoutMs = 15_000) {
	const deadline = Date.now() + timeoutMs;
	while (Date.now() < deadline) {
		if (await cdp.evaluate(expression)) return true;
		await delay(50);
	}
	throw new Error(`Timed out waiting for browser expression: ${expression}`);
}

/**
 * Boots a mock FASTAPI server, a real Vite dev server, and a headless
 * Chromium pointed at `/arguments/{slug}`, then connects CDP to it.
 *
 * Fails loudly (throws with `NO_BROWSER_MESSAGE`) when no Chromium resolves —
 * never silently skips, so a missing browser cannot read as a passing suite.
 *
 * @param {object} options
 * @param {string} options.slug - the argument slug the route is loaded at.
 * @param {object} options.argumentPayload - body for
 *   `GET /arguments/by-slug/{slug}/utterances`.
 * @param {unknown[]} options.speakersPayload - body for
 *   `GET /arguments/by-slug/{slug}/speakers`.
 * @param {{ width: number, height: number }} [options.viewport] - initial
 *   viewport applied via CDP `Emulation.setDeviceMetricsOverride`.
 * @returns {Promise<{ cdp: CdpClient, setViewport: (width: number, height: number) => Promise<void>, close: () => Promise<void> }>}
 */
export async function openTranscriptPage({ slug, argumentPayload, speakersPayload, viewport }) {
	const mockApi = createServer((request, response) => {
		response.setHeader('content-type', 'application/json');
		if (request.method === 'GET' && request.url === `/arguments/by-slug/${slug}/utterances`) {
			response.end(JSON.stringify(argumentPayload));
			return;
		}
		if (request.method === 'GET' && request.url === `/arguments/by-slug/${slug}/speakers`) {
			response.end(JSON.stringify(speakersPayload));
			return;
		}
		response.statusCode = 404;
		response.end(JSON.stringify({ detail: 'not found' }));
	});

	const executable = browserExecutable();
	if (!executable) {
		await new Promise((resolve) => mockApi.close(resolve));
		throw new Error(NO_BROWSER_MESSAGE);
	}

	let vite;
	let browser;
	let cdp;
	let profile;

	try {
		const apiPort = await listen(mockApi);
		const appPort = await freePort();
		const debugPort = await freePort();
		profile = await mkdtemp(path.join(tmpdir(), 'scotus-transcript-page-'));

		vite = spawn(process.execPath, [
			VITE_BIN,
			'--host', '127.0.0.1', '--port', String(appPort), '--strictPort',
		], {
			cwd: APP_DIR,
			env: {
				...process.env,
				ADMIN_USERNAME: 'phase53-admin',
				ADMIN_PASSWORD: 'phase53-password',
				ADMIN_TOKEN: 'phase53-test-token',
				SESSION_SECRET: 'phase53-test-session-secret-at-least-32-characters',
				FASTAPI_BASE_URL: `http://127.0.0.1:${apiPort}`,
			},
			stdio: 'ignore',
			windowsHide: true,
		});
		const casePath = `/arguments/${slug}`;
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

		async function setViewport(width, height) {
			await cdp.call('Emulation.setDeviceMetricsOverride', {
				width,
				height,
				deviceScaleFactor: 1,
				mobile: false,
			});
		}

		if (viewport) await setViewport(viewport.width, viewport.height);

		await waitForExpression(cdp, `!!document.querySelector('h1') && document.querySelector('h1').textContent.length > 0`);

		async function close() {
			cdp?.close();
			await terminateTree(browser);
			await terminateTree(vite);
			mockApi.closeAllConnections();
			await new Promise((resolve) => mockApi.close(resolve));
			if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
		}

		return { cdp, setViewport, close };
	} catch (error) {
		// Setup failed partway through — tear down whatever did start before
		// rethrowing, so a failed openTranscriptPage() never leaks a dangling
		// Vite/Chromium/mock-API process for the caller to clean up.
		cdp?.close();
		await terminateTree(browser);
		await terminateTree(vite);
		mockApi.closeAllConnections();
		await new Promise((resolve) => mockApi.close(resolve));
		if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
		throw error;
	}
}
