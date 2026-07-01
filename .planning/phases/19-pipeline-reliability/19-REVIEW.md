---
phase: 19-pipeline-reliability
reviewed: 2026-06-30T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - alembic/versions/0011_add_source_docket_cover_metadata.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_arguments.py
  - api/services/admin_arguments.py
  - app/src/routes/admin/pipeline/+page.server.ts
  - app/src/routes/admin/pipeline/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - app/src/routes/admin/pipeline/check-duplicate/+server.ts
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/parser/cover_extractor.py
  - pipeline/tests/test_cover_extractor.py
findings:
  critical: 4
  warning: 5
  info: 2
  total: 11
status: issues_found
---

# Phase 19: Code Review Report

**Reviewed:** 2026-06-30
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 19 adds docket-based deduplication (D-01), cover-metadata extraction (D-07), nullable
`argued_date` (D-08), and a job-detail metadata card (D-13–D-15). The cover extractor and test
suite are well-structured and the per-file guards are generally correct. However, the data flow
between the SvelteKit form, FastAPI, and the ingest subprocess contains a critical disconnection
that silently drops the `primary_docket` and `question_number` values the operator enters — so
the core deduplication feature (D-01) never fires from the UI. Three additional blockers are
present: a NOT NULL constraint crash on a rarely-exercised code path, a migration downgrade that
will fail after NULL dates exist, and a security gap (unconstrained SSRF on the photo-URL fetch).
Five warnings round out the review.

---

## Critical Issues

### CR-01: `primary_docket` and `question_number` are silently dropped — D-01 deduplication never fires

**Files:**
- `api/routers/admin.py:140-163` (create_job endpoint)
- `app/src/routes/admin/pipeline/+page.server.ts:39-72` (form action)

**Issue:** The SvelteKit form action correctly appends `primary_docket` and `question_number` to
the multipart `FormData` it POSTs to `POST /api/admin/jobs`. FastAPI's `create_job` handler
declares only two `Form(...)` parameters — `pdf_url` and `pdf_file`. FastAPI silently ignores
any extra form fields, so both values are thrown away before the handler runs. The
`spawn_pipeline_step` calls that follow also never include `--primary-docket` or `--question`
flags, so the ingest subprocess always runs with `args.primary_docket = None` and
`args.question = 1` (the CLI default). The net effect is that `Argument.source_docket` is
always `NULL` regardless of what the operator typed, and the unique constraint
`uq_arguments_source_docket_question` never prevents a duplicate. The preflight
check-duplicate call does its job, but any duplicate entered via the form will silently create a
second argument row.

**Fix:** Add Form parameters to `create_job` and pass them through to the subprocess:

```python
# api/routers/admin.py — create_job signature
@router.post("/jobs", status_code=202, response_model=AdminJobResponse)
async def create_job(
    pdf_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    primary_docket: Optional[str] = Form(None),   # ADD
    question_number: int = Form(1),               # ADD
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    ...
    # URL mode — append docket/question to subprocess args
    spawn_pipeline_step(
        "ingest", job.id,
        ["--url", pdf_url, "--primary-docket", primary_docket, "--question", str(question_number)]
        if primary_docket else ["--url", pdf_url, "--question", str(question_number)]
    )
```

Also store `primary_docket` and `question_number` on the `AdminJob` row at creation time (or
pass them through the DB so rerun can replay them). The same fix is needed for the upload and
local-file branches.

---

### CR-02: Ingest creates `Case` rows with `case_name=None` when consolidated dockets are supplied without a primary docket

**File:** `pipeline/commands/ingest.py:358-367`

**Issue:** In job-driven mode, `primary_docket` and `case_name` may both be `None`. The code
builds `all_dockets` by filtering out `None` from the primary slot but still appends
`args.dockets` unconditionally. If the caller passes any consolidated dockets (`args.dockets`)
alongside `primary_docket=None`, the loop at line 342 creates `Case` rows with
`case_name=case_name` where `case_name` is `None`. `Case.case_name` is declared
`nullable=False` in the ORM model (models.py:149), so PostgreSQL raises a NOT NULL violation at
the `flush()` on line 369. The job is then silently marked FAILED by the outer exception
handler, with a confusing `IntegrityError` message.

