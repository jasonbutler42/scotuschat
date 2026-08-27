# Phase 50: Unified Import Path - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 11 (5 modified, 2 new pipeline modules, 1 new Alembic revision, 3 test-file dispositions)
**Analogs found:** 11 / 11 (every file has at least a role-match analog; none unmapped — this is a rework, not new-system design)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pipeline/commands/import_convokit.py` (`_import_conversation` reconcile branch, replaces early return ~490) | service/writer (pipeline) | compare-and-decide (CRUD + event-driven) | same file's own first-import branch (lines 488-650, 850-930) + `pipeline/commands/resolve.py`'s HIT/MISS bulk-update shape | exact (same function, same file — a rework in place) |
| `pipeline/commands/import_convokit.py` (digest computation helper, D-13) | utility (pure transform) | transform | none in-repo (RESEARCH.md: "no prior art") — closest shape is `api/domain/trust.py`'s pure-string-in/enum-out contract | role-match only — net-new pattern, document explicitly |
| `pipeline/commands/prune_runs.py` (NEW, D-12) | pipeline CLI command | batch | `pipeline/commands/recompute_trust.py` (full file, drift-repair CLI shape) | exact |
| `api/services/admin_arguments.py` (NEW argument-scoped `approve_argument`, D-14) | service | request-response (state transition) | `api/services/admin_jobs.py::approve_job` (lines 653-717) | exact (same transition, job-scoped → argument-scoped) |
| `api/services/admin_arguments.py::delete_argument` (gate widen D-25 + cascade fix D-26) | service | CRUD (delete) | itself, `admin_arguments.py:983-1080` — same function, in-place fix; cascade-ordering precedent for the missing FK step is `argument_status_log`'s own Step 5 in the same function | exact |
| `api/services/admin_dev.py::reset_to_fixture` (REWORK, Pitfall 1) | service (dev/test fixture realization) | batch / state transition | itself, `admin_dev.py:167-335` — same function reworked; the two `approve_job` calls it replaces are the analog for the new argument-scoped approve calls | exact |
| `pipeline/commands/parse.py` (D-22 delegation site — `ArgumentParticipant`/`Argument` field writes) | pipeline writer | CRUD | `api/services/admin_jobs.py:600-618` (the one existing caller of `apply_participant_value_change`) | role-match — this is the pattern parse.py must adopt, not one it already follows |
| `pipeline/commands/resolve.py` (D-22 delegation site — bulk `person_id` UPDATE ~line 317, ungated today) | pipeline writer | CRUD (bulk update) | `api/services/admin_jobs.py:600-618` for the *gate call shape*; `resolve.py` itself (lines 249-261, 312-322) for the *bulk-UPDATE loop shape* that must be replaced per-row with the gate | role-match |
| `pipeline/commands/import_justices_csv.py` (D-22 delegation site, `source=seed`) | pipeline writer | batch (CRUD, blank-only prefill) | `api/services/admin_jobs.py:600-618` (gate call shape) | role-match |
| `alembic/versions/00XX_<name>.py` (NEW — `ArgumentParticipant.oyez_speaker_id` + `ImportRun` digest column, D-04/D-13) | migration | DDL | `alembic/versions/0028_review_state_and_discrepancy.py` (full file) | exact |
| `pipeline/tests/test_import_convokit_adminjob.py` (disposition: rewrite/retire) | test | — | itself — every documented assertion targets deleted behavior | exact (this IS the file, its disposition is the deliverable) |

## Pattern Assignments

### `pipeline/commands/import_convokit.py` — reconcile branch (service, compare-and-decide)

**Analog:** the file's own existing first-import branch, plus the authority-gate call shape from `api/services/admin_jobs.py`.

**Current early-return site to delete** (`pipeline/commands/import_convokit.py:488-495`, verified):
```python
    # ---- Idempotent Argument dedup on oyez_transcript_id (D-08) ----
    existing_argument_result = await session.execute(
        select(Argument).where(Argument.oyez_transcript_id == conversation_id)
    )
    if existing_argument_result.scalar_one_or_none() is not None:
        counters["skipped_existing"] += 1
        return
