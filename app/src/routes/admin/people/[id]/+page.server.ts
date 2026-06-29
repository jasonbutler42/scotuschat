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
	photo_url_full: string | null;
	tenures: Array<{
		seat: string | null;
		start_date: string | null;
		end_date: string | null;
	}>;
	// Phase 9 additions
	first_name: string | null;
	last_name: string | null;
	middle_name: string | null;
	name_suffix: string | null;
	appointing_president: string | null;
	appointing_president_party: string | null;
	// Phase 18 addition
	is_justice: boolean;
}

interface PersonListItem {
	id: number;
	full_name: string;
	last_name: string | null;
	first_name: string | null;
	role_id: number | null;
	role_name: string | null;
}

interface RoleItem {
	id: number;
	name: string;
}

interface MergePreviewCounts {
	utterances: number;
	aliases: number;
	appearances: number;
	argument_participants: number;
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

	// Reconstruct full photo URL server-side (Pitfall 5):
	// FASTAPI_BASE_URL is server-only — pass the full URL to the client via photo_url_full.
	if (person.photo_url && person.photo_url.startsWith('/')) {
		person.photo_url_full = FASTAPI_BASE_URL + person.photo_url;
	} else {
		// Already a full https:// URL, or null
		person.photo_url_full = person.photo_url ?? null;
	}

	// Fetch the people list for two purposes:
	//   1. De-duplicate roles for the role dropdown
	//   2. Build the merge target picker (all persons except the current one)
	let roles: RoleItem[] = [];
	let people: PersonListItem[] = [];
	try {
		const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (peopleRes.ok) {
			const all: PersonListItem[] = await peopleRes.json();

			// Merge picker: exclude the current person
			people = all.filter((p) => p.id !== parseInt(params.id, 10));

			// Roles dedup: keep only items with non-null role_id
			const seen = new Set<number>();
			for (const p of all) {
				if (p.role_id !== null && p.role_name !== null && !seen.has(p.role_id)) {
					seen.add(p.role_id);
					roles.push({ id: p.role_id, name: p.role_name! });
				}
			}
			// Sort alphabetically by name for consistent dropdown ordering
			roles.sort((a, b) => a.name.localeCompare(b.name));
		}
	} catch {
		// Non-critical — degrade gracefully; role dropdown and merge picker will be empty
	}

	// Derive can_delete and delete_block_count from the merge-preview endpoint
	// (target_id=0 is ignored server-side; counts reflect source FKs only, D-09).
	let can_delete = false;
	let delete_block_count = 0;
	try {
		const previewRes = await fetch(
			`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/merge-preview?target_id=0`,
			{ headers: { 'X-Admin-Token': ADMIN_TOKEN } }
		);
		if (previewRes.ok) {
			const counts: MergePreviewCounts = await previewRes.json();
			can_delete =
				counts.utterances === 0 &&
				counts.appearances === 0 &&
				counts.argument_participants === 0;
			delete_block_count = counts.utterances + counts.appearances + counts.argument_participants;
		}
	} catch {
		// Degrade gracefully: can_delete stays false (safe default), delete_block_count stays 0
	}

	return { person, roles, people, can_delete, delete_block_count };
};

