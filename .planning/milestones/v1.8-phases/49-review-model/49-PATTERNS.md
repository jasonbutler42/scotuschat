# Phase 49: Review Model - Pattern Map

**Mapped:** 2026-08-21
**Files analyzed:** 18 (new/modified)
**Analogs found:** 18 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/0028_review_state_and_discrepancy.py` (NEW) | migration | batch/DDL | `alembic/versions/0026_import_run_provenance.py` (enum creation), `0022_person_name_authority.py` (column-swap-with-carry), `0027_trust_tier_and_candidate_status.py` | exact |
| `api/domain/authority.py` (NEW) | utility (pure domain contract) | transform | `api/domain/trust.py` (`derive_tier`/`floor_tier`) | exact (same module family: `person_names.py`, `docket_values.py`, `trust.py`) |
| `api/models/models.py` (CHG — `ReviewState` enum, `Person` col swap, `ArgumentParticipant` new cols, `ValueDiscrepancy` model) | model | CRUD | `Argument.trust_tier` column decl (`models.py:322-330`), `ArgumentParticipant` (`models.py:392`) | exact |
| `api/services/trust.py` (CHG — `_load_constituents` participant branch, D-17/D-18) | service | CRUD/transform | itself (`_load_constituents` utterance branch, lines 92-102) | exact — same function, sibling branch |
| `api/services/admin_review.py` (NEW) | service | CRUD/request-response | `api/services/admin_arguments.py::publish_argument` (transaction shape), `list_arguments`/`get_argument_stats` (query/filter shape) | role-match |
| `api/services/admin_people.py` (CHG — `update_person`'s D-11 review_state write, `missing_filters` re-point) | service | CRUD | itself (existing `update_person`, `missing_filters` dict) | exact |
| `api/services/admin_arguments.py` (CHG — `update_participant_side` becomes/delegates to the D-31 writer) | service | CRUD | itself (`update_participant_side`, `publish_argument`) | exact |
| `api/services/admin_jobs.py` (CHG — `update_resolve_row_for_job`'s CANDIDATE-only guard widened) | service | CRUD | itself (`update_resolve_row_for_job`) | exact |
| `api/schemas/admin_review.py` (NEW) | schema | request-response | `api/schemas/admin_arguments.py::ParticipantSideUpdate`, `api/schemas/admin_jobs.py::ResolveRowUpdate` | role-match |
| `api/schemas/admin_people.py` (CHG — `review_state`/`provenance_metadata` replace legacy fields) | schema | request-response | itself | exact |
| `api/schemas/admin_arguments.py` (CHG — participant schemas gain `review_state`/`source`/`method`) | schema | request-response | itself (`ParticipantSideUpdate`) | exact |
| `api/routers/admin.py` or `api/routers/admin_review.py` (NEW endpoints) | router | request-response | `api/routers/admin.py` participant/resolve-row routes (`:1423`, `:581`) | role-match |
| `api/tests/test_review_state_schema.py` (NEW) | test | batch (schema assertion) | none directly, but structural style from `test_trust_public_leak_ban.py` | role-match |
| `api/tests/test_authority_matrix.py` (NEW) | test | batch (matrix) | `api/tests/test_trust_public_leak_ban.py` (structural/parametrized style) | role-match |
| `api/tests/test_admin_review_service.py` (NEW) | test | integration | existing `admin_arguments`/`admin_people` service test files (not read this session; same DB-gated pytest idiom per RESEARCH.md) | role-match |
| `api/tests/test_legacy_review_mechanism_removed.py` (NEW) | test | structural (AST/grep) | `api/tests/test_trust_public_leak_ban.py` (AST-scan style) | exact |
| `api/tests/test_trust_public_leak_ban.py` (EXTEND — `BANNED_KEYS`) | test | structural | itself | exact |
| `app/src/routes/admin/review/+page.server.ts` (NEW) | route (SSR load) | request-response | `app/src/routes/admin/arguments/+page.server.ts` | exact |
| `app/src/routes/admin/review/+page.svelte` (NEW) | component | request-response | `app/src/routes/admin/arguments/+page.svelte` (badges, filters, expand row) + `app/src/routes/admin/people/+page.svelte` (tabs) | exact (composite of two analogs) |
| `app/src/lib/components/AdminSubNav.svelte` (CHG — add "Review" link) | component | static | itself | exact |
| `app/src/routes/admin/+page.svelte` (CHG — 5th StatCard, grid fix) | component | static/request-response | itself (existing 4-card grid + `StatCard.svelte`) | exact |

## Pattern Assignments

### `alembic/versions/0028_review_state_and_discrepancy.py` (migration)

**Analogs:** `0026_import_run_provenance.py` (enum + pg_type guard), `0022_person_name_authority.py` (column-swap-with-carry), `0027_trust_tier_and_candidate_status.py` (docstring/downgrade structure)

**pg_type existence-guard enum creation** (pattern, verified `0026` docstring + CONTEXT.md's own worked example):
```python
conn = op.get_bind()
for type_name, ddl in [
    ("review_state", "CREATE TYPE review_state AS ENUM "
     "('unreviewed', 'needs_review', 'operator_confirmed', 'operator_edited')"),
]:
    exists = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :n"), {"n": type_name}
    ).fetchone()
    if not exists:
        conn.execute(sa.text(ddl))

