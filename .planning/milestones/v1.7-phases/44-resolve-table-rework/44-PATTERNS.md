# Phase 44: Resolve Table Rework - Pattern Map

**Mapped:** 2026-08-01
**Files analyzed:** 12
**Analogs found:** 12 / 12 (11 are self-analogs — the file itself is the existing pattern being reworked in place; only the Alembic migration needs an external analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|----------------|
| `app/src/lib/components/ResolveCard.svelte` | component | request-response (per-row form submit) | itself (in-place rework) | exact |
| `app/src/lib/components/CopyableExtractedValue.svelte` | component | transform (display-only) | itself (add prop, no structural change) | exact |
| `api/models/models.py` (`ArgumentParticipant.title`) | model | CRUD | itself (column rename) | exact |
| `alembic/versions/00XX_rename_participant_title_to_descriptor.py` (new) | migration | batch (DDL) | `alembic/versions/0021_constrain_tenure_office.py` | role-match (best available `alter_column`-style migration) |
| `api/schemas/admin_arguments.py` | model/schema | CRUD | itself (field rename) | exact |
| `api/schemas/admin_jobs.py` (`ResolveRowUpdate`) | model/schema | CRUD | itself (field rename) | exact |
| `api/schemas/admin_people.py` | model/schema | CRUD | itself (field rename) | exact |
| `api/services/admin_arguments.py` | service | CRUD | itself (field rename) | exact |
| `api/services/admin_jobs.py` (`update_resolve_row_for_job`) | service | CRUD | itself (field rename) | exact |
| `api/services/admin_people.py` (`list_resolve_rows_for_job`) | service | CRUD | itself (field rename) | exact |
| `api/routers/admin.py` (~601, 1358) | controller/route | request-response | itself (field rename) | exact |
| `pipeline/commands/parse.py` (`_update_participant_titles`, ~419-540) | service (pipeline step) | batch | itself (field rename) | exact |

**Note on match quality:** This phase is almost entirely a rename/rework of existing code, not new architecture. The "analog" for nearly every file is the file's own current implementation — the planner should treat these as in-place edits following the established conventions already in that file, not new patterns copied from elsewhere. The one genuinely external analog needed is the Alembic migration, since no `00XX_rename_participant_title_to_descriptor.py` file exists yet.

## Pattern Assignments

### `app/src/lib/components/ResolveCard.svelte` (component, request-response)

**Analog:** itself — current 742-line implementation is the baseline to extend, not replace.

**Imports pattern** (lines 1-4):
```svelte
<script lang="ts">
	import { enhance } from '$app/forms';
	import CopyableExtractedValue from '$lib/components/CopyableExtractedValue.svelte';
	import CreatePersonPopover from '$lib/components/CreatePersonPopover.svelte';
```

**Per-row hidden-form save pattern** (lines 98-109, 344-369) — reuse verbatim, do not replace:
```svelte
let formRefs: Record<number, HTMLFormElement> = {};
let saveState = $state<Record<number, { saving: boolean; error: string | null }>>({});
let pendingSideOverrides = $state<Record<number, string>>({});
let sideGateConfirmed = $state<Record<number, boolean>>({});

function rowFormId(participantId: number): string {
	return `resolve-row-form-${participantId}`;
}
function submitRow(participantId: number) {
	formRefs[participantId]?.requestSubmit();
}
```
```svelte
<!-- Hidden per-row save forms — inputs elsewhere in the table reference these via form="..." -->
{#each mergedRows as row (row.participant_id)}
	<form
		id={rowFormId(row.participant_id)}
		bind:this={formRefs[row.participant_id]}
		method="POST"
		action="?/saveResolveRow"
		style="display: none;"
		use:enhance={() => {
			saveState[row.participant_id] = { saving: true, error: null };
			return async ({ result, update }) => {
				if (result.type === 'failure') {
					saveState[row.participant_id] = {
						saving: false,
						error: (result.data as { resolveRowError?: string })?.resolveRowError ?? 'Could not save.',
					};
				} else {
					saveState[row.participant_id] = { saving: false, error: null };
					await update({ reset: false });
				}
			};
		}}
	>
		<input type="hidden" name="participant_id" value={row.participant_id} />
	</form>
{/each}
```
Rename `row.title`/`row.title_hint` field references throughout to `row.descriptor`/`row.descriptor_hint` (D-05) and the `name="title"` form field to `name="descriptor"` — this hidden-form mechanism itself is unaffected structurally.

**Side gate / segmented toggle pattern to extend (D-07)** — the existing two-plain-button gate (lines 546-562) is the mechanical baseline for the new segmented toggle; keep `confirmSide`/`onSideChange`/`pendingSideOverrides`/`sideGateConfirmed` exactly, only change the rendered markup from two independent bordered buttons to one joined pill per UI-SPEC:
```svelte
function confirmSide(row: MergedRow, choice: 'BENCH' | 'ADVOCATE') {
	const value = choice === 'BENCH' ? 'BENCH' : 'UNKNOWN';
	pendingSideOverrides[row.participant_id] = value;
	sideGateConfirmed[row.participant_id] = true;
	submitRow(row.participant_id);
}

function onSideChange(row: MergedRow, value: string) {
	pendingSideOverrides[row.participant_id] = value;
	submitRow(row.participant_id);
}

const SIDE_LABEL: Record<string, string> = {
	BENCH: 'Bench',
	PETITIONER: "Petitioner's Counsel",
	RESPONDENT: "Respondent's Counsel",
	AMICUS: 'Amicus Curiae',
	UNKNOWN: 'Counsel',
	ADVOCATE: 'Counsel', // legacy — never produced going forward
};
```
The current `<select name="side">` block (lines 564-587) is the source of the 4-real-option pattern to port into the new segmented toggle's underlying value model (values `BENCH`/`PETITIONER`/`RESPONDENT`/`AMICUS`/`UNKNOWN` — same enum values, new visual control per UI-SPEC's toggle state matrix).

