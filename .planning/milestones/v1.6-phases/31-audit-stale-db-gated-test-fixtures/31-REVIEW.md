---
phase: 31-audit-stale-db-gated-test-fixtures
reviewed: 2026-07-13T17:50:04Z
depth: standard
files_reviewed: 25
files_reviewed_list:
  - api/core/config.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/tests/conftest.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_dashboard_stats.py
  - api/tests/test_admin_jobs_list.py
  - api/tests/test_admin_jobs_phase25.py
  - api/tests/test_admin_jobs_service.py
  - api/tests/test_admin_jobs_source.py
  - api/tests/test_admin_jobs_stats.py
  - api/tests/test_admin_people_phase25.py
  - api/tests/test_argument_oyez_field.py
  - api/tests/test_arguments.py
  - api/tests/test_isolation_survives_inner_commit.py
  - api/tests/test_people.py
  - pipeline/__main__.py
  - pipeline/parser/state_machine.py
  - pipeline/tests/conftest.py
  - pipeline/tests/test_ingest.py
  - pipeline/tests/test_parse.py
  - pipeline/tests/test_resolve.py
  - pipeline/tests/test_seed_aliases.py
  - scripts/cleanup_leaked_test_rows.py
  - scripts/provision_test_db.py
  - tests/conftest.py
findings:
  critical: 2
  warning: 3
  info: 0
  total: 5
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-07-13T17:50:04Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

The core Phase 31 deliverables — the `TEST_DATABASE_URL` redirect in `tests/conftest.py`, the dev-DB leak-detection `pytest_sessionstart`/`pytest_sessionfinish` guard, `scripts/provision_test_db.py`, and `scripts/cleanup_leaked_test_rows.py` — are well-reasoned and internally consistent. I verified the collection-order assumption the isolation mechanism depends on (`pytest.ini`'s `testpaths = tests pipeline/tests api/tests` really does put `tests/` first, so `tests/conftest.py`'s module-level `os.environ["DATABASE_URL"]` redirect executes before `api/tests` or `pipeline/tests` import any production module) — that part of the design holds up.

However, one of this phase's own signature fixes — the "Phase 31 fix: refresh the stale identity-map object after a `synchronize_session=False` bulk update" pattern applied to `publish_argument`, `unpublish_argument`, and `approve_job` — was **not** applied to `resolve_job`, which has the identical bug and is reachable from a live API endpoint with no test coverage of the affected field. I also found a pre-existing, narrow but real data-loss/misattribution bug in the rule-based parser's inline-stage-direction-on-a-continuation-line path, which is in-scope per the file list. Additionally, the `_db_configured()` placeholder guard is copy-pasted verbatim into over a dozen files instead of being centralized.

## Critical Issues

### CR-01: `resolve_job` returns a stale `AdminJobResponse` with the pre-resolve status (missed the Phase 31 refresh fix)

**File:** `api/services/admin_jobs.py:418-537` (bug manifests at the `await db.commit()` / re-select on line 533-536); consumed directly by `api/routers/admin.py:522-539`

**Issue:** `publish_argument`, `unpublish_argument`, and `approve_job` in this same phase were each given an explicit `await db.refresh(...)` after their `update(...).execution_options(synchronize_session=False)` + `commit()`, with a comment explaining exactly why: the ORM object loaded earlier in the same session (via `get_job`/`select(Argument)...`) is never synced by a Core-level bulk `UPDATE` with `synchronize_session=False`, and `AsyncSessionLocal` is configured with `expire_on_commit=False` (`api/core/database.py:44-47`), so `commit()` does not force a refresh either. `resolve_job` has the exact same shape of bug and was not fixed:

```python
job = await get_job(db, job_id)          # loads AdminJob into the identity map, status=PAUSED
...
await db.execute(
    update(AdminJob)
    .where(AdminJob.id == job_id)
    .values(status=AdminJobStatus.COMPLETED)
    .execution_options(synchronize_session=False)
)
...
await db.commit()

# Reload and return the updated job
updated = await get_job(db, job_id)       # re-SELECTs the SAME identity-mapped
return updated                             # object -> job.status is STILL PAUSED
```

`get_job`'s internal `select(AdminJob).where(AdminJob.id == job_id)` returns the *same Python object* already in the session's identity map (SQLAlchemy does not overwrite non-expired attributes from a fresh row unless `populate_existing()` is used, and `expire_on_commit=False` means `commit()` never expires it either). The router (`api/routers/admin.py:522-539`) returns this object directly as `AdminJobResponse`:

```python
updated_job = await jobs_service.resolve_job(db, job_id, body.matches)
...
return updated_job  # type: ignore[return-value]
```

