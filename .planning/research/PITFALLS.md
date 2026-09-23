# Pitfalls Research — v1.9 "The Site Becomes Complete"

**Domain:** Adding search, a public landing surface, SEO plumbing, privacy-first analytics, and
bulk publishing to an existing, mature, read-only Supreme Court oral-argument archive
(SvelteKit + FastAPI + PostgreSQL, ~7,800 records, single maintainer, non-commercial, CC BY-NC 4.0
sourced content).

**Researched:** 2026-09-23
**Confidence:** MEDIUM overall — HIGH for the engineering pitfalls (search/sitemap/bulk-ops/SEO,
grounded directly in this codebase's actual code), MEDIUM for the analytics/consent legal
research (cross-checked web sources on regulator guidance, but this is not legal advice and the
underlying law is genuinely unsettled at the margins — see the dedicated section below).

---

## Critical Pitfalls

### Pitfall 1: Search re-implements the publish gate and gets it wrong

**What goes wrong:**
Every existing public route in this codebase gates on `resolved_at IS NOT NULL` /
`status == PUBLISHED` (see `BUG-01`, closed in Phase 45: unpublished arguments were briefly
directly reachable via `/arguments/{id}/utterances`). A new search feature is a *second* code
path that must reach the same gated rows through the same filter. If search is built as a fresh
query against `arguments`/`utterances` (e.g. a `LIKE`/full-text index built for speed) rather than
reusing the existing service-layer visibility filter, it is very easy for the WHERE clause on the
search index/query to omit the publish gate — surfacing draft, unpublished, or `UNCERTAIN`-tier
rows (case names, docket numbers, argument text) in result snippets even though the canonical
detail route still 404s them. This is a quieter version of the exact bug BUG-01 already fixed
once: a second door into the same house, unlocked by omission rather than intent.

**Why it happens:**
Search implementations are typically optimized independently (a materialized search index, a
`tsvector` column, a denormalized search table) for performance reasons, and that optimization
step is exactly where the reused-service-layer discipline gets dropped — the fast path is built
against raw tables, and "add the publish filter" is assumed rather than tested.

**How to avoid:**
- Build the search index/query as a *view* or *materialized view* filtered at creation time by
  `status = 'PUBLISHED'` (or by re-running through the existing `get_argument_detail`-style
  service filter), not as an independent index over the raw table.
- If a materialized view is used, its refresh must re-run the same publish predicate every time —
  a stale materialized view that was refreshed once at a moment when a row was published, then
  never refreshed again after that row was unpublished, silently un-gates it forever.
- Reuse the trust/publish domain rule (`api/domain/trust.py`, `argument.status`) — do not
  reimplement "is this visible" as a second boolean anywhere.
- Add a structural test in the same family as the existing apolitical-leak-ban test
  (`api/tests/test_trust_public_leak_ban.py`): assert that no unpublished argument's slug, case
  name, or docket ever appears in a search response body, exercised against a live unpublished
  fixture row, not a source-text grep.

**Warning signs:**
- Search result count differs from `/arguments` listing count for the same term filter.
- A docket number search returns a hit for an argument that 404s when clicked.
- The search backing table/index has no `published_at`/`status` column at all.

**Phase to address:** SEARCH phase (dedicated), verified against the PUBLISH phase's real
7,800-row corpus, not the 4-fixture set.

---

### Pitfall 2: Forgiving matching on legal names produces wrong matches, not just weak ones

**What goes wrong:**
Metadata-only search over case names, docket numbers, and speaker names is tempting to make
"forgiving" — fuzzy matching, stemming, trigram similarity, typo tolerance — because users won't
remember exact docket numbers or exact case-name punctuation (`Bush v. Gore` vs `Bush v Gore`).
But legal identifiers are exactly the domain where forgiving matching produces *wrong* results,
not just noisy ones: docket numbers are dense alphanumeric strings where a single-character edit
distance can land on a *real, different* docket (e.g. `71-1454` vs `71-1554`); consolidated
argument titles often differ from each other by one plaintiff name. A trigram-similarity search
tuned for "did you mean" will confidently return the wrong case as a top hit rather than no hit,
and because this is a legal-transcript archive, a wrong case attributed to a search term reads as
an editorial error, not a UX rough edge — this is exactly the register the apolitical/non-editorial
constraint cares about (identical treatment, no fabricated inference).

**Why it happens:**
Generic search UX advice ("make search forgiving") is written for product catalogs and blog posts
where a near-miss is harmless. It is imported wholesale into domains where identifiers are
load-bearing.

**How to avoid:**
- Split search into two classes with different tolerance: docket numbers and case citations get
  *exact or normalized-exact* matching (strip whitespace/punctuation, case-fold, but no fuzzy
  distance); case names, speaker names, and free-text terms get forgiving matching (trigram/
  full-text).
- Never silently substitute a near-miss as if it were a match — if fuzzy matching is used, the
  result must be visually distinguishable from an exact hit, or excluded from a query that looks
  like a docket number.
- Detect docket-shaped queries (regex on the input) and route them to the exact matcher only.

**Warning signs:**
- A single-digit-different docket returns a confident top-1 result instead of zero/low-confidence.
- QA finds a search for one case surfacing a different, real case as the top hit.

**Phase to address:** SEARCH phase — design the matching-tier split before implementation, not as
a follow-up tuning pass.

---

### Pitfall 3: Deep pagination on ~7,800 rows silently degrades or silently truncates

**What goes wrong:**
Offset-based pagination (`OFFSET n LIMIT 20`) over a term-grouped or relevance-ranked result set
gets slower as `n` grows and, worse, is *unstable* under concurrent data change: if publish state
changes between page loads (a bulk-publish operation adds rows mid-browse, or the >50%-undetermined
gate holds some rows back and then releases them later), a reader paging through results can see
the same row twice or skip a row entirely, because offset pagination has no fixed anchor. At 7,800
rows this is not a performance emergency, but the correctness bug (duplicate/skipped result) is
real and will reproduce during the PUBLISH phase's bulk rollout, when publish state is actively
changing while search is live.

**Why it happens:**
Offset pagination is the default in every ORM tutorial and is fine for browsing (`/arguments`
already does this) but is invisibly wrong specifically when combined with concurrent writes,
which is exactly the situation this milestone creates (bulk publish running against a site that
may already be receiving search traffic).

**How to avoid:**
- Use keyset/cursor pagination (`WHERE (rank, id) < (last_rank, last_id) ORDER BY rank, id LIMIT n`)
  for search results, anchored on a stable tiebreaker column (`id`), not offset.
- If offset pagination is kept for simplicity (defensible at this corpus size), cap the maximum
  page depth and provide a "refine your search" prompt past that depth rather than paging forever
  through 390 pages of results.
- Do not run bulk publish and expose search to real traffic in overlapping windows without this
  fixed — or accept the small window and document it.

**Warning signs:**
- A result set's total count changes between page 1 and page 5 of the same query.
- QA reproduces a duplicate or missing row by paging during a bulk-publish dry run.

**Phase to address:** SEARCH phase for the pagination mechanism; PUBLISH phase for the
non-overlap-or-documented-risk decision about running bulk publish concurrently with public
search traffic.

---

### Pitfall 4: Bulk publish reuses the one-row `publish_argument` function unmodified and it is far slower and less safe at scale than it looks

**What goes wrong:**
`api/services/admin_arguments.py::publish_argument` is deliberately single-row: per call it does a
`SELECT` for the argument, a full `recompute_argument_tier` (which itself queries utterances and
participants), a conditional `ArgumentStatusLog` insert, and `await db.commit()`. This is correct
and necessary for the one-at-a-time admin UI flow it was built for. Calling it in a loop 7,800
times — the obvious first implementation of "bulk publish" — means 7,800 individual transactions,
7,800 individual trust-tier recomputations (each walking that argument's utterances/participants),
and 7,800 round trips to Postgres. On Digital Ocean's managed Postgres behind PgBouncer
(transaction-mode pooling, already a known constraint in this stack — see the
`statement_cache_size=0` requirement), this is exactly the pattern that starves the connection
pool: 7,800 sequential short transactions each acquiring and releasing a pooled connection, with
no batching, is far slower than it needs to be and will look like a hang rather than a bulk
operation, with no visible progress and no obvious place to resume if it dies partway.

**Why it happens:**
The existing function is correct and already tested; the path of least resistance is "call it in
a for loop," and for a few hundred rows that would even work adequately. At 7,800 rows the same
approach crosses from "slow" to "operationally risky" — a multi-hour job with no checkpoint is a
job nobody can safely interrupt or resume.

**How to avoid:**
- Do not call the single-row service function unmodified in a loop for the full corpus. Instead:
  - Batch trust-tier recomputation: `recompute-trust` already exists as an offline drift-repair
    CLI (Phase 48) — extend or reuse that pattern (bulk read, bulk compute, bulk write) rather than
    re-deriving tier logic inline in a new bulk-publish script.
  - Chunk the commit boundary: commit every N rows (e.g. 100–500), not once per row and not once
    for all 7,800 — a single all-7,800-row transaction risks a huge, long-held lock and an
    all-or-nothing failure mode; per-row commits risk 7,800 round trips.
  - Make the operation resumable by construction: process `WHERE status != 'PUBLISHED' AND
    resolved_at IS NOT NULL ORDER BY id`, and re-running the same command after a partial failure
    must be a no-op for already-published rows (already true of `publish_argument`'s "already
    published" guard) and simply continue from wherever it stopped — no separate "resume from
    checkpoint N" bookkeeping table needed if the query itself is idempotent on `status`.
  - Log per-row outcome (published / skipped-gated / skipped-already-published / errored) to
    either `argument_status_log` (already the audit trail for publish transitions) or a
    run-scoped log file, so a partial run's exact stopping point and failure set is inspectable
    without re-running the whole corpus to find out what happened.
- Decide up front what happens to the ~6 held-back >50%-undetermined arguments and any argument
  still at `resolved_at IS NULL` — the bulk tool should report them as a distinct "not eligible"
  category, not silently skip them indistinguishably from "already published."

**Warning signs:**
- The bulk-publish script has no `--dry-run` or count-only mode to preview what it would do.
- There is no way to answer "how far did it get" after an interrupted run except re-scanning the
  whole `arguments` table.
- Local testing was only ever done against the 4-fixture set — the first real test at 7,800 rows
  is the actual production run.

**Phase to address:** PUBLISH phase. This is the phase's core engineering risk and should be
planned and load-tested (against a full-size dev seed, not fixtures) before it is run against the
real corpus.

---

### Pitfall 5: Sitemap generated from the same query path as search, inheriting the same gating bug — or generated once and never refreshed

**What goes wrong:**
Two distinct failure modes, both plausible here:
1. **Leaks unpublished URLs.** If the sitemap generator queries `arguments` without the publish
   filter (same root cause as Pitfall 1), it emits `<loc>` entries for draft/unpublished/held-back
   arguments. Google will crawl and may index them even though the live page 404s or later
   changes — producing "soft 404" warnings in Search Console and, worse, a brief window where a
   draft case's docket/title is indexed and appears in search results before the argument is ever
   actually published.
2. **Goes stale after bulk publish.** If the sitemap is generated once (e.g. a build-time static
   file) rather than at request time or via a scheduled regeneration, it will not reflect the
   ~7,800 rows that PUBLISH adds — a reader arriving via a search engine indexed from a sitemap
   generated before the bulk publish ran will find a 404 for a case that now exists, and pages
   published after sitemap generation will simply never be discovered by crawlers relying on it.

**Why it happens:**
Sitemaps are often treated as a one-time "add robots.txt and sitemap.xml" checklist item rather
than as a live view over the same gated dataset every other public route uses — especially
tempting here because the archive is framed as "static" (1955–2019, doesn't change often), which
is true of the *content* but not true of the *publish rollout* happening in this same milestone.

**How to avoid:**
- Generate the sitemap dynamically from a request-time (or cache-with-short-TTL) query using the
  identical publish predicate as the public listing route — not a separate script, not a static
  file checked into the repo.
- Regenerate (or re-serve dynamically) after the PUBLISH phase's bulk operation completes; do not
  ship the sitemap before the corpus is actually published, or the two phases will interact badly
  in whichever order they land.
- Respect the protocol limits precisely: **50,000 URLs and 50MB uncompressed per sitemap file**
  (sitemaps.org protocol, cross-confirmed across multiple sources). At ~7,800 arguments plus a
  handful of static pages, this project is nowhere near the limit and does **not** need a sitemap
  index — a single `sitemap.xml` is correct. Do not build unneeded index-file complexity, but do
  not hardcode an assumption that stays true forever without a bounds check either (a future
  PDF-route expansion past 2019 could eventually approach relevant scale — cheap to note, cheap to
  ignore for now).
- Set `<lastmod>` to the argument's actual `published_at` (or last content-affecting edit
  timestamp) and only change it when something genuinely changed — do not stamp every entry with
  "now" on every regeneration. An archive whose `lastmod` values never move after initial publish
  is a legitimate and correctly-read signal to a crawler that the content is stable; an archive
  that reports a fresh `lastmod` on every crawl for content that never changed teaches the crawler
  to distrust the signal and may reduce re-crawl priority for genuinely updated pages later.

**Warning signs:**
- Sitemap URL count doesn't match the published-argument count.
- Search Console reports "submitted URL not found (404)" for archive pages.
- `lastmod` values are identical across the whole sitemap and equal to "today" on every deploy.

**Phase to address:** PLUMBING phase for the mechanism (dynamic generation, correct predicate,
protocol conformance); sequence PLUMBING's sitemap work *after* PUBLISH completes, or make the
sitemap query robust to either ordering (it should be, if built correctly on the live table).

---

### Pitfall 6: A perpetually unchanging archive undersells itself to search engines if every page looks the same

**What goes wrong:**
~7,800 pages that share a nearly identical DOM structure (same layout, same component tree, same
"Argued [date] — Docket [n]" boilerplate) with the differentiating content buried in chat
transcript text is a classic thin/duplicate-template pattern from a crawler's perspective. Search
engines that see thousands of pages with near-identical templated boilerplate and only a small
proportion of unique text (case names, a handful of doctrinally similar phrases, etc.) can
deprioritize crawling/indexing the long tail of the set — this is the same dynamic that affects
large product catalogs and directory sites. Since the corpus stops at 2019 and never grows in the
way a normal content site does (no fresh content signal, no incoming links accumulating over
time), there is no organic momentum pulling crawlers back to revisit; the entire discovery burden
sits on the sitemap plus internal links.

**Why it happens:**
The team is reasonably focused on making sure each page is *correct* (right speakers, right
transcript), not on the fact that at archive scale, "correct but templated" pages compete with
each other for a limited, shared amount of crawl and index attention.

**How to avoid:**
- Ensure per-page metadata (title, meta description, structured data if added later) is genuinely
  distinct per argument — case name + docket + term, not a generic template string repeated
  7,800 times with only the case name swapped in an otherwise-identical sentence.
- Strengthen internal linking: the term-grouped listing (`/arguments/term/{year}`) already
  provides one crawl path; ensure every argument is reachable by at least one other internal link
  besides the sitemap (e.g. cross-links between a case's re-arguments, links from the About/source
  pages) so PageRank-style discovery doesn't depend on the sitemap alone.
- Do not seek to fabricate uniqueness (topic tags, summaries) — that would violate the apolitical/
  non-editorial constraint. The legitimate lever here is structural (linking, metadata) not
  editorial (content generation).
- Set realistic expectations: full, fast indexing of all 7,800 pages simultaneously is not a
  reasonable target for a new site with no existing authority — plan for indexation to happen
  gradually and treat "search console shows most pages indexed within weeks, not days" as the
  normal case, not a bug to fix.

**Warning signs:**
- Search Console's "Crawled — currently not indexed" bucket grows and stays large weeks after
  submission.
- Only a small, static subset of pages ever accumulates any search impressions.

**Phase to address:** SITE/PLUMBING phase for per-page metadata distinctness and internal linking;
this is a "set correctly and move on," not an ongoing SEO campaign — appropriate for a
single-maintainer, non-commercial project.

---

### Pitfall 7: Bulk publish and the >50%-undetermined gate interact through the same trust-tier machinery — running one without re-verifying the other reintroduces a gap already closed once

**What goes wrong:**
`publish_argument` recomputes trust tier fresh at publish time specifically so the gate reads
current constituents rather than a stale stored value (Phase 48 D-14/D-20). A bulk operation that
bypasses this function (e.g. a raw `UPDATE arguments SET status = 'PUBLISHED'` for speed, or a
naive reimplementation that skips the recompute step to go faster) would silently readmit the
UNCERTAIN-tier / >50%-undetermined publish gate that Phase 48 and the SPEAKER work in this
milestone deliberately built. This is the single highest-consequence mistake available in this
phase: it would let one of the six held-back arguments — or any argument whose tier changes
between "resolved" and "publish time" — through the gate that exists specifically to prevent that.

**Why it happens:**
Performance pressure (Pitfall 4) pushes toward bypassing the slow, correct single-row function;
the shortest path to "fast" is exactly the path that removes the gate.

**How to avoid:**
- Whatever bulk mechanism is built, it must call the same `derive_tier`/gate logic per row (even
  if batched for performance) — never a raw bulk `UPDATE` on `status`/`published_at` that skips
  tier evaluation.
- Add an explicit test: after bulk publish, assert zero published arguments have `trust_tier ==
  UNCERTAIN` and zero have `>50%` undetermined utterances, run against the real corpus count, not
  the fixture set.
- Treat "override an UNCERTAIN gate for one of the 7,800 in bulk" as almost certainly a "should not
  happen" case; if the bulk tool has to override anything, that is a signal to stop and inspect
  those rows individually (small number, per the launch-readiness inventory: 6 held back), not to
  build a bulk-override capability.

**Warning signs:**
- The bulk tool's code path never calls `recompute_argument_tier` or an equivalent.
- No post-run assertion checks tier distribution among newly-published rows.

**Phase to address:** PUBLISH phase, and it should be the first thing verified once bulk publish
runs, before any other launch-readiness item is checked off.

---

## Analytics & Consent: what the law actually triggers

**This section is research, not legal advice.** It identifies what regulators and the underlying
directive/regulation text say, cross-checked across multiple secondary sources (law-firm summaries
of primary EDPB/CNIL/ICO material), and is explicit about where the law is unsettled or
jurisdiction-specific. Confidence: MEDIUM (cross-checked web sources, not primary-text review; not
reviewed by counsel).

### The operator's hypothesis, evaluated

**Hypothesis:** the consent trigger under ePrivacy/GDPR is *reading or writing to the visitor's
device*, not analytics as such — so genuinely cookieless analytics may need no consent UI.

**Verdict: substantially correct for the EU ePrivacy framework, with real caveats, and it does not
travel unchanged to every jurisdiction a public archive's visitors come from.**

- **EU — ePrivacy Directive Art. 5(3):** the trigger is explicitly "storing information, or
  gaining access to information already stored, in the terminal equipment of a subscriber or
  user" — not whether the data collected is personal data, and not "analytics" as a named category.
  The EDPB's October 2024 guidelines (cross-confirmed across Hunton, Lexology, Stevens & Bolton,
  Fieldfisher, DLA Piper, and Kluwer/Inside Privacy summaries) confirm this reading is deliberately
  broad: it applies regardless of whether personal data is involved, and it extends beyond
  classic cookies to other client-side techniques that read or write device state (local storage,
  certain fingerprinting-adjacent techniques, tracking pixels that trigger a device-side write).
  **The operator's hypothesis about the trigger is right.** The caveat: "cookieless" is not
  automatically synonymous with "no storage or access at all." A tool only avoids Art. 5(3)
  entirely if it truly never reads from or writes to the device via client-side APIs — reading
  data the browser sends anyway as part of the ordinary HTTP request (User-Agent header, Referer,
  truncated/hashed IP address at the server) is a materially different act from a script actively
  querying `localStorage`, `IndexedDB`, canvas/battery/font-enumeration signals, or setting any
  persistent identifier. Verify any specific analytics vendor's *actual* client-side behavior
  against this distinction — do not take a vendor's "cookieless" marketing claim as dispositive of
  the ePrivacy question without checking what its script does.
- **France — CNIL Sheet 16 (revised 4 July 2025, self-assessment framework effective 1 Jan 2026):**
  CNIL has an explicit, named exemption from consent for audience-measurement trackers, but it is
  *conditional*, not a blanket "analytics never needs consent" rule: exempt only if used strictly
  for the site's own internal technical/performance measurement, producing anonymous aggregate
  data, never combined with other data sources, never enabling cross-site tracking, and only if
  users are informed (privacy policy disclosure required even though a banner is not). This is a
  **French national regulator's soft-law position**, not EU-wide binding law — other member states'
  data protection authorities are not bound by CNIL's specific exemption criteria, even though
  several apply a similar spirit informally.
- **UK — ICO / PECR:** materially stricter on this exact question. ICO guidance treats analytics
  cookies (explicitly including Google Analytics) as requiring active opt-in consent, and reads the
  "strictly necessary" exemption narrowly enough to exclude analytics entirely — there is no
  UK equivalent of CNIL's audience-measurement carve-out currently in force (guidance updates were
  under consultation through 2025 into 2026, so this is a moving target, not settled ground).
  **A cookieless-and-CNIL-exempt design plan for France does not automatically satisfy the ICO's
  reading for UK visitors** — if the ePrivacy-scope argument (no storage/access at all, not merely
  "no cookie") holds for a given tool, the UK question resolves the same way EU-wide because the
  UK's PECR mirrors the same "storage or access" trigger; but a strategy that only relies on
  CNIL's audience-measurement exemption (as opposed to genuinely falling outside Art. 5(3)/PECR
  scope altogether) will not transfer to a UK reading.
