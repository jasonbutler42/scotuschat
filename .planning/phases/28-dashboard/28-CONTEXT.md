# Phase 28: Dashboard - Context

**Gathered:** 2026-07-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the placeholder `/admin/` page (currently just a header and "Select a tool from the navigation to get started" line) with an intentionally designed dashboard: 4 stat cards (Arguments, People, Utterances, Pipeline runs) each with an inline CTA, a "Needs attention" section surfacing real operator tasks (incomplete people, Justices with tenure gaps, draft arguments), and a "coming soon" web traffic placeholder card.

This phase does not touch any other admin screen's core functionality — it only adds read-aggregation queries and CTA links pointing at screens already built in Phases 24–27. It does not add any new filtering capability to those screens (see D-05 below — an integration gap was found and resolved by NOT extending `/admin/people`'s filter model).

</domain>

<decisions>
## Implementation Decisions

### Needs Attention Section
- **D-01:** Capped, not unbounded — each sub-list shows at most **5** items, with a "View all" link to the full filtered view on the relevant admin screen.
- **D-02:** Three separate labeled sub-lists by type — "People", "Justices", "Drafts" — not one interleaved feed. Matches how the admin already separates these concerns into distinct screens (People Admin, Arguments Admin).
- **D-03:** ALL draft arguments count as needing attention — no age threshold. A draft is inherently unfinished/needs-review regardless of how recently it was created.

### Stat Card CTA Destinations
- **D-04:** Arguments stat card: each status count (Published / Draft / Unpublished) is its own deep-link to `/admin/arguments` filtered to that status — not one card-level link. Draft's link doubles as the Needs Attention "Drafts" sub-list's "View all" target.
- **D-05 (integration gap, resolved):** Phase 27 (D-04 in `27-CONTEXT.md`) removed `/admin/people`'s generic "incomplete only" toggle entirely, replacing it with click-to-filter on ONE specific missing-field pill at a time. The dashboard's People stat card shows one aggregate number ("N people missing fields"), which doesn't map to any single pill. **Resolution: the People CTA lands on `/admin/people?tab=X` unfiltered** (bench or advocate tab, whichever the count refers to) — the operator sees the full tab with missing-field pills already rendered inline per-person (existing Phase 27 behavior) and clicks whichever pill they want themselves. **Do not add a new "any missing field" aggregate filter mode** — that would re-introduce the exact toggle Phase 27 deliberately removed.
- **D-06:** Same unfiltered-tab-landing pattern (D-05) applies to the "Justices with tenure gaps" Needs Attention sub-list's "View all" link — lands on `/admin/people?tab=bench&tenure_gaps=1`, reusing the existing `tenure_gaps` query param Phase 27 kept as-is (this one IS a real existing filter, unlike the missing-fields case).
- **D-07:** Pipeline runs stat card CTA links to the plain unfiltered `/admin/pipeline` list — no new filter state needed from the dashboard; the existing "incomplete only" toggle stays a manual operator choice on that screen.

### Visual Design
- **D-08:** No mockup/sketch pass for this phase — design directly from `.planning/codebase/DESIGN-SYSTEM.md` tokens and established admin card patterns (card bg `#1e293b`, borders `#334155`, primary text `#e2e8f0`, muted text `#94a3b8`). Unlike Phase 27, the operator did not want to sketch this one first.
- **D-09:** Page order, top to bottom: **Needs Attention section first**, stat card grid below it. Actionable items lead; overview numbers are supporting context. This directly serves DASH-05's "visual hierarchy guides the operator to the most urgent items."
- **D-10:** Stat cards stay visually neutral/uniform — no red/amber urgency color-coding on the cards themselves (e.g. the Arguments card does NOT turn amber because `draft_count > 0`). All urgency signaling lives in the Needs Attention section. Keeps the dashboard calm rather than alarming, consistent with the project's non-editorial, non-alarmist tone elsewhere.

