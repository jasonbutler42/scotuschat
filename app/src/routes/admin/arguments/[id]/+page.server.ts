import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type ConsolidatedDocket = {
	docket_number: string;
};

type AdvocateParticipant = {
	participant_id: number;
	person_id: number;
	full_name: string;
	side: string;
};

type TenureGapWarning = {
	person_id: number;
	full_name: string;
	argued_date: string;
};

type StatusLogEntry = {
	status: string;
	created_at: string;
};

type SpeakerRow = {
	participant_id: number;
	person_id: number | null;
	full_name: string | null;
	side: string;
	is_bench: boolean;
	argument_role: string | null;
	title: string | null;
	title_hint: string | null;
	utterance_count: number;
	bench_role: string | null;
	missing_tenure: boolean;
	person_edit_href: string | null;
};

type ArgumentDetail = {
	id: number;
	argued_date: string | null;
	case_name: string;
	docket_number: string;
	resolved_at: string | null;
	published_at: string | null;
	status: string;
	slug: string;
	consolidated_dockets: ConsolidatedDocket[];
	participants: AdvocateParticipant[];
	tenure_gap_warnings: TenureGapWarning[];
	status_log: StatusLogEntry[];
	speakers: SpeakerRow[];
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

	// can_delete: server-side gate — derived from already-loaded argument data (D-05).
	// No extra API call needed; argument.status is in the ArgumentDetail response.
	// Only Draft arguments can be deleted (D-03 / AEDIT-09) — Published and Unpublished
	// are both blocked (T-21-01-PUB, T-26-11, Pitfall 4).
	const can_delete = argument.status === 'draft';

	return { argument, can_delete };
};

export const actions: Actions = {
	/**
	 * updateParticipantSide — PATCH /api/admin/arguments/{id}/participants/{participant_id}
	 * with { side }. Isolated to this argument only (ROLE-03, IDOR guard T-15-04-IDOR).
	 * On success, redirects to reload the page with fresh data.
	 */
	updateParticipantSide: async ({ request, params, fetch }) => {
		const formData = await request.formData();
		const participant_id = ((formData.get('participant_id') as string) ?? '').trim();
		const side = ((formData.get('side') as string) ?? '').trim();
		const title = (formData.get('title') as string) ?? '';

		let res: Response;
		try {
			res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/participants/${participant_id}`,
				{
					method: 'PATCH',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ side, title }),
				},
			);
		} catch {
			return fail(502, { roleError: 'Could not save role. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { roleError: 'Could not save role. Try again.' });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},

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

	/**
	 * delete — DELETE /api/admin/arguments/{id}.
	 * Server-side: only unpublished arguments can be deleted (T-21-01-PUB).
	 * On 409 (published): return fail with error copy (server already blocks; copy is fine).
	 * On success: redirect to /admin/arguments (D-06).
	 * Auth: X-Admin-Token header passed server-side; never exposed to client (CLAUDE.md).
	 */
	delete: async ({ params, fetch }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
				method: 'DELETE',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { deleteError: 'Could not delete argument. Try again.' });
		}

		if (!res.ok) {
			if (res.status === 409) {
				return fail(409, {
					deleteError:
						'Published and unpublished arguments cannot be deleted. Only drafts can be removed.',
				});
			}
			return fail(502, { deleteError: 'Could not delete argument. Try again.' });
		}

		throw redirect(303, '/admin/arguments');
	},
};
