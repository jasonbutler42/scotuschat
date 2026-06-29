# Phase 14: Speaker Popover Card - Context

**Gathered:** 2026-06-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 adds a clickable speaker popover card to the public argument view. Visitors can click any speaker's avatar to open a floating card showing identity details. All speakers get name and role. Bench speakers additionally get tenure dates and appointing president.

**Two trigger locations:**
1. **ChatBubble avatars** — the 32px circles inside each utterance bubble become clickable/focusable buttons that open the popover
2. **Header roster avatars** — the existing text-only roster entries in the argument header each get an avatar circle to the left of the name text; these also become clickable

**Popover content by speaker type:**
- All speakers: photo (or styled initials fallback), full_name, role_name
- Bench only: all tenure rows (sorted chronologically) with `[start_year]–present` for active Justices, and "Appointed by [appointing_president]"

**Out of scope:** party affiliation in public popover (admin metadata only — already in REQUIREMENTS.md Out of Scope), image crop, animated transitions, audio playback, multi-appointer tenure attribution (deferred).

</domain>

<decisions>
## Implementation Decisions

### API Data Strategy

- **D-01:** A new public endpoint `GET /api/arguments/{id}/speakers` returns all unique speakers for the argument, pre-assembled with full popover data. One API call from `+page.server.ts` — no per-person loops and no client-side fetch. The new route lives in `api/routers/arguments.py` (or a new `speakers.py` router — Claude's discretion) and calls a new service function.
- **D-02:** Each entry in the response contains: `person_id`, `full_name`, `role_name`, `photo_url` (raw value from DB — relative or absolute), `tenure` (array of `{seat, start_date, end_date}` from `court_tenures`), and `appointing_president`. The `person_id` key lets the frontend build a `Map<number, SpeakerDetail>` for O(1) lookups when rendering popovers.
- **D-03:** `photo_url` reconstruction follows the admin pattern: in `+page.server.ts`, if `photo_url` starts with `/`, prepend `FASTAPI_BASE_URL` (from `$env/static/private`). Otherwise use as-is (full URL from Spaces). The reconstructed URL is passed to the client as `photo_url_full`. `FASTAPI_BASE_URL` never reaches the browser.
- **D-04:** The public `PersonResponse` schema is NOT extended — the new endpoint uses its own Pydantic response model (`SpeakerPopoverResponse` or similar) in `api/schemas/`. The existing `GET /people/{id}` endpoint remains unchanged.

### Trigger Scope

- **D-05:** Both trigger locations get clickable avatars: ChatBubble utterance avatars AND header roster entries. The roster currently shows text names only; Phase 14 adds an avatar circle (matching the ChatBubble 32px size and color logic) to the left of each name.
- **D-06:** The popover trigger is a `<button>` element (or bits-ui `Popover.Trigger` wrapping a button). The existing `div` avatars in `ChatBubble` become `<button>` elements with `type="button"`, `aria-label="View {name} details"`. The `aria-hidden="true"` on the avatar circle is removed when it becomes the trigger.
- **D-07:** The header roster avatar + name row is a flex row: `[avatar button] [name text]`. Clicking either the avatar or the name text should open the popover (wrap both in the trigger, or make the avatar-only clickable — Claude's discretion based on bits-ui API).

### Tenure Display (Bench Only)

- **D-08:** Show all `court_tenure` rows for the person, sorted by `start_date ASC`. Each tenure row displays: seat name + `[start_year]–[end_year]` or `[start_year]–present` when `end_date IS NULL`.
- **D-09:** `appointing_president` is shown as "Appointed by [name]" using the single field from the `people` table. The tenure-linked appointment attribution (e.g., different presidents per tenure) is deferred — for now one appointing president per person.

### Popover Card Layout

- **D-10:** Responsive layout: **horizontal on desktop** (photo/initials left, text right in flex row), **vertical on mobile** (photo/initials above text). Breakpoint: 768px — matches the existing project-wide mobile breakpoint.
- **D-11:** One `SpeakerPopover.svelte` component handles both bench and advocate speakers. Bench-only fields (tenure, appointing president) render conditionally when `isBench` is true. No visual distinction between bench and advocate card — same styling, different content set.

### bits-ui Integration

- **D-12:** Install `bits-ui@^2.18.1` (chosen in prior research — only Svelte 5-native headless popover after `@skeletonlabs/floating-ui-svelte` was archived Oct 2025). Add to `app/package.json` as a dependency.
- **D-13:** Use `bits-ui` Popover primitives: `Popover.Root`, `Popover.Trigger`, `Popover.Content`. The trigger wraps the avatar button; the content renders the `SpeakerPopover.svelte` card. Escape key dismissal is handled by bits-ui natively (PUB-04 satisfied automatically).

### Claude's Discretion

- Whether the header roster trigger wraps avatar-only or avatar+name together
- Exact `SpeakerPopover` card dimensions and padding (match admin dark theme tokens: `#1e293b` card surface, `#334155` border, `#e2e8f0` primary text, `#94a3b8` secondary text)
- Photo/initials circle size in the popover card (suggest 56–64px, larger than the 32px trigger avatar)
- Whether `Popover.Content` has a close button in addition to Escape dismissal
- Popover arrow/caret or no caret

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §Public Experience — PUB-01, PUB-02, PUB-03, PUB-04 (4 requirements this phase closes)
- `.planning/ROADMAP.md` §Phase 14 — Goal and 4 success criteria (must all be TRUE)
- `.planning/REQUIREMENTS.md` §Out of Scope — "Party affiliation in public popover" is explicitly excluded; do NOT expose `appointing_president_party` publicly

### Existing Implementation to Extend
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — argument page where new triggers and popover live; roster section (lines ~108–156) needs avatar circles; roster derived via `$derived.by()` (lines ~27–46)
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` — server load function; add call to new `GET /api/arguments/{id}/speakers`; reconstruct `photo_url_full` server-side
- `app/src/lib/components/ChatBubble.svelte` — avatar `div` (line ~47) becomes a `Popover.Trigger` wrapping a `<button>`; `aria-hidden="true"` must be removed from the trigger
- `api/routers/arguments.py` — add new `GET /arguments/{id}/speakers` route
- `api/models/models.py` — `Person` (photo_url, appointing_president fields), `CourtTenure` (person_id FK, seat, start_date, end_date) — read before writing service query

### API & Service Layer Patterns
- `api/services/arguments.py` — `get_argument_with_utterances()` — existing pattern for argument-scoped queries with joins; new speakers service mirrors this structure
- `api/services/admin_people.py` — `upload_photo()` / `update_photo_url()` — establishes that `photo_url` can be relative (`/uploads/people/...`) or absolute (Spaces URL)
- `app/src/routes/admin/people/[id]/+page.server.ts` — photo_url reconstruction pattern: `if (person.photo_url?.startsWith('/')) { photo_url_full = FASTAPI_BASE_URL + person.photo_url; }` — replicate this in the argument page server load

### Prior Phase Context
- `.planning/STATE.md` §Accumulated Context — "bits-ui ^2.18.1 chosen for speaker popover"; "Speaker popover data pre-loaded in +page.server.ts — no client-side fetch"; "appointing_party is admin-only — public popover shows 'Appointed by [president]' with no party affiliation"
- `.planning/phases/09-people-data-model-migration/09-CONTEXT.md` — D-01 through D-03: migration 0006 added six nullable columns to people; full_name preserved as resolution anchor; the new fields may be null for many people records

### Design System
- Admin dark theme tokens: `#0f1117` bg, `#1e293b` card surface, `#334155` border, `#94a3b8` body text, `#e2e8f0` primary text, `#93c5fd` accent blue — popover card must use these

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatBubble.svelte` — existing `initials` derivation logic (lines ~9–14); avatar circle styles (32px, border-radius 50%, bg from avatarBg); can be extracted to a shared utility or kept inline
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — `roster` `$derived.by()` already groups speakers into `bench[]` and `advocates[]` with `name` and `role`; the new speakers Map from `GET /arguments/{id}/speakers` should be keyed by `person_id` so ChatBubble can look up via `utterance.person_id`
- `formatDate()` — already defined in the argument page; tenure date formatting can follow the same `Intl.DateTimeFormat` pattern or use year-only slicing

### Established Patterns
- **No client-side fetch**: all data fetching in `+page.server.ts`; `FASTAPI_BASE_URL` is `$env/static/private` — never `PUBLIC_`; pattern is established and enforced
- **Svelte 5 Runes exclusively**: `$props()`, `$state()`, `$derived()`, `$effect()` — no stores, no `export let`, no `$:` blocks
- **Conditional rendering by prop**: see `ChatBubble` `isBench` flag pattern — the popover reuses the same approach with `isBench` prop to show/hide bench-only fields
- **Form actions + use:enhance**: applies to admin only; the popover is read-only display, no forms
- **bits-ui integration**: not yet used anywhere in the codebase — Phase 14 is the first usage; follow bits-ui v2 Popover docs for Svelte 5

### Integration Points
- `ChatBubble.svelte` receives `utterance` prop including `utterance.person_id`; the argument page must pass a `speakers` prop (the Map) so ChatBubble can look up speaker detail — or the popover can live at the argument page level and ChatBubble emits an event/callback
- Alternatively: argument page keeps the popover state and renders a single `Popover.Root` at the page level; ChatBubble triggers it via a callback. This avoids one bits-ui Root per bubble (potentially dozens)
- The argument page `+page.server.ts` currently returns `{ utterances, argument, argument_id }` — Phase 14 adds `speakers: Map<number, SpeakerDetail>` or a plain record object

</code_context>

<specifics>
## Specific Ideas

- **Single vs. per-bubble Popover.Root**: Consider rendering one `Popover.Root` at the argument page level rather than one inside each `ChatBubble`. With dozens of bubbles on the page, a per-bubble approach creates many Popover instances. A shared root with a `currentSpeaker` `$state` variable is more efficient. ChatBubble receives an `onAvatarClick(personId)` callback prop; the page handles opening and data lookup.
- **Roster trigger row**: `display: flex; align-items: center; gap: 8px;` wrapping `[avatar button] [name text]`. Avatar button reuses the same 32px circle styles from ChatBubble.
- **Tenure row format**: `"Associate Justice — 2005–present"` or `"Chief Justice — 2005–present"` using the `seat` field from `court_tenures` + the date range.
- **Mobile vertical layout**: inside `SpeakerPopover.svelte`, use a CSS media query at 768px to switch from `flex-direction: row` (desktop) to `flex-direction: column` (mobile), matching the existing project breakpoint.
- **Keyboard focus**: when the popover opens, focus should move to the popover content (bits-ui handles this); when it closes via Escape, focus returns to the trigger button (bits-ui default behavior).

</specifics>

<deferred>
## Deferred Ideas

- **Tenure-linked appointment attribution** — For Justices with multiple tenures (e.g., Rehnquist: Associate Justice appointed by Nixon, Chief Justice appointed by Reagan), the correct appointing president per tenure would require linking `appointing_president` to individual `court_tenure` rows. Current data model has a single `appointing_president` on the `people` table. Defer this data model enhancement to a future phase.
- **Advocate firm/organization in popover** — REQUIREMENTS.md §Future Requirements ADV-01: advocate affiliation field on people records. Not in scope for Phase 14.
- **Photo fallback shimmer/skeleton** — Animated loading state while photo URL resolves. Not required; initials fallback already handles missing photos.

</deferred>

---

*Phase: 14-speaker-popover-card*
*Context gathered: 2026-06-25*
