# Phase 44 (follow-on 44-05): Figma Canonical Reconciliation — Research

**Researched:** 2026-08-04
**Domain:** Svelte 5 admin UI rework (ResolveCard.svelte) + two small FastAPI/SQLAlchemy service-layer verifications/fixes
**Confidence:** HIGH

## Summary

This is a reconciliation pass, not new architecture. `44-FIGMA-RECONCILE.md` is the
canonical spec; every requirement (RESOLVE-07–16) maps onto `ResolveCard.svelte`'s
existing component, snippets, and per-row hidden-form save pattern established in
Plans 44-01 through 44-03. The two flagged open risks both resolved to good news
during this research, with exact line-level evidence:

1. **RESOLVE-09 (side-scoped search) needs almost no backend work.** `Person.is_justice`
   already exists (migration 0010), and `GET /api/admin/people` (the exact endpoint
   `+page.server.ts` already calls for the `people` prop) already returns it via
   `PersonListItem.is_justice`. The only gaps are two TypeScript interfaces that
   currently *drop* the field on the way through (a narrower object-literal type in
   `+page.server.ts` and `ResolveCard.svelte`'s own `Candidate` interface), plus the
   fact that the `AdminJob.discrepancies` JSONB blob (candidates attached to a
   specific unresolved row) was written by `pipeline/commands/resolve.py` at
   resolve-time *without* `is_justice` — but `getRowCandidates` already merges
   `people` first and de-dupes by `id`, so the richer `people` copy of any given
   person already wins for every candidate that also appears in the discrepancy list.
   **No migration, no schema change required.**

2. **RESOLVE-11 (live tenure recompute) is already correctly implemented on both
   paths — they do not diverge.** `api/services/admin_people.py::list_resolve_rows_for_job`
   (the job-scoped editable path) and `api/services/admin_arguments.py::list_argument_speakers`
   (the argument-scoped path that also serves `ResolveCard.svelte`'s read-only
   rendering, since `readonlyMode` reuses the *same* `resolve-rows` endpoint) both
   call the identical `_bench_role_and_missing_tenure()` helper against a **fresh
   `CourtTenure` query issued on every request** — there is no snapshot column, no
   caching, and no divergence between the two call sites. `admin_arguments.py` even
   imports the helper directly from `admin_people.py` rather than duplicating it.
   **No behavior change needed for RESOLVE-11/12/14's live-recompute requirement
   itself** — only the *display copy* (RESOLVE-12/14) and the *card layout*
   (RESOLVE-07/08) around it need to change.

The one genuine backend **behavior bug** this research surfaced (not previously
documented as fixed) is **RESOLVE-13**: `update_resolve_row_for_job`
(`api/services/admin_jobs.py:820`) currently forces
`descriptor = None if body.side == SideEnum.BENCH else body.descriptor` on *every*
write — meaning the very first time an operator toggles a row to Bench, the stored
`ArgumentParticipant.descriptor` is permanently wiped from the database, not just
hidden from the UI. This must change to leave the column untouched on a bench
write, not merely stop rendering it.

**Primary recommendation:** Sequence as the reconciliation doc already prescribes —
structural (RESOLVE-07/08 column merge) first, then the one real data-layer fix
(RESOLVE-13) and the two TS-typing widenings (RESOLVE-09), then copy/visual passes
(RESOLVE-10/12/14) and the two purely client-derived additions (RESOLVE-15/16,
which need no backend calls at all — the data is already in `discrepancies`/
`rowMatchStates`).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 4-column layout / Resolved-As dropdown model (RESOLVE-07/08) | Browser/Client (Svelte component) | — | Pure markup/state restructuring inside `ResolveCard.svelte`; no new data needed |
| Side-scoped candidate filtering (RESOLVE-09) | Browser/Client | Frontend Server (SSR, TS typing only) | Filter runs client-side over the merged candidate list; the only backend-adjacent change is widening two existing TS interfaces to stop dropping `is_justice`, already present in the JSON payload |
| Source-aware hint prefix (RESOLVE-10) | Frontend Server (SSR) | Browser/Client | `job.source` is already computed server-side (`api/services/admin_jobs.py`); SSR load just needs to forward it as a new `ResolveCard` prop |
| Live bench-role recompute (RESOLVE-11/12/14) | API/Backend | Database/Storage (CourtTenure) | Already correctly implemented — both read paths query `court_tenures` live; only display copy is a client change |
| Descriptor preservation on side switch (RESOLVE-13) | API/Backend | Browser/Client | The wipe happens server-side in `update_resolve_row_for_job`; must stop forcing null there. Client also must never render a stale value once unhidden — already correct since `row.descriptor` is refetched after save |
| Progress indicator + always-visible Continue (RESOLVE-15) | Browser/Client | — | Fully derivable from already-loaded `discrepancies`/`rowMatchStates`; no new endpoint |
| Row cue tags (RESOLVE-16) | Browser/Client | — | Fully derivable from `discrepancy.auto_resolved` / gate state already computed client-side |

## Standard Stack

No new libraries. This phase is a rework of existing code using the exact stack
already declared in `CLAUDE.md` and verified in the repo:

| Layer | Verified version | Source |
|-------|------|--------|
| Svelte | `^5.30.0` | `[VERIFIED: app/package.json:20]` |
| SvelteKit | `^2.21.0` | `[VERIFIED: app/package.json:14]` |
| FastAPI | `>=0.115` | `[VERIFIED: requirements.txt:1]` |
| SQLAlchemy | `>=2.0` | `[VERIFIED: requirements.txt:2]` |
| Alembic | `>=1.13` | `[VERIFIED: requirements.txt:4]` |

**Installation:** none — no new packages this phase.

## Package Legitimacy Audit

**Skipped.** This phase installs no external packages; every file touched is an
in-place edit to existing project code (`ResolveCard.svelte`, `CopyableExtractedValue.svelte`,
`api/services/admin_jobs.py`, `+page.server.ts`). No `npm install` / `pip install` is
part of this phase's scope.

## Architecture Patterns

### System Architecture Diagram

```
Browser (ResolveCard.svelte)
   │
   │ 1. GET /admin/pipeline/[job_id]  (SvelteKit load)
   ▼
+page.server.ts  load()
   │  ├─ fetch /api/admin/jobs/{job_id}            → job (has .source: "pdf"|"corpus", ALREADY derived)
   │  ├─ fetch /api/admin/people                   → people[] (has .is_justice, ALREADY returned)
   │  └─ fetch /api/admin/jobs/{job_id}/resolve-rows → resolveRows[] (bench_role/missing_tenure ALREADY live)
   │
   ▼ (props: resolveRows, people, discrepancies-via-job, source ← NEW prop to add)
ResolveCard.svelte
   │  ├─ mergedRows = resolveRows ⋈ discrepancies (by raw_speaker_label)   [existing]
   │  ├─ getRowCandidates(row) = dedupe(people ∪ discrepancy.candidates ∪ extraCandidates)
   │  │      → NEW: filter by is_justice === (effectiveSide(row) === 'BENCH')   [RESOLVE-09]
   │  ├─ 4-column render: Raw Label | Resolved-As{toggle+dropdown} | Argument Role | Descriptor
   │  │      [RESOLVE-07/08 — collapses 3 existing snippets into 1 cell's stacked layout]
   │  ├─ hint prefix ← `source` prop ("Imported"/"Extracted")   [RESOLVE-10]
   │  ├─ argument-role cell copy ← "Calculated from tenure"/"Tenure not found"/"(resolve person first)"
   │  │      [RESOLVE-12/14 — copy only; bench_role/missing_tenure values are already live-correct]
   │  └─ progress + Continue ← derived from discrepancies.length / rowMatchStates  [RESOLVE-15/16]
   │
   ▼ (per-row save, unchanged transport)
?/saveResolveRow (SvelteKit action)
   ▼
PATCH /api/admin/jobs/{job_id}/resolve-rows
   ▼
update_resolve_row_for_job()  api/services/admin_jobs.py:765
   │  CURRENT: descriptor = None if side==BENCH else body.descriptor   ← WIPES on bench (bug, RESOLVE-13)
   │  FIX:     only include descriptor in the UPDATE when side != BENCH
   ▼
ArgumentParticipant.descriptor (DB column, unchanged schema)

Read-only rendering (argument left 'pipeline'):
   Same ResolveCard.svelte, same /resolve-rows endpoint, readonlyMode=true.
   list_resolve_rows_for_job() → same _bench_role_and_missing_tenure() call,
   same fresh CourtTenure query — NOT a different, NOT a snapshotted, path.
   admin_arguments.py's list_argument_speakers() (backs the separate argument-
   editor page's Speakers section) independently imports and calls the SAME
   helper against the SAME live query — confirmed non-divergent.
```

### Recommended Project Structure

No new files/folders. All edits land in:
```
app/src/lib/components/ResolveCard.svelte          # structural + copy rework (RESOLVE-07..16, most of it)
app/src/lib/components/CopyableExtractedValue.svelte # no change needed — prefixLabel prop already exists
app/src/routes/admin/pipeline/[job_id]/+page.server.ts # widen ResolveRow/people types, forward job.source
api/services/admin_jobs.py                         # update_resolve_row_for_job: stop nulling descriptor on BENCH
api/tests/test_phase44_resolve_table_contract.py   # extend/rewrite the 5-column assertions to 4 columns
```

### Pattern 1: Person/side-scoped candidate filter (RESOLVE-09)

**What:** Filter the merged candidate list by `is_justice` matching the row's
currently-selected side, computed entirely client-side.

**Verified fields (read this session):**

- `Person.is_justice` — `[VERIFIED: api/models/models.py:118]` — quoted:
  `is_justice = Column(Boolean, nullable=False, server_default=false())`
- `PersonListItem.is_justice` — `[VERIFIED: api/schemas/admin_people.py:118]` — quoted:
  `is_justice: bool = False`
- The router endpoint `+page.server.ts` already calls with no filter params —
  `[VERIFIED: api/routers/admin.py:629]` — quoted:
  `@router.get("/people", response_model=list[PersonListItem])`
  and `[VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts:126]` — quoted:
  ``const peopleRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/people`, {``
  (no `?is_justice=` query string — the call is genuinely unfiltered, so the
  response already carries every person's `is_justice` value regardless of tab).

**Where the field currently gets dropped (both are pure TS widenings, zero runtime/schema change):**

- `+page.server.ts` types the fetched array too narrowly —
  `[VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts:123]` — quoted:
  `let people: Array<{ id: number; full_name: string; role_name: string | null }> = [];`
  (note: `role_name` isn't even a real `PersonListItem` field — it's already an
  inaccurate annotation; the actual runtime JSON has `missing`, `is_justice`,
  `argument_count`, `tenure_coverage`, `has_tenure_gap`, `name_needs_review`, not `role_name`.
  Widening this type is required regardless of RESOLVE-09.)
- `ResolveCard.svelte`'s own candidate interface —
  `[VERIFIED: app/src/lib/components/ResolveCard.svelte:27-31]` — quoted:
  ```
  interface Candidate {
  	id: number;
  	full_name: string;
  	role_name?: string | null;
  }
  ```
  Needs `is_justice?: boolean;` added.

**The one genuine gap (documented, not a blocker):** `AdminJob.discrepancies`
(JSONB) candidates are built once at resolve-time by
`[VERIFIED: pipeline/commands/resolve.py:262-269]` — quoted:
```python
candidates = [
    {
        "id": person.id,
        "full_name": person.full_name,
        "role_name": role_name,
    }
    for person, role_name in people_rows
]
```
— no `is_justice` key. This is fine in practice because
`[VERIFIED: app/src/lib/components/ResolveCard.svelte:294-303]` (`getRowCandidates`)
spreads `people` *before* `discrepancy.candidates` and de-dupes by `id`, keeping
the first (richer) copy — so any candidate present in both lists (the normal case,
since both ultimately come from the same `people` table) resolves to the
`is_justice`-carrying copy. A candidate that exists *only* in a stale discrepancy
snapshot (never in the live `people` fetch) would lack `is_justice` and should be
treated as "unknown side" (fail-open: show it in both filtered lists, or hide it —
Claude's discretion at plan time) rather than as a reason to touch the pipeline/
resolve.py write path or add a migration.

**`extraCandidates` (freshly created this session via `CreatePersonPopover`)** also
lack `is_justice` in the raw API response —
`[VERIFIED: api/schemas/admin_jobs.py:123-131]` — quoted:
```python
class PersonResponse(BaseModel):
    """Minimal person record returned after inline person creation."""
    id: int
    full_name: str
    role_id: Optional[int] = None
    role_name: Optional[str] = None
```
— but the frontend already knows the chosen side at creation time via
`handlePersonCreated(label, participantId, person, side)` —
`[VERIFIED: app/src/lib/components/ResolveCard.svelte:329-338]`. The planner should
have this handler synthesize `is_justice: side === 'BENCH'` onto the enriched
candidate object client-side rather than requesting a backend schema change.

### Pattern 2: Live tenure recompute — already correct, verify only

**What:** Confirm (do not "add") that both the editable and read-only paths derive
`bench_role`/`missing_tenure` from a fresh `CourtTenure` query on every read.

**Editable path** — `[VERIFIED: api/services/admin_people.py:885-918, 998-1029]`:
`_bench_role_and_missing_tenure()` is a pure function taking `tenures: list[CourtTenure]`
already fetched fresh inside `list_resolve_rows_for_job` at
`[VERIFIED: api/services/admin_people.py:990-995]` — quoted:
```python
tenures_by_person: dict[int, list[CourtTenure]] = {}
if bench_person_ids:
    tenures_result = await db.execute(
        select(CourtTenure).where(CourtTenure.person_id.in_(bench_person_ids))
    )
```
— executed on every call to `GET /api/admin/jobs/{job_id}/resolve-rows` (which is
the *same* endpoint `+page.server.ts` calls regardless of `readonlyMode`).

**"Read-only" path is the same endpoint, not a different one.** `resolveRows` is
fetched unconditionally by job_id —
`[VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts:236-255]` — the
fetch to `/api/admin/jobs/{job_id}/resolve-rows` has no branch on `readonlyMode`.
`readonlyMode` only changes what `ResolveCard.svelte` renders (editable inputs vs.
plain text), not which data-fetch runs.

**The separate argument-editor page's Speakers section (`/admin/arguments/[id]`)
uses a *different* function but the *same* helper, also live** —
`[VERIFIED: api/services/admin_arguments.py:40]` — quoted:
`from api.services.admin_people import _bench_role_and_missing_tenure`
and `[VERIFIED: api/services/admin_arguments.py:248-254, 275-282]` — a fresh
`CourtTenure` query and a fresh call to the identical helper, with no
`Argument.status` branch gating whether this computation runs. This function
backs `GET /api/admin/arguments/{argument_id}` (`get_argument_detail`, called at
`[VERIFIED: api/services/admin_arguments.py:445]`, quoted:
`speakers = await list_argument_speakers(db, argument_id)`), which is the exact
endpoint `+page.server.ts` also calls for `ArgumentDetailsCard` on the same page —
`[VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts:170-173]`.

**Conclusion for the planner:** RESOLVE-11's correctness requirement needs **zero
service-layer code changes**. Plan a verification/regression test (e.g. update
tenure after resolve, re-fetch, assert the new role appears with no cache) rather
than a fix task. The only RESOLVE-11 *code* change is markup: `Edit person` must
gain `target="_blank" rel="noopener"` —
`[VERIFIED: app/src/lib/components/ResolveCard.svelte:531]` — quoted:
`<a href={row.person_edit_href} style="margin-left: 8px; font-size: 14px; color: #93c5fd; text-decoration: underline;">Edit person</a>`
(no `target`/`rel` attributes currently).

### Pattern 3: Descriptor preservation fix (RESOLVE-13)

**What goes wrong today:** `[VERIFIED: api/services/admin_jobs.py:820]` — quoted:
`descriptor = None if body.side == SideEnum.BENCH else body.descriptor`
inside `update_resolve_row_for_job` (`[VERIFIED: api/services/admin_jobs.py:765-830]`,
docstring at 783-785 quoted: `descriptor is forced to null whenever side == BENCH,
regardless of what the client sent, so bench rows never carry an advocate
descriptor (PJOB-15).`). This is a documented, *intentional* Phase-25 design
(PJOB-15) that Figma reconciliation now explicitly reverses (diff item #7 in
`44-FIGMA-RECONCILE.md`): the value must be **preserved in the DB, only hidden in
the UI** when side flips to Bench.

**Required fix:** change the `.values()` call so the update only includes
`descriptor` when `body.side != SideEnum.BENCH`; when side is BENCH, omit
`descriptor` from the update statement entirely (do not write `None` over it).
Concretely (illustrative, not literal since the exact `.values(...)` call site at
`api/services/admin_jobs.py:822-828` was not quoted here in full — the planner
should re-read those exact 6 lines before writing the task):

```python
values = {"side": body.side}
if body.side != SideEnum.BENCH:
    values["descriptor"] = body.descriptor
await db.execute(
    update(ArgumentParticipant)
    .where(...)
    .values(**values)
    ...
)
```

**Also required — frontend must not silently resurrect a stale hint.** Since the
descriptor `<input>` disappears from the DOM entirely when `side === 'BENCH'`
(`[VERIFIED: app/src/lib/components/ResolveCard.svelte:392-393]` — quoted:
`{#if side === 'BENCH'}\n\t\t<span style="color: #94a3b8;">–</span>`), no `name="descriptor"`
field exists in the hidden form while bench is selected — this is already correct
and requires no change; the fix is entirely server-side.

**Hint suppression on bench rows (RESOLVE-13's "no descriptor hint" half) is a
separate, purely presentational change.** `CopyableExtractedValue` renders its
`Imported:`/`Extracted:` prefix line **unconditionally** even when `value=null` —
`[VERIFIED: app/src/lib/components/CopyableExtractedValue.svelte:119-124]` — the
`{#if isStacked}` branch always renders `<span class="prefix">{prefixLabel}:</span>`
plus the copy button (which just shows "N/A" when `isEmpty`); there is no
early-return for a null value. `descriptorCell` in `ResolveCard.svelte` currently
calls `<CopyableExtractedValue>` for the hint unconditionally, outside the
side-branch —`[VERIFIED: app/src/lib/components/ResolveCard.svelte:391-434]`. The
fix is to wrap that hint block in `{#if side !== 'BENCH'}` (or move it inside the
non-bench branches only) so bench rows render no hint line at all, matching
RESOLVE-13's "no descriptor hint" requirement.

### Pattern 4: Source-aware hint prefix (RESOLVE-10)

**What:** `job.source` is already a server-derived `"pdf"|"corpus"` literal —
`[VERIFIED: api/schemas/admin_jobs.py:66-70]` — quoted:
```python
# Phase 30: "pdf" for jobs created via the ingest pipeline, "corpus" for
# jobs created directly by import-convokit (Phase 30, D-01). Derived via
# an exists() subquery on PipelineRun.strategy == "convokit_import" in
# both list_jobs() and get_job() — see api/services/admin_jobs.py.
source: Literal["pdf", "corpus"] = "pdf"
```
and computed at `[VERIFIED: api/services/admin_jobs.py:158-167]` — quoted:
```python
is_corpus_result = await db.execute(
    select(
        exists().where(
            PipelineRun.argument_id == job.argument_id,
            PipelineRun.strategy == PIPELINE_RUN_STRATEGY,
        )
    )
)
is_corpus = is_corpus_result.scalar_one()
job.__dict__["source"] = "corpus" if is_corpus else "pdf"
```
This is **not** `AdminJob.strategy` (no such column exists — confirmed by reading
the full `AdminJob` model, `[VERIFIED: api/models/models.py:492-516]`, which has no
`strategy` field at all; `strategy` lives on `PipelineRun`,
`[VERIFIED: api/models/models.py:403]`, quoted: `strategy = Column(String(100), nullable=True)`).
`get_job()` (called by `GET /api/admin/jobs/{job_id}`, the exact call
`+page.server.ts` already makes at line 107) already attaches this derived
`source` to the response.

**What's missing:** `+page.server.ts`'s local `job` variable is untyped (`const job = await res.json();`
with no declared interface — `[VERIFIED: app/src/routes/admin/pipeline/[job_id]/+page.server.ts:104-119]`),
so `job.source` is already accessible at runtime with zero code change on the SSR
side; it is simply never read or forwarded to `ResolveCard`'s props
(`[VERIFIED: app/src/lib/components/ResolveCard.svelte:58-76]`, `ResolveCardProps`
has no `source`/`prefixLabel`-equivalent field today). Add a `source: 'pdf' | 'corpus'`
prop to `ResolveCardProps`, pass `source={job.source}` from the parent `+page.svelte`
(not yet checked this session — the planner should grep
`app/src/routes/admin/pipeline/[job_id]/+page.svelte` for the existing
`<ResolveCard ... />` call site and add the prop there), and replace every hardcoded
`prefixLabel="Imported"` call site in `ResolveCard.svelte`
(4 occurrences, confirmed via the earlier full read of the file) with
`prefixLabel={source === 'corpus' ? 'Imported' : 'Extracted'}`.

### Pattern 5: Client-only progress/tag derivations (RESOLVE-15/16)

**What:** Both are fully derivable from data `ResolveCard.svelte` already has
loaded — no new endpoint, no new prop beyond what RESOLVE-10 already adds.

- **Progress "N of M speakers still need review"** — `M = (discrepancies ?? []).length`;
  dispositioned count = number of entries in `rowMatchStates` where
  `disposition != null && personId != null` (the exact predicate `allDispositioned`
  already uses, `[VERIFIED: app/src/lib/components/ResolveCard.svelte:266-278]`).
  `N = M - dispositionedCount`.
- **Always-visible Continue, disabled with a reason** — replace the current
  `{#if isPaused && allDispositioned}` wrapper around the entire footer
  (`[VERIFIED: app/src/lib/components/ResolveCard.svelte:904]`) with
  `{#if isPaused}` around the footer and `disabled={!allDispositioned || continueSubmitting}`
  on the button itself, plus a `title`/adjacent text reading `Resolve N more to continue`
  when disabled.
- **`AUTO-MATCHED` / `NEEDS YOU` row tags** — derivable per row from
  `row.discrepancy?.auto_resolved === true` (auto-matched) vs. `needsSideGate(row)`
  or an un-dispositioned `rowMatchStates` entry (needs-you) — both signals already
  exist; this is a pure additive `<span>` in the Resolved-As cell.

### Anti-Patterns to Avoid

- **Do not add a `strategy` column to `AdminJob`, and do not read `PipelineRun.strategy`
  directly from the frontend.** The derived `source` field already exists precisely
  to avoid leaking the raw pipeline-internal `strategy` string ("convokit_import" /
  "rule_based" / "llm_corrective") into the UI layer — reuse `job.source`, don't
  re-derive it client-side or add a new backend field.
- **Do not "fix" RESOLVE-11 by adding a cache or a stored snapshot column.** The
  correct behavior (live recompute) is already implemented; the risk was a
  documentation/verification gap, not a code gap. Adding a cache would be a
  regression relative to the current (correct) behavior.
- **Do not filter candidates using `SIDE_LABEL`/`ADVOCATE_LABEL_MAP` string matching.**
  `is_justice` is the correct, already-established filter field — it is the same
  field the People directory's Bench/Advocate tabs use
  (`[VERIFIED: api/routers/admin.py:640]`, quoted: `is_justice: tab filter (D-01/D-02)
  — true = Bench, false = Advocate, omitted = no filter`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Source-aware hint prefix | A new backend endpoint or a new `AdminJob` column | The existing derived `job.source` field, already computed and already returned by `GET /api/admin/jobs/{job_id}` | Already built in Phase 30; re-deriving it would duplicate the `PipelineRun.strategy == "convokit_import"` `exists()` subquery logic client-side or in a second backend spot |
| Side-scoped candidate filtering | A new `/api/admin/people?side=` query param or a new join in `resolve.py`'s candidate builder | Client-side filter over the already-fetched `people` list using the already-present `is_justice` field | The data is already in the payload; a backend filter param would be a second way to get the same answer and risks drifting from the People-directory's own `is_justice` semantics |
| Progress count / row cue tags | A new `readiness`-style backend aggregate endpoint | Client-side `$derived` over `discrepancies`/`rowMatchStates`, mirroring the existing `allDispositioned` pattern | These are pure counts/booleans over data already loaded once per page render; a round-trip would add latency for no benefit |

**Key insight:** Nearly every piece of data this reconciliation pass needs already
exists in the backend response shapes from Phases 25/30 — the actual work is almost
entirely inside `ResolveCard.svelte` (markup restructuring + a few TS interface
widenings) plus one narrowly-scoped service-layer bug fix (RESOLVE-13). Resist the
urge to add new endpoints; verify what's already there first (as this research did).

## Common Pitfalls

### Pitfall 1: Assuming RESOLVE-11 requires a code fix
**What goes wrong:** A plan that includes a task like "make bench_role recompute
live instead of using a stored value" will find there is no stored value to
replace — the task will either no-op or (worse) an executor under pressure to show
progress introduces an unnecessary caching layer.
**Why it happens:** The Figma doc itself flags this as "the biggest correctness
item" and phrases it as something to "verify," which reads like an implied fix.
**How to avoid:** Frame the RESOLVE-11 task as a **verification + regression test**
(update a tenure row, confirm the resolve-rows and argument-detail responses both
reflect it with no restart/cache-clear needed), not a code change, except for the
`target="_blank" rel="noopener"` markup fix on the "Edit person" link.
**Warning signs:** A plan task titled "recompute bench_role live" with no `git diff`
against `admin_people.py`/`admin_arguments.py` service functions.

### Pitfall 2: Filtering candidates before checking where `is_justice` is actually missing
**What goes wrong:** Naively filtering `getRowCandidates()`'s merged array by
`c.is_justice === (side === 'BENCH')` will silently drop every candidate sourced
*only* from `discrepancy.candidates` or `extraCandidates` (both currently lack
`is_justice`), which could hide legitimate auto-match suggestions or freshly
created people from the filtered list.
**Why it happens:** `is_justice` looks present because `people` (which does carry
it) is deduped first — but that only covers candidates that also independently
appear in the full unscoped `people` fetch.
**How to avoid:** Enrich `extraCandidates` with a synthesized `is_justice` at
creation time (the side is already known — see Pattern 1 above). For
`discrepancy.candidates`, either (a) accept they're always shadowed by `people`
(true for the current single-fixture dataset, verified via the Person table being
the sole source for both lists), or (b) explicitly document the fail-open
behavior chosen (show vs. hide an `is_justice`-less candidate) as a `Claude's
Discretion` item at plan time, don't leave it implicit.

### Pitfall 3: Rewriting the existing 5-column pure-source contract test in place without checking dependent assertions
**What goes wrong:** `api/tests/test_phase44_resolve_table_contract.py`
(`[VERIFIED: api/tests/test_phase44_resolve_table_contract.py, 558 lines, ~35 test
functions]`) hardcodes `count == 5` for `<th scope="col">` and asserts specific
label ordering (`Bench/Advocate` as its own header) — these MUST be updated to
`count == 4` and the merged header set, or the whole suite red-lines the moment
Task 1 of the new plan lands, even though the failure is expected/intentional.
Several other tests in this same file assert on now-retired mechanics (`toggleSide`,
`sideToggle` snippet, standalone `argumentRoleCell` branches) that RESOLVE-07/08
explicitly restructure.
**Why it happens:** The file is shared across Plans 44-02/03/04 by design (banner
comments per plan) — a new plan appending a fourth banner section without revisiting
the first three sections' now-stale assertions will look "additive" but actually
leaves contradictory assertions in the same file.
**How to avoid:** Treat this file as requiring an editing pass, not just an
addition — the new plan should explicitly list which existing test functions get
deleted/rewritten (five-header count, `sideToggle`/`argumentRoleCell` structural
tests) versus which survive unchanged (hex-color palette guard, `flushSync`
pattern, per-row hidden-form save contract).
**Warning signs:** `npm --prefix app run check` passing but
`pytest api/tests/test_phase44_resolve_table_contract.py` failing after the rework —
that failure is signal, not noise; don't suppress it, fix the assertions.

### Pitfall 4: Losing the Phase 27 CR-01/CR-02 always-in-DOM-input invariant during the 4-column merge
**What goes wrong:** Collapsing the toggle+person-search into one stacked cell is
exactly the kind of restructuring where it's tempting to conditionally render the
person-search `<input>` only when a side is chosen — but Phase 27's carried-forward
constraint (`[VERIFIED: .planning/STATE.md, "Phase 27 CR-01/CR-02" line]`, quoted:
`Keep data-carrying form inputs always present in the DOM (outside {#if} blocks);
conditionally-rendered inputs silently don't submit and wipe data on save.`)
explicitly forbids this pattern project-wide.
**Why it happens:** The Figma spec's "structural is now a gate" language (delta #3:
"the side gate is now structural: the toggle sits above the search") reads like it
wants the search hidden until a side is picked.
**How to avoid:** Render the search control always, but disabled/`aria-disabled`
until a side is chosen — mirroring the existing gated-entry-point pattern already
proven in Plan 44-02 (`[VERIFIED: app/src/lib/components/ResolveCard.svelte:680-691]`,
the inert `disabled aria-disabled="true"` button with an sr-only explanation) rather
than an `{#if}`-gated input.
**Warning signs:** A `{#if side}` or `{#if !gated}` wrapper directly around the new
combined search `<input>` (not just around its *listbox popup*, which is fine to
gate).

## Code Examples

### Existing pattern: per-row hidden-form save (reuse verbatim)
```svelte
<!-- Source: app/src/lib/components/ResolveCard.svelte:619-648 (verified this session) -->
{#each mergedRows as row (row.participant_id)}
	<form
		id={rowFormId(row.participant_id)}
		bind:this={formRefs[row.participant_id]}
		method="POST"
		action="?/saveResolveRow"
		style="display: none;"
		use:enhance={() => { /* ... */ }}
	>
		<input type="hidden" name="participant_id" value={row.participant_id} />
		<input type="hidden" name="side" value={effectiveSide(row)} />
	</form>
{/each}
```
This mechanism is unaffected by the column merge — the new stacked toggle+dropdown
cell still writes to the same hidden `side` input via `form={rowFormId(...)}` (or,
per the flushSync pattern, via pure `$state` mutators feeding this one hidden input).

### Existing pattern: gated/inert entry point (model for the new side-scoped search gate)
```svelte
<!-- Source: app/src/lib/components/ResolveCard.svelte:680-691 (verified this session) -->
{#if gated}
	<button type="button" disabled aria-disabled="true" style="...">
		Select person…
	</button>
	<span style="position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%);">
		Choose Bench or Advocate before selecting a person.
	</span>
{:else if ...}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| 5-column table, standalone Bench/Advocate column | 4-column table, side+person stacked in Resolved As | This phase (RESOLVE-07) | Structural rework of `<thead>` and each row's `<td>` boundaries |
| Confirm/Select/Change 3-action model, `disposition: 'confirmed'\|'corrected'` state machine | Single always-editable dropdown, no disposition machine | This phase (RESOLVE-08) | Deletes `openPersonSearch`'s "Change" branch distinction; `rowMatchStates.disposition` may become vestigial — check whether `allDispositioned`/`matchesJson` still need it for the Continue-submit payload shape, or whether they can be simplified once "confirmed vs corrected" no longer has a UI distinction |
| Unfiltered candidate list | Side-filtered candidate list | This phase (RESOLVE-09) | `getRowCandidates` gains a filter step |
| Hardcoded `"Imported"` hint prefix (Phase 44 Plan 01, D-09) | Source-aware `"Imported"`/`"Extracted"` per job | This phase (RESOLVE-10) | Supersedes 44-01/44-CONTEXT.md's D-09 uniform-copy decision, which was itself an explicit interim choice pending "real per-row provenance detection" — this phase resolves that at the job level (not per-field), still short of full per-field provenance |
| `"N/A - from tenure"` / `"N/A - tenure not found"` hint copy | `"Calculated from tenure"` / `"Tenure not found"` as an inline cell state, not an `Imported:`/`Extracted:` hint | This phase (RESOLVE-12) | Removes the argument-role hint's `CopyableExtractedValue` wrapper entirely for bench rows — it was never really an "extracted" value in the first place (D-08 already established there's no separate stored raw value) |
| `descriptor` forced null on any BENCH write (PJOB-15) | `descriptor` preserved, hidden only in UI | This phase (RESOLVE-13) | Reverses a Phase-25 decision (PJOB-15) explicitly cited in 44-01's own commit — flag this reversal in the plan's decision log, it is not an oversight, it is an intentional supersession |
| Continue button hidden until `allDispositioned` | Continue always visible, disabled with reason | This phase (RESOLVE-15) | Footer `{#if}` wrapper moves from gating the whole block to gating only the `disabled` attribute |

**Deprecated/outdated:**
- The `"✓ Corrected"` banner and `disposition === 'corrected'` branch
  (`[VERIFIED: app/src/lib/components/ResolveCard.svelte:699-709]`) are retired by
  RESOLVE-08's "remove the confirm/correct disposition state machine." Confirm at
  plan time whether `disposition` itself can be dropped from `RowMatchState` or
  must survive as an internal implementation detail feeding `matchesJson`'s payload
  shape (`{ raw_speaker_label, person_id }` — `[VERIFIED: app/src/lib/components/ResolveCard.svelte:280-290]`,
  which does not include `disposition`, only `personId`, so the field may already be
  purely internal/removable without touching the wire contract).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | An `is_justice`-less candidate found only in a stale `discrepancy.candidates` entry (never in the live `people` fetch) should fail open — shown in both side-filtered lists rather than hidden from both — is Claude's Discretion, not yet a locked decision | Pattern 1 / Pitfall 2 | If the planner locks a "hide" behavior instead and it's wrong, a legitimate pre-Phase-25 auto-match candidate could silently disappear from the search for an operator; low real-world likelihood since discrepancies and people share the same Person table, but not verified impossible for every historical row |
| A2 | `RowMatchState.disposition` can likely be simplified away once RESOLVE-08 removes the confirm/correct UI distinction, since `matchesJson`'s wire payload never includes it | State of the Art table | Low risk — worst case is dead code retained, not a functional bug; flagged so the planner doesn't assume it's load-bearing for the `?/resolve` submit contract without checking |
| A3 | The `<ResolveCard ... />` call site in `app/src/routes/admin/pipeline/[job_id]/+page.svelte` (not read this session) can accept a new `source` prop without other required changes | Pattern 4 | Low risk — this is a straightforward prop-threading change; if the parent component has an unusual prop-passing pattern, the planner should grep it directly before writing the task, since it was not verified this session |

## Open Questions

1. **Does `RowMatchState.disposition` need to survive RESOLVE-08's state-machine removal, or can it be deleted?**
   - What we know: the `?/resolve` submit payload (`matchesJson`) never serializes it — only `personId`.
   - What's unclear: whether any other internal branch (e.g. `s.disposition === 'corrected'` conditionally showing the "✓ Corrected" banner, which is itself being removed) is the *only* consumer, in which case the field becomes fully removable.
   - Recommendation: the planner should grep every remaining reference to `.disposition` after drafting the new single-dropdown markup, and delete the field from `RowMatchState` if nothing reads it — don't carry dead state forward by default.

2. **Should the People-directory-style `is_justice` filter treat `SideEnum.UNKNOWN`/gated rows (no side chosen yet) as "show all candidates" or "show none until a side is picked"?**
   - What we know: RESOLVE-09's canonical text says "filtered to the currently-selected side" — implying no side selected yet has no defined filter.
   - What's unclear: the exact gated-state UX the Figma mockup shows for the search input before a side is chosen (this research read the code, not the live Figma file/screenshots — node IDs `4205:81`/`4210:81`/`4206:111` were not visually inspected this session).
   - Recommendation: default to "show all candidates, unfiltered" when no side is chosen yet (matches today's gated-entry-point behavior of being fully inert until a side is picked, so filtering an inert control is moot) — but the planner/discuss-phase should confirm against the actual Figma frames if precision matters here.

## Environment Availability

Skipped — no new external tools/services/runtimes are required for this phase; all
work is in-repo (Svelte component, FastAPI service function, one SvelteKit load
function).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (`>=` version not pinned in `requirements.txt`; installed via `./.venv/Scripts/python.exe`) `[VERIFIED: STATE.md/44-SUMMARY files' verification commands]` |
| Config file | `tests/conftest.py` (sets `TEST_DATABASE_URL` redirect — must be an ancestor path of the invoked test paths, per 44-01/44-02/44-03's repeatedly-documented invocation quirk) |
| Quick run command | `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py -q` |
| Full suite command | `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests -q` |

No frontend test framework exists in this repo — confirmed by the existing test
file's own docstring: `[VERIFIED: api/tests/test_phase44_resolve_table_contract.py:8]`,
quoted: `No frontend test framework exists in this repo (see 39-RESEARCH.md /
36-PATTERNS.md), so a static source contract is the strongest automated gate
available.` This phase's frontend verification will continue that same pure
static-source-contract pattern (regex/string assertions against
`ResolveCard.svelte`'s raw text via `Path.read_text()`), not a new framework.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RESOLVE-07 | Exactly 4 `<th scope="col">`, side+person stacked in one `<td>` | unit (static source contract) | `pytest api/tests/test_phase44_resolve_table_contract.py::test_exactly_five_column_headers_declared` → **must be rewritten** to assert 4 | ✅ file exists, assertion needs rewrite |
| RESOLVE-08 | No `>Change<`/confirm-correct machinery remains | unit (static source contract) | new test in the same file | ❌ Wave 0 |
| RESOLVE-09 | `getRowCandidates` filters by `is_justice` | unit (static source contract) — cannot execute real filtering logic without a JS runtime, so assert the filter *expression* exists in source, e.g. `is_justice` appears inside the `getRowCandidates` function body | new test | ❌ Wave 0 |
| RESOLVE-10 | `prefixLabel` derives from a `source` prop, not hardcoded `"Imported"` | unit (static source contract) — assert zero remaining literal `prefixLabel="Imported"` occurrences | new test | ❌ Wave 0 |
| RESOLVE-11 | Live recompute — **backend regression test**, DB-gated | integration | new pytest in `api/tests/` — update a `CourtTenure` row after `list_resolve_rows_for_job` has already returned a value, re-call it, assert the new value appears (mirrors `test_phase44_argument_role_roundtrip.py`'s existing `_db_configured()` skipif pattern) | ❌ Wave 0 (DB-gated) |
| RESOLVE-12/14 | Exact copy strings `Calculated from tenure`/`Tenure not found`/`(resolve person first)` | unit (static source contract) | literal substring `grep -c` checks, following the established `>Bench<`/`>Change<` literal-match convention this file already uses | ❌ Wave 0 |
| RESOLVE-13 | Descriptor survives a bench round-trip (DB-gated) | integration | new pytest: PATCH side=BENCH, then PATCH side=PETITIONER again, assert `descriptor` unchanged throughout — extend `api/tests/test_admin_jobs_phase25.py` (already has a sibling test for the *old* force-null behavior at `test_update_resolve_row_advocate_descriptor_persists_bench_descriptor_forced_null`, per 44-01-SUMMARY.md D3 — that existing test's name/assertion is about to become **incorrect** and must be inverted, not just supplemented) | ✅ file exists, **existing test needs inversion**, not just addition |
| RESOLVE-15/16 | Progress copy, always-visible Continue, row tags | unit (static source contract) | new tests in the same file | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the relevant pytest file(s) touched by that task, no-DB-gate subset first
- **Per wave merge:** `pytest tests/conftest.py api/tests -q` (full suite, matching the exact invocation 44-01/02/03 all converged on after their shared documented quirk)
- **Phase gate:** full suite green, plus `npm --prefix app run check` (0 errors — the existing bar every prior 44-0x plan held itself to)

### Wave 0 Gaps
- [ ] Rewrite `api/tests/test_phase44_resolve_table_contract.py`'s five-column /
  `sideToggle` / `argumentRoleCell`-structural sections (see Pitfall 3) before
  adding new RESOLVE-07..16 sections — treat as one task, not an afterthought.
- [ ] **Invert, don't just supplement,**
  `api/tests/test_admin_jobs_phase25.py::test_update_resolve_row_advocate_descriptor_persists_bench_descriptor_forced_null`
  (name and assertion both describe the behavior RESOLVE-13 reverses).
- [ ] New DB-gated integration test proving live tenure recompute survives a
  post-resolve tenure correction (RESOLVE-11) — none exists today; the closest
  analog is `api/tests/test_phase44_argument_role_roundtrip.py`'s `_db_configured()`
  skipif pattern.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | yes (unchanged) | `X-Admin-Token` header, verified by the router-level dependency already in place (`verify_admin_token`) — no change this phase |
| V4 Access Control | yes (unchanged) | IDOR guards already in place and unaffected: `update_resolve_row_for_job` re-derives `argument_id` from `job_id` server-side and re-checks the participant belongs to that argument before any write (`[VERIFIED: api/services/admin_jobs.py:794-818]`) — the RESOLVE-13 fix only changes *which columns* are written, not the ownership check |
| V5 Input Validation | yes (unchanged) | `ResolveRowUpdate` schema's mass-assignment guard and `SideEnum` Pydantic coercion (already proven to reject out-of-enum values server-side per `test_phase44_argument_role_roundtrip.py::test_resolve_row_update_rejects_out_of_enum_side_value`) — the dropdown/toggle UI is a convenience, not the enforcement boundary; this remains true after the 4-column merge |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Stale/incorrect tenure-derived role silently displayed as authoritative on a published (public-adjacent) argument | Tampering (data integrity) | Already mitigated — confirmed live recompute on every read (Pattern 2 above); this phase should add the regression test in Wave 0 rather than introduce new mitigation code |
| Client-supplied `side`/`descriptor` bypassing the BENCH-forces-descriptor-null-or-preserved rule | Tampering | The rule enforcement stays server-side in `update_resolve_row_for_job` regardless of which direction the rule goes (force-null → preserve); no new client trust is introduced by the RESOLVE-13 fix, since the server still fully controls what gets written based on `body.side`, never trusting a client-supplied descriptor value when side is BENCH |
| `is_justice`-based filtering used as a client-side-only convenience being mistaken for an authorization boundary | Elevation of privilege (if misapplied) | Not applicable here — candidate filtering is a UX convenience over an already-authorized, already-fetched dataset (the operator can already see every person via the People directory); it must not be treated as a security control, and no plan task should frame it as one |

## Sources

### Primary (HIGH confidence — all read directly this session)
- `app/src/lib/components/ResolveCard.svelte` (full file, 949 lines)
- `app/src/lib/components/CopyableExtractedValue.svelte` (full file)
- `api/models/models.py` (full file, all 13 tables)
- `api/services/admin_people.py` (`_bench_role_and_missing_tenure`, `list_resolve_rows_for_job`, lines 880-1048)
- `api/services/admin_arguments.py` (`list_argument_speakers`, `get_argument_detail`, lines 200-450)
- `api/services/admin_jobs.py` (`get_job`, `list_jobs`, `update_resolve_row_for_job`, lines 1-300, 765-830)
- `api/services/speakers.py` (full file)
- `api/schemas/admin_jobs.py` (`AdminJobResponse`, `PersonResponse`, lines 43-131)
- `api/schemas/admin_people.py` (`PersonListItem`, `ResolveRow`, lines 91-400)
- `api/routers/admin.py` (relevant route handlers, lines 600-700)
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` (full file, 612 lines)
- `app/src/lib/components/CreatePersonPopover.svelte` (first 60 lines)
- `pipeline/commands/resolve.py` (lines 150-290)
- `.planning/phases/44-resolve-table-rework/44-FIGMA-RECONCILE.md`, `44-CONTEXT.md`, `44-PATTERNS.md`, `44-01/02/03-SUMMARY.md`
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`
- `api/tests/test_phase44_resolve_table_contract.py` (first 100 lines + full function-name listing)
- `alembic/versions/` directory listing (head confirmed at `0025_rename_participant_title_to_descriptor.py`)
- `app/package.json`, `requirements.txt` (version verification)

### Secondary (MEDIUM confidence)
- None — this research relied entirely on direct source reads, no web search was needed since the domain is fully internal to this codebase.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new stack, all versions verified against `package.json`/`requirements.txt`.
- Architecture: HIGH — every claim about data flow and live-vs-snapshot derivation was verified by reading the actual service-layer source, not inferred.
- Pitfalls: HIGH — all four pitfalls are grounded in specific line numbers of existing code or existing test assertions that will need to change.

**Research date:** 2026-08-04
**Valid until:** 30 days (stable internal codebase; only invalidated by an unrelated Phase 45+ change to the same files before this phase executes)
