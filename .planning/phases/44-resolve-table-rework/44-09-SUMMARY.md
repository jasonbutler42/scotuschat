---
phase: 44-resolve-table-rework
plan: 09
subsystem: ui
tags: [svelte, sveltekit, resolve-card, figma-reconciliation, accessibility, progress-indicator]

# Dependency graph
requires:
  - phase: 44-resolve-table-rework
    provides: "44-05's single personId predicate (allDispositioned) and dropdown-only Resolved As entry point; 44-07's is_justice side-scoped candidates and sourcePrefix; 44-08's benchRoleState and read-only parity — this plan's reviewProgress and rowCueTag both read the same personId/discrepancy signals those plans established"
provides:
  - "reviewProgress — a $derived.by value reading the exact same rowMatchStates[...].personId predicate allDispositioned uses, so the header count and the Continue gate cannot disagree (RESOLVE-15, T-44-36)"
  - "A persistent header progress line, visible whenever the job is paused and the review set is non-empty: 'N of M speakers still need review' / 'All M speakers reviewed'"
  - "An always-visible Continue footer while paused; the button's disabled attribute reads allDispositioned, with a reason line ('Resolve N more to continue') programmatically associated via aria-describedby (T-44-37)"
  - "rowCueTag(row, s) — a named predicate returning 'NEEDS YOU' (checked first, so a suggested-but-gated row still reads as needing the operator), 'AUTO-MATCHED' (only while the current personId still equals the untouched auto_match_id), or null (T-44-35)"
  - "Per-row AUTO-MATCHED/NEEDS YOU cue tags rendered at the top of the Resolved As cell, muted/warning tokens only, no accent, no background fill (RESOLVE-16)"
affects: []

actuals:
  tokens: 4200
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Single shared predicate reused by two consumers: reviewProgress and allDispositioned both read `rowMatchStates[d.raw_speaker_label]?.personId`, the identical field access, rather than each deriving their own copy — this is what makes T-44-36 (a header/gate disagreement) structurally impossible rather than merely tested for"
    - "Derive a rendering-only boolean (cueTagIsWarning) that mirrors a predicate's internal branch condition, instead of re-comparing against the predicate's own string return value at the call site — used here so 'NEEDS YOU'/'AUTO-MATCHED' each appear exactly once in the file (in rowCueTag's own return statements) even though the tag's color needs to fork on which branch produced it"
    - "Omit an explicit return-type annotation on a function returning a small string-literal union when a duplicate-literal-count acceptance criterion would otherwise force writing each literal twice (once in the annotation, once in a return) — TypeScript still infers the correct union type from the return statements"

key-files:
  created: []
  modified:
    - app/src/lib/components/ResolveCard.svelte
    - api/tests/test_phase44_resolve_table_contract.py

key-decisions:
  - "The Continue button's disabled-styling (cursor/opacity) reads reviewProgress.remaining > 0 rather than repeating !allDispositioned a second and third time inside the ?/resolve form region — the two conditions are logically equivalent (proven: disc.length===0 gives allDispositioned=true and remaining=0; disc.length>0 gives allDispositioned=(remaining===0)), and this plan's own acceptance criteria require the literal string 'allDispositioned' to appear exactly once inside that form region (on the disabled attribute itself)."
  - "Reworded two pre-existing code comments (predating this plan) that quoted the literal button label \"Continue Resolve\" — they inflated this task's own grep-count acceptance criterion (expected 1) to 4. Following the precedent set in 44-08-SUMMARY (deviations #2/#3), the comments were reworded to describe the same intent without repeating the literal string; no functional change."
  - "rowCueTag carries no explicit `: 'AUTO-MATCHED' | 'NEEDS YOU' | null` return-type annotation, contrary to the plan's literal action text showing that signature — the annotation would have forced writing each tag literal twice (once in the union, once in a return statement), directly conflicting with the plan's own acceptance criteria requiring each string to appear exactly once in the file. TypeScript infers the identical union type from the two return statements; behavior is unchanged."
  - "The cue tag's color is derived from `cueTagIsWarning = s?.personId == null || gated` (mirroring rowCueTag's own needs-attention branch, reusing the already-declared `gated`) rather than `cueTag === 'NEEDS YOU'`, for the same single-occurrence-per-literal reason above."

requirements-completed: [RESOLVE-15, RESOLVE-16]

