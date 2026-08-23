import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

/**
 * Blank person shape returned by load() — matches the fields the shared
 * [id]/+page.svelte editor template expects (D-07). `id` is null and
 * `is_justice` is null so neither Bench nor Advocate is pre-selected on
 * first render. This route has no `merge`/`delete` actions (Merge/Delete
 * only apply to a person that already exists — PEDIT-11/PEDIT-12), so
 * `load()` does not return the `people`/`can_delete`/`delete_block_count`
 * fields the [id] route needs for those cards.
 *
 * Phase 38 (D-01, D-02): `full_name` is no longer part of this shape at
 * all — Full Name is a generated, read-only preview computed client-side
 * from name parts (app/src/lib/personNames.ts) and is never client-owned
 * data, so there is nothing to preload here. A brand-new person also has
 * no extraction provenance yet (review_state/provenance_metadata, Phase 49
 * D-08, are only meaningful once a person row exists — see the [id] route).
 */
interface BlankPerson {
	id: null;
	bio_text: string | null;
	photo_url: string | null;
	photo_url_full: string | null;
	first_name: string | null;
	last_name: string | null;
	middle_name: string | null;
	name_suffix: string | null;
	is_justice: boolean | null;
}

export const load: PageServerLoad = async () => {
	const person: BlankPerson = {
		id: null,
		bio_text: null,
		photo_url: null,
		photo_url_full: null,
		first_name: null,
		last_name: null,
		middle_name: null,
		name_suffix: null,
		is_justice: null,
	};

	return { person };
};

export const actions: Actions = {
	/**
	 * create — POST a new person to the general, unscoped create endpoint
	 * (D-09, Plan 27-03) after the D-08/D-09 minimum-required validation (at
	 * least a first or last name, plus an explicit Bench/Advocate choice),
	 * then redirect into the freshly-created person's editor (identical
	 * redirect-after-create idiom to the [id] editor's `merge` action —
	 * `redirect(303, '/admin/people/' + id)`).
	 *
	 * Phase 38 (D-01, D-02, D-09, T-38-16): `full_name` is no longer read
	 * from the form or sent to FastAPI at all — PersonCreateRequest does not
	 * even declare that field (`extra="forbid"`, api/schemas/admin_people.py),
	 * so posting one would now be a 422. Full Name is generated server-side
	 * from first_name/middle_name/last_name/name_suffix via the shared
	 * api.domain.person_names.prepare_person_name helper; this action's own
	 * minimum-data guard (at least one of first_name/last_name) mirrors that
	 * same D-09 invariant client-side so the operator gets the exact locked
	 * copy ("Enter at least a first or last name.") with attempted values
	 * preserved and a focus path, rather than a generic 422 message.
	 *
	 * Every fail() below returns the attempted first/middle/last/suffix so
	 * the +page.svelte template can restore exactly what the operator typed
	 * (D-16-style preserved-attempt discipline) — this route has no prior
	 * "data.person" values to fall back to (it is always a blank form), so
	 * losing attempted input on a failed submit would silently discard it.
	 */
	create: async ({ request, fetch }) => {
		const formData = await request.formData();

		const isJusticeRaw = formData.get('is_justice') as string | null;
		const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
		const middle_name = ((formData.get('middle_name') as string) ?? '').trim() || null;
		const last_name = ((formData.get('last_name') as string) ?? '').trim() || null;
		const name_suffix = ((formData.get('name_suffix') as string) ?? '').trim() || null;

		if (!first_name && !last_name) {
			return fail(400, {
				error: 'Enter at least a first or last name.',
				first_name, middle_name, last_name, name_suffix,
			});
		}

		if (isJusticeRaw !== 'true' && isJusticeRaw !== 'false') {
			return fail(400, {
				error: 'Choose Bench or Advocate to continue.',
				first_name, middle_name, last_name, name_suffix,
			});
		}

		const is_justice = isJusticeRaw === 'true';

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					is_justice,
					first_name, middle_name, last_name, name_suffix,
				}),
			});
		} catch {
			return fail(502, {
				error: 'Could not create person. Check the form and try again.',
				first_name, middle_name, last_name, name_suffix,
			});
		}

		if (!res.ok) {
			return fail(422, {
				error: 'Could not create person. Check the form and try again.',
				first_name, middle_name, last_name, name_suffix,
			});
		}

		const created: { id: number } = await res.json();

		// Redirect into the new person's editor — re-runs that route's load()
		// with fresh data, matching the [id] editor's merge-action idiom.
		throw redirect(303, '/admin/people/' + created.id);
	},
};
