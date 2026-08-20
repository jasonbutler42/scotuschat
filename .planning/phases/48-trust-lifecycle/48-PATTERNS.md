# Phase 48: Trust & Lifecycle - Pattern Map

**Mapped:** 2026-08-18
**Files analyzed:** 15 (new + modified, per CONTEXT.md/RESEARCH.md)
**Analogs found:** 15 / 15

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `api/domain/trust.py` (NEW) | utility (pure domain) | transform | `api/domain/person_names.py` / `api/domain/docket_values.py` | exact |
| `api/services/admin_arguments.py::recompute_argument_tier` (NEW fn) | service | CRUD (read-many, write-one) | `admin_arguments.py::publish_argument` (bulk update + log + refresh shape) | exact |
| `api/services/admin_arguments.py::publish_argument` (MOD — UNCERTAIN gate + override) | service | request-response | itself, extended; error-shape precedent from `update_argument`'s `ValueError("slug_collision")` | exact |
| `api/services/admin_arguments.py::delete_argument` (MOD — D-22 fix) | service | CRUD | itself (FK-ordered cascade already has 5 steps; add one) | exact |
| `api/models/models.py` (MOD — enum, `trust_tier` column, `ArgumentStatusLog` cols) | model | CRUD | itself, `ArgumentStatusEnum`/`ArgumentStatusLog` existing declarations | exact |
| `api/schemas/admin_arguments.py` (MOD — `PublishRequest`, `ArgumentDetail.trust_tier`) | model (schema) | request-response | existing `ArgumentUpdate`/`ArgumentDetail` Pydantic models | exact |
| `api/routers/admin.py::publish_argument` route (MOD — body param, error mapping) | route/controller | request-response | itself; `update_argument` route's `slug_collision`/`docket_collision` → 422 mapping | exact |
| `alembic/versions/0027_*.py` (NEW migration) | migration | batch | `0012_unpublished_enum_and_status_log.py` (enum ADD VALUE) + `0026_import_run_provenance.py` (new enum types, DO-block) | exact |
| `api/services/admin_jobs.py::approve_job` (MOD — PIPELINE→CANDIDATE, + recompute call) | service | request-response | itself | exact |
| `api/services/admin_jobs.py::list_jobs` / `get_run_readiness` / `update_resolve_row_for_job` (MOD — 3 PIPELINE guards) | service | request-response | itself (mechanical compare-swap) | exact |
| `api/services/admin_people.py::list_resolve_rows_for_job` (MOD — 1 PIPELINE guard) | service | request-response | itself | exact |
| `pipeline/commands/import_convokit.py` (MOD — CANDIDATE write + status-log + recompute) | service (pipeline writer) | batch | itself; `ArgumentStatusLog` write precedent from `admin_jobs.py:approve_job`/`admin_arguments.py:publish_argument` | exact |
| `pipeline/commands/ingest.py` (MOD — status-log + recompute at birth) | service (pipeline writer) | batch | same as above | exact |
| `pipeline/commands/recompute_trust.py` (NEW CLI command) | service (pipeline writer / CLI) | batch | no existing "recompute all rows" command exists 1:1; closest shape is `pipeline/commands/resolve.py`/`seed_aliases.py` (idempotent, `--all`-style offline command) wired via `pipeline/__main__.py`'s subparser pattern | role-match |
| `pipeline/__main__.py` (MOD — wire `recompute-trust` subcommand) | route/CLI dispatch | request-response | itself (`resolve`/`seed-aliases` subparser + `elif args.command ==` dispatch blocks) | exact |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` + `+page.svelte` (MOD — override reason field, block-reason display) | component/provider | request-response | itself (`publish` action, Status/Publish card) | exact |
| `api/tests/test_arguments.py` (MOD — extend leak-ban) | test | request-response | itself, lines 259-264 | exact |
| `api/tests/test_admin_arguments_service.py` (MOD — D-22 regression) | test | CRUD | itself | exact |
| `api/tests/test_trust_domain.py` (NEW) | test | transform | `api/domain/person_names.py`'s own test file pattern (pure-function unit tests, no DB) | role-match |
| `api/tests/test_trust_recompute.py` (NEW) | test | CRUD | `api/tests/test_admin_arguments_service.py` (DB-gated service test against `TEST_DATABASE_URL`) | role-match |
| `scripts/delete_fixture_argument.py` (MOD — comment fixes) | utility | file-I/O | itself | exact |

## Pattern Assignments

### `api/domain/trust.py` (utility, transform)

**Analog:** `api/domain/person_names.py`, `api/domain/docket_values.py`

**Module docstring / no-framework-imports contract** (mirror exactly — both existing modules state this verbatim):
```python
"""
Pure, dependency-light domain contract for trust-tier derivation (Phase 48).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection —
mirroring api/domain/person_names.py's structural conventions exactly.
"""
from __future__ import annotations
```

**Core pattern** — `derive_tier` / `floor_tier` (RESEARCH.md's Code Examples section gives the
full sketch; re-derive the exhaustive source/method mapping from
`.planning/notes/provenance-and-trust-model.md`'s tier table rather than trusting the sketch's
`if`-chain verbatim per Assumption A1):
```python
class TrustTier(str, enum.Enum):
    VERIFIED = "verified"
    TRUSTED = "trusted"
    PROVISIONAL = "provisional"
    UNCERTAIN = "uncertain"

