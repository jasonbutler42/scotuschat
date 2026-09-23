# Architecture Research — v1.9 Integration

**Domain:** Read-only legal-transcript publishing site (SvelteKit + FastAPI + Postgres), adding search, a public landing surface, sitemap/robots, client-side analytics, and bulk-publish tooling to a mature, phase-gated codebase.
**Researched:** 2026-09-23
**Confidence:** HIGH — every recommendation below is anchored to a file read during this research, not inferred from framework defaults.

This is not a greenfield architecture document. It is an integration map: where each
v1.9 capability attaches to the actual routers, services, models, and SvelteKit routes
that exist today, verified by reading them.

---

## 0. What the codebase actually looks like today (verified)

| Fact | Evidence |
|---|---|
| FastAPI has exactly 5 routers: `arguments`, `people`, `admin`, `admin_dev`, `admin_review` | `api/main.py:17-33` |
| Public (non-admin) routers are only `arguments.py` + `people.py` | `api/main.py:30-31`, confirmed as the exact set `test_trust_public_leak_ban.py` treats as "public" (`PUBLIC_ROUTER_MODULE_NAMES`) |
| Public routes today: `/arguments/{id}/utterances`, `/arguments/{id}/speakers`, `/arguments/by-slug/{slug}/utterances`, `/arguments/by-slug/{slug}/speakers`, `/arguments/terms`, `/arguments/term/{year}` | `api/routers/arguments.py:53-171` |
| Every public query gates on **both** `published_at IS NOT NULL` **and** `status == PUBLISHED` — never one predicate alone (a prior defect, D-2 in Phase 48, means `published_at` alone is not a safe gate since `unpublish_argument` retains it) | `api/services/arguments.py:66-67, 106-107, 148-149, 181-186` |
| `Argument.slug` is nullable with no backfill (reseed-not-migrate); every published-listing query additionally filters `Argument.slug.isnot(None)` so a slugless row can never be counted or linked | `api/services/arguments.py:73-74, 111` |
| `Argument.oyez_transcript_id` (ConvoKit `conversation_id`) already exists on the model and is **already exposed** on `ArgumentMetadataResponse.oyez_transcript_id` — it reaches the public API response today and is not on the leak-ban's `BANNED_KEYS` list | `api/models/models.py:371`, `api/schemas/utterance.py:53`, `api/tests/test_trust_public_leak_ban.py:84-95` |
| No full-text search infrastructure exists (no `tsvector`, no `pg_trgm`, no GIN index) in any of the 31 Alembic migrations at `alembic/versions/` | grep across `alembic/versions/` returned nothing |
| SvelteKit routes: `app/src/routes/` has `+layout.svelte` and no `+page.svelte` (root 404s), `/arguments`, `/arguments/term/[year]`, `/arguments/[slug]`, `/attributions`; `/admin/*` tree is auth-gated | `find app/src/routes` |
| Every SvelteKit→FastAPI call goes through a `+page.server.ts` `load()` using `$env/static/private` → `FASTAPI_BASE_URL`, never `PUBLIC_` | `app/src/routes/arguments/+page.server.ts:1,13` (representative; enforced by a test per CLAUDE.md) |
| `app/src/hooks.server.ts` is the sole auth checkpoint, gating only `/admin*` paths; every other path passes through untouched | `app/src/hooks.server.ts:16-33` |
| `app/static/` is empty; `app.html` links a favicon that 404s; no `<svelte:head>` anywhere; no robots.txt, no sitemap | `.planning/notes/launch-readiness.md` (verified facts, not inference) |
| Frontend has exactly 2 runtime dependencies: `@lucide/svelte`, `bits-ui` — no analytics SDK, no state-management library beyond Svelte 5 runes | `app/package.json` |
| `publish_argument(db, argument_id, override_reason=None)` is a single-row async service function with two non-overridable gates (`resolved_at IS NULL`, already-`PUBLISHED`) and one overridable trust gate (`UNCERTAIN` tier requires a non-blank reason); it commits and writes one `ArgumentStatusLog` row per call | `api/services/admin_arguments.py:751-859` |
| The pipeline CLI (`python -m pipeline <command>`) already has two "scan every argument, one session per row, `--dry-run`, report scanned/unchanged/changed" commands — `recompute-trust` and `prune-runs` — registered in `pipeline/__main__.py` as the standing pattern for any new bulk operator tool | `pipeline/commands/recompute_trust.py`, `pipeline/__main__.py:349-429` |
| `TopNav.svelte` is the single shared nav component (`variant='public'`), currently hard-codes Arguments / Attributions / Admin links | `app/src/lib/components/TopNav.svelte` |
| `app/src/lib/public/` already holds the pattern for small public-facing components (`TermRow.svelte` etc.) — the natural home for new search/landing/about components | directory listing |
| The structural leak-ban test (`test_trust_public_leak_ban.py`) derives its "public surface" from an explicit, hand-maintained list of router modules and frontend route files — it does **not** discover new routes automatically; a new router or route must be added to its lists or it silently doesn't get checked | `PUBLIC_ROUTER_MODULE_NAMES`, `PUBLIC_SCHEMA_MODULE_PATHS`, `PUBLIC_FRONTEND_PATHS` in the test file |

