---
phase: 47
slug: provenance-foundation
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-17
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest.ini`: `asyncio_mode = auto`, `testpaths = tests pipeline/tests api/tests`) |
| **Config file** | `pytest.ini` (repo root, beside root `conftest.py`) |
| **Quick run command** | `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` |
| **Full suite command** | `./.venv/bin/python -m pytest` (from `.planning/config.json` `workflow.test_command`) |
| **Estimated runtime** | ~10s quick / ~180s full suite |

> **Invocation-shape constraint (CLAUDE.md):** the `TEST_DATABASE_URL` redirect lives in the
> repository-root `conftest.py`. Any command recorded here must be safe under explicit-path
> invocation — see the regression test `tests/test_pytest_isolation_invocation_shapes.py`.

> **Schema-application constraint:** every command below assumes migration `0026` has been
> applied to BOTH `DATABASE_URL` and `TEST_DATABASE_URL`. Plan 47-01 Task 3 owns that; running
> any DB-gated test before it will fail with `UndefinedTable` on `import_run`.

> **Intermediate-red constraint:** the schema rename is atomic (see 47-01
> `<intermediate_state_note>`). The full suite is expected RED from the end of 47-01 until 47-04
> and 47-05 complete. Per-task commands below are deliberately scoped so each proves what its
> task owns without importing modules a later wave still owns.

---

## Sampling Rate

- **After every task commit:** run that task's `<automated>` command from the map below
- **After every plan wave:**
  - wave 1–2: `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -q`
  - wave 3: `./.venv/bin/python -m pytest pipeline/tests -q` and `./.venv/bin/python -m pytest api/tests tests -q`
  - wave 4: `./.venv/bin/python -m pytest`
- **Before `/gsd-verify-work`:** full suite green, plus `./.venv/bin/python -m pytest api/tests -q` (explicit-path shape) and `tests/test_pytest_isolation_invocation_shapes.py`
- **Max feedback latency:** 15 seconds for the quick command, 180 seconds for the full suite

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | PROV-01, PROV-02 | — | N/A (checkpoint:decision — enum representation is a one-way door) | checkpoint | n/a — blocking human decision | n/a | ⬜ pending |
| 47-01-02 | 01 | 1 | PROV-01, PROV-02, PROV-03, PROV-04, PROV-06 | T-47-02 / T-47-03 / T-47-06 | Renamed table name lands in all three hardcoded lists in the same commit, so the leak tripwire keeps watching and `reset_to_fixture` keeps working; NOT NULL enum columns reject missing/out-of-vocabulary provenance at the storage boundary | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ❌ W0 (created by this task) | ⬜ pending |
| 47-01-03 | 01 | 1 | PROV-01, PROV-02, PROV-03, PROV-06 | T-47-01 | Confirm `alembic current` is `0025` and echo the resolved database name before destructive DDL | integration | `./.venv/bin/python -m pytest tests/test_pytest_isolation_invocation_shapes.py pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-02-01 | 02 | 2 | PROV-01, PROV-02, PROV-06 | T-47-06 | Ingest and resolve declare `pdf_pipeline`/`normalized`; a typo fails loudly at insert rather than storing a bad string | unit | `python3 -m compileall -q pipeline/commands/ingest.py pipeline/commands/resolve.py pipeline/__main__.py && ./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-02-02 | 02 | 2 | PROV-02, PROV-03, PROV-05 | T-47-07 | `method` derives from the branch actually taken, never from a caller-supplied argument — an operator cannot assert a higher-authority method than the code used | unit | `python3 -m compileall -q pipeline/commands/parse.py && ./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-02-03 | 02 | 2 | PROV-05, PROV-06 | T-47-08 | Both PDF-path tests monkeypatch `parse_with_llm`; the file never imports `anthropic`, so no billable/live API call escapes the suite | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-03-01 | 03 | 2 | PROV-03, PROV-04 | T-47-11 | PDF streaming stays an admin-gated primary-key fetch; `oyez_transcript_id` stays on the metadata response | unit | `python3 -m compileall -q api/services/arguments.py api/services/admin_arguments.py api/routers/admin.py && ./.venv/bin/python -c "import api.services.arguments, api.services.admin_arguments, api.routers.admin"` | ✅ | ⬜ pending |
| 47-03-02 | 03 | 2 | PROV-01, PROV-03 | T-47-10 / T-47-12 | Corpus detection reads a declared enum instead of a free-text string; the `exists()` form is preserved so 1:many runs cannot duplicate job rows | unit | `python3 -m compileall -q api/services/admin_jobs.py api/schemas/admin_jobs.py pipeline/commands/import_convokit.py && ./.venv/bin/python -c "import api.services.admin_jobs" && ./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-03-03 | 03 | 2 | PROV-03, PROV-04 | T-47-04 | No `source`/`method`/`external_id` field is added to any response model — provenance stays operator-facing (apolitical constraint) | unit | `python3 -m compileall -q api/schemas/utterance.py && ./.venv/bin/python -c "import api.main"` | ✅ | ⬜ pending |
| 47-04-01 | 04 | 3 | PROV-02, PROV-03 | T-47-13 / T-47-14 / T-47-15 | Commands target `pipeline/tests` so the rootdir redirect applies; collected test count must not drop, so a failing test cannot be deleted to go green | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_run.py pipeline/tests/test_parse.py pipeline/tests/test_ingest.py pipeline/tests/test_resolve.py -q` | ✅ | ⬜ pending |
| 47-04-02 | 04 | 3 | PROV-01, PROV-04, PROV-05 | T-47-14 / T-47-15 | Fixtures pin `source`/`method` to what the production writer actually stamps, so a fixture cannot assert an unreachable combination | integration | `./.venv/bin/python -m pytest pipeline/tests -q` | ✅ | ⬜ pending |
| 47-05-01 | 05 | 3 | PROV-01, PROV-03 | T-47-16 / T-47-14 | The `reset_to_fixture` patching harness in `test_admin_dev_routes.py` is preserved verbatim so no test executes the real reset against the shared dev DB | integration | `./.venv/bin/python -m pytest api/tests/test_admin_jobs_source.py api/tests/test_admin_jobs_stats.py api/tests/test_admin_jobs_service.py api/tests/test_admin_jobs_phase35.py api/tests/test_admin_dev_routes.py -q` | ✅ | ⬜ pending |
| 47-05-02 | 05 | 3 | PROV-03, PROV-04, PROV-06 | T-47-17 / T-47-18 | Public contract test gains explicit negative assertions that `strategy`/`source`/`method`/`external_id` are absent; table-count assertions must not be edited to pass | integration | `./.venv/bin/python -m pytest api/tests tests -q` | ✅ | ⬜ pending |
| 47-06-01 | 06 | 4 | PROV-01, PROV-02, PROV-04, PROV-05, PROV-06 | T-47-01 | Confirm the resolved database name and `alembic current` before a nine-table TRUNCATE; corpus pre-flight aborts before the truncate, not after | integration | `./.venv/bin/python -m pytest pipeline/tests/test_import_run_provenance.py -x -q` | ✅ | ⬜ pending |
| 47-06-02 | 06 | 4 | PROV-01…PROV-06 | T-47-02 / T-47-20 | Full suite run under both default and explicit-path invocation shapes; evidence recorded as real row values, not prose | integration | `./.venv/bin/python -m pytest` | ✅ | ⬜ pending |
| 47-06-03 | 06 | 4 | PROV-05 | T-47-19 | Operator searches the public page for `corpus`/`pdf_pipeline`/`rule_based`/`llm_corrective` and reports any hit rather than accepting it | checkpoint | n/a — blocking human verify | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Sampling continuity: no three consecutive tasks lack an `<automated>` verify. The only tasks
without one are 47-01-01 and 47-06-03, both checkpoints, and they are separated by twelve
automated tasks.

