---
status: complete
phase: 51-design-system-noun-alignment
source: 51-01-SUMMARY.md, 51-02-SUMMARY.md, 51-03-SUMMARY.md, 51-04-SUMMARY.md, 51-05-SUMMARY.md, 51-06-SUMMARY.md, 51-07-SUMMARY.md, 51-08-SUMMARY.md, 51-09-SUMMARY.md, 51-10-SUMMARY.md
started: 2026-09-04T03:15:00Z
updated: 2026-09-04T13:46:57Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill the running uvicorn and vite processes. Clear ephemeral state. Start both from scratch. Alembic is at head (0031_argument_slug), the API boots without errors, and /arguments returns the October Term 1985 row with its published-argument count.
result: pass

### 2. Figma Primitives page — states read as states
expected: In the Figma file's Primitives page, the four frames (Button, Badge, Input, Card) read correctly as states: Input's focused ring and invalid error treatment are legible as focus and error, and Button's dense 36px variant reads as a denser row than the 44px primary rather than as a mistake.
result: pass
source: human
coverage_id: 51-01/D4

### 3. Figma arguments-transcript frame reads right
expected: The corrected arguments-transcript frame reads as the v1.0 chat layout: BENCH left, ADVOCATE right, 72% bubble max-width, square top-left corner, 3px left border, avatar and speaker label in the side colour — not the single-column coloured-rail version that was there first.
result: pass
source: human
coverage_id: 51-01/D11

### 4. Tailwind removal — base reset preserves rendering
expected: With Tailwind gone and app.css carrying an explicit base reset in preflight's place, the public listing, the transcript and the admin dashboard render with no layout shift, no collapsed margins and no unstyled-element flash.
result: pass
source: human
coverage_id: 51-03/D1

### 5. Admin dashboard stat cards after Card delegation
expected: On /admin, the stat cards render visually unchanged after StatCard was reworked to delegate to the Card primitive — same padding, border, radius and internal spacing as before the extraction.
result: pass
source: human
coverage_id: 51-06/D1

### 6. Pipeline docket entry field after Input adoption
expected: On /admin/pipeline, DocketPillInput's free-text field shows its placeholder, takes a visible focus ring, and renders invalid-state error text in color-destructive after the Input primitive was adopted.
result: pass
source: human
coverage_id: 51-06/D2

### 7. Transcript reading layer — scroll and visual weight
expected: Scrolling a full transcript, the outside-rail avatar sticks correctly over real distance; the frame matches Figma's arguments-transcript; and a Justice turn carries no more visual weight than an advocate turn.
result: pass
source: human
coverage_id: 51-07/D3

### 8. Public path end to end, apolitical sweep
expected: /arguments -> term -> argument -> speaker popover -> full scroll reads as intended at 375px and 1280px, and P-01..P-06 hold on every public screen — no derived statistic, no editorial prominence, no typographic asymmetry between bench and advocates.
result: pass
source: human
coverage_id: 51-10/D6

### 9. Eleven admin screens after the badge conversion
expected: All eleven admin screens behave as before the conversion, and the two deliberate visual changes — badge weight regular -> semibold, and the new tinted badge fills — are acceptable.
result: pass
source: human
coverage_id: 51-10/D7

### 10. Shipped surfaces vs the Figma file
expected: The shipped Public, Primitives and Admin surfaces match their Figma pages, or any drift is written down rather than merely noticed.
result: pass
source: human
coverage_id: 51-10/D8

### 11. Figma file structure — four pages
expected: Figma file exists in the operator's personal 'Jason Butler's team' with exactly four pages named Tokens, Primitives, Public, Admin
result: pass
source: automated
coverage_id: 51-01/D1

### 12. Figma Variables in two collections, semantic aliases primitive
expected: Colour, spacing and type held as Figma Variables (not Styles) in two collections; the semantic collection aliases the primitive collection and holds no literal hex of its own
result: pass
source: automated
coverage_id: 51-01/D2

### 13. Semantic variable names match 51-UI-SPEC.md exactly
expected: Every semantic variable name has a character-for-character counterpart in 51-UI-SPEC.md: 16 colour roles, 7 spacing steps, 5 type sizes, 5 line heights, 2 weights, 2 touch targets
result: pass
source: automated
coverage_id: 51-01/D3

