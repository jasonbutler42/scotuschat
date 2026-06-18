import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

interface ParticipantItem {
	person_id: number;
	full_name: string;
	role_name: string | null;
}

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

	// Fetch all people for the HIT-row Change typeahead (Gap 1b — Plan 07-07).
	// On non-OK, default to [] so the job view still renders.
	let people: Array<{ id: number; full_name: string; role_name: string | null }> = [];
	let peopleLoadError: string | null = null;
	try {
		const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (peopleRes.ok) {
			people = await peopleRes.json();
		} else {
			peopleLoadError = `GET /api/admin/people returned ${peopleRes.status}`;
			console.error('[load] people fetch failed:', peopleLoadError);
		}
	} catch (err) {
		// Non-critical — degrade gracefully; typeahead will fall back to row.candidates
		peopleLoadError = err instanceof Error ? err.message : String(err);
		console.error('[load] people fetch threw:', peopleLoadError);
	}

	// Fetch resolved participants when the job is completed and has an argument (PEOPLE-04, D-02).
	// Only fetches when status === 'completed' and argument_id is set — otherwise defaults to [].
	// Degrades gracefully on any error so the existing page is never broken by this addition.
	let participants: ParticipantItem[] = [];
	if (job.status === 'completed' && job.argument_id != null) {
		try {
			const participantsRes = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/participants`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (participantsRes.ok) {
				participants = await participantsRes.json();
			} else {
				console.error(
					`[load] participants fetch failed: GET /api/admin/jobs/${params.job_id}/participants returned ${participantsRes.status}`,
				);
			}
		} catch (err) {
			// Non-critical — degrade to [] so the page still renders without the participant section
			console.error('[load] participants fetch threw:', err instanceof Error ? err.message : String(err));
		}
	}

	return { job, people, peopleLoadError, participants };
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
		// Attach role_name from form data — the API returns PersonResponse which reads
		// role_name from the ORM object, but Person.role_name is not an ORM column (only
		// role_id is). Enrich with the form value so the Svelte typeahead shows "Name (Role)".
		const enrichedPerson = {
			...person,
			role_name: person.role_name ?? (role_name.trim() || null),
		};
		// Return the created person so the Svelte component can add them to the dropdown.
		return { personCreated: true, person: enrichedPerson };
	},
};
