# Deferred Items — Phase 26 (arguments-admin)

Out-of-scope discoveries logged during plan execution (SCOPE BOUNDARY rule —
not fixed here, tracked for later triage).

## 26-01

- **Pre-existing full-suite test failures, unrelated to this plan's files:**
  `api/tests/test_arguments.py::test_get_utterances_returns_404_for_unknown_argument`,
  `api/tests/test_people.py::test_get_person`,
  `api/tests/test_people.py::test_get_person_404`
  fail with `RuntimeError: Database session factory is not initialised —
  lifespan may not have completed startup` when the entire `api/tests/`
  directory is run together (`pytest api/tests -q`). This reproduces without
  any changes from this plan — it is a pre-existing test-ordering/lifespan
  issue affecting `test_arguments.py` and `test_people.py`, neither of which
  this plan modifies. The plan's own verification command (scoped to
  `test_admin_arguments_service.py`, `test_admin_arguments_routes.py`,
  `test_admin_jobs_service.py`) passes cleanly (24 passed, 20 skipped).