### 14. Public page frames present, both variants render 100+ rows
expected: Public page contains frames arguments-term-index, arguments-term-detail-variant-A, arguments-term-detail-variant-B, arguments-transcript; both variants render at least 100 rows
result: pass
source: automated
coverage_id: 51-01/D5

### 15. Variant-B has a row with no advocate line and no reserved space
expected: The variant-B artifact contains at least one row rendered with no advocate line and no reserved empty space where it would be
result: pass
source: automated
coverage_id: 51-01/D6

### 16. Focal-point annotations on all four Public frames
expected: Each of the four Public frames carries a focal-point annotation naming a primary element, a secondary element, and at least one deliberately-quiet element, matching the UI-SPEC Focal points table
result: pass
source: automated
coverage_id: 51-01/D7

### 17. No derived statistic in any frame
expected: No frame shows a derived per-speaker or per-argument statistic — no count, ranking, sentiment, or most/busiest/notable framing
result: pass
source: automated
coverage_id: 51-01/D8

### 18. Figma: identical type size and weight for Justice and advocate turns
expected: In arguments-transcript, a Justice turn and an advocate turn use identical type size and identical font weight for utterance body text
result: pass
source: automated
coverage_id: 51-01/D9

### 19. 51-DESIGN-DECISIONS.md records the four decisions
expected: 51-DESIGN-DECISIONS.md records the Figma URL and team, the icon-library choice with its informing count, the Button loading-variant answer, and the term-row variant with the deferral clause
result: pass
source: automated
coverage_id: 51-01/D10

### 20. Argument.slug column and migration 0031 round-trip
expected: Argument.slug column + uq_arguments_slug unique constraint, migration 0031, round-trips upgrade/downgrade/upgrade
result: pass
source: automated
coverage_id: 51-02/D1

### 21. derive_argument_slug guards and collision disambiguation
expected: api.domain.argument_slug.derive_argument_slug: reserved-word guard, never-empty guard, collision disambiguation via question_number/argued_date/counter fallback
result: pass
source: automated
coverage_id: 51-02/D2

### 22. By-slug endpoints under the published gate
expected: GET /arguments/by-slug/{slug}/utterances and /speakers resolve under the same published gate as the integer routes; unknown/unpublished slugs 404; path validation rejects malformed slugs
result: pass
source: automated
coverage_id: 51-02/D3

### 23. DS-01 and ROADMAP amended for the flat URL shape
expected: DS-01 (REQUIREMENTS.md) and the Phase 51 goal/success-criterion (ROADMAP.md) amended to describe the flat, no-redirect URL shape with the D-11 rationale recorded inline
result: pass
source: automated
coverage_id: 51-02/D5

### 24. Full suite green after 51-02
expected: Full suite green after this plan's changes, including two pre-existing tests this plan's own edits broke and fixed
result: pass
source: automated
coverage_id: 51-02/D6

### 25. Two-layer token set in app.css, zero hex in semantic layer
expected: Complete two-layer token set (14 primitives + 37 semantic names) authored in app/src/app.css, matching the Figma semantic collection character for character, with zero raw hex in any semantic declaration
result: pass
source: automated
coverage_id: 51-03/D2

### 26. 51-TOKEN-MAP.md covers every distinct literal
expected: 51-TOKEN-MAP.md publishes a deterministic conversion table covering every distinct hex, font-size, font-weight, and spacing literal currently in app/src/**/*.svelte, plus explicit out-of-scope declarations
result: pass
source: automated
coverage_id: 51-03/D3

### 27. DESIGN-SYSTEM.md rewritten for the Phase 51 token system
expected: .planning/codebase/DESIGN-SYSTEM.md rewritten to document the Phase 51 token system result, no longer asserting the stale 3-size/2-weight type scale or an unverified no-Tailwind claim
result: pass
source: automated
coverage_id: 51-03/D4

