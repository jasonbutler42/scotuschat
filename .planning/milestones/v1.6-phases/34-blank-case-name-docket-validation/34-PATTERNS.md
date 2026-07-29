# Phase 34: Blank case_name/docket_number validation - Pattern Map

**Mapped:** 2026-07-14
**Files analyzed:** 10 modified/test files
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/schemas/admin_arguments.py` | model/schema | request-response transform | Existing `ArgumentUpdate` / `MetadataUpdate` PATCH allow-lists in the same file | exact |
| `api/services/admin_arguments.py` | service | CRUD | `update_argument` and `update_argument_metadata` omission/collision flow in the same file | exact |
| `api/tests/test_admin_arguments_service.py` | test | request transform + CRUD | Existing schema allow-list and service update tests in the same file | exact |
| `api/tests/test_admin_arguments_routes.py` | test | request-response | Phase 33 metadata contract tests at lines 25-75 | exact |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | route/action | request-response transform | `parseDuplicateConflict` + `saveArgumentDetails` in the same file | exact |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | route/action | request-response transform | Mirrored `parseDuplicateConflict` + `saveJobMetadata` in the same file | exact |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | route component | enhanced-form event-driven | Existing Case form and alert at lines 125-216 | exact |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | component | enhanced-form event-driven | Existing failure reseed/focus/alert flow in the same file | exact |
| `app/src/lib/components/DocketPillInput.svelte` | component | event-driven transform | Existing pill add/remove and Enter handling in the same file | exact |
| `api/tests/test_question_number_nullable.py` (or a Phase 34 sibling regression file) | source-contract test | batch/static transform | Existing Phase 33 frontend contract assertions at lines 49-90 | role-match |

## Pattern Assignments

### `api/schemas/admin_arguments.py` (model/schema, request-response transform)

**Analog:** Existing PATCH schemas, lines 205-249. Preserve their mass-assignment fields and `Optional[...] = None` omission shape; add Pydantic v2 validators rather than changing the public allow-list.

```python
class ArgumentUpdate(BaseModel):
    case_name: Optional[str] = None
    docket_number: Optional[str] = None
    argued_date: Optional[str] = None

class MetadataUpdate(BaseModel):
    case_name: Optional[str] = None
    source_docket: Optional[str] = None
    source_dockets: Optional[list[str]] = None
```

Import `field_validator` beside `BaseModel`. Follow the research contract: validators run for explicitly supplied values, reject `None`, strip only outer whitespace, reject the stripped empty result, and return the normalized value. Omitted defaults must remain absent from `model_fields_set`. For `source_dockets`, normalize once in the schema: strip members, discard blanks, de-duplicate first-seen values, then reject an empty result. Keep `question_number` and `argued_date` behavior unchanged. When both singular and array docket fields are present, the array is authoritative.

### `api/services/admin_arguments.py` (service, CRUD)

**Analog 1:** `update_argument`, lines 518-563, already centralizes collision checks and derived writes.

```python
if body.docket_number is not None:
    new_docket = body.docket_number.strip()
    # collision query...
    lead_case.docket_number = new_docket
    lead_case.docket_number_norm = new_docket

if body.case_name is not None:
    lead_case.case_name = body.case_name.strip()
    if argument.status == ArgumentStatusEnum.DRAFT:
        new_slug = _derive_slug(lead_case.case_name)
```

Keep the collision/slug flow, but consume schema-normalized values directly so blank data cannot reach `_derive_slug`, `Case.docket_number`, or `Case.docket_number_norm`. Retain status-based slug freezing and existing transaction/error handling.

**Analog 2:** `update_argument_metadata`, lines 854-902, demonstrates omission-aware PATCH writes and array precedence.

```python
values_to_set: dict = {}
if "argued_date" in body.model_fields_set:
    values_to_set["argued_date"] = parsed_date
if body.source_dockets is not None:
    # current normalization loop
    values_to_set["source_dockets"] = normalized if normalized else None
    values_to_set["source_docket"] = normalized[0] if normalized else None
elif body.source_docket is not None:
    values_to_set["source_docket"] = body.source_docket or None
