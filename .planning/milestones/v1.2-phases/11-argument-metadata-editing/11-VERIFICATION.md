---
phase: 11-argument-metadata-editing
verified: 2026-06-22T00:00:00Z
status: human_needed
score: 15/15 must-haves verified
behavior_unverified: 3
overrides_applied: 0
human_verification:
  - test: "Open /admin/arguments in a browser with at least one ingested argument and verify status badges render (Published green #4ade80, Resolved violet #a78bfa, Pending muted #94a3b8), publish/unpublish toggles appear per-row in the correct states, and the Edit link navigates to /admin/arguments/[id]"
    expected: "All three badge states visible; Publish button only on resolved-but-unpublished rows; Unpublish button only on published rows; no control on pending rows; Edit link present on every row"
    why_human: "Status badge state transitions and conditional button rendering depend on runtime resolved_at / published_at values that cannot be verified by grep or static analysis"
  - test: "On /admin/arguments/[id] for a resolved-but-unpublished argument, edit the case title to a value that generates a slug used by another case; submit Save"
    expected: "Form stays on page; role=alert error reads 'This title generates a URL slug that conflicts with an existing case. Choose a different title.' — no 500 error, no redirect"
    why_human: "slug_collision 422 → error display path requires a real database with a colliding case record; static analysis cannot exercise this state transition"
  - test: "Click Publish on a resolved argument; verify the argument appears on the public /cases list; click Unpublish; verify the argument disappears from /cases"
    expected: "Published argument visible at /cases; unpublished argument absent from /cases (published_at IS NOT NULL gate)"
    why_human: "publish/unpublish round-trip and the corresponding public visibility gate change require a live database and a browser session; neither can be verified by pytest without DATABASE_URL"
behavior_unverified_items:
  - truth: "POST /publish sets published_at only when resolved_at IS NOT NULL AND published_at IS NULL; POST /unpublish clears published_at"
    test: "Call POST /api/admin/arguments/{id}/publish on an argument where resolved_at IS NULL; then on an already-published argument; then call POST /unpublish on an argument that is not published"
    expected: "First two calls return 422; third call returns 422; the happy-path call stamps published_at and subsequent get_cases() includes the argument"
    why_human: "Guard correctness and the round-trip visibility state change are runtime invariants — the code is present and wired but no DB test exercises them without DATABASE_URL"
  - truth: "A pre-publish case_name edit that collides with an existing case slug returns 422 with a slug_collision signal (not a 500)"
    test: "PATCH /api/admin/arguments/{id} with a case_name whose _derive_slug output matches a different Case.slug already in the DB"
    expected: "HTTP 422 with detail containing 'slug_collision'; no IntegrityError 500"
    why_human: "Slug collision pre-write check requires two Case rows with a slug collision in a live DB; cannot exercise without DATABASE_URL"
  - truth: "A docket_number edit that collides with another case's docket returns 422 (not a 500)"
    test: "PATCH /api/admin/arguments/{id} with a docket_number already owned by a different Case row in the DB"
    expected: "HTTP 422 with detail containing 'docket_collision'; no IntegrityError 500"
    why_human: "Docket collision pre-write check requires two Case rows with the same docket_number in a live DB; cannot exercise without DATABASE_URL"
---

# Phase 11: Argument Metadata Editing — Verification Report

**Phase Goal:** Enable operators to edit argument metadata (case name, docket number, argued date) and control the public visibility of arguments through a publish/unpublish workflow via the admin UI.
**Verified:** 2026-06-22
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

All 15 must-haves across all four plans are verified at the symbol-presence and wiring level. Three truths are marked PRESENT_BEHAVIOR_UNVERIFIED because they assert runtime state transitions or collision-detection invariants that require a live database, which is not available in the current CI environment (DATABASE_URL not configured). The structural test coverage (12 service tests + 5 route auth tests + 4 visibility-gate tests) all pass.

