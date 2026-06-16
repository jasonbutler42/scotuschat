import { redirect } from '@sveltejs/kit';
import type { Actions } from './$types';
import { SESSION_COOKIE_NAME } from '$lib/server/session';

export const actions: Actions = {
	logout: async ({ cookies }) => {
		// Delete the session cookie using path '/' — must match sessionCookieOptions.path
		// used when the cookie was set in Plan 02 (admin/login/+page.server.ts).
		// A path mismatch would leave the cookie in the browser (T-06-12).
		cookies.delete(SESSION_COOKIE_NAME, { path: '/' });

		// Redirect to login — the deleted cookie cannot pass verifySession on the next
		// request, so the Plan 01 hooks.server.ts guard will also redirect to login
		// if any tab still tries to access /admin (AUTH-03: immediate invalidation).
		throw redirect(302, '/admin/login');
	}
};
