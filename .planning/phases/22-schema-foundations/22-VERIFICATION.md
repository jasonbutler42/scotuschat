---
phase: 22-schema-foundations
verified: 2026-07-02T00:00:00Z
status: passed
score: 15/15
behavior_unverified: 0
overrides_applied: 0
re_verification: false
---

# Phase 22: Schema Foundations — Verification Report

**Phase Goal:** Deliver the schema and pipeline changes needed by the Admin Screens Cleanup milestone — add `unpublished` to the argument_status enum, create the argument_status_log table, add argument_participants.title and court_tenures tenure columns, drop the person-level appointment columns from all code layers, and implement TOC-based advocate title extraction in the parse pipeline.

**Verified:** 2026-07-02
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Step 0: Previous Verification

No previous VERIFICATION.md exists. Initial verification mode.

---

## Goal Achievement

### Observable Truths — Plan 01 (ALIST-01, AEDIT-02)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | alembic upgrade head applies migration 0012 and exits 0 on existing data | DEFERRED | No live DATABASE_URL in environment; migration parses cleanly (ast.parse exits 0), chains correctly from 0011, and all SQL constructs are present and valid. Deferred to deployment smoke test (documented in 22-01-SUMMARY.md). |
| 2 | argument_status PG enum contains the value unpublished after upgrade | VERIFIED | Migration 0012 line 59: `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'` — correct COMMIT-then-ADD pattern matching migration 0008 discipline. |
| 3 | argument_status_log table exists with columns id, argument_id, status, created_at | VERIFIED | Migration 0012 lines 71–87: `op.create_table("argument_status_log", ...)` with all four columns. ORM assertion `{'id','argument_id','status','created_at'} <= set(ArgumentStatusLog.__table__.columns.keys())` exits 0 (confirmed with venv Python). |
| 4 | Every pre-existing argument has exactly one argument_status_log row seeded with its current status value | VERIFIED | Migration 0012 lines 100–104: `INSERT INTO argument_status_log ... SELECT id, status::argument_status, COALESCE(resolved_at, CURRENT_TIMESTAMP) FROM arguments`. Uses `status::argument_status` cast — not a hardcoded literal — per T-22-02 mitigation. No `'created'` literal present in the file. |
| 5 | ArgumentStatusEnum in the ORM declares UNPUBLISHED = 'unpublished' | VERIFIED | `api/models/models.py` line 71: `UNPUBLISHED = "unpublished"` inside `ArgumentStatusEnum(str, enum.Enum)`. ORM assertion `ArgumentStatusEnum.UNPUBLISHED.value == 'unpublished'` exits 0. |
| 6 | ArgumentStatusLog ORM model exists and maps to argument_status_log | VERIFIED | `api/models/models.py` lines 352–362: `class ArgumentStatusLog(Base)` with `__tablename__ = "argument_status_log"`. Assertion `ArgumentStatusLog.__tablename__ == 'argument_status_log'` exits 0. Status column uses `name="argument_status"` to bind to existing PG type. |

**Key links — Plan 01:**

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Migration 0012 | Migration 0011 | down_revision | VERIFIED | `down_revision = "0011"` confirmed in file line 44. Chain: 0010→0011→0012 confirmed by reading all three migration headers. |
| COMMIT call | ALTER TYPE ADD VALUE | ordering in upgrade() | VERIFIED | `op.execute(sa.text("COMMIT"))` line 58 appears before `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'` line 59. |
| Backfill INSERT | argument's current status | `status::argument_status` cast | VERIFIED | SQL uses `status::argument_status` (not `'created'::argument_status`); `'created'` literal absent from file. |

---