- **US — CCPA/CPRA (California; other state analogs are similar in shape):** a fundamentally
  different regime — opt-out, not opt-in. There is no requirement to obtain prior consent before
  running analytics; the obligation is a *right to opt out* of "sale" or "sharing" of personal
  information, plus Notice-at-Collection and Global Privacy Control (GPC) recognition. The
  practical trap here is specific: sending data to a third-party analytics vendor whose own terms
  let it use that data for its own purposes (the fact pattern several 2023–2025 US enforcement
  actions and class actions have targeted around default Google Analytics configurations) can be
  characterized as "sharing" for cross-context behavioral advertising purposes even without any EU
  cookie-consent framing — a separate US-specific risk that a "no EU cookie banner needed" analysis
  does not address. A genuinely self-hosted/first-party tool that sends nothing to a third party
  and sets no persistent identifier avoids this fact pattern entirely.
- **Does non-commercial / CC BY-NC framing change the analysis?** Not for the ePrivacy/GDPR/PECR
  consent-trigger question — those regimes are indifferent to whether the site is commercial; the
  trigger is the technical act (storage/access to a device) or, for CCPA, thresholds tied to
  revenue/data-volume/data-sale that a small non-commercial single-maintainer site is very unlikely
  to meet in the first place (CCPA has applicability thresholds — a low-traffic, non-commercial,
  non-selling site plausibly falls outside CCPA's *applicability* entirely, which is a different
  and stronger position than merely being exempt from *cookie consent* specifically). This is
  worth flagging to the operator as a distinct, favorable fact, but confirming CCPA applicability
  thresholds against actual traffic/revenue figures is a fact-specific legal question, not
  something this research can settle.

