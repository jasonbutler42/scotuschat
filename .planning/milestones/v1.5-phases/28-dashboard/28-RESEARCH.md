# Phase 28: Dashboard - Research

**Researched:** 2026-07-10
**Domain:** SvelteKit `load()` aggregation over an existing FastAPI/SQLAlchemy admin API (internal codebase research — no new external libraries)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Capped, not unbounded — each Needs Attention sub-list shows at most **5** items, with a "View all" link to the full filtered view on the relevant admin screen.
- **D-02:** Three separate labeled sub-lists by type — "People", "Justices", "Drafts" — not one interleaved feed.
- **D-03:** ALL draft arguments count as needing attention — no age threshold.
- **D-04:** Arguments stat card: each status count (Published / Draft / Unpublished) is its own deep-link to `/admin/arguments` filtered to that status — not one card-level link. Draft's link doubles as the Needs Attention "Drafts" sub-list's "View all" target.
- **D-05 (integration gap, resolved):** The dashboard's People stat card shows one aggregate number ("N people missing fields"). Resolution: the People CTA lands on `/admin/people?tab=X` unfiltered (bench or advocate tab, whichever the count refers to) — operator clicks the specific missing-field pill themselves. Do NOT add a new "any missing field" aggregate filter mode.
- **D-06:** Same unfiltered-tab-landing pattern applies to the "Justices with tenure gaps" Needs Attention sub-list's "View all" link — lands on `/admin/people?tab=bench&tenure_gaps=1`, reusing the existing `tenure_gaps` query param.
- **D-07:** Pipeline runs stat card CTA links to the plain unfiltered `/admin/pipeline` list — no new filter state needed from the dashboard.
- **D-08:** No mockup/sketch pass for this phase — design directly from `.planning/codebase/DESIGN-SYSTEM.md` tokens and established admin card patterns.
- **D-09:** Page order, top to bottom: Needs Attention section first, stat card grid below it.
- **D-10:** Stat cards stay visually neutral/uniform — no red/amber urgency color-coding on the cards themselves. All urgency signaling lives in the Needs Attention section.
- **D-11:** Web Traffic placeholder: bare labeled card — a "Web Traffic" title, a muted "Coming soon" label, optionally a small icon. No skeleton/fake chart shapes.
- **D-12:** Web Traffic placeholder visually set apart from the 4 real stat cards — not mixed into the same grid row.

### Claude's Discretion

- Exact visual treatment distinguishing the placeholder card from real stat cards (D-12) — dashed border vs. separate row vs. reduced opacity.
- Exact icon (if any) on the Web Traffic placeholder card (D-11).
- Whether "People" in the Needs Attention list refers to Advocate-tab incomplete people, Bench-tab incomplete people, or both combined — recommend one combined "People" sub-list spanning both tabs, since the stat card itself doesn't split by tab either.
- Exact query/aggregation implementation for each stat count (e.g. whether "Utterances (total)" counts all utterances regardless of argument status) — follow the plain literal reading of DASH-01 ("Utterances: total") unless research turns up a reason to scope it. (Research found no such reason — see Standard Stack below.)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope. One reviewed todo (edit affordance on utterances/speaker popover) was confirmed out of scope for this phase.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Stat cards: Arguments (total/published/draft/unpublished), People (total/incomplete), Utterances (total), Pipeline runs (recent + last activity) | See "New Aggregation Queries Needed" and "Pitfall: Corpus-Scale Row Counts" — dedicated COUNT-based queries required, not full-row `list_*` reuse |
| DASH-02 | Each stat card includes an inline actionable CTA | See "Component Responsibilities" — CTA hrefs are fully pre-computed server-side, no client-side URL building beyond existing `?tab=`/`?status=` idioms |
| DASH-03 | "Needs attention" section: incomplete people, tenure-gap Justices, draft arguments; excludes intentionally-unpublished arguments | See "Reusable Service Functions" — `list_people(is_justice=True, tenure_gaps=True)` and a new drafts-only query satisfy this directly; UNPUBLISHED is a distinct enum value already excluded by construction |
| DASH-04 | Web traffic placeholder card ("coming soon") | See "Pattern 3: Placeholder Card" |
| DASH-05 | Intentional visual design, not a generic table dump | See "Recommended Project Structure" (shared `StatCard.svelte`) and D-09/D-10/D-12 above |

