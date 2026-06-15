# Roadmap: SCOTUS Chat

## Overview

SCOTUS Chat is built in four vertical slices. Phase 1 proves the end-to-end concept — schema, ingest, parse, a minimal API, and a minimal chat view — so the core value is runnable on day one. Phase 2 wires in speaker resolution so every utterance carries a named, sided speaker. Phase 3 completes the UI surface (case list, argument header, section nav, shareable URLs, avatars). Phase 4 hardens accessibility and applies polish so the product meets WCAG 2.1 AA throughout.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation + Proof of Concept** - Schema, ingest, parse, minimal API, minimal chat view — end-to-end on one hand-picked case
- [x] **Phase 2: Speaker Resolution** - Alias table seeded, resolve step wired, every utterance carries a named and sided speaker in the UI
- [x] **Phase 3: Full UI** - Case list, argument header, section nav, shareable URLs, avatars — complete browseable product
- [ ] **Phase 4: Accessibility + Hardening** - WCAG 2.1 AA throughout, full keyboard navigation, focus management, apolitical framing verified

## Phase Details

### Phase 1: Foundation + Proof of Concept
**Goal**: An operator can ingest a real SCOTUS transcript PDF, run the parse step, hit a live API endpoint, and see the oral argument rendered as a two-sided chat in a browser — proving the core concept end-to-end on a single hand-picked case
**Mode**: mvp
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-10, PIPE-11, API-01, UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Operator runs the ingest CLI command with a PDF URL and the database contains case, argument, and pipeline_run records with status `completed` (ingest is synchronous — the run completes immediately)
  2. Operator runs the parse CLI command and the database contains ordered utterance rows with `pipeline_run_id` set, `is_stage_direction` correctly classified, and `person_id` null
  3. Re-running ingest or parse produces new rows linked to a new `pipeline_run_id`; prior run rows are not deleted
  4. `GET /arguments/{id}/utterances` returns ordered utterances for the hand-picked case in a running FastAPI server
  5. A browser pointed at the SvelteKit dev server renders the argument as a two-sided chat: Justice utterances on the bench side, advocate utterances on the advocate side, stage directions visually distinct from speech bubbles
**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — SvelteKit scaffold, component stubs, dev-start.ps1
- [x] 01-02-PLAN.md — PostgreSQL schema + Alembic migration 0001
- [x] 01-03-PLAN.md — Pipeline ingest command
- [x] 01-04-PLAN.md — Pipeline parse command
- [x] 01-05-PLAN.md — FastAPI endpoint + SvelteKit chat view

### Phase 2: Speaker Resolution
**Goal**: Every utterance in the chat view shows a real speaker name and role label — not a raw label — so a reader can immediately tell who is speaking and which side they represent
**Mode**: mvp
**Depends on**: Phase 1
**Requirements**: PIPE-07, PIPE-08, PIPE-09, API-03
**Success Criteria** (what must be TRUE):
  1. The `speaker_alias` table is seeded with known Justice surname patterns, role-only labels (e.g. "GENERAL", "CHIEF JUSTICE"), and counsel-of-record patterns for the hand-picked cases
  2. Operator runs the resolve CLI command and utterances for confirmed matches have `person_id` populated; low-confidence matches are gated as `needs_review` on `pipeline_run` and never silently committed
  3. `GET /people/{id}` returns a person record with name and role
  4. The chat view shows each utterance attributed to a resolved speaker name and role label (no raw labels visible for confirmed matches)
**Plans**: 4 plans

Plans:
**Wave 1**
- [ ] 02-01-PLAN.md — Alembic migration 0002_add_speaker_alias + SpeakerAlias ORM model + test_schema update
**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 02-02-PLAN.md — seed-aliases + resolve pipeline commands + __main__.py wiring + Wave 0 test stubs
- [ ] 02-03-PLAN.md — GET /people/{id} API (router + service + schema) + utterances JOIN extension + Wave 0 test stubs
**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 02-04-PLAN.md — ChatBubble.svelte resolved speaker name + role label display + human verification

