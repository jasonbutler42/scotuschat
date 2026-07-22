---
phase: 37-tenure-seat-as-chief-associate-toggle
verified: 2026-07-21T23:15:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text — Verification Report

**Phase Goal:** During Phase 27 UAT, Jason asked for the tenure-row Seat field (currently free text) to become the same segmented-toggle component used for the Bench/Advocate choice, since for a Justice it's really just Chief or Associate. The open design question (numbered-seat detail dropped vs retained vs reconciled) was resolved during discuss-phase. The phase must deliver the Chief/Associate toggle across database, API, import, editor, and display with no silent migration data loss.
**Verified:** 2026-07-21T23:15:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Derived from ROADMAP.md Success Criteria (§Phase 37) and merged with the five plans' `must_haves.truths`.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tenure Seat is captured via a decision-backed UI control (binary Chief/Associate) instead of unconstrained free text | ✓ VERIFIED | `app/src/routes/admin/people/[id]/+page.svelte:639-710` — free-text seat input removed, replaced with `<fieldset>`/`role="radiogroup"` of two native radios (`chief`/`associate`); discuss-phase decision log (37-DISCUSSION-LOG.md:21) confirms binary model was the resolved design. |
| 2 | Existing `court_tenures.seat` data (including numbered-seat rows) is preserved or migrated per the resolved design with no silent data loss | ✓ VERIFIED | Staged migration: 0020 rename-only (no data change) → `scripts/migrate_tenure_offices.py` (signed dry-run report, explicit per-id resolutions required for blank/unrecognized values, drift-checked atomic execute) → 0021 (CHECK+NOT NULL only after preflight finds zero unresolved rows). `tests/test_migrate_tenure_offices.py` (28 passed) covers report integrity, tamper/overwrite refusal, transactional drift, rollback, and downgrade ordering. |
| 3 | Operator can set/change a person's tenure Office through the new control and it round-trips through save and reload | ✓ VERIFIED | `app/tests/tenure-office.browser.test.mjs` (11/11 passed) exercises hidden-JSON serialization, server-action allowlist/validation, and atomic Save-Person persistence; `api/services/admin_people.py::_replace_tenures` validates-before-mutate and writes `office` inside the existing profile-save transaction. |
| 4 | Every active backend and import write accepts exactly chief or associate and uses office end to end | ✓ VERIFIED | `api/schemas/admin_people.py::TenureWrite.office: Literal["chief","associate"]`; `api/models/models.py` — `CourtTenure.office` NOT NULL + named CHECK; `pipeline/commands/import_justices_csv.py` emits canonical `OFFICE_CHIEF`/`OFFICE_ASSOCIATE` from CSV section classification. `rg -n "\bseat\b"` confirms zero active identifiers outside documented exceptions (audit script below). |
| 5 | Associate-to-Chief elevation remains two dated tenure rows | ✓ VERIFIED | `pipeline/tests/test_import_justices_csv.py::test_elevated_justice_gets_two_tenures`, `::test_idempotent_rerun_creates_no_duplicates` pass; dedup key changed to `(person_id, office, start_date)`. |
| 6 | Every read-only tenure surface uses Office data and formal "Chief Justice"/"Associate Justice" titles, with argument-date selection/fallback unchanged | ✓ VERIFIED | `api/services/speakers.py::_tenure_role_name` and `api/services/admin_people.py::_bench_role_and_missing_tenure` both route through `office_title()`; `SpeakerPopover.svelte` renders formal titles via its own `officeTitle()`. `app/tests/tenure-public-title.browser.test.mjs` (real headless-Edge CDP run) passed: 1/1, asserting exact formal-title text and absence of raw/generic labels. |
| 7 | Invalid legacy values remain visible and block save until explicitly corrected (no silent coercion) | ✓ VERIFIED | Editor stores `office: null` + `invalidOfficeOriginal` verbatim for unrecognized/blank legacy rows (never guesses/defaults); `role="alert"` message, `aria-describedby`/`aria-invalid` on the radiogroup, first-invalid focus on save attempt — covered by 4 of the 11 `tenure-office.browser.test.mjs` assertions. Note: this holds for the primary (Bench/Justice) path; see documented non-blocking finding WR-02 below for a narrow Advocate-toggle edge case. |
| 8 | The complete staged migration and application work together before the final suite passes (blocking gate) | ✓ VERIFIED | Disposable-DB proof (0019→0020→audit→execute→0021→downgrade/re-upgrade) ran the five application modules against the fully-constrained schema (149 passed per 37-05-SUMMARY); independently reproduced here: full pytest suite **527 passed, 5 xfailed**; `tests/test_migrate_tenure_offices.py` **28 passed**; `npm run check` **0 errors**; `node app/tests/tenure-office.browser.test.mjs` **11 passed**; `node app/tests/tenure-public-title.browser.test.mjs` **1 passed**; `scripts/audit_tenure_seat_identifiers.py` **PASS** (21 documented exceptions, zero unclassified hits). |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0020_rename_tenure_seat_to_office.py` | nullable string-compatible rename, no data change | ✓ VERIFIED | Confirmed via direct read: `alter_column` rename only, `nullable=True` preserved both directions. |
| `scripts/migrate_tenure_offices.py` | dry-run/execute CLI with signed report, explicit resolutions, atomic transaction | ✓ VERIFIED | Present, substantive, exercised by 28 passing tests; `hmac.compare_digest` used for report integrity (per 37-02-SUMMARY deviation note). |
| `alembic/versions/0021_constrain_tenure_office.py` | named CHECK + NOT NULL, preflight refuses unresolved data | ✓ VERIFIED | Confirmed via direct read: preflight `RuntimeError` on any `office IS NULL OR office NOT IN (...)`, then `create_check_constraint`/`alter_column(nullable=False)`; downgrade drops constraint before relaxing nullability. |
| `api/models/models.py` | `CourtTenure.office`, `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`/`VALID_OFFICES`, `office_title()` | ✓ VERIFIED (with follow-up hardening) | Column/constants present; `office_title()` itself still raises `KeyError` by design, but see key-link note below — all three call sites now catch it. |
| `api/schemas/admin_people.py` | strict `TenureWrite` (write) / tolerant `TenureRow` (read) split | ✓ VERIFIED | `TenureWrite.office: Literal["chief","associate"]`; `TenureRow.office: Optional[str]` — confirmed via read. |
| `pipeline/commands/import_justices_csv.py` | canonical office classification, idempotent elevation import | ✓ VERIFIED | `_SECTION_OFFICE_VALUES` maps CSV section headers to `OFFICE_CHIEF`/`OFFICE_ASSOCIATE`; dedup on `(person_id, office, start_date)`. |
| `app/src/routes/admin/people/[id]/+page.svelte` | approved Office segmented radio editor | ✓ VERIFIED | Free-text seat input removed; native radiogroup with 44px targets, focus/selected styling, `role="radiogroup"`/`aria-invalid`/`aria-describedby`. |
| `app/src/routes/admin/people/[id]/+page.server.ts` | validated atomic Office serialization + failure restoration | ✓ VERIFIED | Exercised by `tenure-office.browser.test.mjs`'s server-action allowlist/rehydration assertions (all pass). |
| `scripts/audit_tenure_seat_identifiers.py` | allowlist-based stale-identifier gate, nonzero exit on unclassified hits | ✓ VERIFIED | Ran directly: `PASS: no unclassified 'seat' identifiers found ... 21 documented exception(s), all matched.` |
| `app/tests/tenure-office.browser.test.mjs` | Office radio/keyboard/invalid-state/recovery contract | ✓ VERIFIED | Ran directly: 11/11 passed. |
| `app/tests/tenure-public-title.browser.test.mjs` | public formal-title rendering regression | ✓ VERIFIED | Ran directly (real headless-Edge CDP): 1/1 passed. |
| `tests/test_migrate_tenure_offices.py` | migration safety specification | ✓ VERIFIED | Ran directly: 28/28 passed. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `scripts/migrate_tenure_offices.py` | `court_tenures.office` | bound SQL in one transaction | ✓ WIRED | Single `engine.begin()` block; row locks, drift recheck, all-or-none update — confirmed in 37-02-SUMMARY and exercised by passing tests. |
| `alembic/versions/0021_...` | `scripts/migrate_tenure_offices.py` | preflight requires normalization postcondition | ✓ WIRED | 0021's `upgrade()` runs a `COUNT(*)` preflight and raises `RuntimeError` with a remediation pointer to the script if any row is unresolved. |
| `api/services/admin_people.py` | `api/models/models.py` | validated atomic tenure replacement | ✓ WIRED | `_replace_tenures` validates every row against `VALID_OFFICES` before delete; writes `CourtTenure.office`. |
| `pipeline/commands/import_justices_csv.py` | `court_tenures.office` | canonical section mapping | ✓ WIRED | `_SECTION_OFFICE_VALUES` → `CourtTenure(office=...)`. |
| `api/services/speakers.py` / `api/services/admin_people.py` | `api/models/models.py::office_title()` | formal-title projection, now exception-safe | ✓ WIRED | **Critical review finding CR-01 (unhandled `KeyError` for a non-canonical office value during the 0020→0021 rollout window) was fixed in follow-up commit `5c09d5d7`, confirmed by direct diff read**: both `_bench_role_and_missing_tenure` (admin_people.py) and `_tenure_role_name` (speakers.py, both call sites) now wrap `office_title()` in `try/except KeyError` and degrade to the existing `missing_tenure=True` / `None` sentinel rather than raising a 500. `office_title()` itself is unchanged (still raises by design per its docstring) — the fix is at the three call sites, exactly as the instructions asked to confirm. |
| `app/src/lib/components/SpeakerPopover.svelte` | `api/schemas/speakers.py` | office response contract | ✓ WIRED | `TenureEntry.office` (canonical value) flows to `officeTitle()` at the final render boundary; confirmed by passing `tenure-public-title.browser.test.mjs`. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PEOPLE-08 | 37-01 through 37-05 (all 5 plans) | Tenure Seat captured via decision-backed UI control instead of unconstrained free text | ✓ SATISFIED | REQUIREMENTS.md marks PEOPLE-08 "Complete" for Phase 37; cross-checked against all 8 truths above — no contradicting evidence found. No orphaned Phase-37 requirement IDs exist beyond PEOPLE-08. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/schemas/admin_people.py` | 196, 206 | `TODO(D-10): orphaned by Phase 27` | ℹ️ Info | Pre-existing Phase-27 debt marker, unrelated to Phase 37's office/tenure logic; not introduced or touched by this phase. Not a blocker. |
| `api/services/admin_people.py` | 551 | `TODO(D-10): orphaned by Phase 27` | ℹ️ Info | Same as above. |