### Recommended approach, stated as engineering requirements (not legal conclusions)

1. Choose a tool that is verifiably cookieless in the strict sense: no `document.cookie` writes,
   no `localStorage`/`IndexedDB` use, no client-side fingerprinting signals read, no persistent
   identifier of any kind — verify this by reading the tool's actual script (or self-hosting it),
   not by trusting a "GDPR-compliant" badge.
2. Prefer self-hosted or otherwise first-party-only data flow (no third-party sub-processor
   receiving raw request data) to avoid the separate US "sharing" framing entirely, independent of
   the EU cookie question.
3. Ship a privacy policy page regardless — CNIL's exemption still requires *disclosure*, and a
   public, non-commercial, US-based site with any EU/UK visitors benefits from stating plainly what
   is and is not collected, even where no consent *action* is legally compelled.
4. Do not build a cookie-consent banner UI speculatively "to be safe" if the chosen tool is
   genuinely storage/access-free — that is over-building a UI surface the operator explicitly
   wants to avoid absent a real requirement, and it re-adds exactly the friction the milestone's
   framing is trying to avoid.
5. Do build the technical ability to gate the analytics *script itself* on a future consent signal
   (a feature flag / config toggle at the very least) so if the tool choice or legal reading
   changes later, a consent gate can be added without a rearchitecture — cheap insurance, not a
   present-day requirement.
