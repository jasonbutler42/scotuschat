---
phase: 38-full-name-vs-name-parts-rethink
verified: 2026-07-27T22:15:00Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 4/4
  gaps_closed:

    - "G-38-6: authenticated-admin path-traversal / arbitrary-file-write primitive in docket-value handling, discovered during the original UAT pass on 38-01..38-06 and closed by Plans 38-07 through 38-10"
  gaps_remaining: []
  regressions: []
human_verification:

  - test: "Open the standalone create form and the person edit form; type into First/Middle/Last/Suffix and confirm the read-only Full Name <output> updates live, shows 'Generated from name parts.', and cannot be typed into directly."
    expected: "Full Name preview matches the canonical First Middle Last, Suffix format live as parts are typed; no input control exists for it."
    why_human: "Live-typing/render behavior and visual layout require a browser; static source checks only confirm the markup is a read-only <output> bound to a $derived preview function, not that it renders/updates correctly on screen."

  - test: "Submit the create/edit form with only a First Name (no Last), then only a Last Name (no First); confirm save succeeds and no 'Enter at least a first or last name.' error appears; then submit with both blank and confirm the error appears, attempted values are preserved, and focus moves to First Name."
    expected: "First-only and last-only saves succeed; blank-both shows the exact locked error copy with focus on First Name and no attempted data lost."
    why_human: "Focus-management and preserved-form-state-after-error are runtime DOM behaviors that cannot be confirmed by static grep of the server action/component source."

  - test: "Open an ambiguous legacy person record (one migration 0022 flagged name_needs_review=true) in the edit form; confirm each of First/Middle/Last/Suffix shows the stacked 'Extracted: {value} / {Band} confidence · Raw: {raw}' hint (or the disabled N/A state for a still-blank field) at both wide and narrow viewport widths, and that clicking the copy affordance copies only the interpreted value."
    expected: "Per-part provenance stack renders correctly and remains usable/readable at narrow widths per 38-FIGMA.md; copy button copies only the displayed value, never the raw/confidence text."
    why_human: "Visual layout/wrapping at responsive widths and the interactive clipboard behavior require a browser; already exercised once in 38-UAT.md Test 3 (pass) but that is a one-time human session recorded in this phase's own artifacts, not a re-runnable automated check for future regressions."

  - test: "On the People directory, click the 'Name review' pill/indicator; confirm it filters to only name_needs_review=true rows while preserving the active tab in the URL, and that the empty state shows the exact locked copy."
    expected: "Filter applies correctly, tab/URL round-trips, and the empty state is distinct from the generic missing-field empty state."
    why_human: "Selected-pill visual state and URL round-trip behavior in a real browser session require browser confirmation; already exercised once in 38-UAT.md Test 4 (pass)."

  - test: "Exercise DocketPillInput's approved provenance states (editable/read-only, single/multiple pills, mixed confidence within a group, long raw text wrapping, remove-in-edit-mode-only) against the Figma component reference at narrow and wide widths."
    expected: "All approved visual states match the Figma reference; remove control only appears in editable mode; long raw text wraps without truncation or overflow."
    why_human: "Visual/interactive state comparison against an external Figma design reference cannot be done via source-code inspection alone; already exercised once in 38-UAT.md Test 5 (pass)."
---

# Phase 38: Rethink Full Name vs. name-part fields in the people editor — Verification Report (Full Final State, 10/10 Plans)

**Phase Goal:** Jason expected that filling in only the component name fields (first/last/middle/suffix) without Full Name would auto-backfill Full Name on save — instead, Full Name was required standalone. Direction locked during discuss-phase: stop making Full Name operator-editable; derive it entirely from the component fields.

**Verified:** 2026-07-27T22:15:00Z
**Status:** human_needed
**Re-verification:** Yes — supersedes the stale `38-VERIFICATION.md` written before gap G-38-6 was discovered. This report covers the full final state of all 10 plans (38-01 through 38-10), including the three-layer G-38-6 security gap closure and its consolidated regression gate.

