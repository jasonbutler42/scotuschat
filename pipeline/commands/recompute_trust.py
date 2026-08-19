"""
Pipeline recompute-trust command (Phase 48, D-09).

This is D-09's drift-repair tool and D-21's falsifiable verification
vehicle: after a fresh `reset_to_fixture`, `python -m pipeline recompute-trust
--all` must report 0 rows changed — a positive, falsifiable proof that every
one of the phase's writer paths (corpus import, PDF ingest, parse, resolve,
approve_job, participant edits, publish, unpublish) stamped
Argument.trust_tier correctly at write time, not a "no drift was observed"
hand-wave. Plan 48-09 runs this command for exactly that purpose.

Offline CLI only, per CLAUDE.md's pipeline-is-offline-only rule — this
module has no FastAPI import and is reachable only via
`python -m pipeline recompute-trust`.

It derives NOTHING of its own: every recompute goes through
api.services.trust.recompute_argument_tier, the single shared service every
writer in this codebase already calls (TRUST-01) — so this CLI can never
disagree with the API about what a tier should be.

Usage:
    python -m pipeline recompute-trust --all
    python -m pipeline recompute-trust --argument-id 123
    python -m pipeline recompute-trust --all --dry-run
"""

from __future__ import annotations

from sqlalchemy import select

from api.models.models import Argument
from api.services.trust import recompute_argument_tier
from pipeline.db import get_session


async def run_recompute_trust(args) -> None:
    """
    Recompute Argument.trust_tier for one argument (--argument-id) or every
    argument (--all), reporting scanned / unchanged / changed counts.

    One session per argument (not one session for the whole scan) — a
    mid-scan failure leaves earlier repairs durable rather than rolling the
    whole scan back, and each write stays a bounded transaction.

    --dry-run computes the new tier through the exact same
    recompute_argument_tier() call, then rolls the session back instead of
    letting get_session()'s context manager commit — so the report is
    accurate but nothing is written.

    Exits normally (process exit code 0) in every non-error case — a
    non-zero changed count is information for the operator (and plan
    48-09's verification step), not a command failure. An --argument-id
    that does not exist raises ValueError naming the missing id, which
    __main__ propagates as a non-zero process exit.
    """
    dry_run = bool(getattr(args, "dry_run", False))
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

    scanned = 0
    unchanged = 0
    changed = 0
    changes: list[tuple[int, str, str]] = []

    for argument_id in argument_ids:
        scanned += 1
        async with get_session() as session:
            old_tier = (
                await session.execute(
                    select(Argument.trust_tier).where(Argument.id == argument_id)
                )
            ).scalar_one()
            new_tier = await recompute_argument_tier(session, argument_id)
            if dry_run:
                # Discard the UPDATE recompute_argument_tier just issued —
                # the report below is accurate, but nothing is persisted.
                await session.rollback()

            if new_tier == old_tier:
                unchanged += 1
            else:
                changed += 1
                changes.append((argument_id, old_tier.value, new_tier.value))

    for argument_id, old_value, new_value in changes:
        print(f"  argument {argument_id}: {old_value} -> {new_value}")

    mode_prefix = "[dry-run] " if dry_run else ""
    print(
        f"{mode_prefix}recompute-trust: {scanned} scanned, "
        f"{unchanged} unchanged, {changed} changed."
    )
