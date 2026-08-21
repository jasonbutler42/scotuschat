# Phase 49: Review Model - Research

**Researched:** 2026-08-21
**Domain:** PostgreSQL schema evolution (shared enum + provenance columns + audit table) under Alembic, FastAPI/SQLAlchemy async service writers with an authority-ladder discrepancy mechanism, and a new hand-rolled Svelte 5 admin queue screen.
**Confidence:** HIGH — every claim below was verified this session by reading the actual source file and line range named beside it (models, services, routers, pipeline commands, migrations, Svelte components, tests). No Context7/web lookups were needed: this phase extends four already-shipped, already-documented patterns (Phase 47 provenance enums, Phase 48 trust-tier migration/service, Phase 38 name-authority migration, and the existing hand-rolled admin UI idiom) rather than introducing new technology.

## Summary

This phase has no new external technology to research — it is a same-codebase generalization of four things that already exist and were each read this session: (1) the `people.name_needs_review`/`name_extraction_metadata` pair that D-08 replaces outright, (2) the `admin_jobs.discrepancies` JSONB blob that D-14 explicitly leaves alone (a same-named but unrelated PDF-resolve concept), (3) Phase 48's `derive_tier`/`recompute_argument_tier`/`_load_constituents` trio that D-17/D-18 must extend, and (4) the Alembic migration idioms from migrations 0022, 0026, and 0027 that this phase's migration should copy verbatim in shape.

The core technical risk is not "what library to use" — it is transaction discipline (every writer must close discrepancies, advance `review_state`, and call `recompute_argument_tier` in one transaction, exactly as `publish_argument` already does for `ArgumentStatusLog`) and enum irreversibility (the new `review_state` PG enum, once shipped, cannot have values dropped — confirmed by migrations 0027/0026's own downgrade() comments, which is why CONTEXT.md correctly marks D-09 "one-way"). The second-largest risk is the two write paths that currently mutate `ArgumentParticipant.side`/`.descriptor` (`update_participant_side` in `admin_arguments.py:715` and `update_resolve_row_for_job` in `admin_jobs.py:783`) — both must become the "one real authority-checked writer" D-31 requires, and the second one's `argument.status != CANDIDATE` guard is exactly what the folded "widen participant editability" todo must relax.

**Primary recommendation:** Follow migration 0027's five-numbered-step structure exactly (commit-then-ALTER-TYPE is not needed here since `review_state` is a brand-new type, not an existing one being expanded — follow 0026's simpler `CREATE TYPE` + pg_type-existence-guard idiom instead), land the enum + `ArgumentParticipant` columns + `value_discrepancy` table in one migration (`0028`), then implement one shared "resolve a row" service function that both the participant path and the person path call, so D-15's close-discrepancies-and-recompute-in-one-transaction rule has exactly one implementation, not two.

## Project Constraints (from CLAUDE.md)