So `POST /api/admin/jobs/{job_id}/resolve` responds with `"status": "paused"` even though the job was just marked `COMPLETED` in the database. This is exactly the class of bug this phase's own inline comments describe fixing elsewhere, missed on the fourth occurrence.

This is not caught by any existing test: every DB-backed test that exercises `resolve_job`-adjacent code paths (e.g. `test_admin_jobs_phase25.py`) opens a **fresh** `AsyncSessionLocal()` for the read that follows a write, which sidesteps the identity-map staleness entirely. No test in the reviewed files asserts on `resolve_job`'s returned `.status`.

**Fix:**
```python
    await db.commit()
    # Phase 31 fix (same pattern as publish_argument/unpublish_argument/approve_job):
    # the bulk update() above used synchronize_session=False, so `job` (loaded via
    # get_job() at the top of this function) is never synced to the committed row.
    await db.refresh(job)

    # Reload and return the updated job
    updated = await get_job(db, job_id)
    return updated  # type: ignore[return-value]
```

### CR-02: Inline stage direction on the first continuation line of a speaker turn drops text and misattributes the remainder to the wrong speaker

**File:** `pipeline/parser/state_machine.py:342-362`

**Issue:** When a speaker's declaration line ends with nothing after the colon (`rest == ""`, e.g. `"MR. OLSON:"` on its own line) and the *next* physical line is a continuation line containing an inline stage direction (e.g. `"(Pause.) May it please the Court."`), the continuation-line branch does:

```python
if current_speaker is not None:
    if INLINE_STAGE_RE.search(line):
        segments = _split_inline_stages(line)
        if len(segments) > 1:
            if current_text_parts:
                current_text_parts.append(segments[0][0])
            flush()
            for seg_text, is_stage in segments[1:]:
                if not seg_text.strip():
                    continue
                if is_stage:
                    emit_stage(seg_text)
                else:
                    current_speaker = (
                        utterances[-1]["raw_speaker_label"]
                        if utterances else current_speaker
                    )
                    current_text_parts = [seg_text]
            continue
```

Because `current_text_parts` is empty at this point (`rest` was empty on the speaker line), `segments[0][0]` (any text preceding the inline stage direction, e.g. `"May it please --"` if the stage direction were mid-sentence) is silently discarded — it is never appended anywhere and `flush()` is then called with `current_text_parts == []`, which hits the early-return branch in `flush()` (`if not raw_text.strip(): ... return`) and emits nothing for it.

Worse, `flush()` unconditionally resets `current_speaker = None` before returning. The subsequent `else` branch (for the text segment *after* the stage direction) then re-derives the speaker via `utterances[-1]["raw_speaker_label"]`. Since the just-emitted `utterances[-1]` is the stage-direction utterance from `emit_stage()`, and `emit_stage()` always sets `raw_speaker_label=None`, the trailing text segment gets `current_speaker = None` — i.e. it will eventually be flushed as a *non*-stage-direction utterance (`is_stage_direction=False`) with `raw_speaker_label=None`. This violates the parser's own documented invariant ("`raw_speaker_label` (Optional[str]): None for stage directions") and silently attributes real spoken text to no speaker while also permanently losing the text that appeared before the inline stage direction.

This is a genuine transcript-fidelity defect for a product whose core requirement is verbatim, identically-treated speaker attribution (CLAUDE.md: "apolitical framing... every speaker... gets identical schema, depth, and treatment"). The trigger condition (empty `rest` on the speaker line, stage direction on the very next line) is narrow but plausible given real PDF line-wrap variance.

**Fix:** Preserve the pre-stage-direction text and the correct speaker across the `flush()` call, e.g. capture `current_speaker` into a local before calling `flush()` instead of relying on `utterances[-1]`:

```python
        if len(segments) > 1:
            speaker_for_continuation = current_speaker
            if current_text_parts:
                current_text_parts.append(segments[0][0])
            elif segments[0][0].strip():
                # No text accumulated yet for this speaker turn, but there IS
                # leading text before the inline stage direction — do not drop it.
                current_text_parts = [segments[0][0]]
            flush()
            for seg_text, is_stage in segments[1:]:
                if not seg_text.strip():
                    continue
                if is_stage:
                    emit_stage(seg_text)
                else:
                    current_speaker = speaker_for_continuation
                    current_text_parts = [seg_text]
            continue
```

## Warnings

### WR-01: `_db_configured()` guard duplicated verbatim in 12+ files

