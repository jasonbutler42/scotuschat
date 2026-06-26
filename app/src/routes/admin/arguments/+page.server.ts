import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type ArgumentListItem = {
	id: number;
	argued_date: string | null;
	case_name: string;
	docket_number: string;
	resolved_at: string | null;
	published_at: string | null;
	status: string;
};

export const load: PageServerLoad = async ({ fetch }) => {
	let args: ArgumentListItem[] = [];

	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});

		if (res.ok) {
			args = await res.json();
		} else {
			console.error('[arguments load] FastAPI returned', res.status);
		}
	} catch (err) {
		console.error(
			'[arguments load] fetch threw:',
			err instanceof Error ? err.message : String(err),
		);
	}

	return { arguments: args };
};

export const actions: Actions = {
	/**
	 * publish — POST to /api/admin/arguments/{id}/publish and redirect to list.
	 * Each row carries its own argument_id in a hidden input (Pitfall 6).
	 */
	publish: async ({ request, fetch }) => {
		const formData = await request.formData();
		const argument_id = formData.get('argument_id') as string;

		try {
			const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/publish`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
			if (!res.ok) {
				console.error('[arguments publish] FastAPI returned', res.status, await res.text());
			}
		} catch (err) {
			console.error('[arguments publish] fetch threw:', err instanceof Error ? err.message : String(err));
		}

		throw redirect(303, '/admin/arguments');
	},

	/**
	 * unpublish — POST to /api/admin/arguments/{id}/unpublish and redirect to list.
	 */
	unpublish: async ({ request, fetch }) => {
		const formData = await request.formData();
		const argument_id = formData.get('argument_id') as string;

		try {
			await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/unpublish`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch (err) {
			console.error('[arguments unpublish] fetch threw:', err instanceof Error ? err.message : String(err));
		}

		throw redirect(303, '/admin/arguments');
	},
};
