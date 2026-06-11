import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
	if (!res.ok) throw error(res.status, 'Failed to load argument');
	const data = await res.json();
	return {
		utterances: data.utterances,
		argument: data.argument, // includes case_name, docket_number, argued_date, question_number
		argument_id: parseInt(params.id)
	};
};