export const actions: Actions = {
	/**
	 * save — PATCH the person with name/role/tenure/appointment fields and redirect on success.
	 *
	 * The `tenures` form field carries a JSON-serialized array (Pitfall 3 —
	 * hidden JSON field strategy). The _key client-side field is stripped before
	 * sending to FastAPI. Empty role_id converts to null (Open Question 2).
	 *
	 * NOTE: bio_text and photo_url are intentionally NOT sent in this action's PATCH body
	 * (Pitfall 7 extended). Both are managed exclusively by the `photo` action. The Bio &
	 * Photo card is a single form so bio saves together with photo on every photo action submit.
	 */
	save: async ({ request, params, fetch }) => {
		const formData = await request.formData();

		const full_name = ((formData.get('full_name') as string) ?? '').trim();
		const role_id_raw = formData.get('role_id') as string | null;
		const role_id = role_id_raw ? parseInt(role_id_raw, 10) : null;
		if (role_id_raw && isNaN(role_id as number)) {
			return fail(400, { error: 'Please select a valid role or complete the new-role form before saving.' });
		}
		// bio_text intentionally omitted — managed exclusively by the photo action (Pitfall 7 extended)
		// photo_url intentionally omitted — managed exclusively by the photo action (Pitfall 7)
		const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
		const last_name = ((formData.get('last_name') as string) ?? '').trim() || null;
		const middle_name = ((formData.get('middle_name') as string) ?? '').trim() || null;
		const name_suffix = ((formData.get('name_suffix') as string) ?? '').trim() || null;
		const appointing_president = ((formData.get('appointing_president') as string) ?? '').trim() || null;
		const appointing_president_party = ((formData.get('appointing_president_party') as string) ?? '').trim() || null;
		// Checkbox submits 'on' when checked; absent from FormData when unchecked (D-04)
		const is_justice = formData.get('is_justice') === 'on';
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
				body: JSON.stringify({
					full_name, role_id, tenures,
					first_name, last_name, middle_name, name_suffix,
					appointing_president, appointing_president_party,
					is_justice,
					// bio_text omitted intentionally — managed by photo action (Pitfall 7 extended)
					// photo_url omitted intentionally — managed by photo action (Pitfall 7)
				}),
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

	/**
	 * photo — Save bio_text and forward photo to FastAPI POST /api/admin/people/{id}/photo.
	 *
	 * This action handles both bio_text and photo because the Bio & Photo section is
	 * a single card with a single form (Pitfall 7 extended — bio_text excluded from save).
	 *
	 * bio_text is saved via a PATCH request before the photo fetch. This is best-effort:
	 * a failed bio save is not surfaced as an error (consistent with how save action works).
	 *
	 * CRITICAL: Do NOT set Content-Type header on the photo fetch — Node fetch sets the
	 * multipart boundary automatically when body is FormData (Pitfall 4).
	 *
	 * Accepts either a file upload (photo_file) or a URL (photo_url).
	 * On success, redirects to the person's edit page to re-run load with fresh data.
	 */
	photo: async ({ request, params, fetch }) => {
		const formData = await request.formData();
		const bio_text = (formData.get('bio_text') as string | null)?.trim() ?? null;
		const photoFile = formData.get('photo_file') as File | null;
		const photoUrl = (formData.get('photo_url') as string | null)?.trim() || null;

		// Best-effort bio save — always run before photo, ignore response (Pitfall 7 extended)
		await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
			method: 'PATCH',
			headers: {
				'Content-Type': 'application/json',
				'X-Admin-Token': ADMIN_TOKEN,
			},
			body: JSON.stringify({ bio_text: bio_text }),
		}).catch(() => {
			// Non-critical — bio save failure does not block photo save
		});

		const outForm = new FormData();
		if (photoFile && photoFile.size > 0) {
			outForm.append('photo_file', photoFile, photoFile.name);
		}
		if (photoUrl) {
			outForm.append('photo_url', photoUrl);
		}

		// If neither a file nor a URL was provided, bio-only save — skip photo upload
		if (!outForm.has('photo_file') && !outForm.has('photo_url')) {
			throw redirect(303, '/admin/people/' + params.id);
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/photo`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
				// DO NOT set Content-Type — fetch sets the multipart boundary automatically
				body: outForm,
			});
		} catch {
			return fail(502, { photoError: 'Photo could not be saved. Try again.' });
		}

		if (!res.ok) {
			if (res.status === 422) {
				return fail(422, {
					photoError: 'The uploaded file is not a valid image. Please upload a JPG, PNG, or WebP file.',
				});
			}
			return fail(502, { photoError: 'Photo could not be saved. Try again.' });
		}

		throw redirect(303, '/admin/people/' + params.id);
	},

	/**
	 * merge — POST to FastAPI to transfer all FK rows from the current person
	 * (source) to the chosen target, then delete the source.
	 *
	 * On success, redirects to the target person's edit page (D-11 — source no
	 * longer exists after merge).
	 */
	merge: async ({ request, params, fetch }) => {
		const formData = await request.formData();
		const target_id = formData.get('target_id') as string | null;

		if (!target_id) {
			return fail(400, { mergeError: 'Select a target person.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/merge`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ target_id: parseInt(target_id, 10) }),
			});
		} catch {
			return fail(502, { mergeError: 'Merge failed. Please try again.' });
		}

		if (!res.ok) {
			const detail = await res.json().catch(() => ({}));
			return fail(res.status === 422 ? 422 : 502, {
				mergeError: (detail as { detail?: string }).detail ?? 'Merge failed. Please try again.',
			});
		}

		// Redirect to target — source person no longer exists (D-11)
		throw redirect(303, '/admin/people/' + target_id);
	},

	/**
	 * delete — DELETE the current person if they are an orphan (no FK rows).
	 *
	 * The FastAPI endpoint enforces orphan status server-side (D-06).
	 * The client-side disabled button is defense-in-depth only.
	 *
	 * On success, redirects to the people directory (D-07).
	 */
	delete: async ({ params, fetch }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
				method: 'DELETE',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { deleteError: 'Delete failed. Please try again.' });
		}

		if (!res.ok) {
			if (res.status === 409) {
				return fail(409, {
					deleteError: 'This person cannot be deleted — they have associated records.',
				});
			}
			return fail(502, { deleteError: 'Delete failed. Please try again.' });
		}

		// Redirect to people list — person no longer exists (D-07)
		throw redirect(303, '/admin/people');
	},
};
