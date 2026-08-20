import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

type Blocker = { code: string; count: number };

type ArgumentListItem = {
	id: number;
	argued_date: string | null;
	case_name: string;
	docket_number: string;
	resolved_at: string | null;
	published_at: string | null;
	status: string;
	trust_tier: string;
};

export const load: PageServerLoad = async ({ fetch, url }) => {
	// status (DASH-02, D-05/D-06): optional single-value filter driven by the
	// segmented control and by dashboard status CTAs. Not validated client-side —
	// unrecognized values pass through and list_arguments() no-ops on them.
	const status = url.searchParams.get('status');

	const params = new URLSearchParams();
	if (status) params.set('status', status);
	const queryString = params.toString();
	const apiUrl = `${FASTAPI_BASE_URL}/api/admin/arguments${queryString ? '?' + queryString : ''}`;

	let args: ArgumentListItem[] = [];

	try {
		const res = await fetch(apiUrl, {
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

	return { arguments: args, status };
};

export const actions: Actions = {
	/**
	 * publish — POST /api/admin/arguments/{id}/publish.
	 *
	 * The backend enforces two gates (Phase 48 D-14/D-19/D-20): a non-overridable
	 * `resolved_at IS NOT NULL` completeness check, evaluated first, and an
	 * overridable UNCERTAIN trust-tier check, evaluated only after the first gate
	 * passes. Only the trust gate accepts `override_reason`. This action relays
	 * the server's decision — it never re-implements either gate; UI gating (the
	 * `required` textarea attribute) is defense-in-depth only, and the server's
	 * own `.strip()` check on the override reason is the single authority (D-17).
	 *
	 * Mirrors the detail page's `[id]/+page.server.ts` publish action (plan
	 * 48-08), adapted for this page's one shared `form` prop spanning many
	 * rows (plan 48-10): every returned `fail(...)` payload carries
	 * `argumentId` so the page can address the correct row. On success, this
	 * still redirects (unchanged); on ANY non-2xx response or a thrown fetch,
	 * it returns `fail(...)` and never redirects — replacing the previous
	 * unconditional `console.error` + `throw redirect(...)` shape that
	 * silently discarded a blocked publish (Defect 1).
	 */
	publish: async ({ request, fetch }) => {
		const formData = await request.formData();
		const argument_id = formData.get('argument_id') as string;
		const override_reason = (formData.get('override_reason') as string) ?? '';
		const argumentId = Number(argument_id);

		let res: Response;
		try {
			if (override_reason.trim().length > 0) {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/publish`, {
					method: 'POST',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ override_reason }),
				});
			} else {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/publish`, {
					method: 'POST',
					headers: { 'X-Admin-Token': ADMIN_TOKEN },
				});
			}
		} catch {
			return fail(502, { argumentId, error: 'Could not publish this argument. Try again.' });
		}

		if (!res.ok) {
			const payload: unknown = await res.json().catch(() => null);
			const detail = (payload as { detail?: unknown } | null)?.detail;

			if (typeof detail === 'object' && detail !== null) {
				const d = detail as Record<string, unknown>;
				if (d.code === 'uncertain_tier_blocked') {
					return fail(422, {
						argumentId,
						publishBlocked: true,
						trustTier: d.trust_tier as string,
						blockers: (d.blockers as Blocker[]) ?? [],
						blockMessage: d.message as string,
					});
				}
				if (d.code === 'blank_override_reason') {
					return fail(422, {
						argumentId,
						publishBlocked: true,
						overrideReasonRequired: true,
						blockMessage: d.message as string,
					});
				}
			}

			if (typeof detail === 'string' && detail.length > 0) {
				// Resolve-gate (not overridable) and already-published messages
				// reach the operator verbatim — no reason field is offered for
				// either (D-14). This is Defect 1's second half: before this
				// plan, this branch was never reached at all.
				return fail(422, { argumentId, error: detail });
			}

			return fail(422, { argumentId, error: 'Could not publish this argument. Try again.' });
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
