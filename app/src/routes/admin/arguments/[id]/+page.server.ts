import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type ConsolidatedDocket = {
	docket_number: string;
};

type ArgumentDetail = {
	id: number;
	argued_date: string | null;
	case_name: string;
	docket_number: string;
	resolved_at: string | null;
	published_at: string | null;
	slug: string;
	consolidated_dockets: ConsolidatedDocket[];
};

export const load: PageServerLoad = async ({ fetch, params }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
		headers: { 'X-Admin-Token': ADMIN_TOKEN },
	});

	if (res.status === 404) {
		throw error(404, 'Argument not found');
	}

	if (!res.ok) {
		throw error(502, 'Could not load argument');
	}

	const argument: ArgumentDetail = await res.json();

	return { argument };
};

export const actions: Actions = {
	/**
	 * save — PATCH /api/admin/arguments/{id} with the three editable fields.
	 * On slug_collision 422, surface the UI-SPEC error copy (D-11).
	 * On success, redirect re-runs load returning fresh data.
	 */
	save: async ({ request, params, fetch }) => {
		const formData = await request.formData();

		const case_name = ((formData.get('case_name') as string) ?? '').trim();
		const docket_number = ((formData.get('docket_number') as string) ?? '').trim();
		const argued_date_raw = ((formData.get('argued_date') as string) ?? '').trim();
		const argued_date = argued_date_raw || null;

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ case_name, docket_number, argued_date }),
			});
		} catch {
			return fail(502, { error: 'Could not save changes. Check your inputs and try again.' });
		}

		if (!res.ok) {
			let detail = '';
			try {
				const body = await res.json();
				detail = typeof body.detail === 'string' ? body.detail : '';
			} catch {
				// ignore parse error
			}

			if (res.status === 422 && detail.includes('slug_collision')) {
				return fail(422, {
					error:
						'This title generates a URL slug that conflicts with an existing case. Choose a different title.',
				});
			}

			if (res.status === 422 && detail.includes('docket_collision')) {
				return fail(422, {
					error: 'That docket number is already used by another case. Choose a different docket.',
				});
			}

			return fail(422, { error: 'Could not save changes. Check your inputs and try again.' });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},

	/**
	 * publish — POST /api/admin/arguments/{id}/publish.
	 * Backend enforces resolved_at IS NOT NULL (T-11-PUBGATE); UI gating is defense-in-depth.
	 */
	publish: async ({ params, fetch }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/publish`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { error: 'Could not publish this argument. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { error: 'Could not publish this argument. Try again.' });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},

	/**
	 * unpublish — POST /api/admin/arguments/{id}/unpublish.
	 */
	unpublish: async ({ params, fetch }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/unpublish`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { error: 'Could not unpublish this argument. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { error: 'Could not unpublish this argument. Try again.' });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},
};