That last point is a real, concrete pitfall for every item below: **any new public router, schema module, or frontend route added in v1.9 must be added to those three lists in the same phase that adds the route**, or the structural ban stops covering the new surface.

---

## 1. Search

### Where the endpoints belong

FastAPI stays read-only and the query logic is pure Postgres reads — this is squarely
inside the existing `arguments` router's remit, not a new service boundary. Concretely:

- **New router file is not needed.** Add a `GET /arguments/search` endpoint to the
  existing `api/routers/arguments.py` (alongside `/terms`, `/term/{year}`), backed by a
  new function in `api/services/arguments.py` (e.g. `search_arguments(db, q, page,
  page_size)`). This keeps one router module to add to the leak-ban's
  `PUBLIC_ROUTER_MODULE_NAMES` (already present) and one schema file to extend
  (`api/schemas/arguments.py`, already on `PUBLIC_SCHEMA_MODULE_PATHS`) rather than
  introducing new ones to track.
- A speaker-name search needs a join across `Argument` → `CaseArgument` (is_lead) →
  `Case`, plus `ArgumentParticipant` → `Person` for the speaker dimension. This is a new
  query shape (`list_terms`/`list_arguments_for_term` don't join to people at all — D-16
  deliberately deferred that join), so it is new code, not a reuse of an existing
  function.
- **Every search query must carry the exact same two-predicate published gate** every
  other public query in `arguments.py` uses (`published_at IS NOT NULL` AND `status ==
  PUBLISHED`, plus the `slug IS NOT NULL` fail-closed guard). Do not write a third,
  slightly different gate — copy the established one verbatim. This is not a place for
  a design decision; it's a locked constraint per `test_published_gate.py`'s
  exact-substring assertions and CLAUDE.md's published-gate discipline.
- Response shape: reuse `ArgumentListItem` (already exactly "identification only" — id,
  slug, case_name, docket_number, term_year, argued_date, question_number) as the base
  search-result row, adding whatever match-context field is needed (e.g. which
  dimension matched — case/docket/speaker/term) as a new apolitical field, never a
  relevance score or ranking signal (that reads as an editorial judgment the apolitical
  constraint forbids).

### Query strategy: LIKE vs. trigram vs. tsvector

No FTS infrastructure exists today (verified: zero `tsvector`/`pg_trgm` migrations).
At ~7,800 arguments this is a genuinely small table — Postgres does not need heavyweight
FTS to answer this class of query fast:

- **Case name / docket / term**: exact-prefix or `ILIKE '%term%'` against `case_name`
  and `docket_number` is adequate at this row count with a plain B-tree or even no index
  at first; add a `pg_trgm` GIN index (`CREATE EXTENSION pg_trgm; CREATE INDEX ... USING
  gin (case_name gin_trgm_ops)`) only if the operator observes slow queries at real
  volume — this is exactly the kind of premature-optimization the operator's Testing
  Policy warns against pre-committing to.
- **Speaker name**: `ILIKE` against `Person.full_name`, joined through
  `ArgumentParticipant`. Multi-word queries ("Ruth Bader Ginsburg") need every word to
  match, not the exact phrase — `ILIKE '%word1%' AND ILIKE '%word2%'` per split token is
  the plainest correct approach, not `to_tsvector` (which brings a text-search-config,
  stemming, and language behavior this domain has zero use for — proper nouns don't
  stem).
- **Term**: an integer match against `Case.term_year`, already indexed implicitly by
  the existing term-index query pattern.