6. This determination should be treated as provisional and revisited if the operator later adds
   any third-party ad tech, cross-site tracking, or a paid/commercial tier — all of which would
   change the analysis materially.
7. **This is not legal advice.** Any launch decision resting on this reading is worth a
   light-touch confirmation from someone qualified, given the genuinely unsettled areas above
   (UK PECR guidance is mid-consultation as of this research; CNIL's own framework changes
   again 1 Jan 2026).

**Sources (see also stored research-store digests, keys logged during this research pass):**
EDPB guidelines on the technical scope of ePrivacy Art. 5(3) (adopted 7 Oct 2024), summarized by
Hunton Andrews Kurth, Lexology/Stevens & Bolton, Fieldfisher, DLA Piper (Privacy Matters),
McDermott Will & Emery, and Covington (Inside Privacy); CNIL "Sheet 16: Use analytics on your
websites and applications" (cnil.fr, revised 4 Jul 2025); ICO PECR guidance on cookies and similar
technologies (ico.org.uk), and 2025–2026 update commentary (CookieYes, Usercentrics, Clifford
Chance, LexisNexis UK); Plausible Analytics' own published legal-assessment blog post and its
own GitHub discussion #1963 acknowledging the ePrivacy-scope debate is not fully closed; general
CCPA/CPRA cookie-consent-requirement summaries (Osano, Usercentrics, CookieChimp) for the US
opt-out contrast.

