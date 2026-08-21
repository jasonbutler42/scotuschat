---
phase: 48-trust-lifecycle
reviewed: 2026-08-21T14:41:36Z
depth: standard
files_reviewed: 49
files_reviewed_list:
  - alembic/versions/0027_trust_tier_and_candidate_status.py
  - api/domain/trust.py
  - api/models/models.py
  - api/routers/admin.py
  - api/schemas/admin_arguments.py
  - api/schemas/admin_people.py
  - api/services/admin_arguments.py
  - api/services/admin_dev.py
  - api/services/admin_jobs.py
  - api/services/admin_people.py
  - api/services/arguments.py
  - api/services/cases.py
  - api/services/speakers.py
  - api/services/trust.py
  - api/tests/test_admin_arguments_routes.py
  - api/tests/test_admin_arguments_service.py
  - api/tests/test_admin_dev_routes.py
  - api/tests/test_admin_jobs_list.py
  - api/tests/test_admin_jobs_phase25.py
  - api/tests/test_admin_jobs_service.py
  - api/tests/test_argument_oyez_field.py
  - api/tests/test_arguments.py
  - api/tests/test_phase44_argument_role_roundtrip.py
  - api/tests/test_phase48_detail_publish_error_rendering_contract.py
  - api/tests/test_phase48_list_publish_override_ui_contract.py
  - api/tests/test_phase48_publish_override_ui_contract.py
  - api/tests/test_phase48_unpublish_visibility.py
  - api/tests/test_published_gate.py
  - api/tests/test_speakers_service.py
  - api/tests/test_trust_domain.py
  - api/tests/test_trust_public_leak_ban.py
  - api/tests/test_trust_recompute.py
  - api/tests/test_trust_tracer.py
  - app/src/routes/admin/arguments/+page.server.ts
  - app/src/routes/admin/arguments/+page.svelte
  - app/src/routes/admin/arguments/[id]/+page.server.ts
  - app/src/routes/admin/arguments/[id]/+page.svelte
  - app/src/routes/admin/pipeline/[job_id]/+page.server.ts
  - pipeline/__main__.py
  - pipeline/commands/import_convokit.py
  - pipeline/commands/ingest.py
  - pipeline/commands/parse.py
  - pipeline/commands/recompute_trust.py
  - pipeline/commands/resolve.py
  - pipeline/tests/test_import_convokit_adminjob.py
  - pipeline/tests/test_import_convokit_core.py
  - pipeline/tests/test_import_convokit_utterances.py
  - pipeline/tests/test_recompute_trust.py
  - scripts/delete_fixture_argument.py
findings:
  critical: 1
  warning: 2
  info: 2
  total: 5
resolved:
  critical: 1   # CR-01, commit ac77a8f5f
  warning: 2    # CR-02 39a8fdcba, CR-03 ac77a8f5f
  info: 0       # IN-01/IN-02 intentionally left open (not required this round)
status: critical_and_warnings_fixed
fix_commits:
  - ac77a8f5f  # fix(48): list-page unpublish silently redirected on failure (CR-01, CR-03)
  - 39a8fdcba  # fix(48): correct stale StatusLogEntry ordering docstring (CR-02)
fixed_at: 2026-08-21T15:00:45Z
---

# Phase 48: Code Review Report

**Reviewed:** 2026-08-21T14:41:36Z
**Depth:** standard
**Files Reviewed:** 49
**Status:** issues_found

## Fix Status (2026-08-21T15:00:45Z)

| Finding | Severity | Status | Commit |
|---------|----------|--------|--------|
| CR-01 | Critical | Fixed | `ac77a8f5f` |
| CR-02 | Warning | Fixed | `39a8fdcba` |
| CR-03 | Warning | Fixed | `ac77a8f5f` |
| IN-01 | Info | Open (not required this round) | — |
| IN-02 | Info | Open (not required this round) | — |

CR-01's fix also extended `test_phase48_list_publish_override_ui_contract.py`
with `unpublish`-action coverage (confirmed RED against the pre-fix source
before the fix landed) plus two structural assertions generalizing the
defect class: every `fetch(` call inside every action in either admin
arguments `+page.server.ts` must capture its result into `res`, and every
action that reaches `redirect(...)` must check `res.ok` somewhere in its
body. Both Info items remain open by design — see their own **Fix**
sections below for the (not-required) recommended change.

## Summary

Phase 48's core trust-tier machinery is sound: `derive_tier`/`floor_tier` are pure, total,
and fail-closed; `recompute_argument_tier` is correctly non-committing and called
in-transaction by every writer that was checked (corpus import, ingest, resolve_job,
approve_job, update_resolve_row_for_job, create_person_for_job, publish_argument,
unpublish_argument, update_participant_side, the offline `recompute-trust` CLI) — every
caller traced does commit afterward, and the two writers that re-read the same ORM object
post-commit (`publish_argument`, `unpublish_argument`, `approve_job`) correctly call
`db.refresh()` to avoid the stale-identity-map bug Phase 31 already fixed once. The
two-gate publish order (`resolved_at` gate strictly before the overridable trust gate) is
correctly implemented and matches D-14. The apolitical hard constraint holds: no
`trust_tier` leak was found in `cases.py`/`arguments.py`/`speakers.py`, their schemas, or
any public router, and `test_trust_public_leak_ban.py` is a genuinely well-built structural
contract (derives the public model set from the live routers rather than a hardcoded list).
Migration 0027's five-step ordering and its downgrade path are both correct.

