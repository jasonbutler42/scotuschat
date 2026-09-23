/**
 * One browser resolver for every *.browser.test.mjs harness.
 *
 * These tests drive a real Chromium over CDP. Four of them each carried their
 * own copy of this function — three textually different variants — and every
 * copy probed exactly three fixed system paths:
 *
 *   /usr/bin/microsoft-edge, /usr/bin/google-chrome, /usr/bin/chromium
 *
 * On a machine whose only Chromium is the Playwright-managed one under
 * ~/.cache/ms-playwright, all three miss, and the suite fail-closes with
 * "must be installed" while a perfectly good browser sits on disk. That is
 * what kept the five real-browser tests unrunnable here even after the host's
 * NSS libraries were fixed: two different causes wearing one symptom.
 *
 * Resolution order — first hit wins:
 *   1. $SCOTUS_TEST_BROWSER, then $CHROME_PATH — an explicit override always
 *      beats discovery, so CI or a bisect can pin an exact binary.
 *   2. The Playwright-managed Chromium, newest build first. Preferred over the
 *      system browser because it is the one `npx playwright install` pins, so
 *      it matches what the Playwright MCP drives interactively.
 *   3. The system paths the original copies probed, unchanged.
 *
 * The headless shell is deliberately last within (2): it speaks CDP, but it is
 * not a full browser, and these harnesses pass --headless=new to a full one.
 */
import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import path from 'node:path';

function playwrightRoot() {
	if (process.env.PLAYWRIGHT_BROWSERS_PATH) return process.env.PLAYWRIGHT_BROWSERS_PATH;
	if (process.platform === 'win32') {
		return path.join(process.env.LOCALAPPDATA ?? path.join(homedir(), 'AppData', 'Local'), 'ms-playwright');
	}
	if (process.platform === 'darwin') {
		return path.join(homedir(), 'Library', 'Caches', 'ms-playwright');
	}
	return path.join(homedir(), '.cache', 'ms-playwright');
}

// Build directories sort as chromium-1228, chromium-191 — lexically wrong, so
// compare the trailing build number numerically and take the newest.
function buildNumber(name) {
	const n = Number(name.slice(name.lastIndexOf('-') + 1));
	return Number.isFinite(n) ? n : -1;
}

function playwrightCandidates() {
	const root = playwrightRoot();
	if (!existsSync(root)) return [];

	let entries;
	try {
		entries = readdirSync(root);
	} catch {
		return [];
	}

	const binaries = {
		'chromium-': {
			linux: ['chrome-linux64/chrome', 'chrome-linux/chrome'],
			darwin: ['chrome-mac/Chromium.app/Contents/MacOS/Chromium'],
			win32: ['chrome-win/chrome.exe', 'chrome-win64/chrome.exe'],
		},
		'chromium_headless_shell-': {
			linux: ['chrome-headless-shell-linux64/chrome-headless-shell'],
			darwin: ['chrome-headless-shell-mac/chrome-headless-shell'],
			win32: ['chrome-headless-shell-win64/chrome-headless-shell.exe'],
		},
	};
	const platform = process.platform === 'win32' ? 'win32' : process.platform === 'darwin' ? 'darwin' : 'linux';

	const found = [];
	for (const prefix of Object.keys(binaries)) {
		const dirs = entries
			.filter((e) => e.startsWith(prefix))
			.sort((a, b) => buildNumber(b) - buildNumber(a));
		for (const dir of dirs) {
			for (const rel of binaries[prefix][platform]) {
				found.push(path.join(root, dir, rel));
			}
		}
	}
	return found;
}

function systemCandidates() {
	if (process.platform === 'win32') {
		return [
			'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
			'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
			'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
			'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
		];
	}
	if (process.platform === 'darwin') {
		return [
			'/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
			'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
			'/Applications/Chromium.app/Contents/MacOS/Chromium',
		];
	}
	return ['/usr/bin/microsoft-edge', '/usr/bin/google-chrome', '/usr/bin/chromium'];
}

export function browserExecutable() {
	for (const key of ['SCOTUS_TEST_BROWSER', 'CHROME_PATH']) {
		const override = process.env[key];
		if (override) return existsSync(override) ? override : undefined;
	}
	return [...playwrightCandidates(), ...systemCandidates()].find((c) => existsSync(c));
}

/**
 * The assertion message every harness shares. Says how to fix it, because
 * "must be installed" sent someone looking for a missing package when the
 * browser was already on disk and merely unfound.
 */
export const NO_BROWSER_MESSAGE =
	'No Chromium found for this fail-closed browser test. Install one with ' +
	'`npx playwright install chromium`, or a system Chrome/Edge/Chromium, or ' +
	'point $SCOTUS_TEST_BROWSER at an executable.';