```
This `if` block is where D-01's reconcile branch replaces the return. Note `counters["skipped_existing"]` is read by `_SUMMARY_COUNTER_KEYS` (line 1177) and the summary print (line 1228) — decide explicitly whether it becomes dead or is repurposed for "reconciled, no diff."

**ImportRun stamp pattern to mirror for the lazy `step="reconcile"` run** (`import_convokit.py:583-596`, verified — this is the exact shape D-06's lazy run must copy, with `step="reconcile"` substituted and creation deferred until a write/record actually happens):
```python
    run = ImportRun(
        argument_id=argument.id,
        step="parse",
        status=ImportRunStatus.COMPLETED,
        source=ImportSource.CORPUS,
        method=ImportMethod.DIRECT,
        external_id=conversation_id,
    )
    session.add(run)
    await session.flush()
```

**Gate-call pattern to adopt** (`api/services/admin_jobs.py:600-618`, verified — the ONE existing caller of the gate; copy the call shape, but see the Pitfall 2 gap below for the restamp it does NOT include):
```python
await apply_participant_value_change(
    db,
    participant=matched_participant,
    field="person_id",
    incoming_value=match.person_id,
    incoming_source=incoming_authority_source,
    incoming_method=incoming_authority_method,
)
if matched_participant.source is None:
    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == matched_participant.id,
            ArgumentParticipant.argument_id == job.argument_id,
        )
        .values(source=parse_run_source, method=parse_run_method)
        .execution_options(synchronize_session=False)
    )
```
**Do not reuse this exact conditional for D-07.** The `if matched_participant.source is None` guard is backfill-only (only stamps a never-stamped row). D-07 requires an **unconditional** restamp to `corpus`/`direct` on every `ACCEPT`/`ACCEPT_AND_RECORD`. `apply_participant_value_change` itself never touches `source`/`method` — confirmed by its full body (`api/services/admin_review.py:159-221`, read in full, single `.values()` call sets only `{field: incoming_value}`). The reconcile writer must issue its own second, unconditional `UPDATE ... SET source=..., method=...` (or ORM attribute assignment) after every accepted write.

**Participant pairing precedent that must change (D-04)** (`import_convokit.py:912-919`, verified — the CURRENT dedup key, which the reconcile pass must NOT reuse for pairing, only `oyez_speaker_id` may be used per D-04):
```python
    existing = await session.execute(
        select(ArgumentParticipant).where(
            ArgumentParticipant.argument_id == argument_id,
            ArgumentParticipant.raw_speaker_label == raw_speaker_label,
        )
    )
    participant = existing.scalar_one_or_none()
```

**AdminJob fabrication site to delete** (`import_convokit.py:895-903` region — verified in the read):
```python
    resolved = [p for p in resolved_participants.values() if p is not None]
    session.add(
        AdminJob(
            status=AdminJobStatus.PAUSED,
            current_step=AdminJobStep.RESOLVE,
            argument_id=argument.id,
            discrepancies=_build_discrepancies(resolved),
        )
    )
