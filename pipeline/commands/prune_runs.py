"""
Pipeline prune-runs command (Phase 50, D-12).

D-01's always-reconcile behavior and D-10's whole-set utterance replacement
both mean a repeat import RETAINS superseded rows rather than deleting them
(Architecture Rule 3, CLAUDE.md) — an import must never delete, or a crash
mid-write could blank a live public page (the "blank-page hazard" recorded
in 50-CONTEXT.md's Hard Constraints). `prune-runs` is the counterpart D-12
promised in exchange for that promise: a deliberate, OFFLINE, operator-
invoked command that reclaims the space an import intentionally never
touches.

Offline CLI only, per CLAUDE.md's pipeline-is-offline-only rule — this
module has no FastAPI import and is reachable only via
`python -m pipeline prune-runs`.

Safety rules (50-07-PLAN.md decision record):

    PD-22 — a run is a prune candidate only when it is NOT the run
    `api/services/arguments.py`'s `MAX(ImportRun.id) WHERE step='parse'
    AND status='completed'` select would return for its argument. That
    select is the exact definition of "the run the public currently
    sees" — this module re-derives it with the identical shape (never an
    equivalent-looking variant) so the two can never drift apart.
    `step="reconcile"` runs carry no such served/not-served distinction
    of their own (the read path never selects on step="reconcile") and
    are separately prunable once they carry no open discrepancy rows.
    Every other step (`"ingest"`, `"resolve"`) is left untouched — this
    command's scope is exactly the two steps D-10/D-12 name.

    PD-23 — `value_discrepancy.import_run_id` is a hard FK to
    `import_run.id`. A run carrying one or more OPEN (`resolved_at IS
    NULL`) discrepancy rows is refused under every flag combination —
    counted and printed by name, never silently skipped and never
    cascaded; an open row is an operator's outstanding work item. A run
    carrying only RESOLVED discrepancy rows is also refused by default;
    `--include-resolved-discrepancies` opts into deleting those resolved
    rows (and only those — an open row is never deleted by this command
    under any flag) before the run itself is removed.

Usage:
    python -m pipeline prune-runs --all
    python -m pipeline prune-runs --argument-id 123
    python -m pipeline prune-runs --all --dry-run
    python -m pipeline prune-runs --all --include-resolved-discrepancies
    python -m pipeline prune-runs --argument-id 123 --dry-run --include-resolved-discrepancies
"""

from __future__ import annotations

from sqlalchemy import delete, func, select

from api.models.models import Argument, ImportRun, ImportRunStatus, Utterance, ValueDiscrepancy
from pipeline.db import get_session

# The two step values D-10/D-12 scope this command to. "ingest" and
# "resolve" runs are never prune candidates — out of scope for this
# command, left entirely alone.
_PRUNABLE_STEPS = ("parse", "reconcile")


async def _prunable_run_ids(
    session,
    argument_id: int,
    *,
    include_resolved_discrepancies: bool = False,
) -> dict:
    """
    Compute the prune-eligible run set for one argument (PD-22/PD-23).

    Returns a dict:
        served_run_id: int | None
            The run `api/services/arguments.py`'s read path currently
            serves for this argument (never a prune candidate).
        prunable: list[int]
            Run ids eligible for removal under the current flags.
        skipped_open_discrepancy: list[tuple[int, int]]
            (run_id, open_row_count) pairs refused for carrying an OPEN
            discrepancy row — refused under every flag combination.
        skipped_resolved_discrepancy: list[int]
            Run ids refused because they carry only RESOLVED discrepancy
            rows and --include-resolved-discrepancies was not set.
        resolved_discrepancy_ids_to_delete: list[int]
            value_discrepancy.id values that must be deleted (in the
            caller's own transaction) before the paired prunable run can
            be removed — populated only when
            include_resolved_discrepancies is True.

    Read-only — issues no write of its own. The caller decides whether to
    act on `prunable` (a real run) or merely report it (--dry-run).
    """
    # PD-22: re-derive api/services/arguments.py's exact served-run select
    # shape — never an equivalent-looking variant — so the two can never
    # disagree about which run the public currently sees.
    served_run_id = (
        await session.execute(
            select(func.max(ImportRun.id)).where(
                ImportRun.argument_id == argument_id,
                ImportRun.step == "parse",
                ImportRun.status == ImportRunStatus.COMPLETED,
            )
        )
    ).scalar_one_or_none()

    all_runs = (
        await session.execute(
            select(ImportRun.id, ImportRun.step).where(
                ImportRun.argument_id == argument_id
            )
        )
    ).all()

    candidate_ids = [
        run_id
        for run_id, step in all_runs
        if run_id != served_run_id and step in _PRUNABLE_STEPS
    ]

    prunable: list[int] = []
    skipped_open: list[tuple[int, int]] = []
    skipped_resolved: list[int] = []
    resolved_ids_to_delete: list[int] = []

    for run_id in candidate_ids:
        open_count = (
            await session.execute(
                select(func.count(ValueDiscrepancy.id)).where(
                    ValueDiscrepancy.import_run_id == run_id,
                    ValueDiscrepancy.resolved_at.is_(None),
                )
            )
        ).scalar_one()
        if open_count > 0:
            # PD-23: an open row blocks its run's removal under every flag
            # combination — never silently skipped, never cascaded.
            skipped_open.append((run_id, open_count))
            continue

        resolved_ids = (
            await session.execute(
                select(ValueDiscrepancy.id).where(
                    ValueDiscrepancy.import_run_id == run_id,
                    ValueDiscrepancy.resolved_at.isnot(None),
                )
            )
        ).scalars().all()

        if resolved_ids and not include_resolved_discrepancies:
            skipped_resolved.append(run_id)
            continue

        prunable.append(run_id)
        resolved_ids_to_delete.extend(resolved_ids)

    return {
        "served_run_id": served_run_id,
        "prunable": prunable,
        "skipped_open_discrepancy": skipped_open,
        "skipped_resolved_discrepancy": skipped_resolved,
        "resolved_discrepancy_ids_to_delete": resolved_ids_to_delete,
    }