### 28. GET /arguments/terms shape, ordering and published gate
expected: GET /arguments/terms returns one row per October Term with at least one published argument, term_year + argument_count, ordered term_year descending, counting only published-gated arguments through the is_lead join with no double-count from consolidated dockets
result: pass
source: automated
coverage_id: 51-04/D1

### 29. GET /arguments/term/{term_year} shape and status codes
expected: GET /arguments/term/{term_year} lists a term's published arguments in D-16 Variant A's minimal shape, 200/empty for a real empty term, 422 for a bad year, stable ordering for a shared argued_date
result: pass
source: automated
coverage_id: 51-04/D2

### 30. Structural leak-ban extended and proven non-vacuous
expected: Structural leak-ban extended to api/schemas/arguments.py, proven non-vacuous by a temporary trust_tier field that made it fail; published-gate contract extended to both new service functions; three live decoded-JSON leak assertions cover every new public payload and are proven both to run and to be non-vacuous
result: pass
source: automated
coverage_id: 51-04/D3

### 31. Components split into lib/public and lib/admin
expected: The 14 components split into lib/public/ (5) and lib/admin/ (9), with lib/components/ slimmed to TopNav.svelte, and every import site updated to match
result: pass
source: automated
coverage_id: 51-05/D1

### 32. The relocation is behaviour-neutral
expected: Every changed line across the two move commits is an import path, git history follows every rename, and the full backend suite plus the frontend build stay green
result: pass
source: automated
coverage_id: 51-05/D2

### 33. Icon dependency installed under the package-legitimacy gate
expected: @lucide/svelte substituted for the deprecated lucide-svelte D-18 named, operator-approved, install diff adds exactly one dependency
result: pass
source: automated
coverage_id: 51-06/D3

### 34. 51-DESIGN-DECISIONS.md appended, never rewritten
expected: 51-DESIGN-DECISIONS.md gains the D-18 substitution amendment and the bits-ui-vs-hand-rolled report, appended; all four pre-existing decisions confirmed still present before every commit
result: pass
source: automated
coverage_id: 51-06/D4

### 35. Speaker types and side colour have one declaration site each
expected: Speaker types and side colour each have exactly one declaration/computation site (IN-02/IN-03 closed)
result: pass
source: automated
coverage_id: 51-07/D1

### 36. lib/public and the transcript route are token-only
expected: lib/public/ (5 components) and the transcript route contain zero raw hex, zero numeric font-size, zero -webkit-line-clamp/ellipsis, zero font-weight:500, zero svelte/store imports
result: pass
source: automated
coverage_id: 51-07/D2

### 37. Transcript route: no data capture, no derived statistic, no truncation
expected: Transcript route has no top-level `data` capture, no derived per-speaker statistic, and no truncation
result: pass
source: automated
coverage_id: 51-07/D4

### 38. /cases API surface deleted, guarantees re-asserted
expected: The /cases API surface (router, service, schema) is deleted, GET /cases 404s, and every guarantee its tests carried is asserted against its replacement rather than dropped
result: pass
source: automated
coverage_id: 51-08/D4

### 39. Every admin badge renders through the shared primitive
expected: Every admin badge renders through lib/primitives/Badge.svelte; no per-file badge style builder survives
result: pass
source: automated
coverage_id: 51-10/D2

### 40. admin/help styled like every other screen, no rendered change
expected: admin/help styles the way every other screen does, with no rendered change
result: pass
source: automated
coverage_id: 51-10/D3

### 41. DESIGN-SYSTEM.md matches app.css bidirectionally
expected: DESIGN-SYSTEM.md describes the token set app/src/app.css actually declares, in both directions
result: pass
source: automated
coverage_id: 51-10/D4

### 42. The real-browser suite runs and is green
expected: `node --test --test-concurrency=1 app/tests/*.browser.test.mjs` runs and passes
result: pass
source: automated
coverage_id: 51-10/D9
note: Re-run in this UAT session — 10 tests, 10 pass, 0 fail.

