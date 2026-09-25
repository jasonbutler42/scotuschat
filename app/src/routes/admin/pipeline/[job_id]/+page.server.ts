import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

interface ParticipantItem {
	participant_id: number;
	person_id: number;
	full_name: string;
	role_name: string | null;
	side: string | null;
}

interface ArgumentPreview {
	id: number;
	case_name: string;
	docket_number: string;
	argued_date: string | null;
	resolved_at: string | null;
	published_at: string | null;
	status: string | null;
	source_docket: string | null;
	source_dockets: string[] | null;
	cover_metadata: Record<string, unknown> | null;
	question_number: number | null;
}

interface DuplicateArgumentConflict {
	code: 'duplicate_argument';
	message: string;
	conflicting_argument_id: number;
}

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

// Phase 25 backend-derived card contracts (api/schemas/admin_jobs.py, api/schemas/admin_people.py).

interface ReadinessBlocker {
	code: string;
	message: string;
}

interface RunReadiness {
	state: 'not_ready' | 'ready' | 'already_created';
	blockers: ReadinessBlocker[];
	argument_edit_href: string | null;
}

interface FailedStepRecovery {
	step: string | null;
	guidance: string;
	href: string;
	raw_error: string | null;
}

interface ResolveRow {
	participant_id: number;
	raw_speaker_label: string;
	person_id: number | null;
	full_name: string | null;
	photo_url: string | null;
	initials: string | null;
	side: string;
	argument_role: string | null;
	descriptor: string | null;
	descriptor_hint: string | null;
	bench_role: string | null;
	missing_tenure: boolean;
	person_edit_href: string | null;
	editable: boolean;
}

