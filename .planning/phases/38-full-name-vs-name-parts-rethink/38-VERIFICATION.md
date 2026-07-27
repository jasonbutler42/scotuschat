---
phase: 38-full-name-vs-name-parts-rethink
verified: 2026-07-27T17:40:23Z
status: human_needed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open the standalone create form and the person edit form; type into First/Middle/Last/Suffix and confirm the read-only Full Name <output> updates live, shows 'Generated from name parts.', and cannot be typed into directly."
    expected: "Full Name preview matches the canonical First Middle Last, Suffix format live as parts are typed; no input control exists for it."
    why_human: "Live-typing/render behavior and visual layout require a browser; static source checks only confirm the markup is a read-only <output> bound to a $derived preview function, not that it renders/updates correctly on screen."
  - test: "Submit the create/edit form with only a First Name (no Last), then only a Last Name (no First); confirm save succeeds and no 'Enter at least a first or last name.' error appears; then submit with both blank and confirm the error appears, attempted values are preserved, and focus moves to First Name."
    expected: "First-only and last-only saves succeed; blank-both shows the exact locked error copy with focus on First Name and no attempted data lost."
    why_human: "Focus-management and preserved-form-state-after-error are runtime DOM behaviors that cannot be confirmed by static grep of the server action/component source."
  - test: "Open an ambiguous legacy person record (one migration 0022 flagged name_needs_review=true) in the edit form; confirm each of First/Middle/Last/Suffix shows the stacked 'Extracted: {value} / {Band} confidence · Raw: {raw}' hint (or the disabled N/A state for a still-blank field) at both wide and narrow viewport widths, and that clicking the copy affordance copies only the interpreted value."
    expected: "Per-part provenance stack renders correctly and remains usable/readable at narrow widths per 38-FIGMA.md; copy button copies only the displayed value, never the raw/confidence text."
    why_human: "Visual layout/wrapping at responsive widths and the interactive clipboard behavior require a browser; no browser tool is available in this execution environment (flagged by 38-05-SUMMARY.md and 38-06-SUMMARY.md's own human_judgment coverage entries)."
  - test: "On the People directory, click the 'Name review' pill/indicator; confirm it filters to only name_needs_review=true rows while preserving the active tab in the URL, and that the empty state (when no rows match) shows the exact locked copy 'No people need name review' / 'Ambiguous legacy names will appear here for review.'"
    expected: "Filter applies correctly, tab/URL round-trips, and the empty state is distinct from the generic missing-field empty state."
    why_human: "Selected-pill visual state, URL round-trip behavior in a real browser session, and empty-state layout require browser confirmation, consistent with prior phases' precedent for this same click-to-filter mechanism."
  - test: "Exercise DocketPillInput's approved provenance states (editable/read-only, single/multiple pills, mixed confidence within a group, long raw text wrapping, remove-in-edit-mode-only) against the Figma component (38-FIGMA.md node 3:140 / review sheet 3:2) at narrow and wide widths."
    expected: "All approved visual states match the Figma reference; remove control only appears in editable mode; long raw text wraps without truncation or overflow."
    why_human: "Visual/interactive state comparison against an external Figma design reference cannot be done via source-code inspection alone (flagged as human_judgment in 38-05-SUMMARY.md)."
---

# Phase 38: Rethink Full Name vs. name-part fields in the people editor Verification Report

