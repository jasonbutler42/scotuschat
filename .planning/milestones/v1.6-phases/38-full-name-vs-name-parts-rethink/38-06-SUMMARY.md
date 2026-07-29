---
phase: 38-full-name-vs-name-parts-rethink
plan: "06"
subsystem: ui
tags: [svelte5, sveltekit, typescript, node-native-ts, personnames, extracted-value, name-review]

# Dependency graph
requires:
  - phase: 38-full-name-vs-name-parts-rethink (Plan 01)
    provides: "api/domain/person_names.py: prepare_person_name, format_full_name, normalize_name_part canonical contract"
  - phase: 38-full-name-vs-name-parts-rethink (Plan 03)
    provides: "PersonCreateRequest/PersonUpdate reject a client-supplied full_name (extra=\"forbid\"); PersonDetail/PersonListItem expose name_needs_review/name_extraction_metadata; \"name review\" missing_filters allow-list entry"
  - phase: 38-full-name-vs-name-parts-rethink (Plan 05)
    provides: "CopyableExtractedValue optional stacked confidence/raw provenance mode"
provides:
  - "app/src/lib/personNames.ts: preview-only TypeScript mirror of api.domain.person_names, parity-locked to api/tests/fixtures/person_name_cases.json"
  - "Standalone create and person edit forms: generated read-only Full Name <output>, name parts as the only writable identity data, per-part CopyableExtractedValue provenance stacks"
  - "People directory: 'Name review' click-to-filter pill/indicator reusing the existing missing-field mechanism, with its own locked empty-state copy"
affects: [people-directory-ui, admin_people]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Node.js v22.6+/v23.6+ can execute plain, erasable TypeScript syntax directly (`node file.ts`, or `node --input-type=module` from stdin) — used to run app/src/lib/personNames.ts for real against the same JSON fixture the Python test suite consumes, giving genuine cross-language parity verification instead of a source-text substring match, in a repo with no frontend test runner"
    - "A single whole-record name_extraction_metadata envelope ({confidence, raw}, one per Person row) is rendered independently beneath each of First/Middle/Last/Suffix by giving each field its own CopyableExtractedValue instance sharing that one envelope — 'independent per-part provenance' means independent rendering/copy affordance per field, not four separately-stored guesses; a populated field shows its own current value as 'Extracted: {value}', an unfilled ambiguous field shows the Phase 36 disabled N/A state with the shared raw/confidence on the second line"
    - "Display-label indirection for a filter pill: the underlying query-param/filter vocabulary stays the existing lowercase multi-word convention (\"name review\") shared with the API's missing_filters allow-list, while a small pillLabel() helper renders the locked Title Case copy (\"Name review\") — avoids introducing a second filter-value vocabulary just to get the right display casing"

key-files:
  created:
    - app/src/lib/personNames.ts
    - api/tests/test_phase38_people_ui_contract.py
  modified:
    - app/src/routes/admin/people/new/+page.server.ts
    - app/src/routes/admin/people/new/+page.svelte
    - app/src/routes/admin/people/[id]/+page.server.ts
    - app/src/routes/admin/people/[id]/+page.svelte
    - app/src/routes/admin/people/+page.server.ts
    - app/src/routes/admin/people/+page.svelte

key-decisions:
  - "personNames.ts never accepts full_name as input and has no fetch/network call at all (T-38-16) — it is strictly a display mirror; the backend (api.domain.person_names.prepare_person_name) remains the sole write-path authority. A momentarily over-length keystroke degrades the live preview to 'N/A' rather than throwing through the UI layer, since the backend still authoritatively validates at submit time."
  - "Both people forms' server actions stop reading/sending full_name entirely (it is not even declared on PersonCreateRequest/PersonUpdate per Plan 03's extra=\"forbid\" contract) and instead enforce the same D-09 first-or-last minimum client-side with the exact locked copy, preserving every attempted name part and moving focus to First Name on failure — mirrors the existing tenure/office preserved-attempt pattern already established on the [id] editor."
  - "Each of First/Middle/Last/Suffix renders its own CopyableExtractedValue instance driven by the person's single name_extraction_metadata envelope (confidence + raw), gated on that envelope's presence — a never-extracted person (operator-created, or fully migrated with no ambiguity) shows no hint at all; an ambiguous legacy row shows the Phase 36 disabled N/A + shared raw/confidence per the UI-SPEC's 'raw exists with no interpretation' contract, with zero additional component logic required."
  - "'Name review' is additive to the exact existing click-to-filter pill mechanism (togglePillFilter/data.missing/data.tab) rather than a parallel filter code path or a new UI surface — only display/accessible text differs (Title Case via a pillLabel() helper), and the filter's own empty state uses the locked UI-SPEC copy, distinct from the generic 'No matches for this filter.' message. No dashboard queue or job-rerun control was introduced (D-13)."

