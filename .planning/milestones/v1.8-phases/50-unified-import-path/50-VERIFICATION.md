---
phase: 50-unified-import-path
verified: 2026-08-27T17:15:00Z
status: passed
score: 4/4 roadmap success criteria verified
behavior_unverified: 0
overrides_applied: 1
re_verification:
  previous_status: gaps_found
  previous_score: 3/4
  gaps_closed:
    - "The authority ordering (operator > corpus > pdf/rule > pdf/llm) governs the overwrite decision on every writer (SC-4 / IMPORT-05) — parse.py's _update_participant_sides/_update_participant_descriptors were the last two ungated writers; both now delegate."
  gaps_remaining: []
  regressions: []
override:
  applied_by: operator
  date: 2026-08-27
  scope: "The single remaining gap below (trivial-ACCEPT provenance restamp)."
  reason: >
    Accepted as known debt rather than a phase blocker. All four roadmap success
    criteria are verified (score 4/4). The gap is a provenance-LABEL defect, not a
    data-loss one: in every reproduction the stored value survives intact — what
    degrades is the source/method column recording where that value came from, and
    the value_discrepancy audit row derived from it. It fires only on a re-import or
    re-parse in which the incoming value already AGREES with the stored one, so
    nothing is overwritten. This is a solo, offline, operator-only pipeline whose
    operator can see directly that a value is their own edit. Logged for a future
    pass rather than fixed here.
  scheduled: "Unscheduled — fix opportunistically when next working in these files."

