#!/usr/bin/env node
/**
 * narrow-viewport-audit.mjs
 *
 * Operator decision D-49-12-c (2026-08-25): after G-49-5c showed THREE green
 * source-text gates in api/tests/test_phase49_review_ui_contract.py coexisting
 * with a page that visibly scrolled sideways at 375px, the operator asked
 * whether the browser measurement that caught it should become a committed,
 * re-runnable artifact rather than evaporating after one session. This script
 * is that answer.
 *
 * WHAT IT MEASURES: for each route in the default set (or --routes), it loads
 * the page at the given viewport width (default 375px) in a real headless
 * Chromium and compares `document.documentElement.scrollWidth` against
 * `document.documentElement.clientWidth`. If the page overflows, it ALSO
 * reports the specific offending elements (tag, a text snippet, right edge)
 * — "some page scrolls" without naming the culprit is not actionable, and is
 * exactly the gap this script exists to close.
 *
 * THIS IS A TOOL, NOT A GATE. Nothing in api/tests may import it, no PLAN.md
 * may require it to pass, and CI must not depend on it. It is not a pytest
 * test for three reasons: (1) `app/` has no JS test runner wired into the
 * Python test suite, (2) `.venv` has no Python Playwright binding, and (3) a
 * test that silently reports SKIPPED whenever the browser/profile is absent
 * is a green test that proves nothing — the exact false-green failure mode
 * G-49-5c is the case study for. Layer B (test_phase49_nav_narrow_viewport_
 * contract.py) watches page CHROME structurally; G-49-5c was a PAGE-level
 * bug that a chrome-level gate only happens to cover. This script is the
 * page-level, real-browser complement — an operator tool, run by hand,
 * never wired into a pass/fail gate.
 *
 * No new dependency is introduced. `playwright-core` and the Chromium binary
 * are pre-existing operator-installed tooling outside the repo (installed by
 * `npx playwright install`), resolved at runtime below — never added to
 * app/package.json.
 */

import { existsSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const HOME = homedir();

// ── 1. Resolve chromium ────────────────────────────────────────────────────

function resolveChromium() {
	if (process.env.CHROMIUM_PATH && existsSync(process.env.CHROMIUM_PATH)) {
		return { path: process.env.CHROMIUM_PATH, via: '$CHROMIUM_PATH' };
	}

	const cacheDir = join(HOME, '.cache', 'ms-playwright');
	if (existsSync(cacheDir)) {
		const candidates = readdirSync(cacheDir)
			.filter((name) => name.startsWith('chromium-') && !name.includes('headless_shell'))
			.sort()
			.reverse(); // newest version string first
		for (const dir of candidates) {
			const candidatePath = join(cacheDir, dir, 'chrome-linux64', 'chrome');
			if (existsSync(candidatePath)) {
				return { path: candidatePath, via: `~/.cache/ms-playwright/${dir}` };
			}
		}
	}

	for (const bin of ['chromium', 'google-chrome']) {
		const pathDirs = (process.env.PATH || '').split(':');
		for (const dir of pathDirs) {
			const candidatePath = join(dir, bin);
			if (existsSync(candidatePath)) {
				return { path: candidatePath, via: `PATH (${bin})` };
			}
		}
	}

	return null;
}

// ── 2. Resolve playwright-core without touching app/package.json ─────────

function resolvePlaywrightCore() {
	const require = createRequire(import.meta.url);
	try {
		return require.resolve('playwright-core');
	} catch {
		// Not resolvable from app/ — this is expected and correct (Task 2b adds
		// no dependency). Fall back to the operator-installed cache location.
	}
	const fallback = join(HOME, '.cache', 'ms-playwright-pkg', 'node_modules', 'playwright-core');
	if (existsSync(fallback)) {
		return fallback;
	}
	return null;
}

// ── 3. CLI args ─────────────────────────────────────────────────────────────

const DEFAULT_ROUTES = [
	'/',
	'/cases',
	'/admin',
	'/admin/review',
	'/admin/arguments',
	'/admin/people',
	'/admin/help'
];

function parseArgs(argv) {
	const args = { baseUrl: 'http://localhost:5173', width: 375, routes: null };
	for (let i = 0; i < argv.length; i++) {
		const arg = argv[i];
		if (arg === '--base-url') args.baseUrl = argv[++i];
		else if (arg === '--width') args.width = parseInt(argv[++i], 10);
		else if (arg === '--routes') args.routes = argv[++i].split(',').map((r) => r.trim());
	}
	if (!args.routes) args.routes = DEFAULT_ROUTES;
	return args;
}

// ── 4. Main ─────────────────────────────────────────────────────────────────

async function main() {
	const chromium = resolveChromium();
	if (!chromium) {
		console.error(
			'ERROR: could not locate a Chromium binary.\n' +
				'  Tried: $CHROMIUM_PATH, ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome, ' +
				'chromium/google-chrome on PATH.\n' +
				'  Fix: run `npx playwright install chromium`, or set CHROMIUM_PATH to an existing binary.'
		);
		process.exitCode = 1;
		return;
	}
	console.log(`Using chromium: ${chromium.path} (via ${chromium.via})`);

	const pwCorePath = resolvePlaywrightCore();
	if (!pwCorePath) {
		console.error(
			'ERROR: could not resolve `playwright-core`.\n' +
				'  Tried: require.resolve("playwright-core") from app/, then ' +
				'~/.cache/ms-playwright-pkg/node_modules/playwright-core.\n' +
				'  Fix: run `npx playwright install` once to populate the cache. ' +
				'This script does NOT add playwright-core to app/package.json by design (D-49-12-c).'
		);
		process.exitCode = 1;
		return;
	}

	const require = createRequire(import.meta.url);
	let chromiumModule;
	try {
		({ chromium: chromiumModule } = require(pwCorePath));
	} catch (err) {
		console.error(`ERROR: failed to load playwright-core from ${pwCorePath}: ${err.message}`);
		process.exitCode = 1;
		return;
	}

	const { baseUrl, width, routes } = parseArgs(process.argv.slice(2));
	const height = 800;

	const profileDir =
		process.env.AUDIT_PROFILE_DIR || join(process.cwd(), '..', '.playwright-profile');

	let context;
	try {
		context = await chromiumModule.launchPersistentContext(profileDir, {
			executablePath: chromium.path,
			headless: true,
			viewport: { width, height }
		});
	} catch (err) {
		console.error(
			`ERROR: could not launch a browser against profile ${profileDir}: ${err.message}\n` +
				'  If another process (e.g. an active Playwright MCP session) already holds this ' +
				'profile open, close it first or set AUDIT_PROFILE_DIR to an alternate directory.'
		);
		process.exitCode = 1;
		return;
	}

	const page = context.pages()[0] || (await context.newPage());
	const results = [];

	for (const route of routes) {
		let response;
		try {
			response = await page.goto(baseUrl + route, { waitUntil: 'networkidle' });
		} catch (err) {
			results.push({ route, status: 'ERROR', detail: err.message });
			continue;
		}

		const finalUrl = page.url();
		if (finalUrl.includes('/admin/login')) {
			// Never report an unauthenticated admin route as passing — a silent
			// pass on an unmeasured route is the exact false-green this script
			// exists to prevent.
			results.push({ route, status: 'SKIPPED', detail: 'redirected to /admin/login (not authenticated)' });
			continue;
		}

		const measured = await page.evaluate(() => {
			const cw = document.documentElement.clientWidth;
			const sw = document.documentElement.scrollWidth;
			let offenders = [];
			if (sw > cw) {
				offenders = Array.from(document.querySelectorAll('body *'))
					.map((el) => ({
						tag: el.tagName.toLowerCase(),
						text: (el.textContent || '').trim().slice(0, 40),
						right: el.getBoundingClientRect().right
					}))
					.filter((o) => o.right > cw + 1)
					.sort((a, b) => b.right - a.right)
					.slice(0, 5);
			}
			return { scrollWidth: sw, clientWidth: cw, offenders };
		});

		results.push({
			route,
			status: measured.scrollWidth > measured.clientWidth ? 'OVERFLOW' : 'PASS',
			scrollWidth: measured.scrollWidth,
			clientWidth: measured.clientWidth,
			offenders: measured.offenders
		});
	}

	await context.close();

	console.log(`\nNarrow-viewport audit — ${width}px viewport, base ${baseUrl}\n`);
	let anyOverflow = false;
	for (const r of results) {
		if (r.status === 'PASS') {
			console.log(`PASS     ${r.route}  (scrollWidth ${r.scrollWidth} <= clientWidth ${r.clientWidth})`);
		} else if (r.status === 'SKIPPED') {
			console.log(`SKIPPED  ${r.route}  (${r.detail})`);
		} else if (r.status === 'ERROR') {
			console.log(`ERROR    ${r.route}  (${r.detail})`);
			anyOverflow = true;
		} else {
			anyOverflow = true;
			console.log(`OVERFLOW ${r.route}  (scrollWidth ${r.scrollWidth} > clientWidth ${r.clientWidth})`);
			for (const o of r.offenders) {
				console.log(`           <${o.tag}> right=${o.right.toFixed(2)}  "${o.text}"`);
			}
		}
	}

	process.exitCode = anyOverflow ? 1 : 0;
}

main();