review_state_enum = postgresql.ENUM(
    "unreviewed", "needs_review", "operator_confirmed", "operator_edited",
    name="review_state",
    create_type=False,
)
```

**Column-swap-with-carry** (D-08, mirrors `0022_person_name_authority.py:66-77`'s add-then-backfill-then-drop shape; single set-based UPDATE, not per-row loop, since it's a straight boolean→enum flip):
```python
op.add_column("people", sa.Column("review_state", review_state_enum, nullable=False, server_default="unreviewed"))
op.add_column("people", sa.Column("provenance_metadata", postgresql.JSONB(), nullable=True))

bind = op.get_bind()
bind.execute(sa.text(
    "UPDATE people SET review_state = 'needs_review' WHERE name_needs_review = true"
))
bind.execute(sa.text(
    "UPDATE people SET provenance_metadata = name_extraction_metadata "
    "WHERE name_extraction_metadata IS NOT NULL"
))

op.drop_column("people", "name_extraction_metadata")
op.drop_column("people", "name_needs_review")
```

**Docstring structure to copy** (five-numbered-step form, verified `0026`'s own docstring, lines 1-40): state revision id/revises/create date, then a numbered "In order:" list of DDL steps, then a note on `downgrade()`'s one-way character — model this migration's docstring on that shape, explicitly stating D-09's enum irreversibility and D-08's one-way column drop.

**`ArgumentParticipant` new columns** (D-10/D-19 — `review_state`, `source`, `method`) and **new `value_discrepancy` table** (D-13) ship in the same migration file, same idiom.

---

### `api/domain/authority.py` (NEW pure domain module)

**Analog:** `api/domain/trust.py` (full file read)

**Module docstring pattern to copy verbatim in structure** (`api/domain/trust.py:1-15`):
```python
"""
Pure, dependency-light domain contract for <X> (Phase 49).

This module has NO FastAPI/SQLAlchemy/Alembic imports. It must remain
importable by API services, pipeline commands, tests, and Alembic
migrations without initializing the app or a database connection —
mirroring api/domain/trust.py's / person_names.py's structural conventions
exactly.
"""
```

**`derive_tier`'s shape to structurally mirror** — plain strings in, ordered first-match-wins rules, one enum-like value out (verified in full):
```python
def derive_tier(source: str, method: str, review_state: str) -> TrustTier:
    if review_state in ("operator_confirmed", "operator_edited"):
        return TrustTier.VERIFIED
    if review_state == "needs_review":
        return TrustTier.UNCERTAIN
    if source == "operator" and method == "manual":
        return TrustTier.VERIFIED
    if (source, method) in (("corpus", "direct"), ("seed", "direct")):
        return TrustTier.TRUSTED
    if method == "normalized":
        return TrustTier.PROVISIONAL
    if (source, method) == ("pdf_pipeline", "rule_based"):
        return TrustTier.PROVISIONAL
    return TrustTier.UNCERTAIN
