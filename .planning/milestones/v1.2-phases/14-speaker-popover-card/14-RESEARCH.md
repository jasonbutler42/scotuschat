# Phase 14: Speaker Popover Card — Research

**Researched:** 2026-06-25
**Domain:** SvelteKit / Svelte 5 UI component, bits-ui Popover primitives, FastAPI Pydantic v2 schema design, SQLAlchemy async join queries
**Confidence:** MEDIUM (all critical library facts verified against bits-ui official docs; FastAPI/SQLAlchemy patterns verified against existing codebase)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** New public endpoint `GET /api/arguments/{id}/speakers` — single call from `+page.server.ts`, response pre-assembled with full popover data. Route lives in `api/routers/arguments.py` (or a new `speakers.py` — Claude's discretion).
- **D-02:** Each entry contains: `person_id`, `full_name`, `role_name`, `photo_url` (raw DB value), `tenure` array of `{seat, start_date, end_date}`, `appointing_president`.
- **D-03:** `photo_url` reconstruction in `+page.server.ts`: if `startsWith('/')` prepend `FASTAPI_BASE_URL`; else use as-is. Reconstructed as `photo_url_full`. `FASTAPI_BASE_URL` never reaches the browser.
- **D-04:** New Pydantic response model `SpeakerPopoverResponse` in `api/schemas/` — `PersonResponse` is NOT extended.
- **D-05:** Both trigger locations: ChatBubble utterance avatars AND header roster entries.
- **D-06:** Trigger is a `<button type="button" aria-label="View {name} details">`. `aria-hidden="true"` removed from trigger avatar circle.
- **D-07:** Header roster trigger wraps avatar circle; whether name text is also in trigger is Claude's discretion.
- **D-08:** All `court_tenure` rows, sorted by `start_date ASC`; `end_date IS NULL` renders as "present".
- **D-09:** `appointing_president` single field from `people` table; "Appointed by [name]"; multi-tenure attribution deferred.
- **D-10:** Responsive layout: horizontal (flex-row) ≥768px, vertical (flex-column) <768px. Breakpoint 768px matches project-wide mobile breakpoint.
- **D-11:** One `SpeakerPopover.svelte` component for both bench and advocate; bench-only fields conditional on `isBench`.
- **D-12:** Install `bits-ui@^2.18.1` — add to `app/package.json` as dependency.
- **D-13:** Use `Popover.Root`, `Popover.Trigger`, `Popover.Content` from bits-ui.

### Claude's Discretion

- Whether new route lives in `arguments.py` or a new `speakers.py` router
- Whether header roster trigger wraps avatar-only or avatar+name together
- Exact `SpeakerPopover` card dimensions and padding (must use admin dark theme tokens)
- Photo/initials circle size in the popover card (suggested 56–64px)
- Whether `Popover.Content` has a close button
- Popover arrow/caret or no caret

### Deferred Ideas (OUT OF SCOPE)

- Tenure-linked appointment attribution (multiple appointing presidents per person)
- Advocate firm/organization in popover (ADV-01)
- Photo fallback shimmer/skeleton animation
- Party affiliation in public popover — hard out-of-scope (apolitical constraint + REQUIREMENTS.md Out of Scope)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PUB-01 | Visitor can click any speaker's avatar to open a popover card showing name and role | bits-ui Popover.Root/Trigger/Content; shared-root pattern with onAvatarClick callback; roster avatar button additions |
| PUB-02 | Bench speaker popovers additionally show tenure dates and appointing president | CourtTenure SQLAlchemy join in speakers service; conditional isBench rendering in SpeakerPopover.svelte |
| PUB-03 | Speaker popover displays profile photo when available, or styled initials as a fallback | photo_url_full reconstruction in +page.server.ts (D-03 pattern); img onerror fallback to initials circle |
| PUB-04 | Speaker popover is keyboard accessible and dismissible with Escape | bits-ui handles Escape natively (trapFocus default true, escapeKeydownBehavior default close); focus returns to trigger on close |
</phase_requirements>

---

## Summary

Phase 14 adds a speaker identity popover to the public argument view. Two surfaces gain clickable avatar buttons: the ChatBubble utterance header (existing 32px avatar `div` converted to `<button>`) and the header roster entries (new 32px avatar circle added to each row). Clicking either trigger opens a shared `Popover.Root` at the argument page level that displays a `SpeakerPopover.svelte` card — name, role, photo (or initials), and for bench speakers, tenure rows and appointing president.

The implementation spans three tiers. The API tier adds one new FastAPI endpoint (`GET /arguments/{id}/speakers`) and one new Pydantic schema file. The server tier adds a speakers fetch call and photo URL reconstruction to `+page.server.ts`. The UI tier introduces bits-ui (first use in this codebase), a new `SpeakerPopover.svelte` component, and modifications to `ChatBubble.svelte` and `+page.svelte`.

The critical architectural decision is the shared-root pattern: one `Popover.Root` lives at the argument page level rather than one inside each `ChatBubble`. This avoids creating dozens of Popover instances. Because ChatBubble triggers cannot be inside that page-level Root's tree, the connection is made through a callback prop: ChatBubble calls `onAvatarClick(personId)`, the page sets `currentSpeaker` via `$state`, and `bind:open` on the Root controls visibility.

**Primary recommendation:** Implement the shared-root callback pattern; keep the new `SpeakerPopoverResponse` schema and service function as a clean parallel to the existing `get_argument_with_utterances` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Speaker popover data assembly | API / Backend (FastAPI service) | — | Joins three tables (people, roles, court_tenures); belongs in the service layer alongside existing argument queries |
| photo_url reconstruction | Frontend Server (SvelteKit +page.server.ts) | — | FASTAPI_BASE_URL is server-only env var; established pattern from admin people page |
| Popover open/close state | Browser / Client (Svelte 5 $state) | — | Display-only state; no server round-trip needed; bits-ui manages focus/keyboard natively |
| Avatar button rendering (ChatBubble) | Browser / Client (Svelte component) | — | Existing component modification; purely presentational |
| Roster avatar addition | Browser / Client (+page.svelte) | — | Roster is already derived client-side from utterances; avatar additions are presentation-only |
| Tenure date formatting | Browser / Client (SpeakerPopover.svelte) | — | Year slicing is trivial; no i18n complexity; follows existing formatDate pattern in +page.svelte |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| bits-ui | ^2.18.1 | Headless Popover primitives (Root, Trigger, Content) for Svelte 5 | [VERIFIED: npm registry] — only Svelte 5-native headless popover after @skeletonlabs/floating-ui-svelte archived Oct 2025; pre-selected in prior research; confirmed current at 2.18.1 (2026-05-03) |
| SvelteKit 2.x / Svelte 5 | ^2.21.0 / ^5.30.0 | Frontend framework | Project stack — already installed |
| FastAPI 0.115+ | 0.115+ | New endpoint | Project stack — already installed |
| SQLAlchemy 2.0 async | 2.0 | Service query (people + tenures join) | Project stack — already installed |
| Pydantic v2 | v2 | New `SpeakerPopoverResponse` schema | Project stack — already installed |

### Supporting

No new supporting packages. All supporting utilities (Svelte 5 runes, inline styles, existing formatDate) are already in the project.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| bits-ui Popover | @floating-ui/dom directly | Requires manual focus trap and keyboard handling; more code; bits-ui wraps floating-ui internally |
| bits-ui Popover | Custom CSS/JS popover | Custom focus trap is a known accessibility pitfall; bits-ui handles it correctly |
| Shared Root at page level | Per-bubble Popover.Root | Per-bubble creates O(n) Popover instances for n utterances; shared root is O(1) |

**Installation:**
```bash
cd app && npm install bits-ui@^2.18.1
```

**Version verification:**
```
npm view bits-ui version  → 2.18.1 (published 2026-05-03)
```

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| bits-ui | npm | ~2 yrs | 777,547/wk | github.com/huntabyte/bits-ui | OK | Approved |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious SUS:** none

No postinstall script detected on bits-ui.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser click on avatar button
        │
        ▼
ChatBubble.svelte  ──onAvatarClick(personId)──►  +page.svelte
        │                                               │
(roster avatar button)                         $state currentSpeaker
        │                                               │
        └──────────────────────────────────────►  bind:open on Popover.Root
                                                        │
                                               Popover.Content renders
                                               SpeakerPopover.svelte
                                               (receives currentSpeaker)
                                                        │
                                            ┌───────────┴───────────┐
                                     photo_url_full              isBench
                                     from speakersMap           from speakersMap
                                            │                        │
                                     <img> or initials        tenure rows +
                                     circle fallback          appointing president

+page.server.ts (load)
  │
  ├─ fetch /arguments/{id}/utterances  ──► existing
  └─ fetch /arguments/{id}/speakers   ──► new
          │
          ▼
  FastAPI GET /arguments/{id}/speakers
          │
          ▼
  speakers_service.get_argument_speakers(db, argument_id)
          │
          ├─ SELECT DISTINCT person_id FROM utterances WHERE argument_id = ?
          ├─ JOIN people ON utterance.person_id = people.id
          ├─ JOIN roles ON people.role_id = roles.id (LEFT)
          └─ SELECT * FROM court_tenures WHERE person_id IN (...)
          │
          ▼
  SpeakerPopoverResponse[] (JSON)
          │
          ▼
  +page.server.ts reconstructs photo_url_full
  returns speakersMap: Record<number, SpeakerDetail>
```

### Recommended Project Structure

```
api/
├── routers/arguments.py          # add GET /arguments/{id}/speakers route
├── schemas/speakers.py           # NEW: SpeakerPopoverResponse, TenureEntry
├── services/speakers.py          # NEW: get_argument_speakers()
app/src/
├── lib/components/
│   ├── ChatBubble.svelte         # MODIFY: avatar div→button, add onAvatarClick prop
│   └── SpeakerPopover.svelte     # NEW: popover card content
└── routes/cases/[slug]/arguments/[id]/
    ├── +page.server.ts           # MODIFY: add speakers fetch + photo_url_full
    └── +page.svelte              # MODIFY: shared Popover.Root, roster avatars
```

### Pattern 1: bits-ui Shared Popover Root

**What:** One `Popover.Root` at the page level controls a single popover instance. External triggers (in ChatBubble child components) cannot use `Popover.Trigger` directly because they live outside the Root's component tree. Instead, `bind:open` on the Root is driven by a `$state` variable that external callbacks write to.

**When to use:** When many elements on a page can trigger the same popover showing different data — avoids creating O(n) Popover instances.

**Example:**
```svelte
<!-- +page.svelte (simplified) -->
<script lang="ts">
  import { Popover } from 'bits-ui';
  import SpeakerPopover from '$lib/components/SpeakerPopover.svelte';
  import ChatBubble from '$lib/components/ChatBubble.svelte';

  // Source: bits-ui.com/docs/components/popover — controlled state
  let isPopoverOpen = $state(false);
  let currentSpeaker = $state<SpeakerDetail | null>(null);

  // Build O(1) lookup map from server-loaded speakers array
  const speakersMap = $derived(
    new Map(data.speakers.map((s: SpeakerDetail) => [s.person_id, s]))
  );

  function onAvatarClick(personId: number) {
    const speaker = speakersMap.get(personId) ?? null;
    currentSpeaker = speaker;
    isPopoverOpen = speaker !== null;
  }
</script>

<!-- Single Root at page level — no Popover.Trigger here -->
<Popover.Root bind:open={isPopoverOpen} onOpenChange={(open) => { if (!open) currentSpeaker = null; }}>
  <Popover.Content>
    {#if currentSpeaker}
      <SpeakerPopover speaker={currentSpeaker} />
    {/if}
  </Popover.Content>
</Popover.Root>

<!-- ChatBubble uses callback, not Popover.Trigger -->
{#each data.utterances as utterance}
  <ChatBubble {utterance} {onAvatarClick} />
{/each}
```

**Source:** [CITED: bits-ui.com/docs/components/popover] — controlled state via bind:open

### Pattern 2: ChatBubble Avatar Button

**What:** Convert the existing avatar `div` to a `<button>` element while preserving all existing visual styles.

**When to use:** Any time a decorative element must become interactive (keyboard + pointer accessible).

**Example:**
```svelte
<!-- ChatBubble.svelte — avatar button -->
<script lang="ts">
  let { utterance, onAvatarClick } = $props<{
    utterance: UtteranceRow;
    onAvatarClick?: (personId: number) => void;
  }>();
</script>

<!-- BEFORE: <div aria-hidden="true" style="..."> -->
<!-- AFTER: -->
<button
  type="button"
  aria-label="View {displayName} details"
  onclick={() => utterance.person_id && onAvatarClick?.(utterance.person_id)}
  style="background: none; border: none; padding: 6px; cursor: pointer; border-radius: 50%;"
>
  <div style="width: 32px; height: 32px; border-radius: 50%; background-color: {avatarBg}; ...">
    {initials}
  </div>
</button>
```

Note: 6px padding on the button brings the touch target to 32+12=44px, meeting WCAG 2.5.5. [ASSUMED — WCAG touch target guideline; 44px figure widely cited]

### Pattern 3: FastAPI Service with Async Subquery for Tenures

**What:** The speakers endpoint requires two queries: one for people joined to utterances, and one for court_tenures. Running the tenure fetch as a separate `WHERE person_id IN (...)` subquery after collecting person IDs is simpler and more readable than a multi-level join that produces one row per tenure per utterance.

**When to use:** When one-to-many relationships (person → tenures) are needed alongside many-to-one joins (utterance → person).

**Example:**
```python
# api/services/speakers.py
from sqlalchemy import select, distinct
from api.models.models import Utterance, Person, Role, CourtTenure

async def get_argument_speakers(db: AsyncSession, argument_id: int) -> list[dict]:
    # Source: existing get_argument_with_utterances() pattern in services/arguments.py
    # Step 1: Distinct person_ids for this argument
    person_id_result = await db.execute(
        select(distinct(Utterance.person_id))
        .where(Utterance.argument_id == argument_id, Utterance.person_id.isnot(None))
    )
    person_ids = [row[0] for row in person_id_result.all()]
    if not person_ids:
        return []

    # Step 2: People + roles
    people_result = await db.execute(
        select(Person, Role.name.label("role_name"))
        .outerjoin(Role, Person.role_id == Role.id)
        .where(Person.id.in_(person_ids))
    )
    people_rows = people_result.all()

    # Step 3: Tenures for all persons in one query
    tenures_result = await db.execute(
        select(CourtTenure)
        .where(CourtTenure.person_id.in_(person_ids))
        .order_by(CourtTenure.person_id, CourtTenure.start_date.asc())
    )
    tenure_rows = tenures_result.scalars().all()

    # Step 4: Group tenures by person_id
    from collections import defaultdict
    tenures_by_person: dict[int, list] = defaultdict(list)
    for t in tenure_rows:
        tenures_by_person[t.person_id].append(t)

    # Step 5: Assemble response dicts
    result = []
    for person, role_name in people_rows:
        result.append({
            "person_id": person.id,
            "full_name": person.full_name,
            "role_name": role_name,
            "photo_url": person.photo_url,
            "appointing_president": person.appointing_president,
            "tenure": [
                {
                    "seat": t.seat,
                    "start_date": str(t.start_date) if t.start_date else None,
                    "end_date": str(t.end_date) if t.end_date else None,
                }
                for t in tenures_by_person[person.id]
            ],
        })
    return result
```

### Pattern 4: photo_url_full Reconstruction (Established)

**What:** Existing pattern from Phase 12 admin people page. Replicate exactly in the argument page server load.

**Example:**
```typescript
// +page.server.ts — add after speakers fetch
for (const speaker of speakers) {
  if (speaker.photo_url?.startsWith('/')) {
    speaker.photo_url_full = FASTAPI_BASE_URL + speaker.photo_url;
  } else {
    speaker.photo_url_full = speaker.photo_url ?? null;
  }
}
```

Source: [CITED: app/src/routes/admin/people/[id]/+page.server.ts lines 74–79]

### Pattern 5: Pydantic v2 Nested Schema

**What:** A `TenureEntry` model is nested as a list inside `SpeakerPopoverEntry`. Pydantic v2 handles nested model serialization automatically.

**Example:**
```python
# api/schemas/speakers.py
from typing import Optional
from pydantic import BaseModel

class TenureEntry(BaseModel):
    seat: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None  # None = currently active

class SpeakerPopoverEntry(BaseModel):
    person_id: int
    full_name: str
    role_name: Optional[str] = None
    photo_url: Optional[str] = None   # raw DB value; reconstruction happens in +page.server.ts
    appointing_president: Optional[str] = None
    tenure: list[TenureEntry] = []

    model_config = {"from_attributes": True}
```

### Anti-Patterns to Avoid

- **Popover.Trigger inside ChatBubble with nested Root:** ChatBubble is rendered in a loop outside the Root's component tree. Attempting to use `Popover.Trigger` in ChatBubble without a parent `Popover.Root` context will throw a runtime error. Use the callback pattern instead.
- **Per-bubble Popover.Root:** Creates dozens of Root instances and floating-ui position calculations on the DOM. Use one shared Root.
- **PUBLIC_FASTAPI_BASE_URL env var:** The project has an established and enforced rule: `FASTAPI_BASE_URL` is `$env/static/private` — never `PUBLIC_`. Reconstruct the URL server-side.
- **Calling `Base.metadata.create_all`:** CLAUDE.md constraint — Alembic is the sole DDL authority. No schema changes are needed for Phase 14 (all required columns exist from Phase 9 migration 0006).
- **Returning `appointing_president_party` from the speakers endpoint:** This field is admin-only (REQUIREMENTS.md Out of Scope, apolitical framing constraint). The new `SpeakerPopoverEntry` schema must not include this field.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Popover positioning | Custom top/left absolute positioning | bits-ui Popover.Content (wraps @floating-ui/dom) | Viewport collision detection, scroll awareness, and portal rendering are non-trivial; floating-ui handles all edge cases |
| Focus trap in popover | `document.addEventListener('keydown', ...)` | bits-ui Popover.Content (trapFocus default true) | Focus trap has many edge cases (disabled elements, iframes, dynamically added elements); bits-ui implements ARIA APG pattern correctly |
| Escape key dismissal | Custom keydown listener | bits-ui native (escapeKeydownBehavior default 'close') | Already satisfies PUB-04; no code needed |
| Focus return on close | Manually tracking last focused element | bits-ui native (onCloseAutoFocus default) | bits-ui returns focus to the trigger that opened the popover — PUB-04 satisfied automatically |
| Accessible popover role | Custom aria-* attributes | bits-ui Popover.Content (assigns role="dialog") | APG-compliant dialog pattern; screen reader announcements handled |

**Key insight:** bits-ui's entire value proposition for this phase is replacing roughly 200 lines of custom keyboard/focus/positioning code with three primitive components.

---

## Common Pitfalls

### Pitfall 1: Popover.Trigger Context Error

**What goes wrong:** Using `Popover.Trigger` inside `ChatBubble.svelte` without a `Popover.Root` ancestor causes a bits-ui context error at runtime: "Popover.Trigger must be used within a Popover.Root".

**Why it happens:** bits-ui primitives communicate via Svelte 5 context (`setContext`/`getContext`). The context is set by `Popover.Root`; `Trigger` reads it. If `Trigger` renders outside the Root tree, the context is absent.

**How to avoid:** Use the callback pattern — ChatBubble calls `onAvatarClick(personId)` instead of using `Popover.Trigger`. The Root lives at the page level.

**Warning signs:** "getContext called outside of component initialization" or bits-ui-specific context errors in browser console.

### Pitfall 2: speakersMap built from plain array — must convert to Map

**What goes wrong:** `data.speakers` arrives from `+page.server.ts` as a plain serializable array (SvelteKit serializes `Map` objects differently — they may not round-trip as Map). The page must reconstruct the `Map<number, SpeakerDetail>` client-side.

**Why it happens:** SvelteKit's `load` return value is serialized for SSR hydration. `Map` objects serialize as `{}` in JSON. If the server returns a `Map`, the client receives an empty object.

**How to avoid:** Return `speakers` as a plain array from `+page.server.ts`. Build `speakersMap` via `$derived(new Map(data.speakers.map(s => [s.person_id, s])))` in `+page.svelte`.

**Warning signs:** `speakersMap.get(personId)` always returns `undefined`; popover never opens.

### Pitfall 3: Utterances in +page.svelte don't carry person_id

**What goes wrong:** ChatBubble needs `utterance.person_id` to call `onAvatarClick(personId)`. The existing utterance schema (`ArgumentUtterancesResponse`) does include `person_id` on each utterance row (it's a column on the `utterances` table and included in the dict comprehension in `services/arguments.py` lines 117–121). However, the TypeScript interface in `+page.svelte` may not have `person_id` typed.

**Why it happens:** The TypeScript type for `data.utterances` is inferred from the server response and may not explicitly include `person_id` if the `UtteranceItem` interface was manually defined without it.

**How to avoid:** Verify that `person_id` is present on utterance rows returned by the existing API (it is — confirmed by inspecting `services/arguments.py`). Ensure the TS type for utterance items includes `person_id: number | null`.

**Warning signs:** TypeScript errors on `utterance.person_id` in ChatBubble.

### Pitfall 4: Roster speakers use display name, not person_id

**What goes wrong:** The existing `roster` derived value in `+page.svelte` groups speakers by `speaker_name` (a display string), not by `person_id`. The roster's speaker objects are `{ name: string; role: string | null }` — no `person_id`.

**Why it happens:** The roster was built for display only (Phase 1 foundation) and never needed numeric IDs.

**How to avoid:** The roster derivation must be extended to also carry `person_id`. Since roster is built from `data.utterances`, each utterance has `person_id`. The roster derivation should capture the first `person_id` seen for each `name` key.

**Warning signs:** Roster trigger buttons have no `person_id` to pass to `onAvatarClick`.

### Pitfall 5: null person_id in utterances

**What goes wrong:** `utterance.person_id` is `null` for unresolved utterances (populated only after the Resolve pipeline step runs). Calling `onAvatarClick(null)` would pass null to the speakers map lookup.

**Why it happens:** The DB column allows null until resolve runs.

**How to avoid:** Guard the button: only render the avatar as a clickable button when `utterance.person_id != null && speakersMap.has(utterance.person_id)`. When person_id is null, render the avatar as a non-interactive `div` (or keep it as a button with a disabled state and no-op handler).

**Warning signs:** Clicking an unresolved speaker's avatar opens an empty popover or throws a JS error.

### Pitfall 6: Tenure date formatting edge cases

**What goes wrong:** `start_date` comes from the DB as a Python `date` object serialized to a string like `"2005-09-29"`. Slicing `[0:4]` for year extraction is simple and safe. However, `null` dates (for unknown start dates) must be handled.

**Why it happens:** The `court_tenures` table schema shows `start_date` and `end_date` as nullable columns.

**How to avoid:** In `SpeakerPopover.svelte`, guard year extraction: `tenure.start_date ? tenure.start_date.slice(0, 4) : '?'`. Use `tenure.end_date ? tenure.end_date.slice(0, 4) : 'present'` for end dates.

**Warning signs:** "undefined" appearing in tenure rows.

---

## Code Examples

### bits-ui Popover — Controlled Open State

```svelte
<!-- Source: bits-ui.com/docs/components/popover — controlled state example -->
<script lang="ts">
  import { Popover } from 'bits-ui';
  let isOpen = $state(false);
</script>

<Popover.Root bind:open={isOpen} onOpenChange={(open) => { isOpen = open; }}>
  <!-- Trigger lives here OR open is driven externally via bind:open -->
  <Popover.Content>
    <p>Content</p>
  </Popover.Content>
</Popover.Root>
```

### bits-ui Popover — Content Props

```svelte
<!-- Source: bits-ui.com/docs/components/popover -->
<Popover.Content
  trapFocus={true}
  sideOffset={8}
  escapeKeydownBehavior="close"
  interactOutsideBehavior="close"
>
  <!-- card content -->
</Popover.Content>
```

### SpeakerPopover — Tenure Row Rendering

```svelte
<!-- SpeakerPopover.svelte — bench-only tenure block -->
{#if isBench && speaker.tenure.length > 0}
  <div style="margin-top: 8px; border-top: 1px solid #334155; padding-top: 8px;">
    {#each speaker.tenure as t}
      <p style="font-size: 13px; color: #94a3b8; margin: 0 0 4px 0;">
        {t.seat ?? 'Justice'} — {t.start_date ? t.start_date.slice(0,4) : '?'}–{t.end_date ? t.end_date.slice(0,4) : 'present'}
      </p>
    {/each}
    {#if speaker.appointing_president}
      <p style="font-size: 13px; color: #94a3b8; margin: 4px 0 0 0;">
        Appointed by {speaker.appointing_president}
      </p>
    {/if}
  </div>
{/if}
```

### photo_url_full Reconstruction — +page.server.ts

```typescript
// Source: established pattern from app/src/routes/admin/people/[id]/+page.server.ts lines 74–79
const speakersRes = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/speakers`);
const speakersRaw: SpeakerEntry[] = speakersRes.ok ? await speakersRes.json() : [];

const speakers = speakersRaw.map((s) => ({
  ...s,
  photo_url_full: s.photo_url?.startsWith('/')
    ? FASTAPI_BASE_URL + s.photo_url
    : (s.photo_url ?? null),
}));
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| @skeletonlabs/floating-ui-svelte | bits-ui ^2.18.1 | Oct 2025 (skeletonlabs archived) | bits-ui is now the standard headless Svelte 5 popover; no legacy stores, full Runes support |
| Svelte 4 `export let` props | Svelte 5 `$props()` | Svelte 5 GA | All new components use `$props()` — no exceptions |
| Svelte 4 reactive blocks `$:` | Svelte 5 `$derived()` / `$state()` | Svelte 5 GA | All new components use Runes exclusively |

**Deprecated/outdated:**
- `@skeletonlabs/floating-ui-svelte`: archived Oct 2025 — do NOT install this package
- `export let` props in Svelte components: replaced by `$props()` in Svelte 5 — project enforces Runes exclusively

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | bits-ui Popover.Trigger requires a Popover.Root ancestor in the component tree (context-based) | Architecture Patterns, Pitfall 1 | If bits-ui supported a portal-based trigger-outside-root pattern, the callback approach would be unnecessary — but the shared-root pattern is safe regardless |
| A2 | WCAG 2.5.5 recommends 44px minimum touch target | Pattern 2 | Minor: if not required by project, the 6px padding is still a reasonable UX improvement |
| A3 | Svelte 5 / SvelteKit serializes Map objects incorrectly through load return | Pitfall 2 | If SvelteKit v2 added Map serialization, could return Map from server. Defensive conversion in $derived is harmless regardless |

---

## Open Questions

1. **Router location: `arguments.py` vs. new `speakers.py`**
   - What we know: CONTEXT.md D-01 says "Claude's discretion"
   - What's unclear: Project has no speakers router yet; arguments router is small (one endpoint)
   - Recommendation: Add the new route to `api/routers/arguments.py` — it is argument-scoped data; a separate router adds file without meaningful separation at this project scale. Keep the service logic in a new `api/services/speakers.py` for clean separation.

2. **Whether to use Popover.Portal**
   - What we know: bits-ui docs show `Popover.Portal` wrapping `Popover.Content` to teleport content outside the current DOM position
   - What's unclear: Without Portal, the content renders in-place, which may clip inside the scrollable chat column
   - Recommendation: Use `Popover.Portal` to render the popover content at document body level, avoiding overflow/clip issues from the scrollable chat column container.

3. **Roster speaker person_id availability**
   - What we know: The `roster` derived value does not currently carry `person_id` (only `name` and `role`)
   - What's unclear: Whether to re-derive roster from `data.speakers` map (guaranteed person_id) or extend the existing utterance-based derivation
   - Recommendation: Extend the existing `$derived.by()` roster block to also capture the first `person_id` seen per speaker name. This avoids a second derivation and keeps the roster logic in one place.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| bits-ui | Popover UI primitive | Must install | 2.18.1 (latest) | None — install required |
| Node.js / npm | bits-ui install | ✓ | (project dev environment) | — |
| PostgreSQL | Speakers endpoint (court_tenures) | ✓ | 16 (project stack) | — |

**Missing dependencies with no fallback:**
- bits-ui not yet in `app/package.json` — `npm install bits-ui@^2.18.1` is a Wave 0 task

**Missing dependencies with fallback:**
- none

---

## Security Domain

> `security_enforcement` not explicitly set to false in config — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Read-only public page; no auth |
| V3 Session Management | No | No session state changed |
| V4 Access Control | Yes (partial) | `appointing_president_party` must never appear in `SpeakerPopoverEntry` schema; apolitical constraint enforced by schema design |
| V5 Input Validation | Yes | `argument_id` path param is int-typed in FastAPI — non-integer values produce 422 without reaching service (existing T-05-01 mitigation pattern) |
| V6 Cryptography | No | No new secrets or encryption |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Political data exposure via speakers endpoint | Information Disclosure | `appointing_president_party` excluded from `SpeakerPopoverEntry` schema — never serialized in response |
| SQL injection via argument_id | Tampering | FastAPI path parameter type coercion (int) prevents string injection; existing T-05-01 pattern |
| FASTAPI_BASE_URL leaking to client | Information Disclosure | Server-only env var ($env/static/private); photo_url_full reconstructed server-side; established D-03 pattern |
| XSS via `full_name` or `appointing_president` | Tampering | Svelte auto-escapes template interpolations; no `{@html}` usage needed |

---

## Sources

### Primary (MEDIUM confidence)
- [CITED: bits-ui.com/docs/components/popover] — Popover.Root bind:open, Popover.Content trapFocus / escapeKeydownBehavior, focus return behavior, Portal usage
- [CITED: npm registry — bits-ui@2.18.1] — version 2.18.1 confirmed current, published 2026-05-03, 777K weekly downloads

### Secondary (MEDIUM confidence)
- [CITED: app/src/routes/admin/people/[id]/+page.server.ts] — photo_url_full reconstruction pattern (lines 74–79)
- [CITED: app/src/lib/components/ChatBubble.svelte] — existing avatar styles, initials logic, isBench pattern
- [CITED: app/src/routes/cases/[slug]/arguments/[id]/+page.svelte] — roster $derived.by() shape, existing formatDate pattern
- [CITED: api/services/arguments.py] — get_argument_with_utterances() as structural template for new service
- [CITED: api/models/models.py] — Person, CourtTenure, Role column definitions confirmed
- [CITED: api/schemas/people.py] — PersonResponse shape confirmed; new schema must not extend it (D-04)

### Tertiary (LOW confidence — ASSUMED)
- WCAG 2.5.5 44px touch target recommendation (A2)
- SvelteKit Map serialization behavior (A3) — defensive pattern used regardless

---

## Metadata

**Confidence breakdown:**
- Standard stack (bits-ui version, API): MEDIUM — confirmed via npm registry and official docs
- Architecture (shared root pattern, callback approach): MEDIUM — verified against bits-ui docs; existing codebase patterns matched
- Pitfalls (person_id on utterances, roster extension, Map serialization): MEDIUM — verified against actual codebase files; Map serialization is ASSUMED but defensive

**Research date:** 2026-06-25
**Valid until:** 2026-07-25 (bits-ui stable; project patterns stable)
