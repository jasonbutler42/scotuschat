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
	side: string;
	argument_role: string | null;
	title: string | null;
	title_hint: string | null;
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
	let people: Array<{ id: number; full_name: string; role_name: string | null }> = [];
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

	// readonlyMode: the page becomes read-only provenance once the linked argument
	// has left the 'pipeline' lifecycle state (Phase 25, D-18, D-19). No linked
	// argument yet means the run is still in-progress, never read-only.
	const readonlyMode = argument != null && argument.status !== 'pipeline';

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
		readonlyMode,
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
	 * pipeline → draft state. Also PATCHes advocate participant sides from the form data
	 * before approving (atomic capture of side assignments at approve time, D-09).
	 * On success: redirect to the same page so it re-renders in read-only state.
	 * On failure: return fail with approveError key so the UI shows a scoped error.
	 */
	approve: async ({ request, params }) => {
		const data = await request.formData();

		// PATCH advocate side assignments before approving — collect participant_side[id]=SIDE fields
		const sideEntries: Array<{ participant_id: string; side: string }> = [];
		for (const [key, value] of data.entries()) {
			const match = key.match(/^participant_side\[(\d+)\]$/);
			if (match) {
				sideEntries.push({ participant_id: match[1], side: value as string });
			}
		}

		// Fetch the job to get argument_id for the PATCH endpoint (best-effort for side assignments)
		let argumentId: number | null = null;
		try {
			const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
			if (!jobRes.ok) {
				return fail(502, { approveError: 'Could not load job. Try again.' });
			}
			const job = await jobRes.json();
			argumentId = job.argument_id ?? null;
		} catch {
			return fail(502, { approveError: 'Could not load job. Try again.' });
		}

		// PATCH each advocate side (non-blocking — approve proceeds even if a PATCH fails)
		if (argumentId != null && sideEntries.length > 0) {
			await Promise.allSettled(
				sideEntries.map(({ participant_id, side }) =>
					fetch(
						`${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/participants/${participant_id}`,
						{
							method: 'PATCH',
							headers: {
								'X-Admin-Token': ADMIN_TOKEN,
								'Content-Type': 'application/json',
							},
							body: JSON.stringify({ side }),
						},
					).catch(() => undefined),
				),
			);
		}

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
	 * rerun — POST to /api/admin/jobs/{job_id}/rerun to start a fresh pipeline run using
	 * the same source PDF. On success: redirect to the new job's detail page.
	 * On failure: return fail with rerunError key.
	 */
	rerun: async ({ params }) => {
		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/rerun`, {
				method: 'POST',
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
		} catch {
			return fail(502, { rerunError: 'Could not start re-run. Try again.' });
		}

		if (!res.ok) {
			return fail(422, { rerunError: 'Could not start re-run. Try again.' });
		}

		let newJobId: number | null = null;
		try {
			const body = await res.json();
			newJobId = body.id ?? null;
		} catch {
			// fallback — stay on current page if we can't parse the new job id
		}

		if (newJobId == null) {
			return fail(502, { rerunError: 'Re-run started but could not navigate to the new run.' });
		}

		throw redirect(303, `/admin/pipeline/${newJobId}`);
	},

	/**
	 * addPerson — create a new person inline during discrepancy review (D-13).
	 * Accepts full_name and role_name from formData.
	 * On success: returns the created person { id, full_name } for client-side dropdown update.
	 */
	addPerson: async ({ request, params }) => {
		const data = await request.formData();
		const full_name = (data.get('full_name') as string) ?? '';
		const role_name = (data.get('role_name') as string) ?? '';

		if (!full_name.trim()) {
			return fail(400, { error: 'Full name is required.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/people`, {
				method: 'POST',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ full_name: full_name.trim(), role_name: role_name.trim() || null }),
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
	 */
	saveJobMetadata: async ({ request, params }) => {
		const data = await request.formData();
		const dockets = (data.getAll('docket[]') as string[])
			.map((v) => v.trim())
			.filter(Boolean);
		const question_number = ((data.get('question_number') as string) ?? '').trim();
		const argued_date = ((data.get('argued_date') as string) ?? '').trim() || null;

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
				return fail(502, { saveError: 'Could not save. Try again.', dockets });
			}
		} catch {
			return fail(502, { saveError: 'Could not save. Try again.', dockets });
		}

		// PJOB-07: never create an argument — guard argument_id null
		if (argumentId === null) {
			return fail(400, {
				saveError: 'No argument linked to this run yet.',
				dockets,
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
			return fail(502, { saveError: 'Could not save. Try again.', dockets });
		}

		if (!res.ok) {
			return fail(422, { saveError: 'Could not save. Try again.', dockets });
		}

		return { saved: true };
	},
};
