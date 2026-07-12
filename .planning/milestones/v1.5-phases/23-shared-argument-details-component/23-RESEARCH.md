# Phase 23: Shared Argument Details Component — Research

**Researched:** 2026-07-02
**Domain:** SvelteKit 2.x / Svelte 5 Runes, FastAPI, admin UI component authoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `ArgumentDetailsCard` owns its own `<form method="POST" use:enhance>` element. It takes an `action` prop for the save target (e.g., `?/saveJobMetadata` on pipeline job detail, `?/save` on argument edit). Phase 26 reuse is plug-in: same component, different `action` prop.

**D-02:** The component replaces the existing Argument Metadata save form on `pipeline/[id]` entirely — no coexistence with the old form.

**D-03:** Data flows to the component as props from the parent page: `<ArgumentDetailsCard savedValues={...} hints={...} action="..." />`. No data fetching inside the component — consistent with the architecture rule that all data fetching lives in `+page.server.ts`.

**D-04:** Operator adds a docket pill by typing a docket number and pressing **Enter**. The input field clears and the docket appears as a removable pill. Keyboard-first; no visible "Add" button needed.

**D-05:** Each pill serializes as a separate `<input type="hidden" name="docket[]" value="...">` in the form. Server reads `FormData.getAll('docket[]')`. No JSON serialization or comma-splitting needed.

**D-06:** On failed save (server returns a form error), the component restores pill state from the submitted dockets in the `form` prop — not from `savedValues`. Operator does not lose unsaved pill changes.

**D-07:** Extracted hints appear **below each editable input** as small muted text. Linear layout, no second column, works on narrow screens.

**D-08:** Hint prefix is `"Extracted: [value]"` — e.g., `"Extracted: October 12, 2024"` or `"Extracted: N/A"`.

**D-09:** For the docket hint (potentially multiple extracted dockets): each extracted docket displays as its own **small read-only pill/tag** in the hint area below the docket input. Not comma-joined.

### Claude's Discretion

- Component and prop naming (`ArgumentDetailsCard`, prop shapes) — follow PascalCase component convention, camelCase props
- Whether `savedValues` and `hints` are separate props or a single merged prop — researcher can determine cleanest shape given existing `cover_metadata` JSONB structure
- Parse stat card data sourcing (new API response fields vs. reading from existing argument/job fields) — researcher audits what's available; Phase 23 may need backend additions

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AEDIT-03 | Argument Details card mirrors the pipeline job detail version: docket pill/tag, question number free text, argued date, extracted hints always visible from `cover_metadata`; "N/A" if nothing extracted | Component architecture with `hints` prop from `cover_metadata` JSONB |
| AEDIT-04 | Argument Details card is a shared component — same UI on pipeline/[id] and arguments/[id], different save targets | `action` prop pattern (D-01) enables single component with two consumers |
| PJOB-03 | Argument metadata section renamed to "Argument Details" | Copy change inside new component |
| PJOB-04 | Extracted hints always visible alongside editable fields, even after fields are filled; "N/A" if nothing was extracted | Hint row always rendered (D-07/D-08), mutable `savedValues` never changes hint visibility |
| PJOB-05 | Docket: pill/tag UI (consistent with PLIST-02) | Svelte 5 `$state` pill list + hidden inputs per D-04/D-05 |
| PJOB-06 | Question number: free text field (consistent with PLIST-01) | Plain `<input type="text">` replacing current integer dropdown |
| PJOB-07 | Save saves run metadata only — does not create the argument | New `saveJobMetadata` action on `+page.server.ts` targets a new FastAPI endpoint that writes to `AdminJob`-linked fields only |
| PJOB-09 | Ingest card: remove source file display (now shown in run status card) | Delete the "Source file" row from the ingest step card block |
| PJOB-10 | Parse card shows: Utterances, Speakers (Bench / Advocate / Total), Case Name, Argued Date, Docket(s), Question Number(s) | Backend `ParseStats` schema must gain 5 new fields; `get_job` service function must query them |
| PJOB-11 | Parse card shows unextracted fields alongside extracted values — "N/A" for missing | Frontend N/A rendering + always-render discipline for all parse stat rows |
| PJOB-12 | Parse card extracted values match the hints shown in the Argument Details card | Both read from `Argument.cover_metadata` JSONB — confirmed shared source |
</phase_requirements>

---

## Summary

Phase 23 builds a single reusable `ArgumentDetailsCard.svelte` component — docket pills, question number free-text, argued date, and extracted hints — and wires it to the pipeline job detail page as its first consumer. Two backend changes accompany the frontend work: (1) a new `saveJobMetadata` SvelteKit form action + FastAPI endpoint that saves dockets/question number/argued date against the `AdminJob`'s linked argument without creating an argument; and (2) an expanded `ParseStats` response that adds `bench_count`, `advocate_count`, `total_speaker_count`, and `cover_metadata`-derived fields for PJOB-10/11/12.