```
The new authority-ladder function (per RESEARCH.md Pattern 3 / Open Question 2) should follow this exact shape: total-ordering, first-match-wins, fail-closed default branch, plain string/enum inputs only — but its OUTPUT per D-16 should likely be a two-value tuple (`accepted: bool, should_record_discrepancy: bool`) rather than a single TrustTier, since D-16 requires recording a discrepancy even on outright rejection. Do not copy `derive_tier`'s single-return-value shape blindly — extend it deliberately for the two-outcome need.

**Do NOT put this logic in `api/services/admin_review.py`** — the pure/impure split (`trust.py` vs. `services/trust.py`) is the load-bearing precedent: the ladder decision is pure business logic (testable without a DB), while `admin_review.py` is where the DB read/write happens.

---

### `api/models/models.py` (CHG)

**Analog:** `Argument.trust_tier` column declaration (verified, `api/models/models.py:322-330`, referenced via research) and existing `SAEnum(..., values_callable=...)` idiom used project-wide.

**`review_state` column pattern** (both `Person` and `ArgumentParticipant`):
```python
review_state = Column(
    SAEnum(ReviewState, name="review_state", values_callable=lambda e: [x.value for x in e]),
    nullable=False,
    server_default="unreviewed",
    default=ReviewState.UNREVIEWED,
)
```

**Legacy columns to remove** (D-08): `Person.name_needs_review` (Boolean) and `Person.name_extraction_metadata` (JSONB), confirmed present at `api/models/models.py:149-150`. Replace with `review_state` + `provenance_metadata` — no compatibility shim/property.

**`ArgumentParticipant` gains** `review_state`, `source`, `method` — confirmed absent today at `api/models/models.py:392`. `source`/`method` reuse the existing `ImportSource`/`ImportMethod` PG enum types verbatim (D-20 — no new enum for these two columns; only `review_state` is a new enum).

**New `ValueDiscrepancy` model** — a plain SQLAlchemy model with FK-ish `(target_type, target_id, field, import_run_id)` natural key, `incoming_value`, `existing_value`, `incoming_source`, `incoming_method`, `created_at`, `resolved_at` (nullable). No existing exact analog table; follow the general model-declaration conventions already used for `ArgumentStatusLog` (timestamped, immutable-except-one-field audit row).

---

### `api/services/trust.py` (CHG — `_load_constituents`)

**Analog:** itself — the existing utterance branch (lines 92-102) is the exact template the participant branch must mirror.

**Existing utterance branch (verified, `.value` extraction is the critical detail — Pitfall 1):**
```python
for person_id, is_stage_direction, source, method in utterance_rows:
    if is_stage_direction:
        continue
    if person_id is None:
        tiers.append(TrustTier.UNCERTAIN)
        _bump("unresolved_utterance_speaker")
        continue
    tier = derive_tier(source.value, method.value, UNREVIEWED)
    tiers.append(tier)
    if tier is TrustTier.UNCERTAIN:
        _bump("llm_corrective_utterance")
```

**Existing participant branch to REPLACE (verified, lines 104-109):**
```python
for (person_id,) in participant_rows:
    if person_id is None:
        tiers.append(TrustTier.UNCERTAIN)
        _bump("unresolved_participant")
    # A resolved participant contributes no additional tier — D-13, no
    # per-participant source/method exists yet to derive one from.
```

**New participant branch (D-17/D-18 — illustrative, per RESEARCH.md Code Examples):**
```python
for person_id, review_state, source, method in participant_rows:  # SELECT gains 3 columns
    if person_id is None:
        if review_state == "operator_confirmed":  # D-17: confirm-as-unattributable
            tiers.append(TrustTier.VERIFIED)
        else:
            tiers.append(TrustTier.UNCERTAIN)
            _bump("unresolved_participant")
    else:
        tier = derive_tier(source, method, review_state)  # D-18 — call .value if these are enum columns
        tiers.append(tier)
        if tier is TrustTier.UNCERTAIN:
            _bump("<new_blocker_code>")
