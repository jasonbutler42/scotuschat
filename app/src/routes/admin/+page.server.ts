import { redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { SESSION_COOKIE_NAME } from '$lib/server/session';
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';

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

	return {
		argumentStats,
		peopleStats,
		pipelineStats,
		utteranceCount,
		draftsList,
		incompletePeople,
		tenureGapJustices,
	};
};

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
	}
};
