# Cross-Phase UAT Audit — Closure Record

**Date:** 2026-08-18
**Command:** `/gsd-audit-uat`
**Scope:** all 18 `*-UAT.md` / `*-VERIFICATION.md` / `deferred-items.md` files across 15 phases (v1.0–v1.7)
**Result:** 72 outstanding items → 8, all of them facets of one open finding
**Follow-up same day:** operator waived the remaining human UAT; see § 3 and § 4

Precisely: **60 of the original 72 closed** by the audit itself (38 deferred-item bullets, 13
human-verification items, 6 UAT gaps, 1 UAT test block, 2 parser false positives). Of the 12
originals left open, 1 was then verified and 5 waived by operator decision the same day, leaving
**6 — every one a bullet of the single `delete_argument` cascade finding**, now folded into Phase 48.
The query reports 8 rather than 6 because the audit added two tracking bullets to that finding (a
re-confirmation and a Phase 48 pointer) and the parser counts every top-level bullet as an item.

Every item closed by this audit carries `status: resolved` plus a `resolution:` field in the file it
lives in — the per-phase file stays the source of truth. This note is the consolidated record those
resolutions point back to.

---

## Method

1. Ran `gsd-tools query audit-uat --raw` for the item inventory (72 items, 18 files, 15 phases).
2. Cross-referenced every item against current source.
3. Ran the full test suite twice as evidence: once with the default environment, once with `node` on
   PATH and `-rs` to expose skip reasons.
4. Closed only what could be shown closed. Anything still open was left open, and two items were
   *re-opened* in effect by being confirmed still-live.

All three runs used `-p no:randomly` for a deterministic file order. The final run's command was:

```
PATH="<nvm-node>/bin:$PATH" ./.venv/bin/python -m pytest -q -p no:randomly -rs
```

`-rs` printed no SKIPPED lines at all, which is the point: before this audit that same invocation
reported 6 skips from `test_published_gate.py`, and without `node` on PATH it reported 4 more from
`test_phase38_people_ui_contract.py`. The rootdir `conftest.py` row-count tripwire passed, confirming
the shared dev DB was not mutated and that `publish_state_arguments`' teardown removes its rows.

## Test-suite baselines

| Run | Result |
|-----|--------|
| Before the audit's fixes, default env | 4 failed, 1035 passed, 10 skipped, 5 xfailed |
| Before the audit's fixes, `node` on PATH, `-rs` | 4 failed, 1039 passed, 6 skipped, 5 xfailed |
| After the audit's fixes (N-1, N-2), `node` on PATH | **1049 passed, 5 xfailed, 0 failed, 0 skipped** |

The remaining 5 xfailed are the never-implemented stubs tracked below.

---

## What closed, and why

### The bulk: ~35 "pre-existing DB-gated test failure" deferrals (Phases 25, 26, 28, 29, 31)

Five phases independently logged the same class of failure — tests that passed when run scoped but
failed when the whole suite was collected in one process, with `RuntimeError: Database session
factory is not initialised`, `NotNullViolationError`, `UniqueViolationError`, and fixed-ID collisions
against the corpus-scale dev DB. Each phase correctly logged it as out of scope and moved on. Nobody
came back.

Two later phases fixed the root cause without closing the records:

- **Phase 31** put the suite on a dedicated `scotus_test` database via `TEST_DATABASE_URL`.
- **Phase 46** moved `conftest.py` to the pytest rootdir so the redirect fires for *every* invocation
  shape, not just the ones that happen to include `tests/` in the collected paths.

All of these tests now pass. Phase 29's entries additionally referenced names that Phase 47's
`pipeline_run` → `import_run` re-model has since renamed (`test_pipeline_run.py` →
`test_import_run.py`, `test_ingest_creates_pipeline_run` → `test_ingest_creates_import_run`).

### UAT gaps closed by later phases

| Phase | Gap | Closed by |
|-------|-----|-----------|
| 07 | Auto-matched HIT rows need a single Change button; typeahead must list all people | Phase 44 deleted the Confirm/Correct disposition state machine outright and replaced it with an always-rendered searchable combobox over the full people list (`ResolveCard.svelte:15-17`) |
| 07 | "Add new person" flashed *Saving…* then silently failed | Phase 25 CR-01; human-retested in 25-UAT Test 1, pass, 2026-07-07 |
| 07 | Unresolved cases appeared in `/cases` with `Pending review (job 3)` placeholder titles | The `published_at` gate in `api/services/cases.py` (D-06), re-verified as Phase 45 truth 1 |
| 08 | No resolved-participants section on a completed job | Section renders again (`[job_id]/+page.svelte:407-419`), but deliberately as a count + "Review people" link — per-participant detail moved to the Resolve card (Phase 25 design). Closed as superseded, not as-written |
| 11 | Unpublishing did not hide an argument at its direct `/cases/{slug}` URL | Phase 45, BUG-01 |
| 39 | Popover scrollbar rendered outside the card boundary | Phase 45, BUG-02 — via an operator-approved revision that scoped scrolling to the bio paragraph rather than the card |
| 39 | Test 1: `alembic current` names 0024 as head | Reclassified `superseded`; head is now 0026 after Phases 44 and 47 |