def derive_tier(source: str, method: str, review_state: str) -> TrustTier: ...
def floor_tier(tiers: list[TrustTier]) -> TrustTier:
    if not tiers:
        return TrustTier.UNCERTAIN   # Pitfall 3 — never call bare min() on empty list
    return min(tiers, key=lambda t: _TIER_ORDER[t])
```

**Cross-layer import precedent** (how the offline `pipeline` package imports an `api/domain`
module without initializing FastAPI/DB — quoted exactly):
```python
# pipeline/commands/ingest.py:47-48
from api.services.argument_uniqueness import is_argument_pair_violation
from api.domain.docket_values import DocketValueError, normalize_docket_value
```
`pipeline/commands/recompute_trust.py` and the modified `import_convokit.py`/`ingest.py` import
`api.domain.trust` and the new `recompute_argument_tier` service helper the same way — this is
an established pattern, not new architecture.

---

### `api/services/admin_arguments.py::recompute_argument_tier` (NEW, service, CRUD)

**Analog:** `publish_argument`'s bulk-update-then-refresh shape (`api/services/admin_arguments.py:570-616`, quoted in full above under Shared Patterns). Query shape sketch from RESEARCH.md:

```python
async def recompute_argument_tier(db: AsyncSession, argument_id: int) -> TrustTier:
    utterance_rows = (await db.execute(
        select(Utterance.person_id, Utterance.is_stage_direction, ImportRun.source, ImportRun.method)
        .join(ImportRun, Utterance.import_run_id == ImportRun.id)
        .where(Utterance.argument_id == argument_id)
    )).all()
    participant_rows = (await db.execute(
        select(ArgumentParticipant.person_id).where(ArgumentParticipant.argument_id == argument_id)
    )).all()

    tiers: list[TrustTier] = []
    for person_id, is_stage_direction, source, method in utterance_rows:
        if is_stage_direction:          # D-12
            continue
        if person_id is None:           # D-11
            tiers.append(TrustTier.UNCERTAIN)
            continue
        tiers.append(derive_tier(source.value, method.value, "unreviewed"))
    for (person_id,) in participant_rows:
        if person_id is None:
            tiers.append(TrustTier.UNCERTAIN)

    result = floor_tier(tiers)
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(trust_tier=result)
        .execution_options(synchronize_session=False)   # project-wide critical guard (Pitfall 4)
    )
    return result
```

**Must be called BEFORE `await db.commit()`** in every writer (Pitfall 2) — not after, unlike
the post-commit-refresh idiom used elsewhere for re-reading a just-mutated row.

---

### `api/services/admin_arguments.py::publish_argument` (MOD — UNCERTAIN gate + override)

**Analog:** itself, extended in place. Current full body [VERIFIED, quoted]:
```python
async def publish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    # D-07 / T-11-PUBGATE: backend must enforce this independently of the UI
    if argument.resolved_at is None:
        raise ValueError("Cannot publish: resolve step not yet complete")
    if argument.status == ArgumentStatusEnum.PUBLISHED:
        raise ValueError("Already published")

    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(status=ArgumentStatusEnum.PUBLISHED, published_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.PUBLISHED))
    await db.commit()
    await db.refresh(argument)
    return await get_argument_detail(db, argument_id)
