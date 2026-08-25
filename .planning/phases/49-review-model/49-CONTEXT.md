# Phase 49: Review Model - Context

**Gathered:** 2026-08-21
**Status:** Ready for planning

<domain>
## Phase Boundary

The operator gets a real review workflow over the candidate pool. Operator-editable
rows — `argument_participants` and `people` name-parts — carry a four-state
`review_state` (unreviewed / needs_review / operator_confirmed / operator_edited) plus
their own `source` + `method`, folding today's `name_needs_review` /
`name_extraction_metadata` into the unified review_state + provenance record with no
parallel mechanism left. A disagreement between an incoming value and a stored one at
equal-or-higher authority records a **discrepancy** for operator attention instead of
overwriting. A new `/admin/review` queue lists everything needing attention, filterable
by trust tier × review state × status; resolving an item (confirm or edit) advances its
`review_state`, closes its open discrepancies, and recomputes the argument's trust.
"Operator work is sacred" is the invariant throughout.

**In scope:**
- Shared `review_state` PG enum on `people` and `argument_participants` (D-09, D-10)
- `source` + `method` columns on `argument_participants` (D-19)
- `Person.review_state` + `provenance_metadata` **replacing** `name_needs_review` and
  `name_extraction_metadata` outright (D-08, REVIEW-05's no-parallel-mechanism rule)
- A `discrepancy` table keyed on (target row, field, import_run) with its own
  `resolved_at` (D-13, D-15)
- One real authority-checked writer for the discrepancy path — the participant/person
  update path — so nothing ships uncalled (D-21)
- `derive_tier` fed a real per-participant `(source, method, review_state)` triple;
  the Phase 48 D-13 slot is filled with **no signature change** (D-18)
- New `/admin/review` route: Arguments | People tabs, expandable argument rows,
  inline confirm, deep-linked edit, tier × review_state × status filters (D-01 … D-07)
- An explicit **confirm-as-unattributable** action that lifts the D-11 unresolved-speaker
  floor (D-17)
- An unresolved-speaker fixture, closing 26-UAT Test 26 and 14-UAT Test 8 (D-23)
- Widening participant editability to all unpublished states (folded todo)
- One cleanup plan: create-person popover side/selection, Admin Help status diagram,
  Status-card "Created" mislabel (folded todos)

**Out of scope:**
- Corpus/PDF import rework, `admin_job` re-point, making re-import compare-and-record
  instead of skip-existing → Phase 50 (D-21)
- The legacy `admin_jobs.discrepancies` blob and ResolveCard's HIT/MISS rendering —
  a different concept that happens to share a name; left untouched (D-14)
- Wiring the PDF alias-HIT participant method; the mapping is recorded, not built
  (D-20), consistent with the corpus-first scope decision
- Design system, shared component extraction, listing restyle → Phase 51 (D-06)
- Candidate visibility on `/admin/arguments` — 48 D-04's exclusion stands (D-05)
- Any public-facing display of `review_state` or trust — permanently out of scope

</domain>

<decisions>
## Implementation Decisions

### Queue shape

- **D-01:** **A queue row is an argument, expandable to its flagged constituents.**
  Top level shows case name, tier badge, and a needs-attention count; expanding lists
  the participants / names the operator acts on. This satisfies REVIEW-03 (list items
  needing review) and REVIEW-04 (resolving an *item* advances *its* review_state)
  without choosing between them. A flat per-constituent list was rejected because one
  bad argument fans out into many rows that repeat the same argument context; an
  argument-only list was rejected because it degrades the queue into a list of links.

- **D-02:** **Arguments | People are separate tabs on one screen.** A person spans many
  arguments, so the two entity shapes need different columns; a single mixed list goes
  sparse. Mirrors the existing Bench/Advocate tab pattern on `/admin/people`. Leaving
  person-name review behind the existing `/admin/people` "name review" filter
  (`api/services/admin_people.py:244`) was rejected — that splits REVIEW-03's "every
  item needing review" across two screens.

- **D-03:** **Default sort is worst tier first** (UNCERTAIN → PROVISIONAL → TRUSTED),
  then oldest `argued_date` within tier. Puts what blocks publishing at the top, which
  is what the tier exists to signal.

- **D-04:** **The queue is unbounded, like every other admin list.**
  `/admin/arguments` and `/admin/people` are both unbounded today; stay consistent and
  revisit when it hurts. Server-side paging was rejected as a new pattern to establish
  in a phase that already carries schema work. *Known tension, recorded deliberately:*
  this is the one screen guaranteed to be large on a corpus of thousands — if research
  finds the unbounded query is already slow against the real corpus, raise it rather
  than shipping it.

- **D-05:** **Inclusion is "attention-worthy", not "flagged only":** `review_state =
  needs_review` **OR** an unresolved `person_id` **OR** an argument `trust_tier` below
  TRUSTED. Flagged-only was rejected because nothing sets `needs_review` on a
  participant today, so the queue could ship empty; the whole-unreviewed-pool reading
  was rejected because on a corpus of thousands it never looks finishable.
  48 D-11's unresolved-speaker floor is the main UNCERTAIN source on corpus data, so
  the unresolved leg is what gives the queue real content on day one.

- **D-06:** **Published-but-degraded arguments are included, badged, and floated to the
  top.** An UNCERTAIN argument that is already public is the most urgent row in the
  queue. This is what fulfils 48 D-08's promise ("Phase 49's queue picks it up as
  needing review") — excluding them would leave that promise unkept.

- **D-07:** **Filters are trust tier × review state × status.** Status is beyond
  REVIEW-03's literal wording and is included on purpose: candidates are invisible
  everywhere else (48 D-04), and published-but-degraded rows need isolating. Side and
  entity-type filters were rejected as combinatorics for a phase that already has
  schema scope — and `side` has a known silent-fallback bug (todo 2026-08-12).

### Legacy fold (REVIEW-05)

- **D-08:** **`Person` gets `review_state` + `provenance_metadata`, replacing
  `name_needs_review` and `name_extraction_metadata` outright.** The entity sketch's
  `[CHG]` rows. Person-level review reaches the argument floor only via
  `ArgumentParticipant`, so this does not violate 48 D-10's never-read-Person rule.
  Keeping the legacy bool as a derived view was rejected — that *is* the parallel
  mechanism REVIEW-05 exists to remove.
  — **Reversibility:** one-way — dropping two columns and adding two ships in a
  migration; the People-directory filter, the `missing` allow-list, and the admin
  people schemas all read the old names today.

- **D-09:** **One shared `review_state` PG enum used by both `people` and
  `argument_participants`.** Matches the established
  `SAEnum(..., values_callable=lambda e: [x.value for x in e])` pattern used for
  `argument_status` and `trust_tier`. One type, one vocabulary, one place to extend.
  A varchar + CHECK was genuinely considered — it dodges PG's cannot-drop-an-enum-value
  problem this project has now hit twice — and rejected for pattern consistency.
  — **Reversibility:** one-way — a PG enum type ships in a migration and its values
  cannot later be dropped.

- **D-10:** **`argument_participants` gains `review_state`** — filling the column
  48 D-13 predicted and deferred. Confirmed absent during scout
  (`api/models/models.py:392`).

- **D-11:** **A name edit sets `operator_edited`; a new explicit Confirm action sets
  `operator_confirmed`.** This replaces the current
  `person.name_needs_review = False` at `api/services/admin_people.py:545`. The edit
  path always means *edited* — no value-diffing guesswork, no normalization ambiguity —
  and the queue needs an explicit Confirm affordance anyway (D-16), so both states get
  an honest producer. Diffing submitted-vs-stored parts to distinguish them was
  rejected as fragile given `prepare_person_name`'s normalization sits in the middle.

- **D-12:** **Phase 38 D-15's metadata rule carries over unchanged:** an operator edit
  never clears or rewrites `provenance_metadata`. It stays a durable, append-nothing
  audit trail of the extraction/migration decision — the direct ancestor of "operator
  work is sacred." Appending operator actions to it was rejected: `review_state` now
  records the human action, and unbounded JSONB growth would partly duplicate what
  `argument_status_log` does for arguments.

### Discrepancy record (REVIEW-02)

- **D-13:** **A discrepancy gets its own table**, keyed on target row (entity type +
  id), field, and `import_run_id`, carrying incoming value, existing value, incoming
  source/method, and timestamps. Queryable and joinable to the queue, per-value rather
  than per-batch — which is what "records a discrepancy for operator review" needs.
  JSONB on `import_run` was rejected because you cannot filter the queue by "has an
  unresolved discrepancy" without unnesting JSON; JSONB on the target row was rejected
  because it cannot answer "what did this run disagree about" and it bloats hot rows.
  — **Reversibility:** one-way — a new table ships in a migration.

- **D-14:** **The existing `admin_jobs.discrepancies` blob is left completely alone.**
  It is the PDF resolve step's HIT/MISS review payload (`pipeline/commands/resolve.py`,
  `app/src/lib/components/ResolveCard.svelte`) — a different thing that happens to share
  a name. It sits on the deferred PDF route, and Phase 50 owns re-pointing `admin_job`.
  Migrating or renaming it here would drag ResolveCard's whole HIT/MISS rendering into a
  corpus-focused phase for no gain. *Naming collision accepted for now* — planning
  should ensure the new table's name and the code comments make the distinction
  unmissable.