**Argument Role `<select>` pattern to extend (D-01/D-02)** — current Title `<input>` block (lines 619-656) shows the existing per-row `form={rowFormId(...)}` + `onblur={() => submitRow(...)}` idiom to reuse for the new Argument Role `<select>`:
```svelte
<input
	form={rowFormId(row.participant_id)}
	name="title"
	type="text"
	value={row.title ?? ''}
	onblur={() => submitRow(row.participant_id)}
	style="..."
/>
```
Port this exact `form=`/`onblur`/`submitRow` idiom to the new `<select name="side_role">`-equivalent (per UI-SPEC's 3-option + placeholder markup) using `onchange` instead of `onblur` (selects fire on change, matching the existing `onSideChange` handler style at line 568).

**Person-search combobox pattern for D-03 collapse** (lines 428-525) — the existing `correcting`-state combobox (with `comboOutsideClick` action, keyboard nav, `RowMatchState`) is the direct analog to extend for the pre-filled/collapsed entry point; reuse `getRowCandidates`, `handleSelectPerson`, `comboOutsideClick` verbatim. The new "Suggested" badge (UI-SPEC) is a small addition to the existing `<li role="option">` render (lines 500-522), not a new component.

**CopyableExtractedValue current (soon superseded) call site** (lines 640-651) — shows the *old* 2-line stacked pattern that D-09/UI-SPEC explicitly say NOT to replicate for the new hints:
```svelte
<CopyableExtractedValue
	value={row.title_hint}
	copyLabel="Copy title"
	confidence="Medium"
	raw={row.title_hint}
/>
```
New pattern per UI-SPEC (all 4 hint usages in the reworked file): pass `prefixLabel="Imported"` and `raw={null}` (never `confidence`), e.g.:
```svelte
<CopyableExtractedValue
	value={row.descriptor_hint}
	copyLabel="Copy descriptor"
	prefixLabel="Imported"
	raw={null}
/>
```

**TypeScript interfaces to rename** (lines 37-51):
```typescript
interface ResolveRow {
	participant_id: number;
	raw_speaker_label: string;
	person_id: number | null;
	full_name: string | null;
	photo_url: string | null;
	side: string;
	argument_role: string | null;
	title: string | null;        // -> descriptor: string | null;
	title_hint: string | null;   // -> descriptor_hint: string | null;
	bench_role: string | null;
	missing_tenure: boolean;
	person_edit_href: string | null;
	editable: boolean;
}
```

---

### `app/src/lib/components/CopyableExtractedValue.svelte` (component, transform)

**Analog:** itself — additive prop only, per D-09.

**Current hardcoded prefix** (line 8-17 props type, line 111 render):
```typescript
type CopyableExtractedValueProps = {
	value: string | null | undefined;
	copyLabel: string;
	variant?: 'text' | 'pill';
	confidence?: ConfidenceBand | null;
	raw?: string | null;
};
let { value, copyLabel, variant = 'text', confidence, raw }: CopyableExtractedValueProps = $props();
```
```svelte
<span class="prefix">Extracted:</span>
```

**Required change** (add prop, default preserves every existing call site):
```typescript
type CopyableExtractedValueProps = {
	value: string | null | undefined;
	copyLabel: string;
	variant?: 'text' | 'pill';
	confidence?: ConfidenceBand | null;
	raw?: string | null;
	prefixLabel?: string; // NEW — default 'Extracted', ResolveCard passes 'Imported'
};
let { value, copyLabel, variant = 'text', confidence, raw, prefixLabel = 'Extracted' }: CopyableExtractedValueProps = $props();
```
```svelte
<span class="prefix">{prefixLabel}:</span>
```
Note the `isStacked` derivation (`confidence !== undefined || raw !== undefined`, line 27) is unaffected — `ResolveCard` passing `raw={null}` (not omitted) is what activates stacked mode while `hasRaw` (line 28) stays false, suppressing `line2`. This existing derivation logic requires no change; only the prefix string and prop threading change.

**Other call sites (unaffected, verify no `prefixLabel` passed):** `ArgumentDetailsCard.svelte`, `DocketPillInput.svelte`, `app/src/routes/admin/pipeline/[job_id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/arguments/[id]/+page.svelte` — grep these at execution time to confirm no accidental `prefixLabel` regression; they should keep the `"Extracted:"` default.

---

### `api/models/models.py` — `ArgumentParticipant.title` → `.descriptor` (model, CRUD)

**Analog:** itself (rename in place).

**Current column definition** (lines 365-376):
```python
class ArgumentParticipant(Base):
	"""Which people spoke in which arguments (populated at parse time from raw labels)."""

	__tablename__ = "argument_participants"

	id = Column(Integer, primary_key=True)
	argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
	person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null until resolved
	raw_speaker_label = Column(String(200), nullable=False)
	side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False)
	# Phase 22 — migration 0013: TOC subtitle from cover extractor (PJOB-13)
	title = Column(String(500), nullable=True)
```
Rename to `descriptor = Column(String(500), nullable=True)`, updating the docstring/comment to reflect Phase 44's rename (keep the historical Phase 22/PJOB-13 provenance note, append a Phase 44 rename note per this project's existing convention of annotating column history inline).

