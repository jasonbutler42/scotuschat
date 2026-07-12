---
phase: 30-corpus-import-resolve-workflow
reviewed: 2026-07-10T22:20:38Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - pipeline/commands/import_convokit.py
  - pipeline/tests/test_import_convokit_adminjob.py
  - pipeline/tests/test_import_convokit_core.py
  - api/schemas/admin_jobs.py
  - api/services/admin_jobs.py
  - api/tests/test_admin_jobs_source.py
  - app/src/routes/admin/pipeline/+page.svelte
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 30: Code Review Report

**Reviewed:** 2026-07-10T22:20:38Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

This phase adds two things: (1) `import_convokit.py` now creates a paired `AdminJob(status=PAUSED, current_step=RESOLVE)` row for every corpus-imported `Argument`, with a `discrepancies` JSONB blob shaped to match `pipeline.commands.resolve`'s HIT branch, and changes the newly-created `Argument.status` from `DRAFT` to `PIPELINE` so the Resolve card renders editable; (2) a `source: "pdf" | "corpus"` field is threaded through `AdminJobResponse`, `list_jobs()`/`get_job()` (via a correlated `exists()` subquery on `PipelineRun.strategy == "convokit_import"`), and a new "Source" column on `/admin/pipeline`.

I traced the full per-conversation transaction (Argument → CaseArgument → PipelineRun → participant resolution → utterance streaming → AdminJob insert), the `exists()`-subquery derivation in both `list_jobs()`/`get_job()`, and the new Svelte column. Diff-level logic (status change, AdminJob creation timing, `source` derivation, `NULL`-safe subquery correlation) is correct and matches its own extensive design-decision comments, and the new tests exercise the intended happy-path and idempotency behavior. I did not find any critical/security-class defects in the new code.

I did find three cross-module correctness/coupling concerns worth fixing (below), plus two minor test-coverage/duplication notes. None of these are exercised by the new tests, which is exactly why they surfaced under adversarial review rather than in the submitted test suite.

## Warnings

### WR-01: `api/services/admin_jobs.py` imports a pipeline CLI module into the FastAPI service layer

**File:** `api/services/admin_jobs.py:47`
**Issue:** `from pipeline.commands.import_convokit import PIPELINE_RUN_STRATEGY` pulls the entire offline `import-convokit` CLI command module (its argparse plumbing, `pipeline.corpus.loader`/`apolitical`/`stage_directions` imports, `dateutil` dependency, etc.) into the read-only FastAPI API layer, just to reuse one string constant (`"convokit_import"`). CLAUDE.md's architecture rules establish a hard separation ("FastAPI is read-only — the pipeline writes directly to PostgreSQL; the API never triggers pipeline steps"); importing a pipeline *command* module from an API *service* module blurs that boundary and means any future change to `import_convokit.py`'s import graph (or a broken pipeline dependency) can break API startup for a feature (admin job listing) that has nothing to do with running the pipeline.
**Fix:** Move `PIPELINE_RUN_STRATEGY` to a small shared location both sides can import without pulling in command logic, e.g. next to the other enums in `api/models/models.py`, or a new `pipeline/constants.py`:
```python
# pipeline/constants.py
PIPELINE_RUN_STRATEGY = "convokit_import"
```
```python
# pipeline/commands/import_convokit.py
from pipeline.constants import PIPELINE_RUN_STRATEGY

# api/services/admin_jobs.py
from pipeline.constants import PIPELINE_RUN_STRATEGY
```

### WR-02: `rerun_job()` has no guard against being invoked on a corpus-sourced job

**File:** `api/services/admin_jobs.py:577-601`
**Issue:** `rerun_job()` copies `pdf_url`, `spaces_key`, `original_filename`, and `source_dockets` from the original job into a brand-new `AdminJob(status=PENDING, current_step=INGEST)`. For a corpus-imported job, `import_convokit.py`'s `AdminJob(...)` insert (line 539-546) never sets `pdf_url`/`spaces_key` — they are `NULL`. Calling `rerun_job()` on a corpus job therefore silently produces a new job with `current_step=INGEST` and no PDF source at all, which the router would then try to spawn an ingest subprocess for with nothing to ingest. Nothing in this file (or the reviewed schema) rejects that call for a `source="corpus"` job — the `source` field exists specifically to distinguish these two job kinds, but `rerun_job` doesn't consult it.
**Fix:** Reject the call early when the original job has no PDF source:
```python
async def rerun_job(db: AsyncSession, job_id: int) -> AdminJob:
    original = await get_job(db, job_id)
    if original is None:
        raise ValueError(f"AdminJob {job_id} not found")
    if original.pdf_url is None and original.spaces_key is None:
        raise ValueError(
            f"AdminJob {job_id} has no PDF source (source={original.__dict__.get('source')!r}); "
            "corpus-imported jobs cannot be rerun through the PDF ingest path."
        )
    ...
```

