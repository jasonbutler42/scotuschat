# Deferred Items — Phase 49 (out of scope for 49-02)

## `api/tests/test_admin_jobs_service.py` — two trust-tier regression tests broken by plan 49-01's D-18 change, intersecting a deliberately-deferred PDF-pipeline wiring gap

**Found during:** 49-02 Task 3, running the full `api/tests -q` suite for the first time
since plan 49-01 landed.

**Failing tests:**

- `test_resolve_job_recomputes_tier_when_last_speaker_resolves`
- `test_repeated_writer_call_leaves_tier_unchanged`

Both assert `argument.trust_tier is TrustTier.TRUSTED` after `resolve_job` /
`update_resolve_row_for_job` (both in `api/services/admin_jobs.py`) resolve or edit an
`ArgumentParticipant` row; both now observe `TrustTier.UNCERTAIN` instead.

**Root cause:** Plan 49-01 (D-18) changed `api/services/trust.py::_load_constituents` to
feed `derive_tier` a real `(source, method, review_state)` triple for every
*resolved* `ArgumentParticipant` row, instead of contributing nothing. Neither
`resolve_job` nor `update_resolve_row_for_job` ever writes `ArgumentParticipant.source`/
`.method` — only `person_id` (and, for the latter, `side`/`descriptor`) — so a participant
resolved through either path now has `source=NULL, method=NULL`, and
`derive_tier("", "", "unreviewed")` floors to `UNCERTAIN`. This was silently latent because
49-01 never ran `api/tests/test_admin_jobs_service.py` in its own verification.

