/**
 * GET /admin/pipeline/[job_id]/pdf
 *
 * Server-only proxy to FastAPI GET /api/admin/jobs/{job_id}/pdf.
 * Injects ADMIN_TOKEN server-side so the browser never sees the secret
 * (T-17-TOKENLEAK — ADMIN_TOKEN imported exclusively from $env/static/private).
 *
 * FastAPI returns one of two shapes:
 *   - 302 RedirectResponse (Spaces-backed job): proxy passes the Location header
 *     back to the browser as a same-origin 302 so the operator's browser navigates
 *     to the pre-signed Spaces URL directly (PDF bytes never transit SvelteKit).
 *   - 200 FileResponse (disk-backed job): streams the PDF body with forwarded
 *     Content-Type and Content-Disposition headers; body is NOT buffered.
 *
 * Auth guard: hooks.server.ts protects every /admin/* request including +server.ts
 * endpoints — no per-route auth check needed here.
 */
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params }) => {
	let res: Response;
	try {
		res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/pdf`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
			redirect: 'manual',
		});
	} catch {
		error(502, 'Source PDF not available');
	}

	// Spaces-backed case: FastAPI returns a 302 RedirectResponse.
	// `redirect: 'manual'` may produce an opaque response (status 0, type 'opaqueredirect')
	// where Location is unreadable, or a readable 302 where Location is present.
	if (res.status === 302 || res.status === 0) {
		const location = res.headers.get('location');

		if (location) {
			// Readable 302: pass the pre-signed Spaces URL through to the browser.
			// Token never appears in the Location value (server-controlled URL).
			return new Response(null, {
				status: 302,
				headers: { Location: location },
			});
		}

		// Opaque redirect (status 0): Location header is unreadable due to CORS-mode fetch.
		// Re-fetch with redirect: 'follow' to let the server resolve the final URL, then
		// stream the response body. This keeps the PDF bytes off the SvelteKit server
		// while staying within the same-origin proxy contract.
		let followed: Response;
		try {
			followed = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}/pdf`, {
				headers: { 'X-Admin-Token': ADMIN_TOKEN },
				redirect: 'follow',
			});
		} catch {
			error(502, 'Source PDF not available');
		}

		if (!followed.ok) {
			error(followed.status === 404 ? 404 : 502, 'Source PDF not available');
		}

		return new Response(followed.body, {
			status: 200,
			headers: {
				'Content-Type': followed.headers.get('content-type') ?? 'application/pdf',
				'Content-Disposition': followed.headers.get('content-disposition') ?? 'inline',
			},
		});
	}

	// Disk-backed case: FastAPI returns a 200 FileResponse — stream the body directly.
	if (res.ok) {
		return new Response(res.body, {
			status: 200,
			headers: {
				'Content-Type': res.headers.get('content-type') ?? 'application/pdf',
				'Content-Disposition': res.headers.get('content-disposition') ?? 'inline',
			},
		});
	}

	// Non-OK, non-redirect response (e.g. 404 job not found, 404 PDF not found).
	error(res.status === 404 ? 404 : 502, 'Source PDF not available');
};
