# Requirements: SCOTUS Chat

**Defined:** 2026-07-02
**Milestone:** v1.5 Admin Screens Cleanup
**Core Value:** Anyone can open a SCOTUS oral argument and immediately follow the conversation — the chat format makes speaker identity, turn-taking, and flow self-evident without legal background.

## v1.5 Requirements

### Dashboard (`/admin/`)

- [ ] **DASH-01** Stat cards: Arguments (total / published / draft / unpublished), People (total / incomplete), Utterances (total), Pipeline runs (recent + last activity date)
- [ ] **DASH-02** Each stat card includes an inline actionable CTA where applicable (e.g. "12 people missing fields → Review")
- [ ] **DASH-03** "Needs attention" section: people with incomplete fields, Justices with tenure gaps, draft arguments — excludes intentionally unpublished arguments
- [ ] **DASH-04** Web traffic placeholder card ("coming soon")
- [ ] **DASH-05** Intentional visual design — not a generic table dump

### Pipeline List (`/admin/pipeline/`)

- [x] **PLIST-01** Question number: free text field replacing 2-option dropdown
- [x] **PLIST-02** Docket input: pill/tag UI — add one at a time, remove individually, supports multiple dockets for consolidated arguments
- [x] **PLIST-03** Runs table shows all pipeline runs (not just recent)
- [x] **PLIST-04** "Show incomplete only" toggle retained
- [x] **PLIST-05** Status badges show stage + status (e.g. "Parse · Running", "Resolve · Needs Review", "Completed")

### Pipeline Job Detail (`/admin/pipeline/[id]`)

