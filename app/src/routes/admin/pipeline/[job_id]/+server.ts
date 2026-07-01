import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Polling endpoint for the job detail page's live step-card updates.
// Auth enforced by hooks.server.ts before this handler runs (same as +page.server.ts).
// Returns the full AdminJobResponse so the client can update all dynamic job fields.
export const GET: RequestHandler = async ({ params }) => {
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (!res.ok) return json(null, { status: res.status });
		return json(await res.json());
	} catch {
		return json(null, { status: 502 });
	}
};