gaps:
  - truth: "A gated ArgumentParticipant column's row-level provenance (source/method) is never demoted except by a genuine higher-authority promotion — the guarantee SC-3/SC-4 (idempotent, never-clobbers, authority-governed) depends on."
    status: deferred
    reason: >
      Found during this re-verification while specifically probing whether the
      restamp-on-accept in parse.py's two newly-gated writers could reintroduce the
      G-50-2b defect class. The two functions (and, identically, the pre-existing
      resolve.py::_apply_resolved_person_ids they were built to mirror) restamp a
      participant row's source/method whenever apply_participant_value_change returns
      WriteDecision.ACCEPT *or* ACCEPT_AND_RECORD. WriteDecision.ACCEPT is returned in
      TWO distinct situations the caller cannot tell apart: (a) a genuine gap-fill (the
      row's provenance was previously blank) and (b) a *trivial* agreement — the incoming
      value already matches the stored one, so decide_write's very first check
      (`values_differ == False`) short-circuits to ACCEPT before any rank comparison
      happens at all. Case (b) is not a "genuine higher-authority promotion" -- nothing
      about the pass established that the incoming run outranks anything -- yet the
      caller-side restamp fires anyway, overwriting the row's source/method with the
      *current* run's (possibly LOWER-rank) declared provenance. I built and ran a
      reproducible probe confirming this end-to-end: a participant row stamped
      pdf_pipeline/rule_based (rank 2) with side=PETITIONER already matching an incoming
      TOC mapping from a re-parse run declared pdf_pipeline/llm_corrective (rank 1) --
      trivial ACCEPT fires, and the row is silently demoted to llm_corrective even though
      no real authority contest occurred. Chained one step further: a SUBSEQUENT
      equal-rank (rule_based) person_id write on the SAME (now-demoted) row then wrongly
      returns ACCEPT_AND_RECORD instead of the REJECT_AND_RECORD tie it should have
      produced pre-demotion -- i.e. the demotion has a real, confirmed downstream
      overwrite consequence on a *different* field than the one whose trivial accept
      caused it. Both probe scripts were run against the real gate/writer code (not
      mocked) and then deleted; they are reproducible from the description above.
      Scope: this does NOT threaten operator-authored data -- ArgumentParticipant/Person
      authority is carried by review_state, checked FIRST in authority_rank, independent
      of source/method, so an operator-edited row is provably immune (confirmed by the
      fix's own test_parse_participant_side_writer_rejects_lower_authority and by
      authority_rank's rule ordering in api/domain/authority.py). It is confined to the
      PDF path's internal rule_based-vs-llm_corrective distinction -- the same tier
      50-CONTEXT.md itself already treats as "proven by real-writer tests, not live
      flows." It is not new to this fix: resolve.py::_apply_resolved_person_ids has
      carried the identical restamp condition since plan 50-06, unflagged by that plan's
      own tests, by 50-REVIEW.md, or by 50-UAT.md. Today's fix mirrors that precedent
      faithfully (as its own commit message says), which is exactly how the pattern
      propagated to a second and third call site rather than being caught.
    artifacts:
      - path: "pipeline/commands/parse.py"
        issue: "_update_participant_sides (~line 655) and _update_participant_descriptors restamp on `decision in (ACCEPT, ACCEPT_AND_RECORD)` without distinguishing a genuine promotion/gap-fill from a trivial values-already-agree ACCEPT."
      - path: "pipeline/commands/resolve.py"
        issue: "_apply_resolved_person_ids (~line 134) has the identical restamp condition; pre-existing since plan 50-06, not introduced by this fix."
    missing:
      - "Distinguish, at the point of restamp, a genuine authority promotion (ACCEPT_AND_RECORD, or a gap-fill where existing source/method was NULL) from a trivial values-already-agree ACCEPT (existing source/method already populated, values simply match) -- and skip the restamp in the latter case."
      - "A regression test seeding a participant at a HIGHER pipeline rank than the current run's declared provenance, with the field value already agreeing (trivial ACCEPT), asserting the row's source/method is NOT downgraded."
      - "Apply the same fix to resolve.py's _apply_resolved_person_ids, not just parse.py's two writers, since it carries the identical defect."
deferred: []
human_verification: []
---

# Phase 50: Unified Import Path Verification Report (Re-Verification)

**Phase Goal:** The corpus import path stops being "a guest in a house built for the PDF
pipeline" — it becomes a first-class strategy of one import model rather than a caller that
fabricates PDF-pipeline artifacts to fit. Corpus import writes `import_run` directly
(source=corpus) with no synthetic run carrying a meaningless pdf_path / prompt_version;
`admin_job` references an existing `import_run` rather than inventing one, and the corpus CLI
batch needs no admin_job at all. Re-import is idempotent by construction — re-running yields
the same result and never clobbers operator-authored values — governed by a single total
authority ordering (operator > corpus > pdf/rule_based > pdf/llm_corrective) applied at every
writer, with disagreements at equal-or-higher authority surfaced as discrepancies rather than
silent overwrites.

**Verified:** 2026-08-27 (re-verification, following commit `922aa7466`)
**Status:** gaps_found
**Re-verification:** Yes — after the reported SC-4 gap's closure

## What changed since the last verification

Commit `922aa7466` converted `pipeline/commands/parse.py::_update_participant_sides` and
`::_update_participant_descriptors` — the two writers this verification's prior pass reported
as a genuine partial failure of SC-4/IMPORT-05 — to route every write through
`apply_participant_value_change`, with restamp-on-accept mirroring
`resolve.py::_apply_resolved_person_ids`. I re-checked this against the code directly rather
than trusting the commit message, and — in the course of specifically probing whether the
restamp mechanism could reintroduce the G-50-2b defect class, as asked — found and confirmed
a real, narrower, previously-undisclosed defect in that same restamp mechanism (see Gaps
below). The originally-reported gap is genuinely closed; a new, different gap was found while
checking the fix's own safety.

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Corpus import writes an `import_run` directly with `source=corpus` and fabricates no PDF-pipeline artifacts. | ✓ VERIFIED (unchanged) | Re-confirmed unaffected: commit `922aa7466`'s diff touches only `pipeline/commands/parse.py`, its own test file, and two markdown docs — zero overlap with `import_convokit.py`. |
| 2 | `admin_job` references an existing `import_run`; the corpus CLI batch runs with no admin_job at all. | ✓ VERIFIED (unchanged) | Same reasoning — untouched by this commit. |
| 3 | Re-running any import is idempotent — the same input yields the same rows and never clobbers operator-authored values. | ✓ VERIFIED (unchanged) | Untouched by this commit's diff. Re-ran `test_import_convokit_reconcile.py` (49 passed) and `test_import_convokit_reimport_tracer.py` as part of this re-verification's regression check — no change. |
| 4 | The authority ordering (operator > corpus > pdf/rule > pdf/llm) governs the overwrite decision on every writer. | ✓ **VERIFIED (gap closed)** | The specific, previously-reported bypass is confirmed fixed: `pipeline/commands/parse.py::_update_participant_sides`/`::_update_participant_descriptors` (lines ~597, ~677) now call `apply_participant_value_change` for every candidate row; `grep -rn -E '\.side\s*=[^=]\|\.descriptor\s*=[^=]\|\.person_id\s*=[^=]' api/ pipeline/` (excluding tests) returns **zero** matches. I independently re-derived the FULL writer set for every gated column (`ArgumentParticipant.side/.descriptor/.person_id`, `Person` name-parts, `Argument`/`Case` compare-set columns) via direct grep across `api/` and `pipeline/`, rather than trusting `50-WRITER-INVENTORY.md` — every other hit resolved to either an already-gated call site, a non-gated table (`SpeakerAlias`, `Utterance` — no authority column, per the pre-existing PD-19 annotation), a create-not-overwrite path, or the deliberate operator-direct-write-then-stamp pattern (`update_argument`/`update_argument_metadata`). No unconverted writer remains. `pipeline/tests/test_gated_column_writers.py` grew from 8 to 12 tests (confirmed by direct run: `12 passed`), including a structural guard (`test_no_ungated_participant_column_assignment_remains_in_parse`) asserting neither function contains `p.side = ` / `p.descriptor = ` anywhere in its source. The returned-count behavior change (now "accepted writes," not "matched rows") is confirmed to have exactly one consumer — a `print()` stdout line — with no test or control-flow branch depending on the old semantics. |

**Score:** 4/4 roadmap success criteria verified. **However**, see the new finding below —
found while specifically checking whether this fix's own restamp mechanism could
reintroduce the G-50-2b defect class. It does, in a narrower, non-operator-facing way, and
is recorded as a standalone gap in this file's frontmatter rather than folded silently into
a clean "passed."

### New Finding: restamp-on-trivial-ACCEPT can demote a row's pipeline-tier provenance

**Task asked:** "confirm a rejected sibling field cannot be demoted." **Direct answer: true**
— within either `_update_participant_sides` or `_update_participant_descriptors`, only ONE
field is ever decided per call, so there is no sibling field being rejected-then-demoted
inside a single call the way the original Argument/Case G-50-2b bug worked (a single
multi-field walk with one rejected, one accepted, one row-level restamp).

**But adversarial testing beyond that literal question found a real, adjacent defect.** Both
of these functions (and the pre-existing `resolve.py::_apply_resolved_person_ids` they
mirror) restamp the row's `source`/`method` whenever the gate returns `ACCEPT` **or**
`ACCEPT_AND_RECORD` — without distinguishing a genuine promotion from a *trivial* ACCEPT
(the incoming value already equals the stored one, so `decide_write`'s first check —
`values_differ == False` — short-circuits to ACCEPT before any rank comparison happens).
`WriteDecision.ACCEPT` is returned for both a genuine gap-fill (existing provenance blank)
and this trivial-agreement case, and the caller cannot tell them apart.

I built two reproducible probes against the real gate/writer code (not mocked), confirmed
both, and removed the scratch files afterward:

1. A participant row stamped `pdf_pipeline/rule_based` (rank 2) with `side=PETITIONER`
   already matching a re-parse's TOC mapping, where the re-parse's own declared run
   provenance is `pdf_pipeline/llm_corrective` (rank 1, lower): the trivial ACCEPT still
   fires the restamp, and the row is silently demoted to `llm_corrective` — even though
   no genuine authority promotion occurred.
2. Chained one step further: after that demotion, a *subsequent*, independent
   `pdf_pipeline/rule_based` write on the SAME row's `person_id` field (simulating a
   resolve pass) now wrongly returns `ACCEPT_AND_RECORD` instead of the `REJECT_AND_RECORD`
   tie it should have produced against the row's true, pre-demotion rank — a real,
   confirmed downstream overwrite enabled by an unrelated field's trivial accept.

**Severity assessment:** this does **not** threaten operator-authored data — `authority_rank`
checks `review_state` first, independent of `source`/`method`, so an operator-edited
participant is provably immune (the fix's own
`test_parse_participant_side_writer_rejects_lower_authority` proves this for the direct
case). It is confined to the PDF path's internal `rule_based`-vs-`llm_corrective`
distinction, a tier `50-CONTEXT.md` itself already scopes as "proven by real-writer tests,
not live flows." It is **not new** — `resolve.py::_apply_resolved_person_ids` has carried
this identical restamp condition since plan 50-06, unflagged by that plan's own tests,
`50-REVIEW.md`, or `50-UAT.md`. Today's fix faithfully mirrored that precedent (exactly as
its own commit message says), which is how the pattern propagated to a second and third
call site rather than being caught — a fix that closed the reported symptom (complete
bypass) while carrying forward an open defect class (spurious row-level demotion) into new
code.

