---
phase: 19-pipeline-reliability
fixed_at: 2026-06-30T00:00:00Z
review_path: .planning/phases/19-pipeline-reliability/19-REVIEW.md
iteration: 1
findings_in_scope: 8
fixed: 7
skipped: 1
status: partial
---

# Phase 19: Code Review Fix Report

**Fixed at:** 2026-06-30
**Source review:** .planning/phases/19-pipeline-reliability/19-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 8 (CR-01, CR-02, CR-03, CR-04, WR-01, WR-02, WR-03, WR-04, WR-05 — scope is critical_warning; IN-01 and IN-02 excluded)
- Fixed: 7
- Skipped: 1 (CR-04 — pre-existing, out of scope per instruction)

## Fixed Issues

### CR-01: `primary_docket` and `question_number` silently dropped — D-01 deduplication never fires

**Files modified:** `api/routers/admin.py`
**Commit:** f9f0c552
**Applied fix:** Added `primary_docket: Optional[str] = Form(None)` and `question_number: int = Form(1)` parameters to `create_job`. All three ingest branches (URL mode, Spaces upload, local-file fallback) now build an `ingest_args` list that includes `--question` always and `--primary-docket` when provided, then passes it to `spawn_pipeline_step`.

---

### CR-02: Ingest creates `Case` rows with `case_name=None` — NOT NULL violation on flush

**Files modified:** `pipeline/commands/ingest.py`
**Commit:** d1c57df9
**Applied fix:** Added `effective_case_name = case_name or f"Pending review (job {args.job_id})"` before the Case loop so the NOT NULL constraint is always satisfied. Added `lead_docket` variable that falls back to the first docket in `all_dockets` when `primary_docket is None`, and used `lead_docket` in the `is_lead` comparison so `get_argument_detail` always finds a lead row.

---

### CR-03: Migration downgrade sets `argued_date NOT NULL` without backfill — will crash after NULL rows exist

**Files modified:** `alembic/versions/0011_add_source_docket_cover_metadata.py`
**Commit:** 3daf2d66
**Applied fix:** Inserted `op.execute("UPDATE arguments SET argued_date = CURRENT_DATE WHERE argued_date IS NULL")` in `downgrade()` immediately before `op.alter_column("arguments", "argued_date", nullable=False)`. PostgreSQL cannot tighten a column to NOT NULL while null values exist; this backfill prevents the crash.

---

### WR-01: `update_argument_metadata` unconditionally NULLs `source_docket` when field is omitted

**Files modified:** `api/services/admin_arguments.py`
**Commit:** 6b999e61
**Applied fix:** Replaced the unconditional `.values(argued_date=..., source_docket=...)` UPDATE with a conditional dict-based pattern. `argued_date` is included only when `body.argued_date is not None` or a parsed date was produced; `source_docket` is included only when `body.source_docket is not None`. The UPDATE is skipped entirely if nothing changed.

---

### WR-02: Preflight `handleSubmit` does not check `res.ok` — non-OK responses silently bypass duplicate warning

**Files modified:** `app/src/routes/admin/pipeline/+page.svelte`
**Commit:** 2199dfe0
**Applied fix:** Added an `if (!res.ok)` guard immediately after the `fetch` call in `handleSubmit`. Non-OK responses (400, 502, etc.) now log a warning with the status code and allow the submit to proceed — matching the existing `catch` behavior for network errors — rather than silently calling `res.json()` on a body that lacks `exists`.

---

### WR-03: `_derive_slug` leaves URL-unsafe characters (apostrophes, ampersands, slashes) in slugs

**Files modified:** `pipeline/commands/ingest.py`
**Commit:** 840734f0
**Applied fix:** Rewrote `_derive_slug` to replace apostrophes (strip), ampersands (`and`), slashes (`-`), and parentheses (strip) before the existing space/period/comma replacements. Added `re.sub(r"-{2,}", "-", slug)` to collapse consecutive dashes and `.strip("-")` to remove leading/trailing dashes. Added `import re` inside the function (consistent with the project pattern in `parse.py`).

---

### WR-04: `CAPTION_SEP_RE` character class includes literal `x` and `X` — may silently discard petitioner name lines

**Files modified:** `pipeline/parser/cover_extractor.py`
**Commit:** 02fbb5e8
**Applied fix:** Changed `CAPTION_SEP_RE` from `r'^[\xad\-\s–—xX\*]+$'` to `r'^[\xad\-\s–—\*]+(?:\s+[xX])?$'`. The trailing `x` in Alderson separators is always preceded by whitespace, so anchoring it as an optional `(?:\s+[xX])?` suffix correctly matches all real separators while no longer treating a solo `X` line as a separator.

---

### WR-05: `parse.py` contains a soft-hyphen (U+00AD) literal in source code

**Files modified:** `pipeline/commands/parse.py`
**Commit:** 57799a36
**Applied fix:** Replaced the invisible U+00AD literal (UTF-8 bytes `\xC2\xAD`) with the explicit Unicode escape `'­'` and added a comment `# U+00AD SOFT HYPHEN (explicit escape, not invisible literal)`. Replacement was performed at the byte level to avoid editor normalization stripping the invisible character during the edit.

---

## Skipped Issues

### CR-04: Unconstrained SSRF on `photo_url` — any URL accepted including internal metadata endpoints

**File:** `api/routers/admin.py:522-523`
**Reason:** skipped: pre-existing — CR-04 originates from a prior phase, not introduced in Phase 19. Per instruction, this finding is explicitly excluded from this fix run.
**Original issue:** `POST /api/admin/jobs/{person_id}/photo` fetches `photo_url` with `httpx` and `follow_redirects=True` without scheme or hostname validation, allowing SSRF to internal/metadata endpoints. The fix (adding `_validate_photo_url` with HTTPS enforcement and private-IP blocking) should be applied in a dedicated security phase.

---

_Fixed: 2026-06-30_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
