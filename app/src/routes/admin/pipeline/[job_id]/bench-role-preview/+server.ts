import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Plan 44-09 tenure-preview follow-up (RESOLVE-15/16 remediation, operator-
// approved): live preview of a bench candidate's tenure-derived role before
// the Resolve card's batch ?/resolve submit commits the pick. Client-side
// fetch target for ResolveCard.svelte (Architecture Rule 2 — FASTAPI_BASE_URL
// stays server-only; the browser never sees it). Mirrors the sibling polling
// +server.ts's proxy pattern. Auth enforced by hooks.server.ts before this
// handler runs.
export const GET: RequestHandler = async ({ params, url }) => {
	const personId = url.searchParams.get('person_id');
	if (!personId) return json(null, { status: 400 });
	try {
		const res = await fetch(
			`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/people/${personId}/bench-role-preview`,
			{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
		);
		if (!res.ok) return json(null, { status: res.status });
		return json(await res.json());
	} catch {
		return json(null, { status: 502 });
	}
};
