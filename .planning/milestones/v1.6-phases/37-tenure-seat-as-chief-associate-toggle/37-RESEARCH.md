# Phase 37: Represent tenure Seat as a Chief/Associate toggle instead of free text - Research

**Researched:** 2026-07-14
**Domain:** PostgreSQL/SQLAlchemy contract migration plus SvelteKit accessible form integration
**Confidence:** HIGH
**Execution mode:** generic-agent workaround for `gsd-phase-researcher`

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Office model
- **D-01:** The active tenure model is binary: every tenure is either Chief or Associate. Numbered-seat distinctions will not remain in the active model.
- **D-02:** A Justice elevated from Associate to Chief retains two tenure periods: an Associate row ending at elevation and a Chief row beginning at elevation.
- **D-03:** Every saved tenure row must have exactly one valid office. Blank, unset, and Unknown are not valid persisted values.
- **D-04:** The Chief/Associate restriction applies to every write path, including the editor, API, imports, scripts, and migrations.

### Existing-data migration
- **D-05:** Recognized numbered values such as `Associate Justice Seat 3` normalize to Associate.
- **D-06:** The dry-run and execution audit report records every changed row and its original value; numbered-seat removal must never be silent.
- **D-07:** A blank or unrecognized legacy value blocks migration until it receives an explicit Chief/Associate resolution. The migration must not infer or default a value.
- **D-08:** Migration requires a non-writing dry run before a separate explicit execution action.
- **D-09:** Execution is atomic. Any validation or update failure rolls back all changes.

### Editor behavior
- **D-10:** A new tenure row defaults to Associate.
- **D-11:** If invalid data reaches the editor, show the original invalid value with a clear error and block the entire profile save until the operator explicitly selects Chief or Associate. Never coerce it silently.
- **D-12:** Office changes remain local form state and persist through the existing profile Save action, atomically with dates and other tenure changes.
- **D-13:** The segmented control always has exactly one selected option; clicking the active segment cannot deselect it.

### Terminology and display
- **D-14:** The editor segments are labeled `Chief` and `Associate`.
- **D-15:** Read-only tenure summaries and Justice popovers display the formal titles `Chief Justice` and `Associate Justice`.
- **D-16:** The tenure field is called `Office`, not `Role`, because `Role` is reserved for argument-specific roles.
- **D-17:** Rename `seat` to `office` end to end across the database column, ORM, schemas, API payloads, imports, services, tests, UI state, form serialization, and read-only consumers. This is not a UI-only label change and does not require a compatibility alias.

### the agent's Discretion
- Exact enum/check-constraint mechanism and internal constant names, provided only the two locked offices are writable.
- Audit-report file format and command naming, provided the required dry-run, original-value traceability, explicit execution, and atomicity contracts are met.
- Exact visual styling details, provided the control reuses the established segmented-toggle idiom and satisfies the locked behavior.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PEOPLE-08 | Tenure Seat is captured via a decision-backed UI control instead of unconstrained free text | The staged database constraint, strict API write schema, importer mapping, accessible editor radio group, formal display projection, and regression map below cover every persistence and presentation seam. [VERIFIED: `.planning/REQUIREMENTS.md`, codebase audit] |
</phase_requirements>

## Summary

Phase 37 is a contract migration across storage, API, pipeline, admin form state, argument-role projections, public popovers, and fixtures—not a local UI replacement. The repository currently stores nullable free-text `CourtTenure.seat`, accepts it through an all-optional Pydantic `TenureRow`, silently drops completely blank tenure rows, imports formal title strings, and returns raw seat strings to both admin argument-role fields and public tenure arrays. [VERIFIED: `api/models/models.py`, `api/schemas/admin_people.py`, `api/services/admin_people.py`, `api/services/speakers.py`, `pipeline/commands/import_justices_csv.py`]

Use a staged expand/migrate/contract sequence. First rename the column to `office` while it remains string-compatible so unresolved legacy values can still be read and shown. Add an explicit migration utility whose default mode is a non-writing audit and whose `--execute` mode revalidates every candidate inside one transaction before changing anything. Only after the audit has no unresolved rows should a final Alembic migration enforce `NOT NULL` plus a named database check allowing only canonical `chief` and `associate`. [VERIFIED: locked D-03..D-09; Alembic official operations API]

The live development database currently contains 121 tenure rows: 104 `Associate Justice` and 17 `Chief Justice`; no blank, null, numbered, or other values were returned by the grouped read-only audit on 2026-07-14. This does not weaken the migration contract: repository tests still contain `Associate Justice Seat 3`, and other deployed databases may contain values absent from the local development database. [VERIFIED: read-only PostgreSQL query; codebase grep]

