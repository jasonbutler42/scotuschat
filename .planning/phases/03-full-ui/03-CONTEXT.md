# Phase 3: Full UI - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 completes the browseable product. A user can:
- Browse all loaded cases on a case list page
- Open any argument and see a complete header (case name, docket, date, and two-column speaker roster)
- Read the argument with per-speaker avatar initials in every chat bubble
- Jump between argument sections (Petitioner / Respondent / Rebuttal / Amicus) via a sticky sidebar nav rail
- Share or hard-refresh any argument URL and get a correct SSR render

**Phase 3 deliverables:**
1. `GET /cases` FastAPI endpoint (API-02)
2. Case list page at `/cases` (UI-07)
3. Argument header extended with two-column speaker roster (UI-04)
4. Per-bubble avatar circles with initials fallback (UI-05)
5. SSR-correct shareable URLs at `/cases/{slug}/arguments/{id}` verified (UI-06)
6. Sticky sidebar section navigation rail with scroll-spy (UI-08)

**Note:** `photo_url` on `Person` is not populated yet (enrichment deferred to v2). All avatars render as styled initials in Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Section Navigation Rail
- **D-01:** Sticky sidebar layout — two-column: nav rail (~180px) on the left, chat column on the right. Rail anchors to the viewport and is always visible while reading.
- **D-02:** Rail shows section labels (Petitioner / Respondent / Rebuttal / Amicus) with scroll-spy active state — the current section highlights as the user scrolls. Clicking a label smooth-scrolls to that section.
- **D-03:** Mobile behavior: hide the sidebar below ~768px breakpoint; chat spans full width. No section jumping on mobile in Phase 3 (Phase 4 may revisit if needed).
- **D-04:** Section data is derived client-side from the `section_hint` field already present on utterances in the existing response — no new API endpoint needed.

### Chat Bubble Alignment (reverses Phase 1)
- **D-05:** Bench utterances align LEFT; advocate utterances align RIGHT. This is the opposite of the Phase 1 implementation (`ChatBubble.svelte` currently has `isBench → flex-end`, advocates → `flex-start`). Phase 3 flips this to match the header roster layout (Bench left, Advocates right). The planner must update `ChatBubble.svelte` accordingly.

### Avatar Design
- **D-06:** Avatar circle appears in every chat bubble (per-bubble placement), not in the argument header.
- **D-07:** 32px initials circle positioned to the left of the speaker name inside `ChatBubble.svelte`.
- **D-08:** Background color matches speaker side: bench = `#94a3b8` (slate), advocate = `#93c5fd` (blue). Initials text = dark (e.g., `#0f1117`). Consistent with existing label colors in ChatBubble.

### Case List Page
- **D-09:** Navigation model (direct-to-argument vs. intermediate `/cases/[slug]` page) left to the planner. Key constraint: Obergefell has Q1 and Q2 arguments — the model chosen must handle multi-argument cases gracefully.
- **D-10:** Each case in the list shows: case name (primary label) + docket number + argued date.

### Speaker Roster in Argument Header
- **D-11:** Roster is a two-column layout below the existing case name/date subline: Bench (Justice names) on the left, Advocates (counsel names) on the right. Matches the apolitical framing — identical name treatment, spatial separation mirroring the chat layout.
- **D-12:** Roster data derived client-side from the utterances array (deduplicated unique speakers). No new API endpoint — the existing `GET /arguments/{id}/utterances` response already carries `speaker_name`, `speaker_role`, and `side` per utterance.

### Claude's Discretion
- Case list navigation model (D-09): whether the case list links directly to `/cases/[slug]/arguments/[id]` or routes through an intermediate `/cases/[slug]` page. Planner should consider: Obergefell has Q1 + Q2; what's the right UX for multi-argument cases?
- Exact pixel sizing and spacing for the two-column roster within the header bar.
- Scroll-spy implementation approach (IntersectionObserver vs. scroll event listener).
- CSS breakpoint value for mobile sidebar hide (768px suggested; planner may adjust).
- `GET /cases` response shape — what fields to include beyond case name, docket, argued date.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Definition
- `.planning/PROJECT.md` — Core value, apolitical framing hard constraint, out-of-scope items
- `.planning/REQUIREMENTS.md` — UI-04, UI-05, UI-06, UI-07, UI-08 (all Phase 3 UI requirements); API-02 (GET /cases)
- `.planning/ROADMAP.md` — Phase 3 goal, success criteria (5 items), dependency on Phase 2

