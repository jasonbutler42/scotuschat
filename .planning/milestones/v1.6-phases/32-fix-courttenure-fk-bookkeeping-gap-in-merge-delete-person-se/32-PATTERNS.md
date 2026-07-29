# Phase 32: CourtTenure FK Bookkeeping Gap - Pattern Map

**Mapped:** 2026-07-13
**Files analyzed:** 6 (3 backend modify, 2 frontend modify, 1 test modify)
**Analogs found:** 6 / 6 (all in-file — this phase extends existing functions rather than creating new files)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `api/services/admin_people.py` (`get_merge_preview`) | service | CRUD (count/read) | same function, existing 4-table loop (lines 570-580) | exact — extend loop list |
| `api/services/admin_people.py` (`merge_people`) | service | CRUD (bulk update+delete, transactional) | same function, existing 4-table transfer loop (lines 611-622) | exact — extend loop list |
| `api/services/admin_people.py` (`delete_person_if_orphan`) | service | CRUD (count-then-block, transactional) | same function, existing 3-table blocking loop (lines 655-664) | exact — extend loop list |
| `api/schemas/admin_people.py` (`MergePreview`) | model (Pydantic schema) | request-response (DTO) | same class, existing 4 int fields (lines 212-224) | exact — add field |
| `api/routers/admin.py` (`DELETE /people/{person_id}`) | route/controller | request-response | same handler (lines 890-912) | no change expected — verify only |
| `app/src/routes/admin/people/[id]/+page.svelte` | component | request-response (render merge preview) | same component, `mergePreview` state type (lines 112-117) + breakdown render (lines 741-753) | exact — extend type + template |
| `app/src/routes/admin/people/[id]/+page.server.ts` | provider (SvelteKit server load) | request-response | same load fn, `MergePreviewCounts` interface (lines 46-51) + `can_delete`/`delete_block_count` derivation (lines 93-113) | exact — extend interface + boolean/sum logic |
| `api/tests/test_admin_people_merge.py` | test | CRUD (DB-guarded + pure-logic) | same file, existing test functions for preview/merge/delete (lines 59-70, 117-159, 182-213, 236-280) | exact — mirror shape for 5th table |

All "closest analogs" are the surrounding code in the *same file being modified* — this is a pure extension of an established repeated pattern (4-table loop → 5-table loop), not a net-new pattern requiring an external analog.

## Pattern Assignments

### `api/services/admin_people.py` — `get_merge_preview` (service, CRUD)

**Analog:** same function, lines 558-581 (this file)

**Imports already present** (lines 30-42) — `CourtTenure` is already imported, no import change needed:
```python
from api.models.models import (
    AdminJob,
    Argument,
    ArgumentParticipant,
    ArgumentStatusEnum,
    CaseAppearance,
    CourtTenure,
    Person,
    Role,
    SideEnum,
    SpeakerAlias,
    Utterance,
)
```

**Core loop pattern to extend** (lines 570-580):
```python
counts: dict[str, int] = {}
for key, model, col in [
    ("utterances", Utterance, Utterance.person_id),
    ("aliases", SpeakerAlias, SpeakerAlias.person_id),
    ("appearances", CaseAppearance, CaseAppearance.person_id),
    ("argument_participants", ArgumentParticipant, ArgumentParticipant.person_id),
]:
    count = (await db.execute(
        select(sqlfunc.count()).select_from(model).where(col == source_id)
    )).scalar_one()
    counts[key] = count
return counts
```
**Change:** append `("tenures", CourtTenure, CourtTenure.person_id),` as the 5th tuple in the list. No other lines change. Update the docstring's "4 FK tables" → "5 FK tables" and the keys list to include `tenures`.

---

### `api/services/admin_people.py` — `merge_people` (service, CRUD/transactional)

**Analog:** same function, lines 584-630 (this file)

**Core transfer loop pattern to extend** (lines 611-622):
```python
for model, col in [
    (Utterance, Utterance.person_id),
    (SpeakerAlias, SpeakerAlias.person_id),
    (CaseAppearance, CaseAppearance.person_id),
    (ArgumentParticipant, ArgumentParticipant.person_id),
]:
    await db.execute(
        update(model)
        .where(col == source_id)
        .values({col.key: target_id})
        .execution_options(synchronize_session=False)
    )
```
**Change:** append `(CourtTenure, CourtTenure.person_id),` as the 5th tuple. The `synchronize_session=False` guard is already applied generically inside the loop body — no per-model exception needed. Single `db.commit()` at line 628 remains unchanged (atomicity preserved automatically). Update docstring "All 4 UPDATEs" → "All 5 UPDATEs".

---

### `api/services/admin_people.py` — `delete_person_if_orphan` (service, CRUD/two-tier)

**Analog:** same function, lines 633-672 (this file)

