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
- [ ] **ALIST-03** Status column accurately reflects all three statuses with distinct badges
- [ ] **ALIST-04** "Created" column added showing date/time argument was first created

### Argument Edit (`/admin/arguments/[id]`)

- [ ] **AEDIT-01** Argument Status card: current status badge, created date, published date
- [x] **AEDIT-02** Full status log with timestamps for every transition (Created, Published, Unpublished, re-Published, etc.) — requires new `argument_status_log` table + migration; log written from both the argument edit page (publish/unpublish) AND the pipeline job detail (argument creation event)
- [x] **AEDIT-03** Argument Details card mirrors the pipeline job detail version: docket pill/tag, question number free text, argued date, extracted hints always visible from `cover_metadata`; "N/A" if nothing extracted
- [x] **AEDIT-04** Argument Details card is a shared component — same UI on pipeline/[id] and arguments/[id], different save targets (run metadata vs. argument record)
- [ ] **AEDIT-05** Speakers section replaces Advocate Roles card and tenure gap warnings: all argument participants listed with utterance count each
- [ ] **AEDIT-06** Advocates in speakers section: role dropdown (PETITIONER / RESPONDENT / AMICUS) + title field (per argument) + inline save without full page refresh
- [ ] **AEDIT-07** Bench in speakers section: all bench participants listed with role derived from tenure at argued date; "Missing tenure" warning + edit person link when gap exists
- [x] **AEDIT-08** Publish/Unpublish transitions: Draft → Published / Published → Unpublished / Unpublished → Published (re-publish)
- [x] **AEDIT-09** Danger Zone: delete — unchanged

### People List (`/admin/people/`)

- [ ] **PDIR-01** Page title: "People" (was "People Editor")
- [ ] **PDIR-02** Bench / Advocate tab or toggle at top of page
- [ ] **PDIR-03** Bench view columns: name, tenure coverage, tenure gaps indicator, photo/bio completeness
- [ ] **PDIR-04** Advocate view columns: name, argument count, photo/bio completeness
- [ ] **PDIR-05** "Incomplete only" filter retained, scoped per tab
- [ ] **PDIR-06** "Justices with tenure gaps" filter retained (bench tab only)
- [ ] **PDIR-07** "Create person" button on list page — navigates to full person editor starting blank; enables creating Justices before any argument is uploaded

### Person Editor (`/admin/people/[id]`)

- [ ] **PEDIT-01** Full name fields: first / middle / last / suffix — same structure for bench and advocates
- [ ] **PEDIT-02** Optional birthdate field added to Basic Info card
- [ ] **PEDIT-03** No prefix/rank field on person record — rank captured per-argument via `argument_participants.title` (PJOB-13)
- [ ] **PEDIT-04** Role field: Justice-only, lives inside Justice Details card; not shown for advocates
- [ ] **PEDIT-05** Bio & Photo card: button label changed from "Save photo" to "Upload photo"
- [ ] **PEDIT-06** Justice Details card: collapsed by default, consolidates is_justice checkbox, role, tenures, and appointment data into one card
- [ ] **PEDIT-07** "Is Justice" checkbox opens Justice Details card with animation; unchecking hides fields but does not delete tenure or appointment data
- [ ] **PEDIT-08** Role field (Chief Justice / Associate Justice) lives inside Justice Details card
- [ ] **PEDIT-09** Tenure rows each contain: Seat (Chief / Associate), Appointed by, Appointing president's party, Start date, End date — add / remove rows as before
- [x] **PEDIT-10** Schema change: move `appointed_by` and `appointing_president_party` from `people` table to `court_tenures` table — Alembic migration with data backfill
- [ ] **PEDIT-11** Merge card — unchanged
- [ ] **PEDIT-12** Delete card — unchanged

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
| ALIST-03 | Phase 26 | Pending |
| ALIST-04 | Phase 26 | Pending |
| AEDIT-01 | Phase 26 | Pending |
| AEDIT-02 | Phase 22 | Complete |
| AEDIT-03 | Phase 23 | Complete |
| AEDIT-04 | Phase 23 | Complete |
| AEDIT-05 | Phase 26 | Pending |
| AEDIT-06 | Phase 26 | Pending |
| AEDIT-07 | Phase 26 | Pending |
| AEDIT-08 | Phase 26 | Complete |
| AEDIT-09 | Phase 26 | Complete |
| PDIR-01 | Phase 27 | Pending |
| PDIR-02 | Phase 27 | Pending |
| PDIR-03 | Phase 27 | Pending |
| PDIR-04 | Phase 27 | Pending |
| PDIR-05 | Phase 27 | Pending |
| PDIR-06 | Phase 27 | Pending |
| PDIR-07 | Phase 27 | Pending |
| PEDIT-01 | Phase 27 | Pending |
| PEDIT-02 | Phase 27 | Pending |
| PEDIT-03 | Phase 27 | Pending |
| PEDIT-04 | Phase 27 | Pending |
| PEDIT-05 | Phase 27 | Pending |
| PEDIT-06 | Phase 27 | Pending |
| PEDIT-07 | Phase 27 | Pending |
| PEDIT-08 | Phase 27 | Pending |
| PEDIT-09 | Phase 27 | Pending |
| PEDIT-10 | Phase 22 | Complete |
| PEDIT-11 | Phase 27 | Pending |
| PEDIT-12 | Phase 27 | Pending |

**Coverage:**

- v1.5 requirements: 57 total
- Mapped to phases: 57
- Unmapped: 0 ✓

---
*Requirements defined: 2026-07-02*
*Last updated: 2026-07-02 after roadmap creation — all 57 requirements mapped to Phases 22–28*
