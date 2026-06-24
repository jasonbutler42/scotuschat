/**
 * GET /admin/people/[id]/merge-preview?target_id={n}
 *
 * Server-only proxy to FastAPI GET /api/admin/people/{id}/merge-preview.
 * Injects the ADMIN_TOKEN server-side so the browser never sees the secret
 * (T-12-TOKENLEAK — ADMIN_TOKEN imported exclusively from $env/static/private).
 *
 * Returns the four FK counts as JSON:
 *   { utterances, aliases, appearances, argument_participants }
 *
 * The Svelte component fetches this same-origin URL on merge target selection
 * to show an inline confirmation before the operator commits the merge (D-09).
 */
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, url, fetch }) => {
	const target_id = url.searchParams.get('target_id');

	if (target_id === null) {
		return error(400, 'target_id is required');
	}

	let res: Response;
	try {
		res = await fetch(
			`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/merge-preview?target_id=${target_id}`,
			{ headers: { 'X-Admin-Token': ADMIN_TOKEN } }
		);
	} catch {
		return error(502, 'Could not load merge counts');
	}

	if (!res.ok) {
		return error(502, 'Could not load merge counts');
	}

	// Return the FastAPI JSON payload — no token echoed back to the client
	// Cache-Control: no-store prevents browser from serving stale cached responses
	// when the user selects a second merge target (Gap F fix)
	return json(await res.json(), { headers: { 'Cache-Control': 'no-store' } });
};