```

**Insert the D-14 UNCERTAIN gate** between the `resolved_at IS NULL` check and the
already-PUBLISHED check (D-14: two *separate* gates, `resolved_at` non-overridable, UNCERTAIN
overridable). Signature becomes `publish_argument(db, argument_id, override_reason: str | None = None)`.
Follow the existing `ValueError("slug_collision")` / `ValueError("docket_collision")` tagged-error
shape from `update_argument` (same file) for a **distinguishable** blocked-error
(`ValueError("uncertain_tier_blocked")`, carrying structured tier+reasons — RESEARCH.md's Override
Endpoint Shape Decision) so the router/SvelteKit layer can branch on it exactly like it already
branches on collision errors.

The `ArgumentStatusLog(...)` write gains `override_reason=` and `trust_tier_at_transition=`
kwargs (D-15) when the override path is taken — same `db.add(...)` call site, two more kwargs.

**Router error-mapping precedent to follow** [VERIFIED: `api/routers/admin.py:1121-1139`]:
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
    if result is None:
        raise HTTPException(status_code=404, detail="Argument not found")
    return ArgumentDetail(**result)
```
Add a `body: PublishRequest` param (Pydantic, `override_reason: str | None = None`) and pass
`override_reason=body.override_reason` through — same call/except shape, additive only.

---

### `api/services/admin_arguments.py::delete_argument` (MOD — D-22 fix)

**Analog:** itself. FK-ordered cascade [VERIFIED: `api/services/admin_arguments.py:744-816`,
quoted]:
```python
# Step 1: Delete utterances referencing this argument (must be before import_run rows)
await db.execute(delete(Utterance).where(Utterance.argument_id == argument_id)
    .execution_options(synchronize_session=False))
# Step 2: Delete import_run rows for this argument (after utterances)
await db.execute(delete(ImportRun).where(ImportRun.argument_id == argument_id)
    .execution_options(synchronize_session=False))
# Step 3: Delete argument_participants
await db.execute(delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument_id)
    .execution_options(synchronize_session=False))
# Step 4: Delete case_arguments join rows
await db.execute(delete(CaseArgument).where(CaseArgument.argument_id == argument_id)
    .execution_options(synchronize_session=False))
# Step 5: NULL out AdminJob.argument_id
await db.execute(update(AdminJob).where(AdminJob.argument_id == argument_id).values(argument_id=None)
    .execution_options(synchronize_session=False))
# Step 6: Delete the argument itself
```
**Fix (D-22):** insert one more `delete()` step, same shape, anywhere before Step 6:
```python
await db.execute(delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)
    .execution_options(synchronize_session=False))
```
Write the failing-then-passing regression test FIRST (create a DRAFT + one `ArgumentStatusLog`
row, assert `delete_argument` raises `ForeignKeyViolation`), then land this one-line fix.

Also fix `scripts/delete_fixture_argument.py:25` — its comment falsely claims "a DRAFT argument
can never have [an `argument_status_log` row]"; correct once D-03 makes every argument (including
DRAFT) carry a status-log row from birth.

---

### `alembic/versions/0027_trust_tier_and_candidate_status.py` (NEW migration)

**Analog:** `0012_unpublished_enum_and_status_log.py` (enum `ADD VALUE` idiom) +
`0026_import_run_provenance.py` (new-enum-type DO-guarded idiom). Head is `0026`
[VERIFIED: `alembic/versions/` listing, `0026`'s own header `down_revision: str = "0025"`].

**Enum-expansion idiom** [VERIFIED, quoted exactly, `0012_unpublished_enum_and_status_log.py:59-60`]:
```python
op.execute(sa.text("COMMIT"))
op.execute(sa.text("ALTER TYPE argument_status ADD VALUE IF NOT EXISTS 'candidate'"))
```
Cannot run inside a transaction block — commit Alembic's implicit transaction first (same
discipline both existing migrations use).

**New-enum-type idiom** [VERIFIED, quoted exactly, `0026_import_run_provenance.py:59-78`]:
```python
conn = op.get_bind()
for type_name, ddl in [
    ("trust_tier", "CREATE TYPE trust_tier AS ENUM "
     "('verified', 'trusted', 'provisional', 'uncertain')"),
]:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}
    ).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))
```

