import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Polling endpoint for the pipeline list page's live badge updates.
// Auth enforced by hooks.server.ts before this handler runs (same as +page.server.ts).
export const GET: RequestHandler = async () => {
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (!res.ok) return json([]);
		return json(await res.json());
	} catch {
		return json([]);
	}
};
