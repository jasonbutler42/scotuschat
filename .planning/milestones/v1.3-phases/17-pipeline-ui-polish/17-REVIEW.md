---
phase: 17-pipeline-ui-polish
reviewed: 2026-06-29T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - alembic/versions/0009_add_original_filename.py
  - api/models/models.py
  - api/schemas/admin_jobs.py
  - api/services/admin_jobs.py
  - api/services/spaces.py
  - api/routers/admin.py
  - api/tests/test_admin_jobs_stats.py
  - app/src/routes/admin/pipeline/[job_id]/pdf/+server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 3
  warning: 3
  info: 1
  total: 7
status: issues_found
---

# Phase 17: Code Review Report

**Reviewed:** 2026-06-29
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 17 adds `original_filename` storage, `parse_stats` enrichment in `get_job`, a `GET /jobs/{job_id}/pdf` endpoint (Spaces redirect or disk `FileResponse`), and frontend wiring of the PDF card and stat rows. The migration, schema, and Svelte component are clean. The critical issues are: an HTTP response-splitting vulnerability in `Content-Disposition` header construction, three DB integration tests that will fail at insert time because they reference non-existent ORM columns, and a missing file existence check that turns a `FileResponse` on a deleted file into an unhandled 500. Two additional warnings cover data correctness and a behavioral gap on re-runs.

---

## Critical Issues

### CR-01: HTTP response splitting via unsanitized `original_filename` in Content-Disposition header

**File:** `api/routers/admin.py:349-353`
**Issue:** `original_filename` is derived from `pdf_file.filename` — a browser-controlled multipart field. It is embedded verbatim inside a quoted header string without any sanitization:

```python
filename = job.original_filename or f"argument-{job_id}.pdf"
return FileResponse(
    path=run.pdf_path,
    media_type="application/pdf",
    headers={"Content-Disposition": f'inline; filename="{filename}"'},
)
```

Starlette's `MutableHeaders` encodes custom header values using latin-1 and performs no CRLF stripping. A filename containing `\r\n` is written verbatim into the raw HTTP byte stream, enabling header injection / response splitting. A double-quote in the filename also breaks RFC 6266 header syntax (the header parser will truncate the filename token at the `"`).

**Fix:**
```python
import re
from urllib.parse import quote

# Strip characters that are illegal inside a quoted-string or that would
# allow header injection. For a fully standards-compliant header prefer
# the RFC 5987 encoded form which handles all Unicode safely.
safe_filename = re.sub(r'[\r\n"\x00-\x1f\\]', '_', filename)
headers = {
    "Content-Disposition": (
        f"inline; filename=\"{safe_filename}\"; "
        f"filename*=UTF-8''{quote(filename, safe='')}"
    )
}
```
Or strip the `filename=` parameter entirely — the browser will use the URL path segment as the save-as name when it is absent.

---

### CR-02: DB integration tests use non-existent ORM column names — all three will fail at flush time

**File:** `api/tests/test_admin_jobs_stats.py:134,139-147,227,231-238,305,309-316`
**Issue:** Every DB integration test seeds `Case` with the keyword argument `name=`, but the `Case` ORM model has no `name` column — the column is `case_name` (`api/models/models.py:146`). SQLAlchemy will silently accept the unknown keyword and the column will receive its `NOT NULL` constraint default value of `NULL`, causing the `flush()` to fail with an `IntegrityError` at the database layer.

Additionally, each test seeds `Argument` with keyword arguments `case_id=`, `docket_number=`, `case_name=`, and `slug=` (e.g., lines 139-147). None of those columns exist on the `Argument` model (`api/models/models.py:157-179`): `Argument` has only `argued_date`, `question_number`, `resolved_at`, `published_at`, and `status`. These spurious kwargs will be silently ignored by SQLAlchemy's `__init__`, leaving `argued_date` unset and causing an `IntegrityError` on `flush()` because `argued_date` is `NOT NULL`.

The tests will never execute their `get_job()` assertions — they always fail earlier at row insertion. The three `@pytest.mark.skipif(not _db_configured(), ...)` guards mean this only manifests when `DATABASE_URL` is configured; the CI that lacks a live DB masks the defect.

**Fix — correct the `Case` constructor:**
```python
# All three tests: replace
case = Case(name="...", docket_number="22-999")
# with
case = Case(case_name="...", docket_number="22-999", docket_number_norm="22-999",
            term_year=2022, slug="test-case-for-stats")
```

**Fix — correct the `Argument` constructor:**
```python
# Remove case_id, docket_number, case_name, slug; add the required argued_date
arg = Argument(
    argued_date=datetime.date(2022, 10, 1),
    status="pipeline",
)
```
Link the case via `CaseArgument` after both are flushed, or remove the `Case` seed entirely if the test does not need a linked case.

---

### CR-03: `FileResponse` on a missing-but-recorded file raises unhandled `RuntimeError` (500)

**File:** `api/routers/admin.py:344-353`
**Issue:** The code guards against `run.pdf_path is None` but not against the file being absent from disk:

```python
if run is None or run.pdf_path is None:
    raise HTTPException(status_code=404, detail="PDF path not recorded")
# No existence check:
return FileResponse(path=run.pdf_path, ...)
```

Starlette's `FileResponse.__call__` raises `RuntimeError("File at path ... does not exist.")` when the file is missing on disk. FastAPI translates this to an unhandled 500. This is reproducible in any environment where the container is redeployed between ingest and PDF-view (the `data/uploads/` volume is ephemeral unless explicitly mounted), or when a dev cleans `data/uploads/`.

**Fix:**
```python
import os
if not os.path.isfile(run.pdf_path):
    raise HTTPException(status_code=404, detail="PDF file not found on disk")
return FileResponse(path=run.pdf_path, ...)
```

---

## Warnings

### WR-01: `rerun_job` silently drops `original_filename` — PDF card and source row invisible on re-runs

**File:** `api/services/admin_jobs.py:442-447`
**Issue:**
```python
new_job = await create_job(
    db,
    pdf_url=original.pdf_url,
    spaces_key=original.spaces_key,
    # original_filename never forwarded
)
```
For upload-mode jobs where `pdf_url` and `spaces_key` are both `None`, the re-run job has all three of `spaces_key`, `pdf_url`, and `original_filename` as `None`. The PDF card gate on `+page.svelte:471` evaluates `spaces_key || pdf_url || original_filename` — all falsy — so the "View source PDF" card is hidden. The ingest source row on line 544 also depends on `original_filename || pdf_url` and is likewise hidden. The operator cannot view the source PDF from the re-run page.

**Fix:**
```python
new_job = await create_job(
    db,
    pdf_url=original.pdf_url,
    spaces_key=original.spaces_key,
    original_filename=original.original_filename,
)
```

---

### WR-02: `speaker_count` not scoped to the current parse run — overcounts on re-parsed jobs

**File:** `api/services/admin_jobs.py:110-115`
**Issue:**
```python
spk_result = await db.execute(
    select(func.count(ArgumentParticipant.raw_speaker_label.distinct())).where(
        ArgumentParticipant.argument_id == job.argument_id
    )
)
```
`ArgumentParticipant` has no `pipeline_run_id` column, so the query counts all distinct labels ever written for the argument across all parse runs. The utterance count (line 103-108) is correctly scoped to `parse_run_id`. When a job is re-parsed and a speaker's label changes, stale labels from the earlier run accumulate in `argument_participants`, causing `speaker_count` to be higher than the actual count in the latest parse run.

**Fix:** Document this limitation explicitly in the docstring, or — if `argument_participants` is truncated by the pipeline on re-parse — confirm that behaviour and add a comment. If old rows are not deleted, consider scoping via a JOIN to `utterances` on `pipeline_run_id`:
```python
# Distinct speakers who appear in the current parse run
spk_result = await db.execute(
    select(func.count(Utterance.raw_speaker_label.distinct()))
    .where(Utterance.pipeline_run_id == parse_run_id)
    .where(Utterance.raw_speaker_label.isnot(None))
)
```

---

### WR-03: `list_jobs` returns raw ORM objects without `parse_stats` injected — Pydantic serialization will raise `AttributeError`

**File:** `api/services/admin_jobs.py:127-145` and `api/routers/admin.py:237-248`
**Issue:** `list_jobs` returns plain `AdminJob` ORM objects with no `parse_stats` key injected into `__dict__`:
```python
return list(result.scalars().all())
```
`AdminJobResponse` declares `parse_stats: Optional[ParseStats] = None` with `model_config = {"from_attributes": True}`. Pydantic v2 in `from_attributes` mode calls `getattr(obj, "parse_stats")` on each returned job. Because `parse_stats` is not an ORM column and is not in `__dict__`, `getattr` will raise `AttributeError`, causing all calls to `GET /api/admin/jobs` to return 500.

`get_job` correctly injects `job.__dict__["parse_stats"] = None/dict`, and `create_job` injects `None`. `list_jobs` is the gap.

**Fix:**
```python
jobs = list(result.scalars().all())
for job in jobs:
    job.__dict__.setdefault("parse_stats", None)
return jobs
```

---

## Info

### IN-01: Unnecessary DB round-trip — `get_run_id_for_step` called before `argument_id` guard

**File:** `api/services/admin_jobs.py:100-101`
**Issue:**
```python
parse_run_id = await get_run_id_for_step(db, job_id, "parse")
if parse_run_id is not None and job.argument_id is not None:
```
`get_run_id_for_step` issues two SQL queries unconditionally. When `argument_id` is `None` (which is the case during every poll iteration while ingest is running — the most common polling state), the inner query returns `None` immediately but the queries have already been dispatched. Moving the call inside the guard eliminates both queries on every ingest-phase poll.

**Fix:**
```python
if job.argument_id is not None:
    parse_run_id = await get_run_id_for_step(db, job_id, "parse")
    if parse_run_id is not None:
        # ... COUNT queries ...
        job.__dict__["parse_stats"] = {...}
    else:
        job.__dict__["parse_stats"] = None
else:
    job.__dict__["parse_stats"] = None
```

---

_Reviewed: 2026-06-29_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