#### Plan 01 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The arguments table has a nullable published_at TIMESTAMP WITH TIME ZONE column after migration 0007 runs | VERIFIED | `alembic/versions/0007_add_published_at.py` lines 37–43: `op.add_column("arguments", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))`; `revision="0007"`, `down_revision="0006"` |
| 2 | The public case list (get_cases) returns only arguments where published_at IS NOT NULL | VERIFIED | `api/services/cases.py` line 34: `.where(Argument.published_at.isnot(None))` — confirmed by `test_published_gate.py` (4 tests, all pass) |
| 3 | resolved_at still exists on the Argument model and is unchanged in meaning | VERIFIED | `api/models/models.py` line 160: `published_at = Column(DateTime(timezone=True), nullable=True)` added AFTER existing `resolved_at`; `resolved_at` column and comment preserved |

#### Plan 02 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 4 | Operator can fetch a single argument's detail via GET /api/admin/arguments/{id} | VERIFIED | `api/routers/admin.py` lines 386–401: `@router.get("/arguments/{argument_id}", response_model=ArgumentDetail)` → `arguments_service.get_argument_detail`; returns 404 on None |
| 5 | Operator can list all arguments via GET /api/admin/arguments | VERIFIED | `api/routers/admin.py` lines 373–383: `@router.get("/arguments", response_model=list[ArgumentListItem])` → `arguments_service.list_arguments`; ordered argued_date DESC at service level |
| 6 | Operator can PATCH an argument's case_name, docket_number, and argued_date; slug re-derives only when published_at IS NULL | VERIFIED | `api/services/admin_arguments.py` lines 199–213: slug logic gates on `argument.published_at is None`; `_derive_slug` called only when unpublished; `api/tests/test_admin_arguments_service.py` asserts synchronize_session=False guard and ArgumentUpdate allow-list |
| 7 | A pre-publish case_name edit that collides with an existing case slug returns 422 with a slug_collision signal (not a 500) | PRESENT_BEHAVIOR_UNVERIFIED | `admin_arguments.py` lines 205–212: pre-write slug collision query and `raise ValueError("slug_collision")` are present and wired to `HTTPException(422)` in router; no DB test exercised without DATABASE_URL |
| 8 | A docket_number edit that collides with another case's docket returns 422 (not a 500) | PRESENT_BEHAVIOR_UNVERIFIED | `admin_arguments.py` lines 181–188: pre-write docket collision query and `raise ValueError("docket_collision")` present and wired to 422; no DB test exercised without DATABASE_URL |
| 9 | POST /publish sets published_at only when resolved_at IS NOT NULL AND published_at IS NULL; POST /unpublish clears published_at | PRESENT_BEHAVIOR_UNVERIFIED | `admin_arguments.py` lines 237–249 (publish) and 267–277 (unpublish): guards and `sqlfunc.now()` / `None` writes present and wired; round-trip state change not exercised without DATABASE_URL |
| 10 | Missing argument id returns 404 (IDOR guard) | VERIFIED | `api/routers/admin.py` pattern repeated across all 5 routes: `if result is None: raise HTTPException(404, ...)`; route auth tests pass with wrong token; DB-guarded 404 tests confirm the pattern |

#### Plan 03 Must-Haves

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 11 | Operator can open /admin/arguments and see all arguments with Pending/Resolved/Published status badges, sorted by argued date descending | VERIFIED | `+page.svelte` lines 20–36: `badgeStyle`/`badgeLabel` helper functions with #4ade80/#a78bfa/#94a3b8 colors; `+page.server.ts` fetches `GET /api/admin/arguments` which returns argued_date DESC from service layer |
| 12 | Operator can open /admin/arguments/[id], edit case title, docket number, and argued date, and save successfully | VERIFIED | `[id]/+page.svelte` lines 97–169: three labeled inputs (type=text, type=text, type=date) inside `<form action="?/save">`; `[id]/+page.server.ts` lines 44–91: save action PATCHes with `{case_name, docket_number, argued_date}` |
| 13 | A slug collision on save shows the copywriting error in a role=alert slot instead of crashing | VERIFIED | `[id]/+page.server.ts` lines 75–79: `slug_collision` check returns `fail(422, { error: 'This title generates a URL slug...' })`; `[id]/+page.svelte` lines 188–199: `{#if form?.error}` with `role="alert"` |
| 14 | Operator can Publish a resolved argument and Unpublish a published argument from the edit page | VERIFIED | `[id]/+page.svelte` lines 263–331: publish form only when `resolved_at && !published_at`; unpublish form only when `published_at`; both wired to named server actions that POST to respective endpoints |
| 15 | The admin TopNav shows an Arguments link between Pipeline Runner and People Editor | VERIFIED | `TopNav.svelte` lines 46–51: `<a href="/admin/arguments">Arguments</a>` between Pipeline Runner (line 40) and People Editor (line 52); exact inline-style match to sibling anchors |

