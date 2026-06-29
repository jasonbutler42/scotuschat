# Phase 12: People Admin Improvements - Pattern Map

**Mapped:** 2026-06-23
**Files analyzed:** 5 (3 modified, 2 extended)
**Analogs found:** 5 / 5

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `api/routers/admin.py` | router | request-response | `api/routers/admin.py` (existing) | exact — same file, adding 4 endpoints |
| `api/services/admin_people.py` | service | CRUD + batch | `api/services/admin_people.py` (existing) | exact — same file, adding 4 functions |
| `api/services/spaces.py` | service | file-I/O | `api/services/spaces.py` (existing) | exact — same file, adding 1 function |
| `api/schemas/admin_people.py` | model | request-response | `api/schemas/admin_people.py` (existing) | exact — same file, adding 3 schemas |
| `app/src/routes/admin/people/[id]/+page.server.ts` | server | request-response | `app/src/routes/admin/arguments/+page.server.ts` | role-match — multi-action pattern |
| `app/src/routes/admin/people/[id]/+page.svelte` | component | request-response | `app/src/routes/admin/people/[id]/+page.svelte` (existing) | exact — same file, restructuring sections |

---

## Pattern Assignments

### `api/routers/admin.py` — 4 new endpoints

**Analog:** `api/routers/admin.py` (existing file, lines 128–222 for the PDF upload pattern)

