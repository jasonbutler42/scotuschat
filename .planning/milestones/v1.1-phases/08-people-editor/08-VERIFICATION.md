---
phase: 08-people-editor
verified: 2026-06-17T00:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 1
human_verification:
  - test: "Confirm SC4 design decision satisfies PEOPLE-04 intent"
    expected: "Operator can open a completed job page, see resolved participants, click 'Review people →', land on the incomplete people directory, and edit a person's missing metadata — the full loop works end-to-end"
    why_human: "SC4 says 'fill in missing metadata inline' but the implementation routes to the global incomplete people directory (/admin/people?incomplete=1) rather than an inline editor on the job page. The design decision D-01 in CONTEXT.md explicitly chose this approach. Whether 'inline' means 'on the same page' or 'within the same session/workflow' is a product judgment, not a code judgment."
    override: "accepted"
    override_by: "operator"
    override_date: "2026-06-18"
    override_rationale: "D-01 in CONTEXT.md explicitly chose the 2-hop approach. The 2-hop path (job page → Review people → /admin/people?incomplete=1 → /admin/people/[id]) satisfies PEOPLE-04 intent."
behavior_unverified_items:
  - truth: "After a pipeline run completes the resolve step, operator can open a per-argument review page showing resolved participants and fill in missing metadata inline"
    test: "Open a completed job page, verify the ParticipantList section renders with actual participant names and roles, click 'Review people →', land on /admin/people?incomplete=1, open a person record, edit metadata, save, and confirm the save round-trips correctly"
    expected: "Participants visible on job page; link navigates to filtered directory; edit form saves correctly"
    why_human: "The codebase wires the participant fetch and render correctly, but the SC says 'inline' editing on the per-argument page — the implementation provides a 2-hop path (job page → Review people link → /admin/people?incomplete=1 → /admin/people/[id]) rather than inline editing on the job page. D-01 in CONTEXT.md deliberately chose this approach. Codebase evidence cannot determine if this design decision satisfies the SC intent."
---

# Phase 8: People Editor Verification Report

**Phase Goal:** The operator can maintain the people directory and fill in missing metadata for participants after a pipeline run
**Verified:** 2026-06-17
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Operator can open the people directory and see all person records in a list | VERIFIED | `app/src/routes/admin/people/+page.server.ts` fetches real data from `GET /api/admin/people`; `+page.svelte` renders `<table>` with Name/Role/Missing fields/Edit columns and iterates `{#each data.people as person}` |
| 2 | Operator can filter the directory to show only people with one or more missing metadata fields | VERIFIED | Toggle button with `role="switch"` calls `goto('/admin/people?incomplete=1')`; `checked = $derived(data.incomplete ?? false)` pre-checks from URL; backend `list_people(incomplete=True)` applies `or_(Person.role_id.is_(None), Person.bio_text.is_(None), Person.photo_url.is_(None))` filter; `_missing_fields()` returns `["role","bio","photo"]` ordered list verified by unit import test |
| 3 | Operator can open a person record and save changes to name, role, bio text, photo URL, and tenure dates | VERIFIED | `app/src/routes/admin/people/[id]/+page.svelte` renders three section cards (Basic Info, Bio & Photo, Court Tenure); `actions.save` PATCHes `FASTAPI_BASE_URL/api/admin/people/{id}` with JSON body; `actions.createRole` POSTs to `/api/admin/roles`; tenure rows managed with `$state<TenureRow[]>` push/splice and hidden JSON field; 303 redirect on success re-runs load |
| 4 | After a pipeline run completes the resolve step, operator can open a per-argument review page showing resolved participants and fill in missing metadata inline | PRESENT_BEHAVIOR_UNVERIFIED | ParticipantList section exists in `+page.svelte` at `/admin/pipeline/[job_id]`, guarded by `data.job.status === 'completed' && data.participants.length > 0`; participants fetched from `GET /api/admin/jobs/{job_id}/participants`; "Review people →" link goes to `/admin/people?incomplete=1`. However SC4 says "fill in missing metadata inline" — the implementation routes to the global incomplete directory rather than providing inline editing on the job page. This was a deliberate design decision (D-01 in CONTEXT.md) but requires human confirmation that the design satisfies the SC intent. |