### WR-03: New `discrepancies` builder can surface duplicate rows for two distinct speakers with the same resolved name

**File:** `pipeline/commands/import_convokit.py:623-699` (pre-existing `_resolve_and_link_participant`) interacting with the new `_build_discrepancies` (`pipeline/commands/import_convokit.py:333-366`) and the new AdminJob insert (`pipeline/commands/import_convokit.py:538-546`)
**Issue:** `_resolve_and_link_participant`'s idempotency check looks up an existing `ArgumentParticipant` by `(argument_id, raw_speaker_label)` — not by `speaker_id`:
```python
existing = await session.execute(
    select(ArgumentParticipant).where(
        ArgumentParticipant.argument_id == argument_id,
        ArgumentParticipant.raw_speaker_label == raw_speaker_label,
    )
)
```
If two *distinct* `speakers.json` ids resolve to the same `full_name`/`raw_speaker_label` within one conversation (e.g. a data-entry duplicate, or two different participants who happen to share a full name), the second speaker_id's resolution call returns the *first* speaker's `ArgumentParticipant` row instead of creating its own. Because `resolved_participants` is keyed by `speaker_id`, it now holds two dict entries pointing at the same `ArgumentParticipant` object. This phase's new code (`resolved = [p for p in resolved_participants.values() if p is not None]` at line 538, feeding `_build_discrepancies`) has no de-duplication step, so the resulting `AdminJob.discrepancies` JSONB — which is new, operator-facing UI content in this phase — would contain two identical-looking rows (same `raw_speaker_label`/`auto_match_id`) for what is really one participant, confusing the Resolve card's Confirm/Change/Create-person action column.
**Fix:** De-duplicate by participant identity before building discrepancies:
```python
resolved_by_id = {
    p.id: p for p in resolved_participants.values() if p is not None
}
session.add(
    AdminJob(
        status=AdminJobStatus.PAUSED,
        current_step=AdminJobStep.RESOLVE,
        argument_id=argument.id,
        discrepancies=_build_discrepancies(list(resolved_by_id.values())),
    )
)
```

## Info

### IN-01: Missing assertion for AdminJob absence on the docket/question-conflict path

**File:** `pipeline/tests/test_import_convokit_core.py:749-813`
**Issue:** `test_forced_collision_increments_docket_question_conflict_not_errored` asserts no `Argument` row is created when `_next_question_number` is forced to collide, but doesn't assert that no `AdminJob` row is created either. Given this phase's new AdminJob-creation code sits after the `Argument` flush/`IntegrityError` catch in `_import_conversation`, an explicit assertion here would directly pin down that the new AdminJob insert is unreachable on this early-return path (defense against a future refactor moving the AdminJob insert earlier).
**Fix:** Add `assert (await isolated_session.execute(select(AdminJob).where(AdminJob.argument_id == pdf_argument_id))).scalars().all() == []`-style check, or a broader "count of AdminJob rows created this run is 0" assertion.

### IN-02: Duplicated inline-style helper pattern for the new Source tag

**File:** `app/src/routes/admin/pipeline/+page.svelte:159-165`
**Issue:** `sourceLabel`/`sourceTagStyle` re-implement the same "map value → label" / "return a hardcoded inline CSS string" pattern already present in `badgeLabel`/`badgeStyle` a few lines above, repeating the same hex literals (`#94a3b8`, `#0f1117`, `#334155`) that appear throughout the file. Not a correctness issue, but it adds to the file's existing inline-style duplication rather than reusing/extracting a shared "tag" style helper.
**Fix:** Low priority; if this file's style helpers are ever consolidated, fold `sourceTagStyle()` into a generic `tagStyle(color: string)` helper alongside `badgeStyle`.

---

_Reviewed: 2026-07-10T22:20:38Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