One genuine, previously-unrecorded regression was found: the **list page's `unpublish`
form action never checks the response status and always redirects as if it succeeded**,
even when the backend rejects the unpublish (422) or the request otherwise fails — silently
telling the operator an action succeeded when it did not. This is the same defect class
(D-19's "operator needs to see why") that plan 48-10 explicitly found and fixed twice
elsewhere on this same page pair (detail-page publish, then detail-page unpublish by
inspection) — but the list page's own `unpublish` action was never given the parity fix,
and no test exercises its failure path (confirmed: zero references to `unpublish` in
`test_phase48_list_publish_override_ui_contract.py`, the file that owns this page's
contract coverage). This is the review's one BLOCKER.

Two warnings and two info items round out the findings — a stale docstring describing an
ordering rule that was deliberately changed elsewhere in this same phase (ironic given
Finding 2's whole point was to fix exactly this kind of created_at/id mismatch), and a
couple of minor quality notes.

## Critical Issues

### CR-01: List-page `unpublish` action silently reports success on failure

**Fixed:** commit `ac77a8f5f`. See "Fix Status" above.

**File:** `app/src/routes/admin/arguments/+page.server.ts:141-155`
**Issue:**

```ts
unpublish: async ({ request, fetch }) => {
    const formData = await request.formData();
    const argument_id = formData.get('argument_id') as string;

    try {
        await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/unpublish`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch (err) {
        console.error('[arguments unpublish] fetch threw:', err instanceof Error ? err.message : String(err));
    }

    throw redirect(303, '/admin/arguments');
},
```

The response (`res`/the fetch's return value) is never captured or checked — `res.ok` is
never examined and the function unconditionally `throw redirect(303, ...)`s regardless of
whether the backend call succeeded, returned a 4xx/5xx, or the fetch threw. Every other
mutating action on this page and its sibling detail page checks `res.ok` and returns
`fail(...)` on failure:

- This same file's own `publish` action (lines 72-136) checks `res.ok` and returns a
  tagged `fail(422, { argumentId, error: ... })` on every non-2xx branch.
- The detail page's `unpublish` action
  (`app/src/routes/admin/arguments/[id]/+page.server.ts:426-442`) — the fix plan 48-10's
  own SUMMARY documents fixing for exactly this defect class ("Detail-page unpublish
  errors had the identical defect") — checks `res.ok` and returns
  `fail(422, { source: 'unpublish', error: ... })`.

Concretely, `unpublish_argument` (`api/services/admin_arguments.py:793-834`) raises
`ValueError("Not currently published")` whenever `argument.status != PUBLISHED` at the
moment the request lands (e.g. a second admin tab/operator already unpublished it, or the
list page's cached row is stale) — the router maps that to a 422
(`api/routers/admin.py:1216-1219`). With the current code, that 422 is swallowed entirely:
no `console.error`, no `fail()`, nothing — the operator is redirected back to
`/admin/arguments` with zero indication the unpublish did not happen, and (worse) the row
may still visually read "Published" with an "Unpublish" control that appears to have just
been clicked successfully.

This is not a hypothetical: the exact same silent-redirect-on-failure shape was found and
fixed twice already in this same plan (48-10) — once live by the operator (detail-page
publish), once by inspection immediately afterward (detail-page unpublish) — but the fix
was never propagated to this page's own `unpublish` action, which still has the pre-fix
shape verbatim. No test in `test_phase48_list_publish_override_ui_contract.py` (the file
that owns this page's static contract coverage — 20 tests, none touching `unpublish`)
would have caught this, since it only tests the `publish` action and the render template.

**Fix:**

```ts
unpublish: async ({ request, fetch }) => {
    const formData = await request.formData();
    const argument_id = formData.get('argument_id') as string;
    const argumentId = Number(argument_id);

    let res: Response;
    try {
        res = await fetch(`${FASTAPI_BASE_URL}/api/admin/arguments/${argument_id}/unpublish`, {
            method: 'POST',
            headers: { 'X-Admin-Token': ADMIN_TOKEN },
        });
    } catch {
        return fail(502, { argumentId, error: 'Could not unpublish this argument. Try again.' });
    }

    if (!res.ok) {
        return fail(422, { argumentId, error: 'Could not unpublish this argument. Try again.' });
    }

    throw redirect(303, '/admin/arguments');
},
```

This also needs a rendering home in `+page.svelte` — the existing
`{#if form?.error && form.argumentId === arg.id && !form.publishBlocked}` block
(`app/src/routes/admin/arguments/+page.svelte:442-457`) already renders a bare `form.error`
per-row and does not gate on `form.source`, so the fix above will render through that
existing block without further template changes (the list page never adopted the
`source`-tag discriminator the detail page uses, because until now it only had one action —
`publish` — that ever populated `form.error`; this fix gives it a second one that shares the
same untagged `error` key, which is safe today but worth flagging: a future third action on
this page returning `error` would silently collide, exactly as `source`-tagging was
introduced elsewhere in this same plan to prevent). A regression test mirroring
`test_phase48_list_publish_override_ui_contract.py`'s existing style (source-level
assertion that the `unpublish` action checks `res.ok` before redirecting, plus a live
DB-gated 422 case) should be added alongside the fix.

## Warnings

### WR-01: Stale docstring still describes the ordering `get_argument_detail` no longer uses

**Fixed (as CR-02):** commit `39a8fdcba`. See "Fix Status" above.

**File:** `api/schemas/admin_arguments.py:61-62`
**Issue:**

```python
class StatusLogEntry(BaseModel):
    """One ArgumentStatusLog row (Phase 26, T-26-03).

    Surfaced on the argument edit page's Status history list, ordered
    oldest-first by get_argument_detail's query (created_at asc, id asc tiebreak).
```

`get_argument_detail`'s actual query (`api/services/admin_arguments.py:458-462`) was
deliberately changed by this same phase (48-09's Finding 2 fix, documented at length in
that function's own inline comment) to order by `ArgumentStatusLog.id.asc()` alone —
`created_at` is no longer part of the sort key at all, specifically *because* it can be
stale relative to `id` (PostgreSQL's `now()` returns transaction-start time, not
per-statement time). This docstring was not updated to match and now asserts the opposite
of what the code does — a future reader trusting this docstring over the service function's
own (correct) comment could reintroduce the exact ordering bug Finding 2 just fixed.
**Fix:**
```python
    Surfaced on the argument edit page's Status history list, ordered
    oldest-first by get_argument_detail's query (ArgumentStatusLog.id.asc() —
    id, not created_at, is the sort key; see that function's own comment for why).
```

### WR-02: List-page `unpublish` `<form>` has no submitting/disabled state

**Fixed (as CR-03):** commit `ac77a8f5f`. See "Fix Status" above.

**File:** `app/src/routes/admin/arguments/+page.svelte:409-425`
**Issue:** The `Unpublish` button uses bare `use:enhance` with no callback, unlike every
other mutating control on this page (`Publish`, both instances, both track
`publishingId`/disable the button and show "Publishing…" while in flight). A double-click
or slow network round-trip can submit the unpublish action twice before the first
`use:enhance` navigation completes. This is a pre-existing pattern gap rather than a new
defect this phase introduced, but it is directly adjacent to CR-01's fix — implementing
CR-01 without addressing this leaves a fixed error-surfacing path that a double-submit can
still race against. Low severity because the backend's own guard (`status != PUBLISHED`)
makes a double-unpublish harmless (the second call just gets the "Not currently published"
422 CR-01's fix will now correctly surface, rather than corrupting state).
**Fix:** Mirror the `Publish` button's `publishingId`-gated disabled/label pattern on this
same page for consistency, once CR-01 lands.

## Info

### IN-01: `TrustGateBlocked.code` class attribute is dead — the router hardcodes the same string separately

**File:** `api/services/trust.py:46` and `api/routers/admin.py:1168`
**Issue:** `TrustGateBlocked` defines `code = "uncertain_tier_blocked"` as a class
attribute, documented as carrying the structured code for the router to use. But
`api/routers/admin.py`'s `except TrustGateBlocked as exc:` handler
(`api/routers/admin.py:1164-1177`) never reads `exc.code` — it hardcodes the literal string
`"uncertain_tier_blocked"` directly in the response dict instead. The two strings are
consistent today, but nothing enforces they stay that way if either is edited independently
— the whole point of defining `code` on the exception class is defeated if no caller reads
it.
**Fix:** `"code": exc.code,` instead of the literal in `api/routers/admin.py:1168`.

### IN-02: `blank_override_reason`'s tagged-`ValueError` dispatch pattern is fragile to message drift

**File:** `api/services/admin_arguments.py:677` / `api/routers/admin.py:1178-1190`
**Issue:** The router distinguishes the blank-reason case from the two pre-existing
plain-string `ValueError`s inside one `except ValueError as exc:` block by testing
`str(exc) == "blank_override_reason"`. This is documented as deliberate (Python cannot
register two `except` clauses for the same concrete exception type) and is reasonable given
that constraint, but it means any future edit to either the resolve-gate message
(`"Cannot publish: resolve step not yet complete"`) or the already-published message
(`"Already published"`) to literally read `"blank_override_reason"` (vanishingly unlikely,
but the point stands) would silently misroute. A small, more robust alternative — a
dedicated `BlankOverrideReasonError(ValueError)` subclass caught before the bare
`ValueError`, the same pattern already used for `TrustGateBlocked` itself one line above —
would remove the string-matching indirection entirely and is a very small change.
**Fix:** Not required, but worth adopting the pattern this file already uses one exception
class earlier in the same function.

---

_Reviewed: 2026-08-21T14:41:36Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
