# Phase 50: Unified Import Path - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-25
**Phase:** 50-unified-import-path
**Areas discussed:** Todo folding, Reconcile scope & trigger, Utterances on re-import, AdminJob retirement for corpus, Authority gate: every writer, Delete gate for candidates, Reconcile output volume, Batch observability

---

## Todo folding

| Option | Description | Selected |
|--------|-------------|----------|
| None — keep all 7 pending | Cleanest; the phase carries only IMPORT-01/03/04/05 | ✓ |
| Fold reset_to_fixture created_at | Stale `created_at` from transaction reuse; in the blast radius of the idempotency proof | |
| Fold PDF provenance live fixture | Advised against — explicitly deferred with the PDF route | |

**User's choice:** None — keep all 7 pending
**Notes:** All seven matches recorded as reviewed-not-folded in CONTEXT.md. Five of the seven were pure keyword noise.

---

## Reconcile scope & trigger

### Default behavior on a repeat conversation_id

| Option | Description | Selected |
|--------|-------------|----------|
| Always reconcile | Every repeat import walks the field set through `decide_write`; makes the guarantee literally true, at the cost of a no-longer-free re-run | ✓ |
| Reconcile behind a flag | Default stays skip-existing; cheap batches, but the guarantee only holds on the flagged path | |
| Always compare, flag to write | Compare and record always, write only when told; dry-run-first shape | |

**User's choice:** Always reconcile
**Notes:** SC-3 says "re-running *any* import" — a flag-gated guarantee does not satisfy it.

### Which fields are in the compare set

| Option | Description | Selected |
|--------|-------------|----------|
| Case details + participants | Argument + lead Case metadata, participant person/side/descriptor, Person name-parts | ✓ |
| Case details only | Argument + Case metadata alone; excludes exactly the data Phase 49's discrepancy record was built for | |
| Everything with a counterpart | Adds derived and structural fields (`slug`, `is_lead`, `term_year`) | |

**User's choice:** Case details + participants
**Notes:** Reuses the gated writer's existing field vocabulary for two of the four groups.

### Incoming field empty, stored value present

| Option | Description | Selected |
|--------|-------------|----------|
| No opinion — skip silently | A missing corpus field is an absence of information, not a claim | ✓ |
| Record as a discrepancy | Maximum visibility; floods the queue given how often ConvoKit ships gaps | |
| Depends on the field | Per-field policy; more precise, more to encode and review | |

**User's choice:** No opinion — skip silently
**Notes:** D-24 of Phase 49 rejected bulk confirm, so a flood of "still fine" items would be individually clicked.

### What proves SC-3 idempotency

| Option | Description | Selected |
|--------|-------------|----------|
| Live double-import + edit survival | Byte-identical re-import diff plus an operator-edit-survival walkthrough, backed by tests | ✓ |
| Automated tests only | Cheaper and CI-repeatable; but the project's record says the suite misses this class | |
| Live double-import only | Proves "same input, same rows" but leaves "never clobbers operator work" to unit tests | |

**User's choice:** Live double-import + edit survival
**Notes:** Same vehicle Phase 47 used for provenance. Phase 48's three real defects were all found live, none by the 1209-test suite.

### Participant pairing key on re-import

| Option | Description | Selected |
|--------|-------------|----------|
| `(argument_id, raw_speaker_label)` | Reuses the importer's own dedup key at line 912; no schema change | |
| Pair via Person by `oyez_speaker_id` | Survives a corpus rename but breaks on operator reassignment — the case that matters most | |
| Add `oyez_speaker_id` to the participant | Declared lineage instead of an inferred display string; costs a migration | ✓ |

**User's choice:** Add `oyez_speaker_id` to the participant
**Notes:** The backfill half of this was subsequently dropped once the no-migrations principle was stated. Recorded implication accepted without objection: a participant with no external id is unpairable and, since `operator > corpus`, left alone entirely.

### Stored participant the corpus no longer mentions

| Option | Description | Selected |
|--------|-------------|----------|
| Leave it, record nothing | Consistent with the missing-field rule; can never destroy operator work | ✓ |
| Leave it, record a discrepancy | Structural disagreement is arguably meaningful; needs a non-field discrepancy shape | |
| Delete when nothing depends on it | Keeps data honest to the corpus; a deletion path in an import writer is a data-loss risk | |

**User's choice:** Leave it, record nothing

