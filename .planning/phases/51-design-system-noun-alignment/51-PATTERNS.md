# Phase 51: Design System & Noun Alignment - Pattern Map

**Mapped:** 2026-08-27
**Files analyzed:** ~30 (routes, components, primitives, API, migration, docs)
**Analogs found:** 26 / 30

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/src/routes/arguments/+page.svelte` (term index, D-14) | route/component | request-response | `app/src/routes/cases/+page.svelte` | exact (renamed same-shape list page) |
| `app/src/routes/arguments/+page.server.ts` | route (server load) | request-response | `app/src/routes/cases/+page.server.ts` | exact |
| `app/src/routes/arguments/term/[year]/+page.svelte` | route/component | request-response | `app/src/routes/cases/+page.svelte` | role-match (list page, new grouping) |
| `app/src/routes/arguments/term/[year]/+page.server.ts` | route (server load) | request-response | `app/src/routes/cases/[slug]/+page.server.ts` | role-match (param-driven load + 404) |
| `app/src/routes/arguments/[slug]/+page.svelte` | route/component | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | exact (this IS the transcript page, D-09 keeps it, just relocated) |
| `app/src/routes/arguments/[slug]/+page.server.ts` | route (server load) | request-response | `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | exact |
| Deleted: `app/src/routes/cases/**` (6 files) | route | n/a | — | removed per D-10, no redirect (D-11) |
| `app/src/lib/primitives/Button.svelte` | component (primitive) | request-response (UI event) | `app/src/lib/components/StatCard.svelte` (container/slot shape) + inline `<button>` usages in `ChatBubble.svelte`/`SectionRail.svelte` | role-match, synthesized (no existing standalone Button component) |
| `app/src/lib/primitives/Badge.svelte` | component (primitive) | request-response | status-badge inline markup in admin components (grep target, e.g. `ResolveCard.svelte` status pills) | role-match, synthesized |
| `app/src/lib/primitives/Input.svelte` | component (primitive) | request-response / form | `app/src/lib/components/DocketPillInput.svelte` | role-match (existing `role="alert"` error pattern, `invalid`/`descriptionId` props) |
| `app/src/lib/primitives/Card.svelte` | component (primitive) | request-response | `app/src/lib/components/StatCard.svelte` | exact (container + slot/children pattern already exists) |
| `app/src/lib/types/speaker.ts` (folded todo) | utility (types module) | n/a | `TenureRow`/`SpeakerDetail` interfaces duplicated in `SpeakerPopover.svelte` and `.../arguments/[id]/+page.svelte` | exact — extraction target named in CONTEXT.md itself |
| `app/src/lib/components/SpeakerPopover.svelte` (edit: dedupe `avatarBg`/`sideColor`, token adoption) | component | request-response | itself (existing file) | exact — in-place edit |
| `app/src/lib/public/ChatBubble.svelte` (moved+reworked) | component | request-response | `app/src/lib/components/ChatBubble.svelte` | exact — in-place move/edit |
| `app/src/lib/public/StageDirection.svelte` (moved+reworked) | component | request-response | `app/src/lib/components/StageDirection.svelte` | exact |
| `app/src/lib/public/SectionRail.svelte` (moved+reworked) | component | event-driven (IntersectionObserver) | `app/src/lib/components/SectionRail.svelte` | exact |
| `app/src/lib/public/TermRow.svelte` (D-16 variant A/B) | component | request-response | `app/src/routes/cases/+page.svelte` (inline card-link markup) | role-match, new component extracted from route |
| `app/src/lib/{public,admin}/TopNav.svelte` (D-10 link rename) | component | request-response | `app/src/lib/components/TopNav.svelte` | exact — in-place edit (`/cases` → `/arguments`) |
| `app/src/app.css` (token expansion, D-01/D-02/D-03) | config (global styles) | n/a | itself — 8 existing `:root` custom properties | exact — extend in place |
| `app/tailwind.config.js`, `app/postcss.config.js` (deleted, D-01) | config | n/a | — | removal, no analog needed |
| `app/package.json` (Tailwind deps removed, D-01; icon lib possibly added, D-18) | config | n/a | itself | exact — edit in place |
| `api/schemas/cases.py` → `api/schemas/arguments.py`-style additions (D-14/D-15/D-16 pagination+term grouping+advocate join) | model (Pydantic schema) | CRUD (read) | `api/schemas/cases.py` (existing `CaseItem`/`CaseListResponse`) | exact — extend in place |
| `api/services/cases.py` (term grouping, pagination, D-16 advocate join) | service | CRUD (read) | itself — `get_cases()` | exact — extend in place |
| `api/routers/cases.py` (new term-scoped endpoint(s)) | route (FastAPI router) | request-response | itself — `GET /cases` | exact — extend in place |
| `alembic/versions/00XX_argument_slug.py` (D-12 new column + unique constraint) | migration | batch (DDL) | `alembic/versions/0030_argument_case_provenance_and_digest.py` | exact |
| `api/tests/test_trust_public_leak_ban.py` (extend PUBLIC_SCHEMA_MODULE_PATHS if new public model added) | test (structural ban) | n/a | itself | exact — extend in place, never duplicate |
| `.planning/codebase/DESIGN-SYSTEM.md` (update per D-03/D-01 staleness) | doc | n/a | itself | exact — edit in place |
| `.planning/REQUIREMENTS.md` / `.planning/ROADMAP.md` (D-11 amend DS-01) | doc | n/a | itself | exact — edit in place |