```
**Critical pitfall (verified in RESEARCH.md, HIGH confidence):** always pass `.value` for enum-typed SQLAlchemy columns into `derive_tier`, never the enum member itself — `derive_tier`'s checks are plain string equality and will silently fail to match otherwise. The `SELECT` for `participant_rows` must also widen to select `review_state`, `source`, `method` columns, not just `person_id`.

`recompute_argument_tier` itself (lines ~117-135) is UNCHANGED — it already calls `_load_constituents` and stores `floor_tier(tiers)`; only the constituent-loading branch changes.

---

### `api/services/admin_review.py` (NEW service)

**Analog 1 — transaction discipline:** `api/services/admin_arguments.py::publish_argument` (verified in full, lines ~602-660)

**Exact shape to copy** for the resolve-a-row action (confirm / edit / confirm-as-unattributable):
```python
# 1. load the row + any open value_discrepancy rows for it (scoped SELECT)
# 2. apply the operator's action (confirm / edit / confirm-as-unattributable)
# 3. UPDATE resolved_at on every open discrepancy for that row (D-15)
#    .execution_options(synchronize_session=False)
# 4. await recompute_argument_tier(db, argument_id)  # D-17/D-18
# 5. caller commits — the function itself never calls db.commit()
```
Concretely, follow `publish_argument`'s literal structure: `select()` the target row first (return `None` if not found → router 404), do guard checks BEFORE any write, do the `update()`/`db.add()` write(s), then `recompute_argument_tier`, and let the CALLER (router) issue `await db.commit()` — do not call `db.commit()` inside this service function (critical anti-pattern per RESEARCH.md).

**Analog 2 — bulk update discipline** (verified, `publish_argument` and `update_participant_side` both use this):
```python
await db.execute(
    update(Argument)
    .where(Argument.id == argument_id)
    .values(status=ArgumentStatusEnum.PUBLISHED, published_at=sqlfunc.now())
    .execution_options(synchronize_session=False)
)
```
Every bulk `update()` in the new service must include `.execution_options(synchronize_session=False)`, with a `db.refresh()` afterward if the same session re-reads the row (see `publish_argument`'s own `await db.refresh(argument)` comment explaining exactly why).

**Analog 3 — queue query/filter/sort shape:** `api/services/admin_arguments.py::list_arguments`/`get_argument_stats` (lines 67-177, not fully re-read this session but referenced/verified by RESEARCH.md and CONTEXT.md D-28) — server-side sort-in-the-query convention (D-03's worst-tier-first, then oldest `argued_date`), unbounded list (D-04), filter params as plain SQL `WHERE` clauses composed from optional query params — same idiom as `admin_people.py`'s `missing_filters` dict pattern below.

**Analog 4 — filter-dict idiom:** `api/services/admin_people.py`'s `missing_filters` dict (verified, lines 233-244):
```python
missing_filters = {
    "first name": Person.first_name.is_(None),
    ...
    "name review": Person.name_needs_review.is_(True),  # D-08 must re-point this to review_state
}
if missing in missing_filters:
    q = q.where(missing_filters[missing])