</phase_requirements>

## Summary

This phase is pure internal-codebase composition work — no new external libraries, no new database migrations, and no new query patterns beyond what Phases 22–27 already established. The two things that matter for planning quality are (1) following the codebase's own precedent for how a SvelteKit `load()` assembles data from multiple FastAPI sources, and (2) recognizing that this project's data scale changed materially in Phases 29–30 (the historical ConvoKit corpus import added ~7,800 potential argument rows and a matching `AdminJob` per argument), which makes naive reuse of the existing `list_people()` / `list_arguments()` / `list_jobs()` functions for dashboard aggregation the wrong choice — those functions return full row sets with no LIMIT, which is fine for their existing table-driven UIs but wasteful for a dashboard that only needs counts and top-5 slices.

Every existing multi-source `+page.server.ts` in this codebase (most clearly `admin/pipeline/[job_id]/+page.server.ts`) fetches from several **separate, already-existing, resource-scoped** FastAPI endpoints with **sequential `await`s**, each independently wrapped in its own try/catch that degrades to a safe default on failure. There is no `Promise.all` anywhere in the codebase, and no precedent for one FastAPI endpoint that internally composes multiple unrelated resources (people + arguments + jobs + utterances) into a single response. The dashboard's `load()` should follow this exact precedent: add a small number of new, narrowly-scoped, count/limit-based FastAPI endpoints (one per existing resource area: arguments, people, jobs, plus a tiny utterances count), and call them sequentially from `/admin/+page.server.ts`'s new `load()`, matching the established degrade-gracefully idiom.

