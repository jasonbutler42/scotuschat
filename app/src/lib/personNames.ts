/**
 * Preview-only mirror of the Phase 38 person-name authority contract
 * (api/domain/person_names.py). Covers D-01, D-02, D-05–D-09 from
 * .planning/phases/38-full-name-vs-name-parts-rethink/38-CONTEXT.md:
 *
 *   - normalizeNamePart / formatFullName / previewFullName: whitespace
 *     normalization and the canonical `First Middle Last, Suffix` display
 *     format, matching the backend byte-for-byte.
 *
 * This module NEVER accepts a `full_name` input and NEVER submits anything —
 * it exists purely to render a live, read-only Full Name preview in the
 * standalone create and person edit forms while the operator types name
 * parts. The backend (api.domain.person_names.prepare_person_name) remains
 * the sole persistence authority (D-01, D-03) — a client can never author
 * `full_name` (T-38-16); this module cannot be used to do so either, since
 * it has no write path at all.
 *
 * Parity is locked by api/tests/test_phase38_people_ui_contract.py against
 * the same api/tests/fixtures/person_name_cases.json fixture Python's own
 * api/tests/test_person_names.py consumes.
 */

// ---------------------------------------------------------------------------
// Column bounds — mirror api/domain/person_names.py exactly (Person columns,
// api/models/models.py). Used only to keep the live preview from silently
// diverging from what the backend will ultimately accept; the backend is
// still the sole authoritative validator at submit time.
// ---------------------------------------------------------------------------

export const FIRST_NAME_MAX_LENGTH = 150;
export const MIDDLE_NAME_MAX_LENGTH = 150;
export const LAST_NAME_MAX_LENGTH = 150;
export const NAME_SUFFIX_MAX_LENGTH = 50;
export const FULL_NAME_MAX_LENGTH = 300;

type NamePartField = 'first_name' | 'middle_name' | 'last_name' | 'name_suffix';

const PART_BOUNDS: Record<NamePartField, number> = {
	first_name: FIRST_NAME_MAX_LENGTH,
	middle_name: MIDDLE_NAME_MAX_LENGTH,
	last_name: LAST_NAME_MAX_LENGTH,
	name_suffix: NAME_SUFFIX_MAX_LENGTH,
};

const WHITESPACE_RE = /\s+/g;

/**
 * Deterministic validation error raised by this module — mirrors
 * api.domain.person_names.PersonNameError's `code` contract so a caller can
 * branch on a stable machine-readable identifier rather than message text.
 */
export class PersonNameError extends Error {
	code: string;

	constructor(code: string, message: string) {
		super(message);
		this.name = 'PersonNameError';
		this.code = code;
	}
}

/**
 * Trim and collapse internal whitespace; map blank to null.
 *
 * Never changes capitalization or punctuation (D-06/D-07) — initials,
 * hyphens, apostrophes, particles, compound values, and suffix spelling are
 * preserved exactly as authored, identical to the Python implementation.
 * Throws PersonNameError (never truncates) when the normalized value exceeds
 * the column bound for `fieldName`.
 */
export function normalizeNamePart(
	raw: string | null | undefined,
	fieldName: NamePartField
): string | null {
	if (raw === null || raw === undefined) return null;
	const collapsed = raw.trim().replace(WHITESPACE_RE, ' ');
	if (!collapsed) return null;
	const bound = PART_BOUNDS[fieldName];
	if (bound !== undefined && collapsed.length > bound) {
		throw new PersonNameError(
			'length_exceeded',
			`${fieldName} exceeds maximum length of ${bound} characters (got ${collapsed.length})`
		);
	}
	return collapsed;
}

/**
 * Canonical `First Middle Last, Suffix` formatter (D-05) — byte-for-byte
 * mirror of api.domain.person_names.format_full_name. Blank Middle/Suffix
 * are omitted without leaving extra spaces or punctuation. Callers are
 * expected to have already normalized each part via normalizeNamePart —
 * this function does not re-trim or reject per-part length, only the
 * derived full_name's own compatibility bound.
 */
export function formatFullName(
	first: string | null | undefined,
	middle: string | null | undefined,
	last: string | null | undefined,
	suffix: string | null | undefined
): string {
	const nameParts = [first, middle, last].filter((p): p is string => Boolean(p));
	let fullName = nameParts.join(' ');
	if (suffix) {
		fullName = fullName ? `${fullName}, ${suffix}` : suffix;
	}
	if (fullName.length > FULL_NAME_MAX_LENGTH) {
		throw new PersonNameError(
			'full_name_length_exceeded',
			`full_name exceeds maximum length of ${FULL_NAME_MAX_LENGTH} characters (got ${fullName.length})`
		);
	}
	return fullName;
}

export interface PreviewNameParts {
	first: string | null | undefined;
	middle: string | null | undefined;
	last: string | null | undefined;
	suffix: string | null | undefined;
}

/**
 * Live, read-only Full Name preview (D-01, D-02, D-05–D-09).
 *
 * Normalizes each part exactly like the backend, then returns the canonical
 * `First Middle Last, Suffix` string once at least First Name or Last Name
 * is present after normalization (D-09) — otherwise returns 'N/A' (the
 * UI-SPEC's locked empty-preview copy). A momentarily over-length keystroke
 * degrades to 'N/A' rather than throwing through the UI layer; the backend
 * remains the authoritative validator at submit time (this helper is never
 * used to submit or persist anything — see module docstring).
 */
export function previewFullName(parts: PreviewNameParts): string {
	let normFirst: string | null;
	let normMiddle: string | null;
	let normLast: string | null;
	let normSuffix: string | null;
	try {
		normFirst = normalizeNamePart(parts.first, 'first_name');
		normMiddle = normalizeNamePart(parts.middle, 'middle_name');
		normLast = normalizeNamePart(parts.last, 'last_name');
		normSuffix = normalizeNamePart(parts.suffix, 'name_suffix');
	} catch {
		return 'N/A';
	}

	if (!normFirst && !normLast) return 'N/A';

	try {
		return formatFullName(normFirst, normMiddle, normLast, normSuffix);
	} catch {
		return 'N/A';
	}
}
