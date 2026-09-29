---
phase: 53-undetermined-speakers-marker-normalisation
plan: 02
subsystem: pipeline
tags: [corpus-import, stage-directions, trust-tier, pydantic, public-schema]

requires:
  - phase: 53-undetermined-speakers-marker-normalisation
    provides: "plan 53-01's migration 0033 (speaker_undetermined / is_inaudible_marker / verbatim_text columns) and the source-sentinel fact stored at import"
provides:
  - "canonical whole-turn marker storage (D-08/D-09): utterances.text carries the one display form (Inaudible), (Laughter), (Voice Overlap), (Recess), (Luncheon Recess), (Cross Talk) for every whole-turn marker row, with the verbatim source form kept in utterances.verbatim_text"
  - "a known speaker's whole-turn Inaudible marker keeps that speaker as an ordinary attributed row (D-04) instead of a stage direction, and is resolved into Person/ArgumentParticipant even when it is their only turn (Pitfall 1)"
  - "trailing-period tolerance in the whole-turn marker regex ((Inaudible). / [Inaudible].)"
  - "the public UtteranceResponse schema carries speaker_undetermined and is_inaudible_marker as plain booleans (D-05/D-12), with verbatim_text and trust vocabulary never reaching it (D-07/D-10)"
affects: [53-03-treatment-d-rendering, 53-04-explanation-card, 53-05-admin-blocker-copy]

actuals:
  tokens: 12404
  tasks: 2
  commits: 2
  plan_head_before: 7f4869b1788ff2f7be47f8c3b485a30014d17df5
  plan_head_after: 0bb01054b803fc07e8f7ee0e39401bec2d2665f4

tech-stack:
  added: []
  patterns:
    - "Three-way row classification (_ROW_SPEECH / _ROW_ROOM_EVENT / _ROW_INAUDIBLE) replacing the old boolean is_stage_direction split in the corpus importer's row-splitting function"
    - "canonical_marker_text as the one place that wraps a curated label in its D-08 display form, called once inside _split_turn_into_rows -- never re-implemented as a second normaliser"

key-files:
  created: []
  modified:
    - pipeline/corpus/stage_directions.py
    - pipeline/commands/import_convokit.py
    - api/schemas/utterance.py
    - api/services/arguments.py
    - pipeline/tests/test_corpus_stage_directions.py
    - pipeline/tests/test_import_convokit_utterances.py

key-decisions:
  - "_split_turn_into_rows now returns a _SplitRow named tuple (text, kind, verbatim_text) instead of a (text, is_stage_direction) tuple -- the only external caller (scripts/diff_corpus_fixture.py) only checks the list's truthiness, so this signature change is safe."
  - "Speaker resolution in _incoming_utterance_rows now triggers on 'any speech row OR any inaudible row' (was 'any non-stage-direction row') -- a room event alone still suppresses it, matching D-03; the missing-speaker-key V5 errored-and-skip path stays exactly as it was for a turn with a speech row, and only branches for an inaudible-only turn with no speaker key (falls back to an unattributed stage-direction row, not an error -- the Claude's-discretion call CONTEXT.md left open, recorded in the plan's <objective>)."
  - "is_inaudible_marker and verbatim_text are threaded onto both Utterance() call sites in _import_utterances (stage-direction branch always false/room-event-verbatim; spoken branch carries the row dict's computed values) -- an inaudible row takes the spoken branch unchanged, since is_stage_direction is already false for it."

requirements-completed: [SPEAKER-08]