```
The queue's tier × review_state × status filter composition should follow this same "named predicate dict, apply if key present" idiom rather than inventing a new filter-builder abstraction.

---

### `api/services/admin_people.py` (CHG)

**Analog:** itself — `update_person` (verified, lines ~520-560) and the `missing_filters` dict (lines 233-244)

**Line to replace (D-11)** — verified at `api/services/admin_people.py:545` (in context, ~line 549 of the excerpt above):
```python
person.name_needs_review = False
```
Per D-11, this becomes: a name edit sets `review_state = ReviewState.OPERATOR_EDITED` (never a boolean False); a NEW distinct Confirm action (not this code path) sets `review_state = ReviewState.OPERATOR_CONFIRMED`. The docstring immediately above this line (verified, "never touches name_extraction_metadata... independent, durable audit trail") states the D-12 never-rewrite-metadata rule verbatim — carry that comment forward unchanged, renaming only the field it refers to (`provenance_metadata`).

**`missing_filters["name review"]` re-point (D-08):**
```python
"name review": Person.name_needs_review.is_(True),
```
becomes:
```python
"name review": Person.review_state == ReviewState.NEEDS_REVIEW,
```

---

### `api/services/admin_arguments.py` / `admin_jobs.py` (CHG — the two participant writers, D-31)

**Analog:** both are their own analogs (both fully read, verified).

**`update_participant_side`** (`admin_arguments.py:715-754`, verified in full) — IDOR guard pattern to preserve exactly:
```python
result = await db.execute(
    select(ArgumentParticipant).where(
        ArgumentParticipant.id == participant_id,
        ArgumentParticipant.argument_id == argument_id,  # BOTH scoped — IDOR guard
    )
)
```
No status guard exists on this path today (Pitfall 2's warning — do not assume fixing one writer fixes both).

**`update_resolve_row_for_job`** (`admin_jobs.py:783-843`, verified in full) — the exact guard the folded "widen editability" todo must change:
```python
if argument.status != ArgumentStatusEnum.CANDIDATE:
    raise ValueError(
        f"Argument {argument.id} is no longer in 'candidate' state "
        f"(current status: {argument.status.value!r}); resolve rows are "
        "read-only once the argument has been created (D-18, D-19)."
    )
```
Widen to `argument.status in (ArgumentStatusEnum.CANDIDATE, ArgumentStatusEnum.DRAFT, ArgumentStatusEnum.UNPUBLISHED)` per the folded todo — PUBLISHED excluded. Update the docstring's "D-18, D-19" reference to point at Phase 49's decision instead (per RESEARCH.md's State of the Art table).

Both writers must, per D-31, stamp `review_state`/close discrepancies/call `recompute_argument_tier` — either by both calling a shared new helper in `admin_review.py`, or by one becoming the canonical writer. **This choice is an explicit open question (RESEARCH.md Open Question 1) — the plan must resolve it, not assume it.**

---

### `api/schemas/admin_review.py` (NEW) / `admin_arguments.py` / `admin_jobs.py` schemas (CHG)

**Analog:** `api/schemas/admin_arguments.py::ParticipantSideUpdate` (verified in full, lines 44-55) and `api/schemas/admin_jobs.py::ResolveRowUpdate` (verified, lines 195+)

**Mass-assignment guard pattern to copy exactly:**
```python
class ParticipantSideUpdate(BaseModel):
    """PATCH body for argument_participants.side and descriptor (...).

    Mass-assignment guard: ONLY ``side`` and ``descriptor`` are writable
    via this schema. No other ArgumentParticipant column can be set.
    """
    side: SideEnum
    descriptor: Optional[str] = None
```
Any new resolve-action request body (confirm / edit / confirm-as-unattributable / re-flag) must use this exact allow-list-only pattern — explicit field list, explicit docstring stating what is NOT writable, no `**kwargs`/dict passthrough.

**`ResolveRowUpdate`'s IDOR-safety-by-omission note** (verified) — worth copying verbatim in spirit: "this schema does not accept `argument_id`" — the new schemas for review actions must likewise omit any parent-scoping ID from the request body; scoping is enforced server-side from the URL path, never trusted from the body.

---

### `api/tests/test_review_state_schema.py`, `test_authority_matrix.py`, `test_legacy_review_mechanism_removed.py` (NEW)

**Analog:** `api/tests/test_trust_public_leak_ban.py` (read in full)

**Structural/AST-scan pattern** (verified — module docstring + `BANNED_KEY` constant + `_unwrap_annotation_types` helper):
```python
"""
Pure module: no DB, no fixtures, no skip markers — modeled on
api/tests/test_phase45_popover_boxmodel_contract.py's static-contract
shape. The model set under test is DERIVED from the `response_model=`
of every route registered on the public routers, so a newly added
public route that is not covered fails this module rather than
passing silently.
"""
BANNED_KEY = "trust_tier"
```
`test_legacy_review_mechanism_removed.py` should follow this exact "pure module, no DB, structural/AST-derived assertion set" shape — grep/AST-scan the repo for `name_needs_review`/`name_extraction_metadata` outside migration files and `downgrade()` bodies, fail if found.

`test_authority_matrix.py` is a DB-gated integration test (per RESEARCH.md's Validation Architecture table) — it does NOT follow this pure-module pattern; it follows the ordinary pytest-against-`TEST_DATABASE_URL` idiom used throughout `api/tests/` (not itself re-read this session, but confirmed by RESEARCH.md as the established DB-gated test style, isolated via the repo-root `conftest.py`).

---

### `api/tests/test_trust_public_leak_ban.py` (EXTEND)

**Minimal-diff extension** (verified, current single-key form):
```python
BANNED_KEY = "trust_tier"
```
becomes:
```python
BANNED_KEYS = ("trust_tier", "review_state", "source", "method")
# ... in the test body:
for banned_key in BANNED_KEYS:
    assert banned_key not in reachable_model.model_fields, (...)
