# Feature Research

**Domain:** Public read-only legal-transcript / document archive (non-editorial)
**Researched:** 2026-09-23
**Confidence:** MEDIUM (patterns cross-checked across 8 named comparable archives; no direct usability testing)

**Scope of this file:** the five new v1.9 capabilities — search, landing page, about page, source-linking to Oyez, and public-archive analytics. The chat-format transcript view, term-grouped index, attributions/licensing page, and admin area already exist and are out of scope here.

**Comparable sites examined:** CourtListener / Free Law Project, Oyez.org, HUDOC (European Court of Human Rights case-law database), Old Bailey Proceedings Online, the National Archives Catalog (catalog.archives.gov), Chronicling America (Library of Congress), HathiTrust Digital Library, Digital Public Library of America (DPLA). These span the two closest genres to SCOTUS Chat: verbatim-transcript legal archives (CourtListener, HUDOC, Old Bailey) and large-scale public document/library archives (National Archives, Chronicling America, HathiTrust, DPLA).

## Feature Landscape

### Table Stakes (Readers Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Metadata search (case name, docket, speaker, term) | Every comparable — CourtListener, HUDOC, National Archives Catalog, Chronicling America — lets a reader search by the identifiers they already have, not just browse. HOMEPAGE-BRIEF.md already commits to this exact field set. | LOW–MEDIUM | Postgres `ILIKE`/trigram (`pg_trgm`) or `tsvector` over `case_name`, `source_docket`, `person.display_name`, `term` is sufficient at ~7,800 rows — no external search service needed. |
| Result rows carry disambiguating metadata, not just a title | CourtListener shows case name + citation + docket + court + date on every row; National Archives Catalog shows title + date + level of description; HUDOC shows case name + date + respondent state. A bare case-name list is not enough once multiple arguments share a similar name (reargued cases, consolidated dockets). | LOW | Row needs: case name, docket number(s), term/argued date, and (if the row is a speaker match) which argument the speaker appears in. This project's existing consolidated-docket and reargument schema already carries what's needed — no new data model. |
| Explicit, worded zero-result state (not a blank page) | Chronicling America, HathiTrust, and National Archives Catalog all pair "no results" with a reason or a next step ("check spelling," "try Advanced Search," "browse by X" ) rather than just an empty list. | LOW | See dedicated zero-result section below — this is the one place the OT 1955–2019 boundary has to be said out loud. |
| A visible route into the archive without searching (browse) | Every comparable pairs search with a non-search entry point — DPLA's "Browse by Topic," National Archives' collection browsing, this project's own existing term-grouped `/arguments/term/{year}` listing. | Already shipped | The landing page's job is to surface this existing browse path, not build a new one. |
| Per-item link back to the canonical/upstream source | CourtListener links every opinion to the underlying court document; Old Bailey cites the physical Old Bailey Sessions Papers it digitized; Oyez itself supplies a formatted citation block on every case page. Readers of a *re-presentation* expect a way to reach the thing being re-presented. | LOW (data already captured) | See Source-Linking section — `import_run.external_id` already carries Oyez lineage from Phase 47 (PROV-01–06), so this is populating a link template, not new data collection. |
| A plain About/methodology page | Old Bailey Online's "About This Project" page (methodology, transcription accuracy, known limitations of the source material) and HathiTrust's help/about pages are the norm for any archive presenting digitized/reformatted primary sources — readers of primary-source archives specifically look for "how was this made and how faithful is it." | LOW | Content-only; VOICE.md's "About Copy" and "What This Is / Is Not" blocks are already drafted and just need a page. |
| Basic aggregate traffic measurement | Every comparable institutional archive (National Archives, Library of Congress, HathiTrust) runs some form of aggregate analytics for capacity planning and funder/stakeholder reporting — this is baseline web operations, not a differentiator. | LOW | Cookieless, aggregate-only (Plausible/Fathom/self-hosted Umami-without-tracking-cookie class of tool) fits a public-interest archive; the milestone's own ANALYTICS research thread is resolving the specific consent-law question — this file only confirms the feature class is standard, not exceptional. |