export const load: PageServerLoad = async ({ params }) => {
	// Fetch the specific job from the admin jobs endpoint.
	// X-Admin-Token is required for all SvelteKit → FastAPI calls.
	const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
		headers: { 'X-Admin-Token': ADMIN_TOKEN },
	});

	if (res.status === 404) {
		throw error(404, 'Run not found');
	}

	if (!res.ok) {
		throw error(502, 'Could not load run details');
	}

	const job = await res.json();

	// Fetch all people for the HIT-row Change typeahead (Gap 1b — Plan 07-07).
	// On non-OK, default to [] so the job view still renders.
	// Phase 44 Plan 07 (RESOLVE-09): widened to match the real PersonListItem shape
	// (api/schemas/admin_people.py) — is_justice is what ResolveCard.svelte's
	// sideScopedCandidates filters on. role_name was never a PersonListItem field;
	// this annotation had been wrong since it was written and is dropped here.
	let people: Array<{ id: number; full_name: string; is_justice: boolean }> = [];
	let peopleLoadError: string | null = null;
	try {
		const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (peopleRes.ok) {
			people = await peopleRes.json();
		} else {
			peopleLoadError = `GET /api/admin/people returned ${peopleRes.status}`;
			console.error('[load] people fetch failed:', peopleLoadError);
		}
	} catch (err) {
		// Non-critical — degrade gracefully; typeahead will fall back to row.candidates
		peopleLoadError = err instanceof Error ? err.message : String(err);
		console.error('[load] people fetch threw:', peopleLoadError);
	}

	// Fetch resolved participants when the job has an argument and is either completed or paused
	// (PEOPLE-04, D-02). Paused state is needed for the advocate role dropdowns (D-08, Phase 15).
	// Degrades gracefully on any error so the existing page is never broken by this addition.
	let participants: ParticipantItem[] = [];
	if ((job.status === 'completed' || job.status === 'paused') && job.argument_id != null) {
		try {
			const participantsRes = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/participants`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (participantsRes.ok) {
				participants = await participantsRes.json();
			} else {
				console.error(
					`[load] participants fetch failed: GET /api/admin/jobs/${params.job_id}/participants returned ${participantsRes.status}`,
				);
			}
		} catch (err) {
			// Non-critical — degrade to [] so the page still renders without the participant section
			console.error('[load] participants fetch threw:', err instanceof Error ? err.message : String(err));
		}
	}

	// Fetch argument metadata when the job has an argument_id set (D-03, Plan 04).
	// Uses the dedicated argument endpoint — not embedded in AdminJobResponse (RESEARCH Pattern 5).
	// Degrades gracefully to null on any error so the existing job view still renders.
	let argument: ArgumentPreview | null = null;
	if (job.argument_id != null) {
		try {
			const argRes = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/arguments/${job.argument_id}`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (argRes.ok) {
				argument = await argRes.json();
			} else {
				console.error(
					`[load] argument fetch failed: GET /api/admin/arguments/${job.argument_id} returned ${argRes.status}`,
				);
			}
		} catch (err) {
			// Non-critical — degrade gracefully; the existing job view renders without the preview
			console.error('[load] argument fetch threw:', err instanceof Error ? err.message : String(err));
		}
	}

	// Fetch backend-derived Create Argument readiness for the run status card
	// (Phase 25, D-01 through D-04, D-18, D-20, PJOB-01, PJOB-02, PJOB-20).
	// Non-critical — degrade to null on failure so the existing page still renders;
	// Plan 25-04's RunStatusCard guards for a null readiness prop.
	let readiness: RunReadiness | null = null;
	try {
		const readinessRes = await fetch(
			`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/readiness`,
			{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
		);
		if (readinessRes.ok) {
			readiness = await readinessRes.json();
		} else {
			console.error(
				`[load] readiness fetch failed: GET /api/admin/jobs/${params.job_id}/readiness returned ${readinessRes.status}`,
			);
		}
	} catch (err) {
		console.error('[load] readiness fetch threw:', err instanceof Error ? err.message : String(err));
	}

	// Fetch step-specific failed-run guidance only when the job is failed
	// (Phase 25, D-05 through D-08, PJOB-08, PJOB-22 supersession).
	let failedRecovery: FailedStepRecovery | null = null;
	if (job.status === 'failed') {
		try {
			const failedRes = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/failed-recovery`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (failedRes.ok) {
				failedRecovery = await failedRes.json();
			} else {
				console.error(
					`[load] failed-recovery fetch failed: GET /api/admin/jobs/${params.job_id}/failed-recovery returned ${failedRes.status}`,
				);
			}
		} catch (err) {
			console.error(
				'[load] failed-recovery fetch threw:',
				err instanceof Error ? err.message : String(err),
			);
		}
	}

	// Fetch every Resolve card row (including unresolved rows) for the job's linked
	// argument (Phase 25, D-10 through D-19). Only valid once an argument is linked
	// (the backend 422s otherwise, per Plan 25-02); degrades to [] on any failure.
	let resolveRows: ResolveRow[] = [];
	if (job.argument_id != null) {
		try {
			const resolveRowsRes = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/resolve-rows`,
				{ headers: { 'X-Admin-Token': ADMIN_TOKEN } },
			);
			if (resolveRowsRes.ok) {
				resolveRows = await resolveRowsRes.json();
			} else {
				console.error(
					`[load] resolve-rows fetch failed: GET /api/admin/jobs/${params.job_id}/resolve-rows returned ${resolveRowsRes.status}`,
				);
			}
		} catch (err) {
			console.error(
				'[load] resolve-rows fetch threw:',
				err instanceof Error ? err.message : String(err),
			);
		}
	}

	// Construct savedValues and hints for ArgumentDetailsCard (Plan 23-03).
	// savedValues: operator-confirmed values from the Argument record.
	// hints: raw extraction output from cover_metadata JSONB.
	// Both are null when no argument is linked (PJOB-07 guard: component not rendered).
	let savedValues: { dockets: string[]; question_number: string; argued_date: string | null } | null =
		null;
	let hints: {
		dockets: string[];
		question_number: string | null;
		argued_date: string | null;
		case_name: string | null;
	} | null = null;

	if (argument != null) {
		savedValues = {
			dockets: argument.source_dockets ?? (argument.source_docket ? [argument.source_docket] : []),
			question_number: argument.question_number != null ? String(argument.question_number) : '',
			argued_date: argument.argued_date ? argument.argued_date.slice(0, 10) : null,
		};
		hints = {
			dockets: argument.cover_metadata?.primary_docket
				? [String(argument.cover_metadata.primary_docket)]
				: [],
			question_number: null,
			argued_date: (argument.cover_metadata?.argued_date as string) ?? null,
			case_name: (argument.cover_metadata?.case_name as string) ?? null,
		};
	}

	// Phase 49 (D-33a follow-up): this was one shared `readonlyMode` boolean
	// gating two DIFFERENT editability concerns on this page — flagged as a
	// carried-forward open item by plans 49-04 and 49-05, closed here rather
	// than passed along a third time.
	//
	// metadataReadonly (ArgumentDetailsCard): UNCHANGED behavior — read-only
	// once the linked argument has left the 'candidate' lifecycle state
	// (Phase 25, D-18, D-19; Phase 48 D-01 renamed the born state from
	// 'pipeline' to 'candidate'). No linked argument yet means the run is
	// still in-progress, never read-only. This concern predates Phase 49 and
	// nothing in this phase's scope changes it. UPDATED (D-35a, plan 49-11,
	// 2026-08-24): `update_argument_metadata` (api/services/admin_arguments.py)
	// now carries its OWN published guard (it did not before D-35a). The
	// restriction on THIS page is therefore a frontend-only restriction on
	// the CANDIDATE boundary — a narrower, non-published concern this flag
	// predates and still owns — layered ON TOP OF the backend's published
	// lock, not a frontend-only restriction full stop.
	//
	// resolveCardReadonly (ResolveCard): WIDENED to match the backend's own
	// widened guard (Phase 49 plan 49-04) — `update_resolve_row_for_job` and
	// `list_resolve_rows_for_job`'s `editable` flag both accept every
	// unpublished state (candidate/draft/unpublished); only PUBLISHED is
	// read-only. Before this fix, the shared `readonlyMode` flag still keyed
	// on `!== 'candidate'`, so the UI showed DRAFT/UNPUBLISHED as read-only
	// even though the backend had already started accepting those writes —
	// a real UI/backend inconsistency, not just an unsplit variable name.
	const metadataReadonly = argument != null && argument.status !== 'candidate';
	const resolveCardReadonly = argument != null && argument.status === 'published';

	return {
		job,
		people,
		peopleLoadError,
		participants,
		argument,
		savedValues,
		hints,
		readiness,
		failedRecovery,
		resolveRows,
		metadataReadonly,
		resolveCardReadonly,
	};
};