**Two-tier pattern — do NOT touch the unconditional-delete tier** (lines 648-653):
```python
# Delete name-variant aliases first — they are intrinsic to the person (Gap B fix).
await db.execute(
    delete(SpeakerAlias)
    .where(SpeakerAlias.person_id == person_id)
    .execution_options(synchronize_session=False)
)
```
This SpeakerAlias-only unconditional-delete step stays exactly as-is per D-01/D-04 — `CourtTenure` does NOT join this tier.

**Blocking-tier loop pattern to extend** (lines 655-664):
```python
for model, col in [
    (Utterance, Utterance.person_id),
    (CaseAppearance, CaseAppearance.person_id),
    (ArgumentParticipant, ArgumentParticipant.person_id),
]:
    count = (await db.execute(
        select(sqlfunc.count()).select_from(model).where(col == person_id)
    )).scalar_one()
    if count > 0:
        return False  # Not orphaned — caller returns 409 (D-06)
```
**Change:** append `(CourtTenure, CourtTenure.person_id),` as the 4th tuple in this list. Update docstring "all 4 FK tables" → "all 5 FK tables" and "COUNT check covers all 4 FK tables" → "5 FK tables".

---

### `api/schemas/admin_people.py` — `MergePreview` (model/DTO, request-response)

**Analog:** same class, lines 212-224 (this file)

