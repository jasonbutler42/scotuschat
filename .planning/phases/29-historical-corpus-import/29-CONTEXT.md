# Phase 29: Historical Corpus Import - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Bulk-import historical Supreme Court oral arguments (terms 1955–2019, ~7,800 arguments) from the Cornell ConvoKit `supreme-corpus` dataset directly into the existing schema (cases, arguments, utterances, people, court_tenures), bypassing PDF download and LLM parsing entirely for this batch. This is a new, separate one-time bulk-import CLI command (consistent with "pipeline is offline only") — it does not replace or modify the existing PDF ingest/parse/resolve pipeline, which stays the path for terms 2020+ and all future terms going forward.

**Scope amendment from discussion:** Backlog Phase 999.10 (bulk-import historical justices from CSV) is folded into this phase as its first step/prerequisite — the corpus import cannot correctly resolve bench speakers across 1955–2019 without the full historical justice roster (tenure + appointment data), and 999.10 already covers exactly that need. `.planning/ROADMAP.md`'s Phase 999.10 entry should be marked superseded/absorbed when this phase is planned.

**New schema work in scope:** A small Alembic migration adding nullable external-ID columns (`Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id`) — see Decisions below. Also in scope: a dedicated Attributions/License page (small, static) required before any imported argument goes live, even as draft.

**Out of scope (deferred to future phases, captured below):** consolidated-docket companion dockets, any public-facing rendering decision for stage directions or multi-sentence utterance display, any UI toggle/reading-mode feature, browse-by-October-Term navigation.

</domain>

<decisions>
## Implementation Decisions

### Guiding principle established during discussion
Where the corpus gives us information our current schema/UI has no rendering policy for yet (stage directions, sentence/paragraph boundaries), the repeated decision was: **preserve the data losslessly now, defer the display/rendering decision to a future phase.** This principle should be applied by the researcher/planner to any other similar gray spot they find that isn't explicitly covered below — don't guess at a rendering policy; store faithfully and leave it decidable later.

### Justice Roster Prerequisite (absorbs backlog Phase 999.10)
- **D-01:** Fold Phase 999.10 (bulk justice CSV import) into this phase as step zero — not a separate phase that must land first.
- **D-02:** Dedup match strategy for justices against the 13 already-seeded Person rows: **exact `Person.full_name` string match** (same precedent as the existing `seed_aliases.py` script) — not structured first/middle/last/suffix comparison.
- **D-03:** The 13 Person rows already seeded by `pipeline/commands/seed_aliases.py` (pre-Phase-22 model: no `court_tenures`, no `is_justice`, uses old `role_id`) get **upgraded in place** — matched by name, then backfilled with `is_justice=true` and their `court_tenures` row(s) from the CSV. Not left as-is.
- **D-04:** Justices appearing in both the CSV's Chief and Associate Justice sections (confirmed: Rehnquist, Rutledge — elevated justices) get **both `court_tenures` rows auto-created**, not flagged for manual review — the CSV gives two unambiguous, complete date ranges; this is exactly the multi-tenure case the schema (Phase 27 decision log) was designed for.
- **D-05 (verified, no decision needed):** CSV `Party` column values (`Federalist`, `Democratic-Republican`, `Democratic`, `Whig`, `Republican` — confirmed via direct scan of all 126 CSV rows) map cleanly onto Phase 27 D-16's curated `appointing_president_party` dropdown. No value-mapping work needed.