**Required companion migration** — see next section.

---

### `alembic/versions/00XX_rename_participant_title_to_descriptor.py` (new file) (migration, batch/DDL)

**Analog:** `alembic/versions/0021_constrain_tenure_office.py` (closest structural match: single-table `op.alter_column`-style DDL with clean `upgrade`/`downgrade` symmetry). Also check `0019_question_number_nullable.py` (another single-column alter) as a secondary reference if a data-preserving column rename needs different handling than a type/nullability change.

**Migration header/skeleton pattern** (lines 1-17):
```python
"""Constrain normalized tenure offices to chief or associate.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
```

**Applicable technique — `op.alter_column` for rename:** Alembic's `op.alter_column` supports a `new_column_name` argument for pure renames (distinct from the type/nullable-only usage shown in 0021). The new migration should use:
```python
def upgrade() -> None:
	op.alter_column(
		"argument_participants",
		"title",
		new_column_name="descriptor",
		existing_type=sa.String(length=500),
		existing_nullable=True,
	)


def downgrade() -> None:
	op.alter_column(
		"argument_participants",
		"descriptor",
		new_column_name="title",
		existing_type=sa.String(length=500),
		existing_nullable=True,
	)
```
Find current head revision before writing `down_revision` — run `ls alembic/versions | sort | tail -1` at execution time (most recent found during this mapping pass: `0024_add_constrain_tenure_reason_left.py`; confirm no newer file has been added since).

