---
phase: 39-bench-popover-additional-context-data
plan: 04
subsystem: api
tags: [pydantic, fastapi, sqlalchemy, apolitical-framing, decision-log]

# Dependency graph
requires:
  - phase: 39-bench-popover-additional-context-data
    plan: "01"
    provides: "TenureEntry.reason_left, Person.death_date, CourtTenure.reason_left — the schema/service shape this plan extends further"
provides:
  - "TenureEntry.appointed_by / .appointing_president_party — per-tenure appointing-president data (D-11/D-12/D-13)"
  - "SpeakerPopoverEntry.birthdate / .death_date / .bio_text — new person-level public fields"
  - "Retirement of SpeakerPopoverEntry.appointing_president (top-level field, D-13 promote)"
  - "Reversed module docstrings in api/schemas/speakers.py and api/services/speakers.py stating the current (post-T-14-02) position"
  - "Exact-key-set regression tests (api/tests/test_speakers_service.py) pinning the widened contract"
  - "PROJECT.md Key Decisions row recording the T-14-02 reversal"
affects: [39-05, 39-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Step 5 assembly dict stays an explicit hand-written allow-list (never model_validate(person)/vars(person)/__dict__ spread) even as the payload widens — the control an exact-key-set equality test (== not <=) enforces mechanically"
    - "A 'promote, not add-alongside' field migration (D-13): the old top-level field is deleted outright in the same commit that adds its per-tenure replacement, with a comment at the deletion site pointing to where the concept moved"

key-files:
  created: []
  modified:
    - api/schemas/speakers.py
    - api/services/speakers.py
    - api/tests/test_speakers_service.py
    - .planning/PROJECT.md

key-decisions:
  - "D-11/D-12 (39-CONTEXT.md, executed here): appointing_president_party is exposed on the public speaker popover payload, reversing Phase 14's T-14-02 exclusion — the value describes the appointing president's party (factual historical record about a partisan officeholder), not the Justice's, and is rendered identically for every tenure entry with no aggregation or differential framing."
  - "D-13 (39-CONTEXT.md, executed here): the top-level SpeakerPopoverEntry.appointing_president field (hardcoded null since Phase 22) is fully retired — promoted to per-tenure TenureEntry.appointed_by, not kept as a deprecated alias — because a Justice can hold multiple tenures with different appointing presidents (e.g. Rehnquist: Nixon, then Reagan)."

requirements-completed: [PUB-04]

coverage:
  - id: D1
    description: "GET /arguments/{id}/speakers returns appointing_president_party inside each tenure entry (T-14-02 reversal)"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_speakers_service.py::TestPartyFieldNotSilentlyReExcluded::test_appointing_president_party_present_on_tenure_entry"
        status: pass
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_tenures_with_differing_party_values_are_identically_shaped"
        status: pass
    human_judgment: false
  - id: D2
    description: "appointed_by populated per tenure from court_tenures.appointed_by; top-level appointing_president field fully retired"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_speakers_service.py::TestPartyFieldNotSilentlyReExcluded::test_top_level_appointing_president_field_not_reintroduced"
        status: pass
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_speaker_and_tenure_key_sets_are_exact_not_subset"
        status: pass
    human_judgment: false
  - id: D3
    description: "SpeakerPopoverEntry returns birthdate, death_date, bio_text for every speaker, null when unknown"
    requirement: "PUB-04"
    verification:
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_person_fields_with_values_produce_iso_strings_and_verbatim_bio"
        status: pass
      - kind: integration
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_person_fields_all_null_produce_none_with_keys_still_present"
        status: pass
    human_judgment: false
  - id: D4
    description: "Assembled dict's key set is an exact, closed allow-list (T-39-13) — no adjacent Person column leaks as a side effect of widening"
    requirement: "PUB-04"
    verification:
      - kind: unit
        ref: "api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_speaker_and_tenure_key_sets_are_exact_not_subset"
        status: pass
      - kind: other
        ref: "Manual RED demonstration: temporarily added \"oyez_speaker_id\": person.oyez_speaker_id to the Step 5 dict; test_speaker_and_tenure_key_sets_are_exact_not_subset failed with 'Extra items in the left set: oyez_speaker_id'; reverted; confirmed git diff clean and suite green again."
        status: pass
    human_judgment: false

duration: ~2h (includes ephemeral PostgreSQL provisioning — see Issues Encountered)
completed: 2026-07-28
status: complete
---

# Phase 39 Plan 04: Widen the public speaker contract Summary

**Reversed Phase 14's T-14-02 party exclusion, promoted the top-level `appointing_president` field to a per-tenure `appointed_by`, and added `birthdate`/`death_date`/`bio_text` to the public speaker popover payload — all pinned by exact-key-set regression tests.**

## Performance

- **Duration:** ~2h (includes provisioning a throwaway ephemeral PostgreSQL instance for this WSL session)
- **Completed:** 2026-07-28
- **Tasks:** 2 completed
- **Files modified:** 4 (2 source, 1 test, 1 planning doc)

## Accomplishments

- `TenureEntry.appointed_by` and `.appointing_president_party` added; `SpeakerPopoverEntry.birthdate`, `.death_date`, `.bio_text` added; the retired top-level `SpeakerPopoverEntry.appointing_president` field deleted outright (D-13 promote, not add-alongside).
- Both `api/schemas/speakers.py` and `api/services/speakers.py` module docstrings rewritten from the T-14-02 exclusion assertion to the Phase 39 reversal rationale, with the `T-14-02` identifier retained in both files for traceability.
- `api/services/speakers.py` Step 3a now emits `appointed_by`/`appointing_president_party` per tenure (Step 3a's `date_tenures_by_person` representation deliberately left untouched — it exists only for `_tenure_role_name`'s date comparisons). Step 5 emits `birthdate`/`death_date`/`bio_text` directly from the already-loaded `Person` ORM row (no second query) and no longer hardcodes a top-level appointment key.
- The Step 5 assembly dict remains an explicit hand-written allow-list — confirmed by grep (`model_validate(person)|person.__dict__|vars(person)` count is 0) — so the widening does not also leak `oyez_speaker_id`, `name_extraction_metadata`, or `name_needs_review` (T-39-13).
- 7 new test functions added to `api/tests/test_speakers_service.py`:
  - Two pure-Python schema-shape regression guards (`TestPartyFieldNotSilentlyReExcluded`) — no database required.
  - Four DB-gated assembly tests (`TestGetArgumentSpeakersWidenedContractShape`) proving exact key-set equality for both the speaker dict and each tenure dict, correct ISO-string/verbatim-bio rendering with values present, `None`-with-keys-present when all three person fields are `NULL`, and byte-identical shape across two tenures with differing `appointing_president_party` values (ordered by `start_date` ascending, matching the service's `order_by`).
- New `.planning/PROJECT.md` Key Decisions row recording the T-14-02 reversal, its rationale (appointing president's party is factual historical record about a president, not the Justice), and the Phase 39 outcome cross-referencing 39-CONTEXT.md D-11/D-12.

## Task Commits

Each task was committed atomically:

1. **Task 1: Widen the public contract and retire the top-level appointment field** — `55c732b9` (feat) — schema and service changes; both docstrings rewritten; verified against `python -c` field-presence assertions, grep-based exclusion-wording checks, and the T-14-02 traceability grep.
2. **Task 2: Pin the reversed contract with regression tests and record the decision** — `e1cbba9d` (test) — 7 new test functions plus the PROJECT.md Key Decisions row.

## RED Demonstration (Task 2 acceptance criterion)

Per the task's acceptance criteria, temporarily added `"oyez_speaker_id": person.oyez_speaker_id` to the Step 5 assembly dict in `api/services/speakers.py`. Observed the following test fail:

```
FAILED api/tests/test_speakers_service.py::TestGetArgumentSpeakersWidenedContractShape::test_speaker_and_tenure_key_sets_are_exact_not_subset
AssertionError: assert set(entry.keys()) == self._SPEAKER_KEYS
Extra items in the left set: 'oyez_speaker_id'
```

Reverted the stray key immediately after observing the failure; `git diff api/services/speakers.py` confirmed a clean diff (byte-identical to the Task 1 committed state) before re-running the suite to confirm GREEN again.

## New PROJECT.md Key Decisions Row (verbatim)

```
| `appointing_president_party` exposed on the public speaker popover payload, reversing T-14-02; top-level `appointing_president` retired in favour of per-tenure `appointed_by` (D-11/D-12/D-13, Phase 39) | The value describes the appointing president — a partisan officeholder by definition — not the Justice, who has no party; it is factual historical record and renders identically for every tenure entry with no aggregation or differential framing, so the apolitical hard constraint on how Justices themselves are treated is preserved | ✓ Good — Phase 39 is the reversal point; see 39-CONTEXT.md D-11/D-12 for the full rationale; pinned by exact-key-set tests in `api/tests/test_speakers_service.py` |
```

## Deviations from Plan

None — plan executed exactly as written. No auto-fixes were required; Task 1's code changes were correct on first verification pass.

## Issues Encountered

- **No PostgreSQL reachable from this WSL sandbox** (the project's documented split-environment constraint — see the `project-scotuschat-wsl-windows-split` memory note). Provisioned a throwaway, session-local PostgreSQL 16 instance via the `pgserver` PyPI package (Unix-domain-socket only) in a scratch Python 3.12 venv (system default Python was 3.14, which `pgserver` has no wheel for), installed the project's `requirements.txt`/`requirements-dev.txt` into that venv, created a `scotus_test` database, and ran `alembic upgrade head` (through migrations 0023/0024, already present from Plan 39-01) against it. Ran the daemon as a persistent background process (`pgserver`'s default `cleanup_mode='stop'` tears the server down when the last referencing process exits, so a one-shot script per pytest invocation would not keep it running for the reset-and-rerun cycle this plan needed). Torn down explicitly at the end of this plan (`server.cleanup()` plus an explicit `kill` of the orphaned postgres process) and confirmed via `ps aux | grep postgres` returning nothing — never connected to any real dev/CI database, no real data read or written.
- **Full combined `pytest` (no args: `tests/` + `pipeline/tests/` + `api/tests/`) trips the pre-existing `tests/conftest.py` shared-dev-DB row-count guard** on a fresh, empty ephemeral database (observed: `people: before=0 after=12`), while `tests/`, `pipeline/tests/`, and `api/tests/` each pass individually with zero net row-count drift when run in isolation. This reproduces the already-documented Phase 31 finding in STATE.md ("`test_resolve_interrupt_sets_needs_review`'s full-suite-only failure root-caused to a module-reimport identity split — `tests/test_admin_router.py` reimports `api.*` mid-session") — a pre-existing cross-test-file interaction unrelated to this plan's schema/service/test changes, out of this plan's scope per the deviation rules' scope boundary. This plan's actual acceptance criteria that matter for its own changes — `api/tests/test_speakers_service.py` (24/24 pass) and `api/tests/` in full (503/503 pass) — are both clean. Not remediated here; flagged for a future phase/plan that owns full-suite hygiene.

## Next Phase Readiness

- The widened public contract (`appointed_by`, `appointing_president_party`, `birthdate`, `death_date`, `bio_text`, retired `appointing_president`) is in place for Plan 39-05 to rewrite `SpeakerPopover.svelte` (lines 30, 84-88) and the argument page's `SpeakerDetail` interface (`+page.svelte` line 24) — the two confirmed in-repo consumers of the retired top-level field.
- `api/tests/` (503 tests): all green against the ephemeral instance after this plan's changes.
- The full-suite-only guard trip described above is a pre-existing, already-documented environment issue and does not block 39-05/39-06.

## Self-Check: PASSED

- `api/schemas/speakers.py` — FOUND
- `api/services/speakers.py` — FOUND
- `api/tests/test_speakers_service.py` — FOUND
- `.planning/PROJECT.md` — FOUND
- Commit `55c732b9` — FOUND in `git log --oneline --all`
- Commit `e1cbba9d` — FOUND in `git log --oneline --all`