```
Also extend `PUBLIC_SCHEMA_MODULE_PATHS` / the AST-scanned module list if a new admin discrepancy schema needs covering as a "must never be reachable from a public model" check.

---

### `app/src/routes/admin/review/+page.server.ts` (NEW)

**Analog:** `app/src/routes/admin/arguments/+page.server.ts` (read in full)

**Full SSR-load pattern to copy exactly** (verified, entire file):
```typescript
import { ADMIN_TOKEN, FASTAPI_BASE_URL } from '$env/static/private';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, url }) => {
	const status = url.searchParams.get('status');
	// ... same pattern for tier / review_state / tab query params

	const params = new URLSearchParams();
	if (status) params.set('status', status);
	const queryString = params.toString();
	const apiUrl = `${FASTAPI_BASE_URL}/api/admin/review${queryString ? '?' + queryString : ''}`;

	let items = [];
	try {
		const res = await fetch(apiUrl, {
			headers: { 'X-Admin-Token': ADMIN_TOKEN },
		});
		if (res.ok) {
			items = await res.json();
		} else {
			console.error('[review load] FastAPI returned', res.status);
		}
	} catch (err) {
		console.error('[review load] fetch threw:', err instanceof Error ? err.message : String(err));
	}

	return { items, status, tier, reviewState, tab };
};
```
Note the established error-handling contract (per UI-SPEC's Copywriting Contract "Error state" row): a failed fetch is logged server-side only (`console.error`) and the page renders with an empty list — NOT a new error banner. `FASTAPI_BASE_URL`/`ADMIN_TOKEN` come from `$env/static/private` — never `PUBLIC_`, per CLAUDE.md architecture rule 2.

---

### `app/src/routes/admin/review/+page.svelte` (NEW)

**Analog 1 — badges, filters, expand-row technique:** `app/src/routes/admin/arguments/+page.svelte` (targeted reads, lines 105-135 badge helpers, 170-260 filter/header)

**Tier badge helper to reuse verbatim** (`tierBadgeStyle`/`tierLabel`, verified in full):
```typescript
function tierBadgeStyle(tier: string): string {
	let color: string;
	if (tier === 'verified') color = '#38bdf8';
	else if (tier === 'trusted') color = '#34d399';
	else if (tier === 'provisional') color = '#facc15';
	else if (tier === 'uncertain') color = '#f87171';
	else color = '#64748b';
	return `border: 1px solid ${color}; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 400; background-color: #0f1117; color: ${color}; display: inline-block;`;
}
```
The new `review_state` badge helper (four new colors per UI-SPEC) and the discrepancy-indicator badge follow this exact formula — only the color lookup table changes:
```
border: 1px solid {color}; border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: 400; background-color: #0f1117; color: {color}; display: inline-block;
```

**Status badge helper** (14px variant, verified — `badgeStyle`/`badgeLabel`, distinct from the 12px tier badge above): reused unchanged for the queue's status badge on Arguments-tab rows.

**Expand/collapse "full-width row beneath the triggering row" technique** — UI-SPEC explicitly names `admin/arguments/+page.svelte:492-618`'s publish-blocked panel as the analog to copy (not independently re-read this session, but named as the exact technique in both CONTEXT.md and UI-SPEC — a conditionally-rendered full-width `<tr>` immediately following the trigger row, NOT a native `<details>` element since `<details>` cannot legally wrap a `<tr>`).

**Analog 2 — tab pattern:** `app/src/routes/admin/people/+page.svelte` (verified, lines 6-104)
```typescript
function switchTab(tab: 'bench' | 'advocate') {
	goto('/admin/people?tab=' + tab);
}
```
The Arguments|People tab switcher on `/admin/review` follows this exact one-param `goto()` round-trip idiom — verified tab-button styling pattern (active/inactive border+background+color triple, `aria-pressed`) at lines 68-104:
```svelte
<button
	aria-pressed={data.tab === 'bench'}
	aria-label="Bench tab"
	style="
		border: 1px solid {data.tab === 'bench' ? '#93c5fd' : '#334155'};
		background-color: {data.tab === 'bench' ? '#93c5fd' : '#1e293b'};
		color: {data.tab === 'bench' ? '#0f1117' : '#e2e8f0'};
	"