**Enum/table-name style check:** `argument_participants` is the exact `__tablename__` string (confirmed in models.py) — use that literal string in the migration, matching 0021's pattern of hardcoding table/column name strings rather than importing the ORM model.

---

### `api/schemas/admin_arguments.py` (schema, CRUD)

**Analog:** itself.

**Fields to rename** (lines 40-50, 76-96):
```python
class ParticipantSideUpdate(BaseModel):
	"""PATCH body for argument_participants.side and title (ROLE-03, Phase 26 D-06).
	...
	"""
	side: SideEnum
	title: Optional[str] = None   # -> descriptor: Optional[str] = None
```
```python
# SpeakerRow-equivalent output schema (~lines 76-96)
title: Optional[str] = None        # -> descriptor: Optional[str] = None
title_hint: Optional[str] = None   # -> descriptor_hint: Optional[str] = None
```
Update accompanying docstrings referencing "title"/"Title" (lines 18, 21, 27, 45-46, 76, 80) to say "descriptor"/"Descriptor" — this project's convention (seen throughout) is to keep decision-provenance comments (e.g. "D-06, AEDIT-06") intact, only updating the field-name text itself.

---

### `api/schemas/admin_jobs.py` — `ResolveRowUpdate` (schema, CRUD)

**Analog:** itself.

**Current field** (lines 190-211):
```python
class ResolveRowUpdate(BaseModel):
	"""Request body for the job-scoped resolve-row side/title mutation.

	Mass-assignment guard (T-25-15): ONLY side and title are writable via this
	...
	argument-editor path. title is ignored (forced to null) server-side whenever
	...
	WR-03: title is capped at 500 characters to match
	ArgumentParticipant.title (String(500)) — without this, an over-length
	title would raise an unhandled asyncpg DataError (500) instead of the
	...
	"""
	title: Optional[str] = Field(default=None, max_length=500)
```
Rename to `descriptor: Optional[str] = Field(default=None, max_length=500)`; update all "title" references in the docstring to "descriptor" (keep the WR-03/T-25-15 provenance tags).

---

### `api/schemas/admin_people.py` (schema, CRUD)

**Analog:** itself.

**Fields to rename** (lines 365-392):
```python
# ~line 365: full_name/photo_url), side (Bench/Advocate), argument_role, title
# ~line 370: office title (Chief Justice/Associate Justice) — DO NOT rename this
#            "title" — it refers to office_title(), unrelated to ArgumentParticipant.title
# ~line 373: person editor (D-15, D-16, PJOB-16). title/title_hint are always null —
# ~line 377: Counsel"); title/title_hint carry ArgumentParticipant.title. bench_role,
title: Optional[str] = None        # -> descriptor: Optional[str] = None
title_hint: Optional[str] = None   # -> descriptor_hint: Optional[str] = None
```
**Caution flagged for planner:** this file also uses "title" in the unrelated sense of `office_title()` (Chief Justice / Associate Justice formal titles, lines 154-196 per the earlier grep) — only rename the `ArgumentParticipant.title`-sourced fields (`title`/`title_hint` at ~391-392 and their docstring mentions), not the office-title helper functions or their references. Use targeted rename, not a blind find-replace of the word "title" in this file.

---

### `api/services/admin_arguments.py` (service, CRUD)

**Analog:** itself.

**Current read-projection pattern** (lines 214-313, key excerpt at ~296, 312-313):
```python
# (title/title_hint always None — Title is advocate-only, PJOB-15 precedent).
# Advocate rows: argument_role from ADVOCATE_LABEL_MAP; title and title_hint
# both source ArgumentParticipant.title (D-06 — no separate stored "originally
# ...
"title_hint": None,
# ...
"title": participant.title,
"title_hint": participant.title,
```
Rename dict keys `"title"`/`"title_hint"` to `"descriptor"`/`"descriptor_hint"`; rename `participant.title` reads to `participant.descriptor`.

