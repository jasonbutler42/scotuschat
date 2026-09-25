---
phase: 52-justice-identity
verified: 2026-09-25T15:56:08Z
status: human_needed
score: 8/10 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/52-justice-identity/52-01-PLAN.md", ".planning/phases/52-justice-identity/52-01-SUMMARY.md", ".planning/phases/52-justice-identity/52-02-PLAN.md", ".planning/phases/52-justice-identity/52-02-SUMMARY.md", ".planning/phases/52-justice-identity/52-03-PLAN.md", ".planning/phases/52-justice-identity/52-03-SUMMARY.md", ".planning/phases/52-justice-identity/52-04-PLAN.md", ".planning/phases/52-justice-identity/52-04-SUMMARY.md", ".planning/phases/52-justice-identity/52-05-PLAN.md", ".planning/phases/52-justice-identity/52-05-SUMMARY.md", ".planning/phases/52-justice-identity/52-06-PLAN.md", ".planning/phases/52-justice-identity/52-06-SUMMARY.md", ".planning/phases/52-justice-identity/52-CONTEXT.md", ".planning/phases/52-justice-identity/52-REVIEW.md", ".planning/phases/52-justice-identity/deferred-items.md", "alembic/versions/0032_person_display_name_and_oyez_unique.py", "api/domain/person_names.py", "api/models/models.py", "api/routers/admin_dev.py", "api/schemas/admin_dev.py", "api/schemas/admin_people.py", "api/schemas/speakers.py", "api/schemas/utterance.py", "api/services/admin_dev.py", "api/services/admin_people.py", "api/services/admin_review.py", "api/services/arguments.py", "api/services/speakers.py", "api/tests/test_admin_dev_routes.py", "api/tests/test_admin_people_resolve_initials.py", "api/tests/test_admin_people_schema_readonly.py", "api/tests/test_arguments.py", "api/tests/test_authority_matrix.py", "api/tests/test_person_names.py", "api/tests/test_public_arguments_listing.py", "api/tests/test_speakers_service.py", "app/src/lib/admin/ResolveCard.svelte", "app/src/lib/public/SpeakerPopover.svelte", "app/src/lib/types/speaker.ts", "app/src/routes/admin/+page.server.ts", "app/src/routes/admin/+page.svelte", "app/src/routes/admin/dev-fixture-state/+server.ts", "app/src/routes/admin/people/[id]/+page.server.ts", "app/src/routes/admin/people/[id]/+page.svelte", "app/src/routes/admin/pipeline/[job_id]/+page.server.ts", "app/src/routes/arguments/[slug]/+page.server.ts", "app/src/routes/arguments/[slug]/+page.svelte", "app/tests/speaker-initials.browser.test.mjs", "pipeline/commands/import_justices_csv.py", "pipeline/tests/test_import_justices_csv.py", "pipeline/tests/test_justice_identity_mapping.py", "pipeline/tests/test_justice_identity_resolution.py", "tests/test_admin_dev_frontend_gate.py", "tests/test_admin_dev_router_gate.py"]
covered_digest: "v1:sha256:3ded15088464388df80082fd3c5ad0af2aff4bb6af2162e90f5711fa8bdcd6c8"
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "D-14: on any reset failure the frontend re-reads fixture state before asserting anything, and shows one of full-success/partial/inconclusive/environment-refusal based on what the re-read actually found — never the blanket corruption claim by default."
    test: "Start the dev stack, run Reset to Fixture through its two-step confirm, then kill the FastAPI process mid-reset to force a failure."
    expected: "The page reports the partial-reseed message (or full success, or the evidence-free fallback) matching what a fresh fixture-state read actually shows — never the old blanket 'possible data corruption' claim for a failure the code has no basis to assert."
    why_human: "This is SvelteKit server-action/client branching logic (resolveFromReRead, pollResetProgress). Per CLAUDE.md's Testing Policy, frontend runtime behavior is verified by the operator's eye or a real browser, never a source-text contract test, and this project has no browser harness for the auth-gated admin surface."
  - truth: "D-15: the Running state advances through five real per-fixture progress steps (Seeding justices… then Reseeding fixture N of 4…) reflecting the backend's actual polled progress, never a timer-driven guess, and never reports a step before it happens."
    test: "Watch the status line for a full real reset run against the dev database."
    expected: "The line advances in place, in order, with no layout shift, and lags reality rather than leading it."
    why_human: "Same class as above — live polling behavior behind session auth, no browser harness available in this sandbox."
