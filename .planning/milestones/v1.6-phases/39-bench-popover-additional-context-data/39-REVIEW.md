---
phase: 39-bench-popover-additional-context-data
reviewed: 2026-07-29T00:00:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - alembic/versions/0023_add_person_death_date.py
  - alembic/versions/0024_add_constrain_tenure_reason_left.py
  - api/models/models.py
  - api/schemas/admin_people.py
  - api/schemas/speakers.py
  - api/services/admin_people.py
  - api/services/speakers.py
  - api/tests/test_admin_people.py
  - api/tests/test_admin_people_schemas_service.py
  - api/tests/test_migration_0022_person_name_authority.py
  - api/tests/test_phase39_bio_save_contract.py
  - api/tests/test_phase39_popover_ui_contract.py
  - api/tests/test_speakers_service.py
  - api/tests/test_tenure_reason_left.py
  - app/src/lib/components/SpeakerPopover.svelte
  - app/src/routes/admin/people/[id]/+page.server.ts
  - app/src/routes/admin/people/[id]/+page.svelte
  - app/src/routes/cases/[slug]/arguments/[id]/+page.svelte
  - pipeline/commands/import_justices_csv.py
  - pipeline/tests/test_import_justices_csv.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 39: Code Review Report

**Reviewed:** 2026-07-29T00:00:00Z
**Depth:** standard
**Files Reviewed:** 19 (+ 1 test file for the pipeline import command)
**Status:** issues_found

## Summary

This phase adds `people.death_date` (migration 0023), `court_tenures.reason_left`
(migration 0024, CHECK-constrained to `retired`/`died`/`promoted`), widens the
public speaker popover contract to include both plus per-tenure
`appointed_by`/`appointing_president_party`, and extends the historical CSV
importer to backfill all three. The wiring is careful and consistent: the
`model_fields_set`-guarded partial-PATCH discipline is correctly extended to
`death_date`, the DB CHECK constraint mirrors the Pydantic `Literal`, the
public-contract exact-key-set tests are strong, and the CSV import's
blank-only-prefill / never-overwrite-operator-data invariants are well tested.

No crashes, injection vectors, or data-loss bugs were found. The issues below
are data-integrity and UX/robustness gaps specific to the newly introduced
`reason_left` field, one dead-code item, and one test-coverage gap that
mirrors an existing regression test but omits the new `death_date` field.

## Warnings

### WR-01: `reason_left` and `end_date` have no cross-field validation, allowing a documented invariant to be silently violated

**File:** `api/schemas/admin_people.py:36-66` (`TenureWrite`), `api/services/admin_people.py:122-175` (`_replace_tenures`), `alembic/versions/0024_add_constrain_tenure_reason_left.py:47-51`

**Issue:** Multiple docstrings across this phase state the invariant "an open
tenure (`end_date IS NULL`) never has a reason" (e.g.
`api/models/models.py:176-180`'s comment on `VALID_REASONS_LEFT`, and
`alembic/versions/0024...py:14-16`'s migration docstring). Nothing in the
stack actually enforces it:

- The DB CHECK constraint only validates `reason_left IN (...)`, not its
  relationship to `end_date`.
- `TenureWrite` has no model validator tying the two fields together.
- `_replace_tenures` validates `office` up front (lines 146-150) but performs
  no equivalent check for `reason_left` vs. `end_date`.

An operator can therefore save a tenure row with `end_date` blank (open/
active) and `reason_left = "retired"` (or `"died"`/`"promoted"`). This isn't
just a latent data-quality issue — `SpeakerPopover.svelte` renders both
pieces of information unconditionally on the same row: `tenureRange()`
prints `"... – present"` when `end_date` is null (line 129-133) while the
row-2 span below it independently renders `reasonLeftTitle(t.reason_left)`
(line 223) whenever `reason_left` is non-null — so this bad-data state is
directly user-visible as a contradictory "... – present / Retired" popover
row, not just a hidden DB inconsistency.

**Fix:**
```python
# api/schemas/admin_people.py
from pydantic import model_validator

class TenureWrite(BaseModel):
    ...
    @model_validator(mode="after")
    def _reason_left_requires_closed_tenure(self) -> "TenureWrite":
        if self.reason_left is not None and not self.end_date:
            raise ValueError(
                "reason_left requires a non-null end_date — an open tenure "
                "never has a reason (D-02)."
            )
        return self
```
Consider also tightening the DB CHECK constraint (a follow-up migration) to
`reason_left IS NULL OR (end_date IS NOT NULL AND reason_left IN (...))` so
the invariant holds even for writes that bypass the API layer.

### WR-02: `reason_left`'s legacy-value escape hatch has no client-side guidance, unlike the analogous `office` handling — a bad value silently blocks every future save

**File:** `app/src/routes/admin/people/[id]/+page.svelte:171-199` (`handleSaveClick`/`firstInvalidOfficeIndex`), `925-951` (Reason Left `<select>` escape-hatch option), `app/src/routes/admin/people/[id]/+page.server.ts:228-240` (server-side preflight)