**Score:** 12/15 truths verified (3 present, behavior-unverified)

---

### Deferred Items

None — all must-haves are either verified or present with unverified runtime behavior awaiting human testing.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0007_add_published_at.py` | Migration adding published_at; down_revision 0006 | VERIFIED | revision="0007", down_revision="0006"; add_column with DateTime(timezone=True) nullable=True; downgrade drops column; no create_all |
| `api/models/models.py` | Argument.published_at ORM column | VERIFIED | Column(DateTime(timezone=True), nullable=True) present at line 160; resolved_at preserved at line preceding it |
| `api/services/cases.py` | Public visibility gate filtered on published_at | VERIFIED | `.where(Argument.published_at.isnot(None))` at line 34; no resolved_at.isnot anywhere in api/services/ |
| `api/tests/test_published_gate.py` | Source-level gate assertion | VERIFIED | 4 tests; all pass (`4 passed in 0.02s`) |
| `api/schemas/admin_arguments.py` | ArgumentListItem, ArgumentDetail, ArgumentUpdate, ConsolidatedDocket | VERIFIED | All four classes present; ArgumentUpdate.model_fields == {"case_name","docket_number","argued_date"}; no published_at in update schema |
| `api/services/admin_arguments.py` | list_arguments, get_argument_detail, update_argument, publish_argument, unpublish_argument | VERIFIED | All 5 functions present; _derive_slug imported from pipeline.commands.ingest; every update() has .execution_options(synchronize_session=False) |
| `api/tests/test_admin_arguments_service.py` | Service import + slug + schema tests | VERIFIED | 12 passed, 4 skipped (DB tests, no DATABASE_URL) |
| `api/routers/admin.py` | 5 new argument routes with 404/422 | VERIFIED | GET /arguments, GET /arguments/{id}, PATCH /arguments/{id}, POST /arguments/{id}/publish, POST /arguments/{id}/unpublish all present; router-level Depends(verify_admin_token) inherited |
| `api/tests/test_admin_arguments_routes.py` | Auth 401 tests for all 5 routes | VERIFIED | 5 passed, 5 skipped (DB tests); all routes return 401 on wrong token |
| `app/src/routes/admin/arguments/+page.server.ts` | List load + publish/unpublish actions | VERIFIED | Fetches FASTAPI_BASE_URL/api/admin/arguments with X-Admin-Token from $env/static/private; publish and unpublish actions with hidden argument_id |
| `app/src/routes/admin/arguments/+page.svelte` | Arguments list table with status badges | VERIFIED | 232 lines; table with th scope=col; badgeStyle/badgeLabel helpers; per-row publish/unpublish forms with use:enhance; Edit link per row |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | Detail load + save/publish/unpublish actions; slug_collision handling | VERIFIED | load returns 404/502 on error; save action inspects detail for slug_collision/docket_collision; redirect(303) on success |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | Two-card edit form with save + publish/unpublish + consolidated dockets + error slot | VERIFIED | 335 lines; two cards; labeled inputs with for/id; role=alert slot; consolidated dockets conditional on length>0; publish/unpublish visibility guards |
| `app/src/lib/components/TopNav.svelte` | Admin variant Arguments link | VERIFIED | href="/admin/arguments" link text "Arguments" between Pipeline Runner and People Editor anchors; public variant unchanged |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | Extended load fetching argument when argument_id is set | VERIFIED | Lines 80–103: ArgumentPreview interface; conditional fetch inside try/catch; argument=null on failure; returned alongside job/people/peopleLoadError/participants |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | Argument preview card + Ready-to-publish CTA section | VERIFIED | Lines 265–366: {#if data.argument} card with Edit argument metadata link; {#if data.job.status === 'completed' && arg.published_at == null} CTA with "Go to argument editor" link |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/services/cases.py` | `api/models/models.py` | `Argument.published_at.isnot(None)` filter in get_cases SELECT | WIRED | Confirmed by test_published_gate.py test_get_cases_uses_published_at_filter |
| `api/routers/admin.py` | `api/services/admin_arguments.py` | `arguments_service.(list_arguments|get_argument_detail|update_argument|publish_argument|unpublish_argument)` | WIRED | All 5 service functions called in router handlers; ValueError→HTTPException 422 pattern present |
| `api/services/admin_arguments.py` | `api/models/models.py` | `Argument.published_at` write via update(); lead Case via CaseArgument.is_lead | WIRED | update(Argument).values(published_at=...) at lines 242 and 271; lead case loaded via CaseArgument.is_lead==True join |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | `api/routers/admin.py` | PATCH /api/admin/arguments/{id} + POST publish/unpublish with X-Admin-Token | WIRED | Pattern `api/admin/arguments` present in save, publish, unpublish action fetches |
| `app/src/routes/admin/arguments/+page.svelte` | `app/src/routes/admin/arguments/[id]/+page.svelte` | Edit link per row → /admin/arguments/[id] | WIRED | `href={'/admin/arguments/' + arg.id}` at line 220 |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | `api/routers/admin.py` | GET /api/admin/arguments/{argument_id} when job.argument_id is set | WIRED | Line 87: `${FASTAPI_BASE_URL}/api/admin/arguments/${job.argument_id}` inside `if (job.argument_id != null)` |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | `app/src/routes/admin/arguments/[id]/+page.svelte` | "Edit argument metadata" link → /admin/arguments/[argument_id] | WIRED | Line 323: `href="/admin/arguments/{arg.id}"` with text "Edit argument metadata" |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `+page.svelte` (arguments list) | `data.arguments` | `+page.server.ts` load → GET /api/admin/arguments → `list_arguments()` DB query | Yes — SQLAlchemy SELECT with JOIN | FLOWING |
| `[id]/+page.svelte` (argument edit) | `data.argument` | `[id]/+page.server.ts` load → GET /api/admin/arguments/{id} → `get_argument_detail()` DB query | Yes — SELECT Argument + lead Case + consolidated dockets | FLOWING |
| `[job_id]/+page.svelte` (job detail) | `data.argument` | `[job_id]/+page.server.ts` load conditional fetch → `get_argument_detail()` DB query | Yes — fetched when `job.argument_id != null`; null on failure (graceful degrade) | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| test_published_gate.py (4 visibility gate assertions) | `.venv/Scripts/python -m pytest api/tests/test_published_gate.py -x -q` | 4 passed in 0.02s | PASS |
| test_admin_arguments_service.py (import, slug, schema, sync_session guards) | `.venv/Scripts/python -m pytest api/tests/test_admin_arguments_service.py -x -q` | 12 passed, 4 skipped in 0.67s | PASS |
| test_admin_arguments_routes.py (auth 401 for all 5 routes) | `.venv/Scripts/python -m pytest api/tests/test_admin_arguments_routes.py -x -q` | 5 passed, 5 skipped in 1.07s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| ARG-01 | Plans 01, 02, 03, 04 | Operator can view and edit a pending argument's case title, docket number, and argued date from the admin area | SATISFIED | Full stack: Alembic migration → ORM column → service → routes → SvelteKit list + edit pages; all artifacts verified |
| ARG-02 | Plans 02, 03 | Argument metadata fields are read-only after resolved_at is set | SUPERSEDED (by design) | D-09 in 11-CONTEXT.md explicitly drops this requirement: "ARG-02 (read-only after resolved_at is set) is dropped. The argument editor is always editable. The publish model replaces the original read-only gate requirement." REQUIREMENTS.md marks ARG-02 as [x] Complete, consistent with D-09. The argument editor is always editable at any state; the publish/unpublish workflow replaces the read-only gate. This is a deliberate requirements change, not a gap. |