### Human verification never formally closed

`01`, `03` and `11-VERIFICATION.md` all sat at `status: human_needed` while the work had in fact been
verified by a human and recorded elsewhere — 03's five items map 1:1 onto `03-HUMAN-UAT.md`
(`status: complete`, 5/5 pass) and 11's three onto `11-UAT.md` Tests 1–3. This is precisely the
failure mode PROJECT.md's Phase 40.1 process concern warns about: a status field left stale after the
closing work lands outside the original phase. All three flipped to `passed` with the mapping
recorded in-file.

`04-VERIFICATION.md` was a genuine partial: 3 of its 5 items are covered by `04-UAT.md` (8/8 pass),
and 2 have never been run. It stays `human_needed` with the array trimmed to those 2.

### Parser false positives

`25-UAT.md` carried two out-of-scope feedback bullets inside an HTML comment. A commented-out bullet
list still parses as `## Gaps`-shaped entries, so they surfaced as phantom open items. Both had in
fact been routed and delivered (the Archived badge in Phase 26; the Resolve-table rework as SEED-001
→ Phase 44). Rewritten as an explicit resolved record.

---

## What is still open

### 1. `delete_argument` omits `argument_status_log` — folded into Phase 48

`api/services/admin_arguments.py::delete_argument` cascades Utterance → ImportRun →
ArgumentParticipant → CaseArgument → NULL `AdminJob.argument_id` → Argument, with no
`ArgumentStatusLog` step. That FK is NOT NULL with no `ondelete` clause (`api/models/models.py:507`,
migration `0012_unpublished_enum_and_status_log.py:75`), so PostgreSQL applies RESTRICT — and
`approve_job` writes an `ArgumentStatusLog(DRAFT)` row for every argument it creates
(`api/services/admin_jobs.py:591`). Every approve-created DRAFT therefore carries a status-log row,
and the Danger Zone delete on `/admin/arguments/[id]` should raise `ForeignKeyViolation`.

Found in Phase 31 (Plan 31-04) and open ever since. Re-confirmed by reading current source, **but
still not reproduced live** — this audit had no database access, so treat it as static analysis until
someone reproduces it. Note also that `scripts/delete_fixture_argument.py:25` asserts "a DRAFT
argument can never have one", which is wrong and is plausibly why the gap survived three milestones.

Now explicit Phase 48 scope (ROADMAP.md → Phase 48 → "Carried defect folded in 2026-08-18").

### 2. Five never-implemented `xfail(strict=True)` stubs — Phase 31

`test_resolve_alias_hit`, `test_resolve_interactive_prompt`, `test_resolve_resumes_after_interrupt`,
`test_seed_creates_justices`, `test_seed_idempotent`. Every body is `pytest.fail("not implemented")`
behind `xfail(strict=True)`, so the suite reports 0 failures and the gap is invisible. They are
exactly the full suite's `5 xfailed`. This is real test-authoring work — a mocked interactive
`input()` flow, a resume-after-interrupt DB scenario, and full seed-aliases integration coverage.

**This item was mis-classified as stale in the audit's first pass** and is called out here because
reading the file rather than trusting the summary is what caught it.

### 3. Four UAT items still genuinely testable — RESOLVED SAME DAY (1 verified, 3 waived)

The operator elected to skip the outstanding human UAT and move to Phase 48. Disposition:

| Phase | Item | Outcome |
|-------|------|---------|
| 07 | Test 14 — `ingest --help` lists `--job-id` and `--spaces-key`; `parse`/`resolve` list `--job-id` | **PASS**, verified automatically — ran all three via the project venv, all flags present. The original `blocked` state was an unactivated venv in the test terminal, never a defect |
| 07 | Test 13 — failed-state error panel | **WAIVED**, not verified. Needs a deliberately failed live run; re-test with the PDF path at Phase 50 |
| 26 | Test 26 — unresolved-advocate placeholder + Save gate | **WAIVED**, not verified. Code confirmed present (`admin/arguments/[id]/+page.svelte:497,544`) but never exercised in a browser. Its original deferral pointed at a rework that landed elsewhere, so it was never going to resolve itself. Natural fit for Phase 49 |
| 14 | Test 8 — non-resolved utterance has no popover trigger | **WAIVED**, not verified. Unverifiable without an argument containing an unresolved speaker, which has never been available |

### 4. Phase 04 — two accessibility checks never run — WAIVED SAME DAY

Also waived by the operator, recorded via `04-VERIFICATION.md`'s `overrides` block (the project's
existing mechanism for an operator-accepted unverified must-have, same shape Phase 45 used), so
`status: passed` does not imply either check happened:

1. Screen-reader walkthrough (NVDA/JAWS/VoiceOver) — never run. No AT has ever been pointed at this
   codebase.