coverage:
  - id: T1
    description: "Persistent header progress line and an always-visible, reason-disabled Continue button, both reading the single reviewProgress/allDispositioned personId predicate"
    requirement: "RESOLVE-15"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_progress_copy_present_for_both_states"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_progress_derives_from_the_same_person_id_predicate"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_continue_footer_is_not_gated_on_completeness"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_continue_button_is_disabled_by_completeness_inside_the_form"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_disabled_reason_is_programmatically_associated"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_continue_enabled_label_unchanged"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_progress_line_carries_no_speaker_characterisation"
        status: pass
    human_judgment: true
    rationale: "Static source contracts prove the shared predicate, the always-visible footer, and the programmatic disabled-reason association exist and are wired correctly, but the operator-visible states in a live browser session (the countdown, the zero-remaining switch, the enabled/disabled visual treatment) were not exercised end-to-end — deferred to this plan's own Task 4 checkpoint, per the plan's verification section."
  - id: T2
    description: "AUTO-MATCHED/NEEDS YOU row cue tags, mutually exclusive by construction (needs-attention checked before auto-matched), excluding read-only and non-review rows, using only muted/warning tokens"
    requirement: "RESOLVE-16"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_both_cue_tag_labels_present_once"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_row_cue_tag_predicate_exists_and_orders_needs_attention_first"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_row_cue_tag_excludes_readonly_and_non_review_rows"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_row_cue_tag_requires_an_untouched_suggestion"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_cue_tag_renders_above_the_side_toggle"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_cue_tag_uses_no_accent_token"
        status: pass
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py#test_cue_tag_evaluated_once_per_row"
        status: pass
    human_judgment: true
    rationale: "Static source contracts prove the predicate's ordering, exclusivity mechanism, and palette compliance, but a live mix of auto-matched/unresolved/operator-chosen rows was not visually inspected end-to-end — deferred to Task 4."
  - id: T3
    description: "14 new Plan 44-09 tests; full api/tests suite and npm run check green"
    requirement: "RESOLVE-15, RESOLVE-16"
    verification:
      - kind: unit
        ref: "api/tests/test_phase44_resolve_table_contract.py (91 passed)"
        status: pass
      - kind: unit
        ref: "api/tests (646 passed, 4 pre-existing collection errors, 0 failures)"
        status: pass
      - kind: command
        ref: "npm --prefix app run check (804 files, 0 errors, 36 pre-existing warnings)"
        status: pass
    human_judgment: false
  - id: T4
    description: "Operator acceptance of the complete Figma reconciliation (44-05 through 44-09) against all four canonical frames, including end-to-end descriptor-preservation and live-tenure-recompute walkthroughs"
    requirement: "RESOLVE-07 through RESOLVE-16 (whole-reconciliation sign-off)"
    verification: []
    human_judgment: true
    rationale: "Task 4 is a checkpoint:human-verify (gate=blocking) requiring a live browser session, visual comparison against Figma nodes 4205:81/4210:81/4206:111/4194:72, and two end-to-end interactive walkthroughs (descriptor preservation across a side toggle; a tenure fix in a second tab recomputing the role live on reload). This executor has no browser or vision tool and cannot perform or fake this verification. NOT YET COMPLETE — see Checkpoint Status below."
---

# Phase 44 Plan 09: Progress indicator, Continue gate, and row cue tags — INTERIM (paused at Task 4 checkpoint)

**Tasks 1-3 complete: the Resolve card now shows a persistent "N of M speakers still need review" header line, an always-visible Continue button that states why it's disabled, and per-row AUTO-MATCHED/NEEDS YOU cue tags — all reading the same personId predicate so the count and the gate cannot disagree. Task 4 (operator acceptance of the full 44-05→44-09 Figma reconciliation) is a blocking human-verify checkpoint this executor cannot perform and has not yet been approved.**

## Status: NOT COMPLETE — paused at Task 4 checkpoint

This is an **interim summary**. Per the plan's own structure, Task 4 is a
`checkpoint:human-verify` with `gate="blocking"` requiring a live browser
session and operator sign-off against four canonical Figma frames, including
two end-to-end interactive walkthroughs. This executor has no browser or
vision tool and has not performed, and cannot fake, that verification.