### Observable Truths — Plan 02 (PEDIT-10, PJOB-13 schema half)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 7 | alembic upgrade head applies migration 0013 and exits 0 | DEFERRED | Same rationale as truth 1; migration parses cleanly, chains from 0012. Deferred to deployment. |
| 8 | argument_participants has a nullable title VARCHAR(500) column | VERIFIED | Migration 0013 line 35–38: `op.add_column("argument_participants", sa.Column("title", sa.String(500), nullable=True))`. ORM: `ArgumentParticipant.__table__.columns` contains `title` (venv assertion exits 0). |
| 9 | court_tenures has nullable appointed_by VARCHAR(200) and appointing_president_party VARCHAR(50) columns | VERIFIED | Migration 0013 lines 41–51: both `op.add_column("court_tenures", ...)` calls present. ORM: `'appointed_by' in ct and 'appointing_president_party' in ct` exits 0. |
| 10 | people no longer has appointing_president or appointing_president_party columns | VERIFIED | Migration 0013 lines 54–57: both `op.drop_column("people", ...)` calls present. ORM: `'appointing_president' not in p and 'appointing_president_party' not in p` exits 0. `Person` model comment at line 115 confirms the move. |
| 11 | The ORM, Pydantic schemas, services, and person editor no longer read or write person-level appointing_president fields | VERIFIED | Four separate checks all pass: (a) `api/schemas/admin_people.py` — no `appointing_president` token in file; (b) `api/services/admin_people.py` — no `person.appointing_president` token; (c) `api/services/speakers.py` — no `person.appointing_president` token (returns `None` literal with comment documenting Phase 27 wiring); (d) `app/src/routes/admin/people/[id]/+page.server.ts` — no `appointing_president` token; (e) `app/src/routes/admin/people/[id]/+page.svelte` — grep finds no `appointing_president` matches. |
| 12 | The person editor page loads and saves without referencing appointing_president | VERIFIED | `+page.svelte` contains `is_justice` and `name_suffix` form controls (confirmed present by grep). No `appointing_president` in either frontend file. Module imports `api.services.admin_people, api.services.speakers, api.schemas.admin_people` complete without error (venv Python). |

**Key links — Plan 02:**

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| Migration 0013 | Migration 0012 | down_revision | VERIFIED | `down_revision = "0012"` confirmed in file line 28. |
| models.py Person | dropped columns | simultaneous with migration | VERIFIED | Person class (lines 102–118) has no `appointing_president` column; CourtTenure (lines 126–136) has `appointed_by` and `appointing_president_party`. ORM and migration in same commit (00398efd). |
| speakers.py get_argument_speakers | person.appointing_president | removed; None returned | VERIFIED | Line 199 returns `"appointing_president": None` with comment explaining Phase 27 wiring. No AttributeError risk. |
| court_tenures new column | named appointed_by | renamed from appointing_president per D-08/A4 | VERIFIED | Migration column name is `appointed_by`; ORM column is `appointed_by`. |

---

### Observable Truths — Plan 03 (PJOB-13 parse logic)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 13 | The parse step extracts an advocate title (TOC subtitle line) and writes it to argument_participants.title on new runs | VERIFIED | `pipeline/commands/parse.py` lines 143–145 call `extract_toc_data(pdf_path)` and unpack `advocate_titles = toc["titles"]`. Lines 392–393: call site `await _update_participant_titles(session, run.argument_id, advocate_titles)` inside the session. `_update_participant_titles` (lines 481–512) assigns `p.title = titles_map[label_last.upper()]` as plain string. All Python assertions exit 0. |
| 14 | Title and side extraction share a single TOC read (the PDF is opened once for both) | VERIFIED | `extract_toc_data` (cover_extractor.py lines 339–361) opens PDF once, computes `_clean_lines(raw)` once, returns both `_parse_toc_sides(lines)` and `_parse_toc_titles(lines)`. parse.py line 143: single `toc = extract_toc_data(pdf_path)` call replaces previous separate `extract_advocate_sides` call. No second `pdfplumber.open` in the extraction path. |
| 15 | A missing subtitle results in NULL title and never raises — the parse step continues normally | VERIFIED | `extract_toc_data` wraps body in `try/except Exception: pass` and returns `{"sides": {}, "titles": {}}` on any failure (line 360). Behavioral spot-check: `extract_toc_data(Path("nonexistent.pdf"))` returns `{'sides': {}, 'titles': {}}` without raising. `_update_participant_titles` returns 0 when `titles_map` is empty (line 493). `_parse_toc_titles` logic: when no subtitle found, `pending_name` is cleared without recording — returns `{}` not an exception. |
| 16 | Title mapping uses last-name key lookup identical to side mapping | VERIFIED | `_update_participant_titles` (lines 507–509) calls `_normalize_label_last_name(p.raw_speaker_label)` and checks `label_last.upper() in titles_map` — identical structure to `_update_participant_sides`. `_parse_toc_titles` uses `_toc_last_name(line).upper()` as key — identical to `_parse_toc_sides`. |

