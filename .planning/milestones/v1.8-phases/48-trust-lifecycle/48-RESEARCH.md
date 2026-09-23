# Phase 48: Trust & Lifecycle - Research

**Researched:** 2026-08-18
**Domain:** PostgreSQL enum/lifecycle modeling, Alembic migration sequencing, in-transaction
derived-value recomputation, offline pipeline CLI extension, FastAPI admin mutation gating
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 – D-24, verbatim intent, condensed for planner scanning)

- **D-01:** `candidate` replaces `pipeline` as the born-state enum value; `draft` survives. Add
  `candidate` to the existing `argument_status` PG enum; stop writing `pipeline` (PG cannot drop
  enum values — `pipeline` stays defined but dead). One-way migration.
- **D-02:** `draft` is a required stop; a candidate cannot publish directly. `approve_job` remains
  the candidate → draft step. Publish-button visibility rule unchanged.
- **D-03:** Candidate birth is logged — every argument gets an `argument_status_log` row at
  creation. Deliberately makes the carried `delete_argument` cascade defect reachable for every
  row (correct once D-15/D-22 land in this same phase).
- **D-04:** Candidates stay hidden from `/admin/arguments` — the existing PIPELINE/candidate
  exclusion in `list_arguments`/`get_argument_stats` is left exactly as-is (hard-exclude, not
  default-exclude). Phase 49's review queue is the intended screen for candidates.
- **D-05:** The delete gate stays DRAFT-only — this phase does not widen deletion to candidates.
- **D-06:** Only `arguments` carries a materialized `trust_tier`. Utterance/participant tiers are
  derived on the fly during recompute — one materialized column, one drift surface.
- **D-07:** One shared Python function, no DB trigger. `derive_tier(source, method,
  review_state)` plus the floor rollup lives in `api/domain/`, unit-testable without a database. A
  thin service helper `recompute_argument_tier(db, argument_id)` is called **in the same
  transaction as the mutation** by every writer — pipeline and API alike.
- **D-08:** The tier stays live after publish; a drop never auto-unpublishes.
- **D-09:** Ship an offline CLI recompute command (`--all` / single argument) — drift-repair tool
  and verification vehicle (after `reset_to_fixture`, `recompute --all` must change 0 rows).
- **D-10:** The floor reads only per-argument rows — `utterances` and `argument_participants` —
  never `Person` directly. Bounded to exactly one argument by construction.
- **D-11:** An unresolved speaker (`person_id IS NULL`) floors the argument to UNCERTAIN.
- **D-12:** Stage directions (`is_stage_direction = true`) are excluded from the floor. NOT
  extended to `side = UNKNOWN` rows.
- **D-13:** `review_state` stays in the function signature but is supplied as `unreviewed` in
  Phase 48; no adapter is written. Verified: `argument_participants` has no review or method
  column today. Phase 49 supplies the real column with no signature change.
- **D-14:** Two distinct gates; only the UNCERTAIN one is overridable. `resolved_at IS NULL`
  remains a hard precondition with **no** override.
- **D-15:** The override record extends `argument_status_log` — add nullable `override_reason`
  (text) and `trust_tier_at_transition`.
- **D-16:** The override is per publish attempt, never sticky.
- **D-17:** A non-empty reason is required, enforced server-side. Free text, not structured.
- **D-18:** No extra guard beyond the existing admin token.
- **D-19:** Minimal frontend, on the page that already exists (`/admin/arguments/[id]`) — block
  reason + override prompt. The only frontend work in the phase.
- **D-20:** API exposure: detail endpoint returns `trust_tier`; blocked-publish response returns
  tier + blocking reasons. Admin list endpoints stay untouched.
- **D-21:** Tests own tier coverage (every combination incl. UNCERTAIN via NULL `person_id`); the
  live fixture proves the happy path (candidate on arrival, corpus rows TRUSTED, `recompute-trust
  --all` changes 0 rows). No synthetic unresolved-speaker fixture.
- **D-22:** The carried `delete_argument`/`argument_status_log` cascade defect gets a
  failing-then-passing regression test, not a manual repro, plus the false-comment fix in
  `scripts/delete_fixture_argument.py`.
- **D-23:** A contract test enforces the public-leak ban — no public response contains
  `trust_tier`.
- **D-24:** The migration flips any `status=pipeline` rows to `candidate` in the same migration
  that adds the enum value.

### Claude's Discretion (research resolves each below, with rationale — see body sections)

- How `trust_tier` arrives (nullability/default) — operator lean: NOT NULL, server default
  `uncertain`, no in-migration derivation. **Research: confirmed sound, see "Migration
  Mechanics."**
- Review-dimension sourcing — effectively resolved by D-10/D-13. **Research: reconfirmed against
  current source, see "D-13 Confirmation."**
- `trust_tier` column representation (native PG enum vs. ordered smallint). **Research
  recommendation: native PG enum — see "Column Representation Decision."**
- Zero-utterance argument tier. **Research recommendation: UNCERTAIN — see "Zero-Utterance Tier
  Decision."**
- Override endpoint shape (body flag on existing `POST .../publish` vs. new route). **Research
  recommendation: extend the existing endpoint's body — see "Override Endpoint Shape Decision."**

### Deferred Ideas (OUT OF SCOPE for Phase 48)

- Candidate visibility / tier badge in admin UI → Phase 49.
- Widening the delete gate to candidates → Phase 50.
- Person-level review signals reaching the argument floor → Phase 49.
- Auto-unpublish on tier drop → rejected, not this phase.
- A PostgreSQL trigger as a recompute safety net → possible after Phase 50.
- An unresolved-speaker fixture → rejected as partly synthetic.
- A structured per-constituent override acknowledgment → rejected as disproportionate.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRUST-01 | Every argument carries a `trust_tier` derived from provenance + review state | `derive_tier()` design in "Architecture Patterns"; enum-vs-smallint decision below |
| TRUST-02 | `trust_tier` is the floor rollup of utterances + participants, materialized and recomputed on change | `recompute_argument_tier()` design + full writer-path enumeration below |
| TRUST-03 | A newly imported argument is born `candidate` with tier set on arrival | Every-writer-path table below (corpus import, PDF ingest, model default) |
| TRUST-04 | Publish is hard-blocked while any UNCERTAIN element remains | `publish_argument()` gate mechanics below, D-14 two-gate design |
| TRUST-05 | Operator can override the publish block with a deliberate, logged acknowledgment | `argument_status_log` extension + override endpoint shape decision below |
</phase_requirements>

## Summary

This phase is almost entirely a codebase-archaeology and migration-sequencing problem, not a
library problem — no new external dependency is needed. The design is fully settled in
`provenance-and-trust-model.md`/`import-entity-sketch.md` and locked by 24 decisions in
48-CONTEXT.md; what remains is (a) resolving the five items CONTEXT.md explicitly routed to
research, and (b) enumerating, with file:line precision, every place existing code keys off the
literal `ArgumentStatusEnum.PIPELINE` — because D-01's "candidate replaces pipeline" is not a
cosmetic rename. Any code path that still compares against `PIPELINE` after this migration ships
will silently stop matching newly-created (candidate) arguments, producing a **functional
regression**, not just a stale comment. This research found **two such regressions beyond what
CONTEXT.md's canonical-refs list already names** (`admin_jobs.py:804` and `admin_people.py:968`,
both real "is this argument still in the pipeline-editable stage" gates) — see "PIPELINE→CANDIDATE
Guard Inventory" below. This is the single most important finding of this research pass and must
become explicit tasks in the plan.

The four remaining open items are resolved as follows: `trust_tier` should be a native PG enum
(matches the project's `SAEnum(..., values_callable=...)` convention used by five other lifecycle
enums, and the floor computation happens in Python per D-07, not SQL `MIN()`, so the smallint's
main advantage is moot in this architecture). A zero-utterance argument should compute UNCERTAIN
(same fail-closed instinct as the column default; absence of evidence is the maximal attribution
risk, not a free pass). The override should ride the existing `POST /publish` endpoint's body
(add an optional `override_reason` field) rather than a new route — this is what D-19/D-20 already
imply and it is consistent with every other admin mutation in this router. The migration itself is
simpler than CONTEXT.md's discretion framing suggests: `NOT NULL` + `server_default='uncertain'`
on `ADD COLUMN` requires **no separate backfill UPDATE at all** — PostgreSQL applies the default to
existing rows as part of the `ADD COLUMN` statement.

