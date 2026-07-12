# Phase 27: People Admin - Pattern Map

**Mapped:** 2026-07-08
**Files analyzed:** 8 (5 modified, 1 new frontend route, 2 backend additions inline in existing files)
**Analogs found:** 8 / 8 (all are self-analogs — this phase substantially rewrites its own predecessor files; the closest "analog" for each is almost always the current version of that same file)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/src/routes/admin/people/+page.svelte` | component (list) | request-response | itself (current version) | exact — restructure in place |
| `app/src/routes/admin/people/+page.server.ts` | route/load | request-response | itself (current version) | exact — add `tab`/`missing` params |
| `app/src/routes/admin/people/[id]/+page.svelte` | component (form) | CRUD | itself (current version) | exact — restructure in place |
| `app/src/routes/admin/people/[id]/+page.server.ts` | route/load + actions | CRUD | itself (current version) | exact — extend `save` action, add tenure fields |
| `app/src/routes/admin/people/new/+page.svelte` | component (form, new) | CRUD (create) | `app/src/routes/admin/people/[id]/+page.svelte` | role-match — shares template per D-07 |
| `app/src/routes/admin/people/new/+page.server.ts` | route/load + actions (new) | CRUD (create) | `app/src/routes/admin/people/[id]/+page.server.ts` `save` action + `api/services/admin_jobs.py::create_person_for_job` (for the create-not-update pattern) | role-match |
| `api/services/admin_people.py` (`list_people`, `_missing_fields`, `_replace_tenures`, new `create_person`) | service | CRUD | itself (current version); create fn modeled on `api/services/admin_jobs.py::create_person_for_job` (lines 798-833) minus job-scoping | exact for edits; role-match for new create fn |
| `api/schemas/admin_people.py` (`TenureRow`, `PersonUpdate`, new `PersonCreate`-equivalent) | model/schema | CRUD | itself (current version); `PersonCreate` schema already exists in `api/schemas/admin_jobs.py` (used by `create_person_for_job`) as the closest sibling shape | role-match |
| `api/routers/admin.py` (new `POST /people`) | route/controller | request-response | `POST /jobs/{job_id}/people` (`create_person_for_job`, lines 592-616) | exact — same status_code/response_model idiom, minus `job_id` path param |
| `api/models/models.py` (`Person.birthdate` new column) | model | migration | `Person.is_justice` (Phase 18, migration 0010) and `CourtTenure.appointed_by`/`appointing_president_party` (Phase 22, migration 0013) — both are "add nullable column via new migration" precedents | exact pattern, needs new Alembic revision |

## Pattern Assignments

### `app/src/routes/admin/people/+page.server.ts` (route/load, request-response)

**Analog:** itself, current version (full file already read above)

**Existing query-param toggle pattern to extend for `tab` (D-01) and `missing` (D-04):**
```typescript
export const load: PageServerLoad = async ({ fetch, url }) => {
	const incomplete = url.searchParams.get('incomplete') === '1'; // → DELETE this line (D-04 removes toggle)
	const tenure_gaps = url.searchParams.get('tenure_gaps') === '1'; // → KEEP, Bench-tab-only per UI-SPEC

	const params = new URLSearchParams();
	if (incomplete) params.set('incomplete', '1');
	if (tenure_gaps) params.set('tenure_gaps', '1');
	const queryString = params.toString();
	const apiUrl = `${FASTAPI_BASE_URL}/api/admin/people${queryString ? '?' + queryString : ''}`;
	...
};
```
**New shape (pattern to follow):** same `URLSearchParams` builder, add `tab` (default `'bench'` per D-03) and `missing` (single field name, replacing `incomplete`). Pass `is_justice` filter (tab→`is_justice=true|false`) to the backend query param set, matching the existing `if (x) params.set(...)` idiom exactly.

**Type to extend:**
```typescript
type PersonListItem = {
	id: number;
	full_name: string;
	role_id: number | null;
	role_name: string | null;
	missing: string[];
	is_justice: boolean;
};
```
Add `argument_count: number | null` (Advocate tab column, PDIR-04) and tenure-coverage fields (Bench tab column, PDIR-03) — service must compute and add these to `list_people()`'s returned dict shape (see service section below).

---

### `app/src/routes/admin/people/+page.svelte` (component, list, request-response)

**Analog:** itself — the existing toggle-switch pattern (lines 6-27, 77-109) is the direct template for the click-to-filter pill's `goto()` navigation idiom, even though the toggle UI itself is being removed:

```svelte
let checked = $derived(data.incomplete ?? false);
function handleToggle() {
	if (checked) {
		goto('/admin/people');
	} else {
		goto('/admin/people?incomplete=1');
	}
}
```
Reuse this exact `$derived` + `goto()` shape for both the Bench/Advocate tab buttons (D-01) and the click-to-filter pills (D-04) — same one-param-toggle idiom, just parameterized by pill field name instead of a boolean.

**Existing missing-field pill markup (lines 193-215) — direct template for D-04/D-05/D-06, convert `<span>` to `<button>` per UI-SPEC Interaction Contract:**
```svelte
{#if person.missing.length > 0}
	<span aria-label="Missing: {person.missing.join(', ')}" style="display: flex; gap: 4px; flex-wrap: wrap;">
		{#each person.missing as field}
			<span style="display: inline-block; background-color: rgba(245,158,11,0.15); border: 1px solid #f59e0b; color: #f59e0b; border-radius: 4px; padding: 4px 8px; font-size: 14px; font-weight: 400; line-height: 1.4;">{field}</span>
		{/each}
	</span>
{/if}
```
Per UI-SPEC lines 130-135: swap outer/inner `<span>` for `<button>` with `aria-pressed`, `aria-label="Filter by {field}"`, `onclick={() => togglePillFilter(field)}` (a `goto()` call per the toggle pattern above), and add the active-state solid-fill style variant.

**Existing table + empty-state structure (lines 113-265)** is the direct template for both Bench and Advocate tab tables — same `{#if data.people.length > 0} <table>...{:else}...{/if}` shape, just swap column definitions per tab (UI-SPEC "Screen Contract — People List" §Bench/Advocate tab columns) and add the four empty-state branches (UI-SPEC Copywriting Contract).

**Existing "Justice" badge chip (line 177)** — reuse verbatim for the Bench tab Name column:
```svelte
{#if person.is_justice}<span style="display: inline-block; background-color: rgba(147,197,253,0.15); border: 1px solid #93c5fd; color: #93c5fd; border-radius: 4px; padding: 2px 6px; font-size: 14px; font-weight: 400; line-height: 1.4; margin-left: 8px;">Justice</span>{/if}
```

---

### `app/src/routes/admin/people/[id]/+page.svelte` (component, form, CRUD) → also base for `new/+page.svelte`

**Analog:** itself, current version (full file read above)

**Tenure-rows `$state` array pattern (Pattern 1, lines 76-96) — direct base to extend with `appointed_by`/`appointing_president_party` (D-16) and disabled `reason_ended` (D-12/D-19):**
```typescript
interface TenureRow {
	_key: number;
	id?: number;
	seat: string;
	start_date: string;
	end_date: string;
}
let nextKey = $state(1);
let tenureRows = $state<TenureRow[]>(
	(data.person.tenures ?? []).map((t) => ({
		_key: nextKey++,
		seat: t.seat ?? '',
		start_date: t.start_date ?? '',
		end_date: t.end_date ?? '',
	}))
);
function addTenureRow() {
	tenureRows.push({ _key: nextKey++, seat: '', start_date: '', end_date: '' });
}
function removeTenureRow(index: number) {
	tenureRows.splice(index, 1);
}
```
New `TenureRow` needs `appointed_by: string`, `appointing_president_party: string` (free-text, D-16); the sub-card wrapper per D-18 replaces the flat `<div style="display:flex">` row (lines 413-477) — restructure each `{#each}` iteration into a bordered sub-card containing Start/End (2-col), Appointing President (full-width), President's Party + disabled Reason Left (2-col), Remove button — per UI-SPEC "Screen Contract — Create/Edit" item 5.

**Hidden JSON field pattern (Pitfall 3, line 489) — unchanged, extend serialized shape:**
```svelte
<input type="hidden" name="tenures" value={JSON.stringify(tenureRows)} />
```

**`isJustice` state + `{#if isJustice}` conditional (lines 42, 134, 301, 402) — direct base for the Person Type card's Bench/Advocate segmented toggle (D-13) and `slide` transition (D-11):**
```svelte
let isJustice = $state<boolean>(data.person.is_justice ?? false);
...
{#if isJustice}
  <!-- Role select + Court Tenure card -->
{/if}
```
Replace the checkbox at lines 212-215 with a segmented toggle (two `<button>`s, same active/inactive styling idiom as the toggle-switch already in `+page.svelte`); replace the raw `{#if isJustice}` with `{#if isJustice}<div transition:slide>...</div>{/if}` (Svelte built-in `slide` import) wrapping Birth Date/Death Date/Tenure Periods, per D-11/D-13/D-15. **Delete the Role `<select>` block entirely (lines 300-398)** — D-10 drops Role from this card; do not carry `selectedRoleId`/`showAddRoleForm`/`ADD_NEW_ROLE_SENTINEL`/`handleRoleChange`/`cancelAddRole`/`createRole` action forward into the new Person Type card at all (that inline-role-creation machinery is fully removed, not migrated).

**Save-button + `use:enhance` submitting-state idiom (lines 185-199, 615-623) — reuse verbatim for "Save Person" per Copywriting Contract rename:**
```svelte
<form id="save-form" method="POST" action="?/save" use:enhance={() => {
	saveSubmitting = true;
	return async ({ result, update }) => {
		saveSubmitting = false;
		await update();
	};
}}>
```

**Merge/Delete cards (lines 625-764)** — unchanged verbatim on `/admin/people/[id]`; **conditionally omitted** on `/admin/people/new` (Claude's Discretion item 3) — wrap both blocks in `{#if data.person.id}` (or equivalent "not a new/unsaved record" guard) when reusing this template for the create route.

**Photo card (lines 498-606)** — unchanged pattern; per UI-SPEC item 3, planner's call on pre-save gating for `/admin/people/new` (either hide entirely or render disabled-submit with initials placeholder — this file's existing avatar-circle/initials-fallback markup, lines 536-550, is the exact block to reuse either way).

---

### `app/src/routes/admin/people/[id]/+page.server.ts` (route/load + actions, CRUD) → base for `new/+page.server.ts`

**Analog:** itself, current version (full file read above)

**`save` action (lines 148-213) — direct template to extend with `appointed_by`/`appointing_president_party` per tenure row and to strip role_id handling entirely (D-10):**
```typescript
save: async ({ request, params, fetch }) => {
	const formData = await request.formData();
	const full_name = ((formData.get('full_name') as string) ?? '').trim();
	// role_id_raw / role_id parsing → DELETE (D-10 drops Role field)
	const first_name = ((formData.get('first_name') as string) ?? '').trim() || null;
	...
	const is_justice = formData.get('is_justice') === 'on'; // → replace with segmented-toggle value, not checkbox 'on'/absent
	const tenuresRaw = (formData.get('tenures') as string) ?? '[]';
	if (!full_name) return fail(400, { error: 'Full name is required.' });
	let tenuresParsed: TenureRowClient[] = JSON.parse(tenuresRaw);
	const tenures = tenuresParsed.map(({ seat, start_date, end_date }) => ({ seat, start_date, end_date }));
	...
	res = await fetch(`${FASTAPI_BASE_URL}/api/admin/people/${params.id}`, {
		method: 'PATCH',
		headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
		body: JSON.stringify({ full_name, role_id, tenures, first_name, last_name, middle_name, name_suffix, is_justice }),
	});
	...
	throw redirect(303, '/admin/people/' + params.id);
},
```
For `new/+page.server.ts`'s create action: same body-construction shape, but `method: 'POST'` to the new `${FASTAPI_BASE_URL}/api/admin/people` endpoint (no `params.id`), validate D-08's minimum (full_name **and** an explicit Bench/Advocate choice) before the fetch call — mirrors this file's existing `if (!full_name) return fail(400, ...)` guard, add a second guard for the Bench/Advocate choice per UI-SPEC's "Choose Bench or Advocate to continue." copy. Redirect target becomes `/admin/people/{new_id}` using the id from the JSON response (identical redirect-after-create idiom to `merge`'s `redirect(303, '/admin/people/' + target_id)`, lines 360-361).

**Error-handling idiom (fetch try/catch → `fail(502, ...)`, then `!res.ok` → `fail(422, ...)`) — reuse verbatim, this project-wide pattern appears in every action in this file (`save`, `createRole`, `photo`, `merge`, `delete`).**

**Photo/Bio separate-form pattern (lines 269-322, Pitfall 7 extended)** — unchanged; carries forward as-is to the shared template (photo card gating is a display concern per UI-SPEC, not a server-action concern).

---

### `api/services/admin_people.py` — `list_people`, `_missing_fields`, `_replace_tenures`, new `create_person`

**Analog:** itself (current version, full file read above); new `create_person` modeled on `api/services/admin_jobs.py::create_person_for_job` (lines 798-833) with job-scoping removed.

**`_missing_fields` (lines 66-80) — direct base to branch by `is_justice` per D-05/D-06:**
```python
def _missing_fields(person: Person) -> list[str]:
	missing: list[str] = []
	if person.role_id is None:
		missing.append("role")
	if person.bio_text is None:
		missing.append("bio")
	if person.photo_url is None:
		missing.append("photo")
	return missing
```
New shape: drop the `role_id` check entirely (D-10); branch on `person.is_justice` — Bench adds `first_name`/`last_name`/`photo`/`bio`/`birthdate`/"no tenures" (requires a tenure-count lookup, likely needs to become async or take a pre-fetched tenure count map, mirroring the N+1-avoidance pattern already used in `list_resolve_rows_for_job`'s `tenures_by_person` pre-fetch, lines 647-660); Advocate adds `first_name`/`last_name`/`photo`/`bio` only (D-05).

**`list_people` (lines 127-200) — direct base for tab/pill filtering (D-01/D-04) and argument-count column (PDIR-04):**
```python
async def list_people(db: AsyncSession, incomplete: bool = False, tenure_gaps: bool = False) -> list[dict]:
	q = (
		select(Person, Role.name.label("role_name"))
		.outerjoin(Role, Person.role_id == Role.id)
		.order_by(sqlfunc.coalesce(Person.last_name, Person.full_name).asc())
	)
	if incomplete:
		q = q.where(or_(Person.role_id.is_(None), Person.bio_text.is_(None), Person.photo_url.is_(None)))
	if tenure_gaps:
		... # existing EXISTS-subquery pattern, lines 162-187 — KEEP as-is, Bench-tab-only per D-06 note
```
New params: replace `incomplete: bool` with `is_justice: bool | None` (tab filter, D-02) and `missing: str | None` (single-field click-to-filter, D-04) — `missing` needs a per-field `.where(...)` branch (role/bio/photo/birthdate/no-tenures), reusing the existing `or_`/`not_(exists(...))` idioms already present in this function for `tenure_gaps`. Add `argument_count` via a `sqlfunc.count(distinct(ArgumentParticipant.id))`-style subquery/join for Advocate rows (PDIR-04 "distinct arguments" — use `ArgumentParticipant.argument_id` distinct count, not participant-row count, per UI-SPEC line 148).

**`_replace_tenures` (lines 83-119) — direct base to extend with `appointed_by`/`appointing_president_party` (D-16), `reason_ended` explicitly excluded (D-12/D-19):**
```python
async def _replace_tenures(db: AsyncSession, person_id: int, tenures: list[TenureRow]) -> None:
	await db.execute(delete(CourtTenure).where(CourtTenure.person_id == person_id).execution_options(synchronize_session=False))
	for t in tenures:
		if not (t.seat or t.start_date):
			continue
		start_date = datetime.date.fromisoformat(t.start_date) if t.start_date else None
		end_date = datetime.date.fromisoformat(t.end_date) if t.end_date else None
		db.add(CourtTenure(person_id=person_id, seat=t.seat or None, start_date=start_date, end_date=end_date))
```
Add `appointed_by=t.appointed_by or None, appointing_president_party=t.appointing_president_party or None` to the `CourtTenure(...)` constructor call — same delete-and-reinsert strategy (Pattern 5), same date-parsing/ValueError-propagation idiom (Pitfall 6). **Do NOT add `reason_ended`** — no schema field exists this phase (D-12/D-19, explicit in CONTEXT.md line 87).

**New `create_person` function — model on `api/services/admin_jobs.py::create_person_for_job` (lines 798-833), with job-scoping/participant-linkage stripped out (D-09's explicit instruction: NOT a reuse of the job-scoped version):**
```python
async def create_person_for_job(db, job_id, body: PersonCreate) -> Person:
	job = await get_job(db, job_id)
	if job is None:
		raise ValueError(f"AdminJob {job_id} not found")
	if job.status != AdminJobStatus.PAUSED:
		raise ValueError(...)
	# find-or-create role, insert Person, (job-scoped) update matching ArgumentParticipant
```
New shape: drop `job_id`/`job` lookup, drop the `AdminJobStatus.PAUSED` guard, drop the `raw_speaker_label`/`ArgumentParticipant` linkage block entirely. Minimum validation is `full_name` (non-empty) + `is_justice` (bool, required per D-08 — not Optional like `PersonUpdate.is_justice`). Insert `Person(full_name=..., is_justice=..., first_name=None, ...)`, `db.commit()`, `db.refresh()`, return via `get_person_detail(db, person.id)` (reuse the existing detail-fetch function verbatim as the return shape, matching the pattern every other mutation function in this file already follows — see `merge_people`, `delete_person_if_orphan`, `update_photo_url`, `upload_photo` all ending with `return await get_person_detail(db, person_id)`).

---

### `api/schemas/admin_people.py` — `TenureRow`, `PersonUpdate`, new create schema

**Analog:** itself (current version, full file read above); sibling `PersonCreate` in `api/schemas/admin_jobs.py` (used by `create_person_for_job`) is the closest existing create-schema shape, though it carries job-scoped fields (`raw_speaker_label`, `side`, `role_name`) not needed here.

**`TenureRow` (lines 24-34) — direct base, extend with two new Optional str fields (D-16):**
```python
class TenureRow(BaseModel):
	seat: Optional[str] = None
	start_date: Optional[str] = None
	end_date: Optional[str] = None
```
Add `appointed_by: Optional[str] = None` and `appointing_president_party: Optional[str] = None`. **Do not add `reason_ended`** (D-12/D-19 — UI-only, disabled, no schema field).

**`PersonUpdate` (lines 83-107) — direct base, drop `role_id` entirely (D-10), add `birthdate: Optional[str] = None` (PEDIT-02, new migration needed):**
```python
class PersonUpdate(BaseModel):
	full_name: Optional[str] = None
	role_id: Optional[int] = None  # → DELETE (D-10)
	bio_text: Optional[str] = None
	photo_url: Optional[str] = None
	tenures: Optional[list[TenureRow]] = None
	first_name: Optional[str] = None
	last_name: Optional[str] = None
	middle_name: Optional[str] = None
	name_suffix: Optional[str] = None
	is_justice: Optional[bool] = None
```
Mass-assignment allow-list pattern (T-09-01 comment) — same discipline applies to the new `birthdate` field: must be explicitly declared here, nowhere implicit.

**New create-request schema (name TBD by planner, e.g. `PersonCreateRequest`) — model on `PersonCreate` in `api/schemas/admin_jobs.py` minus job-scoped fields:**
Required: `full_name: str`, `is_justice: bool` (both mandatory per D-08 — no `Optional`, unlike every field on `PersonUpdate`). All else optional/absent (tenures/bio/photo/birthdate filled in later via the same `save`/`update_person` PATCH flow, not at creation time) — this matches D-08's "everything else is optional and filled in later on the same page" decision exactly.

---

### `api/routers/admin.py` — new `POST /people`

**Analog:** `POST /jobs/{job_id}/people` (`create_person_for_job`, lines 592-616) — exact structural match minus the `job_id` path param.

```python
@router.post("/jobs/{job_id}/people", status_code=201, response_model=PersonResponse)
async def create_person_for_job(
	job_id: int,
	body: PersonCreate,
	db: AsyncSession = Depends(get_db),
) -> PersonResponse:
	try:
		person = await jobs_service.create_person_for_job(db, job_id, body)
	except ValueError as exc:
		raise HTTPException(status_code=422, detail=str(exc)) from exc
	return person
```
New route: `@router.post("/people", status_code=201, response_model=PersonDetail)` (response as `PersonDetail` — the full shape, since the create page redirects straight into the editor and needs the full record, not the slim `PersonResponse`), calling `people_service.create_person(db, body)` — reraise `ValueError` as `422` exactly per this existing idiom, unchanged.

**Route-ordering note (existing comment in this file, around line 1097):** parameterized routes must be declared in the right order relative to static ones — confirm `POST /people` doesn't collide with `POST /people/{person_id}/photo` etc. (it won't, different HTTP verb/path shape, but worth the same vigilance this file already documents for the `/jobs/*` sub-routes).

---

### `api/models/models.py` — new `Person.birthdate` column

**Analog:** `Person.is_justice` (Phase 18, migration 0010) and `CourtTenure.appointed_by`/`appointing_president_party` (Phase 22, migration 0013) — both are "add nullable column via new Alembic migration" precedents on these exact two tables.

```python
class Person(Base):
	__tablename__ = "people"
	id = Column(Integer, primary_key=True)
	full_name = Column(String(300), nullable=False)
	role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
	bio_text = Column(Text, nullable=True)
	photo_url = Column(String(500), nullable=True)
	first_name = Column(String(150), nullable=True)
	last_name = Column(String(150), nullable=True)
	middle_name = Column(String(150), nullable=True)
	name_suffix = Column(String(50), nullable=True)
	is_justice = Column(Boolean, nullable=False, server_default=false())
```
Add `birthdate = Column(Date, nullable=True)` (PEDIT-02) — new Alembic revision required (CLAUDE.md: Alembic is sole DDL authority, never `Base.metadata.create_all`). **Do NOT add `death_date` this phase** — D-14 explicitly defers it (UI renders a disabled input with no backing column/migration).

---

## Shared Patterns

### Query-param filter toggle → `goto()` navigation
**Source:** `app/src/routes/admin/people/+page.svelte` lines 10-27 (existing `handleToggle`/`handleTenureGapsToggle`)
**Apply to:** Bench/Advocate tab switch (D-01), click-to-filter pills (D-04), "Clear filter" link — all three are the same one-param `goto()` round-trip idiom, just with different param names/values.

### SvelteKit form action error handling
**Source:** `app/src/routes/admin/people/[id]/+page.server.ts`, every action (`save` lines 186-209, `merge` lines 339-357, `delete` lines 373-390)
**Apply to:** the new create action in `new/+page.server.ts` — identical `try { fetch } catch { return fail(502, ...) }` then `if (!res.ok) return fail(422 or specific status, ...)` shape.

### FastAPI ValueError → 422 mapping
**Source:** `api/routers/admin.py`, every mutation route wrapping a service call (e.g. `update_person` lines 650-656, `create_person_for_job` lines 612-616)
**Apply to:** the new `POST /people` route and any new validation raised inside `admin_people.create_person`.

### `.execution_options(synchronize_session=False)` on every bulk statement
**Source:** `api/services/admin_people.py` — every `update()`/`delete()` call (e.g. `_replace_tenures` line 100, `merge_people` lines 396-405, `delete_person_if_orphan` lines 428-447)
**Apply to:** any new bulk statement added to `create_person` or the extended `_replace_tenures` (project-wide critical guard per CLAUDE.md/this file's module docstring).

### Empty-string → None normalization before write
**Source:** `api/services/admin_people.py::update_person`, lines 280-289 (`person.bio_text = body.bio_text if body.bio_text else None`, same for first/last/middle/suffix)
**Apply to:** `birthdate`, `appointed_by`, `appointing_president_party` writes — keeps the `IS NULL` missing-field checks accurate (D-05/D-06 depend on this).

### `datetime.date.fromisoformat()` + ValueError→422 for date strings
**Source:** `api/services/admin_people.py::_replace_tenures`, lines 108-111
**Apply to:** the new `birthdate` field write in `update_person`/`create_person` — same parse-and-propagate idiom.

### Person-detail-refetch-after-mutation
**Source:** `api/services/admin_people.py` — `update_person` (line 314), `merge_people` (line 408), `delete...` n/a, `upload_photo` (line 513), `update_photo_url` (line 466) — all end `return await get_person_detail(db, person_id)`
**Apply to:** new `create_person` — commit, then call `get_person_detail` for the return value rather than hand-assembling a dict.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/src/routes/admin/people/new/+page.svelte` route wiring itself | route (SvelteKit file-based) | n/a | No prior `/admin/*/new` route exists anywhere in the admin section to copy the route-file-creation mechanics from; content is copied from `[id]/+page.svelte` per D-07, but the route folder/file itself is genuinely new plumbing — planner should verify SvelteKit route-matching precedence between `/admin/people/new` (static) and `/admin/people/[id]` (dynamic) resolves as expected (static segments win in SvelteKit by default, so this should be safe, but flag for verification). |
| Alembic migration for `Person.birthdate` | migration | n/a | Not analyzed in depth here — migration 0010 (`is_justice`) and 0013 (`appointed_by`/`appointing_president_party` move) are the two nearest precedents (both are additive/renaming Person or CourtTenure columns); planner should locate the actual migration files under `api/alembic/versions/` for exact revision-chaining boilerplate, not covered by this pass. |

## Metadata

**Analog search scope:** `app/src/routes/admin/people/**`, `api/services/admin_people.py`, `api/services/admin_jobs.py` (create_person_for_job only), `api/schemas/admin_people.py`, `api/routers/admin.py` (people + jobs/people routes), `api/models/models.py` (Person, CourtTenure classes)
**Files scanned:** 8 read in full or targeted sections; 0 additional analog candidates searched beyond these — this phase is almost entirely a self-rewrite of its own predecessor files (Phase 8/9/12/18/22's People Editor work), so no broader codebase search was needed to find "closest analogs" beyond the files already named in CONTEXT.md's `code_context` section.
**Pattern extraction date:** 2026-07-08
