import { fail, redirect } from '@sveltejs/kit';
import {
	classifyFixtureStateOutcome as classifyOutcome,
	EXPECTED_FIXTURE_END_STATES,
	RESET_MID_ERROR,
	RESET_PARTIAL_ERROR,
	toResetFixtures,
} from '$lib/admin/resetOutcome.js';
import type { Actions, PageServerLoad } from './$types';
import { SESSION_COOKIE_NAME } from '$lib/server/session';
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
// Phase 43 (D-07): ENVIRONMENT is deliberately read via the dynamic-private env module
// below, NOT the static-private import above (which ADMIN_TOKEN/FASTAPI_BASE_URL use).
// Static-private values are inlined by Vite at build time, which would make the Dev
// Tools gate a build-time decision and require a separate build artifact for prod vs
// dev. D-07 requires the gate to be evaluated at app-startup/request-time from the
// same codebase — do not "normalize" this back to the static import.
import { env } from '$env/dynamic/private';

// ──────────────────────────────────────────────────────────────────────────
// Types (mirror api/schemas/admin_dashboard.py; Plan 28-02's seven routes)
// ──────────────────────────────────────────────────────────────────────────

interface ArgumentStats {
	total: number | null;
	published: number | null;
	draft: number | null;
	unpublished: number | null;
}

interface RecentDraft {
	id: number;
	case_name: string;
	docket_number: string;
}

interface PeopleStats {
	total: number | null;
	incomplete: number | null;
}

interface IncompletePerson {
	id: number;
	full_name: string;
	missing: string[];
}

interface TenureGapJustice {
	id: number;
	full_name: string;
}

interface PipelineStats {
	recent_count: number | null;
	last_activity_at: string | null;
}

// Phase 49 (D-30) — the fifth StatCard's backing counts.
interface ReviewStats {
	arguments: number | null;
	people: number | null;
	total: number | null;
}

interface UtteranceCount {
	total: number | null;
}