**Cross-cutting constraints:**
- Alembic is sole DDL authority — no `Base.metadata.create_all` anywhere
- Pipeline steps (seed-aliases, resolve) are CLI-only — never HTTP endpoints
- `utterances.raw_speaker_label` is write-once (parse step); resolve only writes `person_id`

### Phase 3: Full UI
**Goal**: A user can browse all loaded cases, open any argument, see a complete argument header with the speaker roster, jump between argument sections, share a stable URL that renders correctly on page refresh, and see speaker avatars with initials fallback
**Mode**: mvp
**Depends on**: Phase 2
**Requirements**: API-02, UI-04, UI-05, UI-06, UI-07, UI-08
**Success Criteria** (what must be TRUE):
  1. `GET /cases` returns the list of loaded cases; the SvelteKit case list page renders them and navigating to any case opens its argument
  2. The argument view shows a header with case name, docket number, date argued, and the full speaker roster
  3. Each speaker bubble shows an avatar; when no `photo_url` is available the avatar renders as styled initials — no broken images
  4. Arguments are accessible at `/cases/{slug}/arguments/{id}` and the page renders correctly on hard refresh (SSR), not just client-side navigation
  5. A section navigation rail shows Petitioner / Respondent / Rebuttal / Amicus sections and clicking a section scrolls the view to that point in the argument
**Plans**: 4 plans

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — GET /cases API endpoint (schema + service + router + main.py) + Wave 0 static-analysis tests
**Wave 2** *(blocked on Wave 1 completion — parallel plans)*
- [x] 03-02-PLAN.md — Case list page (/cases) + intermediate /cases/[slug] page + global nav update
- [x] 03-03-PLAN.md — ChatBubble avatar circle (32px initials, D-06/D-07/D-08) + bench/advocate alignment flip (D-05)
**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-04-PLAN.md — Argument view restructure: two-column CSS Grid + SectionRail.svelte + speaker roster in header + section anchor IDs

**Cross-cutting constraints:**
- No schema migrations in Phase 3 — all data available from existing tables
- No new npm or pip packages — all UI uses native browser APIs and existing SvelteKit
- FASTAPI_BASE_URL always from $env/static/private — never PUBLIC_ prefix
- Apolitical framing: roster columns use identical name styling (#94a3b8) for both bench and advocates

### Phase 4: Accessibility + Hardening
**Goal**: Every page passes WCAG 2.1 AA color contrast, is fully keyboard navigable, and correctly manages focus — so any user, regardless of input method or visual ability, can read and navigate a full oral argument
**Mode**: mvp
**Depends on**: Phase 3
**Requirements**: A11Y-01, A11Y-02, A11Y-03, A11Y-04
**Success Criteria** (what must be TRUE):
  1. All text and UI components pass 4.5:1 contrast ratio (WCAG 2.1 AA) as verified by an automated contrast check tool
  2. A user navigating entirely by keyboard can reach every interactive element — case list, argument view, section nav rail, avatar links — with no mouse required
  3. Speaker side differentiation (bench vs. advocate) is conveyed by layout position alone and remains clear when viewed in a single-color or high-contrast display mode
  4. Focus is visibly managed for any overlays or interactive components: focus moves to the opened element on activation and returns to the trigger on close
**Plans**: 2 plans

Plans:
**Wave 1**
- [ ] 04-01-PLAN.md — Color fixes, global focus ring, ChatBubble ARIA semantics, StageDirection role, SectionRail nav label
**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 04-02-PLAN.md — MobileNavBar.svelte (new component) + HTML landmarks on all pages + roster color fix + mobile nav integration

**Cross-cutting constraints:**
- No new npm packages — all Phase 4 work uses native browser APIs and existing SvelteKit primitives
- After Phase 4 completes: #475569 must not appear anywhere in app/src/
- Svelte 5 Runes only — $props(), $state(), $derived(), $effect() — no export let, no $: blocks

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation + Proof of Concept | 5/5 | Complete | 2026-06-11 |
| 2. Speaker Resolution | 4/4 | Complete | 2026-06-12 |
| 3. Full UI | 4/4 | Complete | 2026-06-13 |
| 4. Accessibility + Hardening | 0/2 | Not started | - |