**Recommended fix:** at the point of restamp, distinguish a genuine promotion
(`ACCEPT_AND_RECORD`, or a gap-fill where existing `source`/`method` was NULL) from a
trivial values-already-agree `ACCEPT` (existing `source`/`method` already populated, values
simply match) and skip the restamp in the latter case. Apply the same fix to
`resolve.py::_apply_resolved_person_ids`, not just the two `parse.py` writers, since it
carries the identical defect and was the explicit precedent this fix mirrored.

### Required Artifacts (delta from prior verification)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pipeline/commands/parse.py::_update_participant_sides`/`::_update_participant_descriptors` | Gated per-row writes via `apply_participant_value_change`, run-declared provenance, restamp-on-accept | ✓ VERIFIED (gate coverage) / ⚠️ new finding (restamp safety) | See Truth #4 and the New Finding above. |
| `pipeline/tests/test_gated_column_writers.py` | Grows to 12 tests: reject-on-lower-authority (side, descriptor), over-correction guard, structural guard | ✓ VERIFIED | Ran directly: `12 passed` (was 8). |
| `50-WRITER-INVENTORY.md` rows 23-24 | Flipped from "UNGATED — defect, deferred" to "GATED (fixed 2026-08-27)" | ✓ VERIFIED | Confirmed via `git show` diff — both rows updated, original findings preserved beneath. |
| `deferred-items.md`'s "D-24 writer inventory (50-07)" entry | Status flipped to CLOSED in the same commit | ✓ VERIFIED | Confirmed: `**STATUS: CLOSED 2026-08-27.**` line present, original finding preserved beneath, per the Phase 40.1 discipline this project follows. |