- [x] **PJOB-01** Pipeline Run status card: status badge + source file linked to PDF — replaces non-editable argument preview card
- [x] **PJOB-02** Run status card has 3 states: Not ready (lists what's blocking creation) / Ready ("Create Argument" CTA) / Already created (link to argument edit page)
- [x] **PJOB-03** Argument metadata section renamed to "Argument Details"
- [x] **PJOB-04** Extracted hints always visible alongside editable fields, even after fields are filled; "N/A" if nothing was extracted — gives operator a historic view of what the pipeline pulled
- [x] **PJOB-05** Docket: pill/tag UI (consistent with PLIST-02)
- [x] **PJOB-06** Question number: free text field (consistent with PLIST-01)
- [x] **PJOB-07** Save saves run metadata only — does not create the argument
- [x] **PJOB-08** Failed step card: shows error message + contextual next-step actions inside the card
- [x] **PJOB-09** Ingest card: remove source file display (now shown in run status card)
- [x] **PJOB-10** Parse card shows: Utterances, Speakers (Bench / Advocate / Total), Case Name, Argued Date, Docket(s), Question Number(s)
- [x] **PJOB-11** Parse card shows unextracted fields alongside extracted values — what should have been captured but wasn't
- [x] **PJOB-12** Parse card extracted values match the hints shown in the Argument Details card
- [x] **PJOB-13** Extract advocate title + role from PDF TOC per argument — new `title` VARCHAR field on `argument_participants`, parse step changes, and Alembic migration
- [x] **PJOB-14** Resolve card: Not ready + Ready states are fully editable; Already created state is read-only
- [x] **PJOB-15** Resolve card columns: Raw label · Resolved as (avatar + name, no confirmation checkmark) · Bench/Advocate · Argument Role · Title (advocates only) · Action
- [x] **PJOB-16** Bench Argument Role: tenure lookup at argued date; "Missing tenure" displayed when no matching tenure found
- [x] **PJOB-17** Saving Argument Details triggers bench role recalculation in the resolve card
- [x] **PJOB-18** Person selection in resolve: operator confirms Bench/Advocate side first, then typeahead to find existing person
- [x] **PJOB-19** New person mini-form in resolve: Name + Bench/Advocate toggle; sets `is_justice` on person record AND `side` on `argument_participants`; all other details filled later in people editor
- [x] **PJOB-20** "Create Argument" action lives in run status card CTA — no standalone floating button
- [x] **PJOB-21** "Continue Resolve" action lives at bottom of resolve card when all rows are dispositioned — no standalone floating button
- [x] **PJOB-22** "Re-run" action lives inside the failed step card as a contextual action — no standalone floating button
- [x] **PJOB-23** Danger Zone: delete run — unchanged

### Arguments List (`/admin/arguments/`)

- [x] **ALIST-01** New `unpublished` argument status — distinct from Draft: Draft (never published, slug editable) / Published (slug locked, visible on public site) / Unpublished (was public, now hidden, slug locked) — new enum value + Alembic migration; unpublish action transitions to `unpublished`, not back to `draft`
- [x] **ALIST-02** Arguments list shows only Draft / Published / Unpublished rows — pipeline-status arguments excluded (they live on pipeline job detail)
- [x] **ALIST-03** Status column accurately reflects all three statuses with distinct badges
- [x] **ALIST-04** "Created" column added showing date/time argument was first created

### Argument Edit (`/admin/arguments/[id]`)

- [x] **AEDIT-01** Argument Status card: current status badge, created date, published date
- [x] **AEDIT-02** Full status log with timestamps for every transition (Created, Published, Unpublished, re-Published, etc.) — requires new `argument_status_log` table + migration; log written from both the argument edit page (publish/unpublish) AND the pipeline job detail (argument creation event)
- [x] **AEDIT-03** Argument Details card mirrors the pipeline job detail version: docket pill/tag, question number free text, argued date, extracted hints always visible from `cover_metadata`; "N/A" if nothing extracted
- [x] **AEDIT-04** Argument Details card is a shared component — same UI on pipeline/[id] and arguments/[id], different save targets (run metadata vs. argument record)
- [x] **AEDIT-05** Speakers section replaces Advocate Roles card and tenure gap warnings: all argument participants listed with utterance count each
- [x] **AEDIT-06** Advocates in speakers section: role dropdown (PETITIONER / RESPONDENT / AMICUS) + title field (per argument) + inline save without full page refresh
- [x] **AEDIT-07** Bench in speakers section: all bench participants listed with role derived from tenure at argued date; "Missing tenure" warning + edit person link when gap exists
- [x] **AEDIT-08** Publish/Unpublish transitions: Draft → Published / Published → Unpublished / Unpublished → Published (re-publish)
- [x] **AEDIT-09** Danger Zone: delete — unchanged

### People List (`/admin/people/`)

- [x] **PDIR-01** Page title: "People" (was "People Editor")
- [x] **PDIR-02** Bench / Advocate tab or toggle at top of page
- [x] **PDIR-03** Bench view columns: name, tenure coverage, tenure gaps indicator, photo/bio completeness
- [x] **PDIR-04** Advocate view columns: name, argument count, photo/bio completeness
- [~] **PDIR-05** ~~"Incomplete only" filter retained, scoped per tab~~ — **Reworked by Phase 27 D-04**: the toggle is removed entirely; replaced by click-to-filter missing-field pills scoped per tab (same underlying capability, different interaction model)
- [x] **PDIR-06** "Justices with tenure gaps" filter retained (bench tab only)
- [x] **PDIR-07** "Create person" button on list page — navigates to full person editor starting blank; enables creating Justices before any argument is uploaded

### Person Editor (`/admin/people/[id]`)

- [x] **PEDIT-01** Full name fields: first / middle / last / suffix — same structure for bench and advocates
- [x] **PEDIT-02** Optional birthdate field added to Basic Info card
- [x] **PEDIT-03** No prefix/rank field on person record — rank captured per-argument via `argument_participants.title` (PJOB-13)
- [~] **PEDIT-04** ~~Role field: Justice-only, lives inside Justice Details card; not shown for advocates~~ — **Superseded by Phase 27 D-10**: role is captured per-argument on `argument_participants` (Phase 26), so a person-level Role field was dropped from the Bench Details card
- [x] **PEDIT-05** Bio & Photo card: button label changed from "Save photo" to "Upload photo"
- [x] **PEDIT-06** Justice Details card: collapsed by default, consolidates is_justice checkbox, role, tenures, and appointment data into one card
- [x] **PEDIT-07** "Is Justice" checkbox opens Justice Details card with animation; unchecking hides fields but does not delete tenure or appointment data
- [~] **PEDIT-08** ~~Role field (Chief Justice / Associate Justice) lives inside Justice Details card~~ — **Superseded by Phase 27 D-10**: same rationale as PEDIT-04
- [x] **PEDIT-09** Tenure rows each contain: Seat (Chief / Associate), Appointed by, Appointing president's party, Start date, End date — add / remove rows as before
- [x] **PEDIT-10** Schema change: move `appointed_by` and `appointing_president_party` from `people` table to `court_tenures` table — Alembic migration with data backfill
- [x] **PEDIT-11** Merge card — unchanged
- [x] **PEDIT-12** Delete card — unchanged

## Historical Corpus Import (Phase 29)

Requirements for the one-time bulk-import of terms 1955–2019 from the Cornell ConvoKit `supreme-corpus` dataset. Sits outside the v1.5 milestone requirement set; added 2026-07-09 during `/gsd-plan-phase 29` from RESEARCH.md's proposed codes and CONTEXT.md decisions D-01…D-26.

- [x] **CORPUS-01** Bulk-import all historical justices from the tenure CSV; dedup by exact `Person.full_name` match against the 13 existing `seed_aliases.py` Person rows; upgrade those 13 rows in place (`is_justice=true`, `court_tenures` backfill); auto-create both tenure rows for elevated justices (Rehnquist, Rutledge) (D-01–D-05)
- [x] **CORPUS-02** Alembic migration adding nullable `Case.oyez_case_id`, `Argument.oyez_transcript_id`, `Person.oyez_speaker_id` columns (D-10)
- [x] **CORPUS-03** New `import-convokit` pipeline CLI subcommand: parses corpus files directly (no `convokit` package), staged/batched by October Term via `--term`/`--term-range`, resumable/idempotent (check-before-insert per argument), writes real `pipeline_runs` rows (`strategy="convokit_import"`), lands arguments at `status=draft`, lead-docket-only for consolidated cases (D-06–D-09, D-15, D-19)
- [x] **CORPUS-04** Source-file handling: copy the 5 needed files into a new gitignored `data/corpus/` directory (mirroring `data/pdfs/`); explicitly exclude the 3 NLP-annotation files; add `python-dateutil` dependency (D-20, D-21)
- [x] **CORPUS-05** Speaker identity resolution: `oyez_speaker_id` primary re-run match key, `full_name` exact-match fallback; import everything with no automated QA gate; apolitical field stripping (never persist `win_side`/`votes_side`/`scdb_docket_id`) (D-11, D-12, D-13)
- [x] **CORPUS-06** Stage-direction detection and row-splitting: curated typo-tolerant vocabulary match inside `[brackets]` or `(parens)`, split into separate `Utterance` rows with `is_stage_direction=true`, `raw_speaker_label=None` (D-16, D-17)
- [ ] **CORPUS-07** Multi-sentence utterance storage: one `Utterance` row per ConvoKit turn, `\n`-delimited segment boundaries preserved verbatim in `Text` (D-18)
- [ ] **CORPUS-08** Per-batch summary report printed at the end of each term/batch run (counts created/skipped/flagged) (D-14)
- [x] **CORPUS-09** Attributions/License static page (`/attributions`) crediting Oyez.org, Cornell ConvoKit, and SCDB; states the Oyez CC BY-NC 4.0 license fact (D-22–D-26)
- [x] **CORPUS-10** Per-argument attribution note visible only on corpus-sourced arguments, linking to the Attributions page (D-22)
- [x] **CORPUS-11** Roadmap bookkeeping: mark backlog Phase 999.10 superseded/absorbed by Phase 29 (D-01)

## Future Requirements

### Public URL

- **URL-01** Rename public URL `/cases/` → `/arguments/` to accurately reflect the entity name

## Out of Scope

| Feature | Reason |
|---------|--------|
| Public URL rename (`/cases/` → `/arguments/`) | SEO and link-rot risk; warrants its own milestone with redirect strategy |
| New pipeline step features (enrich, citations) | Not admin UX scope |
| Any changes to public-facing argument/case view | v1.5 is operator-only admin cleanup |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DASH-01 | Phase 28 | Pending |
| DASH-02 | Phase 28 | Pending |
| DASH-03 | Phase 28 | Pending |
| DASH-04 | Phase 28 | Pending |
| DASH-05 | Phase 28 | Pending |
| PLIST-01 | Phase 24 | Complete |
| PLIST-02 | Phase 24 | Complete |
| PLIST-03 | Phase 24 | Complete |
| PLIST-04 | Phase 24 | Complete |
| PLIST-05 | Phase 24 | Complete |
| PJOB-01 | Phase 25 | Complete |
| PJOB-02 | Phase 25 | Complete |
| PJOB-03 | Phase 23 | Complete |
| PJOB-04 | Phase 23 | Complete |
| PJOB-05 | Phase 23 | Complete |
| PJOB-06 | Phase 23 | Complete |
| PJOB-07 | Phase 23 | Complete |
| PJOB-08 | Phase 25 | Complete |
| PJOB-09 | Phase 23 | Complete |
| PJOB-10 | Phase 23 | Complete |
| PJOB-11 | Phase 23 | Complete |
| PJOB-12 | Phase 23 | Complete |
| PJOB-13 | Phase 22 | Complete |
| PJOB-14 | Phase 25 | Complete |
| PJOB-15 | Phase 25 | Complete |
| PJOB-16 | Phase 25 | Complete |
| PJOB-17 | Phase 25 | Complete |
| PJOB-18 | Phase 25 | Complete |
| PJOB-19 | Phase 25 | Complete |
| PJOB-20 | Phase 25 | Complete |
| PJOB-21 | Phase 25 | Complete |
| PJOB-22 | Phase 25 | Complete |
| PJOB-23 | Phase 25 | Complete |
| ALIST-01 | Phase 22 | Complete |
| ALIST-02 | Phase 26 | Complete |
| ALIST-03 | Phase 26 | Complete |
| ALIST-04 | Phase 26 | Complete |
| AEDIT-01 | Phase 26 | Complete |
| AEDIT-02 | Phase 22 | Complete |
| AEDIT-03 | Phase 23 | Complete |
| AEDIT-04 | Phase 23 | Complete |
| AEDIT-05 | Phase 26 | Complete |
| AEDIT-06 | Phase 26 | Complete |
| AEDIT-07 | Phase 26 | Complete |
| AEDIT-08 | Phase 26 | Complete |
| AEDIT-09 | Phase 26 | Complete |
| PDIR-01 | Phase 27 | Complete |
| PDIR-02 | Phase 27 | Complete |
| PDIR-03 | Phase 27 | Complete |
| PDIR-04 | Phase 27 | Complete |
| PDIR-05 | Phase 27 | Reworked (D-04) |
| PDIR-06 | Phase 27 | Complete |
| PDIR-07 | Phase 27 | Complete |
| PEDIT-01 | Phase 27 | Complete |
| PEDIT-02 | Phase 27 | Complete |
| PEDIT-03 | Phase 27 | Complete |
| PEDIT-04 | Phase 27 | Superseded (D-10) |
| PEDIT-05 | Phase 27 | Complete |
| PEDIT-06 | Phase 27 | Complete |
| PEDIT-07 | Phase 27 | Complete |
| PEDIT-08 | Phase 27 | Superseded (D-10) |
| PEDIT-09 | Phase 27 | Complete |
| PEDIT-10 | Phase 22 | Complete |
| PEDIT-11 | Phase 27 | Complete |
| PEDIT-12 | Phase 27 | Complete |
| CORPUS-01 | Phase 29 | Complete |
| CORPUS-02 | Phase 29 | Complete |
| CORPUS-03 | Phase 29 | Complete |
| CORPUS-04 | Phase 29 | Complete |
| CORPUS-05 | Phase 29 | Complete |
| CORPUS-06 | Phase 29 | Complete |
| CORPUS-07 | Phase 29 | Pending |
| CORPUS-08 | Phase 29 | Pending |
| CORPUS-09 | Phase 29 | Complete |
| CORPUS-10 | Phase 29 | Complete |
| CORPUS-11 | Phase 29 | Complete |

**Coverage:**

- v1.5 requirements: 57 total
- Mapped to phases: 57
- Unmapped: 0 ✓
- Phase 29 (Historical Corpus Import): CORPUS-01…CORPUS-11, all mapped to Phase 29

---
*Requirements defined: 2026-07-02*
*Last updated: 2026-07-08 — PEDIT-04 and PEDIT-08 marked Superseded per Phase 27 discuss-phase decision D-10 (person-level Role field dropped; role is argument-level via `argument_participants`); PDIR-05 marked Reworked per decision D-04 (toggle replaced by click-to-filter pills) — flagged by gsd-plan-checker during Phase 27 plan verification*
