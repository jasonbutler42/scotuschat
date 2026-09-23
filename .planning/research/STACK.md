# Stack Research: v1.9 Additions (Search, Analytics, Sitemap/Metadata)

**Domain:** Additions to an existing SvelteKit/FastAPI/Postgres read-only public archive
**Researched:** 2026-09-23
**Confidence:** HIGH (Postgres search, SvelteKit native capabilities) / MEDIUM (analytics consent legal position, DO extension allowlist for `unaccent`)

**Scope note:** This is a subsequent-milestone STACK research pass. It does not re-litigate the validated v1.0–v1.8 stack (SvelteKit 2.x/Svelte 5 Runes, FastAPI 0.115+/Pydantic v2, PostgreSQL 16/SQLAlchemy 2.0/Alembic, DO App Platform). It covers only what SEARCH, ANALYTICS, and SITEMAP/METADATA need.

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `pg_trgm` (Postgres contrib extension) | Ships with PostgreSQL 16 core (module version 1.6, no separate install) | Trigram-based fuzzy/substring matching on case name, docket number, speaker name | Confirmed on DigitalOcean's Managed PostgreSQL supported-extensions list. Turns `ILIKE '%term%'` into an index-assisted query and adds typo-tolerant `%` similarity matching — exactly the "Miranda finds Miranda v. Arizona" and varied-docket-format requirement, with zero new service to run or sync |
| `unaccent` (Postgres contrib extension) | Ships with PostgreSQL 16 core | Diacritic-insensitive matching for party/speaker names with accents (e.g., a hypothetical "Peña-Rodríguez") | Cheap insurance against a rare-but-real case class; not confirmed on DO's public extension list in this research pass — **verify with `SELECT * FROM pg_available_extensions WHERE name = 'unaccent';` against the actual DO managed instance before writing the migration that depends on it.** If unavailable, the feature degrades gracefully (accented names still match if the user types the accent) |
| Postgres native `tsvector`/`to_tsvector` + GIN index (built into Postgres core, no extension) | PostgreSQL 16 | A single ranked, weighted, multi-field search across case name, docket, speaker names, and term year for the "search bar" query | This is what makes a *single* search box work across four dimensions without four separate query paths: `setweight()` on each source column into one `tsvector`, indexed with GIN, ranked with `ts_rank`. Complements `pg_trgm` rather than replacing it — see integration pattern below |
| GoatCounter (hosted, free tier) | Current hosted service, no self-managed version to track (n/a — SaaS) | Page-view and referrer analytics | Free for non-commercial sites (site content is CC BY-NC — this project qualifies) with a 100,000-pageview/month ceiling on the free tier, no automated enforcement of the commercial/non-commercial line (honor system). No cookies, no localStorage, no persistent client-side identifier — visitor counting is a server-side rotating hash, never written to the browser. Adds a single `<script>` tag; no new infrastructure to deploy or operate before DEPLOY-01 has even shipped |
| SvelteKit `+server.ts` endpoint | SvelteKit 2.x (already pinned) | `/sitemap.xml` generation | SvelteKit endpoints can return arbitrary `Response` bodies including XML with the right `Content-Type` header — this is the documented, native pattern in SvelteKit's own SEO guidance. No library adds capability SvelteKit doesn't already have |
| `svelte:head` | Svelte 5 (already pinned) | Page `<title>`, meta description, Open Graph/Twitter tags | Native Svelte element; every meta-tag library found in this research (svead, svelte-meta-tags) is *itself* a thin wrapper around `svelte:head` with a typed prop API — no functional gain for a project of this size, and it's one more dependency to keep compatible with each SvelteKit/Svelte upgrade |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| *(none)* | — | — | Deliberately no new supporting library for any of the three capabilities. See "What NOT to Use" — every candidate library found in this research is either a thin convenience wrapper around a native SvelteKit/Postgres capability, or solves a scale problem this project does not have |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `EXPLAIN ANALYZE` (built into `psql`) | Verify the trigram/GIN index is actually chosen by the planner instead of a sequential scan | At ~7,800 rows Postgres may legitimately choose a seq scan over an index scan and be *faster* doing so — that is expected and fine at this size; don't force index usage. Re-check with `EXPLAIN ANALYZE` if the row count grows by orders of magnitude |
| DO Managed PostgreSQL control panel / `pg_available_extensions` | Confirm `unaccent` availability before depending on it in a migration | See flag above — this is the one unverified fact in this document |

## Installation