**Primary recommendation:** Implement `derive_tier()`/`recompute_argument_tier()` in
`api/domain/trust.py` (pure) + a thin `api/services/trust.py` (or fold into
`admin_arguments.py`) DB helper, add `trust_tier` as a native PG enum column with
`server_default='uncertain'`, update **every** `ArgumentStatusEnum.PIPELINE` comparison site (8
production sites found, not 3), and reuse the existing `/publish` endpoint for the override.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Trust tier derivation (`derive_tier`) | API/Backend (`api/domain/`) | Pipeline (imports it) | Pure function, no DB — D-07 explicit; both API and offline pipeline must call the identical code, so it cannot live only in one runtime |
| Trust tier recompute + persistence | API/Backend (`api/services/`) | Pipeline (calls the service fn) | D-07: DB read/write step, in-transaction with every writer |
| Candidate birth (status=candidate, tier set, status-log row) | API/Backend + Pipeline (writer paths) | — | Both corpus import (pipeline) and PDF ingest (pipeline) create the row; both must call the same recompute helper |
| Publish gate + override | API/Backend (`admin_arguments.py` service + router) | Frontend Server (SvelteKit `+page.server.ts` action) | Gate is enforced server-side (D-14); SvelteKit only relays the response, never re-implements the gate |
| Block-reason / override UI | Frontend Server (SvelteKit `+page.svelte`/`+page.server.ts`) | — | D-19: minimal read/relay of the API's blocking-reasons payload, no new business logic in the browser |
| Offline recompute CLI | Pipeline (CLI only) | — | CLAUDE.md: pipeline is offline-only, never an HTTP endpoint |
| DB schema (enum, column, table extension) | Database / Storage (Alembic) | — | Alembic is sole DDL authority; no `Base.metadata.create_all` |
| Trust tier public exposure | **None (permanently excluded)** | — | Apolitical hard constraint — trust is operator-facing only, enforced by contract test (D-23) |

## Standard Stack

No new external package is required for this phase. Every primitive needed already exists in the
codebase and its currently-pinned dependencies.

### Core (already in use — versions as pinned)

| Library | Version (from venv) | Purpose | Why Standard |
|---------|------|---------|--------------|
| SQLAlchemy | 2.0.52 [VERIFIED: `.venv` `python -c "import sqlalchemy; print(sqlalchemy.__version__)"`, run this session] | ORM, `SAEnum`, async session | Already the project's sole DB layer |
| Alembic | 1.19.1 [VERIFIED: `.venv` `python -c "import alembic; print(alembic.__version__)"`, run this session] | Migration authorship | CLAUDE.md: sole DDL authority |
| Pydantic | v2 (project convention, CLAUDE.md) | Request/response schemas for the override body | Already used by every admin schema in `api/schemas/admin_arguments.py` |

### Supporting

None new. `pytest` + `pytest-asyncio` (already configured via `pytest.ini`,
`asyncio_mode = auto`) cover the test surface D-21/D-22/D-23 need.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Native PG enum for `trust_tier` | Ordered `smallint` + a Python `IntEnum` | Smallint gives a free SQL `MIN()` floor and side-steps PG's cannot-drop-enum-value limitation forever, but D-07 already computes the floor in Python (see below) — the SQL-aggregation advantage doesn't apply here, and it breaks the project's `SAEnum(...)` convention used by every other lifecycle field |
| Python service helper (D-07) | PostgreSQL `AFTER INSERT/UPDATE` trigger | Cannot drift structurally, but duplicates vocabulary in PL/pgSQL, is invisible to the Python test suite, and was explicitly rejected in the discussion log |
| Reusing `POST /publish` for the override | A dedicated `POST /publish-override` route | Marginally clearer REST semantics, but doubles the frontend/router surface for a single-field difference, and every other write-conflict-with-override pattern in this codebase (e.g. `docket_collision`/`slug_collision` on `PATCH /arguments/{id}`) already uses "same endpoint, richer body/response" rather than a parallel route |

**Installation:** None — no `pip install` / `npm install` needed for this phase's core work.

## Package Legitimacy Audit

**Not applicable.** This phase introduces zero new third-party packages (npm or PyPI). All work is
new modules/columns/migrations built from already-approved, already-pinned dependencies
(SQLAlchemy 2.0.52, Alembic 1.19.1, Pydantic v2, pytest). No `package-legitimacy check` run is
required, and no `checkpoint:human-verify` gate is needed for dependencies in this phase's plan.

## Column Representation Decision — native PG enum vs. ordered smallint

**Recommendation: native PG enum**, named `trust_tier`, declared with the project's established
`SAEnum(TrustTier, name="trust_tier", values_callable=lambda e: [x.value for x in e])` pattern.

**Why the smallint's usual advantage doesn't apply here:** The textbook case for an ordered
smallint over an enum for a "floor/ceiling" column is that `SELECT MIN(tier_rank) ...` becomes a
single SQL aggregate with an index-friendly comparison, and PostgreSQL's inability to ever *remove*
an enum value (only add) becomes a non-issue. But D-07 already settles how the floor is computed:
*"A thin service helper (`recompute_argument_tier(db, argument_id)`) does the read-constituents-
and-store step"* — reading `utterances` and `argument_participants` rows, calling
`derive_tier(source, method, review_state)` **per row in Python**, then taking `min()` over the
resulting Python enum values before writing the single materialized column back. There is no SQL
`MIN(trust_tier)` anywhere in this design — the derivation itself (mapping `source`/`method`/
`review_state` → tier) is not expressible as a column comparison in the first place, since `source`
and `method` are already separate enum columns on `ImportRun`/`Utterance`, not something with a
built-in ordinal relationship to tier. The floor is a Python `min()` over already-computed Python
values, every time, regardless of storage type.

Given that, the smallint's only remaining argument is future evolvability (inserting/reordering
tiers without PG's enum-append-only limitation). That is real, but:
- The four tiers (verified/trusted/provisional/uncertain) come directly from
  `provenance-and-trust-model.md`, which frames them as settled ("already settled ... do not
  re-open them" per 48-CONTEXT.md's canonical-refs note on that file's open questions 1/2/4).
- The project already has five other lifecycle enums declared with the identical
  `SAEnum(..., values_callable=...)` idiom
  [VERIFIED: `api/models/models.py:37-87`, quoted below] — `SideEnum`, `ImportRunStatus`,
  `ImportSource`, `ImportMethod`, `ArgumentStatusEnum` — and PG's "cannot drop, can only add" limit
  has already been hit and worked around twice in this codebase (`side` gained
  PETITIONER/RESPONDENT/AMICUS in migration 0008; `argument_status` gained `unpublished` in
  migration 0012) without incident. A `trust_tier` enum inherits a proven, already-battle-tested
  migration idiom rather than introducing a second representation convention for lifecycle data.

```python
# api/models/models.py:37-87 (quoted exactly — the SAEnum convention this decision follows)
class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"  # legacy — never remove (PG cannot drop enum values)
    UNKNOWN = "UNKNOWN"
    PETITIONER = "PETITIONER"
    RESPONDENT = "RESPONDENT"
    AMICUS = "AMICUS"
...
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
```

**Verdict:** native PG enum. If a future phase needs an intermediate tier (e.g. between PROVISIONAL
and UNCERTAIN), the same `ALTER TYPE trust_tier ADD VALUE ... AFTER 'provisional'` idiom already
used twice in this codebase applies unchanged.

## Zero-Utterance Tier Decision

**Recommendation: UNCERTAIN.** An argument with zero `utterances` rows (e.g. a candidate the
moment it is created by `ingest.py`/`import_convokit.py`, before any `Utterance` rows exist, or a
degenerate edge case) should compute to UNCERTAIN, not TRUSTED-by-default and not a `NULL`
sentinel.

**Rationale grounded in the codebase, not just instinct:**
- This exactly mirrors D-11's reasoning for an unresolved speaker: *"Unattributed speech is
  precisely the attribution-accuracy failure the tier is defined to measure ... [it] gives the
  gate real teeth."* Zero utterances is the maximal case of "no attribution evidence exists" — it
  is strictly *more* uncertain than one unresolved utterance, not less.
- It matches the column's own fail-closed default (`server_default='uncertain'`, per the operator's
  explicit lean) — an argument that has not yet accumulated any evidence should read identically to
  an argument whose evidence hasn't been classified yet. Treating "no rows" as a special TRUSTED
  case would create a gap where a candidate is briefly *more* publishable before its first
  utterance lands than after — backwards from the intended trust signal.
