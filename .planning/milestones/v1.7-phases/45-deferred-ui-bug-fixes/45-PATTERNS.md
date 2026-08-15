# Phase 45: Deferred UI Bug Fixes - Pattern Map

**Mapped:** 2026-08-12
**Files analyzed:** 4 (2 modified for BUG-01, 2 modified for BUG-02)
**Analogs found:** 4 / 4 (all in-repo, sibling/parent files — no RESEARCH.md needed)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|----------------|
| `api/services/arguments.py` (`get_argument_with_utterances`) | service | CRUD (read) | `api/services/cases.py` (`get_cases`) | exact — same publish-gate predicate, same layer |
| `api/services/speakers.py` (`get_argument_speakers`) | service | CRUD (read) | `api/services/cases.py` (`get_cases`) | exact — same publish-gate predicate, same layer |
| `api/tests/test_published_gate.py` (new test class) | test | request-response (source-assertion) | `api/tests/test_published_gate.py::TestPublishedGate` (existing class in same file) | exact — same file, same AST-assertion style |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (`Popover.Content` style) | component | request-response (client render) | same file's own `Popover.Content` block; card styling analog is `SpeakerPopover.svelte`'s `.popover-card` | exact — box-model relocation between two known blocks |
| `app/src/lib/components/SpeakerPopover.svelte` (`.popover-card`) | component | request-response (client render) | itself (styling source of truth being relocated) | exact |

Router file `api/routers/arguments.py` requires **no code change** — per D-01/discretion note, either the service returns `None` for unpublished (existing 404 branch handles it) or the router raises inline. The service-return-`None` approach is the closer-fit pattern since `get_argument_with_utterances` already returns `None` for "not found" and the router already 404s on `None` (lines 41-44 below). Recommend this path — no router diff needed for the utterances endpoint. For `get_speakers`, the router currently returns whatever the service returns with no `None`/404 branch (line 47-59) — service must return `[]` (already does for "no speakers") vs 404 for "argument doesn't exist/unpublished." Need to decide: gate check should raise 404 from the service call site *only if the argument doesn't exist or isn't published*, distinct from the empty-list case (unresolved speakers on a published argument). See Pattern Assignment below for the concrete shape.

## Pattern Assignments

### `api/services/arguments.py::get_argument_with_utterances` (service, CRUD)

**Analog:** `api/services/cases.py::get_cases`

**Imports pattern** (cases.py lines 14-17 — same imports already present in arguments.py, no import changes needed):
```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument, Case, CaseArgument
```
`api/services/arguments.py` already imports `Argument` (line 20) — no new import required.

**Core gate pattern to copy** (`api/services/cases.py` lines 29-36):
```python
result = await db.execute(
    select(Case, Argument)
    .join(CaseArgument, CaseArgument.case_id == Case.id)
    .join(Argument, CaseArgument.argument_id == Argument.id)
    .where(CaseArgument.is_lead == True)  # noqa: E712 — SQLAlchemy requires == True
    .where(Argument.published_at.isnot(None))  # hide unpublished arguments (D-06)
    .order_by(Argument.argued_date.desc())
)
```

**Apply to `get_argument_with_utterances`'s Step 1** (`api/services/arguments.py` lines 45-51 today):
```python
# --- Step 1: Verify the argument exists --------------------------------
arg_result = await db.execute(
    select(Argument).where(Argument.id == argument_id)
)
argument = arg_result.scalar_one_or_none()
if argument is None:
    return None
```
Add `.where(Argument.published_at.isnot(None))` to this same `select(Argument)` query (chained `.where()`, matching the cases.py multi-`.where()` chaining convention) — an unpublished argument then falls into the exact same pre-existing `if argument is None: return None` branch, which the router (line 42-43 of `api/routers/arguments.py`) already turns into a plain 404 (D-01: indistinguishable from nonexistent). No router change needed for this endpoint.

**Error handling pattern** (unchanged — already correct): `api/routers/arguments.py` lines 41-44:
```python
result = await argument_service.get_argument_with_utterances(db, argument_id)
if result is None:
    raise HTTPException(status_code=404, detail="Argument not found")
return result
```

---

### `api/services/speakers.py::get_argument_speakers` (service, CRUD)