The same loop also computes `is_lead=(case.docket_number == primary_docket)` (line 399). When
`primary_docket is None`, this comparison is always `False`, so no `CaseArgument` row is marked
`is_lead=True`. `get_argument_detail` then returns `None` (no lead case found), making the
argument invisible in every admin view.

**Fix:** Add a guard before the loop; if `case_name is None`, substitute a placeholder string
that satisfies the NOT NULL constraint:

```python
# pipeline/commands/ingest.py — before the Case loop
effective_case_name = case_name or f"Pending review (job {args.job_id})"

# In the Case constructor:
new_case = Case(
    docket_number=docket,
    docket_number_norm=docket.replace("-", ""),
    case_name=effective_case_name,   # was: case_name
    ...
)
```

For the `is_lead` issue, designate the first docket in `all_dockets` as lead when
`primary_docket is None`:

```python
lead_docket = primary_docket if primary_docket is not None else (all_dockets[0] if all_dockets else None)
# ...
is_lead=(case.docket_number == lead_docket)
```

---

### CR-03: Migration downgrade sets `argued_date NOT NULL` without backfilling — will fail after NULL rows are inserted

**File:** `alembic/versions/0011_add_source_docket_cover_metadata.py:72-76`

**Issue:** The `downgrade()` reverses the `argued_date` nullability change by calling
`op.alter_column("arguments", "argued_date", nullable=False)` directly. After the upgrade ships
and job-driven ingest runs, some `arguments` rows will have `argued_date = NULL`. Running
`alembic downgrade` at that point fails with a PostgreSQL NOT NULL constraint violation
(`ALTER TABLE cannot alter column "argued_date" to NOT NULL because it contains null values`).

**Fix:** Add a backfill step before tightening the constraint:

```python
def downgrade() -> None:
    op.drop_constraint("uq_arguments_source_docket_question", "arguments", type_="unique")
    # Backfill NULL argued_dates before reinstating NOT NULL — prevents downgrade crash.
    op.execute("UPDATE arguments SET argued_date = CURRENT_DATE WHERE argued_date IS NULL")
    op.alter_column("arguments", "argued_date", nullable=False)
    op.drop_column("arguments", "cover_metadata")
    op.drop_column("arguments", "source_docket")
```

---

### CR-04: Unconstrained SSRF on `photo_url` — any URL accepted including internal metadata endpoints

**File:** `api/routers/admin.py:522-523`

**Issue:** The `POST /api/admin/jobs/{person_id}/photo` route accepts a `photo_url` form
parameter and fetches it with `httpx.AsyncClient(...).get(photo_url, follow_redirects=True)`.
There is no scheme or hostname validation before the request is made. An operator (or a
compromised admin session) can supply `http://169.254.169.254/latest/meta-data/` (DO/AWS
instance metadata), `http://localhost:5432/`, or any other internal service URL. The Pillow
image validation rejects non-images after the fetch, but the outbound request still reaches the
target and the response body is loaded into memory. This violates the SSRF mitigations applied
elsewhere in this codebase (T-07-01 pattern for PDF URLs).

The admin-only auth boundary reduces exploitability, but a legitimate admin account being
phished, combined with follow_redirects=True, makes this a meaningful risk.

**Fix:** Apply the same allow-list pattern used for PDF URLs. If photo URLs are only expected
to come from a small set of trusted sources (e.g., Wikipedia, Oyez, official portrait
repositories), add an explicit allowlist. At minimum, block private/link-local ranges and
enforce HTTPS:

```python
def _validate_photo_url(url: str) -> None:
    """Block private/internal URLs before fetching (SSRF mitigation, mirrors T-07-01)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(status_code=422, detail="Photo URL must use HTTPS.")
    host = parsed.hostname or ""
    # Block RFC-1918, loopback, link-local, and metadata ranges
    import ipaddress
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=422, detail="Photo URL host is not allowed.")
    except ValueError:
        pass  # hostname (not IP) — acceptable
```

---

## Warnings

### WR-01: `update_argument_metadata` unconditionally NULLs `source_docket` when field is omitted

**File:** `api/services/admin_arguments.py:461-465`

**Issue:** The `UPDATE` at line 461 always writes both `argued_date` and `source_docket` in
a single statement, setting them to the parsed value or `None`:

```python
.values(argued_date=parsed_date, source_docket=body.source_docket)
```

`MetadataUpdate.source_docket` defaults to `None` (schemas line 167), so if the operator saves
the metadata card after editing only `argued_date` and leaving the docket field blank, the
existing `source_docket` value is overwritten with `NULL`. This silently clears a docket that
may have been auto-populated by the cover extractor or entered earlier.

**Fix:** Apply a conditional update pattern consistent with `update_argument`:

```python
values_to_set: dict = {}
if parsed_date is not None or body.argued_date is not None:
    values_to_set["argued_date"] = parsed_date
if body.source_docket is not None:
    values_to_set["source_docket"] = body.source_docket
if values_to_set:
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(**values_to_set)
        .execution_options(synchronize_session=False)
    )
```

---

### WR-02: Preflight `handleSubmit` does not check `res.ok` — non-OK responses silently bypass duplicate warning

**File:** `app/src/routes/admin/pipeline/+page.svelte:48-63`

**Issue:** The duplicate-check fetch in `handleSubmit` calls `res.json()` without first
verifying `res.ok`. When the `check-duplicate` endpoint returns a non-200 status (e.g., 400
for missing params, 502 if FastAPI is unreachable), SvelteKit's `error()` helper returns a JSON
body `{message: "..."}`. The client successfully parses this, but `data.exists` is `undefined`,
which is falsy, so the `else` branch executes — `preflightCleared = true` and the form
submits. The catch block has the same behaviour (intentional for network errors) but the non-OK
case is not: a 400 from the proxy (caused by a bug, not a network failure) silently bypasses the
duplicate gate.

**Fix:**

```typescript
const res = await fetch(`/admin/pipeline/check-duplicate?...`);
if (!res.ok) {
    // Treat server errors the same as network errors — allow submit but log
    console.warn('[preflight] check-duplicate returned', res.status, '— proceeding');
    preflightCleared = true;
    (e.target as HTMLFormElement).requestSubmit();
    return;
}
const data = await res.json();
```

---

### WR-03: `_derive_slug` leaves URL-unsafe characters (apostrophes, ampersands, slashes) in slugs

**File:** `pipeline/commands/ingest.py:83-94`

**Issue:** `_derive_slug` strips spaces, periods, and commas but leaves apostrophes (`'`),
ampersands (`&`), slashes (`/`), and parentheses intact. Case names like
`"Dobbs v. Jackson Women's Health Organization"` produce the slug
`"dobbs-v-jackson-womens-health-organization"` (acceptable), but a case name like
`"Smith & Jones"` produces `"smith-&-jones"`, and `"City/County v. State"` produces
`"city/county-v-state"`. Ampersands in URL path segments break RFC 3986 parsing; forward
slashes create phantom path segments. The same `_derive_slug` function is imported and used by
`admin_arguments.py` for re-derivation on operator edits, compounding the exposure.

**Fix:** Extend the replacement chain:

```python
def _derive_slug(case_name: str) -> str:
    import re
    slug = case_name.lower()
    slug = slug.replace("'", "")      # apostrophes: Women's -> womens
    slug = slug.replace("&", "and")   # ampersands
    slug = slug.replace("/", "-")     # slashes
    slug = slug.replace("(", "").replace(")", "")
    slug = slug.replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"-{2,}", "-", slug)  # collapse consecutive dashes
    return slug.strip("-")
```

---

### WR-04: `CAPTION_SEP_RE` character class includes literal `x` and `X` — may silently discard petitioner name lines

**File:** `pipeline/parser/cover_extractor.py:49`

**Issue:** `CAPTION_SEP_RE = re.compile(r'^[\xad\-\s–—xX\*]+$')` is used to identify
separator lines between the SCOTUS header and the petitioner name. The Alderson format ends
separator lines with a trailing `x` (e.g., `\xad \xad \xad ... x`), so `x` and `X` were
included in the class. However, a line consisting solely of `x` or `X` would also match, and
the extractor would skip it rather than accumulate it as a name line. If a petitioner's name
happens to start with a solo `X` on its own line (abbreviated Latin or a short-form name), it
would be silently dropped, producing a truncated case name in the DB.

