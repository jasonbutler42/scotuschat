---
phase: 25-pipeline-job-detail-page
reviewed: 2026-07-07T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - api/routers/admin.py
  - api/schemas/admin_jobs.py
  - api/schemas/admin_people.py
  - api/services/admin_jobs.py
  - api/services/admin_people.py
  - api/tests/test_admin_jobs_phase25.py
  - api/tests/test_admin_people_phase25.py
  - app/src/lib/components/CreatePersonPopover.svelte
  - app/src/lib/components/FailedStepGuidance.svelte
  - app/src/lib/components/ResolveCard.svelte
  - app/src/lib/components/RunStatusCard.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
findings:
  critical: 1
  warning: 6
  info: 2
  total: 9
status: issues_found
---

# Phase 25: Code Review Report

**Reviewed:** 2026-07-07
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The backend (admin.py, admin_jobs.py, admin_people.py, and their schemas) is well-guarded:
IDOR scoping is consistently derived from `job_id` → `argument_id`, every bulk UPDATE/DELETE
carries `synchronize_session=False`, ValueError→422 mapping is consistent, and the Phase 25
readiness/failed-recovery/resolve-row endpoints match their test coverage. No SQL/command
injection, no hardcoded secrets, no `eval`/`@html`/`innerHTML` usage found.

The one Critical finding is in the new Resolve card's "Create new person" flow
(`CreatePersonPopover` → `ResolveCard.handlePersonCreated`): the Bench/Advocate choice made in
the popover is silently discarded by the parent callback, so the row's client-side `side` state
is never updated to match what was just persisted server-side. A routine follow-up interaction
on the same row (e.g. blurring the Title input) re-submits the stale side value and reverts the
just-created person's Bench/Advocate assignment in the database. The remaining findings are
warnings about dead/misleading code left over from the pre-Phase-25 page layout, an unguarded
DB length constraint, and a schema validation gap.

## Critical Issues

### CR-01: Newly created person's Bench/Advocate side is silently discarded, then reverted on next save

**File:** `app/src/lib/components/ResolveCard.svelte:523` (calls `handlePersonCreated`, defined at `ResolveCard.svelte:245-252`)
**File:** `app/src/lib/components/CreatePersonPopover.svelte:22,112`

`CreatePersonPopover` explicitly hands the chosen side back to its caller:

```ts
// CreatePersonPopover.svelte
interface CreatePersonPopoverProps {
  ...
  onCreated: (person: CreatedPerson, side: string) => void;
}
...
onCreated(person, resolvedSide());   // line 112
```

`ResolveCard.svelte` wires this up but drops the second argument entirely:

```svelte
<!-- line 523 -->
onCreated={(person) => handlePersonCreated(label, person)}
```

```ts
// lines 245-252
function handlePersonCreated(label: string, person: Candidate) {
  const s = rowMatchStates[label];
  if (!s) return;
  s.extraCandidates = [...s.extraCandidates, person];
  s.personId = person.id;
  s.disposition = 'corrected';
  s.correcting = true;
  // side is never written to pendingSideOverrides
}
```

The backend (`create_person_for_job` in `api/services/admin_jobs.py:885-894`) already updates
`ArgumentParticipant.side` to the operator's chosen side in the same transaction as the Person
insert, so the database is briefly correct. But the row's rendered `side` in the table comes from
`effectiveSide(row)` (`ResolveCard.svelte:110-112`), which reads
`pendingSideOverrides[row.participant_id] ?? row.side` — and `pendingSideOverrides` was never
updated by `handlePersonCreated`. `row.side` is the stale value from the original `resolveRows`
load (nothing calls `invalidateAll()`/`update()` after the popover's `?/addPerson` submission —
see `CreatePersonPopover.svelte:100-118`, which only toggles local component state on success).

Consequence: the `<select>` in Column 3 (`ResolveCard.svelte:556-579`) still displays/submits the
old side value. Because that `<select>` is wired to the row's hidden `?/saveResolveRow` form via
the HTML `form=` attribute, any subsequent trigger on the same row — most plausibly blurring the
Title `<input>` right after creating the advocate/justice (`ResolveCard.svelte:614-619`,
`onblur={() => submitRow(row.participant_id)}`) — submits a PATCH with the stale `side`, silently
overwriting the correct value `create_person_for_job` had just written, per
`update_resolve_row_for_job` (`api/services/admin_jobs.py:697-765`).

**Fix:** thread `side` through the callback and apply it the same way `confirmSide`/`onSideChange`
already do:

```svelte
onCreated={(person, side) => handlePersonCreated(label, person, side)}
```

