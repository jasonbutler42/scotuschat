# Phase 3: Full UI - Research

**Researched:** 2026-06-12
**Domain:** SvelteKit 2 / Svelte 5 Runes UI, FastAPI endpoint, SQLAlchemy async queries
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: Sticky sidebar layout — nav rail (~180px) left, chat column right. Rail anchors to the viewport.
- D-02: Rail shows section labels with scroll-spy active state; clicking smooth-scrolls to that section.
- D-03: Mobile: hide sidebar below ~768px breakpoint; chat spans full width. No mobile section jumping in Phase 3.
- D-04: Section data derived client-side from `section_hint` on utterances — no new API endpoint.
- D-05: Bench LEFT, advocate RIGHT — reverses Phase 1 (`ChatBubble.svelte` currently has bench at flex-end).
- D-06: Avatar circle in every chat bubble (per-bubble placement, not in argument header).
- D-07: 32px initials circle to the left of the speaker name inside `ChatBubble.svelte`.
- D-08: Bench avatar bg = `#94a3b8`, advocate avatar bg = `#93c5fd`; initials text = `#0f1117`.
- D-10: Case list shows: case name + docket number + argued date.
- D-11: Speaker roster two-column: Bench left, Advocates right. Derived client-side.
- D-12: Roster derived client-side from utterances array (deduplicated unique speakers); no new API endpoint.

### Claude's Discretion

- D-09: Case list navigation model — direct-to-argument vs. intermediate `/cases/[slug]` page. Must handle multi-argument cases (Obergefell has Q1 and Q2 arguments).
- Exact pixel sizing and spacing for the two-column roster within the header bar.
- Scroll-spy implementation approach (IntersectionObserver vs. scroll event listener).
- CSS breakpoint value for mobile sidebar hide (768px suggested; planner may adjust).
- `GET /cases` response shape — what fields to include beyond case name, docket, argued date.

### Deferred Ideas (OUT OF SCOPE)

- Obergefell Q2 session — pipeline supports it; not part of Phase 3.
- `photo_url` avatars — enrichment pipeline (ENRICH-01) deferred to v2. Phase 3 avatars are initials-only.
- Mobile section nav (horizontal pill row) — Phase 4 candidate.
- Case list filtering by term year — DISC-02; deferred.
- Open Graph metadata — DISC-01; deferred.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| API-02 | `GET /cases` — returns list of available cases with basic metadata (name, docket number, term year, argued date) | FastAPI router/service/schema pattern established in `api/routers/people.py`; `Case` ORM model has all needed fields; service query joins cases → case_arguments → arguments |
| UI-04 | Argument header shows case name, docket number, date argued, and the full speaker roster | Roster derived from existing `utterances` array client-side; no API change needed; two-column layout per D-11 |
| UI-05 | Each speaker has an avatar; falls back to styled initials when no `photo_url` available | 32px circle per D-07/D-08; initials from `speaker_name`; no photo_url in Phase 3 — pure initials |
| UI-06 | Arguments at stable shareable URLs that render correctly on page refresh (SSR) | Route `/cases/[slug]/arguments/[id]` already exists; `+page.server.ts` SSR load already works; need to verify slugs are propagated |
| UI-07 | Case list page lets user browse and navigate to any loaded case's argument | New `/cases` route with `+page.server.ts` + `+page.svelte`; requires API-02 |
| UI-08 | Argument section navigation rail shows detected sections and allows jumping between them | IntersectionObserver scroll-spy in Svelte 5 `$effect`; browser guard required; section anchors from section_hint utterances |
</phase_requirements>

---

## Summary

Phase 3 is a pure UI + one API endpoint phase. No schema migrations, no pipeline changes. The work divides into three layers: (1) a new `GET /cases` FastAPI endpoint following the established router/service/schema pattern, (2) a SvelteKit case list page at `/cases`, and (3) changes to the existing argument view — adding a two-column sidebar/chat layout, a speaker roster in the header, per-bubble avatar circles, and a scroll-spy section rail.

The existing codebase provides strong patterns to follow. The argument view (`+page.svelte`) already handles SSR correctly via `+page.server.ts`. `ChatBubble.svelte` uses Svelte 5 Runes (`$props()`) and will receive a new avatar circle. The FastAPI 3-layer pattern (router → service → schema) is established in both `arguments.py` and `people.py`.

The main technical risk is the scroll-spy implementation in Svelte 5, where `$effect` replaces `onMount` for browser API setup and must guard against SSR execution. The second risk is the D-09 navigation model: Obergefell has two arguments (Q1 id=3, Q2 not loaded yet). The recommended model is an intermediate `/cases/[slug]` page that lists arguments for the case — this handles multi-argument cases gracefully and is a 3-file addition (server load, svelte page, no API change needed since argument metadata already exists in the utterances response).