2. axe-core or WAVE scan — never run. Contrast was only ever checked by reading hex tokens in source.

This is an accepted risk on a phase whose goal is WCAG 2.1 AA compliance, and it is carried in
STATE.md's Blockers/Concerns rather than closed silently. The durable fix is automation, not a human
checklist: an axe-core assertion in a browser test would cover item 2 permanently and cost no
operator time. Phase 51 reworks this UI and is the natural home for it.

---

## Findings recorded in no existing file

### N-1 — 4 red tests in full-suite order (FIXED in this audit)

`api/tests/test_phase44_argument_role_roundtrip.py::test_resolve_row_update_accepts_each_dropdown_value_and_coerces_enum`
failed for all 4 params with `isinstance(<SideEnum.UNKNOWN>, SideEnum)` → False, while passing in
isolation. Two-file repro:

```
pytest tests/test_admin_router.py api/tests/test_phase44_argument_role_roundtrip.py   → 4 failed, 16 passed
pytest api/tests/test_phase44_argument_role_roundtrip.py                              → 9 passed
```

`tests/test_admin_router.py::test_api_main_imports_without_error` purges and re-imports every `api.*`
module mid-session (`tests/test_admin_router.py:219-224`). `ResolveRowUpdate` was bound at module
import and holds the *old* `SideEnum`; the test's function-local
`from api.models.models import SideEnum` gets the *new* one. Values stay equal (str-enum equality is
by value) but `isinstance` fails.

This is the same hazard `pipeline/tests/test_resolve.py:100-118` documents for `ImportRun` (Phase 31,
T-31-19); the Phase 44 test simply didn't adopt that pattern. Fixed by resolving the enum from
`ResolveRowUpdate.model_fields["side"].annotation` — the class the model actually coerces to —
instead of a fresh import. Test-harness artifact, never a production defect.

### N-2 — Phase 45's BUG-01 integration tests were silently skipping (FIXED in this audit)

All 6 live tests in `api/tests/test_published_gate.py` skipped with "No unpublished argument found in
the configured DB — seed data required for this integration test." The helper discovered rows in the
configured database, which worked when the suite ran against the dev DB (Phases 41/43 had seeded
publish-state variety) but not after Phases 31/46 moved it onto `scotus_test`.

45-VERIFICATION.md cites "`TestPublishedGate` (4 tests, all pass)" as evidence for BUG-01 truth 1. In
the current test-DB state that evidence was not executing. A publish gate is a public-exposure
control, so this was fixed rather than documented: a `publish_state_arguments` fixture now seeds one
published (with a linked lead Case, required by `get_argument_with_utterances`) and one unpublished
argument, commits them, and deletes them in teardown — the same seed-commit-then-delete pattern
`test_phase44_argument_role_roundtrip.py` already uses. 13 passed / 6 skipped → 19 passed / 0
skipped.

### N-3 — a skip guard masks the item it replaced (OPEN, carried in STATE.md)

The 4 `test_phase38_people_ui_contract.py` node tests skip with "node is not available in this
execution environment" whenever pytest runs outside an nvm shell, which is the default here. With
`node` on PATH the file is 23 passed / 0 failed, which is what let backlog 999.10 be closed as
verified-fixed. But the guard means a genuine regression in that TypeScript/Python parity contract
would be invisible. Worth either making `node` availability explicit in the test invocation or
failing loudly when it is missing.

---

## Files changed by this audit

**Records closed in place** (each with `status: resolved` + evidence):
`25/26/28/29/31/43/44 deferred-items.md`, `07/08/11/25/39-UAT.md`,
`01/03/11-VERIFICATION.md` (status → `passed`), `04-VERIFICATION.md` (trimmed to the 2 open items).

**Planning updates:** `.planning/ROADMAP.md` (Phase 48 carried defect; backlog 999.10 removed),
`.planning/STATE.md` (deferred rows, blocker re-pointed at Phase 48, audit record, two new
open-item rows).

**Code fixes:** `api/tests/test_phase44_argument_role_roundtrip.py` (N-1),
`api/tests/test_published_gate.py` (N-2).

No production source was modified — the one production defect found (`delete_argument`) was folded
into Phase 48 for planning rather than fixed opportunistically, since it is a service-layer cascade
on an operator-reachable destructive path and deserves the regression test Phase 31 specified.

---

## Final state

| | |
|---|---|
| Audit query | 8 items, all bullets of the one `delete_argument` finding, owned by Phase 48 |
| Test suite | 1049 passed, 5 xfailed, 0 failed, 0 skipped |
| Human UAT queued | none — 1 verified automatically, 5 waived |
| Open code defect | 1 (`delete_argument` cascade), folded into Phase 48 |
| Known unmeasured risk | Phase 04 accessibility (no AT walkthrough, no axe scan) — carried in STATE.md |
| Test-coverage gap | 5 never-implemented `xfail(strict=True)` stubs from Phase 31 — carried in STATE.md |

Next action: `/gsd-discuss-phase 48`.
