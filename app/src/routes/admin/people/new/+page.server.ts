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
 */
interface BlankPerson {
	id: null;
	full_name: string;
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
		full_name: '',
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
	 * (D-09, Plan 27-03) after the D-08 minimum-required validation (full
	 * name + an explicit Bench/Advocate choice), then redirect into the
	 * freshly-created person's editor (identical redirect-after-create idiom
	 * to the [id] editor's `merge` action — `redirect(303, '/admin/people/' + id)`).
	 *
	 * tenures/bio_text/photo_url/birthdate are intentionally NOT sent here
	 * (D-08) — they are filled in on the editor after redirect via the
	 * existing `save`/`photo` actions on `/admin/people/[id]`.
	 */
	create: async ({ request, fetch }) => {
		const formData = await request.formData();

		const full_name = ((formData.get('full_name') as string) ?? '').trim();
		const isJusticeRaw = formData.get('is_justice') as string | null;

		if (!full_name) {
			return fail(400, { error: 'Full name is required.' });
		}

		if (isJusticeRaw !== 'true' && isJusticeRaw !== 'false') {
			return fail(400, { error: 'Choose Bench or Advocate to continue.' });
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
				body: JSON.stringify({ full_name, is_justice }),
			});
		} catch {
			return fail(502, { error: 'Could not create person. Check the form and try again.' });
		}

		if (!res.ok) {
			return fail(422, { error: 'Could not create person. Check the form and try again.' });
		}

		const created: { id: number } = await res.json();

		// Redirect into the new person's editor — re-runs that route's load()
		// with fresh data, matching the [id] editor's merge-action idiom.
		throw redirect(303, '/admin/people/' + created.id);
	},
};