**Primary recommendation:** Build in this order: (1) `GET /cases` API endpoint, (2) `/cases` list page with SSR load, (3) intermediate `/cases/[slug]` page (navigation model for multi-argument cases), (4) two-column argument view restructure with sidebar and section rail, (5) speaker roster in header, (6) avatar circles in ChatBubble, (7) flip bench/advocate alignment (D-05), (8) replace hard-coded nav link in `+layout.svelte`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `GET /cases` list | API / Backend | — | Read-only query of DB; follows established pattern; no business logic in frontend |
| Case list page render | Frontend Server (SSR) | Browser | `+page.server.ts` fetches from FastAPI; SvelteKit serializes to HTML; no client-only rendering needed |
| Argument header + roster | Browser (client-side) | — | Roster derived from utterances already in page data via `$derived`; no new fetch |
| Section rail scroll-spy | Browser (client-side) | — | IntersectionObserver is a browser API; SSR phase renders static rail; client activates scroll-spy |
| Avatar initials | Browser (client-side) | — | Pure CSS/computed value from speaker_name; no network call |
| Chat bubble alignment flip | Browser (client-side) | — | Style-only change in `ChatBubble.svelte` |
| Shareable URL SSR render | Frontend Server (SSR) | — | Route already exists; `+page.server.ts` loads from FASTAPI_BASE_URL; needs verification only |

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version in package.json | Purpose | Why Standard |
|---------|------------------------|---------|--------------|
| `@sveltejs/kit` | ^2.21.0 | SSR routing, load functions, error handling | Project stack decision (locked) |
| `svelte` | ^5.30.0 | Runes reactive UI | Project stack decision (locked) |
| `fastapi` | 0.115+ | HTTP router, dependency injection | Project stack decision (locked) |
| `sqlalchemy` | 2.0 async | ORM queries | Project stack decision (locked) |
| `pydantic` | v2 | Response schemas | Project stack decision (locked) |

No new npm or pip packages are required for Phase 3. The IntersectionObserver is a native browser API (no library needed). CSS Grid/Flexbox handles the two-column layout.

### Package Legitimacy Audit

No new packages to install in Phase 3. Audit skipped — existing packages were verified in prior phases.

---

## Architecture Patterns

### System Architecture Diagram

```
Browser Request
    │
    ▼
SvelteKit SSR (+page.server.ts)
    │  loads FASTAPI_BASE_URL from $env/static/private
    │
    ├─► FastAPI GET /cases
    │       │
    │       └─► cases_service.get_cases()
    │               └─► SELECT cases JOIN case_arguments JOIN arguments
    │                         (ordered by argued_date DESC)
    │
    └─► FastAPI GET /arguments/{id}/utterances
            (existing, unchanged)

SvelteKit Serializes Data → HTML
    │
    ▼
Browser Hydrates
    │
    ├─► $derived: extract roster from utterances
    ├─► $derived: extract section anchors from utterances  
    └─► $effect: IntersectionObserver (guarded by browser check)
            │
            └─► Updates $state activeSection
                    └─► Reactive highlight in nav rail
```

### Recommended Project Structure — New Files

```
app/src/routes/
├── cases/
│   ├── +page.server.ts          NEW — loads GET /cases
│   ├── +page.svelte             NEW — case list page
│   └── [slug]/
│       ├── +page.server.ts      NEW — loads arguments for this case (navigation model)
│       ├── +page.svelte         NEW — lists arguments for a case (multi-argument support)
│       └── arguments/
│           └── [id]/
│               ├── +page.server.ts    EXISTING — no changes needed
│               └── +page.svelte       EXISTING — restructure for sidebar + roster

app/src/lib/components/
├── ChatBubble.svelte             EXISTING — add avatar circle, flip alignment
└── SectionRail.svelte            NEW — scroll-spy nav component

api/
├── routers/cases.py              NEW — GET /cases router
├── services/cases.py             NEW — cases service
├── schemas/cases.py              NEW — CaseListResponse, CaseItem
└── main.py                       EDIT — register cases router
```

### Pattern 1: FastAPI 3-Layer for GET /cases

**What:** Router calls service, service returns dict, router creates Pydantic response. Mirrors `api/routers/people.py` exactly.

**When to use:** Every new API endpoint in this project.

```python
# api/schemas/cases.py
import datetime
from pydantic import BaseModel

class CaseItem(BaseModel):
    id: int
    slug: str
    case_name: str
    docket_number: str
    term_year: int
    argued_date: datetime.date   # from argument row (first/only argument for Phase 3)
    argument_id: int             # planner's discretion: include for direct-to-argument linking

class CaseListResponse(BaseModel):
    cases: list[CaseItem]
```

