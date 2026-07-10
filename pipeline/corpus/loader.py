"""
Streaming and full-load readers for the ConvoKit supreme-corpus source
files (D-18 input side, D-21 file scope).

``utterances.jsonl`` is ~900MB -- it is never fully materialized in
memory. ``stream_utterances_for_conversation_ids`` is a generator that
opens the file and iterates ``for line in f``, yielding only rows whose
``conversation_id`` is in the caller-supplied wanted set.

``conversations.json`` (3.8MB) and ``speakers.json`` (0.6MB) are small
enough to load fully. ``cases.jsonl`` (13MB) is streamed line-by-line
for consistency with the same JSONL-per-line convention, and indexed by
docket number for the docket/case_id join Plan 05's importer performs
per October Term batch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def stream_utterances_for_conversation_ids(
    utterances_path: Path, wanted_ids: set[str]
) -> Iterator[dict]:
    """
    Stream ``utterances_path`` (a JSONL file) line-by-line, yielding only
    rows whose ``conversation_id`` is in ``wanted_ids``.

    Never calls ``.read()``/``json.load()`` on the whole file -- this is
    the 900MB streaming constraint (D-18, RESEARCH Pattern 3). Blank
    lines are skipped.
    """
    with utterances_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("conversation_id") in wanted_ids:
                yield row


def load_conversations_for_term(conversations_path: Path, term: int) -> dict:
    """
    Load ``conversations_path`` (conversations.json, ~3.8MB -- safe to
    load whole) and return only the entries whose ``case_id`` field has
    the ``"{term}_"`` prefix (D-15: term batching by October Term).

    The dict KEY is an opaque ConvoKit conversation id (e.g. ``"13127"``)
    unrelated to term/case numbering -- the real corpus never prefixes it
    with the term. The term-prefixed identifier (e.g. ``"1955_71"``) lives
    in each conversation's own ``case_id`` field.
    """
    with conversations_path.open("r", encoding="utf-8") as f:
        all_conversations = json.load(f)

    prefix = f"{term}_"
    return {
        cid: conv
        for cid, conv in all_conversations.items()
        if str(conv.get("case_id", "")).startswith(prefix)
    }


def load_speakers(speakers_path: Path) -> dict:
    """
    Load ``speakers_path`` (speakers.json, ~0.6MB) fully. Keyed by
    speaker slug/id (justices: ``j__firstname_lastname``; advocates:
    slugified display name).
    """
    with speakers_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_cases(cases_path: Path) -> dict:
    """
    Stream ``cases_path`` (cases.jsonl, ~13MB) line-by-line and return a
    dict indexed by each row's ``id`` field (e.g. ``"1955_71"``) -- the
    corpus's own globally-unique case identifier, matching
    conversations.json's per-conversation ``case_id`` field.

    NOT indexed by ``docket_no``: historical docket numbers recycle across
    October Terms (docket "71" is a distinct, unrelated case in nearly a
    dozen different terms), so a docket_no-keyed dict would silently drop
    same-docket rows from earlier terms as later ones overwrite them.

    Blank lines are skipped; rows with no ``id`` are omitted from the index.
    """
    cases_by_id: dict[str, dict] = {}
    with cases_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            case_id = row.get("id")
            if case_id is not None:
                cases_by_id[case_id] = row
    return cases_by_id