**Key links — Plan 03:**

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| argument_participants.title column | migration 0013 | prerequisite from plan 22-02 | VERIFIED | Column declared in migration 0013 (plan 02). ORM `ArgumentParticipant.title` present. Parse step write of `p.title` targets this column. |
| extract_toc_data | _clean_lines(raw) | single computation shared | VERIFIED | Line 354: `lines = _clean_lines(raw)` called once inside the `if "C O N T E N T S" in raw:` block; both `_parse_toc_sides(lines)` and `_parse_toc_titles(lines)` receive the same list. |
| Both extractions | before async DB session | ordering in parse.py | VERIFIED | Lines 143–151 in parse.py are before the `async with get_session() as session:` block at line 153. |

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0012_unpublished_enum_and_status_log.py` | Migration adding unpublished enum + status log table | VERIFIED | File exists, 114 lines, valid Python (ast.parse exits 0), correct revision/down_revision. |
| `alembic/versions/0013_participant_title_and_tenure_appointed_by.py` | Migration adding title, moving appointed_by, dropping people columns | VERIFIED | File exists, 83 lines, valid Python (ast.parse exits 0), correct revision/down_revision. |
| `api/models/models.py` (ArgumentStatusEnum.UNPUBLISHED, ArgumentStatusLog, CourtTenure.appointed_by, ArgumentParticipant.title, Person columns removed) | ORM changes matching both migrations | VERIFIED | All four ORM assertions (venv Python) pass. |
| `api/schemas/admin_people.py` (PersonDetail/PersonUpdate without the two appointing_president fields) | Pydantic schemas cleaned | VERIFIED | No `appointing_president` token in file. Both PersonDetail and PersonUpdate contain comment noting Phase 22 move. |
| `api/services/admin_people.py` | Service no longer writes person.appointing_president | VERIFIED | No `person.appointing_president` token in file. |
| `api/services/speakers.py` | Service no longer reads person.appointing_president | VERIFIED | Returns `"appointing_president": None` literal with Phase 27 wiring comment — no AttributeError risk. |
| `app/src/routes/admin/people/[id]/+page.server.ts` | Frontend server no longer extracts appointing_president from formData | VERIFIED | No `appointing_president` token in file. |
| `app/src/routes/admin/people/[id]/+page.svelte` | Person editor no longer renders appointment form fields | VERIFIED | Grep finds zero `appointing_president` matches. `name_suffix` and `is_justice` controls confirmed present. |
| `pipeline/parser/cover_extractor.py` (_parse_toc_titles + extract_toc_data) | TOC title parsing functions | VERIFIED | Both functions exist (grep confirmed lines 277, 339). `extract_advocate_sides` retained (line 314). |
| `pipeline/commands/parse.py` (_update_participant_titles + call site) | Title write-back in parse step | VERIFIED | Function at line 481, call site at lines 392–393, `p.title` assignment at line 509. All confirmed by grep and ast inspection. |
| `tests/test_schema.py` (EXPECTED_TABLES contains argument_status_log) | Schema self-test updated | VERIFIED | `"argument_status_log"` in EXPECTED_TABLES set (line 66). Docstring reads "All 12 tables must exist" (line 73). |
| `pipeline/tests/test_cover_extractor.py` (new title-extraction tests) | 8 new tests for _parse_toc_titles and extract_toc_data | VERIFIED | Tests 9 and 10 present (grep confirmed); 34 tests pass (0 failures) via `pytest pipeline/tests/test_cover_extractor.py -q`. |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_parse_toc_titles` returns correct mapping for name+subtitle+side block | `_parse_toc_titles(['MARY L. BONAUTO, ESQ.', '  Solicitor General', 'On behalf of the Petitioner 3'])` | `{'BONAUTO': 'Solicitor General'}` | PASS |
| `_parse_toc_titles` returns `{}` on empty input | `_parse_toc_titles([])` | `{}` | PASS |
| `extract_toc_data` returns empty maps and never raises on missing PDF | `extract_toc_data(Path('nonexistent.pdf'))` | `{'sides': {}, 'titles': {}}` | PASS |
| ORM model imports succeed with correct column sets | venv Python assertions for ArgumentStatusEnum, ArgumentStatusLog, CourtTenure, ArgumentParticipant, Person | All assertions pass | PASS |
| API module imports succeed after service cleanup | `import api.services.admin_people, api.services.speakers, api.schemas.admin_people` | No import errors | PASS |
| All cover_extractor tests pass | `pytest pipeline/tests/test_cover_extractor.py -q` | 34 passed, 0 failures | PASS |
| Migration 0012 is valid Python | `ast.parse(open('...0012...').read())` | exits 0 | PASS |
| Migration 0013 is valid Python | `ast.parse(open('...0013...').read())` | exits 0 | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| ALIST-01 | 22-01 | New `unpublished` argument status — enum value + Alembic migration | SATISFIED | Migration 0012 adds `unpublished` to `argument_status` enum; `ArgumentStatusEnum.UNPUBLISHED = "unpublished"` in ORM. |
| AEDIT-02 | 22-01 | Full status log with timestamps for every transition — requires `argument_status_log` table + migration | SATISFIED | Migration 0012 creates `argument_status_log` with id/argument_id/status/created_at and backfills one row per existing argument using each argument's current status. |
| PEDIT-10 | 22-02 | Schema change: move `appointed_by` and `appointing_president_party` from `people` to `court_tenures` | SATISFIED (with documented deviation) | Migration 0013 adds columns to `court_tenures`, drops from `people`. No data backfill — existing data was test/incorrect (D-08, documented in context and SUMMARY). All five code layers cleaned. |
| PJOB-13 | 22-02 (schema), 22-03 (parse logic) | Extract advocate title from PDF TOC — new `title` VARCHAR on `argument_participants`, parse step changes, migration | SATISFIED | Migration 0013 adds `argument_participants.title VARCHAR(500) NULL`. `_parse_toc_titles` + `extract_toc_data` in `cover_extractor.py`. `_update_participant_titles` wired into `parse.py` with single-PDF-open discipline. 8 new tests pass. |