**Imports pattern** (lines 39–72, existing — no new imports needed beyond what's already there):
```python
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from api.core.config import settings
from api.core.database import get_db
from api.schemas.admin_people import PersonDetail, PersonUpdate, ...
from api.services import admin_people as people_service
from api.services import spaces as spaces_service
```
New imports to add: `from io import BytesIO`, `from PIL import Image, UnidentifiedImageError`, `from pathlib import Path`

**Auth pattern** (lines 92–96 — router-level dependency, no per-route changes):
```python
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```
All new endpoints inherit auth automatically — do not add `Depends(verify_admin_token)` per route.

**File upload endpoint pattern** (lines 128–222 — `create_job` with dual-path upload):
```python
@router.post("/jobs", status_code=202, response_model=AdminJobResponse)
async def create_job(
    pdf_url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
) -> AdminJobResponse:
    if pdf_file is not None:
        if pdf_file.content_type != "application/pdf":
            raise HTTPException(status_code=422, detail="...")
        header = await pdf_file.read(4)
        await pdf_file.seek(0)
        if header != b"%PDF":
            raise HTTPException(status_code=422, detail="...")
        file_bytes = await pdf_file.read()
        if settings.do_spaces_bucket:
            key = f"uploads/{job.id}.pdf"
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, spaces_service.upload_pdf_to_spaces, file_bytes, key)
        else:
            uploads_dir = Path("data/uploads")
            uploads_dir.mkdir(parents=True, exist_ok=True)
            local_path = uploads_dir / f"{job.id}.pdf"
            local_path.write_bytes(file_bytes)
```
The photo endpoint mirrors this exactly: replace PDF magic-byte check with Pillow `Image.open()` + `img.verify()`, replace `uploads/{job.id}.pdf` key with `people/{person_id}.{ext}`.

**Error handling pattern** (lines 153–165, 193–196 — HTTPException for client errors, re-raise for storage failures):
```python
try:
    await loop.run_in_executor(None, spaces_service.upload_pdf_to_spaces, file_bytes, key)
except Exception as upload_exc:
    await db.execute(
        update(AdminJob).where(...).values(status=AdminJobStatus.FAILED, ...)
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    raise HTTPException(status_code=502, detail="File upload failed. Please try again.") from upload_exc
```

**ValueError-to-422 pattern** (lines 299–303, `resolve_job`):
```python
try:
    updated_job = await jobs_service.resolve_job(db, job_id, body.matches)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```
The merge endpoint catches `ValueError("Source and target must be different people.")` from `merge_people()` using this pattern.

**New endpoint signatures to add:**
```python
@router.post("/people/{person_id}/photo", response_model=PersonDetail)
async def upload_person_photo(
    person_id: int,
    photo_file: Optional[UploadFile] = File(None),
    photo_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> PersonDetail: ...

@router.get("/people/{person_id}/merge-preview")
async def get_merge_preview(
    person_id: int,
    target_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict: ...

@router.post("/people/{person_id}/merge", response_model=PersonDetail)
async def merge_person(
    person_id: int,
    body: MergeRequest,
    db: AsyncSession = Depends(get_db),
) -> PersonDetail: ...

@router.delete("/people/{person_id}", status_code=200)
async def delete_person(
    person_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict: ...
```

---

### `api/services/admin_people.py` — 4 new service functions

**Analog:** `api/services/admin_people.py` (existing file)

**Module docstring pattern** (lines 1–16 — list new responsibilities):
```python
"""
Business logic for admin people management.

Responsibilities:
  - ...existing...
  - Photo upload with dual-path storage (PADM-01)
  - Merge preview count query (PADM-04)
  - Atomic multi-table merge (PADM-03, PADM-10)
  - Orphan-only delete (PADM-02)

Critical guards (project-wide pattern from admin_jobs.py):
  - EVERY update() / delete() statement includes .execution_options(synchronize_session=False)
  ...
"""
```

**Imports pattern** (lines 17–31 — extend existing imports):
```python
from sqlalchemy import delete, func as sqlfunc, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.models import (
    AdminJob, ArgumentParticipant, CaseAppearance,
    CourtTenure, Person, Role, SpeakerAlias, Utterance,
)
```
Add: `import io`, `from pathlib import Path`, `from PIL import Image` (in the upload function, not at module top if Pillow import is heavy — match project convention).

**Core fetch-guard pattern** (lines 219–221 — `update_person` opening guard):
```python
result = await db.execute(select(Person).where(Person.id == person_id))
person = result.scalar_one_or_none()
if person is None:
    return None
```
Every new service function (`upload_photo`, `delete_person_if_orphan`, `merge_people`) opens with this exact guard — returning `None` for 404, which the router translates to `HTTPException(404)`.

**execution_options pattern** (lines 84–88 — `_replace_tenures` DELETE):
```python
await db.execute(
    delete(CourtTenure)
    .where(CourtTenure.person_id == person_id)
    .execution_options(synchronize_session=False)
)
```
Every `update()` and `delete()` in the new merge/delete functions must include `.execution_options(synchronize_session=False)`.

**Commit-then-refresh pattern** (lines 256–257 — `update_person` end):
```python
await db.commit()
return await get_person_detail(db, person_id)
```
`upload_photo` and `delete_person_if_orphan` follow the same terminal pattern. `merge_people` uses `async with db.begin()` (auto-commit on exit) then calls `get_person_detail`.

**COUNT scalar pattern** (lines 127–152 — `list_people` uses `sqlfunc`):
```python
from sqlalchemy import func as sqlfunc
count = (await db.execute(
    select(sqlfunc.count()).select_from(Model).where(col == person_id)
)).scalar_one()
```
The orphan check and merge preview both use this exact form — one COUNT per FK table.

**Spaces dual-path pattern** (mirrors `create_job` in router, lines 170–214):
```python
if settings.do_spaces_bucket:
    key = f"people/{person_id}.{ext}"
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, spaces_service.upload_photo_to_spaces, file_bytes, key, content_type)
    photo_url = f"{settings.do_spaces_endpoint}/{settings.do_spaces_bucket}/{key}"
else:
    uploads_dir = Path("data/uploads/people")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    local_path = uploads_dir / f"{person_id}.{ext}"
    local_path.write_bytes(file_bytes)
    photo_url = f"/uploads/people/{person_id}.{ext}"
person.photo_url = photo_url
await db.commit()
return await get_person_detail(db, person_id)
```

**Atomic transaction pattern** (new — no existing analog in service layer, but established by project guidance):
```python
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
# db.begin() context manager auto-commits here — do NOT call db.commit() inside the block
return await get_person_detail(db, target_id)
```
CRITICAL: Do not call `await db.commit()` inside `async with db.begin()`. The context manager commits on clean exit and rolls back on exception.

---

### `api/services/spaces.py` — 1 new function

**Analog:** `api/services/spaces.py` (existing file, lines 37–50 — `upload_pdf_to_spaces`)

**Core pattern** (lines 37–50):
```python
def upload_pdf_to_spaces(file_bytes: bytes, key: str) -> str:
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    return key
```

**New function to add** — mirror exactly, changing `ContentType` to the caller-supplied value:
```python
def upload_photo_to_spaces(file_bytes: bytes, key: str, content_type: str) -> str:
    """Upload image bytes to DO Spaces under the given key.

    key format: people/{person_id}.{ext}
    Returns the key so the caller can construct the full public URL.
    """
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(file_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return key
```
The only differences from `upload_pdf_to_spaces`: accepts `content_type: str` parameter; passes it in `ExtraArgs` instead of hard-coding `"application/pdf"`.

---

### `api/schemas/admin_people.py` — 3 new schemas

**Analog:** `api/schemas/admin_people.py` (existing file)

**BaseModel pattern** (lines 18–28 — `TenureRow`):
```python
class TenureRow(BaseModel):
    seat: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
```

**model_config pattern** (lines 43–44, 68–69 — response models use `from_attributes`):
```python
model_config = {"from_attributes": True}
```
Add to `MergePreview` and `PhotoUpdateResponse` only if they are returned from the ORM. `MergeRequest` is a request body — no `model_config` needed.

**New schemas to add:**
```python
class MergeRequest(BaseModel):
    """POST body for POST /api/admin/people/{id}/merge."""
    target_id: int


class MergePreview(BaseModel):
    """Response from GET /api/admin/people/{id}/merge-preview."""
    utterances: int
    aliases: int
    appearances: int
    argument_participants: int


class PhotoUpdateResponse(BaseModel):
    """Alias for PersonDetail — router returns PersonDetail after photo update.

    No separate schema needed; router uses response_model=PersonDetail directly.
    """
    pass  # Not needed — use PersonDetail directly
```
`MergeRequest` and `MergePreview` follow the same Optional-fields or plain-int pattern. `PersonDetail` is reused as the response model for the photo endpoint — no new response schema required.

---

### `app/src/routes/admin/people/[id]/+page.server.ts` — 3 new actions + load extension

**Analog:** `app/src/routes/admin/people/[id]/+page.server.ts` (existing — lines 90–199) for action structure; `app/src/routes/admin/arguments/+page.server.ts` (lines 37–79) for multi-action redirect pattern.

**Imports pattern** (line 1 — existing, no changes):
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
```

**Load extension pattern** (lines 46–88 — extend load to also return `people` list for merge picker):
```typescript
export const load: PageServerLoad = async ({ fetch, params }) => {
    // existing: personRes, roles fetch...
    // NEW: also fetch people list for merge target picker
    let people: PersonListItem[] = [];
    try {
        const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
        if (peopleRes.ok) {
            const all: PersonListItem[] = await peopleRes.json();
            // Exclude current person from merge target list
            people = all.filter(p => p.id !== parseInt(params.id, 10));
        }
    } catch { /* degrade gracefully */ }
    return { person, roles, people };
};
```
The `people` list is already fetched for roles deduplication — reuse that fetch result and filter out `params.id` to get the merge picker list.

**Named action pattern** (lines 90–199 — existing `save` and `createRole` actions; extend `actions` object):
```typescript
export const actions: Actions = {
    save: async ({ request, params, fetch }) => { /* existing */ },
    createRole: async ({ request, fetch }) => { /* existing */ },

    // NEW ACTIONS:
    photo: async ({ request, params, fetch }) => { ... },
    merge: async ({ request, params, fetch }) => { ... },
    delete: async ({ request, params, fetch }) => { ... },
};
```

**Fetch-with-error-handling pattern** (lines 135–155 — `save` action):
```typescript
let res: Response;
try {
    res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
        method: 'PATCH',
        headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
        body: JSON.stringify({ ... }),
    });
} catch {
    return fail(502, { error: 'Could not save changes. Check the form and try again.' });
}
if (!res.ok) {
    return fail(422, { error: 'Could not save changes. Check the form and try again.' });
}
throw redirect(303, '/admin/people/' + params.id);
```

**Photo action pattern** — multipart forward (from RESEARCH.md Pattern 3):
```typescript
photo: async ({ request, params, fetch }) => {
    const formData = await request.formData();
    const photoFile = formData.get('photo_file') as File | null;
    const photoUrl = (formData.get('photo_url') as string | null)?.trim() || null;

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
            // DO NOT set Content-Type — fetch sets multipart boundary automatically
            body: outForm,
        });
    } catch {
        return fail(502, { photoError: 'Photo could not be saved. Try again.' });
    }
    if (!res.ok) {
        if (res.status === 422) {
            return fail(422, { photoError: 'Not a valid image. Please upload a JPG, PNG, or WebP file.' });
        }
        return fail(502, { photoError: 'Photo could not be saved. Try again.' });
    }
    throw redirect(303, '/admin/people/' + params.id);
},
```
CRITICAL: Never set `Content-Type` header when forwarding `FormData` to FastAPI — the boundary will be missing.

**Merge action pattern** (JSON POST → redirect to target):
```typescript
merge: async ({ request, params, fetch }) => {
    const formData = await request.formData();
    const target_id = formData.get('target_id') as string;
    if (!target_id) return fail(400, { mergeError: 'Select a target person.' });

    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}/merge`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
            body: JSON.stringify({ target_id: parseInt(target_id, 10) }),
        });
    } catch {
        return fail(502, { mergeError: 'Merge failed. Try again.' });
    }
    if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        return fail(res.status === 422 ? 422 : 502, { mergeError: detail.detail ?? 'Merge failed.' });
    }
    // Redirect to target — source no longer exists (D-11)
    throw redirect(303, '/admin/people/' + target_id);
},
```

