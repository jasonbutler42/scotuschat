# Phase 47 — Provenance Evidence (D-06 three-combination verification)

This document records the actual rows read back after re-seeding the dev database through the
real `reset_to_fixture` path, and after driving the two `pdf_pipeline` legs through the real
`pipeline.commands.parse.run_parse` writer. Every value below is copied verbatim from a live
query or test run output — no value has been rounded, paraphrased, or inferred.

**Reminder (CLAUDE.md / apolitical framing constraint):** `source` / `method` / `external_id`
are operator-facing lineage only. Nothing recorded here is, or should be, surfaced on the public
site as a quality, credibility, or trust signal to end users.

---

## corpus/direct (live re-seed)

**Timestamp (UTC):** 2026-08-18T14:05:08.016279+00:00
**Resolved database:** `postgresql+asyncpg://scotus:***@172.26.32.1:5432/scotus` (masked; host `172.26.32.1`, db `scotus`)
**Alembic revision confirmed before and after the reseed:** `0026 (head)`

**Method:** A scratchpad script (`reset_and_readback.py`) opened a real `AsyncSession` against
`DATABASE_URL` and called `api.services.admin_dev.reset_to_fixture(db)` directly — the real
production function, no HTTP server, no hand-rolled substitute. `reset_to_fixture` completed in
**77.2s**. Provenance was then read back with raw SQL off the live rows in a fresh session (to
avoid any identity-map staleness), joining `arguments` to `import_run` — no inference, no ORM
convenience property, the query reads the columns directly.

### Pre-seed row counts (captured before the reseed)

| Table | Count |
|---|---|
| arguments | 4 |
| utterances | 0 |
| import_run | 0 |
| cases | 4 |
| people | 36 |
| admin_jobs | 4 |
| court_tenures | 0 |
| case_arguments | 4 |
| argument_participants | 38 |

### Post-reseed row counts (exact)

| Table | Count |
|---|---|
| arguments | 4 |
| utterances | 1001 |
| import_run | 4 |
| cases | 4 |
| people | 36 |
| admin_jobs | 4 |
| court_tenures | 0 |
| case_arguments | 4 |
| argument_participants | 38 |

### `reset_to_fixture` return payload — four fixtures seeded

| conversation_id | case_name | role | argument_id | argument_status | admin_job_status |
|---|---|---|---|---|---|
| 15169 | Baltimore & Ohio Railroad Company v. United States | Complexity | 1771 | pipeline | paused |
| 13015 | Archawski v. Hanioti | Draft | 1772 | draft | completed |
| 18897 | Anderson v. Liberty Lobby, Inc. | Published | 1773 | published | completed |
| 22372 | Abbott v. United States | Mid-pipeline | 1774 | pipeline | running |

### Per-term import stats (from the run log)

| Term | Arguments created | Cases created | Utterances created | Stage-direction utterances | People created | People reused | Unattributed speakers skipped | Bench tenure mismatches | Conversations errored | Utterance rows errored | Docket/question conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1966 | 1 | 1 | 467 | 13 | 17 | 0 | 1 | 8 | 0 | 0 | 0 |
| 1955 | 1 | 1 | 164 | 3 | 4 | 1 | 0 | 3 | 0 | 0 | 0 |
| 1985 | 1 | 1 | 157 | 0 | 6 | 1 | 0 | 5 | 0 | 0 | 0 |
| 2010 | 1 | 1 | 197 | 0 | 9 | 0 | 1 | 6 | 0 | 0 | 0 |

Every term reported 0 conversations errored, 0 utterance rows errored, 0 docket/question
conflicts, 0 speakers flagged.

> **Note on `bench_tenure_mismatch` warnings:** these are pre-existing, D-03 flag-only behavior
> (`court_tenures` is 0 in this fixture set — no `CourtTenure` rows exist to match against). They
> are observed here for completeness but are unrelated to Phase 47 and are not a Phase 47 defect.

### `import_run` rows for the four `FIXTURE_SET` conversation ids (read directly off the live rows)

Query (no join-based inference beyond `arguments.id = import_run.argument_id`, every column
selected directly):

```sql
SELECT
    a.oyez_transcript_id AS conversation_id,
    a.id AS argument_id,
    r.id AS import_run_id,
    r.step,
    r.status,
    r.source,
    r.method,
    r.external_id,
    r.pdf_path,
    r.pdf_url
FROM arguments a
JOIN import_run r ON r.argument_id = a.id
WHERE a.oyez_transcript_id IN ('15169', '13015', '18897', '22372')
ORDER BY a.oyez_transcript_id, r.id
```

| conversation_id | argument_id | import_run_id | step | status | source | method | external_id | pdf_path | pdf_url |
|---|---|---|---|---|---|---|---|---|---|
| 13015 | 1772 | 2 | parse | completed | corpus | direct | 13015 | NULL | NULL |
| 15169 | 1771 | 1 | parse | completed | corpus | direct | 15169 | NULL | NULL |
| 18897 | 1773 | 3 | parse | completed | corpus | direct | 18897 | NULL | NULL |
| 22372 | 1774 | 4 | parse | completed | corpus | direct | 22372 | NULL | NULL |

