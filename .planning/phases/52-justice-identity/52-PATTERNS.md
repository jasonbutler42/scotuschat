# Phase 52: Justice Identity - Pattern Map

**Mapped:** 2026-09-24
**Files analyzed:** 15 (creates + modifies), plus 3 "no-change reference" files
**Analogs found:** 15 / 15 (all classes have at least a role-match; one gap explicitly flagged — partial-unique-index has no in-repo precedent, per RESEARCH.md's own finding)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/003X_person_display_name_and_oyez_unique.py` (NEW) | migration | batch/DDL | `alembic/versions/0031_argument_slug.py` | role-match (nullable-column + unique-constraint shape identical; the `postgresql_where` partial predicate itself has **no analog** — see below) |
| `data/corpus/justice_identity_mapping.csv` (NEW) | config/data | batch (read-once at import) | `data/corpus/supreme_court_justices_sections.csv` (untracked, gitignored data file) via its reader `pipeline/commands/import_justices_csv.py` | role-match |
| `pipeline/commands/import_justices_csv.py` (modify, ~lines 272-275 dedup key, ~277-410 write path) | pipeline/service | CRUD (upsert) | itself — the file's own existing upgrade/create branches (lines 277-410) are the pattern to extend, not replace | exact (self-analog) |
| `pipeline/commands/import_convokit.py::_resolve_person` (reference only, ~1733-1782, **no change**) | service | CRUD (read-then-upsert) | — (this IS the reference implementation `import_justices_csv.py` must converge toward) | exact — reference implementation |
| `api/services/admin_dev.py::reset_to_fixture` (modify, insertion after TRUNCATE ~line 228-235) | service | batch/event-driven (destructive reset + reseed) | itself — the existing `FIXTURE_SET` loop immediately below the insertion point | exact (self-analog) |
| `api/models/models.py::Person` (modify, add `display_name` column) | model | CRUD | `Person.oyez_speaker_id` / `Person.full_name` columns in the same class (lines 138, 152) | exact (self-analog) |
| `api/schemas/admin_people.py::PersonDetail` (modify, +2 read-only fields) | model/DTO | request-response | `PersonDetail.full_name` (read-only, server-derived) at lines 166-178 | exact |
| `api/schemas/speakers.py::SpeakerPopoverEntry` (modify, +`initials` field) | model/DTO | request-response | its own `full_name`/`birthdate` fields (lines 60-71) | exact (self-analog) |
| `api/schemas/utterance.py::UtteranceResponse` (modify, +`initials` field) | model/DTO | request-response | its own `speaker_name`/`speaker_role` fields (lines 34-35) | exact (self-analog) |
| `api/domain/person_names.py` (modify or new function, initials derivation) | utility | transform | `split_legacy_full_name` + `_KNOWN_SUFFIXES` (lines 234, 269-300) in the same module | exact |
| `api/services/arguments.py` (modify, line 242 COALESCE) | service | CRUD (read/query) | itself — the same `select()` call being edited | exact (self-analog) |
| `app/src/lib/public/SpeakerPopover.svelte` (modify, ~line 57) | component | transform (render) | `+page.svelte`'s `getInitials` (byte-identical logic, ~line 181) | exact — the two files are analogs of each other |
| `app/src/routes/arguments/[slug]/+page.svelte` (modify, ~line 181, `getInitials`) | component | transform (render) | `SpeakerPopover.svelte:57` (byte-identical logic) | exact |
| `app/src/routes/admin/people/[id]/+page.svelte` (modify, +2 read-only fields) | component | request-response (render server-loaded data) | the existing Full Name `<output>` block (~lines 375-390) | exact |
| `app/src/routes/admin/people/[id]/+page.server.ts` (modify, `PersonDetail` interface) | route/provider | request-response | its own `PersonDetail` interface (lines 22-65) | exact (self-analog) |
| `app/src/routes/admin/+page.server.ts` (modify, D-14/D-15 copy + re-read) | route/provider | request-response | its own `resetToFixture` action + `RESET_MID_ERROR`/`RESET_ENV_ERROR` literals (lines 210-270) | exact (self-analog); **no existing analog for the "re-read fixture state" GET** — RESEARCH.md Pitfall 4/Open Question 1 flags this as new machinery |
| `pipeline/tests/test_import_justices_csv.py` (modify, ~15 fixture functions) | test | CRUD (fixture setup) | its own `test_upgrades_existing_person_in_place` (line 204) and sibling `Person(...)` fixtures (lines 546, 616, 686, 820, 1025, 1078, 1124, 1182) | exact (self-analog); all need `oyez_speaker_id=` added to the fixture `Person(...)` construction |
| `pipeline/tests/test_justice_identity_mapping.py` (NEW, D-02 structural test) | test | transform (structural check) | none in-repo — a new test category (verifying a data artifact's internal consistency, not application behavior) | no direct analog; nearest kin is any pipeline test reading a CSV fixture, but none checks cross-file structural agreement today |

## Pattern Assignments

### `alembic/versions/003X_person_display_name_and_oyez_unique.py` (migration, batch/DDL)

**Analog:** `alembic/versions/0031_argument_slug.py` (git-tracked: confirmed via `git ls-files`)

**Full analog file is short (61 lines) — reproduced pattern in full**, since this is the template to copy structurally:

```python
"""<Docstring must explain WHY nullable, WHY reseed-not-migrate, per this project's
CLAUDE.md constraint — 0031's docstring is the model for this.>"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "003X"
down_revision: str = "0031"  # or whatever HEAD is at execution time — verify
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "people",
        sa.Column("display_name", sa.String(300), nullable=True),
    )
    # NOTE: 0031 used op.create_unique_constraint for a PLAIN unique index.
    # This migration instead needs a PARTIAL unique index — no in-repo
    # precedent exists for postgresql_where (RESEARCH.md: "grep across all
    # 32 migrations found zero postgresql_where usages"). This block is
    # NOT copied from any tracked source in this repo; it is assembled from
    # SQLAlchemy/Alembic's documented `postgresql_where` API, cross-checked
    # via web search per RESEARCH.md's own citation:
    op.create_index(
        "uq_people_oyez_speaker_id",
        "people",
        ["oyez_speaker_id"],
        unique=True,
        postgresql_where=sa.text("oyez_speaker_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_people_oyez_speaker_id", table_name="people")
    op.drop_column("people", "display_name")
```

**Nullable-column-add pattern** (verbatim shape to copy, `0031` lines 47-51):
```python
op.add_column(
    "arguments",
    sa.Column("slug", sa.String(200), nullable=True),
)
```

**Docstring discipline to copy** (`0031` lines 1-33): explain (a) exact column shape, (b) why nullable given "reseed, don't migrate," (c) no UPDATE/backfill statement in the migration, (d) what downgrade does. Do the same here, additionally stating explicitly that the partial predicate has **no prior in-repo example** and citing SQLAlchemy's `postgresql_where` docs as the source, so a future reader doesn't go hunting for a local precedent that doesn't exist.

**Explicit gap:** No migration among the 32 in `alembic/versions/` uses `postgresql_where` or any partial index. The closest *plain* unique-index/constraint analog is `0031_argument_slug.py`'s `op.create_unique_constraint`. The predicate syntax itself must come from SQLAlchemy's documented Postgres dialect API, not from a repo file.

---

### `data/corpus/justice_identity_mapping.csv` (data artifact, batch)

**Analog:** `data/corpus/supreme_court_justices_sections.csv` — **note this analog file itself is untracked by git** (`data/corpus/*.csv` is gitignored per `data/corpus/.gitignore`, confirmed tracked: `git ls-files -- data/corpus/.gitignore` returns non-empty). This is expected, not a mirror-path violation: the `.gitignore` comment (verified) states these are "operator-supplied inputs," deliberately excluded from git because `utterances.jsonl` alone is ~900MB. The new mapping CSV belongs in the same untracked directory, laid out the same way, and is read the same way — by the tracked Python reader below, not by a tracked copy of the CSV itself.

**Reader pattern to copy** (`pipeline/commands/import_justices_csv.py:85`, git-tracked):
```python
# Matches the data/corpus/ scaffolding created in Plan 01 — the
# operator copies the source CSV here locally; it is gitignored, not tracked.
DEFAULT_CSV_PATH = Path("data/corpus/supreme_court_justices_sections.csv")
```
Follow this exact `DEFAULT_..._PATH` module-constant convention for the new mapping file (RESEARCH.md Open Question 2 recommends `DEFAULT_MAPPING_CSV_PATH`).

---

### `pipeline/commands/import_justices_csv.py` (pipeline/service, CRUD)

**Analog:** itself — extend the existing dedup lookup and write branches.

**Current dedup lookup to replace** (verified, lines 272-275):
```python
result = await session.execute(
    select(Person).where(Person.full_name == full_name)
)
person = result.scalar_one_or_none()
```
Must become an `oyez_speaker_id`-keyed lookup sourced from the new mapping CSV (mirroring `_resolve_person`'s reference shape below), not a `full_name` match.

**Authority-ladder write pattern to copy verbatim for any new gated field** (verified, lines 308-319):
```python
if prepared.first_name is not None:
    decision = await apply_person_value_change(
        session,
        person=person,
        field="first_name",
        incoming_value=prepared.first_name,
        incoming_source=ImportSource.SEED.value,
        incoming_method=ImportMethod.DIRECT.value,
        import_run_id=None,
    )
    if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
        setattr(person, "first_name", prepared.first_name)
```
Four near-identical blocks exist for `first_name`/`middle_name`/`last_name`/`name_suffix` (lines 308-352) — same shape, different field/value. RESEARCH.md Pitfall 2 flags that `display_name` may not need this full ladder call (D-09 makes it un-operator-editable everywhere, so there's no adversarial edit to arbitrate against) — a simpler blank-only assignment (mirroring the `birthdate`/`death_date` pattern below) may be the correct, simpler pattern instead. Either way, **do not invent a third write-gating mechanism** — pick between these two already-established shapes.

**Blank-only prefill pattern (simpler alternative for `display_name`)** (verified, lines ~356-361):
```python
if person.birthdate is None and birthdate is not None:
    person.birthdate = birthdate
    people_birthdates_backfilled += 1
```

**CREATE branch to extend** (verified, lines ~396-410):
```python
person = Person(
    full_name=full_name,
    first_name=prepared.first_name,
    middle_name=prepared.middle_name,
    last_name=prepared.last_name,
    name_suffix=prepared.name_suffix,
    is_justice=True,
    birthdate=birthdate,
    death_date=death_date,
    provenance_metadata=extraction_metadata,
    review_state=ReviewState.UNREVIEWED,
    # oyez_speaker_id intentionally left NULL — the corpus
    # importer backfills it later.
)
session.add(person)
```
The trailing comment marks the **exact change site** (RESEARCH.md's own note) — this comment must be removed/rewritten and `oyez_speaker_id=` (and `display_name=`) added as constructor kwargs, sourced from the mapping.

**Module docstring lines 16-18** also assert the now-false claim ("Dedup key: exact `Person.full_name` string match... `Person.oyez_speaker_id` is left NULL here") — update alongside the code, not left stale.

---

### `pipeline/commands/import_convokit.py::_resolve_person` (reference implementation, NO CHANGE)

**Verified, lines 1733-1782** — this is the pattern `import_justices_csv.py`'s new lookup must match, not a file to edit:
```python
result = await session.execute(
    select(Person).where(Person.oyez_speaker_id == speaker_id)
)
person = result.scalar_one_or_none()
if person is not None:
    await _apply_extracted_name_provenance(session, person, person.full_name)
    counters["people_matched"] = counters.get("people_matched", 0) + 1
    return person

result = await session.execute(select(Person).where(Person.full_name == full_name))
person = result.scalar_one_or_none()
if person is not None:
    if person.oyez_speaker_id is None:
        person.oyez_speaker_id = speaker_id  # D-11 backfill
    await _apply_extracted_name_provenance(session, person, person.full_name)
    counters["people_matched"] = counters.get("people_matched", 0) + 1
    return person

person = Person(
    full_name=full_name,
    oyez_speaker_id=speaker_id,
    is_justice=is_justice,
)
```
Key structural point for the plan: `oyez_speaker_id` checked FIRST, `full_name` SECOND (with backfill-on-match), matching D-13's discretion note ("`_resolve_person` needs no change — it already prefers `oyez_speaker_id`; that lookup simply starts hitting" once `import_justices_csv.py` starts writing the id).

---

### `api/services/admin_dev.py::reset_to_fixture` (service, batch/event-driven)

**Analog:** itself — insertion point immediately below the TRUNCATE.

**Exact insertion point** (verified, lines 228-235):
```python
resolved_corpus_dir = Path(corpus_dir) if corpus_dir else DEFAULT_CORPUS_DIR
_require_corpus_files(resolved_corpus_dir)

await db.execute(text(TRUNCATE_SQL))
await db.commit()
# <- D-16: justice seed step goes here, before the FIXTURE_SET reseed loop below

fixture_rows: list[tuple[dict, int]] = []
for entry in FIXTURE_SET:
    ...
    await run_import_convokit(
        SimpleNamespace(
            conversation_id=conversation_id,
            corpus_dir=str(resolved_corpus_dir),
        )
    )
```
**`SimpleNamespace(...)` call convention to copy** for invoking `run_import_justices_csv` the same way `run_import_convokit` is invoked here — e.g. `await run_import_justices_csv(SimpleNamespace(csv=None))` (RESEARCH.md's own recommendation, matching `run_import_justices_csv`'s existing `args.csv` optional-attribute signature at `import_justices_csv.py:204-222`).

**TRUNCATE table list** (verified, lines 142-154) already names `people` and `court_tenures` — no change needed there; the seed step is a post-TRUNCATE INSERT path, matching how `FIXTURE_SET`'s loop already reseeds `arguments`/`cases`/etc.

---

### `api/models/models.py::Person` (model, CRUD)

**Analog:** the class's own existing nullable-String columns (verified, lines 134-173):
```python
class Person(Base):
    __tablename__ = "people"
    ...
    # Oyez/ConvoKit external speaker ID (historical corpus import)
    oyez_speaker_id = Column(String(100), nullable=True)
    ...
```
Add `display_name = Column(String(300), nullable=True)` immediately adjacent to `oyez_speaker_id`, matching `full_name`'s width (`String(300)`, line 138) since `display_name` is "the corpus's own word, exactly as full_name is the name parts' word" (D-09).

---

### `api/schemas/admin_people.py::PersonDetail` (DTO, request-response)

**Analog:** `full_name` on the same schema — a server-derived, read-only field returned but never accepted (verified, lines 166-178):
```python
"""
Full_name is a server-derived, read-only
compatibility value — it is never accepted on PersonCreateRequest or
PersonUpdate (see below), but it is still returned here so existing
display/sort/dedup consumers keep working unchanged.
"""

id: int
full_name: str
```
Add `display_name: Optional[str] = None` and `oyez_speaker_id: Optional[str] = None` to `PersonDetail` following this exact precedent — returned, documented as read-only, **never added to `PersonUpdate`'s allow-list** (verified `PersonUpdate` at lines 203-260, `model_config = ConfigDict(extra="forbid")` at line 260 — confirm the new fields are absent from that class entirely, per D-09/D-10 and the Anti-Patterns section of RESEARCH.md).

---

### `api/schemas/speakers.py::SpeakerPopoverEntry` / `api/schemas/utterance.py::UtteranceResponse` (DTOs, D-12 initials field)

**Analogs:** each schema's own existing optional string fields.

`SpeakerPopoverEntry` (verified, lines 51-71):
```python
class SpeakerPopoverEntry(BaseModel):
    person_id: int
    full_name: str
    role_name: Optional[str] = None
    photo_url: Optional[str] = None
    birthdate: Optional[str] = None
    death_date: Optional[str] = None
    bio_text: Optional[str] = None
    tenure: list[TenureEntry] = []
```
Add `initials: str` (or `Optional[str]` if a genuinely-unresolvable case exists — RESEARCH.md's fallback rule in D-13 always produces something, even `'?'`, so a non-optional `str` matches the current client behavior more closely).

`UtteranceResponse` (verified, lines 22-37):
```python
class UtteranceResponse(BaseModel):
    id: int
    ...
    speaker_name: Optional[str] = None
    speaker_role: Optional[str] = None
    model_config = {"from_attributes": True}
```
Add `speaker_initials: Optional[str] = None` (nullable here because `speaker_name` itself is nullable when `person_id` is null — an utterance with no resolved person has no initials to compute).

**Per RESEARCH.md Assumption A1**, these are the two schemas the plan should target — verify this pairing explicitly rather than assuming a single shared type covers both `SpeakerPopover.svelte` and the `+page.svelte` roster.

---

### `api/domain/person_names.py` (utility, transform — initials derivation)

**Analog:** `_KNOWN_SUFFIXES` + `split_legacy_full_name` in the same module (verified, lines 234, 269-300):
```python
_KNOWN_SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}
```
```python
def split_legacy_full_name(full_name: str) -> SplitResult:
    """
    Conservatively split a legacy `full_name` string into structured parts.
    ...
    Every other shape — blank/single-part names, particles, more than three
    tokens (ambiguous compound surnames), a suffix-like token without a
    leading comma..., or a split that does not reformat back to the exact
    original string — is returned unapplied...
    """
```
The new initials function should live in this module (co-located with the suffix vocabulary it reuses per D-13) and take the same "structured parts first, `split_legacy_full_name`-shaped fallback second" approach: given `first_name`/`last_name` (structured), compute directly; given only `full_name` (legacy), reuse `_KNOWN_SUFFIXES` to drop suffix tokens before taking first/last initials — this is the precise fix for the `"John Marshall Harlan, II"` → `"JI"` bug (JUSTICE-06), since `_KNOWN_SUFFIXES` already contains `"II"`.

---

### `api/services/arguments.py` (service, CRUD — COALESCE change)

**Analog:** itself, the exact line being edited (verified, lines 236-244; `func` already imported at line 17 per RESEARCH.md):
```python
select(
    Utterance,
    Person.full_name.label("speaker_name"),
    Role.name.label("speaker_role"),
)
.outerjoin(Person, Utterance.person_id == Person.id)
.outerjoin(Role, Person.role_id == Role.id)
```
Change `Person.full_name.label("speaker_name")` to `func.coalesce(Person.display_name, Person.full_name).label("speaker_name")`. If `speaker_initials` is added to `UtteranceResponse`, this same `select()` needs a third labeled expression computed from the same coalesced value (or from structured parts) — do it in this one query, not as a second round-trip.

---

### `app/src/lib/public/SpeakerPopover.svelte` / `app/src/routes/arguments/[slug]/+page.svelte` (components, D-12/D-13)

**Analog:** each is the other's byte-identical twin — both must be replaced with a field consumer, not converged into each other (D-12 already retires both independent copies by moving computation server-side).

`SpeakerPopover.svelte` (verified, lines 55-61):
```javascript
const initials = $derived.by(() => {
    const parts = speaker.full_name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return '?';
});
```
Becomes: `const initials = $derived(speaker.initials);` (still `$derived`, not `const`, per the same-instance-reuse comment already in this file at lines 40-46 — the popover reassigns `speaker` on a new pick, so a plain `const` off the prop would freeze on the first speaker, the same class of bug flagged in MEMORY's "Svelte prop-capture stale flag" note).

`+page.svelte` (verified, lines 180-186):
```javascript
function getInitials(name: string): string {
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return '?';
}
```
Per Pitfall 3, this roster is built from `u.speaker_name` (from `UtteranceResponse`), NOT from `SpeakerPopoverEntry` — so this file's 6 `getInitials(...)` call sites must be rewired to read `u.speaker_initials` from the new `UtteranceResponse.speaker_initials` field, and the now-dead `getInitials` function removed entirely (not left as unused dead code).

**Testing constraint (CLAUDE.md Testing Policy):** verify this fix in a real browser or by the operator's eye — no static source-text contract test asserting the string is absent from the `.svelte` file. Per MEMORY's "Svelte $state proxy vs grep contract tests" note, a grep-based contract here would prove nothing about rendered output.

---

### `app/src/routes/admin/people/[id]/+page.svelte` (component, D-09/D-10 read-only fields)

**Analog:** the existing Full Name `<output>` block, to be copied verbatim in shape (verified, lines 375-390):
```svelte
<div style="display: flex; align-items: baseline; gap: var(--space-sm); margin-bottom: var(--space-sm); flex-wrap: wrap;">
    <span id="full_name_label" style="font-size: var(--font-size-caption); ...">
        Full Name
    </span>
    <span id="full_name_explanation" style="font-size: var(--font-size-caption); ...">
        Generated from name parts.
    </span>
</div>
<output
    id="full_name_preview"
    aria-labelledby="full_name_label full_name_explanation"
    aria-live="polite"
    style="display: block; width: 100%; background-color: var(--color-bg); border: 1px solid var(--color-border); border-radius: 6px; padding: var(--space-sm) var(--space-md); font-size: var(--font-size-body); box-sizing: border-box; color: {fullNamePreview === 'N/A' ? 'var(--color-text-secondary)' : 'var(--color-text-primary)'}; font-style: {fullNamePreview === 'N/A' ? 'italic' : 'normal'};"
>{fullNamePreview}</output>
```
Per 52-UI-SPEC.md's Layout & Placement Contract, add two more of exactly this shape — `Corpus Display Name` and `Oyez Speaker ID` — immediately after this block and before the Name Parts grid, each showing "Not in corpus" (italic, `--color-text-secondary`) when blank, matching the `fullNamePreview === 'N/A'` conditional-style pattern already present.

---

### `app/src/routes/admin/people/[id]/+page.server.ts` (route/provider, Pitfall 5)

**Analog:** itself — the hand-maintained `PersonDetail` TypeScript interface (verified, lines 22-65):
```typescript
interface PersonDetail {
    id: number;
    full_name: string;
    bio_text: string | null;
    photo_url: string | null;
    ...
    review_state: string;
    provenance_metadata: { ... } | null;
}
```
Add `display_name: string | null;` and `oyez_speaker_id: string | null;` here in the same request the Pydantic `PersonDetail` schema gains them — this file has no shared-type codegen from FastAPI (confirmed per RESEARCH.md Pitfall 5), so both edits are one task, not two separately-schedulable ones.

---

### `app/src/routes/admin/+page.server.ts` (route/provider, D-14/D-15)

**Analog:** itself — the existing `resetToFixture` action and its two locked error literals (verified, lines 210-270):
```typescript
const RESET_ENV_ERROR = 'Reset failed: this action is not available in this environment.';
const RESET_MID_ERROR =
    'Reset failed partway through — the database may be in an inconsistent state. Check server logs before retrying.';
```
D-14 keeps `RESET_ENV_ERROR` verbatim (environment refusal is unchanged) and keeps `RESET_MID_ERROR`'s *text* verbatim but demotes it from "every failure" to "true fallback, used only when the re-read itself is inconclusive" (per 52-UI-SPEC.md Copywriting Contract). Two NEW string constants are needed for the other two re-read outcomes (partial-reseed-confirmed, full-success-confirmed) — follow the same top-of-file `const X_ERROR = '...';` declaration pattern immediately above `export const actions`.

**Explicit gap (RESEARCH.md Pitfall 4 / Open Question 1):** no existing endpoint performs the "re-read fixture state" check this action now needs on any failure. The nearest existing logic is `reset_to_fixture`'s own internal per-conversation existence check (`select(Argument).where(Argument.oyez_transcript_id == conversation_id)`, inside `api/services/admin_dev.py`, not exposed as a route) and `admin_dev.py`'s existing pattern of two narrow dev-only POST endpoints under `api/routers/admin_dev.py`. RESEARCH.md's recommendation — and the one this pattern map endorses for the plan — is a **new** narrowly-scoped dev-only GET endpoint mirroring that existing narrow-endpoint shape, not a retrofit of `GET /api/admin/arguments`.

---

### `pipeline/tests/test_import_justices_csv.py` (test, CRUD fixture)

**Analog:** itself — the existing "person to be upgraded" fixture pattern, which must change key, not shape (verified, line 210 and siblings at 546/616/686/820/1025/1078/1124/1182):
```python
existing = Person(full_name="Testcase Q. Fixture", is_justice=False)
```
Per RESEARCH.md Pitfall 1, every one of these ~15 fixtures constructs a "pre-existing person" with `full_name` set and **no `oyez_speaker_id`** — once the importer's dedup key changes, these fixtures will silently take the CREATE branch instead of UPGRADE, and the tests will fail for a reason unrelated to what they test. Each needs `oyez_speaker_id="..."` added to the `Person(...)` constructor call so the UPGRADE branch still triggers as originally intended — mechanical, but touches every one of these ~15 call sites, not a small tail risk.

---

### `pipeline/tests/test_justice_identity_mapping.py` (NEW, D-02 structural test)

**No direct in-repo analog** — this is a new category of test (structural cross-file agreement check on a data artifact, not application behavior). Nearest kin for pytest scaffolding conventions (fixture setup, `isolated_session`/`tmp_path` usage) is `test_import_justices_csv.py` itself, but its actual assertion logic (comparing `oyez_speaker_id` slug ↔ corpus display form ↔ CSV first/last name for structural agreement) has no precedent to copy — build it directly from D-02's stated rule ("the oyez_speaker_id slug, the corpus display form and the CSV first/last name agree structurally").

Per the project's Testing Policy (CLAUDE.md): name it after the unit under test (`test_justice_identity_mapping.py`), not the phase number, and keep it as a permanent regression test (RESEARCH.md's own Open Question 3 recommendation) since a future typo'd `oyez_speaker_id` in the mapping CSV is exactly the kind of regression this suite exists to catch.

## Shared Patterns

### Authority ladder (blank-only prefill / gated overwrite)
**Source:** `api/domain/authority.py::decide_write` via `api/services/admin_review.py::apply_person_value_change`
**Apply to:** `pipeline/commands/import_justices_csv.py` — reuse verbatim for any field where an operator edit must outrank a reseed; do NOT reuse for `display_name` without first resolving RESEARCH.md Pitfall 2 (a field D-09 makes universally read-only has no adversary to arbitrate against, so a simpler blank-only assignment may be correct instead).
```python
decision = await apply_person_value_change(
    session, person=person, field="first_name", incoming_value=prepared.first_name,
    incoming_source=ImportSource.SEED.value, incoming_method=ImportMethod.DIRECT.value,
    import_run_id=None,
)
if decision in (WriteDecision.ACCEPT, WriteDecision.ACCEPT_AND_RECORD):
    setattr(person, "first_name", prepared.first_name)
```

### Mass-assignment allow-list (`extra="forbid"`)
**Source:** `api/schemas/admin_people.py::PersonUpdate`, `model_config = ConfigDict(extra="forbid")` (line 260)
**Apply to:** confirm `display_name` and `oyez_speaker_id` are added ONLY to `PersonDetail` (read path), never to `PersonUpdate` (write path) — this is the one discipline every schema-touching task in this phase must preserve (D-09/D-10).

### `oyez_speaker_id`-first identity resolution
**Source:** `pipeline/commands/import_convokit.py::_resolve_person` (lines 1755-1764, unchanged reference)
**Apply to:** the new lookup in `import_justices_csv.py` — same two-tier order (id first, name second with backfill), same counters-dict increment convention (`counters["people_matched"]`/`counters["people_created"]`), if the plan chooses to track import counters symmetrically.

### `SimpleNamespace(...)` args-object convention for pipeline command invocation from a service
**Source:** `api/services/admin_dev.py:246-251` (`run_import_convokit` call)
**Apply to:** the new `run_import_justices_csv` call inside `reset_to_fixture` (D-16) — same shape, same file.

### Read-only server-derived field, documented in schema docstring
**Source:** `api/schemas/admin_people.py::PersonDetail.full_name` docstring (lines 166-178)
**Apply to:** the docstring additions for `display_name`/`oyez_speaker_id` on the same schema (D-09/D-10) — state explicitly that the field is returned but never accepted, matching `full_name`'s own precedent phrasing.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Partial unique index predicate (`postgresql_where=...`) inside the new migration | migration/DDL | batch | Zero `postgresql_where` usages across all 32 existing migrations (RESEARCH.md, grep-verified). Use SQLAlchemy's documented Postgres dialect `postgresql_where` API directly; `0031_argument_slug.py` supplies the surrounding nullable-column-plus-constraint shape but not this predicate. |
| D-14 fixture-state re-read endpoint | route (new, dev-only GET) | request-response | No existing endpoint answers "did the last reset actually land." Nearest kin is `reset_to_fixture`'s own internal per-conversation check, which lives inside a write transaction, not as an independently-callable read. Follow the existing dev-only-narrow-POST-endpoint shape in `api/routers/admin_dev.py` structurally, but this is new logic, not a copy. |
| `pipeline/tests/test_justice_identity_mapping.py` assertion logic | test | transform | New test category (cross-file structural agreement on a data artifact) with no precedent test to copy from; build directly from D-02's stated rule. |

## Metadata

**Analog search scope:** `alembic/versions/`, `pipeline/commands/`, `pipeline/tests/`, `api/services/`, `api/models/`, `api/schemas/`, `api/domain/`, `app/src/lib/public/`, `app/src/routes/admin/`, `app/src/routes/arguments/[slug]/`, `data/corpus/`
**Files scanned:** ~20 read directly this session (all cited above with verified line numbers); tracked-source status confirmed via `git ls-files` for every path except the gitignored `data/corpus/*.csv` data files, which are untracked by design (confirmed via `data/corpus/.gitignore`, itself tracked)
**Pattern extraction date:** 2026-09-24
