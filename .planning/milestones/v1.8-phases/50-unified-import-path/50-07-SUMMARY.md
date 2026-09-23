---
phase: 50-unified-import-path
plan: 07
subsystem: pipeline
tags: [prune-runs, leak-ban, admin-pipeline, writer-inventory, d-23, d-24, phase-closeout]

requires:
  - phase: 50-unified-import-path
    plan: "01"
    provides: "migration 0030's ImportRun.content_digest / ArgumentParticipant.oyez_speaker_id / Argument+Case.source+.method columns; corpus import writing no AdminJob (D-18/D-19's precondition)"
  - phase: 50-unified-import-path
    plan: "05"
    provides: "the real reconcile pass (whole-set utterance replacement under a new step=parse run) that D-12's prune-runs command reclaims space from"
  - phase: 50-unified-import-path
    plan: "06"
    provides: "test_gated_column_writers.py (D-24's executable half) and the D-22 delegation sweep this plan's inventory documents"
provides:
  - "python -m pipeline prune-runs — D-12's offline, deliberate space-reclamation CLI"
  - "D-24's dispositioned writer inventory (50-WRITER-INVENTORY.md), pairing plan 50-06's executable behavioral gate"
  - "The extended public-leak ban (content_digest, oyez_speaker_id, argument_discrepancies, PD-17's six batch counters) and /admin/pipeline's honest PDF-only narrowing (D-19)"
  - "D-23's closure — deferred-items.md's Person-scoped Status:open line flipped in the same commit as the answer"
affects: [999.11]

actuals:
  tokens: 17047
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "isolated_session + patched-get_session testing (test_import_convokit_reimport_tracer.py's convention) for a CLI command that opens its own per-argument get_session() internally -- lets a single rollback-isolated test session both seed fixtures and observe the command's own writes without a genuinely committed TRUNCATE-based fixture"
    - "Never call session.rollback() defensively under --dry-run when the dry-run branch already issues zero writes -- recompute-trust's rollback is load-bearing there because it always writes to compute the new value; prune-runs computes without writing at all, so an unconditional defensive rollback only serves to discard a caller's OTHER pending, uncommitted work (the bug this plan's own dry-run tests caught)"
    - "A false-green guard whose 'assert the admin schema carries it' premise is not honestly satisfiable (nothing anywhere exposes the column yet) documents that vacuity explicitly and proves the next-best fact (the column is real ORM vocabulary, not a typo) rather than fabricating an admin-facing exposure nobody asked for"

key-files:
  created:
    - pipeline/commands/prune_runs.py
    - pipeline/tests/test_prune_runs.py
    - .planning/phases/50-unified-import-path/50-WRITER-INVENTORY.md
  modified:
    - pipeline/__main__.py
    - api/tests/test_trust_public_leak_ban.py
    - api/services/admin_jobs.py
    - app/src/routes/admin/pipeline/+page.svelte
    - .planning/phases/49-review-model/deferred-items.md

key-decisions:
  - "prune-runs' --dry-run path never issues a write at all (not 'write then roll back') -- the utterance-count projection is computed via a plain SELECT COUNT before the delete gate, so there is nothing pending to discard and no defensive rollback is needed. Discovered mid-implementation: an initial defensive rollback (mirroring recompute-trust's pattern) was destroying the isolated_session test fixture's own uncommitted seed data, since recompute-trust's rollback is load-bearing (it always writes) while this module's dry-run branch structurally never writes."
  - "content_digest and oyez_speaker_id are banned in the public-leak-ban test even though neither is exposed on ANY schema yet, admin included -- the usual 'assert the admin schema DOES carry it' false-green guard is not honestly satisfiable for these two keys, so the test module documents that explicitly (an ORM-layer non-vacuity proof instead) rather than fabricating an admin exposure this plan has no mandate to add."
  - "Found, during the writer-inventory build, a third ungated writer pair D-22's enumeration and plan 50-06's parse.py conversion both missed: parse.py's _update_participant_sides/_update_participant_descriptors write ArgumentParticipant.side/.descriptor by direct assignment on every parse pass, with no gate call — a real risk of a re-parse silently overwriting an operator's own reassignment. Logged as a new deferred-items.md item, not fixed (parse.py is not in this plan's files_modified; a correct fix needs its own per-row-gate conversion and tests, the same 'new decision, not a bug fix' reasoning this file's very first deferred item already used for a sibling gap)."

requirements-completed: [IMPORT-01, IMPORT-03, IMPORT-04, IMPORT-05]

