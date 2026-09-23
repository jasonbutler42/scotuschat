# Requirements: SCOTUS Chat — v1.9 The Site Becomes Complete

**Defined:** 2026-09-23
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

**Milestone goal:** Make everything true that has to be true before the site can go live — correct data, the full corpus published, and a finished public surface — so that v2.0 is purely the deployment.

**Design basis already on disk (do not re-derive):** `.planning/notes/justice-identity-and-seeding.md`, `undetermined-speaker-display.md`, `transcript-rendering-decision-tree.md`, `launch-readiness.md`; `.planning/positioning/` (seven documents, indexed by `README.md`); `.planning/research/SUMMARY.md` and its four source documents.

## v1 Requirements

Requirements for milestone v1.9. Each maps to exactly one roadmap phase.

### Justice Identity (JUSTICE)

- [ ] **JUSTICE-01**: A verified per-justice mapping joins the CSV tenure data to the corpus by `oyez_speaker_id`, covering all 114 corpus justices, stored as data rather than derived by name matching
- [ ] **JUSTICE-02**: `import_justices_csv` writes `oyez_speaker_id` from that mapping, so `import_convokit::_resolve_person` matches on its first and preferred key
- [ ] **JUSTICE-03**: A `people.display_name` column carries the corpus name form; the bio card shows `full_name` (the fuller CSV form) and utterance attribution shows `display_name`, falling back to `full_name` when null
- [ ] **JUSTICE-04**: `reset_to_fixture` seeds all justices after its TRUNCATE, so they persist through every fixture reset
- [ ] **JUSTICE-05**: A partial unique index on `people.oyez_speaker_id` makes duplicate justice rows structurally impossible
- [ ] **JUSTICE-06**: Avatar initials derive from first and last *name*, skipping suffixes — "John Marshall Harlan, II" yields JH, not JI

### Undetermined Speakers (SPEAKER)

- [ ] **SPEAKER-01**: An utterance whose corpus speaker is a `type: "U"` sentinel renders as Treatment D — a narrower bubble centred between two reserved-but-empty rails, labelled "undetermined speaker"
- [ ] **SPEAKER-02**: Hovering an undetermined utterance reveals a question-mark avatar in both rails; clicking either opens an explanation card in the speaker-bio card shape
- [ ] **SPEAKER-03**: The source-sentinel fact is stored on the utterance at import, never re-derived from `raw_speaker_label`
- [ ] **SPEAKER-04**: A stored source-sentinel speaker contributes PROVISIONAL to the trust floor rather than UNCERTAIN, so such arguments are publishable without a per-argument override
- [ ] **SPEAKER-05**: An argument more than 50% undetermined is not publishable without explicit operator intervention
- [ ] **SPEAKER-06**: Every whole-turn marker in the curated vocabulary displays in its canonical form, wherever it appears; markers inline within a spoken sentence are left exactly as the source wrote them
- [ ] **SPEAKER-07**: A whole-turn inaudible marker with a known speaker renders as an ordinary attributed bubble whose body is the marker — the speaker attribution the source supplied is no longer discarded
- [ ] **SPEAKER-08**: Voice Overlap remains classified as a stage direction, and laughter inside a speaker's turn still splits into speech plus a separate room-event row

### Publishing at Scale (PUBLISH)

- [ ] **PUBLISH-01**: An offline `pipeline bulk-publish` CLI command publishes arguments in bulk, with `--dry-run`, following the existing `recompute-trust` / `prune-runs` command template
- [ ] **PUBLISH-02**: Bulk publish calls the existing `publish_argument` service per row so the trust gate and status-log write are never bypassed, and is resumable by construction rather than via a checkpoint table
- [ ] **PUBLISH-03**: Bulk publish commits in chunks sized for PgBouncer transaction mode, and reports a per-row outcome
- [ ] **PUBLISH-04**: The corpus is published — every argument eligible under the trust rules, excluding those SPEAKER-05 holds back
- [ ] **PUBLISH-05**: Every public surface is verified against a real term at real volume (~108 arguments), not against the four fixtures

### Public Site (SITE)

