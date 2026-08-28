import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// D-10/D-11 (Phase 51 plan 51-02): flat listing at /arguments, no /cases
// route and no redirect layer. Still fetches the existing /cases endpoint —
// this is transitional (D-14/D-15's term-grouped endpoints replace it in
// plan 51-08) and is a known, deliberate scope boundary of this plan.
export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load arguments');
	const data = await res.json();
	return { cases: data.cases };
};