patterns-established:
  - "Node.js direct TypeScript execution (no ts-node/tsx/vitest) as a genuine cross-language parity-test mechanism for a repo with no frontend test harness — the driver script is passed to `node --input-type=module` via stdin and imports the real .ts file by file:// URL"

requirements-completed: [PEOPLE-09]

coverage:
  - id: D1
    description: "app/src/lib/personNames.ts mirrors api.domain.person_names byte-for-byte for every shared fixture case (format, normalization, and error-code parity) and never accepts full_name as input"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_people_ui_contract.py::test_personnames_ts_format_cases_match_shared_fixture, test_personnames_ts_normalization_cases_match_shared_fixture, test_personnames_ts_invalid_cases_raise_matching_error_codes, test_personnames_ts_preview_returns_na_until_first_or_last, test_personnames_ts_never_accepts_full_name_as_input, test_personnames_ts_declares_same_column_bounds_as_backend"
        status: pass
    human_judgment: false
  - id: D2
    description: "Standalone create and person edit forms render a live, read-only generated Full Name preview and submit only name parts; save is rejected client-and-server-side unless first or last is present, with attempted values preserved and focus moved to First Name"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_people_ui_contract.py::test_new_page_server_never_reads_or_sends_full_name, test_new_page_server_create_action_enforces_first_or_last_minimum, test_new_page_server_preserves_attempted_parts_on_every_failure_branch, test_new_page_svelte_renders_generated_preview_not_editable_input, test_new_page_svelte_shared_min_name_hint_not_html_required, test_id_page_server_never_reads_or_sends_full_name_in_save_action, test_id_page_server_save_action_enforces_first_or_last_minimum, test_id_page_svelte_renders_generated_preview_not_editable_input"
        status: pass
      - kind: other
        ref: "npm run check (svelte-check --tsconfig ./tsconfig.json) -- 803 files, 0 errors"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> section requires browser UAT (create first-only/last-only people, edit suffix/middle via partial save, live-typing preview updates, focus-on-error, wide/narrow layout, keyboard copy, N/A/success/error/long-raw-text states) against 38-FIGMA.md; no browser tool is available in this execution environment, so visual/interaction confirmation must come from a human."
  - id: D3
    description: "Each of First/Middle/Last/Suffix independently renders a CopyableExtractedValue stacked-provenance hint driven by the person's name_extraction_metadata envelope, gated on its presence, with no autofill/click-to-overwrite wiring"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_people_ui_contract.py::test_id_page_server_person_detail_exposes_name_review_and_provenance, test_id_page_svelte_renders_independent_provenance_per_name_part, test_id_page_svelte_provenance_never_overwrites_operator_value_on_edit"
        status: pass
    human_judgment: true
    rationale: "Visual placement/wrapping of the four independent stacked hints inside the name-parts grid at wide and narrow widths, and the disabled N/A + shared raw/confidence rendering for an ambiguous legacy row, require browser/visual comparison against 38-FIGMA.md and the approved mockup; no browser tool is available in this execution."
  - id: D4
    description: "People directory 'Name review' pill/indicator filters only flagged records while preserving the active tab and URL round-trip behavior, with its own exact empty-state copy; no dashboard queue or job-rerun control is introduced"
    requirement: "PEOPLE-09"
    verification:
      - kind: unit
        ref: "api/tests/test_phase38_people_ui_contract.py::test_list_page_server_threads_name_needs_review_field, test_list_page_svelte_declares_pill_label_helper_for_name_review, test_list_page_svelte_pill_rendering_uses_pill_label_and_preserves_filter_mechanism, test_list_page_svelte_exact_name_review_empty_state_copy, test_list_page_svelte_togglepillfilter_preserves_tab_in_url, test_no_dashboard_queue_or_rerun_control_introduced"
        status: pass
    human_judgment: true
    rationale: "Selected-pill visual state and the empty-state layout require the same browser confirmation as every other pill on this directory (consistent with Plan 05/prior phases' precedent); no browser tool is available in this execution."

duration: ~50min
completed: 2026-07-27
status: complete
---

