import { fail, redirect } from '@sveltejs/kit';
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

// Phase 43 (D-05/D-06/D-07): the two locked error copies from
// 43-UI-SPEC.md's Copywriting Contract. No third variant is ever returned.
const RESET_ENV_ERROR = 'Reset failed: this action is not available in this environment.';
const RESET_MID_ERROR =
	'Reset failed partway through — the database may be in an inconsistent state. Check server logs before retrying.';

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
	 * resetToFixture — proxies to the dev-only reset endpoint below (Phase 43, D-05/D-06/D-07).
	 *
	 * Takes no form data — no corpus path, no fixture list, no other parameter. The
	 * backend endpoint has no request surface and this action must not invent one.
	 *
	 * Re-checks the gate first (defense in depth; the section is already omitted from
	 * the DOM when not development, so this branch should be unreachable — the
	 * backend's unmounted router is the real enforcement, D-07).
	 *
	 * Maps every failure to exactly one of the two locked UI-SPEC error copies:
	 *   - 404 from the backend -> RESET_ENV_ERROR (environment refusal)
	 *   - every other non-ok status, a thrown fetch (network failure), a response
	 *     body that fails to parse as JSON, or a parsed fixtures array that is not
	 *     exactly 4 entries long -> RESET_MID_ERROR (mid-reset failure)
	 * The backend's 503 corpus-missing case also lands on RESET_MID_ERROR even though
	 * nothing was actually deleted (the backend pre-flights the corpus check before the
	 * TRUNCATE) — the UI-SPEC locks a two-copy set and the server log distinguishes them.
	 *
	 * On success, returns the parsed fixtures array under `resetFixtures` (not a
	 * redirect) — the UI-SPEC's Success state renders inline on the same page.
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
			});
		} catch {
			return fail(502, { resetError: RESET_MID_ERROR });
		}

		if (res.status === 404) {
			return fail(404, { resetError: RESET_ENV_ERROR });
		}

		if (!res.ok) {
			return fail(502, { resetError: RESET_MID_ERROR });
		}

		let body: { fixtures?: unknown };
		try {
			body = await res.json();
		} catch {
			return fail(502, { resetError: RESET_MID_ERROR });
		}

		// A partial reseed is an error state, never a shorter success list (43-UI-SPEC.md
		// "partial" row) — the fixture set is fixed at exactly 4 by FIXTURES.md.
		if (!Array.isArray(body.fixtures) || body.fixtures.length !== 4) {
			return fail(502, { resetError: RESET_MID_ERROR });
		}

		return { resetFixtures: body.fixtures };
	},
};
