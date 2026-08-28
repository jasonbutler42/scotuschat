import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// D-14/D-15 (Phase 51 plan 51-08): the term index replaces the transitional
// flat listing plan 51-02 shipped. Primary fetch fails closed —
// `throw error(res.status, ...)` on a non-OK response, so SvelteKit's error
// boundary renders rather than the page pretending the corpus is empty.
// `GET /arguments/terms` (plan 51-04) itself returns an empty `terms` array
// (never a 404) when nothing is published — that is a 200 the empty-state
// branch below handles, not an error path.
export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/terms`);
	if (!res.ok) throw error(res.status, 'Failed to load arguments');
	const data = await res.json();
	return { terms: data.terms };
};