No `TBD`/`FIXME`/`XXX` markers found in any of the 24 files this phase touched (per 37-REVIEW.md's file list). No stub patterns (empty handlers, static `[]`/`{}` returns feeding real UI, `console.log`-only implementations) found in the phase's core deliverables.

### Documented Non-Blocking Findings (from Code Review, fully verified present — not deferred to human judgment)

These were confirmed to still exist by direct code read during this verification (not "uncertain" — hence not routed as Human Verification items). None invalidate a must-have truth. They are carried forward from 37-REVIEW.md as Warning-severity, unaddressed by any follow-up commit, and worth an explicit accept/schedule-follow-up decision by the operator:

1. **WR-02 — Save can become unreachable if an invalid legacy tenure row exists while "Advocate" is selected.** `app/src/routes/admin/people/[id]/+page.svelte:584` gates the entire "Tenure Periods" section (including the only Remove-button path) behind `{#if isJustice}`, but `firstInvalidOfficeIndex()` (line 138) checks `tenureRows` unconditionally. An operator with a legacy-invalid row who switches to Advocate has no way to reach that row's Remove button while Save stays blocked, other than toggling back to Bench. Not a data-loss bug (toggling back restores the escape path) and low real-world likelihood post-migration (see below), but a genuine UX dead-end.
2. **WR-01 — Nondeterministic office-title selection on overlapping tenure windows in the admin Resolve card.** `api/services/admin_people.py`'s `list_resolve_rows_for_job` tenure prefetch has no `ORDER BY`, unlike the sibling `speakers.py` lookup (`.order_by(CourtTenure.person_id.asc(), CourtTenure.start_date.asc())`), so the two surfaces can disagree on which formal title to show for a person with two overlapping tenure windows.
3. **WR-03 — `is_bench` derived from tenure-row count, not `side`, in the public argument page.** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:36` computes `is_bench` from `tenure.length > 0` rather than the payload's own authoritative `side` field, so a Justice with zero tenure rows renders with Advocate popover styling. Pre-existing (predates Phase 37) but sits directly upstream of this phase's title-rendering path.

None of these affect the phase's must-have truths: WR-02 is reachable only by an invalid legacy row, and since migration 0021's CHECK+NOT NULL is already applied to both the dev and shared databases (confirmed by the full test suite and the disposable-DB proof passing against the fully-constrained schema), no currently-loadable person can have an invalid `office` value in practice — WR-02 is a residual defense-in-depth gap for a state the schema no longer permits, not a live blocker. WR-01 and WR-03 are pre-existing/adjacent code-quality issues the reviewer classified Warning (not Critical) and explicitly scoped as optional follow-up.

### Gaps Summary

No blocking gaps found. The one Critical review finding (CR-01: `office_title()` unhandled `KeyError` during the 0020→0021 rollout window) was verified fixed in follow-up commit `5c09d5d7` — both call sites in `api/services/speakers.py` and `api/services/admin_people.py` now catch `KeyError` and degrade to the existing missing-tenure/`None` sentinel, confirmed by direct diff and current-file read.

All three ROADMAP Success Criteria are independently verified:
1. Binary Chief/Associate control replaces free text — confirmed in the editor markup.
2. No silent data loss — confirmed via the staged rename→audit→constrain migration and its 28-test regression suite, plus the discuss-phase decision log matching the implemented normalization rules.
3. Round-trip through save/reload — confirmed via the browser test suite and the atomic service-layer replacement.

All automated gates were independently re-run in this verification session (not merely trusted from SUMMARY.md):
- Full pytest suite: `527 passed, 5 xfailed` (matches claim)
- `tests/test_migrate_tenure_offices.py`: `28 passed` (matches claim)
- `npm run check --prefix app`: `0 errors, 19 warnings` (matches claim)
- `node app/tests/tenure-office.browser.test.mjs`: `11 passed` (matches claim)
- `node app/tests/tenure-public-title.browser.test.mjs`: `1 passed` (matches claim — real CDP browser run)
- `scripts/audit_tenure_seat_identifiers.py`: `PASS` (matches claim)

Three Warning-level review findings (WR-01, WR-02, WR-03) remain open and unaddressed by any follow-up commit; they are documented above as non-blocking, fully-verified findings for the operator's awareness (recommend triage into a follow-up phase/backlog item), not gaps against this phase's goal achievement.

---

_Verified: 2026-07-21T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
