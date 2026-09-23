# Launch Readiness — surface gaps and decisions

**Status:** inventory taken 2026-09-23 against the live codebase. Decisions marked as such;
everything else is a fact or an open scoping item. Not a plan.

## Decisions taken 2026-09-23

- **Remove the Admin link from the public nav.** `app/src/lib/components/TopNav.svelte`
  currently renders an unconditional `/admin` link to every visitor. Auth gates the page, so
  this is not a security hole — but nothing reader-facing should advertise an operator surface.
  `/admin` will be reached by typing it.

## Verified gaps in the public surface

Each confirmed against the code, not inferred.

| | Finding |
|---|---|
| **No root route** | `app/src/routes/` has `+layout.svelte` and **no `+page.svelte`**. Visiting `/` renders the nav bar and a 404. |
| **No page metadata anywhere** | Zero `<svelte:head>`, `<title>`, meta description or Open Graph tags on any public page. No social preview, nothing for search engines. |
| **`app/static/` is empty** | `app.html` links `%sveltekit.assets%/favicon.png`, which does not exist — every page load 404s on it. |
| **One error page** | `+error.svelte` exists only under `/arguments`. Any other bad URL gets SvelteKit's default. |
| **No robots.txt, no sitemap** | Neither file exists. |
| **No search of any kind** | No endpoint, no service function, no route. See the positioning note — the homepage brief is "search-forward" and assumes a capability that has never been built. |
| **No deploy configuration** | `adapter-node` in `svelte.config.js` and nothing else. No Dockerfile, no DigitalOcean app spec. DEPLOY-01/03 are unstarted, not merely carried. |

## Content readiness

- **7,811 of 7,817 arguments publishable** under the 2026-09-23 trust decisions; 6 held back
  for being more than 50% undetermined. See `transcript-rendering-decision-tree.md`.
- **Corpus covers 1955-2019** — 65 terms, most recent OT 2019. Reaching current terms means the
  deferred PDF route (Phase 999.11).
- **No bulk publish path exists.** `publish_argument(db, argument_id)` is one argument at a
  time. Publishing thousands of arguments has no tooling behind it — this is unbuilt work that
  the trust decisions do not by themselves solve.
- **Nothing has ever been rendered at realistic volume.** Every surface has been verified
  against the four fixtures. A 1955 term holds ~108 arguments; `/arguments/term/1955` has never
  been rendered with real content, in either layout or query performance.

## Carried verification debt that matters more at launch than it did internally

- **Phase 04 accessibility is asserted, not measured.** No assistive-technology walkthrough and
  no axe-core/WAVE scan has ever run against the argument view. Waived by the operator
  2026-08-18 via `04-VERIFICATION.md`'s `overrides` block. Phases 14, 38, 39, 45 **and 51** have
  all changed that UI since, so the drift is worse than when the waiver was granted. The cheap
  permanent fix is an axe-core assertion inside a browser test.
- **Three UAT behaviours implemented but never observed:** the failed-run error panel
  (`FailedStepGuidance.svelte`), the unresolved-advocate role placeholder and per-row Save gate,
  and the non-interactive avatar for an unresolved utterance.
- **Phase 49's live-browser checks** are consolidated in `49-EVIDENCE.md` §9 and still unrun.
  They were blocked on sandbox `.env` access at the time; browser tooling works now.

## Open scoping items — for `/gsd-new-milestone`, not for a decision here

1. **Does search ship at launch?** It is net-new and the homepage brief leans on it.
2. **Deployment.** Env vars (`BODY_SIZE_LIMIT`, `ORIGIN`, `PROTOCOL_HEADER`, `HOST_HEADER`) and
   the `admin.scotuschat.com` DNS entry have been on the blocker list since v1.4 and have never
   been exercised once.
3. **The landing page**, against `.planning/positioning/HOMEPAGE-BRIEF.md`. The operator's
   position 2026-09-23: the Figma exploration is a starting point with no conclusions, not a
   shortlist.
4. **How the 1955-2019 range is framed** to a reader. Parked by the operator, to be settled when
   the homepage is actually designed.
5. **Bulk publish tooling.**
6. **An About page** — the positioning docs assume one; none exists.