>Bench</button>
```

**All filter/tab changes use full-page `goto()`, never client-side state** — matches every existing admin filter idiom (status segments, Bench/Advocate tabs, missing-field pills) per both files' verified `switchTab`/`selectStatus`-style handlers.

---

### `app/src/lib/components/AdminSubNav.svelte` (CHG)

**Analog:** itself (read in full)

**Existing link markup to copy for the new "Review" link** (verified, exact structure):
```svelte
<a href="/admin/review" style="font-size: 14px; font-weight: 400; color: #94a3b8; text-decoration: none;">
	Review
</a>
```
Insert between the existing "Arguments" and "People Editor" `<a>` tags (verified current order: Pipeline Runner, Arguments, People Editor, then the logout form) — per D-27/UI-SPEC's specified position.

---

### `app/src/routes/admin/+page.svelte` (CHG — 5th StatCard + grid fix)

**Analog:** itself (verified, grid + StatCard usage)

**Critical fix required (Pitfall 3, HIGH confidence, directly contradicts UI-SPEC's own "absorbs without change" claim):**
```css
/* line 240, verified this session: */
grid-template-columns: repeat(4, 1fr);
```
This is a literal 4-column grid, NOT `auto-fit`/`auto-fill`. Adding a 5th `<StatCard>` (verified pattern below) requires explicitly changing this to `repeat(5, 1fr)` (or an auto-fit formula) — do not trust the UI-SPEC's "StatCard's existing grid layout (32px gap) absorbs the fifth card without change" claim; it is contradicted by direct inspection.

**StatCard usage pattern to copy** (verified, existing four cards, e.g. lines 245-271):
```svelte
<StatCard title="Review queue">
	<!-- large count via formatCount (N/A-on-failure), then one accent link -->
</StatCard>
```
`StatCard.svelte` itself (read in full) is a fixed, non-conditional container — "each card's differently-shaped breakdown body is composed by the caller via the `children` snippet" (verified docstring) — do not modify `StatCard.svelte` itself; only add a new `<StatCard>` usage in the dashboard page.

## Shared Patterns

### One-writer transaction discipline (D-15/D-18/D-31)
**Source:** `api/services/admin_arguments.py::publish_argument` (lines ~602-660, verified in full)
**Apply to:** `api/services/admin_review.py`'s resolve-action function, and any changes to `update_participant_side`/`update_resolve_row_for_job`/`admin_people.py::update_person`.
```
1. select() the target row(s), scoped by every relevant parent id (IDOR guard)
2. guard checks BEFORE any write (return None / raise ValueError as appropriate)
3. the write(s): bulk update() with .execution_options(synchronize_session=False)
   + any db.add() log/audit rows, all before commit
