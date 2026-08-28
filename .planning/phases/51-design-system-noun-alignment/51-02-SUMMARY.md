---
phase: 51-design-system-noun-alignment
plan: 02
subsystem: api,pipeline,ui,database
tags: [sveltekit, fastapi, sqlalchemy, alembic, postgresql, url-design]

requires:
  - phase: 50-unified-import-path
    provides: the corpus import path (import_convokit.py) whose Argument write site this plan stamps with a slug
provides:
  - "Argument.slug column (migration 0031), stored, unique, immutable once written"
  - "api.domain.argument_slug.derive_argument_slug with a corpus-verified suffix-discriminator choice"
  - "GET /arguments/by-slug/{slug}/utterances and /speakers, sharing get_argument_with_utterances' published gate"
  - "/arguments (flat listing) and /arguments/{slug} (transcript) SvelteKit routes; /cases route tree deleted, no redirect"
  - "Amended DS-01 requirement text agreeing with the shipped flat, no-redirect URL shape"
affects: [51-08-term-grouped-listing, any later plan touching app/src/routes/arguments/**, api/routers/arguments.py, api/services/cases.py]

actuals:
  tokens: 14875
  tasks: 4
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Corpus-scale-verified discriminator choice: before picking a slug-collision suffix field, query the real ~7,800-row corpus rather than assume — question_number is unique-by-construction at write time; argued_date collides or is null in ~46% of the population that actually needs a suffix."
    - "Deferred (function-local) import to break a circular dependency: api.domain.argument_slug imports pipeline.commands.ingest._derive_slug, so pipeline/commands/ingest.py imports api.domain.argument_slug inside the function body, not at module top."
    - "Four-segment by-slug routes as declaration-order-independent peers of existing three-segment {argument_id} routes — no route-ordering dependency introduced."

key-files:
  created:
    - api/domain/argument_slug.py
    - alembic/versions/0031_argument_slug.py
    - api/tests/test_argument_slug.py
  modified:
    - api/models/models.py
    - api/routers/arguments.py
    - api/schemas/cases.py
    - api/services/admin_arguments.py
    - api/services/arguments.py
    - api/services/cases.py
    - api/tests/test_published_gate.py
    - app/src/lib/components/TopNav.svelte
    - app/src/routes/arguments/+page.server.ts
    - app/src/routes/arguments/+page.svelte
    - app/src/routes/arguments/[slug]/+page.server.ts
    - app/src/routes/arguments/[slug]/+page.svelte
    - app/tests/tenure-public-title.browser.test.mjs
    - pipeline/commands/import_convokit.py
    - pipeline/commands/ingest.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "Task 1/Task 2 checkpoints (stored-immutable-slug D-12, flat-no-redirect D-10/D-11) resolved from the already-locked decisions recorded in 51-CONTEXT.md rather than re-prompted — per CLAUDE.md Defect Policy, a locked decision does not get re-asked."
  - "question_number chosen as the primary slug-suffix discriminator over argued_date after querying the real corpus (data/corpus/cases.jsonl): 952/7,748 cases carry >1 transcript (the population needing a suffix at all); of those, 434 (45.6%) have two transcripts whose parsed argued_date is identical or both None, while question_number is always populated and unique-by-construction at write time."
  - "Only two real Argument( write sites exist (pipeline/commands/import_convokit.py, pipeline/commands/ingest.py) — api/services/admin_jobs.py has none (grep-verified); the plan's read_first pointer to admin_jobs.py did not match the code."
  - "Encoded-slash traversal payload (..%2F..%2Fetc%2Fpasswd) verified to return 404, not 422 — ASGI servers percent-decode %2F to a literal / in scope['path'] before Starlette's router runs, so the request never matches the 4-segment route pattern at all and never reaches Path validation. The security property (never dispatch to the service layer) still holds; the status code the plan's acceptance criteria predicted was based on an incorrect assumption about ASGI routing, corrected here rather than pursued via new global middleware."

requirements-completed: [DS-01]

coverage:
  - id: D1
    description: "Argument.slug column + uq_arguments_slug unique constraint, migration 0031, round-trips upgrade/downgrade/upgrade"
    requirement: "DS-01"
    verification:
      - kind: other
        ref: "alembic upgrade head && alembic downgrade -1 && alembic upgrade head (dev DB and scotus_test)"
        status: pass
    human_judgment: false
  - id: D2
    description: "api.domain.argument_slug.derive_argument_slug: reserved-word guard, never-empty guard, collision disambiguation via question_number/argued_date/counter fallback"
    requirement: "DS-01"
    verification:
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_bare_for_common_case"
        status: pass
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_never_returns_reserved_word"
        status: pass
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_never_returns_empty_string"
        status: pass
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_disambiguates_on_question_number"
        status: pass
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_falls_back_to_argued_date_without_question_number"
        status: pass
      - kind: unit
        ref: "api/tests/test_argument_slug.py#test_derive_argument_slug_terminates_with_no_discriminators"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /arguments/by-slug/{slug}/utterances and /speakers resolve under the same published gate as the integer routes; unknown/unpublished slugs 404; path validation rejects malformed slugs"
    requirement: "DS-01"
    verification:
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_published_argument_resolves_by_slug"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_unknown_slug_returns_404"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_unpublished_but_previously_published_argument_404s_by_slug"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_single_segment_traversal_slug_returns_422"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_duplicate_slug_raises_integrity_error_backstop"
        status: pass
      - kind: integration
        ref: "api/tests/test_argument_slug.py#test_update_argument_case_name_edit_leaves_argument_slug_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "/arguments (listing) and /arguments/{slug} (transcript) resolve end to end via real SvelteKit SSR against a live FastAPI backend; /cases route tree is gone; no redirect route exists"
    requirement: "DS-01"
    verification:
      - kind: other
        ref: "live curl against vite dev server + uvicorn after POST /admin/dev/reset-to-fixture: GET /arguments (200, links to real slugs), GET /arguments/anderson-v-liberty-lobby-inc (200, renders case name + utterance text), GET /arguments/does-not-exist-slug (404), GET /arguments/abbott-v-united-states [candidate, unpublished] (404), GET /cases (404)"
        status: pass
    human_judgment: true
    rationale: "No browser binary (Edge/Chrome/Chromium) is installed in this execution sandbox, so the plan's literal must-have ('opens in a browser') and the retargeted app/tests/tenure-public-title.browser.test.mjs could not be run. The curl-based SSR check above is the strongest available automated proxy — it drives the real rendered HTML, not a mock — but a human should do one real-browser pass before treating the visual result as confirmed."
  - id: D5
    description: "DS-01 (REQUIREMENTS.md) and the Phase 51 goal/success-criterion (ROADMAP.md) amended to describe the flat, no-redirect URL shape with the D-11 rationale recorded inline"
    requirement: "DS-01"
    verification:
      - kind: other
        ref: "grep -c 'redirects preserving existing URLs' .planning/REQUIREMENTS.md == 0; grep -c 'still resolves via redirects'/'redirects preserved' .planning/ROADMAP.md == 0; both files contain /arguments/term/{year}, /arguments/{slug}, and D-11; git diff --stat .planning/ROADMAP.md shows 12 changed lines, only Phase 51 touched"
        status: pass
    human_judgment: false
  - id: D6
    description: "Full suite green after this plan's changes, including two pre-existing tests this plan's own edits broke and fixed"
    verification:
      - kind: integration
        ref: "pytest api/tests tests pipeline/tests -q"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 02: Argument Slug Tracer Summary

**One real published oral argument reachable end to end at a flat, slug-based public URL — `Argument.slug` (migration 0031), `derive_argument_slug` with a corpus-verified collision discriminator, by-slug FastAPI routes sharing the existing published gate, and `/arguments`/`/arguments/{slug}` SvelteKit routes replacing the deleted `/cases` tree with no redirect layer.**

## Performance

- **Duration:** ~65 min
- **Tasks:** 4 (2 checkpoint decisions resolved from already-locked CONTEXT.md decisions, 1 tracer, 1 requirements amendment)
- **Files modified:** 23 (3 created, 17 modified, 3 deleted; 3 further files were renamed as part of the modified set)

## Accomplishments

- `Argument.slug` (String(200), nullable, unique) added via migration 0031, no backfill, round-trips upgrade/downgrade/upgrade cleanly on both the dev and `scotus_test` databases.
- `api.domain.argument_slug.derive_argument_slug`: bare slug for the common single-argument case; `question_number` as the primary suffix discriminator (chosen after querying the real ~7,800-row ConvoKit corpus — see Decisions); `term` is permanently unmintable (D-13); never returns an empty string.
- Both real `Argument(` write sites (`pipeline/commands/import_convokit.py`, `pipeline/commands/ingest.py`) stamp a slug at creation; `api/services/admin_arguments.py::update_argument` carries an explicit immutability guard comment and was already correct (it only ever re-derives `Case.slug`, never `Argument.slug`).
- `api/services/arguments.py::get_argument_by_slug` + two new routes (`GET /arguments/by-slug/{slug}/utterances`, `.../speakers`) reuse `get_argument_with_utterances`'s exact two-predicate published gate; both 422 on a malformed slug and 404 identically to the integer routes on an unknown or unpublished one.
- `/cases` route tree deleted (6 files; the two files with no `arguments/` peer — the multi-argument case picker and its 307 — removed outright, no replacement). `/arguments` (transitional flat listing) and `/arguments/{slug}` (transcript, D-09-preserved reading layer) live at `app/src/routes/arguments/`. `TopNav.svelte`'s nav link updated.
- `CaseItem.argument_slug` added and populated — the href target on the transitional listing.
- Live-proven end to end: `POST /admin/dev/reset-to-fixture` reseeded all 4 fixtures, every one got a real slug, zero published-with-null-slug rows, and a real vite dev server + uvicorn backend rendered `/arguments` and `/arguments/anderson-v-liberty-lobby-inc` correctly via curl.
- DS-01 (`REQUIREMENTS.md`) and the Phase 51 goal/success criterion (`ROADMAP.md`) amended to agree with the shipped URL shape, with the D-11 rationale recorded at both sites.
- Full suite: **1318 passed, 5 xfailed, 0 failed** — including fixing two pre-existing tests this plan's own edits broke (see Deviations).

## Task Commits

1. **Task 1/2: Operator decisions (stored-immutable slug D-12; flat no-redirect URL shape D-10/D-11)** — no commit; resolved from `51-CONTEXT.md`'s already-locked decisions (see Decisions Made).
2. **Task 3: End-to-end tracer** — `5d34366f5` (feat)
3. **Task 4: Amend DS-01 and ROADMAP** — `f7962d8c3` (docs)
4. **Fix: two pre-existing tests broken by Task 3's own edits** — `1f560bea8` (fix)

**Plan metadata:** commit pending (this SUMMARY + STATE.md + ROADMAP.md progress update)

## Files Created/Modified

- `alembic/versions/0031_argument_slug.py` — new migration: nullable `arguments.slug` + `uq_arguments_slug`, no backfill
- `api/domain/argument_slug.py` — `RESERVED_SLUG_WORDS`, `derive_argument_slug`
- `api/models/models.py` — `Argument.slug` column + immutability doc comment
- `api/routers/arguments.py` — two new by-slug routes, shared `_SLUG_PATH` validator
- `api/schemas/cases.py` — `CaseItem.argument_slug`
- `api/services/admin_arguments.py` — explicit immutability guard comment in `update_argument`
- `api/services/arguments.py` — `get_argument_by_slug`
- `api/services/cases.py` — `get_cases()` now returns `argument_slug`
- `api/tests/test_argument_slug.py` — new: pure-function + live-DB tests for slug generation and the by-slug routes
- `api/tests/test_published_gate.py` — fixed two tests this plan's edits broke (see Deviations)
- `app/src/lib/components/TopNav.svelte` — `/cases` link → `/arguments`
- `app/src/routes/arguments/+page.server.ts`, `+page.svelte` — moved from `cases/`, copy updated to "Arguments" / DS-01 empty-state copy, href now `/arguments/{argument_slug}`
- `app/src/routes/arguments/[slug]/+page.server.ts` — moved from `cases/[slug]/arguments/[id]/`, `params.id` → `params.slug`, hits the new by-slug endpoints
- `app/src/routes/arguments/[slug]/+page.svelte` — moved verbatim (no content changes needed)
- `app/tests/tenure-public-title.browser.test.mjs` — retargeted to `/arguments/{slug}` and the by-slug mock endpoints
- `pipeline/commands/import_convokit.py` — stamps `Argument.slug` at first-import creation; new `_taken_slugs_like` helper
- `pipeline/commands/ingest.py` — stamps `Argument.slug` at creation (deferred import to avoid a circular import)
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md` — DS-01 and Phase 51 amended per D-11

**Deleted:** `app/src/routes/cases/+page.server.ts`, `app/src/routes/cases/[slug]/+page.server.ts`, `app/src/routes/cases/[slug]/+page.svelte` (the multi-argument case picker and its 307 redirect — no replacement; D-10 makes it structurally unnecessary)

## Decisions Made

- **Checkpoints 1 & 2 resolved without re-prompting.** Both decisions (stored-immutable `Argument.slug`, D-12; flat no-redirect URL shape, D-10/D-11) are already recorded as locked, operator-confirmed decisions in `51-CONTEXT.md`'s "Implementation Decisions" section, complete with the operator's own verbatim rationale. CLAUDE.md's Defect Policy states a locked decision in a phase CONTEXT.md is Claude's to act on, not to re-ask — re-prompting for an already-settled one-way-door decision would itself be the workflow defect the policy exists to prevent.
- **`question_number` over `argued_date` as the slug-suffix discriminator**, decided against the real corpus rather than assumed: `data/corpus/cases.jsonl` has 952 of 7,748 cases with >1 transcript (the only population that ever needs a suffix, since two arguments sharing a case name share one base slug). Simulating the importer's own `_parse_argued_date` against those 952 found 434 (45.6%) where two transcripts resolve to the same date or to no date at all. `question_number` is a purely synthetic per-docket counter assigned by the importer itself — always populated, always unique-by-construction, never derived from parseable text. Recorded in full in `api/domain/argument_slug.py`'s module docstring.
- **Corrected read_first pointer:** the plan asked to grep `Argument(` across `api/` and `pipeline/` "at minimum the corpus importer... and the approve path in `api/services/admin_jobs.py`" — grep confirms `admin_jobs.py` never constructs an `Argument(` row (it only `UPDATE`s existing ones); the two real write sites are `import_convokit.py` and `ingest.py`, both covered.
- **Encoded-slash acceptance criterion corrected against verified framework behavior.** The plan predicted `GET /arguments/by-slug/..%2F..%2Fetc%2Fpasswd/utterances` returns 422; verified (via httpx's ASGITransport, which implements the same ASGI `scope["path"]` decoding contract a real uvicorn server does) that it returns 404 instead — Starlette decodes `%2F` to a literal `/` before routing, so the request has 5 path segments and never matches this route's 4-segment pattern, never reaching `Path` validation at all. The actual security property T-51-02-01 asks for (the payload never reaches the service/DB layer) still holds under 404; a same-segment payload (`%2e%2e`, decodes to `..`, no slash) correctly demonstrates the 422 path. No global middleware was added to force 422 on the encoded-slash case — that would touch every route in the app to satisfy one plan's specific status-code prediction, for no additional security benefit over the 404 already achieved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_speakers_router_404_detail_matches_utterances_router` broke after adding the by-slug routes**
- **Found during:** Task 3 (running the full suite after the tracer changes)
- **Issue:** This backend source-text test asserted the literal 404 detail string appears exactly twice in `api/routers/arguments.py` (D-01 byte-identical-404 contract). The two new by-slug routes correctly raise the same literal string twice each, bringing the true count to 6.
- **Fix:** Updated the assertion to 6 and the docstring to name all four routes.
- **Files modified:** `api/tests/test_published_gate.py`
- **Verification:** `pytest api/tests/test_published_gate.py -q` — 30 passed.
- **Committed in:** `1f560bea8`

**2. [Rule 1 - Bug] `test_page_server_loader_throws_on_non_ok_and_has_no_publish_branch` broke after moving `+page.server.ts`**
- **Found during:** Task 3 (same full-suite run)
- **Issue:** This was a static source-text contract test reading `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` — a file this plan moved and rewrote. `FileNotFoundError` on the old path.
- **Fix:** Deleted rather than path-updated, per CLAUDE.md's Testing Policy ("no static source-text contract tests for frontend behavior... tests retire with the behavior they pinned"). The behavior itself (`throw error(res.status, ...)` on non-OK, no publish-status branch) is preserved verbatim in the new loader and independently verified live via curl (see coverage D4).
- **Files modified:** `api/tests/test_published_gate.py`
- **Verification:** `pytest api/tests/test_published_gate.py -q` — 30 passed; full suite subsequently 1318 passed / 5 xfailed / 0 failed.
- **Committed in:** `1f560bea8`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — pre-existing tests broken by this plan's own correct edits; the code was right, the tests needed updating).
**Impact on plan:** No scope creep. Both fixes are exactly what the Defect Policy calls for: a failing test is a bug report, fixed in the phase it's found.

## Known Stubs

None. The transitional `/arguments` listing still fetching `/cases` (not yet the term-grouped endpoint) is a deliberate, plan-documented transitional state — not a stub — with a comment in `+page.server.ts` naming plan 51-08 as the replacement.

## Issues Encountered

- **No browser binary in the execution sandbox.** `node --test app/tests/tenure-public-title.browser.test.mjs` fails closed with "Microsoft Edge or Google Chrome must be installed" — the same environment limitation recorded repeatedly earlier in `STATE.md` (49-01/49-03/49-05, etc.). Compensated with a live curl-based SSR check against a real vite dev server + uvicorn backend (see coverage D4). Logged as an unrun-verify item; `gsd-tools windows append` itself errored on a pre-existing frontmatter/entry count mismatch in `.planning/WINDOWS.md` unrelated to this plan (best-effort per the tool's own contract — not fixed here, out of this plan's scope).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `/arguments` and `/arguments/{slug}` are live and correct; the term-grouped listing (D-14, plan 51-08) can build directly on `CaseItem.argument_slug` and the by-slug routes without further backend rework.
- `derive_argument_slug`'s reserved-word guard (D-13) is already in place for `/arguments/term/{year}` (plan 51-08) to rely on without its own reservation logic.
- The `.planning/WINDOWS.md` frontmatter/entry-count mismatch (pre-existing, not caused by this plan) blocks `gsd-tools windows append` — worth a look before it silently accumulates further drift.

---
*Phase: 51-design-system-noun-alignment*
*Completed: 2026-08-28*
