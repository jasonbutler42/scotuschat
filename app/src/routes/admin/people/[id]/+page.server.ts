import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

interface TenureRowClient {
	_key: number;
	id?: number;
	// office (D-01..D-17, Phase 37) replaces the old free-text seat field.
	// Typed as a plain string here (not the canonical Literal) because this is
	// the client-submitted shape before this action's own allowlisted
	// validation runs below — an invalid/blank client value must be rejected
	// with fail(400), never coerced or silently dropped (D-11).
	office: string;
	start_date: string;
	end_date: string;
	appointed_by: string;
	appointing_president_party: string;
	// reason_left (Phase 39, D-01, D-09) — '' means no reason selected/unset.
	reason_left: string;
}

interface PersonDetail {
	id: number;
	full_name: string;
	bio_text: string | null;
	photo_url: string | null;
	photo_url_full: string | null;
	birthdate: string | null;
	// Phase 39 addition — migration 0023 (PUB-04); mirrors birthdate exactly.
	death_date: string | null;
	tenures: Array<{
		office: string | null;
		start_date: string | null;
		end_date: string | null;
		appointed_by: string | null;
		appointing_president_party: string | null;
		reason_left: string | null;
	}>;
	// Phase 9 additions
	first_name: string | null;
	last_name: string | null;
	middle_name: string | null;
	name_suffix: string | null;
	// Phase 22 — migration 0013: appointment fields removed from person (PEDIT-10)
	// Phase 18 addition
	is_justice: boolean;
	// Phase 38 additions (D-12, D-14, D-15, D-18): name_needs_review drives the
	// People directory's "Name review" attention state (not used on this page
	// directly, but part of the same PersonDetail response shape);
	// name_extraction_metadata is the single whole-record provenance envelope
	// this page's per-part extracted-value hints read from — one shared
	// {confidence, raw} pair rendered independently beneath each of the four
	// name-part fields (D-15, D-19), since the backend does not persist a
	// separate guessed value per part.
	name_needs_review: boolean;
	name_extraction_metadata: {
		source: string | null;
		raw: string | null;
		confidence: 'High' | 'Medium' | 'Low' | null;
		reason: string | null;
		auto_applied: boolean | null;
	} | null;
}

interface PersonListItem {
	id: number;
	full_name: string;
	last_name: string | null;
	first_name: string | null;
}

interface MergePreviewCounts {
	utterances: number;
	aliases: number;
	appearances: number;
	argument_participants: number;
	tenures: number;
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

	// Fetch the people list to build the merge target picker (all persons except
	// the current one). The Role dropdown this list previously fed was removed (D-10).
	let people: PersonListItem[] = [];
	try {
		const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (peopleRes.ok) {
			const all: PersonListItem[] = await peopleRes.json();
			people = all.filter((p) => p.id !== parseInt(params.id, 10));
		}
	} catch {
		// Non-critical — degrade gracefully; merge picker will be empty
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
				counts.argument_participants === 0 &&
				counts.tenures === 0;
			delete_block_count =
				counts.utterances + counts.appearances + counts.argument_participants + counts.tenures;
		}
	} catch {
		// Degrade gracefully: can_delete stays false (safe default), delete_block_count stays 0
	}

	return { person, people, can_delete, delete_block_count };
};

