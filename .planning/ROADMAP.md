# Roadmap: SCOTUS Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–4 (shipped 2026-06-15)
- 🚧 **v1.1 Operator Admin Interface** — Phases 5–8 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–4) — SHIPPED 2026-06-15</summary>

**Overview:** Four vertical slices proving the core concept end-to-end — schema and pipeline (Phase 1), speaker resolution (Phase 2), full browseable UI (Phase 3), and WCAG 2.1 AA accessibility (Phase 4).

- [x] Phase 1: Foundation + Proof of Concept (5/5 plans) — completed 2026-06-11
- [x] Phase 2: Speaker Resolution (4/4 plans) — completed 2026-06-12
- [x] Phase 3: Full UI (4/4 plans) — completed 2026-06-13
- [x] Phase 4: Accessibility + Hardening (2/2 plans) — completed 2026-06-15

Full phase details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

### 🚧 v1.1 Operator Admin Interface (In Progress)

**Milestone Goal:** A password-protected operator web interface that drives the ingestion pipeline step-by-step and manages speaker metadata — making it fast to ingest new arguments without touching the CLI.

- [x] **Phase 5: Admin Foundation** — Alembic migration 0003 + FastAPI admin router; prerequisite infrastructure for auth and pipeline runner (completed 2026-06-15)
- [x] **Phase 6: Auth** — Login, session cookie, route guard; all `/admin/*` routes protected (completed 2026-06-16)
- [ ] **Phase 7: Pipeline Runner** — Upload or URL trigger, fire-and-poll step execution, discrepancy review, resumable job state
- [ ] **Phase 8: People Editor** — Directory listing, metadata editing, per-argument participant review

## Phase Details

### Phase 5: Admin Foundation

**Goal**: The DB schema and FastAPI admin router are in place so that auth and pipeline runner can be built on top of them
**Depends on**: Phase 4
**Requirements**: INFRA-A1 (admin_jobs table via Alembic migration 0003 and FastAPI admin router at `api/routers/admin.py` with X-Admin-Token auth — prerequisite infrastructure for Phases 6 and 7)
**Success Criteria** (what must be TRUE):

  1. Alembic migration 0003 runs cleanly and creates the `admin_jobs` table with all required columns
  2. `api/routers/admin.py` is mounted and returns 401 for requests missing a valid `X-Admin-Token` header
  3. All existing v1.0 API routes and the public chat UI continue to function without regression**Plans**: 2 plans (2 waves)
- [x] 05-PLAN-01.md — Schema layer: Alembic migration 0003 (admin_jobs), AdminJob ORM model, ADMIN_TOKEN config field
- [x] 05-PLAN-02.md — FastAPI admin router (/api/admin) with X-Admin-Token dependency + health route, mounted in main.py

### Phase 6: Auth

**Goal**: The operator can log in to the admin area with username and password and all admin routes are protected from unauthenticated access
**Depends on**: Phase 5
**Requirements**: AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):

  1. Operator can navigate to `/admin/login`, submit valid credentials, and land on the admin dashboard
  2. Submitting invalid credentials shows an error message and does not set a session cookie
  3. Any unauthenticated request to any `/admin/*` URL (pages and API endpoints) redirects to `/admin/login`
  4. Operator can click logout and is immediately redirected to `/admin/login`; the prior session cookie no longer grants access

**Plans**: 3 plans (2 waves)

- [x] 06-01-PLAN.md — Session contract + hooks.server.ts route guard + App.Locals typing + env-var docs (AUTH-02)
- [x] 06-02-PLAN.md — Login page UI + form action (credential check, HMAC cookie set, redirect to /admin) (AUTH-01)
- [x] 06-03-PLAN.md — Isolated admin layout shell + dashboard stub + logout action (AUTH-03)

**UI hint**: yes

### Phase 7: Pipeline Runner

**Goal**: The operator can trigger a pipeline run from the browser, monitor each step's progress, review and resolve discrepancies, and resume the job after closing the browser
**Depends on**: Phase 6
**Requirements**: PIPE-12, PIPE-13, PIPE-14, PIPE-15, PIPE-16, PIPE-17
**Success Criteria** (what must be TRUE):

  1. Operator can enter a transcript PDF URL or upload a local PDF file and start a pipeline run
  2. The pipeline run page shows live step cards (Ingest / Parse / Resolve) that update without a page reload; each card advances to the next step automatically when no discrepancies exist
  3. When the resolve step produces discrepancies, the UI pauses and displays them for review; the run does not auto-advance
  4. Operator can confirm or correct each flagged speaker alias match; confirmed matches are written to the `speaker_alias` table
  5. Operator can close the browser, reopen it, and resume an in-progress run exactly where it paused

**Plans**: 5 plans (3 waves)
**Wave 1**

- [x] 07-01-PLAN.md — Backend contract: boto3 + DO Spaces config/service, subprocess spawn util, admin-job Pydantic schemas, admin_jobs service (atomic step-advance guards, resolve, person create) (Wave 1)
- [x] 07-03-PLAN.md — Pipeline subprocess mods: --job-id on ingest/parse/resolve + --spaces-key on ingest; admin_jobs status writes; resolve writes discrepancies and pauses (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 07-02-PLAN.md — FastAPI admin job routes: create (URL/upload), poll endpoint with step-advance side effect, history list, resolve-continue, inline person create (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 07-04-PLAN.md — SvelteKit start page: Pipeline Runner nav link, two-mode New Run form (URL/upload), Recent Runs history table (Wave 3)
- [ ] 07-05-PLAN.md — SvelteKit status page: live polling step cards, inline discrepancy review (confirm/correct/add-person), Continue Resolve, failed-state error panel, resumability (Wave 3)

**UI hint**: yes

### Phase 8: People Editor

**Goal**: The operator can maintain the people directory and fill in missing metadata for participants after a pipeline run
**Depends on**: Phase 7
**Requirements**: PEOPLE-01, PEOPLE-02, PEOPLE-03, PEOPLE-04
**Success Criteria** (what must be TRUE):

  1. Operator can open the people directory and see all person records in a list
  2. Operator can filter the directory to show only people with one or more missing metadata fields
  3. Operator can open a person record and save changes to name, role, bio text, photo URL, and tenure dates
  4. After a pipeline run completes the resolve step, operator can open a per-argument review page showing resolved participants and fill in missing metadata inline

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Foundation + Proof of Concept | v1.0 | 5/5 | Complete | 2026-06-11 |
| 2. Speaker Resolution | v1.0 | 4/4 | Complete | 2026-06-12 |
| 3. Full UI | v1.0 | 4/4 | Complete | 2026-06-13 |
| 4. Accessibility + Hardening | v1.0 | 2/2 | Complete | 2026-06-15 |
| 5. Admin Foundation | v1.1 | 2/2 | Complete   | 2026-06-15 |
| 6. Auth | v1.1 | 3/3 | Complete   | 2026-06-16 |
| 7. Pipeline Runner | v1.1 | 2/5 | In Progress|  |
| 8. People Editor | v1.1 | 0/? | Not started | - |
