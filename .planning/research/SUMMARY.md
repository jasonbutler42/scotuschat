# Project Research Summary

**Project:** SCOTUS Chat v1.9 — "The Site Becomes Complete"
**Milestone:** v1.9
**Domain:** Publishing and discovery for a read-only legal-transcript archive
**Researched:** 2026-09-23
**Confidence:** HIGH (stack, architecture, engineering pitfalls — grounded in codebase inspection) / MEDIUM (feature expectations, analytics consent interpretation)

## Executive Summary

v1.9 adds six capabilities to a mature read-only archive: metadata search, a landing page, an About page, Oyez source attribution, SEO plumbing (sitemap / robots / page metadata), and privacy-first analytics — on top of the data-correctness and bulk-publish work already specified in `.planning/notes/`.

The architecture strategy is to **extend existing patterns rather than introduce new services**. Search stays inside PostgreSQL. Sitemap generation lives in a SvelteKit endpoint. Analytics is a single client-side script with no new backend. Bulk publishing is a CLI command reusing the existing single-row publish gate. **No new npm or pip packages are required for any of it.**

The critical build order is **bulk-publish first** (it is what makes real-volume testing possible for everything after it), then search, then landing/About, then Oyez links, then sitemap/robots, with analytics last so the one item that changes a structural discipline is isolated.

The highest-consequence pitfall is search or sitemap leaking unpublished content through a missed publish-gate predicate — the same bug class as the already-fixed BUG-01, and easy to reintroduce through a second code path.

Success here is not ambitious: working search across 7,800 rows, every new page keyboard-accessible, and a privacy policy that states plainly what is measured. This is a single-maintainer, non-commercial, read-only site where correct and simple beats polished.

## Key Findings

### Recommended Stack

**No new npm or pip packages.** Every capability is built from existing stack elements or native SvelteKit / PostgreSQL features.

| Technology | Role |
|---|---|
| `pg_trgm` (PostgreSQL contrib, bundled) | Trigram fuzzy/substring matching on case name, docket, speaker name. Confirmed on DigitalOcean's supported-extensions list. Turns `ILIKE '%term%'` into an index-assisted query. |
| Weighted `tsvector` / GIN (PostgreSQL core) | **Disputed — see below.** |
| SvelteKit `+server.ts` endpoints | `/sitemap.xml` at request time (not build time, so it reflects published-corpus state) |
| Native `svelte:head` | Per-page titles, meta descriptions, OG/Twitter tags — no library needed |
| GoatCounter (hosted) | Candidate analytics: free tier, no `document.cookie`, no localStorage, no persistent client-side id, no new backend. Plausible / Fathom / self-hosted Umami are documented alternatives. **Vendor choice is an open operator decision.** |
| `unaccent` (PostgreSQL) | Optional, for diacritic-insensitive matching. **Not verified available on DigitalOcean — confirm with `SELECT * FROM pg_available_extensions` before any migration depends on it.** |

**Explicitly NOT to be added:** Elasticsearch / OpenSearch / Meilisearch / Typesense / Algolia (a scale problem this archive does not have), Tailwind or any utility CSS (locked decision from Phase 51 — must not return), GA4 / Meta Pixel / ad-tech tag managers, cookie-consent platform tooling, and a Redis cache layer.

### The one genuine disagreement: search query strategy

`STACK.md` and `ARCHITECTURE.md` reached different conclusions. This is recorded rather than resolved.

| | Position |
|---|---|
| **STACK.md** | `pg_trgm` GIN trigram **plus** a weighted `tsvector`/GIN combined column, for a single ranked multi-field search |
| **ARCHITECTURE.md** | Trigram alone is adequate at ~7,800 rows; explicitly cautions **against** `tsvector` as premature optimisation |

**They agree trigram is needed.** They disagree only on whether `tsvector` adds anything at this scale. This is a phase-scoped decision for whoever builds search — decide it before engineering starts, ideally against a performance measurement rather than an opinion.

### Expected Features

**Table stakes**

- Metadata search across case name, docket, speaker, term
- A zero-result state that names the OT 1955–2019 boundary
- Landing page following `HOMEPAGE-BRIEF.md`'s content priority
- About page — scope, licensing, maintainer, non-goals (content already drafted in `VOICE.md`)
- "View source transcript on Oyez" link — the data shipped in Phase 47's `external_id`; this is a link template, not new collection
- Aggregate analytics, operator-facing only