- No code path in the current admin/pipeline services treats an empty `utterances` set as
  meaningfully different from a fully-unresolved one; `get_utterance_count`
  (`api/services/admin_arguments.py:193-200`) and every resolve-card query already treat zero rows
  as the ordinary "nothing parsed yet" state, not an error or special case.

**Implementation note for the planner:** `recompute_argument_tier` should treat `min([])` (empty
constituent list after excluding stage directions) as an explicit early return of `UNCERTAIN`,
documented in the function's docstring as a named base case — not left as an accidental
`min()`-over-empty-sequence `ValueError` waiting to happen. This must be a unit test in D-21's
coverage set.

## Override Endpoint Shape Decision

**Recommendation: extend the existing `POST /api/admin/arguments/{argument_id}/publish` endpoint's
request body**, not a new route.

**Current shape** [VERIFIED: `api/routers/admin.py:1121-1140`, read this session]:
```python
@router.post("/arguments/{argument_id}/publish", response_model=ArgumentDetail)
async def publish_argument(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArgumentDetail:
    try:
        result = await arguments_service.publish_argument(db, argument_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
```
This endpoint currently takes no body at all. The frontend action that calls it is equally bare
[VERIFIED: `app/src/routes/admin/arguments/[id]/+page.server.ts:329-345`, read this session]:
```ts
publish: async ({ params, fetch }) => {
    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/publish`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch {
        return fail(502, { error: 'Could not publish this argument. Try again.' });
    }
    if (!res.ok) {
        return fail(422, { error: 'Could not publish this argument. Try again.' });
    }
    throw redirect(303, '/admin/arguments/' + params.id);
},
```

**Why extend rather than add a route:**
- D-16 makes the override "per publish attempt, never sticky" — it is semantically *the same
  action* (publish), just with an accompanying justification. A second route would need to
  duplicate every one of `publish_argument`'s existing guards (`resolved_at IS NULL`,
  already-PUBLISHED) rather than layering one new check onto the one that exists.
- D-20 already commits to this shape implicitly: *"the blocked publish response returns the tier
  plus the blocking reasons"* — a single response contract for both the blocked case and the
  override-accepted case is simplest when it's one endpoint.
- The router's own established pattern for "normal call vs. call with an extra acknowledgment
  field" is exactly this shape elsewhere — `PATCH /arguments/{id}` accepts a body and raises
  `ValueError("slug_collision")`/`ValueError("docket_collision")` that the router converts to a 422
  with a specific `detail` string the SvelteKit layer branches on
  (`update_argument`'s docstring, `api/routers/admin.py:1102-1118`). The publish-override case is
  the same "body carries an optional field; service raises a specific, taggable error; router
  surfaces it" shape, not a new pattern.
- The current bare `fetch(..., { method: 'POST' })` call has no body today, so adding an optional
  JSON body (`{ override_reason?: string }`) is additive, not breaking.

**Concrete shape recommendation for the planner:**
```python
class PublishRequest(BaseModel):
    override_reason: str | None = None
```
`publish_argument(db, argument_id, override_reason=None)` — when the UNCERTAIN gate would block
and `override_reason` is a non-empty string (server-side validated, D-17), publish proceeds and
`ArgumentStatusLog` gets `override_reason` + `trust_tier_at_transition` populated (D-15); when
`override_reason` is `None`/blank and the gate would block, raise a **distinguishable** error
(e.g. `ValueError("uncertain_tier_blocked")`, carrying the tier + reasons in a structured payload,
not just a string) so the 422 response and the SvelteKit action can render the "why blocked" UI
(D-19) versus a plain "already published" 422 from the pre-existing gate.

## Architecture Patterns

### System Architecture Diagram

```
Writer paths (each must call recompute in the SAME transaction as its own commit):

  pipeline/commands/import_convokit.py    pipeline/commands/ingest.py       admin_jobs.approve_job
  (corpus birth: status=CANDIDATE,        (PDF birth: status=CANDIDATE      (CANDIDATE -> DRAFT,
   ImportRun source=CORPUS/DIRECT)         via model default)                stamps resolved_at)
              |                                    |                                |
              v                                    v                                v
      +-------------------------------------------------------------------------------------+
      |            api/domain/trust.py :: derive_tier(source, method, review_state)          |
      |            (pure function -- no DB, no FastAPI/SQLAlchemy imports, D-07)             |
      +-------------------------------------------------------------------------------------+
              |                                    |                                |
              v                                    v                                v
      +-------------------------------------------------------------------------------------+
      | api/services/... :: recompute_argument_tier(db, argument_id)                        |
      |   1. SELECT utterances WHERE argument_id=X (join import_run for source/method)      |
      |   2. SELECT argument_participants WHERE argument_id=X                                |
      |   3. exclude is_stage_direction rows (D-12); person_id IS NULL -> UNCERTAIN (D-11)   |
      |   4. derive_tier() per constituent row, in Python                                     |
      |   5. min() over results (empty set -> UNCERTAIN, see Zero-Utterance decision)         |
      |   6. UPDATE arguments SET trust_tier = <result> WHERE id = X                          |
      +-------------------------------------------------------------------------------------+
              ^                                    ^                                ^
              |                                    |                                |
   admin edit endpoints (participant side,   publish_argument() /            pipeline CLI:
   descriptor, argument metadata) --          unpublish_argument()           `recompute-trust
   also call recompute after their own        (D-08: recompute even          --all` / single-arg
   writes                                      after publish)                (drift repair +
                                                       |                       verification vehicle,
                                                       v                       D-09)
                                       UNCERTAIN gate (D-14): resolved_at
                                       IS NULL is a separate, non-
                                       overridable hard precondition;
                                       UNCERTAIN tier is the overridable
                                       gate -- override_reason required
                                       (D-17), logged to argument_status_log
                                       (D-15), never sticky (D-16)
                                                       |
                                                       v
                                    Public site: trust_tier NEVER serialized
                                    (D-23 contract test enforces this)
