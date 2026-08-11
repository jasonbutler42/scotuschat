# Phase 45: Deferred UI Bug Fixes - Context

**Gathered:** 2026-08-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Two unrelated, already-root-caused operator-reported defects carried out of v1.6:

- **BUG-01 (content-exposure gap):** an unpublished argument is visible in the public `/cases/` list and directly reachable by URL. The `/cases/` list is already gated on `Argument.published_at` (D-06, `api/services/cases.py`) and covered by `api/tests/test_published_gate.py`. The gap is direct access: `GET /arguments/{id}/utterances` and `GET /arguments/{id}/speakers` (`api/routers/arguments.py`) return data for any existing argument regardless of publish status.
- **BUG-02 (styling/boundary mismatch):** the native scrollbar on a Justice's popover renders at the edge of `Popover.Content` (which owns `max-height`/`overflow-y` in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`) instead of flush inside the visible rounded card, whose background/border/border-radius live on an inner element of `SpeakerPopover.svelte`.

</domain>

<decisions>
## Implementation Decisions

### BUG-01: Direct access response
- **D-01:** Requesting an unpublished argument's data (utterances or speakers) returns a plain 404 — indistinguishable from a nonexistent argument ID. No "not published yet" messaging is shown to an unauthenticated visitor. — **Reversibility:** reversible — purely a response-shape choice; can be changed to an explicit state later without data migration.
- **D-02:** The publish gate is applied at both `GET /arguments/{id}/utterances` and `GET /arguments/{id}/speakers` (both in `api/routers/arguments.py` / backed by `api/services/arguments.py` and `api/services/speakers.py`), not just the primary utterances call — so no unpublished argument data leaks through either endpoint. The gate must apply on `Argument.published_at` (same field as D-06's `/cases/` gate), not `resolved_at`.
- **Scope note:** these are the *public* router endpoints only. Admin routes/services (`api/routers/admin.py`, `api/services/admin_arguments.py`) are a separate code path used by authenticated operators and must continue to see unpublished arguments — do not add this gate there.

### BUG-02: Scrollbar/card boundary fix
- **D-03:** Fix by moving the visible card styling (background, border, border-radius) onto `Popover.Content` itself (or a wrapper that exactly matches its box) in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` / `app/src/lib/components/SpeakerPopover.svelte`, so the scrolling element and the visually-bounded element are the same box and the native scrollbar renders flush inside the card. — **Reversibility:** reversible — a CSS/markup structure change local to these two files.
- Custom scrollbar styling (`::-webkit-scrollbar` / `scrollbar-width`/`scrollbar-color`) was considered but not selected — the structural fix (D-03) is sufficient; do not add custom scrollbar theming unless the structural fix alone still looks jarring during implementation.
- Must not regress: every field Phase 39 added to the popover must still render, unclipped and unescaped from the card (Success Criteria #5).

### Claude's Discretion
- Exact FastAPI mechanism for the 404 (raising `HTTPException(404, ...)` inline in the router vs. having the service functions return `None` for unpublished arguments so the existing "not found" branch handles it) — either is acceptable as long as the response is a plain 404 with no distinguishing detail between "doesn't exist" and "not published."
- Whether the SvelteKit `+page.server.ts` needs any change beyond what already happens when the API returns 404 (it already calls `error(res.status, ...)` on non-OK, which SvelteKit renders as its error page on both client-side nav and SSR refresh) — confirm during planning/implementation that no additional client-side gating is needed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### BUG-01 — publish gate
- `api/services/cases.py` — existing D-06 published_at gate pattern for the `/cases/` list; the argument-detail gate should follow the same `Argument.published_at.isnot(None)` filter convention.
- `api/tests/test_published_gate.py` — existing source-level tests asserting the `/cases/` gate uses `published_at` not `resolved_at`; a parallel test should be added for the argument-detail gate.
- `api/routers/arguments.py` — the two public endpoints to gate (`/arguments/{id}/utterances`, `/arguments/{id}/speakers`).
- `api/services/arguments.py` (`get_argument_with_utterances`) and `api/services/speakers.py` (`get_argument_speakers`) — where the gate logic likely belongs.
- `.planning/todos/pending/2026-07-28-unpublished-argument-visible-in-cases-list.md` — original defect report.

### BUG-02 — popover scrollbar
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` — owns `Popover.Content` with the current `max-height`/`overflow-y` styling.
- `app/src/lib/components/SpeakerPopover.svelte` — owns the visible card's background/border/border-radius on an inner element.
- `.planning/todos/pending/2026-07-29-popover-scrollbar-outside-card.md` — original defect report with diagnosed root cause.

No project-level ADR/PRD governs either bug specifically — ROADMAP.md's Phase 45 entry is the authoritative scope statement.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Argument.published_at.isnot(None)` filter pattern already proven in `api/services/cases.py` — reuse the same predicate for the detail-route gate.
- `api/tests/test_published_gate.py`'s source-level AST-assertion test style — reuse this style for the new argument-detail gate test rather than requiring a live DB.

### Established Patterns
- Public routers (`api/routers/arguments.py`, `api/routers/cases.py`) are fully separate from admin routers (`api/routers/admin.py`) and admin services (`api/services/admin_arguments.py`) — the publish gate belongs only in the public path.
- `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` already calls `error(res.status, ...)` on any non-OK API response, which SvelteKit renders identically on hard SSR refresh and client-side navigation — the existing error-boundary plumbing should already satisfy Success Criteria #2 once the API returns 404.

### Integration Points
- The argument-detail gate sits in `api/services/arguments.py` (`get_argument_with_utterances`) and `api/services/speakers.py` (`get_argument_speakers`), called from `api/routers/arguments.py`.
- The scrollbar fix sits entirely within `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` and `app/src/lib/components/SpeakerPopover.svelte` — no API changes.

</code_context>

<specifics>
## Specific Ideas

No specific visual/copy requirements beyond the diagnosed root causes — both bugs already have a clear technical description of the fix; discussion confirmed direction rather than introducing new specifics.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **Create-person popover should inherit row's side and auto-select the new person** (`.planning/todos/pending/2026-08-11-create-person-popover-side-and-selection.md`) — matched Phase 45 by keyword search (popover/app/svelte) but is unrelated to either BUG-01 or BUG-02 and is not in ROADMAP.md's Requirements (BUG-01, BUG-02) for this phase. Left pending for a future phase.

</deferred>

---

*Phase: 45-Deferred UI Bug Fixes*
*Context gathered: 2026-08-11*