**Phase Goal:** Jason expected that filling in only the component name fields (first/last/middle/suffix) without Full Name would auto-backfill Full Name on save — instead, Full Name is currently required standalone. This phase resolves that: Full Name is no longer operator-editable at all and is derived entirely from the component fields.
**Verified:** 2026-07-27T17:40:23Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Full Name field behavior is resolved per a locked design decision (auto-derived, not independently editable) | ✓ VERIFIED | `38-CONTEXT.md` D-01/D-02 lock "structured name parts are authoritative; Full Name is generated and not independently operator-editable." Backend (`api/schemas/admin_people.py` `PersonUpdate`/`PersonCreateRequest`, `api/schemas/admin_jobs.py` `PersonCreate`) all drop `full_name` as a field and set `ConfigDict(extra="forbid")` — a posted `full_name` is a 422, not silently accepted. Both people-editor Svelte pages render Full Name as a read-only `<output>` (`id="full_name_preview"`), not an `<input>`. |
| 2 | Operator can save a person record after filling in only the component name fields | ✓ VERIFIED | `api/domain/person_names.py::prepare_person_name` enforces "first or last required" (D-09), not full_name. `api/services/admin_people.py::create_person`/`update_person` and `admin_jobs.py::create_person_for_job` all call this shared helper. Both Svelte forms' server actions (`+page.server.ts`) validate only `!first_name && !last_name` with the exact locked copy `Enter at least a first or last name.`, never referencing `full_name`. |
| 3 | Existing Full Name values for already-created people are not corrupted or silently overwritten | ✓ VERIFIED | Migration `0022_person_name_authority.py` never issues an `UPDATE ... full_name = ...` — the column is untouched for every row, confident or ambiguous. Ambiguous rows are flagged `name_needs_review=true` and preserved exactly. The CR-01 code-review BLOCKER (round-trip gate compared against the un-stripped string, aborting the whole migration on any legacy name with leading/trailing whitespace) was found and fixed (`46e1c29f`): the gate now compares against `stripped_full_name`, with a new regression fixture (`high_confidence_leading_trailing_whitespace`, `"  Clarence Thomas  "`) added to the shared `legacy_split_cases` array consumed by both `test_person_names.py` and `test_migration_0022_person_name_authority.py`. All write paths (API PATCH merge, pipeline imports) apply blank-only prefill and never overwrite an operator-set part. |
| 4 | Pipeline/parsing-side changes are identified and applied consistently with the admin editor's behavior | ✓ VERIFIED | `pipeline/commands/import_justices_csv.py`, `import_convokit.py`, and `seed_aliases.py` all import and call `api.domain.person_names.prepare_person_name`/`format_full_name`/`split_legacy_full_name` — the same shared contract the API services and migration use. No independent formatter remains in any batch writer (confirmed by grep across all three files plus `admin_people.py`/`admin_jobs.py`). |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/domain/person_names.py` | Shared normalization/formatting/provenance/split contract | ✓ VERIFIED | 367 lines; `normalize_name_part`, `format_full_name`, `prepare_person_name`, `prepare_name_provenance`, `split_legacy_full_name` all present, pure, no FastAPI/SQLAlchemy imports. |
| `api/tests/fixtures/person_name_cases.json` | Shared Python/TS parity + legacy-split fixtures | ✓ VERIFIED | Contains `format_cases`, `normalization_cases`, `invalid_cases`, `legacy_split_cases` (now includes the CR-01 whitespace regression case). |
| `alembic/versions/0022_person_name_authority.py` | Schema + guarded backfill + rollback | ✓ VERIFIED | Adds `name_needs_review`/`name_extraction_metadata`, backfills via `split_legacy_full_name`, never writes `full_name`, round-trip gate fixed post-review. |
| `api/models/models.py` | Person review/provenance mappings | ✓ VERIFIED | `name_needs_review` (Boolean, non-null, default false), `name_extraction_metadata` (nullable JSONB) present on `Person`. |
| `api/schemas/admin_people.py`, `api/services/admin_people.py` | Central people writer enforcement + Name review filter | ✓ VERIFIED | `full_name` removed from writable schemas, `extra="forbid"`; `create_person`/`update_person` route through `prepare_person_name`; `_missing_fields`/`missing_filters` include `"name review"`. |
| `api/schemas/admin_jobs.py`, `api/services/admin_jobs.py` | Job-scoped writer using shared authority | ✓ VERIFIED | `PersonCreate` drops `full_name`; `create_person_for_job` calls `prepare_person_name` before existing IDOR/state guards; WR-01/WR-03 `role_name` fix applied (`8fb3b163`). |
| `pipeline/commands/import_justices_csv.py`, `import_convokit.py`, `seed_aliases.py` | Shared-format import/seed adoption | ✓ VERIFIED | All three import `api.domain.person_names` helpers; no independent formatter remains. |
| `app/src/lib/components/CopyableExtractedValue.svelte` | Stacked provenance rendering | ✓ VERIFIED | Optional `confidence`/`raw` props gate a two-line `Extracted: {value}` / `{Band} confidence · Raw: {raw}` render path; legacy value-only callers unaffected. |
| `app/src/lib/components/DocketPillInput.svelte` | Docket Pill provenance states | ✓ VERIFIED | Accepts `string | {value, confidence, raw}` union; provenance pills route through the shared primitive. |
| `app/src/lib/personNames.ts` | Preview-only TS mirror | ✓ VERIFIED | `normalizeNamePart`/`formatFullName`/`previewFullName`; parity-tested against the shared JSON fixture via real Node execution (`api/tests/test_phase38_people_ui_contract.py`); never accepts `full_name` as input, no network call. |
| `app/src/routes/admin/people/new/+page.svelte`, `+page.server.ts` | Generated preview, parts-only submit | ✓ VERIFIED | Read-only `<output>` preview; server action reads only `first_name`/`middle_name`/`last_name`/`name_suffix`, never `full_name`. |
| `app/src/routes/admin/people/[id]/+page.svelte`, `+page.server.ts` | Generated preview + per-part provenance editor | ✓ VERIFIED | Same generated-preview pattern; each of First/Middle/Last/Suffix independently renders `CopyableExtractedValue` sourced from `data.person.name_extraction_metadata`. |
| `app/src/routes/admin/people/+page.svelte`, `+page.server.ts` | Name review indicator/filter + empty state | ✓ VERIFIED | `pillLabel()` renders "Name review" Title Case over the existing lowercase filter vocabulary; locked empty-state copy present. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/tests/test_person_names.py` | `api/domain/person_names.py` | direct import | ✓ WIRED | 54 fixture-driven tests import and exercise every exported function. |
| `alembic/versions/0022_person_name_authority.py` | `api/domain/person_names.py` | `split_legacy_full_name`, `format_full_name` | ✓ WIRED | Imported at module top; used in the backfill loop and round-trip gate. |
| `api/services/admin_people.py` | `api/domain/person_names.py` | `prepare_person_name` | ✓ WIRED | `create_person`/`update_person` call it; old local `_derive_full_name` deleted. |
| `api/services/admin_jobs.py` | `api/domain/person_names.py` | `prepare_person_name` | ✓ WIRED | `create_person_for_job` calls it before job/participant guards. |
| `pipeline/commands/import_justices_csv.py` / `import_convokit.py` / `seed_aliases.py` | `api/domain/person_names.py` | shared helper imports | ✓ WIRED | Confirmed via grep — all three files import and call the shared contract functions. |
| `app/src/routes/admin/people/[id]/+page.svelte` | `app/src/lib/components/CopyableExtractedValue.svelte` | per-part stacked extracted reference | ✓ WIRED | Four independent `<CopyableExtractedValue>` instances, one per name part, driven by `data.person.name_extraction_metadata`. |
| `app/src/lib/personNames.ts` | `api/tests/fixtures/person_name_cases.json` | shared parity fixture, Node-executed | ✓ WIRED | `test_phase38_people_ui_contract.py` shells out to `node` to run the real `.ts` file against the shared fixture (genuine cross-language parity, not a source-text match). |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PEOPLE-09 | 38-01 through 38-06 | Full Name field behavior locked (auto-derived) and executed end-to-end | ✓ SATISFIED | `.planning/REQUIREMENTS.md:32,84` marks PEOPLE-09 complete/Phase 38. All 6 plans' `requirements: [PEOPLE-09]` frontmatter accounted for; no orphaned requirement IDs found for Phase 38 in REQUIREMENTS.md. |

No other requirement IDs map to Phase 38 in REQUIREMENTS.md — PEOPLE-09 is the only requirement and is fully accounted for across all 6 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/schemas/admin_people.py` | 263, 273 | `TODO(D-10): orphaned by Phase 27 — ... flagged here rather than deleted` | ℹ️ Info | Pre-existing Phase 27 debt marker (unrelated to this phase's D-10 legacy-split-confidence decision — same label, different phase), references formal follow-up ("Plan 27-05 deletes this... caller"). Not introduced by Phase 38, not a blocker. |
| `api/services/admin_people.py` | 613 | Same `TODO(D-10)` marker | ℹ️ Info | Same as above. |

No debt markers were found in any file this phase created or substantively rewrote (`person_names.py`, migration 0022, `admin_jobs.py`, pipeline commands, or any of the 8 people-editor/directory frontend files). The two pre-existing markers reference formal follow-up work and predate Phase 38.

### Code Review Findings (already resolved)

The dispatched code review (`38-REVIEW.md`) found 1 BLOCKER and 3 Warnings; all 4 were fixed and verified against the codebase during this verification pass:

| ID | Finding | Fix Commit | Verified |
|----|---------|-----------|----------|
| CR-01 | Migration 0022 round-trip gate compared against un-stripped `full_name`, aborting the entire migration on any legacy row with leading/trailing whitespace | `46e1c29f` | ✓ Confirmed: gate now compares `recomputed != stripped_full_name`; new fixture case added to shared `legacy_split_cases`. |
| WR-01 | `create_person_for_job`'s `PersonResponse.role_name` had no backing attribute, risking `AttributeError` | `8fb3b163` | ✓ Confirmed: `person.__dict__["role_name"] = role_name_value` set unconditionally before return. |
| WR-02 | Dead `?incomplete=1` link on pipeline job detail page | `bb0dd633` | ✓ Confirmed: link now points to `/admin/people?tab=bench&missing=name%20review`, the working Name review filter. |
| WR-03 | Resolved Role name never captured for `role_name` response field | `8fb3b163` (combined with WR-01) | ✓ Confirmed: `role_name_value` captured on both the role_name-lookup and role_id-direct branches. |

### Behavioral Spot-Checks / Probe Execution

Per the dispatch context, a full regression run (`api/tests/` + `pipeline/tests/`, 588 passed, 5 xfailed, 0 failed) was already completed and confirmed clean against this HEAD by the orchestrator immediately before this verification dispatch — this exercises the DB-backed migration integration tests (upgrade/downgrade/round-trip/repeatability), the API/service PATCH-merge and mass-assignment tests, and all three pipeline import/seed integration tests. This verifier additionally spot-checked (via direct file reads and grep, no re-run of the suite):

- `api/tests/test_migration_0022_person_name_authority.py` generically loads `legacy_split_cases` from the shared fixture (confirmed via `_load_legacy_split_cases()`), so the CR-01 fix's new whitespace regression case is automatically exercised by the already-passing suite without further code changes.
- No frontend (`npm run check`) re-run was performed in this verification pass; all 6 plan SUMMARYs report `npm run check` passing with 0 errors, and no frontend file was touched by the review-fix pass (only backend/Alembic files and one Svelte href string were changed in `38-REVIEW-FIX.md`).

### Human Verification Required

5 items require browser confirmation (no browser tool is available in this execution environment; already flagged as `human_judgment: true` in `38-05-SUMMARY.md` and `38-06-SUMMARY.md`) — see frontmatter `human_verification` list above for full detail:

1. Live-updating generated Full Name preview (create + edit forms)
2. First-only/last-only save success, blank-both error copy + preserved attempted values + focus-on-error
3. Per-part stacked provenance rendering (narrow/wide widths) and copy-only-interpreted-value behavior on an ambiguous legacy record
4. People directory "Name review" pill filter/tab-URL preservation and exact empty-state copy
5. Docket Pill approved provenance states against the Figma reference

### Gaps Summary

No gaps found. All 4 roadmap success criteria and all plan-level must-haves resolve to VERIFIED against the actual codebase (not just SUMMARY.md claims): the domain contract, migration, API/service enforcement, pipeline adoption, and frontend UI all consistently route through one shared `api.domain.person_names` authority, `full_name` is fully removed as a client-writable/operator-editable field, legacy data preservation is intact (including the now-fixed CR-01 round-trip gate), and the one-time code-review BLOCKER plus all 3 Warnings are confirmed fixed in the code. The only open items are UI/visual browser confirmations that this environment cannot perform and that the executing plans themselves already flagged as requiring human judgment — these do not indicate a missing or broken implementation, only unconfirmed visual/interactive polish.

---

_Verified: 2026-07-27T17:40:23Z_
_Verifier: Claude (gsd-verifier)_
