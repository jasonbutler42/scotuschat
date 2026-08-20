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
	override_reason: string | null;
	trust_tier_at_transition: string | null;
};

type Blocker = { code: string; count: number };

type SpeakerRow = {
	participant_id: number;
	person_id: number | null;
	full_name: string | null;
	side: string;
	is_bench: boolean;
	argument_role: string | null;
	descriptor: string | null;
	descriptor_hint: string | null;
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
	trust_tier: string;
	consolidated_dockets: ConsolidatedDocket[];
	participants: AdvocateParticipant[];
	tenure_gap_warnings: TenureGapWarning[];
	status_log: StatusLogEntry[];
	speakers: SpeakerRow[];
	source_docket: string | null;
	source_dockets: string[];
	cover_metadata: Record<string, unknown> | null;
	question_number: number | null;
};

type DuplicateArgumentConflict = {
	code: 'duplicate_argument';
	message: string;
	conflicting_argument_id: number;
};

function parseDuplicateConflict(value: unknown): DuplicateArgumentConflict | null {
	if (typeof value !== 'object' || value === null) return null;
	const detail = value as Record<string, unknown>;
	if (
		detail.code === 'duplicate_argument' &&
		typeof detail.message === 'string' &&
		detail.message.trim().length > 0 &&
		Number.isInteger(detail.conflicting_argument_id) &&
		Number(detail.conflicting_argument_id) > 0
	) {
		return detail as unknown as DuplicateArgumentConflict;
	}
	return null;
}

type RequiredFieldErrors = { caseNameRequired: boolean; docketRequired: boolean };

