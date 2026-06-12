import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	return { cases: data.cases };
};