**Score:** 3/4 truths verified (1 present + wired, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0005_add_person_metadata.py` | Migration adding bio_text + photo_url to people | VERIFIED | `revision = "0005"`, `down_revision = "0004"`, both columns added as nullable, no Base.metadata.create_all |
| `api/models/models.py` | Person model with bio_text + photo_url columns | VERIFIED | `bio_text = Column(Text, nullable=True)` and `photo_url = Column(String(500), nullable=True)` present at lines 96–97 |
| `api/schemas/admin_people.py` | PersonListItem, PersonDetail, PersonUpdate, TenureRow, RoleCreate, RoleResponse, ParticipantItem | VERIFIED | All 7 classes present, substantive Pydantic v2 models with correct field types and `from_attributes=True` on response models |
| `api/services/admin_people.py` | list_people, get_person_detail, update_person, create_role, list_participants_for_job | VERIFIED | All 5 public functions + 2 private helpers fully implemented; `execution_options(synchronize_session=False)` on delete; empty-string normalization in `update_person`; date parsing with `fromisoformat` in `_replace_tenures` |
| `api/routers/admin.py` | GET /people (incomplete filter), GET /people/{id}, PATCH /people/{id}, POST /roles, GET /jobs/{id}/participants | VERIFIED | All 5 routes confirmed via `app.openapi()` spec traversal: `GET /api/admin/people`, `GET /api/admin/people/{person_id}`, `PATCH /api/admin/people/{person_id}`, `POST /api/admin/roles`, `GET /api/admin/jobs/{job_id}/participants` |
| `api/tests/test_admin_people.py` | Auth tests (no DB) + DB-guarded shape tests | VERIFIED | 5 passed, 4 skipped in 1.08s — auth tests assert 401 on all 4 new admin paths with wrong token; DB tests skip cleanly when DATABASE_URL not configured |
| `app/src/routes/admin/people/+page.server.ts` | Load function fetches people with optional incomplete filter | VERIFIED | Imports `ADMIN_TOKEN, FASTAPI_BASE_URL` from `$env/static/private`; reads `incomplete` from `url.searchParams.get('incomplete') === '1'`; degrades to `[]` on non-OK; returns `{ people, incomplete }` |
| `app/src/routes/admin/people/+page.svelte` | PeopleTable + IncompleteToggle + empty states | VERIFIED | Table with `<th scope="col">` headers; toggle button with `role="switch"` and `aria-checked`; amber MissingFieldChip spans; both empty states with exact UI-SPEC copy; no `{@html}` |
| `app/src/routes/admin/+layout.svelte` | Active People Editor nav link | VERIFIED | `<a href="/admin/people">People Editor</a>` present at line 34–39; no `aria-disabled` on the People Editor element |
| `app/src/routes/admin/people/[id]/+page.server.ts` | load + save action (PATCH) + createRole action (POST /roles) | VERIFIED | `load` fetches person detail and derives roles list from people list; `actions.save` converts empty role_id to null, parses tenures JSON, strips `_key`, PATCHes FastAPI, redirects 303; `actions.createRole` POSTs to `/api/admin/roles`, returns `{ roleCreated: true, role }` |
| `app/src/routes/admin/people/[id]/+page.svelte` | PersonEditForm: three sections + Save | VERIFIED | Three section cards (Basic Info, Bio & Photo, Court Tenure); RoleSelect with sentinel "＋ Add new role"; AddRoleInlineForm with `use:enhance`; `$state<TenureRow[]>` with keyed `{#each (row._key)}`; hidden `name="tenures"` JSON field; SaveChangesButton with "Saving…" state; no `{@html}` |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Extended load that fetches participants when job completed | VERIFIED | Conditional fetch when `job.status === 'completed' && job.argument_id != null`; graceful degrade to `[]` on error; returns `participants` alongside existing fields |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | ParticipantList section + Review people link | VERIFIED | Section guarded by `data.job.status === 'completed' && data.participants.length > 0`; pluralized heading; `<ul><li>` list with full_name + role_name; "Review people →" link to `/admin/people?incomplete=1` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `alembic/versions/0005_add_person_metadata.py` | `api/models/models.py` | migration adds DB columns; model adds matching ORM attributes | WIRED | Both bio_text and photo_url present in migration upgrade() and Person ORM class |
| `api/routers/admin.py` | `api/services/admin_people.py` | `from api.services import admin_people as people_service` | WIRED | Import confirmed at line 63; all 5 route handlers call `people_service.*` functions |
| `api/services/admin_people.py` | `api/models/models.py` | delete-and-reinsert CourtTenure rows on PATCH | WIRED | `CourtTenure` imported and used in `_replace_tenures`; `delete(CourtTenure).where(...)` confirmed |
| `app/src/routes/admin/people/+page.server.ts` | `api/routers/admin.py` | fetch `GET /api/admin/people(?incomplete=1)` with X-Admin-Token | WIRED | `${FASTAPI_BASE_URL}/api/admin/people${incomplete ? '?incomplete=1' : ''}` with `X-Admin-Token` header |
| `app/src/routes/admin/people/+page.svelte` | `app/src/routes/admin/people/+page.server.ts` | `data.people` and `data.incomplete` from load | WIRED | `let { data } = $props()`; `data.people` iterated in `{#each}`, `data.incomplete` drives toggle state |
| `app/src/routes/admin/people/[id]/+page.server.ts` | `api/routers/admin.py` | PATCH `/api/admin/people/{id}` and POST `/api/admin/roles` with X-Admin-Token | WIRED | `actions.save` fetches `PATCH /api/admin/people/${params.id}`; `actions.createRole` POSTs to `/api/admin/roles`; both with `X-Admin-Token` |
| `app/src/routes/admin/people/[id]/+page.svelte` | `app/src/routes/admin/people/[id]/+page.server.ts` | form POST → save action; tenure rows serialized as hidden JSON field | WIRED | `<form action="?/save">` present; `<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)}>` confirmed |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | `api/routers/admin.py` | fetch `GET /api/admin/jobs/{id}/participants` when status completed | WIRED | Conditional fetch at line 54–59 with `X-Admin-Token`; `participants` added to return value |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `app/src/routes/admin/people/+page.server.ts` | "Review people →" link navigates to `/admin/people?incomplete=1` | WIRED | `<a href="/admin/people?incomplete=1">Review people →</a>` at line 776 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `app/src/routes/admin/people/+page.svelte` | `data.people` | `list_people()` → `select(Person, Role.name).outerjoin(Role)` | Yes — ORM query with outerjoin, no hardcoded empty returns | FLOWING |
| `app/src/routes/admin/people/[id]/+page.svelte` | `data.person` | `get_person_detail()` → `select(Person, Role.name).outerjoin(Role).where(Person.id == person_id)` | Yes — ORM query with tenure rows loaded | FLOWING |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `data.participants` | `list_participants_for_job()` → `select(ArgumentParticipant.person_id, ...).join(Person).outerjoin(Role).where(...)` | Yes — real DB join; [] only on non-completed job or error | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Schemas import cleanly | `.venv/Scripts/python.exe -c "from api.schemas.admin_people import PersonListItem, ..."` | Schemas OK | PASS |
| `_missing_fields` returns correct order | Unit test via venv Python: all None → `['role','bio','photo']`; only bio None → `['bio']` | Both asserted correctly | PASS |
| Person ORM has bio_text + photo_url | `.venv/Scripts/python.exe -c "from api.models.models import Person; assert hasattr(Person,'bio_text')"` | Person model OK | PASS |
| Auth tests pass (5 passed, 4 skipped) | `.venv/Scripts/python -m pytest api/tests/test_admin_people.py -x -q` | 5 passed, 4 skipped in 1.08s | PASS |
| All 5 admin routes registered | `app.openapi()` spec traversal | All 4 paths found with correct methods (GET/PATCH on people/{id}, POST on roles, GET on participants) | PASS |
| No Base.metadata.create_all in changed files | grep across all 4 changed Python files | No matches | PASS |
| migration revision = "0005" | File read + AST check | `revision: str = "0005"`, `down_revision = "0004"` | PASS |
| No @html in frontend files | grep across 4 Svelte files | No matches | PASS |
| No PUBLIC_ env vars in server files | grep across 2 +page.server.ts files | No matches | PASS |
| `execution_options(synchronize_session=False)` present | grep admin_people.py | 1 actual call on `delete(CourtTenure)` — only delete statement in the file | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PEOPLE-01 | 08-02, 08-03 | Operator can view all people in a directory listing | SATISFIED | `/admin/people` renders table from `list_people()` with Name/Role/Missing/Edit columns |
| PEOPLE-02 | 08-02, 08-03 | Operator can filter directory to show only people with missing metadata fields | SATISFIED | Toggle drives `?incomplete=1`; backend `or_()` IS NULL filter; `_missing_fields()` derives chip labels |
| PEOPLE-03 | 08-01, 08-02, 08-04 | Operator can edit name, role, bio text, photo URL, and tenure dates | SATISFIED | Full edit form at `/admin/people/[id]`; PATCH endpoint with delete-and-reinsert tenure; inline role create |
| PEOPLE-04 | 08-02, 08-05 | After pipeline run completes resolve, operator can review resolved participants and fill in missing metadata inline | NEEDS HUMAN | Participant list on job detail page confirmed; "Review people →" link routes to incomplete directory rather than inline edit on same page — see Human Verification section |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/+layout.svelte` | 25–27 | Stale comment: "Disabled placeholder nav items — rendered as `<span>` not `<a>`..." — the comment describes Phase 6 behavior but both nav items are now `<a>` tags | Warning | No functional impact; comment is misleading for future readers but does not affect behavior |

### Human Verification Required

#### 1. SC4 Design Decision: "Fill in missing metadata inline"

**Test:** After a pipeline run completes, open the job detail page at `/admin/pipeline/[job_id]`. Confirm the ParticipantList section renders with actual participant names and roles. Click "Review people →" and confirm you land on `/admin/people?incomplete=1`. From there, open a person record and confirm you can edit and save their metadata. Confirm this 2-hop flow satisfies the product intent for PEOPLE-04.

**Expected:** The full loop works end-to-end: job page shows participants → link to incomplete directory → operator edits missing metadata in person edit form → data saved.

**Why human:** SC4 says "fill in missing metadata inline" — the CONTEXT.md (D-01) explicitly decided "No dedicated participants page. PEOPLE-04 is satisfied by the incomplete filter in /admin/people." The implementation provides a 2-hop workflow rather than inline editing on the job page. Whether "inline" means "on the same page" or "within the same session/workflow" is a product judgment call. The codebase is fully wired and functional; this is a requirements interpretation question, not a code defect.

**Decision options:**
- **Accept** — the 2-hop workflow satisfies PEOPLE-04; operator can review participants and then edit metadata in one coherent flow.
- **Add override** in VERIFICATION.md frontmatter to accept this deviation:
  ```yaml
  overrides:
    - must_have: "After a pipeline run completes the resolve step, operator can open a per-argument review page showing resolved participants and fill in missing metadata inline"
      reason: "D-01 deliberately chose the incomplete-filter approach over inline editing on the job page. Operator reviews participants on the job page and edits via the people directory — the full workflow is complete."
      accepted_by: "{your name}"
      accepted_at: "{ISO timestamp}"
  ```
- **Reject** — implement inline metadata editing directly on the job detail page (would require significant additional work).

### Gaps Summary

No functional gaps found. All artifacts exist, are substantive, and are fully wired. The only open item is a product judgment call on SC4: the design decision to satisfy PEOPLE-04 via a 2-hop workflow (job page participants → Review people link → people directory) rather than inline editing on the job page. This was deliberately chosen in CONTEXT.md D-01 but the SC wording says "inline." Human confirmation is needed to accept or reject this design decision.

---

_Verified: 2026-06-17_
_Verifier: Claude (gsd-verifier)_
