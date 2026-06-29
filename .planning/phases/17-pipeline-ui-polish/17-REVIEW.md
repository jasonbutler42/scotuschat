---
phase: 17
status: issues
reviewed_at: 2026-06-29
finding_count: 5
severity_high: 1
severity_medium: 2
severity_low: 2
---

# Phase 17 Code Review

**Scope:** Phase 17 pipeline UI polish — `original_filename`, `parse_stats`, PDF proxy endpoint, gap closure fix  
**Effort:** High (3+5 angles × 6 candidates → 1-vote verify)  
**Status:** Issues found

---

## Findings

### 1. HIGH — HTTP response splitting via unsanitized Content-Disposition filename

**File:** `api/routers/admin.py:353`  
**Severity:** High  

```python
filename = job.original_filename or f"argument-{job_id}.pdf"
return FileResponse(
    path=run.pdf_path,
    media_type="application/pdf",
    headers={"Content-Disposition": f'inline; filename="{filename}"'},
)
```

`original_filename` comes from `pdf_file.filename` (browser-controlled). Starlette 1.3.1 encodes custom header values with `latin-1` and performs **no CRLF stripping**. A filename containing `\r\n` (valid latin-1) is embedded verbatim in the raw header byte sequence, enabling HTTP response splitting. A double-quote in the filename also breaks RFC 6266 header syntax.

**Fix:** Strip or encode the filename before embedding:
```python
import re
safe_filename = re.sub(r'[\r\n"\\]', '_', filename)
headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}"}
```
Or use `Content-Disposition: attachment` without `filename=` — the browser will use the URL segment.

---

### 2. MEDIUM — `rerun_job` omits `original_filename`, silently dropping upload source display on re-runs

**File:** `api/services/admin_jobs.py:442`  
**Severity:** Medium  

```python
new_job = await create_job(
    db,
    pdf_url=original.pdf_url,
    spaces_key=original.spaces_key,
    # original.original_filename never passed
)
```

For disk-backed upload jobs, `pdf_url` and `spaces_key` are both `None`. The re-run job has `original_filename=None`, so both the PDF card gate (`spaces_key || pdf_url || original_filename`) and the ingest source row guard (`original_filename || pdf_url`) evaluate false on the new job's detail page — the source identifier is invisible.

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

### 3. MEDIUM — `FileResponse` on a missing file raises `RuntimeError` (500) instead of 404

**File:** `api/routers/admin.py:348`  
**Severity:** Medium  

```python
if run is None or run.pdf_path is None:
    raise HTTPException(status_code=404, detail="PDF path not recorded")
# No existence check before FileResponse:
return FileResponse(path=run.pdf_path, ...)
```

Starlette 1.3.1's `FileResponse.__call__` raises `RuntimeError(f"File at path {self.path} does not exist.")` on `FileNotFoundError`. FastAPI translates this to a 500. The route guards `pdf_path is None` but not whether the file actually exists — a file deleted after ingest (container redeployment, disk cleanup) returns an unhandled 500.

**Fix:**
```python
import os
if not os.path.isfile(run.pdf_path):
    raise HTTPException(status_code=404, detail="PDF file not found on disk")
return FileResponse(path=run.pdf_path, ...)
```

---

### 4. LOW — `speaker_count` not scoped to the current parse run — can overcount on re-runs

**File:** `api/services/admin_jobs.py:100`  
**Severity:** Low  

```python
spk_result = await db.execute(
    select(func.count(ArgumentParticipant.raw_speaker_label.distinct())).where(
        ArgumentParticipant.argument_id == job.argument_id
    )
)
```

`ArgumentParticipant` has no `pipeline_run_id` column. The parse pipeline uses select-before-insert (never deletes old rows). If a re-parse resolves or renames a speaker, the stale label remains — `DISTINCT raw_speaker_label` overcounts. The utterance count is correctly scoped to `parse_run_id`; speaker count is not.

**Note:** This only manifests on re-parsed jobs. For first-run jobs the count is correct.

---

### 5. LOW — `get_run_id_for_step` called unconditionally before `argument_id` guard

**File:** `api/services/admin_jobs.py:96`  
**Severity:** Low  

```python
parse_run_id = await get_run_id_for_step(db, job_id, "parse")  # fires even when argument_id is None
if parse_run_id is not None and job.argument_id is not None:
```

When `argument_id` is `None` (every poll during ingest — the common polling state), `get_run_id_for_step` issues two SQL queries that return `None` immediately. Moving the call inside the guard eliminates a wasted round-trip on every poll.

**Fix:** Swap the guard order:
```python
if job.argument_id is not None:
    parse_run_id = await get_run_id_for_step(db, job_id, "parse")
    if parse_run_id is not None:
        ...
```

---

## Summary

| # | File | Line | Severity | Summary |
|---|------|------|----------|---------|
| 1 | api/routers/admin.py | 353 | HIGH | Content-Disposition CRLF injection via original_filename |
| 2 | api/services/admin_jobs.py | 442 | MEDIUM | rerun_job drops original_filename — source display breaks on re-runs |
| 3 | api/routers/admin.py | 348 | MEDIUM | FileResponse 500 on missing file instead of 404 |
| 4 | api/services/admin_jobs.py | 100 | LOW | speaker_count overcounts on re-parsed jobs |
| 5 | api/services/admin_jobs.py | 96 | LOW | Wasted DB query per poll during ingest phase |
