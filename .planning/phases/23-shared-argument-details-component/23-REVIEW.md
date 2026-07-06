---
phase: 23-shared-argument-details-component
reviewed: 2026-07-06T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - api/schemas/admin_arguments.py
  - api/schemas/admin_jobs.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - app/src/lib/components/ArgumentDetailsCard.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 1
  warning: 3
  info: 2
  total: 6
status: issues_found
---

# Phase 23: Code Review Report

**Reviewed:** 2026-07-06T00:00:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 23 delivered the `ArgumentDetailsCard` shared component and wired it into the pipeline job detail page via the `saveJobMetadata` action. The previous review findings (CR-01 bare fromisoformat, CR-02 multi-docket silent drop, WR-01 dead saveMetadata action) have all been addressed in this revision — the try/except guard, the multi-docket fail-fast, and the saveMetadata removal are all confirmed present.

One new blocker was found: the `approve` action silently discards participant side-assignment PATCH failures, meaning an argument can be approved with incorrect advocate roles when any PATCH to `/api/admin/arguments/{id}/participants/{pid}` fails. The silence is explicit in the code but the consequence — wrong side data in the permanent argument record — is not recoverable without manual correction.

Three warnings were found: two `# type: ignore[return-value]` suppressions that hide a potential None-return-as-AdminJob type violation, a hints construction that hard-codes `question_number: null` contradicting the component's prop contract, and a polling loop that updates `liveJob` via direct state mutation but never updates `data.savedValues` or `data.hints`, leaving the ArgumentDetailsCard stale after a terminal-state poll transition until `invalidateAll()` completes.

---

## Critical Issues

### CR-01: Silently discarded PATCH failures in `approve` action allow argument approval with wrong advocate sides

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:216-231`

**Issue:** The `approve` action uses `Promise.allSettled` to fire side-assignment PATCHes and then unconditionally proceeds to POST `/approve` regardless of whether any PATCH succeeded. Each `.catch(() => undefined)` inside the `map` ensures rejections are swallowed at the Promise level, and `allSettled` ensures no rejection propagates. If the FastAPI `/api/admin/arguments/{id}/participants/{pid}` endpoint returns a non-OK status for any participant, the side assignment for that participant is silently lost — but the argument is still approved and transitions to DRAFT state. The operator has no feedback that their role assignments were not saved.

The consequence is silent corrupt data: an argument is marked DRAFT with one or more advocate participants still in the wrong `side` state (e.g., UNKNOWN instead of PETITIONER). This cannot be recovered without manually editing the argument afterwards, and the admin pipeline page shows no indicator that side assignments failed.

**Fix:** Collect the `allSettled` results and check for rejections. Return `fail(502, { approveError: ... })` if any PATCH yielded a non-OK response before proceeding to POST approve:

```typescript
const sideResults = await Promise.allSettled(
  sideEntries.map(({ participant_id, side }) =>
    fetch(
      `${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/participants/${participant_id}`,
      {
        method: 'PATCH',
        headers: {
          'X-Admin-Token': ADMIN_TOKEN,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ side }),
      },
    ),
  ),
);

const sideFailures = sideResults.filter(
  (r): r is PromiseRejectedResult | PromiseFulfilledResult<Response> =>
    r.status === 'rejected' || (r.status === 'fulfilled' && !r.value.ok),
);
if (sideFailures.length > 0) {
  return fail(502, {
    approveError: 'Could not save advocate role assignments. Check your selections and try again.',
  });
}
```

---

## Warnings

### WR-01: `get_job` / `resolve_job` / `approve_job` suppress `None` return with `# type: ignore` — no null guard

**File:** `api/services/admin_jobs.py:446` and `api/services/admin_jobs.py:504`

**Issue:** Both `resolve_job` and `approve_job` reload the job after their commit with `updated = await get_job(db, job_id)` and then return `updated # type: ignore[return-value]`. `get_job` is typed to return `AdminJob | None`. The `# type: ignore` suppresses the type error rather than asserting or handling the `None` case. In theory, a job that was just committed and confirmed to exist moments earlier should not return `None` on immediate reload. In practice, this assumption could be violated by a concurrent `delete_job` call (the API does not serialize deletes against resolves). If it is violated, the router receives `None` where it expects `AdminJob`, and Pydantic serialization will raise an `AttributeError` or `ValidationError` that surfaces as a 500.

**Fix:** Add an assertion or explicit guard after the reload:

```python
# api/services/admin_jobs.py — apply in both resolve_job and approve_job
updated = await get_job(db, job_id)
if updated is None:
    raise ValueError(f"AdminJob {job_id} disappeared after commit — possible concurrent delete")
return updated
```

---