### Rollout / Publish Status / Batching
- **D-06:** Imported arguments land as **`draft`** status (not auto-published) — matches the existing pipeline's "resolve completes, publish is always a separate deliberate action" pattern (PROJECT.md decision D-05: metadata fabrication forbidden, operator reviews before publish). Applies even though the source data is high-confidence, because 7,800 arguments deserves the same review gate as any other ingestion path.
- **D-07:** Import is **staged with checkpoints, batched by October Term** (not one shot for the whole corpus). See D-15 below for what "term" means and why.
- **D-08:** Import is **resumable/idempotent** — check-before-insert per argument (matches `seed_aliases.py`'s existing idempotency pattern), safe to re-run a batch after a crash or interruption without hand-cleaning partial data.
- **D-09:** Each imported argument gets **real `pipeline_runs` rows** (ingest/parse/resolve style, `strategy="convokit_import"`) — not minimal placeholder rows. `Utterance.pipeline_run_id` is NOT NULL regardless, so this is also the natural audit trail: every argument traces back to a `pipeline_runs` row explaining where its data came from (batch/term, source file, timestamp).

### October Term Sourcing (clarified mid-discussion — locked, not deferred)
- **D-15:** `Case.term_year` = `cases.jsonl`'s `"year"` field, taken **directly** — never derived from `argued_date`'s calendar year. Verified: SCOTUS terms are named "October Term YYYY" and can span into the following calendar year (confirmed via American Airlines, Inc. v. North American Airlines — argued/decided in 1956, but `cases.jsonl` correctly reports `"year": 1955` = October Term 1955). Deriving term_year from argued_date's calendar year would misclassify every case argued January–June. No new column needed — the existing `Case.term_year` (Integer) already fits; format as `"October Term {term_year}"` at display time whenever a future public-facing browse-by-term feature is built (deferred — see below).
- This same `term_year`/October Term boundary is also the natural unit for D-07's staged-batching ("one batch = one October Term").

### External ID Preservation (new schema addition)
- **D-10:** Add nullable columns via a new Alembic migration: `Case.oyez_case_id` (e.g. `"1955_71"`), `Argument.oyez_transcript_id` (e.g. `"13127"` — the ConvoKit `conversation_id` / Oyez audio player id), `Person.oyez_speaker_id` (e.g. `"j__earl_warren"` or `"harry_f_murphy"` — null for people not sourced from the corpus).
- **D-11:** `Person.oyez_speaker_id` becomes the **primary re-run match key** for corpus-sourced people (checked before falling back to `full_name`). Falls back to `full_name` matching only when no ID is stored yet — i.e. for pre-existing manually-entered Person rows, and for the 13 seed-aliases justices before D-03's upgrade runs.
- **Rationale (user-originated):** stable corpus-native IDs are a more robust idempotency key than name-string matching for re-running an import batch, AND preserving them keeps a future "link out to oyez.org" feature possible without re-deriving/re-scraping anything. Both benefits captured now; the outbound-linking feature itself is deferred (not built this phase).

### Advocate Identity QA
- **D-12:** No automated QA gate on advocate name-matching per batch — **import everything**, relying on D-06's draft-status as the review gate (bad matches are visible to the operator before anything publishes; no need for a second gate on top of that).
- **D-13:** Advocate dedup against pre-existing manually-entered Person rows uses the **same exact `full_name` string match** as D-02 (one dedup strategy across the whole script, not two different ones).
- **D-14:** Print a **per-batch summary report** at the end of each term/batch run (counts of arguments/utterances/people created, any flagged items, any skipped/errored cases) — not silent, and not requiring an admin-UI check to get a signal.

### Stage Directions
- **D-16:** **Split stage directions into separate `Utterance` rows** (`is_stage_direction=true`, `raw_speaker_label=None`) at import time — matches the existing schema model exactly, and is the more flexible choice for a future public-facing toggle the user wants eventually (possibly a far-future account setting) to switch between "inline, matches transcript" and "split" rendering. Splitting now is strictly better than leaving inline: the inline view can always be reconstructed later via a trivial rendering-time join of adjacent same-speaker rows, but the reverse (splitting an already-merged blob) requires the same regex work anyway — so splitting now costs nothing extra and keeps the toggle idea cheap to build later.
- **D-17:** Marker detection uses a **curated vocabulary match** (`Inaudible`, `Laughter`/`Laughs`/`Laugh`, `Voice Overlap`, `Recess`, `Luncheon Recess`, `Cross Talk` — case-insensitive, typo-tolerant, e.g. `Luaghter`/`Inaudibel` observed in real data) inside **either** `[brackets]` **or** `(parens)` — **not** a blind "anything inside brackets/parens" regex.
  - **Verified via direct data scan** (400K rows of `utterances.jsonl`): parens are heavily overloaded with legitimate non-stage-direction content — `(a)`/`(b)`/`(1)`/`(2)` legal-citation-style list markers (thousands of occurrences) and `(ph)` ("phonetic spelling, name uncertain" — a real transcript convention) would be misclassified by a blind paren-capture regex.
  - **Parens cannot be skipped or ignored in favor of brackets-only:** `(Inaudible)` alone appears 37,883 times vs. 6,054 for `[Inaudible]` in brackets — the paren form carries the majority of actual stage-direction occurrences.

### Multi-Sentence Utterance / Paragraph Handling
- **D-18:** Store each ConvoKit "utterance" (one turn) as **one `Utterance` row**, with the `\n`-delimited sentence/segment boundaries preserved **verbatim inside the `Text` field** — not collapsed to spaces (which would discard ConvoKit's free per-sentence segmentation), and not pre-split into multiple DB rows per sentence (which would be a harder-to-reverse commitment to a specific bubble-density policy the user explicitly wasn't ready to lock — see mockups below).
  - **Same guiding principle as stage directions:** this is losslessly reversible in both directions later — a future phase can render `\n` as line breaks within one bubble, split on `\n` into separate bubbles with whatever grouping heuristic gets decided then (e.g. one bubble per sentence, exactly matching the "split" mockup, vs. some coarser grouping to avoid choppy short-sentence turns), or collapse to flowing prose matching the existing PDF-pipeline convention.
  - **Open question explicitly deferred, not resolved:** whether the eventual bubble-splitting granularity should be "one bubble per `\n` boundary" (simple, lossless, but can get bubble-dense for short-sentence turns — verified against a real 6-segment turn in the corpus) or some coarser grouping heuristic. The user was explicit this is "tricky" and wants it decided later, not now.
  - **Existing PDF-pipeline convention (verified against real DB rows):** currently stores multi-sentence turns as one flowing paragraph, sentences joined by plain spaces, no boundaries preserved at all. This import intentionally diverges (by preserving boundaries) because ConvoKit gives us information PDF-parsed text doesn't have — not because the two sources need to render identically today.

### Consolidated Docket Companions
- **D-19:** Accept **lead-docket-only** for this phase. Verified: the corpus/Oyez only track the lead docket for consolidated cases (Obergefell's `14-556` present; companions `14-562`/`14-571`/`14-574` absent entirely). Sourcing companion dockets requires a different source (e.g. the Court's own docket pages) — real, separate research/scoping work captured as a deferred idea below, not a tweak to this import.

### Source File Handling
- **D-20:** Copy the needed source files **into the project repo** (e.g. under `/data`) before the import command runs — matches the existing "raw source files are immutable" convention already established for PDFs, and makes the import reproducible on any machine instead of depending on this machine's current absolute paths (`C:\workspace\scotuschat\supreme-corpus`, `C:\Users\jason.butler\Downloads\cases.jsonl`).
- **D-21 (explicit, to prevent a naive full-copy mistake):** Only copy the files actually needed — `utterances.jsonl` (900MB), `conversations.json` (3.8MB), `speakers.json` (0.6MB), `cases.jsonl` (13MB), and the justices tenure CSV. **Do NOT copy** `info.arcs.jsonl` (1.2GB), `info.parsed.jsonl` (5.8GB), or `info.tokens.jsonl` (0.5GB) — these are NLP dependency-parse/token annotations, irrelevant to this project, and would needlessly add ~7.5GB to the repo's data directory.

### Attribution / Licensing
- **D-22:** Attribution appears in **three places**: public-facing footer/about text, a per-argument note on corpus-sourced arguments specifically (vs. manually-ingested ones), and codebase/README.
- **D-23:** Credit **Oyez.org**, **Cornell ConvoKit**, and the **Supreme Court Database (SCDB)** — even though SCDB's vote/outcome data is explicitly excluded from import (apolitical constraint); SCDB is credited for the broader data lineage, not because we imported its outcome data.
- **D-24 (verified fact, not speculation):** **Oyez.org's oral-argument transcripts/audio are licensed CC BY-NC 4.0** (Creative Commons Attribution-**NonCommercial**) — confirmed via Creative Commons' own registry/wiki. ConvoKit separately requests two academic citations if their corpus is used (an academic norm, not a legal license): "Echoes of Power" (Danescu-Niculescu-Mizil et al., WWW 2012) and "ConvoKit" (Chang et al., SIGDIAL 2020). SCDB's exact terms were inconclusive but are moot here since SCDB's actual data (votes/outcomes) isn't imported.
- **D-25 — flagged as a project-level constraint, not just phase-level:** Oyez's NonCommercial license creates real tension with PROJECT.md's existing "Monetization — not a driving goal; not excluded for future milestones" stance, since a large share of the site's content (once this phase ships) originates from NC-licensed source material. **Already added to `.planning/PROJECT.md`'s Constraints table during this discussion** (2026-07-09) — not deferred to the next milestone transition, because it affects a future business decision that shouldn't be silently baked in. Not a legal determination — Claude explicitly is not a lawyer; flagged for visibility, not resolved.
- **D-26:** Build the dedicated Attributions/License page **in this phase** (small, static page) — imported arguments shouldn't go live, even as draft (visible to the operator), without it existing. If attribution text gets too long for the footer/per-argument note, link out to this page instead of cramming full credit text everywhere.

### Claude's Discretion
- Exact wording/placement of the per-argument attribution note (D-22) on corpus-sourced argument pages — left to the planner/implementer, informed by D-24's verified license facts but not a locked visual spec.
- Exact per-batch summary report format (D-14) — console output shape, exact fields — left to the planner.
- Exact `.planning/ROADMAP.md` bookkeeping for how Phase 999.10 gets marked superseded/absorbed once this phase is planned (D-01) — mechanical cleanup, not a user decision.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 29 goal (§ "Phase 29: Historical Corpus Import"). No REQUIREMENTS.md entries exist yet for this phase (it sits outside the v1.5 milestone's requirement set) — planner should propose requirement codes (e.g. `CORPUS-01` etc.) during planning.
- `.planning/ROADMAP.md` — Phase 999.10 (§ "Bulk-import historical justices from CSV (BACKLOG)") — absorbed into this phase per D-01; mark superseded when planning.
- `.planning/PROJECT.md` — Constraints section, Oyez CC BY-NC 4.0 entry added 2026-07-09 during this discussion (D-25).

### Source Data Files (external — see D-20/D-21 for repo-copy requirement)
- `C:\workspace\scotuschat\supreme-corpus\utterances.jsonl` (900MB) — one row per speaking turn, speaker-attributed, per-sentence timestamps within `\n`-delimited segments.
- `C:\workspace\scotuschat\supreme-corpus\conversations.json` (3.8MB, 7,817 entries) — one row per oral-argument session; `case_id` (format `<term>_<docket>`), `advocates` dict (side 0=respondent/1=petitioner/2=amicus/3=unknown), also carries `win_side`/`votes_side` — **must be stripped, never persisted** (apolitical constraint).
- `C:\workspace\scotuschat\supreme-corpus\speakers.json` (0.6MB, 9,651 entries) — justices keyed `j__firstname_lastname`; advocates keyed by slugified name.
- `C:\Users\jason.butler\Downloads\cases.jsonl` (13MB, 7,748 entries, terms 1955–2019) — case metadata: `title`, `petitioner`, `respondent`, `docket_no`, `decided_date`, `citation`, `court`, `transcripts[]` (argued-date embedded in `name`, e.g. "Oral Argument - November 15, 1955"), `advocates` (clean display names mapped to the same slug ids as speakers.json). Also carries `win_side`/`win_side_detail`/`votes`/`votes_detail`/`votes_side`/`scdb_docket_id` — **must be stripped, never persisted**.
- `C:\workspace\scotuschat\supreme_court_justices_sections.csv` (126 lines, two sections: Chief Justices then Associate Justices) — columns: First Name, Middle Name or Initial, Last Name, Suffix, Appointed by, Party, Judicial Oath Taken, Date Service Terminated, Reason Left, Birthdate, Death Date. Confirmed multi-tenure cases: Rehnquist and Rutledge appear in both sections (D-04).
- Explicitly NOT needed: `info.arcs.jsonl`, `info.parsed.jsonl`, `info.tokens.jsonl` (NLP annotations, ~7.5GB combined) — do not copy into the repo (D-21).

### Existing Pipeline Code (reusable patterns)
- `pipeline/db.py` — `get_session()` async context manager, the shared DB-access pattern this new import command should reuse (mandatory `statement_cache_size=0` connect_args already handled here).
- `pipeline/commands/seed_aliases.py` — idempotent check-before-insert pattern (`select()` → `scalar_one_or_none()` → skip or add + flush) — direct template for D-08's resumability requirement, and the closest existing precedent for D-01's justice-CSV-import step, though it needs upgrading to the current `is_justice`/`court_tenures` model (D-03) rather than its own pre-Phase-22 `role_id` approach.
- `pipeline/__main__.py` — argparse subcommand registration pattern (`ingest`/`parse`/`resolve`/`seed-aliases`) — the new import command should register as a new subcommand here (e.g. `import-convokit --term 1955` or `--term-range 1955-1960`, matching D-07's staged-by-term batching).
- `api/models/models.py` — full schema reference; `Utterance.pipeline_run_id` is NOT NULL (drives D-09); `SideEnum` values (PETITIONER/RESPONDENT/AMICUS/UNKNOWN/BENCH) map directly onto `conversations.json`'s advocate side codes (0/1/2/3) plus BENCH for justices who spoke.
- `.planning/phases/27-people-admin/27-CONTEXT.md` D-16 — curated `appointing_president_party` dropdown values (Federalist, Democratic-Republican, Democratic, Whig, Republican, Independent) — confirmed clean match against all CSV `Party` values (D-05).
- `.planning/phases/22-schema-foundations/22-CONTEXT.md` — `court_tenures.appointed_by`/`appointing_president_party` migration this phase's CSV import writes into.

### External Facts Verified During Discussion (not to be re-derived)
- Oyez API (`api.oyez.org/cases/{term}/{docket}`) returns case name/docket/argued+decided dates/citation — confirmed working, but **not needed** as a live dependency since `cases.jsonl` already provides this offline.
- SCOTUS "October Term" convention verified against real data (American Airlines case spans Oct/Dec boundary) — see D-15.
- Oyez CC BY-NC 4.0 license verified via Creative Commons' own wiki/registry (`wiki.creativecommons.org/wiki/Oyez`) — see D-24.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/db.py:get_session()` — async session context manager, singleton engine, mandatory `statement_cache_size=0` — use as-is for the new import command.
- `pipeline/commands/seed_aliases.py` — idempotency pattern to copy for both the justice-CSV step (D-01) and the corpus-import step itself (D-08); needs updating to write `is_justice`/`court_tenures` instead of `role_id` alone.
- `Utterance`, `ArgumentParticipant`, `Case`, `Argument`, `CaseArgument`, `Person`, `CourtTenure`, `PipelineRun` models (`api/models/models.py`) — no structural changes needed beyond D-10's 3 new nullable columns.

### Established Patterns
- Check-before-insert idempotency via `select()` → `scalar_one_or_none()` → skip-or-create — used throughout `seed_aliases.py`; the pattern for both D-02/D-03 (justice dedup) and D-08 (import resumability).
- `pipeline_run_id` FK is NOT NULL on `Utterance` — every write path must create a `PipelineRun` row first, no exceptions (informs D-09).
- Alembic hand-written migrations (not autogenerate), explicit FK dependency order — required for D-10's new columns.
- Windows event loop policy guard in `pipeline/__main__.py` (asyncpg incompatible with default ProactorEventLoop) — applies to any new subcommand invoked via `python -m pipeline`.

### Integration Points — Gaps Found During Scouting (not user decisions — planner must address)
- No existing subcommand resembles a "bulk/batched" import — `ingest`/`parse`/`resolve` are all single-argument, single-run CLI invocations. The planner needs to design the `--term`/`--term-range` batching interface from scratch (informed by D-07).
- `seed_aliases.py`'s 13 justices use the OLD `role_id`-only model with no `court_tenures` rows at all — D-03's "upgrade in place" is real migration-adjacent data work, not a simple skip-if-exists check.
- No existing precedent for a chat-UI turn with `\n` preserved inside `Utterance.Text` — current frontend rendering behavior for embedded newlines inside `Text` is unverified; D-18 intentionally defers this, but the researcher should confirm the current template doesn't accidentally render `\n` in some unexpected way (e.g. literal `\n` characters visible) before this phase ships, even though the *rendering policy* itself is deferred.

</code_context>

<specifics>
## Specific Ideas

- User wants a future on-screen toggle (possibly a far-future account setting) to switch between "inline, matches transcript" and "split" views for stage directions — explicitly not built this phase, but D-16's decision to split now is specifically chosen to keep that toggle cheap to build later.
- User provided two mockup images (`C:\workspace\scotuschat\paragraphs - together.png` and `C:\workspace\scotuschat\paragraphs - split.png`) showing the same 2-paragraph turn rendered as one bubble with an internal blank-line gap ("together") vs. two separate consecutive bubbles from the same speaker ("split") — user wants the "split" visual outcome eventually, but was explicit that the exact grouping granularity (one bubble per sentence vs. some coarser grouping) is "tricky" and should be decided later, not now (D-18).
- User's own framing on external IDs: "this is a standalone project" vs. "this is using data from a larger ecosystem and there may be unrealized synergies like being able to cleanly refer visitors to an Oyez.com page because the ids already match" — directly resulted in D-10/D-11.
- User explicitly said "I know you aren't a lawyer so just use your best judgement" regarding attribution/licensing — Claude verified the Oyez CC BY-NC 4.0 fact directly rather than guessing, then flagged (rather than resolved) the monetization tension per D-25.
- User's throughline across two separate discussions (stage directions, then paragraphs) was consistent: "different people read differently" / preserve data now, let a future reading-mode feature decide how it displays — captured as the guiding principle at the top of Decisions.

</specifics>

<deferred>
## Deferred Ideas

- **Public-facing browse-by-October-Term navigation** — user flagged intent to use `term_year` for this in a future phase. Not built now, but D-15's term_year sourcing decision was made specifically so this isn't blocked later.
- **Outbound linking to oyez.org case/justice pages** using the new `oyez_case_id`/`oyez_speaker_id` columns (D-10) — not built now; columns captured specifically so the idea isn't blocked later.
- **Public argument-page toggle** to switch between inline-merged and split-out stage-direction rendering (possibly a future account setting, per user: "far future") — not built now (public UI, its own phase); D-16's decision to split at import time was specifically chosen to keep this cheap to build later.
- **Bubble-splitting granularity for multi-sentence utterances** (one bubble per `\n` boundary vs. a coarser grouping heuristic) — explicitly left undecided per D-18; a future phase must resolve this before any paragraph-splitting rendering ships.
- **Consolidated-docket companion sourcing** (e.g. researching whether the Court's own docket pages or another source could supply Obergefell-style companion dockets 14-562/571/574) — real, separate research/scoping work, deferred per D-19.

### Reviewed Todos (not folded)
- **Edit affordance on utterances and speaker popover** (`.planning/todos/pending/2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md`) — surfaced as a possible match by automated todo cross-referencing (same match Phase 28 also received and declined). It's a public-UI edit affordance, unrelated to a backend bulk-import script. User confirmed: leave in backlog, do not fold into Phase 29.

</deferred>

---

*Phase: 29-Historical Corpus Import*
*Context gathered: 2026-07-09*
