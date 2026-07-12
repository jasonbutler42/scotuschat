# Phase 26: Arguments Admin - Pattern Map

**Mapped:** 2026-07-07
**Files analyzed:** 9 (5 modified frontend/backend targets + 3 new-content additions inside existing files + 1 touched-but-different-field file)
**Analogs found:** 9 / 9 (all files being modified are their own best analog — this phase is an in-place rebuild, not new-file creation; secondary analogs cited for new sub-patterns)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `app/src/routes/admin/arguments/+page.svelte` | component (list) | request-response | itself (existing file, in-place rebuild) | exact |
| `app/src/routes/admin/arguments/+page.server.ts` | route (load/actions) | request-response | itself | exact |
| `app/src/routes/admin/arguments/[id]/+page.svelte` | component (edit) | request-response | itself | exact |
| `app/src/routes/admin/arguments/[id]/+page.server.ts` | route (load/actions) | request-response | itself | exact |
| `api/services/admin_arguments.py` (`list_arguments`, `publish_argument`, `unpublish_argument`, `delete_argument`, `update_argument`) | service | CRUD | itself | exact |
| `api/services/admin_jobs.py` (`approve_job`) | service | CRUD (state transition) | itself; secondary analog `admin_arguments.publish_argument` for status-log-write shape | exact |
| Speakers section (new sub-component inside `[id]/+page.svelte`) | component (embedded table+form) | CRUD | `[id]/+page.svelte` "Advocate Roles" card (lines 275-366) per D-04 | exact (explicit reuse target) |
| Speakers backend query (new function or extension in `admin_arguments.py` / `admin_people.py`) | service | CRUD (read, aggregate) | `admin_people.list_resolve_rows_for_job` (lines 587-703) + `admin_people._bench_role_and_missing_tenure` (564-584) + `speakers.get_argument_speakers` (88+) for the utterance-count/person_id join pattern | role-match (query-shape analog, not identical entity) |
| `app/src/lib/components/RunStatusCard.svelte` (Archived badge, folded todo) | component | request-response | itself (existing badge-map pattern) | exact |
| `api/services/admin_jobs.py` (`get_job_readiness`, folded todo) | service | CRUD (read) | itself | exact |

## Pattern Assignments

### `app/src/routes/admin/arguments/+page.svelte` (component, request-response)

**Analog:** itself, current implementation

**Badge helper pattern to extend with a third branch** (lines 18-34):
```svelte
function badgeStyle(status: string): string {
	let color: string;
	if (status === 'published') {
		color = '#4ade80'; // Published — green
	} else if (status === 'draft') {
		color = '#a78bfa'; // Draft — violet
	} else {
		color = '#94a3b8'; // Pipeline — muted (fallback, should not appear in this list)
	}
	return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`;
}

function badgeLabel(status: string): string {
	if (status === 'published') return 'Published';
	if (status === 'draft') return 'Draft';
	return 'Pipeline';
}
```
Add an `unpublished` branch: color `#fb923c`, label `'Unpublished'`, per UI-SPEC Color table and List page contract. Keep markup string shape identical — only extend the if/else chain.

**Row-actions three-state branch to replace the current two-branch block** (lines 173-218):
```svelte
{#if arg.resolved_at && !arg.published_at}
	<!-- Publish toggle — only when resolved and not yet published -->
	<form method="POST" action="?/publish" use:enhance>
		<input type="hidden" name="argument_id" value={arg.id} />
		<button type="submit" style="...accent border #93c5fd...">Publish</button>
	</form>
{:else if arg.published_at}
	<!-- Unpublish toggle — only when already published -->
	<form method="POST" action="?/unpublish" use:enhance>
		<input type="hidden" name="argument_id" value={arg.id} />
		<button type="submit" style="...muted border #334155...">Unpublish</button>
	</form>
{/if}
```
Replace with a `status`-keyed three-branch equivalent (DRAFT → Publish/accent; PUBLISHED → Unpublish/muted; UNPUBLISHED → Publish/accent, per UI-SPEC "Row actions column logic"). Keep the exact button style strings (`min-height: 44px`, `#93c5fd` accent / `#334155` muted borders) — only the condition changes from `resolved_at`/`published_at` to `status`.

**New "Created" column** — insert a `<th>`/`<td>` pair between "Argued" and "Publish" using the identical header/cell style block already used for the "Argued" column (lines 102-112, 157-165), and the existing `formatDate()` helper (lines 6-14) applied to `arg.resolved_at` (per Integration Points note: reuse `resolved_at` as "Created").