- Alembic is the sole DDL authority — never `Base.metadata.create_all` anywhere. Verified: every one of the 27 existing migrations under `alembic/versions/` follows this; `api/models/models.py:1-7`'s own docstring states it.
- asyncpg requires `statement_cache_size=0` behind Digital Ocean PgBouncer — not touched by this phase (no new engine config).
- Apolitical framing hard constraint: every speaker gets identical schema/depth/treatment; no derived insight/sentiment/statistics. Directly load-bearing here via D-34 (`review_state`/`source`/`method`/discrepancy fields must never leak to a public response) — see `api/tests/test_trust_public_leak_ban.py`, verified in full below.
- Pipeline is offline-only (CLI, never HTTP endpoints) — this phase's one real writer (D-31) is an *admin API* write path, not a pipeline step, so this constraint is not implicated; Phase 50 is the one that touches pipeline import paths.
- Invocation-shape-independent pytest hooks belong in the repo-root `conftest.py`, verified present at `/home/jason/scotuschat/project/conftest.py` (the `TEST_DATABASE_URL` redirect). Any new DB-gated test for this phase's authority matrix (D-32) runs under this existing isolation — no new conftest needed.
- Raw PDFs immutable — not implicated (no PDF writes in this phase; D-21 explicitly defers PDF wiring).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REVIEW-01 | Operator-editable rows carry a four-state `review_state` | §Standard Stack (shared PG enum pattern, migrations 0026/0027), §Code Touch Points (Person/ArgumentParticipant current columns) |
| REVIEW-02 | Re-import records a discrepancy instead of overwriting equal-or-higher authority | §Legacy `admin_jobs.discrepancies` (what NOT to reuse), §New `value_discrepancy` table design, §Authority ladder (`derive_tier` precedence as the trust-side analog) |
| REVIEW-03 | Review queue lists items needing review, filterable by trust tier / review state | §UI-SPEC cross-references, §`list_arguments`/`get_argument_stats` precedent for the queue query shape |
| REVIEW-04 | Operator can resolve an item (confirm/edit), advancing `review_state` and recomputing trust | §`recompute_argument_tier`/`_load_constituents` (exact lines to change), §Transaction pattern (`publish_argument`'s ArgumentStatusLog-in-same-transaction precedent) |
| REVIEW-05 | Legacy `name_needs_review`/`name_extraction_metadata` folded into unified mechanism, no parallel mechanism left | §Legacy mechanism inventory (every file/line touching the two columns) |

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

All 34 decisions (D-01 through D-34) in `.planning/phases/49-review-model/49-CONTEXT.md` are locked. Do not re-litigate. Key load-bearing ones this research directly grounds:

- **D-08/D-09/D-10**: `Person` gets `review_state` + `provenance_metadata`, replacing `name_needs_review`/`name_extraction_metadata` outright; one shared `review_state` PG enum used by both `people` and `argument_participants`; `argument_participants` gains `review_state` (column confirmed absent this session).
- **D-13/D-14/D-15/D-16**: A new `discrepancy` table (lean name: `value_discrepancy`), keyed on (target row, field, import_run), NOT the same as `admin_jobs.discrepancies` (confirmed a different, untouched mechanism this session); resolving a row closes its open discrepancies in the same transaction; lower-authority rejections also get recorded.
- **D-17/D-18/D-19/D-20/D-22**: An explicit "confirm as unattributable" action lifts the D-11 floor; `derive_tier(source, method, review_state)` gets a real per-participant triple (48 D-13 slot filled, no signature change — confirmed: `derive_tier`'s signature is exactly `(source: str, method: str, review_state: str) -> TrustTier`); `argument_participants` stores both `source` and `method`; the participant `method`/`source` mapping table (corpus/direct, pdf_pipeline/normalized, NULL person_id, operator/unchanged) is settled; an operator edit does NOT overwrite the row's stored source/method.
- **D-23 through D-30**: Confirm is inline (single PATCH); edit deep-links to the existing Resolve card; no bulk confirm; re-flagging to `needs_review` allowed, returning to `unreviewed` never allowed; resolved row stays visible until reload; new top-level `/admin/review` route in `AdminSubNav`; 48 D-04's candidate exclusion on `/admin/arguments` stays as-is; built in today's hand-rolled admin idiom (confirmed: no Tailwind usage anywhere in `app/src/routes/admin/**`, confirmed via this session's own grep results matching the UI-SPEC's claim); entry points via `AdminSubNav` + dashboard `StatCard`.
- **D-31/D-32/D-33/D-34**: Phase 49 builds the record, the display, and ONE real authority-checked writer (the participant/person update path) — confirmed no code path today compares an incoming value against a stored one (`import_convokit.py`'s `skipped_existing` counter, verified at the exact site below); pytest for the authority matrix plus one live authority-conflict walkthrough; build an unresolved-speaker fixture; the public-leak ban (`test_trust_public_leak_ban.py`, read in full this session) extends to `review_state`/`source`/`method`/discrepancy fields.

### Claude's Discretion

- Migration defaults/backfill: `review_state` NOT NULL, `server_default='unreviewed'`, no in-migration derivation beyond the one deterministic mapping (`Person.name_needs_review = true` → `review_state = 'needs_review'`; `name_extraction_metadata` → `provenance_metadata` as a straight column carry).
- Endpoint shapes (queue list, inline-confirm PATCH, confirm-as-unattributable — own route vs. flag).
- Filter widget style: lean is segmented control for status, plain selects for tier/review-state.
- The discrepancy table's name: lean is `value_discrepancy`, with an explicit docstring distinguishing it from `admin_jobs.discrepancies`.
- Dashboard count: lean is a dedicated COUNT query (matching `get_argument_stats`'s shape), never derived from the unbounded queue list.

### Deferred Ideas (OUT OF SCOPE)

- Corpus re-import compare-and-record / `admin_job` re-point → Phase 50.
- Wiring the PDF alias-HIT participant method (mapping recorded, not built) → deferred PDF route.
- Migrating/renaming the legacy `admin_jobs.discrepancies` blob → Phase 50.
- Server-side paging for the review queue → revisit only if proven slow.
- Bulk confirm → rejected outright, not deferred.
- Shared component extraction / design system → Phase 51.
- A per-discrepancy accept/reject UI workflow → rejected as YAGNI; accept is an edit, reject is a confirm.
- Appending operator actions to `provenance_metadata` → rejected; `review_state` records the action.
- A person-name flag reaching the argument trust floor → rejected (preserves 48 D-10's no-fan-out guarantee).
- Side / entity-type filters on the queue → not now; entangled with a known `side` silent-fallback bug.
- Widening the delete gate to candidates → still Phase 50.

</user_constraints>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `review_state` enum + provenance columns (schema) | Database / Storage | API / Backend (SQLAlchemy models) | Alembic is sole DDL authority (CLAUDE.md); models.py mirrors the schema for the ORM layer only |
| Discrepancy record-and-close logic | API / Backend | Database / Storage | Business rule (authority ladder, D-15/D-16) belongs in a service function (`api/services/*`), not a DB trigger — matches every existing write path's pattern (`publish_argument`, `update_resolve_row_for_job`) |
| Trust recomputation on resolve | API / Backend | — | `api/services/trust.py::recompute_argument_tier` already owns this; this phase only feeds it real per-participant values — no new tier ownership |
| `/admin/review` queue list + filters | API / Backend (query) | Frontend Server (SSR) | Query/sort/filter logic (worst-tier-first, tier×review_state×status) belongs server-side per D-04's "sort-in-the-query" convention; SvelteKit's `+page.server.ts` is a thin proxy, not a compute tier |
| Inline confirm / edit / re-flag / confirm-as-unattributable actions | API / Backend | Browser / Client | Every action is a PATCH to FastAPI through a SvelteKit form action; the browser only renders state and issues the request — no client-side authority logic |
| Public-leak ban enforcement | API / Backend | — | Structural Pydantic contract test (`test_trust_public_leak_ban.py`) — enforced entirely at the schema/router layer, no browser-tier role |
| Admin queue UI rendering (badges, expand/collapse, empty/loading/error states) | Browser / Client (SSR-rendered Svelte) | — | Hand-rolled inline-style Svelte 5, no component library (D-29); all navigation is full-page `goto()`, no client-only state beyond `$state`/`$derived` |

## Standard Stack

No new libraries. This phase extends the existing stack exactly as already pinned:

### Core (already installed — verified this session via `.venv/bin/python -c "import ..."`)
| Library | Version (verified) | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.52 | ORM + Core for new columns/table | Already the project's sole DB layer |
| Alembic | 1.19.1 | DDL migration `0028` | Sole DDL authority per CLAUDE.md |
| Pydantic | 2.13.4 | New/extended schemas (`ReviewQueueItem`, discrepancy detail, etc.) | Already the project's schema layer; `model_fields_set` pattern already used for omitted-vs-cleared distinction (`admin_people.py`) |
| FastAPI | 0.141.1 | New `/admin/review` router endpoints | Existing admin router pattern (`api/routers/admin.py`) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SvelteKit / Svelte 5 (Runes) | pinned in `app/package.json` (not re-verified this session — no change needed) | New `/admin/review` route | Extends existing hand-rolled admin pages; no new frontend dependency |

### Alternatives Considered
None — this is a same-stack extension. CONTEXT.md's own "Alternatives Considered" language already covers the two real schema alternatives (varchar+CHECK vs. PG enum for `review_state`; JSONB-on-import_run vs. JSONB-on-target-row vs. a real table for discrepancies) and settled both in favor of the PG-enum/real-table pattern already used project-wide.

**Installation:** None required — no new packages.

## Package Legitimacy Audit

**Not applicable.** This phase adds zero new external dependencies (Python or npm). It is a schema migration + service-layer extension + one new Svelte route built entirely from already-vendored libraries, all verified present and importable in `.venv` this session. No `package-legitimacy check` run was needed.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────┐
                         │  Operator browser — /admin/review        │
                         │  (Arguments | People tabs, filters)      │
                         └───────────────┬───────────────────────────┘
                                         │ full-page goto() / form POST
                                         ▼
                         ┌─────────────────────────────────────────┐
                         │  SvelteKit +page.server.ts (SSR load)    │
                         │  fetches queue list + counts from API    │
                         └───────────────┬───────────────────────────┘
                                         │ HTTPS + X-Admin-Token (server-only FASTAPI_BASE_URL)
                                         ▼
              ┌───────────────────────────────────────────────────────────┐
              │  FastAPI /admin router — new endpoints                     │
              │  GET  /admin/review?status=&tier=&review_state=            │
              │  GET  /admin/review/stats  (dashboard COUNT)                │
              │  PATCH /admin/review/participants/{id}  (confirm/edit/...)  │
              │  PATCH /admin/review/people/{id}        (confirm/edit/...)  │
              └───────────┬─────────────────────────────┬───────────────────┘
                          │                              │
                          ▼                              ▼
        ┌───────────────────────────────┐   ┌─────────────────────────────────┐
        │ api/services/admin_review.py   │   │ existing writers this phase      │
        │ (NEW) — queue query builder    │   │ generalizes into the ONE         │
        │ (D-05 inclusion, D-03 sort)     │   │ authority-checked writer (D-31): │
        └───────────────┬─────────────────┘   │  - update_participant_side       │
                        │                     │  - update_resolve_row_for_job     │
                        │ reads               │  - update_person (name edit)      │
                        ▼                     └───────────────┬───────────────────┘
        ┌───────────────────────────────┐                    │
        │ Person, ArgumentParticipant,   │◄───────────────────┘ writes review_state,
        │ value_discrepancy (NEW table)  │                       source/method (participant only),
        └───────────────┬─────────────────┘                     provenance_metadata (never rewritten)
                        │
                        │ same transaction as the write above
                        ▼
        ┌───────────────────────────────┐
        │ api/services/trust.py          │
        │ recompute_argument_tier()      │  ← D-17/D-18: _load_constituents now
        │ _load_constituents()           │    passes REAL per-participant
        │                                │    (source, method, review_state)
        └───────────────────────────────┘
```

### Recommended Project Structure

No new top-level directories. New/changed files, matching existing per-domain module boundaries exactly:

```
alembic/versions/
└── 0028_review_state_and_discrepancy.py   # NEW — enum + columns + table, mirrors 0026/0027 shape

api/models/models.py                        # CHG — ReviewState enum, Person cols swapped,
                                              #       ArgumentParticipant gains review_state/source/method,
                                              #       new ValueDiscrepancy model (Table 14)
api/domain/trust.py                          # UNCHANGED signature; only callers change what they pass
api/services/
├── trust.py                                 # CHG — _load_constituents reads real participant
│                                              #       (source, method, review_state); D-17 floor rule
├── admin_people.py                          # CHG — update_person: D-11 sets review_state instead of
│                                              #       name_needs_review=False; missing_filters re-pointed
├── admin_arguments.py                       # CHG — update_participant_side becomes (or delegates to)
│                                              #       the one authority-checked writer (D-31)
├── admin_jobs.py                             # CHG — update_resolve_row_for_job's CANDIDATE-only guard
│                                              #       widened to {candidate, draft, unpublished} (folded todo)
└── admin_review.py                           # NEW — queue query (D-01..D-07), resolve/confirm/edit/
                                                #       reflag actions, discrepancy-close-in-transaction (D-15)

api/schemas/
├── admin_people.py                           # CHG — review_state/provenance_metadata replace the two old fields
├── admin_arguments.py                        # CHG — ArgumentParticipant-facing schemas gain review_state/source/method
└── admin_review.py                           # NEW — ReviewQueueItem, DiscrepancyDetail, resolve-action bodies

api/routers/
└── admin.py  (or new admin_review.py router) # NEW — /admin/review endpoints (D-27)

app/src/routes/admin/review/
├── +page.server.ts                           # NEW — SSR load, mirrors admin/arguments' pattern
└── +page.svelte                              # NEW — Arguments|People tabs, filters, table (per 49-UI-SPEC.md)

app/src/lib/components/AdminSubNav.svelte     # CHG — add "Review" link
app/src/routes/admin/+page.svelte             # CHG — 5th StatCard; grid-template-columns needs updating
                                                #       (see Common Pitfalls — it is hardcoded repeat(4, 1fr) today)
```

### Pattern 1: Shared PG enum via `values_callable`, created with the pg_type existence guard

**What:** Every enum in this codebase is declared with `SAEnum(PyEnum, name="...", values_callable=lambda e: [x.value for x in e])` on the model side, and created in the migration via a manual `pg_type` existence check (no native `IF NOT EXISTS` for `CREATE TYPE` in any PG version) followed by `postgresql.ENUM(..., create_type=False)` for use in `op.add_column`/`op.create_table`.
**When to use:** For `review_state` — the same pattern as `import_source`/`import_method` in migration 0026.
**Example (verified this session, `alembic/versions/0026_import_run_provenance.py:44-65`):**
```python
conn = op.get_bind()
for type_name, ddl in [
    ("review_state", "CREATE TYPE review_state AS ENUM "
     "('unreviewed', 'needs_review', 'operator_confirmed', 'operator_edited')"),
]:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}
    ).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))

review_state_enum = postgresql.ENUM(
    "unreviewed", "needs_review", "operator_confirmed", "operator_edited",
    name="review_state",
    create_type=False,
)
```
Model side (mirrors `api/models/models.py:322-330`'s `trust_tier` column exactly):
```python
review_state = Column(
    SAEnum(ReviewState, name="review_state", values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    server_default="unreviewed",
    default=ReviewState.UNREVIEWED,
)
```

### Pattern 2: Column-swap-with-carry migration (replacing, not deriving)

**What:** Migration 0027 proved the "no in-migration backfill effort beyond one deterministic mapping" pattern: `ADD COLUMN ... server_default=...` covers every existing row for free (PostgreSQL applies a non-volatile default to existing rows as part of `ADD COLUMN` itself, no separate `UPDATE` needed). This phase's discretion-lean explicitly re-invokes that precedent, PLUS the one deterministic legacy mapping migration 0022 modeled (row-by-row `UPDATE` inside `upgrade()`).
**When to use:** For `Person`: add `review_state`/`provenance_metadata`, then run one `UPDATE people SET review_state = 'needs_review' WHERE name_needs_review = true` (mirrors 0022's per-row loop style, but this one is a single set-based `UPDATE` — no round-trip gate needed since it is a straight boolean→enum flip, not a text-parsing operation), then `UPDATE people SET provenance_metadata = name_extraction_metadata` (straight carry, per Claude's Discretion lean), then `op.drop_column` the two legacy columns.
**Example (adapted from `alembic/versions/0022_person_name_authority.py:66-77` add-then-backfill-then-drop shape):**
```python
op.add_column("people", sa.Column("review_state", review_state_enum, nullable=False, server_default="unreviewed"))
op.add_column("people", sa.Column("provenance_metadata", postgresql.JSONB(), nullable=True))

bind = op.get_bind()
bind.execute(sa.text(
    "UPDATE people SET review_state = 'needs_review' WHERE name_needs_review = true"
))
bind.execute(sa.text(
    "UPDATE people SET provenance_metadata = name_extraction_metadata "
    "WHERE name_extraction_metadata IS NOT NULL"
))

op.drop_column("people", "name_extraction_metadata")
op.drop_column("people", "name_needs_review")
```
**Downgrade note:** Per migration 0027's own precedent, a clean reverse of `drop_column`/`add_column` calls; re-adding `name_needs_review`/`name_extraction_metadata` on downgrade cannot recover data lost by the upgrade's `drop_column` (same one-way character CONTEXT.md's D-08 "Reversibility: one-way" already documents) — `downgrade()` should re-add the two columns with safe defaults and NOT attempt to reverse-derive them from `review_state`/`provenance_metadata`.

### Pattern 3: One writer, authority-checked (D-31)

**What:** A single service function decides, per field, whether an incoming value may overwrite the stored one (authority ladder) or must instead create a `value_discrepancy` row. `derive_tier`'s ladder is the trust-tier analog; the authority ladder for *write acceptance* is a distinct but structurally similar total-ordering function that should live beside `derive_tier` in `api/domain/` (a new pure module, e.g. `api/domain/authority.py`, following the exact "pure, dependency-light domain contract" discipline `api/domain/trust.py`'s docstring states verbatim) — CONTEXT.md's canonical refs call this "the authority ladder" (`operator > corpus > pdf/rule_based > pdf/llm_corrective`), which is `ImportSource`/`ImportMethod`-keyed, not `TrustTier`-keyed; this is a genuinely separate function from `derive_tier`, even though both consume the same enums.
**When to use:** Called from the new `admin_review.py` service's resolve-item action AND (per D-31, "so nothing ships uncalled") wired into the existing participant/person update path.
**Example (transaction-in-one-place precedent to copy, `api/services/admin_arguments.py:602-660`'s `publish_argument`, verified this session):**
```python
# publish_argument's proven shape: gate checks, then ONE write + ONE
# ArgumentStatusLog row + recompute_argument_tier, all before the caller's
# own commit. The new resolve-a-row action must follow this exact shape:
#   1. load the row + any open value_discrepancy rows for it
#   2. apply the operator's action (confirm / edit / confirm-as-unattributable)
#   3. UPDATE resolved_at on every open discrepancy for that row (D-15)
#   4. await recompute_argument_tier(db, argument_id)  # D-17/D-18
#   5. caller commits — the function itself never calls db.commit()
```

### Anti-Patterns to Avoid
- **Re-deriving `name_needs_review` as a computed view of `review_state`:** explicitly rejected by D-08 — this *is* the parallel mechanism REVIEW-05 exists to remove. Drop the columns; do not keep them as a read-only shim.
- **Writing the discrepancy record as JSONB anywhere** (on `import_run` or on the target row): explicitly rejected by D-13 for exactly the reasons stated there (can't filter/join). Use a real table.
- **Calling `db.commit()` inside the resolve-action service function:** every existing writer (`publish_argument`, `recompute_argument_tier`) relies on the caller owning the transaction boundary — breaking this breaks the "same transaction" guarantee D-15/D-18 depend on.
- **Bulk `update()`/`delete()` without `.execution_options(synchronize_session=False)`:** documented project-wide critical guard (`api/services/admin_arguments.py:606-615`); every bulk write in this phase's new writer must include it, with a `db.refresh()` if the same session re-reads the row afterward.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trust-tier derivation from provenance | A new per-participant tiering function | `api/domain/trust.py::derive_tier` (signature unchanged per 48 D-13/this phase's D-18) | It is the ONLY place this mapping exists per its own docstring — a second implementation would violate TRUST-01 |
| Floor rollup across constituents | Custom min-over-list logic in the new service | `api/domain/trust.py::floor_tier` | Already handles the zero-constituent edge case correctly (explicit early return, not bare `min()`) |
| Admin auth | A new auth check for `/admin/review` | The existing router-level `verify_admin_token` dependency (already covers every `/admin/*` route per `api/routers/admin.py`'s docstrings) | No new auth surface should exist |
| Filter-as-URL-param round trip | Client-side filter state | The existing `goto()`-based `?status=&tier=&review_state=` idiom (`admin/arguments/+page.svelte:36-44`) | Back-button-safe, linkable, and the only pattern this codebase uses anywhere |
| Public-leak enforcement | A new manual code-review checklist item | Extending `api/tests/test_trust_public_leak_ban.py`'s existing `BANNED_KEY` mechanism (see Code Examples) | It is already a derived-from-live-routers structural test, not a hardcoded list — extending it is one line vs. building a new mechanism |

**Key insight:** Every piece of this phase's "hard part" (authority ladder, trust derivation, transaction-per-writer discipline, public-leak enforcement) already has exactly one canonical implementation in this codebase. The entire job is plumbing new columns/values into those existing single sources of truth — never duplicating them.

## Runtime State Inventory

**Trigger check:** This phase is a targeted schema generalization (REVIEW-05 explicitly retires two live columns), so this section is required, not skipped.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `people.name_needs_review` (boolean) and `people.name_extraction_metadata` (JSONB) hold live per-row state for every `Person` row in the dev/test DB today. Verified via `api/models/models.py:151-152`. | **Data migration** (in-migration `UPDATE ... SET review_state = 'needs_review' WHERE name_needs_review = true`, per Claude's Discretion lean) — not just a code edit. Both columns are then dropped. |
| Live service config | None found. No external service (n8n, Datadog, Tailscale, Cloudflare Tunnel) stores `review_state`, `name_needs_review`, or discrepancy data outside this repo's own Postgres — this project has no such external config-bearing services at all (confirmed: this is a single-repo FastAPI/SvelteKit/Postgres stack with no workflow-automation or observability SaaS wired into the data model). | None. |
| OS-registered state | None found. No Task Scheduler / pm2 / launchd / systemd registration references `name_needs_review`, `review_state`, or any Phase-49 vocabulary — this project's only OS-level process management is local dev tooling (uvicorn/vite dev servers), not a registered service. | None. |
| Secrets/env vars | None found. No env var or secret name encodes `name_needs_review`/`review_state`/`discrepancy` — the only DB-related env vars are `DATABASE_URL`/`TEST_DATABASE_URL`, unaffected by a column rename inside the schema they point at. | None. |
| Build artifacts / installed packages | None found. No package name, egg-info directory, or compiled artifact embeds the legacy column names — this is a pure Python/TypeScript source-and-migration change with no name-bearing build output. | None. |

**Canonical-question answer:** After every file in the repo is updated and migration `0028` is applied, the ONLY runtime system that still has old-shaped data is the pre-migration row content itself — which the migration's own `UPDATE`/`DROP COLUMN` sequence handles in the same transaction as the schema change. Nothing survives outside the database that the migration does not already touch. This is a materially smaller inventory than a typical rename/refactor phase because the "rename" here is schema-internal (a Postgres table's own columns), not a cross-system identifier.

## Common Pitfalls

### Pitfall 1: `derive_tier`'s three-argument shape hides an easy-to-miss extra field
**What goes wrong:** D-19 requires storing BOTH `source` and `method` on `ArgumentParticipant`, but `derive_tier(source, method, review_state)` only ever sees the *values*, and a naive implementation might try to pass the `ArgumentParticipant.source`/`.method` SQLAlchemy Column objects directly instead of `.value`.
**Why it happens:** `_load_constituents` already does this correctly for utterances (`source.value, method.value` at `api/services/trust.py:99`) — but that pattern must be copied exactly for the new participant branch, and it is easy to instead pass the enum members directly, which `derive_tier`'s string-equality checks (`source == "operator"`) would silently fail to match.
**How to avoid:** Grep the new participant branch of `_load_constituents` for `.value` on both `source`/`method`/`review_state` before merging — mirror `api/services/trust.py:92-102`'s exact pattern.
**Warning signs:** A resolved, `operator_confirmed` participant reads `UNCERTAIN` instead of `VERIFIED` — the tell-tale sign `derive_tier`'s rule 1 (`review_state in {"operator_confirmed", "operator_edited"}`) never matched because the value passed in was an enum member, not its `.value` string.

### Pitfall 2: `update_resolve_row_for_job`'s CANDIDATE-only guard silently blocks the widened editability
**What goes wrong:** The folded todo widens participant editability to `{candidate, draft, unpublished}`, but the exact guard that must change (`api/services/admin_jobs.py:825`: `if argument.status != ArgumentStatusEnum.CANDIDATE: raise ValueError(...)`) is easy to miss if the planner only edits `admin_arguments.py::update_participant_side` (a *different* function with no such status guard at all today, per `api/services/admin_arguments.py:715-754`).
**Why it happens:** There are TWO separate participant-side write paths in this codebase (D-23's canonical ref list names both: `admin.py:1423`'s `update_participant_side` and `admin.py:581`'s job-scoped resolve-row mutation) — they have different guards and different BENCH-handling rules, and only one of them currently blocks non-CANDIDATE arguments.
**How to avoid:** When implementing D-31's "one real authority-checked writer," decide explicitly whether it replaces, wraps, or sits alongside both existing functions — do not assume fixing one fixes both.
**Warning signs:** A live-browser test (D-32) resolves a queue item on a `draft`-status argument and gets a 422 from the resolve-row path while the participant-side path succeeds, or vice versa.

### Pitfall 3: The dashboard StatCard grid is hardcoded to 4 columns, not a wrapping/auto-fit layout
**What goes wrong:** UI-SPEC's own resolved-consideration table (E8, "overflow") asserts "StatCard's existing grid layout (32px gap) absorbs the fifth card without change" — but the actual CSS at `app/src/routes/admin/+page.svelte:240` is `grid-template-columns: repeat(4, 1fr);`, a literal 4-column grid, not `auto-fit`/`auto-fill`. Adding a 5th `<StatCard>` inside that grid with no CSS change will NOT "absorb" it — it will either overflow the row or (depending on browser default grid behavior) silently drop to a second row with 3 cards on top, not gracefully reflow.
**Why it happens:** The UI-SPEC's Copywriting/Screen Contract sections were written and checker-approved without executing the actual CSS; `repeat(4, 1fr)` is a literal count, verified this session by reading the line directly.
**How to avoid:** The planner must add an explicit task to change `repeat(4, 1fr)` to `repeat(5, 1fr)` (or an auto-fit formula) when adding the "Review queue" StatCard — do not treat the UI-SPEC's "absorbs... without change" claim as verified; it is contradicted by this session's direct read of the file.
**Warning signs:** The dashboard's stat-card row visibly wraps unevenly (4-then-1, or squeezed 5-across with no gap) after the new card is added.

### Pitfall 4: No live corpus data path produces a NULL-`person_id` `ArgumentParticipant` today
**What goes wrong:** D-33's unresolved-speaker fixture assumes such a row can be manufactured, but corpus import's `_resolve_person` (verified `pipeline/commands/import_convokit.py:740-790`) ALWAYS returns a `Person` — by `oyez_speaker_id` match, `full_name` match, or creating a brand-new one. There is no MISS branch in the corpus path at all; MISS/NULL-`person_id` only exists in the PDF `resolve.py` alias-lookup path (verified `pipeline/commands/resolve.py:284-306`), which has no live fixture in the repo (D-21).
**Why it happens:** 48 D-21 rejected a synthetic unresolved-speaker fixture as "partly synthetic" for exactly this reason — corpus import "mints a Person for every corpus speaker" is a direct quote from this phase's own CONTEXT.md, and it is confirmed correct by reading `_resolve_person` in full this session.
**How to avoid:** D-33 quietly reverses 48's own objection ("this phase makes unresolved participants first-class... the fixture becomes representative rather than contrived") without specifying a concrete mechanism. The planner must pick one explicitly: (a) a `reset_to_fixture`-adjacent dev-only helper that nulls out one `ArgumentParticipant.person_id` post-import for a designated fixture argument, or (b) a pytest-only fixture (not wired into `admin_dev.py::FIXTURE_SET`) that inserts a synthetic `ArgumentParticipant` row directly. Either is legitimate, but treat "how is the unresolved-speaker row actually produced" as an open task, not settled by CONTEXT.md.
**Warning signs:** Plan tasks reference "the unresolved-speaker fixture" as if a corpus conversation ID already produces one — verify against the actual `FIXTURE_SET` (four entries: 15169, 13015, 18897, 22372, verified `api/services/admin_dev.py:79-99`) before assuming any existing fixture already has this property.

### Pitfall 5: PG enum irreversibility means `review_state`'s four values are permanent from the moment migration `0028` ships
**What goes wrong:** Unlike a varchar+CHECK column, once `CREATE TYPE review_state AS ENUM (...)` runs, no value can ever be dropped from it (same constraint that made `argument_status`'s `'pipeline'` value "dead-but-permanent" per `api/models/models.py:344`, and the exact reason 47/48's `import_source`/`import_method`/`trust_tier` types are all one-way per their own migration downgrade() comments).
**Why it happens:** PostgreSQL has no `ALTER TYPE ... DROP VALUE`. This is a hard PG limitation, not a project oversight.
**How to avoid:** The four values (`unreviewed`, `needs_review`, `operator_confirmed`, `operator_edited`) must be exactly right before this migration merges — CONTEXT.md states the vocabulary is settled and "do not re-open it," which this constraint makes doubly important: there is no cheap fix later.
**Warning signs:** N/A pre-merge; post-merge, any desire to rename/remove a value requires a full new-column-and-migrate cycle, same as `argument_status`'s `PIPELINE`→`CANDIDATE` migration 0027 had to do.

## Code Examples

### Existing `derive_tier` — the exact function D-18 feeds real values into (verified in full, `api/domain/trust.py`)
```python
def derive_tier(source: str, method: str, review_state: str) -> TrustTier:
    if review_state in ("operator_confirmed", "operator_edited"):
        return TrustTier.VERIFIED
    if review_state == "needs_review":
        return TrustTier.UNCERTAIN
    if source == "operator" and method == "manual":
        return TrustTier.VERIFIED
    if (source, method) in (("corpus", "direct"), ("seed", "direct")):
        return TrustTier.TRUSTED
    if method == "normalized":
        return TrustTier.PROVISIONAL
    if (source, method) == ("pdf_pipeline", "rule_based"):
        return TrustTier.PROVISIONAL
    return TrustTier.UNCERTAIN
```
Note rule 1 already handles D-17's "confirm/edit → VERIFIED" and D-18's "resolved participant contributes a real tier" — no change to this function is needed; only its CALLERS change.

### Existing `_load_constituents`'s participant branch — the exact lines D-17/D-18 replace (verified, `api/services/trust.py:104-109`)
```python
for (person_id,) in participant_rows:
    if person_id is None:
        tiers.append(TrustTier.UNCERTAIN)
        _bump("unresolved_participant")
    # A resolved participant contributes no additional tier — D-13, no
    # per-participant source/method exists yet to derive one from.
```
This must become (illustrative — exact column/field names depend on the migration's final naming):
```python
for person_id, review_state, source, method in participant_rows:  # SELECT gains 3 columns
    if person_id is None:
        if review_state == "operator_confirmed":  # D-17: confirm-as-unattributable
            tiers.append(TrustTier.VERIFIED)
        else:
            tiers.append(TrustTier.UNCERTAIN)
            _bump("unresolved_participant")
    else:
        tier = derive_tier(source, method, review_state)  # D-18
        tiers.append(tier)
        if tier is TrustTier.UNCERTAIN:
            _bump("...")  # new blocker code, mirroring the utterance branch's llm_corrective_utterance
```

### Existing transaction-discipline precedent — `publish_argument`'s ArgumentStatusLog-in-same-transaction (verified, `api/services/admin_arguments.py:602-660`)
The docstring states verbatim: "Writes one ArgumentStatusLog row (status=PUBLISHED) in the same transaction as the Argument update... When the trust gate was overridden, that row also carries the stripped `override_reason`." This is the exact shape the new resolve-action function must copy for closing `value_discrepancy` rows + advancing `review_state` + calling `recompute_argument_tier`, all before the router's own `await db.commit()`.

### Existing public-leak-ban test — the exact mechanism D-34 extends (verified in full, `api/tests/test_trust_public_leak_ban.py`)
Currently parametrized over a single `BANNED_KEY = "trust_tier"`. D-34 requires extending coverage to `review_state`, `source`, `method`, and discrepancy fields. The minimal-diff extension is:
```python
BANNED_KEYS = ("trust_tier", "review_state", "source", "method")
# ... and in the test body:
for banned_key in BANNED_KEYS:
    assert banned_key not in reachable_model.model_fields, (...)
```
Test 3 ("false-green guard") and Test 4 (AST-based import scan) will also need one more model (`ArgumentDetail` or a new admin discrepancy schema) added to their "must carry this field" / scanned-module lists respectively, mirroring the existing structure exactly.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `Person.name_needs_review` (bool) + `Person.name_extraction_metadata` (JSONB) | `Person.review_state` (enum) + `Person.provenance_metadata` (JSONB, straight carry) | This phase (migration 0028) | `admin_people.py:244`'s `missing_filters["name review"]` predicate, `:340`/`:436`'s response payload keys, and `api/schemas/admin_people.py`'s Pydantic fields all must be re-pointed in the same phase — REVIEW-05's "no parallel mechanism" is only satisfied once every one of these is updated, not just the model column |
| `_load_constituents` passes the literal `UNREVIEWED` for every participant (Phase 48, D-13) | Real per-participant `(source, method, review_state)` triple | This phase (D-18) | `api/domain/trust.py`'s `UNREVIEWED` module-level constant becomes dead code for the participant path (it may still be needed elsewhere — check before removing) |
| `argument.status != ArgumentStatusEnum.CANDIDATE` blocks all resolve-row edits (Phase 44/48) | Widened to `{candidate, draft, unpublished}` (folded todo, published excluded) | This phase | `api/services/admin_jobs.py:825`'s exact guard condition changes; the docstring at `:796-797` referencing "D-18, D-19" needs updating to reference this phase's decision instead |

**Deprecated/outdated:**
- `Person.name_needs_review`/`name_extraction_metadata`: replaced outright, not deprecated-with-shim (D-08 explicitly rejects a compatibility view).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The unresolved-speaker fixture (D-33) will be produced by a new dev-only mechanism not yet designed — CONTEXT.md asserts it should be "representative," but no concrete corpus conversation or synthetic-insert mechanism is specified anywhere read this session. | Common Pitfalls #4 | If the planner assumes an existing `FIXTURE_SET` entry already produces a NULL-`person_id` participant, the fixture task will silently no-op or fail late in a live-verification pass, wasting a checkpoint cycle |
| A2 | The new authority-ladder function (distinct from `derive_tier`) does not yet exist anywhere in the codebase under any name — this research did not find a `authority.py` or equivalent pure module. | Architecture Patterns, Pattern 3 | If one already exists under an unexpected name, the plan should extend it rather than create a duplicate; a targeted grep for "authority" across `api/domain/` and `api/services/` at plan time is cheap insurance |
| A3 | `api/schemas/admin_jobs.py`'s `ResolveRowUpdate` schema shape was not fully read this session (only its consumer, `update_resolve_row_for_job`, was) — its exact field list may need a `review_state`-related addition for the confirm/edit flow if the resolve-scoped path is chosen as (part of) the D-31 writer. | Recommended Project Structure | Low risk — schema shape is easy to inspect at plan time; flagged only because this research did not open the file directly |

## Open Questions

1. **Which existing writer(s) become D-31's "one real authority-checked writer"?**
   - What we know: Two participant-side writers exist today (`admin_arguments.py::update_participant_side` at line 715, no status guard; `admin_jobs.py::update_resolve_row_for_job` at line 783, CANDIDATE-only guard) plus one person writer (`admin_people.py::update_person`, unrestricted by status since `Person` has none). D-23 says edit deep-links to "the argument's Resolve card" (implying `update_resolve_row_for_job` is the edit-path writer for participants) while D-31 says "the participant/person update path" (singular-sounding, ambiguous between the two).
   - What's unclear: Whether the new inline-confirm/edit/reflag actions on `/admin/review` call a brand-new function that wraps both existing writers, or whether one of the two existing writers is extended in place and the other left untouched (but then which one is REVIEW-04's "resolve a review item" mechanism?).
   - Recommendation: Resolve this explicitly in the plan's task breakdown before writing code — it determines whether Pitfall 2's CANDIDATE-only guard needs touching at all.

2. **Exact shape of the new authority-ladder pure function's inputs/outputs.**
   - What we know: `derive_tier`'s shape (three plain strings in, one enum out, precedence-ordered rules) is the established template; the authority ladder needs to answer "does incoming (source, method) outrank stored (source, method) [as modified by review_state per D-22]?" for a specific field.
   - What's unclear: Whether it returns a boolean (accept/reject) or a three-way result (accept / reject-but-record / accept-and-record, per D-16's "discrepancy recorded even on outright rejection").
   - Recommendation: Given D-16, a three-way or two-boolean return (`accepted: bool, should_record_discrepancy: bool`) is more honest than a single boolean — plan the function signature explicitly rather than discovering the need for a second return value mid-implementation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (.venv) | Alembic migration, pytest suite | ✓ | 3.12.13 (venv), host `python3` reports 3.14.4 — the pinned venv is what matters | — |
| SQLAlchemy | ORM models/queries | ✓ | 2.0.52 | — |
| Alembic | Migration `0028` | ✓ | 1.19.1 | — |
| Pydantic | Schemas | ✓ | 2.13.4 | — |
| FastAPI | Router endpoints | ✓ | 0.141.1 | — |
| pytest | Authority-matrix tests (D-32) | ✓ (`.venv/bin/pytest` present) | not separately verified | — |
| Node.js | Frontend build/dev server | ✓ | v24.18.0 (via nvm; not on default PATH — see project's own environment note) | Export the nvm bin dir before any node-dependent command |
| PostgreSQL server (dev/test) | All DB-gated tests, `reset_to_fixture` | Not directly probed this session — `pg_isready` CLI itself is absent (exit 127), and `.env`/`DATABASE_URL` contents are out of bounds for this research session per this environment's own file-access boundary | — | Confirm via `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py -x` at plan/execute time rather than a raw `pg_isready` call |

**Missing dependencies with no fallback:** None identified — every library this phase needs is already installed and importable.

**Missing dependencies with fallback:** PostgreSQL connectivity itself was not directly probed (tooling/permission constraints of this research session, not a project gap) — falls back to letting the existing test suite's own DB-gated tests serve as the connectivity check at execute time, which is the project's own established verification method for every prior phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`.venv/bin/pytest`, verified present) |
| Config file | `pytest.ini` at repo root, with the isolation-critical `conftest.py` beside it (verified present, read in full this session) |
| Quick run command | `./.venv/bin/python -m pytest api/tests/test_<new_module>.py -x` |
| Full suite command | `./.venv/bin/python -m pytest` (per `.planning/config.json`'s own `test_command`) — baseline at Phase 48 close: 1209 passed / 5 xfailed / 0 failed / 0 skipped |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REVIEW-01 | `review_state` enum present with 4 values on both `people` and `argument_participants` | unit (model/migration) | `pytest api/tests/test_review_state_schema.py -x` (new) | ❌ Wave 0 |
| REVIEW-02 | Equal-or-higher-authority disagreement records a discrepancy, never overwrites | unit + integration (authority matrix, D-32) | `pytest api/tests/test_authority_matrix.py -x` (new) | ❌ Wave 0 |
| REVIEW-03 | Queue lists items filterable by tier × review_state × status | integration | `pytest api/tests/test_admin_review_service.py -x` (new) | ❌ Wave 0 |
| REVIEW-04 | Resolve action advances `review_state` and recomputes trust in one transaction | integration | `pytest api/tests/test_admin_review_service.py::test_resolve_recomputes_trust -x` (new) | ❌ Wave 0 |
| REVIEW-05 | No `name_needs_review`/`name_extraction_metadata` reference remains outside the migration's own historical comments | static/structural (grep-based contract test, mirroring `test_trust_public_leak_ban.py`'s AST-scan style) | `pytest api/tests/test_legacy_review_mechanism_removed.py -x` (new) | ❌ Wave 0 |
| D-34 (public-leak extension) | `review_state`/`source`/`method`/discrepancy fields never reach a public response | structural | `pytest api/tests/test_trust_public_leak_ban.py -x` (EXTEND existing file) | ✓ exists, needs extension |

### Sampling Rate
- **Per task commit:** the relevant new/extended test file only (`-x`, fail-fast).
- **Per wave merge:** `./.venv/bin/python -m pytest api/tests -q` (matches the project's own full-suite discipline).
- **Phase gate:** Full suite green (`./.venv/bin/python -m pytest`) before `/gsd-verify-work`, PLUS D-32's one live browser walkthrough of an authority conflict (operator edits a corpus value, a second writer disagrees) — per the phase's own stated lesson: "three of Phase 48's defects were found by operator browser testing and none by the 1209-test suite."

### Wave 0 Gaps
- [ ] `api/tests/test_review_state_schema.py` — covers REVIEW-01 (enum presence/values on both tables)
- [ ] `api/tests/test_authority_matrix.py` — covers REVIEW-02 (every (incoming-authority, stored-authority) combination — CONTEXT.md's D-32 calls this "exhaustive")
- [ ] `api/tests/test_admin_review_service.py` — covers REVIEW-03/REVIEW-04 (queue query + resolve action + trust recompute)
- [ ] `api/tests/test_legacy_review_mechanism_removed.py` — covers REVIEW-05 (structural grep/AST check that `name_needs_review`/`name_extraction_metadata` do not appear outside migration history and the `downgrade()` path)
- [ ] Extend `api/tests/test_trust_public_leak_ban.py` — covers D-34 (no new file, but a real code change to an existing Wave-0-adjacent gap)
- [ ] A dev-only fixture mechanism for the unresolved-speaker case (D-33) — see Open Question 1 / Pitfall 4; this is infrastructure, not a test file itself, but it gates every test that needs a NULL-`person_id` participant

*Framework install: none needed — pytest and all fixtures already exist project-wide.*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | `/admin/review` inherits the existing router-level `verify_admin_token` dependency — no new auth mechanism introduced |
| V3 Session Management | No | No change to session handling |
| V4 Access Control | Yes | IDOR guard pattern already established (`update_participant_side`'s "the SELECT and UPDATE are both scoped by BOTH argument_id AND participant_id" — verified `api/services/admin_arguments.py:725-727`) must extend to the new resolve-action writer: a discrepancy/participant/person row must be scoped to its owning argument/person before any write, exactly as today |
| V5 Input Validation | Yes | Pydantic schemas (mass-assignment guard pattern already used: `ParticipantSideUpdate` exposes ONLY `side`/`descriptor`, verified `api/schemas/admin_arguments.py:44-55`) — new resolve-action request bodies must use the same allow-list-only-writable-fields discipline |
| V6 Cryptography | No | Not implicated |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Public information disclosure of operator-only trust/review data | Information Disclosure | The structural public-leak-ban contract test (`test_trust_public_leak_ban.py`), extended per D-34 — this is the project's own established, non-negotiable pattern, not a general OWASP recommendation |
| IDOR on cross-argument/cross-person writes | Tampering | Scoped-SELECT-then-UPDATE pattern (WHERE both the parent id AND child id match) — already used by every existing admin writer touched by this phase |
| Mass assignment via an overly permissive PATCH body | Tampering | Pydantic schema exposing only the intended writable fields (established codebase pattern, e.g. `ParticipantSideUpdate`) |

## Sources

### Primary (HIGH confidence — all read directly this session)
- `api/models/models.py` (full read of relevant sections: enums lines 38-100, `Person` lines 118-152, `Argument.trust_tier` lines 322-330, `ArgumentParticipant` lines 393-406, `AdminJob` lines 550-575)
- `api/domain/trust.py` (read in full)
- `api/services/trust.py` (read in full)
- `api/services/admin_people.py` (targeted reads: lines 1-30, 230-260, 325-345, 425-560)
- `api/schemas/admin_people.py` (grep-confirmed field locations)
- `api/services/admin_arguments.py` (targeted reads: `update_participant_side` lines 715-754, `publish_argument` lines 602-660, `list_arguments`/`get_argument_stats` lines 67-177)
- `api/services/admin_jobs.py` (targeted read: `update_resolve_row_for_job` lines 783-843)
- `api/routers/admin.py` (targeted reads around participant/resolve-row routes)
- `pipeline/commands/import_convokit.py` (targeted reads: `_resolve_person` lines 735-790, `ArgumentParticipant` creation lines 905-925, `skipped_existing` line ~493)
- `pipeline/commands/resolve.py` (targeted read: lines 140-335, HIT/MISS discrepancy-building)
- `alembic/versions/0022_person_name_authority.py`, `0026_import_run_provenance.py`, `0027_trust_tier_and_candidate_status.py` (all read in full)
- `api/tests/test_trust_public_leak_ban.py` (read in full)
- `api/services/admin_dev.py` (targeted read: docstring + `FIXTURE_SET` lines 74-99)
- `conftest.py` (repo root, targeted read of the isolation-rationale docstring)
- `app/src/lib/components/AdminSubNav.svelte`, `StatCard.svelte` (read in full)
- `app/src/routes/admin/arguments/+page.svelte` (targeted reads: lines 1-120 badge/filter helpers, 160-260 header/filter/empty-state markup)
- `app/src/routes/admin/+page.svelte` (targeted reads: script section, StatCard grid lines ~240)
- `app/src/routes/admin/people/[id]/+page.svelte` (targeted read: select-element styling ~895-925)
- `.planning/phases/49-review-model/49-CONTEXT.md`, `49-UI-SPEC.md` (read in full)
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md` (read in full)
- Live environment probes this session: `.venv/bin/python -c "import sqlalchemy, alembic, pydantic, fastapi"` (versions confirmed), `node --version`, `python3 --version`

### Secondary (MEDIUM confidence)
- None — no web/Context7 lookups were performed; this phase required zero external-technology research, only codebase verification.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every version number was read from the live `.venv` this session.
- Architecture: HIGH — every code touch point CONTEXT.md names was independently re-verified by reading the actual file this session (not merely trusted from CONTEXT.md's own citations).
- Pitfalls: HIGH for Pitfalls 1, 2, 3, 5 (each grounded in a direct file read with exact line quotes); MEDIUM for Pitfall 4 (grounded in a direct read of both the corpus and PDF resolve paths, but the eventual fixture-construction mechanism is genuinely undesigned, which is why it is also logged as Open Question 1 / Assumption A1).

**Research date:** 2026-08-21
**Valid until:** Stable — 30 days, or until Phase 50 begins (whichever is sooner), since Phase 50's IMPORT-01..05 work will directly touch several of the same files (`import_convokit.py`, `admin_jobs.py`) this research reads.