```

### Recommended Project Structure

```
api/
├── domain/
│   ├── trust.py                # NEW — derive_tier(), floor helper (D-07, pure)
│   ├── person_names.py         # existing precedent for this module's shape
│   └── docket_values.py        # existing precedent for this module's shape
├── services/
│   └── admin_arguments.py      # add recompute_argument_tier(); publish_argument() gains
│                                # the UNCERTAIN gate + override_reason param
├── models/
│   └── models.py               # ArgumentStatusEnum gains CANDIDATE; TrustTier enum;
│                                # Argument.trust_tier column; ArgumentStatusLog gains
│                                # override_reason / trust_tier_at_transition
├── schemas/
│   └── admin_arguments.py      # ArgumentDetail gains trust_tier; PublishRequest body
alembic/versions/
└── 0027_trust_tier_and_candidate_status.py   # NEW migration (see Migration Mechanics)
pipeline/
├── commands/
│   ├── import_convokit.py      # status=ArgumentStatusEnum.CANDIDATE (was PIPELINE);
│                                # write ArgumentStatusLog(CANDIDATE) at birth (D-03);
│                                # call recompute_argument_tier after ImportRun flush
│   ├── ingest.py                # birth now CANDIDATE via model default; ALSO needs the
│                                # new ArgumentStatusLog(CANDIDATE) write at birth (D-03)
│   └── recompute_trust.py       # NEW — pipeline CLI subcommand (D-09)
└── __main__.py                  # wire the new subcommand; fix "status=pipeline" help text
app/src/routes/admin/arguments/[id]/
├── +page.server.ts              # publish action reads structured block payload,
│                                 # supports override_reason resubmission
└── +page.svelte                 # block-reason display + override reason field (D-19)
```

### Pattern 1: Pure domain function imported by both runtimes

**What:** `api/domain/trust.py` has zero FastAPI/SQLAlchemy/Alembic imports, mirroring
`person_names.py` and `docket_values.py` exactly [VERIFIED: `api/domain/person_names.py:1-20`,
`api/domain/docket_values.py:1-27`, read this session — both modules' docstrings state "This module
has NO FastAPI/SQLAlchemy/Alembic imports. It must remain importable by API services, pipeline
commands, tests, and Alembic migrations without initializing the app or a database connection"].

**When to use:** Any derivation both the offline pipeline and the FastAPI service layer must
compute identically.

**Example (precedent for the cross-layer import, not the trust logic itself):**
```python
# pipeline/commands/ingest.py:47-48 (quoted exactly)
from api.services.argument_uniqueness import is_argument_pair_violation
from api.domain.docket_values import DocketValueError, normalize_docket_value
```
`pipeline/commands/recompute_trust.py` (the new CLI command) should import
`api/domain/trust.py` and `api/services/admin_arguments.recompute_argument_tier` (or a new
`api/services/trust.py`) the same way — this precedent (pipeline importing an API-side module) is
already established, not a new architectural pattern this phase invents.

### Pattern 2: In-transaction recompute after every mutating write

**What:** `recompute_argument_tier(db, argument_id)` runs inside the SAME session/transaction as
the mutation that triggered it, using the already-open `db: AsyncSession`, and commits together
with the caller (or the caller commits once after both writes) — never a separate transaction, and
never deferred to a background job.

**When to use:** Every one of the writer paths enumerated in "Complete Writer-Path Enumeration"
below.

**Example — the shape to follow, modeled on the existing `publish_argument` refresh-after-bulk-
update pattern** [VERIFIED: `api/services/admin_arguments.py:598-616`, read this session]:
```python
await db.execute(
    update(Argument)
    .where(Argument.id == argument_id)
    .values(status=ArgumentStatusEnum.PUBLISHED, published_at=sqlfunc.now())
    .execution_options(synchronize_session=False)
)
db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.PUBLISHED))
await db.commit()
# ... db.refresh(argument) because synchronize_session=False leaves the
# already-loaded ORM object stale relative to the just-committed row.
```
`recompute_argument_tier` should follow this exact discipline: `.execution_options
(synchronize_session=False)` on its own `UPDATE arguments SET trust_tier = ...`, and any caller
that re-reads the same `Argument` object in the same session afterward must `db.refresh()` it —
this is a project-wide critical guard (Pitfall 5 in this file's docstring), not optional.

### Anti-Patterns to Avoid

- **Computing the floor in SQL:** Do not write `SELECT MIN(trust_tier_rank) FROM ...` against a
  smallint column as the "clever" implementation — D-07 already settles that the derivation
  (`source`/`method`/`review_state` → tier) happens in Python per row; a SQL aggregate has nothing
  to aggregate until that mapping has already run in Python. Building a SQL-side derivation would
  duplicate `derive_tier()`'s vocabulary in two places, which D-07 explicitly rejected once already
  (for the PL/pgSQL-trigger alternative) for exactly this reason.
- **Trusting the model's Python-level `default=` to cover every write path automatically:**
  `Argument.status`'s `default=ArgumentStatusEnum.PIPELINE` [VERIFIED: `api/models/models.py:311`]
  only applies when an `Argument(...)` is constructed *without* an explicit `status=` kwarg
  (`pipeline/commands/ingest.py:497-502` relies on this). `pipeline/commands/import_convokit.py:515`
  passes `status=ArgumentStatusEnum.PIPELINE` explicitly and will NOT pick up a changed model
  default — it must be edited directly.
- **Leaving any `== ArgumentStatusEnum.PIPELINE` / `!= ArgumentStatusEnum.PIPELINE` comparison
  unaudited:** see "PIPELINE→CANDIDATE Guard Inventory" — this is the phase's highest-risk
  mechanical hazard.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Enum expansion under "PG cannot drop enum values" | A rename migration, or a `CREATE TYPE ... RENAME` dance | `ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'candidate'` — the exact idiom already used twice (migrations 0008, 0012) | Proven, already exercises the "COMMIT before ADD VALUE" transaction-boundary requirement correctly in this codebase |
| Backfilling `trust_tier` for pre-existing rows | An UPDATE statement that re-derives tier in SQL during the migration | `ADD COLUMN trust_tier ... NOT NULL server_default='uncertain'` alone | PostgreSQL applies the default to every existing row as part of `ADD COLUMN` — no separate backfill statement is needed, and the operator explicitly said backfill effort has no value here |
| Verifying every writer stamped correctly | A one-off manual dev-DB check | `recompute-trust --all` after `reset_to_fixture`, asserting 0 rows changed | Exactly the D-09/D-21 "falsifiable, not absence-of-drift hand-wave" pattern Phase 47's D-06 already established for provenance |
| Publish-override audit trail | A new `publish_override` table | Extend `ArgumentStatusLog` (already exists, already written on every status transition) | D-15: one audit table tells the whole story; a second table is a second join for the same "what happened" question |

**Key insight:** Every piece of infrastructure this phase needs — the enum-expansion idiom, the
audit-log table, the cross-layer domain-module pattern, the disposable-DB-so-no-backfill precedent
— already exists in this codebase from prior phases. The risk here is not "we lack a library"; it
is "we miss one of the several existing call sites that assume the old vocabulary."

## PIPELINE→CANDIDATE Guard Inventory

This is the concrete, file:line enumeration the planner needs. Grep for
`ArgumentStatusEnum.PIPELINE` across `api/` and `pipeline/` (excluding tests, which are fixtures
and are expected to still construct `Argument(status=ArgumentStatusEnum.PIPELINE, ...)` rows as
regression fixtures for the dead-but-still-valid enum value) found the following production
call sites [VERIFIED: grep run this session, each line individually opened and confirmed]:

| # | File:line | Current text | What must change | In CONTEXT.md's canonical refs? |
|---|-----------|---------------|-------------------|----------------------------------|
| 1 | `api/models/models.py:311` | `default=ArgumentStatusEnum.PIPELINE` | Change default to `ArgumentStatusEnum.CANDIDATE` | No — not listed |
| 2 | `api/services/admin_jobs.py:284` | `arg_status is not None and arg_status != ArgumentStatusEnum.PIPELINE` (in `list_jobs`, derives `is_archived`) | Compare against `CANDIDATE` | Yes |
| 3 | `api/services/admin_jobs.py:577` | `if argument.status != ArgumentStatusEnum.PIPELINE:` (in `approve_job`, double-approve guard) | Compare against `CANDIDATE` | Yes |
| 4 | `api/services/admin_jobs.py:701` | `if argument is not None and argument.status != ArgumentStatusEnum.PIPELINE:` (in `get_run_readiness`, "already_created" branch) | Compare against `CANDIDATE` | Yes |
| 5 | `api/services/admin_jobs.py:804` | `if argument.status != ArgumentStatusEnum.PIPELINE:` (in `update_resolve_row_for_job`, editability guard) | Compare against `CANDIDATE` | **No — found this session, NOT in CONTEXT.md's list of "three admin_jobs guards"** |
| 6 | `api/services/admin_people.py:968` | `editable = argument.status == ArgumentStatusEnum.PIPELINE` (in the Resolve-card row builder) | Compare against `CANDIDATE` | **No — found this session, in a different file entirely** |
| 7 | `pipeline/commands/import_convokit.py:515` | `status=ArgumentStatusEnum.PIPELINE,` (explicit write at argument creation) | Change to `ArgumentStatusEnum.CANDIDATE` | Yes (implicitly, as "the born-candidate write site") |
| 8 | `pipeline/commands/ingest.py:497-502` | No explicit `status=` kwarg — relies on model default | No code change needed once #1 lands, but the planner must NOT add an explicit `status=ArgumentStatusEnum.PIPELINE` here by habit/copy-paste from `import_convokit.py` | No — worth calling out explicitly so a task doesn't "fix" this file wrongly |

**Why #5 and #6 matter more than a cosmetic miss:** both are **editability gates**, not merely
list-filtering or archival-flag logic. If either is left comparing against the now-dead
`PIPELINE` value, then the moment a newly-created argument is born `CANDIDATE` instead of
`PIPELINE`:
- `update_resolve_row_for_job` (#5) would raise `ValueError` on **every** resolve-row edit attempt
  for a freshly-created argument — the error message it raises even names the wrong state
  explicitly (`f"Argument {argument.id} is no longer in 'pipeline' state (current status:
  {argument.status.value!r}); resolve rows are read-only once the argument has been created"`) —
  this reads as "already finalized" for an argument that was *just born*.
- `list_resolve_rows_for_job`'s `editable` flag (#6) would report `False` for every fresh
  candidate, meaning the Resolve card would render every row read-only immediately after ingest —
  a full-severity functional regression in the PDF pipeline's primary operator workflow.

Additionally worth a low-priority pass (not functional bugs, but accuracy/consistency):