---

### `app/src/routes/admin/arguments/[id]/+page.svelte` (component, request-response)

**Analog:** itself, current implementation

**Badge helper** (lines 21-38) — same three-branch extension as the list page (`unpublished` → `#fb923c` / "Unpublished").

**Status card content to extend** (lines 238-273):
```svelte
{#if data.argument.resolved_at}
	<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
		Resolved {formatDate(data.argument.resolved_at)}
	</p>
{/if}

{#if data.argument.published_at}
	<p style="font-size: 14px; color: #94a3b8; margin: 0 0 8px 0;">
		Published {formatDate(data.argument.published_at)}
	</p>
{/if}
```
Relabel "Resolved" → "Created" (copy-only change, still reads `data.argument.resolved_at`, per UI-SPEC Copywriting Contract). Add the new "Status history" list directly below this block (or as its own card with identical chrome `background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;`), rendering `data.argument.status_log` entries with `padding: 8px 0` per-row density (UI-SPEC Spacing Scale). Reuse `formatDate()` (or a variant with time) for the `{date, time}` format. Move the Publish/Unpublish button block (currently lines 394-463, outside any card) into or directly beneath this card per UI-SPEC Layout Contract §2.

**Advocate Roles card — direct template for Speakers section per D-04** (lines 275-366):
```svelte
{#each data.argument.participants as participant}
	<div style="margin-bottom: 16px;">
		<p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin: 0 0 8px 0;">
			{participant.full_name}
		</p>
		<form
			method="POST"
			action="?/updateParticipantSide"
			use:enhance={() => {
				savingRoleId = participant.participant_id;
				return async ({ update }) => {
					savingRoleId = null;
					await update();
				};
			}}
			style="display: flex; gap: 8px; align-items: center;"
		>
			<input type="hidden" name="participant_id" value={participant.participant_id} />
			<select name="side" style="flex: 1; ...min-height: 36px;">
				<option value="PETITIONER" selected={participant.side === 'PETITIONER'}>Petitioner's Counsel</option>
				<option value="RESPONDENT" selected={participant.side === 'RESPONDENT'}>Respondent's Counsel</option>
				<option value="AMICUS" selected={participant.side === 'AMICUS'}>Amicus Curiae</option>
				<option value="UNKNOWN" selected={participant.side === 'UNKNOWN'}>Counsel</option>
			</select>
			<button type="submit" disabled={savingRoleId === participant.participant_id} style="min-height: 36px; ...">
				{savingRoleId === participant.participant_id ? 'Saving…' : 'Save'}
			</button>
		</form>
	</div>
{/each}
```
For the new Speakers section: keep the per-row `<form use:enhance>` + `savingRoleId`-keyed state exactly as-is; drop the `UNKNOWN` option (three options only per AEDIT-06/UI-SPEC); add a `Title <input type="text">` field inside the same form (posts alongside `side`) with an "Extracted: {hint}" row beneath it, styled per the `ArgumentDetailsCard` hint convention below; add a read-only `Utterances` count `<td>`/column; add read-only bench rows (no form, no select) rendering plain role text or "Missing tenure" (`#fbbf24`) + "Edit person" link. Table/row wrapper should switch from the current stacked-`<div>` layout to a single unified table per UI-SPEC column order: Name | Role | Title | Utterances | Action.

**Tenure-gap-warning banner block to remove entirely** (lines 368-392) — replaced by inline bench-row "Missing tenure" text per D-07; do not port this banner pattern forward, only its color (`#fbbf24`) and copy convention ("Edit person" link).

**Danger Zone gate to update** (lines 465-538):
```svelte
{#if data.can_delete}
	...
{:else}
	<button disabled aria-describedby="delete-tip" ...>Delete argument</button>
	<p id="delete-tip" ...>Published arguments cannot be deleted. Unpublish first.</p>
{/if}
```
`data.can_delete` is computed server-side in `+page.server.ts` (see below) — only the tooltip copy changes here, to: "Published and unpublished arguments cannot be deleted. Only drafts can be removed." (per UI-SPEC Copywriting Contract, D-03).