**D-24 flip-existing-rows step**, modeled on migration 0008's backfill-by-precedence UPDATE shape:
```python
op.execute(sa.text("UPDATE arguments SET status = 'candidate' WHERE status = 'pipeline'"))
```
Must run AFTER the `COMMIT` + `ALTER TYPE ADD VALUE 'candidate'` step.

**`trust_tier` column addition — no separate backfill needed** (PostgreSQL applies a
non-volatile `server_default` to every existing row as part of `ADD COLUMN`):
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

**`ArgumentStatusLog` extension (D-15)**, both nullable — mirrors the existing minimal-schema
precedent [VERIFIED: `api/models/models.py:494-500`, docstring: `"Minimal schema (D-06): no
previous_status, notes, or triggered_by in v1.5."` — D-15 explicitly revisits this]:
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

**Ordering (Pitfall 5):** (1) COMMIT + `ALTER TYPE argument_status ADD VALUE 'candidate'`;
(2) `UPDATE ... SET status='candidate' WHERE status='pipeline'`; (3) `CREATE TYPE trust_tier`
(independent, order-agnostic vs. steps 1/2); (4) `ADD COLUMN arguments.trust_tier`; (5)
`ADD COLUMN argument_status_log.override_reason` / `.trust_tier_at_transition` (must come after
step 3, since they reference the `trust_tier` type).

---

### PIPELINE→CANDIDATE guard sites (mechanical, all same shape)

**Model default** [VERIFIED: `api/models/models.py:303-311`, quoted]:
```python
class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"   # dead-but-permanent after this migration; PG cannot drop it
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    # ADD: CANDIDATE = "candidate"
...
    status = Column(
        SAEnum(ArgumentStatusEnum, name="argument_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=ArgumentStatusEnum.PIPELINE,   # CHANGE to CANDIDATE
    )
```

**`admin_jobs.py::approve_job`** [VERIFIED, quoted, `api/services/admin_jobs.py:576-599`]:
```python
if argument.status != ArgumentStatusEnum.PIPELINE:      # CHANGE to CANDIDATE
    raise ValueError(
        f"Argument is already in '{argument.status.value}' state; cannot approve again."
    )

await db.execute(
    update(Argument)
    .where(Argument.id == job.argument_id)
    .values(status=ArgumentStatusEnum.DRAFT, resolved_at=func.now())
    .execution_options(synchronize_session=False)
)
db.add(ArgumentStatusLog(argument_id=job.argument_id, status=ArgumentStatusEnum.DRAFT))
# INSERT recompute_argument_tier(db, job.argument_id) call here, before commit (writer #4)
await db.execute(update(AdminJob).where(AdminJob.id == job_id)
    .values(status=AdminJobStatus.COMPLETED).execution_options(synchronize_session=False))
await db.commit()
```

**`admin_jobs.py::update_resolve_row_for_job`** — the editability guard [VERIFIED, quoted,
`api/services/admin_jobs.py:804-808`]:
```python
if argument.status != ArgumentStatusEnum.PIPELINE:      # CHANGE to CANDIDATE
    raise ValueError(
        f"Argument {argument.id} is no longer in 'pipeline' state "
        f"(current status: {argument.status.value!r}); resolve rows are "
        "read-only once the argument has been created (D-18, D-19)."
    )
```
Also update the f-string's literal `'pipeline'` wording to `'candidate'`.

**`admin_people.py::list_resolve_rows_for_job`** — the Resolve-card `editable` flag [VERIFIED,
quoted, `api/services/admin_people.py:968`]:
```python
editable = argument.status == ArgumentStatusEnum.PIPELINE   # CHANGE to CANDIDATE
```

Same mechanical `!= / == ArgumentStatusEnum.PIPELINE` → `CANDIDATE` swap applies at
`admin_jobs.py:284` (`list_jobs`, `is_archived` derivation) and `admin_jobs.py:701`
(`get_run_readiness`, "already_created" branch) — not individually quoted here since they follow
the identical one-line comparison-swap shape shown above. **Re-run
`grep -rn "ArgumentStatusEnum.PIPELINE" api/ pipeline/`** (excluding tests) as a plan verification
step — RESEARCH.md's guard inventory found 8 production sites total, two of which
(`admin_jobs.py:804`, `admin_people.py:968`) are NOT in CONTEXT.md's canonical-refs list.

