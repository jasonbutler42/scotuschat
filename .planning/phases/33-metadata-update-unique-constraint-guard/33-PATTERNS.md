# Phase 33: metadata-update-unique-constraint-guard - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 13
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `api/services/admin_arguments.py` | service | CRUD | same file: `check_duplicate_argument`, `update_argument_metadata` | exact |
| `api/routers/admin.py` | controller | request-response | same metadata PATCH and duplicate-preflight route | exact |
| `pipeline/commands/ingest.py` | command/service | batch CRUD | same insert-time `IntegrityError` branch | exact |
| `pipeline/commands/import_convokit.py` | command/service | batch CRUD | same next-number query and flush fallback | exact |
| `pipeline/commands/parse.py` | command/service | batch transform/CRUD | same conditional docket update | exact |
| both admin `+page.server.ts` files | controller/action | request-response | each other''s mirrored metadata action | exact |
| `ArgumentDetailsCard.svelte` | component | event-driven request-response | same failure update and inline alert | exact |
| API service/route/nullable tests | test | CRUD/request-response/source-contract | established tests in same files | exact |
| ingest/import/parse tests | test | batch CRUD | established command tests in same files | exact |
| focused frontend source-contract test | test | source-contract | `test_question_number_nullable.py` | role-match |

`api/models/models.py:219-227` is the authoritative definition, not necessarily a behavioral edit: it names `uq_arguments_source_docket_question` and documents NULL uniqueness semantics.

## Pattern Assignments

### `api/services/admin_arguments.py` (service, CRUD)

**Analog:** same file.

**Canonical lookup** (`718-734`):

```python
result = await db.execute(
    select(Argument.id).where(
        Argument.source_docket == docket,
        Argument.question_number == question,
    )
)
row = result.scalar_one_or_none()
```

Generalize this parameterized query with optional `Argument.id != exclude_argument_id` and return the conflicting id. Preserve the existing preflight dictionary by delegating without exclusion.

**Effective values** (`832-889`): load the row first; normalize `source_dockets` by trim/drop-empty/order-preserving dedupe; synchronize `source_docket` to element zero; parse question text with current invalid-text behavior; then derive:

```python
final_docket = values_to_set.get("source_docket", argument.source_docket)
final_question = values_to_set.get("question_number", argument.question_number)
```

Check only a concrete pair and always exclude `argument_id`. Keep the established SQLAlchemy update plus `.execution_options(synchronize_session=False)` (`883-889`).

### `api/routers/admin.py` (controller, request-response)

**Analog:** metadata PATCH `1087-1114`; duplicate preflight `935-952`.

Keep router-level admin auth, `AsyncSession = Depends(get_db)`, service delegation, and the existing transaction boundary:

```python
try:
    result = await arguments_service.update_argument_metadata(db, argument_id, body)
except IntegrityError as exc:
    await db.rollback()
```

Classify the named constraint by walking `exc`, `exc.orig`, and chained causes/contexts with cycle protection. Roll back before re-querying. Only `uq_arguments_source_docket_question` maps to:

```python
HTTPException(status_code=409, detail={
    "code": "duplicate_argument",
    "message": f"An argument already uses docket {docket}, question {question}. Open conflicting argument.",
    "conflicting_argument_id": conflicting_id,
})
```

Other integrity failures remain sanitized and separately coded; never return rendered driver text.

### Offline writers (command/services, batch CRUD)

- **Ingest:** `pipeline/commands/ingest.py:396-414` constructs the pair, flushes, and converts duplicate failure into CLI-specific `ValueError`. Preserve wording/channel but narrow it to the named constraint; unrelated failures must not be duplicates.
- **ConvoKit:** `pipeline/commands/import_convokit.py:308-325` selects max question per docket; `425-465` creates, flushes, rolls back, increments `docket_question_conflict`, prints sanitized feedback, and returns. Preserve counter/next-number behavior while narrowing classification.
- **Parse:** `pipeline/commands/parse.py:367-376` fills docket only when NULL and uses `synchronize_session=False`. Pre-check the extracted docket plus stored question, exclude current id, and retain the no-overwrite predicate. Race fallback stays pipeline-specific, not HTTP-specific.

### Both admin `+page.server.ts` actions (controller/action, request-response)

**Analogs:** pipeline action `520-583`; argument action `223-251`.

Keep `formData()`, `getAll(''docket[]'')`, trimming, and server-derived argument ids:

```typescript
const dockets = (data.getAll(''docket[]'') as string[]).map((v) => v.trim()).filter(Boolean);
const question_number = ((data.get(''question_number'') as string) ?? '''').trim();
const argued_date = ((data.get(''argued_date'') as string) ?? '''').trim() || null;
```

Keep the authenticated PATCH body (`source_dockets`, `argued_date`, nullable `question_number`). Every failure branch echoes:

```typescript
{ saveError: ''Could not save. Try again.'', dockets, question_number, argued_date }
```

For status 409, parse JSON defensively; accept only `detail.code === ''duplicate_argument''` with usable message and numeric id, then `fail(409, { ...attemptedValues, conflict: detail })`. Malformed/network/other failures retain generic sanitized copy plus all attempted values.

### `ArgumentDetailsCard.svelte` (component, event-driven)

**Analog:** same component `5-39,63-78,211-234`.

Extend the existing `form` type with question/date and typed conflict. Like the docket effect, input values prioritize returned form values after failure. Preserve:

```typescript
if (result.type === ''failure'') await update();
else await update({ reset: false });
```

After failure update, await Svelte `tick()` and focus the bound existing alert. Reuse the one `role="alert"`, add `tabindex="-1"`, and render:

```svelte
<a href={`/admin/arguments/${form.conflict.conflicting_argument_id}`}
   target="_blank" rel="noopener noreferrer">Open conflicting argument</a>.
```

Do not create route-specific banners.

### Tests

- **Service:** follow `api/tests/test_admin_arguments_service.py` pytest and DB-gate conventions. Cover concrete collision, both partial-update directions, unchanged self, either-value NULL, and successful unique update.
- **Route:** follow `api/tests/test_admin_arguments_routes.py:39-86` dependency override cleanup, `ASGITransport`, and admin headers. Assert exact JSON, rollback-before-lookup, target race fallback, and sanitized non-target behavior.
- **Source contract:** `api/tests/test_question_number_nullable.py:48-59` is the lightweight `inspect.getsource` analog. Replace/augment the broad occurrence check with focused classification and inspect both actions/component because no frontend runner exists.
- **Pipeline:** extend the existing command test files; preserve idempotence/counter tests and add named-versus-other classification plus parse pre-check/self/NULL/race cases.

## Shared Patterns

### Constraint identity and NULL semantics

**Source:** `api/models/models.py:219-227`. Compare structured `constraint_name`, never message text. Only two non-NULL canonical values can collide.

### Rollback and recovery

**Sources:** `api/routers/admin.py:1105-1111`, `pipeline/commands/import_convokit.py:446-455`. Catch at transaction boundary, roll back before SQL, then query the committed winner. Never expose asyncpg text.

### Canonical pair