## Pattern Assignments

### `app/src/routes/arguments/+page.server.ts` (route/server-load, request-response)

**Analog:** `app/src/routes/cases/+page.server.ts` (11 lines, read in full)

**Imports pattern** (lines 1-3):
```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
```
Confirms Architecture Rule 2: `FASTAPI_BASE_URL` only ever appears server-side, imported from `$env/static/private`, never `$env/static/public`.

**Core request-response pattern** (lines 5-10):
```typescript
export const load: PageServerLoad = async ({ fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	return { cases: data.cases };
};
```
New file swaps the endpoint for the term-index endpoint (D-14/D-15 — new pagination/grouping query params land here) and the return key from `cases` to whatever the term-list shape needs (e.g. `terms`). Error propagation via `error(res.status, ...)` is the fixed convention — do not swallow non-OK into an empty array here (contrast with the *speakers* fetch below, which does degrade gracefully because it's a secondary, non-blocking fetch).

**Param-driven load + 404 pattern** — analog for `arguments/term/[year]/+page.server.ts`:
`app/src/routes/cases/[slug]/+page.server.ts` (16 lines, read in full):
```typescript
export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/cases`);
	if (!res.ok) throw error(res.status, 'Failed to load cases');
	const data = await res.json();
	const matches = data.cases.filter((c: { slug: string }) => c.slug === params.slug);
	if (matches.length === 0) throw error(404, 'Case not found');
	...
};
```
For the term route, `params.year` replaces `params.slug`; an out-of-range/non-numeric year must throw `error(404, ...)` per the UI-SPEC E2 "error" row (genuine 404, distinct from the empty-term-with-zero-published-rows case which is NOT a 404 — that renders the empty-state copy instead). **D-11 note:** unlike this analog's `redirect(307, ...)` on the single-match case, the new arguments routes must NOT add any `/cases` redirect — D-11 struck that requirement.

---

### `app/src/routes/arguments/[slug]/+page.server.ts` (route/server-load, request-response, secondary fetch degradation)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` (55 lines, read in full)

