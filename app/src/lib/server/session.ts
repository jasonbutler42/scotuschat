import { createHmac, timingSafeEqual } from 'node:crypto';
import { SESSION_SECRET } from '$env/static/private';

/** Cookie name for the admin session (D-04). */
export const SESSION_COOKIE_NAME = 'scotus_admin_session';

/**
 * Cookie options to use when setting or deleting the session cookie.
 * Plan 02 sets the cookie with these; Plan 03 logout deletes with matching path.
 */
export const sessionCookieOptions = {
	httpOnly: true,
	sameSite: 'strict' as const,
	secure: true,
	maxAge: 86400, // D-02: 24 hours (86400 seconds)
	path: '/'
};

/**
 * Sign a session with an expiry timestamp.
 *
 * Returns a string of the form `${expiryMs}.${hmacHex}` where hmacHex is
 * HMAC-SHA256 of the string `${expiryMs}` keyed by SESSION_SECRET.
 *
 * @param expiryMs - Unix timestamp in milliseconds when the session expires.
 */
export function signSession(expiryMs: number): string {
	const payload = String(expiryMs);
	const hmacHex = createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');
	return `${payload}.${hmacHex}`;
}

/**
 * Verify a session cookie value.
 *
 * Returns true only if the cookie is well-formed, the HMAC signature matches,
 * and the expiry timestamp is in the future.
 *
 * Comparison uses timingSafeEqual to prevent timing oracle attacks (T-06-01).
 * Length mismatch is handled before timingSafeEqual to avoid the throw (T-06-04).
 *
 * @param cookieValue - The raw cookie string, or undefined if absent.
 */
export function verifySession(cookieValue: string | undefined): boolean {
	if (!cookieValue) return false;

	// Split on the last '.' to separate payload from signature.
	const lastDot = cookieValue.lastIndexOf('.');
	if (lastDot === -1) return false;

	const payload = cookieValue.slice(0, lastDot);
	const signature = cookieValue.slice(lastDot + 1);

	if (!payload || !signature) return false;

	// Recompute expected HMAC over the payload.
	const expectedHex = createHmac('sha256', SESSION_SECRET).update(payload).digest('hex');

	const sigBuf = Buffer.from(signature, 'hex');
	const expBuf = Buffer.from(expectedHex, 'hex');

	// Reject if lengths differ before calling timingSafeEqual (which throws on mismatch).
	if (sigBuf.length !== expBuf.length) return false;

	// Constant-time comparison (T-06-01).
	if (!timingSafeEqual(sigBuf, expBuf)) return false;

	// Parse expiry from payload and reject if expired or non-numeric (T-06-03).
	const expiry = parseInt(payload, 10);
	if (isNaN(expiry)) return false;

	return expiry > Date.now();
}
