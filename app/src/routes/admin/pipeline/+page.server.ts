import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { redirect, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	// Fetch the 10 most recent pipeline jobs from the admin jobs endpoint.
	// X-Admin-Token is required for all SvelteKit → FastAPI calls (T-07-12).
	try {
		const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (!res.ok) {
			// Non-OK response — return empty list so the page still renders.
			return { jobs: [] };
		}
		const jobs = await res.json();
		return { jobs };
	} catch {
		// Network error or FastAPI unavailable — return empty list to avoid crash.
		return { jobs: [] };
	}
};

export const actions: Actions = {
	default: async ({ request }) => {
		const data = await request.formData();
		const mode = data.get('mode') as string;

		if (mode === 'url') {
			// URL mode: forward the pdf_url as multipart FormData to FastAPI.
			const pdf_url = (data.get('pdf_url') as string) ?? '';
			if (!pdf_url) {
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			const body = new FormData();
			body.append('pdf_url', pdf_url);

			// Do NOT set Content-Type — let fetch set the multipart boundary automatically.
			let res: Response;
			try {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
					method: 'POST',
					headers: { 'X-Admin-Token': ADMIN_TOKEN },
					body,
				});
			} catch {
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			if (!res.ok) {
				// T-07-13: surface a generic message; do not expose FastAPI error body verbatim.
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			const { id } = await res.json();
			// SvelteKit project convention: always throw redirect (not bare redirect).
			throw redirect(303, `/admin/pipeline/${id}`);
		} else {
			// Upload mode: forward the PDF file bytes to FastAPI.
			const file = data.get('pdf_file') as File | null;
			if (!file || file.size === 0) {
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			const body = new FormData();
			body.append('pdf_file', file);

			// NOTE: BODY_SIZE_LIMIT=10M must be set in DO App Platform env vars for
			// SvelteKit to accept payloads larger than the 512 KB default (documented
			// blocker in STATE.md). SvelteKit merely forwards the file bytes; the actual
			// Spaces upload is performed by the FastAPI service using boto3.
			// DO_SPACES_* / AWS_* credentials belong to the FastAPI service, not this
			// SvelteKit service — SvelteKit needs none of those env vars.
			let res: Response;
			try {
				res = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs`, {
					method: 'POST',
					headers: { 'X-Admin-Token': ADMIN_TOKEN },
					body,
				});
			} catch {
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			if (!res.ok) {
				return fail(400, { error: 'Could not start the run. Check the URL and try again.' });
			}

			const { id } = await res.json();
			throw redirect(303, `/admin/pipeline/${id}`);
		}
	},
};