**Analog:** `api/services/cases.py::get_cases` (gate predicate) — but this function's control flow differs from `get_argument_with_utterances`: today it never checks argument existence at all, it goes straight to Step 0 (`argued_date` lookup) and Step 1 (person_ids), returning `[]` if no resolved speakers. There is no existing "argument not found" signal here to reuse; a `None`-vs-`[]` split must be introduced deliberately.

**Core gate pattern to copy** (same predicate as above, applied to the existing Step 0 query):

Current Step 0 (`api/services/speakers.py` lines 132-136):
```python
# Step 0 — Fetch the argument's argued_date (needed for tenure lookup) ----
arg_result = await db.execute(
    select(Argument.argued_date).where(Argument.id == argument_id)
)
argued_date = arg_result.scalar_one_or_none()
```

**Recommended change:** widen this query to also fetch `published_at` (or add a preceding existence+publish check), and short-circuit to a sentinel that the router turns into 404 — distinct from the legitimate `[]` case (published argument, zero resolved speakers). Concretely:
```python
arg_result = await db.execute(
    select(Argument.argued_date, Argument.published_at).where(Argument.id == argument_id)
)
arg_row = arg_result.one_or_none()
if arg_row is None or arg_row.published_at is None:
    return None  # router maps None -> 404; distinct from [] (no resolved speakers yet)
argued_date = arg_row.argued_date
```
This mirrors the `None`-sentinel convention already used by `get_argument_with_utterances` (return `None` for "not found/blocked", not an exception) — keeping both services consistent with the discretion note in 45-CONTEXT.md ("service functions return `None` for unpublished arguments so the existing not-found branch handles it").

**Router change required** (unlike the utterances endpoint) — `api/routers/arguments.py`'s `get_speakers` (lines 47-59) currently has no `None`/404 branch:
```python
@router.get("/{argument_id}/speakers", response_model=list[SpeakerPopoverEntry])
async def get_speakers(
    argument_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[SpeakerPopoverEntry]:
    return await speakers_service.get_argument_speakers(db, argument_id)
```
Apply the same `if result is None: raise HTTPException(404, ...)` pattern used in `get_utterances` (lines 41-44) immediately above in the same file — this is the direct in-file analog to copy, not an external one.

---

### `api/tests/test_published_gate.py` (test, source-assertion)

**Analog:** the file's own existing `TestPublishedGate` class (lines 47-119) — add a new sibling test class rather than a new file, matching the "one test module per concern, source-level AST assertions, no live DB" convention.

**Structure to copy** (lines 23-44, the source-extraction helper — parametrize by function name and file):
```python
def _get_cases_source_lines() -> list[str]:
    """Read api/services/cases.py and return non-comment, non-blank lines from get_cases()."""
    import pathlib
    source_path = pathlib.Path(__file__).parent.parent / "services" / "cases.py"
    source = source_path.read_text(encoding="utf-8")

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "get_cases":
            start = node.lineno
            end = node.end_lineno
            lines = source.splitlines()[start - 1 : end]
            non_comment = [
                line for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
            return non_comment
    return []
```
Write two parallel helpers (`_get_argument_with_utterances_source_lines()` targeting `api/services/arguments.py`, `_get_argument_speakers_source_lines()` targeting `api/services/speakers.py`), then a new test class (e.g. `TestArgumentDetailPublishedGate`) with the same two-assertion shape as `test_get_cases_uses_published_at_filter` / `test_get_cases_does_not_use_resolved_at_filter` (lines 50-83): assert `"Argument.published_at.isnot"` is present and `"Argument.resolved_at.isnot"` is absent, for each of the two gated functions.

---

### `app/src/lib/components/SpeakerPopover.svelte` + `+page.svelte` `Popover.Content` (component, request-response/render — box-model fix)

**Analog:** same two files, before/after states already fully specified in 45-UI-SPEC.md's Box-Model Contract table — this is a pure relocation, not a new-pattern derivation.

**Current split (to remove):**

`SpeakerPopover.svelte` lines 232-242 (style block — remove these 3 properties from here):
```css
.popover-card {
	background-color: #1e293b;
	border: 1px solid #334155;
	border-radius: 8px;
	padding: 24px;
	min-width: 300px;
	max-width: 400px;
	display: block;
}
```