Every row reads `source = 'corpus'`, `method = 'direct'`, `external_id` equal to the conversation
id, `pdf_path IS NULL`, `pdf_url IS NULL` — exactly as PROV-05 (reframed by D-03) requires.
`Argument.oyez_transcript_id` for each of the four rows still equals its `external_id` (both are
the same conversation id) — the `import_run.external_id` dual-write did not relocate the corpus
dedup key or the public API field.

### Corroborating integrity assertions (same run, live dev database)

| Assertion | Query | Result |
|---|---|---|
| Argument rows matching the four `FIXTURE_SET` conversation ids | `SELECT count(*) FROM arguments WHERE oyez_transcript_id IN ('15169','13015','18897','22372')` | **4** (re-import created no duplicate `Argument`) |
| Orphan utterances (no matching `import_run`) | `SELECT count(*) FROM utterances u LEFT JOIN import_run r ON u.import_run_id = r.id WHERE r.id IS NULL` | **0** |
| `strategy` column existence, `utterances` and `import_run` | `SELECT table_name, column_name FROM information_schema.columns WHERE table_name IN ('utterances','import_run') AND column_name = 'strategy'` | **zero rows returned** — the column is gone from both tables |

---

## pdf_pipeline/rule_based

**Vehicle:** `pipeline/tests/test_import_run_provenance.py::test_parse_rule_based_stamps_pdf_pipeline_rule_based`
**Database:** `TEST_DATABASE_URL` (`scotus_test`), via the `async_session` fixture (rolled back
after the test) — never `DATABASE_URL`.
**Monkeypatch that selected this branch:** `pipeline.commands.parse.parse_with_llm` is replaced
with `_raise_llm_unavailable`, an async function that unconditionally
`raise RuntimeError("LLM not available in unit tests")`. `pipeline.commands.parse.extract_pages`
is also monkeypatched to a minimal synthetic transcript (`_mock_extract_pages`) so no real PDF is
ever opened, and `pipeline.commands.parse.get_session` is monkeypatched to the test's own
session. The real `pipeline.commands.parse.run_parse` writer is invoked unmodified — the LLM
corrective pass runs, raises, and `run_parse`'s own branch logic (not the test) decides the
resulting method.

**Test run output:**

```
pipeline/tests/test_import_run_provenance.py::test_parse_rule_based_stamps_pdf_pipeline_rule_based PASSED
```

**Resulting row values, asserted directly in the test body against the newly created
`ImportRun`:**

| Field | Value |
|---|---|
| `source` | `ImportSource.PDF_PIPELINE` (`"pdf_pipeline"`) |
| `method` | `ImportMethod.RULE_BASED` (`"rule_based"`) |

A companion assertion in the same file (`test_pdf_pipeline_run_populates_pdf_path`, same
monkeypatch) confirms the `pdf_pipeline` leg's `pdf_path` carries forward from the source ingest
run (`new_run.pdf_path == source_run.pdf_path`, both non-null) and `external_id IS NULL` — the
inverse of the corpus leg's null-PDF / non-null-external_id shape, as the vocabulary intends.
`test_parse_utterances_link_to_import_run` (same monkeypatch) confirms every resulting
`Utterance` row has `import_run_id == new_run.id` and `not hasattr(row, "strategy")`.

---

## pdf_pipeline/llm_corrective

**Vehicle:** `pipeline/tests/test_import_run_provenance.py::test_parse_llm_success_stamps_pdf_pipeline_llm_corrective`
**Database:** `TEST_DATABASE_URL` (`scotus_test`), via the `async_session` fixture (rolled back
after the test) — never `DATABASE_URL`.
**Monkeypatch that selected this branch:** `pipeline.commands.parse.parse_with_llm` is replaced
with `_return_llm_success`, an async function that returns a valid `ParseResponse` (two
`ParsedUtterance` rows, no exception). Same `extract_pages` / `get_session` monkeypatches as the
`rule_based` leg above. No live Anthropic API call is made anywhere in this test file — the
module never imports `anthropic` (confirmed by
`grep -c anthropic pipeline/tests/test_import_run_provenance.py` returning 0, per T-47-08).

**Test run output:**

```
pipeline/tests/test_import_run_provenance.py::test_parse_llm_success_stamps_pdf_pipeline_llm_corrective PASSED
```

**Resulting row values, asserted directly in the test body against the newly created
`ImportRun`:**

| Field | Value |
|---|---|
| `source` | `ImportSource.PDF_PIPELINE` (`"pdf_pipeline"`) |
| `method` | `ImportMethod.LLM_CORRECTIVE` (`"llm_corrective"`) |

The method is derived from the branch `pipeline.commands.parse.run_parse` actually took (the LLM
pass returned, rather than raised) — never from a caller-supplied argument (T-47-07). No test in
this file passes `method=` as an argument to `run_parse`; the value is read back from the row
`run_parse` itself wrote.