export const actions: Actions = {
	/**
	 * resolve — post the operator-dispositioned discrepancy matches to FastAPI.
	 * The hidden `matches` field carries a JSON array of { raw_speaker_label, person_id }.
	 * On non-OK: return fail(422) so the job stays paused and the operator can retry (Pitfall 5).
	 */
	resolve: async ({ request, params }) => {
		const data = await request.formData();
		const matchesRaw = (data.get('matches') as string) ?? '[]';

		let matches: Array<{ raw_speaker_label: string; person_id: number }>;
		try {
			matches = JSON.parse(matchesRaw);
		} catch {
			return fail(422, { error: 'Invalid matches data. Please try again.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/resolve`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ matches }),
			});
		} catch {
			return fail(422, { error: 'Could not save the review. Check your selections and try again.' });
		}

		if (!res.ok) {
			// Non-OK leaves the job paused so the operator can retry (Pitfall 5).
			return fail(422, { error: 'Could not save the review. Check your selections and try again.' });
		}

		return { success: true };
	},

	/**
	 * approve — POST to /api/admin/jobs/{job_id}/approve to transition the argument from
	 * pipeline → draft state. Side/descriptor persistence now happens per-row via ResolveCard's
	 * own ?/saveResolveRow action (Phase 25) — this action only triggers the transition.
	 * On success: redirect to the same page so it re-renders in read-only state.
	 * On failure: return fail with approveError key so the UI shows a scoped error.
	 */
	approve: async ({ params }) => {
		// POST approve — transitions argument to draft state
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/approve`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { approveError: 'Could not create argument. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { approveError: 'Could not create argument. Try again.' });
		}

		throw redirect(303, `/admin/pipeline/${params.job_id}`);
	},

	/**
	 * addPerson — create a new person inline during discrepancy review (D-13).
	 *
	 * Accepts first_name/last_name (structured parts) and (optional) role_name,
	 * raw_speaker_label, and side from formData for the Phase 25 mini
	 * create-person popover (D-12, PJOB-19) — when raw_speaker_label and side
	 * are both present the backend also sets Person.is_justice from
	 * side == BENCH and updates the matching job-owned ArgumentParticipant's
	 * person_id/side. Phase 38 (D-01/D-03/D-09) removed full_name from
	 * PersonCreate entirely — the backend derives it server-side from
	 * first_name/last_name via prepare_person_name, which requires at least
	 * one of the two non-blank; sending full_name is now a 422
	 * (extra="forbid"). This action previously still sent full_name (a stale
	 * caller Phase 38 never migrated, found live 2026-08-10) — fixed here.
	 * On success: returns the created person { id, full_name } for client-side dropdown update.
	 */
	addPerson: async ({ request, params }) => {
		const data = await request.formData();
		const first_name = (data.get('first_name') as string) ?? '';
		const last_name = (data.get('last_name') as string) ?? '';
		const role_name = (data.get('role_name') as string) ?? '';
		const raw_speaker_label = (data.get('raw_speaker_label') as string) ?? '';
		const side = (data.get('side') as string) ?? '';

		if (!first_name.trim() && !last_name.trim()) {
			return fail(400, { error: 'First or last name is required.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/people`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					first_name: first_name.trim() || null,
					last_name: last_name.trim() || null,
					role_name: role_name.trim() || null,
					raw_speaker_label: raw_speaker_label.trim() || null,
					side: side.trim() || null,
				}),
			});
		} catch {
			return fail(400, { error: 'Could not create person. Please try again.' });
		}

		if (!res.ok) {
			return fail(400, { error: 'Could not create person. Please try again.' });
		}

		const person = await res.json();
		// Attach role_name from form data — the API returns PersonResponse which reads
		// role_name from the ORM object, but Person.role_name is not an ORM column (only
		// role_id is). Enrich with the form value so the Svelte typeahead shows "Name (Role)".
		const enrichedPerson = {
			...person,
			role_name: person.role_name ?? (role_name.trim() || null),
		};
		// Return the created person so the Svelte component can add them to the dropdown.
		return { personCreated: true, person: enrichedPerson };
	},

	/**
	 * saveResolveRow — persist a Resolve card row's side (BENCH allowed) and
	 * advocate descriptor edit (Phase 25, D-14, D-18, PJOB-14, PJOB-18).
	 *
	 * Reads participant_id, side, and optional descriptor from form data.
	 * job_id (the route param) is the only trust boundary consulted here —
	 * argument ownership is derived and re-verified server-side inside the
	 * FastAPI PATCH handler, so this action never accepts or forwards a
	 * client-supplied argument_id (T-25-16 elevation-of-privilege guard).
	 * Backend 4xx guard failures (IDOR, non-pipeline argument) surface as a
	 * scoped resolveRowError.
	 */
	saveResolveRow: async ({ request, params }) => {
		const data = await request.formData();
		const participantIdRaw = (data.get('participant_id') as string) ?? '';
		const side = ((data.get('side') as string) ?? '').trim();
		const descriptor = ((data.get('descriptor') as string) ?? '').trim();

		const participant_id = Number(participantIdRaw);
		if (!Number.isInteger(participant_id) || participant_id <= 0) {
			return fail(400, { resolveRowError: 'Missing or invalid participant.' });
		}
		if (!side) {
			return fail(400, { resolveRowError: 'Side is required.' });
		}

		let res: Response;
		try {
			res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/resolve-rows`,
				{
					method: 'PATCH',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({
						participant_id,
						side,
						descriptor: descriptor || null,
					}),
				},
			);
		} catch {
			return fail(502, { resolveRowError: 'Could not save. Try again.' });
		}

		if (!res.ok) {
			// Backend maps IDOR / non-pipeline-argument guard failures to 422 (Plan 25-01).
			return fail(422, { resolveRowError: 'Could not save. Check the row and try again.' });
		}

		return { resolveRowSaved: true };
	},

	/**
	 * delete — DELETE the admin_job row for this pipeline run (ADMIN-02).
	 *
	 * Issues DELETE /api/admin/jobs/{job_id} with X-Admin-Token header.
	 * On non-OK or network error: return fail(502) so the operator can retry.
	 * On success: redirect to /admin/pipeline (D-12).
	 *
	 * No can_delete gate — jobs are always deletable (D-08 applies to arguments, not jobs).
	 */
	delete: async ({ params }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
				method: 'DELETE',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { deleteError: 'Could not delete run. Try again.' });
		}

		if (!res.ok) {
			return fail(502, { deleteError: 'Could not delete run. Try again.' });
		}

		throw redirect(303, '/admin/pipeline');
	},

	/**
	 * saveJobMetadata — persist dockets, question_number, and argued_date for the linked argument.
	 *
	 * Reads docket[] via getAll (D-05 pill serialization). Fetches the job to derive argument_id
	 * server-side (T-23-03-01: IDOR guard — argument_id never accepted from form data).
	 * Guards: never creates an argument (PJOB-07); argument_id null → fail(400).
	 * Always echoes dockets in fail() payload (D-06 pill restore on failed save).
	 * PATCHes existing /api/admin/arguments/{id}/metadata endpoint (source_docket = dockets[0]).
	 *
	 * refreshResolveRows: true (Phase 25, D-17, PJOB-17) signals the page that
	 * an argued_date change may shift bench tenure-role derivation, so the
	 * Resolve card's data should be refreshed. ArgumentDetailsCard's use:enhance
	 * already calls the default update() on success, which invalidates the load
	 * function (refetching resolveRows) — this flag lets Plan 25-04's page
	 * composition assert that behavior explicitly rather than relying on it implicitly.
	 */
	saveJobMetadata: async ({ request, params }) => {
		const data = await request.formData();
		const dockets = (data.getAll('docket[]') as string[])
			.map((v) => v.trim())
			.filter(Boolean);
		const question_number = ((data.get('question_number') as string) ?? '').trim();
		const argued_date = ((data.get('argued_date') as string) ?? '').trim() || null;
		const attemptedValues = { dockets, question_number, argued_date };

		// Fetch the job to get argument_id server-side (T-23-03-01: never accept from form)
		let argumentId: number | null = null;
		try {
			const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
			if (jobRes.ok) {
				const job = await jobRes.json();
				argumentId = job.argument_id ?? null;
			} else {
				return fail(502, { saveError: 'Could not save. Try again.', ...attemptedValues });
			}
		} catch {
			return fail(502, { saveError: 'Could not save. Try again.', ...attemptedValues });
		}

		// PJOB-07: never create an argument — guard argument_id null
		if (argumentId === null) {
			return fail(400, {
				saveError: 'No argument linked to this run yet.',
				...attemptedValues,
			});
		}

		// PATCH the argument metadata (source_docket, argued_date, question_number)
		let res: Response;
		try {
			res = await fetch(
				`${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/metadata`,
				{
					method: 'PATCH',
					headers: {
						'X-Admin-Token': ADMIN_TOKEN,
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({
						// WR-02: case_name is intentionally omitted here � it is not editable
						// from the job detail page. case_name edits are handled via the
						// argument edit page (/admin/arguments/{id}) only.
						// D-MULTI-DOCKET: send full array; service writes source_dockets and
						// keeps source_docket = dockets[0] as the canonical dedup key.
						source_dockets: dockets,
						argued_date,
						question_number: question_number || null,
					}),
				},
			);
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

		return { saved: true, refreshResolveRows: true };
	},
};