**Primary recommendation:** Add dedicated lightweight stats/aggregate service functions and endpoints under each existing resource's section of `api/services/admin_*.py` / `api/routers/admin.py` (not one new mega-endpoint), call them sequentially (not `Promise.all`) from a new `load()` in `admin/+page.server.ts`, and introduce the project's first shared Svelte component (`StatCard.svelte`) since this phase is the first place 4+ structurally-identical cards appear on one page.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stat counts (Arguments/People/Utterances/Pipeline) | API / Backend (new SQL COUNT queries) | Frontend Server (SSR `load()` composes the 3-4 calls) | Counting thousands of rows must happen in Postgres, not by fetching full row sets into SvelteKit and counting in JS (Architecture Rule 1: FastAPI is read-only, but that doesn't mean "return everything") |
| Needs Attention top-5 lists | API / Backend (LIMIT 5 queries, reusing/extending `admin_people.list_people` and a new drafts query) | — | Same reasoning — bounded queries, not client-side `.slice(0, 5)` on a full fetched array |
| CTA href construction | Frontend Server (`+page.server.ts` load, computed once) | Browser (plain `<a href>`, no client JS routing) | Matches every existing admin page — hrefs are plain strings built server-side from already-established `?tab=`/`?missing=`/`?tenure_gaps=1` query param contracts (Phase 27) |
| Visual layout / StatCard rendering | Browser (Svelte component) | — | Presentation only; no new client-side state beyond what any other admin page uses |
| Auth on new endpoints | API / Backend (inherited router-level `verify_admin_token` dependency) | — | No new auth surface — every route under `/api/admin` prefix already requires `X-Admin-Token`/session auth by construction |

## Standard Stack

This phase introduces **no new external packages**. It is composed entirely from the project's existing, already-installed stack:

### Core (existing, reused as-is)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit | ^2.21.0 [VERIFIED: app/package.json] | `+page.server.ts` `load()` composing FastAPI calls | Already the sole pattern for every admin page |
| Svelte | ^5.30.0 [VERIFIED: app/package.json] | Runes-only components (`$props`, `$state`, `$derived`) | CLAUDE.md hard constraint — no legacy stores |
| FastAPI | 0.115+ [CITED: CLAUDE.md] | New stats endpoints under `/api/admin` | Existing router, existing auth dependency |
| SQLAlchemy 2.0 async | [CITED: CLAUDE.md] | New `func.count()`/`func.max()` aggregate queries | Existing session/engine setup, no new config |
| Pydantic v2 | [CITED: CLAUDE.md] | New response schemas (`api/schemas/admin_dashboard.py`) | Matches every existing schema file's `BaseModel` + `from_attributes` pattern |

### Supporting
None — no icon library, no charting library, no state-management library is needed. `DESIGN-SYSTEM.md` [CITED: .planning/codebase/DESIGN-SYSTEM.md] explicitly documents "no component library or icon library — every element is plain HTML with inline styles" as the established convention; this phase should not be the one to introduce Tailwind (present in `package.json` as a devDependency but, per DESIGN-SYSTEM.md, not actually used anywhere in the admin UI) or an icon package for one placeholder card. If D-11's "small icon" is wanted on the Web Traffic card, use a single inline `<svg>` (no dependency).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sequential `await` fetches in `load()` | `Promise.all([...])` for parallel fetches | Faster (parallel round-trips) but **zero precedent** in this codebase — every existing multi-fetch `load()` (pipeline/[job_id]) uses sequential awaits with independent try/catch degradation. Introducing `Promise.all` here would be a new pattern for a phase whose CONTEXT.md explicitly says "does not add any new filtering capability" and should stay low-risk. Sequential is marginally slower (a handful of small internal HTTP round-trips) but consistent. |
| One new aggregate `GET /admin/dashboard` FastAPI endpoint | 3-4 small resource-scoped stats endpoints | An aggregate endpoint is architecturally valid (Rule 1 only requires FastAPI stay read-only) but has no precedent — every existing FastAPI router endpoint is scoped to one resource (jobs, people, arguments). Small scoped endpoints keep the new code discoverable inside the existing `admin_people.py`/`admin_arguments.py`/`admin_jobs.py` service files rather than inventing a new cross-cutting module that has to import from all three. |
| Reusing `list_people()`/`list_arguments()`/`list_jobs()` as-is and counting/slicing in Python | New dedicated `COUNT()`/`LIMIT 5` queries | `list_arguments()` and `list_people()` currently return **every** row with no limit (Phase 24 PLIST-03 explicitly removed pagination from `list_jobs()` for the same reason people list has none). Post-Phase-29/30, `arguments` and `people` tables can hold thousands of historical-corpus rows. Fetching all of them into SvelteKit just to `.filter().length` or `.slice(0,5)` is wasteful and will get slower as the corpus-resolve backlog (Phase 30) processes more rows into `draft`/`published` over time. |

**Installation:** None — no new packages.

**Version verification:** Not applicable — no new packages installed this phase.

## Package Legitimacy Audit

Not applicable. This phase adds no new npm/pip/cargo packages — it is entirely new Python service/router functions, new Pydantic schemas, and new Svelte components built from the existing stack.

## Architecture Patterns

### System Architecture Diagram

```
Operator loads /admin/
        │
        ▼
+page.server.ts  load()                         (SvelteKit server, FASTAPI_BASE_URL)
        │
        ├─▶ await fetch  GET /api/admin/arguments/stats   ──▶ admin_arguments.get_argument_stats()
        │        (total/published/draft/unpublished counts   admin_arguments.get_recent_drafts(limit=5)
        │         + top-5 draft rows, ordered by id DESC)     [COUNT + LIMIT queries only]
        │
        ├─▶ await fetch  GET /api/admin/people/stats       ──▶ admin_people.get_people_stats()
        │        (total/incomplete counts + top-5             reuses list_people(missing=None) filtered
        │         incomplete rows + top-5 tenure-gap rows)     to non-empty `missing`, and
        │                                                      list_people(is_justice=True, tenure_gaps=True)
        │
        ├─▶ await fetch  GET /api/admin/jobs/stats         ──▶ admin_jobs.get_pipeline_stats()
        │        (recent_count over last 30 days,              COUNT(created_at >= now()-30d),
        │         last_activity_at)                             MAX(updated_at)
        │
        └─▶ await fetch  GET /api/admin/utterances/count   ──▶ new tiny count query (or folded
                 (total utterance rows)                          into arguments/stats response)
        │
        ▼
Each fetch: try/catch, non-OK or thrown error → safe zero-value default
(mirrors admin/pipeline/[job_id]/+page.server.ts's established pattern)
        │
        ▼
return { statCards, needsAttention } to +page.svelte
        │
        ▼
+page.svelte renders: Needs Attention section (top), then StatCard grid (below), then
Web Traffic placeholder card in its own row (D-09/D-12)
```

### Recommended Project Structure
```
api/
├── services/
│   ├── admin_arguments.py   # add: get_argument_stats(), get_recent_drafts()
│   ├── admin_people.py      # add: get_people_stats(), get_incomplete_people(), get_tenure_gap_justices()
│   └── admin_jobs.py        # add: get_pipeline_stats()
├── schemas/
│   └── admin_dashboard.py   # NEW — ArgumentStats, PeopleStats, PipelineStats, response shapes
├── routers/
│   └── admin.py             # add: GET /arguments/stats, GET /people/stats, GET /jobs/stats,
│                             #      GET /utterances/count (each registered BEFORE its sibling
│                             #      {id}-parameterized route — see Pitfall below)
app/src/
├── routes/admin/
│   ├── +page.server.ts      # rewritten: new load() with 4 sequential fetches
│   └── +page.svelte         # rewritten: Needs Attention section + StatCard grid + placeholder
└── lib/components/
    └── StatCard.svelte      # NEW — first shared admin card component (see Pattern 2 below)
```

### Pattern 1: Sequential degrade-gracefully `load()` (established precedent)
**What:** Each data source gets its own `try { ... } catch { ...safe default... }` block; failures never throw and never block the other fetches.
**When to use:** Any `load()` needing 2+ independent FastAPI calls.
**Example:**
```typescript
// Source: app/src/routes/admin/pipeline/[job_id]/+page.server.ts (existing code, lines 82-98)
let people: Array<{ id: number; full_name: string; role_name: string | null }> = [];
let peopleLoadError: string | null = null;
try {
	const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {
		headers: { 'X-Admin-Token': ADMIN_TOKEN },
	});
	if (peopleRes.ok) {
		people = await peopleRes.json();
	} else {
		peopleLoadError = `GET /api/admin/people returned ${peopleRes.status}`;
	}
} catch (err) {
	peopleLoadError = err instanceof Error ? err.message : String(err);
}
```
Apply this exact shape 3-4 times in the new dashboard `load()`, one block per stats endpoint, each defaulting to `{ total: 0, ... }` / `[]` on failure so the dashboard always renders (never a hard `error()` throw — this is a landing page, not a detail page with a 404 concept).

### Pattern 2: New shared `StatCard.svelte` component
**What:** A single Svelte 5 runes component accepting `title`, a value/breakdown slot, and CTA link(s) as props, rendering the established card CSS (`background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;` per DESIGN-SYSTEM.md).
**When to use:** This phase is the first time 4+ structurally-identical cards appear on one admin page (Arguments/People/Utterances/Pipeline, plus the differently-styled placeholder). Every other admin page has at most one or two visually-distinct cards, which is why no shared card component exists yet — introducing one now is a net simplification, not a new-pattern risk, since it still uses inline `style` attributes internally (no Tailwind, no component library — stays within the documented convention).
**Example shape:**
```svelte
<!-- app/src/lib/components/StatCard.svelte — new, Svelte 5 runes only -->
<script lang="ts">
	let { title, children } = $props();
</script>
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">{title}</h2>
	{@render children()}
</div>
```
Each stat card's internal breakdown (per-status counts + per-status CTA links, per D-04) is passed as the `children` snippet from `+page.svelte`, since the breakdown shape differs per card (Arguments has 3 sub-counts with individual links; Utterances has just one number).

### Pattern 3: Placeholder Card (DASH-04, D-11, D-12)
**What:** A visually-distinct, non-interactive card with no data-fetch at all.
**When to use:** Web Traffic card only.
**Example:**
```svelte
<div style="border: 1px dashed #334155; border-radius: 8px; padding: 24px; margin-top: 16px; opacity: 0.7;">
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 8px 0;">Web Traffic</h2>
	<p style="font-size: 14px; color: #94a3b8; margin: 0;">Coming soon</p>
</div>
```
Dashed border + its own row below the stat grid + `opacity: 0.7` together satisfy D-12's "never mistaken for live data" bar without inventing new visual language.

### Anti-Patterns to Avoid
- **Reusing `list_arguments()`/`list_people()`/`list_jobs()` unmodified for dashboard counts:** These return every row with no LIMIT (Phase 24 PLIST-03 explicitly removed pagination site-wide). At corpus-import scale (thousands of historical rows, Phase 29/30), fetching the whole table to compute a count or take the first 5 is a real, measurable performance regression the existing table-driven pages don't have (those pages are meant to show everything; the dashboard is not).
- **`Promise.all` in `load()`:** Not wrong per se, but has zero precedent in this codebase and isn't needed at this data volume (4 small internal HTTP calls).
- **One mega aggregate FastAPI endpoint:** Possible, but breaks the router's existing per-resource organization and would need to import all three service modules into one new cross-cutting function — the resource-scoped alternative (small stats function living inside each existing `admin_*.py` service file) is simpler review-wise and matches how every other feature in this codebase has been added, phase over phase.
- **Color-coding stat cards by urgency:** Explicitly rejected by D-10 — do not add conditional amber/red styling to the 4 real stat cards based on their counts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "N people with at least one missing field" | A new SQL "any missing field" filter mode on `list_people()` | Call `list_people(db, is_justice=None)` (both tabs, no filter) once, then filter server-side (Python) for rows where `len(row["missing"]) > 0` | D-05 explicitly forbids reintroducing a generic "incomplete" toggle at the API filter level (Phase 27 removed it on purpose) — but nothing stops a NEW dashboard-only aggregation function from calling the unfiltered list and counting in Python, since `list_people()` without a tab filter is not the removed toggle, it's the existing full-directory query with no new SQL surface |
| "Justices with tenure gaps" top-5 | A new standalone reusable version of the `gap_person_ids_query` subquery (CONTEXT.md describes this as reusable at "lines ~246-263") | Call `admin_people.list_people(db, is_justice=True, tenure_gaps=True)` directly and take the first 5 rows | **Correction to CONTEXT.md's framing:** `gap_person_ids_query` is a *local variable* built fresh inside `list_people()`'s function body (api/services/admin_people.py:246-261) — it is not an importable/exported symbol and cannot be reused directly by a new function without either duplicating the subquery or refactoring it out first. `list_people()` itself, however, already accepts `tenure_gaps=True` and returns exactly the rows needed (full_name, id, etc.) — calling the existing public function is simpler than extracting the private subquery |
| "Recent" pipeline activity | A new pagination/windowing UI | A simple `COUNT(*) WHERE created_at >= now() - interval '30 days'` plus `MAX(updated_at)` for last-activity — see Open Questions below for the exact recommendation | `AdminJob` already has both `created_at` (server_default now()) and `updated_at` (onupdate now()) — no new column, no new index needed for a table of this size |

**Key insight:** Every piece of data this dashboard needs already has an existing, correct source function or column — the only genuinely new code is a thin COUNT/LIMIT layer on top, plus glue.

## Common Pitfalls

### Pitfall 1: Route-ordering collision on new `/stats` sub-routes
**What goes wrong:** `GET /api/admin/arguments/{argument_id}` is registered with a bare `int` Python type hint but NO `:int` path converter in the route string (`@router.get("/arguments/{argument_id}", ...)`). Starlette/FastAPI route matching tries registered routes **in order**; if a new `GET /arguments/stats` route is registered *after* `/arguments/{argument_id}`, the string `"stats"` will match the `{argument_id}` template first (routing matches by segment presence, not by type — type coercion/validation happens only after a route matches), producing a confusing 422 instead of hitting the new stats endpoint.
**Why it happens:** This exact bug class is already documented and guarded against in this codebase — see `GET /arguments/check-duplicate`'s comment: *"CRITICAL ordering note (T-19-03-05): this literal route MUST be registered before GET /arguments/{argument_id}"* (api/routers/admin.py line ~869).
**How to avoid:** Register every new `/stats`-style literal sub-route (`/arguments/stats`, `/people/stats`, `/jobs/stats`) **before** its sibling `{id}`-parameterized route in `admin.py`, exactly like `check-duplicate` already does.
**Warning signs:** A 422 "value is not a valid integer" error when calling the new stats endpoint.

### Pitfall 2: Corpus-scale row counts silently degrading dashboard performance
**What goes wrong:** Phase 29 (Historical Corpus Import) added up to ~7,800 potential `Argument` rows (terms 1955–2019) and Phase 30 pairs each with an `AdminJob` row. `list_arguments()`, `list_people()`, and `list_jobs()` all return every matching row with no LIMIT (by explicit prior design — PLIST-03). If the dashboard's new stats functions call these unmodified and count/slice in Python, every dashboard page load fetches thousands of rows just to produce 4 numbers and three 5-item lists.
**Why it happens:** These functions were designed for their own table-driven admin pages, which are supposed to show everything. The dashboard has a fundamentally different access pattern (aggregate, not enumerate).
**How to avoid:** Write dedicated `func.count()` / `func.max()` / `LIMIT 5` queries for every new dashboard stat. Only `list_people(is_justice=True, tenure_gaps=True)` is safe to reuse as-is (Justices are a small, bounded subset; still take `[:5]` from its result rather than assuming the caller must always slice).
**Warning signs:** Dashboard load time visibly correlates with total `arguments`/`people` row count as the Phase 30 corpus-resolve backlog is worked through over time.

### Pitfall 3: `Argument` has no creation timestamp — the existing "Created" column is mislabeled
**What goes wrong:** `api/models/models.py`'s `Argument` table [VERIFIED: api/models/models.py lines 180-226] has **no `created_at` column at all**. The existing `/admin/arguments` list page's table header literally says "Created" (ALIST-04), but its data cell renders `arg.resolved_at`, not a creation timestamp [VERIFIED: app/src/routes/admin/arguments/+page.svelte line 188]. A planner assuming "sort the Drafts Needs Attention list by created date" will find no such column to sort by.
**Why it happens:** Pre-existing labeling inconsistency from Phase 26, out of this phase's scope to fix.
**How to avoid:** For the "Drafts" Needs Attention sub-list ordering, use `Argument.id DESC` (auto-increment PK is a reliable insertion-order proxy) rather than inventing a fake "created" sort key. Do not silently reuse `resolved_at` for this purpose either — a resolved-but-still-draft argument's `resolved_at` reflects when the *pipeline resolve step* finished, not when it became a draft (those can be the same moment for PDF ingests but are decoupled for corpus-approved arguments going through Phase 30's resolve workflow).
**Warning signs:** None visible until an operator asks "why isn't the newest draft at the top" and the ordering turns out to be arbitrary.

