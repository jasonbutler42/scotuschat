# Phase 54: Publishing at Scale & Verification Debt - Context

**Gathered:** 2026-09-30
**Status:** Ready for planning, but blocked on Phase 53.1 (see below)

<domain>
## Phase Boundary

Phase 54 has two jobs:

- **Publish the corpus.** Build offline `pipeline bulk-approve` and `pipeline bulk-publish` commands, run the
  launch script end to end into a dedicated corpus database, and verify every public surface at
  real volume.
- **Clear verification debt.** VERIFY-01 is the three never-observed UAT behaviours. VERIFY-02 is
  Phase 49's live-browser checks.

**Blocked on Phase 53.1 (Tenure-Bounded Speaker Correction), inserted 2026-09-30 during this
discussion.** The corpus must not go live while about 4,300 turns are credited to a justice outside
their tenure. 53.1 owns that correction, and this phase publishes only after it lands. Harlan I/II was
first raised here as a Phase 54 fix; it moved to 53.1 with the other tenure errors.

Out of scope here: deployment (v2.0), and any change to the trust rules or the more-than-half
undetermined gate (Phase 53).

</domain>

<decisions>
## Implementation Decisions

### Bulk approval
- **D-01:** Approval and publication are **two separate commands**, `bulk-approve` then
  `bulk-publish`, each with `--dry-run`. A corpus argument lands at `candidate` with
  `resolved_at` NULL, and `publish_argument` refuses non-overridably without `resolved_at`. The only
  writer of `resolved_at` for a corpus argument is `approve_argument`. Keeping the operator's
  approval as its own deliberate, logged act, rather than a side effect of publishing, is the point of
  the split.
- **D-02:** `bulk-approve` **skips any argument with an open `needs_review` item** and names each one in
  the report. Those arguments stay `candidate` for the `/admin/review` queue, so the queue remains the one
  place they get decided. Everything else is approved through `approve_argument` per row.
- **D-03:** Bulk-run status-log rows are **marked as bulk**. The `argument_status_log` row records that it
  came from `bulk-approve` / `bulk-publish` and which run, so an argument's history
  distinguishes a hand publish from the corpus batch. This needs a small, additive Alembic change.
  **Reversibility:** costly. It adds a column or an FK to a run record, and the admin history rendering
  reads it.
- **D-04 (carried, not re-asked):** `bulk-publish` never supplies an `override_reason`. UNCERTAIN
  arguments, including those more than half undetermined, are held back and reported. Zero UNCERTAIN
  arguments get published.

### Where the corpus lives
- **D-05:** The launch dataset goes into a **separate corpus database** (working name
  `scotus_corpus`) alongside the existing four-fixture dev database. Reset-to-Fixture keeps targeting
  only the fixture database, so the full corpus survives resets. The local app is pointed at one or
  the other by configuration. Call it the "corpus database", not "staging": it is local, not a
  deployment environment. The same launch script is what v2.0 later replays against production.
  **Reversibility:** reversible. It is configuration plus a script target.
- **D-06:** "The corpus is published" (PUBLISH-04) means one **idempotent launch script** run to
  completion against the corpus database. It does the justice seed, imports all 65 terms (1955–2019),
  applies the Phase 53.1 corrections, then runs `bulk-approve` and `bulk-publish`. It must be safe to
  re-run, create no duplicates, and resume after an interruption. See the pre-launch-disposable-DB
  stance: the correctness properties matter; preserving data does not.

### Operator report & scope
- **D-07:** Both commands report **totals per outcome plus one line per exception**. The outcomes
  are approved / published / skipped / held back / failed. Each exception line gives the argument
  (ConvoKit id, case name) and its reason, e.g. "held back, 68% of turns undetermined". The
  majority-undetermined reason reuses Phase 53's D-18 wording. Successes are counted, not listed. The dry
  run prints the same report, labelled DRY RUN, and writes nothing.
- **D-08:** Both commands take the **same scoping flags as `import-convokit`**: `--term`,
  `--term-range` and `--conversation-id`, mutually exclusive. The launch script loops over terms. This lets
  the operator prove one term (1955) end to end before running all 65, and re-run a single term
  after a fix.

### Claude's Discretion
- Chunk size and commit strategy for PgBouncer transaction mode. Note: `publish_argument` and
  `approve_argument` currently commit internally, so chunked commits need either a no-commit core
  or an accepted per-row commit. The research and planning agents choose; D-04 and the no-raw-`UPDATE` rule
  are fixed.
- The config mechanism for switching the local app between the fixture and corpus databases.
- The shape of the bulk-run marker in D-03 (a column vs a run record), provided the admin history
  can show it.