```
This whole block is the D-14/D-19 deletion site. `_build_discrepancies` (D-18) — check for other callers before deleting (RESEARCH.md flags this explicitly).

---

### `pipeline/commands/prune_runs.py` (NEW, D-12)

**Analog:** `pipeline/commands/recompute_trust.py` (full file read — 30-line docstring + CLI body).

**Pattern to copy verbatim in shape** (docstring framing, offline-only declaration, `--all`/`--argument-id` mutually-exclusive CLI group):
```python
"""
Pipeline recompute-trust command (Phase 48, D-09).
...
Offline CLI only, per CLAUDE.md's pipeline-is-offline-only rule — this
module has no FastAPI import and is reachable only via
`python -m pipeline recompute-trust`.
...
Usage:
    python -m pipeline recompute-trust --all
    python -m pipeline recompute-trust --argument-id 123
    python -m pipeline recompute-trust --all --dry-run
"""
```
And the CLI registration shape to mirror in `pipeline/__main__.py` (lines 289-360, verified):
```python
recompute_trust_p = sub.add_parser(
    "recompute-trust",
    help="Re-derive every argument's trust tier through the shared service",
    ...
)
recompute_trust_group = recompute_trust_p.add_mutually_exclusive_group(required=True)
recompute_trust_group.add_argument("--all", action="store_true", ...)
recompute_trust_group.add_argument("--argument-id", type=int, default=None, ...)
```
`prune-runs` is a new `sub.add_parser(...)` following this exact `--all`/`--argument-id` mutually-exclusive-group shape. D-28's `--dry-run` on `import-convokit` is a plain `add_argument("--dry-run", action="store_true", ...)` on the existing `import_convokit_p` parser (same file).

---

### `api/services/admin_arguments.py` — NEW argument-scoped approve (D-14)

**Analog:** `api/services/admin_jobs.py::approve_job` (lines 653-717, full function read).

**Pattern to copy** — same status transition, same completeness gate, same `resolved_at` stamp, minus the `AdminJob`-status write:
```python
async def approve_job(db: AsyncSession, job_id: int) -> AdminJob:
    """..."""
    job = await get_job(db, job_id)
    if job is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if job.argument_id is None:
        raise ValueError(f"AdminJob {job_id} has no linked argument")

    arg_result = await db.execute(select(Argument).where(Argument.id == job.argument_id))
    argument = arg_result.scalar_one_or_none()
    if argument is None:
        raise ValueError("Argument not found for this job")
    if argument.status != ArgumentStatusEnum.CANDIDATE:
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
    await recompute_argument_tier(db, job.argument_id)
    await db.commit()
```
The new function is the same body keyed directly on `argument_id` (not `job_id`/`get_job`) — drop the `AdminJob`-status `update()` block entirely (there is no AdminJob to flip for a corpus argument), keep every other statement, including the `db.refresh()` stale-identity-map fix noted right after (Phase 31 precedent, same file, immediately following lines) if this session object is reused elsewhere.

**Load-bearing constraint (D-14):** `publish_argument` (`admin_arguments.py:626`, cited in RESEARCH.md) refuses on `resolved_at IS NULL` non-overridable — this new function is the *only* other writer of `resolved_at` once `approve_job` stops being corpus's path, so it must set it, not merely gate on it.

---

### `api/services/admin_arguments.py::delete_argument` — D-25 gate widen + D-26 cascade fix

**Analog:** itself (`api/services/admin_arguments.py:983-1080`, full function read).

**Current gate to invert** (verified, line ~1018-1020):
```python
    if argument.status != ArgumentStatusEnum.DRAFT:
        return False
```
D-25 requires: `if argument.status == ArgumentStatusEnum.PUBLISHED: return False` — deletable in every OTHER state.

**Current FK-ordered cascade (verified, full step list) — D-26 inserts a new step:**
```python
    # Step 1: Delete utterances referencing this argument (must be before import_run rows)
    await db.execute(delete(Utterance).where(Utterance.argument_id == argument_id)...)
    # Step 2: Delete import_run rows for this argument (after utterances)
    await db.execute(delete(ImportRun).where(ImportRun.argument_id == argument_id)...)
    # Step 3: Delete argument_participants
    await db.execute(delete(ArgumentParticipant).where(ArgumentParticipant.argument_id == argument_id)...)
    # Step 4: Delete case_arguments join rows
    ...
    # Step 5: Delete argument_status_log rows — FK is NOT NULL with no ondelete clause
    await db.execute(delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)...)
    # Step 6: NULL out AdminJob.argument_id
    ...
    # Step 7: Delete the argument itself