---

### Pipeline writer births — `import_convokit.py` / `ingest.py`

**Status write site** [VERIFIED: `pipeline/commands/import_convokit.py:515`]:
```python
status=ArgumentStatusEnum.PIPELINE,   # CHANGE to CANDIDATE (explicit kwarg — does NOT
                                        # pick up a changed model default)
```
`pipeline/commands/ingest.py:497-502` relies on the model `default=` and needs **no** code
change here once the model default itself changes — do not add an explicit
`status=ArgumentStatusEnum.PIPELINE` kwarg here by copy-paste habit (RESEARCH.md's explicit
warning).

**New `ArgumentStatusLog` write at birth (D-03)** — neither file currently writes one
[VERIFIED via grep this session]. Follow the exact `db.add(ArgumentStatusLog(...))` shape already
used at `admin_jobs.py::approve_job` and `admin_arguments.py::publish_argument`:
```python
db.add(ArgumentStatusLog(argument_id=argument.id, status=ArgumentStatusEnum.CANDIDATE))
```
Add immediately after the `Argument` row is flushed (so `argument.id` exists) and before commit,
followed by a call to `recompute_argument_tier(db, argument.id)` (writer #1/#2 in RESEARCH.md's
enumeration) — same transaction as the birth write.

---

### `pipeline/commands/recompute_trust.py` (NEW CLI command)

**Analog:** no 1:1 "recompute-all" command exists; closest shape is the `--job-id`-optional /
idempotent commands already wired through `pipeline/__main__.py`'s subparser + `elif` dispatch
pattern [VERIFIED, quoted, `pipeline/__main__.py:98-118, 226-236, 348-361`]:
```python
sub = parser.add_subparsers(dest="command", required=True)
...
resolve_p = sub.add_parser(
    "resolve",
    help="Interactively resolve speaker labels for a parse run",
    description="...",
)
resolve_p.add_argument("--run-id", required=True, type=int, help="...")
resolve_p.add_argument("--job-id", type=int, required=False, default=None, help="...")
...
sub.add_parser(
    "seed-aliases",
    help="Pre-seed Justice people records and speaker_alias rows",
    description="Insert roles, people, and speaker_alias rows ... Idempotent — safe to re-run.",
)
...
elif args.command == "resolve":
    try:
        asyncio.run(run_resolve(args))
    except KeyboardInterrupt:
        print("Resolve interrupted.")
```
New `recompute-trust` subcommand should add `--all` (flag) and `--argument-id` (int, mutually
exclusive-ish with `--all`) arguments, follow the same `sub.add_parser(...)` + `elif
args.command == "recompute-trust": asyncio.run(run_recompute_trust(args))` shape, and internally
call `recompute_argument_tier` per argument inside its own `get_session()` transaction (import
precedent already shown above for `ingest.py`). This is D-09's drift-repair tool and the
verification vehicle (`reset_to_fixture` → `recompute-trust --all` → 0 rows changed).

---

### `app/src/routes/admin/arguments/[id]/+page.server.ts` / `+page.svelte` (D-19)

**Analog:** itself — the existing bare `publish` action [VERIFIED, quoted,
`app/src/routes/admin/arguments/[id]/+page.server.ts:329-345`]:
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
Extend: add an optional JSON body `{ override_reason }` read from `request.formData()`, and branch
on the structured 422 payload (`uncertain_tier_blocked` vs. other errors) to render the
block-reason UI rather than the generic "Try again" message — additive change to the existing
action, not a new route. The Publish control's visibility rule stays unchanged
(`app/src/routes/admin/arguments/[id]/+page.svelte:332` — draft or unpublished only, per D-02).

---

### `api/tests/test_arguments.py` (D-23 public-leak-ban contract test)