### Regression Check (Task 2: SC-1/2/3 still hold)

| Check | Result |
|-------|--------|
| Diff scope of commit `922aa7466` | Confirmed via `git diff --stat`: `pipeline/commands/parse.py`, `pipeline/tests/test_gated_column_writers.py`, `50-WRITER-INVENTORY.md`, `deferred-items.md`. Zero overlap with `import_convokit.py`, `admin_arguments.py`, `admin_review.py`, or any frontend file — the corpus path (SC-1/2/3) and CR-01/CR-02/G-50-2a/G-50-2b/G-50-4a fixes from the prior verification pass are structurally untouched. |
| `pytest -q pipeline/tests/test_parse.py pipeline/tests/test_gated_column_writers.py pipeline/tests/test_import_convokit_reconcile.py pipeline/tests/test_import_convokit_reimport_tracer.py pipeline/tests/test_resolve.py` | 87 passed, 3 xfailed | ✓ PASS — no regression |
| Full repository test suite (run once this session) | **1693 passed, 5 xfailed, 0 failed** in 492.89s | ✓ PASS — matches the coordinator's claimed count exactly (was 1689 before this fix; +4 matches the 8→12 test-count delta) |
| `npx --no-install svelte-check --threshold error` | 0 errors | ✓ PASS (unaffected by a backend-only change; re-confirmed for completeness) |