coverage:
  - id: D1
    description: "Whole-turn markers canonicalise to one display form (D-08/D-09) with the verbatim source kept (D-10); a marker inline within a spoken sentence is left untouched (D-11); the whole-turn regex tolerates a trailing period"
    requirement: "SPEAKER-06"
    verification:
      - kind: unit
        ref: "pipeline/tests/test_corpus_stage_directions.py::TestTrailingPeriodTolerance (5 cases), TestCanonicalMarkerText (2 cases), TestVocabularySplit (3 cases)"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_canonical_marker_form_and_verbatim_kept (13 parametrized forms)"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_inline_marker_inside_spoken_sentence_left_untouched"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_marker_between_speech_segments_splits_three_rows_same_speaker, test_adjacent_inaudible_markers_not_merged, test_adjacent_room_event_markers_not_merged"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_empty_bracket_segments_stay_inside_speech_row (3 cases), test_empty_turn_text_imported_unchanged"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_reimport_same_corpus_is_a_no_op_one_parse_run"
        status: pass
    human_judgment: false
  - id: D2
    description: "A known speaker's whole-turn Inaudible marker is their own attributed row (not a stage direction), resolved into Person/ArgumentParticipant even when it is their only turn, deriving corpus/direct TRUSTED"
    requirement: "SPEAKER-07"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_known_speaker_whole_turn_inaudible_is_their_own_attributed_row"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_room_event_then_inaudible_known_speaker_stage_then_attributed"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_speakerless_inaudible_turn_falls_back_unattributed_not_errored"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_sentinel_speaker_inaudible_turn_marks_both_flags (D-13 data half)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Voice Overlap (including the ( Voice Overlap) and (voive overlap) forms) stays an unattributed stage direction, and laughter inside a speaker's turn still splits into a speech row plus a separate room-event row -- the two pre-existing D-03 regression tests pass unchanged"
    requirement: "SPEAKER-08"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_whole_turn_stage_direction_produces_separate_row, test_inline_marker_segment_splits_spoken_remainder_into_own_rows (pre-existing, unmodified)"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_speech_then_laughter_speech_attached_room_event_unattributed, test_speakerless_room_event_turn_not_errored"
        status: pass
    human_judgment: false
  - id: D4
    description: "The public UtteranceResponse payload carries speaker_undetermined and is_inaudible_marker as plain booleans (NULL reads as false), and never carries verbatim_text or any trust vocabulary"
    requirement: "SPEAKER-01"
    verification:
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_inaudible_and_sentinel_rows_reach_public_payload"
        status: pass
      - kind: integration
        ref: "pipeline/tests/test_import_convokit_utterances.py::test_null_flags_serialise_as_false_on_public_payload"
        status: pass
      - kind: other
        ref: "grep -n verbatim_text api/schemas/utterance.py (empty output)"
        status: pass
      - kind: integration
        ref: "api/tests/test_trust_public_leak_ban.py (full suite, unchanged pass -- utterance.py already registered)"
        status: pass
    human_judgment: false

duration: 62min
completed: 2026-09-29
status: complete
---

# Phase 53 Plan 2: Marker Normalisation & Inaudible-Speaker Attribution Summary

**Three-way row classification (speech / room event / inaudible) in the corpus importer stores every whole-turn marker in one canonical form with the verbatim source kept, keeps a known speaker's lost-words turn attributed to them instead of discarding it as a stage direction, and puts both facts on the public utterance payload.**

## Performance

- **Duration:** 62 min
- **Started:** 2026-09-29T11:35:00Z (approximate)
- **Completed:** 2026-09-29T12:37:00Z (approximate)
- **Tasks:** 2 completed
- **Files modified:** 6

## Accomplishments

- `pipeline/corpus/stage_directions.py` widens `_WHOLE_TURN_MARKER_RE` to tolerate a trailing period after the closing bracket (`(Inaudible).` / `[Inaudible].`), and adds `INAUDIBLE_LABEL`, `ROOM_EVENT_LABELS`, and `canonical_marker_text` — the one place that wraps a curated label in its D-08 display form, raising `ValueError` for anything not curated.
- `pipeline/commands/import_convokit.py`'s `_split_turn_into_rows` now returns a `_SplitRow(text, kind, verbatim_text)` named tuple classifying every whole-turn marker segment as speech, a room event, or Inaudible — replacing the old boolean `is_stage_direction` split. `_incoming_utterance_rows` triggers speaker resolution on any speech row OR any Inaudible row (only an all-room-event turn suppresses it, D-03), and a known speaker's whole-turn Inaudible marker is stored as their own attributed row rather than a stage direction (D-04, Pitfall 1) — resolved into Person/ArgumentParticipant even when it is their only turn. A speakerless Inaudible-only turn is NOT counted as an error; it falls back to today's unattributed stage-direction treatment, per the Claude's-discretion call CONTEXT.md left open.
- `_import_utterances` threads `is_inaudible_marker` and `verbatim_text` onto both `Utterance(...)` call sites; an inaudible row takes the spoken branch unchanged (participant resolution, side, section-hint) because it is that speaker's turn.
- `api/schemas/utterance.py` gains `speaker_undetermined` and `is_inaudible_marker` (both default `False`, coerced from nullable columns so a legacy NULL row reads as false); `verbatim_text` is deliberately not added — D-10 keeps it database-only.
- `api/services/arguments.py` coerces both new fields with `utterance.<column> is True` after the existing column spread, so the public payload never leaks a raw `None`.
- 45 new tests (17 stage-direction cases, 3 Task-1 importer/payload cases, 25 Task-2 regression-matrix cases including a 13-way parametrize over the curated vocabulary) — the two pre-existing D-03 splitting regression tests pass unmodified. Bare `./.venv/bin/python -m pytest -q`: 1482 passed, 5 xfailed, 0 failed (was 1442/5 before this phase).

## Task Commits

1. **Task 1: known speaker's whole-turn inaudible marker reaches the public payload as their own row** - `06872f229` (feat)
2. **Task 2: vocabulary-wide regression matrix, every adjacency/empty/ordering edge** - `0bb01054b` (test)