**Primary recommendation:** plan three ordered implementation slices: (1) staged schema plus audited atomic data normalization, (2) strict backend/import/projection rename and formal-title mapping, and (3) accessible editor serialization/error recovery plus complete regressions.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Canonical office persistence and invariant | Database / Storage | API / Backend | The database must reject invalid future writes, while API validation gives useful operator-facing errors. [VERIFIED: D-03/D-04] |
| Legacy audit and normalization | Pipeline / operator CLI | Database / Storage | An offline operator tool owns dry-run/execute behavior; PostgreSQL transaction ownership provides atomicity. [VERIFIED: D-06..D-09; `scripts/cleanup_leaked_test_rows.py`] |
| Admin Office control and local correction state | Browser / Client | Frontend Server (SSR) | Svelte state owns unsaved selection and first-invalid focus; the server action validates serialized JSON and forwards the atomic profile PATCH. [VERIFIED: `+page.svelte`, `+page.server.ts`] |
| Write validation and tenure replacement | API / Backend | Database / Storage | Pydantic/service logic rejects invalid payloads before delete-and-reinsert, and the DB constraint is the final guard. [VERIFIED: `admin_people.py`] |
| Historical Justice CSV classification | Pipeline / operator CLI | Database / Storage | CSV section headers already determine Chief/Associate and tenure deduplication. [VERIFIED: `import_justices_csv.py`] |
| Argument-date role/title projection | API / Backend | Browser / Client | Backend date-window helpers choose the tenure; consumers should receive formal display titles rather than raw storage values. [VERIFIED: `admin_people.py`, `admin_arguments.py`, `speakers.py`] |
| Popover/read-only tenure rendering | Browser / Client | API / Backend | API supplies canonical office and dates; display mapping must consistently produce formal titles. Prefer one backend mapping helper reused by projections. [VERIFIED: D-15; `SpeakerPopover.svelte`] |

## Project Constraints

- Alembic is the sole DDL authority; do not call `Base.metadata.create_all`. [VERIFIED: `CLAUDE.md`]
- Pipeline operations remain offline/operator-only and are never exposed as HTTP endpoints. [VERIFIED: `CLAUDE.md`]
- Keep `statement_cache_size=0` for asyncpg engine creation behind Digital Ocean PgBouncer. [VERIFIED: `CLAUDE.md`, existing scripts]
- Keep public treatment apolitical and identical for every Justice; this phase only maps office titles. [VERIFIED: `CLAUDE.md`]
- Use Svelte 5 runes and the existing project-native visual idiom; add no component or icon dependency. [VERIFIED: `CLAUDE.md`, `37-UI-SPEC.md`]
- Preserve date-window semantics and the existing profile-level atomic Save flow. [VERIFIED: D-12/D-15, codebase]

## Standard Stack

No new package is required. Use the installed repository stack and native platform features. [VERIFIED: codebase/package manifests]