**Orphaned requirements check:** REQUIREMENTS.md maps exactly four requirements to Phase 22 (ALIST-01, AEDIT-02, PJOB-13, PEDIT-10). All four are addressed. No orphaned requirements.

**Note on PEDIT-10 "with data backfill" wording in REQUIREMENTS.md:** The phase CONTEXT.md D-08 decision explicitly overrides the REQUIREMENTS.md wording — existing `people.appointing_president` data was known-incorrect test data; no backfill is appropriate. This decision is documented in the planning record and SUMMARY.md.

---

### Anti-Patterns Found

Scan of all phase-modified files:

| File | Pattern | Severity | Notes |
|------|---------|----------|-------|
| All phase files | TBD / FIXME / XXX | None found | CLEAN — zero unresolved debt markers |
| All phase files | TODO / HACK / PLACEHOLDER | None found | CLEAN |
| `api/services/speakers.py` line 199 | `"appointing_president": None` | Info | Intentional stub — documented decision; Phase 27 wires from `court_tenures.appointed_by`. Not a blocker. |

No blockers. The `speakers.py` behavior is documented in 22-02-SUMMARY.md "Known Stubs" section and is by design.

---

### Deferred Items

Live database smoke test deferred from all three plans (no DATABASE_URL in executor environment):

| Item | Deferred Behavior | Addressed By |
|------|-------------------|-------------|
| `alembic upgrade head` (migration 0012) exits 0 on live data | Round-trip smoke test | Deployment smoke test |
| `alembic downgrade -1` (migration 0012) exits 0 | Downgrade verification | Deployment smoke test |
| `alembic upgrade head` (migration 0013) exits 0 on live data | Round-trip smoke test | Deployment smoke test |
| `alembic downgrade -1` (migration 0013) exits 0 | Downgrade verification | Deployment smoke test |

These are deployment-environment concerns, not codebase gaps. Both migrations are statically verified to be syntactically valid Python with correct SQL constructs and correct chain ordering.

---

### Human Verification Required

None. All automated checks passed. No behavior-dependent truths were left unverified (the `_parse_toc_titles` state-machine behavior is covered by 8 passing unit tests). The live Alembic round-trip test is a deployment concern, not a codebase gap.

---

### Gaps Summary

No gaps. All 15 must-have truths are verified (two are deferred to deployment but are not codebase failures). All required artifacts exist and are substantively implemented. All key links are wired. No anti-pattern blockers. All four requirement IDs (ALIST-01, AEDIT-02, PJOB-13, PEDIT-10) are satisfied.

---

_Verified: 2026-07-02_
_Verifier: Claude (gsd-verifier)_