async def run_prune_runs(args) -> None:
    """
    Reclaim superseded ImportRun/Utterance rows for one argument
    (--argument-id) or every argument (--all), deliberately and offline.

    One session per argument (mirrors recompute-trust's own per-argument
    session boundary, Phase 48) — a mid-batch failure leaves earlier
    prunes durable rather than rolling the whole batch back.

    Delete ordering per argument (never reversed — Utterance.import_run_id
    is a real FK, matching delete_argument's own documented discipline in
    api/services/admin_arguments.py):
        1. RESOLVED value_discrepancy rows for the prunable run ids, only
           when --include-resolved-discrepancies allows it.
        2. Utterance rows whose import_run_id is in the prunable set.
        3. The ImportRun rows themselves.
    Every statement uses .execution_options(synchronize_session=False).

    --dry-run computes the exact same sets and prints the exact same
    report, issuing no delete statement at all — not "delete then roll
    back" (this module never depends on a rollback to undo a write it
    should never have attempted).

    Exits normally (process exit code 0) in every non-error case — a
    printed skip/removal count is information for the operator, not a
    command failure. An --argument-id that does not exist raises
    ValueError naming the missing id, which __main__ propagates as a
    non-zero process exit.
    """
    dry_run = bool(getattr(args, "dry_run", False))
    include_resolved = bool(getattr(args, "include_resolved_discrepancies", False))
    single_id = getattr(args, "argument_id", None)

    if single_id is not None:
        async with get_session() as session:
            exists = (
                await session.execute(
                    select(Argument.id).where(Argument.id == single_id)
                )
            ).scalar_one_or_none()
        if exists is None:
            raise ValueError(f"No argument with id {single_id} exists")
        argument_ids = [single_id]
    else:
        async with get_session() as session:
            argument_ids = (
                (await session.execute(select(Argument.id).order_by(Argument.id)))
                .scalars()
                .all()
            )

    arguments_scanned = 0
    runs_removed = 0
    utterances_removed = 0
    resolved_discrepancies_removed = 0
    runs_skipped_open_discrepancy = 0
    runs_skipped_served = 0

    for argument_id in argument_ids:
        arguments_scanned += 1
        async with get_session() as session:
            info = await _prunable_run_ids(
                session,
                argument_id,
                include_resolved_discrepancies=include_resolved,
            )

            if info["served_run_id"] is not None:
                runs_skipped_served += 1

            for run_id, open_count in info["skipped_open_discrepancy"]:
                runs_skipped_open_discrepancy += 1
                print(
                    f"  argument {argument_id}: run {run_id} refused — "
                    f"{open_count} open discrepancy row(s) attached"
                )

            prunable = info["prunable"]
            resolved_ids = info["resolved_discrepancy_ids_to_delete"]

            utterance_count = (
                await session.execute(
                    select(func.count(Utterance.id)).where(
                        Utterance.import_run_id.in_(prunable)
                    )
                )
            ).scalar_one() if prunable else 0

            if prunable and not dry_run:
                if resolved_ids:
                    await session.execute(
                        delete(ValueDiscrepancy)
                        .where(ValueDiscrepancy.id.in_(resolved_ids))
                        .execution_options(synchronize_session=False)
                    )
                # Utterances before runs — Utterance.import_run_id is a
                # real FK; the reverse order raises ForeignKeyViolation.
                await session.execute(
                    delete(Utterance)
                    .where(Utterance.import_run_id.in_(prunable))
                    .execution_options(synchronize_session=False)
                )
                await session.execute(
                    delete(ImportRun)
                    .where(ImportRun.id.in_(prunable))
                    .execution_options(synchronize_session=False)
                )

            resolved_discrepancies_removed += len(resolved_ids) if prunable else 0
            utterances_removed += utterance_count
            runs_removed += len(prunable)

            # No explicit rollback under --dry-run: unlike recompute-trust
            # (which always issues a write to compute the new tier, then
            # rolls it back), this module never issues a write at all when
            # dry_run is True (the `and not dry_run` gate above) -- there
            # is nothing pending to discard. get_session()'s own commit()
            # on a session with zero pending writes is a harmless no-op.

    mode_prefix = "[dry-run] " if dry_run else ""
    print(
        f"{mode_prefix}prune-runs: {arguments_scanned} arguments scanned, "
        f"{runs_removed} runs removed, {utterances_removed} utterance rows "
        f"removed, {resolved_discrepancies_removed} resolved discrepancy "
        f"rows removed, {runs_skipped_open_discrepancy} runs skipped for "
        f"open discrepancies, {runs_skipped_served} runs skipped as "
        "currently served."
    )
