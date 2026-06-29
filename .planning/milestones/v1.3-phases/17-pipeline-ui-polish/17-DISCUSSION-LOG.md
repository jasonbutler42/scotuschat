# Phase 17: Pipeline UI Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 17-pipeline-ui-polish
**Areas discussed:** Ingest filename display, PDF access UX, PDF serving backend

---

## Ingest Filename Display

| Option | Description | Selected |
|--------|-------------|----------|
| Filename from URL | Derive last path segment from pdf_url (e.g., `21-476.pdf`). No migration needed. | |
| Full URL (truncated) | Show the full supremecourt.gov URL, truncated with ellipsis if long. | |
| Mode-dependent (user clarification) | Upload: show original filename. URL: show full URL. | ✓ |

**User's choice:** Free-text clarification — display is mode-dependent: upload mode shows the original filename from the browser; URL mode shows the full supremecourt.gov URL verbatim.

**Notes:** Original filename from browser uploads is not currently stored (`spaces_key` is synthetic). This requires an `original_filename` column on `admin_jobs` via Alembic migration, populated at job creation time from `pdf_file.filename`.

---

## PDF Access UX

| Option | Description | Selected |
|--------|-------------|----------|
| Open in new tab | Browser opens PDF inline using native PDF viewer. `Content-Disposition: inline`. | ✓ |
| Force download | Triggers file download. `Content-Disposition: attachment`. | |
| Both — View + Download | Two separate links. More flexible but adds UI complexity. | |

**User's choice:** Open in new tab — browser's native PDF viewer.

**Notes:** Operator can use the browser's built-in save/download button after opening inline, so a separate download button is not needed.

---

## PDF Serving Backend

| Option | Description | Selected |
|--------|-------------|----------|
| One unified endpoint | `GET /api/admin/jobs/{id}/pdf` — checks spaces_key; if set, redirects to Spaces pre-signed URL; otherwise streams from pdf_path. | ✓ |
| Two separate paths | Frontend checks source type and calls different endpoints. | |
| You decide | Claude picks. | |

**User's choice:** One unified endpoint. Frontend always hits the same URL; storage backend is transparent.

---

## Claude's Discretion

- Whether to return parse stats inline with the existing `GET /api/admin/jobs/{id}` response or as a separate sub-request
- Exact label and placement of the "View source PDF" link
- Pre-signed URL TTL for Spaces-backed PDFs
- Null-allowance on `original_filename` column for pre-migration rows

## Deferred Ideas

- Showing docket number on the Parse card — redundant with the Argument metadata preview already on the page
- Incremental stats during parse step running — adds polling complexity; out of scope
- Separate download button — operator can use browser's native PDF viewer save action
