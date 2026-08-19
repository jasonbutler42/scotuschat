# Phase 48: Trust & Lifecycle - Context

**Gathered:** 2026-08-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Every argument is born a *candidate* carrying a materialized `trust_tier`, and reaches
the public site through exactly one review-gated promotion (`published_at`) that is
hard-blocked while any UNCERTAIN element remains, with the operator retaining final
authority through a deliberate, logged, per-argument override. `trust_tier`
(verified / trusted / provisional / uncertain) is derived from `(authority, method,
review_state)` by one documented function and stored on the argument as the floor
rollup of its constituents, recomputed on every mutation path. Trust is operator-facing
only — never on the public site.

**In scope:**
- `candidate` added to the `argument_status` enum, replacing `pipeline` as the born state
- `arguments.trust_tier` materialized column + the shared derivation/rollup function
- Recompute called in-transaction by every writer (corpus import, approve, edits, publish)
- An offline `pipeline` CLI recompute command (drift repair + verification vehicle)
- The UNCERTAIN publish gate, the required-reason override, and its audit record
- Minimal admin UI on the existing argument detail page: block reason + override prompt
- The carried `delete_argument` → `argument_status_log` cascade defect (fix, regression
  test, and the wrong comment at `scripts/delete_fixture_argument.py:25`)

**Out of scope (later phases):**
- `review_state` column, discrepancy recording, the operator review queue → Phase 49
- Candidate visibility in the admin arguments list / any tier badge UI → Phase 49
- Widening the delete gate to candidates → Phase 50 (re-import idempotency decides it)
- Corpus/PDF import path rework, `admin_job` re-point → Phase 50
- Design system, shared components, listing style → Phase 51
- Any public-facing display of trust — permanently out of scope (apolitical constraint)

</domain>

<decisions>
## Implementation Decisions

### Status vocabulary

- **D-01:** **`candidate` replaces `pipeline`; `draft` survives.** The lifecycle stays
  four-state: `candidate` → `draft` → `published` ⇄ `unpublished`. Add `candidate` to
  the existing `argument_status` PG enum and stop writing `pipeline` (PG cannot drop an
  enum value, so `pipeline` remains defined but dead). This preserves the meaning of
  `draft` (operator has approved it) and leaves the three `admin_jobs` guards that key
  on PIPELINE (`api/services/admin_jobs.py:284`, `:577`, `:701`) and the DRAFT-only
  delete gate (`api/services/admin_arguments.py:780`) working with a one-word rename.
  — **Reversibility:** one-way — the enum value and the writer changes ship in a
  migration; reverting needs a reverse migration and PG still cannot remove the value.

- **D-02:** **`draft` is a required stop; a candidate cannot publish directly.**
  Promotion remains one gate at `published_at`; `approve_job` remains the
  candidate → draft step. The Publish control's visibility rule is unchanged
  (`app/src/routes/admin/arguments/[id]/+page.svelte:332` — draft or unpublished only).

- **D-03:** **Candidate birth is logged.** Every argument gets an
  `argument_status_log` row at creation, so status history starts at the first state
  rather than at `draft`. Consequence, accepted deliberately: every argument now
  carries a status-log row, which makes the carried `delete_argument` cascade defect
  reachable for every row — correct behavior once D-15 lands in this same phase, and
  it means the regression test exercises the real path.

- **D-04:** **Candidates stay hidden from `/admin/arguments`.** The PIPELINE/candidate
  exclusion in `list_arguments` and `get_argument_stats`
  (`api/services/admin_arguments.py:94-103`, `:145`) is left exactly as-is, including
  the `valid_status_values` allow-list — hard-exclude, not default-exclude. Phase 49's
  review queue is the screen that was always meant to surface candidates.

- **D-05:** **The delete gate stays DRAFT-only.** This phase does not widen deletion to
  candidates. The reason the gate is DRAFT-only (a live `AdminJob` may still reference a
  candidate — `api/services/admin_arguments.py:766-771`) is unchanged.

### Tier storage + recompute

- **D-06:** **Only `arguments` carries a materialized `trust_tier`.** Utterance and
  participant tiers are derived on the fly during recompute — a utterance's tier is a
  join away (`utterance.import_run_id` → `import_run.source` / `.method`). One
  materialized column means one drift surface. Matches the design note: "Utterance
  inherits its `import_run` provenance … no per-row record needed."
  — **Reversibility:** one-way — the column ships in a migration; adding
  per-constituent columns later is additive, removing this one is not.