The cover_metadata JSONB on `Argument` contains exactly three keys: `argued_date` (a date serialized to ISO string), `case_name`, and `primary_docket`. The schema does NOT have a `question_number` key in `cover_metadata` — `question_number` is a separate integer column (`Argument.question_number`) with no extracted analogue in `cover_metadata`. The UI-SPEC's `hints.question_number` field therefore comes from `Argument.question_number` itself (the value stored at ingest time), not from a cover extractor key. This is a critical distinction for prop shape design.

The existing `saveMetadata` action on `pipeline/[id]/+page.server.ts` saves to the `Argument` record via `/api/admin/arguments/{id}/metadata`. PJOB-07 requires a **new** `saveJobMetadata` action that saves run-level metadata (dockets, question number) without creating an argument and without necessarily having an argument_id. This requires a new FastAPI endpoint or a redefined target — the researcher recommendation is a new PATCH endpoint on the job itself, or alternatively, a write to the `AdminJob` row directly. The architectural clarification below resolves this.

**Primary recommendation:** Implement `ArgumentDetailsCard` per the UI-SPEC contract; add `bench_count`/`advocate_count`/`total_speaker_count`/`cover_metadata` fields to the `ParseStats` schema and `get_job` service; implement `saveJobMetadata` as a new SvelteKit action that PATCHes argument metadata only when `argument_id` is set (mirroring the existing `saveMetadata` flow but scoped to dockets + question number).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Docket pill/tag interaction (add/remove) | Browser / Client | — | Pure client state; no network call until Save |
| Hint display from `cover_metadata` | Frontend Server (SSR) | — | Data fetched in `+page.server.ts` load; passed as props |
| Save Argument Details | API / Backend | Frontend Server | Form action → FastAPI PATCH |
| Parse stat card expanded fields | API / Backend | Frontend Server | New queries in `admin_jobs.get_job` service |
| `cover_metadata` JSONB source-of-truth | Database / Storage | — | Written by parse step; read by job load and argument detail load |
| FormData `docket[]` serialization | Browser / Client | Frontend Server | Hidden inputs serialized by browser; read by SvelteKit action |

---

## Standard Stack

This phase installs no new packages. All libraries listed are already in the project.

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SvelteKit | 2.x | Routing, server loads, form actions | Project stack |
| Svelte 5 (Runes) | 5.x | `$state`, `$derived`, `$props`, `$effect` | Project lock — no legacy stores |
| FastAPI | 0.115+ | API endpoints, Pydantic v2 schemas | Project stack |
| SQLAlchemy 2.0 async | 2.0 | ORM queries in service layer | Project stack |

### No New Packages

No new npm or PyPI packages are required for this phase. The UI is pure inline CSS (no bits-ui headless components needed). The backend adds new service queries, not new libraries.

---

## Package Legitimacy Audit

Not applicable — no new packages are installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
Operator browser
  │
  ├─ GET /admin/pipeline/[job_id]
  │    └─ +page.server.ts load()
  │         ├─ GET /api/admin/jobs/{job_id}   → AdminJobResponse (parse_stats expanded)
  │         └─ GET /api/admin/arguments/{arg_id}  → ArgumentDetail (cover_metadata)
  │              ↓
  │         Returns: { job, argument, ... }
  │              ↓
  │    +page.svelte renders ArgumentDetailsCard
  │         savedValues={dockets, question_number, argued_date}
  │         hints={cover_metadata fields}
  │         action="?/saveJobMetadata"
  │
  ├─ POST ?/saveJobMetadata
  │    └─ +page.server.ts saveJobMetadata action
  │         ├─ reads FormData: docket[] (array), question_number, argued_date
  │         └─ PATCH /api/admin/arguments/{arg_id}/metadata  (existing endpoint, new fields)
  │
  └─ Polling fetch /admin/pipeline/[job_id] (JSON)
       └─ GET /api/admin/jobs/{job_id}
            └─ get_job() service:
                 ├─ parse_stats.utterance_count  (existing)
                 ├─ parse_stats.speaker_count    (existing, renamed total_speaker_count)
                 ├─ parse_stats.bench_count       (NEW)
                 ├─ parse_stats.advocate_count    (NEW)
                 └─ parse_stats.cover_metadata    (NEW — from Argument row)
```

### Recommended Project Structure

No new directories. New files:

```
app/src/lib/components/
└── ArgumentDetailsCard.svelte   ← NEW