---

## Pitfall 8: Accessibility was never measured, and five phases have touched the UI since the waiver

**What goes wrong:**
The Phase 04 waiver (`04-VERIFICATION.md` overrides block, 2026-08-18) asserted accessibility
without measurement, and Phases 14, 38, 39, 45, and 51 have all changed the relevant UI since —
including Phase 51's full CSS-token rewrite (Tailwind removal), which is exactly the kind of change
that can silently regress color contrast (new custom-property values may not hit 4.5:1),
interactive-element focus styles, and touch-target sizing, none of which were re-verified as part
of that phase's own scope. Launching without measurement means the most likely real-world failures
are: color contrast regressions from the token rewrite, keyboard-focus traps or invisible focus
rings on the new `lib/primitives` component library (Button/Badge/Card/Input), and the new search/
landing/about surfaces (built in this exact milestone, so they have *never* been checked against
anything) inheriting whatever the untested baseline already has.

**Why it happens:**
Accessibility audits are usually deferred because they feel like a distinct, specialist workstream
gated behind a whole extra tool/process (axe-core, WAVE, screen-reader walkthrough) rather than a
cheap check that can run inside the existing test suite.

**How to avoid (cheapest mitigations, given the audit is explicitly out of scope this milestone):**
- Add an automated axe-core assertion inside an existing browser test (Playwright is already
  proven working in this environment per prior session notes) against at least one representative
  argument page, the new landing page, the new search results page, and the new About page. This
  is the single cheapest, highest-value action available: it does not require a human audit, it
  catches the mechanical class of defects (contrast, missing labels, missing alt text, ARIA misuse)
  automatically, and it runs in CI going forward so future UI phases cannot regress silently again.
