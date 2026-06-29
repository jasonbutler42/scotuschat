---
phase: 17-pipeline-ui-polish
fixed_at: 2026-06-29T00:00:00Z
review_path: .planning/phases/17-pipeline-ui-polish/17-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 17: Code Review Fix Report

**Fixed at:** 2026-06-29
**Source review:** .planning/phases/17-pipeline-ui-polish/17-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (Critical: 3, Warning: 2; IN-01 excluded by fix_scope: critical_warning)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: HTTP response splitting via unsanitized `original_filename` in Content-Disposition header

**Files modified:** `api/routers/admin.py`
**Commit:** f3f2a6ed
**Applied fix:** Added `import os`, `import re`, and `from urllib.parse import quote` to the import block. In the disk-backed PDF branch, replaced the bare `f'inline; filename="{filename}"'` header value with a two-part RFC 5987 header: `safe_filename` (CRLF, NUL, backslash, and double-quote stripped via `re.sub`) for the `filename=` parameter, and `quote(filename, safe='')` for the `filename*=UTF-8''` parameter. This eliminates both the header injection vector and the RFC 6266 syntax break from unescaped double-quotes.

---

### CR-02: DB integration tests use non-existent ORM column names — all three will fail at flush time

**Files modified:** `api/tests/test_admin_jobs_stats.py`
**Commit:** 4036d2b9
**Applied fix:** Added `date` to the `datetime` import. In all three DB integration test functions that seeded a `Case` and `Argument` with wrong column names: removed the `Case(name=...)` seeds entirely (the `Case` model has no `name` column, and the tests do not require a linked case), replaced each `Argument(case_id=..., docket_number=..., case_name=..., slug=..., status=...)` with `Argument(argued_date=date(...), status="pipeline")` using only the columns that actually exist on the `Argument` ORM model. Also removed stale local imports of `ArgumentParticipant`, `SideEnum`, and `Case` in the functions where they became unused.

---

### CR-03: `FileResponse` on a missing-but-recorded file raises unhandled `RuntimeError` (500)

**Files modified:** `api/routers/admin.py`
**Commit:** f3f2a6ed (committed atomically with CR-01 — same file and function)
**Applied fix:** Added `if not os.path.isfile(run.pdf_path): raise HTTPException(status_code=404, detail="PDF file not found on disk")` immediately after the `run.pdf_path is None` guard. This converts the unhandled `RuntimeError` from Starlette's `FileResponse.__call__` into a proper 404.

---

### WR-01: `rerun_job` silently drops `original_filename` — PDF card and source row invisible on re-runs

**Files modified:** `api/services/admin_jobs.py`
**Commit:** d69fd4c0
**Applied fix:** Added `original_filename=original.original_filename` to the `create_job(...)` call inside `rerun_job`. The `create_job` function already accepted this parameter; it was simply not forwarded. Upload-mode re-run jobs now carry the original filename so the PDF card gate (`spaces_key || pdf_url || original_filename`) evaluates truthy and the "View source PDF" card renders correctly.

---

### WR-02: `speaker_count` not scoped to the current parse run — overcounts on re-parsed jobs

**Files modified:** `api/services/admin_jobs.py`, `api/tests/test_admin_jobs_stats.py`
**Commit:** f0d13a14
**Applied fix:** Replaced the `ArgumentParticipant`-based `speaker_count` query with a `Utterance`-scoped query: `select(func.count(Utterance.raw_speaker_label.distinct())).where(Utterance.pipeline_run_id == parse_run_id).where(Utterance.raw_speaker_label.isnot(None))`. This scopes the count to only the current parse run and eliminates accumulation of stale labels from prior runs.

Test alignment: Updated Test 1 and Test 3 assertions in `test_admin_jobs_stats.py` to reflect the new semantics (speaker count now equals distinct labels in the current parse run's utterances, not the count of `ArgumentParticipant` rows). Removed the now-unused `ArgumentParticipant` participant-seed block from Test 1 and updated both docstrings to document the correct behavior.

---

### WR-03: `list_jobs` returns raw ORM objects without `parse_stats` injected — Pydantic serialization will raise `AttributeError`

**Files modified:** `api/services/admin_jobs.py`
**Commit:** d6a370c3
**Applied fix:** After `list(result.scalars().all())`, added a loop that calls `job.__dict__.setdefault("parse_stats", None)` for every returned job. This mirrors the pattern used by `get_job` and `create_job`, ensuring Pydantic v2's `from_attributes` mode finds the attribute on every object and does not raise `AttributeError` on `GET /api/admin/jobs`.

---

_Fixed: 2026-06-29_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
