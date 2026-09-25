---
phase: 52-justice-identity
reviewed: 2026-09-25T00:00:00Z
depth: standard
files_reviewed: 38
files_reviewed_list:
  - alembic/versions/0032_person_display_name_and_oyez_unique.py
  - api/domain/person_names.py
  - api/models/models.py
  - api/routers/admin_dev.py
  - api/schemas/admin_dev.py
  - api/schemas/admin_people.py
  - api/schemas/speakers.py
  - api/schemas/utterance.py
  - api/services/admin_dev.py
  - api/services/admin_people.py
  - api/services/admin_review.py
  - api/services/arguments.py
  - api/services/speakers.py
  - api/tests/test_admin_dev_routes.py
  - api/tests/test_admin_people_resolve_initials.py
  - api/tests/test_admin_people_schema_readonly.py
  - api/tests/test_arguments.py
  - api/tests/test_authority_matrix.py
  - api/tests/test_person_names.py
  - api/tests/test_public_arguments_listing.py
  - api/tests/test_speakers_service.py
  - app/src/lib/admin/ResolveCard.svelte
  - app/src/lib/public/SpeakerPopover.svelte
  - app/src/lib/types/speaker.ts
  - app/src/routes/admin/+page.server.ts
  - app/src/routes/admin/+page.svelte
  - app/src/routes/admin/dev-fixture-state/+server.ts
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/arguments/[slug]/+page.server.ts
  - app/src/routes/arguments/[slug]/+page.svelte
  - app/tests/speaker-initials.browser.test.mjs
  - data/corpus/justice_identity_mapping.csv
  - pipeline/commands/import_justices_csv.py
  - pipeline/tests/test_import_justices_csv.py
  - pipeline/tests/test_justice_identity_mapping.py
  - pipeline/tests/test_justice_identity_resolution.py
  - tests/test_admin_dev_frontend_gate.py
  - tests/test_admin_dev_router_gate.py
findings:
  critical: 0
  warning: 1
  info: 1
  total: 2
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2026-09-25T00:00:00Z
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

Reviewed the justice-identity phase: migration 0032 (`display_name` +
`uq_people_oyez_speaker_id` partial unique index), the single
`derive_initials` implementation and its three call sites, the
`reset_to_fixture` transaction ordering and progress-tracking rework,
`PersonUpdate`'s read-only allow-list for `display_name`/`oyez_speaker_id`,
`pipeline/commands/import_justices_csv.py`'s oyez-id-keyed dedup path, and
the verified `justice_identity_mapping.csv` artifact.

The five areas the review brief flagged all check out:

1. `derive_initials` is genuinely the only implementation — every call site
   (`api/services/admin_people.py`, `api/services/arguments.py`,
   `api/services/speakers.py`) imports it from `api.domain.person_names`,
   and a repo-wide grep for client-side name-splitting patterns
   (`.split(' ')`, `.charAt(0)`, `.slice(0, 2)`) in `app/src/lib`/`app/src/routes`
   found none in `ResolveCard.svelte`/`SpeakerPopover.svelte`/the argument
   page — all three render the server-computed `initials`/`speaker_initials`
   field directly.
2. `reset_to_fixture`'s pre-flight (`_require_corpus_files`) raises before
   the `TRUNCATE` executes (verified: `_require_corpus_files` is called at
   step 1, before `await db.execute(text(TRUNCATE_SQL))` at step 2), and the
   justice seed (`run_import_justices_csv`) runs after the `TRUNCATE`
   commits and before the four-fixture reseed loop, matching the module
   docstring's own transaction-boundary description.
3. `PersonUpdate` (`api/schemas/admin_people.py`) does not declare
   `display_name` or `oyez_speaker_id`, carries `extra="forbid"`, and
   `api/tests/test_admin_people_schema_readonly.py` proves the 422 through a
   live PATCH rather than inspecting `model_fields` alone.
4. Migration 0032's `upgrade()`/`downgrade()` are simple, symmetric, and
   correctly ordered (`downgrade()` drops the index before the column); no
   other migration defines an index named `uq_people_oyez_speaker_id`.
5. The 14 term-year bands in `api/tests/test_public_arguments_listing.py`
   are individually documented and all sit below 1955 — but two of them are
   **not actually disjoint** from their neighbor once a `+1` offset is
   applied (WR-01 below).

