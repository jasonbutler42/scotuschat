import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Polling proxy for the Dev Tools "Reset to Fixture" control's Running-state
// per-fixture progress line (Phase 52-05, D-15). Mirrors
// admin/pipeline/[job_id]/+server.ts's proxy shape: FASTAPI_BASE_URL and
// ADMIN_TOKEN are server-only env vars that must never reach the browser
// (Architecture Rule 2), and the browser needs to poll during the in-flight
// resetToFixture POST — this route is what keeps that possible without
// leaking either value client-side.
//
// The +page.server.ts resetToFixture action's own D-14 re-read on failure
// does NOT go through this route — it already runs server-side with direct
// access to FASTAPI_BASE_URL/ADMIN_TOKEN, the same access this handler uses,
// so a self-referential server-to-server hop through this proxy would add
// nothing.
//
// Re-checks the environment gate as defense in depth (mirrors
// resetToFixture's own re-check): the Dev Tools section is already omitted
// from the DOM outside development, and the backend route is itself
// unmounted outside development (D-07), so this branch should be
// unreachable in practice.
export const GET: RequestHandler = async ({ fetch }) => {
	if (env.ENVIRONMENT !== 'development') {
		return json(null, { status: 404 });
	}

	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/dev/fixture-state`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (!res.ok) return json(null, { status: res.status });
		return json(await res.json());
	} catch {
		return json(null, { status: 502 });
	}
};