### 43. Public routes resolve end to end; /cases gone with no redirect
expected: /arguments (listing) and /arguments/{slug} (transcript) resolve end to end via real SvelteKit SSR against a live FastAPI backend; /cases route tree is gone; no redirect route exists
result: pass
source: automated
coverage_id: 51-02/D4
note: Re-verified in this session against a real browser — /arguments 200, /arguments/{slug} 200, /cases 404 on both the app (5173) and the API (8000); tenure-public-title.browser.test.mjs green.

### 44. Public transcript renders unchanged after the component move
expected: The public transcript page renders unchanged after the lib/public split (real-browser visual check)
result: pass
source: automated
coverage_id: 51-05/D3
note: Re-verified in this session — transcript renders correctly at 1280px and 375px in a real browser. The admin-dashboard half of this deliverable is carried by test 5 and test 9 (admin login required).

### 45. /arguments term index renders rows, count, empty and error states
expected: /arguments term index renders one row per term with published-argument count, empty state, and error state per the Copywriting Contract
result: pass
source: automated
coverage_id: 51-08/D1
note: Re-verified in this session — arguments-listing.browser.test.mjs cases 1, 2, 5, 6 green; real-browser screenshot at 1280px shows the term row with the plural count form.

### 46. /arguments/term/{year} lists rows, distinguishes empty from bad year
expected: /arguments/term/{year} term detail lists a term's published arguments in D-16 Variant A's row shape, distinguishes a real-but-empty term (200) from a bad year (404), and links each row to /arguments/{slug}
result: pass
source: automated
coverage_id: 51-08/D2
note: Re-verified in this session — browser cases 3, 4, 5, 6 green; real-browser screenshot shows both rows in Variant A's shape with working slug hrefs.

### 47. arguments-listing.browser.test.mjs runs green
expected: app/tests/arguments-listing.browser.test.mjs — first real-browser coverage of the public listing, six test cases
result: pass
source: automated
coverage_id: 51-08/D3
note: Genuinely unrun at 51-08 time (no browser binary). Run in this session — 7 cases, all green (the seventh is the P-06 test 51-10 added).

### 48. Codemod is committed and idempotent
expected: A committed, idempotent codemod converts literal style values to token references per 51-TOKEN-MAP.md
result: pass
source: automated
coverage_id: 51-09/D1
note: Re-verified in this session — 26/26 unit tests pass; a report-mode run over app/src reports "files changed: 0".

### 49. No mapped hex, numeric font-size or font-weight remains
expected: No mapped hex, numeric font-size, or numeric font-weight remains in any .svelte file under app/src
result: pass
source: automated
coverage_id: 51-09/D2
note: Re-verified in this session — 6-digit hex 0, 3-digit hex 0, `font-size: <digit>` 0, `font-weight: 400|500|600` 0.

### 50. The D-08 artifact report lists every surviving artifact
expected: The D-08 artifact report lists every surviving visual/UX artifact for operator judgment
result: pass
source: automated
coverage_id: 51-09/D3
note: Superseded and closed by 51-10 D1 — all 23 rows (A-01..A-10, B-01..B-08, C-01, D-01..D-04) carry a ruling; no empty ruling cells.

### 51. Spacing scale gains a 12px step with no rendered change
expected: The spacing scale gains a 12px step with every reference remapped and no rendered change
result: pass
source: automated
coverage_id: 51-09/D4
note: Landed in `present` only because 51-09's coverage block omits `status:` and `human_judgment:`. The recorded evidence is automated on both sides (409 resolved-px buckets unchanged; Playwright re-measure at 390x844 identical).

### 52. Every artifact row ruled and every fix-now ruling applied
expected: Every row in 51-ADMIN-ARTIFACTS.md carries an operator ruling, and every fix-now ruling is applied
result: pass
source: automated
coverage_id: 51-10/D1
note: Re-verified in this session — 23 ids defined, 23 ruled, zero empty ruling cells.

### 53. Long text on the public listing is not truncated
expected: Long text on the public listing is not truncated, clipped or ellipsised, and the docket stays visible (P-06)
result: pass
source: automated
coverage_id: 51-10/D5
note: Re-verified in this session — browser test 7 green at 375px; 1280px screenshot shows the 164-character NLRB case name wrapping intact across three lines with "No. 84-1493" fully visible.

## Summary

total: 53
passed: 53
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