coverage:
  - id: D1
    description: "python -m pipeline prune-runs reclaims superseded ImportRun/Utterance rows deliberately and offline; the served run (api/services/arguments.py's exact MAX(ImportRun.id) select shape) is never a candidate; a run with an OPEN value_discrepancy row is refused under every flag combination; a run with only RESOLVED rows is refused by default and removed under --include-resolved-discrepancies; --dry-run reports without writing"
    requirement: IMPORT-04
    verification:
      - kind: integration
        ref: "pipeline/tests/test_prune_runs.py (18 tests: single/three-run scenarios, get_argument_with_utterances parity, open/resolved discrepancy handling under every flag combination, reconcile-run pruning, dry-run totals parity, --all batch totals, FK delete ordering, zero-run no-op, unknown-argument-id ValueError, direct _prunable_run_ids unit coverage, CLI --help/no-flag)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The public-leak ban is extended to content_digest, oyez_speaker_id, argument_discrepancies, and PD-17's six reconcile batch-counter names, with the module's false-green-guard convention extended in the same pass (a genuine Pydantic-layer proof for argument_discrepancies, an honest ORM-layer proof for the two keys nothing yet exposes)"
    requirement: IMPORT-05
    verification:
      - kind: unit
        ref: "api/tests/test_trust_public_leak_ban.py (parametrized Test 1 over every public-reachable model x BANNED_KEYS; test_review_queue_argument_item_does_declare_argument_discrepancies; test_content_digest_and_oyez_speaker_id_exist_at_the_orm_layer_not_yet_any_schema; test_banned_keys_include_phase_50_vocabulary; test_public_response_models_never_declare_reconcile_counter_names; test_public_frontend_pages_never_reference_reconcile_counter_names)"
        status: pass
    human_judgment: false
  - id: D3
    description: "/admin/pipeline is honestly narrowed to PDF-only (D-19): a one-line page note points to /admin/arguments and /admin/review, and both is_corpus EXISTS-subquery derivation sites in admin_jobs.py carry a comment recording the corpus branch is unreachable by construction as of Phase 50, citing 999.11"
    requirement: IMPORT-03
    verification:
      - kind: automated_ui
        ref: "cd app && npx --no-install svelte-check --threshold error (0 errors); pipeline/tests/test_import_convokit_adminjob.py (fresh corpus import produces zero admin_job rows, pre-existing from plan 50-01, re-verified green here)"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-24's dispositioned writer inventory (50-WRITER-INVENTORY.md): 24 rows across four dispositions covering every writer that can reach a gated ArgumentParticipant/Person/Argument/Case column, naming the two writers D-22's enumeration missed (found+fixed by plans 50-05/50-06) and D-18's no-op closure, pairing plan 50-06's executable test_gated_column_writers.py gate"
    requirement: IMPORT-05
    verification:
      - kind: other
        ref: "manual table-completeness check: `awk -F'|' 'NR>2 && NF>3 {if ($4~/^[[:space:]]*$/||$5~/^[[:space:]]*$/) print}' 50-WRITER-INVENTORY.md` prints nothing (no blank Disposition/Reason cell); 24 data rows counted via `grep -c '^| [0-9]* |'`"
        status: pass
    human_judgment: false
  - id: D5
    description: "D-23's closure: deferred-items.md's Person-scoped Status:open line is flipped to closed, recording the operator's no-Person-level-published-lock answer with its three reasons, the date 2026-08-25, and a 50-CONTEXT.md citation, in the SAME commit as the writer inventory (Phase 40.1 lesson)"
    requirement: IMPORT-05
    verification:
      - kind: other
        ref: "grep -q 'awaiting the operator' deferred-items.md (absent, confirmed); grep -rn 'Person-level published lock|person_published_lock' api/ app/src/ (zero hits — zero implementation); git log confirms both edits landed in commit ef3ec8bf8"
        status: pass
    human_judgment: false

duration: ~70min
completed: 2026-08-26
status: complete
---

# Phase 50 Plan 07: Prune-Runs, the Extended Leak Ban, and the D-24 Writer Inventory Summary

**D-12's offline `prune-runs` CLI, the leak ban extended to this phase's new vocabulary and PD-17's batch counters, `/admin/pipeline`'s honest PDF-only narrowing, D-24's 24-row dispositioned writer inventory (naming a third ungated writer pair the sweep missed), and D-23's same-commit closure — Phase 50's final plan.**

## Performance

- **Duration:** ~70 min (commit span 12:29–12:40 CDT plus a substantial upfront research/reading phase reading nine prior-phase source files and three prior-plan summaries)
- **Started:** 2026-08-26 (session start)
- **Completed:** 2026-08-26T17:40:29Z
- **Tasks:** 3
- **Files modified:** 8 (3 created, 5 modified)

## Accomplishments