app/src/routes/admin/pipeline/[job_id]/
├── +page.svelte                  ← MODIFIED (replace Argument Metadata form, expand parse stat card)
└── +page.server.ts               ← MODIFIED (add saveJobMetadata action, expose savedValues/hints)
```

Backend (no new files — only additions to existing):

```
api/schemas/admin_jobs.py         ← MODIFIED (expand ParseStats, new MetadataJobUpdate schema)
api/services/admin_jobs.py        ← MODIFIED (get_job adds bench/advocate counts + cover_metadata)
api/routers/admin.py              ← possibly MODIFIED (if new endpoint needed for dockets array)
```

### Pattern 1: Svelte 5 Runes — Pill List State

The pill list is `$state` initialized from `savedValues.dockets`. The `onkeydown` handler on the input intercepts Enter to push a pill. Hidden inputs are rendered with `{#each pills}`.

```svelte
<!-- Source: project codebase — established Svelte 5 pattern -->
<script lang="ts">
  let { savedValues, hints, action, readonly = false, form } = $props();

  let pills = $state<string[]>(savedValues.dockets ?? []);
  let docketInput = $state('');
  let saving = $state(false);

  // D-06: on failed save, restore pills from form.dockets (not savedValues)
  $effect(() => {
    if (form?.dockets) {
      pills = form.dockets;
    }
  });

  function addPill() {
    const v = docketInput.trim();
    if (v && !pills.includes(v)) {
      pills = [...pills, v];
    }
    docketInput = '';
  }
</script>

{#each pills as pill}
  <input type="hidden" name="docket[]" value={pill} />
{/each}

<input
  type="text"
  bind:value={docketInput}
  placeholder="Add docket and press Enter…"
  onkeydown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addPill(); } }}
/>
```

### Pattern 2: `use:enhance` with `saving` State

Follows the exact pattern used for existing forms on this page. Note: `update({ reset: false })` must be passed so pill state is not wiped on success.

```svelte
<!-- Source: project codebase — pipeline/[job_id]/+page.svelte and arguments/[id]/+page.svelte -->
<form method="POST" {action} use:enhance={() => {
  saving = true;
  return async ({ result, update }) => {
    saving = false;
    if (result.type === 'failure') {
      await update();
    } else {
      await update({ reset: false });
    }
  };
}}>
```

### Pattern 3: FormData `docket[]` Array on the Server

In the SvelteKit `saveJobMetadata` action:

```typescript
// Source: project codebase — D-05 pattern
const dockets = formData.getAll('docket[]') as string[];
const question_number = ((formData.get('question_number') as string) ?? '').trim() || null;
const argued_date = ((formData.get('argued_date') as string) ?? '').trim() || null;
```

The existing `MetadataUpdate` Pydantic schema (`api/schemas/admin_arguments.py`) must be extended or a new schema created that includes `dockets: list[str]` and `question_number: Optional[str]`.

### Pattern 4: Expanded `ParseStats` in `get_job` Service

The `get_job` function in `api/services/admin_jobs.py` currently attaches `parse_stats` as a dynamic dict with `utterance_count` and `speaker_count`. PJOB-10 requires 3 new numeric fields and `cover_metadata` pass-through.

Key queries to add:
```python
# Bench count — participants with side=BENCH resolved in this argument
bench_result = await db.execute(
    select(func.count(ArgumentParticipant.id))
    .where(
        ArgumentParticipant.argument_id == job.argument_id,
        ArgumentParticipant.side == SideEnum.BENCH,
        ArgumentParticipant.person_id.isnot(None),
    )
)
bench_count = bench_result.scalar_one()

# Advocate count — participants with side != BENCH resolved in this argument
advocate_result = await db.execute(
    select(func.count(ArgumentParticipant.id))
    .where(
        ArgumentParticipant.argument_id == job.argument_id,
        ArgumentParticipant.side != SideEnum.BENCH,
        ArgumentParticipant.person_id.isnot(None),
    )
)
advocate_count = advocate_result.scalar_one()

# cover_metadata — from the Argument row directly
arg_result = await db.execute(
    select(Argument.cover_metadata, Argument.question_number)
    .where(Argument.id == job.argument_id)
)
arg_row = arg_result.one_or_none()
cover_metadata = arg_row.cover_metadata if arg_row else None
question_number_val = arg_row.question_number if arg_row else None
```

Note: `Argument.question_number` is the DB column (integer, not from cover extractor). It is the question number set at ingest time. The hints prop for question_number comes from this value, not from `cover_metadata`.

### Anti-Patterns to Avoid

- **Fetching data inside `ArgumentDetailsCard`:** The component must be purely presentational. All data comes via props from `+page.server.ts` load — violation of the architecture rule in CLAUDE.md.
- **Using `update({ reset: true })` after a successful save:** This wipes `$state` pill list back to empty. Always use `update({ reset: false })` so UI state is preserved.
- **Reading `cover_metadata.question_number`:** This key does NOT exist in `cover_metadata`. The cover extractor writes `argued_date`, `case_name`, and `primary_docket` only. `question_number` is `Argument.question_number` (integer column) set at ingest.
- **Showing the hint only when value differs from saved:** PJOB-04 and D-07 require hints to be **always visible**, even after the operator has filled the field. The existing `saveMetadata` code conditionally showed the hint (`{#if data.argument?.cover_metadata?.case_name != null && data.argument?.cover_metadata?.case_name !== data.argument.case_name}`) — this is the pattern to replace.
- **`save` action name collision on `pipeline/[id]`:** The new action must be named `saveJobMetadata`, not `save` or `saveMetadata`, to avoid collision with any future action renaming.
- **Docket serialization via JSON or comma-split:** D-05 locks serialization to hidden inputs (`name="docket[]"`). The server uses `FormData.getAll('docket[]')`. No JSON parsing.
- **`Base.metadata.create_all` for schema changes:** CLAUDE.md hard constraint — Alembic is the sole DDL authority. Phase 23 adds no schema changes, so this is not an issue, but any impulse to add a `dockets` column to `AdminJob` must be resisted.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form enhancement | Custom `fetch` POST | SvelteKit `use:enhance` from `$app/forms` | Already used on this page; handles progressive enhancement, form reset, result routing |
| Date formatting | Custom date logic | Existing `formatDate()` helper in `+page.svelte` | Already defined in the page; extract to `$lib/utils.ts` or pass formatted string as prop |
| Duplicate pill detection | Complex state | `pills.includes(v)` — one-liner | D-04 says silent reject on duplicate |

---

## cover_metadata JSONB — Confirmed Key Inventory

[VERIFIED: cover_extractor.py source read this session]

`extract_cover_metadata()` in `pipeline/parser/cover_extractor.py` returns a dict with AT MOST these three keys:

| Key | Type stored | Notes |
|-----|-------------|-------|
| `argued_date` | `datetime.date` (serialized to ISO string for JSONB) | Extracted from cover page date line |
| `case_name` | `str` | Lead petitioner name |
| `primary_docket` | `str` | Single docket number (e.g. `"22-123"`) — only ONE docket |

**There is no `question_number` key in `cover_metadata`.** Question number is `Argument.question_number` (Integer column, default 1, set at ingest via `--question` CLI arg).

**There is no `consolidated_dockets` array in `cover_metadata`.** The cover extractor only extracts the first docket it finds. Multiple dockets are stored via the `case_arguments` M:M table (linked `Case` rows), not in `cover_metadata`.

### Implication for Props Shape

The UI-SPEC's `hints` prop is:

```ts
hints: {
  dockets: string[];        // from cover_metadata.primary_docket → wrap in array: [primary_docket] or []
  question_number: string | null;  // from Argument.question_number (integer → string display)
  argued_date: string | null;  // from cover_metadata.argued_date (ISO string)
  case_name: string | null;    // from cover_metadata.case_name
}
```

This is consistent but requires the `+page.server.ts` load (or a new backend field) to construct the `hints` object. The simplest approach: load constructs `hints` directly from `data.argument.cover_metadata` (already in the `ArgumentPreview` type).

For `question_number` hint: the "extracted" value shown is `Argument.question_number` formatted as a string (e.g., `"1"` or `"2"`). Since this is set at ingest time by the operator, calling it "Extracted: 1" may be slightly misleading but is consistent with the hint system — it shows the value the pipeline captured. The frontend simply reads `data.argument.question_number` and formats it as a string.

---

## `saveJobMetadata` Action — Architecture Clarification

**PJOB-07:** "Save saves run metadata only — does not create the argument."

The current `saveMetadata` action (pipeline/[id]) requires `argument_id != null` — it PATCH-es the Argument record. The new `saveJobMetadata` action covers the case where the operator is filling in details on a job that has an `argument_id` (the argument exists in `pipeline` state).

The key difference from the current `saveMetadata`:
- Must accept `docket[]` array (multiple dockets) rather than `source_docket` (single string)
- Must save `question_number` (currently only settable at ingest time via CLI)
- Must NOT create an argument (guard: if `argument_id == null`, return failure; do not ingest)

**Backend surface options:**

Option A (recommended): Extend the existing `PATCH /api/admin/arguments/{id}/metadata` endpoint to accept `dockets: list[str]` and `question_number: Optional[str]`. The `MetadataUpdate` Pydantic schema gains two new optional fields. The service updates `Argument.source_docket` to `dockets[0]` if provided and `Argument.question_number` to the parsed int.

Option B: New endpoint `PATCH /api/admin/jobs/{job_id}/metadata` that internally fetches `argument_id` then patches the Argument.

**Recommendation: Option A.** It reuses the existing auth-protected endpoint and the `MetadataUpdate` schema. The SvelteKit action constructs `source_docket = dockets[0]` before sending (or sends all dockets and the service picks the primary).

**PJOB-07 semantics confirmed:** The "does not create the argument" requirement means this save action must never call the `approve` endpoint. It only writes to the already-existing Argument row. When `argument_id == null`, the action returns `fail(400, { saveError: 'No argument linked to this job yet.' })` — identical guard to the existing `saveMetadata`.

---

## Existing Form Being Replaced

[VERIFIED: source read this session]

The current "Argument Metadata" form on `pipeline/[id]/+page.svelte` (lines 508–601):
- Is conditionally rendered: `{#if data.argument != null}`
- Saves to action `?/saveMetadata`
- Fields: `case_name` (text), `source_docket` (text, single value), `argued_date` (date)
- Shows hints only when extracted value DIFFERS from saved value (must be replaced with always-visible hints)
- Uses `data.argument.cover_metadata.primary_docket` for hint text

**The `ArgumentDetailsCard` component replaces this entire block.** The old `saveMetadata` action on `+page.server.ts` remains but can be kept or removed — the new `saveJobMetadata` action is what `ArgumentDetailsCard` targets on this page.

---

## Source File Row Removal (PJOB-09)

[VERIFIED: source read this session]

Lines 677–682 of `+page.svelte` (inside the ingest step card block):

```svelte
{#if step === 'ingest' && (liveJob.original_filename || liveJob.pdf_url)}
  <div style="margin-top: 12px;">
    <span style="display: block; font-size: 14px; ...">Source file</span>
    <span style="font-size: 16px; ...">{liveJob.original_filename ?? liveJob.pdf_url}</span>
  </div>
{/if}
```

This entire block is deleted (PJOB-09). No replacement on this page — source file moves to the run status card in Phase 25.

---

## Parse Stat Card Current State vs. Required State

[VERIFIED: source read this session]

**Current** (lines 685–706 of `+page.svelte`):
- Shows `ps.utterance_count` and `ps.speaker_count` (renamed "Distinct speakers")
- Shows `data.argument.case_name` and `data.argument.argued_date` (from argument record, not cover_metadata)
- No N/A states — missing fields silently absent

**Required after Phase 23** (PJOB-10/11/12):
- `ps.utterance_count` — Utterances
- `ps.bench_count` — Bench speakers (N/A when null)
- `ps.advocate_count` — Advocate speakers (N/A when null)
- `ps.total_speaker_count` — Total speakers (N/A when null)
- `ps.cover_metadata.case_name` — Case name (N/A when null/empty)
- `ps.cover_metadata.argued_date` — Argued (N/A when null)
- `ps.cover_metadata.primary_docket` — Docket(s) as read-only pill(s) (N/A when empty)
- `ps.question_number` — Question number from Argument.question_number (N/A when null)

PJOB-12: All `cover_metadata` fields in the parse stat card MUST match the hints in `ArgumentDetailsCard` — same source (`Argument.cover_metadata`) guarantees this. The `+page.server.ts` can either re-read these from `data.argument.cover_metadata` OR the `parse_stats` object can carry them from the backend. Backend approach is cleaner (single source for polling JSON response; no separate data dependency).

---

## `ParseStats` Schema Changes Required

[VERIFIED: api/schemas/admin_jobs.py read this session]

Current `ParseStats` Pydantic model:
```python
class ParseStats(BaseModel):
    utterance_count: int
    speaker_count: int
```

Required expanded model:
```python
class ParseStats(BaseModel):
    utterance_count: int
    speaker_count: int  # keep for backward compat, equals total_speaker_count
    # New fields for PJOB-10
    bench_count: Optional[int] = None
    advocate_count: Optional[int] = None
    total_speaker_count: Optional[int] = None
    # cover_metadata pass-through for PJOB-10/12
    case_name: Optional[str] = None
    argued_date: Optional[str] = None   # ISO date string
    primary_docket: Optional[str] = None
    question_number: Optional[int] = None
```

**Note:** The `speaker_count` field must be retained for backward compatibility with the polling JavaScript in `+page.svelte` (TypeScript interface `ParseStats` declares `speaker_count: number`). Both `speaker_count` and `total_speaker_count` can be set to the same value, or `total_speaker_count` can be derived from bench + advocate counts.

The `cover_metadata` fields are added directly to `ParseStats` rather than as a nested dict because the frontend TypeScript interface is flatter and safer to extend.

---

## `ArgumentPreview` Type — Server Load Additions

[VERIFIED: api/+page.server.ts for pipeline job read this session]

The `ArgumentPreview` type in `+page.server.ts` currently:
```typescript
interface ArgumentPreview {
  id: number;
  case_name: string;
  docket_number: string;
  argued_date: string | null;
  resolved_at: string | null;
  published_at: string | null;
  status: string | null;
  source_docket: string | null;
  cover_metadata: Record<string, unknown> | null;
}
```

Phase 23 adds: reading `argument.cover_metadata` to construct `hints` for `ArgumentDetailsCard`, and reading `argument.source_docket` + `argument.question_number` to construct `savedValues`. The `question_number` field is **not** currently in `ArgumentPreview` or `ArgumentDetail` — it must be added to `ArgumentDetail` (backend schema) and `ArgumentPreview` (TypeScript interface). `Argument.question_number` is an integer column that already exists in the DB.

**Backend addition needed:** `ArgumentDetail` Pydantic schema gains `question_number: Optional[int] = None`. The `get_argument_detail` service function must include `question_number` in its return dict.

---

## `savedValues` and `hints` Prop Shape — Final Recommendation

Based on codebase audit:

```typescript
// savedValues: operator-confirmed values from the Argument record
interface SavedValues {
  dockets: string[];       // from [source_docket] (wrap single string in array) or []
  question_number: string; // from Argument.question_number formatted as string, or ''
  argued_date: string | null; // ISO YYYY-MM-DD from Argument.argued_date
}

// hints: raw extraction output from cover_metadata JSONB
interface Hints {
  dockets: string[];          // from cover_metadata.primary_docket → [primary_docket] or []
  question_number: string | null; // from Argument.question_number (no cover extractor source)
  argued_date: string | null;  // from cover_metadata.argued_date (ISO string)
  case_name: string | null;    // from cover_metadata.case_name (shown in parse stat card)
}
```

Note: `hints.question_number` uses `Argument.question_number` (ingest-time value), same as `savedValues.question_number`. The distinction is intentional: `savedValues.question_number` is what the operator last saved; `hints.question_number` is what the pipeline captured at ingest. If the operator changes question_number, `savedValues` updates but `hints` stays constant. In practice these will often be the same since question_number is rarely changed post-ingest.

The `+page.server.ts` load constructs these shapes:
```typescript
const savedValues = {
  dockets: argument.source_docket ? [argument.source_docket] : [],
  question_number: argument.question_number != null ? String(argument.question_number) : '',
  argued_date: argument.argued_date ? argument.argued_date.slice(0, 10) : null,
};

const hints = {
  dockets: argument.cover_metadata?.primary_docket
    ? [argument.cover_metadata.primary_docket as string]
    : [],
  question_number: argument.question_number != null
    ? String(argument.question_number)
    : null,
  argued_date: (argument.cover_metadata?.argued_date as string) ?? null,
  case_name: (argument.cover_metadata?.case_name as string) ?? null,
};
```

---

## Common Pitfalls

### Pitfall 1: Pill State Not Restored After Failed Save
**What goes wrong:** After a server-side save failure, `pills` stays at the pre-submit value because `update()` replaces `form` with the failure result but `pills` is `$state` initialized from `savedValues`.
**Why it happens:** `savedValues.dockets` is the initial value; pill state diverges as operator adds pills; on failure `$state` doesn't automatically sync.
**How to avoid:** D-06 — use a `$effect` that watches `form?.dockets` and sets `pills = form.dockets` when present. The server must echo back `dockets` in the `fail()` return.
**Warning signs:** Operator adds 3 pills, save fails, pills revert to the original list.

### Pitfall 2: Enter Key Submits Form Instead of Adding Pill
**What goes wrong:** Pressing Enter in the docket input field submits the enclosing `<form>` before the pill add handler fires.
**Why it happens:** The docket input is inside the `<form>` element. Enter in a text input triggers form submission by default.
**How to avoid:** `onkeydown` handler must call `e.preventDefault()` before calling `addPill()`.
**Warning signs:** First docket typed submits the form rather than adding a pill.

### Pitfall 3: `cover_metadata.question_number` Does Not Exist
**What goes wrong:** Code reads `argument.cover_metadata?.question_number` and gets `undefined`, causing hint row to always show "Extracted: N/A".
**Why it happens:** The cover extractor only writes three keys (`argued_date`, `case_name`, `primary_docket`). `question_number` is never in `cover_metadata`.
**How to avoid:** Read `Argument.question_number` (the integer column) for both `savedValues.question_number` and `hints.question_number`.
**Warning signs:** Question number hint always shows N/A even though question_number is 1 in the database.

### Pitfall 4: `update({ reset: true })` Wipes Pill State on Success
**What goes wrong:** After a successful save, the form resets and `pills` reverts to the initially-rendered list (pre-edit).
**Why it happens:** `use:enhance`'s default `update()` resets the form — this re-triggers Svelte's initialization of `$state`.
**How to avoid:** Always use `update({ reset: false })` in the success path.
**Warning signs:** Successfully saving 3 pills causes the page to show only the original pills.

### Pitfall 5: Old `saveMetadata` Action Still Present Creates Confusion
**What goes wrong:** Two actions (`saveMetadata` and `saveJobMetadata`) with overlapping field sets; form action attribute typo uses wrong one.
**Why it happens:** The old form is replaced but its action may remain in `+page.server.ts`.
**How to avoid:** The old `saveMetadata` action can be retained but must not be referenced by `ArgumentDetailsCard`. The component uses `action` prop value only. Consider removing `saveMetadata` in this phase since D-02 says no coexistence.
**Warning signs:** Save button saves case_name (old action) instead of dockets + question_number (new action).

### Pitfall 6: `argument_id` Null When Operator Saves Early
**What goes wrong:** Operator reaches the job detail page before ingest completes; `argument_id` is null; `saveJobMetadata` action fails with an opaque error.
**Why it happens:** `AdminJob.argument_id` starts null until the ingest step writes the Argument row.
**How to avoid:** The `saveJobMetadata` action must guard `if (argumentId == null) return fail(400, { saveError: 'Run not ready — complete ingest first.' })`. The UI (ArgumentDetailsCard) should not be rendered until `data.argument != null` (same condition as the existing form).
**Warning signs:** Null pointer error in the server action.

### Pitfall 7: Parse Stat Card PJOB-12 Source Mismatch
**What goes wrong:** Parse stat card shows `data.argument.case_name` (from the Case table, operator-editable) instead of `cover_metadata.case_name` (from the cover extractor). These can diverge after an operator edits the case name.
**Why it happens:** Existing code already reads from `data.argument` for the parse stat case_name/argued_date. PJOB-12 requires reading from `cover_metadata`.
**How to avoid:** Parse stat card must read from `ps.case_name` (passed through `ParseStats` from `cover_metadata`), not `data.argument.case_name`.
**Warning signs:** Editing case name on the argument edit page changes what appears in the parse stat card.

---

## Code Examples

### ArgumentDetailsCard Internal State Initialization

```svelte
<!-- Source: established Svelte 5 pattern from project codebase -->
<script lang="ts">
  interface ArgumentDetailsCardProps {
    savedValues: {
      dockets: string[];
      question_number: string;
      argued_date: string | null;
    };
    hints: {
      dockets: string[];
      question_number: string | null;
      argued_date: string | null;
      case_name: string | null;
    };
    action: string;
    readonly?: boolean;
    form?: { dockets?: string[]; saveError?: string; saved?: boolean } | null;
  }

  let { savedValues, hints, action, readonly = false, form = null }: ArgumentDetailsCardProps = $props();

  let pills = $state<string[]>(savedValues.dockets ?? []);
  let docketInput = $state('');
  let saving = $state(false);

  // D-06: restore pill state from server echo on failed save
  $effect(() => {
    if (form?.dockets) {
      pills = form.dockets;
    }
  });
</script>
```

### Hint Row — Always Visible, N/A Italic

```svelte
<!-- Source: UI-SPEC + D-07/D-08 decisions -->
{#snippet hintRow(value: string | null)}
  <p style="font-size: 14px; font-weight: 400; color: #94a3b8; margin-top: 4px;{!value ? ' font-style: italic;' : ''}">
    Extracted: {value ?? 'N/A'}
  </p>
{/snippet}
```

### `saveJobMetadata` Server Action Pattern

```typescript
// Source: project codebase pattern from existing saveMetadata action
saveJobMetadata: async ({ request, params }) => {
  const data = await request.formData();
  const dockets = (data.getAll('docket[]') as string[]).filter(v => v.trim());
  const question_number_raw = ((data.get('question_number') as string) ?? '').trim();
  const argued_date = ((data.get('argued_date') as string) ?? '').trim() || null;

  // Fetch job to get argument_id (same two-step pattern as approve/saveMetadata)
  let argumentId: number | null = null;
  try {
    const jobRes = await fetch(`${FASTAPI_BASE_URL}/api/admin/jobs/${params.job_id}`, {
      headers: { 'X-Admin-Token': ADMIN_TOKEN },
    });
    if (jobRes.ok) {
      const job = await jobRes.json();
      argumentId = job.argument_id ?? null;
    }
  } catch {
    return fail(502, { saveError: 'Could not save. Try again.', dockets });
  }

  if (argumentId === null) {
    return fail(400, { saveError: 'No argument linked to this run yet.', dockets });
  }

  // PATCH to existing metadata endpoint (extended to accept dockets + question_number)
  const res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argumentId}/metadata`, {
    method: 'PATCH',
    headers: { 'X-Admin-Token': ADMIN_TOKEN, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_docket: dockets[0] ?? null,
      argued_date,
      question_number: question_number_raw ? parseInt(question_number_raw, 10) : null,
    }),
  });

  if (!res.ok) return fail(422, { saveError: 'Could not save. Try again.', dockets });
  return { saved: true };
},
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Svelte 4 `export let` + `$:` reactive | Svelte 5 Runes `$props()` + `$state()` | Project locked to Svelte 5 | No legacy reactivity patterns allowed |
| Comma-separated docket string | Pill/tag UI with `<input type="hidden" name="docket[]">` | Phase 23 (D-05) | Server reads array via `getAll()` |
| Show hint only when value differs | Always-show hint, N/A when null | Phase 23 (PJOB-04) | Operator always sees extraction provenance |
| `speaker_count` (total) | Bench / Advocate / Total breakdown | Phase 23 (PJOB-10) | Operators can see distribution |
| Question number as 1/2 dropdown | Free-text input | Phase 23 (PJOB-06) | Supports arbitrary Q numbers |

