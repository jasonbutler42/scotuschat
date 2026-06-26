import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import type { PageServerLoad } from './$types';

type PersonListItem = {
	id: number;
	full_name: string;
	role_id: number | null;
	role_name: string | null;
	missing: string[];
};

export const load: PageServerLoad = async ({ fetch, url }) => {
	const incomplete = url.searchParams.get('incomplete') === '1';
	const tenure_gaps = url.searchParams.get('tenure_gaps') === '1';

	const params = new URLSearchParams();
	if (incomplete) params.set('incomplete', '1');
	if (tenure_gaps) params.set('tenure_gaps', '1');
	const queryString = params.toString();
	const apiUrl = `${FASTAPI_BASE_URL}/api/admin/people${queryString ? '?' + queryString : ''}`;

	let people: PersonListItem[] = [];

	try {
		const res = await fetch(apiUrl, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});

		if (res.ok) {
			people = await res.json();
		} else {
			console.error('[people load] FastAPI returned', res.status);
		}
	} catch (err) {
		console.error('[people load] fetch threw:', err instanceof Error ? err.message : String(err));
	}

	return { people, incomplete, tenure_gaps };
};