### Hard Constraints
- `CLAUDE.md` — Apolitical framing (identical treatment for all speakers), all FastAPI calls via `+page.server.ts` (never `PUBLIC_` env var), Alembic sole DDL authority, pipeline offline only

### Existing Code to Read Before Planning
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — current argument view; receives the two-column layout restructure for the section sidebar
- `app/src/lib/components/ChatBubble.svelte` — to be extended with 32px avatar circle; read to understand current props and layout
- `app/src/routes/+layout.svelte` — global nav currently hard-codes Obergefell link; Phase 3 replaces this with a link to the case list
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` — SSR load function pattern; new routes follow this
- `api/schemas/utterance.py` — `UtteranceResponse` (has `speaker_name`, `speaker_role`, `side`, `section_hint`); `ArgumentMetadataResponse` (case_name, docket_number, argued_date, question_number)
- `api/routers/arguments.py` + `api/services/arguments.py` — router/service/schema pattern for new `GET /cases` endpoint
- `api/routers/people.py` — structural template for new cases router

### Established Patterns
- `.planning/phases/01-foundation-proof-of-concept/01-CONTEXT.md` — D-17 (route structure `/cases/[slug]/arguments/[id]` fixed), D-01 (Svelte 5 Runes only), D-18 (FastAPI router/service/schema)
- `.planning/phases/02-speaker-resolution/02-CONTEXT.md` — D-11 (photo_url deferred; GET /people/{id} has name + role only in Phase 2)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatBubble.svelte` — receives `utterance` prop; already has `isBench`, `displayName`, `displayRole`. Avatar circle slots in next to the existing name header row.
- `StageDirection.svelte` — unchanged; stage directions render between bubbles as before.
- `+page.server.ts` (argument route) — SSR load function pattern; new `/cases` and `/cases/[slug]` routes follow the same `FASTAPI_BASE_URL` + `fetch` + `error()` pattern.
- `api/schemas/utterance.py` — `speaker_name`, `speaker_role`, `side`, `section_hint` already in `UtteranceResponse`; no schema changes needed to drive the section rail or roster.

### Established Patterns
- **Dark palette:** #0f1117 (page bg), #1e293b (surface/card), #334155 (borders), #e2e8f0 (body text), #94a3b8 (muted/bench label), #93c5fd (advocate label)
- **Svelte 5 Runes:** `$props()` only — no `export let`, no `$:` reactive blocks, no legacy stores
- **API calls in `+page.server.ts`:** `FASTAPI_BASE_URL` from `$env/static/private` only — never `PUBLIC_` prefix
- **FastAPI 3-layer:** router → service → schema; new `/cases` endpoint follows same split as `arguments` router
- **Apolitical framing:** Identical background color (#1e293b) for all bubble surfaces; side differentiation by layout position only; roster uses spatial separation not color difference

### Integration Points
- `+layout.svelte` global nav: hard-coded Obergefell link needs replacing with `/cases` link
- `+page.svelte` argument view: restructure from single-column to two-column (sidebar + chat) for section rail
- `ChatBubble.svelte`: add avatar circle prop driven by `utterance.speaker_name` initials + `utterance.side`
- `api/main.py` (or router include): new cases router to be registered

</code_context>

<specifics>
## Specific Ideas

- The argument view currently has `max-width: 860px; margin: 0 auto` as the chat column container. The two-column layout will change this — the outer container expands and the sidebar sits beside the chat column (not on top of it).
- Section labels in the rail should map exactly to the `section_hint` values produced by the parse step: `"PETITIONER"`, `"RESPONDENT"`, `"REBUTTAL"`, `"AMICUS"` (uppercase from state machine). Display them in title case.
- The `sequence` number is already shown in every bubble. When implementing scroll-spy, the first utterance of each section (the one with a non-null `section_hint`) is the scroll target anchor.
- Obergefell Q2 session is not loaded yet — the case list for Phase 3 will show only Q1. This is fine.

</specifics>

<deferred>
## Deferred Ideas

- **Obergefell Q2 session** — pipeline supports it; not part of Phase 3. Load after Phase 3 validates the case list.
- **`photo_url` avatars** — enrichment pipeline (ENRICH-01) deferred to v2. Phase 3 avatars are initials-only.
- **Mobile section nav** — hide sidebar on mobile in Phase 3; a horizontal sticky pill row on narrow screens is a Phase 4 candidate.
- **Case list filtering by term year** — DISC-02; deferred to v2 discovery features.
- **Open Graph metadata** — DISC-01; deferred to v2.

</deferred>

---

*Phase: 3-Full UI*
*Context gathered: 2026-06-12*