`.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md`
have deliberately **not** been updated by this run — per the calling
instruction, they are only to be touched after operator approval, in a later
continuation that resumes from this checkpoint.

## Performance

- **Tasks completed:** 3 of 4 (Task 4 pending operator action)
- **Files modified:** 2 (`app/src/lib/components/ResolveCard.svelte`, `api/tests/test_phase44_resolve_table_contract.py`)
- **Commits:** 3

## Accomplishments (Tasks 1-3)

- **RESOLVE-15**: `reviewProgress` derived value reads the identical
  `rowMatchStates[d.raw_speaker_label]?.personId` field access `allDispositioned`
  already used — one predicate, two consumers, so a header/gate disagreement
  (T-44-36) is structurally impossible. The header renders a persistent
  progress line (only while paused and the review set is non-empty), and the
  footer form now always renders while paused, with the button's `disabled`
  reading `allDispositioned` and a reason line wired via `aria-describedby`
  (T-44-37).
- **RESOLVE-16**: `rowCueTag(row, s)` returns the needs-attention tag first
  (checked before the auto-matched case, so a suggested-but-gated row reads
  as needing the operator), the auto-matched tag only while the current
  `personId` still equals the untouched `auto_match_id` (T-44-35), or `null`
  for a read-only row, a non-review row, or an operator's own choice. The tag
  renders once per row at the top of the Resolved As cell, using only the
  existing muted (`#94a3b8`) and warning (`#fbbf24`) tokens — never the accent
  token, per the UI-SPEC's interactive-elements-only reservation.
- 14 new contract tests added (`Plan 44-09` banner), full `api/tests` suite
  green (646 passed, the same 4 pre-existing collection errors documented
  since 44-01/02/03, 0 failures), `npm --prefix app run check` green (804
  files, 0 errors, 36 pre-existing warnings).

## Task Commits

1. **Task 1: Persistent progress line and reason-disabled Continue button** — `bed27f53` (feat)
2. **Task 2: AUTO-MATCHED and NEEDS YOU row cue tags** — `fda0d2b0` (feat)
3. **Task 3: Contract tests for the progress indicator, Continue gate, and row cue tags** — `0cf3a03a` (test)

