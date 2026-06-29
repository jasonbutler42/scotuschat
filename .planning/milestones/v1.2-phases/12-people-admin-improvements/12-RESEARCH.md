# Phase 12: People Admin Improvements - Research

**Researched:** 2026-06-23
**Domain:** FastAPI file upload / SQLAlchemy atomic transactions / SvelteKit multipart form actions / DO Spaces image storage
**Confidence:** HIGH (codebase verified) / MEDIUM (external APIs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Photo Management (PADM-01)**
- D-01: Dual-path upload — if `do_spaces_bucket` is set, upload to Spaces and store full public URL in `people.photo_url`; if not set, save to `data/uploads/people/` and serve via FastAPI StaticFiles or dedicated endpoint; `photo_url` stores the accessible path.
- D-02: Bio & Photo section replaces the standalone `photo_url` text input with a combined widget: "Upload file" tab and "Enter URL" tab. Shows a preview above the tabs.
- D-03: If both file and URL are submitted, file upload takes precedence. URL-only submit updates `photo_url` directly without touching Spaces.

**Delete (PADM-02)**
- D-04: Delete surfaced only from the person edit page — not the directory listing.
- D-05: "Delete person" button at the bottom of `/admin/people/[id]`. Enabled only when the person has no rows in utterances, speaker_alias, case_appearances, argument_participants. Rendered disabled with tooltip when not eligible.
- D-06: API endpoint checks orphan status server-side before deleting — not reliant on client disabled state.
- D-07: After successful delete, redirect to `/admin/people`.

**Merge (PADM-03, PADM-04)**
- D-08: Merge initiated from the source person's edit page.
- D-09: Operator picks a target from a picker; after selecting, sees an inline confirmation: heading, transfer counts (utterances/aliases/appearances), "Confirm merge" button.
- D-10: Merge executes atomically in a single DB transaction — transfer all 4 FK tables then delete source. No commit between steps.
- D-11: After successful merge, redirect to `/admin/people/[target_id]`.

### Claude's Discretion
- Target-picker UI for merge (searchable `<select>` vs. inline list)
- Disabled delete button tooltip wording
- Whether merge section is always visible or revealed by expand button
- Photo preview styling in the combined upload widget
- Whether count preview is fetched eagerly on target selection or after a "Check counts" step

### Deferred Ideas (OUT OF SCOPE)
- DO Spaces ACL setup for `people/` prefix
- Image crop UI
- `photo_url` format decision beyond dual-path approach
- Bulk merge or bulk delete
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PADM-01 | Operator can upload a profile photo file or enter a photo URL; both paths store the image on the server and update the person's photo | FastAPI UploadFile + Pillow validation + boto3/StaticFiles dual-path; SvelteKit multipart form action |
| PADM-02 | Operator can delete a person record that has no associated utterances, aliases, or appearances | FastAPI DELETE endpoint with server-side orphan COUNT check returning 409; client-side disabled button |
| PADM-03 | Operator can merge two person records; all utterances, aliases, and appearances transfer from source to target before source is deleted | SQLAlchemy async with db.begin() wrapping 4 UPDATEs + DELETE; merge service function |
| PADM-04 | Merge confirmation shows a count of records that will transfer before the operator commits | GET merge-preview endpoint returning {utterances, aliases, appearances, argument_participants}; eagerly fetched on target select |
</phase_requirements>

---

## Summary

Phase 12 adds three admin operations to the person edit page at `/admin/people/[id]`: profile photo upload, orphan-only delete, and atomic people merge. All three require new FastAPI endpoints, new service functions, and SvelteKit form action handlers. The existing multi-action pattern from Phase 11 (multiple named actions in one `+page.server.ts`) scales cleanly to the four actions needed here: `save` (existing), `photo`, `merge`, `delete`.

The most complex sub-problem is the photo upload dual-path: when DO Spaces is configured, the FastAPI endpoint receives the file bytes, validates them via Pillow, and uploads to Spaces via boto3; otherwise it writes to `data/uploads/people/{person_id}.{ext}` and returns a serve-path. The SvelteKit `photo` form action must use `enctype="multipart/form-data"` on its own dedicated `<form>` element — the main save form must not gain multipart enctype (it submits JSON via PATCH, not form data). This is the most common architectural mistake in this type of integration.

The merge operation is conceptually straightforward but must be disciplined about atomicity: all four FK-table UPDATE statements plus the source DELETE must execute inside a single `async with db.begin()` block. The existing codebase establishes `.execution_options(synchronize_session=False)` as a project-wide rule for every UPDATE/DELETE — this must be applied to each of the four merge UPDATE statements.

**Primary recommendation:** Use four named form actions (`save`, `photo`, `merge`, `delete`); the `photo` action uses its own `<form enctype="multipart/form-data">`; the merge action is a separate `<form>` posting to `?/merge`; the delete action is a separate `<form>` posting to `?/delete`. No changes to the save form's structure or enctype.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Photo file receipt and validation | API / Backend (FastAPI) | — | File bytes must be validated server-side; client content_type is spoofable |
| Photo storage (Spaces path) | API / Backend (boto3 + DO Spaces) | — | boto3 runs inside FastAPI container only |
| Photo storage (local fallback) | API / Backend (FastAPI StaticFiles) | Filesystem | No SvelteKit involvement; StaticFiles mount on `/uploads` path |
| Photo URL persistence | Database (people.photo_url) | — | Sole DB write authority |
| Orphan count check (delete guard) | API / Backend (FastAPI) | — | Server-side enforcement regardless of client disabled state |
| Delete operation | API / Backend (FastAPI) | Database | DELETE endpoint with orphan pre-check |
| Merge count preview | API / Backend (FastAPI GET) | — | Reads 4 COUNT queries, returns JSON |
| Merge atomic execution | Database / SQLAlchemy | API / Backend | `async with db.begin()` owns the transaction |
| Merge / Delete UI triggers | Frontend Server (SvelteKit) | Browser | Named form actions in +page.server.ts |
| Photo widget tab state | Browser / Client | — | Svelte `$state` tab tracking; no server round-trip |
| Merge target picker + count display | Browser / Client | Frontend Server | Target list loaded server-side; count fetched client-side via fetch |

---

## Standard Stack

### Core (already in project — no new installs required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | >=0.115 | New endpoints: photo, merge-preview, merge, delete | Already used; UploadFile + File() handles multipart natively |
| SQLAlchemy async | >=2.0 | Atomic merge transaction | `async with db.begin()` established pattern |
| Pillow | 12.2.0 | Image byte validation before upload | Already installed (pulled by pdfplumber); official PIL fork |
| boto3 | >=1.34 | Spaces photo upload | Already used in `api/services/spaces.py` |
| SvelteKit | ^2.21.0 | `photo`, `merge`, `delete` named form actions | Already the app framework |

### Supporting (no new installs)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `pathlib.Path` | stdlib | `data/uploads/people/` directory creation | Local dev fallback — `Path.mkdir(parents=True, exist_ok=True)` |
| Python `io.BytesIO` | stdlib | Wrap bytes for Pillow and boto3 | Both require file-like objects |
| FastAPI `StaticFiles` | bundled with fastapi[standard] | Serve locally-stored photos at `/uploads/people/` | Only if local path used |

### No new packages required

This phase installs zero new packages. All required capabilities (Pillow, boto3, FastAPI, SQLAlchemy, SvelteKit) are already declared in `requirements.txt` and `app/package.json`.

**Installation:** None required.

---

## Package Legitimacy Audit

> All packages in this phase are already in `requirements.txt` and confirmed installed via `pip show`. No new packages are introduced. The legitimacy checker returned "SUS" verdicts for all PyPI packages due to "too-new" heuristics and null weekly download signals from the PyPI downloads API — these are false positives for well-established packages already in active use in the codebase.

| Package | Registry | Age | Source Repo | Verdict | Disposition |
|---------|----------|-----|-------------|---------|-------------|
| Pillow 12.2.0 | PyPI | Active — 2010+ | github.com/python-pillow/Pillow | Already in requirements.txt | Approved — existing dependency |
| boto3 >=1.34 | PyPI | Active — 2015+ | github.com/boto/boto3 | Already in requirements.txt | Approved — existing dependency |
| fastapi >=0.115 | PyPI | Active — 2019+ | github.com/fastapi/fastapi | Already in requirements.txt | Approved — existing dependency |
| sqlalchemy >=2.0 | PyPI | Active — 2006+ | sqlalchemy.org | Already in requirements.txt | Approved — existing dependency |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious:** none (all are established packages already in active use)

---

## Architecture Patterns

### System Architecture Diagram

```
Operator Browser
     |
     | multipart POST ?/photo (file bytes)
     | POST ?/merge (target_id)
     | POST ?/delete
     | GET /api/admin/people/{id}/merge-preview?target_id=N  (client fetch)
     v
SvelteKit +page.server.ts
  photo action  ──► POST /api/admin/people/{id}/photo  (multipart, file bytes forwarded)
  merge action  ──► POST /api/admin/people/{id}/merge  (JSON {target_id})
  delete action ──► DELETE /api/admin/people/{id}
  load          ──► GET /api/admin/people/{id}  (existing)
                ──► GET /api/admin/people (people list for merge picker + roles)
     |
     v
FastAPI admin router (api/routers/admin.py)
  POST /api/admin/people/{id}/photo
    ├─ receive UploadFile
    ├─ Pillow validate (UnidentifiedImageError → 422)
    ├─ if do_spaces_bucket:
    │     boto3 upload_fileobj → Spaces key → full public URL
    │     UPDATE people SET photo_url = full_url
    └─ else:
          write bytes to data/uploads/people/{id}.{ext}
          UPDATE people SET photo_url = /uploads/people/{id}.{ext}
          (StaticFiles mount serves /uploads → data/uploads/)

  GET /api/admin/people/{id}/merge-preview?target_id=N
    ├─ SELECT COUNT(*) FROM utterances WHERE person_id = source_id
    ├─ SELECT COUNT(*) FROM speaker_alias WHERE person_id = source_id
    ├─ SELECT COUNT(*) FROM case_appearances WHERE person_id = source_id
    └─ SELECT COUNT(*) FROM argument_participants WHERE person_id = source_id
       → returns {utterances, aliases, appearances, argument_participants}

  POST /api/admin/people/{id}/merge  (body: {target_id})
    └─ async with db.begin():
          UPDATE utterances SET person_id=target WHERE person_id=source
          UPDATE speaker_alias SET person_id=target WHERE person_id=source
          UPDATE case_appearances SET person_id=target WHERE person_id=source
          UPDATE argument_participants SET person_id=target WHERE person_id=source
          DELETE FROM people WHERE id=source
       → redirect to /admin/people/{target_id}

  DELETE /api/admin/people/{id}
    ├─ orphan check: COUNT(*) across all 4 FK tables WHERE person_id=id
    ├─ if any count > 0: return 409 Conflict
    └─ DELETE FROM people WHERE id=id
       → redirect to /admin/people

     |
     v
PostgreSQL 16
  people (id, photo_url, ...)
  utterances (person_id FK)
  speaker_alias (person_id FK)
  case_appearances (person_id FK)
  argument_participants (person_id FK)
```

### Recommended Project Structure Changes

```
api/
├── services/
│   ├── admin_people.py       # add: upload_photo, get_merge_preview, merge_people, delete_person_if_orphan
│   └── spaces.py             # add: upload_photo_to_spaces(key, image_bytes, content_type) -> str
├── schemas/
│   └── admin_people.py       # add: MergeRequest, MergePreview, PhotoUpdateResponse
├── routers/
│   └── admin.py              # add 4 new endpoints + StaticFiles mount (local path)
app/src/routes/admin/people/[id]/
├── +page.server.ts           # add: photo, merge, delete actions; extend load for people list
└── +page.svelte              # restructure Bio & Photo; add Merge section; add Delete section
data/uploads/
└── people/                   # new subdirectory (mkdir -p, created on demand)
```

### Pattern 1: FastAPI Multipart Photo Upload Endpoint

**What:** `POST /api/admin/people/{id}/photo` receives an UploadFile, validates it with Pillow, then dispatches to Spaces or local path.

**When to use:** Any file upload route that must validate image bytes server-side.

```python
# Source: FastAPI docs https://fastapi.tiangolo.com/tutorial/request-files/
# and existing create_job upload pattern in api/routers/admin.py

from io import BytesIO
from PIL import Image, UnidentifiedImageError
from fastapi import UploadFile, File, HTTPException
import asyncio

@router.post("/people/{person_id}/photo", response_model=PersonDetail)
async def upload_person_photo(
    person_id: int,
    photo_file: UploadFile | None = File(None),
    photo_url: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> PersonDetail:
    # D-03: file takes precedence over URL
    if photo_file is not None:
        # Check MIME type as first gate (client-supplied, spoofable — Pillow is second gate)
        if not (photo_file.content_type or "").startswith("image/"):
            raise HTTPException(status_code=422, detail="Uploaded file must be an image.")

        file_bytes = await photo_file.read()

        # Pillow second gate — raises UnidentifiedImageError for invalid images
        try:
            with Image.open(BytesIO(file_bytes)) as img:
                img_format = img.format  # "JPEG", "PNG", "WEBP"
                img.verify()            # verify() can only be called once; do not reopen
        except (UnidentifiedImageError, Exception):
            raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")

        # Derive extension from detected format
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        ext = ext_map.get(img_format or "", "jpg")
        content_type = photo_file.content_type or f"image/{ext}"

        result = await people_service.upload_photo(
            db, person_id, file_bytes, ext, content_type
        )
    elif photo_url is not None:
        result = await people_service.update_photo_url(db, person_id, photo_url)
    else:
        raise HTTPException(status_code=422, detail="Provide either a file or a URL.")

    if result is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return PersonDetail(**result)
```

### Pattern 2: Atomic Merge Transaction

**What:** SQLAlchemy async atomic block wrapping 4 UPDATE statements plus DELETE.

**When to use:** Any operation that must transfer data across multiple tables and delete a row — all-or-nothing.

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
# and project pattern: execution_options(synchronize_session=False) on every statement

from sqlalchemy import update, delete, select, func as sqlfunc

async def merge_people(
    db: AsyncSession, source_id: int, target_id: int
) -> dict | None:
    """Transfer all FK rows from source to target, then delete source.

    Returns the refreshed target person dict on success.
    Returns None if either person does not exist.
    Raises ValueError if source == target.
    All operations execute inside a single async with db.begin() block —
    any failure rolls back the entire transaction (D-10).
    """
    if source_id == target_id:
        raise ValueError("Source and target must be different people.")

    # Verify both exist before starting the transaction
    source = (await db.execute(select(Person).where(Person.id == source_id))).scalar_one_or_none()
    target = (await db.execute(select(Person).where(Person.id == target_id))).scalar_one_or_none()
    if source is None or target is None:
        return None

    # Atomic transfer — no commit between steps
    async with db.begin():
        for model, col in [
            (Utterance, Utterance.person_id),
            (SpeakerAlias, SpeakerAlias.person_id),
            (CaseAppearance, CaseAppearance.person_id),
            (ArgumentParticipant, ArgumentParticipant.person_id),
        ]:
            await db.execute(
                update(model)
                .where(col == source_id)
                .values({col.key: target_id})
                .execution_options(synchronize_session=False)
            )
        await db.execute(
            delete(Person)
            .where(Person.id == source_id)
            .execution_options(synchronize_session=False)
        )
    # Transaction committed — now fetch refreshed target
    return await get_person_detail(db, target_id)
```

### Pattern 3: SvelteKit Named Photo Action with Multipart

**What:** A separate `<form enctype="multipart/form-data">` for the photo action, keeping the main save form JSON-only.

**When to use:** Any file upload in a page that already has a non-file form. Do NOT add enctype to the save form.

```typescript
// Source: SvelteKit docs + project pattern (api/routers/admin.py PDF upload reference)

// In +page.server.ts — photo named action
photo: async ({ request, params, fetch }) => {
    const formData = await request.formData();
    const photoFile = formData.get('photo_file') as File | null;
    const photoUrl = (formData.get('photo_url') as string | null)?.trim() || null;

    // Build multipart body to forward to FastAPI
    const outForm = new FormData();
    if (photoFile && photoFile.size > 0) {
        outForm.append('photo_file', photoFile, photoFile.name);
    }
    if (photoUrl) {
        outForm.append('photo_url', photoUrl);
    }

    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/photo`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
            // No Content-Type header — fetch sets multipart boundary automatically
            body: outForm,
        });
    } catch {
        return fail(502, { photoError: 'Photo could not be saved. Try again.' });
    }

    if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        if (res.status === 422) {
            return fail(422, {
                photoError: 'The uploaded file is not a valid image. Please upload a JPG, PNG, or WebP file.',
            });
        }
        return fail(502, { photoError: 'Photo could not be saved. Try again.' });
    }

    throw redirect(303, '/admin/people/' + params.id);
},
```

```svelte
<!-- In +page.svelte — dedicated photo form, separate from save form -->
<form
  method="POST"
  action="?/photo"
  enctype="multipart/form-data"
  use:enhance={() => {
    photoSubmitting = true;
    return async ({ result, update }) => {
      photoSubmitting = false;
      await update();
    };
  }}
>
  <!-- tab-driven: show file input or URL input based on activeTab state -->
  {#if activeTab === 'upload'}
    <input type="file" name="photo_file" accept="image/*" />
  {:else}
    <input type="text" name="photo_url" placeholder="https://…" />
  {/if}
  <button type="submit">{photoSubmitting ? 'Saving photo…' : 'Save photo'}</button>
</form>
```

### Pattern 4: StaticFiles Mount for Local Photo Serving

**What:** Mount `data/uploads/` as a static files route so locally-stored photos are accessible at `/uploads/people/{filename}`.

**When to use:** When `do_spaces_bucket` is not configured (local dev fallback, D-01).

```python
# Source: FastAPI docs — StaticFiles
# Add to api/main.py (or wherever the FastAPI app object is created)

from fastapi.staticfiles import StaticFiles
import os

# Only mount if the uploads directory exists (creates it on first use)
uploads_path = "data/uploads"
os.makedirs(uploads_path, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")
```

The local photo URL stored in `people.photo_url` would be `/uploads/people/{person_id}.{ext}` — a path the SvelteKit frontend can resolve against `FASTAPI_BASE_URL` or as a relative path from the origin. Confirm the serving strategy (relative to FastAPI base vs. served by SvelteKit proxy) before implementing.

### Pattern 5: Orphan Check Service Function

**What:** Count FK rows before delete; return 409 if any exist.

```python
async def delete_person_if_orphan(db: AsyncSession, person_id: int) -> bool | None:
    """Delete person only if they have no FK rows across the 4 child tables.

    Returns True on success, False if not orphaned (caller returns 409),
    None if person does not exist (caller returns 404).
    Server-side check is authoritative — client disabled state is defense-in-depth only (D-06).
    """
    person = (await db.execute(select(Person).where(Person.id == person_id))).scalar_one_or_none()
    if person is None:
        return None

    counts = []
    for model, col in [
        (Utterance, Utterance.person_id),
        (SpeakerAlias, SpeakerAlias.person_id),
        (CaseAppearance, CaseAppearance.person_id),
        (ArgumentParticipant, ArgumentParticipant.person_id),
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == person_id)
        )).scalar_one()
        counts.append(count)

    if any(c > 0 for c in counts):
        return False  # Not orphaned

    await db.execute(
        delete(Person)
        .where(Person.id == person_id)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return True
```

### Anti-Patterns to Avoid

- **Adding `enctype="multipart/form-data"` to the main save form:** The save action sends a JSON body via PATCH. Adding multipart enctype would break JSON parsing on the FastAPI side. The photo upload must use its own dedicated `<form>` with a named action.
- **Relying on `img.verify()` alone without catching the right exceptions:** `verify()` raises a generic `Exception` (not always `UnidentifiedImageError`) for some corrupted images. Always catch `(UnidentifiedImageError, Exception)` together.
- **Calling operations on an `Image` object after `verify()`:** `verify()` can only be called once; the image object is exhausted afterward. Get `img.format` before calling `verify()`, or reopen the image.
- **Omitting `.execution_options(synchronize_session=False)` on UPDATE/DELETE:** This is a project-wide rule established in `admin_jobs.py`. Every `update()` and `delete()` statement must include it.
- **Committing inside `async with db.begin()`:** The context manager commits automatically on exit. Calling `await db.commit()` inside the block causes an error. Only `await db.execute()` calls belong inside the block.
- **Forwarding `Content-Type: multipart/form-data` header from SvelteKit to FastAPI:** When using the `fetch` API with a `FormData` body, do NOT set the `Content-Type` header manually — the browser/Node.js `fetch` sets it automatically with the correct multipart boundary. Manually setting it omits the boundary and breaks parsing.
- **Using `photo_url` hidden field in the save form while also having a dedicated photo form:** The save action currently reads `photo_url` from form data and sends it in the PATCH body. After Phase 12, the save action should either drop the `photo_url` field entirely (since photo management moves to the photo action) or keep it for URL-only saves — but the two paths must not conflict.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image format detection | Custom byte-sniffing | `Pillow Image.open()` + `img.format` | Handles JPEG, PNG, WEBP, GIF, BMP variants; correct for all header patterns |
| Atomic multi-table transfer | Manual commit-after-each-UPDATE | `async with db.begin()` | Single-statement failure rolls back all prior statements automatically |
| S3-compatible upload | Custom HTTP multipart | `boto3.upload_fileobj()` | Handles retry, chunking, error codes; already proven in `spaces.py` |
| Static file serving | Custom route reading file bytes | FastAPI `StaticFiles` | Handles ETag, Range, Content-Type, caching headers correctly |
| Multipart form forwarding | Manual boundary construction | Python `FormData` (built-in) | `fetch` with FormData sets boundary automatically; manual construction is error-prone |

**Key insight:** Every "build vs. buy" decision in this phase has an established precedent already in the codebase. The photo upload mirrors `upload_pdf_to_spaces()`, the atomic transaction mirrors the project's existing `async with db.begin()` guidance, and the StaticFiles approach mirrors the `data/uploads/` local PDF serving pattern.

---

## Common Pitfalls

### Pitfall 1: Photo Save Form vs. Main Save Form Enctype Conflict

**What goes wrong:** Developer adds `enctype="multipart/form-data"` to the main save form so it can submit a file. FastAPI's PATCH `/api/admin/people/{id}` expects `application/json` (it uses `body: PersonUpdate`). The multipart form sends URL-encoded/multipart data that Pydantic cannot parse.

**Why it happens:** The file input is inside the same visual section ("Bio & Photo") as the rest of the save form, so it feels natural to put them in one form.

**How to avoid:** The photo upload is a **separate named action** (`?/photo`) with its **own `<form enctype="multipart/form-data">`** element, completely outside the main save `<form>`. The main save form keeps `method="POST" action="?/save"` with no enctype (defaults to `application/x-www-form-urlencoded`, then the action reformats to JSON for the PATCH call).

**Warning signs:** If FastAPI returns 422 with "value is not a valid dict" or "field required" on the save action after adding file input, this is the cause.

### Pitfall 2: Pillow `verify()` Exhausts the Image Object

**What goes wrong:** Code calls `img.verify()` then tries to read `img.format` or `img.size` — getting `None` or an error because `verify()` leaves the image in an invalid state.

**Why it happens:** Pillow's `verify()` is a one-shot operation that reads to end-of-stream and validates; the image cannot be used afterward.

**How to avoid:** Read `img.format` (and any other metadata needed) BEFORE calling `img.verify()`:
```python
with Image.open(BytesIO(file_bytes)) as img:
    img_format = img.format   # read FIRST
    img.verify()              # then verify
```

**Warning signs:** `img.format` returns `None` after `verify()` was called first.

### Pitfall 3: Missing `execution_options(synchronize_session=False)` in Merge Transaction

**What goes wrong:** `UPDATE utterances SET person_id = target_id WHERE person_id = source_id` raises a SQLAlchemy synchronization error because the session's identity map is not updated to reflect the bulk UPDATE.

**Why it happens:** SQLAlchemy's async session tracks ORM instances in an identity map. Bulk UPDATE/DELETE statements bypass instance-level tracking. The `synchronize_session=False` option tells SQLAlchemy not to attempt identity-map synchronization.

**How to avoid:** Every `update()` and `delete()` statement in the merge function must include `.execution_options(synchronize_session=False)`. This is the project-wide pattern established in `admin_jobs.py` and documented in `admin_people.py` module docstring.

**Warning signs:** `sqlalchemy.exc.InvalidRequestError` during bulk UPDATE inside `async with db.begin()`.

### Pitfall 4: SvelteKit FormData File Forwarding — Do Not Set Content-Type Header

**What goes wrong:** SvelteKit action code manually sets `'Content-Type': 'multipart/form-data'` when forwarding to FastAPI. FastAPI receives the multipart body but cannot parse it because the boundary parameter is missing from the Content-Type header.

**Why it happens:** The correct multipart Content-Type header looks like `multipart/form-data; boundary=----WebKitFormBoundary...`. When you manually set the header, you omit the boundary.

**How to avoid:** When creating a `FormData` object and passing it as `body` to `fetch()`, **do not set Content-Type**. Node.js `fetch` (used by SvelteKit server) sets the header automatically with the correct boundary.

**Warning signs:** FastAPI returns 422 with "There was an error parsing the body" on the photo endpoint.

### Pitfall 5: StaticFiles Mount Path and SvelteKit Proxy Interaction

**What goes wrong:** Photos stored locally at `data/uploads/people/abc.jpg` are served by FastAPI at `http://localhost:8000/uploads/people/abc.jpg`. The SvelteKit frontend tries to render `<img src="/uploads/people/abc.jpg">` against the SvelteKit origin (port 5173 in dev) and gets a 404 because SvelteKit doesn't proxy `/uploads/*`.

**Why it happens:** The `photo_url` stored in the DB is a path relative to FastAPI's origin, not SvelteKit's origin.

**How to avoid:** Two options:
1. Store the full URL in `photo_url` (e.g., `http://localhost:8000/uploads/people/abc.jpg`) — but this leaks the internal API URL.
2. Add a SvelteKit route or proxy rule that forwards `/uploads/*` to FastAPI in dev.
3. Store only the path, and in the Svelte template render `<img src="{FASTAPI_BASE_URL}{person.photo_url}">` — but `FASTAPI_BASE_URL` is server-only, so this requires passing it through the load function or using a public env var for the base URL.

The cleanest approach for this project: store only the relative path (e.g., `/uploads/people/1.jpg`) and construct the full URL in the `+page.server.ts` load function before sending `person` to the client, appending `FASTAPI_BASE_URL` server-side. The client receives a fully-qualified URL and renders it directly. This keeps `FASTAPI_BASE_URL` server-only.

**Warning signs:** `<img>` tag shows broken image in the UI when local fallback is active; browser devtools shows 404 on the image URL.

### Pitfall 6: Merge to Self

**What goes wrong:** Operator selects the current person as merge target. All FK rows get UPDATE'd to the same person_id (no-op), then the source person is deleted — the person disappears from the system entirely with their data intact but now pointing to a deleted row.

**Why it happens:** The UI target picker should exclude the current person, but the server endpoint must also guard against this case since the picker can be bypassed.

**How to avoid:** The `merge_people` service function raises `ValueError("Source and target must be different people.")` when `source_id == target_id`. The router catches this and returns 422.

**Warning signs:** Person disappears from directory after "merging" — their utterances remain but the person row is gone.

### Pitfall 7: photo action and save action both writing photo_url

**What goes wrong:** The existing `save` action reads `formData.get('photo_url')` and includes it in the PATCH body. After Phase 12, the photo widget's URL tab also submits via the `photo` action. If the save form still sends `photo_url`, saving any other field (bio, name) will overwrite whatever photo was set by the photo action if the save form's `photo_url` field is empty.

**Why it happens:** The save form currently has a `photo_url` text input. Phase 12 removes that input (replaced by the photo widget), but if the hidden field or input survives in the form HTML, it sends an empty string that becomes NULL in the PATCH body.

**How to avoid:** Remove the `photo_url` input entirely from the main save form's HTML. The `update_person()` service function normalizes empty `photo_url` to None and writes it — an empty `photo_url` in a save action will clear a previously-set photo. After Phase 12, `photo_url` must not be sent by the save action at all (it is managed exclusively by the photo action).

---

## Code Examples

### Verified FK column names (from `api/models/models.py`)

```python
# Source: C:\workspace\scotuschat\project\api\models\models.py (verified via Read tool)
Utterance.person_id           # Column(Integer, ForeignKey("people.id"), nullable=True)
SpeakerAlias.person_id        # Column(Integer, ForeignKey("people.id"), nullable=False)
CaseAppearance.person_id      # Column(Integer, ForeignKey("people.id"), nullable=False)
ArgumentParticipant.person_id # Column(Integer, ForeignKey("people.id"), nullable=True)
```

### Merge preview query pattern

```python
# Source: project pattern from admin_people.py (COUNT + scalar_one)
async def get_merge_preview(db: AsyncSession, source_id: int, target_id: int) -> dict | None:
    """Return counts of FK rows that would transfer from source to target.

    Returns None if source_id does not exist.
    target_id existence is not required for the preview — planner can show counts
    even before confirming target selection.
    """
    source = (await db.execute(select(Person).where(Person.id == source_id))).scalar_one_or_none()
    if source is None:
        return None

    results = {}
    for key, model, col in [
        ("utterances", Utterance, Utterance.person_id),
        ("aliases", SpeakerAlias, SpeakerAlias.person_id),
        ("appearances", CaseAppearance, CaseAppearance.person_id),
        ("argument_participants", ArgumentParticipant, ArgumentParticipant.person_id),
    ]:
        count = (await db.execute(
            select(sqlfunc.count()).select_from(model).where(col == source_id)
        )).scalar_one()
        results[key] = count
    return results
```

### Spaces photo upload function

```python
# Source: mirrors upload_pdf_to_spaces in api/services/spaces.py (verified via Read tool)
def upload_photo_to_spaces(image_bytes: bytes, key: str, content_type: str) -> str:
    """Upload image bytes to DO Spaces under the given key.

    key format: people/{person_id}.{ext}
    Returns the key so the caller can construct the full public URL.
    Full URL = {do_spaces_endpoint}/{do_spaces_bucket}/{key}
      e.g. https://nyc3.digitaloceanspaces.com/mybucket/people/42.jpg
    """
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(image_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
        # ACL: "public-read" only if bucket-level Block Public Access is disabled.
        # This is deferred (see Deferred section) — store URL and serve privately for now.
    )
    return key
```

### Alembic chain verification

```
Migration chain verified from codebase:
0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 (current head)

Phase 12 does NOT require a new Alembic migration. All required columns exist:
- people.photo_url: Column(String(500), nullable=True) — present since 0001
- All 4 FK columns on child tables — present since initial schema

No schema changes needed.
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `photo_url` plain text input in save form | Combined upload/URL widget with separate `photo` action | Enables file upload without breaking existing save flow |
| No delete operation in people admin | `DELETE /api/admin/people/{id}` with orphan pre-check | Safe deletion of unused person records |
| No people merge | Atomic 4-table transfer + source delete | Resolves duplicate person records created during resolve step |

**No deprecated patterns introduced in this phase.** All patterns (multi-action forms, atomic transactions, Spaces upload, StaticFiles) are established in prior phases.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | FastAPI `StaticFiles` is available without additional install (bundled with `fastapi[standard]`) | Standard Stack | If not, `pip install aiofiles` is the only dependency needed — low risk |
| A2 | DO Spaces ACL is not configured for public-read in the `people/` prefix during Phase 12 (deferred per CONTEXT.md) — photos uploaded to Spaces during dev/test may not be publicly readable | Architecture | Photos would be stored but not rendered correctly until ACL is configured; local fallback unaffected |
| A3 | The local photo serve path resolves best by constructing a full URL server-side in `+page.server.ts` load (appending FASTAPI_BASE_URL to the relative path) | Pitfall 5 | If FASTAPI_BASE_URL is not accessible at runtime (e.g., misconfigured), photo renders broken |
| A4 | `ArgumentParticipant.person_id` being nullable (null until resolved) means some participants may have person_id IS NULL — these rows are not affected by merge UPDATE (WHERE person_id = source_id naturally excludes NULL rows) | Architecture Patterns | No risk — SQL WHERE on a specific integer ID never matches NULL rows |

**If this table is empty:** All other claims in this research were verified against the codebase or official docs.

---

## Open Questions

1. **Photo URL format in `people.photo_url` for local fallback**
   - What we know: D-01 says `photo_url` stores "the accessible path." The DB column is `String(500)`.
   - What's unclear: Should local photos store an absolute URL like `http://localhost:8000/uploads/people/1.jpg`, a path like `/uploads/people/1.jpg`, or something else? The stored value must be usable by the SvelteKit frontend, but `FASTAPI_BASE_URL` is server-only.
   - Recommendation: Store the relative path (e.g., `/uploads/people/1.jpg`) and reconstruct the full URL in `+page.server.ts` load by prepending `FASTAPI_BASE_URL`. Pass the full URL to the Svelte component as `person.photo_url_full` or similar. This keeps `FASTAPI_BASE_URL` server-only and the stored value environment-agnostic.

2. **StaticFiles mount location in the FastAPI app**
   - What we know: The FastAPI app is defined somewhere (likely `api/main.py` or similar); StaticFiles is mounted on the app object.
   - What's unclear: The research did not read `api/main.py`. The `app.mount()` call must go there.
   - Recommendation: Executor reads `api/main.py` before adding the StaticFiles mount.

3. **Save action `photo_url` field removal**
   - What we know: The existing save action reads `formData.get('photo_url')` and sends it in the PATCH body. The save form has a `<input name="photo_url">` element.
   - What's unclear: Whether to remove `photo_url` from the PATCH body entirely or keep it as a fallback. If removed, `update_person()` will always set `photo_url=None` (since the field is not sent), which will clear photos on every save.
   - Recommendation: Remove `photo_url` from the save form HTML entirely. Remove `photo_url` from the `PersonUpdate` schema fields that the save action sends. The `photo_url` field in `PersonUpdate` should remain for backward compatibility but the save action should not include it in the JSON body (omit it from the `JSON.stringify({...})` call). Alternatively, serialize the current `data.person.photo_url` as a hidden field in the save form so the PATCH preserves it — but this creates a race condition if the photo action runs concurrently. Cleanest: redirect after photo action re-runs load, so the page always reflects current state.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Pillow | Image validation | ✓ | 12.2.0 (confirmed via pip show) | None needed — installed |
| boto3 | DO Spaces upload | ✓ (in requirements.txt) | >=1.34 | Local file fallback (D-01) |
| FastAPI StaticFiles | Local photo serving | ✓ (bundled with fastapi[standard]) | >=0.115 | N/A |
| Python pathlib | Local directory creation | ✓ | stdlib | N/A |
| Node.js fetch / FormData | SvelteKit action file forwarding | ✓ | Node 24.15.0 | N/A |
| DO Spaces bucket | Spaces upload path | [depends on env] | — | Local file fallback (D-01) |

**Missing dependencies with no fallback:** none.

**Missing dependencies with fallback:** DO Spaces bucket (if not configured, local file path is used per D-01 — this is expected behavior, not a failure).

---

## Validation Architecture

> `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is skipped per config.

---

## Security Domain

> PADM-01 through PADM-04 touch file upload and destructive data operations. Security analysis required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | Pillow image validation (server-side); content_type check + magic bytes |
| V6 Cryptography | no | No crypto in this phase |
| V12 File Upload | yes | Validate image bytes server-side; reject non-images; cap file size |
| V4 Access Control | yes | Admin-only endpoints via existing `verify_admin_token` dependency on router |
| V2 Authentication | no | Auth handled by router-level dependency — no changes |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious file upload (polyglot image/executable) | Tampering | Pillow `Image.open()` + `img.verify()` server-side; content_type check is first gate only |
| IDOR on merge/delete (operator provides wrong person_id) | Elevation of Privilege | Server-side person existence check before any write; 404 on unknown IDs |
| Merge-to-self data loss | Tampering | `source_id == target_id` raises ValueError → 422 before any DB write |
| Delete bypass (client-side disabled circumvented) | Tampering | Server-side orphan COUNT check in `delete_person_if_orphan`; 409 if not orphaned (D-06) |
| Decompression bomb via image upload | Denial of Service | Pillow raises `DecompressionBombWarning` at `MAX_IMAGE_PIXELS` threshold; catch or configure limit |
| Stored XSS via `photo_url` URL field | XSS | `photo_url` String(500) stored in DB; rendered in `<img src>` attribute — URL value is benign in src; validate URL starts with https:// if accepting arbitrary URLs |
| Partial merge state on crash | Data Integrity | `async with db.begin()` auto-rollback on exception — no partial-merge possible |

### File Upload Security Notes

The existing PDF upload in `admin.py` (lines 162-165) validates magic bytes (`b"%PDF"`) as a second layer after `content_type` check. The photo upload should follow the same two-layer pattern:
1. First gate: `content_type.startswith("image/")` — client-supplied, spoofable
2. Second gate: Pillow `Image.open()` + `img.verify()` — server-side truth

This mirrors the established project pattern exactly. [VERIFIED: codebase — admin.py lines 162-165]

---

## Sources

### Primary (HIGH confidence — verified against codebase)
- `api/models/models.py` — FK column names for all 4 child tables verified
- `api/services/spaces.py` — `upload_pdf_to_spaces` pattern for photo mirror
- `api/services/admin_people.py` — `update_person()` and `.execution_options(synchronize_session=False)` patterns
- `api/routers/admin.py` — existing file upload (PDF) pattern with magic bytes + content_type check
- `app/src/routes/admin/people/[id]/+page.server.ts` — multi-action pattern; existing save action
- `app/src/routes/admin/people/[id]/+page.svelte` — current Bio & Photo section structure
- `alembic/versions/0007_add_published_at.py` — confirmed current migration head; no new migration needed

### Secondary (MEDIUM confidence — official docs)
- [FastAPI request files docs](https://fastapi.tiangolo.com/tutorial/request-files/) — UploadFile patterns
- [SQLAlchemy async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html) — `async with session.begin()` pattern
- [Pillow Image.html docs](https://pillow.readthedocs.io/en/stable/reference/Image.html) — `Image.open()`, `verify()`, `UnidentifiedImageError`

### Tertiary (LOW confidence — web search)
- Web search: SvelteKit multipart form actions with use:enhance — confirmed enctype=multipart/form-data is required; FormData body works with Node fetch without manual Content-Type header

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already in requirements.txt and pip-confirmed installed
- Architecture patterns: HIGH — derived from reading actual project codebase (models, services, routers, Svelte files)
- Security threats: MEDIUM — standard file upload threat patterns, mitigated by existing project patterns
- Pillow validation: MEDIUM — docs fetched from pillow.readthedocs.io
- SvelteKit multipart: LOW — web search; official SvelteKit docs not directly fetched

**Research date:** 2026-06-23
**Valid until:** 2026-07-23 (stable stack — all packages pre-existing; no fast-moving dependencies)