human_verification:
  - test: "Open /admin/people/{id} for a corpus-joined justice (non-blank Oyez Speaker ID) and for an advocate or a D-04 justice (Barrett/Jackson). Confirm: (1) the two new rows sit between Full Name and the Name Parts inputs; (2) they match the Full Name readout's box/border/padding/text size; (3) the justice shows real values and the other person shows 'Not in corpus' in grey italic in both rows; (4) neither row can be typed into or focused as a form control."
    expected: "Placement, treatment, and empty/populated contrast match 52-UI-SPEC.md exactly, as described above."
    why_human: "Visual placement and styling — CLAUDE.md Testing Policy forbids a static source-text contract test for this; deferred to end-of-phase UAT per workflow.human_verify_mode."
  - test: "Run one real reset against the dev database: open /admin, run Reset to Fixture through its two-step confirm, watch the status line for the whole run, then open the People directory. Optionally kill the FastAPI process mid-reset to observe the partial-reseed message."
    expected: "Status line advances Seeding justices… → Reseeding fixture 1 of 4… → …4 of 4, in place, never leading reality; Success state renders on completion; People directory shows the full justice roster; a mid-reset failure shows the evidence-based partial/inconclusive message, not the blanket corruption claim."
    why_human: "Live end-to-end UI behavior of the D-14/D-15 rework — no browser harness for the auth-gated admin dev-tools surface in this sandbox."
  - test: "Open an admin pipeline job's Resolve card for an argument with a bench row whose person has a name suffix. Confirm the avatar circle shows JH for John Marshall Harlan, II (not the suffix letter), and confirm an unresolved row's avatar looks exactly as it did before this change."
    expected: "Avatar renders JH (not JI); unresolved-row avatar is visually unchanged."
    why_human: "The admin Resolve card sits behind session auth with no browser harness in this repo. The public-surface equivalent of this same derive_initials call IS mechanically proven by app/tests/speaker-initials.browser.test.mjs in a real Chromium."
---

# Phase 52: Justice Identity Verification Report