### Does a reconciling pass create an ImportRun

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy run, `step="reconcile"` | Minted only when something is written or recorded; invisible to the parse-step read path | ✓ |
| Always a reconcile run per argument | Full audit trail; ~7,800 rows on a no-op pass breaks the byte-identical proof | |
| No new run — attribute to the original | Zero new rows; two passes then collide on `value_discrepancy`'s deliberately non-unique key | |

**User's choice:** Lazy run, `step="reconcile"`
**Notes:** Asked after discovering that `api/services/arguments.py:100-108` selects `MAX(ImportRun.id)` filtered to `step="parse"`/`COMPLETED` — an empty parse-step run blanks the argument's public page. The blank-page hazard was stated as a hard constraint before the question.

### review_state and provenance on an ACCEPTED overwrite

| Option | Description | Selected |
|--------|-------------|----------|
| Restamp provenance, leave `review_state` | The discrepancy record already drives the queue; one fact, one mechanism | ✓ |
| Restamp provenance, reset to `needs_review` | Self-describing at row level; two mechanisms that can disagree | |
| Leave both untouched | Mirrors D-22's treatment of operator edits; but reinstates the archaeology problem | |

**User's choice:** Restamp provenance, leave `review_state`

### What a reconcile pass does on a PUBLISHED argument

| Option | Description | Selected |
|--------|-------------|----------|
| Compare and record, never write | Honors D-35a from the import writer too; unpublish → reconcile → republish | ✓ |
| Skip published arguments entirely | Absolutely safe; a corpus correction becomes invisible forever | |
| Write it — authority is the only gate | Most consistent with corpus-as-trustworthy; a CLI batch would change live content unattended | |

**User's choice:** Compare and record, never write
**Notes:** Raised as a genuine conflict between two already-locked things: `decide_write` has no notion of publication, and the reconcile writer is a seventh path to data D-35a froze behind six.

---

## Utterances on re-import

### Does a reconciling re-import touch utterances

| Option | Description | Selected |
|--------|-------------|----------|
| Whole-set replace under a new parse run | Read path flips atomically; prior rows survive; identical input produces no run | ✓ |
| Never touch utterances | Zero blank-page risk; a corpus transcription fix could never reach the site | |
| In-place per-utterance update | Smallest write volume; violates Architecture Rule 3 and can leave a mixed run | |

**User's choice:** Whole-set replace under a new parse run

### Where the new run's utterance person_id comes from

| Option | Description | Selected |
|--------|-------------|----------|
| From the paired participant | Operator resolve work is authority-protected there, so corrections survive for free | ✓ |
| From the raw corpus speaker mapping | Simplest; silently discards every operator reassignment (an IMPORT-04 violation) | |
| Carry forward by sequence match | Preserves utterance-level divergence; least reliable exactly when text changed | |

**User's choice:** From the paired participant

### Retention of superseded utterance rows

| Option | Description | Selected |
|--------|-------------|----------|
| Retain + offline prune CLI | Rule 3's guarantee kept; deletion is an explicit operator act, mirroring `recompute-trust` | ✓ |
| Retain forever, no prune | Most conservative; unbounded growth with no operator lever | |
| Prune superseded runs on success | Bounded automatically; an import that deletes data is a different risk profile | |

**User's choice:** Retain + offline prune CLI

### How a pass decides utterances differ

| Option | Description | Selected |
|--------|-------------|----------|
| Content digest on the run | One comparison per argument instead of hundreds; digest definition must stay frozen | ✓ |
| Full row-by-row comparison | Always exactly right; a no-op pass reads millions of rows | |
| Cheap pre-check, then full compare | Fast in the common case; a same-length text fix passes every pre-check | |

**User's choice:** Content digest on the run

---

## AdminJob retirement for corpus

### What moves a corpus argument from candidate to draft

| Option | Description | Selected |
|--------|-------------|----------|
| Argument-scoped approve | Non-job-scoped approve setting DRAFT + `resolved_at`; `approve_job` stays for PDF | ✓ |
| Born draft when nothing is flagged | Fewer clicks on the clean majority; still needs an approve path, and skips human review | |
| Keep the admin_job for corpus | Zero work; the fabricated-job smell the phase exists to remove stays | |

**User's choice:** Argument-scoped approve
**Notes:** Presented with the blocker stated up front — `approve_job` is the only writer of `resolved_at`, and `publish_argument` refuses on `resolved_at IS NULL` non-overridably, so a jobless corpus argument would otherwise be permanently unpublishable.