**Why not fixed here:** 49-CONTEXT.md D-20 locks the exact `source`/`method` mapping for
every participant-resolution mechanism that exists TODAY — corpus auto-match (`corpus`/
`direct`), PDF alias-table HIT (`pdf_pipeline`/`normalized`, explicitly **not yet wired**,
per the same document's "Out of scope" list: "Wiring the PDF alias-HIT participant method;
the mapping is recorded, not built (D-20), consistent with the corpus-first scope
decision"), and operator popover assignment (`admin.py:1423`, unchanged by design, D-22).
Neither `resolve_job` nor `update_resolve_row_for_job` appears in that table at all — there
is no locked decision for what provenance an admin-driven resolve-job/Resolve-card action
should stamp. Inventing one here would be a new architectural decision (Rule 4), not a bug
fix, and would risk conflicting with whatever Phase 50's corpus-first PDF-pipeline wiring
plan eventually decides for this exact code path. Neither file
(`api/services/admin_jobs.py`, `api/tests/test_admin_jobs_service.py`) is in plan 49-02's
`files_modified` list, and the fix genuinely requires a decision this plan has no mandate to
make.

**Contrast with the fix this plan DID make:** `pipeline/commands/import_convokit.py`'s
`ArgumentParticipant` creation had the exact same NULL-source/method gap and was fixed in
this plan (see 49-02-SUMMARY.md) — that fix was in-scope because it implements an
ALREADY-LOCKED D-20 mapping row (corpus resolution -> `corpus`/`direct` -> TRUSTED) in a file
already in this plan's `files_modified` list, not a new decision.

**Status:** acknowledged
Open — out of scope for 49-02. Candidate follow-up: either fold into whatever
plan wires the PDF-pipeline participant provenance (D-20's deferred row), or raise as its
own small decision — "what source/method (if any) should an admin-driven resolve_job/
Resolve-card resolution stamp on `ArgumentParticipant`?" — via `/gsd-review-backlog` or a
phase-49 cleanup plan.

## D-35a published-write inventory (49-11) — every write path that can reach an argument, dispositioned (2026-08-24)

Moved to `49-PUBLISHED-WRITE-INVENTORY.md` on 2026-09-23 — it is a dispositioned decision
record rather than deferred work, and its tables were surfacing as false open items in the
milestone-close audit.

**Status:** resolved — closed 2026-08-25 by D-23 (operator), cited in `50-CONTEXT.md`. D-35a
itself (the whole-argument scope question this section used to record as open) has been LOCKED
and implemented since 49-11 — see `49-CONTEXT.md`'s `### D-35a (locked)` entry.

## D-35 convergence (49-10) — the public chat page's independently derived bench flag is NOT reconciled, and this plan makes it MORE reachable

**Found during:** 49-10 Task 3, closing G-49-3 by converging the Speakers card onto the
Resolve card's full side vocabulary (D-35, "Converge both surfaces").

Admin derives `is_bench` from `side == SideEnum.BENCH`. The public chat page derives its own,
independent bench signal from `tenure.length > 0`
(`app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts:36`), and
`api/services/speakers.py` falls through to `ADVOCATE_LABEL_MAP` when the bench branch is
skipped — so a `BENCH` participant with no covering `CourtTenure` reads **Bench** in admin
and **Counsel** in public. This is the open todo
`2026-08-12-speakers-bench-classification-silent-fallback.md`; its reconcile-the-two-signals
suggestion is the eventual fix.

**This plan makes the divergence MORE reachable, stated plainly rather than buried.** Before
49-10, this state required a data accident (a corpus-resolved bench participant landing
without a covering tenure row). After 49-10, an operator can produce it **on purpose** by
moving any participant to Bench from the Speakers card. That is a real, direct consequence of
D-35 and is recorded here as such — not softened.

**Partial mitigation, not a fix:** 49-09's published lock means this divergence cannot be
*introduced* on an already-published argument — a reclassification is only reachable on
draft/unpublished/candidate data. It CAN still reach the public site: the argument must be
published (or re-published) afterward, and the publish trust gate does not currently check
tenure coverage as a precondition. Reconciling the two signals touches the public read path
(`api/services/speakers.py`, `app/src/routes/cases/[slug]/...`), which is outside Phase 49's
boundary (admin-only).

**Status:** open — accepted with this consequence stated, tracked by
`2026-08-12-speakers-bench-classification-silent-fallback.md`.

## D-35 convergence (49-10) — person-to-participant assignment remains uneditable on the Speakers card

**Found during:** 49-10 Task 3.

The Speakers card converges the SIDE control (bench vs. every advocate role) but does not add
a person picker — its Name column stays plain text (`speaker.full_name ?? '—'`), unchanged
from before this plan. Reassigning WHICH person a participant row refers to (as opposed to
reclassifying that row's side) remains possible only via the Resolve card's person combobox.
This is a genuinely separate gap from G-49-3 — the operator has not raised it, and D-35's
"almost the exact interface" language was read (see 49-10-PLAN.md `<planner_decisions>`) as
covering the side/role vocabulary the operator explicitly complained about, not the person-
assignment mechanism, which is a materially different control (a searchable combobox against
a candidate pool) that this plan's `files_modified` list and time budget do not cover.

**Status:** open — not raised by the operator; current remedy is the Resolve card. Candidate
follow-up if the operator wants person reassignment from the argument-detail page directly.

## D-24 writer inventory (50-07) — `parse.py`'s TOC-mapping side/descriptor writers bypass the authority gate entirely

**Found during:** 50-07 Task 3, building `50-WRITER-INVENTORY.md` — reading every writer's
source directly (per D-24's own instruction) rather than trusting D-22's enumeration or
50-06's already-converted list, exactly the discipline that already found the two writers
50-05/50-06 fixed (`resolve.py`'s bulk `person_id` UPDATE, `import_convokit`'s
`_apply_extracted_name_provenance`).

**STATUS: CLOSED 2026-08-27.** Both writers now route through `apply_participant_value_change` with restamp-on-accept, mirroring `resolve.py::_apply_resolved_person_ids`. Found still open by the phase-50 goal verification, which judged it a genuine partial failure of SC-4/IMPORT-05 ("on every writer") rather than an acceptable deferral. Covered by three new `test_gated_column_writers.py` tests plus a structural guard, falsifiability-checked. Original finding below, kept for the record.

**The defect:** `pipeline/commands/parse.py::_update_participant_sides` and
`::_update_participant_descriptors` (Phase 16 PARSE-02 / Phase 22 PJOB-13, both pre-dating
Phase 49's authority ladder) write `ArgumentParticipant.side`/`.descriptor` by direct ORM
attribute assignment (`p.side = ...`, `p.descriptor = ...`) from a TOC-derived label map,
called unconditionally on **every** parse pass — including a re-parse of an argument whose
participant rows already survived a prior pass. `ArgumentParticipant` rows persist across
re-parses (select-before-insert dedup on `raw_speaker_label`, `_run_parse_inner` Step 7b) —
so a participant an operator already moved to a different side via
`admin_arguments.update_participant_side` (gated) can be silently overwritten back to the
TOC's mapping on the next re-parse. No `apply_participant_value_change` call, no
`review_state` check, no `source`/`method` stamp — the exact overwrite-an-operator-edit
failure mode D-22's whole sweep exists to close, on the one call site the sweep never
named.

**Why not fixed here:** out of scope for plan 50-07 (a documentation-and-closeout plan;
`pipeline/commands/parse.py` is not in its `files_modified`) and out of scope for 50-06
(already shipped, closed, and summarized before this defect was found — 50-06's own
`files_modified` covered `parse.py`'s Blocks A/B/D cover-metadata writes only, never this
Phase-16-era TOC-mapping helper pair). A real fix needs a per-row `apply_participant_value_
change` conversion mirroring `resolve.py`'s own `_apply_resolved_person_ids` shape (50-06's
established pattern), a decision on `incoming_source`/`incoming_method` for a TOC-derived
correction (likely `run.source`/`run.method`, matching Block D's convention), and dedicated
tests — the same class of "new decision, not a bug fix, needs its own mandate" reasoning
the trust-tier regression item at the top of this file already used for a sibling gap in
this same file's history.

**Status:** open — not fixed by this plan. Candidate follow-up: a small plan converting
`_update_participant_sides`/`_update_participant_descriptors` to per-row gate calls,
mirroring 50-06's `resolve.py` conversion, with its own `test_gated_column_writers.py`
coverage.

---

## Trivial-ACCEPT provenance restamp (found 2026-08-27, phase-50 goal verification)

**Status:** acknowledged
Open — accepted as known debt, operator override recorded in `50-VERIFICATION.md`.

**The defect.** `decide_write` returns `ACCEPT` for two different situations: a
genuine gap-fill (stored side blank, incoming populated) and a trivial agreement
(the values already match). Callers cannot tell them apart from the decision
alone, so they restamp the row's `source`/`method` for both — treating a write
that changed nothing as an authority event.

**Where:**

- `pipeline/commands/import_convokit.py::_row_should_restamp` — the severe one.
  `Argument`/`Case` have no `review_state`, so `source` is the only carrier of
  operator authority. An OPERATOR-stamped row whose compare-set fields all AGREE
  with the corpus is demoted `operator -> corpus` on a byte-identical re-import.
  Reproduced against real code 2026-08-27.
- `pipeline/commands/resolve.py::_apply_resolved_person_ids` — pre-existing since
  plan 50-06.
- `pipeline/commands/parse.py::_update_participant_sides` /
  `::_update_participant_descriptors` — inherited 2026-08-27 by mirroring
  `resolve.py`. Narrower: `review_state` protects operator data on
  `ArgumentParticipant`, so the blast radius is the PDF path's internal
  `rule_based`-vs-`llm_corrective` tiers.

**Why it is debt and not a blocker.** No data loss in any reproduction — the
stored value always survives. What degrades is the label recording where the
value came from, and the `value_discrepancy` row derived from it. It fires only
when the incoming value already agrees, so nothing is overwritten.

**Same class as G-50-2b, different trigger.** G-50-2b was a row-level provenance
write driven by a *rejected sibling* field; this is one driven by an *accept that
wrote nothing*. The G-50-2b fix closed the first door only — worth remembering
that fixing one trigger of a class does not close the class.

**The fix, when someone is next in these files.** Restamp only when the accepted
write actually changed the value: gate each restamp on `_values_differ(field,
incoming, existing)` in addition to the existing decision check. `_values_differ`
is already imported in all three modules. Add a test for the operator-demotion
case (an OPERATOR row whose fields all agree must stay OPERATOR across a
re-import) — the existing G-50-2b tests all use a disagreeing sibling and so pass
straight through this defect.
