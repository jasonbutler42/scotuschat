# Phase 38: Rethink Full Name vs. name-part fields in the people editor - Pattern Map

**Mapped:** 2026-07-15
**Files analyzed:** 19 new or modified files/file groups
**Analogs found:** 19 / 19

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `api/domain/person_names.py` (new) | utility/domain | transform | `pipeline/commands/import_justices_csv.py::reconstruct_full_name` | exact algorithm seam |
| `api/schemas/admin_people.py` | schema | request-response/validation | existing `PersonUpdate` / `PersonCreateRequest` | exact |
| `api/schemas/admin_jobs.py` | schema | request-response/validation | existing `PersonCreate` | exact |
| `api/models/models.py` | model | CRUD/persistence | `Argument.cover_metadata` plus `Person` name columns | role-match |
| `alembic/versions/0022_*.py` (new) | migration | batch/backfill | `0011_add_source_docket_cover_metadata.py` + `0006_add_structured_name_fields.py` | role-match |
| `api/services/admin_people.py` | service | CRUD/request-response | existing `update_person` / `create_person` | exact |
| `api/services/admin_jobs.py` | service | CRUD/request-response | existing `create_person_for_job` | exact |
| `pipeline/commands/import_justices_csv.py` | import adapter | batch/transform | existing `reconstruct_full_name` and manual override contract | exact |
| `pipeline/commands/import_convokit.py` | import adapter | batch/CRUD | existing Oyez-ID-first `_get_or_create_person` flow | exact |
| `pipeline/commands/seed_aliases.py` | seed | batch/CRUD | existing select-before-insert seed loop | exact |
| `app/src/lib/personNames.ts` (new) | frontend utility | transform | backend formatter plus shared parity fixtures | contract-match |
| `app/src/lib/components/CopyableExtractedValue.svelte` | component | event-driven/presentation | existing component itself | exact extension seam |
| `app/src/routes/admin/people/new/+page.server.ts` | route action | request-response | existing create action | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` | route action | request-response | existing save action/model-fields-set backend contract | exact |
| `app/src/routes/admin/people/new/+page.svelte` | page/component | event-driven/form | existing identity form | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` | page/component | event-driven/form | existing identity form | exact |
| `app/src/routes/admin/people/+page.svelte` and server/API list seams | page/filter | request-response/navigation | existing missing-field pill filter | exact |
| current `CopyableExtractedValue` consumers | component consumers | presentation | pipeline and argument detail consumers | exact |
| backend/pipeline/frontend tests | tests | unit/integration/static | existing admin people, job Phase 25, CSV import, and Phase 36 contract tests | role-match |

## Pattern Assignments

### `api/domain/person_names.py` (utility, transform)

**Analog:** `pipeline/commands/import_justices_csv.py:70-99`

**Canonical formatting pattern:**

```python
parts = [first]
if middle:
    parts.append(middle)
parts.append(last)
full_name = " ".join(parts)
if suffix:
    full_name = f"{full_name}, {suffix}"
return full_name
```

Move this behavior into a dependency-light domain module and broaden it to first-only or last-only names. Add one normalization helper that trims, collapses internal whitespace, and maps blank strings to `None`; do not alter capitalization or punctuation. The legacy splitter belongs beside the formatter so migration and fixture tests call ordinary Python rather than importing an Alembic revision. Return a structured result containing parts, confidence band, and reason; only a high-confidence, round-trip-equal result is eligible for automatic backfill.

Do not copy the current `api/services/admin_people.py:52-63` implementation: it requires both first and last and joins suffix without the required comma.

### `api/schemas/admin_people.py` and `api/schemas/admin_jobs.py` (schema, validation)

**Analog:** `api/schemas/admin_people.py:104-134`, `api/schemas/admin_jobs.py:88-104`

**Allow-list pattern:**

```python
class PersonUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    name_suffix: Optional[str] = None
```

Keep explicit Pydantic fields as the mass-assignment boundary. Remove `full_name` from writable request schemas, add the four parts to job mini-create, and validate that create has at least one of first/last after normalization. PATCH validation must permit omitted fields and explicit clearing; the service merges against stored values before enforcing the invariant. Response schemas continue exposing generated `full_name` for compatibility and add typed provenance/review fields needed by the UI.

### `api/models/models.py` and `alembic/versions/0022_*.py` (model/migration, persistence/backfill)

**Analogs:** `api/models/models.py:102-121`, `alembic/versions/0011_add_source_docket_cover_metadata.py:41-59`, `alembic/versions/0006_add_structured_name_fields.py:34-49`

**Column pattern:**