### Web Traffic Placeholder Card (DASH-04)
- **D-11:** Bare labeled card — a "Web Traffic" title, a muted "Coming soon" label, optionally a small icon. No skeleton/fake chart shapes. Minimal effort now, nothing chart-shaped to later reconcile with real data.
- **D-12:** Visually set apart from the 4 real stat cards — not mixed into the same grid row as Arguments/People/Utterances/Pipeline (e.g. its own row below them, or a dashed border) so the operator never mistakes it for live data.

### Claude's Discretion
- Exact visual treatment distinguishing the placeholder card from real stat cards (D-12) — dashed border vs. separate row vs. reduced opacity — left to the planner/implementer, as long as it reads as clearly inactive.
- Exact icon (if any) on the Web Traffic placeholder card (D-11).
- Whether "People" in the Needs Attention list refers to Advocate-tab incomplete people, Bench-tab incomplete people, or both combined into one "People" sub-list — the stat card itself shows "People (total / incomplete)" as one aggregate per DASH-01, so this needs a concrete decision at planning/implementation time about whether Needs Attention's "People" sub-list spans both tabs or is itself split. Not discussed explicitly; left to the planner to resolve against DASH-01's aggregate framing (recommend: one combined "People" sub-list spanning both tabs, since the stat card itself doesn't split by tab either).
- Exact query/aggregation implementation for each stat count (e.g. whether "Utterances (total)" counts all utterances regardless of argument status, or only published-argument utterances) — no explicit user preference surfaced; follow the plain literal reading of DASH-01 ("Utterances: total") unless research turns up a reason to scope it.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope and Requirements
- `.planning/ROADMAP.md` — Phase 28 goal and success criteria (§ "Phase 28: Dashboard").
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-05 (this phase's requirements, all currently `Pending`).
- `.planning/codebase/DESIGN-SYSTEM.md` — Colors/typography/spacing reference; this phase's sole visual-design source per D-08 (no mockups this time).

### Prior Decisions (integration dependencies)
- `.planning/phases/27-people-admin/27-CONTEXT.md` — D-01 through D-06: the `?tab=` query param model and the click-to-filter-by-specific-pill replacement for the old generic "incomplete only" toggle. **Directly drives D-05/D-06 above** — the dashboard must NOT assume a generic incomplete filter exists on `/admin/people`.
- `.planning/phases/26-arguments-admin/26-CONTEXT.md` — Three-state (Draft/Published/Unpublished) `Argument.status` model that D-04's per-status deep-links filter against.
- `.planning/phases/25-pipeline-job-detail-page/25-CONTEXT.md` and `.planning/phases/24-pipeline-list-page/24-CONTEXT.md` — Establish the `/admin/pipeline` list page and its existing "incomplete only" toggle that D-07 deliberately leaves untouched.
- `.planning/phases/22-schema-foundations/22-CONTEXT.md` — `ArgumentStatusEnum` (PIPELINE/DRAFT/PUBLISHED/UNPUBLISHED) — Draft-only counts toward Arguments stat card breakdown and Needs Attention per D-03; PIPELINE-status arguments are pipeline-run scoped, not part of this phase's Arguments breakdown (consistent with Phase 26's list scoping).

### Existing Admin Root Page (this phase's main edit target)
- `app/src/routes/admin/+page.svelte` — Currently a placeholder: header + one line of static text ("Select a tool from the navigation to get started"). Full rewrite target.
- `app/src/routes/admin/+page.server.ts` — Currently only has a `logout` action, no `load` function at all. Needs a new `load()` aggregating all stat-card and Needs Attention data.

### Backend/API
- `api/services/admin_people.py` — `list_people()` (D-06's `tenure_gaps` param, existing and reusable as-is), `_missing_fields()` (per-tab missing-field logic — the counts behind the People stat card and Needs Attention "People" sub-list), `gap_person_ids_query` pattern (lines ~246+, reusable for the "Justices with tenure gaps" Needs Attention data).
- `api/services/admin_arguments.py` — `list_arguments()` (status filtering — the source for Arguments stat card breakdown and Draft Needs Attention data).
- `api/services/admin_jobs.py` — `list_jobs()` (source for Pipeline runs stat card's "recent count + last activity date" — no existing "recent" definition; planner/researcher must define what counts as recent, e.g. last N runs vs. last N days).
- `api/models/models.py` — `Argument.status`, `Person.is_justice`, `Utterance`, `AdminJob` — no new columns or migrations anticipated for this phase; this is a read-aggregation phase only.
- `api/routers/admin.py` — Existing `/people`, `/arguments`, `/pipeline` (jobs) routes this phase's dashboard `load()` will call into (directly via service functions, per the architecture rule that FastAPI/pipeline stay separate — but since dashboard queries run server-side in SvelteKit's `+page.server.ts` calling FastAPI endpoints, or whether this phase adds a new aggregate `/admin/dashboard` FastAPI endpoint, is an open implementation question for the researcher/planner — no existing precedent for a single aggregate endpoint spanning people+arguments+pipeline+utterances).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `admin_people._missing_fields()` and its per-tab branching (is_justice) — direct source for both the People stat card's incomplete count and the Needs Attention "People" sub-list rows.
- `admin_people.gap_person_ids_query` (lines ~246-263 in `api/services/admin_people.py`) — direct source for the "Justices with tenure gaps" Needs Attention sub-list; already computes exactly this set for the existing `tenure_gaps=1` filter.
- `admin_arguments.list_arguments()`'s status filtering — direct source for the Arguments stat card's total/published/draft/unpublished breakdown.
- Every existing admin page's inline dark-theme card CSS (`#1e293b` bg / `#334155` border / `#e2e8f0` text / `#94a3b8` muted) — the styling foundation for the new stat cards; no shared `StatCard`/`Card` Svelte component exists yet in `app/src/lib/components/` — each admin page currently rolls its own inline card markup, so the planner should decide whether this phase introduces the first shared card component or continues the existing per-page inline pattern.

### Established Patterns
- Svelte 5 Runes only: `$props`, `$state`, `$derived`, `$effect`; no legacy `export let` or `$:` blocks.
- `?tab=`, `?tenure_gaps=1` query-param patterns on `/admin/people` (Phase 27) — the exact link-target shapes for D-05/D-06's CTAs.
- SvelteKit server `load()` functions call FastAPI via `FASTAPI_BASE_URL` (server-only env var) — never `PUBLIC_`, per project Architecture Rule 2.

### Integration Points — Gaps Found During Scouting (not user decisions — planner must address)
- No `load()` function exists at all on `/admin/+page.server.ts` today — this phase adds one from scratch.
- No aggregate "dashboard" backend endpoint or service function exists — planner must decide: one new FastAPI endpoint aggregating all 4 stat categories in one round trip, vs. the SvelteKit `load()` calling multiple existing/new FastAPI endpoints in parallel. Architecture Rule 1 ("FastAPI is read-only") is satisfied either way; this is purely a request-shape decision.
- "Recent" pipeline runs count (DASH-01's "Pipeline runs (recent count + last activity date)") has no existing definition in the codebase — `admin_jobs.list_jobs()` currently returns ALL jobs with no time-windowing (Phase 24, PLIST-03, explicitly removed pagination/limits). Planner/researcher must define a concrete "recent" window (e.g. last 10 runs, or last 30 days) since this wasn't discussed and has no precedent to reuse.

</code_context>

<specifics>
## Specific Ideas

- The operator wants the dashboard to feel calm and task-oriented, not alarming — explicitly rejected color-urgency-coding on stat cards (D-10) in favor of keeping all urgency signaling contained to the Needs Attention section.
- No mockups this time (contrast with Phase 27) — explicit operator choice to let Claude design from the existing system directly (D-08).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- **Edit affordance on utterances and speaker popover** (`.planning/todos/pending/2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md`) — Surfaced as a possible match by automated todo-cross-referencing, but it's about adding an operator edit affordance to the public-facing argument page, unrelated to the `/admin/` dashboard. Operator confirmed: leave in backlog, do not fold into Phase 28.

</deferred>

---

*Phase: 28-Dashboard*
*Context gathered: 2026-07-09*