```python
# api/services/cases.py — query pattern
# Source: [VERIFIED — established pattern from api/services/arguments.py]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.models import Case, Argument, CaseArgument

async def get_cases(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Case, Argument)
        .join(CaseArgument, CaseArgument.case_id == Case.id)
        .join(Argument, CaseArgument.argument_id == Argument.id)
        .where(CaseArgument.is_lead == True)
        .order_by(Argument.argued_date.desc())
    )
    rows = result.all()
    return [
        {
            "id": case.id,
            "slug": case.slug,
            "case_name": case.case_name,
            "docket_number": case.docket_number,
            "term_year": case.term_year,
            "argued_date": argument.argued_date,
            "argument_id": argument.id,
        }
        for case, argument in rows
    ]
```

**Note on multi-argument cases:** For Phase 3 (Obergefell Q1 only), joining through `is_lead=True` and taking one argument per case is sufficient. If Q2 is later loaded, the intermediate `/cases/[slug]` page handles it. The `argument_id` field in `CaseItem` enables direct linking from the case list to arguments.

### Pattern 2: SvelteKit SSR Load for Case List

**What:** `+page.server.ts` fetches from FASTAPI_BASE_URL (private env var), throws `error()` on failure.

```typescript
// app/src/routes/cases/+page.server.ts
// Source: [VERIFIED — mirrors app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts]
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch }) => {
    const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
    if (!res.ok) throw error(res.status, 'Failed to load cases');
    const data = await res.json();
    return { cases: data.cases };
};
```

### Pattern 3: Case Navigation Model (D-09 — Claude's Discretion)

**Recommendation:** Intermediate `/cases/[slug]` page.

**Rationale:** Obergefell eventually has Q1 and Q2. A direct case-list → argument link works only for single-argument cases. The intermediate page is a lightweight list of arguments for the case — it renders a single-argument case as an instant redirect (using SvelteKit `redirect()`) or a selection list for multi-argument cases.

**Implementation approach:**
- `/cases/+page.server.ts` — loads `GET /cases`, returns `cases` array
- `/cases/+page.svelte` — renders list linking to `/cases/{slug}`  
- `/cases/[slug]/+page.server.ts` — queries FastAPI for arguments of this case OR redirects immediately if only one argument exists
- `/cases/[slug]/+page.svelte` — argument picker (rendered only for multi-argument cases)

For Phase 3 with one loaded argument per case, the `[slug]` page will always have one argument and can link directly to `/cases/[slug]/arguments/[id]`. When Q2 is loaded, it renders naturally without code changes.

**API consideration:** The `GET /cases` endpoint returns one row per case (lead-docket join). A separate `GET /cases/{slug}/arguments` is NOT needed for Phase 3 — the `argument_id` in the cases list response is sufficient for single-argument cases. The intermediate `[slug]` page can derive the single argument from the cases list data passed via the load function, or use the existing `/arguments/{id}/utterances` response for context.

### Pattern 4: Svelte 5 `$effect` with IntersectionObserver (Scroll-Spy)

**What:** Observe each section anchor element; update `$state activeSection` when a section enters the viewport.

**Critical rule:** `$effect` runs after the DOM mounts but ALSO runs during SSR prerender. Browser APIs like `IntersectionObserver` do not exist on the server. Must guard with `browser` from `$app/environment` or check `typeof IntersectionObserver !== 'undefined'`.