- **D-07:** **One shared Python function, no DB trigger.** The pure derivation
  (`derive_tier(source, method, review_state)` plus the floor rollup) lives in
  `api/domain/` alongside the existing shared modules (`person_names.py`,
  `docket_values.py`), unit-testable without a database. A thin service helper
  (`recompute_argument_tier(db, argument_id)`) does the read-constituents-and-store
  step and is called **in the same transaction as the mutation** by every writer —
  pipeline and API alike. Precedent for the pipeline importing an API-side module
  already exists (`api/services/argument_uniqueness.py` is imported by
  `pipeline/commands/import_convokit.py` and `ingest.py`). PL/pgSQL was rejected: it
  would duplicate the vocabulary `api/domain` owns and cannot be exercised by the
  Python suite.

- **D-08:** **The tier stays live after publish; a drop never auto-unpublishes.**
  Published arguments keep recomputing so the stored value is always truthful, but
  nothing removes public content automatically — that stays an operator decision,
  consistent with operator-final-authority. A published argument reading UNCERTAIN is a
  valid state; Phase 49's queue picks it up as needing review.

- **D-09:** **Ship an offline CLI recompute command.** A `pipeline` subcommand
  recomputes tiers (`--all` / single argument). It is the drift-repair tool and doubles
  as the verification vehicle: after `reset_to_fixture`, `recompute --all` must change
  **0 rows**, which positively proves every write path stamped correctly at write time.
  Same shape as Phase 47's D-06 guardrail. Offline CLI, not an HTTP endpoint, per
  CLAUDE.md's pipeline-is-offline-only rule.

### Trust derivation

- **D-10:** **The floor reads only per-argument rows — never `Person` directly.**
  Inputs are `utterances` and `argument_participants`, both scoped to exactly one
  argument. This matches the design note's "floor of its constituent utterances and
  attributions," and it means `recompute_argument_tier` touches exactly one argument by
  construction — no fan-out design, no dirty-marking, no thousands-of-rows recompute
  when a justice's name is edited. Person-level review signals reach the floor only in
  Phase 49, via the participant-level `review_state` that lands there.

- **D-11:** **An unresolved speaker (`person_id IS NULL`) floors the argument to
  UNCERTAIN.** Unattributed speech is precisely the attribution-accuracy failure the
  tier is defined to measure, and it is what gives the gate real teeth on corpus data
  today. Publishing an argument with an anonymous speaker becomes a deliberate, logged
  override rather than an accident.

- **D-12:** **Stage directions are excluded from the floor.** Rows with
  `is_stage_direction = true` have no speaker to attribute and therefore no attribution
  risk. Narrow carve-out keyed on the existing boolean column, documented inside the
  derivation function so it cannot later be mistaken for a bug. Explicitly *not*
  extended to `side = UNKNOWN` rows — those are exactly the rows most likely to be wrong.

- **D-13:** **`review_state` stays in the function signature but is supplied as
  `unreviewed` in Phase 48; no adapter is written.** Verified during scout:
  `argument_participants` has no review or method column today
  (`api/models/models.py:380-392`) — those are Phase 49 additions. Combined with D-10
  (per-argument rows only), there is no per-argument review signal available in this
  phase, so mapping `Person.name_needs_review` through the floor is not possible without
  reintroducing the fan-out D-10 rejects. The signature is final; Phase 49 supplies the
  real column with no signature change. Consequence, accepted: in Phase 48 UNCERTAIN
  arises from unresolved attribution (D-11) and from `pdf_pipeline/llm_corrective` when
  that route returns — not from review flags.

### Publish gate + override

- **D-14:** **Two distinct gates; only the UNCERTAIN one is overridable.**
  `resolved_at IS NULL` (`api/services/admin_arguments.py:591`, T-11-PUBGATE) remains a
  hard precondition with **no** override — an argument whose resolve step never ran is
  incomplete, not a trust judgment call. The UNCERTAIN block is the reviewable gate.
  They report separately so the operator sees which wall they hit. The existing
  already-PUBLISHED guard is unchanged.

- **D-15:** **The override record extends `argument_status_log`.** Add nullable
  `override_reason` (text) and `trust_tier_at_transition` to the existing table.
  Publishing past a block *is* a status transition, so the record belongs on the row
  that transition already writes, and one table answers "what happened to this
  argument." This consciously revisits Phase 15's D-06 minimalism ("no previous_status,
  notes, or triggered_by in v1.5" — `api/models/models.py:497`), which was scoped to
  v1.5 and predates trust entirely. — **Reversibility:** one-way — new columns on an
  audit table ship in a migration.