**Differentiators (not required for v1.9)**

- Speaker-name results showing which argument the speaker appears in
- Docket-number format normalisation in search
- Query-aware zero-result state that detects an out-of-range year

**Anti-features — actively wrong for this project**

| Anti-feature | Constraint it violates |
|---|---|
| Public "trending" / "most viewed" modules | Implicit importance ranking. Table stakes on library archives (DPLA, National Archives) and forbidden here — the same effect as "featured" labelling. |
| Relevance-ranked search results | Editorialises which case matters |
| Outcome / disposition filters (cf. HUDOC's "violation found or not") | Requires outcome data already excluded entirely |
| Prominent coverage-count statistics | `HOMEPAGE-BRIEF.md`'s deliberate departure from the DPLA convention of leading with scale |
| Speaker leaderboards | Creates the implicit hierarchy the apolitical constraint forbids |

Comparable archives checked: CourtListener, HUDOC, Old Bailey Online, National Archives Catalog, Chronicling America, HathiTrust, DPLA, and Oyez itself.

### Architecture Approach

Search is a pure-read query added to the **existing** `api/routers/arguments.py` — not a new router. It reuses the `ArgumentListItem` response schema and the exact same two-predicate published gate (`published_at IS NOT NULL AND status == PUBLISHED`) every other public route uses.

Sitemap is a SvelteKit `+server.ts` endpoint querying published arguments at request time with a short cache TTL — not a build-time artifact (stale the moment bulk publish runs) and not served from FastAPI (breaks the server-load-function discipline).

Analytics is genuinely new **in kind, not degree**: the first client-side third-party script in this codebase and the first `PUBLIC_` env var it will ever have — distinct from, not a violation of, the rule that `FASTAPI_BASE_URL` stays server-only. It must be excluded from `/admin/*`, and **no case, docket or speaker identity may ever be attached as an event property**, which would recreate the banned cross-case-statistics anti-feature through analytics taxonomy rather than code.

Bulk publish is a CLI command following the existing `recompute-trust` / `prune-runs` template in `pipeline/__main__.py`. It must call the existing `publish_argument()` service per row — **never a raw bulk `UPDATE`** — because that function carries the trust-gate and audit-log logic bulk publish must not bypass.

**Cross-cutting constraint:** `api/tests/test_trust_public_leak_ban.py` derives "the public surface" from hand-maintained lists (`PUBLIC_ROUTER_MODULE_NAMES`, `PUBLIC_SCHEMA_MODULE_PATHS`, `PUBLIC_FRONTEND_PATHS`). It does **not** auto-discover. Every new public route or schema in v1.9 must be registered in the same phase that adds it, or the ban silently stops covering it.

### Critical Pitfalls

1. **Search re-implements the publish gate and leaks unpublished rows.** The same class as the already-fixed BUG-01. Reuse the service-layer gate; add a structural test proving zero unpublished-row leakage.
2. **Forgiving matching on docket numbers produces confidently wrong results.** Trigram matching is right for case names and wrong for dockets, where a one-character edit is a different real docket. Split into two classes: dockets get exact or normalised-exact matching; case and speaker names get forgiving matching. Never silently substitute a near-miss.
3. **Bulk publish looping over `publish_argument` is far slower at 7,800 rows than it looks** — 7,800 transactions, 7,800 trust recomputations, 7,800 PgBouncer round trips, and this stack already has PgBouncer constraints. Chunk commits, batch where possible, and make it resumable by construction (`WHERE status != 'PUBLISHED'`) rather than via a checkpoint table.
4. **Sitemap goes stale or leaks.** Generate dynamically using the same publish predicate as every other public route. Protocol limits confirmed at 50,000 URLs / 50MB — this corpus needs no sitemap index.
5. **Bulk publish bypasses the trust gate under performance pressure.** A raw bulk `UPDATE` silently readmits the UNCERTAIN / >50%-undetermined gate that Phase 48 exists to enforce. Whatever is built must derive the tier per row, and a post-run test should assert zero UNCERTAIN rows among newly-published arguments.

### Analytics and consent

The operator's hypothesis **holds**: the EU ePrivacy trigger (Art. 5(3), confirmed by EDPB's October 2024 guidelines) is genuinely *storage of, or access to, information on the device* — not "analytics" and not "personal data". Genuinely storage-free tooling therefore falls outside the consent requirement.

