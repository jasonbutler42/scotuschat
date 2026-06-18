# Architecture Research

**Domain:** Content-display web app with admin pipeline — v1.2 feature integration
**Researched:** 2026-06-18
**Confidence:** HIGH

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SvelteKit Frontend                           │
│                                                                     │
│  +layout.svelte (root)     +layout.svelte (admin/*)                 │
│    └── NavHeader (NEW)       └── AdminNavHeader (MODIFIED)          │
│                                                                     │
│  Public routes                 Admin routes                         │
│  /cases/[slug]/arguments/[id]  /admin/pipeline/[job_id]             │
│    └── ChatBubble (MODIFIED)   /admin/people/[id]/edit (MODIFIED)   │
│         └── SpeakerPopover     /admin/arguments/[id]/edit (NEW)     │
│              (NEW, bench only) /admin/people (MODIFIED)             │
└───────────────────────┬────────────────────────┬────────────────────┘
                        │ FASTAPI_BASE_URL        │ server-only
                        │ ($env/static/private)   │
┌───────────────────────▼────────────────────────▼────────────────────┐
│                        FastAPI Backend                              │
│                                                                     │
│  GET  /arguments/{id}/utterances  (MODIFIED — add person fields)    │
│  GET  /people/{id}                (MODIFIED — extend response)      │
│  GET  /api/admin/arguments/{id}   (NEW)                             │
│  PATCH /api/admin/arguments/{id}  (NEW)                             │
│  POST  /api/admin/people/{id}/image  (NEW)                          │
│  POST  /api/admin/people/merge    (NEW)                             │
│  DELETE /api/admin/people/orphaned (NEW)                            │
│  PATCH /api/admin/people/{id}     (MODIFIED — new fields)           │
└───────────────────────┬────────────────────────┬────────────────────┘
                        │ SQLAlchemy async        │ boto3
┌───────────────────────▼────────┐  ┌─────────────▼────────────────────┐
│       PostgreSQL 16            │  │       Digital Ocean Spaces        │
│                                │  │                                   │
│  people (MODIFIED — 6 cols)    │  │  uploads/{job_id}.pdf (existing)  │
│  court_tenures (unchanged)     │  │  images/{person_id}.{ext} (NEW)   │
│  arguments (unchanged)         │  └───────────────────────────────────┘
│  utterances (unchanged)        │
│  speaker_alias (unchanged)     │
│  admin_jobs (unchanged)        │
│  … (all other tables unchanged)│
└────────────────────────────────┘
```

---

## Component Responsibilities

### New Components

| Component | Layer | Responsibility |
|-----------|-------|----------------|
| `NavHeader.svelte` | SvelteKit | Shared top-nav rendered in root `+layout.svelte`; accepts `variant: 'public' | 'admin'` prop; used by both layouts |
| `SpeakerPopover.svelte` | SvelteKit | Floating card triggered by avatar click; bench-only; displays photo, name, role, tenure dates, appointing president/party |
| `admin/arguments/[id]/edit/+page.svelte` | SvelteKit | Form to correct argument title, docket, and date; calls PATCH /api/admin/arguments/{id} |
| `admin/arguments/[id]/edit/+page.server.ts` | SvelteKit | Load + form action; enforces that resolved_at cannot be set via this form |
| `GET /api/admin/arguments/{id}` route | FastAPI | Fetch argument + lead case metadata for the edit form |
| `PATCH /api/admin/arguments/{id}` route | FastAPI | Allows editing case_name, argued_date; explicitly blocks resolved_at via schema exclusion |
| `POST /api/admin/people/{id}/image` route | FastAPI | Accepts multipart, validates image type + magic bytes, uploads to DO Spaces, updates person.photo_url |
| `POST /api/admin/people/merge` route | FastAPI | Atomic transfer of utterances, aliases, appearances, argument_participants; DELETE source person |
| `DELETE /api/admin/people/orphaned` route | FastAPI | Deletes people rows where no utterances, aliases, or appearances reference them |
| `services/admin_arguments.py` | FastAPI | New service module for argument metadata read + update logic |
| Alembic migration 0006 | DB | Adds first_name, last_name, middle_name, suffix, appointed_by, appointing_party to people |

### Modified Components

| Component | What Changes |
|-----------|-------------|
| `root +layout.svelte` | Extract nav into `NavHeader.svelte`; remove `{#if !page.url.pathname.startsWith('/admin')}` branch; delegate to shared component |
| `admin/+layout.svelte` | Replace inline nav markup with `<NavHeader variant="admin">`; keep Pipeline Runner, People Editor links, and Logout button as admin-specific slots/props |
| `ChatBubble.svelte` | Avatar `<div>` becomes a `<button>` (bench side only); click opens `SpeakerPopover`; WCAG: `aria-haspopup="dialog"`, keyboard-dismissible |
| `PATCH /api/admin/people/{id}` | `PersonUpdate` schema and `update_person` service extended to accept `first_name`, `last_name`, `middle_name`, `suffix`, `appointed_by`, `appointing_party` |
| `PersonDetail` schema | Add new name/appointment fields to the response shape returned by GET and PATCH people endpoints |
| `admin/people/[id]/+page.svelte` | Add form fields for first/last/middle/suffix + appointing president + party; add image upload control |
| `GET /people/{id}` | `PersonResponse` extended with `photo_url`, `appointed_by`, `appointing_party`, and `tenures` so SpeakerPopover can be populated without a new endpoint |
| `PersonListItem` missing-fields logic | Evaluate whether structured name fields should be added to the missing list; `full_name` remains required, structured fields are supplementary |

---

## Recommended Project Structure (additions only)

```
app/src/
├── lib/
│   └── components/
│       ├── NavHeader.svelte           (NEW — shared nav, replaces inline markup in both layouts)
│       └── SpeakerPopover.svelte      (NEW — popover card for bench speakers)
└── routes/
    └── admin/
        └── arguments/
            └── [id]/
                └── edit/
                    ├── +page.server.ts  (NEW)
                    └── +page.svelte     (NEW)

api/
├── routers/
│   └── admin.py                       (MODIFIED — new argument + merge + image + orphan routes)
├── schemas/
│   ├── admin_arguments.py             (NEW — ArgumentDetail, ArgumentUpdate)
│   └── admin_people.py                (MODIFIED — PersonDetail/PersonUpdate get new fields)
└── services/
    ├── admin_arguments.py             (NEW — get_argument_detail, update_argument)
    ├── admin_people.py                (MODIFIED — merge_people, delete_orphaned added)
    └── spaces.py                      (MODIFIED — add upload_image_to_spaces helper)

alembic/versions/
└── 0006_add_structured_name_and_appointment.py  (NEW)
```

---

## Data Flow Changes

### Speaker Popover Flow

```
+page.server.ts loads argument page
    ↓
Calls GET /arguments/{id}/utterances (existing)
    AND calls GET /people/{id} for each unique bench speaker person_id (NEW calls)
    ↓
Returns: { utterances, argument, benchPeople: Map<personId, PersonDetail> }
    ↓
+page.svelte passes benchPeople map to ChatBubble for bench utterances
    ↓
User clicks bench avatar
    ↓
ChatBubble dispatches event with person_id
    ↓
+page.svelte looks up person in benchPeople map — no network call
    ↓
SpeakerPopover renders with pre-loaded data
```

**Why no client-side fetch:** `FASTAPI_BASE_URL` is `$env/static/private` — it must not be `PUBLIC_`. A client-side fetch from the browser cannot reach FastAPI directly. A proxy route (`/api/people/[id]`) would work but is unnecessary overhead when SSR can pre-load the small set of bench participants.

### Argument Metadata Edit Flow

```
Admin clicks "Edit" on an argument in the pipeline job detail view
    ↓
Navigates to /admin/arguments/[id]/edit
    ↓
+page.server.ts load → GET /api/admin/arguments/{id}
    Returns: { argument_id, case_name, docket_number, argued_date }
    ↓ server renders form
Operator corrects fields and submits
    ↓
+page.server.ts form action → PATCH /api/admin/arguments/{id}
    Body: { case_name?, argued_date? }  — resolved_at NOT in schema
    ↓
FastAPI admin_arguments service:
    UPDATE cases SET case_name=... WHERE id=(lead case id for argument)
    UPDATE arguments SET argued_date=... WHERE id=argument_id
    COMMIT
    ↓
Return updated ArgumentDetail
    ↓
Redirect to /admin/arguments/[id]/edit with success flash
```

**Note on schema:** The argument title lives on `cases.case_name`, not `arguments`. The service must resolve the lead case via `CaseArgument WHERE argument_id=X AND is_lead=TRUE` before issuing the cases UPDATE.

### People Merge Flow

```
POST /api/admin/people/merge  body: { source_id: int, target_id: int }
    ↓
FastAPI service (single transaction via async with db.begin()):
  1. Validate both IDs exist; source != target
  2. UPDATE utterances SET person_id=target WHERE person_id=source
  3. UPDATE speaker_alias SET person_id=target WHERE person_id=source
  4. UPDATE case_appearances SET person_id=target WHERE person_id=source
  5. UPDATE argument_participants SET person_id=target WHERE person_id=source
  6. DELETE FROM people WHERE id=source
  7. COMMIT (on context manager exit)
    ↓
Return 200 + updated target PersonDetail
```

### Image Upload Flow

```
Operator selects image file on /admin/people/[id] form
    ↓
SvelteKit form action (multipart) → POST /api/admin/people/{id}/image
    ↓
FastAPI:
  1. Validate content_type in {image/jpeg, image/png, image/webp}
  2. Read first 4 bytes — verify magic bytes
     PNG: b'\x89PNG'; JPEG: b'\xff\xd8\xff'
  3. key = f"images/{person_id}.{ext}"
  4. loop.run_in_executor → spaces_service.upload_image_to_spaces(bytes, key)
     (ACL: public-read so URL is directly accessible)
  5. public_url = f"{settings.do_spaces_endpoint}/{settings.do_spaces_bucket}/{key}"
  6. UPDATE people SET photo_url=public_url WHERE id=person_id
  7. COMMIT
    ↓
Return 200 + { photo_url: "https://..." }
    ↓
SvelteKit form action invalidates data, re-renders page with updated photo
```

---

## Architectural Patterns

### Pattern 1: Extend Existing Endpoint Before Adding New One

**What:** When the popover needs person detail (photo, appointment, tenure), extend `GET /people/{id}` rather than add a new `/people/{id}/popover` endpoint.

**When to use:** The existing endpoint is public, already called on the argument page load, and the new fields add less than ~300 bytes per person.

**Trade-offs:** Slight over-fetch for callers that don't need the new fields; avoided by making fields optional in the response schema (existing callers ignore unknown fields).

### Pattern 2: Atomic Multi-table Mutation via Single Transaction

**What:** Merge and delete-orphaned operations must use `async with db.begin()`, not sequential `await db.commit()` calls mid-operation.

**When to use:** Any operation touching more than one table where partial application leaves inconsistent state.

**Example structure:**
```python
async def merge_people(db: AsyncSession, source_id: int, target_id: int) -> dict:
    async with db.begin():
        await db.execute(
            update(Utterance).where(Utterance.person_id == source_id)
            .values(person_id=target_id)
            .execution_options(synchronize_session=False)
        )
        # ... remaining UPDATEs ...
        await db.execute(
            delete(Person).where(Person.id == source_id)
            .execution_options(synchronize_session=False)
        )
    # committed on exit; rolled back on any exception
    return await get_person_detail(db, target_id)
```

Every `update()`/`delete()` requires `.execution_options(synchronize_session=False)` — this is the project-wide pattern established in `admin_people.py` and `admin_jobs.py`.

### Pattern 3: Alembic Migration for Schema Changes — Hand-written Only

**What:** All new people columns go into a single migration 0006. No autogenerate. Explicit FK dependency order control.

**Order of operations:**
1. Write migration 0006 (down_revision=0005)
2. Update ORM model (`Person` class in `models.py`)
3. Update Pydantic schemas (`PersonDetail`, `PersonUpdate`, `PersonResponse`)
4. Update service layer (`get_person_detail`, `update_person`, `get_person_by_id`)
5. Update SvelteKit admin form

### Pattern 4: resolved_at Gate via Schema Exclusion

**What:** `ArgumentUpdate` Pydantic schema must not include `resolved_at` as a field. This is mass-assignment protection at the schema boundary.

**Why:** If the field isn't in the schema, it cannot be set regardless of what the client sends. A runtime check is a weaker guarantee and can be accidentally removed.

**Applies to:** Any Pydantic schema used for user-supplied input that should not be able to touch gating fields.

### Pattern 5: Shared Nav via Layout Composition

**What:** Extract nav markup from both layout files into `lib/components/NavHeader.svelte`. Accept `variant: 'public' | 'admin'` prop. Both layouts import and render it.

**Current situation:** Root `+layout.svelte` suppresses its nav on `/admin/*` via a pathname check. Admin `+layout.svelte` has its own nav. Adding new nav items means editing two files.

**Target:** One `NavHeader.svelte` controls all nav rendering. The root layout's `{#if !page.url.pathname.startsWith('/admin')}` guard is removed entirely — the admin layout renders the admin variant; the root layout renders the public variant by default.

---

## API Endpoint Inventory

### New Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/api/admin/arguments/{id}` | Admin cookie | Fetch argument + lead case metadata for the edit form |
| PATCH | `/api/admin/arguments/{id}` | Admin cookie | Update case_name, argued_date (resolved_at excluded from schema) |
| POST | `/api/admin/people/{id}/image` | Admin cookie | Upload image to DO Spaces, update person.photo_url |
| POST | `/api/admin/people/merge` | Admin cookie | Atomic merge: transfer all refs, delete source person |
| DELETE | `/api/admin/people/orphaned` | Admin cookie | Delete people with no utterances, aliases, or appearances |

### Modified Endpoints

| Method | Path | Change |
|--------|------|--------|
| GET | `/people/{id}` | Add `photo_url`, `appointed_by`, `appointing_party`, `tenures` to `PersonResponse` |
| PATCH | `/api/admin/people/{id}` | Accept `first_name`, `last_name`, `middle_name`, `suffix`, `appointed_by`, `appointing_party` in `PersonUpdate` |
| GET | `/api/admin/people` | `PersonListItem.missing` list updated if structured name fields are required |

---

## Database Schema Changes

### Migration 0006: Structured Name + Appointment Fields

**Table:** `people` — all new columns nullable, no defaults, existing rows retain NULL.

```sql
ALTER TABLE people ADD COLUMN first_name    VARCHAR(100);
ALTER TABLE people ADD COLUMN last_name     VARCHAR(100);
ALTER TABLE people ADD COLUMN middle_name   VARCHAR(100);
ALTER TABLE people ADD COLUMN suffix        VARCHAR(20);
ALTER TABLE people ADD COLUMN appointed_by  VARCHAR(200);
ALTER TABLE people ADD COLUMN appointing_party VARCHAR(50);
```

`full_name` remains the display/pipeline field. Structured name fields are supplementary operator data for the SpeakerPopover.

**No additional migration needed:** Image URLs are stored in the existing `photo_url` column (added in migration 0005). DO Spaces key pattern `images/{person_id}.{ext}` is a naming convention, not a schema concern.

---

## Build Order (Dependency-Respecting)

```
Phase A — Foundation (must go first)
  └── Migration 0006 + ORM model update
      └── PersonDetail / PersonUpdate / PersonResponse schema updates
          └── admin_people service update (new fields in read/write)
              └── Admin people edit form (new field inputs)

Phase B — Independent of A, parallelizable after A completes
  ├── Unified nav (NavHeader.svelte extraction)
  ├── Argument metadata editing (new endpoint + new admin page)
  └── People admin improvements
      ├── Image upload (depends on spaces.py helper addition)
      ├── People merge (depends on ORM model from A being final)
      └── People orphan delete (no schema deps)

Phase C — Depends on A + B data being populated
  └── Speaker popover
      ├── SpeakerPopover.svelte component
      ├── PersonResponse extension (photo_url, appointed_by, appointing_party, tenures)
      ├── +page.server.ts argument page: pre-load bench person details
      └── ChatBubble: avatar → button (bench only)
```

**Rationale:**
- Migration 0006 gates everything downstream that touches the new person fields. Build it first.
- Unified nav has no data dependencies; it can be built any time but benefits from being done before new admin pages are added so they automatically inherit the nav.
- Argument metadata editing and people admin improvements are independent of each other; build them in parallel.
- SpeakerPopover depends on `appointed_by`/`appointing_party` being in the database (migration A) AND being exposed via `GET /people/{id}` (schema change). It also depends on the people edit form (phase B) having been used to populate data for meaningful end-to-end testing. Build the component in parallel with B but full testing requires B data.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| DO Spaces | boto3 `upload_fileobj` via `run_in_executor` (existing pattern in `spaces.py`) | Images use same client and credentials as PDFs; add `ExtraArgs={"ContentType": mime_type, "ACL": "public-read"}`; key pattern: `images/{person_id}.{ext}` |
| PostgreSQL | SQLAlchemy async (existing); merge uses `async with db.begin()` | No new connection config; PgBouncer `statement_cache_size=0` constraint already in `connect_args` |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| SvelteKit → FastAPI (admin) | `+page.server.ts` loads + form actions via `FASTAPI_BASE_URL` (server-only env) | Never `PUBLIC_` prefix; all new admin API calls follow this pattern |
| SvelteKit → FastAPI (public, popover) | Server load in `+page.server.ts`; pre-load all bench person details during SSR | No client-side fetch; SpeakerPopover data arrives with the page |
| ChatBubble → SpeakerPopover | Svelte component props; parent page owns the popover open/close state | Popover state lives in `+page.svelte`, not inside ChatBubble, so only one popover is open at a time |
| Admin layout → shared nav | `<NavHeader variant="admin">` imported from `$lib/components` | Public layout uses `<NavHeader variant="public">`; both point at same file |

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Client-side fetch for SpeakerPopover data

**What people do:** Add `fetch('/api/people/{id}')` inside `SpeakerPopover.svelte` on click.

**Why it's wrong:** `FASTAPI_BASE_URL` is `$env/static/private` — not accessible in the browser. A proxy route adds unnecessary plumbing. SSR pre-loading is already the established pattern in this codebase.

**Do this instead:** In `+page.server.ts`, call `GET /people/{id}` for each distinct bench `person_id` in the utterances list. Return as `benchPeople: Record<number, PersonDetail>`. Pass to `ChatBubble` as a prop.

### Anti-Pattern 2: Setting resolved_at via the argument edit form

**What people do:** Include `resolved_at` as an optional field in `ArgumentUpdate` with a comment "admin can override if needed."

**Why it's wrong:** `resolved_at` is the public visibility gate. The pipeline resolve step sets it; the admin metadata edit form must not. Including it in the schema defeats the gate.

**Do this instead:** Never include `resolved_at` in `ArgumentUpdate`. If promoting an argument to public visibility ever needs an explicit trigger, that is a separate, explicitly-named action with its own endpoint and audit log.

### Anti-Pattern 3: Sequential commits inside merge_people

**What people do:** `await db.commit()` after each UPDATE statement to "make progress."

**Why it's wrong:** A failure after the source aliases are transferred but before the source person is deleted leaves orphaned alias rows pointing at a person that may later be deleted, or worse, pointing at the wrong person.

**Do this instead:** `async with db.begin()`: commit happens on clean exit, rollback on any exception. The entire merge is atomic.

### Anti-Pattern 4: Deriving full_name from structured name fields on save

**What people do:** On update, compute `full_name = f"{first_name} {last_name}"` and overwrite the stored `full_name`.

**Why it's wrong:** `full_name` is what the pipeline's resolve step writes from the raw transcript label (e.g., "CHIEF JUSTICE ROBERTS"). That value is what drives speaker attribution display. Overwriting it with a derived formal name breaks the display of existing resolved utterances.

**Do this instead:** `full_name` remains an independently editable field. Structured name fields are additive, not a replacement for `full_name`.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (1 operator, public read-only) | No changes needed; SSR handles load |
| 10k concurrent readers | CDN (Cloudflare) in front of DO App Platform; argument pages are SSR-cacheable |
| 100k+ readers | PostgreSQL read replica; utterance queries are the hot read path; v1.2 feature additions do not affect this path |

Merge and orphan-delete operations are infrequent operator actions — no concurrency risk at any expected scale.

---

## Sources

- Existing codebase: `api/`, `app/src/`, `alembic/versions/` (direct inspection, 2026-06-18)
- `.planning/PROJECT.md` — key decisions log, architecture rules, confirmed stack

---

*Architecture research for: SCOTUS Chat v1.2 feature integration*
*Researched: 2026-06-18*
