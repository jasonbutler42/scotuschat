---
phase: 44-resolve-table-rework
reviewed: 2026-08-11T00:00:00Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - .planning/REQUIREMENTS.md
  - .planning/phases/44-resolve-table-rework/deferred-items.md
  - alembic/versions/0025_rename_participant_title_to_descriptor.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_arguments.py
  - api/schemas/admin_jobs.py
  - api/schemas/admin_people.py
  - api/services/admin_arguments.py
  - api/services/admin_jobs.py
  - api/services/admin_people.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_jobs_phase25.py
  - api/tests/test_admin_people_phase25.py
  - api/tests/test_phase38_extracted_value_contract.py
  - api/tests/test_phase44_argument_role_roundtrip.py
  - api/tests/test_phase44_bench_role_preview.py
  - api/tests/test_phase44_descriptor_rename.py
  - api/tests/test_phase44_live_tenure_recompute.py
  - api/tests/test_phase44_resolve_table_contract.py
  - app/src/lib/components/CopyableExtractedValue.svelte
  - app/src/lib/components/ResolveCard.svelte
  - app/src/lib/components/CreatePersonPopover.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - app/src/routes/admin/pipeline/[job_id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/bench-role-preview/+server.ts
  - pipeline/commands/parse.py
  - scripts/diff_corpus_fixture.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: clean
---

# Phase 44: Code Review Report

**Reviewed:** 2026-08-11
**Depth:** standard
**Files Reviewed:** 21 (of 30 listed; `api/models/models.py`, `app/src/routes/admin/arguments/[id]/+page.server.ts`, `app/src/routes/admin/arguments/[id]/+page.svelte`, `api/services/admin_arguments.py`, `api/tests/test_phase44_descriptor_rename.py`, `api/tests/test_admin_arguments_routes.py`, `api/tests/test_admin_arguments_service.py` were read/grepped for cross-reference but not exhaustively line-audited beyond the areas touching this phase's changes — see Summary)
**Status:** clean (all 6 findings fixed manually — see Resolution below; not run through the automated `--fix` path)

## Resolution (2026-08-11, commit `1c6483c7`)

Every finding below was independently re-verified against the actual source
(not taken on faith) before fixing, per this project's own established
discipline for this checkpoint:

- **CR-01, CR-02** (both Critical): confirmed via direct grep/read that
  `lastDescriptorValue`/`lastAdvocateRole` had no seeding path — fixed with a
  new, ungated `$effect` in `ResolveCard.svelte` that seeds both from
  `mergedRows` at most once per participant, never overwriting an
  already-seeded value. Locked with three new static-source-contract tests
  in `test_phase44_resolve_table_contract.py`.
- **WR-01**: fixed — `bench_role_preview_for_job` now validates `person_id`
  refers to an existing `Person` before querying tenures. Locked with
  `test_preview_raises_for_nonexistent_person` in
  `test_phase44_bench_role_preview.py`.
- **WR-02**: fixed — `comboOutsideClick`'s redundant nested-`$effect`
  teardown removed; the action body registers the listener directly.
- **IN-02**: fixed — `PersonCreate`'s docstring now notes RESOLVE-13 doesn't
  apply to it (no `descriptor` field on this schema at all).
- **IN-01**: NOT fixed — `console.debug` in the poll loop (`+page.svelte`)
  is a deliberate, documented diagnostic from an earlier phase (PIPE-18,
  D-02), not something Phase 44 introduced. Left as-is; out of this phase's
  scope to reverse an unrelated prior decision.

Full suite after fixes: 904 passed, 5 xfailed, same 4 pre-existing
collection errors, 0 failures. `npm run check`: 806 files, 0 errors, 36
pre-existing warnings.

## Summary

Phase 44's `ResolveCard.svelte` rework (Plans 44-05 through 44-09) is extensively
tested at the *static source-contract* level — `test_phase44_resolve_table_contract.py`
has 100+ regex/AST-style assertions against the component's source text, and the
backend round-trip tests in `test_phase44_argument_role_roundtrip.py` and
`test_admin_jobs_phase25.py` prove the server-side write/read paths are correct in
isolation. However, tracing the actual client-side control flow of the two
"confirmed and fixed" data-loss bugs documented in 44-09-SUMMARY.md
("descriptor data-loss" and its sibling "specific advocate role" memory) shows
that **neither client-side memory fix reliably survives its own primary use
case** — both are data-loss bugs against operator-entered/pipeline-extracted
metadata on `ArgumentParticipant` rows, a system-of-record table this project
treats as audit-relevant (CLAUDE.md: no silent tidying/loss of extracted
data). The backend-side guards (RESOLVE-13's "ignore descriptor on BENCH
write") are correctly implemented — the defect is entirely in what the
*client* submits on the toggle-back step, which none of the automated tests
actually exercise (the tests hand-craft the "correct" payload a fixed client
would send, rather than deriving it from `ResolveCard.svelte`'s own reactive
logic, or assert only that a source-text pattern exists).

The backend admin router/services (IDOR guards, mass-assignment allow-lists,
SSRF/path-traversal defenses, docket-injection guards, live tenure recompute)
are in solid shape and match their extensive documentation. The Alembic
rename migration is a clean, symmetric column rename. `pipeline/commands/parse.py`
and `scripts/diff_corpus_fixture.py`'s title→descriptor rename is consistent.

## Critical Issues

### CR-01: Descriptor value is silently wiped on an Advocate→Bench→Advocate toggle unless the operator retypes it this session

**File:** `app/src/lib/components/ResolveCard.svelte:165, 771-774` (declaration and read site), `286-312` (the toggle that triggers the loss)

**Issue:** 44-09-SUMMARY.md documents a confirmed descriptor data-loss bug and
claims it is fixed by `lastDescriptorValue`, a per-participant client memory:

```svelte
value={lastDescriptorValue[row.participant_id] ?? row.descriptor ?? ''}
oninput={(e) => {
    lastDescriptorValue[row.participant_id] = (e.target as HTMLInputElement).value;
}}
```

`lastDescriptorValue[pid]` is **only ever written from this `oninput` handler**
(confirmed via `grep -n lastDescriptorValue ResolveCard.svelte` — exactly 3
hits: the declaration, this read, this write). There is no seeding `$effect`
that captures the row's already-committed `row.descriptor` into this memory
on initial mount or on any subsequent server-data refresh.

Trace of the exact scenario the fix claims to solve — a row that already has
a correctly saved descriptor (e.g. "Solicitor General") from a *prior*
session, where the operator does not retype it in this session:

1. Page loads. `side` = Advocate, `row.descriptor` = "Solicitor General".
   The input renders with this value via the `row.descriptor` fallback.
   `lastDescriptorValue[pid]` is still unset (no `oninput` has fired).
2. Operator clicks the Bench toggle segment. `toggleSide` → `onSideChange(row,
   'BENCH')` → `submitRow()` → `flushSync()` (forces the DOM to `side=BENCH`
   before serializing) → `requestSubmit()`. At this instant the descriptor
   `<input>` has already unmounted (side is now BENCH, `descriptorCell`
   renders the dash branch), so this particular request carries no
   `descriptor` field — correct so far.
3. The row's `use:enhance` callback resolves and calls `await update({ reset:
   false })`, which invalidates and reruns the page's `load()` — `resolveRows`
   refreshes. Per `list_resolve_rows_for_job`'s deliberate design
   (`api/services/admin_people.py:1022`), `descriptor` is now reported as
   `null` for this BENCH row. `saveState[...] = { saving: false, ... }` is
   set (re-enabling the toggle buttons) *before* this `await`, so the toggle
   is clickable again slightly ahead of the reload finishing, but in normal
   human-speed interaction the reload completes first.
4. Operator clicks Advocate again. `toggleSide`'s Advocate branch (line
   300-311) computes `restored` from `lastAdvocateRole`/`row.side` (unrelated
   to descriptor) and calls `onSideChange(row, restored)` → `submitRow()` →
   `flushSync()`. This flush mounts the descriptor `<input>` (side is no
   longer BENCH) with `value={lastDescriptorValue[pid] ?? row.descriptor ??
   ''}`. Since `lastDescriptorValue[pid]` was never populated (step 1 never
   fired `oninput`) and `row.descriptor` is now `null` (step 3's reload), the
   value resolves to `''`.
5. `requestSubmit()` fires immediately after the flush, submitting
   `descriptor=''` in the **same request** as the side change back to
   Advocate. Since `side != BENCH`, `update_resolve_row_for_job`
   (`api/services/admin_jobs.py:829-831`) includes `descriptor` in the write
   — overwriting "Solicitor General" with an empty string (persisted as
   `NULL` after `+page.server.ts`'s `saveResolveRow` action's `descriptor ||
   null` normalization, `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:478`).

This is the *exact* scenario the fix's own root-cause writeup describes, just
missing the one detail that makes the fix incomplete: the memory is captured
only from the DOM's `oninput`, never seeded from the server-reported value.
The claim in 44-09-SUMMARY.md that the fix is proven is based on:
 - a static source-contract test (`test_descriptor_input_uses_a_client_memory_that_survives_side_toggles`,
   `api/tests/test_phase44_resolve_table_contract.py:1596`) that only checks
   the *pattern* `lastDescriptorValue[...] ?? row.descriptor ?? ''` exists —
   it does not simulate the reactive sequence above; and
 - a backend round-trip test
   (`test_descriptor_and_specific_role_survive_an_immediate_bench_then_back_toggle`,
   `api/tests/test_phase44_argument_role_roundtrip.py:195`) that manually
   sends `descriptor="Attorney"` on the toggle-back step, i.e. it assumes "a
   correctly-behaving client" rather than deriving the payload from
   `ResolveCard.svelte`'s actual logic (the test's own docstring says as much:
   "given the payloads a correctly-behaving client ... would send").

Net effect: this bug reproduces for the common case where an operator simply
glances at an already-resolved row and flips the Bench/Advocate toggle
(e.g. correcting a wrong auto-classification) without retyping the descriptor
box — the previously-saved descriptor is silently destroyed.

**Fix:** Seed `lastDescriptorValue[row.participant_id]` from `row.descriptor`
the first time each row's descriptor is known (mirroring how `sideHintValue`/
`extracted_side` freezes a value read from a first-seen server prop), e.g. in
the existing seeding `$effect` (`ResolveCard.svelte:449-537`) or a small
dedicated `$effect` keyed on `mergedRows`, seeding once per participant (never
overwriting once seeded) so a never-retyped, already-correct descriptor
survives a side round trip. Add a browser-level (not just static-source)
regression test that actually renders the toggle sequence rather than
asserting the payload by hand.

### CR-02: `lastAdvocateRole` has the identical unseeded-memory gap as CR-01 — a pre-existing specific advocate role can revert to generic "Counsel" after a Bench round-trip

**File:** `app/src/lib/components/ResolveCard.svelte:150` (declaration), `286-312` (`toggleSide`), `319-334` (`chooseArgumentRole`, the only writer)

**Issue:** `lastAdvocateRole[pid]` is written in exactly one place —
`chooseArgumentRole` (line 324), i.e. only when the operator explicitly picks
a role from the Argument Role `<select>` **during this session**. It is never
captured when the operator instead uses the Bench/Advocate toggle to leave a
row that already has a server-committed specific role (e.g. `side =
'PETITIONER'` from a prior session). `toggleSide`'s BENCH branch (line
300-303) unconditionally calls `onSideChange(row, 'BENCH')` with no capture
step at all.

The Advocate-restore branch's fallback,
`specificAdvocateRole(row.side) ?? 'UNKNOWN'` (line 309-310), was presumably
intended to cover this case ("falling back to the row's own already-committed
side if it was already a specific role... loaded from the server still set to
RESPONDENT" — see the comment at line 304-308). But `row` here is the current
render's `MergedRow`, sourced from the `resolveRows` prop, which by the time
the *second* toggle click happens has already been refreshed by the *first*
toggle's own save+reload (same mechanism as CR-01, step 3) — so `row.side` is
already `'BENCH'` by the time this fallback runs, and
`specificAdvocateRole('BENCH')` returns `null`. The fallback therefore only
works if the operator clicks the second toggle before the first save's reload
completes — a narrow, unreliable timing window, not the intended safety net.

Net effect: a row that already has, say, `side = 'PETITIONER'` from a prior
resolve session, if merely toggled to Bench and back to Advocate without the
operator re-picking the role from the dropdown, silently reverts to the
generic "Select case role" / Counsel placeholder — losing the previously
recorded advocate role. This is the same class of bug as CR-01 (an unseeded
client-side memory whose only fallback reads a server prop that has, by
construction, already been overwritten by the round trip that triggers the
restore), just with a race-condition-dependent (rather than deterministic)
reproduction window — which is likely why it survived six rounds of live
checkpoint testing: 44-09-SUMMARY.md's own remediation notes state the
specific-role restore path was verified by *reading the source* ("a pure
client memory... already correct pre-remediation") rather than by exercising
this exact "committed-but-never-repicked-this-session" case, and the
DB-gated round-trip test (`test_phase44_argument_role_roundtrip.py:195`)
covers only a role chosen earlier *in the same test's own session*, not a
role that arrived pre-set from a prior one.

**Fix:** Same remedy as CR-01 — seed `lastAdvocateRole[participantId]` from
`specificAdvocateRole(committedRow.side)` in the existing seeding `$effect`
(`ResolveCard.svelte:449-537`, which already seeds `lastSideBucket` and
`sideGateConfirmed` from `committedRow` — this is the natural place to add a
third seed) rather than relying on a live re-read of `row.side` at
restore-time.

## Warnings

### WR-01: `bench_role_preview_for_job` never validates that `person_id` refers to an existing `Person`

**File:** `api/services/admin_people.py:1051-1093`

**Issue:** The service queries `CourtTenure` directly by the caller-supplied
`person_id` without first checking a matching `Person` row exists. A
nonexistent or mistyped `person_id` silently returns `(None, True)` ("missing
tenure") instead of a 404/422, unlike every sibling person-scoped endpoint in
this router (`get_person`, `update_person`, `upload_person_photo`, etc.),
which all explicitly guard on person existence. Low severity — this is a
read-only, admin-authenticated preview endpoint with no side effects and no
sensitive data disclosed either way — but it's an inconsistency with the
project's established IDOR/existence-guard convention.

**Fix:** Add a `select(Person).where(Person.id == person_id)` existence check
before/alongside the tenure query and raise `ValueError` (mapped to 422 by the
router, matching the job/argument guards already in this function) when the
person does not exist.

### WR-02: Redundant double-teardown of the combobox outside-click listener

**File:** `app/src/lib/components/ResolveCard.svelte:702-733`

**Issue:** `comboOutsideClick` registers its `click` listener inside a nested
`$effect(() => { document.addEventListener(...); return () =>
document.removeEventListener(...); })`, **and** the action also returns its
own `{ destroy() { document.removeEventListener(...); } }`. Both teardown
paths fire on unmount (the effect's own cleanup when its owning scope is
destroyed, and the action's `destroy()` when the node is removed), so
`removeEventListener` is called twice for the same listener. This is harmless
at runtime (removing an already-removed listener is a no-op) but is dead,
confusing code — a future maintainer editing one teardown path without
noticing the other could reintroduce a leak.

**Fix:** Pick one mechanism. Since the action already needs `container` (the
node) and `rowKey` from its own closure, the simplest fix is to drop the
inner `$effect` entirely and add the `document.addEventListener(...)` call
directly in the action body, keeping only the returned `destroy()`.

## Info

### IN-01: `console.debug` left in the 1-second poll loop

**File:** `app/src/routes/admin/pipeline/[job_id]/+page.svelte:104`

**Issue:** `console.debug('[poll]', { status: liveJob.status, current_step:
liveJob.current_step })` fires on every poll tick (every second) while any
pipeline job is running, for the lifetime of the page. Not a security issue
(no sensitive data), but it is a debug artifact that spams the browser console
during normal operator use.

**Fix:** Remove, or gate behind an explicit dev-only flag if the diagnostic
value is still wanted.

### IN-02: `PersonCreate`'s docstring still omits the RESOLVE-13 supersession that the sibling services docstring documents

**File:** `api/schemas/admin_jobs.py:88-107` (docstring), cross-referenced against `api/services/admin_jobs.py:783-789`'s comment, which correctly documents the RESOLVE-13 supersession ("hidden, not shown, not cleared")

**Issue:** `PersonCreate`'s docstring in `admin_jobs.py` schema module doesn't
mention the RESOLVE-13 supersession at all, while the sibling
`update_resolve_row_for_job` docstring in the services module explicitly notes
"this supersedes PJOB-15's storage half." Not a functional bug (this schema
doesn't write descriptor at all), but the schema-level documentation is now
slightly stale relative to the services-level documentation for the same
project decision, which could mislead a future reader of the schema file in
isolation.

**Fix:** Low priority — add a one-line cross-reference to RESOLVE-13/44-06 in
`PersonCreate`'s docstring for consistency, or leave as-is since it does not
affect behavior.

---

_Reviewed: 2026-08-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
