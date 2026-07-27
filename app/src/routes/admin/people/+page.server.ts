import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import type { PageServerLoad } from './$types';

type PersonListItem = {
	id: number;
	full_name: string;
	missing: string[];
	is_justice: boolean;
	argument_count: number | null;
	tenure_coverage: string | null;
	has_tenure_gap: boolean;
	// Phase 38 (D-12) — threaded through unchanged from the API response;
	// the directory's "Name review" pill/filter is driven by `missing`
	// already containing "name review" (see admin_people.py's
	// missing_filters allow-list), so this typed field is available to any
	// consumer that prefers an explicit boolean over array membership, but
	// is not itself required by the pill rendering below.
	name_needs_review: boolean;
};

export const load: PageServerLoad = async ({ fetch, url }) => {
	// tab (D-03): defaults to 'bench' when absent; strictly is_justice=true → Bench,
	// is_justice=false → Advocate (D-02).
	const tab = url.searchParams.get('tab') === 'advocate' ? 'advocate' : 'bench';
	const is_justice = tab === 'bench';
	// missing (D-04): single click-to-filter field name, replaces the removed
	// 'incomplete' toggle entirely.
	const missing = url.searchParams.get('missing');
	const tenure_gaps = url.searchParams.get('tenure_gaps') === '1';

	const params = new URLSearchParams();
	params.set('is_justice', String(is_justice));
	if (missing) params.set('missing', missing);
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

	return { people, tab, missing, tenure_gaps };
};