**Known issue:** There is a reported Svelte 5 bug (issue #12731) where `bind:this` cleanup ordering in `$effect` can cause crashes with observers. The safe pattern is to collect all bound elements into a reactive array via `$state`, then observe them in a single `$effect` that returns a cleanup function.

```typescript
// app/src/lib/components/SectionRail.svelte
// Source: [VERIFIED — Svelte 5 docs: $effect cleanup pattern]
<script lang="ts">
    import { browser } from '$app/environment';

    let { sections }: { sections: { hint: string; label: string; anchorId: string }[] } = $props();

    let activeSection = $state<string | null>(null);

    $effect(() => {
        if (!browser) return;
        const observers: IntersectionObserver[] = [];

        for (const section of sections) {
            const el = document.getElementById(section.anchorId);
            if (!el) continue;
            const obs = new IntersectionObserver(
                (entries) => {
                    if (entries[0].isIntersecting) {
                        activeSection = section.hint;
                    }
                },
                { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
            );
            obs.observe(el);
            observers.push(obs);
        }

        return () => {
            observers.forEach((o) => o.disconnect());
        };
    });

    function scrollTo(anchorId: string) {
        document.getElementById(anchorId)?.scrollIntoView({ behavior: 'smooth' });
    }
</script>
```

**rootMargin explanation:** `-40% 0px -55% 0px` means the intersection zone is a ~5% band around the viewport center. A section becomes "active" when its first utterance is near the middle of the screen — the standard scroll-spy UX. [ASSUMED — specific rootMargin values depend on desired UX; planner may tune]

### Pattern 5: Section Anchor Derivation (D-04)

**What:** Client-side extraction of section boundaries from the utterances array.

**section_hint values in DB:** Confirmed lowercase: `"petitioner"`, `"respondent"`, `"rebuttal"`, `"amicus"`. Display as title case in the rail label.

**Key constraint (from CONTEXT.md specifics):** The first utterance after a section transition marker carries `section_hint`. Only that first utterance per section has a non-null hint — subsequent utterances have null. Use these as the scroll anchor targets.

```typescript
// In +page.svelte (argument view) — $derived
// Source: [VERIFIED — utterance schema in api/schemas/utterance.py]
const sectionAnchors = $derived(
    data.utterances
        .filter(u => u.section_hint !== null && !u.is_stage_direction)
        .map(u => ({
            hint: u.section_hint as string,
            label: u.section_hint!.charAt(0).toUpperCase() + u.section_hint!.slice(1),
            anchorId: `section-${u.section_hint}-${u.sequence}`,
            sequence: u.sequence,
        }))
);
```

Each utterance that is the first of a section gets `id={anchorId}` on its bubble wrapper `<div>`.

### Pattern 6: Avatar Circle (D-06/D-07/D-08)

**What:** 32px circle with speaker initials. Color based on side.

**Initials computation:** Take first letter of first word and first letter of last word of `displayName`. Handle single-word names (use first two chars or just first char).

```typescript
// In ChatBubble.svelte — $derived
// Source: [ASSUMED — standard initials algorithm]
const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
const initials = $derived(() => {
    const parts = displayName.trim().split(/\s+/);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    return displayName.slice(0, 2).toUpperCase();
});
```

**Layout:** The bubble `<div>` currently wraps speaker name + text in a single column. Adding the avatar changes the layout to a flex row: `[avatar circle] [name + text column]`. The avatar sits to the LEFT of the speaker name row (per D-07).

**Note on D-05 (alignment flip):** `ChatBubble.svelte` line 14 has `justify-content: {isBench ? 'flex-end' : 'flex-start'}`. Phase 3 reverses this to `justify-content: {isBench ? 'flex-start' : 'flex-end'}`. This is a one-line change but must be made first before testing the avatar layout, since alignment affects which side the avatar appears on.

### Pattern 7: Two-Column Argument View Layout

**Current state:** Single-column, `max-width: 860px; margin: 0 auto` on the chat column.

**New structure:**

```
┌──────────────────────────────────────────────────┐
│  Header bar (full width, #1e293b)                │
│    Case name + docket + date + speaker roster    │
└──────────────────────────────────────────────────┘
┌────────────┬─────────────────────────────────────┐
│  Nav Rail  │   Chat Column                       │
│  ~180px    │   (grows to fill remaining width)   │
│  sticky    │                                     │
│            │   [ChatBubble]                      │
│  Petitioner│   [ChatBubble]                      │
│  Respondent│   [StageDirection]                  │
│  Rebuttal  │   ...                               │
└────────────┴─────────────────────────────────────┘
```

**CSS approach:** CSS Grid on the outer container with `grid-template-columns: 180px 1fr`. The rail column uses `position: sticky; top: [header height]px; height: calc(100vh - [header height]px); overflow-y: auto`. The chat column has no max-width cap (the grid handles sizing). [ASSUMED — exact header height depends on roster expansion; planner should measure]

**Mobile (D-03):** Below 768px, the rail column hides (`display: none`) and the chat spans full width.

### Pattern 8: Speaker Roster in Header (D-11/D-12)

**What:** Two-column layout below the docket/date subline. Bench (Justice names) left; Advocates right.

**Data source:** `data.utterances` already in scope. Derive with `$derived`.

```typescript
// In +page.svelte — $derived
// Source: [VERIFIED — UtteranceResponse schema has speaker_name, speaker_role, side]
const roster = $derived(() => {
    const seen = new Set<string>();
    const bench: { name: string; role: string | null }[] = [];
    const advocates: { name: string; role: string | null }[] = [];
    for (const u of data.utterances) {
        if (u.is_stage_direction) continue;
        const key = u.speaker_name ?? u.raw_speaker_label ?? '';
        if (!key || seen.has(key)) continue;
        seen.add(key);
        const entry = { name: key, role: u.speaker_role ?? null };
        if (u.side === 'BENCH') bench.push(entry);
        else advocates.push(entry);
    }
    return { bench, advocates };
});
```

**Apolitical constraint:** Both bench and advocate columns use the same font weight, size, and color treatment — no visual hierarchy between the two groups beyond their spatial position.

### Anti-Patterns to Avoid

- **`export let` in Svelte 5:** Use `$props()` exclusively. No `export let` anywhere in Phase 3 components.
- **`$:` reactive blocks in Svelte 5:** Use `$derived` for computed values. No `$:` assignments.
- **`onDestroy` for observer cleanup:** Return cleanup function from `$effect` instead.
- **`PUBLIC_FASTAPI_BASE_URL`:** The env var is always `FASTAPI_BASE_URL` from `$env/static/private`. Never use a `PUBLIC_` prefix.
- **`Base.metadata.create_all`:** Not applicable to Phase 3 (no schema changes), but worth stating: Alembic is sole DDL authority.
- **IntersectionObserver without browser guard:** Always check `browser` from `$app/environment` before accessing browser APIs in `$effect`. The SSR pass will execute `$effect` on the server; IntersectionObserver is undefined there.
- **`bind:this` arrays for section anchors:** Prefer `document.getElementById(anchorId)` over binding arrays, because the bind:this/`$effect` ordering issue (svelte#12731) can cause crashes.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Scroll-spy active state | Custom scroll event listener with throttle/debounce | IntersectionObserver (native browser API) | IntersectionObserver is declarative, performant (no scroll event jank), handles resizes automatically |
| Initials computation | Edge-case-heavy name parser | Simple split-on-whitespace, first+last char | Names in this dataset are in "First Last" or "Last" format; no honorifics in `full_name` field |
| Two-column layout | JavaScript-driven positioning | CSS Grid | Grid handles sticky sidebar, responsive collapse, and dynamic content height natively |

**Key insight:** All UI state in Phase 3 derives from the utterances array already loaded at page render time. No additional data fetching is needed on the client.

---

## Common Pitfalls

### Pitfall 1: `section_hint` casing mismatch

**What goes wrong:** CONTEXT.md specifics says values are `"PETITIONER"` etc. in uppercase. The actual DB values (confirmed in `pipeline/parser/state_machine.py` SECTION_HINT_MAP) are lowercase: `"petitioner"`, `"respondent"`, `"rebuttal"`, `"amicus"`.

**Why it happens:** The CONTEXT.md was describing the TOC markers (which are uppercase in the transcript), not the stored canonical values.

**How to avoid:** Always use lowercase when comparing `section_hint` values. Convert to title case for display: `hint.charAt(0).toUpperCase() + hint.slice(1)`.

**Warning signs:** Sections not matching / no rail items appearing — check the hint casing.

### Pitfall 2: IntersectionObserver on SSR

**What goes wrong:** `$effect` that creates `new IntersectionObserver(...)` runs on the Node.js server during SSR. `IntersectionObserver` is not defined there. The page throws a ReferenceError.

**Why it happens:** Unlike `onMount` (which is browser-only), `$effect` runs in both environments in Svelte 5 unless guarded.

**How to avoid:** Import `browser` from `$app/environment` and guard: `if (!browser) return;` as the first line of any `$effect` that uses browser APIs.

**Warning signs:** `ReferenceError: IntersectionObserver is not defined` in the dev server console.

### Pitfall 3: Multi-argument case navigation breaks on Q2 load

**What goes wrong:** If the case list links directly to `/cases/[slug]/arguments/3` (hardcoded argument_id), adding Q2 (argument_id=N) won't be reachable.

**Why it happens:** Direct linking encodes the argument_id in the case list, so the UI never offers a Q2 choice.

**How to avoid:** Use the intermediate `/cases/[slug]` page model. Each case list item links to `/cases/{case.slug}`, not to `/cases/{case.slug}/arguments/{argument_id}`. The `[slug]` page resolves to arguments for that case.

**Warning signs:** Q2 loads into DB but is unreachable from the UI.

### Pitfall 4: GET /cases returns duplicate rows for consolidated dockets

**What goes wrong:** Obergefell has 4 docket numbers (14-556, 14-562, 14-571, 14-574) linked to argument_id=3 via `case_arguments`. A naive `JOIN cases → case_arguments → arguments` returns 4 rows for the same argument.

**Why it happens:** The M:M join table has one row per (case, argument) pair.

**How to avoid:** Filter `WHERE case_arguments.is_lead = TRUE` in the `GET /cases` service. This returns exactly one row per case (the lead docket). Non-lead consolidated dockets are intentionally excluded from the case list.

**Warning signs:** Obergefell appears multiple times in the case list.

### Pitfall 5: Roster appears empty when `speaker_name` is null

**What goes wrong:** Phase 2 (resolve step) populates `speaker_name`. If Phase 2 has not run for a new case, all `speaker_name` fields are null. The roster fallback must use `raw_speaker_label`.

**Why it happens:** `speaker_name` is nullable per `UtteranceResponse` schema; Phase 1 utterances have `person_id = null` and therefore `speaker_name = null`.

**How to avoid:** Roster derivation uses `u.speaker_name ?? u.raw_speaker_label ?? ''` — same fallback as `ChatBubble.svelte`'s existing `displayName`.

**Warning signs:** Empty roster even though utterances are visible.

### Pitfall 6: Sticky sidebar height causes double scrollbar

**What goes wrong:** `position: sticky` on the sidebar with `height: 100vh` creates an inner scrollable area, resulting in two scrollbars (page + sidebar).

**Why it happens:** `height: 100vh` gives the sidebar its own height context that can exceed the viewport if not managed correctly.

**How to avoid:** Use `position: sticky; top: 0; max-height: calc(100vh - [nav-height]px); overflow-y: auto;` only if sidebar content overflows. For Phase 3 (at most 4 section items), overflow is unlikely. Prefer `align-self: start` + `position: sticky; top: [offset]` with no explicit height.

**Warning signs:** A second scrollbar appears on the left side of the page.

---

## Code Examples

### GET /cases router (follows people.py template)

```python
# api/routers/cases.py
# Source: [VERIFIED — mirrors api/routers/people.py exactly]
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.schemas.cases import CaseListResponse
from api.services import cases as cases_service

router = APIRouter(prefix="/cases", tags=["cases"])

@router.get("", response_model=CaseListResponse)
async def get_cases(
    db: AsyncSession = Depends(get_db),
) -> CaseListResponse:
    """Return all loaded cases with metadata for the case list page."""
    results = await cases_service.get_cases(db)
    return CaseListResponse(cases=results)
```

### main.py registration (one line addition)

```python
# api/main.py — EDIT
# Source: [VERIFIED — existing api/main.py pattern]
from api.routers import cases as cases_router
# ...
app.include_router(cases_router.router)
```

### ChatBubble.svelte — avatar + alignment flip (D-05 + D-06/D-07/D-08)

```svelte
<!-- app/src/lib/components/ChatBubble.svelte — EDIT -->
<!-- Source: [VERIFIED — read existing ChatBubble.svelte] -->
<script lang="ts">
    let { utterance } = $props();

    const isBench = utterance.side === 'BENCH';
    // D-05: Bench LEFT, advocate RIGHT (reverses Phase 1)
    const labelColor = isBench ? '#94a3b8' : '#93c5fd';
    const avatarBg = isBench ? '#94a3b8' : '#93c5fd';
    const displayName = utterance.speaker_name ?? utterance.raw_speaker_label ?? '';
    const displayRole = utterance.speaker_role ?? null;

    // D-07: 32px initials circle — first letter of first + last word
    const initials = (() => {
        const parts = displayName.trim().split(/\s+/);
        if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        return displayName.slice(0, 2).toUpperCase();
    })();
</script>

<!-- D-05: justify-content flipped — bench LEFT, advocate RIGHT -->
<div style="display: flex; justify-content: {isBench ? 'flex-start' : 'flex-end'};">
    <div style="max-width: 72%; ...">
        <!-- Bubble header row: avatar + sequence + speaker label -->
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <!-- D-07: 32px avatar circle, left of speaker name -->
            <div style="
                width: 32px; height: 32px; border-radius: 50%;
                background-color: {avatarBg};
                display: flex; align-items: center; justify-content: center;
                font-size: 12px; font-weight: 600; color: #0f1117;
                flex-shrink: 0;
            ">{initials}</div>
            <span style="font-size: 13px; color: #475569; ...">{utterance.sequence}</span>
            <span style="font-size: 13px; font-weight: 600; color: {labelColor};">{displayName}</span>
            {#if displayRole}<span ...>{displayRole}</span>{/if}
        </div>
        <p ...>{utterance.text}</p>
    </div>
</div>
```

### SectionRail.svelte — scroll-spy with $effect + browser guard

```svelte
<!-- app/src/lib/components/SectionRail.svelte — NEW -->
<!-- Source: [VERIFIED — Svelte 5 $effect cleanup pattern from svelte.dev/docs] -->
<script lang="ts">
    import { browser } from '$app/environment';

    type SectionAnchor = { hint: string; label: string; anchorId: string };
    let { sections }: { sections: SectionAnchor[] } = $props();

    let activeSection = $state<string | null>(null);

    $effect(() => {
        if (!browser || sections.length === 0) return;

        const observers: IntersectionObserver[] = [];
        for (const sec of sections) {
            const el = document.getElementById(sec.anchorId);
            if (!el) continue;
            const obs = new IntersectionObserver(
                ([entry]) => { if (entry.isIntersecting) activeSection = sec.hint; },
                { rootMargin: '-40% 0px -55% 0px', threshold: 0 }
            );
            obs.observe(el);
            observers.push(obs);
        }
        return () => observers.forEach(o => o.disconnect());
    });
</script>

<nav style="position: sticky; top: 0; padding: 24px 16px;">
    {#each sections as sec}
        <button
            onclick={() => document.getElementById(sec.anchorId)?.scrollIntoView({ behavior: 'smooth' })}
            style="
                display: block; width: 100%; text-align: left;
                padding: 8px 12px; margin-bottom: 4px; border: none; cursor: pointer;
                border-radius: 4px; font-size: 13px;
                background-color: {activeSection === sec.hint ? '#1e293b' : 'transparent'};
                color: {activeSection === sec.hint ? '#e2e8f0' : '#94a3b8'};
                border-left: 3px solid {activeSection === sec.hint ? '#93c5fd' : 'transparent'};
            "
        >{sec.label}</button>
    {/each}
</nav>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `onDestroy` for browser API cleanup | Return cleanup function from `$effect` | Svelte 5 (2024) | No `onDestroy` import needed; `$effect` manages its own teardown |
| `export let` props | `$props()` rune | Svelte 5 (2024) | Already enforced in this codebase |
| `$:` reactive declarations | `$derived` / `$state` | Svelte 5 (2024) | Already enforced in this codebase |
| `@app.on_event` startup | `lifespan` context manager | FastAPI 0.93+ | Already implemented in `api/main.py` |

**Deprecated/outdated:**
- `onMount` for observer setup: Still works but `$effect` with `browser` guard is the idiomatic Svelte 5 pattern. `onMount` is valid fallback.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `rootMargin: '-40% 0px -55% 0px'` produces good scroll-spy UX | Code Examples / SectionRail | Sections may activate too early or late; planner should note this is tunable |
| A2 | Intermediate `/cases/[slug]` page is the right navigation model for D-09 | Architecture Patterns / Pattern 3 | If planner decides direct linking, skip the `[slug]` intermediate page; API-02 still needs `argument_id` in response |
| A3 | CSS Grid `grid-template-columns: 180px 1fr` for two-column layout | Code Examples | Exact column width may need adjustment based on actual content width |
| A4 | Avatar initials use first+last word first letters | Code Examples / ChatBubble | Names like "MR. JUSTICE SCALIA" would produce "MS" — may look odd; planner may want to strip titles |
| A5 | GET /cases returns one argument per case (lead docket only) for Phase 3 | Architecture Patterns / Pattern 1 | If cases have multiple arguments (Q2 loaded), endpoint needs GROUP BY or DISTINCT logic — confirmed as non-issue for Phase 3 |

---

## Open Questions (RESOLVED)

1. **D-09: Navigation model for multi-argument cases** — RESOLVED: Intermediate `/cases/[slug]` page with `redirect(307, ...)` for single-argument cases; argument picker for multi-argument cases. Implemented in 03-02-PLAN.md.
   - What we know: Obergefell has Q1 (loaded) and Q2 (not loaded in Phase 3). The slug is `obergefell-v-hodges`.
   - Decision: Build the intermediate page. It's 3 files and enables Q2 without a refactor. If only one argument exists, `redirect(307, ...)` to it directly.

2. **`GET /cases` response: include `argument_id` field?** — RESOLVED: Yes, `argument_id` is included in `CaseItem`. Implemented in 03-01-PLAN.md (`api/schemas/cases.py`).
   - What we know: CaseItem needs `argument_id` to link to arguments. The join already retrieves the Argument row.
   - Decision: Include `argument_id` in `CaseItem`. Cheap to add and enables direct argument links.

3. **Avatar initials for unresolved speakers** — RESOLVED: Simple first+last word algorithm used. Implemented in 03-03-PLAN.md (`ChatBubble.svelte`).
   - What we know: Phase 2 resolves speaker names. If a new case is loaded without running resolve, `speaker_name` is null and `raw_speaker_label` is used (e.g., "CHIEF JUSTICE ROBERTS").
   - Decision: Use simple first+last word algorithm. Output for "CHIEF JUSTICE ROBERTS" is "CR". Acceptable for Phase 3.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Node.js / npm | SvelteKit build | Already in use | No new install needed |
| Python 3.12 / pip | FastAPI | Already in use | No new install needed |
| PostgreSQL 16 | API data layer | Already running | No change |
| `browser` from `$app/environment` | SectionRail SSR guard | Built into SvelteKit | No install; tree-shaken at build |
| IntersectionObserver | Section scroll-spy | Browser native API | Not available during SSR; use `browser` guard |

No missing dependencies.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (Python), no frontend test framework installed |
| Config file | `pytest.ini` or default discovery (tests/ directory) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| API-02 | `GET /cases` returns 200 with cases array | smoke (static analysis) | `pytest tests/test_cases_api.py -x -q` | No — Wave 0 gap |
| API-02 | `GET /cases` result does not duplicate Obergefell via consolidated dockets | unit (no DB) | N/A — tested via DB integration | No |
| UI-04 | Argument header renders roster | manual-only | — | N/A |
| UI-05 | Avatar renders initials, no broken images | manual-only | — | N/A |
| UI-06 | Hard refresh at `/cases/{slug}/arguments/{id}` returns 200 SSR | manual | `curl -s http://localhost:5173/cases/obergefell-v-hodges/arguments/3 | grep -c 'data-sveltekit'` | No |
| UI-07 | Case list page loads and renders | manual | — | N/A |
| UI-08 | Section rail shows Petitioner section | manual | — | N/A |

**Note:** The existing test suite (tests/test_schema.py, tests/test_models_import.py) covers schema-level concerns. Phase 3 API additions should have a static analysis test verifying the new `cases` router is registered in `main.py`, mirroring the `test_no_create_all_in_codebase` pattern.

### Sampling Rate

- Per task commit: `pytest tests/ -x -q` (< 5s — static analysis + schema tests skip DB)
- Per wave merge: `pytest tests/ -x -q` + manual browser check
- Phase gate: Full suite green + 5 manual checks (case list renders, argument opens, section rail shows, avatar initials visible, hard refresh works)

### Wave 0 Gaps

- `tests/test_cases_api.py` — static analysis test: cases router registered in main.py; `GET /cases` path defined in router; no `create_all` in `api/routers/cases.py`

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Read-only public site; no auth in v1 |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | All content public |
| V5 Input Validation | Yes — `argument_id` path param | FastAPI type annotation (`int`) — non-integers produce 422 before service layer (established pattern from arguments router) |
| V6 Cryptography | No | No secrets in Phase 3 |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via slug | Tampering | `slug` is read from DB (not filesystem); used only as a URL param, never as a file path |
| FASTAPI_BASE_URL exposure | Info Disclosure | Already enforced: `$env/static/private` only; never `PUBLIC_` prefix — CLAUDE.md hard constraint |
| SQL injection via argument_id | Tampering | FastAPI `int` type annotation rejects non-integers at router level; parameterized SQLAlchemy queries |

---

## Sources

### Primary (HIGH confidence)

- Codebase read — `api/routers/people.py`, `api/services/arguments.py`, `api/schemas/utterance.py`, `api/models/models.py`, `api/main.py` — established patterns verified directly
- Codebase read — `pipeline/parser/state_machine.py` (SECTION_HINT_MAP) — confirmed `section_hint` values are lowercase
- Codebase read — `app/src/lib/components/ChatBubble.svelte`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`, `+page.server.ts` — current implementation verified
- Codebase read — `app/package.json` — confirmed Svelte 5.30, SvelteKit 2.21, no new packages needed
- Codebase read — `app/src/app.css` — confirmed CSS custom properties already defined
- [svelte.dev/docs/svelte/svelte-reactivity](https://svelte.dev/docs/svelte/svelte-reactivity) — `createSubscriber` and `$effect` cleanup pattern verified
- [svelte.dev/docs/kit/load](https://svelte.dev/docs/kit/load) — `+page.server.ts` pattern, SSR behavior, `error()` helper verified

### Secondary (MEDIUM confidence)

- [github.com/sveltejs/svelte/issues/12731](https://github.com/sveltejs/svelte/issues/12731) — `bind:this`/`$effect` ordering issue; recommends `getElementById` over `bind:this` arrays
- WebSearch + official docs — `browser` from `$app/environment` is the canonical SSR guard for browser APIs in SvelteKit

### Tertiary (LOW confidence)

- rootMargin values for scroll-spy (`-40% 0px -55% 0px`) — training knowledge, community convention; marked [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already installed; no new dependencies
- Architecture: HIGH — all patterns read directly from existing codebase; FastAPI 3-layer pattern and SvelteKit SSR pattern are verified
- Pitfalls: HIGH (section_hint casing, SSR guard, duplicate rows) / MEDIUM (sticky sidebar height) — most confirmed via codebase inspection
- Scroll-spy rootMargin: LOW — specific values are assumed

**Research date:** 2026-06-12
**Valid until:** 2026-07-12 (stable stack; Svelte 5 / SvelteKit 2 patch releases unlikely to break patterns)
