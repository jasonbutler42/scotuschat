import { redirect } from '@sveltejs/kit';
import type { Handle } from '@sveltejs/kit';
import { verifySession, SESSION_COOKIE_NAME } from '$lib/server/session';

/**
 * SvelteKit auth guard — the sole auth checkpoint for all /admin/* routes (D-05).
 *
 * Runs before every load function and +server.ts endpoint handler, so both page
 * requests and API endpoints under /admin are protected.
 *
 * D-07: /admin/login is publicly accessible — never redirected.
 * D-10: Guard must not redirect the login page itself (no infinite redirect loop).
 * D-05: hooks.server.ts is the sole checkpoint; layout guards alone do not
 *       protect +server.ts endpoints.
 */
export const handle: Handle = async ({ event, resolve }) => {
	const path = event.url.pathname;

	const isAdminArea = path === '/admin' || path.startsWith('/admin/');
	// D-07, D-10: login route is publicly accessible — never redirect it.
	const isLoginRoute = path === '/admin/login' || path.startsWith('/admin/login/');

	// Always set locals.session so downstream load functions can read it.
	const cookie = event.cookies.get(SESSION_COOKIE_NAME);
	const valid = verifySession(cookie);
	event.locals.session = valid;

	if (isAdminArea && !isLoginRoute && !valid) {
		throw redirect(302, '/admin/login');
	}

	return resolve(event);
};
