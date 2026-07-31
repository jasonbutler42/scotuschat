---
phase: 42-corpus-import-fidelity-diff-fix
verified: 2026-07-30T21:15:00Z
status: passed
score: 5/5 roadmap success criteria verified; 2 human-confirmation items resolved 2026-07-30 via 42-UAT.md (both approved)
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Confirm the 'Post-Review Correction' (item 9) classification in .planning/CORPUS-FIDELITY-DIFF.md — the case-level `advocates` dead-key finding (CR-01) proposed as 'documentation/cleanup note, not a fidelity defect' — as the document itself states this was found AFTER the operator's 2026-07-30 batch review and has never received explicit operator disposition, unlike items 1-8."
    expected: "Operator reviews the Post-Review Correction section and records an explicit approve/adjust/decline disposition for item 9, consistent with the D-05/D-06 process already applied to items 1-8."
    why_human: "The document's own text states this classification is 'a proposal awaiting explicit operator confirmation, not something this correction may decide on its own' — this is a process/governance gate the phase's own rules require a human to close, not something a grep or test can verify."
  - test: "Confirm whether the existing DB-level (source_docket, question_number) UNIQUE constraint is sufficient assurance for concurrency safety of the --conversation-id scoped import path, given Plan 02's must-have truth ('Two concurrent scoped imports of the same conversation id never both create an Argument row') was declared `verification: backstop` and no concurrency test was built or run."
    expected: "A human judges whether relying on the existing UNIQUE constraint (surfacing a race as a docket_question_conflict counter increment) is adequate, given this is offline, operator-only tooling with no concurrent-access scenario in normal use (CLAUDE.md: 'pipeline is offline only')."
    why_human: "No concurrency harness exists in this codebase; this is inherently unverifiable by an automated check in the time available, and Plan 02's own SUMMARY explicitly flags it as `human_judgment: true`."
---

# Phase 42: Corpus Import Fidelity Diff & Fix Verification Report

**Phase Goal:** Everything `import-convokit` drops, mis-maps, or silently defaults for the confirmed fixture is identified, classified, and fixed — so the fixture's rows in `cases`, `arguments`, `utterances`, `people`, `argument_participants`, and `court_tenures` faithfully reflect its raw ConvoKit source, with real defects separated from deliberate exclusions.

**Verified:** 2026-07-30T21:15:00Z
**Status:** passed (was human_needed; both items resolved 2026-07-30 via 42-UAT.md)
**Re-verification:** No — initial verification

## Goal Achievement