- Specifically re-check color contrast on the Phase 51 token set's new semantic colors — this is a
  concrete, bounded, cheap check (a script or test asserting each foreground/background pairing in
  the token set computes to ≥4.5:1) rather than a full manual audit.
- Verify keyboard reachability and visible focus state on every new interactive element this
  milestone adds (search input, search result links, any consent/analytics-adjacent control if one
  ends up shipping) — a manual pass with Tab/Shift-Tab, not a formal audit.
- Do not silently expand the waiver's scope: the original waiver covered the argument view as it
  existed 2026-08-18. New surfaces built in this milestone (search, landing, About) were never
  covered by that waiver and are not "already accepted risk" — they need at least the axe-core
  pass, or an explicit fresh waiver decision from the operator, not an assumed inherited pass.

**Warning signs:**
- No axe-core or equivalent check exists anywhere in the test suite by the end of this milestone.
- The new landing/search/About pages ship with no keyboard-navigation pass at all.
- A contrast regression is only found by eye, post-launch, rather than by an assertion.

**Phase to address:** Add a lightweight axe-core browser-test check as part of the SITE phase (when
landing/search/About ship) rather than waiting for a dedicated accessibility phase that this
milestone has explicitly deferred — this converts "unmeasured" into "measured for the cheap,
mechanical class of defects," which is the realistic bar given the audit itself is out of scope.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|-----------------|
| Loop over `publish_argument` for bulk publish | Zero new code, reuses tested function | Multi-hour run, no resume point, PgBouncer connection-pool pressure | Never at 7,800 rows — acceptable only for the existing single-row admin-UI use case it was built for |
| Static/build-time sitemap.xml checked into repo | Simple, no server logic | Goes stale the moment PUBLISH runs or any argument's publish state changes | Never, given this milestone bulk-publishes the whole corpus in the same window |
| Fuzzy/trigram matching applied uniformly to all search fields including docket numbers | Simpler implementation, one query path | Wrong-match results on legal identifiers read as editorial error | Never for docket/citation fields; fine for case-name/speaker free text |
| Speculative cookie-consent banner "to be safe" without confirming the chosen tool actually needs one | Feels conservative | Reintroduces exactly the UX friction this milestone is trying to avoid, for no legal requirement | Only if the chosen analytics tool cannot be verified as storage/access-free |
| Offset pagination for search results | Simplest to implement, matches existing `/arguments` listing pattern | Duplicate/skipped rows under concurrent publish-state changes at depth | Acceptable if PUBLISH's bulk operation is fully complete and search isn't exposed to live traffic during any future bulk operation |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-------------------|
| Postgres full-text search (`tsvector`/`GIN`) | Building the index over the raw `arguments`/`utterances` table without the publish predicate | Index a filtered view or maintain the predicate in the query, never the raw table alone |
| DO managed Postgres + PgBouncer (transaction mode) | Bulk operation opens/closes a connection per row via the ORM's default session lifecycle | Batch commits (chunked, not per-row and not all-7,800-at-once); reuse a single session across a chunk |
| Third-party analytics vendor | Trusting a "GDPR-compliant"/"cookieless" marketing claim without checking what the script actually reads/writes on the device | Inspect (or self-host) the actual script; verify no `document.cookie`, `localStorage`, `IndexedDB`, or fingerprinting-signal reads before relying on a no-consent-needed design |
| Oyez source links (CC BY-NC 4.0) | Linking to Oyez without the required attribution string near the link, or implying the site authored the transcript | Every Oyez-sourced link/page carries visible attribution per the existing Attributions page pattern already in the codebase (`/attributions`) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Client-side roster/derived computation pattern (existing `$derived.by()` roster pattern) applied to full-corpus search results | Slow initial page render if search result assembly is pushed to the client | Do result ranking/filtering server-side; ship only the current page's rows to the client | Noticeable above a few hundred results rendered per request, well below the corpus size |
| `recompute_argument_tier` called once per row in a naive bulk loop | Bulk publish takes hours instead of minutes | Batch-read utterances/participants per chunk of arguments rather than per single argument | Becomes painful anywhere north of a few hundred rows; certain at 7,800 |
| Sitemap query without an index on the publish-predicate columns | Sitemap generation request times out or is slow at 7,800+ rows | Ensure `status`/`published_at` are indexed (likely already true given existing listing queries filter on them) | Only a risk if a new ad hoc query bypasses the existing indexed access pattern |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Search index/materialized view built from a one-time snapshot that includes now-unpublished rows | Unpublished/incomplete argument content (case name, docket, transcript snippets) exposed publicly indefinitely | Re-derive the search index from the live gated query on every refresh; never treat a snapshot as permanently safe |
| Sitemap or search API responses leaking `trust_tier` or `review_state` fields by including the full ORM object instead of a public schema | Operator-only trust metadata reaches a public response, violating the structural ban already enforced elsewhere (`test_trust_public_leak_ban.py`) | Extend that same structural test class to cover the new search response schema explicitly |
| Analytics script sourced from an unvetted third-party CDN | Supply-chain risk (a compromised third-party script can read/write anything client-side, including exactly the storage/access behavior this milestone is trying to avoid needing consent for) | Self-host the analytics script, or pin/verify subresource integrity if loaded externally |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Search returns zero results for any post-2019 term with no explanation | Reader concludes the archive is broken or incomplete for no stated reason | Empty-results state explicitly explains the OT 1955–2019 range (already scoped as a requirement — keep it prominent, not a footnote) |
| Fuzzy search "corrects" a docket number to a different real case silently | Reader is shown wrong content believing it's what they searched for | Never silently substitute; show "no exact match" plus clearly-labeled suggestions instead |
| Deep search pagination with no visible "you've reached the end" or result-count context | Reader can't tell if they've seen everything or if the list is broken | Show total result count and current position; cap or clearly bound pagination depth |