Tasks 1 and 2 both edited `app/src/lib/components/ResolveCard.svelte`; both
tasks' edits were applied to the working tree before either was committed
(discovered mid-Task-2, after Task 1's edits were already in place), so the
two commits were produced by splitting the combined diff along its natural
hunk boundaries (7 hunks to Task 1, 3 hunks to Task 2 — verified disjoint and
non-overlapping) rather than by editing sequentially with a commit in
between. This mirrors the precedent documented in 44-01-SUMMARY for the same
situation. No behavioral difference; each commit's diff was independently
confirmed self-consistent (the Task-1-only staged state contains no trace of
`rowCueTag`/cue-tag markup).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two pre-existing comments quoting "Continue Resolve" inflated this task's own grep-count acceptance criterion**

- **Found during:** Task 1, running the acceptance-criteria grep checks after the initial edit.
- **Issue:** Two comments predating this plan (lines ~32 and ~355, in the
  file's module-level header comment and inside `allDispositioned`'s own
  comment) quoted the literal button label `"Continue Resolve"`. Combined
  with the footer comment and the button's own label, `grep -c 'Continue
  Resolve'` read 4 instead of the acceptance criterion's required 1.
- **Fix:** Reworded both pre-existing comments (and this plan's own new
  footer comment) to say "the primary CTA" instead of quoting the literal
  label. No functional change.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`.
- **Commit:** `bed27f53` (Task 1).

**2. [Rule 1 - Bug] The type-signature form of `rowCueTag` mandated by the plan's own action text made the "exactly once" tag-literal acceptance criteria unsatisfiable**

- **Found during:** Task 2, running the acceptance-criteria grep checks.
- **Issue:** The plan's action text specifies `function rowCueTag(...): 'AUTO-MATCHED' | 'NEEDS YOU' | null`. Writing that explicit union
  annotation plus the two return statements produces 2 occurrences of each
  tag literal, but the same task's acceptance criteria require `grep -c
  'AUTO-MATCHED'` and `grep -c 'NEEDS YOU'` to each equal exactly 1 — a
  genuine internal conflict in the plan between the mandated signature and
  the mandated count.
- **Fix:** Omitted the explicit return-type annotation; TypeScript infers the
  identical `'AUTO-MATCHED' | 'NEEDS YOU' | null` union from the two return
  statements, so each literal is written exactly once (functionally
  identical, verified via `npm run check` — 0 type errors).
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`.
- **Commit:** `fda0d2b0` (Task 2).

**3. [Rule 1 - Bug] A naive color-selection expression would have re-introduced a second occurrence of the "NEEDS YOU" literal**

- **Found during:** Task 2, while wiring the tag's color.
- **Issue:** The natural implementation — `color: {cueTag === 'NEEDS YOU' ? warning : muted}` — compares the rendered value against the literal string a second time, which would again violate the exactly-once acceptance criterion for that literal.
- **Fix:** Introduced `cueTagIsWarning = s?.personId == null || gated`, mirroring `rowCueTag`'s own needs-attention branch condition (reusing the already-declared `gated`), so the color forks on the same underlying signal without a second string comparison.
- **Files modified:** `app/src/lib/components/ResolveCard.svelte`.
- **Commit:** `fda0d2b0` (Task 2).

### Auth Gates

None encountered.

### Prohibited Actions Avoided

- No new hex color introduced — the cue tag and progress copy use only the
  already-approved `#94a3b8` (muted) and `#fbbf24` (warning) tokens; the
  accent token `#93c5fd` is not used for either addition, per the UI-SPEC's
  interactive-elements-only reservation. `test_no_unapproved_hex_colors_introduced`
  and `test_cue_tag_uses_no_accent_token` both pass.
- The `?/resolve` submit path and its `matches` payload are unchanged — no
  new fetch, no new prop, no new endpoint. `test_matches_payload_shape_is_unchanged`
  (44-05) still passes unmodified.
- The `Suggested` badge inside the listbox option (44-02) is untouched —
  `test_suggested_badge_lives_inside_the_listbox_option_region` still passes.

## Verification

- `npm --prefix app run check` — **804 files, 0 errors**, 36 pre-existing
  warnings (unrelated to this plan's file — none new in `ResolveCard.svelte`
  beyond the one pre-existing a11y warning on the listbox `<li>`, unchanged
  by this plan).
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests/test_phase44_resolve_table_contract.py -q` — **91 passed**, 0 failures.
- `./.venv/Scripts/python.exe -m pytest tests/conftest.py api/tests -q` — **646 passed**, 0 failures, the same 4 pre-existing collection errors documented in every prior 44-0x SUMMARY (Node.js path issue in `test_phase38_people_ui_contract.py`, unrelated to this plan). This is the phase-gate baseline for the next phase: 646 passed / 4 pre-existing collection errors / 0 failures.
- `grep -c 'still need review'` / `grep -c 'speakers reviewed'` / `grep -c 'more to continue'` — all 1.
- `grep -c 'AUTO-MATCHED'` / `grep -c 'NEEDS YOU'` — both 1.
- `grep -c '{#if isPaused && allDispositioned}'` — 0 (the retired combined condition is gone).
- `git diff --name-only` (uncommitted working tree at plan-pause time) shows only pre-existing, not-mine changes (`.env.example`, `app/.env.example`, `app/vite.config.ts`, `scripts/dev-start.ps1`, a todos-directory move) — no unexpected file was touched by this plan.

Items 6-12 of the plan's own `<verification>`/Task 4 `<how-to-verify>` list
(operator acceptance against Figma nodes 4205:81/4210:81/4206:111/4194:72,
including the descriptor-preservation and tenure-recompute walkthroughs) are
**not yet performed** — this is the Task 4 checkpoint this summary pauses at.

## Self-Check: PASSED (for Tasks 1-3 only)

- FOUND: `app/src/lib/components/ResolveCard.svelte`
- FOUND: `api/tests/test_phase44_resolve_table_contract.py`
- FOUND: commit `bed27f53` (Task 1)
- FOUND: commit `fda0d2b0` (Task 2)
- FOUND: commit `0cf3a03a` (Task 3)

## Checkpoint Status: BLOCKED at Task 4 (gate=blocking, human-verify)

See the returned checkpoint message for full verification steps. Awaiting
operator sign-off in a live browser session against Figma file
`9PDECvbdHM2vYVxt3SCwru`, page "screen mockups for GSD", nodes `4205:81`,
`4210:81`, `4206:111`, `4194:72`.