export const load: PageServerLoad = async ({ fetch }) => {
	// Sequential degrade-gracefully fetches (28-PATTERNS.md; RESEARCH.md zero
	// parallel-fetch precedent) — each of the seven Plan 28-02 endpoints is fetched
	// in its own try/catch with a safe default. load() never throws error()/
	// redirect() here: this is a landing page with no 404 concept, and the
	// UI-SPEC "Load-failure state" contract requires the dashboard to never
	// hard-error on a partial data-source failure (T-28-09).

	// 1. Arguments stat-card counts (DASH-01, DASH-02).
	let argumentStats: ArgumentStats = { total: null, published: null, draft: null, unpublished: null };
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/stats`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			argumentStats = await res.json();
		} else {
			console.error(`[load] arguments/stats fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] arguments/stats fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 2. People stat-card counts (DASH-01, DASH-02) — combined bench+advocate (D-05 amendment).
	let peopleStats: PeopleStats = { total: null, incomplete: null };
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/stats`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			peopleStats = await res.json();
		} else {
			console.error(`[load] people/stats fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] people/stats fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 3. Pipeline runs stat-card (DASH-01) — 30-day recent_count + unbounded last_activity_at.
	let pipelineStats: PipelineStats = { recent_count: null, last_activity_at: null };
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/stats`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			pipelineStats = await res.json();
		} else {
			console.error(`[load] jobs/stats fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] jobs/stats fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 4. Utterances stat-card (DASH-01) — no CTA, single total.
	let utteranceCount: UtteranceCount = { total: null };
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/utterances/count`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			utteranceCount = await res.json();
		} else {
			console.error(`[load] utterances/count fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] utterances/count fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 4b. Review queue stat-card counts (Phase 49, D-30) — dedicated COUNT
	// endpoint, never derived by fetching the unbounded queue list.
	let reviewStats: ReviewStats = { arguments: null, people: null, total: null };
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/review/stats`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			reviewStats = await res.json();
		} else {
			console.error(`[load] review/stats fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] review/stats fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 5. Needs Attention — Drafts sub-list (DASH-03, D-01, D-02, D-03). Degrades to [].
	let draftsList: RecentDraft[] = [];
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/recent-drafts`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			draftsList = await res.json();
		} else {
			console.error(`[load] arguments/recent-drafts fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error(
			'[load] arguments/recent-drafts fetch threw:',
			err instanceof Error ? err.message : String(err),
		);
	}

	// 6. Needs Attention — People sub-list (DASH-03, D-01, D-02). Degrades to [].
	let incompletePeople: IncompletePerson[] = [];
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/incomplete`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			incompletePeople = await res.json();
		} else {
			console.error(`[load] people/incomplete fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] people/incomplete fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// 7. Needs Attention — Justices sub-list (DASH-03, D-01, D-02, D-06). Degrades to [].
	let tenureGapJustices: TenureGapJustice[] = [];
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/tenure-gaps`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			tenureGapJustices = await res.json();
		} else {
			console.error(`[load] people/tenure-gaps fetch failed: returned ${res.status}`);
		}
	} catch (err) {
		console.error('[load] people/tenure-gaps fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// Phase 43 (D-07): server-decided gate for the Dev Tools section. Allow-list
	// comparison (not a block-list) — an unset or misspelled value yields false,
	// matching the backend's settings.environment == "development" contract (D-02).
	// Only this derived boolean crosses to the client; the raw string never does.
	const isDevelopment = env.ENVIRONMENT === 'development';

	return {
		argumentStats,
		peopleStats,
		pipelineStats,
		utteranceCount,
		reviewStats,
		draftsList,
		incompletePeople,
		tenureGapJustices,
		isDevelopment,
	};
};

// Phase 43 (D-05/D-06/D-07) error copies, unchanged verbatim.
// Phase 52-05 (D-14) lifts this file's former two-copy-only lock — see
// 52-UI-SPEC.md's Copywriting Contract, which amends 43-UI-SPEC.md's in
// place. There are now four outcomes: the two below, plus RESET_PARTIAL_ERROR
// and a no-error full-success path, each driven by a follow-up read of what
// actually landed (resolveFromReRead below) rather than by which code path
// failed.
const RESET_ENV_ERROR = 'Reset failed: this action is not available in this environment.';
// RESET_MID_ERROR and RESET_PARTIAL_ERROR live in $lib/admin/resetOutcome.js,
// shared with the page's post-still-running completion check.

// Phase 52-05 (D-15): the reset fetch previously had no AbortSignal at all,
// inheriting undici's own 300s headersTimeout uncontrolled — the exact
// false-alarm case the folded todo documented (a fully successful reset
// whose client simply gave up listening). Sized comfortably above the
// 71.67s wall-clock floor plan 52-04 measured via a direct call (bypassing
// HTTP-layer overhead — a floor, not a final number; see 52-04-SUMMARY.md's
// methodology caveat), while staying well under undici's 300s ceiling.
// Exceeding it throws (AbortError), which routes into resolveFromReRead
// below rather than being reported as a failure outright.
const RESET_ABORT_TIMEOUT_MS = 280_000;

// Phase 52-05 follow-up (UAT 2026-09-25): a reset that is STILL RUNNING is not
// a reset that failed. The backend publishes `progress` on the same
// fixture-state response the re-read already fetches, non-null for exactly as
// long as an operation is in flight — but classifyFixtureStateOutcome used to
// read only `fixtures`, so an abort that fired while the server was still
// working produced a fixtures snapshot that was legitimately incomplete and
// was reported as RESET_PARTIAL_ERROR ("do not use it"). Observed live: the
// reset completed correctly (132 people, all 4 fixtures in their expected end
// states) while the operator was told the database was unusable. The evidence
// to tell the two apart was in the response and was being discarded — exactly
// what D-14 exists to prevent.
const RESET_STILL_RUNNING_NOTICE =
	'Still reseeding. This request stopped listening before the reset finished, but the server is still working — the progress line above is live. Nothing is wrong with the database; wait for it to finish.';

interface FixtureStateItem {
	conversation_id: string;
	case_name: string;
	role: string;
	present: boolean;
	argument_id: number | null;
	status: string | null;
	latest_import_run_step: string | null;
}

interface FixtureStateResponse {
	fixtures: FixtureStateItem[];
	progress: { step: string; completed: number; total: number } | null;
}

/**
 * Phase 52-05 (D-14): re-reads GET /api/admin/dev/fixture-state directly
 * (server-side, same FASTAPI_BASE_URL/ADMIN_TOKEN access resetToFixture
 * already uses — not routed through the dev-fixture-state/+server.ts proxy,
 * which exists for the browser's own polling, not for this server-side
 * call). Returns null on any failure to obtain evidence at all.
 */
async function reReadFixtureState(
	fetch: typeof globalThis.fetch,
): Promise<FixtureStateResponse | null> {
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/dev/fixture-state`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (!res.ok) return null;
		return (await res.json()) as FixtureStateResponse;
	} catch {
		return null;
	}
}