**Delete action pattern** (DELETE → redirect to list):
```typescript
delete: async ({ params, fetch }) => {
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
            method: 'DELETE',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch {
        return fail(502, { deleteError: 'Delete failed. Try again.' });
    }
    if (!res.ok) {
        if (res.status === 409) {
            return fail(409, { deleteError: 'This person has associated records and cannot be deleted.' });
        }
        return fail(502, { deleteError: 'Delete failed. Try again.' });
    }
    throw redirect(303, '/admin/people');
},
```

---

### `app/src/routes/admin/people/[id]/+page.svelte` — restructure Bio & Photo section; add Merge and Delete sections

**Analog:** `app/src/routes/admin/people/[id]/+page.svelte` (existing file)

**Svelte 5 Runes state pattern** (lines 31–99 — `$state`, `$props`):
```svelte
<script lang="ts">
    let { data, form } = $props();
    let photoTab = $state<'upload' | 'url'>('upload');
    let photoSubmitting = $state(false);
    let mergeTargetId = $state<string>('');
    let mergePreview = $state<{ utterances: number; aliases: number; appearances: number; argument_participants: number } | null>(null);
    let mergeSubmitting = $state(false);
    let deleteSubmitting = $state(false);
</script>
```
Use `$state` for all reactive values. No legacy stores (`writable`, `readable`) allowed.