- [ ] **SITE-01**: `/` serves a landing page following `HOMEPAGE-BRIEF.md`'s content priority — format-first, with no coverage claim anywhere, and a quiet note that the archive is incomplete and being extended
- [ ] **SITE-02**: An About page covers scope, licensing, maintainer and non-goals
- [ ] **SITE-03**: A search endpoint on the existing arguments router matches case name, docket number, speaker name and term, reusing the existing published gate rather than reimplementing it
- [ ] **SITE-04**: Case and speaker names match forgivingly; docket numbers match exactly or by normalised-exact, never by near-miss
- [ ] **SITE-05**: A search results surface shows enough per row for a reader to choose between hits, with bounded pagination
- [ ] **SITE-06**: A zero-result search states the OT 1955–2019 coverage boundary plainly
- [ ] **SITE-07**: Every argument links to its source transcript on Oyez, built from the `external_id` lineage captured in Phase 47

### Surface Plumbing (PLUMBING)

- [ ] **PLUMBING-01**: `robots.txt` is served
- [ ] **PLUMBING-02**: A sitemap is generated at request time from published arguments only, using the same publish predicate as every other public route
- [ ] **PLUMBING-03**: Every public page carries a distinct `<title>`, meta description and Open Graph tags
- [ ] **PLUMBING-04**: The referenced favicon exists and no longer 404s on every page load
- [ ] **PLUMBING-05**: A root-level error page handles any bad URL, not just those under `/arguments`
- [ ] **PLUMBING-06**: The Admin link is removed from the public navigation
- [ ] **PLUMBING-07**: Every new public route and schema is registered in `test_trust_public_leak_ban.py`'s coverage lists in the same phase that adds it — the test does not auto-discover

### Analytics and Privacy (ANALYTICS)

- [ ] **ANALYTICS-01**: A cookieless, first-party analytics script records page views and referrers, loaded on public pages only and never on `/admin/*`
- [ ] **ANALYTICS-02**: Search queries are captured, and zero-result queries are surfaced on the admin dashboard, distinguishing an out-of-range query (a genuine content gap) from an in-range one (a search-quality bug)
- [ ] **ANALYTICS-03**: No case, docket or speaker identity is ever attached as an analytics event property, and no search or popularity data reaches a public surface
- [ ] **ANALYTICS-04**: A privacy policy page states plainly what is measured and what is not
- [ ] **ANALYTICS-05**: The chosen tool's actual client-side behaviour is verified — no `document.cookie`, `localStorage`, `IndexedDB` or fingerprinting reads — and the consent determination is recorded with its jurisdictional caveats

### Verification Debt (VERIFY)

- [ ] **VERIFY-01**: The three never-observed UAT behaviours are verified working — the failed-run error panel, the unresolved-advocate role placeholder with its per-row Save gate, and the non-interactive avatar for an unresolved utterance
- [ ] **VERIFY-02**: Phase 49's outstanding live-browser checks (`49-EVIDENCE.md` §9) are run to completion

## Future Requirements

Deferred. Tracked but not in this roadmap.

### Search refinements

- **SEARCH-F01**: Docket-number format normalisation accepting citation-style or free-form entry — trigger: real search logs show readers typing formats the raw match misses
- **SEARCH-F02**: Query-aware zero-result refinement that detects an out-of-range year specifically — trigger: the baseline copy proves too ambiguous against real logs
- **SEARCH-F03**: Full-text search across utterance text — gated on a design pass answering how highlighted snippets avoid reading as "notable quotes"

### Deployment (v2.0)

- **DEPLOY-01**: Application deployed to DigitalOcean App Platform
- **DEPLOY-03**: Continuous deployment from the GitHub main branch

## Out of Scope

| Feature | Reason |
|---------|--------|
| Deployment and DNS | v2.0 is the deployment and only that |
| Accessibility audit / axe-core assertion | Operator decision 2026-09-23; the Phase 04 waiver stands, now drifted across five phases of UI change. Recorded as known risk in `launch-readiness.md` |
| Theme and user preferences | Not scoped; raised only as a reason a consent surface might later be needed |
| Recent terms (post-2019) | Requires the deferred PDF route, Phase 999.11 |
| Public "request a case" form | Deferred to Phase 999.12 — first public write path, and most zero-result searches are unfulfillable until 999.11. Search analytics covers the prioritisation need |
| Public "trending" / "most viewed" | Anti-feature — implicit importance ranking, violates the apolitical constraint |
| Relevance-ranked search results | Editorialises which case matters |
| Outcome / disposition filters | Requires outcome data excluded from the project entirely |
| Prominent coverage-count statistics | `HOMEPAGE-BRIEF.md` locks against leading with scale |
| An external search engine | A scale problem this archive does not have; Postgres is sufficient at ~7,800 rows |

