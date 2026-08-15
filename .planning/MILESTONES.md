# Milestones

## v1.7 Corpus Fidelity & Resolve Rework (Shipped: 2026-08-15)

**Phases completed:** 6 phases, 29 plans, 69 tasks

**Key accomplishments:**

- Offline `scripts/select_corpus_fixtures.py` streams the full 1.7M-row ConvoKit utterances corpus once, scores all 7,817 conversations on a 4-flag path-coverage checklist (never a weighted sum), and prints a deterministic top-5 shortlist, recommendation, 3 state-variety proposals, and a paste-ready fixtures-draft table — with the apolitical field exclusion enforced structurally, at runtime, and via a commit-gate-equivalent literal-hit check.
- `.planning/FIXTURES.md` created at the project root, transcribed verbatim from the real full-corpus re-rank of `scripts/select_corpus_fixtures.py`: conversation 15169 (Baltimore & Ohio Railroad Co. v. United States) recommended as the complexity fixture at 3/4 path coverage, with 14969 (Shapiro v. Thompson) as the named tied runner-up, alongside three state-variety target fixtures (13015, 18897, 22372) -- Status: PROPOSED, awaiting Plan 03's operator confirmation.
- The operator explicitly confirmed all four proposed fixtures with no substitutions (confirm-as-proposed) — `.planning/FIXTURES.md` rewritten to `Status: CONFIRMED` with a `## Confirmation` section recording the decision verbatim; Phase 42 and Phase 43 are now unblocked.
- New `--conversation-id` option on `import-convokit` narrows the corpus loaders to one conversation before the 900MB utterance stream, landing ConvoKit conversation 15169 in the dev database as an isolated `status=pipeline` Argument.
- A purpose-built `scripts/delete_fixture_argument.py` deletes a `status=pipeline` corpus argument and its full FK-ordered dependent cascade in one transaction (bypassing the admin API's DRAFT-only gate without weakening it), and the delete-then-reimport round trip against the real conversation-15169 fixture reproduced every per-table count exactly.
- A regenerable, read-only `scripts/diff_corpus_fixture.py` diffs conversation 15169's raw ConvoKit source against its imported DB rows across all six affected tables, and its court_tenures integrity check distinguished a genuine bench-classification timing anomaly (Marshall) from a previously-unknown Person-dedup mismatch between the two justice-import tools (White/Black/Clark/Douglas), all captured in the committed `.planning/CORPUS-FIDELITY-DIFF.md`.
- Recorded the operator's D-05/D-06 batch disposition for all 8 Review Gate items, implemented non-cascading `section_hint` derivation (item 1) restoring the transcript page's section-jump anchors, and added a bench-tenure mismatch warning/counter (item 2, `bench-warn-only`) that flags Thurgood Marshall's pre-tenure BENCH classification without reassigning his fixture row's side.
- Deleted and re-imported the conversation-15169 fixture through Plan 04's fixed `import_convokit` code path, re-ran the same field-by-field fidelity diff against the fresh rows (not assumed), and got the operator's live-browser confirmation that the transcript page renders exactly the section-jump anchor its approved bench-warn-only disposition implies — closing CORPUS-14.
- One `POST /api/admin/dev/reset-to-fixture` wipes the test DB (TRUNCATE across 9 named tables, CASCADE, `roles` excluded) and reseeds conversation 15169 through the real `run_import_convokit` importer in-process, behind a separately-mounted router that's genuinely absent (404, not 403) outside `settings.environment == "development"`.
- `reset_to_fixture` now reseeds all four confirmed CORPUS-12 fixtures (15169, 13015, 18897, 22372) through the real `run_import_convokit` importer and drives the three state-variety fixtures into distinguishable Draft/Published/Mid-pipeline end states via the real `approve_job`/`publish_argument` service functions, with a documented single exception for the Mid-pipeline `AdminJob` flip.
- `/admin` now renders a server-gated "Dev Tools" section (DEV ONLY badge, two-step Confirm/Cancel, Running spinner, four-fixture Success list, `role="alert"` Error state) wired to Plan 43-01/43-02's backend endpoint through a zero-input SvelteKit form action, with the environment value read server-side only and never exposed to the browser.
- Operator-confirmed, live proof against the real corpus and real dev database: Reset to Fixture produces exactly the four confirmed fixtures in four distinguishable states, and the environment gate is a genuine fail-closed allow-list — demonstrated by actually attempting the production refusal, an unset value, and a capitalization near-miss, not asserted from the code.
- Full-stack rename of `ArgumentParticipant.title` to `.descriptor` (and `title_hint` to `descriptor_hint`) — new Alembic migration 0025, ORM, Pydantic schemas, services, routers, the pipeline TOC-subtitle writer, both SvelteKit consumers, all affected tests, and a new pure-source residual-name contract test.
- `ResolveCard.svelte` restructured from six columns to five — the Action column is deleted, its two person-matching buttons fold into a single `openPersonSearch` entry point inside Resolved As with a D-04 pre-filled/accepted-by-default combobox, and Descriptor (renamed from Title in Plan 44-01) now always renders via a new `descriptorCell` snippet instead of disappearing for Bench/gated rows — locked by a new 11-test pure-source contract.
- Replaces the overloaded `<select name="side">` with a two-segment Bench/Advocate toggle (which also absorbs the pre-resolution side gate) and a real four-option Argument Role dropdown for advocate rows, both writing through a single always-present hidden `side` input flushed synchronously before submit — closing a latent defect where the old gate path submitted with no side value at all.
- Added a `prefixLabel` prop to `CopyableExtractedValue.svelte` and rendered four "Imported:" hint lines across the Resolve table's columns; the plan's remaining visual-acceptance checkpoint was superseded by a subsequent Figma canonical redesign before it could be resolved.
- Collapsed the Resolve table's standalone Bench/Advocate column into the Resolved As cell (toggle stacked above a new always-rendered `personDropdown` combobox) and deleted the confirm/correct disposition state machine entirely. The first Task 3 checkpoint was rejected with specific defects; confirmed-in-scope defects (create-person placement, combobox affordance, neutral gated placeholder, and a toggle data-loss bug) were fixed and covered by new regression tests. The operator approved the second Task 3 checkpoint on 2026-08-07 — plan complete.
- Task 1 (red-first test inversion).
- Person search now filters by `Person.is_justice` fail-open, and every ingestion hint's prefix is derived from the job's real `pdf`/`corpus` source instead of a hardcoded "Imported" literal — no backend, pipeline, or shared-component change required.
- Bench Argument Role now renders one of three states in the operator's own words — `Calculated from tenure`, `Tenure not found`, or `(resolve person first)` — instead of the interim `Imported: N/A - ...` hint wording, and the tenure-fix path opens in a second tab so the live recompute 44-06 locked is actually usable.
- Tasks 1-3 complete: the Resolve card now shows a persistent "N of M speakers still need review" header line, an always-visible Continue button that states why it's disabled, and per-row AUTO-MATCHED/NEEDS YOU/MANUALLY MATCHED cue tags — all reading the same personId predicate so the count and the gate cannot disagree. Task 4 (operator acceptance of the full 44-05→44-09 Figma reconciliation) is a blocking human-verify checkpoint this executor cannot perform. Its first pass was REJECTED with specific, Figma-confirmed feedback; the second round fixed every confirmed defect (a real descriptor data-loss bug, a real side-switch person-selection bug, and four visual/structural corrections against the actual mockup); the third round added the MANUALLY MATCHED row cue tag the operator requested mid-review; the fourth round root-caused and fixed two live-testing regressions (toggle-highlight/gate disagreement, side-mismatched seeding); the fifth round built the tenure-preview endpoint the fourth round deliberately deferred; the sixth round found and fixed two more real bugs during final live-testing (a create-person popover outside-click bug, and a stale full_name/422 schema mismatch) — the operator then confirmed all 16 checklist items pass. APPROVED 2026-08-11.
- Both public argument-detail endpoints (utterances, speakers) now 404 identically for an unpublished or nonexistent argument, keyed solely on `Argument.published_at`; Task 3's live operator verification is still pending.
- BUG-02 is closed. After the initial whole-card-scroll fix (D-03 as originally specified) failed live checkpoint verification, the operator supplied a Figma reference showing the intended shape: only the bio paragraph scrolls internally (capped at 150px), not the whole card. Popover.Content dropped its max-height/overflow-y; the bio `<p>` gained a `.bio-scroll` class with a thin custom scrollbar. Operator-approved on the revised implementation.
- Relocated the TEST_DATABASE_URL redirect and dev-DB row-count tripwire from a sibling `tests/conftest.py` to a root-level `conftest.py` at the pytest rootdir, closing the sibling-directory blind spot that wiped the shared dev database twice during Phase 45, and backed the fix with a subprocess-based regression test plus fail-closed guards in both sibling conftests.
- Brought the Windows PostgreSQL 18 service up and reachable from WSL on the live NAT subnet (172.26.32.0/20), recreated `.venv` as a WSL-native Python 3.12 environment with GSD's own `test_command` repointed at it, and re-verified the dev-only admin router's allow-list gate is unaffected by the environment cutover — closing out a blocking human-action checkpoint and fixing a real crash bug discovered along the way in the just-relocated rootdir `conftest.py`.
- A permanent test proves a WSL-native process reaches the Windows Postgres service over the dynamically-resolved NAT gateway with a loud, self-correcting failure on host drift; both databases are migrated to the same Alembic head with no new DDL path; and five full-suite/explicit-path pytest invocations plus a fail-closed control show dev-DB row counts byte-identical throughout — empirically retiring the Phase 45 wipe bug.
- Repository copied intact (217 unpushed commits, all untracked secrets/data) from the 9p/DrvFs mount to `/home/jason/scotuschat/project` on native ext4, with a rebuilt WSL-native venv/node_modules proving the full stack works from there, and the operator's general cutover approval independently substantiated by orchestrator read-only re-verification.
- WSL-native `scripts/dev-start.sh` with dynamic host resolution, a `/dev/tcp` PostgreSQL probe, `setsid -w` process-group launches, real HTTP health polling, and trap-based teardown; a share-path-aware PowerShell wrapper; an explicit Vite server block -- live-smoke-tested by the operator, who found and the executor fixed a real health-check bug (Bug 1) and surfaced a genuine Windows-side environmental gotcha (Bug 2, flagged for 46-06's README).
- README.md rewritten to document the single WSL2 + Windows-PostgreSQL-service setup this phase actually built (replacing every reference to the retired portable-PostgreSQL/Windows-venv arrangement); the pre-relocation checkout retired in place under operator-decided option-c with a fresh integrity re-proof and an advisory marker; 46-VALIDATION.md fully resolved to `validated`/`nyquist_compliant: true` with the pre-existing green row untouched.

---

## v1.6 Backlog Cleanup (Shipped: 2026-07-29)

**Phases completed:** 11 phases (31–40, 40.1), 51 plans, 99 tasks
**Timeline:** 2026-07-12 → 2026-07-29 (17 days)
**Files changed:** 323 (96 code files: +11,960 / -1,221) | **Total incl. docs:** +42,847 / -1,389

**Delivered:** Closed out the 10 phases promoted from the 999.x backlog — an escalated test-isolation/data-leakage fix, four pipeline/people-admin bug fixes, one operator UX pattern, two resolved design questions (tenure Seat toggle, Full Name auto-derivation), a public-UI enrichment (bench popover context), and a README gap — plus Phase 40.1, an inserted phase that turned out to already be satisfied by Phase 38's work and closed via documentation reconciliation instead of duplicate code.

**Known deferred items at close:** 3 (see STATE.md Deferred Items — 2 out-of-scope bugs/polish found during Phase 39 UAT, 1 seed already designed to resurface at next milestone planning)

**Key accomplishments:**

- Idempotent `scripts/provision_test_db.py` (CREATE DATABASE + `alembic upgrade head` via subprocess) plus a `TEST_DATABASE_URL`-gated session-scoped auto-reset fixture in `pipeline/tests/conftest.py`, both guarded to never touch the shared dev DB.
- Root `tests/conftest.py` now redirects `DATABASE_URL` onto `TEST_DATABASE_URL` for the whole suite when configured, and enforces an automated `pytest_sessionstart`/`pytest_sessionfinish` guard that fails loudly if any session changes `people`/`arguments` row counts on the real shared dev DB.
- Consolidated 7 verbatim-duplicated `db_session` pytest-asyncio fixtures into a single definition in `api/tests/conftest.py`, eliminating drift risk across api/tests.
- Standalone `scripts/cleanup_leaked_test_rows.py` — dry-run-by-default script that broadly detects duplicate `Person` rows and orphaned/test-fixture `Argument` rows in the shared dev DB, picks survivors by real tenure/bio data, and gates all deletion behind `--execute` plus an interactive confirmation.
- Fixed 5 api/tests files' DB-gated tests against scotus_test — including 3 genuine stale-identity-map bugs in publish_argument/unpublish_argument/approve_job that a config.py crash had masked from ever executing.
- Fixed job_id/argparse drift, an anthropic SDK construction bug, a genuine parser regex bug (plural PETITIONERS/RESPONDENTS never matched), a stale idempotency assumption in test_ingest.py, and a session-scoped-engine/function-scoped-event-loop pytest-asyncio mismatch — all 5 pipeline/tests files now pass (19 passed, 5 documented xfails, 0 failures) against scotus_test.
- Added the criterion-3 regression test, then root-caused and fixed the 3 remaining full-suite failures — the entire suite now runs 429 passed / 5 xfailed / 0 failed / 0 errored under scotus_test isolation, with the shared-dev-DB leak hook silent across repeated runs.
- Operator-authorized `scripts/cleanup_leaked_test_rows.py --execute` removed the 81 leaked rows (25 duplicate Person rows across 6 name groups including 6 Ketanji Brown Jackson rows, 56 orphaned Argument rows) from the shared dev DB; `python -m pipeline import-justices` and a full `pytest -q` run both completed cleanly afterward, confirming success criterion 4.
- Extended MergePreview and all three admin-people service functions (get_merge_preview, merge_people, delete_person_if_orphan) to count, transfer, and block on CourtTenure rows, closing the unhandled-IntegrityError gap on merging/deleting Justices with tenure history.
- Synced both admin-people frontend surfaces (`+page.server.ts` and `+page.svelte`) to the Plan 01 backend contract, adding `tenures` as a 5th field so the merge breakdown renders the count and the delete button's client-side defense-in-depth check blocks on tenure rows.
- Metadata saves now combine the final docket/question pair, reject known duplicates before update, and recover named PostgreSQL races through an exact sanitized 409 contract.
- All offline argument writers now use the shared concrete-pair semantics and reserve duplicate recovery for the exact PostgreSQL constraint.
- Both admin metadata editors now preserve attempted values and guide keyboard users from a sanitized duplicate response to the conflicting argument.
- Duplicate conflict responses now state only the colliding pair, leaving the shared component to render the actionable recovery link exactly once.
- Constraint-valid Case resubmissions now discard stale native required state while preserving authoritative server-required, collision, and generic failure handling.
- Deleted same-source job recreation ownership from FastAPI and its service layer while preserving ordinary creation, recovery, PDF delivery, and durable PipelineRun history.
- Removed the hidden job-detail rerun action while preserving authenticated historical loads, failed-run recovery, and local source-PDF navigation.
- Authenticated removal-by-absence coverage now proves the retired route returns framework 404 while ordinary job creation, recovery, durable source fields, and disk-backed PDF delivery remain operational.
- A reusable Svelte 5 clipboard affordance now serves every argument-detail docket, question-number, and argued-date hint.
- One shared extracted-value interaction now covers every eligible pipeline and argument-editor surface, with paste-compatible date presentation and a native-date-safe fill action.
- 1. [Rule 3 - Blocking] Added an isolated Vite fixture configuration
- Collectable migration-integrity and Office-control RED contracts covering irreversible normalization, accessibility, and failed-save recovery
- Reversible rename, integrity-protected audit normalization, and post-normalization binary Office constraint
- CourtTenure.office replaces free-text seat end to end across the ORM, admin-people schemas/service, and the justice CSV importer, with a strict write / tolerant read schema split and validated atomic tenure replacement
- Speaker/admin-argument read projections and the public argument view/popover now render `Chief Justice`/`Associate Justice` from canonical `office`, with date-window and D-14 fallback selection algorithms byte-for-byte unchanged
- Free-text tenure Seat replaced end-to-end by an accessible native-radio Chief/Associate control, with a disposable-database proof that the staged migration and application layers agree, and a fail-closed repository audit confirming zero stray `seat` identifiers remain
- Pure Python domain module (api/domain/person_names.py) implementing canonical First Middle Last, Suffix formatting, whitespace-only normalization with column-bound validation, provenance envelope validation, and a conservative fixture-driven legacy Full Name splitter — zero new dependencies, zero app/database initialization.
- Alembic revision 0022 adds `Person.name_needs_review` (durable review flag) and `Person.name_extraction_metadata` (independent JSONB provenance), then guardedly backfills legacy full-name-only rows into structured parts via Plan 01's `split_legacy_full_name` — confident splits applied, every ambiguous shape preserved exactly and flagged for review, `full_name` itself never written.
- PersonUpdate, PersonCreateRequest, and admin_jobs.PersonCreate all drop `full_name` as a writable field (Pydantic `extra="forbid"`, a 422 not a silent no-op), and every create/update write path — including the job-scoped mini-create — derives `full_name` exclusively through the shared `prepare_person_name` helper, with PATCH correctly merging omitted-vs-cleared name parts and clearing `name_needs_review` (never `name_extraction_metadata`) on an authoritative edit.
- All three batch person-writers (justice CSV import, ConvoKit corpus import, and alias seeds) now derive `full_name` exclusively through the shared `api.domain.person_names` contract, write a uniform `name_extraction_metadata` provenance envelope, and apply blank-only prefill so no import path can silently overwrite an operator-authored or previously-confident name part.
- Extended the Phase 36 `CopyableExtractedValue` component with an optional two-line stacked provenance mode (interpreted value / confidence / exact raw source) and wired it into `DocketPillInput`, `ResolveCard`, the pipeline job detail page, and the argument editor's speaker title hint, without regressing any existing value-only/pill consumer.
- Standalone create and person edit forms now show a live, read-only "Generated from name parts." Full Name preview (a Node-executable TypeScript mirror of the backend's canonical formatter) and submit only structured name parts; each saved part carries its own independent extracted-provenance hint; and the People directory gets a "Name review" click-to-filter pill reusing the existing missing-field pattern verbatim, closing PEOPLE-09 end to end.
- Closed the authenticated-admin arbitrary-file-write primitive (G-38-6) by adding a single canonical `normalize_docket_value` allow-list/length-cap rule in `api/domain/docket_values.py` and wiring it into `_normalize_dockets` so a hostile or malformed docket value now gets a 422 before any `AdminJob` row or ingest subprocess exists.
- Second, independent layer of the G-38-6 fix: `pipeline/commands/ingest.py` now validates every docket-derived filename and slug component itself, plus asserts the resolved PDF write path stays inside `data/pdfs`, closing the direct-CLI bypass of the Plan 38-07 API-boundary check.
- TypeScript mirror of the Phase 38-07 canonical docket rule (`app/src/lib/docketValues.ts`), an opt-in inline `role="alert"` shape error in `DocketPillInput` used only by the Pipeline Runner, and a SvelteKit-server re-check in `+page.server.ts` that rejects a forged `docket[]` value before FastAPI is ever called — closing item 3 of UAT gap G-38-6's `missing` list.
- Consolidated 119-test regression gate across all docket-guard-touching suites plus operator re-verification of the original UAT Test 6 reproduction (and traversal/absolute-path variants) on the live Pipeline Runner, closing UAT gap G-38-6.
- One column (`court_tenures.reason_left`) wired end to end — migration through ORM, canonical constants + display-title helper, public schema, service assembly, and popover render — plus `people.death_date`'s DB column and ORM mapping, both proven by a real DB-backed test of `get_argument_speakers()`.
- `python -m pipeline import-justices` now reads the CSV's Birthdate, Death Date and Reason Left columns and null-only backfills Person.birthdate/death_date and CourtTenure.reason_left, mapping the 5-value CSV vocabulary through an explicit membership check that surfaces (rather than silently drops) anything unrecognised.
- Both Phase 27 "Coming soon" placeholder inputs — person-level Death Date and per-tenure Reason Left — are now live, strictly validated on write, tolerant on read, and wired end to end through the existing single atomic save form with no new form or action.
- Reversed Phase 14's T-14-02 party exclusion, promoted the top-level `appointing_president` field to a per-tenure `appointed_by`, and added `birthdate`/`death_date`/`bio_text` to the public speaker popover payload — all pinned by exact-key-set regression tests.
- Rebuilt `SpeakerPopover.svelte` from a narrow flex-row card into a header-row-plus-stacked-sections layout that renders every field Plan 39-04 added (birth/death line, per-tenure appointed-by/party, clamped bio with toggle, advocate descriptor slot), and widened the argument page's speaker types plus a scroll backstop on the popover wrapper to match.
- Checkpoint not approved: operator found a real styling regression (separator dot, overall Figma mismatch) and a silent Bio save failure; two items pass, one is unconfirmed either way.
- Moved bio_text ownership from the photo action to the save action so the primary Save Person button now saves the whole person atomically, including the bio -- closing 39-UAT.md gap 1/test 10.
- Closed 39-UAT.md gaps 2 and 3 by moving the birth/death and president/party separator's space into a `{#snippet}` span (fixing Svelte's whitespace-trimming at `{#if}` block boundaries), giving all four stacked sections their own hairline divider, and rebuilding each tenure block into the mockup's two-column row pair with month-and-year date granularity — all pinned by a new 17-test DB-free source-contract module.
- Checkpoint approved: all three 39-06 UAT gaps confirmed closed on the live stack, party-neutral rendering holds after the restyle, one new minor finding filed separately.
- Windows-first onboarding now covers a clean checkout through an empty migrated stack, with equally runnable portable and service-managed PostgreSQL paths.
- Cross-platform setup guidance now has a dated Windows portable-stack PASS, including real admin login and authenticated-session preservation.
- Phase 40.1 was inserted to fix a path-traversal/arbitrary-file-write vulnerability that the v1.6 pre-close artifact audit reported as open — but the gsd-planner agent's source audit, independently re-verified in this session, found the vulnerability had already been fully fixed, tested, and operator-signed-off two days earlier as Phase 38 Plan 10 (gap G-38-6). No new code was written; this phase closes by reconciling the stale tracking documents that caused the duplicate insertion.

---

## v1.5 Admin Screens Cleanup (Shipped: 2026-07-12)

**Phases completed:** 10 phases, 55 plans, 110 tasks

**Key accomplishments:**

- Migration 0012 adds `unpublished` to the `argument_status` PG enum, creates the `argument_status_log` audit table, and backfills one row per argument using its current status — with matching ORM changes and schema test registration.
- Alembic migration 0013 adds `argument_participants.title` and moves appointment columns from `people` to `court_tenures`, with simultaneous ORM/schema/service/frontend cleanup eliminating every person-level `appointing_president` reference.
- TDD implementation of `_parse_toc_titles` + `extract_toc_data` in cover_extractor.py, and `_update_participant_titles` wired into parse.py via a single shared PDF open (D-12).
- Expanded ParseStats with bench/advocate/total speaker counts and cover_metadata fields; added question_number to MetadataUpdate and ArgumentDetail; wired get_job and update_argument_metadata service functions to populate and persist these fields.
- Reusable `ArgumentDetailsCard.svelte` with docket pill input, free-text question number, argued date, always-visible extracted hints, and action-prop-driven form — built in Svelte 5 Runes exclusively.
- Wired ArgumentDetailsCard into /admin/pipeline/[job_id] with saveJobMetadata action, savedValues/hints from load(), expanded parse stat card (8 fields, N/A fallbacks), and removal of the ingest Source file row.
- Closed all five Phase 23 UAT failures: removed two orphaned UI cards, fixed silent docket-clear bug via empty-string sentinel, froze question_number hint to null, and promoted docket instruction from placeholder to always-visible static label.
- Client-side max-count guard prevents a second docket pill from being added, making the server CR-02 rejection unreachable from normal UI interaction.
- 1. [Rule 1 - Bug] Corrupted em-dash in CR-02 comment blocked Edit match
- Admin jobs listing now returns the full pipeline run history newest-first, with incomplete filtering preserved.
- Extracted a standalone `DocketPillInput.svelte` Svelte 5 Runes component from `ArgumentDetailsCard.svelte`'s inline pill logic, ready for reuse on both the job detail page (Plan 03) and the New Run form (Plan 04).
- Refactored ArgumentDetailsCard.svelte to delegate docket pill add/remove/render logic to the shared DocketPillInput component, replacing ~90 lines of inline pill markup and state with a single keyed component instance.
- Typed FastAPI/Pydantic contract for run readiness, failed-step recovery, job-scoped mini create-person, and a new resolve-row side/title mutation that allows BENCH — all guarded by argument ownership derived from job_id.
- Typed FastAPI/Pydantic `ResolveRow` shape and job-scoped `GET /api/admin/jobs/{job_id}/resolve-rows` endpoint that returns every participant on a job's argument — including unresolved rows — with backend-derived tenure-based bench role, an explicit "Missing tenure" state, and advocate title/hint data.
- SvelteKit `+page.server.ts` load/action bridge for the Phase 25 job detail page — new readiness, failed-recovery, and resolve-row HTTP fetches feeding a computed `readonlyMode`, plus a `saveResolveRow` action and extended `addPerson`/`saveJobMetadata` actions — including two router endpoints (`GET .../readiness`, `GET .../failed-recovery`) that Plan 25-01 had built the service layer for but never exposed over HTTP.
- Four new Svelte 5 components (RunStatusCard, ResolveCard, FailedStepGuidance, CreatePersonPopover) plus a full `+page.svelte` recomposition that turns `/admin/pipeline/[id]` into a sibling-card operator workflow — run status first, resolve fully restructured with locked columns and side-first gating, failed recovery contextual to its step card, and Danger Zone unchanged and last.
- Rewrote publish/unpublish/delete/slug-freeze/list guards to key on Argument.status (not published_at), and started writing the ArgumentStatusLog audit trail on every transition.
- New `list_argument_speakers` service helper backing `ArgumentDetail.status_log` and `ArgumentDetail.speakers` (unified bench+advocate rows with utterance counts), plus a writable advocate `title` on the existing participant-update endpoint.
- Arguments list gains a three-state (Draft/Published/Unpublished) badge, a Created column, and status-driven row actions; RunStatusCard gains a neutral-grey "Archived" badge override for already-created pipeline runs.
- Rebuilt the `/admin/arguments/[id]` edit page around the three-state lifecycle: Status card with Created/Published dates and in-card Publish/Unpublish, a new timestamped Status history card, a unified Speakers section replacing the old Advocate Roles card and tenure-gap banners, and a Draft-only delete gate.
- Tightened delete_argument to a single positive DRAFT-only status gate and added an authoritative backend + explicit UI guard preventing an unresolved advocate's side from being silently persisted.
- Closed Phase 26 UAT gap (Test 18) by adding `is_archived` to `AdminJobResponse` via a `list_jobs()` outerjoin on `Argument`, and rendering the same grey "Archived" badge on `/admin/pipeline` that RunStatusCard already shows on the detail page.
- New Alembic migration 0016 adds people.birthdate; admin_people schemas gain per-tenure appointment fields, drop person-level Role, and add a two-field PersonCreateRequest
- `list_people`/`_missing_fields` now drive Bench/Advocate tabs, click-to-filter-by-missing-field, and per-tab columns (tenure coverage/gap, distinct argument count) with zero person-level Role and zero N+1 tenure queries
- `get_person_detail`/`update_person`/`_replace_tenures` now carry birthdate + per-tenure appointment data with zero person-level Role, and a new `POST /people` exposes a general `create_person` behind the standard admin-auth boundary
- `/admin/people/` is now a tabbed "People" directory (Bench default, Advocate via `?tab=`) with click-to-filter missing-field pills, a Bench-only tenure-gaps toggle, and a "Create person" entry point — all driven by Plan 27-02/27-03's `is_justice`/`missing`/`tenure_gaps` query-param contract
- `/admin/people/[id]` rebuilt into Identity/Photo/Biography/Person Type cards with a Bench/Advocate segmented toggle that slide-reveals Birth Date, disabled Death Date, and bordered Tenure Period sub-cards carrying free-text appointment fields — the Role field and its inline-creation machinery are gone entirely
- `/admin/people/new` — a new static route reusing the `/admin/people/[id]` editor's Identity/Person Type card structure, with a three-state (unselected) Bench/Advocate toggle, D-08 minimum validation, and a create action that POSTs to the general `POST /api/admin/people` endpoint before redirecting into the freshly-created person's editor
- Fixed zero-horizontal-padding defect on all four middle columns (Tenure coverage, Tenure gap, Argument count, Missing fields) in the /admin/people list table, restoring the codebase's 8px gutter convention.
- Closed UAT Gap 3 — PersonCreateRequest, create_person, and the SvelteKit create action now carry first_name/middle_name/last_name/name_suffix end-to-end, matching the [id] editor's save behavior.
- Converted the tenure sub-card's President's Party free-text input to a curated `<select>` (six historical US parties + blank + legacy-value fallback), reversing D-16 for that field only while leaving Appointing President free-text.
- Relocated the hidden birthdate/tenures save-form inputs outside the Bench/Advocate toggle's conditional, and completed the person-id-change reset effect to also re-derive tenureRows/nextKey — closing the two BLOCKER data-loss defects (CR-01, CR-02) that failed Phase 27's third verification pass.
- Replaced a self-referential `nextKey` $state read+write inside the person-id-change reset `$effect` with a write-only pattern using a local non-reactive counter, eliminating the infinite-loop regression introduced by the 27-10 CR-02 fix.
- Seven read-only COUNT/MAX/LIMIT aggregation service functions across three admin service files, plus a new Pydantic schema module and DB-gated test suite proving their I/O contracts against the corpus-scale (~7,800 row) dev database.
- Seven thin, resource-scoped GET routes on the existing `/api/admin` router exposing Plan 01's aggregation service functions, each literal route registered before its `{id}`-parameterized sibling and proven via a DB-gated test suite to resolve 200 (not 422).
- Rewrote `/admin/` from a placeholder into an at-a-glance operator dashboard: a new shared `StatCard.svelte` component, a sequential degrade-gracefully `load()` fetching all seven Plan 02 endpoints, and a `+page.svelte` rendering Needs Attention first, four neutral stat cards, then a visually-distinct Web Traffic placeholder — all from DESIGN-SYSTEM.md tokens with no mockup pass.
- External services require manual configuration.
- Three tested pure-Python modules -- streaming JSONL loader, typo-tolerant curated-vocabulary stage-direction detector, and a positive apolitical allowlist extractor -- that Plan 05's ConvoKit importer will orchestrate.
- A new `import-justices` CLI command upgrades the 13 pre-existing seed_aliases.py Person rows in place (is_justice=True + court_tenures) and creates the remaining historical justices, with idempotent check-before-insert dedup and auto dual-tenure handling for elevated justices.
- New `import-convokit` term-batched CLI command that idempotently scaffolds draft Case/Argument/CaseArgument/PipelineRun rows and resolves bench/advocate speakers into Person/ArgumentParticipant rows, entirely from conversations.json/cases.jsonl/speakers.json with a provably apolitical field allowlist.
- Streams ConvoKit utterances.jsonl one term at a time (never the full 900MB file) into Utterance rows with `\n` boundaries preserved verbatim, splits curated-vocabulary stage-direction markers (including inline mid-turn ones) into their own rows via the existing `detect_stage_direction` helper, and prints a per-term/rollup summary of created/skipped/matched/flagged/errored counts.
- Static /attributions page (Oyez.org/ConvoKit/SCDB credits + CC BY-NC 4.0 callout), a server-gated per-argument attribution note, TopNav entry point, and README credit — clearing the D-26 gate before any corpus-imported argument can go live
- ArgumentMetadataResponse and CaseItem now accept argued_date=None without a pydantic ValidationError, closing the BLOCKER gap where GET /arguments/{id}/utterances 500'd for historical corpus rows lacking a parseable transcript date.
- `pipeline/commands/import_convokit.py`'s single per-argument `PipelineRun` now writes `step="parse"` instead of `step="ingest"`, and a new end-to-end test proves `get_argument_with_utterances` now returns the actual, non-empty, correctly-attributed `Utterance` rows for a corpus-imported argument — closing the gap 29-07-PLAN.md's own regression test explicitly left open.
- Per-docket `question_number` derivation aligned with the DB's real `(source_docket, question_number)` UNIQUE constraint, plus a distinct `docket_question_conflict` counter and explicit `IntegrityError` safety net, so reargued cases and PDF-ingest-overlap dockets import instead of being silently dropped into `conversations_errored`.
- Corpus-imported arguments now start at `status=PIPELINE` (not `DRAFT`) and are paired with a HIT-shaped `PAUSED`/`RESOLVE` `AdminJob`, making the existing resolve→approve→publish workflow reachable for the ~7,800 historical corpus arguments for the first time.
- Derived `source: Literal["pdf","corpus"]` field on `AdminJobResponse`, computed at read time in both `list_jobs()` and `get_job()` via a duplication-safe `exists()` subquery on `PipelineRun.strategy == "convokit_import"` — no schema change.
- Quiet neutral "PDF"/"Corpus" provenance tag added to the /admin/pipeline/ list table, positioned between Status and Created, using only pre-existing color tokens.
- Term-1955 corpus batch (163 arguments) wiped via a scoped FK-safe transaction and re-imported through the 30-01-patched path, landing at status=PIPELINE with paired paused/resolve AdminJobs — closing the D-02 stored-data gap that left the batch permanently unpublishable and unreviewable.
- GET /api/admin/arguments now accepts an allow-list-guarded `?status=` query param that narrows results to a single status end-to-end, with a new segmented filter control, active-filter indicator, and filtered empty-state on the `/admin/arguments` list page (DASH-02).
- `/admin/arguments/[id]` now renders the shared `ArgumentDetailsCard.svelte` component as a true second consumer, with the old hand-rolled docket/date form reduced to a small "Case" identity card whose `?/save` action no longer touches `argued_date` (AEDIT-04).
- Migration 0019 makes arguments.question_number nullable (parity with argued_date); admin router now catches IntegrityError as a 409 instead of leaking a 500; CaseItem/ArgumentMetadataResponse schemas accept None

---

## v1.4 Admin Completeness (Shipped: 2026-07-02)

**Phases completed:** 4 phases (18–21), 13 plans
**Timeline:** 2026-06-29 → 2026-07-02 (3 days)
**Files changed:** 94 | **Net lines:** +11,903 / -330
**Closeout type:** verified_closeout (10/10 requirements shipped; 2 stale todos closed at milestone)

**Key accomplishments:**

- `is_justice` boolean migration (0010) with tenure-based backfill; people editor conditionally renders bench-only sections (Role, Court Tenure, Appointment) based on `is_justice`; Justice badge in directory listing (PEOPLE-05/06/07)
- Duplicate argument prevention — DB UNIQUE constraint on `(source_docket, question_number)` via migration 0011; preflight UI check before pipeline run start with duplicate warning banner (PIPE-25)
- Argument metadata prefill — `cover_extractor` extracts docket from PDF cover; `cover_metadata` JSONB written at parse; job detail Argument Metadata card with auto-populated fields operator can override (PIPE-26)
- Live pipeline status — unconditional 1s `$effect`/`invalidateAll()` polling on list page; detail-page step card polling human-verified live (PIPE-23/24)
- Argument delete with FK-ordered cascade (Utterance → PipelineRun → ArgumentParticipant → CaseArgument → NULL AdminJob.argument_id → Argument); published guard returns 409; two-step inline confirm UI (ADMIN-01)
- Pipeline run delete — `delete_job` removes admin_job row only; argument and its utterances survive; two-step confirm UI with redirect to /admin/pipeline (ADMIN-02)
- Unified admin nav — `AdminSubNav` component + `TopNav variant=public` in admin layout; dead `variant=admin` TopNav branch removed; NAV-02 gap closed via Plan 21-04 (NAV-02)

---

## v1.3 Speaker Accuracy + Pipeline Confidence (Shipped: 2026-06-29)

**Phases completed:** 3 phases (15–17), 9 plans
**Timeline:** 2026-06-25 → 2026-06-29 (5 days)
**Commits:** 84 | **Files changed:** 73 | **Net lines:** +11,791 / -177
**Closeout type:** override_closeout (1 acknowledged item — Phase 11 human_needed verification, v1.2 carry-over)

**Key accomplishments:**

- Tenure-aware speaker popover — Justices now show the role they held at the argument's argued_date via `_tenure_role_name()` date-range lookup; D-14 fallback to most-recent tenure; advocates show per-argument side (PETITIONER/RESPONDENT/AMICUS) via ADVOCATE_LABEL_MAP (ROLE-01, ROLE-02)
- Per-argument advocate role editor — IDOR-guarded PATCH `/api/admin/arguments/{id}/participants/{pid}` with advocate role dropdowns on both argument edit page and pipeline job detail UI; each save is isolated per argument (ROLE-03)
- Argument status lifecycle — new argument_status enum (pipeline/draft/published) via Alembic migration 0008 + ArgumentStatusEnum ORM; approve action transitions pipeline→draft and unlocks public visibility gate
- Cover-page metadata extraction — `cover_extractor.py` extracts argued_date and case_name from PDF transcript via regex; parse step writes both to DB after dry-run gate without blocking parse on extraction failure (PARSE-01)
- TOC advocate side detection — `_update_participant_sides()` maps ESQ. name pairs from transcript TOC to PETITIONER/RESPONDENT/AMICUS and seeds argument_participants.side after step 7b (PARSE-02)
- Pipeline UI polish — Ingest source filename (migration 0009), Parse stat cards (utterance count, speaker count, extracted metadata), same-origin SvelteKit PDF proxy keeping ADMIN_TOKEN server-side throughout (PIPE-21, PIPE-22)

---

## v1.2 Pre-Launch Polish (Shipped: 2026-06-25)

**Phases completed:** 6 phases (9–14), 21 plans
**Timeline:** 2026-06-18 → 2026-06-25 (7 days)

**Key accomplishments:**

- Structured people schema — Alembic migration 0006 adds six nullable name-part and appointing president columns to `people`; `_derive_full_name` preserves `full_name` as resolution anchor; edit form extended with name-parts grid and Appointment section (PEOP-01, PEOP-02)
- Unified navigation — shared `TopNav.svelte` (variant prop) wired to both root and admin layouts; single component, no duplicate markup; admin auth guard stays in layout (NAV-01)
- Argument metadata editing — migration 0007 adds `published_at` to arguments; public visibility gate swapped from `resolved_at` to `published_at`; admin edit page with case title/docket/date + read-only after publish; `ArgumentUpdate` allow-list prevents mass-assignment (ARG-01, ARG-02)
- People admin tooling — photo upload to DO Spaces or URL, orphan-safe delete returning 409 when FK rows exist, merge transferring all 4 FK tables in single `db.begin()` transaction with preview count (PADM-01–04)
- Ingestion flow polish — `lastKnownStep` $state fallback for null-transition step badges (PIPE-18); custom Svelte 5 Runes combobox replacing native datalist (PIPE-19); incomplete filter toggle with empty state (PIPE-20)
- Speaker popover card — `SpeakerPopoverEntry` schema + `get_argument_speakers` service (no N+1 lazy loads); bits-ui ^2.18.1 for Svelte 5-native headless popover; `appointing_president_party` excluded at schema level (apolitical constraint) (PUB-01–03)

---

## v1.1 Operator Admin Interface (Shipped: 2026-06-18)

**Phases completed:** 4 phases (5–8), 19 plans, 33 tasks
**Timeline:** 2026-06-15 → 2026-06-18 (4 days)
**Commits:** 155 (v1.0 → v1.1) | **Files changed:** 120 | **Net lines:** +23,277 / -1,410

**Key accomplishments:**

- Operator admin area secured end-to-end — HMAC stateless session cookie (`node:crypto`), `hooks.server.ts` sole auth checkpoint, dark-theme login page with constant-time credential validation, logout action, AUTH-01/02/03 all verified
- FastAPI admin router at `/api/admin` with router-level `X-Admin-Token` dependency, admin_jobs service layer (Pydantic schemas, atomic step-advance guards, boto3 DO Spaces upload, detached subprocess spawn)
- Three pipeline commands (ingest, parse, resolve) made job-aware via `--job-id`: each writes RUNNING/COMPLETED/FAILED to admin_jobs; resolve replaces terminal prompts with discrepancy JSONB + PAUSED state
- Pipeline Runner UI — two-mode start page (URL/file upload), live step cards polling every 2.5s, auto-advance on clean resolve, pauses for discrepancy review; fire-and-poll pattern survives browser close (PIPE-17)
- Discrepancy review workflow — HIT rows pre-confirmed with single Change button, MISS rows with Correct/Override; people-backed typeahead (full roster via server-loaded data); inline add-new-person via `use:enhance` for reliable devalue deserialization
- `arguments.resolved_at` visibility gate — cases hidden from `/cases/` until resolve completes; no placeholder metadata leaks publicly (Alembic migration 0004)
- People directory at `/admin/people` — filterable by incomplete metadata, edit form with bio text / photo URL / tenure dates / role create (Alembic migration 0005); per-argument participant review after pipeline run

---

## v1.0 MVP (Shipped: 2026-06-15)

**Phases completed:** 4 phases (1–4), 15 plans, 76 commits
**Timeline:** 2026-06-11 → 2026-06-15 (4 days)
**Lines of code:** ~4,895 (TypeScript + Svelte + Python) across 146 files

**Key accomplishments:**

- SvelteKit 2 + Svelte 5 Runes scaffold with adapter-node, final route `/cases/[slug]/arguments/[id]` from day one, stub ChatBubble/StageDirection components, Python dependencies, pytest config, PowerShell dev startup script
- 10-table PostgreSQL schema via hand-written Alembic migration — people/roles/tenures/cases/arguments/case_arguments/appearances/participants/pipeline_runs/utterances — supporting M:M consolidated dockets and idempotent re-runs via `pipeline_run_id`
- Async pipeline CLI: `ingest` (SSRF-validated PDF download, immutable storage) + `parse` (pdfplumber extraction, rule-based state machine, instructor/tenacity LLM corrective pass)
- Speaker resolution: `speaker_alias` table + `resolve` step + `GET /people/{id}` API; ChatBubble displays resolved names with role labels and raw-label fallback
- FastAPI `GET /arguments/{id}/utterances` with PgBouncer-safe async engine (`statement_cache_size=0` in `connect_args`), max-pipeline-run-id filtering, and full chat layout in SvelteKit
- Full browseable UI: SSR case list, slug routing with 307 redirect, CSS Grid argument layout, avatar initials circles, SectionRail scroll-spy
- WCAG 2.1 AA accessibility: global focus ring, ARIA article semantics, HTML5 landmarks on all pages, MobileNavBar for narrow viewports; `#475569` eliminated from entire `app/src/` tree

**Known deferred items at close:** 4 (see STATE.md Deferred Items — stale verification status markers; human UAT completed per commits)

---
