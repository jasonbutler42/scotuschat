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
	cover_metadata: Record<string, unknown> | null;
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

	return { job, people, peopleLoadError, participants, argument };
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

		// Fetch the job to get argument_id for the PATCH endpoint
		let argumentId: number | null = null;
		try {
			const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
			if (jobRes.ok) {
				const job = await jobRes.json();
				argumentId = job.argument_id ?? null;
			}
		} catch {
			// Continue — PATCH is best-effort; approve still proceeds
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
	 * saveMetadata — PATCH the argument metadata (case_name, source_docket, argued_date).
	 * Fetches the job first to get argument_id (same two-step pattern as approve action).
	 * Returns fail(400) when no argument is linked, fail(502) on network error,
	 * fail(422) on non-OK FastAPI response, { metadataSaved: true } on success.
	 * (D-13, D-14, D-15 — UI-SPEC Component 4/5/6/7/8)
	 */
	saveMetadata: async ({ request, params }) => {
		const data = await request.formData();
		const case_name = ((data.get('case_name') as string) ?? '').trim() || null;
		const source_docket = ((data.get('source_docket') as string) ?? '').trim() || null;
		const argued_date = ((data.get('argued_date') as string) ?? '').trim() || null;

		// Fetch the job to get argument_id — same two-step pattern as approve action
		let argumentId: number | null = null;
		try {
			const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
			});
			if (jobRes.ok) {
				const job = await jobRes.json();
				argumentId = job.argument_id ?? null;
			}
		} catch {
			return fail(502, { metadataError: 'Could not save metadata. Please try again.' });
		}

		if (argumentId === null) {
			return fail(400, { metadataError: 'No argument linked to this job yet.' });
		}

		let res: Response;
		try {
			res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/metadata`, {
				method: 'PATCH',
				headers: {
					'X-Admin-Token': ADMIN_TOKEN,
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ case_name, source_docket, argued_date }),
			});
		} catch {
			return fail(502, { metadataError: 'Could not save metadata. Please try again.' });
		}

		if (!res.ok) {
			return fail(422, { metadataError: 'Could not save metadata. Please try again.' });
		}

		return { metadataSaved: true };
	},
};