**Extracted-hint pattern to copy for Speakers Title field** — from `app/src/lib/components/ArgumentDetailsCard.svelte` (lines 98-112, 163-167, 204-207):
```svelte
<p
	style="
		font-size: 14px;
		font-weight: 400;
		color: #94a3b8;
		margin: 4px 0 0 0;
		{!hints.question_number ? 'font-style: italic;' : ''}
	"
>
	Extracted: {hints.question_number ?? 'N/A'}
</p>
```
Apply identically to the advocate Title field: italic when the extracted value is null/N/A, plain otherwise. This is the exact convention referenced by D-06 and UI-SPEC's "Extracted" hint row.

---

### `app/src/routes/admin/arguments/[id]/+page.server.ts` (route, request-response)

**Analog:** itself, current implementation

**Load function `can_delete` gate to update** (lines 51-54):
```typescript
// can_delete: server-side gate — derived from already-loaded argument data (D-05).
const can_delete = argument.status !== 'published';
```
Change to `argument.status !== 'published' && argument.status !== 'unpublished'` (or equivalently `argument.status === 'draft'`) per D-03.

**Publish/unpublish actions — reusable as-is for re-Publish** (lines 153-190): both `publish` and `unpublish` actions already POST to the existing `/publish` / `/unpublish` endpoints with no body; no frontend action changes needed for D-01/D-02 since the backend re-Publish and error-copy handling absorb the new state transition. Confirm error copy matches UI-SPEC: "Could not publish/unpublish this argument. Please try again." (existing copy is close — verify exact wording during execution).

**Delete action's 409 error copy to update** (lines 199-220, specifically line 212-214): change `'Published arguments cannot be deleted. Unpublish first.'` to the new D-03 tooltip copy.