### Differentiators (Not Expected, But Valuable Here)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Search-result snippet showing *which* speaker matched | HUDOC and CourtListener both show *why* a row matched (a highlighted snippet). For a speaker-name search here, showing "Justice Scalia — 41 arguments" or similar on the *search* surface (not a ranking) helps a reader confirm they found the right person before clicking through. | MEDIUM | Only if the speaker-name path returns a person, not just a list of arguments — needs a person-first result type in the search response, and depends on the JUSTICE-phase dedup work landing first so a name maps to one canonical person. |
| Docket-number normalization in search (accepting "552 U.S. 130," "06-1321," "06-1321 " with stray whitespace) | Readers rarely have the exact stored format of a docket string. CourtListener's search tooling normalizes citation formats before matching. | LOW–MEDIUM | Strip/normalize punctuation and whitespace before the `ILIKE`/trigram match; do this in the query layer, not by mutating stored `source_docket` values (which stay immutable per existing constraints). |
| Full-text search inside utterance/transcript text | HathiTrust and CourtListener both offer full-text search across the document body, not just metadata. Readers researching a specific exchange would want this. | HIGH | Explicitly **not** part of the v1.9 scope (the milestone names cases/dockets/speakers/terms only). Flag as a clean, self-contained future phase — a separate `tsvector` index over `utterances.text`, ranked snippets, and highlight rendering are all new surface area with their own apolitical-framing questions (should a search snippet ever look like a "notable quote"?). Do not fold into the v1.9 search work. |
| "Argument not yet in the archive" disambiguation on zero-result | Rather than a generic empty state, detect when a normalized query looks like a real case/date outside 1955–2019 (e.g., a 4-digit year outside range) and surface the coverage-boundary explanation specifically, vs. a generic "check spelling" message for other misses. | MEDIUM | Nice-to-have refinement of the required zero-result copy (see below); the *baseline* zero-result behavior is table stakes, this refinement is optional polish. |

### Anti-Features (Common Elsewhere, Wrong Here)

| Feature | Why It's Common Elsewhere | Why It's Wrong Here | Alternative |
|---------|---------------------------|----------------------|-------------|
| Relevance-ranked search results ordered by a "match quality" or popularity score | Standard on CourtListener (Citegeist relevance engine), HUDOC, and virtually all commercial and legal search products. | Any non-obvious ranking (popularity, "most relevant," click-through weighting) implicitly tells the reader which result matters more — a soft form of editorializing that Principle 4 ("Treat Speakers Equally") and Principle 1 ("Clarify Structure, Not Meaning") both rule out for case-level content. | Sort by an explicit, stated, non-editorial basis only: exact-match first, then alphabetical by case name or chronological by term — same rule the homepage brief already applies to "recent arguments." |
| A "Most Viewed" / "Trending" / "Popular This Month" module fed by analytics data | Common on DPLA, National Archives, and most library/archive homepages — analytics naturally produces this once you're already collecting page views. | This is the single most likely place analytics work accidentally reintroduces an editorial ranking: showing which arguments get the most traffic functions exactly like the "featured"/"notable" labeling HOMEPAGE-BRIEF.md and PRINCIPLES.md explicitly forbid, even though no human curator chose it — the ranking mechanism doesn't matter, the effect does. | Analytics stays internal/operator-facing only (aggregate counts for capacity and interest reporting) and is never rendered as a public "popular" or "trending" list, full stop. |
| An outcome/disposition filter ("affirmed," "reversed," "violation found") | HUDOC lets readers filter by whether a violation was found; most legal-research tools filter by disposition or outcome. | SCDB-style outcome/vote data is already excluded entirely per the apolitical constraint (see PROJECT.md Constraints) — an outcome filter would require exactly the data this project has deliberately chosen not to import. | None needed — search stays scoped to case identity (name/docket/speaker/term), never case result. |
| Prominent "X,XXX arguments" / coverage-count statistics on the landing page | DPLA, National Archives, and HathiTrust all lead with scale ("14+ million objects," etc.) as a trust signal. | HOMEPAGE-BRIEF.md already rules this out explicitly ("format-first, no coverage claim anywhere ... a quiet note that the archive is incomplete") — a prominent count would imply completeness the corpus does not have (OT 1955–2019 only, PDF ingest for other years deferred). This is a place a common convention directly conflicts with the operator's locked positioning. | Keep the existing "quiet note" approach: state the covered range factually when relevant (e.g., in the zero-result state or About page), never as a headline metric. |
| Donation/funding calls-to-action, sponsor logos, or a "meet the team" section on the About page | Standard on nonprofit archive About pages (Free Law Project, StoryCorps) because they're funded orgs soliciting support. | Monetization is explicitly "not a driving goal" (Out of Scope) and there is no team — a single maintainer. Copying this convention would misrepresent the project's structure and violate VOICE.md's "modest" attribute. | About page states plainly that this is a single-maintainer project, per AUDIENCE.md's "Built from one real need, made public in case the same format helps others." |
| User-level analytics: session replay, heatmaps, individual visitor tracking, cross-site pixels | Common on commercial sites and even some public archives that adopt Google Analytics/Hotjar-class tooling by default. | No accounts/no interactivity is a stated hard constraint, and individual-level tracking is a much larger privacy/consent surface than the milestone's own framing assumes ("cookieless tooling may mean no consent UI at all") — bringing in session replay would reopen exactly the consent question the milestone is trying to avoid. | Aggregate, cookieless page-view analytics only (Plausible/Fathom/self-hosted-without-cross-site-ID class of tool) — the milestone's ANALYTICS research thread should confirm the specific tool, this file only flags the tracking-depth boundary. |
| Speaker "profile pages" ranked by number of appearances, argument win/loss record, or "most active advocate" leaderboards | Legal-research products (and some oral-history sites) build these because frequency-of-appearance is an easy, database-native ranking to produce. | Ranking speakers by any metric — including a neutral-seeming one like appearance count — creates an implicit hierarchy of importance among speakers, which Principle 4 forbids regardless of intent. | A speaker-name search result can state factual counts if asked for directly by a search ("14 arguments"), but no standalone ranked leaderboard page. |