```ts
function handlePersonCreated(label: string, person: Candidate, side: string) {
  const s = rowMatchStates[label];
  if (!s) return;
  s.extraCandidates = [...s.extraCandidates, person];
  s.personId = person.id;
  s.disposition = 'corrected';
  s.correcting = true;
  pendingSideOverrides[/* participant_id for this row */] = side;
}
```
`handlePersonCreated` only has `label` (raw_speaker_label) in scope, not `participant_id` — the
row lookup (`mergedRows.find(r => r.raw_speaker_label === label)`) or an extra parameter should be
added so the correct `pendingSideOverrides` key can be set, and ideally `submitRow` should also be
invoked immediately so the corrected side is persisted (rather than left to accidentally be
persisted or reverted by an unrelated field blur).

## Warnings

### WR-01: Dead pre-Phase-25 code path in the `approve` action silently swallows PATCH failures

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:311-355`

The `approve` action still parses `participant_side[<id>]` form fields and PATCHes each one to
`/api/admin/arguments/{argumentId}/participants/{participant_id}` before calling `/approve`:

```ts
const match = key.match(/^participant_side\[(\d+)\]$/);
...
await Promise.allSettled(
  sideEntries.map(({ participant_id, side }) =>
    fetch(`.../participants/${participant_id}`, { method: 'PATCH', ... }).catch(() => undefined),
  ),
);
```

No component in this phase (or anywhere in `app/src`) renders a field named
`participant_side[...]` any more — that responsibility moved to `ResolveCard`'s own
`?/saveResolveRow` per-row action (Phase 25). `sideEntries` is therefore always empty and this
block never executes today, but it is misleading: the comment claims this is how "side
assignments" are "atomically captured at approve time (D-09)", which is no longer true. If this
code is ever reconnected (e.g. a future refactor reintroduces the field name), note that
`Promise.allSettled(...).catch(() => undefined)` never inspects `res.ok`, so both network errors
and 4xx/5xx responses are silently discarded and `approve` proceeds regardless — a latent
silent-data-loss pattern.

**Fix:** remove the dead `sideEntries`/PATCH block (lines 311-355) now that `ResolveCard` owns
side/title persistence, or if intentionally kept as a compatibility shim, check `res.ok` for each
settled promise and surface any failures via `approveError` before calling `/approve`.

### WR-02: `create_person_for_job` can silently create an orphaned Person when `raw_speaker_label` is set without `side`

**File:** `api/services/admin_jobs.py:880-894`
**File:** `api/schemas/admin_jobs.py:76-93` (`PersonCreate`)

```python
is_justice = body.side == SideEnum.BENCH if body.side is not None else False
person = Person(full_name=body.full_name, role_id=role_id, is_justice=is_justice)
db.add(person)
await db.flush()

if participant is not None and body.side is not None:
    await db.execute(update(ArgumentParticipant)...)
```

The participant lookup (and its IDOR validation) runs whenever `raw_speaker_label` is supplied,
but the actual `ArgumentParticipant` linkage only happens if `body.side` is *also* non-None. A
caller that supplies `raw_speaker_label` but omits `side` gets a 201 response with a newly
created, unlinked `Person` and no error — the participant the request implied it was resolving
is left untouched. The current UI (`CreatePersonPopover.svelte`) always sends both fields, so this
is not reachable today, but nothing in `PersonCreate` enforces the pairing.

**Fix:** add a model validator on `PersonCreate` requiring `side` whenever `raw_speaker_label` is
present, or raise `ValueError` in `create_person_for_job` when `raw_speaker_label` is set but
`side` is None, so the person insert and participant-scoping validation stay in sync (matching the
"validate before mutate" pattern already used elsewhere in this function).

### WR-03: `ResolveRowUpdate.title` has no length validation against the `String(500)` DB column

**File:** `api/schemas/admin_jobs.py:162-178` (`ResolveRowUpdate`)
**File:** `api/services/admin_jobs.py:752-763` (`update_resolve_row_for_job`)
**File:** `api/models/models.py:263` (`title = Column(String(500), nullable=True)`)

`ResolveRowUpdate.title: Optional[str] = None` accepts arbitrary-length text, and
`update_resolve_row_for_job` writes it straight into the `UPDATE ArgumentParticipant ... .values(side=..., title=title)` call with no try/except around the `db.execute`/`db.commit`. A title over
500 characters will raise an unhandled `DataError`/`StringDataRightTruncation` from asyncpg,
surfacing to the router as an uncaught exception (500) rather than the 422 pattern used
everywhere else in this file.

**Fix:** add `max_length=500` to the `title` field on `ResolveRowUpdate`, or validate/truncate in
`update_resolve_row_for_job` and raise `ValueError` (mapped to 422 by the router) instead of
letting the DB constraint raise.

### WR-04: "Continue Resolve" can never appear when a paused job has zero discrepancies

**File:** `app/src/lib/components/ResolveCard.svelte:187-195`

```ts
let allDispositioned = $derived.by(() => {
  if (!isPaused) return false;
  const disc = discrepancies ?? [];
  if (disc.length === 0) return false;   // <-- always false when there is nothing to disposition
  return disc.every((d) => { ... });
});
```

If a job is `paused` but `AdminJobResponse.discrepancies` is empty or null (e.g. every speaker was
already resolved by alias lookup, or all rows were fixed via the inline `saveResolveRow` action
instead of the batch discrepancy flow), `allDispositioned` is forced to `false` and the "Continue
Resolve" button (`ResolveCard.svelte:681-724`) never renders. There is no other UI path to POST
`?/resolve` and flip the job to `COMPLETED`, so the run would be stuck in `paused` until an
operator manipulates the database directly.

**Fix:** treat an empty-but-paused discrepancy list as already dispositioned (`disc.length === 0
? true : disc.every(...)`), or otherwise render the Continue button whenever `isPaused` regardless
of discrepancy count.

### WR-05: Dead duplicate `list_people` in `admin_jobs.py` — never called, shadows a differently-scoped function of the same name

**File:** `api/services/admin_jobs.py:773-797`

```python
async def list_people(db: AsyncSession) -> list[dict]:
    """... Used by the discrepancy review typeahead ..."""