/**
 * Classifies the re-read's evidence into one of D-14's three post-re-read
 * outcomes (the fourth, environment refusal, short-circuits before any
 * re-read is attempted — see resetToFixture below).
 */
function classifyFixtureStateOutcome(
	state: FixtureStateResponse | null,
): 'in-progress' | 'full-success' | 'partial' | 'inconclusive' {
	// Delegates to the extracted, unit-tested implementation
	// (app/src/lib/admin/resetOutcome.js + app/tests/reset-outcome-classifier.test.mjs).
	// This decides what an operator is told after a destructive operation, and
	// the original in-file version shipped with no test and a real defect: it
	// read only `fixtures`, never `progress`, so a still-running reset was
	// reported as a partial one.
	return classifyOutcome(state, EXPECTED_FIXTURE_END_STATES);
}

/**
 * Phase 52-05 (D-14): the single convergence point every non-404
 * resetToFixture failure routes through — a thrown fetch/abort, a non-ok
 * status, an unparseable body, or a fixtures array that is not exactly 4
 * entries long. Re-reads fixture state and maps the evidence to one of
 * three outcomes:
 *   - full success: returns the same `resetFixtures` success shape the
 *     happy path returns, so the page renders the existing Success markup
 *     with no new template branch and NO error is shown at all — the
 *     direct fix for the false-alarm case the folded todo identified.
 *   - partial: RESET_PARTIAL_ERROR.
 *   - inconclusive (no evidence obtained): RESET_MID_ERROR, now the true
 *     fallback rather than the default for every failure mode.
 */
async function resolveFromReRead(fetch: typeof globalThis.fetch) {
	const state = await reReadFixtureState(fetch);
	const outcome = classifyFixtureStateOutcome(state);

	if (outcome === 'in-progress') {
		// 503 + resetStillRunning: the page keeps its Running state and keeps
		// polling instead of dropping to Idle with an error, because the
		// operation the operator started has not finished yet.
		return fail(503, {
			resetError: RESET_STILL_RUNNING_NOTICE,
			resetStillRunning: true,
		});
	}

	if (outcome === 'full-success') {
		return { resetFixtures: toResetFixtures(state!) };
	}

	if (outcome === 'partial') {
		return fail(502, { resetError: RESET_PARTIAL_ERROR });
	}

	return fail(502, { resetError: RESET_MID_ERROR });
}

// Phase 49 (D-33a): the seeder's own two copies — deliberately NOT the reset
// action's RESET_ENV_ERROR/RESET_MID_ERROR literals above. This action never
// truncates or reseeds the database, so it must not claim to risk leaving it
// "in an inconsistent state" the way RESET_MID_ERROR does.
const SEED_ENV_ERROR = 'Seed failed: this action is not available in this environment.';
const SEED_GENERIC_ERROR = 'Seed failed — check server logs for details.';