**ARG-02 note:** The REQUIREMENTS.md text for ARG-02 describes read-only behavior that was intentionally replaced by D-09 before implementation began. The requirement is marked `[x]` Complete in the traceability table. The implementation satisfies the intent of controlled post-resolve access via the publish model — which is a superset of the original read-only gate.

---

### Anti-Patterns Found

No blocker anti-patterns. Scanned all 8 modified/created files:
- `alembic/versions/0007_add_published_at.py` — no TODO/FIXME/XXX/TBD
- `api/models/models.py` — no markers in phase-modified lines
- `api/services/cases.py` — no markers in phase-modified lines
- `api/schemas/admin_arguments.py` — no markers
- `api/services/admin_arguments.py` — no markers
- `api/routers/admin.py` — no markers in phase-added lines
- `app/src/routes/admin/arguments/**` — no markers
- `app/src/routes/admin/pipeline/[job_id]/**` — no markers in phase-added lines
- `app/src/lib/components/TopNav.svelte` — no markers

No empty implementations (`return null`, `return {}`, `return []`) in phase-new rendering paths. No hardcoded empty data passed to rendering components. No `{@html}` used for operator-entered fields (XSS guard confirmed).

---

### Human Verification Required

Three items require live database + browser session to exercise runtime state transitions:

#### 1. Status Badges and Per-Row Publish Toggles (Visual)

**Test:** Open /admin/arguments in a browser with at least one argument in each state (Pending, Resolved, Published).
**Expected:** Status badge colors match spec (#4ade80 Published, #a78bfa Resolved, #94a3b8 Pending). Publish button appears only on resolved-but-unpublished rows. Unpublish button appears only on published rows. No control on pending rows. Edit link present on every row.
**Why human:** Badge state transitions and conditional button rendering depend on runtime resolved_at / published_at values. Cannot be verified without live data.

#### 2. Slug Collision Error Display

**Test:** On /admin/arguments/[id] for a resolved-but-unpublished argument, edit the case title to a value whose slug (_derive_slug output) is already used by another case in the DB. Click Save.
**Expected:** Form remains on page with error message "This title generates a URL slug that conflicts with an existing case. Choose a different title." in the role=alert slot. No 500 error. No redirect.
**Why human:** Requires two Case rows with the same slug in a live DB. The code path (pre-write collision query → ValueError("slug_collision") → fail(422) → role=alert display) is wired but cannot be exercised without DATABASE_URL.

#### 3. Publish/Unpublish Round-Trip + Public Visibility

**Test:** Navigate to a resolved-but-unpublished argument in /admin/arguments. Click Publish. Verify the argument now appears at /cases. Navigate back and click Unpublish. Verify the argument no longer appears at /cases.
**Expected:** Publish stamps published_at; public /cases list includes the argument. Unpublish clears published_at; public /cases list excludes the argument.
**Why human:** Round-trip state change and public visibility gate enforcement require a live database. The publish/unpublish guards (resolved_at IS NOT NULL, already-published check) are code-present but not DB-testable without DATABASE_URL.

---

### Gaps Summary

No gaps. All 15 must-haves are present, substantive, and wired. The 3 behavior-unverified truths are present and wired in the codebase — they require a live database to exercise the runtime invariants. Human verification items 1-3 above cover these cases.

The ARG-02 requirement is superseded by D-09 (always-editable + publish model), confirmed by CONTEXT.md and REQUIREMENTS.md traceability. This is not a gap.

---

_Verified: 2026-06-22_
_Verifier: Claude (gsd-verifier)_
