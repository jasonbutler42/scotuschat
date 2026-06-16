import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	// Fetch the specific job from the admin jobs endpoint.
	// X-Admin-Token is required for all SvelteKit → FastAPI calls.
	const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
		headers: { 'X-Admin-Token': ADMIN_TOKEN },
	});

	if (res.status === 404) {
		throw error(404, 'Run not found');
	}

	if (!res.ok) {
		throw error(502, 'Could not load run details');
	}

	const job = await res.json();
	return { job };
};

export const actions: Actions = {
	/**
	 * resolve — post the operator-dispositioned discrepancy matches to FastAPI.
	 * The hidden `matches` field carries a JSON array of { raw_speaker_label, person_id }.
	 * On non-OK: return fail(422) so the job stays paused and the operator can retry (Pitfall 5).
	 */
	resolve: async ({ request, params }) => {
		const data = await request.formData();
		const matchesRaw = (data.get('matches') as string) ?? '[]';

		let matches: Array<{ raw_speaker_label: string; person_id: number }>;
		try {
			matches = JSON.parse(matchesRaw);
		} catch {
			return fail(422, { error: 'Invalid matches data. Please try again.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/resolve`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ matches }),
			});
		} catch {
			return fail(422, { error: 'Could not save the review. Check your selections and try again.' });
		}

		if (!res.ok) {
			// Non-OK leaves the job paused so the operator can retry (Pitfall 5).
			return fail(422, { error: 'Could not save the review. Check your selections and try again.' });
		}

		return { success: true };
	},

	/**
	 * addPerson — create a new person inline during discrepancy review (D-13).
	 * Accepts full_name and role_name from formData.
	 * On success: returns the created person { id, full_name } for client-side dropdown update.
	 */
	addPerson: async ({ request, params }) => {
		const data = await request.formData();
		const full_name = (data.get('full_name') as string) ?? '';
		const role_name = (data.get('role_name') as string) ?? '';

		if (!full_name.trim()) {
			return fail(400, { error: 'Full name is required.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/people`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ full_name: full_name.trim(), role_name: role_name.trim() || null }),
			});
		} catch {
			return fail(400, { error: 'Could not create person. Please try again.' });
		}

		if (!res.ok) {
			return fail(400, { error: 'Could not create person. Please try again.' });
		}

		const person = await res.json();
		// Return the created person so the Svelte component can add them to the dropdown.
		return { personCreated: true, person };
	},
};