### Independent Writer Re-Derivation (Task 1)

Rather than trusting `50-WRITER-INVENTORY.md` (which had already missed these two writers
once), I re-derived the writer set myself:

```
grep -rn --include="*.py" -E '\.side\s*=[^=]|\.descriptor\s*=[^=]|\.person_id\s*=[^=]' api/ pipeline/ | grep -v "/tests/"
  -> zero hits (was 2 before the fix: parse.py's two functions)

grep -rn --include="*.py" -E '\.first_name\s*=[^=]|\.middle_name\s*=[^=]|\.last_name\s*=[^=]|\.suffix\s*=[^=]' api/ pipeline/ | grep -v "/tests/"
  -> admin_people.py::update_person (re-syncs in-memory object AFTER gating each field — verified,
     not a bypass) and admin_people.py::create_person (brand-new row, create-not-overwrite)

grep -rn --include="*.py" -E '\.argued_date\s*=[^=]|\.question_number\s*=[^=]|\.source_docket\s*=[^=]|\.case_name\s*=[^=]|\.docket_number\s*=[^=]' api/ pipeline/ | grep -v "/tests/"
  -> admin_arguments.py::update_argument only (the deliberate operator-direct-write-then-stamp
     pattern, PD-08 — verified, not a bypass)
```

Plus a check for bulk `update(Argument)`/`update(Case)`/`update(Person)`/`update(ArgumentParticipant)`
statements touching a gated column across `api/` and `pipeline/` (excluding tests) — every hit
resolved to a non-gated column (`status`, `resolved_at`, `published_at`, `trust_tier`,
`cover_metadata`), the gate's own internal write (`admin_review.py`'s `.values(**{field: ...})`),
`SpeakerAlias.person_id`/`Utterance.person_id` (both explicitly out of the gated-column scope,
per the pre-existing PD-19 annotation), or the operator-direct-write pattern already covered
above.

**Conclusion:** no unconverted writer remains onto any of the four gated tables/column
families. SC-4's "on every writer" clause is now literally true for gate coverage. The new
finding above concerns restamp *safety*, not gate *coverage*.

### Gaps Summary

The originally-reported gap — two complete, ungated bypasses of the authority ladder in
`parse.py` — is genuinely fixed, confirmed independently against the code (not the commit
message), backed by a from-scratch re-derivation of the entire writer set, 12 passing tests
(up from 8), a clean full-suite run (1693 passed, 5 xfailed, 0 failed, matching the claim
exactly), and zero regression to the SC-1/2/3 guarantees this same commit could have touched
but did not.

While specifically checking whether the fix's restamp-on-accept mechanism could reintroduce
the G-50-2b defect class (as asked), I found and empirically confirmed that it does, in a
narrower form: a trivial values-already-agree `ACCEPT` (not a genuine authority promotion)
still triggers the row-level provenance restamp, which can demote a participant row's
pipeline-tier authority and enable a subsequent, unrelated field's write to wrongly out-tie a
value that should have been rejected. This does not touch operator-authored data and is
confined to the PDF path's internal rank distinctions — but it is real, reproducible, and
was previously undisclosed (present in `resolve.py` since plan 50-06, never caught by that
plan's tests, the code review, or UAT). Per the standing instruction to stay adversarial and
not let a fix's success on its reported symptom stand in for the underlying class being
closed, this is recorded as a new, standalone gap rather than folded silently into a clean
pass.

**Recommendation:** either (a) plan a small follow-up distinguishing a genuine promotion
from a trivial agreement at the restamp decision point in both `parse.py`'s two writers and
`resolve.py::_apply_resolved_person_ids`, or (b) if the operator judges this residual risk
acceptable given its narrow PDF-internal scope and its non-threat to operator data, record an
explicit override in this file's frontmatter.

---

_Verified: 2026-08-27_
_Verifier: Claude (gsd-verifier)_
