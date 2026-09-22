---
phase: 51-design-system-noun-alignment
reviewed: 2026-09-22T00:00:00Z
depth: standard
files_reviewed: 78
files_reviewed_list:
  - app/src/app.css
  - app/src/lib/primitives/Badge.svelte
  - app/src/lib/primitives/Button.svelte
  - app/src/lib/primitives/Card.svelte
  - app/src/lib/primitives/Input.svelte
  - app/src/lib/primitives/badge-tone.ts
  - app/src/lib/admin/AdminSubNav.svelte
  - app/src/lib/admin/ArgumentDetailsCard.svelte
  - app/src/lib/admin/CopyableExtractedValue.svelte
  - app/src/lib/admin/CreatePersonPopover.svelte
  - app/src/lib/admin/DocketPillInput.svelte
  - app/src/lib/admin/FailedStepGuidance.svelte
  - app/src/lib/admin/ResolveCard.svelte
  - app/src/lib/admin/RunStatusCard.svelte
  - app/src/lib/admin/StatCard.svelte
  - app/src/lib/components/TopNav.svelte
  - app/src/lib/public/ChatBubble.svelte
  - app/src/lib/public/MobileNavBar.svelte
  - app/src/lib/public/SectionRail.svelte
  - app/src/lib/public/SpeakerPopover.svelte
  - app/src/lib/public/StageDirection.svelte
  - app/src/lib/public/TermRow.svelte
  - app/src/lib/public/VariantSwitcher.svelte
  - app/src/lib/formatting.ts
  - app/src/lib/server/session.ts
  - app/src/lib/types/speaker.ts
  - app/src/lib/README.md
  - app/src/routes/admin/+layout.svelte
  - app/src/routes/admin/+page.svelte
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/help/+page.svelte
  - app/src/routes/admin/login/+page.svelte
  - app/src/routes/admin/people/+page.svelte
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/admin/people/new/+page.svelte
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - app/src/routes/admin/review/+page.svelte
  - app/src/routes/arguments/+error.svelte
  - app/src/routes/arguments/+page.server.ts
  - app/src/routes/arguments/+page.svelte
  - app/src/routes/arguments/[slug]/+page.server.ts
  - app/src/routes/arguments/[slug]/+page.svelte
  - app/src/routes/arguments/term/[year]/+page.server.ts
  - app/src/routes/arguments/term/[year]/+page.svelte
  - app/src/routes/attributions/+page.svelte
  - app/scripts/tokenize-styles.mjs
  - app/scripts/tokenize-styles.test.mjs
  - app/package.json
  - app/tests/arguments-listing.browser.test.mjs
  - app/tests/case-required-recovery.browser.test.mjs
  - app/tests/copyable-extracted-value.browser.test.mjs
  - app/tests/tenure-public-title.browser.test.mjs
  - app/tests/fixtures/copyable-extracted-value-main.ts
  - app/tests/helpers/browser-executable.mjs
  - app/tests/helpers/paths.mjs
  - alembic/versions/0031_argument_slug.py
  - api/domain/argument_slug.py
  - api/main.py
  - api/models/models.py
  - api/routers/admin.py
  - api/routers/arguments.py
  - api/schemas/admin_arguments.py
  - api/schemas/arguments.py
  - api/services/admin_arguments.py
  - api/services/arguments.py
  - api/tests/test_argument_list_item_argued_date_optional.py
  - api/tests/test_argument_slug.py
  - api/tests/test_arguments.py
  - api/tests/test_public_arguments_listing.py
  - api/tests/test_published_gate.py
  - api/tests/test_question_number_nullable.py
  - api/tests/test_trust_public_leak_ban.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/ingest.py
  - tests/test_admin_dev_router_gate.py
  - tests/test_admin_router.py
findings:
  critical: 1
  warning: 1
  info: 1
  total: 3
status: issues_found
---

# Phase 51: Code Review Report

**Reviewed:** 2026-09-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 78
**Status:** issues_found

## Summary

Reviewed the full Phase 51 file set: the new design-token primitive layer
(`Badge`/`Button`/`Card`/`Input`), the admin-component relocation
(`lib/components/*` → `lib/admin/*` / `lib/public/*`), the new term-grouped
public arguments IA (`/arguments`, `/arguments/term/[year]`,
`/arguments/[slug]`), the new `Argument.slug` domain/migration/import work
(`api/domain/argument_slug.py`, migration `0031`, `pipeline/commands/
ingest.py`, `pipeline/commands/import_convokit.py`), and the session/auth
surface (`app/src/lib/server/session.ts`, `hooks.server.ts`,
`api/routers/admin.py`).