| Layer | Existing mechanism | Phase use |
|-------|--------------------|-----------|
| PostgreSQL 16 / Alembic | Named migrations and explicit SQL/operations | Rename `seat` to `office`, then enforce a named `CHECK (office IN ('chief','associate'))` and `NOT NULL` after data normalization. Alembic documents `alter_column(..., new_column_name=...)` and named check creation. [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html] |
| SQLAlchemy 2 async | `CourtTenure`, `AsyncSession`, transaction contexts | Rename ORM attribute, parameterize audit queries, and execute all normalization updates in one `engine.begin()` transaction. [VERIFIED: codebase] |
| Pydantic v2 | `BaseModel`, `Literal` or string enum validation | Split the strict write contract from legacy-tolerant read data if unresolved values must reach the editor. Do not let a permissive response shape become a permissive write shape. [CITED: https://docs.pydantic.dev/latest/api/standard_library_types/#literals] |
| SvelteKit 2 / Svelte 5 | `$state`, `$effect`, enhanced form action, hidden JSON | Rename state to `office`, default new rows to `associate`, preserve invalid original values separately, validate before fetch, and restore submitted state on `fail`. [VERIFIED: codebase] |
| Native radio semantics / WAI-ARIA APG | `<fieldset><legend><input type="radio">` preferred | Native radios provide one-selection behavior and standard keyboard interaction; if styled buttons are retained, implement radiogroup/radio/aria-checked plus roving focus exactly. [CITED: https://www.w3.org/WAI/ARIA/apg/patterns/radio/] |
| pytest + Svelte check/browser smoke | Existing `pytest.ini`, API/pipeline tests, `npm run check`, browser `.mjs` precedent | Cover schema, migration utility, services, importer, projections, serialization/error recovery, accessibility markup, and no-stale-`seat` grep. [VERIFIED: codebase] |

## Architecture Patterns

### Staged expand/migrate/contract flow

```text
Alembic rename-only migration
  seat VARCHAR NULL -> office VARCHAR NULL
             |
             v
Default dry-run audit (SELECT only)
  recognized rows -> proposed canonical mapping + original value
  unresolved rows -> blocking report + explicit resolution input required
             |
             v
Explicit --execute transaction
  re-read/revalidate all rows -> abort on any unresolved/drift -> update all -> commit
             |
             v
Final Alembic constraint migration
  precondition query -> CHECK chief/associate -> NOT NULL
             |
             v
Strict writers + canonical read projections + editor toggle
```

The rename migration should not convert the column directly to a PostgreSQL enum: strict ORM enum decoding or an immediate enum cast would prevent the editor and audit utility from reading unresolved original strings, contradicting D-07/D-11. Keep a string column and use a named check constraint after cleanup. [VERIFIED: locked decisions; existing nullable string model]

### Canonical internal values and formal projection

Use lowercase storage/API values (`chief`, `associate`) and one pure mapping helper for read-only titles:

```python
OFFICE_TITLES = {
    "chief": "Chief Justice",
    "associate": "Associate Justice",
}

def office_title(office: str) -> str:
    return OFFICE_TITLES[office]
```

This keeps compact editor labels separate from formal display copy and prevents raw enum leakage. [VERIFIED: D-14/D-15]

### Separate legacy-tolerant reads from strict writes

The existing `TenureRow` is reused for request and response and every field is optional. Replace this with a strict submitted-tenure schema (office required and constrained) and a response shape capable of carrying the original invalid string during the migration window. [VERIFIED: `api/schemas/admin_people.py`; D-03/D-11]

The service must no longer use `if not (office or start_date): continue`; once a tenure row is submitted, missing office is an error. Empty UI placeholder rows are not part of the locked model because adding a row immediately supplies `associate`. [VERIFIED: D-03/D-10; current `_replace_tenures`]

### Audit utility contract

Follow the repository's `scripts/cleanup_leaked_test_rows.py` safety pattern, adapted for updates: [VERIFIED: codebase]

1. Default invocation is read-only and emits a deterministic report sorted by tenure id.
2. Each row contains `id`, person identifier/name if useful, `original_office`, classification, and `proposed_office` or unresolved status.
3. Recognize exact known formal values and numbered Associate values with an anchored rule; do not use broad substring matching that could classify arbitrary text.
4. Accept explicit resolutions for unresolved row ids through a reviewable JSON file (recommended) rather than interactive guesses.
5. `--execute` requires the audit/resolution input, begins one database transaction, re-reads the rows, verifies original values still match the report (drift guard), verifies every result is canonical, then applies all updates.
6. Any mismatch, unresolved row, SQL error, or post-update invariant failure raises and rolls back the entire transaction.
7. Emit the same row-level audit on execution plus a committed/rolled-back outcome; never log credentials.

The final Alembic constraint migration must independently preflight for null or noncanonical values and fail with a clear remediation command; it must not normalize data itself. [VERIFIED: D-06..D-09]

### Accessible Office control

Prefer visually styled native radio inputs within a fieldset/legend because native semantics cover idempotent selection and keyboard behavior without a custom roving-focus implementation. The UI contract permits native radios where practical. [VERIFIED: `37-UI-SPEC.md`; W3C APG]

For the invalid legacy state, keep `office: null` plus `invalidOfficeOriginal: string | null` in local state. Neither option is selected until the operator acts. Associate the persistent error with the group, mark it invalid, focus the first unresolved group on attempted submit, and preserve the entire serialized tenure array in the failed action result. [VERIFIED: D-11; `37-UI-SPEC.md`]

### Component Responsibilities

| Area / likely file | Required change |
|--------------------|-----------------|
| `alembic/versions/0020_*.py` | Rename column only; preserve readable legacy strings. [VERIFIED: migration chain currently ends at 0019] |
| `scripts/migrate_tenure_offices.py` plus focused tests | Dry-run report, explicit resolution input, drift detection, atomic execute, postcondition. [VERIFIED: repository safety-script precedent] |
| `alembic/versions/0021_*.py` | Preflight, add named canonical check, set non-null; reversible downgrade should remove check and restore nullable/string name as explicitly designed. [VERIFIED: D-03/D-17] |
| `api/models/models.py` | `CourtTenure.office`, named check metadata, canonical constants/helper. [VERIFIED: codebase] |
| `api/schemas/admin_people.py`, `api/schemas/speakers.py` | Rename payload fields and make writes strict; no compatibility alias. [VERIFIED: D-17] |
| `api/services/admin_people.py` | Strict replacement, response rename, formal bench-role mapping; preserve transaction ownership. [VERIFIED: codebase] |
| `api/services/speakers.py`, `api/services/admin_arguments.py` | Rename tenure dictionaries and return formal titles without changing date-window/fallback semantics. [VERIFIED: D-15/D-17] |
| `pipeline/commands/import_justices_csv.py` | Section header -> canonical office; dedup key becomes `(person_id, office, start_date)`. [VERIFIED: current importer] |
| `app/.../people/[id]/+page.server.ts` | Parse/validate `office`; return submitted rows and row index/key on failure; never send invalid PATCH. [VERIFIED: D-11; current action loses submitted tenure state on fail] |
| `app/.../people/[id]/+page.svelte` | Office radios, Associate default, invalid-original state, error/focus behavior, hidden JSON rename, UI-SPEC styling. [VERIFIED: UI contract] |
| `app/.../cases/...`, `SpeakerPopover.svelte` | Rename types and render formal title only. [VERIFIED: codebase] |
| API/pipeline/frontend fixtures | Replace `seat` keys and numbered fixture expectations; retain dedicated migration fixtures for numbered/blank/unrecognized values. [VERIFIED: grep inventory] |

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | PostgreSQL `court_tenures.seat`; live dev grouping is 104 `Associate Justice`, 17 `Chief Justice`. Other environments may contain numbered/blank/unrecognized values. [VERIFIED: read-only DB audit, model] | Rename by Alembic; audited explicit data migration; final constraint. |
| Live service config | No application/external-service configuration key named `seat` was found; the value is ordinary DB/application payload data. [VERIFIED: repository-wide grep] | None beyond coordinated code/schema deployment. |
| OS-registered state | No task/service registration referring to tenure `seat` was found. [VERIFIED: repository-wide grep; phase scope] | None. |
| Secrets/env vars | No tenure seat/office environment variable or secret name was found. [VERIFIED: repository-wide grep] | None. |
| Build artifacts / installed packages | Generated SvelteKit/types and Python caches can retain old identifiers locally, but no installed package owns this contract. [VERIFIED: project layout] | Run `svelte-kit sync` through `npm run check`; clear only generated caches if stale diagnostics appear. Do not edit generated artifacts. |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Binary selection semantics | Checkbox/switch or two independent toggle buttons | Native grouped radios styled as segments | Office is one-of-two, not on/off; native radios make active-click idempotent and keyboard behavior standard. [CITED: W3C APG] |
| Persistence invariant | Frontend-only validation | Pydantic strict input plus named PostgreSQL check and NOT NULL | Imports/scripts can bypass the browser. [VERIFIED: D-04] |
| Transaction rollback | Manual compensating updates | One SQLAlchemy/PostgreSQL transaction | Automatic rollback is the required all-or-nothing mechanism. [VERIFIED: D-09; existing scripts] |
| Legacy inference | Fuzzy matching/default-to-Associate | Explicit allowlist normalization plus resolution file | Broad matching can silently destroy distinctions or accept garbage. [VERIFIED: D-05..D-07] |
| Display wording | Scattered inline ternaries/fallback `Justice` | One exhaustive office-to-formal-title helper | Prevents raw values and inconsistent copy across projections. [VERIFIED: D-15] |

## Common Pitfalls

### Immediate strict enum conversion
**Failure:** migration or ORM cannot read unresolved legacy values, so the audit/editor cannot expose originals.  
**Avoid:** string-compatible rename first, audited normalization second, check/non-null contract last. [VERIFIED: D-07/D-11]

### Reusing a permissive read schema for writes
**Failure:** `office=None` or arbitrary strings reach `_replace_tenures`, and blank rows are silently discarded.  
**Avoid:** strict write model and explicit service rejection; keep any legacy-tolerant field isolated to response/edit-load handling. [VERIFIED: current schema/service]

### Normalizing only production rows
**Failure:** local DB succeeds but numbered fixtures, import dedup keys, argument-role expectations, and popover types still encode `seat`.  
**Avoid:** retain migration-specific legacy fixtures while renaming every active contract occurrence. [VERIFIED: repository grep]

### Mixing canonical values and formal titles
**Failure:** the database stores `Chief Justice` in one path and `chief` in another, causing check failures or raw UI leakage.  
**Avoid:** canonical storage/API enum; formal title only at projection/display boundary. [VERIFIED: D-14/D-15]

### Losing unsaved form state on validation failure
**Failure:** SvelteKit `fail()` currently returns only an error; rerender may rebuild state from loaded data and erase corrections/other edits.  
**Avoid:** return submitted values/tenures from the action and explicitly rehydrate state; test server and client failure recovery. [VERIFIED: current `+page.server.ts`; UI-SPEC]

### Calling current `aria-pressed` buttons a radio group without keyboard work
**Failure:** two buttons create two tab stops and do not provide required arrow behavior.  
**Avoid:** native radio inputs, or full radiogroup/radio/aria-checked/roving-tabindex handling. [CITED: https://www.w3.org/WAI/ARIA/apg/patterns/radio/]

### Conflating argument role with tenure office
**Failure:** renaming `bench_role`/`argument_role` indiscriminately changes public/admin contract beyond scope.  
**Avoid:** rename stored tenure `seat` to `office`, but keep argument-role field names where they describe argument-specific projections; only their derived display value changes to formal office title. [VERIFIED: D-16/D-17; current schemas]

### Unsafe downgrade
**Failure:** downgrade relabels canonical values without documenting information loss or leaves a constraint referencing the wrong column.  
**Avoid:** drop named constraint before column rename; map canonical values back to formal strings only if downgrade contract explicitly requires old application compatibility. Test upgrade/downgrade SQL ordering. [VERIFIED: Alembic migration patterns]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Backend/pipeline | pytest via `pytest.ini`; configured project full command `.\.venv\Scripts\python.exe -m pytest` [VERIFIED: config] |
| Frontend static | `npm run check` from `app` [VERIFIED: `app/package.json`] |
| Frontend interaction precedent | Node browser test in `app/tests/*.browser.test.mjs`; no general component-test framework is installed. [VERIFIED: file/package inventory] |
| Database | PostgreSQL test DB fixtures with async SQLAlchemy; tests skip when DB URL is absent. [VERIFIED: conftest files] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PEOPLE-08 | Strict API accepts only chief/associate and round-trips `office` | unit/integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py -x` | Exists; update/add cases |
| PEOPLE-08 | Dry run writes nothing, reports every recognized change/original, blocks unresolved, execute is atomic and drift-safe | DB integration | `.\.venv\Scripts\python.exe -m pytest tests/test_migrate_tenure_offices.py -x` | Wave 0 gap |
| PEOPLE-08 | CSV maps both sections to canonical office and remains idempotent/elevation-safe | DB integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_justices_csv.py -x` | Exists; update |
| PEOPLE-08 | Argument-date projections and public tenure payloads return formal titles with unchanged window semantics | unit/integration | `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py api/tests/test_admin_arguments_service.py -x` | Exists; update |
| PEOPLE-08 | Editor serializes `office`, defaults new rows to Associate, blocks/focuses invalid legacy state, preserves failed state | browser/static | `node app/tests/tenure-office.browser.test.mjs` then `npm run check --prefix app` | Wave 0 gap |
| PEOPLE-08 | Active code has no `seat` contract residue outside migration/history fixtures | static audit | `rg -n "\\bseat\\b" api pipeline app tests` | command-only gate |

### Sampling Rate

- **Per migration task:** focused migration utility tests plus `alembic upgrade head` against a disposable/test database. [VERIFIED: project migration architecture]
- **Per backend task:** affected pytest modules under 30 seconds where possible. [VERIFIED: test inventory]
- **Per frontend task:** `npm run check --prefix app` plus the focused browser test. [VERIFIED: package scripts]
- **Phase gate:** full `.\.venv\Scripts\python.exe -m pytest`, frontend check, migration round-trip/preflight, and final stale-identifier grep. [VERIFIED: config/phase scope]

### Wave 0 Gaps

- [ ] `tests/test_migrate_tenure_offices.py` — recognized/formal/numbered/blank/unrecognized cases, non-writing dry run, explicit resolutions, drift abort, rollback on injected failure, exact audit fields.
- [ ] `app/tests/tenure-office.browser.test.mjs` — Office group semantics, selection/idempotence/keyboard behavior, Associate default, invalid-original message, first-invalid focus, submitted-state recovery.
- [ ] Disposable migration fixture/helper covering 0019 -> rename stage -> data utility -> constraint stage and downgrade ordering.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Existing only | Admin editor/API retains the existing admin-token boundary; no auth changes. [VERIFIED: `+page.server.ts`] |
| V3 Session Management | No new behavior | No session contract changes. [VERIFIED: phase scope] |
| V4 Access Control | Existing only | Migration remains offline/operator-only; do not expose it through FastAPI. [VERIFIED: project constraint] |
| V5 Input Validation | Yes | Strict Pydantic write enum/Literal, service validation, parameterized SQL, named DB check and NOT NULL. [VERIFIED: D-03/D-04] |
| V6 Cryptography | No | No secrets or cryptographic behavior introduced. [VERIFIED: phase scope] |

### Known Threat Patterns

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Arbitrary office string through non-UI writer | Tampering | Strict API/import constants plus DB invariant. [VERIFIED: D-04] |
| Resolution-file SQL injection | Tampering | Parse JSON as data, validate ids/enums, and use bound parameters; never interpolate values into SQL. [VERIFIED: existing script patterns] |
| Stale audit applied after data changes | Tampering | Re-read and compare original values inside execute transaction; abort on drift. [VERIFIED: cleanup-script precedent] |
| Partial normalization | Integrity/repudiation | One transaction and row-level before/after audit with explicit outcome. [VERIFIED: D-06/D-09] |
| Sensitive connection details in report | Information disclosure | Report row ids/original values only; never print DATABASE_URL/password. [VERIFIED: environment model] |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | None. Recommendations are grounded in locked decisions, current code/database inspection, and official Alembic/Pydantic/W3C documentation. | — | — |

## Open Questions

No product decision remains open. The planner may choose exact script/report names and check-constraint names under the explicit discretion already granted. [VERIFIED: CONTEXT.md]

One implementation sequencing detail must be explicit in the plan: whether application code is deployed while the database is at the rename-only stage or the entire phase is executed as a coordinated maintenance operation. For this single-operator project, a coordinated sequence is recommended: rename migration -> dry-run/review -> explicit execute -> constraint migration -> application/tests. This avoids maintaining a prohibited compatibility alias. [VERIFIED: D-17; current architecture]

## Environment Availability

| Dependency | Required By | Available | Version / State | Fallback |
|------------|-------------|-----------|-----------------|----------|
| Node.js | Svelte check/browser test | Yes | v24.15.0 | — |
| npm | frontend scripts | Yes | 11.12.1 | — |
| Project Python venv | API/pipeline/tests | Yes | repository `.venv` executable works | — |
| PostgreSQL client/server | audit/migrations/tests | Yes | `psql` installed; local server accepting connections on 5432 | use configured test DB for destructive/migration tests |
| Context7 | documentation seam | No | CLI/MCP unavailable | Official documentation fetched directly; research cache write also blocked by sandbox EPERM. |

**Missing dependencies with no fallback:** none.

## Sources

### Primary (HIGH confidence)

- Locked Phase 37 context and approved UI specification. [VERIFIED: `.planning/phases/37-*/37-CONTEXT.md`, `37-UI-SPEC.md`]
- Current repository code, migrations, tests, and live read-only grouped database audit. [VERIFIED: codebase/PostgreSQL]
- Alembic Operations official documentation: column rename and named check operations. [CITED: https://alembic.sqlalchemy.org/en/latest/ops.html]
- Pydantic official standard-library types documentation. [CITED: https://docs.pydantic.dev/latest/api/standard_library_types/#literals]
- W3C WAI-ARIA Authoring Practices radio group pattern. [CITED: https://www.w3.org/WAI/ARIA/apg/patterns/radio/]

### Secondary (MEDIUM confidence)

- None required.

### Tertiary (LOW confidence)

- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no dependency change; current manifests and official docs verified.
- Architecture: HIGH — all active `seat` seams and the live database distribution were inspected.
- Migration safety: HIGH — derived directly from D-05..D-09 and an existing repository dry-run/atomic/drift-guard script.
- UI behavior: HIGH — approved UI-SPEC plus official W3C radio pattern.
- Pitfalls: HIGH — each maps to a current permissive or raw-string code path.

**Research date:** 2026-07-14  
**Valid until:** 2026-08-13 (stable internal architecture; refresh if Phase 38/39 changes tenure projections first)