export const actions: Actions = {
	logout: async ({ cookies }) => {
		// Delete the session cookie using path '/' — must match sessionCookieOptions.path
		// used when the cookie was set in Plan 02 (admin/login/+page.server.ts).
		// A path mismatch would leave the cookie in the browser (T-06-12).
		cookies.delete(SESSION_COOKIE_NAME, { path: '/' });

		// Redirect to login — the deleted cookie cannot pass verifySession on the next
		// request, so the Plan 01 hooks.server.ts guard will also redirect to login
		// if any tab still tries to access /admin (AUTH-03: immediate invalidation).
		throw redirect(302, '/admin/login');
	},

	/**
	 * resetToFixture — proxies to the dev-only reset endpoint below (Phase 43, D-05/D-06/D-07;
	 * re-read behavior added Phase 52-05, D-14/D-15).
	 *
	 * Takes no form data — no corpus path, no fixture list, no other parameter. The
	 * backend endpoint has no request surface and this action must not invent one.
	 *
	 * Re-checks the gate first (defense in depth; the section is already omitted from
	 * the DOM when not development, so this branch should be unreachable — the
	 * backend's unmounted router is the real enforcement, D-07).
	 *
	 * D-14: only the 404/environment-refusal path short-circuits directly to
	 * RESET_ENV_ERROR. Every other failure — a thrown fetch (including the
	 * RESET_ABORT_TIMEOUT_MS signal firing), a non-ok status (including the
	 * backend's 503 corpus-missing case), an unparseable body, or a parsed
	 * fixtures array that is not exactly 4 entries long — converges on
	 * resolveFromReRead, which re-reads fixture state before asserting
	 * anything and reports what it actually found.
	 *
	 * On success (this request's own response, not a re-read), returns the
	 * parsed fixtures array under `resetFixtures` (not a redirect) — the
	 * UI-SPEC's Success state renders inline on the same page.
	 */
	resetToFixture: async ({ fetch }) => {
		if (env.ENVIRONMENT !== 'development') {
			return fail(404, { resetError: RESET_ENV_ERROR });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/dev/reset-to-fixture`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
				signal: AbortSignal.timeout(RESET_ABORT_TIMEOUT_MS),
			});
		} catch {
			return await resolveFromReRead(fetch);
		}

		if (res.status === 404) {
			return fail(404, { resetError: RESET_ENV_ERROR });
		}

		if (!res.ok) {
			return await resolveFromReRead(fetch);
		}

		let body: { fixtures?: unknown };
		try {
			body = await res.json();
		} catch {
			return await resolveFromReRead(fetch);
		}

		// A partial reseed is an error state, never a shorter success list —
		// the fixture set is fixed at exactly 4 by FIXTURES.md. Routed through
		// the same re-read as every other failure rather than asserted
		// directly, since the re-read is the only thing that can distinguish
		// "actually partial" from "this response was malformed but the
		// database is fine" (D-14).
		if (!Array.isArray(body.fixtures) || body.fixtures.length !== 4) {
			return await resolveFromReRead(fetch);
		}

		return { resetFixtures: body.fixtures };
	},

	/**
	 * seedUnresolvedSpeaker — proxies to the dev-only unresolved-speaker
	 * seeder below (Phase 49, D-33a).
	 *
	 * Takes no form data — the target conversation is the backend service's
	 * own default constant, never a request surface (mirrors resetToFixture's
	 * own no-request-surface discipline).
	 *
	 * Re-checks the gate first — defense in depth; the control is already
	 * omitted from the DOM when not development, so this branch should be
	 * unreachable. The real enforcement is the backend's unmounted router
	 * (D-07), the same gate resetToFixture relies on.
	 *
	 * Maps every failure to exactly one of two copies, distinct from
	 * resetToFixture's pair:
	 *   - 404 from the backend -> SEED_ENV_ERROR (environment refusal)
	 *   - every other non-ok status, a thrown fetch (network failure), or a
	 *     response body that fails to parse as JSON -> SEED_GENERIC_ERROR
	 *
	 * On success, returns the parsed body under `seedResult` (not a
	 * redirect) — renders inline on the same page, mirroring resetToFixture.
	 */
	seedUnresolvedSpeaker: async ({ fetch }) => {
		if (env.ENVIRONMENT !== 'development') {
			return fail(404, { seedError: SEED_ENV_ERROR });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/dev/seed-unresolved-speaker`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { seedError: SEED_GENERIC_ERROR });
		}

		if (res.status === 404) {
			return fail(404, { seedError: SEED_ENV_ERROR });
		}

		if (!res.ok) {
			return fail(502, { seedError: SEED_GENERIC_ERROR });
		}

		let body: unknown;
		try {
			body = await res.json();
		} catch {
			return fail(502, { seedError: SEED_GENERIC_ERROR });
		}

		return { seedResult: body };
	},
};
