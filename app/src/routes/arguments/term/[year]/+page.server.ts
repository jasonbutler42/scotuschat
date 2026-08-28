import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

// D-14/D-15/D-16 (Phase 51 plan 51-08): the term-detail listing. Two
// distinct error paths, per the UI-SPEC E2 "error"/"empty" contract:
//  - A non-numeric or out-of-range year -> the API answers 422 -> a
//    genuine 404, rendered by the /arguments error boundary. Unlike the
//    old /cases/[slug] load (git history), no redirect is ever added
//    here (D-11).
//  - A real term with nothing published -> the API answers 200 with an
//    empty `arguments` array -> NOT a 404; the page renders the
//    term-scoped empty state.
//  - Any other non-OK response fails closed with the generic listing
//    error copy (rendered by the same error boundary).
export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/term/${params.year}`);
	if (res.status === 422) throw error(404, 'Term not found');
	if (!res.ok) throw error(res.status, 'Failed to load arguments');
	const data = await res.json();
	return { termYear: data.term_year, arguments: data.arguments };
};