- **D-16:** **The override is per publish attempt, never sticky.** It authorizes exactly
  the publish it accompanies. An unpublish → republish while still UNCERTAIN requires a
  fresh acknowledgment and writes its own log row with the tier at that moment. No
  persistent per-argument exemption flag exists to outlive the reason it was granted for.

- **D-17:** **A non-empty reason is required, enforced server-side.** A blank
  acknowledgment is just a second click; requiring the operator to state why is what
  makes success criterion 5's "deliberate" real and what makes the log entry worth
  keeping. Free text — not a structured per-constituent acknowledgment (rejected as
  disproportionate UI and schema scope for this phase).

- **D-18:** **No extra guard beyond the existing admin token.** The `X-Admin-Token`
  check already gates every admin write; the override's protection is the required
  reason plus the permanent log row. A typed-confirmation-phrase pattern (as used by the
  Danger Zone delete) was considered and rejected as inconsistent with the rest of the
  admin mutation surface.

- **D-19:** **Minimal frontend, on a page that already exists.** When publish is
  blocked, `/admin/arguments/[id]` shows why (tier + what dragged it down) and offers a
  reason field that re-submits as an override. Without this the gate is a dead end — an
  UNCERTAIN argument would be unpublishable through the app with no recourse. No new
  screens, no new components, no design-system dependency. This is the **only** frontend
  work in the phase.

- **D-20:** **API exposure: detail endpoint + publish-block error.**
  `GET /api/admin/arguments/{id}` returns `trust_tier`; the blocked publish response
  returns the tier plus the blocking reasons. The detail page already fetches that
  endpoint, so the block message needs no new call, and Phase 49's queue inherits a
  field that already works. Admin **list** endpoints stay untouched (consistent with D-04).

### Verification

