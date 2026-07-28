/**
 * Preview-only mirror of the Phase 38 docket-value authority contract
 * (api/domain/docket_values.py). Closes item 3 of UAT gap G-38-6's `missing`
 * list: an operator typing an out-of-shape docket value into the Pipeline
 * Runner's docket input previously got no feedback until job failure.
 *
 * The backend remains the sole authority — plan 38-07 enforces this rule at
 * the FastAPI `create_job` boundary and plan 38-08 enforces it again inside
 * the pipeline's filename construction. This module exists only so the
 * operator sees the problem at the control instead of discovering it later
 * as a crashed job; it has no independent write path. It is not itself the
 * sole enforcement point either — the SvelteKit server action re-checks
 * server-side too (see app/src/routes/admin/pipeline/+page.server.ts),
 * because a forged `docket[]` hidden input can bypass this module entirely.
 *
 * Parity is locked by api/tests/test_docket_ui_contract.py, which extracts
 * this module's pattern literal and max-length constant and replays
 * api/tests/fixtures/docket_value_cases.json through Python's `re` module
 * to prove the two languages agree case-for-case.
 */

// ---------------------------------------------------------------------------
// Rule constants — mirror api/domain/docket_values.py exactly. Kept as a
// plain string literal (not only inside the compiled RegExp) so the contract
// test can extract and compare it directly to the Python literal, the single
// canonical copy of this rule.
// ---------------------------------------------------------------------------

export const DOCKET_VALUE_MAX_LENGTH = 64;

// Leading character must be alphanumeric, followed by any run of
// alphanumeric/underscore/hyphen characters. No separator, no dot, no
// quote, no whitespace, and no control character can ever match.
export const DOCKET_VALUE_PATTERN = '^[A-Za-z0-9][A-Za-z0-9_-]*$';

// Built via new RegExp() from the shared literal above rather than an inline
// regex literal, so DOCKET_VALUE_PATTERN is the single thing that has to
// match Python and a reader cannot accidentally edit one of two copies.
const DOCKET_VALUE_RE = new RegExp(DOCKET_VALUE_PATTERN);

export type DocketValueErrorCode = 'empty' | 'length_exceeded' | 'invalid_characters';

/**
 * Deterministic validation error raised by this module — mirrors
 * api.domain.docket_values.DocketValueError's `code` contract so a caller
 * can branch on a stable machine-readable identifier rather than message
 * text.
 */
export class DocketValueError extends Error {
	code: DocketValueErrorCode;

	constructor(code: DocketValueErrorCode, message: string) {
		super(message);
		this.name = 'DocketValueError';
		this.code = code;
	}
}

/**
 * Validate and normalize a single operator-supplied docket value.
 *
 * Ordering is a hard determinism contract, identical to the Python rule:
 * blank check, then length check, then pattern check. Because
 * DOCKET_VALUE_PATTERN is fully anchored (`^...$`) and JavaScript's `$` does
 * not match before a trailing newline, `test()` on the trimmed value gives
 * the same verdict as Python's `re.fullmatch`.
 *
 * Raises DocketValueError with code:
 *   - "empty" when the trimmed value is blank (or raw is null/undefined)
 *   - "length_exceeded" when it exceeds DOCKET_VALUE_MAX_LENGTH
 *   - "invalid_characters" when it does not match DOCKET_VALUE_PATTERN
 *
 * Returns the trimmed value unchanged otherwise.
 */
export function normalizeDocketValue(raw: string | null | undefined): string {
	const value = (raw ?? '').trim();

	if (!value) {
		throw new DocketValueError('empty', 'Docket value cannot be blank.');
	}

	if (value.length > DOCKET_VALUE_MAX_LENGTH) {
		throw new DocketValueError(
			'length_exceeded',
			`Docket value exceeds maximum length of ${DOCKET_VALUE_MAX_LENGTH} characters (got ${value.length}).`
		);
	}

	if (!DOCKET_VALUE_RE.test(value)) {
		throw new DocketValueError(
			'invalid_characters',
			'Docket value contains characters that are not allowed. Only letters, numbers, ' +
				'underscores, and hyphens are permitted, and the value must start with a letter or number.'
		);
	}

	return value;
}

/**
 * Maps a DocketValueError code to the operator-facing sentence shared by
 * DocketPillInput and the Pipeline Runner's SvelteKit server action, so the
 * wording is defined once instead of duplicated at each call site.
 */
export function docketValueErrorMessage(code: DocketValueErrorCode): string {
	switch (code) {
		case 'invalid_characters':
			return 'Dockets may only use letters, numbers, hyphens, and underscores.';
		case 'length_exceeded':
			return `Dockets must be ${DOCKET_VALUE_MAX_LENGTH} characters or fewer.`;
		case 'empty':
			return 'Docket value cannot be blank.';
	}
}