**Note on this being a re-verification:** The previous VERIFICATION.md (status: `passed`, 4/4) only covered plans 38-01–38-06. It predates the discovery of G-38-6 during UAT and is fully superseded by this report. All 4 original roadmap-success-criteria truths were re-checked here (not merely carried forward) plus 4 new truths added for the gap-closure plans (38-07–38-10).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Full Name field behavior is resolved per a locked design decision (auto-derived, not independently editable) | ✓ VERIFIED | `api/schemas/admin_people.py` (`PersonUpdate`/`PersonCreateRequest`) and `api/schemas/admin_jobs.py` (`PersonCreate`) all drop `full_name` as a field and set `ConfigDict(extra="forbid")`. Both people-editor Svelte pages render Full Name as a read-only `<output>`, not an `<input>`. Unchanged since the prior verification; re-confirmed by direct file read. |
| 2 | Operator can save a person record after filling in only the component name fields | ✓ VERIFIED | `api/domain/person_names.py::prepare_person_name` enforces "first or last required," never `full_name`. `create_person`/`update_person`/`create_person_for_job` all route through it. `api/tests/test_person_names.py` (54 passed) re-run and green. |
| 3 | Existing Full Name values for already-created people are not corrupted or silently overwritten | ✓ VERIFIED | Migration `0022_person_name_authority.py` never writes `full_name`; round-trip gate (CR-01 fix, commit `46e1c29f`) compares against the stripped value. `api/tests/test_migration_0022_person_name_authority.py` re-run and green (part of the 54-passed/7-skipped run; DB-gated cases skip without `DATABASE_URL`, consistent with this WSL sandbox's documented Postgres-unreachable constraint). |
| 4 | Pipeline/parsing-side changes are identified and applied consistently with the admin editor's behavior | ✓ VERIFIED | `pipeline/commands/import_justices_csv.py`, `import_convokit.py`, `seed_aliases.py` all import `api.domain.person_names` helpers — grep-confirmed, no independent formatter remains. |
| 5 (gap closure) | The G-38-6 authenticated-admin path-traversal / arbitrary-file-write primitive is closed at its authoritative boundary | ✓ VERIFIED | `api/domain/docket_values.py::normalize_docket_value` (allow-list `^[A-Za-z0-9][A-Za-z0-9_-]*$` + 64-char cap) is wired into `_normalize_dockets` in `api/routers/admin.py` (grep-confirmed `normalize_docket_value` call at line 184, raising 422 via `HTTPException` before `create_job` ever creates an `AdminJob` row). Read directly; matches the SUMMARY claim exactly. |
| 6 (gap closure) | A second, independent enforcement layer inside the pipeline itself prevents the write from landing outside `data/pdfs` even if the character rule were bypassed | ✓ VERIFIED | `pipeline/commands/ingest.py::_validate_docket_value` (delegates to the shared rule, then re-asserts structural invariants) plus a resolved-path containment assertion (`resolved_pdf_path.parent != resolved_pdf_dir` → `ValueError`) placed before every read/write branch — read directly at lines 356-382; matches the SUMMARY and REVIEW-GAPCLOSURE claims. |
| 7 (gap closure) | Operator gets immediate, specific inline feedback at the point of entry, and a forged/bypassed form field is still rejected server-side | ✓ VERIFIED | `app/src/lib/docketValues.ts` is a byte-identical TS mirror (pattern and cap literal-matched); `DocketPillInput.svelte`'s `addPill()` renders a `role="alert"` error on rejection without clearing the input (read directly, lines 78-99); `+page.server.ts`'s default action re-checks every `docket[]` value with `normalizeDocketValue` before the mode split and returns `fail(400, ...)` with docket-specific copy that never echoes the raw value or forwards FastAPI's 422 body (read directly, lines 48-70). |
| 8 (gap closure) | The gap is proven closed against the original human-reported reproduction, not only unit tests, with a credible consolidated regression gate | ✓ VERIFIED | Re-ran the exact 9-suite gate from 38-10-PLAN.md myself: `119 passed, 0 failures` — identical to the count claimed in `38-10-SUMMARY.md`. `38-UAT.md` records gap `G-38-6` as `status: resolved` with the operator's own reproduction (double-quote string, `../../../tmp/evil`, Windows drive path, real docket `22-915`, metadata-editor non-regression, non-docket generic-error preservation) and an explicit "Approved" sign-off dated 2026-07-27 — not just a status flip; the resolution field documents concrete evidence for every checkpoint step. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/domain/person_names.py` | Shared normalization/formatting/provenance/split contract | ✓ VERIFIED | Unchanged since prior verification; re-confirmed present and imported by all callers. |
| `alembic/versions/0022_person_name_authority.py` | Schema + guarded backfill + rollback | ✓ VERIFIED | Never writes `full_name`; round-trip gate fixed (CR-01). |
| `api/schemas/admin_people.py`, `api/services/admin_people.py` | Central people writer enforcement | ✓ VERIFIED | `full_name` removed, `extra="forbid"`. |
| `api/schemas/admin_jobs.py`, `api/services/admin_jobs.py` | Job-scoped writer using shared authority | ✓ VERIFIED | `PersonCreate` drops `full_name`. |
| `pipeline/commands/import_justices_csv.py`, `import_convokit.py`, `seed_aliases.py` | Shared-format import/seed adoption | ✓ VERIFIED | All import shared `person_names` helpers. |
| `app/src/routes/admin/people/new/+page.svelte`, `[id]/+page.svelte` | Generated preview, parts-only submit | ✓ VERIFIED | Read-only `<output>` preview on both. |
| `api/domain/docket_values.py` | Canonical docket-value allow-list/length-cap rule (G-38-6) | ✓ VERIFIED | 137 lines; no FastAPI/SQLAlchemy imports (`import re` / `typing` only, grep-confirmed); exports `DOCKET_VALUE_PATTERN`, `DOCKET_VALUE_MAX_LENGTH`, `DocketValueError`, `normalize_docket_value`. |
| `api/tests/fixtures/docket_value_cases.json` | Shared Python/TS accept/reject fixture | ✓ VERIFIED | Consumed by both `test_docket_values.py` and `test_docket_ui_contract.py`; both pass. |
| `pipeline/commands/ingest.py` | Docket path-component guard + containment assertion | ✓ VERIFIED | `_validate_docket_value` called at line 356 (before `pdf_filename`) and line 458 (before `case_slug`); containment assertion at lines 372-382, placed before `pdf_path.exists()`. |
| `app/src/lib/docketValues.ts` | Byte-identical TS mirror | ✓ VERIFIED | `DOCKET_VALUE_PATTERN` string literal identical to Python; `docketValueErrorMessage()` shared by component and server action. |
| `app/src/lib/components/DocketPillInput.svelte` | Opt-in `enforceShape` inline error | ✓ VERIFIED | `enforceShape` prop defaults `false`; `role="alert"` error element present; attempted value preserved on rejection (input not cleared). |
| `app/src/routes/admin/pipeline/+page.server.ts` | Server-side re-check, docket-specific `fail(400)` | ✓ VERIFIED | Re-checks every `docket[]` value before the `mode` split; never echoes raw value or forwards FastAPI's 422 detail (T-07-13 posture retained). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/services/admin_people.py` / `admin_jobs.py` | `api/domain/person_names.py` | `prepare_person_name` | ✓ WIRED | Unchanged since prior verification. |
| `api/routers/admin.py::_normalize_dockets` | `api/domain/docket_values.py` | `normalize_docket_value` import + call | ✓ WIRED | Grep-confirmed import at line 57 and call at line 184; `DocketValueError` caught and translated to `HTTPException(422)`. |
| `pipeline/commands/ingest.py::_validate_docket_value` | `api/domain/docket_values.py` | `normalize_docket_value` import + delegated call, then independent structural re-assertion | ✓ WIRED | Grep-confirmed import at line 48, call at line 100; structural checks (no `/`/`\`, no `..`, not absolute) verified present in the helper (read directly). |
| `app/src/lib/components/DocketPillInput.svelte` | `app/src/lib/docketValues.ts` | `normalizeDocketValue`/`DocketValueError`/`docketValueErrorMessage` import | ✓ WIRED | Read directly — imported at line 13, used inside `addPill()`. |
| `app/src/routes/admin/pipeline/+page.server.ts` | `app/src/lib/docketValues.ts` | same imports | ✓ WIRED | Read directly — imported at line 4, used in the `rawDockets` loop before the mode split. |
| `app/src/lib/docketValues.ts` | `api/tests/test_docket_ui_contract.py` | source-extraction parity test | ✓ WIRED | Extracts the TS pattern/cap literals via regex and replays the shared fixture through Python's `re` — genuine cross-language parity check, not a source-text match; passes (13 tests). |
| `pipeline/db.py::get_session` | rollback-on-exception | `except Exception: await session.rollback(); raise` | ✓ WIRED | Read directly at lines 76-78 — confirms the REVIEW-GAPCLOSURE claim that a `ValueError` raised mid-transaction triggers a full rollback, no partial-write window. |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PEOPLE-09 | 38-01 through 38-10 | Full Name field behavior locked (auto-derived), executed end-to-end, and the security gap discovered during its own UAT closed | ✓ SATISFIED | `.planning/REQUIREMENTS.md` lines 32/84 mark PEOPLE-09 complete/Phase 38. All 10 plans' `requirements: [PEOPLE-09]` frontmatter accounted for (grep-confirmed across all 10 `*-PLAN.md` files). No orphaned requirement IDs found for Phase 38 in REQUIREMENTS.md. |

No other requirement IDs map to Phase 38 in REQUIREMENTS.md — PEOPLE-09 is the only requirement and is fully accounted for across all 10 plans, including the gap-closure plans 38-07 through 38-10 (which reuse the same requirement ID rather than declaring a new one, since G-38-6 was discovered while validating this same requirement's UAT).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/routers/admin.py` | 1235 | `TODO(D-10): orphaned by Phase 27 — ...` | ℹ️ Info | Pre-existing Phase 27 debt marker, unrelated to Phase 38 (same label, different phase), references formal follow-up. Not introduced by this phase, not a blocker. Confirmed still present and unchanged from the prior verification. |

No debt markers (`TODO`/`FIXME`/`XXX`/`HACK`/`placeholder`) found in any file created or modified by the gap-closure plans (`api/domain/docket_values.py`, `api/tests/test_docket_values.py`, `api/tests/test_docket_arg_safety.py`, `api/tests/test_docket_ui_contract.py`, `pipeline/commands/ingest.py`, `pipeline/tests/test_ingest.py`, `app/src/lib/docketValues.ts`, `app/src/lib/components/DocketPillInput.svelte`, `app/src/routes/admin/pipeline/+page.server.ts`) — grep-confirmed directly.

### Code Review Findings

**Original 01-06 review (`38-REVIEW.md`):** 1 BLOCKER (CR-01) + 3 Warnings (WR-01/02/03), all previously confirmed fixed in the prior verification cycle. Re-confirmed unchanged in this pass (no regression).

**Fresh gap-closure review (`38-REVIEW-GAPCLOSURE.md`, dated 2026-07-27, 13 files, standard depth):** 0 critical, 1 warning, 3 info, `status: issues_found` (no blockers). The reviewer's own adversarial trace concluded **"The vulnerability is closed... I traced the fix adversarially across all three layers and could not construct a bypass."** This verifier independently re-confirmed the three specific claims the review makes:

| ID | Finding | Severity | This Verifier's Independent Check |
|----|---------|----------|-----------------------------------|
| WR-01 (gap-closure) | No end-to-end test drives `_run_ingest_inner` through the real call path with a hazardous docket (session-rollback not exercised end-to-end) | Warning | Confirmed as described — `pipeline/tests/test_ingest.py` covers the guard at the unit level plus two static `inspect.getsource` assertions, not a full DB-gated end-to-end run. This is a coverage gap, not a functional gap: the guard's unit behavior, its wiring into the executed code path, and `pipeline/db.py`'s rollback-on-exception behavior (read directly, confirmed generic to any exception) are all independently verified true; only the *combination* of all three in one integration test is missing. Non-blocking per the reviewer's own classification, and reasonable for a security-fix phase to leave as documented residual coverage debt rather than block sign-off on. |
| IN-01/02/03 (gap-closure) | Copy-only message mismatch on leading-hyphen (no security gap), unreachable `'empty'` branches at two call sites, platform-dependent `PurePath` note | Info | All three confirmed as described by direct reading of `admin.py`, `docketValues.ts`, and `ingest.py`; none reopen the path-traversal class per the reviewer's own analysis, which this verifier's independent read of the domain regex confirms (the `[A-Za-z0-9]` leading-character requirement structurally subsumes the leading-hyphen class either way). |

### Behavioral Spot-Checks / Probe Execution

This verifier independently re-ran (not merely re-cited) the consolidated regression gate specified in `38-10-PLAN.md` Task 1, from the repository root, in this environment:

```
./.venv/Scripts/python.exe -m pytest api/tests/test_docket_values.py api/tests/test_docket_arg_safety.py \
  api/tests/test_docket_ui_contract.py pipeline/tests/test_ingest.py pipeline/tests/test_ingest_startup_guard.py \
  api/tests/test_admin_jobs_list.py api/tests/test_admin_jobs_phase35.py \
  api/tests/test_admin_jobs_phase35_frontend.py api/tests/test_admin_dashboard_routes.py -q
```

Result: **119 passed, 0 failures** — exactly matching the count recorded in `38-10-SUMMARY.md`. This is credible, independently-reproduced evidence, not a re-citation of the SUMMARY's own claim.

Additionally ran the full `api/tests/` + `pipeline/tests/` suite once (not filtered per-truth, per verifier constraints): **655 passed, 5 xfailed, 4 errors**. The 4 errors are all in `api/tests/test_phase38_people_ui_contract.py`'s node-subprocess driver tests — a pre-existing, environment-specific failure (a Windows-path-into-JS-string-literal mangling bug in this WSL/Windows split dev environment) that predates plans 38-07–38-10, is explicitly named and scoped out in `38-09-PLAN.md`'s context section and `38-10-PLAN.md`'s Task 1 action ("Known pre-existing, unrelated failure to expect and NOT to chase here"), and does not touch any docket-guard or Full-Name-behavior code path. Confirmed via direct execution this is a setup-time `ENOENT` on a malformed concatenated path, not an assertion failure in the tested logic itself — not a regression introduced by this phase's work.

Independently re-verified the on-disk `data/pdfs` corpus claim: 56 real PDF filenames (58 total dir entries including `.gitignore`/`.gitkeep`) all satisfy `DOCKET_VALUE_PATTERN` + `DOCKET_VALUE_MAX_LENGTH` when run through the actual imported module — 0 violations among real files, matching the SUMMARY's "58 files, 0 violations" claim (its count included the two non-PDF marker files).

Independently re-ran `api/tests/test_person_names.py` + `api/tests/test_migration_0022_person_name_authority.py` in isolation to confirm the original Full-Name-behavior truths (1-4) have not regressed under the gap-closure changes: **54 passed, 7 skipped** (DB-gated cases skip cleanly with no `DATABASE_URL`, consistent with this project's documented WSL/Postgres-unreachable dev-environment constraint — not a failure).

### Human Verification Required

5 items require browser confirmation. 4 of these were already exercised once by the operator during `38-UAT.md` (Tests 1-5, all recorded `pass`), but that is a one-time human session recorded in this phase's artifacts, not an automated regression check — they remain flagged here per the verifier's standing "no browser tool available" constraint, consistent with how the prior verification handled them:

1. Live-updating generated Full Name preview (create + edit forms) — UAT Test 1 already passed.
2. First-only/last-only save success, blank-both error copy + preserved attempted values + focus-on-error — UAT Test 2 already passed.
3. Per-part stacked provenance rendering (narrow/wide widths) and copy-only-interpreted-value behavior — UAT Test 3 already passed.
4. People directory "Name review" pill filter/tab-URL preservation and exact empty-state copy — UAT Test 4 already passed.
5. Docket Pill approved provenance states against the Figma reference (editable/read-only, mixed confidence, long raw text wrapping) — UAT Test 5 already passed.

The G-38-6 security-specific human verification (UAT Test 6, the reproduction, traversal, and absolute-path cases) is **not** re-listed here as outstanding — it was already completed by the operator against the live running stack in `38-10-SUMMARY.md`/`38-UAT.md` with an explicit "Approved" sign-off and concrete reported evidence (no `[Errno 22]`, no pill created, nothing written outside `data/pdfs`), which this verifier accepts as genuine resolution, not a status flip: the resolution text names specific observed behavior for each of the 6 checkpoint sub-steps, not merely "resolved."

### Gaps Summary

No gaps found. All 8 truths (4 original Full-Name-behavior truths, re-confirmed unregressed, plus 4 new truths covering the 3-layer G-38-6 defense-in-depth and its consolidated proof) resolve to VERIFIED against the actual codebase — independently re-read and, where testable, independently re-executed by this verifier rather than trusted from SUMMARY.md text. The one Warning from the fresh gap-closure code review (WR-01, missing end-to-end integration test for the pipeline guard) is a documented coverage gap, not a functional gap — the guard's unit behavior, wiring, and the rollback-on-exception contract it depends on are each independently confirmed true in isolation. The pre-existing node-driver test failure in `test_phase38_people_ui_contract.py` is an environment artifact unrelated to this phase's work and was already known before the gap-closure plans began.

The only remaining status driver is `human_needed`, not `gaps_found` — the 5 items above require a browser this verifier does not have, and 4 of the 5 already carry a one-time human "pass" from `38-UAT.md`'s own session (not re-verifiable by grep, only by re-running in a browser).

---

_Verified: 2026-07-27T22:15:00Z_
_Verifier: Claude (gsd-verifier)_