**Fix:** The trailing `x` in Alderson separators is preceded by soft hyphens and spaces; match
it as a suffix rather than an arbitrary class member:

```python
# Matches Alderson (\xad-based) and Heritage (dash-based) separators.
# The trailing ' x' in Alderson lines is anchored to the end with a preceding space.
CAPTION_SEP_RE = re.compile(r'^[\xad\-\s–—\*]+(?:\s+x)?$')
```

---

### WR-05: `parse.py` contains a soft-hyphen (U+00AD) literal in source code

**File:** `pipeline/commands/parse.py:57`

**Issue:** Line 57 reads:
```python
text = text.replace('­', '-')
```
The character between the quotes is a soft hyphen (U+00AD, UTF-8: `0xC2 0xAD`), not a visible
dash. This is functionally correct (it replaces soft hyphens with hyphens), but the invisible
character is a maintenance hazard: developers cannot distinguish it from an empty string literal
at a glance, editors may silently strip it on save, and code review tools that strip non-ASCII
characters will appear to produce a no-op replacement. This matches the known project bug
documented in `memory/project_known_bugs.md`.

**Fix:** Replace the invisible literal with an explicit Unicode escape so the intent is clear and the character survives editor normalization:

```python
text = text.replace('­', '-')  # U+00AD SOFT HYPHEN
```

---

## Info

### IN-01: Duplicate `_normalize_label_last_name` defined in both `parse.py` and `cover_extractor.py`

**Files:**
- `pipeline/commands/parse.py:404-423`
- `pipeline/parser/cover_extractor.py:173-189`

**Issue:** The same function exists in two files with nearly identical implementations (the only
difference is that `parse.py` imports `re` inside the function body). `parse.py` could simply
import `_normalize_label_last_name` from `cover_extractor` since it already imports other
symbols from that module.

**Fix:** Remove the copy in `parse.py` and import from `cover_extractor`:

```python
from pipeline.parser.cover_extractor import (
    extract_cover_metadata,
    extract_advocate_sides,
    _normalize_label_last_name,  # add
)
```

---

### IN-02: `[job_id]/+page.server.ts` logs internal error details to server console including FastAPI status codes

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:53-59, 75-82, 98-104`

**Issue:** The server load function logs strings like
`"GET /api/admin/people returned 500"` and raw exception messages with `console.error`. In a
production environment these entries end up in DO App Platform logs. While this is admin-only
infrastructure and not a high risk, internal API endpoint names and failure modes surfaced in
log aggregators should be treated as sensitive operational data per the project's
confidentiality posture.

**Fix:** Replace `console.error` with a structured logger that can be silenced at a log level,
or at minimum avoid interpolating full FastAPI response details into the message string. The
current pattern is acceptable for development; add a TODO to route through a production logger
before v1.3 deployment.

---

_Reviewed: 2026-06-30_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Plan 05 Supplement (2026-07-01)

**Files reviewed:** `app/src/routes/admin/pipeline/+page.svelte` (3-line gap closure fix)
**Correctness bugs:** 0
**Cleanup findings:** 2 (PLAUSIBLE, low severity)

### P05-C1: `formEl` typed as `HTMLFormElement` without `| undefined` (cleanup)

**File:** `app/src/routes/admin/pipeline/+page.svelte:33`

`let formEl: HTMLFormElement;` declares the binding without an initializer. TypeScript accepts `formEl.requestSubmit()` without a null check because the type excludes `undefined`. In practice, `bind:this` sets `formEl` synchronously on mount and the button is inside the form (so both mount together), making this safe at runtime. No action required; this is the standard Svelte `bind:this` pattern.

### P05-C2: Three `(e.target as HTMLFormElement).requestSubmit()` calls in `handleSubmit` inconsistent with new `formEl` ref (cleanup)

**File:** `app/src/routes/admin/pipeline/+page.svelte:58,66,71`

The new diff introduces `formEl` via `bind:this` for imperative submission, but the three existing resubmit calls inside `handleSubmit` still use `(e.target as HTMLFormElement).requestSubmit()`. Both reference the same element and are correct; the inconsistency is cosmetic only. Could be unified in a future cleanup pass.

**Status:** advisory — no blocking issues in plan 05 changes.