4. recompute_argument_tier(db, argument_id) in the SAME transaction
5. the function itself never calls db.commit() — the caller (router) does
6. db.refresh() the in-session object afterward if the same session re-reads it
```

### IDOR guard — scoped SELECT before write
**Source:** `api/services/admin_arguments.py::update_participant_side` (lines 725-727, verified)
**Apply to:** every new writer touching `ArgumentParticipant`/`Person`/`ValueDiscrepancy` rows.
```python
result = await db.execute(
    select(ArgumentParticipant).where(
        ArgumentParticipant.id == participant_id,
        ArgumentParticipant.argument_id == argument_id,
    )
)
```

### Mass-assignment guard schemas
**Source:** `api/schemas/admin_arguments.py::ParticipantSideUpdate` (lines 44-55), `api/schemas/admin_jobs.py::ResolveRowUpdate`
**Apply to:** every new PATCH body in `api/schemas/admin_review.py`.
Explicit field allow-list only, docstring stating what is NOT writable, no parent-scoping id accepted in the body (server derives scope from the URL path).

### PG enum via `values_callable`, pg_type existence guard
**Source:** `alembic/versions/0026_import_run_provenance.py`, model-side pattern at `api/models/models.py` (trust_tier column)
**Apply to:** the new `review_state` enum, both migration and model declaration.

### Public-leak-ban structural test extension
**Source:** `api/tests/test_trust_public_leak_ban.py` (read in full)
**Apply to:** D-34 — extend `BANNED_KEY` to `BANNED_KEYS = ("trust_tier", "review_state", "source", "method")`.

### Admin filter round-trip via full-page `goto()`
**Source:** `app/src/routes/admin/arguments/+page.svelte`, `app/src/routes/admin/people/+page.svelte`
**Apply to:** every filter/tab control on `/admin/review` — no client-side filter state, URL query params only, back-button-safe.

### `.execution_options(synchronize_session=False)` + `db.refresh()`
**Source:** `api/services/admin_arguments.py:602-660` (`publish_argument`'s own comment explains the refresh necessity in detail)
**Apply to:** every bulk `update()` in the new writers.

## No Analog Found

None — every file in scope has at least a role-match analog in the existing codebase. This phase is explicitly a same-codebase generalization per RESEARCH.md ("no new external technology... extends four already-shipped, already-documented patterns").

## Open Items Planner Must Resolve (not settled by pattern-mapping)

- **Which writer becomes D-31's "one real authority-checked writer"** — `update_participant_side` vs. `update_resolve_row_for_job` vs. a new wrapper calling both. RESEARCH.md Open Question 1. Pattern-mapping surfaces both candidates' exact guard differences (Pitfall 2) but does not resolve which wins.
- **Authority-ladder function's exact return shape** (`api/domain/authority.py`) — likely a two-value tuple per D-16, not a single value like `derive_tier`. RESEARCH.md Open Question 2.
- **Unresolved-speaker fixture mechanism** (D-33) — no existing `FIXTURE_SET` entry produces a NULL-`person_id` `ArgumentParticipant` (Pitfall 4). No analog exists for this because the capability doesn't exist in the codebase yet; the plan must design this as new dev-tooling, likely adjacent to `api/services/admin_dev.py::reset_to_fixture`.

## Metadata

**Analog search scope:** `api/domain/`, `api/models/`, `api/services/`, `api/schemas/`, `api/routers/`, `api/tests/`, `alembic/versions/`, `app/src/routes/admin/`, `app/src/lib/components/`
**Files read directly this session:** `api/domain/trust.py` (partial, docstring+rules), `alembic/versions/0026_import_run_provenance.py` (docstring), `api/services/admin_arguments.py` (publish_argument, update_participant_side — full), `api/services/admin_jobs.py` (update_resolve_row_for_job — full), `api/schemas/admin_arguments.py` / `admin_jobs.py` (targeted), `api/services/trust.py` (`_load_constituents`/`recompute_argument_tier` — full), `api/services/admin_people.py` (`missing_filters`, `update_person` — targeted), `api/tests/test_trust_public_leak_ban.py` (header — targeted), `app/src/routes/admin/arguments/+page.svelte` (badge helpers — targeted), `app/src/routes/admin/+page.svelte` (grid line confirmed), `app/src/lib/components/StatCard.svelte` (full), `app/src/lib/components/AdminSubNav.svelte` (full), `app/src/routes/admin/arguments/+page.server.ts` (full), `app/src/routes/admin/people/+page.svelte` (tab logic — targeted)
**Pattern extraction date:** 2026-08-21