```
**D-26 fix, modeled directly on Step 5's own precedent** (a hard NOT-NULL FK that was missed once before and had to be added as its own numbered step): insert a new step **before Step 2** (before `import_run` rows are deleted, since `value_discrepancy.import_run_id` is a hard FK to `import_run.id` per migration 0028's `sa.ForeignKeyConstraint(["import_run_id"], ["import_run.id"])`) that deletes `value_discrepancy` rows scoped by `target_type="argument_participant"` + the set of this argument's `ArgumentParticipant.id`s (soft ref, D-26's second leg — no FK exists to catch this one, so it must be explicit or it silently orphans). Follow the exact same `.execution_options(synchronize_session=False)` discipline (Pitfall 3, project-wide, cited in this function's own docstring).

---

### `api/services/admin_dev.py::reset_to_fixture` — REWORK (Pitfall 1)

**Analog:** itself (`api/services/admin_dev.py:167-335`, full function read).

**Existence-check site to delete** (verified, the `ResetIncompleteError` raised when no paired `AdminJob` is found):
```python
        admin_job = (
            await db.execute(select(AdminJob).where(AdminJob.argument_id == argument.id))
        ).scalar_one_or_none()
        if admin_job is None:
            raise ResetIncompleteError(
                f"Conversation {conversation_id!r} landed an Argument row but "
                "no paired AdminJob — reset is incomplete."
            )
        fixture_rows.append((entry, argument.id, admin_job.id))
```
Must drop the `admin_job is None` check entirely for corpus fixtures; `fixture_rows` no longer needs an `admin_job_id` leg.

**State-realization calls to replace** (verified, "Draft" and "Published" fixtures):
```python
    _draft_argument_id, draft_job_id = ids_by_conversation["13015"]
    await jobs_service.approve_job(db, draft_job_id)
    ...
    published_argument_id, published_job_id = ids_by_conversation["18897"]
    await jobs_service.approve_job(db, published_job_id)
    await arguments_service.publish_argument(db, published_argument_id)
```
Replace each `jobs_service.approve_job(db, <job_id>)` call with the new D-14 argument-scoped approve, called with the `argument_id` directly (`_draft_argument_id` / `published_argument_id`) — the two-call ordering constraint for the Published fixture (approve before publish, because `publish_argument` raises on `resolved_at IS NULL`) is unchanged and must be preserved verbatim.

**"Mid-pipeline" fixture role with no clean equivalent** (verified, conversation 22372 — Open Question 2 in RESEARCH.md, unresolved by CONTEXT.md, decide at plan time):
```python
    _mid_argument_id, mid_job_id = ids_by_conversation["22372"]
    await db.execute(
        update(AdminJob).where(AdminJob.id == mid_job_id)
        .values(status=AdminJobStatus.RUNNING)
        .execution_options(synchronize_session=False)
    )
```
No `AdminJob` row exists post-rework to flip. RESEARCH.md's own recommendation: either retire this fixture role, or redefine it as a `step="reconcile"` `ImportRun` mid-state — this must be an explicit plan decision, not inferred.

**Response schema field to update** (verified, line ~326-333): `"admin_job_status": admin_job.status.value if admin_job else ""` — drop this key or repurpose it (e.g. reporting `review_state`/reconcile-run presence) since `admin_job` will always be `None` for corpus fixtures going forward.

---

### `pipeline/commands/parse.py` / `resolve.py` / `import_justices_csv.py` — D-22 delegation sweep

**Analog:** `api/services/admin_jobs.py:600-618` (the one existing caller — same gate-call shape every one of these three files must adopt).

**`parse.py`'s current ungated `ImportRun` write is fine as-is** (it doesn't touch a gated column — `ImportRun` itself has no authority column); the D-22 gap in this file is any `ArgumentParticipant`/`Argument` field write it performs directly. Verified shape at `parse.py:260-340` — cover-metadata block ("Block A: argued_date → Argument row — only if currently NULL") and the participant-seeding block (`session.add(ArgumentParticipant(...))`, no `source`/`method` set) are the two writers that must be checked against D-22's inventory and, where they write a gated column value (not just seed a NULL placeholder), routed through `apply_participant_value_change`/`apply_person_value_change`.

**`resolve.py`'s ungated bulk UPDATE — the two writers RESEARCH.md names explicitly** (verified, lines 249-261 and 312-322):
```python
                    # ---- Bulk UPDATE utterances (Pitfall 2: use raw_label) ----
                    await session.execute(
                        update(Utterance)
                        ...
                        .values(person_id=person_id)
                        ...
                    )
                    resolved_map[raw_label] = person_id