**Write-path function signature** (lines 623, 646, 686):
```python
title: str | None = None,
...
# title leaves the existing ArgumentParticipant.title unchanged (does not
...
persisted_title = title if title is not None else participant.title
```
Rename parameter `title` → `descriptor`, and `participant.title` → `participant.descriptor`, `persisted_title` → `persisted_descriptor` (or equivalent) for consistency with the renamed column.

---

### `api/services/admin_jobs.py` — `update_resolve_row_for_job` (service, CRUD)

**Analog:** itself.

**Current write pattern** (lines 770, 820, 828):
```python
"""Update ArgumentParticipant.side (BENCH allowed) and .title for a job-owned row.
...
"""
title = None if body.side == SideEnum.BENCH else body.title
...
.values(side=body.side, title=title)
```
Rename to:
```python
descriptor = None if body.side == SideEnum.BENCH else body.descriptor
...
.values(side=body.side, descriptor=descriptor)
```
Note this depends on `ResolveRowUpdate.title` → `.descriptor` rename in `admin_jobs.py` schema above being applied first (same-file dependency, both in `admin_jobs.py`).

---

### `api/services/admin_people.py` — `list_resolve_rows_for_job` (service, CRUD)

**Analog:** itself.

**Current read-projection pattern** (lines 942-1040):
```python
# these rows. title/title_hint are always None (PJOB-15 — Title column is
...
# Non-bench rows get argument_role from ADVOCATE_LABEL_MAP; title/title_hint
# are sourced from ArgumentParticipant.title (there is no separate stored
# ... date/docket, ArgumentParticipant.title is written once by the parse-time
...
"title_hint": None,          # (~line 1022)
...
"title": participant.title,        # (~line 1039)
"title_hint": participant.title,   # (~line 1040)
```
Rename dict keys and `participant.title` reads identically to the `admin_arguments.py` pattern above — this is the exact same projection idiom duplicated across both services (both should be updated in lockstep since `ResolveCard.svelte` consumes both `admin_arguments.py`'s and `admin_people.py`'s `list_resolve_rows_for_job`-style output shape).

---

### `api/routers/admin.py` (~601, 1358) (controller/route, request-response)

**Analog:** itself.

**Line 601** (direct dict-building read):
```python
return {"id": participant.id, "side": participant.side.value, "title": participant.title}
```
Rename to:
```python
return {"id": participant.id, "side": participant.side.value, "descriptor": participant.descriptor}
```

**Line 1358** (service call passing through the body field):
```python
db, argument_id, participant_id, body.side, body.title
```
Rename to:
```python
db, argument_id, participant_id, body.side, body.descriptor
```
This depends on `body` being the renamed `ParticipantSideUpdate.descriptor` field from `admin_arguments.py` schema above, and the corresponding service function parameter rename in `admin_arguments.py`.

---

### `pipeline/commands/parse.py` — `_update_participant_titles` (~419-540) (service/pipeline-step, batch)

**Analog:** itself.

