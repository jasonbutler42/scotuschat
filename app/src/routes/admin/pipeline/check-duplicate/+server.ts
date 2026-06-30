/**
 * GET /admin/pipeline/check-duplicate?docket={d}&question={n}
 *
 * Server-only proxy to FastAPI GET /api/admin/arguments/check-duplicate.
 * Injects the ADMIN_TOKEN server-side so the browser never sees the secret
 * (T-12-TOKENLEAK — ADMIN_TOKEN imported exclusively from $env/static/private).
 *
 * Returns JSON: { exists: boolean, argument_id: number | null }
 *
 * The Svelte pipeline start form calls this same-origin URL before submitting
 * when the operator has filled in the docket field, to warn about duplicate
 * arguments (D-03, D-04, D-05, D-06).
 */
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ url, fetch }) => {
	const docket = url.searchParams.get('docket');
	const question = url.searchParams.get('question');

	if (docket === null || question === null) {
		return error(400, 'docket and question are required');
	}

	let res: Response;
	try {
		res = await fetch(
			`${FASTAPI_BASE_URL}/api/admin/arguments/check-duplicate?docket=${encodeURIComponent(docket)}&question=${encodeURIComponent(question)}`,
			{ headers: { 'X-Admin-Token': ADMIN_TOKEN } }
		);
	} catch {
		return error(502, 'Could not check for duplicate');
	}

	if (!res.ok) {
		return error(502, 'Could not check for duplicate');
	}

	// Return the FastAPI JSON payload — no token echoed back to the client
	// Cache-Control: no-store prevents browser from caching the check result
	return json(await res.json(), { headers: { 'Cache-Control': 'no-store' } });
};