...
            # Step 5: Update argument_participants.person_id (Pitfall 7)
            for raw_label, person_id in resolved_map.items():
                await session.execute(
                    update(ArgumentParticipant)
                    ...
                    .values(person_id=person_id)
                    ...
                )
```
The `ArgumentParticipant.person_id` bulk UPDATE (Step 5) is the ungated gated-column write D-22 must close — this loop must become a per-row `apply_participant_value_change(...)` call (fetch each `ArgumentParticipant` row first; the gate function operates on one ORM object at a time, not a bulk `update()`, per its own signature at `admin_review.py:159-178`). The `Utterance.person_id` bulk UPDATE is NOT gated (Utterance has no authority column) and stays as-is.

**`import_justices_csv.py`'s blank-only Person prefill (`source=seed`)**: verified at lines 1-40/240-345 as a "hand-rolled blank-only Person prefill" per RESEARCH.md's Sources list — any write to a `Person` name-part field must route through `apply_person_value_change` with `incoming_source="seed"` (ranked with `corpus` per `authority_rank`'s rule 3).

---

### `alembic/versions/00XX_<name>.py` — NEW migration (D-04 + D-13)

**Analog:** `alembic/versions/0028_review_state_and_discrepancy.py` (full file, 165 lines, read in full — head is currently `0029`, so this is `0030`).

**Column-add pattern to copy exactly** (no backfill needed — nullable column, D-16):
```python
def upgrade() -> None:
    op.add_column(
        "argument_participants",
        sa.Column("oyez_speaker_id", sa.String(50), nullable=True),  # D-04, no backfill (D-16)
    )
    op.add_column(
        "import_run",
        sa.Column("content_digest", sa.String(64), nullable=True),  # D-13, sha256 hex
    )


def downgrade() -> None:
    op.drop_column("import_run", "content_digest")
    op.drop_column("argument_participants", "oyez_speaker_id")
```
Follow 0028's exact discipline: no `server_default`-driven backfill logic needed here (both nullable, D-15/D-16 forbid backfill regardless); reuse existing PG enum types verbatim if either column becomes an enum (neither does here — both are plain scalar columns, simpler than 0028's `review_state` enum + `value_discrepancy` table). `revision = "0030"`, `down_revision = "0029"`.

---

### `pipeline/tests/test_import_convokit_adminjob.py` — disposition

**Analog:** itself. Full docstring read (22 lines) — every documented assertion (exactly-one-AdminJob creation, discrepancies JSONB shape, no-second-AdminJob-on-rerun) targets deleted behavior. This file's disposition (rewrite vs. retire) must be an explicit plan task per RESEARCH.md's Wave 0 Gaps — do not leave it silently red or silently deleted without a plan note. If retired, its replacement is the new negative-space test (Pitfall 3) asserting zero `AdminJob` rows after a fresh corpus import.

---

## Shared Patterns

### The ONE gated writer (D-21) — every delegation site uses this same two-function contract
**Source:** `api/services/admin_review.py::apply_participant_value_change` (lines 159-227) / `apply_person_value_change` (lines 229-289).
**Apply to:** `import_convokit.py` reconcile branch, `resolve.py`'s Step 5, `parse.py`'s gated writes, `import_justices_csv.py`'s Person writes.
```python
async def apply_participant_value_change(
    db: AsyncSession,
    *,
    participant: ArgumentParticipant,
    field: str,
    incoming_value,
    incoming_source: str,
    incoming_method: str,
    import_run_id: int | None = None,
) -> WriteDecision:
    ...
    decision = decide_write(
        incoming_source=incoming_source,
        incoming_method=incoming_method,
        incoming_review_state="",
        existing_source=existing_source_value,
        existing_method=existing_method_value,
        existing_review_state=existing_review_state_value,
        values_differ=values_differ,
    )
    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        await db.execute(update(ArgumentParticipant).where(...).values(**{field: incoming_value})...)
    if decision in (WriteDecision.ACCEPT_AND_RECORD, WriteDecision.REJECT_AND_RECORD):
        await record_value_discrepancy(db, target_type="argument_participant", target_id=participant.id, field=field, ...)
    return decision