**Phase Goal:** Every justice in the corpus resolves to exactly one person record, joined by a verified stable key that survives a fixture reset, with each name form shown where it belongs.
**Verified:** 2026-09-25T15:56:08Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1 / JUSTICE-01,02: 114 corpus justices resolve on `oyez_speaker_id`; a spelling difference between the two sources no longer mints a second row | ✓ VERIFIED | `data/corpus/justice_identity_mapping.csv` — 114 data rows, no `confidence` column, header matches D-06/D-07/D-08; `pipeline/tests/test_justice_identity_mapping.py` (7 tests, coverage+structural, re-run pass); `pipeline/tests/test_justice_identity_resolution.py::test_rerun_creates_no_second_white_row` and `::test_existing_person_with_id_but_different_full_name_is_upgraded` re-run pass against real Postgres |
| 2 | SC2 / JUSTICE-03: utterance attribution reads the corpus form (`display_name`), bio card reads the fuller CSV form (`full_name`); an advocate with no display name is unaffected | ✓ VERIFIED | `api/services/arguments.py:243` — `func.coalesce(Person.display_name, Person.full_name).label("speaker_name")`; `pipeline/tests/test_justice_identity_resolution.py::test_speaker_name_coalesces_display_name_then_full_name` re-run pass; `api/tests/test_admin_dev_routes.py::test_reset_justice_utterance_speaker_name_uses_corpus_display_form` re-run pass |
| 3 | SC3 / JUSTICE-04: `reset_to_fixture` seeds the full justice roster after TRUNCATE, so the People directory shows the bench, not an empty list | ✓ VERIFIED | `api/services/admin_dev.py` — `run_import_justices_csv` called between `TRUNCATE_SQL` execution and the `FIXTURE_SET` loop (D-16); `api/tests/test_admin_dev_routes.py::test_reset_seeds_full_justice_roster`, `::test_reset_justice_seed_is_idempotent`, `::test_reset_missing_justice_csv_raises_before_truncate` all re-run pass |
| 4 | SC4 / JUSTICE-05: a second row carrying an already-used `oyez_speaker_id` is refused by Postgres itself, not only application code | ✓ VERIFIED | Migration 0032 — `uq_people_oyez_speaker_id`, `postgresql_where=sa.text("oyez_speaker_id IS NOT NULL")`; `pipeline/tests/test_justice_identity_resolution.py::test_duplicate_oyez_speaker_id_raises_integrity_error` (raises `IntegrityError` from a raw `Person` insert, no application-level gate involved) and `::test_multiple_null_oyez_speaker_id_rows_coexist` both re-run pass |
| 5 | SC5 / JUSTICE-06: `John Marshall Harlan, II` renders `JH`, not `JI` | ✓ VERIFIED | `api/domain/person_names.py::derive_initials` ignores `name_suffix`; `app/tests/speaker-initials.browser.test.mjs` re-run in a real Chromium — 1 passed, asserts literal rendered strings `JH`/`OH`/`?` in both the transcript avatar and the popover fallback avatar |
| 6 | D-12: exactly one initials implementation exists in the codebase, repository-wide (public surfaces via 52-02, admin `ResolveCard.svelte` via 52-06) | ✓ VERIFIED | `grep -rn 'def derive_initials\|def getInitials\|def get_initials' api/ pipeline/` → exactly 1 hit; `grep -rn 'getInitials\|get_initials' app/src/` → 0 hits; `grep -rnE 'split\(/\\s\+/\)' app/src/` → 0 hits (all re-run live) |
| 7 | D-09/D-10: `display_name`/`oyez_speaker_id` are visible and read-only on the admin person page — a PATCH carrying either gets a 422 | ✓ VERIFIED | `api/schemas/admin_people.py` — `PersonDetail` declares both fields; `PersonUpdate` does not, and carries `extra="forbid"`; `api/tests/test_admin_people_schema_readonly.py` (4 tests) re-run pass, proving the 422 through a real ASGI PATCH request |
| 8 | Code-review WR-01 fix: two term-year test bands no longer collide with their neighbor's band | ✓ VERIFIED | `api/tests/test_public_arguments_listing.py:220-221,334-335` — offsets now drawn from `% 9` not `% 10`, with an in-line comment explaining the boundary case; `api/tests/test_public_arguments_listing.py` re-run — 18/18 pass |
| 9 | D-14: on any reset failure, the frontend re-reads fixture state before asserting anything, and shows one of four evidence-based outcomes instead of a blanket corruption claim | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Backend wiring present and unit/integration-tested (`GET /api/admin/dev/fixture-state`, `resolveFromReRead` convergence point in `+page.server.ts`); no test exercises the live end-to-end frontend failure→re-read→render path — see Human Verification |
| 10 | D-15: the Running state advances through five real per-fixture progress steps, never reporting a step before it happens | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Backend progress record tested (`test_reset_progress_advances_through_expected_steps_then_clears`, `test_reset_progress_cleared_after_mid_reset_failure`, both re-run pass); the frontend polling loop's live-observed ordering is not exercised by any test — see Human Verification |

