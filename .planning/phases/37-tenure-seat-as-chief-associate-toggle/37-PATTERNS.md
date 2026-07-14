# Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text - Pattern Map

**Mapped:** 2026-07-14
**Execution mode:** generic-agent workaround for `gsd-pattern-mapper`
**Files analyzed:** 25 new/modified files and test seams
**Analogs found:** 25 / 25

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0020_rename_tenure_seat_to_office.py` | migration | transform | `alembic/versions/0019_question_number_nullable.py` | exact role |
| `scripts/migrate_tenure_offices.py` | utility | batch / database CRUD | `scripts/cleanup_leaked_test_rows.py` | exact role + safety flow |
| `alembic/versions/0021_constrain_tenure_office.py` | migration | validation / transform | `alembic/versions/0012_unpublished_enum_and_status_log.py` | role-match |
| `api/models/models.py` | model | CRUD | existing `CourtTenure` model in same file | exact |
| `api/schemas/admin_people.py` | schema | request-response validation | existing `TenureRow`, request and detail schemas in same file | exact |
| `api/schemas/speakers.py` | schema | response projection | existing `TenureDetail` in same file | exact |
| `api/services/admin_people.py` | service | CRUD / request-response | existing `_replace_tenures`, detail serialization, date-window role lookup | exact |
| `api/services/speakers.py` | service | transform / response projection | existing `_tenure_role_name` and speaker detail construction | exact |
| `api/services/admin_arguments.py` | service | transform / request-response | existing bench participant projection in same file | exact |
| `pipeline/commands/import_justices_csv.py` | utility/service | batch CRUD | existing section classification and idempotent tenure insert in same file | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` | route/action | request-response | existing save action and tenure JSON parsing in same file | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` | component/page | local state / form serialization | existing Bench/Advocate segmented control and tenure editor in same file | exact |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | route loader | response transform | existing tenure payload typing in same file | exact |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | component/page | read-only render | existing speaker/tenure typing in same file | exact |
| `app/src/lib/components/SpeakerPopover.svelte` | component | read-only render | existing tenure loop in same file | exact |
| `tests/test_migrate_tenure_offices.py` | test | batch / DB integration | `api/tests/test_cleanup_leaked_test_rows.py` and safety-script tests | role-match |
| `api/tests/test_admin_people_schemas_service.py` | test | request-response / CRUD | existing tenure schema/service cases in same file | exact |
| `api/tests/test_admin_people_phase25.py` | test | transform / CRUD | existing tenure stand-ins and bench-role assertions | exact |
| `api/tests/test_admin_arguments_service.py` | test | response projection | existing dated-tenure participant tests | exact |
| `api/tests/test_speakers_service.py` | test | transform | existing date-window/fallback matrix | exact |
| `api/tests/test_admin_dashboard_stats.py` | test | CRUD fixture | existing `CourtTenure(seat=...)` fixtures | exact |
| `pipeline/tests/test_import_justices_csv.py` | test | batch CRUD | existing Chief/Associate import and elevation tests | exact |
| `app/tests/tenure-office.browser.test.mjs` | test | event-driven browser interaction | existing `app/tests/*.browser.test.mjs` scripts | role-match |
| other active API/app/pipeline fixtures returned by `rg -n "\\bseat\\b"` | tests/fixtures | mixed | their current assertions and builders | exact |
| migration-history fixtures retaining legacy values | test fixtures | migration transform | numbered-seat cases in existing tests | exact, intentionally legacy-only |

## Pattern Assignments

### Staged Alembic migrations

**Analogs:** `alembic/versions/0019_question_number_nullable.py`; `alembic/versions/0012_unpublished_enum_and_status_log.py`

Use the repository's small, linear revision modules: imports and revision identifiers at top, narrow `upgrade()`/`downgrade()` bodies, and explicit Alembic operations. The first revision must only rename `seat` to `office` while leaving the string nullable, so legacy values remain readable. The second revision must preflight, create a named `CHECK`, then set `nullable=False`; downgrade reverses dependency order by dropping the named constraint before loosening/renaming. Do not perform silent data normalization in either migration.

Planner implementation contract:

```python
def upgrade() -> None:
    op.alter_column("court_tenures", "seat", new_column_name="office",
                    existing_type=sa.String(length=100), existing_nullable=True)

def downgrade() -> None:
    op.alter_column("court_tenures", "office", new_column_name="seat",
                    existing_type=sa.String(length=100), existing_nullable=True)
```

The contract revision should follow the same operation-oriented style, with a precondition query that fails clearly on null/noncanonical rows, `op.create_check_constraint(...)`, and `op.alter_column(..., nullable=False)`. This sequencing implements D-03, D-07, D-09, and D-17 without a compatibility alias.

### `scripts/migrate_tenure_offices.py` (utility, batch database CRUD)

**Analog:** `scripts/cleanup_leaked_test_rows.py`

**Imports and database guard** (`scripts/cleanup_leaked_test_rows.py:58-75`):

```python
import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

def _db_configured(url: str) -> bool:
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
```

**Bound SQL and deterministic detection** (`scripts/cleanup_leaked_test_rows.py:83-96`, `113-134`): use `text(...)` plus parameter dictionaries, return structured row dictionaries, and sort by stable identifiers. Never interpolate resolution values into SQL.

**Dry-run/execute and PgBouncer pattern** (`scripts/cleanup_leaked_test_rows.py:375-399`):

```python
engine = create_async_engine(
    database_url,
    connect_args={"statement_cache_size": 0},
    pool_size=2,
    echo=False,
)
async with engine.connect() as conn:
    report = await run_detection(conn)
print_report(report)
if not execute:
    print("Dry-run complete -- no rows changed.")
    return
```

Copy the safety shape, but strengthen it for D-06..D-09: default invocation is SELECT/report only; report every row with `id`, `original_office`, classification, and proposed canonical value; require explicit resolutions for blanks/unrecognized values; on `--execute`, open one transaction, re-read and compare originals (drift guard), validate every target as `chief`/`associate`, update all rows, verify the postcondition, and commit once. Any mismatch or exception rolls back everything. Use an anchored Associate-numbered rule, not substring inference.

### `api/models/models.py` and schemas (model/schema, CRUD + request-response)

**Analogs:** current `CourtTenure` (`api/models/models.py:126-138`), current `TenureRow` (`api/schemas/admin_people.py:25-42`), and speaker tenure response (`api/schemas/speakers.py:14-19`).

The ORM currently follows declarative columns and relationships:

```python
class CourtTenure(Base):
    __tablename__ = "court_tenures"
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False, index=True)
    seat = Column(String(100))
```

Rename the ORM attribute to `office` and declare the named database invariant consistently with the 0021 migration. Prefer canonical constants plus an exhaustive pure title helper shared by projections:

```python
OFFICE_TITLES = {"chief": "Chief Justice", "associate": "Associate Justice"}

def office_title(office: str) -> str:
    return OFFICE_TITLES[office]
```

Do not preserve `seat` as a property or Pydantic alias (D-17). Split contracts where needed: submitted tenure rows require `office: Literal["chief", "associate"]`; legacy-tolerant edit responses may carry an invalid original string so D-11 can be corrected. Never reuse response tolerance for writes.

### `api/services/admin_people.py` (service, atomic replace-all CRUD)

**Analog:** `_replace_tenures` (`api/services/admin_people.py:120-159`) and person-detail serialization (`api/services/admin_people.py:375-393`).

Current transaction ownership and replace-all flow:

```python
await session.execute(delete(CourtTenure).where(CourtTenure.person_id == person_id))
for t in tenures:
    session.add(CourtTenure(person_id=person_id, seat=t.seat or None, ...))
```

Retain the enclosing profile transaction and delete/reinsert shape, but remove the current blank-row skip (`if not (t.seat or t.start_date): continue`). Every submitted row must contain a canonical office, and validation must occur before destructive replacement. Serialize `office` everywhere. The date-window helper around `api/services/admin_people.py:798-812` should keep its inclusive boundary and missing-tenure behavior while mapping the selected canonical office to the formal title.

### Projection services and read-only consumers

**Analogs:** `_tenure_role_name` (`api/services/speakers.py:46-80`), tenure payload construction (`api/services/speakers.py:145-160`), and `SpeakerPopover.svelte:61-68`.

Keep the established selection algorithm: return the tenure covering `argued_date`; otherwise use the tenure with the highest start date. Change dictionaries and schemas from `seat` to `office`, then project with the single formal-title helper. Keep argument-specific field names such as `bench_role`/`argument_role`; D-16 forbids conflating those with tenure Office.

Current public rendering shape (`app/src/lib/components/SpeakerPopover.svelte:64-67`):

```svelte
{#each speaker.tenure as t}
  <p>{t.seat ?? 'Justice'} — {startYear}–{endYear}</p>
{/each}
```

Preserve the date layout, but render the formal `Chief Justice`/`Associate Justice` title supplied or derived from canonical `office`; valid records must not fall back to generic `Justice` (D-15).

### `pipeline/commands/import_justices_csv.py` (utility/service, batch CRUD)

**Analog:** the existing importer is the exact seam. Its section mapping at `pipeline/commands/import_justices_csv.py:45-52` classifies Chief and Associate sections; `_iter_csv_rows` yields the classification with each CSV row (`112-139`); insertion checks `(person_id, seat, start_date)` before adding (`151-224`).

Retain streamed CSV parsing, explicit section classification, idempotent query-before-insert, transaction ownership, and separate elevation rows. Change section values to canonical `chief`/`associate`, rename loop variables and dedup predicates to `office`, and keep `(person_id, office, start_date)` as the key. This directly preserves D-02 and enforces D-04/D-17.

### `app/src/routes/admin/people/[id]/+page.server.ts` (route/action, request-response)

**Analog:** existing tenure type/parsing/serialization (`+page.server.ts:6-25`, `155-171`) and action error handling.

The route currently parses the hidden JSON array and maps known fields before one profile PATCH. Preserve that allowlisted map and atomic PATCH, rename to `office`, and validate every row before calling the API. On invalid input, return `fail(400, ...)` with the full submitted values/tenures and first invalid row identity/index so the client rehydrates edits and focuses the correct group. Never coerce an invalid original or issue a partial request.

### `app/src/routes/admin/people/[id]/+page.svelte` (component/page, local state + form serialization)

**Analogs:** current tenure-row state/add/remove/hidden JSON (`+page.svelte:28-82`, `133-149`, `496-501`) and the existing Bench/Advocate segmented control (`452-488`).

Current local/atomic serialization pattern:

```svelte
let tenureRows = $state(data.person.tenures.map((t) => ({ ...t, _key: nextKey++ })));
function addTenureRow() { tenureRows.push({ ..., _key: nextKey++ }); }
<input type="hidden" name="tenures" form="save-form" value={JSON.stringify(tenureRows)} />
```

Copy the explicit local state, stable `_key`, external `save-form`, and one hidden JSON payload. Replace `seat` with `office`, default new rows to `associate`, and retain a separate `invalidOfficeOriginal` for legacy values. Replace the free-text input at lines 548-565 with a `fieldset`/`legend` and styled native radios. Native same-name radios provide idempotent one-of-two behavior and standard arrows. Apply the exact UI-SPEC colors, 44px target, `aria-describedby`/`aria-invalid`, persistent `role="alert"` copy, first-invalid focus, and failure rehydration. Do not copy the existing `aria-pressed` buttons without adding full radio keyboard semantics.

## Shared Patterns

### Transaction ownership

Services add/delete rows without an internal commit and rely on the route/service caller's transaction. The migration utility owns one explicit database transaction. Validate all office values before the first mutation, and never commit per row.

### Validation layers

Apply the same two-value invariant at every write seam: UI preflight for operator feedback, SvelteKit action validation, strict Pydantic write schema, importer constants, service guard, and named DB `CHECK` plus `NOT NULL`. The database is the final invariant, not the only validator.

### Canonical versus display values

Persist and transmit only `chief`/`associate`; map to `Chief Justice`/`Associate Justice` at projection/display boundaries. Editor labels remain compact `Chief`/`Associate`. Keep one mapping helper so API, argument-role projections, summaries, and popovers cannot diverge.

### Error handling and state recovery

Python operator utilities print actionable errors to stderr and exit nonzero; transaction exceptions roll back. SvelteKit actions use `fail(400, ...)` for operator-correctable validation and retain submitted form state. Inline editor errors use `role="alert"`, are associated with the Office group, and block the full save.

### Test style

Use pytest's existing focused modules and async DB fixtures. Extend the current date-window tables rather than replacing them. Preserve numbered/blank/unrecognized `seat` strings only in migration-specific fixtures; all active application fixtures and payload assertions become `office`. The browser test follows the repository's Node `.browser.test.mjs` convention and must cover selection, idempotence, keyboard behavior, Associate default, invalid original, focus, and failed-state restoration.

### Stale identifier gate

Finish with `rg -n "\\bseat\\b" api pipeline app tests`. Every remaining result must be migration history, migration utility compatibility input, or an explicitly documented legacy migration fixture. There is no active compatibility alias (D-17).

## Planner Grouping Guidance

1. **Wave 0:** create migration-utility and browser interaction tests plus disposable migration fixture.
2. **Storage/audit slice:** 0020 rename, audited atomic utility, 0021 constraint, model constants/helper.
3. **Backend/import/projection slice:** strict schemas, replace-all service, importer, speaker/admin-argument projections, focused pytest updates.
4. **Editor/read-only slice:** server action recovery, Office radios, case route typings, popover/formal display, browser/static checks.
5. **Final gate:** full pytest, frontend check, migration upgrade/normalize/constraint round trip, and reviewed stale-`seat` audit.

This grouping preserves the research recommendation's coordinated sequence and all D-01 through D-17 decisions.

## No Analog Found

None. Every Phase 37 seam has a direct in-place implementation pattern or a close repository analog. The new work is chiefly contract hardening and end-to-end renaming, not a new architectural style.

## Metadata

**Analog search scope:** `alembic/`, `scripts/`, `api/`, `pipeline/`, `app/`, `tests/`
**Primary analogs deeply inspected:** 9
**Pattern extraction date:** 2026-07-14
**Decision coverage:** D-01 through D-17