- A single combined query with `UNION` (or `OR` across all four dimensions in one
  query) is simpler to reason about than dispatching to four different endpoints —
  match the "empty-results state that explains the OT 1955–2019 range" requirement
  (PROJECT.md) to a single result set, not four.
- This is a genuine build-time decision (LIKE now, trigram GIN later if needed) — not
  a phase-blocking research question. Do not spike Postgres FTS extensions for a
  7,800-row table.

### Results route: SSR vs. client, query params, pagination

- **Route**: `app/src/routes/search/+page.server.ts` + `+page.svelte`, following the
  exact same shape as `arguments/+page.server.ts` — `load()` reads `url.searchParams`
  (e.g. `?q=...&page=...`), calls `FASTAPI_BASE_URL` via server-only `fetch`, and
  returns data to the page. This is a load-function fetch exactly like every other
  page — **no client-side fetch to FastAPI is introduced**, preserving Architecture
  Rule 2 without exception.
- **SSR, not client-rendered.** A search-results page is a shareable URL
  (`/search?q=Obergefell`) the same way `/arguments/{slug}` is — SSR on hard refresh is
  already a locked requirement pattern (UI-06, v1.0). A client-side-only search
  (fetch-on-keystroke against a public API) would require exposing a `PUBLIC_` API
  base URL, which is exactly the discipline Architecture Rule 2 exists to prevent. Do
  not build that.
- **The query itself is submitted via a GET form** (`<form method="GET">` posting to
  the same route, no `use:enhance`/action needed) so the URL is the state — matches
  the read-only, no-interactivity-beyond-navigation posture CLAUDE.md's project
  description sets ("never interactive for end users" beyond browsing).
- **Pagination**: `?page=N` query param, default page size in the 20–50 range given
  7,800 max rows across all dimensions combined (never unbounded — `list_terms()` /
  `list_arguments_for_term()` return everything unbounded today only because term-
  scoped result sets are small; a global search has no such natural bound and must
  paginate from day one). Offset/limit is sufficient at this scale; keyset pagination
  is unwarranted complexity for a corpus this size.