```python
full_name = Column(String(300), nullable=False)
first_name = Column(String(150), nullable=True)
last_name = Column(String(150), nullable=True)
middle_name = Column(String(150), nullable=True)
name_suffix = Column(String(50), nullable=True)
```

```python
op.add_column(
    "arguments",
    sa.Column("cover_metadata", postgresql.JSONB(), nullable=True),
)
```

Add a nullable JSONB provenance envelope and an explicit review flag/state using the existing SQLAlchemy/PostgreSQL types. Keep `full_name NOT NULL`. In `upgrade()`, add columns first, iterate deterministically, call the pure splitter, backfill parts plus canonical `full_name` only for confident round trips, and otherwise preserve `full_name` exactly while setting review. In `downgrade()`, drop only Phase 38 state; never attempt to reconstruct pre-migration operator data. Follow the reverse-order downgrade discipline illustrated by revision 0011.

### `api/services/admin_people.py` (service, CRUD)

**Analog:** `api/services/admin_people.py:411-494`

**Partial PATCH pattern:**

```python
fields_set = body.model_fields_set
if "first_name" in fields_set:
    person.first_name = body.first_name or None
if "last_name" in fields_set:
    person.last_name = body.last_name or None
if "middle_name" in fields_set:
    person.middle_name = body.middle_name or None
if "name_suffix" in fields_set:
    person.name_suffix = body.name_suffix or None
```

Preserve `model_fields_set`; it is the established omitted-vs-cleared contract. Change the core sequence to: load row/404 guard, merge submitted parts with stored parts, normalize, validate first-or-last, derive canonical name, assign parts and `full_name` atomically, clear name-review when authoritative parts become valid, commit, and refetch detail. `create_person` follows the same helper and the existing detail-refetch idiom (`api/services/admin_people.py:497-532`). Never accept a client-owned `full_name`.

**Directory attention analog:** `api/services/admin_people.py:185-228`

```python
missing_filters = {
    "first name": Person.first_name.is_(None),
    "last name": Person.last_name.is_(None),
    # ...
}
if missing in missing_filters:
    q = q.where(missing_filters[missing])
```

Add a fixed, non-interpolated `name review` predicate/state to this allow-list pattern and include the corresponding indicator in list rows.

### `api/services/admin_jobs.py` (service, job-scoped CRUD)

**Analog:** `api/services/admin_jobs.py:839-942`

Keep the job existence/status and participant scoping checks before mutation. In particular, preserve the `(job.argument_id, raw_speaker_label)` lookup and same-transaction participant update. Replace only the construction seam:

```python
is_justice = body.side == SideEnum.BENCH if body.side is not None else False
person = Person(full_name=body.full_name, role_id=role_id, is_justice=is_justice)
db.add(person)
await db.flush()
```

with the shared normalized-parts contract and derived compatibility name. Provenance prefill is blank-only; later extraction refresh updates the envelope without overwriting saved parts.

### Pipeline import and seed paths (adapters, batch CRUD)

**Justice CSV analog:** `pipeline/commands/import_justices_csv.py:54-99`. Retain `MANUAL_NAME_OVERRIDES` as an explicit escape hatch, but delegate normal formatting to the shared domain helper. Feed the CSV cells into both authoritative saved parts and provenance `{value, raw, confidence}`.

**ConvoKit analog:** `pipeline/commands/import_convokit.py:608-624`.

```python
result = await session.execute(select(Person).where(Person.full_name == full_name))
person = result.scalar_one_or_none()
if person is not None:
    if person.oyez_speaker_id is None:
        person.oyez_speaker_id = speaker_id
    return person
```

Preserve Oyez-ID-first resolution and the existing exact-name fallback during transition. New rows use shared formatting; matched rows receive refreshed provenance and only blank saved fields are prefilled. Do not let a canonicalization change create duplicates.

**Seed analog:** `pipeline/commands/seed_aliases.py:105-158`. Preserve select-before-insert idempotency and exact alias strings. Change seed fixtures to structured parts and derive `full_name`; keep byte-for-byte regression fixtures for all 13 names.

### `app/src/lib/personNames.ts`, people pages, and server actions (frontend transform/form)

The TypeScript helper is preview-only and mirrors the Python contract through shared fixture data. It must not become an independent authority. Both people pages should bind name-part inputs, derive a live read-only `Full Name` display, label it generated, and preserve attempted parts on action failure. Remove `full_name` from posted JSON in `new/+page.server.ts` (current authority leak is lines 64-91) and `[id]/+page.server.ts`; validate first-or-last at the action boundary for immediate feedback while retaining backend enforcement.

Use the existing identity layout in `new/+page.svelte:73-90` and `[id]/+page.svelte:227-245`, replacing the editable full-name input rather than adding a second representation.

