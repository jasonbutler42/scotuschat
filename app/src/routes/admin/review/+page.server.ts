import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type DiscrepancyDetail = {
	id: number;
	field: string;
	existing_value: string | null;
	existing_source: string | null;
	existing_method: string | null;
	incoming_value: string | null;
	incoming_source: string | null;
	incoming_method: string | null;
	created_at: string;
};

type TierBlocker = { code: string; count: number };

type ReviewQueueConstituent = {
	participant_id: number;
	person_id: number | null;
	display_name: string;
	side: string;
	review_state: string;
	has_open_discrepancy: boolean;
	discrepancies: DiscrepancyDetail[];
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
	blockers: TierBlocker[];
	// Phase 50 plan 50-02 (PD-09): open value_discrepancy rows recorded
	// directly against this argument's own value columns or its lead
	// case's columns — distinct from constituents[].discrepancies, which
	// covers only argument_participant-level rows. Rendered by 50-04.
	argument_discrepancies: DiscrepancyDetail[];
};

type ReviewQueuePersonItem = {
	id: number;
	full_name: string;
	review_state: string;
	provenance_note: string;
	has_open_discrepancy: boolean;
	discrepancies: DiscrepancyDetail[];
};

/**
 * Full `/admin/review` load — extends plan 49-01's tracer with the full
 * Arguments|People tab pair and the three-axis filter set (D-02, D-07).
 * Every filter/tab is a full-page goto() round trip (no client-side
 * filter state, E3/loading) — this load reads whichever of tab/status/
 * tier/review_state are present in the URL and forwards them to whichever
 * FastAPI endpoint the active tab needs, then returns them alongside the
 * rows so the page can render the active-filter indicator and the correct
 * control states (aria-pressed / selected option) without re-deriving
 * anything from the fetch itself.
 *
 * Keeps the single try/catch + console.error + empty-list fallback shape
 * (E1/E2/error — the inherited admin load-failure precedent, including
 * its known weakness that a fetch failure is visually indistinguishable
 * from a genuinely empty queue).
 */
export const load: PageServerLoad = async ({ fetch, url }) => {
	const tab: 'arguments' | 'people' = url.searchParams.get('tab') === 'people' ? 'people' : 'arguments';
	const status = url.searchParams.get('status');
	const tier = url.searchParams.get('tier');
	const review_state = url.searchParams.get('review_state');

	let argumentItems: ReviewQueueArgumentItem[] = [];
	let personItems: ReviewQueuePersonItem[] = [];

	if (tab === 'arguments') {
		const params = new URLSearchParams();
		if (status) params.set('status', status);
		if (tier) params.set('tier', tier);
		if (review_state) params.set('review_state', review_state);
		const queryString = params.toString();

		try {
			const res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/review/arguments${queryString ? '?' + queryString : ''}`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (res.ok) {
				argumentItems = await res.json();
			} else {
				console.error('[review load] arguments fetch returned', res.status);
			}
		} catch (err) {
			console.error(
				'[review load] arguments fetch threw:',
				err instanceof Error ? err.message : String(err),
			);
		}
	} else {
		const params = new URLSearchParams();
		if (review_state) params.set('review_state', review_state);
		const queryString = params.toString();

		try {
			const res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/review/people${queryString ? '?' + queryString : ''}`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (res.ok) {
				personItems = await res.json();
			} else {
				console.error('[review load] people fetch returned', res.status);
			}
		} catch (err) {
			console.error(
				'[review load] people fetch threw:',
				err instanceof Error ? err.message : String(err),
			);
		}
	}

	return { tab, status, tier, review_state, argumentItems, personItems };
};

/**
 * Shared PATCH helper for the three resolve-action form actions below —
 * each POSTs the corresponding fixed action verb the server chose (never
 * a client-supplied field name/value, T-49-massassign) to
 * `/api/admin/review/participants/{id}` or `/api/admin/review/people/{id}`,
 * then redirects back to the CURRENT url (preserving tab and filters) on
 * success (D-26: the row stays visible with its new state until the next
 * reload, which this redirect triggers).
 */
async function patchReviewAction(
	fetchFn: typeof fetch,
	kind: 'participants' | 'people',
	id: string,
	action: 'confirm' | 'confirm_unattributable' | 'reflag',
): Promise<{ error: string } | null> {
	let res: Response;
	try {
		res = await fetchFn(`${FASTAPI_BASE_URL}/api/admin/review/${kind}/${id}`, {
			method: 'PATCH',
			headers: {
				'X-Admin-Token': ADMIN_TOKEN,
				'Content-Type': 'application/json',
			},
			body: JSON.stringify({ action }),
		});
	} catch {
		return { error: 'Could not complete this action. Try again.' };
	}

	if (!res.ok) {
		const payload: unknown = await res.json().catch(() => null);
		const detail = (payload as { detail?: unknown } | null)?.detail;
		if (typeof detail === 'string' && detail.length > 0) {
			return { error: detail };
		}
		return { error: 'Could not complete this action. Try again.' };
	}

	return null;
}

export const actions: Actions = {
	confirm: async ({ request, fetch, url }) => {
		const formData = await request.formData();
		const kind = (formData.get('kind') as string) === 'person' ? 'people' : 'participants';
		const id = formData.get('id') as string;

		const failure = await patchReviewAction(fetch, kind, id, 'confirm');
		if (failure) return fail(502, failure);

		throw redirect(303, url.pathname + url.search);
	},

	/**
	 * confirmUnattributable — participant-only (D-17); there is no
	 * analogous action on the People tab (a bare Person has no
	 * unattributable state).
	 */
	confirmUnattributable: async ({ request, fetch, url }) => {
		const formData = await request.formData();
		const id = formData.get('id') as string;

		const failure = await patchReviewAction(fetch, 'participants', id, 'confirm_unattributable');
		if (failure) return fail(422, failure);

		throw redirect(303, url.pathname + url.search);
	},

	reflag: async ({ request, fetch, url }) => {
		const formData = await request.formData();
		const kind = (formData.get('kind') as string) === 'person' ? 'people' : 'participants';
		const id = formData.get('id') as string;

		const failure = await patchReviewAction(fetch, kind, id, 'reflag');
		if (failure) return fail(422, failure);

		throw redirect(303, url.pathname + url.search);
	},
};