---

## Wave 0 Requirements

- [x] **PDF-path provenance fixture coverage** — RESEARCH.md flagged that all four `FIXTURE_SET`
      fixtures in `api/services/admin_dev.py` go through the corpus path only, so there is
      currently **zero** coverage proving `rule_based` / `llm_corrective`, and success criterion 4
      requires all three combinations. **Resolved by plan:** the gap is closed by
      `pipeline/tests/test_import_run_provenance.py` (created in 47-01 Task 2, extended in 47-02
      Task 3), which reuses the `pipeline/tests/test_parse.py::test_run_id_strategy` monkeypatch
      skeleton to drive a real `run_parse` down both branches without a live LLM call.
      `reset_to_fixture` is deliberately NOT extended — the PDF fixture it would need does not
      exist and creating one is out of scope. The composition is recorded in 47-06's
      `<d06_composition>` block and in `47-PROVENANCE-EVIDENCE.md`.
- [ ] `pipeline/tests/test_import_run_provenance.py` — new file, created by 47-01 Task 2. This is
      the ONLY Wave 0 test artifact this phase needs; every other verification command targets a
      file that already exists.

All other `<automated>` commands reference existing files — no further Wave 0 scaffolding.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Admin job list Source tag reads **corpus** for the four re-seeded fixture arguments | PROV-01 | The tag is rendered by the SvelteKit admin UI reading a derived API field; the derivation is unit-tested but its end-to-end rendering is not | 47-06 Task 3 step 2 — open the admin job list and confirm all four fixture jobs read `corpus` |
| Admin job detail parse stats still render | PROV-03 | Depends on the per-step `step="parse"` grain surviving through the API into a rendered card | 47-06 Task 3 step 3 |
| Public argument page renders and `is_corpus_sourced` behaves as before | PROV-04 | The derivation lives in a SvelteKit `+page.server.ts` load function that this phase deliberately does not modify or test | 47-06 Task 3 step 4 |
| No provenance vocabulary visible to a public visitor | PROV-01, PROV-02 | An automated check would have to render the full public page; the apolitical constraint is a judgment about what a visitor sees | 47-06 Task 3 step 5 — search the rendered page for `corpus`, `pdf_pipeline`, `rule_based`, `llm_corrective`; report any hit rather than accepting it |
| Live PDF ingest end-to-end stamping | PROV-02, PROV-06 | No PDF fixture exists in the repository; this requires an operator-supplied PDF | 47-06 Task 3 step 6 — optional; the two monkeypatched parse tests cover the same branches automatically |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 180s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