| File:line | Issue |
|-----------|-------|
| `pipeline/__main__.py:293` (`import-convokit` subcommand help text) | "Arguments land at status=pipeline, paired with a paused resolve admin job." — should say `status=candidate` |
| `scripts/delete_fixture_argument.py:12-13` (docstring) | "every corpus-imported argument starts at `status == pipeline`" — should say `status == candidate` (separate from the D-22 false-comment fix at line 25-27, same file) |
| `api/services/admin_arguments.py` docstrings (`list_arguments`/`get_argument_stats`, lines ~70-113) | Docstrings say "PIPELINE-status arguments are hidden" and single out `"pipeline"` as never-selectable — accurate in spirit (candidate is likewise hard-excluded per D-04) but the wording should acknowledge `candidate` by name once it exists, for future-reader clarity |

## Complete Writer-Path Enumeration (for the recompute call-site task list)

Every path that creates or mutates an `Argument`'s constituent rows (`Utterance`,
`ArgumentParticipant`) or its own status must call `recompute_argument_tier` in the same
transaction:

| # | Writer | File:line | What it writes | Recompute trigger reason |
|---|--------|-----------|-----------------|---------------------------|
| 1 | Corpus import (birth) | `pipeline/commands/import_convokit.py:507-576` (Argument + ImportRun creation, participant resolution loop that follows) | New Argument (status=CANDIDATE), ImportRun (source=CORPUS/method=DIRECT), Utterance rows, ArgumentParticipant rows | Tier must be set the moment the argument exists (TRUST-03) |
| 2 | PDF ingest (birth) | `pipeline/commands/ingest.py:497-529` (Argument + ImportRun creation) | New Argument (status=CANDIDATE via default), ImportRun (source=PDF_PIPELINE) | Same as above; utterances arrive later via `parse`/`resolve`, so tier at ingest time is UNCERTAIN (zero utterances) until parse runs |
| 3 | Parse step (writes Utterance rows) | `pipeline/commands/parse.py` (writes Utterance rows against the ImportRun from ingest) | New Utterance rows with `is_stage_direction`, `side`, no `person_id` yet | Utterance set changed — tier may move |
| 4 | Resolve step / `approve_job` (CANDIDATE → DRAFT) | `api/services/admin_jobs.py:547-599` (`approve_job`) | Argument.status = DRAFT, resolved_at stamped, ArgumentStatusLog(DRAFT) | Not itself a constituent change, but D-07 says every writer calls recompute — the tier should be verified/re-stamped at this transition too, cheap because it's one argument |
| 5 | Resolve-row participant/utterance person_id updates | `api/services/admin_jobs.py` (`update_resolve_row_for_job`'s persistence path, ~line 790-850) and `pipeline/commands/resolve.py`'s alias-match writes | `Utterance.person_id`, `ArgumentParticipant.person_id` updates | Directly changes the D-11 unresolved-speaker floor input |
| 6 | Argument edit page — participant side/descriptor | `api/services/admin_arguments.py:619-688` (`update_participant_side`) | `ArgumentParticipant.side`/`.descriptor` | Participant row changed (though side/descriptor don't feed `derive_tier` directly per D-10's scope — still call recompute for consistency since D-07 says every writer, and a future signature change (Phase 49 review_state) will read this same row) |
| 7 | Publish | `api/services/admin_arguments.py:570-616` (`publish_argument`) | Argument.status = PUBLISHED, published_at, ArgumentStatusLog(PUBLISHED, +override fields if applicable) | The gate itself needs the current tier; D-08 also requires recompute to continue after publish |
| 8 | Unpublish | `api/services/admin_arguments.py:691-728` (`unpublish_argument`) | Argument.status = UNPUBLISHED | D-08: tier stays live |
| 9 | Offline CLI | `pipeline/commands/recompute_trust.py` (NEW) | No mutation to constituents — re-derives and re-stamps `trust_tier` only | D-09: drift repair + the `--all` "0 rows changed" verification vehicle |

Writers NOT in this list, confirmed by reading their bodies this session, that do **not** need a
recompute call: `update_argument` (argued_date/case_name/docket_number — none of these feed
`derive_tier`), `update_argument_metadata` (same reasoning), `delete_argument` (removes the row
entirely, nothing to recompute).

## Migration Mechanics

**Current Alembic head, confirmed against files on disk (no DB credentials available/assumed —
per CONTEXT.md's explicit instruction):**
```
alembic/versions/0026_import_run_provenance.py   # down_revision = "0025", revision = "0026"
```
[VERIFIED: `ls /home/jason/scotuschat/project/alembic/versions/` this session — `0026_import_run_provenance.py` is the highest-numbered file, and its own header states `down_revision: str = "0025"`, confirming no branch/fork]. The next migration is `0027`.

**Enum-expansion idiom to follow (already used twice — migrations 0008 and 0012), quoted exactly:**
```python
# alembic/versions/0012_unpublished_enum_and_status_log.py:59-60 (quoted)
op.execute(sa.text("COMMIT"))
op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'unpublished'"))
```
`ALTER TYPE ... ADD VALUE` cannot run inside a transaction block; Alembic's implicit transaction
must be committed first. The same discipline applies to adding `'candidate'`.

**New enum type idiom (for `trust_tier`, matching migration 0026's DO-guarded / existence-checked
pattern), quoted exactly:**
```python
# alembic/versions/0026_import_run_provenance.py:61-78 (quoted, abbreviated)
conn = op.get_bind()
for type_name, ddl in [
    ("import_source", "CREATE TYPE import_source AS ENUM ('operator', 'corpus', 'pdf_pipeline', 'seed')"),
    ...
]:
    exists = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))
```
or the equivalent DO-block form from migration 0012's own header comment:
```python
# alembic/versions/0012's pattern (also usable, quoted from migration 0008 which
# established the idiom — migration 0012's docstring calls migration 0008 "same
# discipline")
op.execute(sa.text("""
    DO $$ BEGIN
        CREATE TYPE argument_status AS ENUM ('pipeline', 'draft', 'published');
    EXCEPTION WHEN duplicate_object THEN null;
    END $$;
"""))
```
Either idiom is already proven in this codebase; the planner should pick whichever the executing
plan's migration author prefers, but must not invent a third.

**Flip-existing-rows step (D-24), modeled on migration 0008's backfill-by-precedence idiom:**
```python
# alembic/versions/0008_side_enum_and_argument_status.py:94-95 (quoted, for the UPDATE shape)
op.execute(sa.text(
    "UPDATE arguments SET status = 'published' WHERE published_at IS NOT NULL"
))
```
D-24's version is simpler — one unconditional UPDATE, no precedence chain needed:
```python
op.execute(sa.text("UPDATE arguments SET status = 'candidate' WHERE status = 'pipeline'"))
```
This must run AFTER the `COMMIT` + `ALTER TYPE ADD VALUE 'candidate'` step (same ordering
constraint migration 0008 documents for its own three-UPDATE backfill).

**`trust_tier` column addition — confirmed to need NO separate backfill statement:**
```python
op.add_column(
    "arguments",
    sa.Column(
        "trust_tier",
        sa.Enum("verified", "trusted", "provisional", "uncertain", name="trust_tier"),
        nullable=False,
        server_default="uncertain",
    ),
)
```
This is the operator's exact lean from 48-CONTEXT.md ("NOT NULL with server default `uncertain`,
no in-migration derivation") and it is sound: PostgreSQL's `ADD COLUMN ... DEFAULT <literal>` (a
non-volatile default) populates every existing row with that literal as part of the single DDL
statement — this is standard PostgreSQL behavior since version 11 (no table rewrite, and no
separate `UPDATE` needed for old rows). The operator's framing ("I don't see much value in
migration... I leave this decision to you") is fully satisfied by the single `add_column` call; no
additional UPDATE statement is needed even for a "proper" fail-closed backfill, because the
`server_default` *is* the backfill.

**`ArgumentStatusLog` extension (D-15):**
```python
op.add_column("argument_status_log", sa.Column("override_reason", sa.Text(), nullable=True))
op.add_column(
    "argument_status_log",
    sa.Column(
        "trust_tier_at_transition",
        sa.Enum("verified", "trusted", "provisional", "uncertain", name="trust_tier", create_type=False),
        nullable=True,
    ),
)
```
Both nullable — every historical and non-override status-log row (DRAFT/PUBLISHED/UNPUBLISHED
writes that aren't overrides) legitimately has `NULL` here, mirroring the existing minimal-schema
precedent [VERIFIED: `api/models/models.py:494-500`, quoted: `"""Minimal schema (D-06): no
previous_status, notes, or triggered_by in v1.5."""` — D-15 explicitly revisits this minimalism,
not silently expands it].

**D-03's new write site — `ArgumentStatusLog` at candidate birth:** neither
`import_convokit.py` nor `ingest.py` currently writes an `ArgumentStatusLog` row
[VERIFIED: grep for `ArgumentStatusLog` in both files this session returned no matches]. Both must
gain `session.add(ArgumentStatusLog(argument_id=argument.id, status=ArgumentStatusEnum.CANDIDATE))`
immediately after the `Argument` row is flushed (so `argument.id` exists) and before the function
returns/commits. This is a genuinely new write site in both writer paths, not a rename of an
existing one.

## D-13 Confirmation (Review-Signal Gap)

Re-verified against current source, exactly as CONTEXT.md's D-13 states:
```python
# api/models/models.py:380-392 (quoted in full)
class ArgumentParticipant(Base):
    """Which people spoke in which arguments (populated at parse time from raw labels)."""

    __tablename__ = "argument_participants"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null until resolved
    raw_speaker_label = Column(String(200), nullable=False)
    side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False)
    # Phase 22 — migration 0013: TOC subtitle from cover extractor (PJOB-13)
    # Phase 44 D-05 — migration 0025: renamed title -> descriptor (full-stack rename)
    descriptor = Column(String(500), nullable=True)
```
**No `review_state`, no `method` column exists on `ArgumentParticipant` today.** The closest
existing analogue is `Person.name_needs_review` / `Person.name_extraction_metadata`
[VERIFIED: `api/models/models.py:140-150`, quoted: `"""name_needs_review surfaces the People
directory's `Name review` attention filter for any full_name this migration (or later
pipeline/import extraction) could not confidently split into structured parts.
name_extraction_metadata persists independently of operator-edited name parts — an operator edit
never clears or rewrites it, and it is never used to overwrite an existing operator value."""`] —
but this lives on `Person`, not `ArgumentParticipant`, and D-10 (per-argument rows only, no fan-out
through `Person`) means this phase's floor cannot reach it without violating D-10's own bounded-
recompute guarantee. D-13's resolution stands confirmed: `derive_tier(source, method,
review_state)` keeps `review_state` in its signature, Phase 48 always supplies `"unreviewed"` for
every constituent, and Phase 49 will supply the real per-participant value with no signature
change once `ArgumentParticipant.review_state`/`.method` land.

## Common Pitfalls

### Pitfall 1: Treating "candidate replaces pipeline" as a find-and-replace

**What goes wrong:** Editing the enum and the two or three most-visible write sites, then assuming
"pipeline" is gone from the codebase's active vocabulary.

**Why it happens:** CONTEXT.md's own canonical-refs list names exactly three `admin_jobs.py` guard
lines plus the `import_convokit.py` write site — a natural reading is "that's the complete set."
This research found two more production comparisons (`admin_jobs.py:804`,
`admin_people.py:968`) by grepping the whole tree rather than trusting the pre-enumerated list.

**How to avoid:** Re-run `grep -rn "ArgumentStatusEnum.PIPELINE" api/ pipeline/` (excluding
`api/tests/` and `pipeline/tests/`) as a plan verification step, and confirm every hit is
either (a) the enum definition itself, (b) a test fixture intentionally exercising the still-valid
dead value, or (c) updated to `CANDIDATE`.

**Warning signs:** Any admin UI page or resolve card that renders read-only or "already finalized"
immediately after a fresh corpus import or PDF ingest.

### Pitfall 2: Recomputing outside the mutation's transaction

**What goes wrong:** Calling `recompute_argument_tier` after `db.commit()` rather than before/as
part of it — a crash between the two leaves a stale `trust_tier` with no re-derivation trigger,
silently violating TRUST-02's "recomputed on every mutation path."

**Why it happens:** Several existing writers in this file already call `db.commit()` then
`db.refresh(argument)` afterward (`publish_argument`, `unpublish_argument`) — it's easy to append a
recompute call after that pattern instead of before the commit.

**How to avoid:** `recompute_argument_tier`'s own `UPDATE arguments SET trust_tier = ...` must be
issued and the whole batch committed together — i.e., call recompute BEFORE the writer's
`await db.commit()`, not after.

**Warning signs:** `recompute-trust --all` after a fresh `reset_to_fixture` reports nonzero changed
rows (violates D-09's "must change 0 rows" verification contract).

### Pitfall 3: `min()` over an empty sequence

**What goes wrong:** `min([])` raises `ValueError: min() iterable argument is empty` — a genuine
Python runtime crash, not a graceful UNCERTAIN result, if the zero-utterance / zero-participant
case isn't special-cased.

**Why it happens:** The natural implementation is "collect all constituent tiers into a list, take
`min()`" — correct for the non-empty case, but every freshly-created argument (before its first
utterance lands) hits this exact empty case.

**How to avoid:** Explicit early-return: `if not constituent_tiers: return TrustTier.UNCERTAIN`
before calling `min()`. Must be covered by a unit test per D-21 (this is exactly the kind of base
case CONTEXT.md's "Claude's Discretion" item flags as unsettled).

### Pitfall 4: Forgetting `.execution_options(synchronize_session=False)` on the recompute UPDATE

**What goes wrong:** An `UPDATE arguments SET trust_tier = ...` without this option can desync the
ORM's in-session identity map from the just-written value, so a subsequent `get_argument_detail`
read in the same request returns the stale `trust_tier`.

**Why it happens:** This is an easy-to-miss detail specific to this codebase's async SQLAlchemy
setup — every single bulk `update()`/`delete()` in `admin_arguments.py` and `admin_jobs.py` already
carries this option [VERIFIED: confirmed present on all six `update()`/`delete()` calls read in
`admin_arguments.py` this session].

**How to avoid:** Copy the exact `.execution_options(synchronize_session=False)` +
`db.refresh(argument)` pattern from `publish_argument` (lines 598-615) for any recompute call whose
result will be read back in the same request/session.

### Pitfall 5: Building `trust_tier`'s enum type before `'candidate'` exists on `argument_status`

**What goes wrong:** These are two independent PG enum types (`argument_status` and the new
`trust_tier`) — no ordering dependency actually exists between them, but a migration author might
assume one does and add unnecessary cross-type sequencing, or conversely forget that the
`argument_status` `ADD VALUE` step still needs its own `COMMIT`-then-continue discipline
independent of whatever else the migration does.

**Why it happens:** Migration 0026's docstring calls out an explicit ordering constraint between
its own steps ("CREATE TABLE must come AFTER the ALTER TYPE ADD VALUE... so that the enum type
already contains the new value") — that constraint is real for 0026's *own* `argument_status_log`
column referencing `argument_status`, but does not transitively apply to an unrelated new type
like `trust_tier`.

**How to avoid:** Order this migration as: (1) `COMMIT` + `ALTER TYPE argument_status ADD VALUE
'candidate'`, (2) the `UPDATE ... SET status='candidate' WHERE status='pipeline'` flip, (3)
`CREATE TYPE trust_tier` (independent, order-agnostic relative to step 1/2), (4) `ADD COLUMN
arguments.trust_tier`, (5) `ADD COLUMN argument_status_log.override_reason` /
`.trust_tier_at_transition` (must come after step 3, since these columns reference the `trust_tier`
type).

## Code Examples

### Deriving a per-row tier (D-07's pure function shape)

```python
# api/domain/trust.py — NEW, modeled on api/domain/person_names.py's module-level
# docstring convention (quoted structure, not literal contents)
"""
Pure, dependency-light domain contract for trust-tier derivation (Phase 48).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain importable
by API services, pipeline commands, tests, and Alembic migrations without
initializing the app or a database connection — mirroring
api/domain/person_names.py's structural conventions exactly.
"""
from __future__ import annotations
import enum


class TrustTier(str, enum.Enum):
    VERIFIED = "verified"
    TRUSTED = "trusted"
    PROVISIONAL = "provisional"
    UNCERTAIN = "uncertain"


_TIER_ORDER = {
    TrustTier.UNCERTAIN: 0,
    TrustTier.PROVISIONAL: 1,
    TrustTier.TRUSTED: 2,
    TrustTier.VERIFIED: 3,
}


def derive_tier(source: str, method: str, review_state: str) -> TrustTier:
    """Derive a single row's trust tier from (source, method, review_state).

    review_state wins first (provenance-and-trust-model.md): a confirmed/edited
    row is VERIFIED regardless of source; needs_review floors to UNCERTAIN
    regardless of source. Phase 48 always passes review_state="unreviewed"
    (D-13) — Phase 49 supplies the real value with no signature change.
    """
    if review_state in ("operator_confirmed", "operator_edited"):
        return TrustTier.VERIFIED
    if review_state == "needs_review":
        return TrustTier.UNCERTAIN
    # review_state == "unreviewed" (or Phase 48's constant "unreviewed") falls
    # through to source/method:
    if source == "corpus" and method == "direct":
        return TrustTier.TRUSTED
    if source == "seed" and method == "direct":
        return TrustTier.TRUSTED
    if method == "normalized" or (source == "pdf_pipeline" and method == "rule_based"):
        return TrustTier.PROVISIONAL
    # pdf_pipeline/llm_corrective, or any other unmapped combination
    return TrustTier.UNCERTAIN


def floor_tier(tiers: list[TrustTier]) -> TrustTier:
    """The argument-level rollup: the minimum (least-trusted) tier among all
    constituents. An empty constituent set (zero utterances/participants,
    e.g. a just-born candidate) is the maximal-uncertainty case, not a
    free pass — see 48-RESEARCH.md "Zero-Utterance Tier Decision"."""
    if not tiers:
        return TrustTier.UNCERTAIN
    return min(tiers, key=lambda t: _TIER_ORDER[t])
```

### Unresolved-speaker and stage-direction handling in the recompute service (D-11/D-12)

```python
# Sketch for api/services/admin_arguments.py (or a new api/services/trust.py) —
# the per-argument, bounded query shape D-10 requires.
async def recompute_argument_tier(db: AsyncSession, argument_id: int) -> TrustTier:
    utterance_rows = (
        await db.execute(
            select(Utterance.person_id, Utterance.is_stage_direction, ImportRun.source, ImportRun.method)
            .join(ImportRun, Utterance.import_run_id == ImportRun.id)
            .where(Utterance.argument_id == argument_id)
        )
    ).all()
    participant_rows = (
        await db.execute(
            select(ArgumentParticipant.person_id)
            .where(ArgumentParticipant.argument_id == argument_id)
        )
    ).all()

    tiers: list[TrustTier] = []
    for person_id, is_stage_direction, source, method in utterance_rows:
        if is_stage_direction:  # D-12: no speaker to attribute, excluded from the floor
            continue
        if person_id is None:  # D-11: unresolved speaker floors to UNCERTAIN
            tiers.append(TrustTier.UNCERTAIN)
            continue
        tiers.append(derive_tier(source.value, method.value, "unreviewed"))
    for (person_id,) in participant_rows:
        if person_id is None:
            tiers.append(TrustTier.UNCERTAIN)
        # else: D-13 — no per-participant source/method/review_state exists yet
        # in Phase 48; a resolved participant contributes no additional signal
        # beyond what its utterances already contributed.

    result = floor_tier(tiers)
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(trust_tier=result)
        .execution_options(synchronize_session=False)
    )
    return result