function parseRequiredFieldErrors(value: unknown): RequiredFieldErrors | null {
	if (typeof value !== 'object' || value === null) return null;
	const detail = (value as { detail?: unknown }).detail;
	if (!Array.isArray(detail)) return null;
	const errors = { caseNameRequired: false, docketRequired: false };
	for (const entry of detail) {
		if (typeof entry !== 'object' || entry === null) continue;
		const loc = (entry as { loc?: unknown }).loc;
		if (!Array.isArray(loc)) continue;
		const field = loc.at(-1);
		if (field === 'case_name') errors.caseNameRequired = true;
		if (field === 'docket_number' || field === 'source_docket' || field === 'source_dockets') {
			errors.docketRequired = true;
		}
	}
	return errors.caseNameRequired || errors.docketRequired ? errors : null;
}

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

	// Construct savedValues and hints for the second ArgumentDetailsCard consumer
	// (AEDIT-04, mirroring the pipeline job detail page's Plan 23-03 derivation,
	// adapted to source from the already-fetched `argument` — no second fetch needed).
	// savedValues: operator-confirmed values from the Argument record.
	// Pitfall 3: source_dockets defaults to [] (never null), so a bare `??` would
	// never fall back to source_docket — an argument with only source_docket set
	// would show an empty pill list. Use `.length ?` instead.
	const savedValues = {
		dockets: argument.source_dockets?.length
			? argument.source_dockets
			: argument.source_docket
				? [argument.source_docket]
				: [],
		question_number: argument.question_number != null ? String(argument.question_number) : '',
		argued_date: argument.argued_date ? argument.argued_date.slice(0, 10) : null,
	};

	// hints: raw extraction output from cover_metadata JSONB — always visible (D-04).
	// question_number is frozen to null (existing project-wide decision 23-04):
	// Argument.question_number is operator-editable, not an immutable extraction source.
	const hints = {
		dockets: argument.cover_metadata?.primary_docket
			? [String(argument.cover_metadata.primary_docket)]
			: [],
		question_number: null,
		argued_date: (argument.cover_metadata?.argued_date as string) ?? null,
		case_name: (argument.cover_metadata?.case_name as string) ?? null,
	};

	return { argument, can_delete, savedValues, hints };
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
		const descriptor = (formData.get('descriptor') as string) ?? '';

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
					body: JSON.stringify({ side, descriptor }),
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
	 * save — PATCH /api/admin/arguments/{id} with the Case card's two editable fields.
	 * argued_date is no longer part of this action (Pitfall 2) — it is edited solely
	 * via the ArgumentDetailsCard's own saveArgumentDetails action below.
	 * On slug_collision 422, surface the UI-SPEC error copy (D-11).
	 * On success, redirect re-runs load returning fresh data.
	 */
	save: async ({ request, params, fetch }) => {
		const formData = await request.formData();

		const case_name = (formData.get('case_name') as string) ?? '';
		const docket_number = (formData.get('docket_number') as string) ?? '';
		const attemptedValues = { case_name, docket_number };

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ case_name, docket_number }),
			});
		} catch {
			return fail(502, { error: 'Could not save changes. Check your inputs and try again.', ...attemptedValues });
		}

		if (!res.ok) {
			let detail = '';
			try {
				const body: unknown = await res.json();
				if (res.status === 422) {
					const required = parseRequiredFieldErrors(body);
					if (required) return fail(422, { ...required, ...attemptedValues });
				}
				detail =
					typeof body === 'object' && body !== null && typeof (body as { detail?: unknown }).detail === 'string'
						? String((body as { detail: string }).detail)
						: '';
			} catch {
				// ignore parse error
			}

			if (res.status === 422 && detail.includes('slug_collision')) {
				return fail(422, {
					error:
						'This title generates a URL slug that conflicts with an existing case. Choose a different title.',
					...attemptedValues,
				});
			}

			if (res.status === 422 && detail.includes('docket_collision')) {
				return fail(422, {
					error: 'That docket number is already used by another case. Choose a different docket.',
					...attemptedValues,
				});
			}

			return fail(422, { error: 'Could not save changes. Check your inputs and try again.', ...attemptedValues });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},

	/**
	 * saveArgumentDetails — persist source_dockets, question_number, and argued_date
	 * for this argument via the shared ArgumentDetailsCard's own action target (AEDIT-04).
	 *
	 * Mirrors the pipeline job detail page's saveJobMetadata, simplified: params.id
	 * IS the argument id directly, no job-fetch indirection is needed. Argument id is
	 * derived solely from params.id (never a form field) — matches every other action
	 * on this page (V4 IDOR guard, T-30.1-04).
	 *
	 * CRITICAL (Pitfall 1 / WR-02): case_name is intentionally omitted from this PATCH
	 * body — the Case card's ?/save action above is the sole owner of case_name, so it
	 * can never be double-written from two actions.
	 *
	 * Does NOT redirect on success — ArgumentDetailsCard's own use:enhance expects
	 * update({reset:false}) and renders its own "Saved." message; a redirect would
	 * bypass that UI (RESEARCH.md Pattern 1 / A1).
	 */
	saveArgumentDetails: async ({ request, params, fetch }) => {
		const data = await request.formData();
		const dockets = (data.getAll('docket[]') as string[]).map((v) => v.trim()).filter(Boolean);
		const question_number = ((data.get('question_number') as string) ?? '').trim();
		const argued_date = ((data.get('argued_date') as string) ?? '').trim() || null;
		const attemptedValues = { dockets, question_number, argued_date };

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/metadata`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					source_dockets: dockets,
					argued_date,
					question_number: question_number || null,
				}),
			});
		} catch {
			return fail(502, { saveError: 'Could not save. Try again.', ...attemptedValues });
		}

		if (!res.ok) {
			if (res.status === 422) {
				try {
					const required = parseRequiredFieldErrors(await res.json());
					if (required) return fail(422, { ...required, ...attemptedValues });
				} catch {
					// Malformed backend data is intentionally replaced with generic copy.
				}
			}
			if (res.status === 409) {
				try {
					const body: unknown = await res.json();
					const detail = parseDuplicateConflict(
						typeof body === 'object' && body !== null ? (body as { detail?: unknown }).detail : null,
					);
					if (detail) return fail(409, { conflict: detail, ...attemptedValues });
				} catch {
					// Malformed backend data is intentionally replaced with generic copy.
				}
			}
			return fail(422, { saveError: 'Could not save. Try again.', ...attemptedValues });
		}

		return { saved: true };
	},

	/**
	 * publish — POST /api/admin/arguments/{id}/publish.
	 *
	 * The backend enforces two gates (Phase 48 D-14/D-19/D-20): a non-overridable
	 * `resolved_at IS NOT NULL` completeness check, evaluated first, and an
	 * overridable UNCERTAIN trust-tier check, evaluated only after the first gate
	 * passes. Only the trust gate accepts `override_reason`. This action relays the
	 * server's decision — it never re-implements either gate; UI gating (the
	 * `required` textarea attribute, the disabled-button state) is defense-in-depth
	 * only, and the server's own `.strip()` check on the override reason is the
	 * single authority (D-17). A blocked-publish response sets `publishBlocked`
	 * on the returned form payload so the page can render the block panel; the
	 * non-overridable resolve gate and the already-published guard never set
	 * `publishBlocked` and take the plain `error` path instead.
	 *
	 * Every fail(...) payload also carries `source: 'publish'`. This page's
	 * `form` prop is shared across every action (`?/save`, `?/publish`,
	 * `?/unpublish`, ...), and `?/save` returns the same `error` key. Without
	 * this discriminator a publish error rendered in the case-metadata card's
	 * unrelated alert slot instead of the Status card, where the Publish
	 * button and block panel actually live — the defect this tag fixes.
	 */
	publish: async ({ request, params, fetch }) => {
		const formData = await request.formData();
		const override_reason = (formData.get('override_reason') as string) ?? '';

		let res: Response;
		try {
			if (override_reason.trim().length > 0) {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/publish`, {
					method: 'POST',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({ override_reason }),
				});
			} else {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/publish`, {
					method: 'POST',
					headers: { 'X-Admin-Token': ADMIN_TOKEN },
				});
			}
		} catch {
			return fail(502, { source: 'publish', error: 'Could not publish this argument. Try again.' });
		}

		if (!res.ok) {
			const payload: unknown = await res.json().catch(() => null);
			const detail = (payload as { detail?: unknown } | null)?.detail;

			if (typeof detail === 'object' && detail !== null) {
				const d = detail as Record<string, unknown>;
				if (d.code === 'uncertain_tier_blocked') {
					return fail(422, {
						source: 'publish',
						publishBlocked: true,
						trustTier: d.trust_tier as string,
						blockers: (d.blockers as Blocker[]) ?? [],
						blockMessage: d.message as string,
					});
				}
				if (d.code === 'blank_override_reason') {
					return fail(422, {
						source: 'publish',
						publishBlocked: true,
						overrideReasonRequired: true,
						blockMessage: d.message as string,
					});
				}
			}

			if (typeof detail === 'string' && detail.length > 0) {
				// Resolve-gate (not overridable) and already-published messages reach
				// the operator verbatim — no reason field is offered for either (D-14).
				// `source: 'publish'` discriminates this from ?/save's own `error` key
				// on this page's shared `form` prop — see the `publish` doc comment above.
				return fail(422, { source: 'publish', error: detail });
			}

			return fail(422, { source: 'publish', error: 'Could not publish this argument. Try again.' });
		}

		throw redirect(303, '/admin/arguments/' + params.id);
	},

	/**
	 * unpublish — POST /api/admin/arguments/{id}/unpublish.
	 *
	 * Both fail(...) payloads carry `source: 'unpublish'` for the same reason
	 * `publish` carries `source: 'publish'` (see that action's doc comment
	 * above): this page's `form` prop is shared across every action, and
	 * `?/save` returns the same `error` key. Without this tag an unpublish
	 * failure would render in the case-metadata card's unrelated alert slot
	 * instead of the Status card, where the Unpublish control lives.
	 */
	unpublish: async ({ params, fetch }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/unpublish`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { source: 'unpublish', error: 'Could not unpublish this argument. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { source: 'unpublish', error: 'Could not unpublish this argument. Try again.' });
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
