# Phase 39: Bench popover — additional context data for Justices - Research

**Researched:** 2026-07-22
**Domain:** Full-stack feature — Postgres/Alembic schema extension, pipeline CSV backfill, FastAPI schema/service, SvelteKit admin editor + public popover
**Confidence:** HIGH

## Summary

Phase 39 is an unusually well-specified phase: `39-CONTEXT.md` already locks 17 implementation decisions (D-01–D-17) naming exact files, exact CSV columns, and an exact prior-phase pattern (Phase 37's `CourtTenure.office` CHECK-constraint rename) to replicate for a new `reason_left` field. This research verified every one of those claims directly against the current repository state — all checked out true. Nothing in CONTEXT.md's description of "current code" was found to be stale or inaccurate.

The work spans five layers that must move together: (1) two Alembic migrations adding `people.death_date` and `court_tenures.reason_left` (mirroring migrations 0016/0020/0021 exactly), (2) `pipeline/commands/import_justices_csv.py` extended to read three already-present CSV columns (`Birthdate`, `Death Date`, `Reason Left`) and null-only-backfill them onto existing rows, (3) `api/schemas/admin_people.py` + `api/services/admin_people.py` extended so the admin editor's PATCH flow carries the two new fields end-to-end, (4) `api/schemas/speakers.py` + `api/services/speakers.py` reworked to move `appointed_by`/`appointing_president_party` from a single top-level field to per-tenure fields and to reverse the T-14-02 "party excluded" comment, and (5) `app/src/routes/admin/people/[id]/+page.svelte` (activate two disabled inputs) and `app/src/lib/components/SpeakerPopover.svelte` (render the new fields) on the frontend. The public argument page's `+page.server.ts` needs **no changes** — it already spreads every key off the raw speaker object (`{ ...s, photo_url_full, is_bench }`), so new fields pass through automatically.

**Primary recommendation:** Follow the Phase 37 migration pattern byte-for-byte (rename-safe add-column migration + a *second* migration that adds the CHECK constraint with a bind-time integrity check), reuse the exact `office_title()`/`OFFICE_TITLES` code shape for a new `reason_left_title()`/`REASON_LEFT_TITLES` helper, and thread the two new fields through `TenureWrite`/`TenureRow` exactly like `appointed_by`/`appointing_president_party` already are.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `people.death_date` + `court_tenures.reason_left` schema | Database / Storage | API / Backend (ORM model + CHECK constraint mirror) | Alembic is sole DDL authority (CLAUDE.md); ORM model documents the same constraint for self-documentation only |
| CSV historical data backfill | Pipeline (offline CLI) | Database / Storage | `import_justices_csv.py` is explicitly an offline operator-only script (CLAUDE.md hard constraint) that writes directly to Postgres |
| Reason-left canonical→display mapping | API / Backend | Browser / Frontend (SvelteKit render boundary) | Mirrors existing `office_title()` split: backend emits raw canonical value; only `SpeakerPopover.svelte` and the admin editor project to display text |
| Party affiliation public exposure (T-14-02 reversal) | API / Backend | — | Policy-level schema/service change (what is or isn't serialized); no client-side logic needed beyond rendering plain text |
| Admin editor input activation (Death Date, Reason Left) | Browser / Frontend (SvelteKit `+page.svelte` + `+page.server.ts`) | API / Backend (`PersonUpdate`/`TenureWrite` allow-list) | Existing atomic save-form pattern; API schema is the enforcement boundary (mass-assignment guard) |
| Bio text display with clamp/expand | Browser / Frontend | — | Pure presentation of an already-fetched, already-public field (`Person.bio_text` is already selected in `get_argument_speakers`... **verify**: see Pitfall 1 below — it is currently NOT selected) |
| Advocate descriptor placeholder | Browser / Frontend | — | Static/dummy text only this phase (D-16); no data layer involvement |

## Package Legitimacy Audit

**No new external packages are introduced by this phase.** All work uses libraries already installed and verified in prior phases:

| Package | Registry | Status | Disposition |
|---------|----------|--------|-------------|
| `python-dateutil>=2.9` | PyPI | Already installed (`requirements.txt:11`), already used by `import_justices_csv.py`'s `_parse_optional_date()` — no new usage pattern needed | Reuse as-is |
| `alembic` | PyPI | Already installed, sole DDL authority per CLAUDE.md | Reuse as-is |
| `bits-ui ^2.18.1` | npm | Already installed (`app/package.json`), already the popover primitive `SpeakerPopover.svelte` renders inside | Reuse as-is |
| `svelte ^5.30.0` | npm | Already installed; Runes mode confirmed in use (`$props`, `$state`, `$derived`) | Reuse as-is |

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
data/corpus/supreme_court_justices_sections.csv  [VERIFIED: direct file read]
   │  (Birthdate, Death Date, Reason Left columns — confirmed present, 126 rows)
   ▼
pipeline/commands/import_justices_csv.py  (offline CLI, "python -m pipeline import-justices")
   │  extend _iter_csv_rows() consumers to also read the 3 new columns
   │  null-only backfill onto existing Person/CourtTenure rows (D-06)
   ▼
Postgres: people.death_date, court_tenures.reason_left  (new columns, Alembic-owned)
   │
   ├──► api/services/admin_people.py::get_person_detail / update_person
   │        │  (admin editor read/write — PersonDetail/PersonUpdate/TenureWrite/TenureRow)
   │        ▼
   │    app/src/routes/admin/people/[id]/+page.svelte  (activate 2 disabled inputs)
   │
   └──► api/services/speakers.py::get_argument_speakers
            │  (public popover read — currently hardcodes appointing_president=None,
            │   currently omits party; both must be wired/reversed here)
            ▼
        api/schemas/speakers.py (TenureEntry gains appointed_by/appointing_president_party/
            reason_left; SpeakerPopoverEntry gains birthdate/death_date/bio_text)
            ▼
        GET /arguments/{id}/speakers  (public FastAPI endpoint, no auth)
            ▼
        app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts
            (NO CHANGES NEEDED — spreads all keys via `{ ...s, photo_url_full, is_bench }`)
            ▼
        app/src/lib/components/SpeakerPopover.svelte
            (render birthdate/death date, bio clamp+expand, per-tenure
             appointed_by/party/reason, advocate descriptor placeholder slot)
```

### Recommended Project Structure

No new directories. Every touched file already exists at the path CONTEXT.md names:

```
alembic/versions/
├── 00XX_add_person_death_date.py          # new — mirrors 0016 shape
└── 00XX_add_add_constrain_tenure_reason_left.py  # new — mirrors 0020+0021 shape (see Pitfall 3)
api/models/models.py                        # Person.death_date, CourtTenure.reason_left + constant module
api/schemas/admin_people.py                 # TenureWrite/TenureRow/PersonDetail/PersonUpdate additions
api/services/admin_people.py                # get_person_detail/update_person/_replace_tenures additions
api/schemas/speakers.py                     # TenureEntry/SpeakerPopoverEntry additions + T-14-02 comment reversal
api/services/speakers.py                    # get_argument_speakers wiring + T-14-02 comment reversal
pipeline/commands/import_justices_csv.py    # read 3 new CSV columns, null-only backfill
app/src/routes/admin/people/[id]/+page.svelte     # activate Death Date input, Reason Left <select>
app/src/routes/admin/people/[id]/+page.server.ts  # extend TenureRowClient/PersonDetail interfaces + save action
app/src/lib/components/SpeakerPopover.svelte      # render new fields, bio clamp/expand, advocate placeholder
```

### Pattern 1: Canonical-enum-with-CHECK-constraint + display-title helper (Phase 37 precedent)

**What:** A `court_tenures` string column is constrained to an exact vocabulary via a two-step migration (add nullable column with no constraint → later migration adds `CheckConstraint` + flips `nullable=False` only after a bind-time `SELECT COUNT(*)` preflight proves zero invalid rows exist).

**When to use:** For the new `reason_left` field. D-01 fixes the vocabulary as exactly `retired`, `died`, `promoted` (nullable — covers "still active" and the 2 blank historical rows).

**Example (mirrors `api/models/models.py` lines 137–159 and `alembic/versions/0021_constrain_tenure_office.py` exactly):**
```python
# api/models/models.py — Source: this repo, verified 2026-07-22
REASON_RETIRED = "retired"
REASON_DIED = "died"
REASON_PROMOTED = "promoted"
VALID_REASONS_LEFT = (REASON_RETIRED, REASON_DIED, REASON_PROMOTED)

REASON_LEFT_TITLES = {
    REASON_RETIRED: "Retired",
    REASON_DIED: "Died in office",
    REASON_PROMOTED: "Promoted",
}

def reason_left_title(reason: str) -> str:
    """Exhaustive over VALID_REASONS_LEFT — raises KeyError for any other input."""
    return REASON_LEFT_TITLES[reason]
```
```python
class CourtTenure(Base):
    __table_args__ = (
        CheckConstraint("office IN ('chief', 'associate')", name="ck_court_tenures_office"),
        CheckConstraint(
            "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
            name="ck_court_tenures_reason_left",
        ),
    )
    ...
    reason_left = Column(String(50), nullable=True)  # D-02: null covers active + unknown historical rows
```

**Important divergence from the office pattern:** `office` is `nullable=False` after migration 0021 because every tenure MUST have an office. `reason_left` is **nullable=True permanently** (D-01, D-02) — an active tenure (`end_date IS NULL`) never has a reason, and 2 historical rows have a genuinely blank CSV value. The CHECK constraint must therefore be `reason_left IS NULL OR reason_left IN (...)`, not a bare `IN (...)` (which would reject NULL under Postgres's three-valued CHECK semantics being permissive for NULL anyway — but writing it explicitly documents intent and matches D-02's stated null semantics).

### Pattern 2: Null-only backfill on re-import (Phase 38 D-16 precedent)

**What:** When an importer gains the ability to populate a new field, it must never overwrite an existing non-null value — only fill currently-null fields.

**Example — extending `import_justices_csv.py`'s existing tenure/person lookup (verified against current file, lines 178–229):**
```python
# person branch (upgrade-in-place) — existing code only sets is_justice;
# extend to also backfill birthdate/death_date, but ONLY when currently None (D-06):
if person is not None:
    if not person.is_justice:
        person.is_justice = True
        people_upgraded += 1
    if person.birthdate is None and birthdate is not None:
        person.birthdate = birthdate
    if person.death_date is None and death_date is not None:
        person.death_date = death_date
else:
    person = Person(
        ...,
        birthdate=birthdate,       # new-row case: always set from CSV (D-05)
        death_date=death_date,     # new-row case: always set from CSV (D-05)
    )
```
The existing tenure branch (`existing_tenure is None` → create; else → do nothing) needs the analogous null-only-backfill branch added for `reason_left` on the `else` arm, since today the `else` arm silently no-ops on every field including ones that could be backfilled.

### Pattern 3: Assembly-time null hardcode → real per-row wiring (D-13)

**What:** `api/services/speakers.py`'s Step 5 assembly currently hardcodes `"appointing_president": None` at the top level and stringifies only `office`/`start_date`/`end_date` per tenure (lines 172–178, 213–217). D-13 requires this to become per-`TenureEntry` fields.

**Example:**
```python
# str_tenures_by_person building (Step 3a) — add the 3 new keys per tenure:
str_tenures_by_person[t.person_id].append(
    {
        "office": t.office,
        "start_date": str(t.start_date) if t.start_date else None,
        "end_date": str(t.end_date) if t.end_date else None,
        "appointed_by": t.appointed_by,
        "appointing_president_party": t.appointing_president_party,
        "reason_left": t.reason_left,
    }
)
# Step 5 assembly — drop the top-level hardcode entirely, add birthdate/death_date/bio_text:
result.append({
    "person_id": person.id,
    "full_name": person.full_name,
    "role_name": role_name,
    "photo_url": person.photo_url,
    "birthdate": str(person.birthdate) if person.birthdate else None,
    "death_date": str(person.death_date) if person.death_date else None,
    "bio_text": person.bio_text,
    "tenure": str_tenures_by_person[person.id],
    "side": side.value if side is not None else None,
})
```

### Anti-Patterns to Avoid

- **Auto-deriving `reason_left` from `end_date`/`death_date` comparison:** D-03 explicitly forbids this — the field is authoritative CSV source data, imported directly, never computed. Do not add "if `end_date == death_date` then `died`" logic anywhere.
- **Reusing `_bench_role_and_missing_tenure`'s (admin_people.py) no-fallback semantics for the public popover:** the public-facing `_tenure_role_name` (speakers.py) intentionally has a most-recent-tenure fallback (D-14, Phase 15) that the admin Resolve-card helper intentionally does NOT have — these two helpers are deliberately different; do not consolidate them.
- **Coercing an invalid/blank legacy `office` or future invalid `reason_left`:** both `office_title()` and the new `reason_left_title()` must stay exhaustive-over-canonical-values-only and raise `KeyError` for anything else, with callers catching `KeyError` and degrading to `None` (never crashing the whole popover for one bad row — see `_tenure_role_name`'s and `_bench_role_and_missing_tenure`'s existing `except KeyError: return None` pattern).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Constrained-vocabulary DB column | A new validation library or custom Python enum class | `CheckConstraint` + a plain module-level tuple/dict (`VALID_REASONS_LEFT`, `REASON_LEFT_TITLES`) — exact Phase 37 shape | Project already has this exact pattern proven in production (`OFFICE_CHIEF`/`OFFICE_TITLES`/`office_title()`); a `SAEnum`/native Python `enum.Enum` would require a new PG enum type and diverge from the string+CHECK convention `office` already established |
| CSV parsing / date parsing | `pandas`, hand-rolled regex date parsing | Existing `csv` stdlib + `dateutil.parser.parse()` via `_parse_optional_date()` | Already proven against this exact CSV (126 rows, all sections) — no new dependency justified for reading 3 more columns from a file already being parsed |
| Bio text clamp/expand interaction | A generic new "read more" component from scratch, or an npm line-clamp library | Plain CSS `-webkit-line-clamp` (or max-height + overflow) + a `$state<boolean>` toggle, matching the existing `showInitials` `$state` idiom already in `SpeakerPopover.svelte` | The component already uses zero external UI libraries beyond `bits-ui`'s Popover primitive; a bespoke ~10-line toggle is simpler and more consistent than pulling in a clamp library |

**Key insight:** This project's established convention for "constrained value with formal display mapping" is a plain Python dict + helper function, not a class hierarchy or third-party validation library — every prior phase (Phase 37's office, this phase's reason_left) should look identical in shape.

## Common Pitfalls

### Pitfall 1: `bio_text` is NOT currently selected by `get_argument_speakers` — D-14 requires a new SELECT, not just a schema field
**What goes wrong:** Assuming `Person.bio_text` is already available in the assembly loop and only the schema/frontend need touching.
**Why it happens:** `bio_text` already exists on the `Person` model and is already fetched by Step 2's `select(Person, Role.name...)` query (the whole `Person` ORM object is selected) — so it actually **is** available on the `person` object in the Step 5 loop without a new query. [VERIFIED: `api/services/speakers.py` lines 143–148 select the full `Person` row]. The pitfall is the opposite of what it looks like: no new SELECT is needed, but a reviewer might mistakenly add a redundant one. Just reference `person.bio_text` directly in the Step 5 dict.
**How to avoid:** Confirm `person.bio_text` is accessible directly from the already-selected ORM row before adding any new query.
**Warning signs:** A PR that adds a second query for bio_text, or that forgets to add the field at all because it assumes a new fetch is required.

### Pitfall 2: Migration numbering collision risk with in-flight Phase 38
**What goes wrong:** Phase 38 (full-name-vs-name-parts-rethink) has 6 unexecuted `PLAN.md` files sitting in the working tree as of this research (`git status` confirms no new migrations under `alembic/versions/` yet — highest existing migration is `0021_constrain_tenure_office.py`). If Phase 38 executes and adds its own migration(s) before Phase 39 executes, Phase 39's planned "`0022`" migration number will collide.
**Why it happens:** Both phases are scheduled in the same v1.6 milestone; STATE.md shows Phase 38 as `current_phase` and `status: executing`.
**How to avoid:** The planner should NOT hardcode a migration filename number in the plan. Instruct the execute-phase agent to run `ls alembic/versions/ | sort | tail -1` (or equivalent) immediately before generating each migration file to pick the next free number at execution time, not planning time.
**Warning signs:** Two migration files with the same revision number, or an Alembic `down_revision` chain that doesn't match `alembic heads` at execution time.

### Pitfall 3: `reason_left`'s CHECK constraint must explicitly permit NULL — the office pattern's bare `IN (...)` is not directly reusable
**What goes wrong:** Copy-pasting `CheckConstraint("reason_left IN ('retired', 'died', 'promoted')", ...)` without the `IS NULL OR` prefix. Postgres CHECK constraints are actually NULL-permissive by default (a NULL input makes the whole boolean expression UNKNOWN, which passes), so this would *technically* still allow NULL — but it's fragile/non-obvious and diverges from `office`'s constraint (which is `nullable=False` and never needs a NULL branch). Because `reason_left` is *intentionally* nullable forever (unlike `office`), writing the constraint without the explicit `IS NULL OR` makes the intent unclear to future readers and to `office_title`-style helpers that might assume exhaustiveness.
**Why it happens:** Phase 37's exact CHECK constraint text has no NULL-handling because `office` became `NOT NULL` in the same migration. `reason_left` never goes through that second step.
**How to avoid:** Write the constraint as `"reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')"` and do NOT add a `nullable=False` migration step for this column — there is no Phase-37-style "second migration that flips NOT NULL" for `reason_left` (D-02 requires it stay nullable permanently, unlike `office`).
**Warning signs:** A migration that includes an `alter_column(..., nullable=False)` step for `reason_left`, or a preflight `SELECT COUNT(*)` that treats existing NULL `reason_left` rows (all currently-active tenures, ~9 CSV rows, plus any tenure created before this phase) as "invalid."

### Pitfall 4: `TenureWrite` (strict schema) vs `TenureRow` (tolerant schema) split must be preserved for the two new tenure fields
**What goes wrong:** Adding `appointed_by`/`appointing_president_party` (already present) is fine as free-text `Optional[str]` on both schemas — no change needed there per D-13 clarification (they were already per-tenure; only the *public* `TenureEntry` needs them added). But `reason_left` is a NEW constrained field: if it's added only to `TenureRow` (read) and forgotten on `TenureWrite` (the admin editor's save contract), the admin `<select>` dropdown (D-09) will have no way to persist its value.
**Why it happens:** The existing split exists specifically so writes are strict (`Literal["chief", "associate"]`) while reads are tolerant (`Optional[str]`) for legacy data. A new constrained field needs the identical treatment: `TenureWrite.reason_left: Optional[Literal["retired", "died", "promoted"]] = None` (write side, since D-02 means it's optional even for TenureWrite — most rows have no `end_date` yet so no reason) and `TenureRow.reason_left: Optional[str] = None` (read side, tolerant).
**How to avoid:** Update BOTH `TenureWrite` and `TenureRow` in `api/schemas/admin_people.py`, and BOTH the `_replace_tenures()` write path and `get_person_detail()`/`get_argument_speakers()` read paths in the respective services.
**Warning signs:** The admin editor's Reason Left `<select>` silently fails to persist a selection after save+reload.

### Pitfall 5: `PersonUpdate.death_date` needs the exact same `model_fields_set` guard as `birthdate`
**What goes wrong:** `update_person()` in `api/services/admin_people.py` uses `body.model_fields_set` (not `is not None`) to distinguish "field omitted from this specific form submission" from "field explicitly cleared to null" — this is CR-01/CR-02's fix for the Identity+Person-Type form vs. Bio+Photo form split (two separate `<form>` elements submitting to two separate actions, each carrying only its own field subset). If `death_date` is written unconditionally (`person.death_date = body.death_date`), the Bio+Photo form's `photo` action would wipe `death_date` to `None` on every photo/bio save, since `PersonUpdate.death_date` defaults to `None` and isn't in that form's submitted field set.
**Why it happens:** The pattern is subtle and easy to miss if a developer models the new field after `body.is_justice is not None` (a *different*, older guard style still present in the same function for a field that IS shared across both forms) rather than the `"birthdate" in fields_set` style used for the Identity-form-only fields.
**How to avoid:** Add `death_date` to the save-form (not the photo-form) exactly like `birthdate`, and guard with `if "death_date" in fields_set:` in `update_person()`.
**Warning signs:** Death Date value disappears after uploading a photo or editing the bio, even though the operator never touched the Death Date field.

### Pitfall 6: `SpeakerPopover.svelte`'s current fixed `max-width: 360px` popover card will visually overflow with the new content volume
**What goes wrong:** The card currently renders name + role + a short 2-line tenure block. Adding birthdate/death date, a bio paragraph, and a richer multi-line-per-tenure block (office+dates / president+party / reason — 3 lines × N tenures, per the mockup) inside a 280–360px-wide, unconstrained-height card risks an unusably tall popover, especially for Justices with 2 tenures (e.g. Rehnquist: Associate + Chief).
**Why it happens:** The original Phase 14 popover was designed for a much smaller data set.
**How to avoid:** This is explicitly flagged as "Claude's Discretion" in CONTEXT.md ("Exact popover layout for fitting birthdate/death date + a multi-tenure list without overwhelming the card... defer pixel-level layout to `/gsd-ui-phase`"). The planner should route this to a UI-phase task, not hand-wave a layout in the implementation plan. Consider a scrollable inner region or a max-height on the `Popover.Content` wrapper (currently unconstrained in `+page.server.ts`'s parent `+page.svelte`).
**Warning signs:** UAT/UI-review flags the popover extending off-screen for multi-tenure Justices.

### Pitfall 7: Naming the constant module additions — avoid colliding with the existing `VALID_OFFICES` import surface
**What goes wrong:** `api/services/admin_people.py` already does `from api.models.models import ..., VALID_OFFICES, office_title`. Adding `VALID_REASONS_LEFT`/`reason_left_title` to the same import block is fine, but a developer might instead try to reuse the generic name `VALID_REASONS` or `REASON_TITLES` — collision risk if a future phase adds another "reason X" enum (e.g. a hypothetical "removal reason" for something else).
**How to avoid:** Keep the `reason_left`-specific naming (`VALID_REASONS_LEFT`, `REASON_LEFT_TITLES`, `reason_left_title()`) rather than a generic `REASON_*` name, mirroring how `VALID_OFFICES`/`OFFICE_TITLES` are tenure-office-specific, not generically named.

## Code Examples

### Extending `import_justices_csv.py`'s per-row read (Task/D-04)
```python
# Source: this repo, pipeline/commands/import_justices_csv.py — verified 2026-07-22
# Existing pattern (line ~204-207) already reads 4 columns this way; add 3 more identically:
birthdate = _parse_optional_date(row.get("Birthdate", ""))
death_date = _parse_optional_date(row.get("Death Date", ""))
reason_left_raw = row.get("Reason Left", "").strip()
reason_left = _REASON_LEFT_CSV_MAP.get(reason_left_raw)  # see mapping table below
```

### CSV → canonical `reason_left` value mapping (verified against real file, 2026-07-22)
```python
# Confirmed vocabulary via `awk -F',' 'NR>2 {print $9}' | sort | uniq -c`:
#    2  (blank)
#   51  Died
#    3  Promoted to Chief Justice
#    1  "Reason Left"  <- section-header column-name row from the 2nd (Associate) section,
#                          correctly excluded by the existing _iter_csv_rows() header-detection
#                          logic (this stray count is a shell/awk artifact of a naive line-based
#                          count that doesn't respect the two-section structure; the real
#                          importer's _iter_csv_rows() never yields this row as data)
#   58  Retired
#    9  Still in Office
_REASON_LEFT_CSV_MAP = {
    "Died": "died",
    "Retired": "retired",
    "Promoted to Chief Justice": "promoted",
    "Still in Office": None,   # D-02: open tenure — no reason
    "": None,                  # 2 blank historical rows — unknown
}
```
**Note:** The CSV's raw string "Promoted to Chief Justice" always describes a promotion to Chief — the CSV never uses a bare "Promoted" string. `reason_left="promoted"` on a Chief Justice tenure row would be semantically backwards (per D-03, no auto-derivation) — but per D-03 also, don't try to "fix" this: import the value building on whichever tenure row the CSV attaches "Promoted to Chief Justice" to (the Associate-Justice row that ended when the promotion happened), exactly as it appears, on the correct row per the CSV's own per-row `Reason Left` cell — this is a straight column-value import, not a semantic reassignment.

### Full CourtTenure model addition
```python
# api/models/models.py — Source: this repo, pattern verified against OFFICE_* (lines 137-169)
class CourtTenure(Base):
    __tablename__ = "court_tenures"
    __table_args__ = (
        CheckConstraint("office IN ('chief', 'associate')", name="ck_court_tenures_office"),
        CheckConstraint(
            "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
            name="ck_court_tenures_reason_left",
        ),
    )
    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    office = Column(String(100), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)
    appointed_by = Column(String(200), nullable=True)
    appointing_president_party = Column(String(50), nullable=True)
    reason_left = Column(String(50), nullable=True)  # new — D-01/D-02
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `appointing_president_party` explicitly excluded from public API (T-14-02, Phase 14) | Publicly shown, plain neutral text, identical treatment for every entry (D-11) | Phase 39 (this phase) | Reverses a documented security/apolitical-framing decision — see Security Domain section below; must update stale comments in both `speakers.py` and `schemas/speakers.py` (D-12) |
| Single top-level `appointing_president: Optional[str]` on `SpeakerPopoverEntry` | Per-`TenureEntry` `appointed_by`/`appointing_president_party` fields (D-13) | Phase 39 (this phase) | `SpeakerPopoverEntry.appointing_president` should be removed once callers are migrated — confirm no other consumer reads the top-level field before deleting it (only `SpeakerPopover.svelte` line 84-88 uses it currently) |
| `Person.death_date`/`CourtTenure.reason_left` explicitly deferred with "UI renders a disabled placeholder input with no backing column" (migration 0016 docstring, Phase 27) | Both fields added, backed by real columns | Phase 39 (this phase) | This phase is the explicitly-planned fulfillment of that Phase-27 deferral — migration 0016's own docstring names this exact future phase's scope |

**Deprecated/outdated:**
- The disabled/`placeholder="Coming soon"` inputs at `+page.svelte` lines ~602-617 (Death Date) and ~798-813 (Reason Left) are explicitly temporary scaffolding from Phase 27, meant to be activated by exactly this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Exact migration file names/numbers (`00XX_add_person_death_date.py`, etc.) are illustrative only — actual numbers must be picked at execution time per Pitfall 2 | Recommended Project Structure, Pitfall 2 | Low — explicitly flagged as non-fixed; planner should not hardcode |
| A2 | "Died in office" / "Retired" / "Promoted" display strings match the mockup's tone closely enough — exact final copy is D-15's explicit discretion area, not fully locked | Pattern 1 code example | Low — CONTEXT.md already flags this as agent's discretion; UI-phase can adjust wording |
| A3 | The stray 1-count "Reason Left" awk artifact is a section-header row correctly filtered by `_iter_csv_rows()`'s existing logic, not a 3rd real blank-vocabulary case | Code Examples (CSV mapping) | Low — confirmed by re-reading `_iter_csv_rows()`'s header-skip logic in the actual importer source, not just the awk count |

**All claims above were verified directly against the current repository state (file reads, CSV inspection, awk counts) during this research session — none rely on training-data assumptions about this specific codebase.** No `[ASSUMED]`-tagged package names or unverified library claims exist in this document, since no new packages are introduced.

## Open Questions

1. **Should `SpeakerPopoverEntry.appointing_president` (top-level) be deleted, or kept as a deprecated-but-present field?**
   - What we know: D-13 says the mockup shows appointing president per-tenure, and the hardcoded top-level field "moves" to per-`TenureEntry`.
   - What's unclear: Whether any other consumer (beyond `SpeakerPopover.svelte`) reads the top-level field — none was found in this research, but a full-repo grep at plan time is cheap insurance.
   - Recommendation: Delete the top-level field and its serialization; grep for `appointing_president` (singular, not `_party`) across `app/` and `api/` at plan-check time to confirm zero remaining consumers before removing.

2. **Exact wording/placement for the advocate descriptor placeholder (D-16)?**
   - What we know: It's placeholder-only this phase, dummy text, no real data pipeline.
   - What's unclear: Whether the placeholder should render for ALL advocates or be conditionally hidden — D-16 doesn't specify.
   - Recommendation: Route to UI-phase per CONTEXT.md's own discretion note; a plausible default is rendering it unconditionally with an obviously-generic placeholder (e.g. italicized "—") until real data exists, so the UI slot's spacing/behavior can be validated without misleading users into thinking it's real per-advocate data.

## Environment Availability

No new external dependencies. All tooling (Postgres, Alembic, Python 3.12 + `python-dateutil`, Node/SvelteKit + `bits-ui`) is already installed and in active use by prior phases in this same repository.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (local dev) | New migrations, backfill | ✓ (assumed running per project README, Phase 40) | 16.x per stack table | — |
| Alembic | Sole DDL authority | ✓ | already pinned in requirements.txt | — |
| python-dateutil | CSV date parsing | ✓ (`>=2.9`, already used by this exact file) | — | — |
| bits-ui | Popover primitive | ✓ (`^2.18.1`) | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (`pytest.ini` — `asyncio_mode = auto`, session-scoped loop) [VERIFIED: pytest.ini read directly] |
| Config file | `pytest.ini` (repo root) |
| Quick run command | `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py api/tests/test_admin_people_schemas_service.py -x` |
| Full suite command | `.\.venv\Scripts\python.exe -m pytest` (per `.planning/config.json`'s configured `test_command`) |

No frontend test framework is present (`app/package.json` devDependencies has no `vitest`/`@testing-library/svelte` — only `svelte-check` for type-checking). Frontend verification for this phase is manual/UAT-only, consistent with every prior phase touching `SpeakerPopover.svelte`.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PUB-04 | `reason_left_title()`/`office_title()`-style exhaustiveness (raises KeyError for invalid, never silently coerces) | unit | `pytest api/tests/test_admin_people_schemas_service.py -k reason -x` | ❌ Wave 0 — new test cases to add alongside existing `test_tenure_write_rejects_*` |
| PUB-04 | `import_justices_csv.py` null-only backfill of birthdate/death_date/reason_left onto pre-existing rows | integration (DB-gated, skips without `DATABASE_URL`) | `pytest pipeline/tests/test_import_justices_csv.py -x` | ✅ existing file — extend with new cases (mirrors existing idempotency test shape) |
| PUB-04 | `get_argument_speakers` assembles birthdate/death_date/bio_text/per-tenure appointed_by+party+reason correctly | unit | `pytest api/tests/test_speakers_service.py -x` | ✅ existing file, pure-Python, no DB — extend `_tenure_role_name`-style tests with a new assembly-shape test |
| PUB-04 | Public schema no longer excludes party (T-14-02 reversal doesn't silently regress) | unit | `pytest api/tests/test_admin_people_schemas_service.py -k schema -x` | ❌ Wave 0 — add an explicit "party IS present" regression test to guard against a future accidental re-exclusion |
| PUB-04 (UI) | Popover renders new fields for a Justice with 2 tenures without visual overflow | manual-only | N/A (UAT) | — no automated frontend test framework in this repo |

### Sampling Rate
- **Per task commit:** the quick-run command above (targeted files only).
- **Per wave merge:** full suite (`.\.venv\Scripts\python.exe -m pytest`).
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus manual UAT of the popover for at least one multi-tenure Justice (e.g. Rehnquist) and one advocate.

### Wave 0 Gaps
- [ ] New unit test cases in `api/tests/test_speakers_service.py` covering the reworked assembly (per-tenure `appointed_by`/`appointing_president_party`/`reason_left`, top-level `birthdate`/`death_date`/`bio_text`) — no fixture/framework gap, just new test bodies in an existing DB-free file.
- [ ] New unit test cases in `api/tests/test_admin_people_schemas_service.py` for `TenureWrite`/`TenureRow` accepting/rejecting `reason_left` values, mirroring the existing `test_tenure_write_rejects_*` shape exactly.
- [ ] A new pure-Python test module (or addition to `test_speakers_service.py`) for `reason_left_title()`/`REASON_LEFT_TITLES` exhaustiveness, mirroring the absence of a dedicated `office_title()` unit test today (there isn't one — `office_title` is only exercised indirectly via `_tenure_role_name` tests) — **recommend planner explicitly add a direct test for the new helper** even though the precedent (`office_title`) itself lacks one, since this phase intentionally reverses a security-relevant exclusion and deserves an explicit regression guard (see Phase Requirements → Test Map row 4).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Public read-only endpoint; unauthenticated by design (existing pattern, unchanged) |
| V3 Session Management | No | No session state involved |
| V4 Access Control | No | No new access boundary — `GET /arguments/{id}/speakers` remains public; admin editor remains behind existing `X-Admin-Token` header check (unchanged by this phase) |
| V5 Input Validation | Yes | Pydantic v2 (`TenureWrite`'s `Literal[...]` constraint, mirrored for `reason_left`); DB CHECK constraint as defense-in-depth (existing project convention, Phase 37 precedent) |
| V6 Cryptography | No | Not applicable |
| V14 Configuration / Information Disclosure | **Yes — the central concern of this phase** | This phase is a deliberate, documented reversal of a prior information-disclosure mitigation (`T-14-02`, Phase 14: `appointing_president_party` was "intentionally excluded... admin-only field, apolitical framing constraint"). D-11/D-12 in CONTEXT.md make this an explicit, user-approved policy change, not an accidental regression. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reintroducing a previously-excluded field without updating the threat-model comment that justified the exclusion | Information Disclosure | D-12 explicitly requires updating the T-14-02 comments in both `api/services/speakers.py` and `api/schemas/speakers.py` in the same commit that reverses the exclusion — this research recommends the plan also update the *original* Phase 14 threat-model artifact reference (`.planning/milestones/v1.2-phases/14-speaker-popover-card/14-01-PLAN.md` line 210, `.planning/milestones/v1.2-ROADMAP.md` line 167) is historical and should NOT be edited (it's an archived milestone record of what was true *then*) — instead, PROJECT.md's "Key Decisions" table (already tracking `appointing_president_party` origin per CONTEXT.md's own canonical_refs) is the correct living document to annotate with the reversal, consistent with how this project tracks decision evolution (see STATE.md's "Decisions" log pattern of appending `[Phase N]: ...` entries rather than editing history) |
| Invalid/out-of-vocabulary enum value reaching a display-title lookup and crashing the whole popover for one bad row | Denial of Service (partial) | `office_title()`'s existing `except KeyError: return None` degrade-gracefully pattern (Phase 37 CR-01 precedent, explicitly named in STATE.md's decision log: "fix(37-review): degrade gracefully on non-canonical office values") — `reason_left_title()` must follow the identical pattern from day one, not retrofit it after a UAT gap like Phase 37 needed to |
| Constrained field written via a path that bypasses Pydantic validation (e.g. a future raw-SQL backfill script) | Tampering | DB-level `CheckConstraint` as defense-in-depth (already the established pattern — Pydantic + CHECK constraint together, never CHECK constraint alone) |

**Note for the planner:** Because this phase's core public-API change (D-11) is itself the reversal of a named, documented security control, `/gsd-secure-phase` or an explicit code-review pass should treat the T-14-02 reversal as an intentional, already-approved change (traced to `39-CONTEXT.md` D-11/D-12) rather than flagging it as a new vulnerability to fix. The plan should include a task that updates PROJECT.md's Key Decisions table with the reversal and its rationale, so future audits don't rediscover this as a surprise.

## Sources

### Primary (HIGH confidence)
- Direct file reads of the current repository state (verified 2026-07-22): `api/models/models.py`, `api/services/speakers.py`, `api/schemas/speakers.py`, `api/services/admin_people.py`, `api/schemas/admin_people.py`, `pipeline/commands/import_justices_csv.py`, `app/src/lib/components/SpeakerPopover.svelte`, `app/src/routes/admin/people/[id]/+page.svelte`, `app/src/routes/admin/people/[id]/+page.server.ts`, `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts`, `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`, `app/src/lib/components/CopyableExtractedValue.svelte`, `api/routers/people.py`, `api/routers/arguments.py`, `alembic/versions/0016_add_person_birthdate.py`, `alembic/versions/0020_rename_tenure_seat_to_office.py`, `alembic/versions/0021_constrain_tenure_office.py`, `pytest.ini`, `app/package.json`, `.planning/config.json`.
- Direct CSV inspection: `data/corpus/supreme_court_justices_sections.csv` (head + full `awk`-based column-value census).
- `.planning/phases/39-bench-popover-additional-context-data/39-CONTEXT.md` (locked decisions), `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/ROADMAP.md` (Phase 39 goal/success criteria), `.planning/PROJECT.md` (apolitical framing constraint text).

### Secondary (MEDIUM confidence)
- None — no web search or external documentation was needed; this is an entirely internal, codebase-verifiable phase with no new third-party libraries or unfamiliar APIs.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries; every pattern verified against files already in this repository.
- Architecture: HIGH — every integration point (migrations, schemas, services, frontend files) was read directly, not inferred.
- Pitfalls: HIGH — each pitfall traces to a specific, quoted line range in the actual current code, not a generic domain concern.

**Research date:** 2026-07-22
**Valid until:** Effectively indefinite for the schema/pattern findings (internal codebase, not a fast-moving external API) — but re-verify the migration-number Pitfall 2 immediately before execution if Phase 38 has executed in the interim.