Real caveats, stated honestly:

- CNIL's audience-measurement exemption is **French-specific soft law**, not EU-wide, and its framework changes again on 1 Jan 2026.
- The **UK ICO reads this more strictly** with no equivalent carve-out, and its PECR guidance is mid-consultation.
- **"Cookieless" is a marketing claim.** Verify what a candidate script actually does — check for `document.cookie`, `localStorage`, `IndexedDB` and fingerprinting-signal reads — rather than trusting the label.
- A **privacy policy page is required regardless**, even where no consent UI is.
- This research is cross-checked secondary sources, not primary-text legal review. It is not legal advice.

## Implications for Roadmap

Six phases, ordered by dependency and risk.

| # | Phase | Why here |
|---|---|---|
| 1 | **Bulk publish (CLI)** | Everything after it is better verified at real volume. Retires "nothing has ever been rendered at realistic volume." |
| 2 | **Search (metadata)** | Pure backend, no dependency on the landing page. Depends on JUSTICE dedup — a speaker-name search before dedup would surface the exact bug that work closes. |
| 3 | **Landing page + About** | Depends on search existing. Product design is the bottleneck; the Figma exploration is a starting point, not a shortlist. |
| 4 | **Oyez source links** | Small and independent. Data dependency already satisfied by Phase 47's `external_id`. |
| 5 | **Sitemap + robots + page metadata** | Needs the published corpus to exist. |
| 6 | **Analytics + privacy policy** | Deliberately last and isolated — the one item that changes a structural discipline (first client-side script, first `PUBLIC_` env var). |

The data-correctness work already specified in `.planning/notes/justice-identity-and-seeding.md` and `undetermined-speaker-display.md` sequences **before** all of the above; search in particular depends on justice dedup having landed.

## Research Flags

**Needs resolution during planning**

- **Search query strategy** — trigram-only vs. trigram + `tsvector`. Decide before engineering starts (see the disagreement above).
- **Analytics vendor** — an ordinary operator choice. Once picked, inspect the actual script for device storage/access behaviour.
- **`unaccent` on DigitalOcean Managed PostgreSQL** — verify before a migration depends on it.
- **Oyez `external_id` URL format** — spot-check stored values resolve to real Oyez URLs. A verification task, not a build task.

**Standard patterns, no further research needed**

- Bulk publish CLI — mirrors the existing `recompute-trust` precedent
- Sitemap generation — a well-documented SvelteKit pattern

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| Stack | HIGH | Official PostgreSQL / SvelteKit docs, DO's own supported-extensions page. One unverified item (`unaccent`) flagged above. |
| Features | MEDIUM | Cross-checked across 8 comparable archives; no direct usability testing. Anti-features derive from this project's own locked constraints (high confidence) rather than comparative observation. |
| Architecture | HIGH | Every recommendation verified by reading the actual routers, services, schemas and tests. |
| Pitfalls — engineering | HIGH | Grounded in this codebase and its own bug history (BUG-01, the Phase 48 trust gate). |
| Pitfalls — legal/consent | MEDIUM | Cross-checked secondary sources (law-firm summaries of EDPB / CNIL / ICO guidance), not primary text. Genuinely unsettled at the margins. |

## Sources

Full detail, citations and per-claim confidence live in the four research documents this summary consolidates:

- `.planning/research/STACK.md` — versions, index types, DO extension verification, do-not-add list
- `.planning/research/FEATURES.md` — comparable-archive matrix, table stakes / differentiators / anti-features, MVP cut
- `.planning/research/ARCHITECTURE.md` — integration map against real files, build order, leak-ban maintenance
- `.planning/research/PITFALLS.md` — 8 pitfalls with warning signs and prevention, analytics/consent by jurisdiction, pitfall-to-phase mapping

Project-side context that shaped this research and should be read alongside it:

- `.planning/notes/` — justice identity, undetermined speakers, the transcript decision tree, launch readiness
- `.planning/positioning/` — seven documents including `HOMEPAGE-BRIEF.md`, indexed by `README.md`

---
*Synthesised 2026-09-23 for milestone v1.9. Supersedes the v1.2 summary previously at this path.*