This verification does not rely on SUMMARY.md claims alone. Every load-bearing claim
below was independently re-checked against the live codebase, the real dev database
(`scotus`, reached via `./.venv/Scripts/python.exe` per this project's documented
WSL/Windows split), and by **re-running `scripts/diff_corpus_fixture.py` myself** and
diffing its fresh output against the committed document.

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A field-by-field comparison exists for all six tables, every field marked Faithful/Dropped/Mis-mapped/Silently defaulted | ✓ VERIFIED | `.planning/CORPUS-FIDELITY-DIFF.md` contains all six section headings (cases, arguments, utterances, people, argument_participants, court_tenures). Independently re-ran `./.venv/Scripts/python.exe scripts/diff_corpus_fixture.py --conversation-id 15169 --out ...` against the real dev DB and `data/corpus/` — output reproduced the committed post-fix tables byte-for-byte (apart from the timestamp line), confirming the document is genuinely regenerable, not fabricated. |
| 2 | Each discrepancy classified as real defect or intentional exclusion, with reason recorded | ✓ VERIFIED (with 1 open governance item, see Human Verification) | `## Disposition` section records the operator's 2026-07-30 verbatim disposition for all 8 originally-identified Review Gate items (classification + chosen option + reason for each). One additional item (item 9, the case-level `advocates` dead-key correction from code review) was found *after* the operator's batch review and is explicitly flagged in the document itself as still awaiting operator confirmation — see Human Verification. |
| 3 | Re-importing after fixes produces correct rows for every real-defect field, re-verified not assumed | ✓ VERIFIED | Plan 05 deleted the fixture (`scripts/delete_fixture_argument.py --conversation-id 15169 --delete-case --yes`), re-imported (`import-convokit --conversation-id 15169`), and re-ran the same diff generator against the fresh rows (Argument id 1864). I independently re-ran the same script again post-verification and confirmed: `section_hint` non-null count is 1/480 (up from 0/480 pre-fix, matching the fixture's actual single PETITIONER-side transition); `ArgumentParticipant.side` for Thurgood Marshall queried directly against the live DB is still `BENCH` (matching the operator-approved `bench-warn-only` disposition, which explicitly does not reassign side); the case-level `advocates` field now correctly reads `Dropped`/`dead key` instead of the pre-review-fix `Faithful` misclassification. |
| 4 | Re-imported fixture's utterance count, speaker roster, and source-docket set match raw ConvoKit source exactly | ✓ VERIFIED | Direct DB query: 480 utterance rows for Argument id 1864 (467 spoken + 13 stage-direction rows from 479 raw turns — the split is explained and expected, not a discrepancy). Volume and Roster Exactness section cross-checked against `.planning/FIXTURES.md`'s independently-derived counts (9 advocates, 15 distinct speakers, 8 bench speakers, 479 turns, 2 transcripts) — zero divergence found. Roster count (17) vs. raw distinct speakers minus sentinel (15) is explained by 2 advocates of record who never personally speak (Cox, Auerbach) — documented, not a defect. Docket set match: `{'642'}` both sides. |
| 5 | Corpus-import behavior for other arguments unchanged; no full-corpus backfill triggered | ✓ VERIFIED | Direct DB queries (run independently by this verifier): `arguments` total = 166, `people` = 343, `court_tenures` = 123, `cases` where `term_year=1966` = 1 — all match the Plan 01/02 recorded baseline. `pipeline_runs` query in the diff document shows 163 pre-existing `convokit_import` runs all dated 2026-07-10 (before this phase started), with only the fixture's own run created during Phase 42. |

**Score:** 5/5 roadmap success criteria independently verified against live evidence (not assumed from SUMMARY claims).

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| CORPUS-13 | 42-01, 42-03 | Field-by-field comparison exists, surfacing dropped/mis-mapped/silently-defaulted fields | ✓ SATISFIED | `.planning/CORPUS-FIDELITY-DIFF.md` + `scripts/diff_corpus_fixture.py`, confirmed regenerable |
| CORPUS-14 | 42-01, 42-02, 42-04, 42-05 | Every gap fixed and verified by re-importing the fixture cleanly | ✓ SATISFIED | Plan 04's 2 approved code fixes (section_hint, bench-tenure warn-only) landed in `pipeline/commands/import_convokit.py`; Plan 05's re-import + re-diff confirms them; independently re-verified live |

Both requirement IDs declared in plan frontmatter (`42-01`, `42-02`, `42-03`, `42-04`, `42-05`) match REQUIREMENTS.md's traceability table exactly (CORPUS-13 → Phase 42, CORPUS-14 → Phase 42, both marked Complete). No orphaned requirements found for Phase 42.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `pipeline/corpus/loader.py::load_conversation_by_id` | Single-conversation loader | ✓ VERIFIED | Present, no `argparse` import (confirmed via grep) |
| `pipeline/commands/import_convokit.py::_resolve_scoped_conversation` | Validates/derives term for `--conversation-id` | ✓ VERIFIED | Present; WR-02 fix (no-underscore case_id guard) confirmed present and behaviorally correct via direct interactive test I ran |
| `--conversation-id` CLI flag | Registered in `import-convokit`'s mutually-exclusive term group | ✓ VERIFIED | `pipeline/__main__.py` |
| `scripts/delete_fixture_argument.py` | FK-ordered, id-scoped, single-transaction delete routine | ✓ VERIFIED | Present; WR-04 fix (admin_jobs pre-flight count) confirmed present in code |
| `scripts/diff_corpus_fixture.py` | Regenerable field-by-field diff generator | ✓ VERIFIED | Present; CR-01, WR-01, WR-03 fixes all confirmed present in code and behaviorally correct via live re-run |
| `.planning/CORPUS-FIDELITY-DIFF.md` | Durable diff + classification document | ✓ VERIFIED | Present, 526 lines, all six table sections, Disposition, Fixes Applied, Post-Fix Verification, Regression Checks, Post-Review Correction sections all present and internally consistent with live DB state |
| `pipeline/tests/test_import_convokit_bench_tenure.py` | Coverage for bench-tenure warn-only fix | ✓ VERIFIED | Present, 4 tests |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `--conversation-id` narrowing | `stream_utterances_for_conversation_ids` | narrowing happens before `wanted_ids` is built | ✓ WIRED | Confirmed by live DB state: only 1 term-1966 conversation ever imported across the whole phase (`cases where term_year=1966` = 1, never 135) |
| `scripts/diff_corpus_fixture.py` raw side | `pipeline.corpus.loader` / `pipeline.corpus.apolitical` | reads only through loader + extractor functions, never a second parser | ✓ WIRED | Confirmed: `_parse_argued_date` reuse verified by test; FORBIDDEN_FIELDS membership check is data-driven (`raw_case.keys()` / `raw_conversation.keys()` sweep after WR-03 fix), not a second hand-written list |
| `import_convokit.py::_import_utterances` | `Utterance.section_hint` | non-cascading derivation, threaded through `_resolve_and_link_participant`'s `argued_date` param | ✓ WIRED | Confirmed live: fresh re-import produces exactly 1/480 non-null section_hint, matching the fixture's one real side transition |
| `_check_bench_tenure_mismatch` | `bench_tenure_mismatch` summary counter | read-only `CourtTenure` query, no write | ✓ WIRED | Confirmed: re-import printed "5 bench tenure mismatches"; grep confirms zero `CourtTenure`/`Person.is_justice` write statements in the check's code path |

### Code Review Findings — Fix Verification

The phase went through `42-REVIEW.md` (1 critical, 4 warnings) and `42-REVIEW-FIX.md`
(claims all 5 fixed). I independently re-verified each fix landed in the actual code,
not just in the fix report's prose:

| Finding | Claimed Fix | Verified in Code? |
|---|---|---|
| CR-01 (dead advocates field misreported Faithful) | `_CASE_DEAD_KEYS = {"advocates"}`, verdict changed to Dropped/dead key | ✓ Confirmed via grep + live regeneration — now correctly reports `Dropped`/`dead key` |
| WR-01 (raw value leak for non-allowlisted dropped fields) | New `NOT_ALLOWLISTED` fixed marker | ✓ Confirmed via grep + live regeneration — `url`, `adv_sides_inferred`, `known_respondent_adv`, `is_eq_divided` all now show `[NOT SHOWN -- ...]` instead of their real raw values |
| WR-02 (case_id with no underscore silently derives bogus term) | Explicit `"_" not in case_id_str` guard | ✓ Confirmed via direct interactive test — a case_id of `"642"` (no underscore) now correctly raises `ArgumentTypeError` naming both the conversation id and the malformed case_id, instead of silently deriving term=642 |
| WR-03 (conversation-level FORBIDDEN_FIELDS reporting incomplete) | Data-driven sweep over `raw_conversation.keys()` | ✓ Confirmed via grep — `_build_arguments_rows` now iterates `raw_conversation.keys()` the same way `_build_cases_rows` iterates `raw_case.keys()` |
| WR-04 (delete script's report omits admin_jobs nullification) | Explicit `admin_jobs` count-and-print step | ✓ Confirmed via grep — `admin_jobs (argument_id set NULL, not deleted): N` line present in `scripts/delete_fixture_argument.py` |

### Apolitical Hard Constraint — Independently Re-Verified

I independently read the fixture's actual raw values for all six `FORBIDDEN_FIELDS`
names directly from `data/corpus/cases.jsonl` (`win_side=1.0`, `win_side_detail=4.0`,
`votes={...}`, `votes_detail={...}`, `votes_side={...}`, `scdb_docket_id='1966-071-01'`)
and confirmed via grep that **none of these literal raw values appear anywhere** in the
committed `.planning/CORPUS-FIDELITY-DIFF.md` — only the fixed `[REDACTED ...]` marker
appears. This independently confirms Plan 03's prohibition ("No raw value of any field
in `FORBIDDEN_FIELDS` may appear anywhere in the committed document") actually holds in
the artifact, not just in the plan's stated intent.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any of the six
files this phase modified or created (`scripts/diff_corpus_fixture.py`,
`scripts/delete_fixture_argument.py`, `pipeline/commands/import_convokit.py`,
`pipeline/corpus/loader.py`, `pipeline/corpus/apolitical.py`, `pipeline/__main__.py`).

### Deferred (Pre-Existing, Unrelated) Items — Confirmed Genuinely Out of Scope

`.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` logs two
pre-existing `api/tests` failures (a WSL/Windows Node.js path-mangling bug in
`test_phase38_people_ui_contract.py`, and a `roles.name` UniqueViolation in
`test_speakers_service.py`). I independently confirmed both are genuinely unrelated:

- `git log -1` on both affected test files shows their last modification was
  2026-07-27 and 2026-07-28 respectively — **before** Phase 42 started (2026-07-30).
- `git diff --stat` across every Phase 42 commit (`68e83c55` through `4995a946`)
  against the `api/` directory returns **empty** — no Phase 42 commit touched any
  `api/` file.
- `pipeline/tests/ -q` (the actual gate every Phase 42 plan's verification block
  requires) is fully green: 226 passed, 5 pre-existing xfailed, independently
  re-run by this verifier with the same result.

These are correctly deferred, not something this phase should have fixed.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full pipeline test suite green | `./.venv/Scripts/python.exe -m pytest pipeline/tests/ -q` | `226 passed, 5 xfailed` | ✓ PASS |
| Diff generator is genuinely regenerable | `./.venv/Scripts/python.exe scripts/diff_corpus_fixture.py --conversation-id 15169 --out ...` (run live by this verifier) | Output reproduces committed post-fix tables byte-for-byte apart from the timestamp | ✓ PASS |
| Fixture present, correct row counts | Direct SQL queries against real dev DB via `pipeline.db.get_session` | `arguments`=166, `people`=343, `court_tenures`=123, fixture utterances=480, non-null section_hint=1, Marshall side=BENCH | ✓ PASS |
| WR-02 fix behaves correctly on the untested edge case it targets | Direct interactive Python call with a no-underscore `case_id` | Correctly raises `ArgumentTypeError` naming both ids | ✓ PASS |
| No FORBIDDEN_FIELDS raw value leak | grep of real raw values against the committed diff document | Zero matches | ✓ PASS |

### Human Verification Required — RESOLVED 2026-07-30 (see 42-UAT.md)

Both items below were presented to the operator and approved. Recorded in
`.planning/CORPUS-FIDELITY-DIFF.md` (item 9 disposition) and `42-UAT.md` (both test results).

1. **Item 9 (Post-Review Correction) operator disposition is still open.** `.planning/CORPUS-FIDELITY-DIFF.md`'s own "Post-Review Correction" section states its proposed classification ("documentation/cleanup note, not a fidelity defect") for the case-level `advocates` dead-key finding "is a proposal awaiting explicit operator confirmation, not something this correction may decide on its own" — and no such confirmation appears anywhere in `STATE.md` or any plan SUMMARY. This is a process gap the phase's own D-05/D-06 rule requires a human to close (items 1-8 all have recorded dispositions; item 9 does not), not a code defect — the underlying fix (CR-01) is verified correct.
   - **Expected:** Operator reviews and records an explicit disposition for item 9, matching the treatment already given to the structurally identical item 5 (dead `conversation_id` key).
   - **Why human:** This is an explicit governance/sign-off requirement stated by the document itself, not a technical correctness question.

2. **D8's concurrency-safety truth was never actually tested.** Plan 02's must-have truth "Two concurrent scoped imports of the same conversation id never both create an Argument row" is marked `verification: backstop` in the plan and `human_judgment: true` in the SUMMARY — no concurrency harness exists in this codebase, so this was never exercised. The only safety net is the existing `(source_docket, question_number)` DB UNIQUE constraint.
   - **Expected:** A human judges whether that existing constraint is sufficient assurance, given this is offline/operator-only tooling with no normal concurrent-access scenario.
   - **Why human:** No automated test exists or was built to exercise this; it is inherently a judgment call about acceptable risk for dev-only tooling, already flagged honestly by the plan's own author rather than glossed over.

### Gaps Summary

No BLOCKER-level gaps found. All five ROADMAP success criteria, both requirement IDs
(CORPUS-13, CORPUS-14), and every plan-level must-have artifact/key-link were
independently re-verified against live code, a live re-run of the diff generator, and
direct database queries — not assumed from SUMMARY.md claims. All 5 code-review
findings (1 critical, 4 warnings) were confirmed actually fixed in the committed code,
not just claimed fixed in `42-REVIEW-FIX.md`'s prose. The two items above were
WARNING-level (present, correct, but formally unconfirmed by a human) rather than
defects — they routed this verification to `human_needed` rather than `passed` per the
decision tree, since both were genuinely open sign-off items rather than something a
grep or test could resolve. **Both were presented to the operator on 2026-07-30 and
approved without adjustment** — item 9 approved as documentation/cleanup note (same
treatment as item 5), and the existing DB UNIQUE constraint judged sufficient for the
concurrency-safety question. No code changes resulted. Status updated to `passed`.

---

_Verified: 2026-07-30T21:15:00Z_
_Verifier: Claude (gsd-verifier)_