**Type additions needed:** `ArgumentDetail` type (lines 22-34) needs a `status_log: { status: string; created_at: string }[]` field (or similar) to carry the new Status history data from the API response; `AdvocateParticipant` type (lines 9-14) needs `title`, `title_hint`, `utterance_count` fields for advocates and a parallel bench-row shape (or a unified `participants` shape covering both, matching whatever the backend's extended list-participants response returns).

---

### `api/services/admin_arguments.py` — `list_arguments` (service, CRUD)

**Analog:** itself (lines 46-85)

**Bug fix per Integration Points note** (line 69):
```python
.where(Argument.status.in_([ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.PUBLISHED]))
```
Change to `.where(Argument.status.in_([ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.PUBLISHED, ArgumentStatusEnum.UNPUBLISHED]))` per ALIST-02.

---

### `api/services/admin_arguments.py` — `publish_argument` / `unpublish_argument` (service, CRUD/state-transition)

**Analog:** each other (near-identical shape, lines 313-343 and 392-417)

**Current publish pattern**:
```python
async def publish_argument(db: AsyncSession, argument_id: int) -> dict | None:
    result = await db.execute(select(Argument).where(Argument.id == argument_id))
    argument = result.scalar_one_or_none()
    if argument is None:
        return None
    if argument.resolved_at is None:
        raise ValueError("Cannot publish: resolve step not yet complete")
    if argument.published_at is not None:
        raise ValueError("Already published")
    await db.execute(
        update(Argument)
        .where(Argument.id == argument_id)
        .values(published_at=sqlfunc.now())
        .execution_options(synchronize_session=False)
    )
    await db.commit()
    return await get_argument_detail(db, argument_id)
```
Extend per D-09/Integration Points:
1. Also set `status=ArgumentStatusEnum.PUBLISHED` in the `.values(...)` call.
2. Change the guard from `if argument.published_at is not None: raise ValueError("Already published")` to a status-based guard that allows re-Publish from UNPUBLISHED (only block when already PUBLISHED): e.g. `if argument.status == ArgumentStatusEnum.PUBLISHED: raise ValueError(...)`.
3. Insert an `ArgumentStatusLog` row (`argument_id=argument_id, status=ArgumentStatusEnum.PUBLISHED`) — see shared helper pattern below (D-10).

**Current unpublish pattern** (lines 392-417) — same shape, mirror the changes: set `status=ArgumentStatusEnum.UNPUBLISHED` instead of clearing `published_at` to `None`; UI-SPEC/D-02 imply `published_at` should likely remain untouched on unpublish (kept for "latest published" history — verify against ALIST/AEDIT requirements during planning), guard on `argument.status != ArgumentStatusEnum.PUBLISHED` before allowing unpublish; insert `ArgumentStatusLog` row with `status=ArgumentStatusEnum.UNPUBLISHED`.

**`execution_options(synchronize_session=False)` — project-wide critical guard, present on every `update()`/`delete()` call in this file** (e.g. lines 335-339, 410-414, 471-475, 477-479) — must be preserved on any new/modified `update()` statement.

---

### `api/services/admin_arguments.py` — `update_argument` (slug-freeze) and `delete_argument` (delete gate)

**Analog:** itself (lines 216-310 and 439-479+)

**Slug-freeze bug** (per Integration Points, around line 224-229 docstring / actual conditional in the body after line 256): current logic keys off `argument.published_at is None`. Must change to key off `argument.status != ArgumentStatusEnum.DRAFT` (i.e., freeze the slug once status leaves DRAFT — covers both PUBLISHED and UNPUBLISHED) per ALIST-01/D-03 analog reasoning.

**Delete gate bug** (lines 463-468):
```python
result = await db.execute(select(Argument).where(Argument.id == argument_id))
argument = result.scalar_one_or_none()
if argument is None:
    return None
if argument.published_at is not None:
    return False
```
Change the gate to `if argument.status in (ArgumentStatusEnum.PUBLISHED, ArgumentStatusEnum.UNPUBLISHED): return False` per D-03. Preserve the docstring's FK-ordered cascade comment and the `.execution_options(synchronize_session=False)` calls further down (lines 471-479) unchanged.

---

### `api/services/admin_jobs.py` — `approve_job` (service, CRUD/state-transition)

**Analog:** itself (lines 466-506+)

**Current pattern**:
```python
await db.execute(
    update(Argument)
    .where(Argument.id == job.argument_id)
    .values(
        status=ArgumentStatusEnum.DRAFT,
        resolved_at=func.now(),
    )
    .execution_options(synchronize_session=False)
)
```
Add an `ArgumentStatusLog` insert immediately after (or before commit) for the "Created" transition per D-08: `ArgumentStatusLog(argument_id=job.argument_id, status=ArgumentStatusEnum.DRAFT)`. This is the first-ever log write for arguments created going forward — pair with the same helper/inline pattern chosen for `publish_argument`/`unpublish_argument` (D-10).

**Suggested shared helper (D-10 discretion)** — given both `admin_jobs.py` and `admin_arguments.py` need an identical two-line "insert `ArgumentStatusLog` row" operation, and cross-module imports between these two service files already exist in the codebase (check for existing precedent before introducing a new shared util), a small `async def _log_status_transition(db, argument_id, status)` helper co-located with `ArgumentStatusLog` usage (or duplicated inline per file, since it is only 3-4 lines) is reasonable — planner's call per D-10.

---

### Speakers backend query — new function (service, CRUD/read)

**Analog:** `api/services/admin_people.py` `list_resolve_rows_for_job` (lines 587-703) for the overall per-participant row-building shape (advocate vs. bench branching, tenure prefetch avoiding N+1), and `_bench_role_and_missing_tenure` (lines 564-584) reused verbatim for bench-row role/missing-tenure computation:
```python
def _bench_role_and_missing_tenure(
    tenures: list[CourtTenure],
    argued_date: Optional[datetime.date],
) -> tuple[Optional[str], bool]:
    if argued_date is not None:
        for t in tenures:
            if t.start_date is not None and argued_date >= t.start_date:
                if t.end_date is None or argued_date <= t.end_date:
                    return t.seat, False
    return None, True
```
Per Integration Points note, the per-job utterance-count aggregate (`admin_jobs.get_job_detail`, lines ~140-147) is NOT reusable — instead use the `Utterance.argument_id` + `Utterance.person_id` join pattern demonstrated in `speakers.get_argument_speakers` (lines 88-118+) as the shape for a new per-participant utterance-count query (group by `person_id`, scoped by `argument_id`, in one query to avoid N+1 — same batching principle as `list_resolve_rows_for_job`'s tenure prefetch).

---

### `app/src/lib/components/RunStatusCard.svelte` (folded todo — Archived badge)

**Analog:** itself (lines 27-45, 103-123)

**Current badge-map pattern**:
```svelte
const BADGE_COLOR: Record<string, string> = {
	pending: '#94a3b8',
	running: '#93c5fd',
	completed: '#4ade80',
	paused: '#fbbf24',
	failed: '#ef4444',
};
const BADGE_LABEL: Record<string, string> = {
	pending: 'Pending',
	running: 'Running',
	completed: 'Completed',
	paused: 'Needs review',
	failed: 'Failed',
};
let badgeColor = $derived(BADGE_COLOR[jobStatus] ?? '#94a3b8');
let badgeLabel = $derived(BADGE_LABEL[jobStatus] ?? jobStatus);
```
Per UI-SPEC, this is a badge-*selection* override, not a new map entry: when `readiness?.state === 'already_created'`, override `badgeColor`/`badgeLabel` to `'#cbd5e1'` / `'Archived'` regardless of `jobStatus`. Suggested implementation: change the `$derived` expressions to check `readiness?.state === 'already_created'` first, falling back to the existing `BADGE_COLOR[jobStatus]` lookup otherwise. Reuse the exact badge `<span>` markup (lines 70-86) unchanged — only the derived color/label values change.

---

## Shared Patterns

### Dark-theme card chrome (applies to every card on both pages, including new Status History and Speakers cards)
**Source:** `[id]/+page.svelte` lines 85-93, 239-246, 277-284, 467
```svelte
style="
	background-color: #1e293b;
	border: 1px solid #334155;
	border-radius: 8px;
	padding: 24px;
	margin-bottom: 16px;
"
```

### Status badge markup (shared between list page, edit page, and RunStatusCard)
**Source:** `+page.svelte` (list) lines 18-34; `[id]/+page.svelte` lines 21-38
```svelte
`border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 14px; font-weight: 400; background-color: #1e293b; color: ${color}; display: inline-block;`
```
Apply to: list page badge (add `unpublished`), edit page badge (add `unpublished`), status log entry badges (reuse label text per UI-SPEC copy contract).

### `use:enhance` inline-save form pattern (no full page reload)
**Source:** `[id]/+page.svelte` lines 298-309 (Advocate Roles), 98-107 (Argument Details), 396-405 (Publish)
```svelte
use:enhance={() => {
	savingRoleId = participant.participant_id;
	return async ({ update }) => {
		savingRoleId = null;
		await update();
	};
}}
```
Apply to: every Speakers-section per-advocate row form (per D-04, one form per row, independent save state).

### SvelteKit form action → FastAPI fetch pattern (server-only token, error mapping)
**Source:** `[id]/+page.server.ts` lines 153-169 (publish), 174-190 (unpublish), 199-220 (delete)
```typescript
publish: async ({ params, fetch }) => {
	let res: Response;
	try {
		res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${params.id}/publish`, {
			method: 'POST',
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
	} catch {
		return fail(502, { error: 'Could not publish this argument. Try again.' });
	}
	if (!res.ok) {
		return fail(422, { error: 'Could not publish this argument. Try again.' });
	}
	throw redirect(303, '/admin/arguments/' + params.id);
},
```
Apply to: no new actions needed for publish/unpublish (existing actions already generically support re-Publish), but this is the template if any new Speakers-section save action needs a dedicated route (likely reuses `updateParticipantSide`, extended to also post `title`).

### `execution_options(synchronize_session=False)` — mandatory on every SQLAlchemy update()/delete()
**Source:** `admin_arguments.py` lines 335-339, 379-386, 410-414, 471-479; `admin_jobs.py` lines 498-506
Apply to: every modified/new `update()` call in `publish_argument`, `unpublish_argument`, `list_arguments` (n/a, read-only), `approve_job` (already present, must be preserved when adding the log-insert alongside it).

### "Extracted: X" hint convention
**Source:** `ArgumentDetailsCard.svelte` lines 98-112, 163-167, 204-207 (see full excerpt above)
Apply to: Speakers section advocate Title field's hint row (D-06).

## No Analog Found

None — every file in scope for this phase is an existing file being modified, and each modification has either a direct self-analog (same file, prior code) or a clear cross-file analog (Advocate Roles card → Speakers section; `_bench_role_and_missing_tenure` → Speakers bench rows; `RunStatusCard`'s badge-map → Archived override). No net-new architectural pattern (e.g. no new route file, no new top-level component file) is introduced by this phase.

## Metadata

**Analog search scope:** `app/src/routes/admin/arguments/`, `app/src/routes/admin/pipeline/` (RunStatusCard), `app/src/lib/components/` (ArgumentDetailsCard, ResolveCard), `api/services/admin_arguments.py`, `api/services/admin_jobs.py`, `api/services/admin_people.py`, `api/services/speakers.py`, `api/models/models.py`
**Files scanned:** 10
**Pattern extraction date:** 2026-07-07