```python
class MergePreview(BaseModel):
    """Response from GET /api/admin/people/{id}/merge-preview (PADM-04).

    Returns the count of each FK table row that will transfer from source to target
    when a merge is executed. Used to show the operator a summary before confirming.
    """

    utterances: int
    aliases: int
    appearances: int
    argument_participants: int

    model_config = {"from_attributes": True}
```
**Change:** add `tenures: int` as a 5th field (per Claude's Discretion naming, D-01/D-02). Field order should mirror the service dict key order (append after `argument_participants`) to match the router's `MergePreview(**counts)` unpacking in `api/routers/admin.py` line 863.

---

### `api/routers/admin.py` — `DELETE /people/{person_id}` and `GET /people/{id}/merge-preview` (route/controller, request-response)

**Analog:** same handlers, lines 890-912 (delete) and lines ~850-863 (merge-preview, not shown in full but confirmed at line 860-863)

```python
counts = await people_service.get_merge_preview(db, person_id)
if counts is None:
    raise HTTPException(status_code=404, detail="Person not found")
return MergePreview(**counts)
```
**No change expected** — `MergePreview(**counts)` automatically picks up the new `tenures` key once the schema and service both add it (unpacking is dict-key-driven, not positional). The 409 message in `delete_person` (lines 907-911) stays generic per CONTEXT.md D-05 discretion note ("no per-table wording exists today and none needs to be added").

---

### `app/src/routes/admin/people/[id]/+page.svelte` (component, request-response render)

**Analog:** same component, `mergePreview` state type (lines 111-120) and rendered breakdown (lines 741-755)

**State type to extend** (lines 112-117):
```typescript
let mergePreview = $state<{
    utterances: number;
    aliases: number;
    appearances: number;
    argument_participants: number;
} | null>(null);
```
**Change:** add `tenures: number;` as a 5th field.

**All-zero check + breakdown render to extend** (lines 746-753):
```svelte
{#if mergePreview.utterances === 0 && mergePreview.aliases === 0 && mergePreview.appearances === 0 && mergePreview.argument_participants === 0}
    <p style="font-size: 14px; color: #94a3b8; margin: 0;">
        No records to transfer. This person has no associated data.
    </p>
{:else}
    <p style="font-size: 14px; color: #e2e8f0; margin: 0;">
        {mergePreview.utterances} utterance(s) · {mergePreview.aliases} alias(es) · {mergePreview.appearances} appearance(s) · {mergePreview.argument_participants} argument participant(s)
    </p>
{/if}
```
**Change:** add `&& mergePreview.tenures === 0` to the all-zero condition, and append `· {mergePreview.tenures} tenure(s)` after `argument participant(s)` in the breakdown string (per Claude's Discretion copy position, D-05).

---

### `app/src/routes/admin/people/[id]/+page.server.ts` (provider/server-load, request-response)

**Analog:** same file, `MergePreviewCounts` interface (lines 46-51) and `can_delete`/`delete_block_count` derivation (lines 93-113)

```typescript
interface MergePreviewCounts {
    utterances: number;
    aliases: number;
    appearances: number;
    argument_participants: number;
}
```
**Change:** add `tenures: number;` as a 5th field.

```typescript
if (previewRes.ok) {
    const counts: MergePreviewCounts = await previewRes.json();
    can_delete =
        counts.utterances === 0 &&
        counts.appearances === 0 &&
        counts.argument_participants === 0;
    delete_block_count = counts.utterances + counts.appearances + counts.argument_participants;
}
```
**Change (D-01, blocking tier — matches `utterances`/`appearances`/`argument_participants`, NOT `aliases`):**
```typescript
can_delete =
    counts.utterances === 0 &&
    counts.appearances === 0 &&
    counts.argument_participants === 0 &&
    counts.tenures === 0;
delete_block_count = counts.utterances + counts.appearances + counts.argument_participants + counts.tenures;
```
Note: `aliases` is deliberately excluded from both `can_delete` and `delete_block_count` — do not add `counts.tenures` to the aliases bucket; it must join the blocking three, per CONTEXT.md D-05/D-01.

---

### `api/tests/test_admin_people_merge.py` (test, CRUD-verification)

**Analog:** same file — 4 pattern shapes to mirror for `CourtTenure`:

**1. Schema construction test** (lines 59-70) — extend the `MergePreview(...)` call with `tenures=N` and assert it:
```python
def test_merge_schemas_import() -> None:
    from api.schemas.admin_people import MergePreview, MergeRequest
    req = MergeRequest(target_id=7)
    assert req.target_id == 7
    preview = MergePreview(utterances=2, aliases=1, appearances=3, argument_participants=0)
    assert preview.utterances == 2
    ...
```

**2. Preview-counts DB test** (lines 117-159) — mirrors the "insert test person, assert all counts including new key are 0" shape. New test should insert a `CourtTenure` row tied to a test person and assert `result["tenures"] == 1` (transfer counting), plus a zero-tenure case.

**3. Delete-blocked test** (mirrors lines 182-213 `test_delete_person_if_orphan_deletes_orphaned_person`, but needs a NEW companion test for the blocking path — no existing "blocked" test currently exists in this file since it currently only tests the orphan-success path with zero FK rows across the board; the phase should add a `test_delete_person_if_orphan_blocked_by_tenure` test that inserts a `CourtTenure` row and asserts `result is False`).

**4. Merge-transfer test** (lines 236-280) — mirrors `test_merge_people_transfers_and_deletes_source`; extend or add a companion assertion that a `CourtTenure` row's `person_id` is reassigned to `tgt_id` after merge, using the same insert/rollback-via-cleanup DB pattern (`db.execute(text("INSERT INTO ..."))`, `db.commit()`, fetch by unique name, run service fn, assert, cleanup via `DELETE FROM people WHERE id = ...` — CourtTenure rows cascade-delete via person_id transfer so no separate tenure cleanup needed beyond the person cleanup, but insert should use `INSERT INTO court_tenures (person_id, seat, ...)` raw SQL matching the DB-guarded style already used, e.g. `_db_configured()` skipif guard, `create_async_engine`/`sessionmaker` boilerplate exactly as in the existing tests).

**Test naming convention to follow:** `test_<function>_<scenario>` (e.g., `test_get_merge_preview_counts_tenures`, `test_delete_person_if_orphan_blocked_by_tenure`, `test_merge_people_transfers_tenures`) — matches existing naming style in this file.

---

## Shared Patterns

### Bulk-statement transactional guard (`synchronize_session=False`)
**Source:** module docstring `api/services/admin_people.py` lines 15-19, and every `update()`/`delete()` call in the three target functions.
**Apply to:** any new `CourtTenure` UPDATE/DELETE/COUNT statement added to the loops — the guard is already baked into the loop body, so extending the tuple list automatically inherits it. No new statement should be written outside these loops.

### 4-table-list-append pattern
**Source:** `get_merge_preview` (lines 571-576), `merge_people` (lines 611-616), `delete_person_if_orphan` (lines 655-659) — all use a `for key(, model, col) in [...]` list literal.
**Apply to:** all three service functions — the fix is a single tuple appended to each list, not new branching logic.

### Two-tier FK classification (blocking vs. intrinsic-unconditional)
**Source:** `delete_person_if_orphan`, `SpeakerAlias` (intrinsic, lines 648-653) vs. `Utterance`/`CaseAppearance`/`ArgumentParticipant` (blocking, lines 655-664).
**Apply to:** `CourtTenure` joins the blocking tier per D-01 — do not add a second unconditional-delete block.

### Frontend merge-preview response contract (fixed-shape dict, not dynamic list)
**Source:** `app/src/routes/admin/people/[id]/+page.svelte` (lines 112-117, 746-753) and `+page.server.ts` (lines 46-51, 93-113).
**Apply to:** both frontend files must add the `tenures` field in lockstep with the backend schema change — the field name is hardcoded on both sides (Pydantic + TypeScript interfaces), so a mismatch would silently drop the count rather than error.

## No Analog Found

None — every file in scope is an in-place extension of an already-established 4/5-field pattern within the same file. No new file, new role, or new data-flow type is introduced by this phase.

## Metadata

**Analog search scope:** `api/services/admin_people.py`, `api/schemas/admin_people.py`, `api/routers/admin.py`, `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.server.ts`, `api/tests/test_admin_people_merge.py`
**Files scanned:** 6 (all directly named in CONTEXT.md canonical refs; no broader codebase search needed since CONTEXT.md pins exact line numbers and the pattern to mirror is intra-file)
**Pattern extraction date:** 2026-07-13