**No deprecated patterns introduced in this phase.**

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ArgumentDetail` Pydantic schema does not currently include `question_number` | "ArgumentPreview Type" section | If it already includes it, no backend change needed for that field — simplifies work |
| A2 | The `saveJobMetadata` action should reuse the existing `/api/admin/arguments/{id}/metadata` PATCH endpoint (Option A) rather than a new job-level endpoint | saveJobMetadata section | If the existing endpoint cannot cleanly accept `question_number` (e.g., due to Pydantic validation), a new endpoint may be cleaner |

---

## Environment Availability

Step 2.6: SKIPPED — this phase is frontend/backend code changes only; no external tooling dependencies beyond the existing project stack (Node.js, Python venv, PostgreSQL already running).

---

## Validation Architecture

Skipped — `workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`.

---

## Security Domain

This phase does not introduce new auth paths, new public-facing endpoints, or new data ingress points. All new endpoints are protected by the existing `verify_admin_token` router-level dependency. The `docket[]` array is operator-supplied string input — each value should be trimmed on the server before writing to the DB, consistent with existing `strip()` / `trim()` patterns in the codebase. No ASVS category is newly in scope.

The `saveJobMetadata` IDOR guard (same as `saveMetadata`): argument_id is derived server-side from the job, not client-supplied — ensures an operator cannot target an unrelated argument's metadata by manipulating form data.

---

## Sources

### Primary (HIGH confidence — verified by direct codebase read this session)
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — current form structure, parse stat card, ingest card, step card patterns
- `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — existing actions, two-step argument_id fetch pattern
- `app/src/routes/admin/arguments/[id]/+page.svelte` — Phase 26 consumer reference, form patterns
- `app/src/routes/admin/arguments/[id]/+page.server.ts` — `save` action pattern
- `app/src/lib/components/AdminSubNav.svelte` — inline CSS + Svelte 5 Runes component pattern
- `api/models/models.py` — `Argument.cover_metadata`, `Argument.question_number`, `ArgumentParticipant.side`
- `api/schemas/admin_jobs.py` — `ParseStats` current shape
- `api/schemas/admin_arguments.py` — `MetadataUpdate`, `ArgumentDetail` schemas
- `api/services/admin_jobs.py` — `get_job` current parse_stats query
- `api/routers/admin.py` — endpoint surface
- `pipeline/parser/cover_extractor.py` — confirmed cover_metadata key inventory (3 keys only)
- `.planning/phases/23-shared-argument-details-component/23-CONTEXT.md` — locked decisions
- `.planning/phases/23-shared-argument-details-component/23-UI-SPEC.md` — visual/interaction contract
- `.planning/REQUIREMENTS.md` — requirement text for PJOB-03 through PJOB-12, AEDIT-03/04

### Secondary (MEDIUM confidence)
- None — all findings based on direct source reads

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; entire stack verified by direct source read
- Architecture: HIGH — confirmed by reading actual service code, schemas, and page components
- Pitfalls: HIGH — identified from direct inspection of existing code patterns that must change
- Backend schema gaps: HIGH — confirmed by reading `cover_extractor.py` (3 keys only) and `api/schemas/admin_jobs.py`

**Research date:** 2026-07-02
**Valid until:** 2026-08-01 (stable codebase; assumptions about existing code are snapshot-valid)