**Core pattern — primary fetch fails closed, secondary fetch degrades gracefully** (lines 13-43):
```typescript
export const load: PageServerLoad = async ({ params, fetch }) => {
	const res = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/utterances`);
	if (!res.ok) throw error(res.status, 'Failed to load argument');
	const data = await res.json();

	let speakers: Array<RawSpeaker & { photo_url_full: string | null; is_bench: boolean }> = [];
	try {
		const speakersRes = await fetch(`${FASTAPI_BASE_URL}/arguments/${params.id}/speakers`);
		if (speakersRes.ok) {
			const raw: RawSpeaker[] = await speakersRes.json();
			speakers = raw.map((s) => { /* photo_url_full reconstruction server-side */ });
		}
	} catch {
		// Network or parse error: leave speakers as []
	}

	return { utterances: data.utterances, argument: data.argument, argument_id: parseInt(params.id), speakers, is_corpus_sourced: data.argument.oyez_transcript_id != null };
};
```
Swap `params.id` (numeric argument id) for `params.slug` (D-12's new `Argument.slug`); the endpoint the new route hits should resolve by slug server-side (API work implied — either a new `/arguments/by-slug/{slug}` endpoint or a slug-aware lookup added to the existing endpoint). Keep the `photo_url_full` server-side reconstruction pattern verbatim — it exists specifically so `FASTAPI_BASE_URL` never reaches the client (Architecture Rule 2). Keep the try/catch degrade-gracefully shape for any non-critical secondary fetch; do NOT apply it to the primary fetch.

---

### `app/src/routes/arguments/[slug]/+page.svelte` (component, request-response, D-09 "reading polish" scope)

**Analog:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` itself (349 lines) — this is the exact file being edited in place and relocated, not a different analog. D-09 names this file plus `ChatBubble.svelte` (107), `StageDirection.svelte` (33), `SectionRail.svelte` (62), `SpeakerPopover.svelte` (259) as the 810-line scope: type scale/measure, vertical rhythm, speaker-change emphasis, stage-direction treatment, color roles via tokens. The chat-bubble metaphor, popover model, and rail are KEPT — only styling mechanism and typographic/spacing values change.

**Landmine check — `data` prop capture (CLAUDE.md two-week published-lock bug class):**
Line 2 of `+page.svelte` files in this codebase uses `let { data } = $props();` (see `cases/+page.svelte` line 2) — a **plain destructure, not `const`, and not further captured into a separate non-reactive variable**. This is the safe form: `$props()` returns a reactive proxy and `data` re-reads on each invalidation because it's accessed fresh via the `let` binding each render. The landmine pattern to watch for while editing `[slug]/+page.svelte` (349 lines) during D-09's rework is any line that does `const argument = data.argument;` etc. at the top of `<script>` and then references `argument` — that freezes across invalidation. Prefer `let argument = $derived(data.argument);` for any value read across multiple places in the template, matching the `$derived` usage already established in `CopyableExtractedValue.svelte` (`let isEmpty = $derived(...)`) and `SectionRail.svelte` (`$state`/`$effect`).

---

### `app/src/lib/public/TermRow.svelte` (new component, D-16 two variants)

**Analog:** inline card-link markup in `app/src/routes/cases/+page.svelte` (lines 79-115, read in full):
```svelte
{#each data.cases as c (c.id)}
	<a href="/cases/{c.slug}" style="background-color: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 16px; margin-bottom: 16px; display: block; text-decoration: none;">
		<span style="font-size: 20px; font-weight: 600; color: #e2e8f0; display: block; margin-bottom: 4px;">{c.case_name}</span>
		<span style="font-size: 14px; font-weight: 400; color: #94a3b8;">No. {c.docket_number} · Argued {formatDate(c.argued_date)}</span>
	</a>
{/each}
```
Extract this pattern into a standalone `TermRow.svelte` component (D-17 requires primitives/public split; a per-row component is new, not present today — this route currently inlines row markup rather than componentizing it). Variant A (minimal: case name + argued date + docket) is a direct token-ized lift of the above. Variant B (+ advocate names, D-16) adds a line sourced from the new `argument_participants` → `people` join (D-16, D-15) — per UI-SPEC E2 "partial" row, omit the advocate line entirely (no empty-space placeholder) when an argument has zero resolved advocates. Also copy the `formatDate` helper (lines 11-19 of `cases/+page.svelte`) verbatim — it is the one non-style logic in this file and is reused for both the term index and term-detail dates.