**Issue:** `office` has full defense-in-depth for an invalid/legacy stored
value: a dedicated `invalidOfficeOriginal` field, a visible inline error
(`office-error-{row._key}`), a `firstInvalidOfficeIndex()` client-side
preflight that blocks the submit button and focuses the offending row
(`handleSaveClick`, lines 190-199), and a mirrored server-side preflight in
`+page.server.ts` (lines 228-240). `reason_left`'s escape-hatch `<option>`
(lines 948-950) is documented as existing "so a pre-existing non-canonical
stored value stays visible and correctable" — but there is no equivalent
error message, no preflight check, and no submit-blocking for it anywhere.

Because the `tenures` hidden field is always re-submitted on every Save
Person click regardless of which card actually changed (line 710:
`<input type="hidden" name="tenures" ... value={JSON.stringify(tenureRows)} />`),
a single tenure row carrying a non-canonical `reason_left` (however it got
there — see WR-01) will cause FastAPI to 422 on `TenureWrite.reason_left`'s
`Literal` validation on *every* subsequent save, including saves that only
touch Identity or Biography fields. The operator sees only the generic
`"Could not save changes. Check the form and try again."` (line 271-276 in
`+page.server.ts`) with no indication that a tenure row's Reason Left is the
cause, and the escape-hatch option that's supposed to make the bad value
"correctable" gives no signal that it needs correcting.

**Fix:** Add a `firstInvalidReasonLeftIndex()` mirroring
`firstInvalidOfficeIndex()`, check it in `handleSaveClick` alongside the
office check, and render an inline error under the Reason Left `<select>`
analogous to `office-error-{row._key}` when the stored value isn't one of
`''`/`retired`/`died`/`promoted`.

### WR-03: CR-01 partial-PATCH regression test covers `birthdate` but omits the newly added `death_date`, despite an identical documented silent-wipe risk

**File:** `api/tests/test_admin_people.py:207-291` (`test_update_person_partial_patch_does_not_wipe_other_fields`)

**Issue:** `update_person`'s `death_date` guard (`api/services/admin_people.py:557-568`)
explicitly cites "39-RESEARCH.md Pitfall 5" — the exact same silent-wipe
failure mode this integration test exists to catch for `birthdate`,
`first_name`, and `last_name`. The schema-level unit test
(`test_admin_people_schemas_service.py::test_person_update_photo_bio_payload_never_touches_death_date`)
only checks `model_fields_set` in isolation; it never exercises the real
`update_person` service function or a real PATCH round-trip through the API,
so a regression in the `"death_date" in fields_set` guard (e.g. someone
"fixing" it to `is not None` the way CR-02 was accidentally reverted per the
comment at `api/services/admin_people.py:494-499`) would not be caught by
any DB-backed test.

**Fix:** Extend `test_update_person_partial_patch_does_not_wipe_other_fields`
to set `death_date` alongside `birthdate` in the identity PATCH, then assert
it survives the bio-only PATCH and the reverse-direction identity-only PATCH,
mirroring the existing `birthdate` assertions.

## Info

### IN-01: `reason_left_title()` is dead code — zero production callers, duplicating a title map that's independently maintained in the frontend

**File:** `api/models/models.py:195-205`

**Issue:** `reason_left_title()` is documented and tested
(`api/tests/test_tenure_reason_left.py`) as the exhaustive canonical ->
formal-title projection for `reason_left`, explicitly modeled on
`office_title()`. Unlike `office_title()`, which has real backend callers
(`api/services/admin_people.py:915`, `api/services/speakers.py:90,102`),
`reason_left_title()` has no callers anywhere in `api/` or `pipeline/` — the
raw canonical value is carried end-to-end to the client (by design, per the
`TenureEntry.reason_left` docstring), and the formal-title projection is
reimplemented independently in `SpeakerPopover.svelte`'s `REASON_LEFT_TITLES`/
`reasonLeftTitle()`. This is consistent with the stated "projection happens
at the render boundary" design, but it leaves an unused, untriggered function
in the backend whose only purpose today is to be a comment-referenced mirror
for the frontend copy — a future edit to `REASON_LEFT_TITLES` in one file
with no shared source of truth (unlike `VALID_REASONS_LEFT`, which the
frontend doesn't reference at all) can silently drift from the other.

**Fix:** Either remove `reason_left_title()` (the popover is the only
current consumer and it's already implemented client-side), or add a
regression test asserting the two `REASON_LEFT_TITLES` dicts (Python and the
Svelte component's) stay in sync, the same way
`test_tenure_write_reason_left_matches_valid_reasons_left_set` already does
for the value set.

### IN-02: Redundant `or None` on an already-`Optional[Literal]`-typed field

**File:** `api/services/admin_people.py:173`

**Issue:** `reason_left=t.reason_left or None` implies `t.reason_left` could
be a falsy non-`None` value (e.g. `""`), but `TenureWrite.reason_left` is
`Optional[Literal["retired", "died", "promoted"]]` — Pydantic has already
rejected any value other than `None` or one of the three literals by the
time this line runs (confirmed by
`test_tenure_write_rejects_non_canonical_reason_left`, which includes `""`
in its rejected-values list). The `or None` here is unreachable dead logic
that reads as if it's normalizing something it can never actually receive,
unlike the genuinely-needed `appointed_by or None` /
`appointing_president_party or None` on the same lines (those fields are
plain `Optional[str]`, so an empty string is a real possible input).

**Fix:** `reason_left=t.reason_left,` (drop the `or None`), or add a comment
clarifying why the redundancy is kept.

---

_Reviewed: 2026-07-29T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