```

Move the normalization responsibility to the schema, then assign the validated array and its first item directly. Preserve the `if array ... elif singular ...` precedence, `model_fields_set` semantics for unrelated nullable fields, duplicate-pair lookup at lines 889-895, `synchronize_session=False`, and the existing rollback/constraint handling.

### Backend tests

**Analogs:** `api/tests/test_admin_arguments_service.py:154-172` for pure schema allow-list assertions; `api/tests/test_admin_arguments_routes.py:25-75` for isolated async route contracts using `AsyncMock`.

```python
def test_argument_update_allow_list() -> None:
    assert set(ArgumentUpdate.model_fields) == {
        "case_name", "docket_number", "argued_date"
    }
```

Add table-driven pure-model cases for omission versus explicit null, ASCII/Unicode whitespace, outer trimming, and internal-whitespace preservation. Assert `model_fields_set` explicitly. Cover collection normalization, all-empty rejection, first-seen de-duplication, and array-authoritative disagreement. Add route assertions that direct invalid PATCH bodies return standard FastAPI `422` bodies with `detail[*].loc` ending in the expected field and that mocked services are not called. Extend service tests to prove normalized values reach writes and empty arrays cannot clear canonical docket state.

### Both SvelteKit `+page.server.ts` actions (route/action, request-response transform)

**Analog:** Phase 33's structured parser in both files (`arguments/[id]`:68-81; `pipeline/[job_id]`:33 onward) validates unknown JSON structurally rather than trusting backend text.

```ts
function parseDuplicateConflict(value: unknown): DuplicateArgumentConflict | null {
    if (typeof value !== 'object' || value === null) return null;
    const detail = value as Record<string, unknown>;
    if (detail.code === 'duplicate_argument' && /* typed guards */) {
        return detail as unknown as DuplicateArgumentConflict;
    }
    return null;
}
```

Add a small typed 422-location parser alongside this helper. It must accept `unknown`, require an object with array `detail`, inspect each entry's `loc` array, accumulate (not `else if`) terminal fields, and never match `msg`. Map `case_name` to `caseNameRequired`; map `docket_number`, `source_docket`, and `source_dockets` to `docketRequired`. Keep the 409 duplicate parser as a separate branch and preserve generic handling for malformed/unrelated 422s.

For the Case action, the current lines 182-193 trim before transport. Instead retain raw `case_name` and `docket_number` for the failure payload and send them to FastAPI unchanged; successful API output remains authoritative and normalized. Every failure branch must echo both attempted values.

For metadata actions, retain the current action symmetry (`arguments/[id]`:244-284 and `pipeline/[job_id]`:541-616). Continue sending a full `source_dockets` array and returning `{ dockets, question_number, argued_date }` on failure. An empty `dockets: []` is meaningful state. On a loc-matched 422, add the docket-required flag/copy; do not disturb 409 conflict recovery.

### `app/src/routes/admin/arguments/[id]/+page.svelte` (route component, enhanced-form event-driven)

**Analog:** Existing Case form inputs and single inline alert, lines 125-216.

```svelte
<input id="case_name" name="case_name" value={data.argument.case_name} />
<input id="docket_number" name="docket_number" value={data.argument.docket_number} />
{#if form?.error}
    <p role="alert">{form.error}</p>
{/if}
```

Keep this alert region rather than adding a banner. Bind each input's value from the corresponding attempted form key when present (presence check, not truthiness), falling back to loaded data. Render both exact required messages in field order, apply `aria-invalid` and `aria-describedby` to each affected control, and use the existing red border treatment. After `await update()` and `tick()`, focus `case_name` first when both fail, otherwise focus `docket_number`; retain existing behavior for collision/generic errors.

### `app/src/lib/components/ArgumentDetailsCard.svelte` (component, enhanced-form event-driven)

**Analog:** Current recovery and focus sequence, lines 44-54 and 78-95.

```svelte
$effect(() => {
    if (form?.dockets) effectiveDockets = form.dockets;
});

if (result.type === 'failure') {
    await update();
    await tick();
    alertElement?.focus();
}
```

Change docket restoration to a key/presence check so `[]` replaces saved pills. Keep `await update()` before `await tick()`. Required docket failures focus the pill input via the child component API; conflicts and generic failures keep alert focus. Extend the existing one alert region (lines 240-262) with exact docket-required copy, and pass required/error/description state to the pill control. Do not add required behavior in readonly mode.

### `app/src/lib/components/DocketPillInput.svelte` (component, event-driven transform)

**Analog:** Current pill normalization and keyboard behavior, lines 19-30 and 98-124.

```ts
function addPill() {
    const v = docketInput.trim();
    if (v && !pills.includes(v)) pills = [...pills, v];
    docketInput = '';
}
```

Retain Enter's `preventDefault()` and add/de-duplicate behavior. Add props for invalid state and alert association plus a bindable/imperative focus contract targeting the visible text input. Expose enough state to the parent form to block enhanced submission when editable pills are empty, show the same server error state, and focus the text input. Apply `aria-invalid`, `aria-describedby`, and the red border only during the error; readonly remains disabled and non-required.

### Frontend source-contract regression tests

**Analog:** `api/tests/test_question_number_nullable.py:49-90` reads frontend files and asserts shared action/component invariants without introducing a frontend runner.

```python
def _frontend_source(relative_path: str) -> str:
    return (Path(__file__).parents[2] / "app" / relative_path).read_text(encoding="utf-8")
```

Use the same lightweight convention to assert both actions inspect structured `loc`, preserve all attempted values including `dockets: []`, and do not match `msg`; assert the Case form exposes both messages/focus order; assert the shared card uses a presence check and routes required focus to the pill input; assert the pill control retains Enter prevention and exposes required ARIA/focus behavior. Keep browser/conversational UAT for actual focus movement and client submission prevention.

## Shared Patterns

### Structured error routing

**Sources:** both page-server `parseDuplicateConflict` helpers and `api/tests/test_admin_arguments_routes.py:25-75`.

Treat response JSON as `unknown`, validate its shape, and route by stable machine structure. Required 422 routing uses `detail[].loc`; duplicate conflicts continue to use their existing typed 409 detail. Human-readable Pydantic `msg` is never a discriminator.

### Attempt preservation

**Sources:** metadata actions' `attemptedValues` payloads (`arguments/[id]`:245-281; `pipeline/[job_id]`:541-613) and `ArgumentDetailsCard.svelte:49-54,158-200`.

Capture attempts before API normalization, spread the same attempted payload into every failure result, and choose attempted versus saved values by property presence. Empty string, null, and empty array are valid attempted-state representations and must not trigger saved-value fallback.

### Authentication, IDOR, and transaction safety

No new endpoint or trust boundary is introduced. Preserve `X-Admin-Token`, route-param-derived argument IDs, the pipeline job-to-argument lookup, existing service collision checks, standard FastAPI 422 serialization, database rollback behavior, and `synchronize_session=False` on bulk updates.

## End-to-End Data Flow

```text
Case native inputs / DocketPillInput committed pills
  -> SvelteKit action captures raw attempted state
  -> PATCH JSON (route-derived id + admin token)
  -> Pydantic validates explicitly supplied required fields
       omission: absent from model_fields_set -> existing value untouched
       valid: outer-trimmed; internal whitespace preserved
       invalid: standard 422 detail[] with field loc
       docket array: blanks dropped, first-seen de-dupe, non-empty required
  -> service consumes normalized values
       array wins over singular; first item is canonical source_docket
       collision/dedup/slug logic remains unchanged
  -> on 422, action maps loc to field flags and returns all attempts
  -> component restores even blank/empty attempts, renders existing alert,
     marks invalid controls, and focuses the first invalid field
```

## No Analog Found

None. Every proposed modification extends an existing exact local pattern. The only new behavior is Pydantic required-value normalization and field-location parsing, both directly prescribed by `34-RESEARCH.md` and implemented inside existing schema/action structures.

## Metadata

**Analog search scope:** `api/schemas`, `api/services`, `api/tests`, `app/src/routes/admin`, `app/src/lib/components`
**Strong analogs read:** 8 source/test files plus Phase 34 context, research, and UI contract
**Pattern extraction date:** 2026-07-14
