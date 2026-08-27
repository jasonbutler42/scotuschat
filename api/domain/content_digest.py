"""
Pure, dependency-light domain contract for the D-13 utterance content
digest (Phase 50, plan 50-01, Task 0's checkpoint — `freeze-as-proposed`).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection —
mirroring api/domain/authority.py's and api/domain/trust.py's structural
conventions exactly.

This is the ONE definition of "the same utterance content" for D-13's
change detection: a re-import compares this digest against the stored
`import_run.content_digest` of an argument's latest `step="parse"` run
 and only walks the full compare-and-write path when they differ.

THE CONTRACT IS FROZEN. It was frozen at Task 0's `checkpoint:decision`
gate (`freeze-as-proposed`) precisely because every digest already stored
in the database was computed by this exact function — changing the field
list or the serialization reads as a universal diff across the whole
corpus and forces a full-corpus false-positive reconcile pass. Any future
change to the field list or serialization requires bumping
`DIGEST_VERSION` and a deliberate full-corpus repass; it must never be
changed silently in place.

Frozen shape:
  - Algorithm: hashlib.sha256, lowercase hex digest, 64 characters.
  - Input: the ordered incoming utterance rows for ONE argument, in the
    exact order `_import_utterances` would write them, ascending
    `sequence` starting at 1.
  - Per-row fields, in exactly this order: `sequence` (int),
    `raw_speaker_label` (str or None), `text` (str), `is_stage_direction`
    (bool).
  - Serialization: `json.dumps` of a list of 4-element lists,
    `ensure_ascii=False`, `separators=(",", ":")`, no key sorting, UTF-8
    encoded. JSON framing (not a delimiter join) so a separator character
    inside `text` can never forge a row boundary.
  - Normalization: NONE. Byte-exact — a whitespace-only change in `text`
    IS a content change and does trigger a rewrite.
  - Empty input: an empty row list hashes to a real, stable, non-empty
    64-character digest — never NULL and never the empty string, so "this
    argument has zero utterances" is a distinguishable state, never
    "unknown".

Deliberately EXCLUDED fields, and why:
  - `person_id` and `side` are both participant-derived and
    authority-governed. Including either would make an operator's
    participant reassignment or side edit read as a transcript-content
    change and trigger a full utterance-set rewrite on the next import —
    exactly the clobber IMPORT-04 forbids.
  - `section_hint` is derived by the importer's own section state machine
    from resolved sides, so it inherits the same problem.
  - `id`, `argument_id`, `import_run_id` are identity, not content.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

# Frozen per the module docstring above. Bump only alongside a deliberate,
# full-corpus repass — never to silently change what "the same content"
# means for already-stored digests.
DIGEST_VERSION: int = 1


def compute_utterance_digest(rows: Sequence[Mapping[str, Any]]) -> str:
    """
    Compute the D-13 frozen content digest over `rows` — the ordered
    incoming utterance rows for ONE argument.

    Each row must be a mapping carrying at least the keys `sequence`,
    `raw_speaker_label`, `text`, `is_stage_direction`. Any other key
    present on a row is ignored — two row lists that differ ONLY in
    fields outside this frozen list produce the same digest.

    Raises ValueError if `sequence` values are not a strictly ascending
    run of integers starting at 1 — the function never re-sorts; an
    ordering bug must be loud, not silently absorbed into a different
    digest.
    """
    payload: list[list[Any]] = []
    for index, row in enumerate(rows):
        expected_sequence = index + 1
        sequence = row["sequence"]
        if int(sequence) != expected_sequence:
            raise ValueError(
                f"compute_utterance_digest: row at index {index} has "
                f"sequence={sequence!r}, expected {expected_sequence} — "
                "rows must be strictly ascending from 1 (no re-sort)."
            )
        payload.append(
            [
                int(sequence),
                row["raw_speaker_label"],
                row["text"],
                bool(row["is_stage_direction"]),
            ]
        )

    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()