**File:** `api/tests/conftest.py:19-22`, `tests/conftest.py:39-41`, `scripts/cleanup_leaked_test_rows.py:73-75`, and repeated identically (down to the exact placeholder string) in `api/tests/test_admin_arguments_service.py:24-27`, `test_admin_jobs_service.py:25-28`, `test_admin_jobs_list.py:30-33`, `test_admin_jobs_source.py:24-27`, `test_admin_jobs_phase25.py:31-34`, `test_admin_people_phase25.py:31-34`, `test_argument_oyez_field.py:75-78`, `test_arguments.py:46-49`, `test_people.py:33-36`, `test_admin_dashboard_stats.py:42-45`, and `scripts/provision_test_db.py`'s analogous inline check.

**Issue:** The exact same three-line placeholder-detection function is copy-pasted rather than imported from one shared location:

```python
def _db_configured() -> bool:
    url = os.environ.get("DATABASE_URL", "")
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```

`api/tests/conftest.py` already documents ("Same guard every api/tests DB-gated fixture uses") that this is a known, intentional duplication rather than an oversight — but a Phase whose explicit purpose is auditing/hardening these exact test fixtures is the natural place to have consolidated this. If the placeholder sentinel value or the `sk-ant` substring check ever needs to change (e.g., a new default value in `.env.example`, or a different secret prefix), every one of these 12+ copies needs to be updated in lockstep, and a missed one silently reintroduces exactly the kind of dev-DB-pollution risk this phase is trying to close.

**Fix:** Move `_db_configured()` into `api/tests/conftest.py` / `pipeline/tests/conftest.py` (or a shared `tests/_db_helpers.py`) and import it everywhere else, e.g.:
```python
# api/tests/conftest.py
def db_configured() -> bool:
    ...

# other test files
from api.tests.conftest import db_configured as _db_configured
```

### WR-02: `provision_test_db.py` interpolates the target database name into `CREATE DATABASE` without escaping embedded quotes

**File:** `scripts/provision_test_db.py:75`

**Issue:**
```python
await conn.execute(f'CREATE DATABASE "{target_db}"')
```
`target_db` is derived from `TEST_DATABASE_URL` in `.env` (operator-controlled, not attacker-controlled over the network), so this is low-severity in practice, but PostgreSQL identifiers cannot be parameterized via bind params for DDL, and this code does not escape a `"` character embedded in `target_db` (Postgres identifier-escaping convention is to double any embedded `"`). A malformed or mistyped `TEST_DATABASE_URL` containing a stray `"` would produce a confusing syntax error at best, or (in a more exotic misconfiguration) execute unintended SQL.

**Fix:**
```python
safe_name = target_db.replace('"', '""')
await conn.execute(f'CREATE DATABASE "{safe_name}"')
```

### WR-03: `cleanup_leaked_test_rows.py` merges `court_tenures` onto the survivor Person with no post-merge overlap check

**File:** `scripts/cleanup_leaked_test_rows.py:294-318`

**Issue:** `_delete_person_candidates` reassigns every dependent row (including `court_tenures`) from a duplicate Person to the chosen survivor:
```python
_PERSON_DEPENDENT_TABLES = (
    ("court_tenures", "person_id"),
    ...
)
...
await conn.execute(
    text(f"UPDATE {table} SET {column} = :survivor WHERE {column} = ANY(:ids)"),
    {"survivor": survivor_id, "ids": candidates},
)
```
If two duplicate Person rows for the same Justice each independently accumulated their own `court_tenures` row (plausible, since duplicate-Person creation itself was the underlying leak this script exists to clean up), merging them onto one survivor can leave that survivor with two overlapping/conflicting tenure date ranges (e.g. both an untruncated `end_date IS NULL` row and an earlier bounded row). This isn't a crash risk, but it silently produces a data-integrity anomaly (duplicate/overlapping tenure rows on one Person) that the tenure-gap logic elsewhere in the codebase (`_bench_role_and_missing_tenure`, `admin_arguments.get_argument_detail`'s tenure-gap-warning query) may not expect, and there is no report or warning surfaced to the operator about it.

**Fix:** After reassigning `court_tenures`, detect and report (not necessarily auto-fix) overlapping tenure ranges on the survivor so the operator can manually reconcile them, e.g. add a post-merge check in `print_report`/the execute path:
```python
overlap_check = await conn.execute(
    text("""
        SELECT a.id, b.id FROM court_tenures a
        JOIN court_tenures b ON a.person_id = b.person_id AND a.id < b.id
        WHERE a.person_id = :survivor
          AND a.start_date <= COALESCE(b.end_date, 'infinity'::date)
          AND COALESCE(a.end_date, 'infinity'::date) >= b.start_date
    """),
    {"survivor": survivor_id},
)
if overlap_check.first():
    print(f"  WARNING: survivor {survivor_id} now has overlapping court_tenures rows — manual review needed.")
```

---

_Reviewed: 2026-07-13T17:50:04Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