export const actions: Actions = {
	/**
	 * save — PATCH the person with name/birthdate/tenure/appointment fields and redirect on success.
	 *
	 * The `tenures` form field carries a JSON-serialized array (Pitfall 3 —
	 * hidden JSON field strategy). The _key client-side field is stripped before
	 * sending to FastAPI. The person-level Role field and its inline-creation
	 * machinery were removed entirely (D-10) — there is no `role_id` anywhere
	 * in this action.
	 *
	 * Phase 38 (D-01, D-02, D-09, T-38-16): `full_name` is no longer read from
	 * the form or sent to FastAPI at all — PersonUpdate does not even declare
	 * that field (`extra="forbid"`, api/schemas/admin_people.py), so posting
	 * one would now be a 422. Full Name is generated server-side from the
	 * submitted name parts via the shared prepare_person_name helper. This
	 * action's own minimum-data guard (at least one of first_name/last_name)
	 * mirrors that same D-09 invariant client-side, returning the exact
	 * locked copy ("Enter at least a first or last name.") with every
	 * attempted value preserved and a focus path, rather than a generic 422.
	 *
	 * NOTE: bio_text and photo_url are intentionally NOT sent in this action's PATCH body
	 * (Pitfall 7 extended). Both are managed exclusively by the `photo` action. The Bio &
	 * Photo card is a single form so bio saves together with photo on every photo action submit.
	 */
	save: async ({ request, params, fetch }) => {
		const formData = await request.formData();

		// bio_text intentionally omitted — managed exclusively by the photo action (Pitfall 7 extended)
		// photo_url intentionally omitted — managed exclusively by the photo action (Pitfall 7)
		const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
		const last_name = ((formData.get('last_name') as string) ?? '').trim() || null;
		const middle_name = ((formData.get('middle_name') as string) ?? '').trim() || null;
		const name_suffix = ((formData.get('name_suffix') as string) ?? '').trim() || null;
		const birthdate = ((formData.get('birthdate') as string) ?? '').trim() || null;
		const death_date = ((formData.get('death_date') as string) ?? '').trim() || null;
		// The Bench/Advocate segmented toggle always submits a hidden 'true'/'false'
		// value, unlike the old checkbox which was absent from FormData when unchecked.
		const is_justice = formData.get('is_justice') === 'true';
		const tenuresRaw = (formData.get('tenures') as string) ?? '[]';

		let tenuresParsed: TenureRowClient[];
		try {
			tenuresParsed = JSON.parse(tenuresRaw);
		} catch {
			// Every fail() below restores the full submitted profile state
			// (D-12, D-16) so a failed save never silently erases unsaved
			// edits elsewhere on the form.
			return fail(422, {
				error: 'Invalid tenure data. Please try again.',
				first_name, last_name, middle_name, name_suffix, birthdate, death_date, is_justice,
				tenures: [] as { office: string; start_date: string; end_date: string; appointed_by: string; appointing_president_party: string; reason_left: string }[],
			});
		}

		// Strip the client-only _key field before sending to FastAPI. reason_left
		// (Phase 39, D-01, D-09) is part of TenureRowClient's state now — a
		// constrained enum, normalized to null when unselected — and is included
		// in this mapping like every other tenure field.
		const tenures = tenuresParsed.map(({ office, start_date, end_date, appointed_by, appointing_president_party, reason_left }) => ({
			office,
			start_date,
			end_date,
			appointed_by,
			appointing_president_party,
			reason_left: reason_left || null,
		}));

		if (!first_name && !last_name) {
			return fail(400, {
				error: 'Enter at least a first or last name.',
				first_name, last_name, middle_name, name_suffix, birthdate, death_date, is_justice,
				tenures,
			});
		}

		// Every row must carry a canonical office before this action ever calls
		// FastAPI — an unresolved/invalid Office selection blocks the entire
		// profile save atomically; never a partial request (T-37-10, D-11).
		const firstInvalidIndex = tenures.findIndex(
			(t) => t.office !== 'chief' && t.office !== 'associate'
		);
		if (firstInvalidIndex !== -1) {
			return fail(400, {
				error: 'Select Chief or Associate for every tenure period before saving.',
				first_name, last_name, middle_name, name_suffix, birthdate, death_date, is_justice,
				tenures,
			});
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					tenures,
					first_name, last_name, middle_name, name_suffix,
					is_justice, birthdate, death_date,
					// bio_text omitted intentionally — managed by photo action (Pitfall 7 extended)
					// photo_url omitted intentionally — managed by photo action (Pitfall 7)
				}),
			});
		} catch {
			return fail(502, {
				error: 'Could not save changes. Check the form and try again.',
				first_name, last_name, middle_name, name_suffix, birthdate, death_date, is_justice,
				tenures,
			});
		}

		if (!res.ok) {
			return fail(422, {
				error: 'Could not save changes. Check the form and try again.',
				first_name, last_name, middle_name, name_suffix, birthdate, death_date, is_justice,
				tenures,
			});
		}

		// Redirect re-runs the load function, returning fresh data (no stale state)
		throw redirect(303, '/admin/people/' + params.id);
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