**Score:** 8/10 truths verified (2 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/corpus/justice_identity_mapping.csv` | 114-row verified mapping, no `confidence` column | ✓ VERIFIED | 115 lines (114 data + header), header exactly `oyez_speaker_id,corpus_display_name,first_name,middle_name,last_name,name_suffix`; gitignored by design per `data/corpus/.gitignore` (present on disk, confirmed) |
| `alembic/versions/0032_person_display_name_and_oyez_unique.py` | nullable `display_name` + partial unique index | ✓ VERIFIED | Adds `people.display_name` (String(300)) and `uq_people_oyez_speaker_id` with `postgresql_where`; symmetric `downgrade()` |
| `pipeline/tests/test_justice_identity_mapping.py` | permanent structural/coverage regression suite | ✓ VERIFIED | 7 tests, re-run pass |
| `pipeline/tests/test_justice_identity_resolution.py` | end-to-end Byron White resolution + edge cases | ✓ VERIFIED | Re-run pass, includes the IntegrityError and multiple-NULL tests |
| `app/tests/speaker-initials.browser.test.mjs` | real-Chromium regression for JH/OH/`?` | ✓ VERIFIED | Re-run pass (15.1s) |
| `api/tests/test_admin_people_schema_readonly.py` | proves 422 refusal via real PATCH | ✓ VERIFIED | Re-run pass |
| `api/tests/test_admin_people_resolve_initials.py` | proves `ResolveRow.initials` populated/null | ✓ VERIFIED | Re-run pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| Mapping CSV name-part key | `import_justices_csv` row lookup | `Person.oyez_speaker_id` write | WIRED | `_load_justice_mapping` builds a name-part-keyed dict; import loop looks up by the same normalized key and writes `oyez_speaker_id`/`display_name` |
| `Person.first_name/last_name/name_suffix` | `derive_initials` | `SpeakerPopoverEntry.initials` / `UtteranceResponse.speaker_initials` / `ResolveRow.initials` | WIRED | Single call site per file in `api/services/speakers.py`, `api/services/arguments.py`, `api/services/admin_people.py`; confirmed by grep and by passing integration tests reading the real service output |
| `TRUNCATE` commit | `run_import_justices_csv` seed | `FIXTURE_SET` reseed loop | WIRED | `api/services/admin_dev.py` — seed call sits strictly between the TRUNCATE execution and the fixture loop (D-16), confirmed by source-order grep and by `test_reset_seeds_full_justice_roster` |
| `PersonUpdate extra=forbid` | 422 on posted `display_name`/`oyez_speaker_id` | Pydantic model config | WIRED | Both fields absent from `PersonUpdate`; `extra="forbid"` config present; proven via real ASGI PATCH test |
| `reset_to_fixture` progress record | `GET /api/admin/dev/fixture-state` | SvelteKit proxy → Running-state text | WIRED (backend); UI-observed behavior deferred | Endpoint, progress record, and proxy route all exist and are tested at the API/integration layer; the rendered polling behavior itself is a human-check item (see above) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| JUSTICE-01 | 52-01 | Verified per-justice mapping, 114 rows, stored as data not derived by name matching | ✓ SATISFIED | Mapping CSV + coverage tests |
| JUSTICE-02 | 52-01 | `import_justices_csv` writes `oyez_speaker_id` from the mapping; `_resolve_person` matches on it first | ✓ SATISFIED | Import loop dedup key; resolution tests |
| JUSTICE-03 | 52-01, 52-02, 52-03 | `display_name` column; bio card reads `full_name`; utterances read `display_name` with fallback | ✓ SATISFIED | Migration 0032, COALESCE, admin read-only fields |
| JUSTICE-04 | 52-04, 52-05 | `reset_to_fixture` seeds all justices after TRUNCATE, persisting through every reset | ✓ SATISFIED (backend); UI live-behavior deferred | Seed insertion point, pre-flight, progress record; D-14/D-15 UI behavior is a human-check item |
| JUSTICE-05 | 52-01 | Partial unique index makes duplicate justice rows structurally impossible | ✓ SATISFIED | `IntegrityError` test against real Postgres |
| JUSTICE-06 | 52-02, 52-06 | Avatar initials derive from first/last name, skipping suffixes | ✓ SATISFIED | `derive_initials`, real-browser test, repo-wide singularity sweep |

No orphaned requirements — `.planning/REQUIREMENTS.md` maps exactly JUSTICE-01 through JUSTICE-06 to Phase 52, and all six appear in at least one plan's `requirements` frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `api/schemas/admin_people.py` | 314, 324 | `# TODO: orphaned by Phase 27 — person-level roles removed; safe to ...` | ℹ️ Info | Pre-existing since a Phase-9/18/27-era commit (confirmed via `git log` — not introduced or touched by Phase 52); not a debt marker under the TBD/FIXME/XXX gate |
| `api/services/admin_people.py` | 686 | Same TODO, same provenance | ℹ️ Info | Pre-existing, untouched by this phase |

No `TBD`, `FIXME`, or `XXX` markers found in any file this phase modified. No stub returns, no hardcoded empty payloads reaching rendered output, no console.log-only handlers found in the 39 impl files reviewed.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Mapping/resolution/index/coverage test suite | `pytest pipeline/tests/test_justice_identity_mapping.py pipeline/tests/test_justice_identity_resolution.py api/tests/test_person_names.py api/tests/test_admin_people_schema_readonly.py api/tests/test_admin_people_resolve_initials.py api/tests/test_authority_matrix.py -q` | 162 passed | ✓ PASS |
| Reset-to-fixture, gate, speaker/argument/import suites, WR-01 fix | `pytest api/tests/test_admin_dev_routes.py tests/test_admin_dev_router_gate.py tests/test_admin_dev_frontend_gate.py api/tests/test_speakers_service.py api/tests/test_arguments.py pipeline/tests/test_import_justices_csv.py api/tests/test_public_arguments_listing.py -q` | 128 passed | ✓ PASS |
| Real-Chromium JH/OH/`?` rendering | `node --test app/tests/speaker-initials.browser.test.mjs` | 1 passed (15.1s) | ✓ PASS |
| Repo-wide initials singularity sweep | `grep -rn 'def derive_initials\|def getInitials\|def get_initials' api/ pipeline/` → 1 hit; `grep -rn 'getInitials\|get_initials' app/src/` → 0 hits | as expected | ✓ PASS |
| Frontend typecheck/build | `npm --prefix app run check` / `run build` | 0 errors, 32 pre-existing warnings (unchanged baseline); build exit 0 | ✓ PASS |

### Probe Execution

Not applicable — this phase has no `scripts/*/tests/probe-*.sh` conventional probes, and no plan or the ROADMAP success criteria reference probe-based verification.

### Human Verification Required

See `human_verification` in frontmatter for the full detail. Three items, all harvested from `<verify><human-check>` blocks the planner deliberately deferred to end-of-phase UAT (this project runs `workflow.human_verify_mode: end-of-phase`), plus the two `behavior_unverified_items` (D-14/D-15) that are present-and-wired but have no behavioral test exercising the live UI transition:

1. **Admin person page Identity card placement/treatment** (52-03) — two read-only rows' position, box styling, and empty/populated contrast.
2. **Live reset-to-fixture run** (52-05) — the five-step progress line's ordering/lag behavior and the four evidence-based outcome states, observed against a real reset (including a forced mid-reset failure).
3. **Admin Resolve card `JH` rendering** (52-06) — the third (now-deleted) splitter's replacement rendering correctly for a suffixed name, and the unresolved-row avatar unchanged. Note: the public-surface equivalent of this exact `derive_initials` call IS mechanically proven in a real Chromium by `app/tests/speaker-initials.browser.test.mjs`.

None of these are gaps — they are deferred eye-checks by design (admin surfaces sit behind session auth with no browser harness in this sandbox), not missing work. The underlying backend/schema/service logic for all three is implemented and covered by passing automated tests.

### Gaps Summary

No gaps found. All 5 ROADMAP success criteria are verified against real Postgres and a real Chromium browser test, not against SUMMARY.md claims. All 6 requirement IDs (JUSTICE-01 through JUSTICE-06) are satisfied with re-run passing evidence. The one code-review warning (WR-01, term-year test band collision) has already been fixed in commit `c3f3895ae` and its band comments and `% 9` offsets were confirmed present and correct in the current tree; the affected test file was re-run standalone (18/18 pass). The one code-review info item (IN-01) requires no action per the review's own conclusion. The only open items are three UI-behavior eye-checks the phase's own workflow mode (`end-of-phase`) deliberately defers to the operator — status is `human_needed`, not `gaps_found`.

---

*Verified: 2026-09-25T15:56:08Z*
*Verifier: Claude (gsd-verifier)*