### `app/src/lib/components/CopyableExtractedValue.svelte` and consumers (component, event-driven)

**Analog:** existing component, especially `CopyableExtractedValue.svelte:1-77`.

```svelte
let { value, copyLabel, variant = 'text' } = $props();
let isEmpty = $derived(value === null || value === undefined || value === '');

await navigator.clipboard.writeText(value);
if (attemptGeneration !== generation) return;
state = 'copied';
```

Extend props with optional confidence/raw/label while leaving this clipboard state machine intact. Stacked mode renders line 1 as `Extracted: {interpreted value}` with the button attached only to `value`; line 2 renders `{High|Medium|Low} confidence · Raw: {raw}`. Keep disabled `N/A`, tooltip/ARIA labels, live success, race invalidation, and error alert. Render all values/raw text through normal Svelte interpolation, never `{@html}`. Retain old text/pill rendering when stacked props are absent so consumers can migrate safely.

Current consumer seams are `app/src/routes/admin/pipeline/[job_id]/+page.svelte:328-343` and `app/src/routes/admin/arguments/[id]/+page.svelte:529`. Update every editable-destination hint to pass interpreted value, confidence, and exact raw source; copies still contain only interpreted value.

### `app/src/routes/admin/people/+page.svelte` (page/filter)

**Analog:** lines 23-35.

```typescript
function togglePillFilter(field: string) {
    if (data.missing === field) goto('/admin/people?tab=' + data.tab);
    else goto('/admin/people?tab=' + data.tab + '&missing=' + encodeURIComponent(field));
}
```

Add `Name review` using the existing single-select toggle and URL round-trip pattern. Preserve active tab and clear incompatible filters exactly as existing pills do.

### Tests (unit/integration/static)

Extend `api/tests/test_admin_people_schemas_service.py` for explicit allow-lists, first-only/last-only validation, partial PATCH merging, whitespace normalization, suffix comma, and rejection of client `full_name`. Extend `api/tests/test_admin_jobs_phase25.py` around its existing pre-mutation guards and same-transaction linkage. Extend `pipeline/tests/test_import_justices_csv.py` and ConvoKit tests for shared formatting, stable IDs/dedup, blank-only prefill, and provenance refresh.

Add migration tests for confident/ambiguous/single-part/particle/punctuation/suffix cases, exact preservation, deterministic review counts, and downgrade. Add shared Python/TypeScript formatter fixtures. For the Svelte component, keep Phase 36 behaviors and add stacked narrow/wide rendering, confidence-band validation, raw escaping, copy payload, keyboard, N/A, success/error, and stale-promise cases.

## Shared Patterns

### Authentication and authorization

No new public boundary is introduced. Keep existing admin routers/server actions and `X-Admin-Token` forwarding (`new/+page.server.ts:84-92`). The job mini-create must retain its job-state and argument-participant IDOR guards (`admin_jobs.py:874-908`).

### Transaction and validation ordering

Validate identities, state, all name parts, and migration confidence before mutation. Use `flush()` when later rows need a generated person ID, then commit once and refresh/refetch. This is the established `create_person_for_job` pattern (`admin_jobs.py:883-942`).

### Provenance envelope

Use one stable shape for every extracted field:

```json
{"value": "interpreted text", "raw": "exact source text", "confidence": "high"}
```

Saved operator fields and provenance are independent. Initial extraction fills only blank saved fields; later extraction replaces only the envelope. Bound string lengths and validate confidence as an enum/literal.

### Compatibility and display

`Person.full_name` remains non-null and readable by all current sort, display, alias, dedup, and response paths. Only server-owned writers change. Display stays canonical `First Middle Last, Suffix`; directory ordering may continue `coalesce(last_name, full_name)` (`admin_people.py:212-214`).

### Error handling

Domain helpers raise deterministic validation errors; HTTP routers translate them to 422 using existing conventions. Import paths preserve explicit warning/counter behavior rather than silently swallowing ambiguous data. Migrations fail loudly on invariant violations and must never blank or rewrite ambiguous legacy names.

## No Analog Found

None. The conservative legacy splitter is new domain logic, but its formatting half, migration structure, fixture-driven tests, and review UI all have close project analogs. The planner should specify splitter confidence rules in tests before authoring the backfill.

## Metadata

**Analog search scope:** `api/`, `alembic/versions/`, `pipeline/commands/`, `api/tests/`, `pipeline/tests/`, `app/src/lib/`, `app/src/routes/admin/`, and Phase 36 pattern artifacts.

**Strong analogs retained:** 5 pattern families (domain formatter, service mutation, migration/JSONB, import/seed, shared Svelte extracted-value UI).

**Pattern extraction date:** 2026-07-15