---

### `app/src/lib/primitives/Input.svelte` (new primitive, form, request-response)

**Analog:** `app/src/lib/components/DocketPillInput.svelte` (292 lines; imports and props read, lines 1-60)

**Error-text pattern to reuse** (referenced by UI-SPEC E4 "error" row, "the existing `role="alert"` pattern already used by `DocketPillInput`"):
```typescript
interface DocketPillInputProps {
	...
	invalid?: boolean;
	descriptionId?: string;
	...
}
```
`Input.svelte` should expose the same `invalid` boolean + `descriptionId`/`aria-describedby` wiring convention, with the error text rendered under `role="alert"` and styled with the new `--color-destructive` semantic token (UI-SPEC Color section) rather than a literal hex. Grep `DocketPillInput.svelte` for the exact `role="alert"` element before writing `Input.svelte`, to match markup shape precisely (not just re-derive it).

---

### `app/src/lib/primitives/Card.svelte` (new primitive)

**Analog:** `app/src/lib/components/StatCard.svelte` (32 lines, read in full):
```svelte
<script lang="ts">
	let { title, children } = $props();
</script>
<div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;">
	<h2 style="font-size: 20px; font-weight: 600; color: #e2e8f0; margin: 0 0 16px 0;">{title}</h2>
	{@render children()}
</div>
```
This is already exactly the "Card pattern" the CONTEXT.md documents as applied identically everywhere (`background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;`). `Card.svelte` in `lib/primitives/` should generalize this: token-ize the three hardcoded colors to `--color-surface`/`--color-border`/`--color-text-primary`, keep the `{@render children()}` snippet-slot convention (Svelte 5 Runes-era snippet API, not the legacy `<slot>`), and make the `title` heading optional per UI-SPEC E4 "partial" row ("a Card with a heading but no body... must not break layout").

---

### `app/src/lib/types/speaker.ts` (new shared types module — folded todo)

**Duplication to eliminate** — both files declare byte-for-byte identical interfaces:
- `app/src/lib/components/SpeakerPopover.svelte` (grep for `interface TenureRow` / `interface SpeakerDetail`)
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` lines 8-38 (read above — `TenureRow` and `SpeakerDetail`)

Extract verbatim into `app/src/lib/types/speaker.ts` (a new bare `.ts` module — no existing `lib/types/` directory today, this is the first file in it) and import in both call sites: `import type { TenureRow, SpeakerDetail } from '$lib/types/speaker';`. Do not change field shapes while extracting — this is a pure dedupe per the folded todo, not a redesign.

---

### `app/src/app.css` (config, token expansion — D-01, D-02, D-03)

**Analog:** itself, current state (23 lines, read in full):
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
	--color-bg: #0f1117;
	--color-surface: #1e293b;
	--color-border: #334155;
	--color-text-primary: #e2e8f0;
	--color-text-secondary: #94a3b8;
	--color-text-advocate: #93c5fd;
	--color-stage-accent: #d97706;
	--color-stage-text: #fcd34d;
	font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
```
Required edits per D-01/D-02/D-03/UI-SPEC:
1. Delete the three `@tailwind` directives (line 1-3).
2. Add the primitive-palette layer (private, e.g. `--slate-950`, `--slate-800`, ... per UI-SPEC "Primitive palette" table) feeding the existing/expanded semantic layer — two-layer structure is load-bearing (D-02), do not flatten.
3. Existing `--color-text-advocate` maps to the new `--color-side-advocate` semantic name per UI-SPEC (keep the old name only if still referenced elsewhere — grep before removing).
4. Add spacing tokens (`--space-xs` through `--space-3xl`) and type-scale tokens (`--font-size-caption` through `--font-size-display`, `--line-height-*`) per UI-SPEC Spacing/Typography tables.
5. Add the five admin-only status tokens (`--color-status-*`) and `--color-destructive`, `--color-accent`.
6. Keep the existing `*:focus-visible` rule (lines ~20-24) but replace the literal `#93c5fd` with `var(--color-accent)`.