**Section card pattern** (lines 132–321 — `div` with inline dark-theme styles):
```svelte
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
    <h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0; line-height: 1.2;">
        Section Title
    </h2>
    <!-- section content -->
</div>
```
All new sections (Photo widget, Merge, Delete) use these exact token values: bg `#1e293b`, border `#334155`, body text `#94a3b8`, accent border `#93c5fd`, error `#ef4444`.

**use:enhance pattern** (lines 119–130 — save form):
```svelte
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
```
Every new `<form>` must use `use:enhance`. The photo form adds `enctype="multipart/form-data"` — the save form must NOT gain this attribute.

**Nested form pattern** (lines 252–319 — `createRole` inline form inside the main save form section):
The merge section uses a dedicated `<form method="POST" action="?/merge">` — a separate top-level form, not nested inside the main save form. This matches the `createRole` form approach (nested for createRole because it's logically part of the role section, but merge and delete are bottom-of-page standalone forms).

**Error display pattern** (lines 508–513):
```svelte
{#if form?.error}
    <p role="alert" style="color: #ef4444; font-size: 14px; margin: 0 0 8px 0;">
        {form.error}
    </p>
{/if}
```
New sections use `form?.photoError`, `form?.mergeError`, `form?.deleteError` as their respective namespaced error keys.

**Button pattern** (lines 516–522 — Save Changes button):
```svelte
<button
    type="submit"
    disabled={saveSubmitting}
    style="display: block; width: 100%; min-height: 44px; background: transparent; border: 1px solid #93c5fd; border-radius: 6px; font-size: 16px; font-weight: 600; color: #e2e8f0; cursor: pointer; opacity: {saveSubmitting ? 0.7 : 1};"
>
    {saveSubmitting ? 'Saving…' : 'Save changes'}
</button>
```
Delete button uses `border: 1px solid #ef4444` (red border, not accent blue) to signal destructive action.

**Photo tab state pattern** (new — no existing analog; use $state toggle):
```svelte
<div style="display: flex; gap: 0; margin-bottom: 16px;">
    <button type="button"
        onclick={() => photoTab = 'upload'}
        style="... border-bottom: {photoTab === 'upload' ? '2px solid #93c5fd' : '2px solid transparent'};">
        Upload file
    </button>
    <button type="button"
        onclick={() => photoTab = 'url'}
        style="... border-bottom: {photoTab === 'url' ? '2px solid #93c5fd' : '2px solid transparent'};">
        Enter URL
    </button>
</div>
{#if photoTab === 'upload'}
    <input type="file" name="photo_file" accept="image/*" ... />
{:else}
    <input type="text" name="photo_url" placeholder="https://…" ... />
{/if}
```

**Merge count preview pattern** (client-side fetch on target selection):
```svelte
async function fetchMergePreview(targetId: string) {
    if (!targetId) { mergePreview = null; return; }
    try {
        const res = await fetch(
            `/api/admin/people/${data.person.id}/merge-preview?target_id=${targetId}`,
            { headers: { 'X-Admin-Token': ... } }  // NOTE: ADMIN_TOKEN is server-only
        );
        // ALTERNATIVE: proxy through a dedicated +server.ts endpoint that adds the token
        if (res.ok) mergePreview = await res.json();
    } catch { mergePreview = null; }
}
```
IMPORTANT: `ADMIN_TOKEN` is a server-only env var. The merge preview fetch must go through SvelteKit server (either a `+server.ts` route that proxies to FastAPI, or load the preview server-side after target selection via a form action that returns data). Claude's discretion: simplest implementation is to fetch preview in the `merge` action pre-flight (fetch preview in `merge` action before executing if a "preview" flag is set), or add a `GET /api/admin/people/[id]/merge-preview/+server.ts` SvelteKit endpoint that proxies the FastAPI call server-side.

**Disabled button with tooltip pattern** (no existing analog — inline `title` attribute):
```svelte
<button
    type="submit"
    disabled={data.person_is_orphan === false || deleteSubmitting}
    title={data.person_is_orphan === false ? `This person has associated records and cannot be deleted.` : ''}
    style="... opacity: {!data.person_is_orphan ? 0.4 : 1}; cursor: {!data.person_is_orphan ? 'not-allowed' : 'pointer'};"
>
    Delete person
</button>
```
The `person_is_orphan` boolean comes from the load function — load calls the orphan count check or derives it from the person detail. Alternatively, the load passes `can_delete: boolean` derived from a COUNT query added to the load phase.

---

## Shared Patterns

### Authentication / Admin Token
**Source:** `api/routers/admin.py` lines 75–96 (router-level dependency)
**Apply to:** All new endpoints in `admin.py`
```python
# Already applied at router level — new endpoints inherit automatically.
# Never add `dependencies=[Depends(verify_admin_token)]` to individual routes.
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(verify_admin_token)],
)
```

**Source:** `app/src/routes/admin/people/[id]/+page.server.ts` line 1
**Apply to:** All new action `fetch()` calls in `+page.server.ts`
```typescript
headers: { 'X-Admin-Token': ADMIN_TOKEN }
// ADMIN_TOKEN from '$env/static/private' — never PUBLIC_
```

### Error Handling (Router Layer)
**Source:** `api/routers/admin.py` lines 253–257, 299–303, 357–360
**Apply to:** All 4 new router endpoints
```python
# Pattern A — None guard → 404
result = await people_service.some_function(db, person_id)
if result is None:
    raise HTTPException(status_code=404, detail="Person not found")

# Pattern B — ValueError → 422
try:
    result = await people_service.some_function(db, ...)
except ValueError as exc:
    raise HTTPException(status_code=422, detail=str(exc)) from exc
```

### execution_options on Every UPDATE/DELETE
**Source:** `api/services/admin_people.py` lines 84–88 (and established by admin_jobs.py)
**Apply to:** Every `update()` and `delete()` call in the 4 new service functions
```python
.execution_options(synchronize_session=False)
```
This is a project-wide mandatory rule — SQLAlchemy bulk UPDATE/DELETE bypass identity map tracking. Omitting this raises `InvalidRequestError` on async sessions.

### SvelteKit use:enhance (Mandatory)
**Source:** `app/src/routes/admin/people/[id]/+page.svelte` lines 119–130
**Apply to:** All new `<form>` elements (photo, merge, delete)
```svelte
use:enhance={() => {
    submittingFlag = true;
    return async ({ result, update }) => {
        submittingFlag = false;
        await update();
    };
}}
```

### Redirect After Mutation
**Source:** `app/src/routes/admin/people/[id]/+page.server.ts` line 158; `app/src/routes/admin/arguments/+page.server.ts` lines 58, 78
**Apply to:** photo, merge, delete actions
```typescript
throw redirect(303, '/admin/people/' + params.id);  // photo action
throw redirect(303, '/admin/people/' + target_id);   // merge action (D-11)
throw redirect(303, '/admin/people');                 // delete action (D-07)
```
`throw redirect(303, ...)` is SvelteKit's form action redirect. Always use 303 (POST-redirect-GET).

### Pillow Image Validation (Anti-Pattern Avoidance)
**Source:** RESEARCH.md Pitfall 2 — read format BEFORE calling verify()
**Apply to:** `upload_person_photo` router endpoint
```python
with Image.open(BytesIO(file_bytes)) as img:
    img_format = img.format   # MUST read format BEFORE verify()
    img.verify()              # verify() exhausts image object — no attributes readable after
ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
ext = ext_map.get(img_format or "", "jpg")
```

### Server-Only Env Vars
**Source:** CLAUDE.md Architecture Rule 2
**Apply to:** Any reference to `FASTAPI_BASE_URL` or `ADMIN_TOKEN`
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
// NEVER: import { PUBLIC_FASTAPI_BASE_URL } from '$env/static/public'
```

---

## No Analog Found

No files in this phase lack analogs. All patterns have direct codebase precedents.

| File | Role | Data Flow | Note |
|------|------|-----------|------|
| `api/main.py` (StaticFiles mount) | config | file-I/O | Not an analog gap — the `StaticFiles` mount is a one-liner added to the existing app factory. Research notes the file was not read; executor must read `api/main.py` before adding the mount. |

---

## Metadata

**Analog search scope:** `api/routers/`, `api/services/`, `api/schemas/`, `app/src/routes/admin/`
**Files read:** 7 (admin.py, admin_people.py, spaces.py, admin_people schema, people [id] page.server.ts, people [id] page.svelte, arguments page.server.ts)
**Pattern extraction date:** 2026-06-23