- Which surfaces and terms besides `/arguments/term/1955` get the at-volume check (PUBLISH-05),
  and which database each VERIFY-01/02 check runs against. Most of them need specific fixture
  states rather than volume.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § Phase 54: goal, success criteria, notes (the 7,811-transaction trap,
  resumable by construction, no checkpoint table)
- `.planning/ROADMAP.md` § Phase 53.1: the blocking prerequisite
- `.planning/REQUIREMENTS.md`: PUBLISH-01–05, VERIFY-01, VERIFY-02
- `.planning/phases/53.1-tenure-bounded-speaker-correction/53.1-PRE-DISCUSSION-NOTES.md`: why
  publishing waits, and the scale of the tenure errors

### Publish gate and trust
- `api/services/admin_arguments.py`: `approve_argument` (only `resolved_at` writer for corpus
  arguments), `publish_argument` (resolved_at gate, then trust gate, status-log row, internal commit)
- `api/services/trust.py`, `api/domain/trust.py`: tier derivation, `TrustGateBlocked`
- `.planning/phases/53-undetermined-speakers-marker-normalisation/53-CONTEXT.md`: D-17 (a
  more-than-half undetermined argument floors to UNCERTAIN) and D-18 (blocker sentence wording, reused in D-07)

### CLI template
- `pipeline/__main__.py`: `import-convokit` (scoping flags and dry-run conventions for D-08),
  `recompute-trust`, `prune-runs` (command template)
- `pipeline/commands/recompute_trust.py`, `pipeline/commands/prune_runs.py`
- `pipeline/db.py`: pipeline session and engine (asyncpg `statement_cache_size=0`)

### Verification debt
- `.planning/milestones/v1.8-phases/49-review-model/49-EVIDENCE.md` §9: VERIFY-02 checks
- `.planning/notes/launch-readiness.md`: content readiness and the never-rendered-at-volume gap

### Environment
- `api/services/admin_dev.py`: `reset_to_fixture` (must keep targeting only the fixture database, D-05)
- `conftest.py` (repo root): `TEST_DATABASE_URL` redirect. A third database must not weaken it.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `approve_argument` / `publish_argument`: the per-row services D-01 and D-04 require. Each writes its
  own status-log row and recomputes trust in the same transaction.
- The `import-convokit` argparse block: copy its mutually exclusive scope group and `--dry-run`
  "DRY RUN" labelling.
- The `blockerSentence` wording (`app/src/lib/admin/blockerSentence.js`): the Python report should
  produce the same sentence for the majority-undetermined reason.
- `api/services/admin_review.py`: the `needs_review` predicates D-02 needs to find arguments with open items.

### Established Patterns
- Resumable by construction: select `status != PUBLISHED` (and `== CANDIDATE` for approve). No
  checkpoint table.
- Alembic is the only DDL authority. The D-03 change is a migration, never `create_all`.
- Reseed rather than backfill: no migration-time backfill of existing status-log rows.

### Integration Points
- The admin argument page's status history must show the D-03 bulk marker.
- The local app's DB configuration gains a second target for D-05.

</code_context>

<specifics>
## Specific Ideas

- Prove one term end to end first (`--term 1955`, about 108 arguments), then the full corpus. That
  term is also the PUBLISH-05 at-volume check.
- The operator asked whether the corpus database is "staging". The answer, which is recorded to avoid drift, is no:
  staging is a deployment environment and belongs to v2.0. This is a local database holding launch data.

</specifics>

<deferred>
## Deferred Ideas

- A real staging environment seeded by the launch script belongs to v2.0 deployment.

### Reviewed Todos (not folded)
- `2026-09-25-harlan-i-carries-harlan-ii-utterances.md`, `2026-09-25-harlan-ii-stray-2003-utterance.md`:
  folded into **Phase 53.1**, not this phase.
- `2026-09-29-reset-progress-bar.md`, `2026-08-20-reset-error-copy-overclaims-db-corruption.md`:
  Reset-to-Fixture UI polish, unrelated to bulk publishing. Left pending.
- `2026-08-18-pdf-provenance-live-fixture-verification.md`: belongs with the deferred PDF route
  (Phase 999.11).
- `2026-08-12-speakers-bench-classification-silent-fallback.md`: API bench/advocate fallback. Worth
  re-checking once 53.1 moves pre-appointment justices to the advocate side, but not folded here.

</deferred>

---

*Phase: 54-publishing-at-scale-verification-debt*
*Context gathered: 2026-09-30*