- `pipeline/commands/prune_runs.py` (`run_prune_runs`, `_prunable_run_ids`) plus a `prune-runs` subcommand in `pipeline/__main__.py` (`--all`/`--argument-id` mutually exclusive, `--dry-run`, `--include-resolved-discrepancies`). Re-derives `api/services/arguments.py`'s exact `MAX(ImportRun.id) WHERE step='parse' AND status='completed'` select shape (PD-22) so the served run can never be a prune candidate; a run with an OPEN `value_discrepancy` row is refused under every flag combination (PD-23), counted and printed by name; utterances are deleted before their run, matching `delete_argument`'s documented FK-ordering discipline. 18 new tests in `pipeline/tests/test_prune_runs.py`.
- `api/tests/test_trust_public_leak_ban.py`'s `BANNED_KEYS` extended with `content_digest`, `oyez_speaker_id`, `argument_discrepancies`; a new `BANNED_COUNTER_NAMES` tuple bans PD-17's six reconcile batch-counter names from every public response model AND every genuinely public SvelteKit page. The false-green-guard convention is extended in the same pass: a real Pydantic-layer proof for `argument_discrepancies` (carried by `ReviewQueueArgumentItem`), and an honest ORM-layer proof for `content_digest`/`oyez_speaker_id` documenting that neither is exposed on any schema yet, admin included.
- `api/services/admin_jobs.py`'s two `is_corpus` EXISTS-subquery derivation sites (`get_job`, `list_jobs`) now carry a comment recording the corpus branch is unreachable by construction as of Phase 50 (D-19), citing Phase 999.11 as where it becomes live again. `app/src/routes/admin/pipeline/+page.svelte` gains a one-line page-level note above the run history: "This screen shows PDF-pipeline jobs only. Corpus arguments are reached through /admin/arguments and /admin/review." No new screen, no `class=` attribute added (idiom preserved).
- `.planning/phases/50-unified-import-path/50-WRITER-INVENTORY.md`: a 24-row dispositioned table across `delegates` / `N/A — create, not overwrite` / `N/A — no authority column` / `N/A — review metadata only`, covering every writer that can reach a gated `ArgumentParticipant`/`Person`/`Argument`/`Case` column, naming both writers D-22's own enumeration did not list (`resolve.py`'s bulk `person_id` UPDATE, `import_convokit`'s `_apply_extracted_name_provenance`, both found+fixed by plans 50-05/50-06), D-18's no-op closure, and `test_gated_column_writers.py`'s falsifiability control.
- `.planning/phases/49-review-model/deferred-items.md`: D-23's closure (Person-scoped `Status: open` flipped to closed, recording the operator's no-Person-level-published-lock answer, its three reasons, the 2026-08-25 date, and a `50-CONTEXT.md` citation — same commit as the inventory), plus a new deferred item recording a third ungated writer pair this plan's own inventory build found (`parse.py`'s `_update_participant_sides`/`_update_participant_descriptors`) but did not fix.

## Task Commits

Each task was committed atomically:

1. **Task 1: The offline prune-runs command** — `da4029099` (feat)
2. **Task 2: Extend the public-leak ban and narrow /admin/pipeline to PDF-only** — `dad63a15f` (feat)
3. **Task 3: The dispositioned writer inventory, D-23's closure, and COVERAGE.md** — `ef3ec8bf8` (docs)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP/REQUIREMENTS update)

## Files Created/Modified

- `pipeline/commands/prune_runs.py` — the offline `prune-runs` command (D-12)
- `pipeline/__main__.py` — registers the `prune-runs` subcommand
- `pipeline/tests/test_prune_runs.py` — 18 tests covering every `<behavior>` bullet
- `api/tests/test_trust_public_leak_ban.py` — BANNED_KEYS/BANNED_COUNTER_NAMES extension, extended false-green guard, two new public-frontend/counter-name tests
- `api/services/admin_jobs.py` — D-19 unreachability comments on both `is_corpus` derivation sites
- `app/src/routes/admin/pipeline/+page.svelte` — the honest PDF-only page note
- `.planning/phases/50-unified-import-path/50-WRITER-INVENTORY.md` — the D-24 dispositioned inventory
- `.planning/phases/49-review-model/deferred-items.md` — D-23's closure + the new ungated-writer deferred item

`.planning/phases/50-unified-import-path/COVERAGE.md` was verified, not modified — its declaration line still opens `No external API integration:` and nothing this plan (or 50-01 through 50-06) shipped contacts an external service (`grep -rnE "^(import|from) (anthropic|httpx|requests|openai)" pipeline/commands/prune_runs.py api/domain/content_digest.py` returns nothing).

## Decisions Made