## Table-Stakes Deep Dives

### Search: what a result row needs, and what "no results" should say

**Result row contents (cross-checked against CourtListener, HUDOC, National Archives Catalog):**
A result row needs enough to let the reader pick between near-identical hits without opening each one. For SCOTUS Chat, given the existing schema, that's:
- Case name (as displayed on the argument page)
- Docket number(s) — consolidated cases show all associated dockets, matching existing schema support
- Term / argued date
- If the hit is a speaker match rather than a case match: which role the speaker held in that argument (bench/advocate/side), not just the raw name

None of this requires new data collection — it's a read projection over data already captured. It does *not* need: a snippet of transcript text (differentiator, deferred — see Full-text search above), a relevance score, or any status/trust-tier information (trust is operator-only and structurally banned from public responses already, per Phase 48's `test_trust_public_leak_ban.py`).

**Zero-result handling — the one place OT 1955–2019 has to be said explicitly.**
Comparable archives handle genuine non-coverage in one of two ways: (1) a generic "no results, try different terms" message (Chronicling America, HathiTrust) that treats every miss the same regardless of cause, or (2) a targeted explanation when the archive can detect *why* the query missed. This project's coverage gap is unusually easy to detect (a single contiguous date range, 1955–2019) compared to most archives' fuzzier, uneven coverage — so the low-effort baseline and the higher-value refinement are both cheap here:

- **Table stakes (LOW complexity):** every zero-result state names the covered range plainly, once, regardless of query — e.g. "No arguments match this search. This archive currently covers oral arguments from the 1955 through 2019 terms." This satisfies VOICE.md's empty-state guidance ("No arguments match this search") while adding the one fact a reader actually needs to interpret a miss, matching the milestone's own framing ("the one place a reader needs that fact to interpret what they are seeing").
- **Differentiator (MEDIUM complexity):** detect a 4-digit year in the query that falls outside 1955–2019 and surface a more specific line for that case ("Arguments from after 2019 aren't in this archive yet") versus a generic miss (misspelled case name, unmatched docket). This is a refinement, not a requirement — ship the plain baseline first.

Either way, the copy must stay in VOICE.md's register — factual and calm, never apologetic or promotional ("we're working hard to add more!").

### Landing page: already researched, converges with comparables

