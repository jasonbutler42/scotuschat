import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { existsSync } from 'node:fs';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';
import test from 'node:test';

async function freePort() { const server = createServer(); await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); }); const port = server.address().port; await new Promise((resolve) => server.close(resolve)); return port; }
async function waitFor(url, predicate = (response) => response.ok, timeoutMs = 20_000) { const deadline = Date.now() + timeoutMs; while (Date.now() < deadline) { try { const response = await fetch(url); if (await predicate(response)) return response; } catch {} await delay(100); } throw new Error(`Timed out waiting for ${url}`); }
function browserExecutable() { return (process.platform === 'win32' ? ['C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe','C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'] : ['/usr/bin/microsoft-edge','/usr/bin/google-chrome','/usr/bin/chromium']).find(existsSync); }
async function terminate(child) { if (!child || child.exitCode !== null) return; child.kill('SIGTERM'); await Promise.race([new Promise((resolve) => child.once('exit', resolve)), delay(5_000)]); }
class Cdp { constructor(url) { this.socket = new WebSocket(url); this.id = 0; this.pending = new Map(); } async open() { await new Promise((resolve, reject) => { this.socket.addEventListener('open', resolve, { once: true }); this.socket.addEventListener('error', reject, { once: true }); }); this.socket.addEventListener('message', ({ data }) => { const message = JSON.parse(data); const waiter = this.pending.get(message.id); if (!waiter) return; this.pending.delete(message.id); message.error ? waiter.reject(new Error(message.error.message)) : waiter.resolve(message.result); }); } call(method, params = {}) { const id = ++this.id; return new Promise((resolve, reject) => { this.pending.set(id, { resolve, reject }); this.socket.send(JSON.stringify({ id, method, params })); }); } async eval(expression) { const result = await this.call('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (result.exceptionDetails) throw new Error(result.exceptionDetails.text); return result.result.value; } close() { this.socket.close(); } }

test('copy feedback belongs only to the latest payload and activation', { timeout: 60_000 }, async () => {
	let vite, browser, cdp, profile;
	try {
		const appPort = await freePort(), debugPort = await freePort(); profile = await mkdtemp(path.join(tmpdir(), 'scotus-copy-browser-')); const executable = browserExecutable(); assert.ok(executable, 'Microsoft Edge or Google Chrome must be installed for this fail-closed test');
		vite = spawn(process.execPath, [path.resolve('node_modules/vite/bin/vite.js'), '--config', path.resolve('tests/fixtures/copyable-extracted-value-vite.config.mjs'), '--host','127.0.0.1','--port',String(appPort),'--strictPort'], { cwd: path.resolve('.'), stdio: 'ignore', windowsHide: true });
		await waitFor(`http://127.0.0.1:${appPort}/copyable-extracted-value.html`);
		browser = spawn(executable, ['--headless=new','--disable-gpu','--no-first-run','--remote-allow-origins=*',`--remote-debugging-port=${debugPort}`,`--user-data-dir=${profile}`,`http://127.0.0.1:${appPort}/copyable-extracted-value.html`], { stdio: 'ignore', windowsHide: true });
		const response = await waitFor(`http://127.0.0.1:${debugPort}/json/list`, async (r) => (await r.clone().json()).some((x) => x.type === 'page')); const targets = await response.json(); cdp = new Cdp(targets.find((x) => x.type === 'page').webSocketDebuggerUrl); await cdp.open(); await cdp.call('Runtime.enable'); await delay(500);
		const evalDom = (body) => cdp.eval(`(async()=>{${body}})()`);
		await evalDom(`while(!window.copyFixture) await new Promise(r=>setTimeout(r,20));`);

		// A newer success owns the full timer even when an older success already scheduled one.
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(0,true); await Promise.resolve();`);
		await delay(300);
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(1,true); await Promise.resolve();`);
		await delay(1250);
		assert.equal(await cdp.eval(`document.querySelector('.success')?.textContent`), 'Copied');
		await delay(300);
		assert.equal(await cdp.eval(`document.querySelector('.success')?.textContent ?? null`), null);

		// Out-of-order settlement cannot let an older attempt replace newer feedback.
		await evalDom(`document.querySelector('button').click(); document.querySelector('button').click(); copyFixture.settle(3,true); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success')?.textContent`), 'Copied');
		await evalDom(`copyFixture.settle(2,false); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.error')?.textContent ?? null`), null);

		// Latest rejection uses fixed local copy; a successful retry replaces it.
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(4,false); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.error')?.textContent`), "Couldn't copy.");
		assert.equal((await cdp.eval(`document.body.textContent`)).includes('secret browser error'), false);
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(5,true); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success')?.textContent`), 'Copied');

		// Payload changes clear pending, success, and error feedback and invalidate old work.
		await evalDom(`document.querySelector('button').click(); copyFixture.set('Beta','Copy Beta'); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success,.error')?.textContent ?? null`), null);
		await evalDom(`copyFixture.settle(6,true); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success,.error')?.textContent ?? null`), null);
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(7,true); await Promise.resolve(); copyFixture.set('Gamma','Copy Gamma'); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success,.error')?.textContent ?? null`), null);
		await evalDom(`document.querySelector('button').click(); copyFixture.settle(8,false); await Promise.resolve(); copyFixture.set('Delta','Copy Delta'); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('.success,.error')?.textContent ?? null`), null);

		// Destruction invalidates a pending attempt without a post-destroy update.
		await evalDom(`document.querySelector('button').click(); copyFixture.destroy(); copyFixture.settle(9,true); await Promise.resolve();`);
		assert.equal(await cdp.eval(`document.querySelector('#fixture').textContent`), '');
	} finally { cdp?.close(); await terminate(browser); await terminate(vite); if (profile) await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }); }
});