## "Looks Done But Isn't" Checklist

- [ ] **Search:** Often missing the publish-state filter on the index/query itself, not just on
      the UI's result-click-through — verify by searching for a term unique to a known unpublished
      or held-back fixture row and confirming zero hits.
- [ ] **Sitemap:** Often generated once and forgotten — verify by re-running the generator after a
      bulk-publish dry run and diffing the URL count against the actual published-row count.
- [ ] **Bulk publish:** Often "done" after a successful run against the 4-fixture set only — verify
      by running against a full-size (or realistically large, e.g. thousands of rows) seeded dev
      database before the real corpus, and verify it is safely re-runnable after a simulated
      mid-run failure (kill the process partway, re-run, confirm no duplicate log rows / no
      double-charged side effects).
- [ ] **Analytics/consent:** Often "done" once a tool is picked, without verifying what that tool's
      script actually does on the device — verify by reading the shipped script (or its published
      source if self-hosted) for any `document.cookie`, `localStorage`, or `IndexedDB` use.
- [ ] **Accessibility:** Often asserted from a stale waiver — verify by running an automated
      axe-core pass against every *new* public page this milestone adds, not just the
      previously-waived argument view.
- [ ] **Sitemap/robots.txt pairing:** Often robots.txt is added without actually referencing the
      sitemap's URL, or disallows a path the sitemap still lists — verify the two files agree.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|-----------------|