### Existing corpus AdminJob rows

| Option | Description | Selected |
|--------|-------------|----------|
| Delete them in a data migration | One coherent end state, no mixed-mode rows | |
| Leave them, create no new ones | No migration; fabricated jobs persist indefinitely | |
| Rely on a fixture re-seed | No migration code; holds while the DB is genuinely disposable | (effectively ✓) |

**User's choice:** Free-text — *"we still have a lot of parsing and design work so the ability to reseed over and over is not going away. The current database is all throwaway entries so I don't care about migrating anything at this point."*
**Notes:** Read as a standing constraint broader than this question: propose DDL freely, legacy-data backfill never. It immediately killed the participant-column backfill in the follow-up question, and it closes Phase 49's deferred `admin_jobs.discrepancies` item as a no-op.

### Backfill for the new participant column

| Option | Description | Selected |
|--------|-------------|----------|
| No backfill — reseed populates it | Drops a task; consistent with disposable existing rows | ✓ |
| Backfill from Person anyway | Populated even without a reseed; real work for data just called disposable | |

**User's choice:** No backfill — reseed populates it

### admin_job → import_run FK

| Option | Description | Selected |
|--------|-------------|----------|
| No FK — SC-2 met by removing the fabrication | Remaining linkage is PDF-only, wrong cardinality for one FK, derivation already works | ✓ |
| Invert it — `import_run.admin_job_id` | Correct cardinality and declared rather than derived; PDF-route work in a corpus-only phase | |
| Add `admin_job.import_run_id` as sketched | Matches the entity sketch literally; can only point at one of three runs | |

**User's choice:** No FK — SC-2 met by removing the fabrication
**Notes:** Recorded as a deliberate deviation from `import-entity-sketch.md`, inherited by Phase 999.11.

### Operator visibility for corpus imports

| Option | Description | Selected |
|--------|-------------|----------|
| No new screen | `/admin/pipeline` becomes honestly PDF-only; `/admin/arguments` + `/admin/review` cover corpus | ✓ |
| Make the pipeline list runs-based | What "peer strategies" would look like on screen; rewrites a shipped screen unscoped | |
| New Imports view | Cleanest conceptually; a whole new admin surface ahead of the design phase | |

**User's choice:** No new screen

### resolve_job / create_person_for_job parity

| Option | Description | Selected |
|--------|-------------|----------|
| No — review queue actions suffice | Corpus's only unresolved rows are ConvoKit sentinels, already handled by confirm-as-unattributable | ✓ |
| Yes — build argument-scoped parity | Also closes 49-10's person-assignment gap; substantial unscoped increase | |
| Record the gap, decide later | Cheap and honest; leaves the operator stuck if the case appears | |

**User's choice:** No — review queue actions suffice
**Notes:** Settled on frequency evidence: Phase 48's Finding 1 traced corpus `uncertain` floors to genuine `type == "U"` sentinels, and the D-12 ambiguous-type case does mint a Person.

---

## Authority gate: every writer

### Where the gate lives for import writers

| Option | Description | Selected |
|--------|-------------|----------|
| Import the existing gated writer as-is | Same pattern as four commands importing `api.services.trust`; one literal implementation | ✓ |
| Move it to a neutral module | Name matches its shared role; churn in a module that shipped days ago | |
| Pipeline-side wrapper | API layer untouched; an adapter over a gate is where a second gate grows | |

**User's choice:** Import the existing gated writer as-is
**Notes:** Verified first that `api/services/admin_review.py` imports no FastAPI.

### Which writers must delegate

| Option | Description | Selected |
|--------|-------------|----------|
| Every pipeline writer of a gated column | `import_convokit`, `import_justices`, `parse.py`, `resolve.py`; no unguarded caller anywhere | ✓ |
| Corpus writers only | Tightest corpus-only reading; pdf rungs proven only by pure-function unit tests | |
| Corpus importer alone | Smallest change; leaves `import_justices` clobbering Person name-parts ungated | |

**User's choice:** Every pipeline writer of a gated column
**Notes:** Presented with the observation that the ROADMAP's own scope note ("proven by real-writer tests") already implies the PDF writers delegate, verified by test rather than live re-seed.

### Person-scoped write boundary (Phase 49's one open question)

| Option | Description | Selected |
|--------|-------------|----------|
| No lock at all | A Person is shared; a lock freezes a sitting Justice permanently. Zero implementation | ✓ |
| Lock merges only | Line drawn at structural repointing; blocks the known Person-dedup fix | |
| Lock all person edits | Most consistent with D-35a's letter; freezes a Justice's record site-wide forever | |