**`test_d06_all_three_combinations_present`** (same file) drives one corpus import plus both
parse branches within a single test/transaction and asserts the distinct `(source, method)`
pairs present in `import_run` include exactly `(corpus, direct)`, `(pdf_pipeline, rule_based)`,
and `(pdf_pipeline, llm_corrective)` — all three combinations reachable from code, in one place.
This test also passed.

---

## D-06 composition

D-06 requires the verification to exercise `corpus/direct`, `pdf_pipeline/rule_based` and
`pdf_pipeline/llm_corrective`. RESEARCH established that the existing `reset_to_fixture` tool
cannot supply the last two: all four `FIXTURE_SET` entries go through `run_import_convokit`, and
no PDF fixture exists anywhere under `pipeline/tests/`. Extending `reset_to_fixture` was
explicitly rejected — the PDF fixture it would need does not exist and creating one is not in
this phase's scope.

The verification is therefore a composition of two real-writer runs, recorded together as one
piece of evidence:

| Combination | Vehicle | Database |
|-------------|---------|----------|
| `corpus/direct` | `reset_to_fixture` re-seeding all four `FIXTURE_SET` conversations through `run_import_convokit` | dev (`DATABASE_URL`) |
| `pdf_pipeline/rule_based` | `test_parse_rule_based_stamps_pdf_pipeline_rule_based` driving a real `run_parse` with `parse_with_llm` monkeypatched to raise | test (`TEST_DATABASE_URL`) |
| `pdf_pipeline/llm_corrective` | `test_parse_llm_success_stamps_pdf_pipeline_llm_corrective` driving a real `run_parse` with `parse_with_llm` monkeypatched to return a valid response | test (`TEST_DATABASE_URL`) |

In every case the row is written by the production writer, never hand-inserted. That is what
makes this evidence rather than a restatement of the plan.

**Standing note for a future phase:** `.planning/FIXTURES.md`'s four-fixture set remains 100%
corpus-sourced. PDF-path (`pdf_pipeline`) coverage lives entirely in the `pipeline/tests` suite,
not in the reset tool — no PDF fixture file exists in the repository for `reset_to_fixture` to
consume. A future phase that wants live-database `pdf_pipeline` rows (beyond the monkeypatched
test coverage above) will need to add a PDF fixture and extend `reset_to_fixture` accordingly;
that work is out of scope for Phase 47.

---

## Full suite state (Task 2 gate)

**Command:** `./.venv/bin/python -m pytest` (project's configured full-suite command, from
`.planning/config.json` `workflow.test_command`)

**Result:** **1039 passed, 6 skipped, 5 xfailed, 4 failed, zero collection errors.**

This is NOT a fully green suite, and this document does not describe it as one. The 4 failures
are all in
`api/tests/test_phase44_argument_role_roundtrip.py::test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum`
(parametrized over `UNKNOWN`/`PETITIONER`/`RESPONDENT`/`AMICUS`). They are **pre-existing and
unrelated to Phase 47**:

- They reproduce identically at the pre-phase commit `8e1c6a33b`.
- They pass when that file runs in isolation.
- Phase 47 touched neither `test_phase44_argument_role_roundtrip.py` nor the `SideEnum`
  definition.
- Root cause (documented in `.planning/phases/47-provenance-foundation/deferred-items.md` and
  `.planning/WINDOWS.md` entry #5): a `SideEnum` module-identity bug caused by
  `tests/test_admin_router.py`'s intentional mid-suite module reimport interacting with
  `pytest.ini`'s `testpaths` collection order (`tests` before `api/tests`).

This gap is tracked, out of scope for Phase 47, and is not treated as a regression introduced by
this phase's work.

**Explicit-path invocation shape** (the exact class of failure that wiped the shared dev
database twice during Phase 45, D-03):

- `./.venv/bin/python -m pytest api/tests -q` — exits 0. **718 passed, 6 skipped**, no failures
  (confirms the `test_phase44_argument_role_roundtrip` failure surfaces only under `testpaths`
  collection order, not this explicit-path shape).
- `./.venv/bin/python -m pytest tests/test_pytest_isolation_invocation_shapes.py -q` — **3
  passed** (all 3 parametrized shapes).

**Retired-name hygiene sweep:**
`grep -rn "PipelineRun\|PipelineRunStatus\|pipeline_run_id\|pipeline_runs\|PIPELINE_RUN_STRATEGY" api pipeline tests conftest.py --include=*.py`
returns only the two deliberately-preserved, documented exceptions already recorded in
47-05-SUMMARY.md:

- `api/tests/test_migration_0022_person_name_authority.py` — pinned to Alembic revision
  0021/0022, both of which predate migration 0026's rename; at that revision the table is
  genuinely still called `pipeline_runs`, so renaming this reference would break the very
  revision the test exercises.
- `tests/test_schema.py` — its own live-schema absence assertion, which must name the retired
  string (`'pipeline_runs' not in actual_tables`) in order to assert that it is gone.

No other surviving reference exists anywhere in `api`, `pipeline`, `tests`, or `conftest.py`.

**Build check:** `python3 -m compileall -q pipeline api scripts tests alembic` exits 0.

---

*Phase: 47-provenance-foundation*
*Recorded: 2026-08-18*

