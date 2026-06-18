# Stack Research — v1.2 Pre-Launch Polish Additions

**Domain:** v1.2 incremental additions to existing SvelteKit 2 + Svelte 5 Runes + FastAPI + PostgreSQL app
**Researched:** 2026-06-18
**Confidence:** MEDIUM (community docs + official docs; consistent cross-source findings)

---

## Context: What Already Exists (Do Not Re-research)

Validated v1.0/v1.1 stack — no changes:

- SvelteKit 2.x + adapter-node, Svelte 5 Runes (`$state`, `$derived`, `$effect`)
- FastAPI 0.115+ with Pydantic v2; `python-multipart` already in `fastapi[standard]`
- SQLAlchemy 2.0 async + asyncpg (`statement_cache_size=0` in `connect_args`) + Alembic hand-written migrations
- PostgreSQL 16 on Digital Ocean managed Postgres (PgBouncer transaction mode)
- boto3 already in requirements.txt for DO Spaces PDF upload — `get_spaces_client()` pattern exists in `api/services/spaces.py`
- All FastAPI calls from SvelteKit go through `+page.server.ts` server load functions; `FASTAPI_BASE_URL` is server-only
- SvelteKit form actions + `use:enhance` established pattern throughout admin UI

This document covers ONLY net-new additions for v1.2 features.

---

## New Libraries Needed

### Frontend (npm) — One New Package

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `bits-ui` | `^2.18.1` | Headless Popover for speaker card | Svelte 5 native (uses `$state` / `$derived` internally). Built on Floating UI — handles positioning, collision detection, and ARIA automatically. Clean composable API: `Popover.Root` / `Popover.Trigger` / `Popover.Content`. Headless (bring-your-own Tailwind styles) — no style conflicts with the existing design. Current latest as of 2026-06-18. |

**Install:**
```bash
cd app
npm install bits-ui
```

### Backend Python — One New Package

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| `Pillow` | `>=11.0` | Image validation + resize before DO Spaces upload | Validate content type (JPEG/PNG/WebP), reject non-images, resize to a max dimension before upload so storage stays predictable. Standard FastAPI image upload companion. Current stable is 12.x. |

**Add to `requirements.txt`:**
```
Pillow>=11.0
```

---

## No New Libraries Needed For These Features

| Feature | Why No New Library |
|---------|-------------------|
| Image upload to DO Spaces | boto3 already in requirements.txt. Same `get_spaces_client()` pattern as PDF upload — add a new `upload_image_to_spaces()` helper alongside the existing `upload_pdf_to_spaces()`. |
| People merge operation | Pure SQLAlchemy 2.0 async DML: `update()` + `delete()` statements in one session transaction. No extension or helper library needed. |
| Argument metadata edit form | FastAPI already handles form data via Pydantic models. SvelteKit `use:enhance` form actions already established. No new libraries. |
| Structured name fields migration | Alembic `op.add_column` + `op.execute()` SQL backfill in one revision — the established hand-written migration pattern. |
| Unified top nav | Extract to `src/lib/components/TopNav.svelte`, import in both layout files. Component composition, not a routing pattern change. No new npm package. |
| File upload form action (image) | `request.formData()` → `file.arrayBuffer()` is already the validated pattern from v1.1 PDF upload. No new npm package. |

---

## Integration Patterns

### 1. bits-ui Popover in Svelte 5

```svelte
<script lang="ts">
  import { Popover } from "bits-ui";

  let open = $state(false);
</script>

<Popover.Root bind:open>
  <Popover.Trigger>
    <!-- avatar img or initials element -->
  </Popover.Trigger>
  <Popover.Portal>
    <Popover.Content sideOffset={8} class="z-50 ...your Tailwind classes...">
      <!-- person card: photo, name, role, tenure, appointing president -->
    </Popover.Content>
  </Popover.Portal>
</Popover.Root>
```

`Popover.Portal` renders outside the DOM subtree — avoids z-index stacking context issues from the two-column chat layout. `sideOffset` controls the gap from the trigger element. Placement defaults to `bottom`; set `side="top"` or `side="right"` as needed. No manual Floating UI wiring required.

### 2. Image Upload to DO Spaces (FastAPI + boto3)

Add a new helper to `api/services/spaces.py` alongside the existing `upload_pdf_to_spaces`:

```python
import asyncio, io
from PIL import Image

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB

def _upload_image_sync(image_bytes: bytes, key: str, content_type: str) -> str:
    client = get_spaces_client()
    client.upload_fileobj(
        io.BytesIO(image_bytes),
        settings.do_spaces_bucket,
        key,
        ExtraArgs={"ContentType": content_type, "ACL": "public-read"},
    )
    return key

async def upload_image_to_spaces(image_bytes: bytes, key: str, content_type: str) -> str:
    """Resize and upload a profile photo. Returns the Spaces key."""
    return await asyncio.to_thread(_upload_image_sync, image_bytes, key, content_type)
```