**User's choice:** No lock at all
**Notes:** This closes the single question `49-deferred-items.md` recorded as open and explicitly declined to guess. Per the Phase 40.1 stale-status lesson, its `Status: open` line must be flipped in the same commit.

### What proves "no ungated writer survives"

| Option | Description | Selected |
|--------|-------------|----------|
| Executable gate + dispositioned inventory | Behavioral test catches the unnamed writer; table records the deliberate exclusions | ✓ |
| Executable gate only | Less documentation to maintain; no record of what was left out or why | |
| Inventory + code review | Cheapest; the exact shape that has failed here twice | |

**User's choice:** Executable gate + dispositioned inventory
**Notes:** Framed with the two prior failures — 49-12's fourth scroll cause past three green gates, and the `$state` proxy case with 28 green tests over a broken button. The gate must not be a source-text grep.

---

## Delete gate for candidates

| Option | Description | Selected |
|--------|-------------|----------|
| Everything except published | D-35a's doctrine applied consistently; most useful under a reseed workflow | ✓ |
| Candidate and draft only | Conservative about anything that ever shipped; adds a second gating concept | |
| Candidate only, keep draft as-is | Smallest diff; leaves a three-way rule nobody can state in one sentence | |

**User's choice:** Everything except published
**Notes:** Asked alongside a defect found while checking the cascade — `delete_argument` deletes the argument's `ImportRun` rows but never `value_discrepancy`, which hard-FKs to `import_run`, so deleting an argument carrying a discrepancy raises `ForeignKeyViolation`. Recorded as a must-fix regardless of the gate answer; same defect class Phase 48 closed for `argument_status_log`.

---

## Reconcile output volume

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing beyond batch counters | Frequency says the load won't arrive; reseeding prevents accumulated drift | ✓ |
| Add a fail-loud cap | A systematic-drift bug surfaces as a refused batch rather than an unclearable queue | |
| Add server-side paging now | Closes Phase 49's D-04; real work for a load nothing has demonstrated | |

**User's choice:** Nothing beyond batch counters
**Notes:** The fail-loud cap was offered on the grounds that D-24 rejected bulk confirm, making a flood genuinely unclearable, and was declined.

---

## Batch observability

### Dry-run mode

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — `--dry-run` flag | Default stays write; a batch that rewrites utterance sets should be inspectable first | ✓ |
| No — the counters are enough | One less code path whose output can drift from the real pass | |

**User's choice:** Yes — `--dry-run` flag

### What a pass reports

| Option | Description | Selected |
|--------|-------------|----------|
| Extended stdout counters | Same shape and place the operator already reads | ✓ |
| Counters plus a written report file | Auditable after the fact, two runs diffable; a new artifact to own | |
| Counters plus verbose per-argument lines | Detail on demand; only useful piped to a file, i.e. the report option with extra steps | |

**User's choice:** Extended stdout counters

### Transaction boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Per-argument, unchanged | Guarantees a parse-step run can never be visible without its utterances | ✓ |
| Per-argument, but utterances separately | Smaller transactions; a crash between commits blanks the public page | |
| Whole batch in one transaction | Strongest consistency; discards per-row error isolation and holds locks across ~7,800 arguments | |

**User's choice:** Per-argument, unchanged

---

## Claude's Discretion

Nothing was answered "you decide." Two items were recorded as implications rather than asked,
with an explicit invitation to correct either:

- A participant with no external id after D-04 is unpairable, and since `operator > corpus`,
  re-import leaves it alone entirely.
- `admin_jobs.discrepancies` becomes PDF-only by construction once the corpus job write is
  removed, so Phase 49's deferred blob item closes as a no-op.

Left to planner and researcher: digest algorithm and covered tuple, counter names, the
argument-scoped approve's surface placement, `prune-runs` flag design, test file placement.

## Deferred Ideas

See CONTEXT.md `<deferred>` for the full list with rationale. Summary: the
`admin_job`/`import_run` FK and all remaining PDF-route work to Phase 999.11; a runs-based
pipeline list or Imports view to Phase 51 at the earliest; argument-scoped resolve/create-person
parity and review-queue paging revisited only on evidence; the fail-loud volume cap and the
written report file both offered and declined; the Person-dedup mismatch remains its own future
phase, which D-23 deliberately keeps unblocked.