```
Never commits, never recomputes trust tier — caller owns both. Import path: `from api.services.admin_review import apply_participant_value_change, apply_person_value_change` — this module imports only SQLAlchemy + `api.domain` + `api.models`, confirmed importable from pipeline (D-21).

### Authority ladder (pure decision function)
**Source:** `api/domain/authority.py::decide_write` (full file, 183 lines).
**Apply to:** every gated writer above, and any new `apply_argument_value_change`/`apply_case_value_change` if Open Question 1 is resolved by adding a peer gate function this phase.
```python
def decide_write(
    *, incoming_source: str, incoming_method: str, incoming_review_state: str,
    existing_source: str, existing_method: str, existing_review_state: str,
    values_differ: bool,
) -> WriteDecision:
    if not values_differ:
        return WriteDecision.ACCEPT
    incoming_rank = authority_rank(incoming_source, incoming_method, incoming_review_state)
    existing_rank = authority_rank(existing_source, existing_method, existing_review_state)
    if incoming_rank > existing_rank:
        return WriteDecision.ACCEPT_AND_RECORD
    if incoming_rank == existing_rank == AuthorityRank.OPERATOR:
        return WriteDecision.ACCEPT_AND_RECORD
    return WriteDecision.REJECT_AND_RECORD
```
All arguments are plain strings, never enum members — callers pass `.value`. Fail-closed `UNKNOWN` rank for any unrecognised `(source, method)` pair.

### Discrepancy recording
**Source:** `api/services/admin_review.py::record_value_discrepancy` (lines 99-137).
**Apply to:** every `ACCEPT_AND_RECORD`/`REJECT_AND_RECORD` outcome across the reconcile pass, `resolve.py`, `parse.py`.
```python
discrepancy = ValueDiscrepancy(
    target_type=target_type, target_id=target_id, field=field,
    import_run_id=import_run_id,
    incoming_value=_stringify(incoming_value), existing_value=_stringify(existing_value),
    incoming_source=ImportSource(incoming_source) if incoming_source else None,
    incoming_method=ImportMethod(incoming_method) if incoming_method else None,
    existing_source=ImportSource(existing_source) if existing_source else None,
    existing_method=ImportMethod(existing_method) if existing_method else None,
)
db.add(discrepancy)
```
Never commits — caller owns the transaction (D-30's per-argument boundary). `import_run_id` is nullable at the model level, but D-06 requires the reconcile pass to have minted its lazy run BEFORE calling this, since D-06's own rationale is "value_discrepancy's natural key requires an import_run_id to attribute a record to."

### Value-difference normalization
**Source:** `api/services/admin_review.py::_values_differ` (lines 78-97) + `api.domain.person_names.normalize_name_part`.
**Apply to:** every D-02 compare-set field comparison in the reconcile pass.
```python
def _values_differ(field: str, incoming, existing) -> bool:
    if field in _NAME_PART_FIELDS:
        norm_incoming = normalize_name_part(incoming, field_name=field) if incoming else None
        norm_existing = normalize_name_part(existing, field_name=field) if existing else None
    else:
        norm_incoming = _normalize_generic(incoming)
        norm_existing = _normalize_generic(existing)
    return norm_incoming != norm_existing