FastAPI endpoint handler pattern:
```python
from fastapi import UploadFile, File, HTTPException
from PIL import Image
import io

async def handle_photo_upload(person_id: int, file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, "Image must be JPEG, PNG, or WebP")
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Image exceeds 5 MB limit")
    img = Image.open(io.BytesIO(content))
    img.thumbnail((400, 400), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    fmt = "JPEG" if file.content_type == "image/jpeg" else "PNG"
    img.save(out, format=fmt, optimize=True)
    out.seek(0)
    key = f"people/{person_id}/photo.{fmt.lower()}"
    await upload_image_to_spaces(out.read(), key, file.content_type)
    return key
```

**ACL note:** DO Spaces has a documented community-reported issue where per-object `ACL: public-read` is sometimes silently ignored. Mitigation: also enable bucket-level public access in the DO Spaces control panel for the `people/` prefix. Profile photos are public content (displayed to all site visitors) — no presigned URLs needed. Serve via the CDN URL: `https://<bucket>.<region>.cdn.digitaloceanspaces.com/<key>`.

### 3. People Merge — SQLAlchemy 2.0 Async

Pure DML within one async session. No new libraries. Dependency order matters (FK constraints):

```python
from sqlalchemy import update, delete

async def merge_people(source_id: int, target_id: int, session: AsyncSession) -> None:
    """Transfer all FK references from source to target, then delete source."""
    for model, col in [
        (Utterance, Utterance.person_id),
        (SpeakerAlias, SpeakerAlias.person_id),
        (CaseAppearance, CaseAppearance.person_id),
        (ArgumentParticipant, ArgumentParticipant.person_id),
    ]:
        await session.execute(
            update(model).where(col == source_id).values({col: target_id})
        )
    await session.execute(delete(Person).where(Person.id == source_id))
    await session.commit()
```

All five DML statements run within one implicit transaction. If any `execute` raises, the session rolls back automatically before `commit` is reached. No savepoints or nested transactions needed.

### 4. Alembic Migration for Name Field Split

In a single hand-written revision file:

```python
def upgrade() -> None:
    # Add new nullable columns — no constraint violations on existing rows
    op.add_column("people", sa.Column("first_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("last_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("middle_name", sa.String(150), nullable=True))
    op.add_column("people", sa.Column("suffix", sa.String(50), nullable=True))
    op.add_column("people", sa.Column("appointing_president", sa.String(200), nullable=True))
    op.add_column("people", sa.Column("party_of_appointing_president", sa.String(50), nullable=True))
    # Best-effort backfill: first word = first_name, last word = last_name
    # Middle names and suffixes will be left NULL for operator to fill manually
    op.execute("""
        UPDATE people
        SET first_name = split_part(full_name, ' ', 1),
            last_name   = reverse(split_part(reverse(full_name), ' ', 1))
        WHERE full_name IS NOT NULL
    """)
    # Do NOT drop full_name — retain as display fallback and for backward compat

def downgrade() -> None:
    op.drop_column("people", "party_of_appointing_president")
    op.drop_column("people", "appointing_president")
    op.drop_column("people", "suffix")
    op.drop_column("people", "middle_name")
    op.drop_column("people", "last_name")
    op.drop_column("people", "first_name")
```

**Important:** The backfill is approximate. "Ruth Bader Ginsburg" → first=Ruth, last=Ginsburg, middle=NULL. This is acceptable — the operator will correct values via the people editor. Do NOT add NOT NULL constraints to the new columns in this migration. Name fields will be filled over time via the admin UI.

### 5. Unified Top Nav — Component Composition

No new library. Extract shared markup to `src/lib/components/TopNav.svelte`:

```svelte
<script lang="ts">
  interface Props {
    isAdmin?: boolean;
  }
  let { isAdmin = false }: Props = $props();
</script>

<nav class="...">
  <!-- shared nav content -->
  {#if isAdmin}
    <!-- admin-specific links -->
  {/if}
</nav>
```

Import in both layout files:
- `src/routes/+layout.svelte` — `<TopNav />`
- `src/routes/admin/+layout.svelte` — `<TopNav isAdmin />`

No routing changes. No route groups needed. The existing layout hierarchy is already correct.

---

## Alternatives Considered

