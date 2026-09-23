# Deferred Items — Phase 47 (out of scope for 47-05)

## `tests/test_schema.py::test_no_create_all_in_codebase` false positive on `api/tests/test_phase44_descriptor_rename.py`

**Found during:** 47-05 Task 2, running the full `api/tests tests` suite together for
the first time (the previous single collection error in `api/tests/test_admin_dev_routes.py`
had always aborted collection before this test could run alongside
`test_phase44_descriptor_rename.py` in the same process).

**Root cause:** `test_no_create_all_in_codebase`'s `search_dirs` list is `[api/, alembic/,
pipeline/]` — its docstring claims this "excludes test files," but `api/tests/` is a
subdirectory of `api/` and is walked by the same `rglob("*.py")`. `api/tests/test_phase44_descriptor_rename.py`
(created in Phase 44, commit `03b235660`) contains the literal source string
`"Base.metadata.create_all"` inside its OWN assertion text (a test that itself guards against
`create_all` appearing in a Svelte/JS resolve-card component), which trips the substring
match.

**Why not out-of-scope after all:** Pre-existing since Phase 44 (long before Phase 47/47-05),
and not caused by any file in this plan's `files_modified` list. However, this plan's own
acceptance criteria requires `./.venv/bin/python -m pytest api/tests tests -q` to exit 0 with
zero collection errors, and this pre-existing bug was blocking that gate the first time the
two directories were ever collected together in one process. The fix itself is a minimal,
well-scoped restoration of `test_no_create_all_in_codebase`'s own documented intent ("excludes
test files") — skip nested `tests/` subdirectories during the `rglob` walk — rather than an
architectural change, so it was applied here under Rule 1 (auto-fix bugs) / Rule 3
(auto-fix blocking issues).

**Status:** FIXED in this plan (47-05) — see 47-05-SUMMARY.md for the commit.

---

## `api/tests/test_migration_0022_person_name_authority.py`'s downgrade fixture assumed an empty database

**Found during:** 47-05 Task 2, running the full `api/tests tests` suite. `_baseline_at_0021`
tried to downgrade past migration 0026, whose `downgrade()` recreates `pipeline_runs` empty
and re-adds `utterances.pipeline_run_id`'s FK against it — this raised
`ForeignKeyViolationError` whenever `api/tests/test_admin_dev_routes.py`'s corpus-reset tests
(which deliberately leave 4 fixture arguments + their `import_run`/`utterances` rows behind —
that endpoint's whole purpose is to seed, not clean up after itself) ran earlier in the same
session and left real rows in `utterances`/`import_run`.

**Status:** FIXED in this plan (47-05) — `_baseline_at_0021` now truncates `utterances,
import_run CASCADE` (scotus_test only, never touching migration 0026 itself or
`DATABASE_URL`) before downgrading, whenever `import_run` currently exists. See
47-05-SUMMARY.md for the commit. Logged here for visibility since it's a cross-file test
interaction, not a simple identifier rename.

---

## `api/tests/test_phase44_argument_role_roundtrip.py` fails under the bare full-suite
`pytest -q` (testpaths order `tests pipeline/tests api/tests`) — pre-existing, unrelated to
Phase 47

**Found during:** 47-05's final full bare-suite `pytest -q` integration check
(`.planning/phases/47-provenance-foundation/47-05-PLAN.md`'s `<upstream_state>` explicitly
asks for this to be run and reported honestly).

**Symptom:** 4 parametrized `test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum`
cases fail with `AssertionError: assert False` on `isinstance(body.side, SideEnum)`, even
though `body.side == SideEnum(value)` passes on the line immediately above.

**Root cause:** `tests/test_admin_router.py` intentionally `del sys.modules[...]`s and
`importlib.import_module("api.main")`s every `api.*` module mid-suite (a documented pattern —
`api/tests/conftest.py`'s own docstring names this exact test and explains why several
fixtures elsewhere use function-local imports to avoid it). `pytest.ini`'s
`testpaths = tests pipeline/tests api/tests` collects `tests/` (and therefore
`test_admin_router.py`) before `api/tests/`, so by the time
`test_phase44_argument_role_roundtrip.py`'s tests run, `api.models.models.SideEnum` has been
reimported as a NEW class object. `ResolveRowUpdate` (imported at MODULE level in that test
file, i.e. at collection time, before the reimport happens) is bound to the OLD `SideEnum`
class for its Pydantic field, while the test body's own `from api.models.models import SideEnum`
(a function-local import, executed at test-run time, after the reimport) resolves to the NEW
class object — two distinct class objects with identical values fail `isinstance`.

**Reproduces in isolation**, confirming it has nothing to do with any file this plan touched:
```
./.venv/bin/python -m pytest tests/test_admin_router.py api/tests/test_phase44_argument_role_roundtrip.py -q
# 4 failed, 16 passed
```
Neither file references `PipelineRun`/`ImportRun`/`import_run` at all. `tests/test_admin_router.py`
dates to Phase 5 (`01faf02ee`); `api/tests/test_phase44_argument_role_roundtrip.py` dates to
Phase 44 (`bbaac48d5`) — both long before Phase 47. It does NOT reproduce when running
`api/tests tests -q` with explicit paths (as Task 2's own acceptance criteria does) because
pytest then collects in command-line order (`api/tests` before `tests`), so the reimport
happens AFTER this file's tests already ran.

**Status:** open — out of scope for 47-05 (neither file is in this plan's `files_modified`,
and the underlying fix is either changing `test_admin_router.py`'s reimport strategy or
switching `test_phase44_argument_role_roundtrip.py`'s `ResolveRowUpdate` import to be
function-local, both unrelated to the provenance/import_run conversion this phase is about).
Candidate for a follow-up plan or `/gsd-review-backlog`.