- **D-21:** **Tests own tier coverage; the live fixture proves the happy path.**
  pytest against `TEST_DATABASE_URL` seeds every tier combination — including UNCERTAIN
  via a NULL `person_id` — and drives the block, the override, and the log row. The live
  `reset_to_fixture` reseed proves the corpus-born path: candidate on arrival, corpus
  rows reading TRUSTED, and `recompute-trust --all` changing 0 rows. Each vehicle proves
  what it can honestly prove. An unresolved-speaker *fixture* was considered and
  rejected: corpus import mints a Person for every corpus speaker, so such a fixture
  would be partly synthetic — exactly the kind of gap Phase 47's D-06 exists to catch.
  (This means STATE.md's 14-UAT Test 8 and 26-UAT Test 26 remain unclosed by this phase.)

- **D-22:** **The carried defect gets a failing-then-passing regression test, not a
  manual repro.** Write the test first — create a DRAFT with an `argument_status_log`
  row, assert `delete_argument` raises `ForeignKeyViolation` — confirming the defect is
  real, then land the one-line fix
  (`delete(ArgumentStatusLog).where(ArgumentStatusLog.argument_id == argument_id)`
  anywhere before the final `Argument` delete) and watch the same test pass. That test
  *is* the live repro: reproducible, in CI forever, and it proves the fix rather than
  asserting it. Phase 31 recommended exactly this test and it was never written. Also in
  scope: correcting the false comment at `scripts/delete_fixture_argument.py:25`, which
  claims "a DRAFT argument can never have one" — that claim is what let the gap survive
  three milestones.

- **D-23:** **A contract test enforces the public-leak ban.** Assert that no public
  response (`/cases`, argument detail, utterances, `/people/{id}`) contains a
  `trust_tier` key — same shape as the existing public schema-contract tests Phase 47
  touched. This turns the apolitical hard constraint into something that fails a build
  rather than something someone has to remember.

### Migration

- **D-24:** **The migration flips any `status=pipeline` rows to `candidate`** in the
  same migration that adds the enum value, so no code ever has to read `pipeline` again
  and the dead value is genuinely dead.

### Claude's Discretion

The operator explicitly left these to me. Recorded with the lean so planning does not
re-open them:

- **How `trust_tier` arrives (operator: "I'm not concerned about existing arguments. We
  are going to be resetting to the fixture multiple times during development so I don't
  see much value in migration at this point. I leave this decision to you").**
  **Lean: NOT NULL with server default `uncertain`, no in-migration derivation.**
  Fail-closed — an unclassified row must read as *blocked from publishing*, never as
  publishable — and zero backfill logic, since the fixture reset settles real values and
  `recompute-trust --all` reports exactly what was unclassified. In-migration derivation
  is rejected because it would duplicate in SQL the logic D-07 deliberately centralizes
  in `api/domain`.
- **Review-dimension sourcing (originally "you decide"; effectively resolved by D-10 —
  see D-13).** Research should confirm the D-13 finding that no per-argument review
  signal exists today before planning locks it.
- **`trust_tier` column representation** — native PG enum (matches the existing
  `SAEnum(..., values_callable=...)` pattern and Phase 47's precedent) vs. ordered
  smallint (makes `MIN()` a native floor operation and evolves without the
  cannot-drop-a-value problem). Genuine trade-off; the floor semantics argue for
  smallint, project consistency argues for the enum. Left to research/planning.
- **What tier an argument with zero utterances carries** — not settled. Should follow
  the same fail-closed instinct as the column default unless research finds a reason
  otherwise.
- **Endpoint shape for the override** — whether the reason rides on the existing
  `POST .../publish` body or gets its own route. Implementation detail.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design (the worked-out model — read first)
- `.planning/notes/provenance-and-trust-model.md` — The trust tier table, the derivation
  order (`review_state` wins first, then source/method), the floor-rollup rule, the
  authority ladder, and the "operator work is sacred" invariant. **Column names are
  illustrative — Alembic is the sole DDL authority.** Its open questions 1/2/4 are
  already settled (four review states, hard gate with logged override, materialized
  tier) — do not re-open them.
- `.planning/notes/import-entity-sketch.md` — The target ER sketch. Phase 48 delivers
  the `ARGUMENT.trust_tier` [NEW] and `status: candidate` [CHG] rows of that sketch;
  `ARGUMENT_PARTICIPANT.review_state` / `.method` are Phase 49.
- `.planning/notes/import-architecture-diagnosis.md` — Why the re-model exists; the
  targeted-re-model-not-a-rewrite boundary.

### Prior phase context
- `.planning/phases/47-provenance-foundation/47-CONTEXT.md` — The `import_run` /
  `source` / `method` vocabulary this phase derives trust from, and the D-06
  verification-must-cover-every-combination lesson that shaped D-21.

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — TRUST-01 … TRUST-05.
- `.planning/ROADMAP.md` §"Phase 48: Trust & Lifecycle" — goal, five success criteria,
  and the full write-up of the carried `delete_argument` defect (lines 204-225).
- `.planning/STATE.md` — carry-forward constraints; the `argument_status` enum warning;
  the still-unverified `alembic current` vs. head `0026` check (run it before planning
  migrations).

### Code touch points (verified during scout)
- `api/models/models.py:83` — `ArgumentStatusEnum` (pipeline/draft/published/unpublished).
- `api/models/models.py:303-311` — `Argument.published_at`, `.status`.
- `api/models/models.py:380-392` — `ArgumentParticipant`: **no** review or method column
  today (the D-13 finding).
- `api/models/models.py:494-514` — `ArgumentStatusLog`, deliberately minimal (D-06 of
  Phase 15); the table D-15 extends.
- `api/models/models.py:149-150` — `Person.name_needs_review` / `name_extraction_metadata`
  (the Phase 49 generalization target, not used by this phase per D-13).
- `api/services/admin_arguments.py:570-616` — `publish_argument`, the existing gate and
  status-log write; where D-14/D-15/D-17 land.
- `api/services/admin_arguments.py:744-810` — `delete_argument`, the FK-ordered cascade
  missing the `ArgumentStatusLog` step (D-22).
- `api/services/admin_arguments.py:88-160` — `list_arguments` / `get_argument_stats`
  status exclusions (left untouched per D-04).
- `api/services/admin_jobs.py:577-591` — `approve_job`: the candidate → draft transition,
  `resolved_at` stamp, and the existing DRAFT status-log write.
- `pipeline/commands/import_convokit.py:507-570` — corpus argument creation
  (`status=ArgumentStatusEnum.PIPELINE` at `:515`) — the born-candidate write site.
- `api/domain/person_names.py`, `api/domain/docket_values.py` — the shared pure-domain
  precedent D-07 follows.
- `api/services/argument_uniqueness.py` — precedent for the pipeline importing an
  API-side service module.
- `app/src/routes/admin/arguments/[id]/+page.svelte:295-361` — the Status card and
  Publish control; the only frontend surface D-19 touches.
- `scripts/delete_fixture_argument.py:25` — the false comment D-22 corrects.
- `CLAUDE.md` — Alembic sole DDL authority; pipeline offline-only; apolitical hard
  constraint; the rootdir `conftest.py` test-isolation rule.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/domain/` — the existing pure shared layer both the API and the offline pipeline
  import. The natural home for the trust derivation function (D-07).
- Phase 43 `reset_to_fixture` + the Phase 41 four-fixture set — the live verification
  vehicle for D-21's happy path, already proven in Phase 47.
- `ArgumentStatusLog` — an audit table that already exists and is already written on
  every publish; D-15 extends it rather than adding a parallel record.
- `SAEnum(..., values_callable=...)` — the established PG enum declaration pattern, if
  a native enum is chosen for `trust_tier`.
- The existing `resolved_at IS NULL` publish gate and its T-11-PUBGATE test — the shape
  D-14's second gate mirrors.

### Established Patterns
- Alembic is the sole DDL authority; PG cannot drop enum values, which is why D-01 adds
  `candidate` rather than renaming `pipeline`.
- Bulk `update()` / `delete()` always use `.execution_options(synchronize_session=False)`,
  and a `db.refresh()` follows when the same session re-reads the row afterward
  (`publish_argument` documents this at `:606-615`) — recompute-then-read paths must
  respect it.
- The test suite runs against `scotus_test` via `TEST_DATABASE_URL` with a rootdir
  `conftest.py` that fails any run changing shared-dev-DB row counts. Every DB-gated
  test D-21/D-22 adds must respect that isolation.
- Public response models are explicit Pydantic allow-lists — structurally safe, which
  D-23 converts into an asserted guarantee.

### Integration Points
- Write paths that must call recompute in-transaction: corpus import (birth),
  `approve_job` (candidate → draft, stamps `resolved_at`), resolve-row and participant
  edits, and publish itself.
- `publish_argument` gains the UNCERTAIN gate, the reason parameter, and the extended
  log write.
- `get_argument_detail` gains `trust_tier` in its response (D-20).
- The new `pipeline` CLI subcommand joins the existing offline command set.

</code_context>

<specifics>
## Specific Ideas

- The operator's framing on migrations: "I'm not concerned about existing arguments. We
  are going to be resetting to the fixture multiple times during development so I don't
  see much value in migration at this point." Backfill effort is unwarranted here —
  design for the reseed, not for legacy rows.
- Verification should be positive and falsifiable, following Phase 47's lesson:
  `recompute-trust --all` changing **0 rows** after a fresh reseed is the assertion that
  every writer stamped correctly, not an absence-of-drift hand-wave.
- The publish-block message should say *what* dragged the tier down (e.g. "3 utterances
  have no resolved speaker"), not just report the tier — a bare "UNCERTAIN" gives the
  operator nothing to act on.

</specifics>

<deferred>
## Deferred Ideas

- **Candidate visibility and any tier badge in the admin UI** → Phase 49's review queue
  (D-04). Includes adding `candidate` to the list filter's `valid_status_values`.
- **Widening the delete gate to candidates** → Phase 50, where re-import idempotency
  decides whether cleanup is delete-and-reimport or update-in-place (D-05).
- **Person-level review signals reaching the argument floor** → Phase 49, via
  participant-level `review_state` (D-10/D-13).
- **Auto-unpublish when a published argument's tier drops** — considered and rejected as
  a behavior change too large to bury in this phase (D-08). Revisit only if a live
  UNCERTAIN-but-published row proves to be a real problem.
- **A PostgreSQL trigger as a belt-and-braces recompute safety net** — rejected for now
  (D-07); a plausible addition once Phase 50 settles the write paths.
- **An unresolved-speaker fixture** — rejected as partly synthetic (D-21). It remains the
  missing ingredient for STATE.md's 14-UAT Test 8 and 26-UAT Test 26, both of which stay
  open after this phase.
- **A structured, per-constituent override acknowledgment** — rejected as disproportionate
  scope (D-17); free text is enough for now.

### Reviewed Todos (not folded)

All five phase-48 keyword matches were reviewed and deliberately **not** folded — the
matches were generic keyword/area overlap, not subject-matter fit. They remain
`/gsd-review-backlog` material:

- `2026-08-11-create-person-popover-side-and-selection.md` (ui, minor) — Resolve card
  popover polish; no trust or lifecycle content.
- `2026-08-12-speaker-popover-frontend-duplication-cleanup.md` (ui, low) — frontend
  duplication; this phase touches one existing page only.
- `2026-08-12-speakers-bench-classification-silent-fallback.md` (api, low) — trust-adjacent
  in spirit (a silently wrong label is what a tier should catch), but it is a
  classification bug in the read path, not lifecycle scope.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (dev-environment, low) — unrelated.
- `2026-08-18-pdf-provenance-live-fixture-verification.md` (pipeline, minor) — explicitly
  deferred with the PDF route under the corpus-first scope decision.

</deferred>

---

*Phase: 48-Trust & Lifecycle*
*Context gathered: 2026-08-18*