# Phase 38 Plan 06: Generated Full Name Editor UI + Name Review Directory Summary

**Standalone create and person edit forms now show a live, read-only "Generated from name parts." Full Name preview (a Node-executable TypeScript mirror of the backend's canonical formatter) and submit only structured name parts; each saved part carries its own independent extracted-provenance hint; and the People directory gets a "Name review" click-to-filter pill reusing the existing missing-field pattern verbatim, closing PEOPLE-09 end to end.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-07-27
- **Tasks:** 3
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments

- `app/src/lib/personNames.ts`: a preview-only TypeScript mirror of `api.domain.person_names` (`normalizeNamePart`/`formatFullName`/`previewFullName`), parity-verified for real against `api/tests/fixtures/person_name_cases.json` by shelling out to `node` (v22.6+/v23.6+ execute plain erasable TypeScript directly — no `ts-node`/`tsx`/`vitest` needed). Never accepts `full_name` as input and has no persistence path at all (T-38-16) — the backend remains the sole write-path authority.
- `app/src/routes/admin/people/new/+page.server.ts` / `+page.svelte` and `app/src/routes/admin/people/[id]/+page.server.ts` / `+page.svelte`: the editable Full Name `<input>` is replaced with a read-only `<output>` labeled `Full Name` / `Generated from name parts.`, live-updating from `firstName`/`middleName`/`lastName`/`nameSuffix` `$state` bindings via `previewFullName()`. Server actions stop reading/forwarding `full_name` entirely and instead enforce the D-09 first-or-last minimum with the exact locked copy (`Enter at least a first or last name.`), preserving every attempted name part on a 400/422 and moving focus to First Name. First/Middle/Last/Suffix each render an independent `CopyableExtractedValue` stacked hint (`copyLabel="Copy extracted {field}"`) driven by the person's single `name_extraction_metadata` envelope, gated on its presence — a never-extracted person shows no hint; an ambiguous legacy row's still-blank field shows the Phase 36 disabled N/A state with the shared raw/confidence, with zero extra component logic required.
- `app/src/routes/admin/people/+page.server.ts` / `+page.svelte`: `name_needs_review` is threaded through the existing `PersonListItem` shape; the People directory's "Name review" state reuses the exact existing click-to-filter pill mechanism (`togglePillFilter`/`data.missing`/`data.tab`) via a `pillLabel()` display-text helper, so the underlying filter value stays the lowercase vocabulary the API's `missing_filters` allow-list already expects while the visible/accessible text is the locked Title Case copy. The filter's empty state now shows the exact locked heading/body (`No people need name review` / `Ambiguous legacy names will appear here for review.`), distinct from the generic missing-field empty state. No dashboard queue or job-rerun control was introduced.
- `api/tests/test_phase38_people_ui_contract.py` (new, 23 tests): genuine cross-language parity verification for Task 1 (Node executes the real `.ts` file against the shared fixture) plus static source-contract assertions for Tasks 2–3, following the established Phase 38 pattern for a repo with no frontend test runner.
- Full Phase 38 focused matrix (`test_person_names.py`, `test_migration_0022_person_name_authority.py`, `test_admin_people_schemas_service.py`, `test_admin_jobs_phase25.py`, the three pipeline import/seed test files, `test_phase38_extracted_value_contract.py`, and this plan's new contract file): 230 passed, 2 pre-existing xfailed. `npm run check`: 803 files, 0 errors.

## Task Commits

Each task was committed atomically:

1. **Task 1: Mirror canonical formatting for live preview** - `a449f3c3` (feat)
2. **Task 2: Convert standalone and edit forms to generated Full Name** - `045e03d7` (feat)
3. **Task 3: Add focused Name review directory workflow and close the source audit** - `2245d945` (feat)

## Files Created/Modified

- `app/src/lib/personNames.ts` (new) — preview-only TypeScript mirror of the backend name-authority contract
- `api/tests/test_phase38_people_ui_contract.py` (new) — 23 tests across all three tasks, including genuine Node-executed parity verification
- `app/src/routes/admin/people/new/+page.server.ts` — drops `full_name` entirely, enforces first-or-last minimum, preserves attempted values
- `app/src/routes/admin/people/new/+page.svelte` — generated `<output>` preview, `bind:value` name-part inputs, shared minimum-name hint
- `app/src/routes/admin/people/[id]/+page.server.ts` — same server-side contract change; `PersonDetail` interface gains `name_needs_review`/`name_extraction_metadata`
- `app/src/routes/admin/people/[id]/+page.svelte` — generated preview, per-part `CopyableExtractedValue` provenance stacks, restore/focus effects extended to name parts
- `app/src/routes/admin/people/+page.server.ts` — `name_needs_review` added to `PersonListItem`
- `app/src/routes/admin/people/+page.svelte` — `pillLabel()` helper, exact Name review empty-state copy

## Decisions Made

See `key-decisions` in frontmatter. In summary: `personNames.ts` is a pure display mirror with no write path of its own; both people forms enforce the D-09 minimum client-side with the exact locked copy and full attempted-value preservation instead of any `full_name` requirement; per-part provenance hints share one whole-record `name_extraction_metadata` envelope rendered independently per field (not four separately-stored guesses); and "Name review" is additive to the existing missing-field pill mechanism via a display-label indirection rather than a new filter vocabulary or UI surface.

## Deviations from Plan

None — plan executed as written. All three tasks' `<behavior>`/`<action>` requirements (parity-locked preview, generated Full Name with preserved-attempt validation, per-part independent provenance, focused Name review filter reusing the existing pattern, no dashboard queue/rerun control) were implemented directly per the plan; no unplanned bugs, missing critical functionality, or blocking issues were encountered.

## Issues Encountered

- **Full `api/tests/` directory run shows 4 unrelated failures** (`test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`, `test_isolation_survives_inner_commit.py::test_create_person_for_job_inner_commit_is_queryable_after_return`, `test_people.py::test_get_person`, `test_people.py::test_get_person_404` — `ConnectionRefusedError` to `127.0.0.1:5432`). This is the same pre-existing, environment-specific `DATABASE_URL` pollution hazard Plan 03's summary already documented (root-caused there to `test_migration_0022_person_name_authority.py`'s own env-var resolution interacting with `.env`); it reproduces identically with `--ignore`-ing that file too, and none of the four failing tests, nor their files, are in this plan's `files_modified` or its own `<verify>` command list. This plan's own required focused matrix (230 passed, 2 xfailed) and `npm run check` (0 errors) both pass cleanly. Not fixed here — out of this plan's scope (Rule: scope boundary) and pre-dates this session.
- **No reachable PostgreSQL / no system `pip` in this Linux/WSL sandbox** (same class of gap Plans 01–05 documented). Reused an already-provisioned scratch venv and an already-running ephemeral, session-local PostgreSQL 16 instance (via `pgserver`, Alembic head `0022`) left over from this same session's earlier Phase 38 plans — no new instance provisioned, no project file/`.env`/fixture modified, nothing connected to the real dev database.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- PEOPLE-09 is now fully closed: Full Name is generated everywhere (API, pipeline/import/seed paths, and both editor UIs), structured parts alone save, legacy ambiguous names remain safe and are now reviewable through a focused People-directory filter, and every extracted editable field (name parts, docket pills, and the pre-existing Resolve-card/pipeline-job hints) uses the one approved stacked provenance pattern.
- **Browser/visual UAT is still required** for this plan's three deliverables (generated preview live-update/focus/validation behavior, per-part provenance stack layout at wide/narrow widths and in the disabled-N/A ambiguous-row state, and the Name review pill/empty-state) — no browser tool was available in this execution to perform that confirmation. See `coverage` entries D2–D4 (`human_judgment: true`) in this file's frontmatter.
- This is the final plan of Phase 38 (`full-name-vs-name-parts-rethink`) — the phase is ready for `/gsd-verify-work 38`.
- No blockers. Full Phase 38 focused matrix (230 passed, 2 pre-existing xfailed) and `npm run check` (0 errors) both green.

---
*Phase: 38-full-name-vs-name-parts-rethink*
*Completed: 2026-07-27*

## Self-Check: PASSED

- FOUND: app/src/lib/personNames.ts
- FOUND: api/tests/test_phase38_people_ui_contract.py
- FOUND: app/src/routes/admin/people/new/+page.server.ts
- FOUND: app/src/routes/admin/people/new/+page.svelte
- FOUND: app/src/routes/admin/people/[id]/+page.server.ts
- FOUND: app/src/routes/admin/people/[id]/+page.svelte
- FOUND: app/src/routes/admin/people/+page.server.ts
- FOUND: app/src/routes/admin/people/+page.svelte
- FOUND commit: a449f3c3 (Task 1)
- FOUND commit: 045e03d7 (Task 2)
- FOUND commit: 2245d945 (Task 3)