`.planning/codebase/DESIGN-SYSTEM.md` must be updated alongside this file per CONTEXT.md's explicit instruction — treat it as documentation of the *result*, not a pre-existing source of truth (it is flagged stale on both the Tailwind and type-scale claims).

---

### `alembic/versions/00XX_argument_slug.py` (migration, D-12)

**Analog:** `alembic/versions/0030_argument_case_provenance_and_digest.py` (structure read, lines 1-50+):
```python
"""<summary line>

Revision ID: 0030
Revises: 0029
Create Date: 2026-08-26

<prose body explaining each column, referencing the plan/decision IDs that
justify it, and explicitly stating there is NO backfill/UPDATE — reseed-not-
migrate constraint>
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030"
down_revision: str = "0029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    ...
```
New migration: `op.add_column("arguments", sa.Column("slug", sa.String(200), nullable=True))` then a follow-up `UniqueConstraint` (nullable initially is a defensible choice if slugs are backfilled at import rather than via migration-time UPDATE — reseed-not-migrate per MEMORY.md and CLAUDE.md; confirm with D-12's "generated at import" language, meaning the column can be `nullable=False` if the reseed happens before promotion, or `nullable=True` with a later NOT NULL migration if it must land before reseed). Follow `Case.slug`'s existing column shape exactly: `Column(String(200), nullable=False, unique=True)` (see `api/models/models.py:300`) — same width, same uniqueness mechanism. Docstring must state explicitly (matching 0030's convention) that no backfill/UPDATE statement is included, and must note the `term` reserved-slug-word constraint (D-13) is enforced at the application layer (slug generation), not as a DB CHECK constraint.

---

### `api/services/cases.py` / `api/routers/cases.py` (D-14/D-15/D-16 extension)

**Analog:** itself, current `get_cases()` (read in full above) and `GET /cases` router (read in full above).

Core pattern to extend, not replace — the existing join/filter/order shape:
```python
select(Case, Argument)
    .join(CaseArgument, CaseArgument.case_id == Case.id)
    .join(Argument, CaseArgument.argument_id == Argument.id)
    .where(CaseArgument.is_lead == True)
    .where(Argument.published_at.isnot(None))
    .where(Argument.status == ArgumentStatusEnum.PUBLISHED)
    .order_by(Argument.argued_date.desc())
```
D-14/D-15 need: (1) a term-grouping query (`GROUP BY Argument.term_year`-equivalent with counts, gated by the same three `WHERE` predicates so unpublished rows never inflate a term's count — UI-SPEC E1 "partial" row is explicit about this), and (2) a term-scoped detail query (same base query plus `WHERE Argument.term_year == :year`). D-16 Variant B needs an additional join through `argument_participants` → `people`, filtered to advocates — copy the existing join style (explicit `.join()` chain, not implicit relationship loading) and evaluate query cost at term scale (~150 rows/term) before committing to eager-loading it on every row. Router pattern: add a second route function in `api/routers/cases.py` (or rename the file/router prefix to `arguments` — check whichever the planner decides for the noun rename) mirroring the existing `@router.get("", response_model=CaseListResponse)` shape, with its own dedicated response schema for the term-grouped shape.

---

## Shared Patterns

### Server-side `FASTAPI_BASE_URL` boundary (Architecture Rule 2)
**Source:** `app/src/routes/cases/+page.server.ts`, `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts`
**Apply to:** every new/moved `+page.server.ts` under `app/src/routes/arguments/**`
```typescript
import { FASTAPI_BASE_URL } from '$env/static/private';
```
Never `$env/static/public`; never let a raw `FASTAPI_BASE_URL`-prefixed URL reach a component prop except when explicitly reconstructed server-side (see `photo_url_full` pattern).

### Fail-closed primary fetch / degrade-gracefully secondary fetch
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` lines 5-8 vs 19-43
**Apply to:** all new route load functions — the primary data fetch always `throw error(res.status, ...)` on non-OK; a secondary, non-blocking fetch (e.g. advocate names for D-16 Variant B, if fetched separately) degrades to an empty/null value inside try/catch instead.

### Inline-style-to-token conversion (D-04)
**Source:** every existing component (`ChatBubble.svelte`, `StageDirection.svelte`, `SectionRail.svelte`, `TopNav.svelte`, `StatCard.svelte`, `cases/+page.svelte` — all read above)
**Apply to:** every file this phase touches. The literal hexes appearing repeatedly (`#1e293b`, `#334155`, `#94a3b8`, `#93c5fd`, `#e2e8f0`, `#0f1117`, `#d97706`, `#fcd34d`) map 1:1 onto the existing/new `app.css` custom properties. Convert `style="background-color: #1e293b; ..."` to `style="background-color: var(--color-surface); ..."` — the string-literal `style=` attribute mechanism itself is retained (no CSS-in-JS, no Tailwind classes); only the values inside become `var(--token)` references. Zero raw hex values may remain in any component at phase end.

### Svelte 5 Runes props/state/derived (no legacy stores)
**Source:** `SectionRail.svelte` (`$state`, `$effect`), `CopyableExtractedValue.svelte` (`$derived`, `$derived.by`), all components' `let { ... } = $props()`
**Apply to:** every new/edited `.svelte` file. Never introduce `writable`/`readable`/`derived` from `svelte/store` or a top-level reactive `$:` label — this codebase is Runes-only. Any value read from `$props()` that needs to stay reactive across invalidation must be wrapped in `$derived`, never captured into a plain `const` at the top of `<script>` (see the `data` prop landmine note above).

### `role="alert"` + `invalid`/`descriptionId` validation pattern
**Source:** `DocketPillInput.svelte`
**Apply to:** `lib/primitives/Input.svelte` and any other new form control.

### Structural leak-ban extension, never a parallel check
**Source:** `api/tests/test_trust_public_leak_ban.py` (`PUBLIC_SCHEMA_MODULE_PATHS` list)
**Apply to:** any new public Pydantic response model this phase adds (e.g. a term-grouped list response, an advocate-augmented row response). Add the new schema module path to the existing list; do not write a second, separate leak-ban test.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/src/lib/primitives/Button.svelte` | component (primitive) | request-response | No standalone `<button>` component exists today — every button is inline markup inside a larger component (`ChatBubble.svelte`'s avatar button, `SectionRail.svelte`'s nav buttons). Use those inline button blocks for styling values (padding, cursor, border-radius) but there is no primitive shape to copy structurally; follow the UI-SPEC's Button/touch-target contract (44px / 36px dense) directly. |
| `app/src/lib/primitives/Badge.svelte` | component (primitive) | request-response | No dedicated Badge component exists; admin status pills are inline markup scattered across components (grep `ResolveCard.svelte` and similar for the closest inline shape). Build from the UI-SPEC's semantic status-color table directly. |
| Icon usage (`lucide-svelte` or hand-rolled, D-18) | component/utility | n/a | UI-SPEC states "the codebase has near-zero icon usage (2 files touch an SVG/icon concept at all)" — no established icon pattern exists to copy; this is a genuinely new decision point pending operator input at the Wave 1 checkpoint. |
| `app/src/lib/primitives/` directory itself | config (new directory) | n/a | Does not exist yet — `lib/components/` is the only current shared-component location; `lib/primitives/`, `lib/public/`, `lib/admin/` are all new per D-17/D-06 and have no prior directory-structure analog in this codebase. |

## Metadata

**Analog search scope:** `app/src/routes/cases/**`, `app/src/lib/components/**`, `app/src/app.css`, `api/schemas/cases.py`, `api/services/cases.py`, `api/routers/cases.py`, `api/models/models.py`, `alembic/versions/` (latest), `api/tests/test_trust_public_leak_ban.py`
**Files scanned:** ~20 read in full or targeted excerpt
**Pattern extraction date:** 2026-08-27