- **Empty state**: the PROJECT.md requirement ("an empty-results state that explains
  the OT 1955–2019 range") is a copy/product decision, not an architecture one — flag
  it to the operator when scoping the phase, but the plumbing (a `results.length === 0`
  branch in `+page.svelte`) is identical either way.

### New vs. modified components

| File | New/Modified |
|---|---|
| `api/services/arguments.py` — add `search_arguments()` | Modified |
| `api/routers/arguments.py` — add `GET /arguments/search` | Modified |
| `api/schemas/arguments.py` — add `SearchResultItem`/`SearchResponse` (or reuse `ArgumentListItem`) | Modified |
| `api/tests/test_trust_public_leak_ban.py` — add the new response model to the covered set | Modified (mandatory, same phase) |
| `app/src/routes/search/+page.server.ts`, `+page.svelte` | New |
| `app/src/lib/public/SearchResultRow.svelte` (or similar) | New |
| `app/src/lib/components/TopNav.svelte` — add a Search link | Modified |

---

## 2. Sitemap and robots.txt

### Where it's generated: FastAPI vs. SvelteKit endpoint vs. build-time artifact

**Recommendation: a SvelteKit `+server.ts` endpoint that queries FastAPI at request
time, not a build-time static artifact, and not a FastAPI-served file.**

Reasoning, weighed against the actual constraints:

- **A build-time artifact is wrong for this content.** ~7,800 URLs are a live database
  state, not a compile-time constant — Architecture Rule 1 ("FastAPI is read-only —
  the pipeline writes directly to Postgres; the API never triggers pipeline steps")
  and Rule 3 (re-running steps produce new rows) already establish that published
  content changes outside of any deploy. A build-time-generated sitemap goes stale the
  moment an operator publishes another batch — worse, it goes stale silently, which is
  exactly the kind of drift this project's whole trust/review model exists to prevent
  elsewhere. Regenerating and redeploying static assets on every publish batch is a
  workflow no one has asked for and the roadmap doesn't budget for.
- **FastAPI serving the sitemap directly is a Rule 2 violation waiting to happen.**
  It would mean either (a) exposing a raw FastAPI URL to search-engine crawlers,
  bypassing SvelteKit entirely — a second public entry point outside the
  `+page.server.ts` discipline the whole frontend is built around — or (b) FastAPI
  generating XML, which is a presentation concern that has never lived in this API
  layer (every existing router returns Pydantic JSON, nothing else).
  Neither is a good precedent to set for what is otherwise a strict rule.
- **A SvelteKit `app/src/routes/sitemap.xml/+server.ts`** (returning
  `Content-Type: application/xml`) is the correct seam: it is a server-only file (same
  trust boundary as every `+page.server.ts`), it calls `FASTAPI_BASE_URL` exactly like
  every load function does, and it can set an HTTP cache header (e.g.
  `Cache-Control: public, max-age=3600`) so it isn't recomputed on every crawler hit
  without needing a build step at all. This is the standard SvelteKit sitemap pattern
  and it fits this codebase's existing seams exactly.
- **`robots.txt`** is genuinely static (it only needs to say "disallow /admin,
  reference the sitemap URL") — that one *can* be a plain file at `app/static/robots.txt`,
  since its content has no dependency on database state. Do not put dynamic logic in
  it.

### Respecting the published-gate

- The sitemap-generating query is **the same two-predicate published gate** every
  other public query uses — `published_at IS NOT NULL` AND `status == PUBLISHED`
  (plus the `slug IS NOT NULL` guard, since a slugless argument has no sitemap-able
  URL at all). This needs either a new lightweight FastAPI endpoint
  (`GET /arguments/sitemap-urls` returning `{slug, term_year}` for every published,
  slugged argument) or reuse of `list_terms`/`list_arguments_for_term` iterated across
  all terms. A dedicated endpoint that returns just slugs (no metadata) is the leaner,
  more obviously-safe choice — smaller response, and it minimizes what new fields have
  to be checked against the leak-ban in the first place.
- **This dedicated endpoint is new public API surface** — it must be added to
  `PUBLIC_ROUTER_MODULE_NAMES`/schema coverage in `test_trust_public_leak_ban.py` in
  the same phase, same as search.
- At ~7,800 rows, returning the full slug list in one response and building XML in the
  SvelteKit endpoint is trivial (a few hundred KB of JSON, well under any reasonable
  timeout) — no pagination needed for the sitemap generator itself, unlike the
  human-facing search results.

### New vs. modified components

| File | New/Modified |
|---|---|
| `api/services/arguments.py` — add `list_all_published_slugs()` (or similar) | Modified |
| `api/routers/arguments.py` — add `GET /arguments/sitemap-urls` | Modified |
| `api/schemas/arguments.py` — add a minimal `SitemapEntry` model | Modified |
| `api/tests/test_trust_public_leak_ban.py` — cover the new endpoint | Modified |
| `app/src/routes/sitemap.xml/+server.ts` | New |
| `app/static/robots.txt` | New |

---

## 3. Analytics — the first client-side third-party script

This is the one item that genuinely breaks a pattern rather than extending one, so it
needs the most explicit reasoning.

### What "first client-side script" actually changes

Every existing request in this codebase is `SvelteKit server → FastAPI`, gated through
`$env/static/private`. There has never been a browser making a request to anything
outside the SvelteKit origin. An analytics script, by definition, has the browser make
a request to a third-party origin (the analytics vendor's collector endpoint) — that is
new in kind, not degree, and needs to be treated as a genuine architectural boundary
change, not "one more script tag."

### Where it loads

- **`app/src/app.html`** is the only place a global, every-page script tag can live
  without duplicating markup into every route's `+layout.svelte` — it is already the
  file that owns the single other static, whole-site concern (the favicon link,
  `%sveltekit.head%`/`%sveltekit.body%` placeholders). A `<script>` tag for the
  analytics loader belongs there, or (cleaner, and easier to make conditional) inside
  `app/src/routes/+layout.svelte`'s markup, which already wraps every route including
  `/admin/*`.
- **It must not load on `/admin/*`.** There is no operator-facing reason to send
  analytics events for authenticated admin sessions, and every existing precedent in
  this codebase (nav, layout) treats admin as a genuinely separate surface. Since
  `+layout.svelte` at the root wraps both public and admin routes, the loader needs a
  path check (`$page.url.pathname.startsWith('/admin')`) or the analytics script needs
  to live in a public-only layout scope. Given `hooks.server.ts` already knows
  `isAdminArea` as a boolean, the cleanest fix is to pass that signal down (e.g. via
  `event.locals` into root `+layout.server.ts` → `data.isAdminArea` → conditional
  render in `+layout.svelte`) rather than re-deriving the path check independently in
  two places.

### Server-only-env-var discipline: does `FASTAPI_BASE_URL`'s rule extend to analytics config?

**No — and that distinction matters.** `FASTAPI_BASE_URL` is server-only because it
names an internal service the browser must never be able to address directly (Rule 2
exists to keep the API surface behind SvelteKit's own load functions). An analytics
site ID/token is the opposite case: it is **meant** to be visible in the browser — the
vendor's collector script cannot function without the browser knowing which site/key
to report against, and that value carries no ability to read or write anything (unlike
`ADMIN_TOKEN`, which authenticates privileged writes).

So:
- The analytics site key belongs in `PUBLIC_` env vars
  (`$env/static/public`, e.g. `PUBLIC_ANALYTICS_SITE_ID`), a genuinely different (and
  first-ever) category from every existing env var in this codebase, which are all
  `$env/static/private` (`FASTAPI_BASE_URL`, `ADMIN_TOKEN`, `SESSION_SECRET`,
  `ADMIN_USERNAME`/`PASSWORD`). This is not a violation of Rule 2 — Rule 2 is
  specifically about `FASTAPI_BASE_URL` never becoming `PUBLIC_`, not a blanket ban on
  ever introducing a `PUBLIC_` var. Document this distinction explicitly when the
  phase lands, since it is the first `PUBLIC_` var this project will ever have and a
  future reader could otherwise misread it as drift.
- **No secret ever needs to leave the server for analytics to work** — cookieless,
  vendor-hosted analytics products (the class PROJECT.md's milestone note already
  points toward — "cookieless tooling may mean no consent UI at all") typically need
  only a public site identifier client-side; any server-to-server reporting API key
  (if the chosen vendor has one, e.g. for a server-side event-forwarding option) stays
  `$env/static/private` exactly like `ADMIN_TOKEN` does today.

### Public-leak-ban interaction

The structural ban (`test_trust_public_leak_ban.py`) protects **response payloads**
(Pydantic models and the frontend files that render data reaching them) — an analytics
script tag emitting page-view events carries no `trust_tier`/`review_state`/
provenance vocabulary by construction, since analytics reports URLs and UA strings, not
argument/participant field values. There is no code path by which analytics touches
the banned-key surface, so **no change to the ban test is needed for analytics
itself.**

The place analytics *does* intersect the apolitical constraint is indirect: if the
chosen vendor supports custom event properties, **never attach a case name, docket, or
speaker identity as an event property that could be aggregated into a
"most-viewed-Justice" or "most-viewed-case" style report** — that is exactly the
"cross-case justice statistics... politically interpretable" anti-feature PROJECT.md's
Out of Scope section already bans, just surfaced through a different tool. Flag this
explicitly in the phase's design so whoever configures the analytics dashboard doesn't
recreate the banned feature by accident through event taxonomy.

### Analytics vendor selection is an operator decision

The vendor itself is out of scope for this architecture note — what matters structurally is
that it be a genuinely cookieless, first-party-only script (see PITFALLS.md), since that is
what determines whether any consent surface is needed at all. Verify what the script actually
reads and writes on the device rather than trusting a "cookieless" claim.

### New vs. modified components

| File | New/Modified |
|---|---|
| `app/.env.example` — add `PUBLIC_ANALYTICS_SITE_ID` (or equivalent) | Modified |
| `app/src/routes/+layout.server.ts` | New (if it doesn't exist) or Modified — surface `isAdminArea` |
| `app/src/routes/+layout.svelte` | Modified — conditional script include |
| `app/src/app.html` | Possibly modified, if the loader is a raw `<script src>` rather than a Svelte-rendered tag |
| A privacy-policy page (`app/src/routes/privacy/+page.svelte`) | New — PROJECT.md names this explicitly alongside analytics |

---

## 4. Bulk publish

### CLI, not an admin API endpoint — and this is a strong, not a close, call

The pipeline-is-offline rule in CLAUDE.md ("Ingest/parse/resolve are CLI scripts.
Never expose pipeline steps as HTTP endpoints or user-facing features") is written
about the *ingest* pipeline, but the same reasoning applies squarely to bulk publish,
and the codebase already has the exact template to follow:

- **`recompute-trust` and `prune-runs` are the precedent**, and they are structurally
  identical in shape to what bulk-publish needs: "scan every argument (or a
  `--term`/`--argument-id` subset), one DB session per row, `--dry-run` support,
  report scanned/unchanged/changed, never a partial-scan rollback." Bulk publish is not
  a new architectural pattern — it is the third instance of a pattern this codebase
  has already built twice (`pipeline/commands/recompute_trust.py`,
  `pipeline/commands/prune_runs.py`), registered in `pipeline/__main__.py` alongside
  them.
- **It must call the existing `publish_argument(db, argument_id, override_reason=None)`
  service function per row, not reimplement its gates.** That function already
  encodes every rule bulk-publish needs to respect: the non-overridable `resolved_at
  IS NULL` guard, the already-published no-op guard, and the overridable trust-tier
  gate for `UNCERTAIN` rows (this is the exact mechanism behind the ">50%-undetermined
  publish gate" PROJECT.md's SPEAKER work item names — it is not a new gate bulk-publish
  invents, it is the existing one bulk-publish must not bypass). Writing a bespoke bulk
  UPDATE that sets `status=PUBLISHED, published_at=now()` directly against the table
  would silently skip the trust gate and the `ArgumentStatusLog` audit row
  `publish_argument` writes on every call — a real defect class per the Defect Policy's
  "anything contradicting a locked decision" bucket, not a style choice.
- **An admin API endpoint would be the wrong shape for the actual failure mode.**
  ~7,800 rows means several genuinely-blocked rows (the 6 arguments PROJECT.md already
  notes are held back at >50% undetermined) and a long-running operation with a
  scanned/blocked/published report — that is a batch-job shape (stdout, exit code,
  re-runnable), not a request/response shape a browser click should be waiting on. The
  existing `AdminJob`/pipeline-subprocess-with-polling machinery exists precisely
  because HTTP request handlers in this app are never supposed to await
  long-running work (`pipeline_spawn.py`'s fire-and-poll pattern) — bulk-publish for
  the *entire remaining corpus* is a one-time, operator-initiated, off-hours operation,
  not a recurring admin-UI action that benefits from a live status page. If per-batch
  publishing becomes a recurring need post-launch (e.g. publishing each new term as it
  is imported), that is a scoping question for a future milestone, not a reason to
  build a live-progress admin screen now.
- **The one thing the CLI needs that `recompute-trust`/`prune-runs` don't**: a report
  that distinguishes "blocked, needs an operator override reason" from "published
  cleanly" from "already published" — because `publish_argument` raises
  `TrustGateBlocked`/`ValueError` rather than silently skipping. The command needs to
  catch those per-row, accumulate them into a blocked-list (with the `TrustGateBlocked`
  breakdown for whichever handful of arguments are genuinely stuck), and print a
  summary — not let one blocked row abort the whole batch, and not silently drop the
  info about which rows need operator attention.
- **`--override-reason` should not be a single blanket flag applied to all 7,800
  rows.** A generic reason like "bulk launch publish" applied uniformly would satisfy
  the non-blank check but defeat the audit trail's purpose (the reason is meant to
  explain *why this specific argument* is being published despite being UNCERTAIN).
  The realistic path: run the bulk command with no override first, let it publish
  everything that passes the trust gate cleanly, then handle the small number of
  blocked rows (PROJECT.md already names 6) individually through the existing
  single-argument publish flow in `/admin/arguments/[id]`, where a real per-argument
  reason can be entered. This is a genuinely good fit for the "Claude's, always" vs.
  "operator's" line in CLAUDE.md's Defect Policy — the *plumbing* (bulk CLI, batching,
  reporting) is an implementation question Claude can just build; *whether an
  individual blocked argument should be force-published with a given reason* is a
  domain judgment call for the operator, one row at a time.

### New vs. modified components

| File | New/Modified |
|---|---|
| `pipeline/commands/bulk_publish.py` | New — mirrors `recompute_trust.py`'s shape exactly |
| `pipeline/__main__.py` — register `bulk-publish` subcommand (`--all` / `--term` / `--dry-run`) | Modified |
| `api/services/admin_arguments.py` | Not modified — `publish_argument` is reused as-is |

---

## 5. Suggested build order

Ordering follows real dependencies, not just a phase-numbering convenience:

1. **Bulk publish (CLI)** — first, because it has zero dependency on anything else in
   this list and every other item's real-world testing quality depends on it. Search,
   the sitemap, and "nothing has ever been rendered at realistic volume"
   (`launch-readiness.md`) are all better verified against ~7,800 real published rows
   than against four fixtures. This also directly retires the launch-readiness item
   "Nothing has ever been rendered at realistic volume."

2. **Search** — next, because it is pure backend + one new route, has no dependency on
   the landing page, and is explicitly named as an open question ("Does search ship at
   launch? It is net-new and the homepage brief leans on it" —
   `launch-readiness.md`). Building search before the landing page means the landing
   page's search-forward design (per `HOMEPAGE-BRIEF.md`, "prominent search... search
   or browse entry point") has a real endpoint to link to instead of a stub.

3. **Landing page + About page** — depends on search existing (the homepage brief
   leans on a working search box) and benefits from real published volume (a landing
   page's "recent arguments" or count-of-corpus framing needs real numbers, not four
   fixtures). This is also the item most gated on a **product decision the operator
   has explicitly not made yet** ("the Figma exploration is a starting point with no
   conclusions, not a shortlist" — `PROJECT.md`), so sequence it after the
   lower-ambiguity backend work so that open design conversation doesn't block
   everything behind it.

4. **Oyez source links** — small, independent, can land any time after step 1 (needs
   real `oyez_transcript_id` data to look non-trivial, though the field already exists
   and is already public). Cheapest to slot in alongside the About page phase or
   directly after bulk-publish, since it touches the same argument-detail template.

5. **Sitemap + robots.txt** — depends on real published-corpus volume (a sitemap of
   four fixtures proves nothing about the ~7,800-URL case explicitly named in the
   question) and depends on slugs existing for the whole corpus, which bulk-publish
   (step 1) exercises. Do this after bulk-publish, not before — building it against
   the tiny current corpus would leave the "respects the published-gate at 7,800 URLs"
   claim unverified until the very end.

6. **Analytics + privacy policy** — last, and deliberately decoupled from the rest.
   It has no functional dependency on search, the landing page, or the sitemap; it is
   the one item that changes a structural discipline (first client-side script, first
   `PUBLIC_` env var) rather than extending an existing pattern, so isolating it into
   its own phase makes that boundary change easy to review and easy to roll back
   independently of the content-facing work above. Landing it last also means it
   starts collecting real page-view data against the actual final public surface
   (search, landing page, About, sitemap all already live) rather than against a
   still-changing site.

**Cross-cutting reminder for every phase above that adds a public FastAPI route or
schema**: update `PUBLIC_ROUTER_MODULE_NAMES` / `PUBLIC_SCHEMA_MODULE_PATHS` /
`PUBLIC_FRONTEND_PATHS` in `api/tests/test_trust_public_leak_ban.py` in the *same*
phase, not as a follow-up — that test only covers what it's told to cover.

---

## Sources

- Direct reads (2026-09-23) of: `api/main.py`, `api/routers/arguments.py`,
  `api/services/arguments.py`, `api/schemas/arguments.py`, `api/schemas/utterance.py`,
  `api/services/admin_arguments.py` (publish_argument, ~lines 751-859),
  `api/models/models.py` (Person/Case/Argument/ArgumentParticipant),
  `api/tests/test_trust_public_leak_ban.py`, `pipeline/__main__.py`,
  `pipeline/commands/recompute_trust.py`, `app/src/hooks.server.ts`,
  `app/src/app.html`, `app/src/routes/arguments/+page.server.ts`,
  `app/src/routes/arguments/+page.svelte`, `app/src/lib/components/TopNav.svelte`,
  `app/package.json`, `app/svelte.config.js`, `app/.env.example`, `.env.example`,
  `alembic/versions/` (directory listing, migration-count check).
- `.planning/PROJECT.md`, `.planning/notes/launch-readiness.md`,
  `.planning/positioning/HOMEPAGE-BRIEF.md` (search requirements, positioning intent).
- `/home/jason/scotuschat/project/CLAUDE.md` (pipeline-is-offline rule, Architecture
  Rules, Defect Policy, Testing Policy).

---
*Architecture research for: scotuschat v1.9 — The Site Becomes Complete*
*Researched: 2026-09-23*