```bash
# Postgres side — via an Alembic migration (Alembic is the sole DDL authority per project constraint)
# alembic/versions/00XX_add_search_extensions_and_indexes.py
#   op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
#   op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")   # gate behind the DO verification above
#   op.execute("CREATE INDEX idx_arguments_case_name_trgm ON arguments USING gin (lower(case_name) gin_trgm_ops)")
#   op.execute("CREATE INDEX idx_arguments_docket_trgm ON arguments USING gin (lower(docket_number) gin_trgm_ops)")
#   op.execute("CREATE INDEX idx_people_display_name_trgm ON people USING gin (lower(display_name) gin_trgm_ops)")
#   # combined weighted document for the single search bar:
#   op.execute("""
#     ALTER TABLE arguments ADD COLUMN search_document tsvector
#       GENERATED ALWAYS AS (
#         setweight(to_tsvector('simple', coalesce(case_name, '')), 'A') ||
#         setweight(to_tsvector('simple', coalesce(docket_number, '')), 'B')
#       ) STORED
#   """)
#   op.execute("CREATE INDEX idx_arguments_search_document ON arguments USING gin (search_document)")

# Frontend — no npm install needed for sitemap/metadata; SvelteKit already covers it
# Analytics — one script tag in app.html or a root +layout.svelte, no package install:
# <script defer data-goatcounter="https://yoursite.goatcounter.com/count" src="https://gc.zgo.at/count.js"></script>
```

No `npm install` and no `pip install` are required for any of the three v1.9 capabilities. That absence is the finding, not an oversight.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|--------------------------|
| `pg_trgm` + native `tsvector`/GIN on Postgres 16 | Meilisearch / Typesense / Elasticsearch / OpenSearch (external search engine) | Only if the project ever brings the 1.7M utterance *bodies* into search scope with linguistic ranking/highlighting at high query volume — a different, larger problem than the four-dimension metadata search actually in scope. At 7,800 metadata rows this is categorically not warranted; see Scale Threshold below |
| `pg_trgm` | `pg_bigm` | `pg_bigm` (2-gram, not 3-gram) is the standard choice for CJK-language fuzzy search, where trigrams are too coarse for short logographic tokens. Irrelevant here — all corpus text is English |
| GoatCounter hosted free tier | Plausible Cloud ($9/mo Starter, 10k views) | If the operator wants a more polished dashboard/UI and is fine paying from day one; Plausible's cloud tier is priced for exactly this kind of small site |
| GoatCounter hosted free tier | Plausible Community Edition (self-hosted, free software but ~$12–24/mo in DO Droplet/infra cost plus ongoing maintenance) or Umami (self-hosted, free, MIT-licensed, requires its own Next.js service + Postgres DB) | If the operator wants zero third-party data processor and full control, accepting the added ops burden of a second deployed service *before* DEPLOY-01 has even shipped this app's first service. Self-hosting Plausible CE currently also carries a live CVE (CVE-2026-8467, fixed in v3.2.1 — patch immediately if this path is chosen) |
| GoatCounter hosted free tier | Fathom Analytics ($15/mo minimum, 100k views, no self-host option) | If the operator specifically wants Fathom's dashboard/support and is comfortable with a recurring paid SaaS bill for a non-commercial archive |
| Native `svelte:head` | `svead` or `svelte-meta-tags` (npm) | If the site grows to dozens of distinct page templates and the team wants one typed component enforcing a consistent OG/Twitter tag shape across all of them. At the current handful of page types (landing, about, argument detail, term listing, search results) this is not yet worth a dependency |
| Native `+server.ts` sitemap endpoint | `svelte-sitemap` (Vite plugin, build-time generation) | If the site were fully static-content (no per-request DB-backed URL list) and a build-time sitemap made sense. This project's sitemap needs live data (~7,800 argument slugs from Postgres) — a request-time endpoint is the correct shape, not a build artifact that goes stale between deploys |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|--------------|
| Tailwind or any utility-CSS framework, for anything touched by this milestone | Removed for cause in Phase 51 (v1.8) in favor of the hand-authored CSS custom-property token set; the operator has stated this preference unprompted and it is a locked project decision, not a live tradeoff | The existing two-layer token set (35 primitives + 75 semantic names) and `lib/primitives` component library |
| Elasticsearch / OpenSearch / Algolia / Meilisearch / Typesense for the case/docket/speaker/term search | Solves a query-latency-at-scale problem this project does not have at ~7,800 rows across four narrow metadata dimensions; introduces a second system of record that must be kept in sync with Postgres (indexing lag, dual-write consistency risk, an operational service to run/monitor/patch) for no measurable query-time benefit here | `pg_trgm` + `tsvector`/GIN directly in the existing Postgres 16 instance |
| Google Analytics / GA4, Meta Pixel, or any ad-tech tag manager (GTM, etc.) | Explicitly ruled out by the operator ("does not want ad tech or monetisation"); these set persistent cross-site identifiers/cookies, which is precisely the category that *does* trigger a real ePrivacy consent obligation — the opposite of what's wanted here | GoatCounter (or Plausible/Fathom/Umami if the operator later prefers one of those) |
| A cookie-consent-management platform (OneTrust, Cookiebot, CookieYes, etc.) or a hand-rolled consent banner | Solves a problem a genuinely cookieless, non-fingerprinting analytics tool doesn't create; adding one back reintroduces the exact UX/legal surface the "cookieless" choice was meant to avoid, plus a new third-party vendor relationship of its own | A short, honest privacy-policy page describing what is and isn't collected (no banner needed if the analytics tool meets the criteria below) |
| Assuming "cookieless" alone settles the legal question | Cookieless avoids the *ePrivacy* device-storage trigger, but a cookieless tool can still process personal data server-side, which is a separate GDPR analysis. The safe-harbor most privacy-first analytics vendors actually design against is the French CNIL's audience-measurement exemption criteria (self-assessment framework effective 2026-01-01): first-party only, ≤3 event types, IP truncated/hashed, ≤13-month tracker lifespan, ≤25-month data retention, host-only referrer, results aggregated to the nearest 10, no cross-site tracking, statistics-only purpose | Confirm the chosen tool's own compliance documentation against those specific criteria (GoatCounter, Plausible, Fathom, and Umami are all built around meeting them) and say so plainly on the privacy-policy page rather than asserting "no cookies, so no obligations" |
| A separate Redis/cache layer in front of Postgres for search | No query volume in this project (low-traffic public archive) justifies a caching layer; adds operational surface for a problem that doesn't exist yet | Direct Postgres queries; revisit only if real traffic data says otherwise |