**Function to rename** (lines 505-540, called from ~419-424):
```python
if advocate_titles and run.argument_id is not None:
	titles_updated = await _update_participant_titles(session, run.argument_id, advocate_titles)
	print(f"Participant titles updated: {titles_updated} row(s) from TOC mapping.")

...

async def _update_participant_titles(
	session: AsyncSession,
	argument_id: int,
	titles_map: "dict[str, str]",
) -> int:
	"""
	Update argument_participants.title for advocates whose normalized last name
	matches a key in titles_map ({last_name_upper: title_string}).

	Returns count of participant rows updated. Unmatched participants keep
	NULL title (D-11). Title is stored as a plain string — no enum cast.
	"""
	if not titles_map:
		return 0

	result = await session.execute(
		select(ArgumentParticipant).where(
			ArgumentParticipant.argument_id == argument_id
		)
	)
	participants = result.scalars().all()

	updated = 0
	for p in participants:
		if p.raw_speaker_label is None:
			continue
		label_last = _normalize_label_last_name(p.raw_speaker_label)
		if label_last and label_last.upper() in titles_map:
			p.title = titles_map[label_last.upper()]
			updated += 1

	return updated
```
Rename function to `_update_participant_descriptors`, parameter `titles_map` → `descriptors_map` (or keep param name if the planner decides scope-minimization is preferred — note the outer variable `advocate_titles` at the call site would need matching if renamed, but this is cosmetic; only `p.title = ...` → `p.descriptor = ...` is functionally required since that's the renamed ORM column). Keep the `_normalize_label_last_name` helper (lines 452-470) untouched — unaffected by this rename, reused as-is.

**Shared invariant:** unmatched participants keep NULL descriptor (D-11 predecessor decision, now applies identically to the renamed column) — behavior unchanged, only the attribute name changes.

---

## Shared Patterns

### Full-stack field rename (D-05)
**Source:** this phase's own dependency chain — `alembic migration` -> `models.py` -> `schemas/*.py` -> `services/*.py` -> `routers/admin.py` + `pipeline/commands/parse.py` -> `ResolveCard.svelte`
**Apply to:** every file in the "Descriptor rename call sites" list in CONTEXT.md.
**Sequencing note for planner:** the Alembic migration and `models.py` column rename must land before any service/router code that reads/writes `participant.descriptor` — since Alembic is the sole DDL authority (CLAUDE.md), no other file may assume the column exists until that migration is planned/applied. Recommend the migration + model rename as Wave 1, schemas as Wave 2, services+router+pipeline as Wave 3, and the Svelte UI rework as a Wave 4 (or parallel wave, since the SvelteKit layer only depends on the API response shape, not the DB column name directly).

### `CopyableExtractedValue` prefix-label extension (D-09)
**Source:** `app/src/lib/components/CopyableExtractedValue.svelte` lines 8-17, 108-113
**Apply to:** `ResolveCard.svelte`'s 4 hint call sites only; all other existing call sites (`ArgumentDetailsCard.svelte`, `DocketPillInput.svelte`, 3 `+page.svelte` routes) must NOT be touched — default value preserves them.

### Per-row hidden-form submit (existing, unaffected)
**Source:** `ResolveCard.svelte` lines 98-109, 344-369
**Apply to:** all edited controls within the Resolve table (segmented toggle, Argument Role select, Descriptor input) — extend `pendingSideOverrides`/`sideGateConfirmed` state shape per D-07/CONTEXT.md instruction to reuse, not replace.

### Mass-assignment guard convention (existing, unaffected)
**Source:** `api/schemas/admin_jobs.py` `ResolveRowUpdate` docstring ("Mass-assignment guard (T-25-15): ONLY side and title are writable...")
**Apply to:** keep this exact guard-comment convention when renaming `title` → `descriptor` in the docstring text — this project consistently documents mass-assignment guards inline in schema docstrings; the renamed schema should retain an equivalent guard comment referencing the new field name.

## No Analog Found

None — every file in this phase's scope either already exists (in-place rework/rename) or has a directly comparable existing migration (`0021_constrain_tenure_office.py`) to model the new Alembic migration on.

## Metadata

**Analog search scope:** `app/src/lib/components/`, `api/models/`, `api/schemas/`, `api/services/`, `api/routers/`, `pipeline/commands/`, `alembic/versions/`
**Files scanned:** `ResolveCard.svelte`, `CopyableExtractedValue.svelte`, `api/models/models.py`, `api/schemas/admin_arguments.py`, `api/schemas/admin_jobs.py`, `api/schemas/admin_people.py`, `api/services/admin_arguments.py`, `api/services/admin_jobs.py`, `api/services/admin_people.py`, `api/services/speakers.py`, `api/routers/admin.py`, `pipeline/commands/parse.py`, `alembic/versions/0021_constrain_tenure_office.py`, `alembic/versions/0019_question_number_nullable.py`, `alembic/versions/0011_add_source_docket_cover_metadata.py` (directory listing only)
**Pattern extraction date:** 2026-08-01