HOMEPAGE-BRIEF.md already specifies content priority (statement of what the site is → search/browse entry → recent/available arguments → browse by term → format explanation → trust/source note → About). This matches the comparable-archive pattern closely — DPLA and National Archives Catalog both lead with a *browse* entry point before any statistics or mission framing, and neither leads with a coverage-count statistic as its primary hero element (see anti-feature above; DPLA and National Archives both *do* show scale numbers, just not as the lead framing — SCOTUS Chat's stricter "no coverage claim anywhere" is a deliberate, already-made departure from the more common convention, not an oversight). No new landing-page research is needed here beyond confirming this convergence; do not re-derive HOMEPAGE-BRIEF.md's decisions.

### About page: standard contents for a single-maintainer primary-source archive

Cross-checking Old Bailey Online's "About This Project" (methodology, transcription accuracy, source-material limitations), HathiTrust's help/about pages, and nonprofit legal-archive About pages (Free Law Project) against VOICE.md's already-drafted About copy, the standard contents are:
1. What the site is and what it contains (already drafted in VOICE.md's "About Copy" block)
2. What it is *not* (already drafted — "What This Is / Is Not")
3. Where the material comes from and how it's licensed — this project has a real, disclosed complication other archives don't: Oyez-sourced content is CC BY-NC 4.0 (NonCommercial), noted in PROJECT.md Constraints. The About page (or the existing attributions page) is the natural place this gets stated plainly for readers, not just operators.
4. Coverage scope and its boundary (OT 1955–2019, PDF route deferred) — stated as a fact, consistent with the "quiet note" approach used elsewhere, not restated as an apology.
5. Who built it and why — single-maintainer, accessibility-origin framing per AUDIENCE.md, kept modest per Principle 6/7 (no unvalidated accessibility outcome claims).
6. A way to reach the maintainer (feedback/contact), without inviting public contributions — the product is read-only by design, so this should not become a comment system or issue tracker link that implies interactivity.

Complexity: LOW. This is a content page with no new data dependencies — the hard work (deciding what to say) is already done in VOICE.md/PRINCIPLES.md/AUDIENCE.md.

### Source-linking to Oyez

CourtListener, Old Bailey, and Oyez itself all follow the same convention for re-presented primary sources: a per-item link back to the canonical/upstream location, usually near the item's metadata header, worded as "View source" rather than implying the re-presentation supersedes the original (this matches PRINCIPLES.md #2, "Preserve the Source," and VOICE.md's preferred phrasing "View source transcript").

The good news for complexity: Phase 47 (PROV-01–06) already added `external_id` to `import_run` specifically to capture Oyez lineage during corpus import. **This means the data this feature needs already exists in the schema** — the work is building the link template (`oyez.org/cases/{term}/{docket-or-oyez-id}`) and confirming the stored `external_id` format actually matches what Oyez's URL scheme expects, not collecting new data. Complexity: LOW, contingent on that format check. Flag as a verification item (not a research gap) for whoever plans this phase: confirm a sample of `external_id` values resolve to real Oyez case URLs before building the link generically across ~7,800 rows.

Attribution wording should credit Oyez without implying SCOTUS Chat supersedes it, per PRINCIPLES.md #2 ("Copy that implies SCOTUS Chat is the canonical version of the argument" is explicitly listed as something this principle argues against) — "View source transcript on Oyez," not "Original," not "Official record."

### Analytics: table stakes as a category, anti-feature in its most common presentation

The feature *category* (aggregate, privacy-respecting page-view analytics) is standard operational infrastructure on every comparable public archive and is not itself something to research further here — the milestone's ANALYTICS thread is correctly scoped to the legal/consent question, not the feature's existence. What this file adds: the most common *public-facing* consumption of analytics data — a "trending"/"most viewed" module — is the anti-feature called out above, and is worth flagging early because it's the kind of feature that tends to get added later, informally, once the data already exists, well after the apolitical-framing review that would normally catch it.

## Feature Dependencies

```
Search (metadata: case/docket/speaker/term)
    └──requires──> Justice identity dedup (JUSTICE phase)
    │                  (speaker-name search must resolve to one canonical person)
    └──requires──> Corpus published at scale (PUBLISH phase)
    │                  (search must only surface published arguments — reuses
    │                   existing trust/publish gate, no new filtering logic)
    └──enhances──> none new; reuses existing /arguments/term/{year} listing

Source link to Oyez
    └──requires──> import_run.external_id (already shipped, Phase 47 PROV-01–06)
    └──requires──> format verification (Oyez URL scheme vs. stored external_id)

Landing page
    └──requires──> term-grouped /arguments listing (already shipped, Phase 51 DS-04)
    └──enhances──> Search (landing page is the primary entry point to it)

About page ──independent── (content-only, no data dependency)

Analytics ──independent── (infrastructure-only; legal/consent question is the
                            actual dependency, tracked separately by the
                            milestone's own ANALYTICS research thread)

Full-text utterance search (differentiator, deferred)
    └──conflicts with──> apolitical framing until snippet-highlighting rules
                          are explicitly reasoned through (a highlighted
                          "matching" excerpt can read as a featured quote)
```

### Dependency Notes

- **Search requires Justice identity dedup:** a speaker-name search that returns two rows for one Justice (the exact bug the JUSTICE phase is closing) would be a visible, confusing defect on the single most-used search dimension. Sequence search after JUSTICE, not before.
- **Search requires corpus published at scale:** searching a partially-published corpus is fine functionally (the publish gate already filters), but the *value* of shipping search before PUBLISH is low — most searches would miss. No hard technical blocker, but a real ordering argument for the roadmap.
- **Source link requires the Phase 47 external_id work, already done:** this is a rare case where a dependency is already satisfied rather than upcoming — flag it as a verification task, not a build task, so it doesn't get over-scoped.
- **Full-text search conflicts with apolitical framing, not with any existing feature:** including it prematurely would require solving "does a highlighted search snippet count as a featured quote?" (PRINCIPLES.md #1/#4 territory) before any engineering starts. This is exactly the kind of feature PRINCIPLES.md's Decision Test exists for — keep it out of v1.9 and treat it as its own future spec.

## MVP Definition

### Launch With (v1.9, matches milestone scope already set in PROJECT.md)

- [ ] Metadata search: case name, docket number, speaker name, term — essential per HOMEPAGE-BRIEF.md's committed search field set and the milestone's own SITE requirement
- [ ] Zero-result state naming the OT 1955–2019 coverage boundary plainly — essential because this is the one place the range fact changes how a reader interprets what they see
- [ ] Landing page per HOMEPAGE-BRIEF.md's already-decided content priority — essential, already scoped
- [ ] About page covering scope, licensing (Oyez CC BY-NC 4.0), maintainer, and non-goals — essential, content already drafted in VOICE.md
- [ ] Per-argument "View source transcript on Oyez" link — essential per PRINCIPLES.md #2, data dependency already satisfied
- [ ] Aggregate, cookieless page-view analytics (operator-facing only) — essential for basic operational visibility, scoped by the milestone's own consent research

### Add After Validation (later milestone)

- [ ] Docket-number format normalization in search (accepting citation-style/free-form docket entry) — trigger: real search usage shows readers typing docket numbers in a format the raw match misses
- [ ] Query-aware zero-result refinement (detecting an out-of-range year specifically) — trigger: operator wants to reduce ambiguity in the baseline zero-result copy after seeing real search logs

### Future Consideration (v2+ or never, pending an explicit apolitical-framing review)

- [ ] Full-text search across utterance/transcript text — defer until a specific design pass answers how highlighted result snippets avoid reading as "notable quotes"
- [ ] Any public "most viewed"/"trending" surface — do not build without a fresh PRINCIPLES.md review; flagged here specifically so it isn't added informally once analytics data exists

## Feature Prioritization Matrix

| Feature | Reader Value | Implementation Cost | Priority |
|---------|--------------|----------------------|----------|
| Metadata search (case/docket/speaker/term) | HIGH | MEDIUM | P1 |
| Zero-result coverage-boundary message | HIGH | LOW | P1 |
| Landing page | HIGH | MEDIUM (mostly assembly of existing pieces) | P1 |
| About page | MEDIUM | LOW | P1 |
| Source link to Oyez | MEDIUM | LOW (contingent on format verification) | P1 |
| Aggregate analytics | LOW (reader-facing value is indirect) | LOW | P1 |
| Docket normalization | MEDIUM | LOW–MEDIUM | P2 |
| Query-aware zero-result refinement | LOW | MEDIUM | P3 |
| Full-text utterance search | HIGH (for a subset of readers — researchers/legal professionals per AUDIENCE.md) | HIGH | P3, gated on a framing review |
| Public "trending"/"most viewed" | N/A — anti-feature | — | Do not build |

## Comparable-Archive Feature Analysis

| Feature | CourtListener / HUDOC (legal transcript archives) | National Archives / DPLA / HathiTrust (library/document archives) | SCOTUS Chat's approach |
|---------|----------------------------------------------------|----------------------------------------------------------------------|--------------------------|
| Search fields | Case name, citation, docket, judge, court, date, full text | Keyword, date range, person, subject, format | Case name, docket, speaker, term (metadata only — no full text in v1.9) |
| Result ranking | Relevance-scored (Citegeist, HUDOC relevance) | Relevance-scored | Exact-match-first, then alphabetical/chronological — never a relevance score, per apolitical framing |
| Outcome/disposition filter | Yes (HUDOC: violation found/not; CourtListener: precedential status) | N/A | Explicitly excluded — no vote/outcome data is imported at all |
| Landing page scale statistics | Not prominent (legal archives lead with search) | Prominent ("14M+ objects") | Explicitly excluded per HOMEPAGE-BRIEF.md — "no coverage claim anywhere" |
| Source attribution | Direct links to underlying court filings/documents | Rights-statement logos + citation generation per item | "View source transcript on Oyez" per argument, using existing `external_id` lineage |
| About/methodology page | Mission + methodology (Free Law Project is nonprofit-funded, mentions funding) | Methodology + limitations (Old Bailey: OCR/transcription accuracy caveats) | Scope, licensing, maintainer, non-goals — no funding ask (not funded, not monetized) |
| Analytics-driven "trending" module | Not observed on legal archives (would imply case importance) | Common on library/museum archives (DPLA "popular this month") | Explicitly excluded — anti-feature, see above |

## Sources

- [CourtListener — Non-Profit Free Legal Search Engine](https://www.courtlistener.com/) — MEDIUM confidence (cross-checked search-field description against FLP wiki advanced-search docs)
- [FLP Wiki — Advanced Search and Query Techniques](https://wiki.free.law/c/courtlistener/help/search/advanced-search-and-query-techniques) — MEDIUM confidence
- [Oyez case pages and citation format](https://en.wikipedia.org/wiki/Oyez_Project) — LOW confidence (single secondary source; direct Oyez case-page inspection not performed this pass)
- [HUDOC database — European Court of Human Rights](https://www.echr.coe.int/hudoc-database) — MEDIUM confidence
- [HUDOC User Manual](https://www.echr.coe.int/documents/d/echr/HUDOC_Manual_ENG) — MEDIUM confidence
- [Old Bailey Proceedings Online — About This Project](https://www.dhi.ac.uk/blogs/old-bailey/about/) — MEDIUM confidence (methodology/accuracy claims cross-checked against a second academic source)
- [National Archives Catalog — Search Tips](https://www.archives.gov/research/catalog/help/search-tips) — MEDIUM confidence
- [Chronicling America — Search Tips (Library of Congress)](https://guides.loc.gov/chronicling-america/search-tips) — MEDIUM confidence
- [HathiTrust — How to Search & Access](https://www.hathitrust.org/the-collection/search-access/) — MEDIUM confidence
- [DPLA — Announcing the Launch of our New Website](https://dp.la/news/announcing-the-launch-of-our-new-website) — LOW confidence (single vendor/press source on redesign rationale)
- Internal (binding, not re-derived): `.planning/positioning/HOMEPAGE-BRIEF.md`, `.planning/positioning/PRINCIPLES.md`, `.planning/positioning/VOICE.md`, `.planning/positioning/AUDIENCE.md`, `.planning/PROJECT.md` — HIGH confidence, primary source

---
*Feature research for: SCOTUS Chat v1.9 — search, landing page, about page, Oyez source links, public-archive analytics*
*Researched: 2026-09-23*