## Stack Patterns by Variant

**If the operator later wants zero third-party data processor for analytics at all:**
- Self-host Umami (MIT-licensed, genuinely no cookies/localStorage, server-side salted-hash identity) as an additional DO App Platform component with its own Postgres (either a second managed DB or a separate schema in the existing cluster)
- Accept the added ops cost: one more service to deploy, patch, and monitor, on top of a stack that hasn't shipped DEPLOY-01 yet

**If utterance-body full-text search ever comes into scope (currently explicitly out of scope for v1.9):**
- Start with Postgres `tsvector`/GIN across the 1.7M utterance rows before reaching for an external engine — Postgres full-text search remains viable well past this row count for read-mostly workloads
- Only escalate to Meilisearch/Typesense/Elasticsearch if that Postgres-native approach demonstrably fails a real latency or relevance requirement under real traffic — not preemptively

**If commercial use is ever considered for this CC BY-NC site (flagged as an open tension in PROJECT.md, not resolved here):**
- GoatCounter's free tier is honor-system non-commercial-only; a move toward monetization would obligate upgrading to GoatCounter's paid Business plan or switching tools — note this dependency if that decision ever gets made

## Search Scale Threshold — the specific answer to "is Postgres enough?"

**Recommendation: Postgres 16 native (`pg_trgm` GIN indexes + a weighted `tsvector`/GIN combined-search column) is not just sufficient but the *correct* choice at the current and reasonably-projected scale (~7,800 arguments, ~7,800×~a few participants for speakers, 65 terms).** Concretely:

- **Case name fuzzy matching** ("Miranda" → "Miranda v. Arizona"): a GIN index on `lower(case_name) gin_trgm_ops` makes `ILIKE '%miranda%'` index-assisted (not a sequential scan) and also supports typo tolerance via the `%` similarity operator (default threshold 0.3, tunable per session with `SET pg_trgm.similarity_threshold`)
- **Docket numbers in varied formats** (`759`, `84-1602`, `09-479`, `23-367`): these are short strings, but trigram indexing still works on them (a 7-character string like `84-1602` yields enough trigrams); a second GIN trigram index on `lower(docket_number)` handles substring search for both the term-prefix (`84-`) and full-string cases without a separate normalization column. A normalization column (digits only, via `regexp_replace`) is a reasonable follow-on if operator testing shows users typing dockets without hyphens, but isn't needed to ship
- **Speaker name and term year**: speaker name follows the same trigram pattern as case name; term year is a plain integer/date filter needing only a standard B-tree index — no fuzzy matching problem exists there at all
- **The scale threshold where this answer changes**: this recommendation would stop being right if either (a) utterance-body full-text search (1.7M rows of transcript prose) came into scope with a relevance-ranking/highlighting requirement at real user-facing query volume — a fundamentally different, larger problem than metadata search, and explicitly out of scope for v1.9 — or (b) sustained query throughput reached a level (many hundreds of concurrent search requests/second) where protecting the primary OLTP database's resources became the binding constraint, which would justify moving search reads to a replica or a dedicated index off the primary. Neither condition is remotely close for a public, read-only archive of ~7,800 historical documents. Metadata-only search over low tens of thousands of rows, or even low millions, stays comfortably inside what Postgres trigram/full-text indexing is designed for

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `pg_trgm` | PostgreSQL 16 (contrib module, bundled) | Confirmed present on DigitalOcean Managed PostgreSQL's supported-extensions list; enable per-database via `CREATE EXTENSION IF NOT EXISTS pg_trgm` in an Alembic migration, not manually |
| `unaccent` | PostgreSQL 16 (contrib module, bundled) | **Not independently confirmed available on DO Managed PostgreSQL in this research pass** — some managed Postgres providers (e.g., Azure Flexible Server in some tiers) restrict less-common contrib extensions even though they ship with core Postgres. Run `SELECT * FROM pg_available_extensions WHERE name = 'unaccent';` against the actual DO instance before the migration that depends on it lands |
| GoatCounter tracking script | Any static or SSR page (plain `<script>` tag, no build-time dependency) | Framework-agnostic; add via `app.html` or a root layout component. No SvelteKit-version coupling |
| Plausible self-hosted (if that path is chosen instead) | Current Community Edition is v3.2.1 (patches CVE-2026-8467, an RCE via an exposed `/storybook` endpoint in earlier CE builds) | If self-hosting Plausible is ever chosen over GoatCounter, do not deploy any version before v3.2.1 |
| SvelteKit `+server.ts` XML endpoint | SvelteKit 2.x (already pinned) | No version-specific gotchas found; this pattern has been stable across SvelteKit 1.x and 2.x |

## Sources

- [PostgreSQL 18 docs — F.35. pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html) — HIGH confidence, official docs
- [PostgreSQL docs — Appendix F, Additional Supplied Modules](https://www.postgresql.org/docs/current/contrib.html) — HIGH confidence, official docs (unaccent/pg_trgm as contrib modules)
- [DigitalOcean — Supported PostgreSQL Extensions](https://docs.digitalocean.com/products/databases/postgresql/details/supported-extensions/) — HIGH confidence, official docs; confirms `pg_trgm`, does not explicitly list `unaccent` in the search excerpt retrieved (verify directly)
- [Fast Search with PostgreSQL: GIN Index](https://whitestork.me/blog/20/Fast-Search-with-PostgreSQL:-GIN-Index) — MEDIUM confidence, practitioner blog, corroborates official docs
- [Performant text searching and indexes in PSQL](https://medium.com/@daniel.tooke/performant-text-searching-and-indexes-in-psql-trigrams-like-and-full-text-search-784c000efaa6) — MEDIUM confidence, practitioner blog
- [GoatCounter — self-hosting / pricing coverage via analytics-alternatives.com](https://analytics-alternatives.com/goatcounter-review-2026/) — MEDIUM confidence, third-party review site, cross-checked against goatcounter.com positioning
- [Plausible Analytics Pricing 2026 — seline.com](https://seline.com/blog/plausible-analytics-pricing) — MEDIUM confidence, third-party pricing aggregator
- [Plausible/analytics GitHub Releases](https://github.com/plausible/analytics/releases) — HIGH confidence, primary source (version/CVE)
- [Umami GitHub — umami-software/umami](https://github.com/umami-software/umami) — HIGH confidence, primary source (no-cookie, no-localStorage architecture)
- [CNIL Sheet n°16 — Use analytics on your websites and applications](https://www.cnil.fr/en/sheet-ndeg16-use-analytics-your-websites-and-applications) — HIGH confidence, primary regulator source
- [CNIL Sheet 16, Decoded — statnive.com](https://statnive.com/blog/cnil-sheet-16-audience-measurement-exemption-france) — MEDIUM confidence, third-party summary of the 2026 self-assessment framework
- [Digital Omnibus / ePrivacy Regulation withdrawal coverage — ppc.land](https://ppc.land/french-data-regulator-updates-cookie-exemption-rules-for-websites/) — MEDIUM confidence, industry news, flags that EU cookie-rule consolidation into GDPR is still a live proposal as of mid-2026, not settled law
- [SvelteKit SEO guidance — sveltekit.io blog, sitemap endpoint pattern](https://sveltekit.io/blog/svelte-sitemaps) — MEDIUM confidence, community blog referencing SvelteKit's own documented `+server.ts` pattern
- [Svead — GitHub](https://github.com/spences10/svead) and [svelte-meta-tags — npm](https://www.npmjs.com/package/svelte-meta-tags) — HIGH confidence, primary sources, both confirm they wrap `svelte:head` rather than adding new capability

---
*Stack research for: SCOTUS Chat v1.9 — Search, Analytics, Sitemap/Metadata*
*Researched: 2026-09-23*