`+page.svelte` lines 139-150 (current `Popover.Content` — owns scroll only, no visible boundary):
```svelte
<Popover.Content
	customAnchor={currentAnchor}
	sideOffset={8}
	trapFocus={true}
	escapeKeydownBehavior="close"
	interactOutsideBehavior="close"
	style="z-index: 50; max-height: min(560px, 80vh); overflow-y: auto;"
>
	{#if currentSpeaker}
		<SpeakerPopover speaker={currentSpeaker} />
	{/if}
</Popover.Content>
```

**Required fix** — move `background-color`/`border`/`border-radius`/`min-width`/`max-width` onto the `Popover.Content` inline `style=` string (same inline-`style=` convention already used for `z-index`/`max-height`/`overflow-y` at line 145 — this file has no `<style>` block and does not use Tailwind classes, matching 45-UI-SPEC's "hand-rolled inline `style=`" note):
```svelte
<Popover.Content
	customAnchor={currentAnchor}
	sideOffset={8}
	trapFocus={true}
	escapeKeydownBehavior="close"
	interactOutsideBehavior="close"
	style="z-index: 50; max-height: min(560px, 80vh); overflow-y: auto;
	       background-color: #1e293b; border: 1px solid #334155; border-radius: 8px;
	       min-width: 300px; max-width: 400px;"
>
	{#if currentSpeaker}
		<SpeakerPopover speaker={currentSpeaker} />
	{/if}
</Popover.Content>
```
And in `SpeakerPopover.svelte`, shrink `.popover-card` to padding-only (padding is "not load-bearing," per UI-SPEC, and may stay here):
```css
.popover-card {
	padding: 24px;
	display: block;
}
```
Padding may alternatively move up to `Popover.Content` — UI-SPEC treats both as acceptable; leaving it on `.popover-card` is the smaller diff and is the recommended choice.

**No other lines in `SpeakerPopover.svelte` change** — every field-rendering block (avatar, name/pill, birth/death, descriptor, bio, tenure list, lines 137-230) is untouched; this is confirmed by the Regression Checklist in 45-UI-SPEC.md, which enumerates every field that must render unchanged.

---

## Shared Patterns

### Publish-status gate predicate (BUG-01)
**Source:** `api/services/cases.py` line 34 — `.where(Argument.published_at.isnot(None))`
**Apply to:** `api/services/arguments.py::get_argument_with_utterances` (Step 1 query) and `api/services/speakers.py::get_argument_speakers` (Step 0 query)
**Rule:** always gate on `published_at`, never `resolved_at` — this exact distinction is what `test_published_gate.py` asserts today for `cases.py` and what the new tests must assert for these two functions.

### "Return `None` for not-found/blocked, let router 404" convention
**Source:** `api/services/arguments.py` lines 49-51 (`if argument is None: return None`) + `api/routers/arguments.py` lines 41-44 (`if result is None: raise HTTPException(404, ...)`)
**Apply to:** both `get_argument_with_utterances` (already follows this — just widen the gate) and `get_argument_speakers` (needs a new `None`-vs-`[]` distinction, plus a new 404 branch added to the `get_speakers` router handler, copying the `get_utterances` handler's shape verbatim).

### Source-level AST-assertion test style (no live DB)
**Source:** `api/tests/test_published_gate.py` lines 17-119 (`_db_configured`, `_get_cases_source_lines`, `TestPublishedGate`)
**Apply to:** new test class(es) covering `get_argument_with_utterances` and `get_argument_speakers`, added to the same file.

### Inline `style=` attribute convention (no Tailwind, no `<style>` block in `+page.svelte`)
**Source:** `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` line 145 (existing `Popover.Content` `style=`)
**Apply to:** the box-model fix — new properties are appended to the same inline `style=` string, not extracted to a class or `<style>` block, to match the file's existing convention.

## No Analog Found

None — both bugs are fully scoped to files with direct, in-repo sibling/parent analogs (in three of four cases, the analog is a different function in the *same* file). No RESEARCH.md was needed or produced for this phase.

## Metadata

**Analog search scope:** `api/services/`, `api/routers/`, `api/tests/`, `app/src/lib/components/`, `app/src/routes/cases/[slug]/arguments/[id]/`
**Files read:** `api/services/cases.py`, `api/tests/test_published_gate.py`, `api/routers/arguments.py`, `api/services/arguments.py`, `api/services/speakers.py`, `app/src/lib/components/SpeakerPopover.svelte`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`
**Pattern extraction date:** 2026-08-12