```
Note `_normalize_generic` collapses `None`/`""` to `None` on both sides — this is exactly D-03's "empty incoming vs. populated stored ⇒ no opinion" mirror case ALREADY handled by `decide_write`'s `values_differ=False → ACCEPT` path when BOTH sides are blank, but D-03 covers the *asymmetric* case (blank incoming, populated existing) which this normalization does NOT resolve by itself — RESEARCH.md's Hard Constraint 4 flags this precisely: "`decide_write` normalizes before comparing and already treats a blank stored value as ACCEPT; D-03 covers only the mirror case (blank incoming), which the ladder does not decide." The reconcile pass must add an explicit pre-check: if incoming is blank/None and existing is non-blank, skip the field entirely (no `decide_write` call, no record) — do not rely on `_values_differ` collapsing both to `None` to produce this behavior, because it only collapses correctly when BOTH sides are blank.

### Trust-tier recompute after any write
**Source:** `api/services/trust.py::recompute_argument_tier`.
**Apply to:** end of the reconcile pass (after any accepted write), `approve_argument` (new D-14 function), `delete_argument` is exempt (nothing left to recompute).
Already imported and called last (after every constituent write) by `approve_job` (`admin_jobs.py:697`) and `resolve.py` (Step 3 area) — same "call it last, never commits" contract every existing writer already follows.

### Blank-page hazard — the one constraint that gates D-06/D-10/D-30 together
**Source:** `api/services/arguments.py:100-108` (verified, full function read).
```python
    max_run_result = await db.execute(
        select(func.max(ImportRun.id)).where(
            ImportRun.argument_id == argument_id,
            ImportRun.step == "parse",
            ImportRun.status == ImportRunStatus.COMPLETED,
        )
    )
```
Any reconcile-branch task that mints a `step="parse"`/`COMPLETED` `ImportRun` (D-10, on any utterance diff) MUST write that run's full utterance set inside the same transaction — this select is exactly what would otherwise surface a crashed/partial rewrite as an empty public page.

### Provenance-restamp precedent that cannot be reused verbatim (flagged per task emphasis)
**Source:** `api/services/admin_jobs.py:1017-1018` (backfill-only conditional, embedded in `resolve_participant_review`, full surrounding context read at lines 990-1035).
```python
    if participant.source is None:
        parse_run_id = await get_run_id_for_step(db, job_id, "parse")
        if parse_run_id is not None:
            parse_run_row = ...
            if parse_run_row is not None:
                participant.source = parse_run_row.source
                participant.method = parse_run_row.method
```
**Why this cannot be reused for D-07:** this restamp only fires `if participant.source is None` — i.e. it backfills a row that has never been stamped at all. D-07 requires restamping `source`/`method` to `corpus`/`direct` on *every* accepted reconcile overwrite, unconditionally, including rows that already carry a prior `source`/`method` value (e.g. a row stamped `corpus`/`direct` in a previous import that now needs its provenance touched again because THIS pass's value won and needs the restamp to reflect that THIS write is what produced the current value). The reconcile writer needs its own unconditional restamp statement, not a copy of this conditional.

## No Analog Found

| File/Concern | Role | Data Flow | Reason |
|---|---|---|---|
| D-13 content digest algorithm/helper | pure utility | transform | RESEARCH.md states explicitly: "No prior art exists in this codebase for this exact pattern — no other table has a content digest column." Nearest structural precedent for "pure function, plain-string contract" is `api/domain/authority.py`/`api/domain/trust.py`'s no-ORM-import discipline, but the hashing logic itself is net-new; field list and canonicalization must be frozen in the plan (one-way door per D-13). |
| `Argument`/`Case` compare-set authority tracking (Open Question 1) | schema/service | CRUD | No existing gate function (`apply_argument_value_change`) exists because `Argument`/`Case` have no `source`/`method`/`review_state` columns at all (verified: `api/models/models.py:314-368`, `285-303`, full model bodies). This is not merely "no analog" — RESEARCH.md flags it as the single most consequential unresolved item; the planner must decide whether to add columns (mirroring migration 0028's shape) or adopt a no-stored-bit rule before this file's compare-set fields can be planned at all. |

## Metadata

**Analog search scope:** `api/domain/`, `api/services/` (admin_review.py, admin_jobs.py, admin_arguments.py, admin_dev.py, arguments.py, trust.py), `pipeline/commands/` (import_convokit.py, parse.py, resolve.py, import_justices_csv.py, recompute_trust.py), `pipeline/__main__.py`, `api/models/models.py`, `alembic/versions/0028_review_state_and_discrepancy.py`, `pipeline/tests/test_import_convokit_adminjob.py`.
**Files scanned:** 15 read directly this session (full-file or targeted line-range reads, per the required-reading emphasis list); no stale `.planning/codebase/*.md` maps consulted (per 50-CONTEXT.md's explicit warning — they predate Phases 47-49).
**Pattern extraction date:** 2026-08-25