- **D-15:** **Resolving the row closes its open discrepancies in the same transaction,
  and each discrepancy still carries its own `resolved_at`.** One operator action, no
  second accept/reject workflow — "accept the incoming value" *is* an edit and "reject
  it" *is* a confirm, both of which already exist. The per-row `resolved_at` is not
  optional bookkeeping: without it, a later re-import that disagrees again is
  indistinguishable from the stale one already dealt with, and the queue either nags
  forever or goes quiet when it shouldn't. Cardinality note for planning: the natural
  key is (row, field, run), so typically one per row per run, but a corpus re-import can
  disagree on `last_name` *and* `name_suffix`, or on `person_id` *and* `side`, at once —
  never assume one.

- **D-16:** **Discrepancies are also recorded when a lower-authority incoming value is
  rejected outright.** This is the design note's worked example verbatim: the corpus
  disagrees with an operator fix, the fix stands, "and the operator sees a note that the
  corpus disagrees." Silent rejection means you never learn the corpus changed its mind.

### Review → trust precedence

- **D-17:** **An explicit "confirm as unattributable" action lifts the floor; a normal
  confirm does not.** `derive_tier` rule 1 wins as written — but only via a distinct
  action, never as a side effect of an ordinary confirm. Two corpus fixtures (15169,
  22372) already read UNCERTAIN solely because of ConvoKit's own unattributed-speaker
  sentinel rows; without this path they need a publish override forever, which would
  make 48 D-16/D-17's "deliberate" override routine and devalue it. `review_state =
  operator_confirmed` on that row is the permanent record that the operator judged the
  speaker genuinely unidentifiable in the source. Note for planning: this means
  `api/services/trust.py:95` and `:105`'s NULL-`person_id` shortcut can no longer bypass
  `review_state` unconditionally — it must consult it.

- **D-18:** **A resolved participant runs through the full
  `derive_tier(source, method, review_state)`.** Today `api/services/trust.py:108`
  contributes nothing for a resolved participant (48 D-13, no source/method existed).
  With D-19's columns in place the designed path opens, and 48 D-13's promise holds
  exactly: **no signature change**. Contributing only via `review_state` was rejected
  because the row then cannot state its own provenance; contributing nothing-unless-
  flagged was rejected because an operator's confirm could then never lift an argument
  out of UNCERTAIN, undercutting REVIEW-04's "recomputes trust."

- **D-19:** **`argument_participants` stores both `source` and `method`.** The design
  note's "provenance sits where values diverge." Inheriting `source` from the argument's
  `import_run` was rejected because an argument accumulates runs over time (Phase 50
  makes re-import routine), so inheritance has no single answer; implying source from
  method was rejected because `normalized` legitimately applies to both corpus and pdf.
  — **Reversibility:** one-way — two columns ship in a migration.

- **D-20:** **Participant `method` reuses the existing `ImportMethod` vocabulary
  verbatim** — no new enum, no mapping layer, `derive_tier` already keys on it. The
  mapping, which closes the entity sketch's last open item:

  | Mechanism | Code site | source / method | Tier |
  |---|---|---|---|
  | corpus `oyez_speaker_id` match | `import_convokit.py:763` | `corpus` / `direct` | TRUSTED |
  | corpus `full_name` fallback | `import_convokit.py:745` (D-13) | `corpus` / `direct` | TRUSTED |
  | corpus new person created | `import_convokit.py:782` | `corpus` / `direct` | TRUSTED |
  | PDF alias-table HIT | `resolve.py:227` | `pdf_pipeline` / `normalized` | PROVISIONAL |
  | MISS / unresolved | — | NULL `person_id` | UNCERTAIN (D-11) |
  | operator popover assignment | `admin.py:1423` | unchanged; `review_state` carries it (D-22) | VERIFIED via rule 1 |

  **The corpus `full_name` fallback gets `direct` → TRUSTED. This is settled, and the
  reasoning matters — do not re-open it.** The initial recommendation was `normalized` →
  PROVISIONAL on the theory that a name-string match is weaker evidence than an
  authoritative external ID. The operator challenged it with the right question — *how
  often does this actually happen?* — and reading the code answers it decisively against
  the recommendation:

  - **The branch is self-extinguishing.** `import_convokit.py:774` backfills
    `oyez_speaker_id` on a `full_name` match. Each person can therefore traverse that
    path **at most once, ever**; every later argument matches by ID. It is a one-time
    first-encounter handshake, not a recurring class of weaker links.
  - **It is not stage directions or laughter.** Those never reach `_resolve_person`:
    unattributed speakers are skipped (`:861`, `unattributed_speakers_skipped`) and
    stage directions are utterance rows with no speaker (`:1093`).
  - **The population that hits it is the most trustworthy cohort in the database** —
    justices seeded from the curated CSV (`import_justices_csv.py` creates them with no
    `oyez_speaker_id`) and operator-created people (same reason). Plus, rarely, two
    distinct Oyez IDs sharing an identical `full_name`: a genuine collision, and exactly
    the White/Black/Clark/Douglas dedup mismatch explicitly out of v1.8 scope.

  So `normalized` would have tiered **down** the seed-justice and operator-created rows
  on a first-encounter-only basis, yielding a tier that flips to TRUSTED on the next
  import of the same person. That is not a trust signal, it is a race with the backfill.
  `direct` is correct. (Optional confirmation for research, not a blocker: count
  `people` rows with `oyez_speaker_id IS NULL`, and any duplicate `full_name` values, to
  size the cohort — the existing `people_matched` counter cannot distinguish the two
  reuse paths, so it cannot answer this.)

  **Two consequences to carry forward rather than rediscover:** (1) a corpus participant
  reads TRUSTED regardless of *how* its link was made, so `method` on a participant only
  ever varies for the operator and PDF paths — it still earns its place as a record of
  how, and Phase 50 needs it, but it is not a tier discriminator on corpus data; (2) an
  accepted asymmetry — a corpus name match reads TRUSTED while a PDF alias HIT, also a
  name-string match, reads PROVISIONAL. Defensible (corpus rows carry corroborating
  authoritative external IDs and the match self-extinguishes; the alias table is a
  standing heuristic bridge over PDF text that fires on every run) and recorded here so
  it is not later filed as a bug.

- **D-21:** **The PDF alias-HIT mapping is recorded, not built.** `pdf_pipeline` /
  `normalized` is documented (D-20's table) and the wiring stays on the deferred PDF
  route with todo `2026-08-18-pdf-provenance-live-fixture-verification.md`. It cannot be
  proven live — no PDF fixture exists in the repo. Consistent with the corpus-first
  scope decision.

- **D-22:** **An operator edit does NOT overwrite the row's stored `source`/`method`.**
  The row keeps its original provenance as a durable record of where the value came
  from; the authority ladder reads operator-authority off
  `review_state ∈ {operator_confirmed, operator_edited}`. This is exactly how the design
  note's worked example derives it ("Authority check: incoming `corpus` < existing
  `operator`" — where *existing* is operator because it was `operator_edited`).
  Consequence, accepted: 48's `derive_tier` rule 3 (`operator`/`manual` → VERIFIED)
  stays unreachable, which 48 documented as intentional — "it exists so the mapping is
  total." Overwriting to `operator`/`manual` was rejected because the original
  provenance would survive only in the discrepancy record, not on the row; storing both
  was rejected because two columns answering "what authority is this row" is the exact
  ambiguity the re-model exists to remove.

### Actions and reversibility

- **D-23:** **Confirm is inline; edit deep-links.** "Looks right" is one inline click on
  the queue row (a single PATCH, no form). Changing a person link deep-links to the
  argument's Resolve card, where `SpeakerPopover` + person search + create-person
  already work. Rebuilding the hardest UI in the app in a second place was rejected —
  there is already an open todo about duplication in that stack
  (`2026-08-12-speaker-popover-frontend-duplication-cleanup.md`). Triage-only (every
  action a deep link) was rejected because a round-trip per item *is* the job on a
  corpus sweep.

- **D-24:** **No bulk confirm.** `operator_confirmed` means "a human checked this" —
  which is the claim the VERIFIED tier rests on. A bulk button makes that claim cheap
  and unfalsifiable. Per-item only, even at corpus scale.

- **D-25:** **Re-flagging to `needs_review` is allowed; returning to `unreviewed` never
  is.** An operator can push a row back for another look, but once a human has touched
  it that fact is permanent — which keeps the audit meaning of `unreviewed` intact. A
  full reset was rejected because it turns `review_state` into a mutable label rather
  than a record of what happened. Note: this means a mistaken confirm is corrected by
  re-flagging, not by erasing.

- **D-26:** **A resolved row stays visible with its new state until reload.** The row
  remains with its updated `review_state` and recomputed tier so the operator can see
  what they just did and catch a mis-click; rows leave only on refresh/refilter.

### Placement and UI

- **D-27:** **A new top-level `/admin/review` route**, in `AdminSubNav` alongside
  Arguments / People / Pipeline. The queue's row unit (constituents), filters
  (tier × review_state × status) and audience (candidates) are all different from
  `/admin/arguments`; bolting it on would mean two lists fighting over one page.

- **D-28:** **48 D-04's candidate exclusion on `/admin/arguments` stays exactly as-is.**
  The review queue is the screen candidates were always meant to appear on — precisely
  what 48 D-04 anticipated. `list_arguments` / `get_argument_stats`
  (`api/services/admin_arguments.py:94-103`, `:145`) and the `valid_status_values`
  allow-list are untouched, so nothing regresses and no existing stat card changes
  meaning.

- **D-29:** **Build it in today's admin idiom** — inline styles, the palette in
  `.planning/codebase/DESIGN-SYSTEM.md`, no component library, no new abstractions.
  Phase 51 reworks it along with everything else. Extracting shared components here was
  rejected as widening a schema+workflow phase into a refactor; a `/gsd-ui-phase` pass
  was considered and declined.

- **D-30:** **Entry points: an `AdminSubNav` link plus a dashboard count** in the
  existing `StatCard` shape, so pending work is visible without navigating.

### Verification (REVIEW-02's proof)

- **D-31:** **Phase 49 builds the record, the display, and one real authority-checked
  writer.** The writer is the participant/person update path — so the discrepancy
  mechanism has a genuine production caller from day one. Phase 50 then wires corpus
  re-import through the same function rather than inventing one. Record-and-display-only
  was rejected: that is exactly how 48's `derive_tier` rule 3 shipped unreachable for a
  whole phase. Building corpus compare-and-record here was rejected as annexing the core
  of Phase 50. **Grounding fact from scout:** `pipeline/commands/import_convokit.py:493`
  skips existing arguments outright (counter `skipped_existing`), so no code path today
  compares an incoming value against a stored one.

- **D-32:** **pytest for the authority matrix, plus one live authority-conflict
  walkthrough.** pytest against `TEST_DATABASE_URL` covers every rung of the ladder
  exhaustively; one live browser pass creates a real conflict through the admin UI
  (operator edits a corpus value, a second writer disagrees) so the queue is *observed*,
  not asserted. Each vehicle proves what it can honestly prove — 48 D-21's shape, and
  the direct lesson of Phase 48, where **three of the phase's defects were found by
  operator browser testing and none by the 1209-test suite**.

- **D-33:** **Build the unresolved-speaker fixture and close 26-UAT Test 26 and 14-UAT
  Test 8.** 48 D-21 rejected such a fixture as "partly synthetic" because corpus import
  mints a Person for every corpus speaker. That objection weakens here: this phase makes
  unresolved participants first-class — they are the main thing the queue exists for
  (D-05) — so the fixture becomes representative rather than contrived. Closes two items
  open since June 2026. 26-UAT Test 26's code is confirmed present at
  `app/src/routes/admin/arguments/[id]/+page.svelte:497,544` and has never been
  exercised in a browser.

- **D-34:** **The public-leak ban extends to `review_state`.** 48 D-23's contract test
  asserts no public response carries a `trust_tier` key; the same test grows to cover
  `review_state`, `source`, `method`, and any discrepancy field. Trust and review are
  operator-facing only — the apolitical hard constraint, enforced as a failing build
  rather than a thing someone remembers.

### Claude's Discretion

The operator left these to me, or they were not raised. Recorded with the lean so
planning does not re-open them:

- **Migration defaults and backfill.** **Lean:** follow 48's precedent exactly —
  `review_state` NOT NULL with `server_default 'unreviewed'`, no in-migration
  derivation, no backfill effort beyond the one deterministic legacy mapping. The
  operator's Phase 48 framing stands: "I'm not concerned about existing arguments. We
  are going to be resetting to the fixture multiple times during development." The one
  mapping that *is* required by REVIEW-05: `Person.name_needs_review = true` →
  `review_state = 'needs_review'` (per the design note's backfill table), and
  `name_extraction_metadata` → `provenance_metadata` as a straight column carry.
- **Endpoint shapes** — the queue's list endpoint, the inline-confirm PATCH, and the
  confirm-as-unattributable action (own route vs. a flag on the confirm body).
  Implementation detail.
- **Whether the queue's tier/status/review filters reuse the segmented-control pattern**
  from `/admin/arguments` (`+page.svelte:170-224`) or a plain select set. **Lean:** reuse
  the segmented control for status, plain selects for the two new axes — three segmented
  controls side by side would dominate the page.
- **The discrepancy table's name.** **Lean:** something that cannot be confused with
  `admin_jobs.discrepancies` (D-14) — e.g. `value_discrepancy` — with a docstring
  stating the distinction explicitly.
- **Whether the dashboard count (D-30) is a separate aggregate query or derives from the
  queue endpoint.** **Lean:** a dedicated COUNT, in the shape of
  `get_argument_stats` — the queue list is unbounded (D-04) and must not be fetched just
  to produce a number.

### Folded Todos

Four pending todos folded, with a deliberate split (operator decision): the editability
widening belongs *inside* the review work because it is a prerequisite for resolving
items from the queue; the other three are independent and group into a single low-risk
cleanup plan at the end of the phase.

**Inside the review work:**
- `2026-08-21-widen-participant-editability-to-all-unpublished-states.md` — participants
  should be editable in every state except published, not only in `candidate`. Filed at
  Phase 48 close as an operator-requested design-scope change, deliberately not
  implemented there. It sits directly in the path of D-23's confirm/edit flow: a queue
  that surfaces `draft` and `unpublished` arguments (D-07) but cannot edit their
  participants would be a dead end.

**Cleanup plan (end of phase):**
- `2026-08-11-create-person-popover-side-and-selection.md` (ui, minor) — the
  create-person popover should inherit the row's Bench/Advocate side as its default and
  visibly select the newly created person. Lands where D-23's edit path terminates.
- `2026-08-19-admin-help-status-diagram.md` (ui) — an Admin Help page diagramming
  statuses, tiers, and publish gates. `review_state` is now a third axis on top of
  `status` and `trust_tier`; the vocabulary has outgrown what fits in one's head.
- `2026-08-20-argument-status-card-labels-resolved-at-as-created.md` (ui) — the Status
  card labels `resolved_at` as "Created"; `Argument` has no `created_at` column. Small
  correctness fix on a card this phase touches anyway.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design (the worked-out model — read first)
- `.planning/notes/provenance-and-trust-model.md` — the four `review_state` values
  (§"The provenance record" #4), the authority ladder and its record-a-discrepancy rule
  (§"The authority ladder"), the derivation order, the granularity rule that puts
  provenance on `ArgumentParticipant` and `Person` (§"Granularity"), the worked example
  D-16/D-22 both derive from, and the old→new backfill table. **Column names are
  illustrative — Alembic is the sole DDL authority.** Its open question 1 (four review
  states) is settled; do not re-open it.
- `.planning/notes/import-entity-sketch.md` — the target ER sketch. Phase 49 delivers
  the `ARGUMENT_PARTICIPANT.review_state` / `.method` `[NEW]` rows and the
  `PERSON.review_state` / `.provenance_metadata` `[CHG]` rows. Its last open item
  ("exact `method` vocabulary on ARGUMENT_PARTICIPANT") is closed by D-20's table.
- `.planning/notes/import-architecture-diagnosis.md` — why the re-model exists; the
  targeted-re-model-not-a-rewrite boundary.

### Prior phase context (both directly load-bearing)
- `.planning/phases/48-trust-lifecycle/48-CONTEXT.md` — D-04 (candidate exclusion is
  this phase's to relax or keep — D-28 keeps it), D-08 (published-but-UNCERTAIN belongs
  in this queue — D-06), D-10 (the floor never reads `Person` directly — D-08 respects
  it), D-11 (unresolved speaker floors to UNCERTAIN — D-17 qualifies it), D-13 (the
  `review_state` slot this phase fills, with no signature change — D-18), D-21 (the
  rejected unresolved-speaker fixture — D-33 revisits it), D-23 (the public-leak
  contract test — D-34 extends it).
- `.planning/phases/47-provenance-foundation/47-CONTEXT.md` — the `import_run` /
  `source` / `method` vocabulary D-19/D-20 reuse, and the D-06
  verification-must-cover-every-combination lesson behind D-31/D-32.

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — REVIEW-01 … REVIEW-05 (lines 31-35).
- `.planning/ROADMAP.md` §"Phase 49: Review Model" (lines 262-281) — goal and the five
  success criteria.
- `.planning/ROADMAP.md` §"Phase 50: Unified Import Path" (lines 282-300) — read the
  boundary: Phase 50 owns making re-import compare-and-record, and carries a scope flag
  splitting its PDF half onto the deferred route.
- `.planning/STATE.md` — carry-forward constraints; the `argument_status` PG-enum
  cannot-drop warning that also applies to D-09; the two never-observed UAT items D-33
  closes; the Phase 48 open item about corpus fixtures 15169/22372 reading UNCERTAIN via
  ConvoKit sentinel rows (the case D-17 exists for).

### Code touch points (verified during scout, 2026-08-21)
- `api/models/models.py:149-150` — `Person.name_needs_review` /
  `name_extraction_metadata`, the two columns D-08 replaces.
- `api/models/models.py:392` — `ArgumentParticipant`, confirmed to have **no**
  `review_state`/`method`/`source` column today (48 D-13's finding, re-verified).
- `api/models/models.py:322-330` — `Argument.trust_tier` as shipped by Phase 48.
- `api/domain/trust.py` — `derive_tier` (rules 1-7, precedence order), `floor_tier`,
  and the `UNREVIEWED` literal D-18 replaces with real per-participant values. **The
  signature does not change** (48 D-13).
- `api/services/trust.py:54-140` — `_load_constituents` / `recompute_argument_tier`.
  Specifically `:95` and `:105`, where NULL `person_id` appends UNCERTAIN *without*
  consulting `review_state` — the lines D-17 must change — and `:108`, where a resolved
  participant contributes nothing, which D-18 replaces.
- `api/services/admin_people.py:244` — the `missing_filters` allow-list entry
  `"name review": Person.name_needs_review.is_(True)`, which D-08 must re-point.
- `api/services/admin_people.py:545` — `person.name_needs_review = False` on an
  authoritative name edit (Phase 38 D-12), the line D-11 replaces; and `:475-480`'s
  docstring stating Phase 38 D-15's never-rewrite-metadata rule that D-12 carries.
- `api/services/admin_people.py:340`, `:436` — `name_needs_review` in the list and
  detail response payloads.
- `api/schemas/admin_people.py` — the Pydantic surface carrying `name_needs_review`.
- `api/services/admin_arguments.py:88-160` — `list_arguments` / `get_argument_stats`
  status exclusions, left untouched per D-28.
- `api/routers/admin.py:1423-1453` — `PATCH /arguments/{id}/participants/{pid}`
  (`update_participant_side`) and its IDOR guard; the existing participant write path
  D-31's authority check hooks into.
- `api/routers/admin.py:581-605` — the job-scoped resolve-row mutation and
  `ResolveRowUpdate` (`api/schemas/admin_jobs.py:195`), the other participant writer.
- `pipeline/commands/import_convokit.py:740-790` — `_resolve_person`: `oyez_speaker_id`
  first, then `full_name` (D-13), with `oyez_speaker_id` backfill. The mechanisms D-20's
  table maps.
- `pipeline/commands/import_convokit.py:913-920` — `ArgumentParticipant` creation, where
  D-10/D-19's new columns get stamped at birth.
- `pipeline/commands/import_convokit.py:493` — `counters["skipped_existing"] += 1`, the
  proof that no compare-and-record path exists today (D-31).
- `pipeline/commands/import_convokit.py:404` + `:643` — `_build_discrepancies`, the
  HIT-shaped blob D-14 leaves alone.
- `pipeline/commands/resolve.py:152-153`, `:225-300` — `normalize_label` + alias lookup,
  already self-described as `normalized` by Phase 47; the D-20/D-21 PDF row.
- `app/src/routes/admin/arguments/+page.svelte:105-135`, `:170-224` — the trust-tier
  badge helpers and the status segmented filter the queue's filter UI can follow.
- `app/src/routes/admin/arguments/[id]/+page.svelte:497,544` — the unresolved-advocate
  placeholder and per-row Save gate D-33 finally exercises.
- `app/src/lib/components/ResolveCard.svelte` — the deep-link target for D-23's edit
  path; also the consumer of the legacy discrepancy blob D-14 protects.
- `app/src/lib/components/SpeakerPopover.svelte`, `CreatePersonPopover.svelte`,
  `StatCard.svelte`, `AdminSubNav.svelte` — the components D-23/D-27/D-30 reuse.
- `app/src/routes/admin/people/+page.server.ts` — the `missing` filter round-trip
  D-08 re-points.
- `.planning/codebase/DESIGN-SYSTEM.md` — the palette and spacing D-29 builds within.
- `CLAUDE.md` — Alembic sole DDL authority; pipeline offline-only; the apolitical hard
  constraint; the rootdir `conftest.py` test-isolation rule every DB-gated test must
  respect.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `api/domain/trust.py` — `derive_tier` / `floor_tier` land unchanged; this phase only
  starts feeding them real `review_state` values. The pure-module pattern
  (`person_names.py`, `docket_values.py`, `trust.py`) is where any new shared review
  vocabulary belongs.
- `SAEnum(..., values_callable=lambda e: [x.value for x in e])` — the established PG
  enum declaration pattern D-09 follows.
- `ResolveCard.svelte` + `SpeakerPopover.svelte` + `CreatePersonPopover.svelte` — the
  full person-search / assign / create stack already works. D-23 deep-links to it rather
  than duplicating it.
- `StatCard.svelte` and `get_argument_stats`'s single-grouped-COUNT shape — the pattern
  for D-30's dashboard count.
- The `/admin/people` `missing` click-to-filter round-trip and its Bench/Advocate tabs —
  the precedent for D-02's tabs and the queue's filter plumbing.
- Phase 43 `reset_to_fixture` + the Phase 41 four-fixture set — the live verification
  vehicle for D-32/D-33.

### Established Patterns
- Alembic is the sole DDL authority; PG cannot drop enum values — which is why D-09's
  shared enum is a one-way decision and why the varchar+CHECK alternative was a real
  contender.
- Bulk `update()` / `delete()` use `.execution_options(synchronize_session=False)` with
  a `db.refresh()` when the same session re-reads the row (documented at
  `api/services/admin_arguments.py:606-615`). D-15's close-discrepancies-in-transaction
  write and the recompute that follows it must respect this.
- Every writer calls `recompute_argument_tier` **in the same transaction as the
  mutation** (48 D-07). The queue's inline confirm and the confirm-as-unattributable
  action are new writers and inherit that obligation.
- Public response models are explicit Pydantic allow-lists — structurally safe, which
  D-34 converts into an asserted guarantee.
- Admin lists are unbounded and server-rendered through `+page.server.ts` with
  `X-Admin-Token`; `FASTAPI_BASE_URL` is server-only, never `PUBLIC_`.
- The suite runs against `scotus_test` via `TEST_DATABASE_URL` with a rootdir
  `conftest.py` that fails any run changing shared-dev-DB row counts.
- No frontend test framework exists; Svelte behavior is covered by static
  source-contract tests (`test_phase45_popover_boxmodel_contract.py` shape). **Read
  memory note first:** grep-style `.svelte` contract tests have already passed green
  against a fully broken button (`$state` proxy trap, Phase 48 plan 48-10) — do not
  treat a green contract test as evidence the queue works.

### Integration Points
- Write paths that must now stamp `review_state` and call recompute: corpus import
  (birth, `import_convokit.py:913`), `update_participant_side`
  (`admin.py:1423`), the job-scoped resolve-row mutation (`admin.py:581`), the person
  name edit (`admin_people.py:545`), the new inline confirm, and the new
  confirm-as-unattributable action.
- `api/services/trust.py`'s `_load_constituents` is the single point where D-17 and D-18
  both land.
- `summarize_tier_blockers` (`api/services/trust.py:141`) already produces the
  what-dragged-it-down payload for 48 D-19's publish-block message — the queue's
  needs-attention summary (D-01) should read from it rather than recomputing the reasons.
- The new `/admin/review` route joins `AdminSubNav`; its data comes through a
  `+page.server.ts` load like every other admin page.

</code_context>

<specifics>
## Specific Ideas

- On per-discrepancy lifecycle, the operator's framing was the useful one: *"I can't
  tell if giving each discrepancy its own lifecycle is due diligence or an example of
  YAGNI."* The resolution that came out of it (D-15) is worth restating because it
  generalizes: a per-row `resolved_at` is due diligence because repeat disagreements
  must be distinguishable; a per-discrepancy accept/reject **UI** is YAGNI because
  accept is an edit and reject is a confirm. Separate the bookkeeping from the workflow.
- The corpus name-fallback exchange (D-20) is worth reading as a method, not just a
  decision. The operator's challenge to the recommendation was a single question —
  *"How often does this happen?"* — and it overturned the recommendation outright once
  the code was actually read (`:774`'s backfill makes the branch fire at most once per
  person, and the cohort that hits it is the seeded justices). **Apply the same test to
  any remaining tier-granularity question in this phase:** before tiering a mechanism
  down, establish how often it fires and on which rows. A tier that flips on the next
  import is a race condition wearing a trust label.
- Do not let the queue become a screen that only lists. D-23's inline confirm is the
  point: the operator sweeps a corpus, and every navigation round-trip is the job.
- The Phase 48 lesson bears repeating verbatim for a phase whose deliverable is a new
  screen: three of Phase 48's defects were found by operator browser testing, none by
  the 1209-test suite. Budget the live pass; do not treat contract tests as its
  substitute.

</specifics>

<deferred>
## Deferred Ideas

- **Making corpus re-import compare-and-record instead of skip-existing** → Phase 50.
  This phase builds the mechanism and one writer (D-31); Phase 50 supplies the corpus
  caller and the idempotency guarantee.
- **Wiring the PDF alias-HIT participant provenance** → deferred PDF route (D-21),
  tracked by todo `2026-08-18-pdf-provenance-live-fixture-verification.md`.
- **Migrating or renaming the legacy `admin_jobs.discrepancies` blob** → Phase 50, which
  re-points `admin_job` at `import_run` anyway (D-14).
- **Server-side paging for the review queue** → revisit if the unbounded query proves
  slow against the real corpus (D-04); not built now.
- **Bulk confirm** → rejected outright, not deferred (D-24). It would make the VERIFIED
  tier's central claim unfalsifiable.
- **Extracting shared components (badges, filters, table) from the queue** → Phase 51's
  design-system work (D-29).
- **A per-discrepancy accept/reject workflow** → rejected as YAGNI (D-15); accept is an
  edit, reject is a confirm.
- **Appending operator actions to `provenance_metadata`** → rejected (D-12);
  `review_state` records the action and `argument_status_log` is the audit-log precedent.
- **A person-name flag reaching the argument trust floor** → rejected to preserve 48
  D-10's no-fan-out guarantee (D-08 / the Review→trust area). Revisit only if a
  misspelled name on a published argument proves to be a real problem.
- **Side / entity-type filters on the queue** → not now (D-07); also entangled with the
  known `side` silent-fallback bug.
- **Widening the delete gate to candidates** → still Phase 50 (48 D-05), unchanged.

### Reviewed Todos (not folded)

Seven of the eleven keyword matches were reviewed and deliberately not folded:

- `2026-08-12-speakers-bench-classification-silent-fallback.md` (api, low) — a
  classification bug in the read path. Review-adjacent in spirit and it is why D-07
  declines a `side` filter, but fixing it is not review-model scope.
- `2026-08-20-reset-to-fixture-stale-created-at-timestamps.md` (api) — dev-only
  `reset_to_fixture` transaction reuse; the root cause behind Phase 48's display-ordering
  bug. Unrelated to review state.
- `2026-08-20-reset-error-copy-overclaims-db-corruption.md` (ui) — error copy on a
  destructive dev action.
- `2026-08-20-reset-has-no-timeout-or-progress.md` (ui) — observability on
  `reset_to_fixture`.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (dev-environment, low) —
  unrelated.
- `2026-08-18-pdf-provenance-live-fixture-verification.md` (pipeline, minor) — explicitly
  deferred with the PDF route (D-21).
- `SEED-001-rework-resolve-table-requirements` (dormant seed) — the bulk was absorbed
  into Phase 44's RESOLVE-01–06; remaining scope is `/gsd-review-backlog` material.

</deferred>

---

## Planning-Session Addendum (2026-08-21, `/gsd-plan-phase 49`)

Three items `49-RESEARCH.md` raised as Open Questions / Pitfall 4 were put to the operator
during planning and are now **locked decisions**, binding on the planner and any replan.

### D-31a (locked) — one authority-checked writer, both existing writers delegate

D-31's "one real authority-checked writer" resolves to a **new domain-gated service** that owns
the authority gate, the discrepancy record, and the trust recomputation. Both existing writers
become thin callers of it:

- `api/services/admin_arguments.py::update_participant_side` (no status guard today)
- `api/services/admin_jobs.py::update_resolve_row_for_job` (CANDIDATE-only guard today —
  RESEARCH Pitfall 2; this guard is in scope to widen because the writer now delegates)

Rejected alternative: extending `update_resolve_row_for_job` in place and leaving
`update_participant_side` untouched. It leaves a second, unguarded write path alive, which
contradicts D-31 outright. The larger diff is the point — one gate, no parallel mechanism,
consistent with REVIEW-05's own "no parallel mechanism survives" standard applied to writers
rather than to columns.

The person writer `api/services/admin_people.py::update_person` follows the same rule.

### D-31b (planner's discretion) — authority-ladder return shape

Left to the planner, with one hard constraint: **a single accept/reject boolean is not
sufficient**, because D-16 requires a discrepancy to be recorded even when the incoming value is
outright rejected. Two candidate shapes, either acceptable if justified in the plan:

- `(accepted: bool, should_record_discrepancy: bool)` — no new enum; mirrors
  `api/domain/trust.py`'s plain-value discipline
- a three-way result (`ACCEPT` / `ACCEPT_AND_RECORD` / `REJECT_AND_RECORD`) — self-documenting
  at call sites, makes the unreachable combination inexpressible

The function is new: this session confirmed no generic authority-ladder exists (RESEARCH
Assumption A2 verified — `api/domain/` holds only `trust.py`, `person_names.py`,
`docket_values.py`, and the latter two are field-specific Phase 38 contracts, not a general
ladder). It belongs in `api/domain/` beside them.

### D-33a (locked) — dev-only direct-insert mechanism for the unresolved-speaker fixture

RESEARCH Pitfall 4 established that no live corpus path can produce a NULL-`person_id`
`ArgumentParticipant` today, because `_resolve_person` always resolves-or-creates. D-33's
fixture gets a **dev-only seeding mechanism that inserts a NULL-`person_id` participant
directly**, gated the same way `reset_to_fixture` is (`api/services/admin_dev.py` sibling).

Rejected alternatives: a synthetic corpus `FIXTURE_SET` entry (would require `_resolve_person`
to gain a give-up branch — a production behavior change for a test need), and unit-level-only
coverage with the live fixture deferred (leaves D-33 unproven end-to-end).

This is new dev tooling with no analog to copy; it is infrastructure that **gates** every test
needing the unresolved case, so it must land before those tests.

### D-35 (locked 2026-08-24, operator, during Phase 49 gap-closure execution)

**Decision, verbatim:** *"If an argument is currently published, the data for that argument is
locked. If an argument is in any other state, I expect the data to be editable and have almost
the exact interface."*

Raised at the checkpoint plan 49-09 originally posed, offering three mechanisms
(`deep-link`, `port-control`, `defer`) for closing G-49-3's Speakers-card/Resolve-card
divergence. The operator rejected all three mechanisms **and the framing that produced
them**, verbatim: *"I'm less concerned about the mechanisms behind the scenes and the
decisions that came before that led us here but I feel like they are tripping us up. I'll
tell you my mental model and I want you to assess the code and see if it supports it in the
best way possible."* They then selected: **"Converge both surfaces."**

**Consequence, split across two plans:**
- **49-09** shipped the first half — the published lock on `update_participant_side`, using
  the same predicate, error shape, and folded-todo citation the resolve writer already used.
- **49-10** shipped the second half — the Speakers card converged onto one row template
  reaching all five stored side values (including BENCH), gated by a boundary-crossing
  confirm, with equal affordance depth for bench and advocate rows (CLAUDE.md apolitical
  constraint).

**T-15-02-BENCH was retired as SATISFIED, not weakened.** The threat, minted in Phase 15
(`15-02-PLAN.md:207`), was never really "bench must never be settable" — the Resolve card
has set it every day since Phase 25. Its real concern was "bench must not be settable
**without the reconciliation the Resolve card performs**." Under D-35 that concern is met at
the Speakers card's own call site by four compensating controls:
1. An explicit two-step confirmation before a boundary crossing (49-10 Task 3) — the same
   purpose `needsSideGate`/`confirmSide` serve on the Resolve card.
2. No fabricated bench role — the read path derives `bench_role` from a `CourtTenure`
   date-window lookup with NO fallback (`_bench_role_and_missing_tenure`, D-15) and reports
   *Missing tenure* otherwise.
3. No silent carry of a mismatched person link — the same read path turns a non-Justice
   person on a bench row into the Missing-tenure affordance plus a link to the person editor
   (RESOLVE-09's disjoint-pool concern, answered by the read path because this surface has
   no person picker to clear).
4. 49-09's published lock — the strongest control: a reclassification from this surface can
   never mutate live public data.

**Honest boundary of that argument:** the retirement is strictly stronger where the threat's
impact lives (published data) and deliberately permissive on unpublished data — that is the
authority D-35 grants the operator, not a claim that it is stronger everywhere.

**Status:** LOCKED. Not to be re-litigated by a future plan in this phase.

### D-35a (locked 2026-08-24, operator, during Phase 49 gap-closure execution)

**The question, as 49-09's Task 3 posed it in `deferred-items.md`:** does D-35's *"the
data for that argument is locked"* extend to the Case card and the Argument Details card
on `/admin/arguments/{id}` — argued date, case name, docket, question number — or is D-35
scoped to participant data only (the half 49-09 closed)?

**The operator's answer, verbatim:** **"Whole argument — lock everything."**

**Consequences, all binding on plan 49-11:**
- Every writer of an argument's own value columns refuses while `status == PUBLISHED`:
  `api/services/admin_arguments.py::update_argument` (previously froze only the slug) and
  `::update_argument_metadata` (previously had no status check at any layer), plus the two
  job-scoped participant writers D-35's first half never reached —
  `api/services/admin_jobs.py::resolve_job` and `::create_person_for_job` (both defence in
  depth; the published case is not reachable through any current path today).
- **This REVERSES a prior explicit decision**, recorded in a comment above the
  `ArgumentDetailsCard` call site in `app/src/routes/admin/arguments/[id]/+page.svelte`:
  *"readonly is always false here: this page's argument details remain editable regardless
  of publish status."* That comment is replaced, in place, with one naming D-35, D-35a, the
  operator, and 2026-08-24 — the reversal is visible without a git blame, never a silent
  flip.
- Lifecycle operations are explicitly OUT of the lock — the operator's own second sentence
  ("if an argument is in any other state I expect the data to be editable") presupposes an
  argument can always leave the published state. `publish_argument` / `unpublish_argument`
  stay callable on a published argument; proved live.
- Review-state writes (`admin_review.resolve_participant_review` / `resolve_person_review`)
  are OUT of the lock, carried forward from 49-09's classification unchanged and now proved
  live.
- The Case card and the Argument Details card are locked behind 49-09's SAME single
  `speakersLocked` flag — no second flag was minted — with one page-level lock statement
  covering both cards, rather than a third card-level restatement.

**Left open, NOT decided here — a genuinely different question:** whether `Person`-scoped
writers (`admin_people.update_person`, `merge_people`, and siblings) should be restricted at
all, given a `Person` is shared across every argument they appear in and any lock there
would freeze a sitting Justice's record the moment one of their arguments publishes. This is
distinct from the whole-argument-scope question answered above — that one was about which
CARDS on the argument page are locked; this one is about data no single argument owns.
Recorded in `deferred-items.md` as the phase's one new operator question, not guessed at.

**Status:** LOCKED. Not to be re-litigated by a future plan in this phase.

---

*Phase: 49-Review Model*
*Context gathered: 2026-08-21*
</content>
