import { FASTAPI_BASE_URL } from '$env/static/private';
import { error, redirect } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	const matches = data.cases.filter((c: { slug: string }) => c.slug === params.slug);
	if (matches.length === 0) throw error(404, 'Case not found');
	if (matches.length === 1) {
		redirect(307, `/cases/${params.slug}/arguments/${matches[0].argument_id}`);
	}
	// Multi-argument case: return list for the argument picker page
	return { slug: params.slug, caseName: matches[0].case_name, arguments: matches };
};
