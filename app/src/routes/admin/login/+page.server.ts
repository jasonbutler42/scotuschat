import { ADMIN_USERNAME, ADMIN_PASSWORD } from '$env/static/private';
import { redirect, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { timingSafeEqual } from 'node:crypto';
import { signSession, SESSION_COOKIE_NAME, sessionCookieOptions } from '$lib/server/session';

export const load: PageServerLoad = async ({ locals }) => {
	// D-06: redirect already-authenticated operators away from the login page
	if (locals.session) {
		throw redirect(302, '/admin');
	}
	return {};
};

export const actions: Actions = {
	default: async ({ request, cookies }) => {
		const data = await request.formData();
		const username = (data.get('username') as string) ?? '';
		const password = (data.get('password') as string) ?? '';

		// Constant-time credential comparison (T-06-07).
		// Guard length mismatch before calling timingSafeEqual, which throws if
		// buffers have different byte lengths.
		const userBuf = Buffer.from(username);
		const expectedUserBuf = Buffer.from(ADMIN_USERNAME);
		const passBuf = Buffer.from(password);
		const expectedPassBuf = Buffer.from(ADMIN_PASSWORD);

		const usernameMatch =
			userBuf.length === expectedUserBuf.length &&
			timingSafeEqual(userBuf, expectedUserBuf);

		const passwordMatch =
			passBuf.length === expectedPassBuf.length &&
			timingSafeEqual(passBuf, expectedPassBuf);

		// T-06-08: require BOTH to match; no cookie on partial match.
		// D-13: single generic message for all failure modes — no enumeration.
		if (!usernameMatch || !passwordMatch) {
			return fail(401, { error: 'Invalid username or password.' });
		}

		// Success — sign the session and set the cookie (D-02, D-03).
		const expiry = Date.now() + 86400_000; // 24 hours
		const cookieValue = signSession(expiry);
		cookies.set(SESSION_COOKIE_NAME, cookieValue, sessionCookieOptions);

		// D-06: redirect to admin dashboard after login.
		throw redirect(302, '/admin');
	}
};