| Search leaks unpublished rows | LOW | Add the missing predicate, rebuild/refresh the index; audit logs for any external crawler that indexed the leaked content and consider a `noindex` + removal request if it was already crawled |
| Bulk publish partially fails mid-run | LOW, if built resumably as recommended | Re-run the same idempotent command; it picks up remaining `resolved_at IS NOT NULL AND status != 'PUBLISHED'` rows |
| Bulk publish built non-resumably and fails mid-run | MEDIUM–HIGH | Manually diff `argument_status_log` against the full corpus to find which rows completed, then targeted re-run per missing row — exactly the operational cost the resumability design in Pitfall 4 is meant to avoid |
| Sitemap goes stale after bulk publish | LOW | Regenerate/re-trigger; resubmit in Search Console if needed to accelerate re-crawl |
| Analytics tool turns out to trigger consent after all (later legal reading changes, or the script does more than assumed) | LOW, if the config-toggle insurance from the Analytics section was built | Flip the toggle to gate the script behind a minimal consent action; no rearchitecture needed |
| Accessibility axe-core pass finds contrast failures in the Phase 51 token set | LOW–MEDIUM | Adjust the specific failing semantic token values; token-based design means a fix is centralized, not scattered across components |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Search leaks unpublished records | SEARCH | Structural test proving zero unpublished-row leakage, run against a live unpublished fixture |
| Forgiving matching produces wrong docket/case matches | SEARCH | Manual test cases: single-character docket variants must not return confident false hits |
| Deep pagination duplicate/skip under concurrent publish changes | SEARCH | Keyset pagination implemented, or documented non-overlap with PUBLISH's bulk window |
| Bulk publish is slow, unsafe, non-resumable | PUBLISH | Dry run against a large (thousands-of-rows) seeded dev DB; kill-and-resume test |
| Bulk publish bypasses the trust-tier gate | PUBLISH | Post-run assertion: zero UNCERTAIN-tier or >50%-undetermined rows among newly published |
| Sitemap leaks unpublished URLs or goes stale | PLUMBING (sequenced after or robust to PUBLISH) | URL count matches published-row count; re-verified after any future bulk operation |
| Archive undersells itself to crawlers (templated pages) | SITE / PLUMBING | Per-page metadata distinctness spot-checked; internal linking beyond the sitemap confirmed |
| Analytics/consent mismatch (banner over- or under-built) | ANALYTICS | Chosen tool's script inspected for storage/device-access behavior; privacy policy page shipped regardless; config toggle for future consent gate exists |
| Accessibility unmeasured on new + changed UI | SITE (as the new surfaces ship) | Automated axe-core pass added to the test suite covering landing/search/About/argument pages |

## Sources

- Direct codebase inspection: `api/services/admin_arguments.py::publish_argument` (single-row,
  per-call commit + trust recompute), `api/schemas/admin_arguments.py` (trust_tier admin-only
  comments), `api/tests/test_trust_public_leak_ban.py` pattern, route tree under `app/src/routes`
  (confirms no search implementation exists yet), Phase 45/48 fix history in `.planning/PROJECT.md`
  (BUG-01 unpublished-argument leak, trust-tier gating design).
- `.planning/notes/launch-readiness.md` — verified gaps (no sitemap, no robots.txt, no search, no
  bulk publish path, 6 of 7,817 held back, accessibility waiver and its staleness).
- sitemaps.org protocol and FAQ (50,000 URL / 50MB limit, sitemap index mechanics) — cross-checked
  across Screaming Frog, CrawlSense, Bing Webmaster Blog, and Wikipedia summaries.
- General SEO crawl-budget guidance on large/static archive sites (multiple SEO-industry sources,
  consistent on the `lastmod`-accuracy and per-sitemap-segmentation points).
- EDPB, CNIL, and ICO consent-scope research — see the dedicated Analytics & Consent section above
  for the full citation list; MEDIUM confidence, cross-checked secondary sources, not primary-text
  or counsel review.
- Prior-session memory notes (`Playwright MCP is the missing browser`, `Svelte $state proxy vs grep
  contract tests`) — informed the accessibility mitigation recommendation (automated browser-test
  axe-core check is feasible in this environment) and the caution against source-text-only
  verification for frontend behavior.

---
*Pitfalls research for: SCOTUS Chat v1.9 — search, landing/About, SEO plumbing, analytics/consent,
bulk publish*
*Researched: 2026-09-23*