### Pitfall 4: `Utterance` is a `BigInteger` PK table meant to scale to millions of rows
**What goes wrong:** A naive `SELECT COUNT(*) FROM utterances` performs a full sequential scan in PostgreSQL (no covering index makes COUNT(*) free). At the current and near-term expected row count (low millions per the model's own docstring: "could accumulate millions of rows over many arguments" [VERIFIED: api/models/models.py line 313]) this is still likely sub-second, but it is worth a deliberate choice, not an accident.
**Why it happens:** COUNT(*) is the obvious first implementation.
**How to avoid:** For this phase, a plain `COUNT(*)` is acceptable (dashboard is loaded infrequently, not on every request) — do not over-engineer with `pg_class.reltuples` approximation unless a future phase's real-world load times prove it necessary. Just make the choice explicit in the plan rather than silent.
**Warning signs:** Dashboard load time regressing noticeably once utterance count crosses several million rows.

## Code Examples

### Reusable service function signatures confirmed by direct read (not assumed)
```python
# api/services/admin_people.py
async def list_people(
    db: AsyncSession,
    is_justice: bool | None = None,
    missing: str | None = None,
    tenure_gaps: bool = False,
) -> list[dict]:
    # Returns: [{id, full_name, missing: list[str], is_justice, argument_count, tenure_coverage, has_tenure_gap}, ...]
    # No LIMIT — caller must slice for top-5 use cases.

# api/services/admin_arguments.py
async def list_arguments(db: AsyncSession) -> list[dict]:
    # Returns: [{id, argued_date, case_name, docket_number, resolved_at, published_at, status}, ...]
    # Already filters OUT PIPELINE-status rows (ALIST-02) — only DRAFT/PUBLISHED/UNPUBLISHED returned.
    # No LIMIT, no status filter param today — a dashboard-only drafts query needs its own
    # WHERE status = 'draft' ORDER BY id DESC LIMIT 5, not a filtered call to this function.

# api/services/admin_jobs.py
async def list_jobs(db: AsyncSession, incomplete: bool = False) -> list[AdminJob]:
    # Returns ORM AdminJob objects (not dicts) with is_archived/source/parse_stats injected
    # onto __dict__. AdminJob.created_at and AdminJob.updated_at both exist and are non-null
    # (server_default=func.now(), onupdate=func.now()) — safe aggregation targets.
```

### Confirmed enum values (V5 correctness for filter predicates)
```python
# api/models/models.py
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"      # excluded from all admin Arguments-list views (ALIST-02)
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"  # distinct from draft — DASH-03 excludes this from Needs Attention
                                  # by construction: filtering status == DRAFT already excludes it.

class Person:
    is_justice: bool  # Boolean, nullable=False, server_default=false()
```

### Existing FastAPI ordering-safe route registration precedent
```python
# api/routers/admin.py — literal route registered BEFORE its {id}-parameterized sibling
@router.get("/arguments/check-duplicate")
async def check_duplicate_argument(docket: str, question: int, ...): ...

@router.get("/arguments/{argument_id}", response_model=ArgumentDetail)
async def get_argument(argument_id: int, ...): ...
# New /arguments/stats route must follow this exact ordering discipline.
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Recent" pipeline activity window = last 30 days (COUNT), with "last activity date" = `MAX(AdminJob.updated_at)` unbounded by that window | Don't Hand-Roll / Architecture Diagram | No user decision exists for this — CONTEXT.md explicitly flags it as unresolved. If the operator's mental model of "recent" differs (e.g. "last 10 runs" instead of a day-window), the stat card's number reads oddly, but this is a display-only, easily-adjusted constant with no schema impact. Low risk. |
| A2 | "Drafts" Needs Attention ordering = `Argument.id DESC` (insertion-order proxy) since no real created-at timestamp exists on `Argument` | Pitfall 3 | If a future migration adds a real `Argument.created_at` column, this ordering should be revisited; until then `id DESC` is the only reliable proxy — low risk, easily changed later since it's a single ORDER BY clause. |
| A3 | Utterances (total) counts ALL utterance rows regardless of the parent argument's status (draft/published/unpublished/pipeline) | Standard Stack, Code Examples | CONTEXT.md's own discretion note flags this as unscoped; a literal reading of DASH-01 ("Utterances: total") supports counting everything. If the operator actually wants only published-argument utterances, this is a one-line WHERE-clause change with no schema impact. |
| A4 | A single inline `<svg>` icon (no icon library) is an acceptable D-11 "small icon" implementation | Pattern 3 | DESIGN-SYSTEM.md documents zero icon library usage anywhere in the admin UI today; introducing one for a single decorative icon on a placeholder card would be a disproportionate new dependency. Very low risk — D-11 explicitly marks the icon itself as optional. |

## Open Questions

1. **Exact "recent" pipeline-run window (30 days vs. some other N)**
   - What we know: `AdminJob.created_at`/`updated_at` both exist and are reliable; no existing UI concept of a "recent" window exists anywhere else in the codebase to borrow from (Phase 24 explicitly removed all pagination/limiting from the jobs list).
   - What's unclear: Whether 30 days is the right window for an admin tool with irregular, bursty activity (a bulk corpus-import batch can create many jobs in one sitting, then nothing for weeks).
   - Recommendation: Use 30 days as the count window (a broadly-understood dashboard convention) and always show `last_activity_at` unbounded by that window (so "last activity: 45 days ago" is still meaningful even when the 30-day count is 0). Treat this as an easy-to-change constant, not a locked architectural decision — flag it to the operator during `/gsd-plan-phase` or `/gsd-verify-work` if a stronger opinion emerges.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No (new code) | Inherited — no new auth surface; all new routes sit under the existing `/api/admin` prefix with router-level `verify_admin_token` dependency |
| V3 Session Management | No (new code) | Inherited — SvelteKit session cookie auth (Phase 6) already gates all of `/admin/*` via `hooks.server.ts`; this phase adds no new session logic |
| V4 Access Control | Yes, trivially | All new stats endpoints return aggregate/global data (not scoped to any client-supplied resource id), so there is no IDOR surface to guard — no per-row ownership check is needed because nothing is fetched by client-supplied id |
| V5 Input Validation | Yes, minimally | New endpoints take no new query params beyond possibly a `?days=` override (not required — a fixed 30-day server-side constant needs no input validation at all) |
| V6 Cryptography | No | Not applicable — no new secrets, tokens, or crypto operations |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unbounded query DoS (fetching entire `arguments`/`people`/`admin_jobs` tables just to compute a dashboard number) | Denial of Service | Use `func.count()`/`LIMIT` at the SQL layer for every new dashboard aggregation (Pitfall 2 above) — never reuse the existing unbounded `list_*` functions verbatim for counting |
| Route-shadowing (new literal `/stats` route silently swallowed by an existing `{id}` route) | — (correctness, not a STRIDE category, but a real production bug class already documented in this codebase) | Register literal sub-routes before their `{id}`-parameterized siblings (Pitfall 1) |

No new PII, no new PCI-relevant data, and no new financial/regulatory data is introduced by this phase — it aggregates counts over data that is already exposed via existing, already-authenticated admin endpoints.

## Sources

### Primary (HIGH confidence — direct codebase reads this session)
- `app/src/routes/admin/+page.svelte`, `+page.server.ts` — current placeholder state, confirmed empty `load()`
- `app/src/routes/admin/{arguments,people,pipeline}/+page.server.ts` and `[id]`/`[job_id]` variants — confirmed the sequential-await, no-`Promise.all`, per-call try/catch precedent
- `api/services/admin_people.py`, `admin_arguments.py`, `admin_jobs.py` — confirmed exact function signatures, `gap_person_ids_query`'s local-variable (non-exported) status, `list_jobs()`'s no-LIMIT behavior
- `api/models/models.py` — confirmed `ArgumentStatusEnum` values, `Person.is_justice` type, absence of `Argument.created_at`, presence of `AdminJob.created_at`/`updated_at`
- `api/routers/admin.py` — confirmed router-level auth dependency, confirmed the literal-route-before-`{id}`-route ordering precedent (`check-duplicate`)
- `api/schemas/admin_people.py`, `admin_arguments.py`, `admin_jobs.py` — confirmed exact Pydantic response shapes
- `.planning/codebase/DESIGN-SYSTEM.md` — confirmed color/spacing tokens and the "no component library" convention
- `.planning/STATE.md` — confirmed Phase 29/30 historical corpus import scale (~7,800 arguments) and its `AdminJob` pairing (Phase 30-01), which drives the corpus-scale pitfall finding
- `app/package.json` — confirmed no icon library, Tailwind present but unused per DESIGN-SYSTEM.md

### Secondary (MEDIUM confidence)
None — this research required no external documentation lookups; everything needed was already present in this project's own codebase and planning artifacts.

### Tertiary (LOW confidence)
None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, every claim verified against actual project files this session
- Architecture: HIGH — the sequential-await/no-mega-endpoint recommendation is directly derived from reading every comparable existing `+page.server.ts` in the codebase, not inferred from general SvelteKit best practice
- Pitfalls: HIGH — all four pitfalls are backed by direct file reads (route ordering precedent, missing `created_at` column, corpus-import scale from STATE.md, BigInteger PK comment)

**Research date:** 2026-07-10
**Valid until:** 30 days (stable internal codebase; only invalidated by an unrelated Phase touching `admin_people.py`/`admin_arguments.py`/`admin_jobs.py` schemas before Phase 28 executes)