- **`--dry-run` never issues a write, rather than "write then roll back."** `prune_runs.py`'s utterance-count projection under `--dry-run` is computed with a plain `SELECT COUNT` before the delete gate (`if prunable and not dry_run:`), so there is nothing pending for the session to discard. An earlier draft defensively called `session.rollback()` under `--dry-run` regardless (mirroring `recompute-trust`'s pattern, where the rollback IS load-bearing because that command always writes to compute the new tier). Under this module's `isolated_session`-based tests (one shared, uncommitted session across seeding and the command under test — the `test_import_convokit_reimport_tracer.py` convention), that unconditional rollback silently discarded the test's own just-seeded, still-uncommitted fixture rows, producing a false failure. Removed once the actual cause was traced (Rule 1 territory, but caught before any commit — no separate deviation entry needed since the fix landed inside the original Task 1 commit).
- **`content_digest`/`oyez_speaker_id` banned despite no current schema exposure.** Neither column is on ANY Pydantic schema yet, admin included, so the module's established "assert the admin schema DOES carry it" false-green guard genuinely cannot be satisfied honestly for these two keys without fabricating an admin-facing exposure this plan has no mandate to add. Documented that vacuity explicitly in a dedicated test (`test_content_digest_and_oyez_speaker_id_exist_at_the_orm_layer_not_yet_any_schema`) proving the columns are real ORM vocabulary, plus a direct `BANNED_KEYS` membership test, rather than silently forcing the guard's usual shape.
- **A third ungated writer pair found, not fixed.** Reading every writer's source directly (D-24's own stated discipline) surfaced `pipeline/commands/parse.py`'s `_update_participant_sides`/`_update_participant_descriptors` — pre-Phase-49 TOC-mapping helpers that write `ArgumentParticipant.side`/`.descriptor` by direct assignment on every parse pass, unconditionally, with no gate call, no `review_state` check, and no provenance stamp. Since participant rows persist across re-parses, a re-parse can silently overwrite a side/descriptor an operator already reassigned through the gated `update_participant_side` route — the exact failure class D-22's whole sweep exists to close, on a call site neither D-22's enumeration nor plan 50-06's `parse.py` conversion named. Not fixed here: `parse.py` is not in this plan's `files_modified`, and a correct fix needs a real per-row gate conversion (mirroring `resolve.py`'s own 50-06 shape) plus dedicated tests — logged as a new open item in `deferred-items.md` per the scope-boundary rule (log out-of-scope discoveries, do not fix them).

## Deviations from Plan

None — plan executed exactly as written. The `--dry-run`/`session.rollback()` correction above was caught and fixed during Task 1's own implementation, before any commit, and is documented under Decisions Made rather than as a deviation from a plan the commit already reflects correctly.

## Issues Encountered

None beyond the two items documented above under Decisions Made (both resolved: the rollback bug fixed pre-commit; the ungated-writer finding correctly deferred, not fixed, per scope discipline).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 50 (Unified Import Path) is complete: all four in-scope requirements (IMPORT-01, IMPORT-03, IMPORT-04, IMPORT-05) are satisfied across plans 50-01 through 50-07.
- Two phase-gate human items remain open, logged in `WINDOWS.md` per prior plans' SUMMARYs — not closed by this plan, not in its scope: #30 (50-04's browser walkthrough), #31 (50-05's D-09 live double-import + operator-edit-survival walkthrough).
- One new deferred item for a future small plan: converting `parse.py`'s `_update_participant_sides`/`_update_participant_descriptors` to per-row gate calls (mirroring `resolve.py`'s `_apply_resolved_person_ids`), with its own `test_gated_column_writers.py`-style coverage.
- Phase 999.11 (the deferred PDF-route `import_run` peer-strategy work, IMPORT-02) inherits: the `admin_jobs.py` `is_corpus` derivation sites (now dead-but-documented), the deferred `ADMIN_JOB.import_run_id` FK (D-17), and the PDF-route writer coverage this phase's D-22 sweep left to it by design.

---
*Phase: 50-unified-import-path*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created files verified present on disk (`pipeline/commands/prune_runs.py`,
`pipeline/tests/test_prune_runs.py`,
`.planning/phases/50-unified-import-path/50-WRITER-INVENTORY.md`). All modified files
verified present with expected content (`pipeline/__main__.py`,
`api/tests/test_trust_public_leak_ban.py`, `api/services/admin_jobs.py`,
`app/src/routes/admin/pipeline/+page.svelte`,
`.planning/phases/49-review-model/deferred-items.md`). All three task commit hashes
(`da4029099`, `dad63a15f`, `ef3ec8bf8`) verified present in `git log --oneline`. Plan-level
`<verification>` re-run: `./.venv/bin/python -m pytest pipeline/tests/test_prune_runs.py
api/tests/test_trust_public_leak_ban.py -q` — 107 passed; full suite
`./.venv/bin/python -m pytest -q` — 1666 passed, 5 xfailed, 0 failed (baseline was 1618
passed, 5 xfailed, 0 failed — the +48 delta is this plan's own new tests, zero
regressions); `python -m pipeline prune-runs --help` lists all four flags; `cd app &&
npx --no-install svelte-check --threshold error` — 0 errors; the `deferred-items.md`
status flip and the writer inventory are both in commit `ef3ec8bf8`.
