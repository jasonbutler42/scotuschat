---
status: complete
phase: 47-provenance-foundation
source: 47-01-SUMMARY.md, 47-02-SUMMARY.md, 47-03-SUMMARY.md, 47-04-SUMMARY.md, 47-05-SUMMARY.md, 47-06-SUMMARY.md
started: 2026-08-18T19:02:31Z
updated: 2026-08-18T20:14:04Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running API/frontend process. From a cold start, `alembic upgrade head` brings a fresh database to 0026 with the `import_run` table and the `import_source`/`import_method` enums present, the fixture re-seed completes, and a primary read returns live utterances resolved through `import_run_id` — no errors, no missing-table or missing-enum failure, no stale `pipeline_runs` reference.
result: pass
note: injected cold-start smoke test (migration + seed paths touched)

### 2. D-03 Pytest-Isolation Intermediate RED Was Expected Sequencing
expected: During 47-01 the D-03 regression test failed all 3 parametrized shapes; during 47-03 it passed 2 of 3; 47-05 closed it at 3/3. Confirm the intermediate RED was expected wave sequencing, not a regression that should have blocked those plans.
result: pass
coverage_ids: D5 (47-01), D16 (47-03)

### 3. Four Pre-existing test_phase44 Failures Are Out of Scope
expected: The bare full-suite `pytest` reports 4 failures in `api/tests/test_phase44_argument_role_roundtrip.py` — a pre-existing `SideEnum` module-identity bug from Phase 5/44 that reproduces identically at the pre-phase commit `8e1c6a33b`, passes in isolation, and touches no file this phase modified. Confirm accepting these as out of scope for Phase 47 (logged in WINDOWS.md #5 and deferred-items.md) rather than phase-blocking.
result: pass
coverage_ids: D4 (47-05), E4 (47-06)

### 4. import_run table + import_source/import_method PG enums created by migration 0026, applied to both DATABASE_URL and TEST_DATABASE_URL
expected: import_run table + import_source/import_method PG enums created by migration 0026, applied to both DATABASE_URL and TEST_DATABASE_URL
result: pass
source: automated
coverage_id: D1 (47-01)

### 5. Corpus importer stamps source=CORPUS/method=DIRECT/external_id at row creation; pdf_path/pdf_url stay NULL; Argument.oyez_transcript_id unchanged
expected: Corpus importer stamps source=CORPUS/method=DIRECT/external_id at row creation; pdf_path/pdf_url stay NULL; Argument.oyez_transcript_id unchanged
result: pass
source: automated
coverage_id: D2 (47-01)

### 6. Corpus reimport is idempotent on Argument; empty-utterance corpus import still writes a provenance-carrying run row (PROV-05 empty/adjacency edges)
expected: Corpus reimport is idempotent on Argument; empty-utterance corpus import still writes a provenance-carrying run row (PROV-05 empty/adjacency edges)
result: pass
source: automated
coverage_id: D3 (47-01)

### 7. import_run.source/method reject NULL at the storage boundary (T-47-06)
expected: import_run.source/method reject NULL at the storage boundary (T-47-06)
result: pass
source: automated
coverage_id: D4 (47-01)

### 8. Ingest stamps source=pdf_pipeline/method=normalized; pdf_path/pdf_url populated
expected: Ingest stamps source=pdf_pipeline/method=normalized; pdf_path/pdf_url populated
result: pass
source: automated
coverage_id: D6 (47-02)

### 9. Resolve stamps source=pdf_pipeline/method=normalized; still refuses a non-parse source run
expected: Resolve stamps source=pdf_pipeline/method=normalized; still refuses a non-parse source run
result: pass
source: automated
coverage_id: D7 (47-02)

### 10. Parse stamps source=pdf_pipeline plus exactly one of rule_based/llm_corrective, derived from whether parse_with_llm returned or raised (T-47-07), never caller-supplied
expected: Parse stamps source=pdf_pipeline plus exactly one of rule_based/llm_corrective, derived from whether parse_with_llm returned or raised (T-47-07), never caller-supplied
result: pass
source: automated
coverage_id: D8 (47-02)

### 11. Utterances link via import_run_id with no per-row strategy column
expected: Utterances link via import_run_id with no per-row strategy column
result: pass
source: automated
coverage_id: D9 (47-02)

### 12. pdf_path carries forward from the source ingest run on pdf_pipeline parse rows; external_id stays NULL
expected: pdf_path carries forward from the source ingest run on pdf_pipeline parse rows; external_id stays NULL
result: pass
source: automated
coverage_id: D10 (47-02)

### 13. All three D-06 combinations (corpus/direct, pdf_pipeline/rule_based, pdf_pipeline/llm_corrective) reachable from code within one transaction
expected: All three D-06 combinations (corpus/direct, pdf_pipeline/rule_based, pdf_pipeline/llm_corrective) reachable from code within one transaction
result: pass
source: automated
coverage_id: D11 (47-02)

### 14. No live Anthropic API call from the test suite
expected: No live Anthropic API call from the test suite
result: pass
source: automated
coverage_id: D12 (47-02)

### 15. Public utterance read path selects the latest completed parse run deterministically by MAX(import_run.id), unchanged step/status semantics
expected: Public utterance read path selects the latest completed parse run deterministically by MAX(import_run.id), unchanged step/status semantics
result: pass
source: automated
coverage_id: D13 (47-03)

### 16. Corpus-vs-pdf Source tag derived from ImportRun.source == ImportSource.CORPUS at both call sites (get_job, list_jobs); PIPELINE_RUN_STRATEGY deleted repo-wide
expected: Corpus-vs-pdf Source tag derived from ImportRun.source == ImportSource.CORPUS at both call sites (get_job, list_jobs); PIPELINE_RUN_STRATEGY deleted repo-wide
result: pass
source: automated
coverage_id: D14 (47-03)

### 17. Public UtteranceResponse carries import_run_id, no strategy/source/method/external_id field; FastAPI app imports cleanly; no frontend file needed modification
expected: Public UtteranceResponse carries import_run_id, no strategy/source/method/external_id field; FastAPI app imports cleanly; no frontend file needed modification
result: pass
source: automated
coverage_id: D15 (47-03)

### 18. The four PDF-lifecycle pipeline test files (test_import_run.py, test_parse.py, test_ingest.py, test_resolve.py) pass against the import_run schema; test_pipeline_run.py renamed to test_import_run.py with git history preserved
expected: The four PDF-lifecycle pipeline test files (test_import_run.py, test_parse.py, test_ingest.py, test_resolve.py) pass against the import_run schema; test_pipeline_run.py renamed to test_import_run.py with git history preserved
result: pass
source: automated
coverage_id: D1 (47-04)

### 19. test_run_id_strategy renamed to test_run_id_and_method; the per-utterance strategy assertion moved to the parent run's ImportMethod assertion, not deleted
expected: test_run_id_strategy renamed to test_run_id_and_method; the per-utterance strategy assertion moved to the parent run's ImportMethod assertion, not deleted
result: pass
source: automated
coverage_id: D2 (47-04)

### 20. The entire pipeline/tests suite (244 tests) collects and passes against the import_run schema; no test was deleted to achieve this
expected: The entire pipeline/tests suite (244 tests) collects and passes against the import_run schema; no test was deleted to achieve this
result: pass
source: automated
coverage_id: D3 (47-04)

### 21. Standing assertion guards Argument.oyez_transcript_id after corpus import; _write_corpus_fixture/_args/_scoped_args helper names and signatures unchanged (test_import_run_provenance.py depends on them)
expected: Standing assertion guards Argument.oyez_transcript_id after corpus import; _write_corpus_fixture/_args/_scoped_args helper names and signatures unchanged (test_import_run_provenance.py depends on them)
result: pass
source: automated
coverage_id: D4 (47-04)

### 22. Full-suite collection confirms exactly one remaining collection error (api/tests/test_admin_dev_routes.py, owned by 47-05) -- no new collection errors introduced by this plan's changes
expected: Full-suite collection confirms exactly one remaining collection error (api/tests/test_admin_dev_routes.py, owned by 47-05) -- no new collection errors introduced by this plan's changes
result: pass
source: automated
coverage_id: D5 (47-04)

### 23. The five admin-jobs and dev-reset API test files (test_admin_jobs_source.py, test_admin_jobs_stats.py, test_admin_jobs_service.py, test_admin_jobs_phase35.py, test_admin_dev_routes.py) pass against the import_run schema, with corpus-vs-pdf fixtures established via the declared ImportRun.source enum rather than a strategy string
expected: The five admin-jobs and dev-reset API test files (test_admin_jobs_source.py, test_admin_jobs_stats.py, test_admin_jobs_service.py, test_admin_jobs_phase35.py, test_admin_dev_routes.py) pass against the import_run schema, with corpus-vs-pdf fixtures established via the declared ImportRun.source enum rather than a strategy string
result: pass
source: automated
coverage_id: D1 (47-05)

### 24. The remaining eight API test files and the two root schema-contract test files pass against the import_run schema; schema-contract files name import_run with unchanged table counts and gain standing ImportSource/ImportMethod exhaustiveness assertions; the public utterance contract test proves no provenance field is exposed
expected: The remaining eight API test files and the two root schema-contract test files pass against the import_run schema; schema-contract files name import_run with unchanged table counts and gain standing ImportSource/ImportMethod exhaustiveness assertions; the public utterance contract test proves no provenance field is exposed
result: pass
source: automated
coverage_id: D2 (47-05)

### 25. tests/test_pytest_isolation_invocation_shapes.py (D-03 regression, CLAUDE.md-named) -- all 3 parametrized invocation shapes now pass, closing the gap 47-01/47-03 left open
expected: tests/test_pytest_isolation_invocation_shapes.py (D-03 regression, CLAUDE.md-named) -- all 3 parametrized invocation shapes now pass, closing the gap 47-01/47-03 left open
result: pass
source: automated
coverage_id: D3 (47-05)

### 26. reset_to_fixture (real production writer, real AsyncSession, no HTTP server) re-seeds the dev database; every import_run row for the four FIXTURE_SET conversation ids reads source=corpus/method=direct/external_id=<conversation_id>/pdf_path IS NULL/pdf_url IS NULL, read directly off the live rows with no join beyond arguments.id=import_run.argument_id
expected: reset_to_fixture (real production writer, real AsyncSession, no HTTP server) re-seeds the dev database; every import_run row for the four FIXTURE_SET conversation ids reads source=corpus/method=direct/external_id=<conversation_id>/pdf_path IS NULL/pdf_url IS NULL, read directly off the live rows with no join beyond arguments.id=import_run.argument_id
result: pass
source: automated
coverage_id: E1 (47-06)

### 27. Integrity properties across the re-seeded database: 0 orphan utterances, 0 strategy columns on utterances/import_run
expected: Integrity properties across the re-seeded database: 0 orphan utterances, 0 strategy columns on utterances/import_run
result: pass
source: automated
coverage_id: E2 (47-06)

### 28. pipeline.commands.parse.run_parse stamps pdf_pipeline/rule_based when parse_with_llm raises, and pdf_pipeline/llm_corrective when it returns -- method derived from the branch actually taken, never caller-supplied (T-47-07)
expected: pipeline.commands.parse.run_parse stamps pdf_pipeline/rule_based when parse_with_llm raises, and pdf_pipeline/llm_corrective when it returns -- method derived from the branch actually taken, never caller-supplied (T-47-07)
result: pass
source: automated
coverage_id: E3 (47-06)

## Summary

total: 28
passed: 28
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