**Plan metadata:** committed alongside this SUMMARY (see below)

_Both TDD-flagged tasks: `workflow.tdd_mode` is `false` in this project's config (matching plan 53-01's precedent), so tests and implementation were authored together per task rather than as separate RED/GREEN commits — see "TDD Gate Compliance" below._

## Files Created/Modified

- `pipeline/corpus/stage_directions.py` - trailing-period tolerance, `INAUDIBLE_LABEL`, `ROOM_EVENT_LABELS`, `canonical_marker_text`
- `pipeline/commands/import_convokit.py` - `_SplitRow` named tuple, `_ROW_SPEECH`/`_ROW_ROOM_EVENT`/`_ROW_INAUDIBLE`, reworked `_split_turn_into_rows`/`_incoming_utterance_rows`/`_import_utterances`
- `api/schemas/utterance.py` - `speaker_undetermined`, `is_inaudible_marker` public fields
- `api/services/arguments.py` - NULL-coalescing coercion for both new fields in the per-row response dict
- `pipeline/tests/test_corpus_stage_directions.py` - trailing-period, canonical-text, vocabulary-split test classes
- `pipeline/tests/test_import_convokit_utterances.py` - Task 1's known-speaker/payload/null-flag tests plus Task 2's full regression matrix

## Decisions Made

- Kept `_split_turn_into_rows`'s row-classification logic entirely inside the pre-existing pending/flush shape (the D-03 laughter-splitting guarantee) rather than restructuring it — the three-way kind classification slots into the existing per-segment loop with no new control flow shape.
- No production code changed in Task 2 — every regression-matrix case (13 vocabulary forms, 6 adjacency shapes, 4 empty/ordering shapes) already passed against Task 1's classification, so Task 2 is pure regression coverage per the Defect Policy's own framing (a defect fix would have been reported in one line; there was none to report).

## Deviations from Plan

None - plan executed exactly as written. One inline self-correction: the module docstring added to `api/schemas/utterance.py` initially referenced the literal substring `verbatim_text`, which the task's own acceptance-criteria grep (`grep -n 'verbatim_text' api/schemas/utterance.py` expecting no output) would have failed against — reworded before the first verification run, not a behavior change.

## TDD Gate Compliance

Both tasks carry `tdd="true"`, but `workflow.tdd_mode` is `false` in this project's `.planning/config.json` (same precedent as plan 53-01), so the formal RED→GREEN→REFACTOR gate is not enforced this phase. Task 1 landed as a single `feat(53-02):` commit with tests and implementation together, verified against its `<verify>` commands before commit. Task 2 landed as a single `test(53-02):` commit (test-only — no production code needed fixing), also verified before commit. No `test(...)`/`feat(...)` commit pair was expected for Task 1's RED/GREEN split, and none was claimed.

## Issues Encountered

None. The `scotus_test` DB-tombstone risk noted in project memory did not manifest.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `speaker_undetermined` and `is_inaudible_marker` are now on the public `UtteranceResponse` payload (SPEAKER-01's payload half) and every whole-turn marker row carries canonical text plus verbatim — 53-03 (Treatment D rendering) and 53-04 (explanation card) can read both facts directly, no further pipeline work needed.
- SPEAKER-06, SPEAKER-07, and SPEAKER-01 are also declared by sibling plan 53-03 in this phase (shared-ID gate, #2388) — `REQUIREMENTS.md` holds them `Pending` until 53-03 finishes too; only SPEAKER-08 (declared solely by this plan) was marked `Complete` here.
- No blockers. `api/domain/content_digest.py`, `pipeline/parser`, and `pipeline/commands/parse.py` are confirmed untouched (plan-level verification passed), so the D-13 digest contract and the PDF path are unaffected.

## Self-Check: PASSED

- `pipeline/corpus/stage_directions.py` (`canonical_marker_text`, `INAUDIBLE_LABEL`, `ROOM_EVENT_LABELS`) — FOUND
- `pipeline/commands/import_convokit.py` (`_SplitRow`, `_ROW_INAUDIBLE`) — FOUND
- Commit `06872f229` — FOUND in `git log --oneline --all`
- Commit `0bb01054b` — FOUND in `git log --oneline --all`
- All plan-level `<verification>` commands re-run and passing: bare `pytest -q` → 1482 passed, 5 xfailed, 0 failed; `scripts/diff_corpus_fixture.py --help` → exit 0; `git diff --name-only ef5d79f1f -- api/domain/content_digest.py pipeline/parser pipeline/commands/parse.py` → empty

---
*Phase: 53-undetermined-speakers-marker-normalisation*
*Completed: 2026-09-29*