```

`api/services/admin_people.py` also defines `list_people(db, incomplete=False, tenure_gaps=False)`,
which is the one actually wired to `GET /api/admin/people` in `admin.py:569-588`
(`people_service.list_people(...)`, where `people_service = api.services.admin_people`). A
repo-wide search finds no caller of `admin_jobs.list_people` — not the router, not the frontend
load function (which fetches `/api/admin/people` directly), not the test suite. This is dead code
that also creates a maintenance hazard: a future edit to "the" `list_people` function could target
the wrong module, silently missing the one actually serving traffic.

**Fix:** delete `admin_jobs.list_people` (lines 773-797), or if it is intentionally kept for some
undiscovered caller, rename it to avoid colliding with `admin_people.list_people`.

### WR-06: Local-upload job-creation path issues a no-op `db.commit()`

**File:** `api/routers/admin.py:301-312`

```python
else:
    # No object storage configured — save locally for dev use.
    uploads_dir = Path("data/uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    local_path = uploads_dir / f"{job.id}.pdf"
    local_path.write_bytes(file_bytes)
    await db.commit()          # <-- nothing was changed on `db` since create_job() already committed
    await db.refresh(job)
```

`jobs_service.create_job` already commits the new `AdminJob` row. No `update()`/`db.add()` happens
between that commit and this second `db.commit()`, so the call is a no-op that adds confusion about
what state is actually being persisted here (in contrast to the Spaces-backed branch just above,
where the commit follows a real `update(AdminJob)...values(spaces_key=key)`).

**Fix:** remove the redundant `await db.commit()` (keep `await db.refresh(job)` if needed for
serialization), or add a comment clarifying it is defensive/no-op.

## Info

### IN-01: `CreatePersonPopover` builds HTML `id`/`for` values directly from `raw_speaker_label`

**File:** `app/src/lib/components/CreatePersonPopover.svelte:125,131`

```svelte
<label for="cp-name-{rawSpeakerLabel}" ...>
<input id="cp-name-{rawSpeakerLabel}" ... />
```

Raw speaker labels routinely contain spaces and punctuation (e.g. `"MR. SMITH"`), which are not
valid characters in an HTML `id` per spec (`id` must not contain ASCII whitespace); browsers
tolerate this today, but it is not spec-compliant and could break if `rawSpeakerLabel` ever
contains characters that collide with CSS selector syntax used elsewhere.

**Fix:** slugify `rawSpeakerLabel` (e.g. replace whitespace/non-word characters) before using it in
`id`/`for`, mirroring the `comboId` pattern already used in `ResolveCard.svelte:404`
(`` `listbox-${label.replace(/\s+/g, '-')}` ``).

### IN-02: `title_hint` cannot show the original parser extraction once a title has been edited

**File:** `api/services/admin_people.py:704-712` (`title_hint` sourced from the same
`ArgumentParticipant.title` column as `title`)
**File:** `app/src/lib/components/ResolveCard.svelte:632-634` (`Extracted: {row.title_hint ?? 'N/A'}`)

The docstring for `list_resolve_rows_for_job` explicitly notes there is no separate "originally
extracted" column for title — `title_hint` and `title` are the same value. Once an operator edits
and saves a title, the "Extracted: …" caption shown next to the input will thereafter echo the
edited value, not the parser's original output, which can mislead an operator into thinking the
displayed hint reflects untouched parse output. This is a documented, intentional limitation
rather than a bug, but the UI label ("Extracted:") overstates the guarantee.

**Fix:** consider relabeling to something like "Current value" once edited, or persist the
original parse-time title separately if the distinction matters operationally.

---

_Reviewed: 2026-07-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