| Feature | Recommended | Alternative | Why Not |
|---------|-------------|-------------|---------|
| Popover | `bits-ui` Popover | `@floating-ui/dom` direct | Requires manual Svelte 5 wiring: `useFloating`, `useClick`, `useInteractions`, prop spreading. bits-ui wraps all of this. Same positioning engine underneath — no tradeoff. |
| Popover | `bits-ui` Popover | `@skeletonlabs/floating-ui-svelte` | **Archived October 2025. Deprecated. End of life. Hard no.** |
| Popover | `bits-ui` Popover | HTML native `<details>`/`<summary>` | Cannot anchor to a trigger position. No collision detection. Not keyboard-accessible for a floating card. |
| Popover | `bits-ui` Popover | CSS Anchor Positioning (AnchorPop) | Browser support still incomplete as of mid-2026 (no Firefox GA). Not production-safe. |
| Image resize | `Pillow` (Python) | `sharp` (npm, Node side) | Image processing belongs on the FastAPI side where upload validation already occurs. No benefit to moving it to Node. |
| Image resize | `Pillow` | `imageio` | Pillow is the standard; imageio adds no benefit for resize + format conversion. |
| Photo serving | Direct CDN URL | Presigned URLs | Profile photos are public content visible to all site visitors. Presigned URLs add complexity and expiry handling with zero security benefit. |
| Name split | SQL `split_part()` in Alembic | Python string splitting in upgrade() | `op.execute()` with a SQL expression runs in the DB transaction — no extra Python loop, no ORM loading. Faster and simpler for a one-time backfill. |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `@skeletonlabs/floating-ui-svelte` | Archived October 2025, deprecated, no support, end of life | `bits-ui` Popover |
| `@floating-ui/dom` (standalone) | bits-ui already wraps it; direct use requires substantial boilerplate for this use case | `bits-ui` |
| Any full component library (Flowbite-Svelte, shadcn-svelte, Skeleton) | Style conflicts with existing raw Tailwind design; pulling in a library for one component is over-engineering | `bits-ui` (headless, no styles shipped) |
| `aiobotocore` or async S3 client | Overkill; `boto3` wrapped in `asyncio.to_thread` is the established pattern in this codebase | Existing `boto3` + `asyncio.to_thread` |
| `python-multipart` explicit pin | Already bundled in `fastapi[standard]`; adding an explicit pin risks version conflicts | Leave as transitive dep of fastapi[standard] |
| `aiofiles` | Not needed; FastAPI's `UploadFile.read()` is already async | FastAPI built-in `UploadFile` |
| SvelteKit route groups for nav sharing | Adds routing restructuring complexity to a problem that's solved by a shared Svelte component | `TopNav.svelte` component imported in both layouts |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `bits-ui@^2.18.1` | `svelte@^5.30.0` | bits-ui 2.x requires Svelte 5. Do not use bits-ui 0.x (Svelte 4 only). |
| `bits-ui@^2.18.1` | `@sveltejs/kit@^2.21.0` | No conflict. bits-ui is framework-agnostic at the Kit routing level. |
| `Pillow>=11.0` | `Python 3.12` | Pillow 11.x+ targets Python 3.9+. Full 3.12 support confirmed. |
| `Pillow>=11.0` | `FastAPI 0.115+` | No conflict. Pillow is a pure image processing dependency with no FastAPI integration layer. |

---

## Sources

- https://bits-ui.com/docs/components/popover — Popover component API, Svelte 5 Runes usage (MEDIUM confidence)
- https://floating-ui-svelte.vercel.app/examples/popovers — Confirmed v0.3.9, Svelte 5 native; archived repo (MEDIUM confidence)
- https://github.com/skeletonlabs/floating-ui-svelte/discussions/169 — Confirmed archived October 2025, deprecated (MEDIUM confidence)
- https://docs.digitalocean.com/products/spaces/reference/s3-compatibility/ — DO Spaces ACL support via x-amz-acl header (MEDIUM confidence)
- https://www.digitalocean.com/community/questions/spaces-api-put-call-ignores-acl-header — Known ACL ignore issue; prefer bucket-level public policy (MEDIUM confidence)
- https://pillow.readthedocs.io/en/stable/reference/Image.html — Pillow 12.x thumbnail/resize API (MEDIUM confidence)
- https://alembic.sqlalchemy.org/en/latest/ops.html — op.add_column / op.execute backfill pattern (MEDIUM confidence)
- https://docs.sqlalchemy.org/en/20/orm/queryguide/dml.html — SQLAlchemy 2.0 async UPDATE/DELETE DML for merge (MEDIUM confidence)

---
*Stack research for: SCOTUS Chat v1.2 pre-launch polish*
*Researched: 2026-06-18*
