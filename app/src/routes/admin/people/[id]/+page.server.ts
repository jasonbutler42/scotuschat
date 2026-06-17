import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

interface TenureRowClient {
	_key: number;
	id?: number;
	seat: string;
	start_date: string;
	end_date: string;
}

interface PersonDetail {
	id: number;
	full_name: string;
	role_id: number | null;
	role_name: string | null;
	bio_text: string | null;
	photo_url: string | null;
	tenures: Array<{
		seat: string | null;
		start_date: string | null;
		end_date: string | null;
	}>;
}

interface PersonListItem {
	id: number;
	full_name: string;
	role_id: number | null;
	role_name: string | null;
}

interface RoleItem {
	id: number;
	name: string;
}

export const load: PageServerLoad = async ({ fetch, params }) => {
	// Fetch the person detail for the edit form.
	const personRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
		headers: { 'X-Admin-Token': ADMIN_TOKEN },
	});

	if (personRes.status === 404) {
		throw error(404, 'Person not found');
	}

	if (!personRes.ok) {
		throw error(502, 'Could not load person');
	}

	const person: PersonDetail = await personRes.json();

	// Fetch the people list to derive a de-duplicated roles list.
	// There is no dedicated GET /api/admin/roles endpoint; the people list
	// carries role_id + role_name and is the available source.
	let roles: RoleItem[] = [];
	try {
		const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (peopleRes.ok) {
			const people: PersonListItem[] = await peopleRes.json();
			// Dedupe by role_id — keep only items with non-null role_id
			const seen = new Set<number>();
			for (const p of people) {
				if (p.role_id !== null && p.role_name !== null && !seen.has(p.role_id)) {
					seen.add(p.role_id);
					roles.push({ id: p.role_id, name: p.role_name! });
				}
			}
			// Sort alphabetically by name for consistent dropdown ordering
			roles.sort((a, b) => a.name.localeCompare(b.name));
		}
	} catch {
		// Non-critical — degrade gracefully; role dropdown will be empty
	}

	return { person, roles };
};

export const actions: Actions = {
	/**
	 * save — PATCH the person with all form fields and redirect on success.
	 *
	 * The `tenures` form field carries a JSON-serialized array (Pitfall 3 —
	 * hidden JSON field strategy). The _key client-side field is stripped before
	 * sending to FastAPI. Empty role_id converts to null (Open Question 2).
	 */
	save: async ({ request, params, fetch }) => {
		const formData = await request.formData();

		const full_name = ((formData.get('full_name') as string) ?? '').trim();
		const role_id_raw = formData.get('role_id') as string | null;
		const role_id = role_id_raw ? parseInt(role_id_raw, 10) : null;
		const bio_text = ((formData.get('bio_text') as string) ?? '').trim() || null;
		const photo_url = ((formData.get('photo_url') as string) ?? '').trim() || null;
		const tenuresRaw = (formData.get('tenures') as string) ?? '[]';

		if (!full_name) {
			return fail(400, { error: 'Full name is required.' });
		}

		let tenuresParsed: TenureRowClient[];
		try {
			tenuresParsed = JSON.parse(tenuresRaw);
		} catch {
			return fail(422, { error: 'Invalid tenure data. Please try again.' });
		}

		// Strip the client-only _key field before sending to FastAPI
		const tenures = tenuresParsed.map(({ seat, start_date, end_date }) => ({
			seat,
			start_date,
			end_date,
		}));

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ full_name, role_id, bio_text, photo_url, tenures }),
			});
		} catch {
			return fail(502, { error: 'Could not save changes. Check the form and try again.' });
		}

		if (!res.ok) {
			return fail(422, { error: 'Could not save changes. Check the form and try again.' });
		}

		// Redirect re-runs the load function, returning fresh data (no stale state)
		throw redirect(303, '/admin/people/' + params.id);
	},

	/**
	 * createRole — POST to /api/admin/roles and return the new role.
	 *
	 * On success, returns { roleCreated: true, role } so the use:enhance callback
	 * can add the new role to the local dropdown without a page reload (Pattern 3).
	 * On error, returns fail(400, { roleError }) — kept separate from save errors
	 * to avoid polluting the main form's error state (Pitfall 4).
	 */
	createRole: async ({ request, fetch }) => {
		const formData = await request.formData();
		const name = ((formData.get('role_name') as string) ?? '').trim();

		if (!name) {
			return fail(400, { roleError: 'Role name is required.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/roles`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ name }),
			});
		} catch {
			return fail(400, { roleError: 'Could not create role. Try again.' });
		}

		if (!res.ok) {
			return fail(400, { roleError: 'Could not create role. Try again.' });
		}

		const role = await res.json();
		// Return roleCreated + role so the Svelte component can add it to the dropdown
		return { roleCreated: true, role };
	},
};