## Traceability

Populated during roadmap creation (2026-09-23). Every v1 requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| JUSTICE-01 | Phase 52 | Pending |
| JUSTICE-02 | Phase 52 | Pending |
| JUSTICE-03 | Phase 52 | Pending |
| JUSTICE-04 | Phase 52 | Pending |
| JUSTICE-05 | Phase 52 | Pending |
| JUSTICE-06 | Phase 52 | Pending |
| SPEAKER-01 | Phase 53 | Pending |
| SPEAKER-02 | Phase 53 | Pending |
| SPEAKER-03 | Phase 53 | Pending |
| SPEAKER-04 | Phase 53 | Pending |
| SPEAKER-05 | Phase 53 | Pending |
| SPEAKER-06 | Phase 53 | Pending |
| SPEAKER-07 | Phase 53 | Pending |
| SPEAKER-08 | Phase 53 | Pending |
| PUBLISH-01 | Phase 54 | Pending |
| PUBLISH-02 | Phase 54 | Pending |
| PUBLISH-03 | Phase 54 | Pending |
| PUBLISH-04 | Phase 54 | Pending |
| PUBLISH-05 | Phase 54 | Pending |
| VERIFY-01 | Phase 54 | Pending |
| VERIFY-02 | Phase 54 | Pending |
| SITE-03 | Phase 55 | Pending |
| SITE-04 | Phase 55 | Pending |
| SITE-05 | Phase 55 | Pending |
| SITE-06 | Phase 55 | Pending |
| PLUMBING-07 | Phase 55 | Pending |
| SITE-01 | Phase 56 | Pending |
| SITE-02 | Phase 56 | Pending |
| SITE-07 | Phase 56 | Pending |
| PLUMBING-01 | Phase 57 | Pending |
| PLUMBING-02 | Phase 57 | Pending |
| PLUMBING-03 | Phase 57 | Pending |
| PLUMBING-04 | Phase 57 | Pending |
| PLUMBING-05 | Phase 57 | Pending |
| PLUMBING-06 | Phase 57 | Pending |
| ANALYTICS-01 | Phase 58 | Pending |
| ANALYTICS-02 | Phase 58 | Pending |
| ANALYTICS-03 | Phase 58 | Pending |
| ANALYTICS-04 | Phase 58 | Pending |
| ANALYTICS-05 | Phase 58 | Pending |

**Coverage:**

- v1 requirements: 40 total
- Mapped to phases: 40 ✓
- Unmapped: 0 ✓

**Count correction (2026-09-23, roadmap creation):** this section previously recorded 33 total v1
requirements. The actual count in the sections above is **40** — JUSTICE 6, SPEAKER 8, PUBLISH 5,
SITE 7, PLUMBING 7, ANALYTICS 5, VERIFY 2. No requirement was added or removed; the earlier figure
was an arithmetic error in the summary block only. All 40 are mapped.

**Phase distribution:**

| Phase | Requirements | Count |
|-------|--------------|-------|
| 52 — Justice Identity | JUSTICE-01–06 | 6 |
| 53 — Undetermined Speakers & Marker Normalisation | SPEAKER-01–08 | 8 |
| 54 — Publishing at Scale & Verification Debt | PUBLISH-01–05, VERIFY-01, VERIFY-02 | 7 |
| 55 — Search | SITE-03, SITE-04, SITE-05, SITE-06, PLUMBING-07 | 5 |
| 56 — Landing Page, About & Oyez Source Links | SITE-01, SITE-02, SITE-07 | 3 |
| 57 — Surface Plumbing | PLUMBING-01–06 | 6 |
| 58 — Analytics & Privacy | ANALYTICS-01–05 | 5 |

**PLUMBING-07 is owned by Phase 55** (the first phase adding a new public route), but the obligation
it encodes is cross-cutting: Phases 53, 55, 56, 57 and 58 each add a public route, schema module or
frontend path and must register it in `test_trust_public_leak_ban.py`'s coverage lists in the same
phase. The test does not auto-discover.

---
*Requirements defined: 2026-09-23 — traceability populated 2026-09-23*