### WR-02: `hints.question_number` is always `null` — component prop contract says it should reflect extracted value

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:132`

**Issue:** The `hints` object is built at lines 128-135 with `question_number: null` hardcoded. The `ArgumentDetailsCard` component renders `Extracted: {hints.question_number ?? 'N/A'}` for the question number hint row. The result is always "Extracted: N/A" regardless of what `cover_metadata` contains. The comment at line 132 is absent — there is no explanation of why the hint is permanently null.

Per `admin_jobs.py` line 170-171, `cover_metadata` does not have a `question_number` key — that value comes from `Argument.question_number`. However, the `ArgumentPreview` interface at line 24 exposes `question_number: number | null` from the Argument record. The current hints construction skips this and simply renders N/A, which is misleading if `argument.question_number` is already set (the saved value and the "extracted" hint would both say the same thing but from different sources).

The correct behavior is one of:
- Intentionally show N/A because there is no cover-metadata source for question_number (then add a comment explaining this).
- Show `argument.question_number` as the extracted hint (if the intent is to echo the previously saved value as the hint).

Either way, the current code is silently incorrect because it provides no extracted hint even when data is available.

**Fix (option A — document the intentional N/A):** Add a comment:

```typescript
hints = {
  dockets: argument.cover_metadata?.primary_docket
    ? [String(argument.cover_metadata.primary_docket)]
    : [],
  // question_number has no cover_metadata source; Argument.question_number is the
  // operator-saved value shown in savedValues, not a pipeline extraction hint.
  question_number: null,
  argued_date: (argument.cover_metadata?.argued_date as string) ?? null,
  case_name: (argument.cover_metadata?.case_name as string) ?? null,
};
```

**Fix (option B — use the saved value as the hint when no extracted value exists):**

```typescript
question_number: argument.question_number != null ? String(argument.question_number) : null,
```

---

### WR-03: `invalidateAll()` in the poll loop does not update `data.savedValues` / `data.hints` — `ArgumentDetailsCard` shows stale data after terminal transition

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:103-106`

**Issue:** When the poll detects a terminal job status, it calls `invalidateAll()` to refresh the server load data, which re-fetches `data.argument`, `data.savedValues`, and `data.hints`. However, there is a race window between the terminal status being written to `liveJob` (line 94) and `invalidateAll()` completing. During this window, `ArgumentDetailsCard` continues to display the stale `data.savedValues` (the pre-terminal values). If the pipeline step just completed updates `Argument.question_number`, `source_docket`, or `argued_date`, the card will briefly show old values.

More importantly, `liveJob` is a direct `$state` copy updated from the poll, but `data.savedValues` and `data.hints` are server-load props that only update after `invalidateAll()` resolves. They are NOT derived from `liveJob`. The `$effect(() => { liveJob = data.job; })` sync at line 76 keeps `liveJob` in step with load re-runs, but there is no equivalent sync that rebuilds `savedValues`/`hints` from the polled job data. The ArgumentDetailsCard prop values can therefore be permanently stale if `invalidateAll()` fails silently or if SvelteKit's re-hydration does not propagate the load result to the component.

**Fix:** After `invalidateAll()`, check that `data.savedValues` was updated. Alternatively, derive `savedValues` reactively from `data.argument` using `$derived`, so any time `data.argument` changes (including after `invalidateAll()`), the card reflects it automatically. This is a reactive model concern inherent to the `liveJob` + `data.*` split, not a bug in the polling logic itself.

---

## Info

### IN-01: `AdvocateParticipant.side` typed as `str` instead of `SideEnum` weakens schema validation

**File:** `api/schemas/admin_arguments.py:99`

**Issue:** `AdvocateParticipant.side` is declared as `side: str  # SideEnum value as string`. The service populates this via `row.side.value` (a correct `.value` serialization of the enum). However, if this schema were ever used as input validation, `str` would accept any string including values outside the `SideEnum` domain. Pydantic v2's `use_enum_values: True` config can serialize an enum to its string value automatically, making the type safer.

**Fix:** Change the field type to `SideEnum` and add `use_enum_values: True` to the model's config, or add a `field_validator` to enforce enum membership:

```python
class AdvocateParticipant(BaseModel):
    participant_id: int
    person_id: int
    full_name: str
    side: SideEnum

    model_config = {"from_attributes": True, "use_enum_values": True}
```

---

### IN-02: `comboOutsideClick` Svelte action registers a global `click` listener on `document` and also removes it in `destroy` — double-removal risk

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:382-402`

**Issue:** The `comboOutsideClick` Svelte action adds `handleClick` to `document` via `$effect` (which returns a teardown) and also removes it in the `destroy` method. When the action is destroyed, both the `$effect` teardown AND the `destroy` cleanup both call `document.removeEventListener('click', handleClick)`. The second call is a no-op (removing a listener that was already removed) and does not cause a bug, but it indicates the two cleanup paths are redundant. If the `$effect` dependency is re-evaluated while the element is live, a new listener is added each time, accumulating multiple listeners — though in this case the `$effect` inside the action has no reactive dependencies that would trigger re-execution after mount.

**Fix:** Remove the redundant `destroy` teardown since the `$effect` inside the action already handles cleanup, or keep `destroy` and remove the `$effect`. Do not maintain both.

---

_Reviewed: 2026-07-06T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