```
This sketch is illustrative of the query shape and ordering, not a final implementation —
the planner should verify field names against the models once `TrustTier`/`trust_tier` are added,
and decide the exact placement (new `api/services/trust.py` vs. folding into
`admin_arguments.py`) at plan time.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Trust reconstructed by reading `pipeline_runs.strategy` free text + nullable `oyez_*` columns | Trust declared via `ImportRun.source`/`.method` (Phase 47) | 2026-08-17, migration 0026 | Phase 48 can derive tier from structured enum columns instead of string parsing |
| `Argument.status` = pipeline/draft/published/unpublished, with PIPELINE meaning both "just created" and "actively being parsed" | `candidate`/`draft`/`published`/`unpublished`, with `candidate` explicitly meaning "exists, not yet approved, trust-tiered" | This phase (D-01) | Every PIPELINE-keyed guard becomes a CANDIDATE-keyed guard — see the Guard Inventory |
| No trust concept at all — publish gated only on `resolved_at IS NOT NULL` | Two independent gates: `resolved_at IS NULL` (hard, D-14) and `trust_tier == UNCERTAIN` (overridable, D-14) | This phase | `publish_argument` gains a second failure mode with a distinct, overridable error shape |

**Deprecated/outdated:** `ArgumentStatusEnum.PIPELINE` becomes a dead-but-permanent enum value
after this phase (PG cannot drop it) — new code must never write it, but old test fixtures and any
already-migrated dev-DB rows may still carry it until the D-24 flip runs.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `derive_tier`'s exact tier-boundary mapping (e.g. `seed/direct` → TRUSTED, `normalized` → PROVISIONAL) in the Code Examples sketch, beyond the four rows the design note gives verbatim | Code Examples | Low — `provenance-and-trust-model.md`'s table is the source of truth and is explicitly "already settled, do not re-open"; the sketch is illustrative code shape, not a claim about which combinations exist. The planner/executor should re-derive the exhaustive mapping table directly from that note's tier table rather than trust this sketch's `if`-chain verbatim. |
| A2 | The recommendation to fold `recompute_argument_tier` into `api/services/admin_arguments.py` vs. a new `api/services/trust.py` | Architecture Patterns / Recommended Project Structure | Low — either placement satisfies D-07; this is a file-organization preference, not a locked decision. Flagged so the planner treats it as a choice, not a requirement. |
| A3 | `PublishRequest.override_reason` as the exact Pydantic field name for the override body | Override Endpoint Shape Decision | Low — the *shape* (extend existing endpoint's body) is the load-bearing recommendation; the literal field name is a naming preference the planner/executor can adjust without contradicting any CONTEXT.md decision. |

**All claims that touch schema, migrations, or existing-guard behavior in this document are
`[VERIFIED]` against source read this session** — the assumptions above are limited to
illustrative code-shape details, not structural facts.

## Open Questions

1. **Should `update_participant_side` (writer #6 in the enumeration) actually trigger a
   recompute, given side/descriptor don't feed `derive_tier` under D-10's current scope?**
   - What we know: D-07 says "every writer — pipeline and API alike" calls recompute; D-10 scopes
     the floor's *inputs* to `person_id`/`is_stage_direction`/`source`/`method`, none of which
     `update_participant_side` touches.
   - What's unclear: whether "every writer" means literally every write to any table this phase
     touches, or specifically every write that could change a constituent's derived tier.
   - Recommendation: call it anyway (cheap — one bounded per-argument query) for forward
     consistency with Phase 49, which will add `review_state`/`method` to `ArgumentParticipant`
     and make this write path genuinely tier-relevant. Calling it now costs nothing and avoids a
     second phase having to remember to add the call site.

2. **Exact wording/shape of the "what dragged the tier down" reason list in the blocked-publish
   response (D-19's "not just report the tier" requirement).**
   - What we know: the response needs enough structure for the SvelteKit page to render something
     like "3 utterances have no resolved speaker" per the Specific Ideas note in CONTEXT.md.
   - What's unclear: whether this needs a structured list of `{reason_code, count}` or a
     pre-formatted string list is sufficient for a "minimal frontend" (D-19).
   - Recommendation: a small structured payload (`list[{"code": "unresolved_speaker", "count":
     3}]`) is cheap to build from the same query `recompute_argument_tier` already runs (just
     don't discard the per-constituent breakdown before returning), and keeps the door open for
     Phase 49's review queue to reuse the same shape rather than re-deriving it.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Alembic | Migration authorship | ✓ (via `.venv`) | 1.19.1 [VERIFIED this session] | — |
| SQLAlchemy | ORM/domain code | ✓ (via `.venv`) | 2.0.52 [VERIFIED this session] | — |
| PostgreSQL dev DB (`alembic current` check) | Confirming no drift before adding migration 0027 | **Not probed — no DB credentials available or assumed this session, per CONTEXT.md's explicit instruction** | — | Verified from migration files on disk instead (head = 0026, confirmed via directory listing + each file's own `down_revision` header) |
| `psql` CLI | Direct DB inspection | ✗ (not on PATH in this sandbox) | — | Not needed — all schema facts were confirmed by reading migration/model source files directly |

**Missing dependencies with no fallback:** None — the one "missing" item (a live `alembic
current` check against the real dev DB) has a sound file-based fallback already applied in this
research (confirmed head = 0026 by reading every migration file's `down_revision` chain on disk).

**Missing dependencies with fallback:** `psql`/live DB access — fallback is source-file reading,
already exercised throughout this document.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio, `asyncio_mode = auto` [VERIFIED: `pytest.ini`, read this session] |
| Config file | `pytest.ini` (`testpaths = tests pipeline/tests api/tests`, `pythonpath = .`) |
| Quick run command | `./.venv/bin/python -m pytest api/tests/test_admin_arguments_service.py -q` (or the specific new test module) |
| Full suite command | `./.venv/bin/python -m pytest` (matches `.planning/config.json`'s `workflow.test_command`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|-------------|
| TRUST-01 | `derive_tier()` maps every (source, method, review_state) combination correctly | unit | `pytest api/tests/test_trust_domain.py -x` | ❌ Wave 0 — new file |
| TRUST-02 | Floor rollup recomputes on utterance/participant change, excludes stage directions, floors on unresolved speaker | unit + integration (DB-gated via `TEST_DATABASE_URL`) | `pytest api/tests/test_trust_recompute.py -x` | ❌ Wave 0 — new file |
| TRUST-03 | New corpus/PDF argument is born CANDIDATE with tier set | integration | `pytest pipeline/tests/test_import_convokit_core.py -x` (extend existing) + live `reset_to_fixture` reseed | ✅ existing file to extend |
| TRUST-04 | Publish hard-blocked on UNCERTAIN; `resolved_at IS NULL` remains separately hard-blocked, non-overridable | integration | `pytest api/tests/test_published_gate.py -x` (extend existing — already seeds/tears down its own published/unpublished rows per the 2026-08-18 UAT audit's N-2 fix) | ✅ existing file to extend |
| TRUST-05 | Override with non-empty reason succeeds and is logged with `trust_tier_at_transition` | integration | `pytest api/tests/test_admin_arguments_routes.py -x` (extend existing) | ✅ existing file to extend |
| D-22 (carried defect) | `delete_argument` cascades through `argument_status_log`; fails before the fix, passes after | integration | `pytest api/tests/test_admin_arguments_service.py -x` (extend existing, or a new focused test) | ✅ existing file to extend |
| D-23 (public-leak ban) | No public response contains `trust_tier` | contract | `pytest api/tests/test_arguments.py -x` (extend the exact pattern at lines 259-264) + extend to `/cases`, `/people/{id}` | ✅ existing pattern to extend, per-endpoint coverage may need a new file for `/cases`/`/people` if not already covered there |

### Sampling Rate

- **Per task commit:** the specific new/extended test module for that task (`pytest
  api/tests/test_trust_domain.py -q`, etc.)
- **Per wave merge:** `./.venv/bin/python -m pytest api/tests pipeline/tests -q`
- **Phase gate:** full suite green (`./.venv/bin/python -m pytest`) before `/gsd-verify-work`, plus
  the live `reset_to_fixture` → `recompute-trust --all` → assert 0 rows changed check (D-09/D-21's
  falsifiable verification vehicle, not automated by pytest — run manually or via a dev-only script
  akin to the existing `check_counts.py`/`check_fixture_integrity.py` verify-scripts pattern from
  Phase 43)

### Wave 0 Gaps

- [ ] `api/tests/test_trust_domain.py` — pure unit coverage for `derive_tier`/`floor_tier`,
  including the empty-list UNCERTAIN base case (Pitfall 3) — no DB needed, fastest feedback loop
- [ ] `api/tests/test_trust_recompute.py` — DB-gated coverage of `recompute_argument_tier` against
  `TEST_DATABASE_URL`, covering every tier combination CONTEXT.md's D-21 requires (including
  UNCERTAIN via a NULL `person_id` fixture, and the stage-direction exclusion)
- [ ] A DB-gated regression test proving `delete_argument` raises `ForeignKeyViolation` before the
  D-22 fix and passes after — new test, not an extension, per D-22's "failing-then-passing" mandate
- [ ] Framework install: none — pytest/pytest-asyncio already configured

*(No shared-fixture gaps beyond the above — `conftest.py`'s DB-redirect discipline already covers
every new test file under `api/tests/`/`pipeline/tests/` per the rootdir conftest rule in
CLAUDE.md.)*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | No | Unchanged — this phase adds no new auth surface |
| V3 Session Management | No | N/A |
| V4 Access Control | Yes | The existing `X-Admin-Token` header check (D-18: "No extra guard beyond the existing admin token") — every new endpoint/body field rides the same gate every other admin mutation already uses |
| V5 Input Validation | Yes | `override_reason` must be validated non-empty server-side (D-17) — Pydantic `str` with a service-layer non-blank check, mirroring the existing pattern of raising a specific `ValueError` the router maps to 422 (e.g. `invalid_date_format`, `slug_collision`) |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Mass-assignment via the publish-override body | Tampering | `PublishRequest` schema must expose ONLY `override_reason` — exactly the same allow-list discipline `ArgumentUpdate`/`ParticipantSideUpdate` already document ("T-11-MASS", "T-26-04") |
| Trust-tier leak into a public response (apolitical constraint violation) | Information Disclosure | D-23's contract test, modeled exactly on the existing `strategy`/`source`/`method`/`external_id` leak-ban assertions at `api/tests/test_arguments.py:259-264` |
| Empty/whitespace-only override reason treated as "provided" | Tampering (bypassing the "deliberate" requirement) | Server-side `.strip()` check before accepting — client-side disabled-submit-button is defense-in-depth only, never authoritative, per this codebase's established pattern (T-11-PUBGATE's own docstring: "backend must enforce this independently of the UI") |

## Sources

### Primary (HIGH confidence — read directly this session)

- `api/models/models.py` (full file) — enum definitions, `Argument`/`ArgumentParticipant`/
  `ArgumentStatusLog`/`ImportRun`/`Utterance` schemas
- `api/services/admin_arguments.py` (full file) — `publish_argument`, `unpublish_argument`,
  `delete_argument`, `list_arguments`, `get_argument_stats`, `update_participant_side`
- `api/services/admin_jobs.py` (relevant sections) — `approve_job`, `list_jobs`,
  `get_run_readiness`, `update_resolve_row_for_job`
- `api/services/admin_people.py` (relevant section) — `list_resolve_rows_for_job`'s `editable` flag
- `api/routers/admin.py` (relevant section) — `/publish`, `/unpublish` route handlers
- `app/src/routes/admin/arguments/[id]/+page.svelte` / `+page.server.ts` — Status card, publish
  action, badge helpers
- `pipeline/commands/import_convokit.py`, `pipeline/commands/ingest.py`, `pipeline/__main__.py` —
  writer paths and CLI subcommand structure
- `api/services/admin_dev.py` — `reset_to_fixture`'s exact fixture-state-realization logic (the
  live verification vehicle for D-21)
- `scripts/delete_fixture_argument.py` — the false comment D-22 corrects, confirmed verbatim
- `api/domain/person_names.py`, `api/domain/docket_values.py`, `api/domain/__init__.py` —
  cross-layer pure-module precedent
- `api/services/argument_uniqueness.py` — pipeline-imports-API-service precedent
- `alembic/versions/0008_side_enum_and_argument_status.py`,
  `0012_unpublished_enum_and_status_log.py`, `0026_import_run_provenance.py` (full files) — enum
  expansion, new-type creation, and backfill idioms
- `alembic/versions/` directory listing — confirmed head = 0026
- `api/tests/test_arguments.py` — the exact public-leak-ban assertion precedent (lines 259-264)
- `pytest.ini`, root `conftest.py` (partial) — test isolation discipline
- `.planning/config.json` — `workflow.nyquist_validation: true`, `test_command`
- `.planning/phases/48-trust-lifecycle/48-CONTEXT.md`, `48-DISCUSSION-LOG.md`
- `.planning/notes/provenance-and-trust-model.md`, `import-entity-sketch.md`,
  `import-architecture-diagnosis.md`
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`

### Secondary (MEDIUM confidence)

- None used — every claim in this document that isn't a research recommendation/rationale was
  verified against project source read this session.

### Tertiary (LOW confidence)

- None — no WebSearch was needed; this phase has no external-library research surface.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; every primitive is an already-pinned, already-in-use
  package confirmed via the venv this session.
- Architecture: HIGH — every pattern cited is either an explicit CONTEXT.md decision or a directly-
  quoted precedent already live in the codebase (enum expansion idiom, cross-layer domain module,
  in-transaction recompute discipline).
- Pitfalls: HIGH — the two "not in CONTEXT.md's canonical refs" guard-inventory findings
  (`admin_jobs.py:804`, `admin_people.py:968`) were found by exhaustive grep + direct file read this
  session, not inferred.

**Research date:** 2026-08-18
**Valid until:** No external dependency expiry risk (no third-party library versions pinned by this
research). Re-verify the Alembic head number if any other phase's migration lands between this
research and Phase 48's plan execution — re-run `ls alembic/versions/` before planning if more than
a few days pass.