**Analog:** itself, the exact existing leak-ban assertion block [VERIFIED, quoted,
`api/tests/test_arguments.py:245-264`]:
```python
# Phase 47 (T-47-17): provenance is operator-facing lineage only — the
# public utterance contract must never leak strategy/source/method/
# external_id, and must never be inferred as a quality/trust signal.
assert "strategy" not in first, "strategy must not appear on the public utterance contract"
assert "source" not in first, "source must not appear on the public utterance contract"
assert "method" not in first, "method must not appear on the public utterance contract"
assert "external_id" not in first, "external_id must not appear on the public utterance contract"
```
D-23's addition follows this exact shape:
```python
assert "trust_tier" not in first, "trust_tier must never appear on any public response (apolitical constraint)"
```
Applied per-endpoint to `/cases`, argument detail, utterances, `/people/{id}` responses — extend
this test file's existing pattern to each; a new test file may be needed for endpoints this file
doesn't already cover.

---

## Shared Patterns

### In-transaction recompute discipline (D-07/Pattern 2)
**Source:** `api/services/admin_arguments.py::publish_argument` lines 598-615 (bulk update +
`.execution_options(synchronize_session=False)` + post-commit `db.refresh()`)
**Apply to:** Every writer in RESEARCH.md's "Complete Writer-Path Enumeration" (corpus import,
PDF ingest, parse, `approve_job`, resolve-row edits, `update_participant_side`, publish,
unpublish, and the new CLI command) — call `recompute_argument_tier(db, argument_id)` **before**
`await db.commit()`, never after (Pitfall 2).

### `.execution_options(synchronize_session=False)` + refresh
**Source:** every bulk `update()`/`delete()` in `admin_arguments.py` and `admin_jobs.py`
already carries this option [VERIFIED: confirmed present on all six `update()`/`delete()` calls
in `admin_arguments.py`].
**Apply to:** `recompute_argument_tier`'s own `UPDATE arguments SET trust_tier = ...`, and any
caller re-reading the same `Argument` object in the same session must `db.refresh()` it
afterward.

### `ArgumentStatusLog` write shape
**Source:** `api/services/admin_jobs.py:591` (`db.add(ArgumentStatusLog(argument_id=job.argument_id, status=ArgumentStatusEnum.DRAFT))`) and `api/services/admin_arguments.py:606`
(`db.add(ArgumentStatusLog(argument_id=argument_id, status=ArgumentStatusEnum.PUBLISHED))`).
**Apply to:** birth (`CANDIDATE`, D-03, two new call sites in `import_convokit.py`/`ingest.py`)
and the override acknowledgment (extend the existing PUBLISHED-status write in
`publish_argument` with `override_reason=` / `trust_tier_at_transition=` kwargs, D-15).

### Tagged `ValueError` → HTTP 422 mapping
**Source:** `api/routers/admin.py`'s router handlers uniformly do
`except ValueError as exc: raise HTTPException(status_code=422, detail=str(exc)) from exc`,
and `update_argument`'s service layer raises specific tagged strings (`"slug_collision"`,
`"docket_collision"`, invalid-date `ValueError`) that the frontend branches on by string match.
**Apply to:** the new `"uncertain_tier_blocked"` tag from `publish_argument`, and D-17's
non-empty-`override_reason` server-side validation error.

### PIPELINE→CANDIDATE mechanical guard swap
**Source:** the 8-site inventory in RESEARCH.md — all are one-line `== / !=
ArgumentStatusEnum.PIPELINE` comparisons.
**Apply to:** `api/models/models.py:311`, `admin_jobs.py:284,577,701,804`,
`admin_people.py:968`, `import_convokit.py:515`. Verify completeness with
`grep -rn "ArgumentStatusEnum.PIPELINE" api/ pipeline/` excluding `api/tests/`/`pipeline/tests/`.

## No Analog Found

None — every file in scope has at least a role-match analog (see table above); the lowest-quality
matches (`recompute_trust.py` CLI command, the two new pure unit/DB test files) still have a
directly-applicable structural precedent (subparser/dispatch pattern; sibling domain-module test
file pattern; existing DB-gated service test pattern) cited above.

## Metadata

**Analog search scope:** `api/domain/`, `api/services/`, `api/models/`, `api/routers/`,
`api/schemas/`, `api/tests/`, `pipeline/commands/`, `pipeline/__main__.py`,
`alembic/versions/` (0008, 0012, 0026), `app/src/routes/admin/arguments/[id]/`,
`scripts/delete_fixture_argument.py`
**Files scanned:** ~20 (all directly read this session; no blind grepping without a follow-up read)
**Pattern extraction date:** 2026-08-18