One test-reliability issue was found (WR-01); no Critical-tier defects.

## Warnings

### WR-01: Two term-year test bands can collide with their neighbor's band

**File:** `api/tests/test_public_arguments_listing.py:220-221,334-335`
**Issue:** The file's own header comment (lines 211-219) documents "14
disjoint decade bands, each strictly below 1955" as a load-bearing
invariant — each test draws `base + (uuid4().int % 10)` from a private,
non-overlapping base so two tests can never seed a published argument into
the same `term_year` and cause one test's count assertion to see the
other's row.

Two tests break that invariant by drawing a **second** year as `base + 1`
instead of staying within the same `% 10` band:

- `test_terms_counts_published_only_ordered_desc` (line 220-221):
  `base_year = 1850 + (uuid4().int % 10)` → range 1850-1859;
  `later_year = base_year + 1` → range **1851-1860**. When `base_year`
  happens to be 1859, `later_year` is 1860 — inside the *next* test's
  band (`test_terms_excludes_draft_argument`, line 244:
  `year = 1860 + (uuid4().int % 10)` → 1860-1869).
- `test_term_detail_lists_only_published_arguments_for_that_term`
  (line 334-335): `year = 1900 + (uuid4().int % 10)` → 1900-1909;
  `other_year = year + 1` → **1901-1910**. When `year` happens to be 1909,
  `other_year` is 1910 — inside `test_term_detail_excludes_unpublished_with_retained_published_at`'s
  band (line 391: `1910 + (uuid4().int % 10)` → 1910-1919).

Each collision requires both `uuid4()` draws to land on the boundary value
simultaneously (~1% chance per full suite run), so this will not fail on
most runs — but when it does, the two colliding tests both seed a published
`Argument` for the *same* `term_year`, and whichever runs second sees an
extra row it did not create, failing an exact-count assertion
(`terms_by_year.get(year) == 1`, etc.) for a reason that has nothing to do
with the code under test. This is exactly the class of flaky, hard-to-reproduce
failure the file's own comment is trying to prevent by hand-reserving bands.

**Fix:** Either draw the base offset from `% 9` (reserving the band's last
year so `base + 1` never leaves the decade) for any test that computes a
second year via `+ 1`, or move the two affected tests' bases so neither one
borders an adjacent test's band with no gap:
```python
# test_terms_counts_published_only_ordered_desc
base_year = 1850 + (uuid.uuid4().int % 9)  # was % 10 — leaves room for +1
later_year = base_year + 1

# test_term_detail_lists_only_published_arguments_for_that_term
year = 1900 + (uuid.uuid4().int % 9)  # was % 10 — leaves room for +1
other_year = year + 1
```

## Info

### IN-01: Source-text contract test for Dev Tools gate predates this phase's testing policy but is extended by it

**File:** `tests/test_admin_dev_frontend_gate.py:74-141`
**Issue:** CLAUDE.md's Testing Policy states "No static source-text contract
tests for frontend behavior" with a narrow exception for a structural-ban
sweep. `test_dev_tools_section_is_server_gated` asserts on the *rendered
structure* of `+page.svelte` (heading appears once, sits between a
specific `{#if}`/`{/if}` pair, no `display: none`/`visibility: hidden`, no
`<dialog>`) via string search rather than a real render — this is closer to
the banned pattern than the permitted "identifier reaches no public
surface" sweep, since it is trying to prove something about what the page
*shows*, not merely that a forbidden name is absent. The file's own
docstring acknowledges this directly and explains why (a two-process
ENVIRONMENT-flip is impractical for the existing browser harness) with a
manual-UAT fallback noted — this is a deliberate, reasoned exception from
Phase 43, not new debt introduced by Phase 52. Phase 52 only added
`RESET_PARTIAL_ERROR` to the file's existing pattern (`test_error_copies_match_ui_spec`),
so no new instance of the banned pattern was introduced here.
**Fix:** No action required for this phase. If this file is touched again,
consider whether the Playwright/CDP-based `*.browser.test.mjs` harness
(already used by `app/tests/speaker-initials.browser.test.mjs` in this same
phase) could assert the gate's rendered absence for the production case
directly, retiring the structural heading/if-index check in favor of a real
render.

---

_Reviewed: 2026-09-25T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
