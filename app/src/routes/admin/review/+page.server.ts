import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type ReviewQueueConstituent = {
	participant_id: number;
	person_id: number | null;
	display_name: string;
	side: string;
	review_state: string;
	has_open_discrepancy: boolean;
};

type ReviewQueueArgumentItem = {
	id: number;
	case_name: string;
	docket_number: string;
	argued_date: string | null;
	status: string;
	trust_tier: string;
	attention_count: number;
	admin_job_id: number | null;
	constituents: ReviewQueueConstituent[];
};

export const load: PageServerLoad = async ({ fetch }) => {
	let items: ReviewQueueArgumentItem[] = [];

	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/review/arguments`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});

		if (res.ok) {
			items = await res.json();
		} else {
			console.error('[review load] FastAPI returned', res.status);
		}
	} catch (err) {
		console.error('[review load] fetch threw:', err instanceof Error ? err.message : String(err));
	}

	return { items };
};

export const actions: Actions = {
	/**
	 * confirm — PATCH /api/admin/review/participants/{participant_id} with
	 * {"action": "confirm"}. Mirrors the arguments list page's publish/
	 * unpublish actions: on ANY non-2xx response or a thrown fetch, returns
	 * fail(...) and never redirects; on success, redirects back to
	 * /admin/review so the confirmed row drops off the queue.
	 *
	 * Only applies to a constituent flagged via the needs_review leg
	 * (review_state === 'needs_review') — +page.svelte renders the Confirm
	 * button only for those, and the API's own guard rejects a confirm on
	 * a person_id-IS-NULL participant with a 422 as defense-in-depth
	 * (tracer feedback gate defect 2). An unresolved (person_id === null)
	 * constituent has no Confirm button at all; it instead gets a
	 * "Resolve speaker" link to /admin/pipeline/{admin_job_id} (falling
	 * back to /admin/arguments/{argument_id} when unlinked), which is
	 * where the real person-search/assign/create flow lives. Clearing an
	 * unresolved row via Confirm is plan 49-04's "confirm as
	 * unattributable" action, not this one.
	 */
	confirm: async ({ request, fetch }) => {
		const formData = await request.formData();
		const participant_id = formData.get('participant_id') as string;

		let res: Response;
		try {
			res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/review/participants/${participant_id}`,
				{
					method: 'PATCH',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ action: 'confirm' }),
				},
			);
		} catch {
			return fail(502, { error: 'Could not confirm this participant. Try again.' });
		}

		if (!res.ok) {
			const payload: unknown = await res.json().catch(() => null);
			const detail = (payload as { detail?: unknown } | null)?.detail;
			if (typeof detail === 'string' && detail.length > 0) {
				return fail(res.status, { error: detail });
			}
			return fail(res.status, { error: 'Could not confirm this participant. Try again.' });
		}

		throw redirect(303, '/admin/review');
	},
};