The design-token sweep is clean and complete for the scope this phase
covers — no raw hex, numeric `font-size`, or numeric `font-weight` literal
remains in any `.svelte` file outside `app.css`'s own token definitions and
the two already-filed 500-weight sight-check sites in `ResolveCard.svelte`.
The session/HMAC cookie code (`session.ts`, `hooks.server.ts`, admin
`login/+page.server.ts`) is sound: length-gated `timingSafeEqual`,
fail-closed `verifySession`, single auth checkpoint in `hooks.server.ts`
covering both pages and `+server.ts` endpoints. The published-gate on the
new `by-slug` argument routes correctly reuses the same two-predicate
(`published_at IS NOT NULL` AND `status == PUBLISHED`) guard the existing
integer-id routes use — verified in both `api/services/arguments.py` and
its test coverage. Slug collision handling in `api/domain/argument_slug.py`
is well-reasoned and its `taken`-set prefix query is safe against SQL LIKE
metacharacters (the input alphabet is already restricted to
`[a-z0-9-]`).

One genuine Svelte 5 reactivity defect was found — the same "prop captured
once at mount, then reused across a changing prop" class this project has
been bitten by twice before and explicitly documented against
(`ChatBubble.svelte`'s own comments in this same diff) — reproduced here in
`SpeakerPopover.svelte`, one file away from where the defect class is
explained. One data-correctness gap was found in the new public term
listing: it does not filter out `Argument` rows whose new `slug` column is
still `NULL`, which the migration deliberately allows and which the test
suite's own fixture defaults to, producing a rendered but permanently
dead link.

## Critical Issues

### CR-01: `SpeakerPopover.svelte` freezes `isBench` across a live prop change, misclassifying a re-selected speaker

**File:** `app/src/lib/public/SpeakerPopover.svelte:40`
**Issue:**

```svelte
let { speaker, paletteVars = '' } = $props<{...}>();
const isBench = speaker.is_bench;
```

`isBench` is captured with a plain `const` off the `speaker` prop instead of
`$derived(speaker.is_bench)`. This is exactly the defect class
`ChatBubble.svelte` (added in this same diff, a few files away) documents at
length and deliberately avoids: "Every value below is `$derived`, NOT
`const`. A plain `const` off a prop is captured once at component init and
then frozen." `SpeakerPopover` is instantiated once at the page level in
`app/src/routes/arguments/[slug]/+page.svelte:256-261`:

```svelte
{#if currentSpeaker}
  <SpeakerPopover speaker={currentSpeaker} paletteVars={...} />
{/if}
```

`currentSpeaker` is reassigned directly by `onAvatarClick` (line 26-31) on
every avatar click — it is never set to `null` and back within the same
click before this component is asked to re-render. When a user opens the
popover for one speaker (say, a Justice) and then, without closing it,
clicks a different avatar (say, an Advocate) while the popover stays open,
`currentSpeaker` changes value but the `{#if currentSpeaker}` block's
truthiness never toggles false→true in between (both writes to
`currentSpeaker` settle before Svelte's reactive flush runs), so Svelte
never destroys and remounts `SpeakerPopover` — it just updates its
`speaker` prop in place. `isBench`, captured once at the component's first
mount, keeps the *original* speaker's bench/advocate classification
forever (or until the popover is closed long enough to actually unmount).

Concretely: the birth/death line (`{#if isBench && ...}`, line 140), the
advocate-only "Coming soon" descriptor line (`{#if !isBench}`, line 146),
and the tenure list (`{#if isBench && speaker.tenure.length > 0}`, line
166) all read the frozen value — so an Advocate selected after a Justice
renders the Justice's tenure history and omits the "Coming soon" line, and
vice versa. This is not merely cosmetic: it misattributes bench/advocate
identity data to the wrong person, which is exactly the class of error the
project's apolitical-identity-accuracy bar treats as a hard defect
(`speaker.is_bench` is otherwise computed correctly and freshly per-speaker
by `+page.server.ts:41`; only this component's captured copy goes stale).

**Fix:**
```svelte
let { speaker, paletteVars = '' } = $props<{...}>();
const isBench = $derived(speaker.is_bench);
```
(Everything downstream — the three `{#if isBench ...}` blocks — already
reads the reactive binding correctly once it is one.)

## Warnings

### WR-01: Public term listing links to `/arguments/{slug}` for arguments whose `slug` is `NULL`

**File:** `api/services/arguments.py:78-115` (`list_terms`, `list_arguments_for_term`), `app/src/lib/public/TermRow.svelte:19-29` (`slug: string`, non-optional), `app/src/routes/arguments/+page.svelte` / `app/src/routes/arguments/term/[year]/+page.svelte` (consumers)
**Issue:**

Migration `0031_argument_slug.py` deliberately adds `Argument.slug` as
`nullable=True` with **no backfill** ("reseed, do not migrate" —
CLAUDE.md), leaving every pre-existing row's `slug` `NULL` until the next
full reseed. `list_terms` and `list_arguments_for_term`
(`api/services/arguments.py:61-70`, `93-115`) filter only on
`CaseArgument.is_lead`, `Case.term_year`, `Argument.published_at IS NOT
NULL`, and `Argument.status == PUBLISHED` — there is no
`Argument.slug.isnot(None)` predicate. `ArgumentListItem.slug` is
correctly typed `str | None` in `api/schemas/arguments.py:46`, and this is
not a hypothetical edge case: the review suite's own fixture,
`_SeededFixture.add_argument` in `api/tests/test_public_arguments_listing.py:73-116`,
defaults `slug=None`, and none of that file's `list_terms`/
`list_arguments_for_term` tests assert `slug` is populated — the default
seeded state for nearly every test in that file is exactly the NULL-slug
state this finding is about.

On the frontend, `TermRow.svelte:19-25` declares `slug: string` as a
*required, non-optional* prop, and the term-detail page passes
`arg.slug` straight through (`app/src/routes/arguments/term/[year]/+page.svelte:78`)
into `href="/arguments/{slug}"` (`TermRow.svelte:29`). A `null` slug
interpolates to an empty string in Svelte's attribute binding, so the
rendered row links to `/arguments/` (or a similarly malformed path)
instead of a working argument page — and even a manually-corrected request
to `GET /arguments/by-slug/null/utterances` cannot succeed, because
`get_argument_by_slug` (`api/services/arguments.py:118-140`) does an exact
string match against `Argument.slug`, which is a genuine SQL `NULL`, not
the string `"null"`. The row is visible on a real, published term listing
but permanently unreachable until the underlying argument is reseeded with
a slug.

**Fix:** Either (a) add `.where(Argument.slug.isnot(None))` to both
`list_terms` and `list_arguments_for_term`'s queries so a slugless argument
never appears in the public listing until it has one, or (b) have the
frontend render the row without a link (or omit the row) when `slug` is
falsy, and loosen `TermRowProps.slug` to `string | null`. (a) is preferable
since it also keeps `list_terms`'s per-term count consistent with what a
reader can actually click through to.

## Info

### IN-01: `api/routers/admin.py` module docstring describes an auth swap that never happened

**File:** `api/routers/admin.py:26-29`, `106-120`
**Issue:** The module docstring states "All routes are protected via the
router-level `verify_admin_token` dependency... Phase 6 replaces
`verify_admin_token` with HMAC session-cookie auth in a single location,"
and `verify_admin_token`'s own docstring repeats "Throwaway token check —
Phase 6 replaces this with HMAC session cookie auth." The code still uses
the static `X-Admin-Token` header compared via `hmac.compare_digest`
against `settings.admin_token` — this was never replaced. In practice this
is fine as a defense-in-depth layer: the browser-facing auth boundary is
now `app/src/lib/server/session.ts`'s HMAC session cookie, enforced by
`hooks.server.ts`, and the SvelteKit server presumably forwards a static
token to FastAPI server-to-server. But the comment reads as though the
static-token check is legacy/dead code slated for removal, which it is
not — a future reader (or reviewer) could reasonably delete or "clean up"
`verify_admin_token` believing Phase 6 already superseded it.
**Fix:** Update the docstring to state the two-layer model explicitly (HMAC
session cookie at the SvelteKit boundary, static bearer token at the
FastAPI boundary) rather than describing the static-token check as
scheduled for replacement.

---

_Reviewed: 2026-09-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
