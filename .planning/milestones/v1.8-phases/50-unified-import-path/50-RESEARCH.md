# Phase 50: Unified Import Path - Research

**Researched:** 2026-08-25
**Domain:** Import/reconcile write-path rework (SQLAlchemy 2.0 async, PostgreSQL, offline pipeline CLI + FastAPI admin services). No new external dependency, no new framework — this phase adds a compare-and-reconcile pass and closes ungated write paths inside an existing service layer.
**Confidence:** HIGH — every claim below was checked against the current source tree this session (not the stale `.planning/codebase/*.md` maps, which predate Phases 47-49 entirely, per 50-CONTEXT.md's warning). Exact file:line citations are given for every structural claim; two consequential facts not surfaced during discussion are flagged below.

## Summary

Phase 50 is a rework of existing writers, not new-system design. The authority ladder (`api/domain/authority.py`) and its one gated writer (`api/services/admin_review.py`) already exist and are fully tested for `ArgumentParticipant`/`Person` — the phase's job is (a) giving the corpus importer a real reconcile pass instead of an early return, (b) deleting the fabricated `AdminJob` and replacing its one load-bearing side effect (`resolved_at`) with a new argument-scoped approve, and (c) routing every remaining pipeline writer of a gated column through the existing gate.

Two facts turned up during this research that 50-CONTEXT.md's decisions do not address and materially affect planning:

1. **`api/services/admin_dev.py::reset_to_fixture` — the operator's dev-reset tool and D-09's own named verification vehicle — is hard-wired to the exact `AdminJob` fabrication this phase removes.** It raises `ResetIncompleteError` if a fixture's `Argument` lands without a paired `AdminJob` (admin_dev.py:230-241), it calls the job-scoped `approve_job` twice to realize the "Draft" and "Published" fixture states (admin_dev.py:262-273), and its "Mid-pipeline" fixture role is defined entirely as an `AdminJob.status` flip (admin_dev.py:275-291) with no `AdminJob` left to flip once corpus stops minting one. This function must be reworked as part of this phase, or D-09's own proof method breaks on first use. See Pitfall 1.

2. **`Argument` and `Case` have no `source`/`method`/`review_state` columns at all** ([VERIFIED: api/models/models.py:314-368, 285-303] — full model bodies read, no such columns present). D-02's compare set includes `Argument.argued_date`/`question_number`/`source_docket` and lead `Case.case_name`/`docket_number` — fields the authority ladder is supposed to govern — but there is no column on either table to read "existing authority" from, and `apply_participant_value_change`/`apply_person_value_change` both require exactly that. See Open Question 1 — this needs a planner decision this phase's decisions do not make.

**Primary recommendation:** Treat this phase as three sequenced slices — (1) reconcile pass + digest + `ArgumentParticipant.oyez_speaker_id` migration, (2) `AdminJob` retirement + argument-scoped approve + `reset_to_fixture` rework, (3) authority-gate delegation sweep across the four remaining pipeline writers — with the `reset_to_fixture` rework treated as a hard dependency of slice 2, not an afterthought.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Reconcile compare-and-decide | Pipeline (offline CLI, `import_convokit.py`) | API domain (`api/domain/authority.py`) | Pipeline owns the write; the pure domain module owns the decision — same split as every existing writer |
| Authority gate execution | API service (`api/services/admin_review.py`) | Pipeline (caller) | D-21: the gate lives in one place; pipeline calls it directly (importable, no FastAPI deps) |
| Discrepancy recording | API service (`admin_review.py::record_value_discrepancy`) | Database (`value_discrepancy` table) | Already built (Phase 49); reconcile is a new caller, not a new mechanism |
| Argument-scoped approve (D-14) | API service (`admin_arguments.py` or new function) | API router (`/admin/arguments` or `/admin/review`) | Surfaces where the operator already works per D-19 — no new screen |
| `ImportRun`/digest bookkeeping | Database schema (Alembic) | Pipeline (writer) | New columns only; Alembic remains sole DDL authority (CLAUDE.md) |
| Delete-cascade correctness (D-25/D-26) | API service (`admin_arguments.py::delete_argument`) | Database (FK constraints) | Existing bug fix, same tier as the function that has the bug |
| Dev fixture realization (`reset_to_fixture`) | API service (`admin_dev.py`) | Pipeline (`run_import_convokit`) | Currently AdminJob-coupled; must move to the argument-scoped approve this phase adds |

## User Constraints

<user_constraints>

### Locked Decisions

All 30 decisions (D-01 through D-30) in `.planning/phases/50-unified-import-path/50-CONTEXT.md` are locked. Highlights most load-bearing for planning (full text in that file, not restated here in full to avoid drift):

- **D-01**: Every repeat corpus import always reconciles — no `--reconcile` flag, no skip-existing default.
- **D-02**: Compare set = `Argument.argued_date`/`question_number`/`source_docket`; lead `Case.case_name`/`docket_number`; `ArgumentParticipant.person_id`/`side`/`descriptor`; `Person` name-parts. Derived values (`slug`, `term_year`, `CaseArgument.is_lead`, `Person.is_justice`) excluded.
- **D-03**: Empty incoming vs. populated stored = "no opinion" — skip, write nothing, record nothing.
- **D-04**: New `ArgumentParticipant.oyez_speaker_id` column is the re-import pairing key (not `raw_speaker_label` dedup, not Person lookup). Alembic column add + every pairing call site — reversal is costly.
- **D-05**: A stored participant the corpus no longer mentions is left untouched, nothing recorded.
- **D-06**: A reconciling pass mints an `ImportRun` lazily, `step="reconcile"`, only when it writes a value or records a discrepancy.
- **D-07**: On accepted overwrite, restamp `source`/`method` to `corpus`/`direct`; leave `review_state` untouched.
- **D-08**: On a PUBLISHED argument, compare-and-record but never write.
- **D-09**: SC-3 closed by a live double-import byte-identical diff + operator-edit-survival walkthrough — not by automated tests alone.
- **D-10**: Any utterance diff → full utterance set rewritten as a new `step="parse"`/`COMPLETED` run.
- **D-11**: New run's utterance `person_id` comes from the paired post-reconcile `ArgumentParticipant`, never raw corpus speaker mapping.
- **D-12**: Superseded utterance rows retained; offline `pipeline prune-runs` CLI added.
- **D-13**: Change detection via a content digest column on `ImportRun`, frozen once shipped.
- **D-14**: New argument-scoped approve sets `status=DRAFT`/`resolved_at=now()`; `approve_job` stays as the PDF path's job-scoped wrapper.
- **D-15/D-16**: No data migrations, no backfill for legacy rows — DDL yes, backfill never (operator's verbatim reseed framing).
- **D-17**: No `admin_job` ↔ `import_run` FK this phase — deviates from `import-entity-sketch.md` deliberately.
- **D-18**: `admin_jobs.discrepancies` closes as a no-op (dies with the corpus job).
- **D-19**: No new visibility screen; `/admin/pipeline` becomes honestly PDF-only.
- **D-20**: No argument-scoped resolve/create_person parity.
- **D-21**: Import writers call `api/services/admin_review.py` directly — no adapter, no relocation.
- **D-22**: Every pipeline writer of a gated column delegates: `import_convokit`, `import_justices` (source=seed), `parse.py`, `resolve.py`.
- **D-23**: No Person-level published lock (closes an open Phase 49 question).
- **D-24**: SC-4 closed by an executable behavioral gate + dispositioned inventory — not a source-text grep.
- **D-25**: An argument is deletable in every state except `published`.
- **D-26**: MUST-FIX — `delete_argument`'s cascade omits `value_discrepancy` (hard FK) and orphans `value_discrepancy.target_id` (soft ref) on participant delete.
- **D-27**: No paging, no cap on reconcile volume — batch counters only.
- **D-28**: `--dry-run` flag on the reconcile pass.
- **D-29**: Extended stdout counters, no report file.
- **D-30**: Transaction boundary stays per-argument.

### Claude's Discretion

- A stored participant with no external id (operator-created, or otherwise not derivable) is unpairable; since `operator > corpus`, re-import leaves it alone.
- Left to planner/researcher: digest algorithm and exact tuple covered, counter names, argument-scoped approve's surface placement, `prune-runs` flag design, test file placement.

### Deferred Ideas (OUT OF SCOPE)

- `admin_job.import_run_id` (or inverted `import_run.admin_job_id`) → Phase 999.11 with the PDF route.
- A runs-based pipeline list / dedicated Imports view → Phase 51 earliest.
- Argument-scoped `resolve`/`create_person` parity → not now.
- Server-side paging on `/admin/review` → still Phase 49's D-04 bet.
- A fail-loud discrepancy cap → declined.
- A written per-argument reconcile report file → declined.
- Person-dedup mismatch (White/Black/Clark/Douglas) → its own future phase.
- Anything on the PDF route beyond D-22's real-writer test coverage → Phase 999.11.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMPORT-01 | Corpus import writes `import_run` directly (source=corpus) without fabricating PDF-pipeline artifacts | [VERIFIED: pipeline/commands/import_convokit.py:583-596] — already true since Phase 47; `ImportRun` write sets `source=CORPUS`/`method=DIRECT`, no `pdf_path`/`pdf_url`. Remaining work for this requirement is negative-space verification (no PDF fields ever populate on this path) plus the reconcile pass's own `ImportRun` write (D-06) following the same pattern. |
| IMPORT-03 | `admin_job` references an `import_run` rather than inventing one; corpus CLI batch needs no admin_job | D-14/D-17/D-19 close this by deletion, not linkage — see "AdminJob Fabrication" and "AdminJob ↔ ImportRun Linkage" sections below. `reset_to_fixture` (Pitfall 1) is the load-bearing call site this requirement's closure breaks unless reworked in the same phase. |
| IMPORT-04 | Re-import is idempotent — re-running yields the same result and never clobbers operator-authored values | D-01/D-02/D-03/D-09/D-10/D-13 govern the mechanism; "Idempotency Mechanism" and "Validation Architecture" sections below. |
| IMPORT-05 | Authority ordering (operator > corpus > pdf/rule > pdf/llm) governs overwrite decisions on every writer | `api/domain/authority.py` (fully built, all 4 rungs) + "Call-Site Inventory" section — enumerates every writer, its current disposition (delegates / bypasses / N/A), and the two writers found ungated during this research that D-22 does not yet name explicitly (`resolve.py`'s bulk `person_id` UPDATE at line ~317, `import_convokit.py`'s own `_apply_extracted_name_provenance`). |

</phase_requirements>

## Standard Stack

No new external package is required. This phase extends existing internal modules (`api/domain/authority.py`, `api/services/admin_review.py`) and adds Alembic DDL. All libraries in play are already pinned project dependencies.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0 (async) | ORM for every model/writer touched | Already the project's sole DB layer |
| Alembic | (project-pinned) | DDL for the two new columns (D-04, D-13) | CLAUDE.md: sole DDL authority |
| Python `hashlib` (stdlib) | 3.12 | Content digest for D-13's change-detection column | No third-party hashing library needed for a frozen-once digest over ordered tuples; stdlib `sha256` is sufficient and adds zero dependency risk to a "must stay frozen" contract |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest / pytest-asyncio | (project-pinned) | New reconcile/authority-delegation tests | Same suite every prior phase used |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib `hashlib.sha256` for D-13's digest | A DB-side computed column (PostgreSQL `GENERATED ALWAYS AS`) | Rejected implicitly by D-13's own framing ("digest stamped on the ImportRun" by the writer) — a generated column can't hash an *ordered utterance tuple set* across a join without a stored procedure, adding real complexity for no benefit over an app-level hash computed once per reconcile pass. |

**Installation:** None — no new package.

## Package Legitimacy Audit

**Not applicable.** This phase adds no new third-party dependency to `requirements.txt`/`pyproject.toml`. `hashlib` is Python stdlib. No `npm view`/`pip index versions`/`cargo search` gate applies.

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────┐
                     │   python -m pipeline import-convokit     │
                     │   --term / --term-range / --conv-id      │
                     │   [--dry-run]  (D-28, new)                │
                     └───────────────┬───────────────────────────┘
                                     │  per conversation, one DB
                                     │  transaction (D-30)
                                     ▼
                     ┌─────────────────────────────────────────┐
                     │  _import_conversation()                  │
                     │  (pipeline/commands/import_convokit.py)  │
                     └───────────────┬───────────────────────────┘
                                     │
                    existing Argument found? (oyez_transcript_id)
                                     │
                 ┌───────────────────┴───────────────────┐
                 │ NO — first import                     │ YES — reconcile pass (NEW,
                 │ (existing path, unchanged)             │ replaces early return at ~490)
                 ▼                                        ▼
     Case/Argument/CaseArgument/         ┌───────────────────────────────┐
     ImportRun(step=parse,               │ For each D-02 compare-set     │
     source=CORPUS) created              │ field on Argument/lead Case/  │
     (IMPORT-01, already true)           │ ArgumentParticipant/Person:   │
                 │                       │   decide_write()               │
                 ▼                       │   (api/domain/authority.py)    │
     Speaker resolution +                └───────────┬───────────────────┘
     ArgumentParticipant rows                          │
     stamped source=CORPUS/                 ACCEPT / ACCEPT_AND_RECORD /
     method=DIRECT                          REJECT_AND_RECORD
                 │                                      │
                 ▼                          ┌───────────┴────────────┐
     Utterance rows streamed,                │ write (if accepted)     │  record_value_discrepancy
     import_run_id = parse run               │ restamp source/method   │  (api/services/admin_review.py)
                 │                            │ (D-07, NEW — existing   │  → value_discrepancy row,
                 ▼                            │ gate doesn't do this)   │  attributed to a LAZY
     [REMOVED] AdminJob(PAUSED,               └───────────┬────────────┘  step="reconcile" ImportRun
     RESOLVE) fabrication                                  │              (D-06)
     (D-01/D-19 — deleted)                                 ▼
                 │                          Any utterance diff? (content
                 ▼                          digest mismatch, D-13)
     recompute_argument_tier()                             │
                 │                              ┌──────────┴──────────┐
                 ▼                              │ YES                  │ NO
     [session commits — one                     ▼                      ▼
     transaction, D-30]              New step="parse"/COMPLETED   nothing (D-09's
                                      ImportRun; full utterance    byte-identical
                                      set rewritten; person_id     no-op proof)
                                      from POST-reconcile
                                      ArgumentParticipant (D-11)
                                                 │
                                                 ▼
                                      recompute_argument_tier()
                                                 │
                                                 ▼
                                      session commits (D-30) —
                                      MAX(ImportRun.id) read path
                                      (api/services/arguments.py:100-108)
                                      now sees the new run atomically
```

Operator-facing side (unchanged mechanism, new entry point):
```
/admin/arguments or /admin/review  →  NEW argument-scoped approve (D-14)
       │                                  sets status=DRAFT, resolved_at=now()
       │                                  (same completeness gate approve_job
       │                                  enforces at admin_jobs.py:653-717)
       ▼
publish_argument() (admin_arguments.py:626) — unchanged, still gates on
resolved_at IS NULL (non-overridable) and the trust-tier gate.
```

### Recommended Project Structure

No new top-level module. Changes land inside existing files:

```
pipeline/commands/
├── import_convokit.py     # _import_conversation reconcile branch replaces
│                           # the early return; new helper(s) for compare-set
│                           # diffing, digest computation, pairing by
│                           # oyez_speaker_id
├── prune_runs.py           # NEW — D-12's offline CLI, mirrors recompute_trust.py's shape
api/services/
├── admin_review.py         # unchanged public API; import_convokit calls
│                           # apply_participant_value_change /
│                           # apply_person_value_change directly (D-21)
├── admin_arguments.py      # NEW argument-scoped approve function (D-14);
│                           # delete_argument gate widened (D-25) + cascade
│                           # fix (D-26)
├── admin_dev.py            # reset_to_fixture REWORKED — see Pitfall 1
alembic/versions/
├── 0030_<name>.py           # NEW — ArgumentParticipant.oyez_speaker_id (D-04)
│                           # + ImportRun digest column (D-13); one revision,
│                           # per code_context's own note that one revision
│                           # can carry both
```

### Pattern 1: The ONE gated writer, called directly by the pipeline (D-21)

**What:** `api/services/admin_review.py::apply_participant_value_change` / `apply_person_value_change` are the only functions permitted to write a gated value column. The pipeline calls them directly — no pipeline-side wrapper.

**When to use:** Any write to `ArgumentParticipant.person_id/side/descriptor` or `Person`'s name-part fields, from any writer, pipeline or API.

**Verified precedent — an existing API caller** [VERIFIED: api/services/admin_jobs.py:600-618]:
```python
await apply_participant_value_change(
    db,
    participant=matched_participant,
    field="person_id",
    incoming_value=match.person_id,
    incoming_source=incoming_authority_source,
    incoming_method=incoming_authority_method,
)
if matched_participant.source is None:
    await db.execute(
        update(ArgumentParticipant)
        .where(
            ArgumentParticipant.id == matched_participant.id,
            ArgumentParticipant.argument_id == job.argument_id,
        )
        .values(source=parse_run_source, method=parse_run_method)
        .execution_options(synchronize_session=False)
    )
```

**Important gap this pattern does NOT cover — read before reusing it verbatim:** the restamp above is gated `if matched_participant.source is None` (only backfills when never stamped). D-07 requires the reconcile pass to restamp `source`/`method` to `corpus`/`direct` on **every** `ACCEPT`/`ACCEPT_AND_RECORD`, unconditionally — not only when previously NULL. `apply_participant_value_change` itself never touches `source`/`method` (confirmed by reading its full body, `admin_review.py:159-221` — the only `.values()` call sets `{field: incoming_value}`). The reconcile writer must perform the source/method restamp itself as a second statement after the gate call, on every accepted write, not reuse this exact conditional.

### Pattern 2: Content digest for change detection (D-13)

**What:** A digest column on `ImportRun`, computed over the ordered incoming utterance tuple set, compared against the stored digest to skip row-level comparison on an unchanged re-import.

**When to use:** At the top of the reconcile branch, before any per-field `decide_write` call, to make a true no-op pass one comparison instead of hundreds.

No prior art exists in this codebase for this exact pattern — no other table has a content digest column. [ASSUMED] shape: `sha256` over a canonical ordering of `(sequence, raw_speaker_label, text, is_stage_direction, side)` tuples, stored as a fixed-length string column on `ImportRun` (mirrors `ImportRun.external_id`'s `String(50)`-class precedent, though a hex sha256 digest needs `String(64)`). **The digest's exact field list and canonicalization must be decided and frozen in the plan** — CONTEXT.md's D-13 explicitly leaves this to the planner/researcher and flags it as a one-way door (changing it later reads as a universal diff).

### Anti-Patterns to Avoid

- **A pipeline-side adapter over the gate (rejected by D-21).** Do not wrap `apply_participant_value_change`/`apply_person_value_change` in a new pipeline-local function "for convenience" — that is exactly the second, subtly-different gate D-31a's "one gated writer" invariant exists to prevent.
- **Reusing the `if x.source is None` backfill-only conditional for the reconcile restamp.** As shown in Pattern 1, this silently fails D-07 (it never restamps an already-stamped row).
- **Deriving "existing authority" for Argument/Case fields from `Argument.trust_tier`.** `trust_tier` is a *floor rollup* of constituent utterances/participants (TRUST-02) — it answers "how much do we trust this argument as a whole," not "did an operator edit this specific field." Reusing it for D-02's Argument/Case compare-set fields would silently misattribute authority. See Open Question 1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Overwrite-or-reject decision for any provenance-bearing field | A new comparison function per field, or a bespoke corpus-only ladder | `api.domain.authority.decide_write` | Already exists, exhaustively tested ([VERIFIED: api/tests/test_authority_matrix.py] — full rank×rank×differs matrix, 969 lines), fail-closed on `UNKNOWN` |
| Recording an overwritten/rejected value for operator review | A corpus-specific discrepancy log, or reusing `admin_jobs.discrepancies` JSONB | `api.services.admin_review.record_value_discrepancy` → `value_discrepancy` table | Already exists (migration 0028); D-18 explicitly retires the JSONB blob rather than extending it |
| Determining whether a name-part pair actually differs (whitespace/case) | A new string-compare helper | `api.domain.person_names.normalize_name_part` via `admin_review.py::_values_differ` (line 78) | Already the single named home of this normalization contract (REVIEW-01) |
| Trust-tier recompute after any write | Inline tier logic in the reconcile pass | `api.services.trust.recompute_argument_tier` | Already imported by four pipeline commands, never commits, composes inside caller's transaction — call it last, per D-07's writer-ordering precedent |

**Key insight:** Every mechanism this phase needs except the reconcile compare loop, the digest, and the argument-scoped approve already exists and is already tested. The risk in this phase is *omission* (a writer that should delegate but doesn't) and *silent gap* (a helper that looks reusable but doesn't do the whole job, as with the source/method restamp above) — not missing infrastructure.

## Runtime State Inventory

> Rename/refactor/migration-adjacent phase — the corpus path's write behavior is being restructured in place, and D-15/D-16 explicitly forbid legacy-data backfill. Answering all five categories.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Existing corpus `AdminJob` rows (status=PAUSED/COMPLETED/RUNNING, `discrepancies` JSONB) already in the dev DB from every prior corpus import. [VERIFIED: pipeline/commands/import_convokit.py:640-645] is the only site that currently creates them for corpus. | **No migration** (D-15, verbatim operator quote in CONTEXT.md). The importer stops minting new ones; existing rows are inert. A reseed via `reset_to_fixture` produces the clean state — but see Pitfall 1: `reset_to_fixture` itself currently *requires* these rows to exist, so it must be reworked in this same phase, not left as a "just reseed" afterthought. |
| Live service config | None. This is an offline pipeline + admin-API rework; no external service (Datadog, n8n, Tailscale, Cloudflare Tunnel) holds corpus-import-path configuration. | None. |
| OS-registered state | None. No Task Scheduler entries, pm2 processes, or systemd units reference the corpus importer or `AdminJob`. | None. |
| Secrets/env vars | None. No env var or secret name encodes `admin_job`, `pipeline_run`, or the corpus AdminJob mechanism. | None. |
| Build artifacts / installed packages | None. No compiled artifact, egg-info, or Docker tag embeds the AdminJob-fabrication behavior — it is pure application logic in one module. | None. |

**Canonical question answered:** After Phase 50 ships, `AdminJob` rows minted by prior corpus imports remain in whatever dev/test database exists, inert (no code path reads them as meaningful for corpus arguments once `get_job`/`list_jobs`'s `is_corpus` derivation — see Pitfall 3 — and `reset_to_fixture` are updated). Nothing outside the database needs to change.

## Common Pitfalls

### Pitfall 1: `reset_to_fixture` is hard-coupled to the exact mechanism this phase removes

**What goes wrong:** `api/services/admin_dev.py::reset_to_fixture` — the operator's `/admin` dev-reset tool and the function D-09's "live double-import" proof would naturally run against — does three things that break the moment corpus stops minting `AdminJob`:

1. **Existence check** [VERIFIED: api/services/admin_dev.py:230-241]: after importing each `FIXTURE_SET` conversation, it selects `AdminJob` by `argument_id` and raises `ResetIncompleteError` if none is found — "every corpus-imported argument must land paired with exactly one AdminJob, or it is unpublishable" (its own comment, now stale).
2. **State realization via `approve_job`** [VERIFIED: api/services/admin_dev.py:262-273]: the "Draft" fixture (conversation 13015) and "Published" fixture (conversation 18897) both advance CANDIDATE → DRAFT by calling `jobs_service.approve_job(db, draft_job_id)` / `jobs_service.approve_job(db, published_job_id)` — the job-scoped approve that D-14 says stays PDF-only. With no `AdminJob` to pass a `job_id` for, these two calls have nothing to call.
3. **"Mid-pipeline" fixture role defined as an `AdminJob.status` flip** [VERIFIED: api/services/admin_dev.py:275-291]: conversation 22372's entire distinguishing state is `AdminJob.status = RUNNING` — with no `AdminJob` row, this fixture's role has no realization at all.
4. The response schema itself reports `admin_job_status` per fixture [VERIFIED: api/services/admin_dev.py:326-333].

**Why it happens:** `reset_to_fixture` was built in Phase 30, before the review model or the authority ladder existed, and has never been revisited since — it predates every phase this milestone shipped.

**How to avoid:** Treat `reset_to_fixture`'s rework as an explicit task in this phase's plan, not a side effect. Its "Draft"/"Published" fixture realization must call the new D-14 argument-scoped approve instead of `approve_job`. Its "Mid-pipeline" fixture role needs a new definition with no `AdminJob` to flip — likely reusing D-06's `step="reconcile"` ImportRun state, or simply retiring that fixture's distinct role if no analogous CANDIDATE-with-partial-state exists in the new model. The existence check must stop requiring an `AdminJob`.

**Warning signs:** Any plan that treats D-09's "live double-import byte-identical diff" proof as trivially available via the existing dev tooling, without first checking whether that tooling still runs.

### Pitfall 2: The gate helper does not restamp provenance — D-07 needs a second write

**What goes wrong:** A plan that calls `apply_participant_value_change` and assumes D-07's "restamp to corpus/direct on accept" is handled will ship a reconcile pass where accepted overwrites keep stale `source`/`method` values.

**Why it happens:** `apply_participant_value_change`'s only `.values()` call sets the target `field` — never `source`/`method` [VERIFIED: api/services/admin_review.py:159-221, full function body read]. The one place in the codebase that *does* restamp does so conditionally (`if matched_participant.source is None`, admin_jobs.py:1017-1018) — a backfill-only shape, not the unconditional restamp D-07 requires.

**How to avoid:** After every `ACCEPT`/`ACCEPT_AND_RECORD` decision the reconcile pass acts on, issue an explicit `UPDATE ... SET source = ImportSource.CORPUS, method = ImportMethod.DIRECT` (or ORM-attribute assignment) unconditionally — not gated on "was it NULL."

**Warning signs:** A test that only checks the field value changed, not that `source`/`method` also changed, on an accepted overwrite of an already-stamped row.

### Pitfall 3: Detail/list job derivations quietly go stale, not loudly wrong

**What goes wrong:** `api/services/admin_jobs.py::get_job` (line 161-169) and `list_jobs` (line 268-275) both derive an `is_corpus` flag via an `exists()` subquery on `ImportRun.source == ImportSource.CORPUS` correlated to `AdminJob.argument_id`. Once corpus stops minting `AdminJob` rows, this derivation still runs correctly (it will just always evaluate to `False`, since no future corpus argument will ever have a linked `AdminJob`) — but any UI or test that still expects to see corpus arguments in the `/admin/pipeline` job list will find them silently absent, not erroring.

**Why it happens:** D-19 makes this the *intended* outcome ("`/admin/pipeline` becomes honestly PDF-only") — this is not a bug, but it is a behavior change with no compiler/test signal unless a test explicitly asserts the new corpus argument does NOT appear in `list_jobs`.

**How to avoid:** Add a negative-space test asserting a fresh corpus import produces zero new `AdminJob` rows and does not appear in `list_jobs`/`get_pipeline_stats` — this is D-24's "structural gate, not a grep" applied to the removal itself.

### Pitfall 4: `Argument`/`Case` compare-set fields have no authority home (see Open Question 1)

**What goes wrong:** Implementing D-02's full compare set naively by calling `apply_participant_value_change`-style logic against `Argument`/`Case` rows will fail immediately — those tables have no `source`, `method`, or `review_state` column to read "existing authority" from ([VERIFIED: api/models/models.py:314-368] Argument model, full body; [VERIFIED: api/models/models.py:285-303] Case model, full body — neither declares any such column).

**Why it happens:** The authority ladder and its gate were built in Phase 49 scoped to `ArgumentParticipant`/`Person` only (REVIEW-01's four-state `review_state` lives on exactly those two tables). D-02 folds `Argument`/`Case` fields into the same compare set without a corresponding schema decision.

**How to avoid:** Resolve Open Question 1 before writing the reconcile branch for these fields — do not assume the existing gate functions extend to them for free.

**Warning signs:** A plan task that says "gate Argument.argued_date the same way as ArgumentParticipant.side" without naming which new column or lookup supplies `existing_source`/`existing_method`/`existing_review_state`.

### Pitfall 5: The delete gate's condition, not just its cascade, needs to change for D-25

**What goes wrong:** D-26's MUST-FIX (the `value_discrepancy` FK violation and the soft-ref orphan) is only reachable to test/fix once D-25 widens `delete_argument`'s gate — but the current gate is a single hardcoded condition, not a set of excluded values.

**Why it happens:** [VERIFIED: api/services/admin_arguments.py:1018-1020] `if argument.status != ArgumentStatusEnum.DRAFT: return False` — today, DRAFT is the *only* deletable status. D-25 ("deletable in every state except published") requires inverting this to `if argument.status == ArgumentStatusEnum.PUBLISHED: return False`, not adding a new branch.

**How to avoid:** Plan the gate-condition change and the D-26 cascade fix as one task — the cascade fix cannot be meaningfully tested against a CANDIDATE/UNPUBLISHED argument carrying discrepancies until the gate itself is widened.

## Code Examples

### The full existing reconcile-adjacent write path (early-return site to replace)

```python
# Source: pipeline/commands/import_convokit.py:488-495 (verified this session)
    # ---- Idempotent Argument dedup on oyez_transcript_id (D-08) ----
    existing_argument_result = await session.execute(
        select(Argument).where(Argument.oyez_transcript_id == conversation_id)
    )
    if existing_argument_result.scalar_one_or_none() is not None:
        counters["skipped_existing"] += 1
        return
```
This is the exact site D-01's "always reconciles" replaces. The `counters["skipped_existing"]` counter name is referenced by `_SUMMARY_COUNTER_KEYS` (line 1177) and the summary print (line 1228) — a plan that removes the early return must decide whether `skipped_existing` becomes dead (no code path increments it anymore) or is repurposed for "reconciled, no diff found."

### The exhaustive authority matrix test already covering `decide_write` (nothing to add here)

```python
# Source: api/tests/test_authority_matrix.py:1-33 (verified this session)
"""
Exhaustive authority-ladder matrix test (Phase 49, plan 49-04, D-32).

Two sections:
  1. Pure unit matrix over `api.domain.authority` — no DB, always collects,
     always runs (this half must remain runnable with no DATABASE_URL).
  2. DB-gated integration coverage of the ONE authority-gated writer
     (`api.services.admin_review.apply_participant_value_change` /
     `apply_person_value_change`) against every plan `<behavior>` bullet.
"""
```
Phase 50 extends this file's *coverage* (new pipeline-writer delegation cases) — it does not need a parallel matrix test.

### CLI subcommand registration pattern to extend for `--dry-run` and `prune-runs`

```python
# Source: pipeline/__main__.py:289-360 (verified this session — real argparse shape)
import_convokit_p = sub.add_parser(
    "import-convokit",
    help="Bulk-import historical arguments from the ConvoKit supreme-corpus",
    ...
)
...
recompute_trust_p = sub.add_parser(
    "recompute-trust",
    help="Re-derive every argument's trust tier through the shared service",
    ...
)
recompute_trust_group = recompute_trust_p.add_mutually_exclusive_group(required=True)
recompute_trust_group.add_argument("--all", action="store_true", ...)
recompute_trust_group.add_argument("--argument-id", type=int, default=None, ...)
```
D-28's `--dry-run` is a plain `add_argument("--dry-run", action="store_true", ...)` on `import_convokit_p`. D-12's `prune-runs` is a new `sub.add_parser("prune-runs", ...)` mirroring `recompute_trust_p`'s `--all`/`--argument-id` mutually-exclusive-group shape, per `pipeline/commands/recompute_trust.py`'s own docstring precedent ("D-09's drift-repair tool").

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Corpus import fabricates a paired `AdminJob` to borrow resolve/approve/publish machinery | Corpus import writes `import_run` directly and (post-Phase-50) needs no `AdminJob` at all | This phase | `AdminJob` becomes PDF-only by construction; `/admin/pipeline` list narrows accordingly (D-19) |
| Re-import skips on `oyez_transcript_id` match, compares nothing | Re-import always reconciles through `decide_write`, records disagreements | This phase (D-01) | Every repeat corpus batch does real work; no more near-zero-cost no-op re-runs |
| `name_needs_review`/`name_extraction_metadata` (pre-Phase-49) | Unified `review_state` + `provenance_metadata` (Phase 49) | Phase 49 | Already complete — Phase 50 inherits this, does not touch it further |

**Deprecated/outdated:**
- The corpus-specific `_build_discrepancies` helper (`import_convokit.py:405`) — dies with the `AdminJob` it feeds (D-18). Check for other callers before deleting (code_context already flags this).
- `test_import_convokit_adminjob.py` ([VERIFIED: pipeline/tests/test_import_convokit_adminjob.py:1-22], full docstring read) — every one of its four documented assertions (exactly-one-AdminJob creation, discrepancies JSONB shape, no-second-AdminJob-on-rerun) is about behavior this phase deletes. This file needs a full rewrite or retirement, not incidental breakage — flag explicitly in the plan's test-file disposition table (D-24's inventory shape).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-13's digest should be a `sha256` hex string over `(sequence, raw_speaker_label, text, is_stage_direction, side)` tuples, stored in a new `String(64)` column | Architecture Patterns / Pattern 2 | If the planner picks a different field list or algorithm, this is a one-way door per D-13 itself — get the field list confirmed at plan time, not discovered mid-implementation |
| A2 | The "Mid-pipeline" `reset_to_fixture` role (conversation 22372) has no clean equivalent once `AdminJob` is gone and needs a new definition or retirement | Pitfall 1 | If the plan doesn't address this fixture explicitly, `/admin` dev tooling silently loses one of its four reference states, discovered only when a later phase's browser-check walkthrough can't find it |
| A3 | Argument/Case compare-set authority tracking (Open Question 1) needs either a schema addition (new `source`/`method` columns on `Argument`) or an explicit "these fields are always operator-authority once touched by `update_argument`/`update_argument_metadata`" rule with no stored bit | Pitfall 4 / Open Question 1 | Get this decided at plan time — implementing D-02's compare set for these two tables without a resolved answer here will produce ad hoc, inconsistent behavior across fields |

## Open Questions

1. **How does the authority ladder read "existing authority" for `Argument.argued_date`/`question_number`/`source_docket` and `Case.case_name`/`docket_number`, given neither table has a `source`/`method`/`review_state` column?**
   - What we know: D-02 locks these fields into the reconcile compare set. `decide_write` requires `existing_source`/`existing_method`/`existing_review_state` strings (`api/domain/authority.py:116-125`). `ArgumentParticipant`/`Person` have exactly those columns (or `review_state` alone, for Person); `Argument`/`Case` have none [VERIFIED: api/models/models.py:314-368, 285-303].
   - What's unclear: whether this phase adds new nullable `source`/`method` columns to `Argument` (mirroring migration 0028's shape for `ArgumentParticipant`) so `apply_argument_value_change` can exist as a peer to the two existing gate functions, or whether a simpler rule suffices — e.g., since `update_argument`/`update_argument_metadata` are the only writers of these fields today and both already gate on published-status (D-35a), perhaps "any value already present that differs from a fresh corpus value is presumed operator-authored" without a stored bit. The second approach cannot express "an operator's second edit vs. a first" the way `review_state` does for the other two tables, and provides no discrepancy-recording home either.
   - Recommendation: resolve this explicitly in the plan, before task-writing the reconcile branch for these two tables. This is the single most consequential unresolved item this research surfaced — CONTEXT.md's 30 decisions do not address it.

2. **What replaces `reset_to_fixture`'s "Mid-pipeline" (conversation 22372) fixture role once there is no `AdminJob.status` to flip?**
   - What we know: today it's a bare `AdminJob.status = RUNNING` flip with no `ArgumentStatusLog`-style audit ([VERIFIED: api/services/admin_dev.py:275-291]).
   - What's unclear: whether a `step="reconcile"` `ImportRun` mid-state is an adequate analog, or whether this fixture role should simply retire.
   - Recommendation: decide during planning, not discovered while implementing the `reset_to_fixture` rework Pitfall 1 already requires.

3. **Does the digest column (D-13) live on the `step="parse"` run only, the `step="reconcile"` run only, or both?**
   - What we know: D-06 says reconcile mints a run lazily; D-13 says the digest is "stamped on the ImportRun." D-10 says any diff produces a *new* `step="parse"` run.
   - What's unclear: whether the digest that a re-import compares against is read off the argument's most recent `step="parse"` run (the one the public read path actually serves), or off the most recent run of any step. Given D-06's `step="reconcile"` run is only minted when something actually changes, the natural answer is "compare against the latest `step="parse"` run's digest, and if it differs, write a new `step="parse"` run carrying the new digest" — but this should be stated explicitly in the plan, not inferred.
   - Recommendation: state explicitly which run the comparison digest is read from before writing the reconcile task.

## Environment Availability

Skipped — this phase has no new external tool/service/runtime dependency. PostgreSQL, Alembic, and the pytest suite are all already-provisioned dependencies exercised by every prior v1.8 phase; no new probe is needed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (project-pinned) |
| Config file | `pytest.ini` + repo-root `conftest.py` (CLAUDE.md: invocation-shape-independent hooks live there — the `TEST_DATABASE_URL` redirect) |
| Quick run command | `./.venv/bin/python -m pytest pipeline/tests/test_import_convokit_core.py api/tests/test_authority_matrix.py -x` |
| Full suite command | `./.venv/bin/python -m pytest` (project `test_command` per `.planning/config.json`) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMPORT-01 | Corpus import writes `import_run` directly, no PDF artifacts | unit + negative-space | `pytest pipeline/tests/test_import_run_provenance.py -x` | ✅ (extend) |
| IMPORT-03 | No `admin_job` created by corpus batch; `admin_job` unrelated to new `import_run` model | structural/behavioral (D-24: not a grep) | new test asserting zero `AdminJob` rows after a fresh corpus import | ❌ Wave 0 — replaces/retires `test_import_convokit_adminjob.py`'s existing assertions |
| IMPORT-04 | Re-import is idempotent; operator edits survive | automated (matrix) + **live, human-observed** (D-09 explicitly: not closed by automated tests alone) | `pytest pipeline/tests/test_import_convokit_reconcile.py -x` (new) + a live `reset_to_fixture`-driven double-import diff walkthrough | ❌ Wave 0 for the automated half; the live half is D-09's own named requirement, not skippable |
| IMPORT-05 | Authority ordering governs every writer | unit (existing, exhaustive) + real-writer tests for the two PDF legs (D-22, Phase 47's verification split) | `pytest api/tests/test_authority_matrix.py -x` (extend with pipeline-writer delegation cases) | ✅ (extend) |

### Sampling Rate
- **Per task commit:** the quick-run command above (targeted files for whatever writer/reconcile logic that task touched).
- **Per wave merge:** full suite (`./.venv/bin/python -m pytest`).
- **Phase gate:** full suite green before `/gsd-verify-work`, **plus** D-09's live double-import walkthrough performed and observed (not automatable per the operator's own framing — Phase 48's three real defects were all found live, none by the automated suite).

### Authority-rung verification split (Phase 47's precedent, reused per D-22)

| Rung | Verified by | Why |
|------|-------------|-----|
| `operator` | Live corpus flow — an operator edit via `update_participant_side`/`update_person`, then a re-import that disagrees | Operator authority is exercised constantly by existing `/admin` flows; no new mechanism |
| `corpus` | Live double-import (D-09) — the byte-identical no-op proof and the operator-edit-survival walkthrough | This is the requirement's own closure criterion, not optional |
| `pdf_pipeline/rule_based` | Real-writer test with the LLM monkeypatched — `parse.py`'s writer delegating to the gate | No live PDF fixture exists in this repo (per the deferred todo `2026-08-18-pdf-provenance-live-fixture-verification.md`); Phase 47 already established this split |
| `pdf_pipeline/llm_corrective` | Real-writer test with the LLM monkeypatched — `parse.py`'s LLM branch delegating to the gate | Same as above |

### Wave 0 Gaps
- [ ] A reconcile-specific test module (`pipeline/tests/test_import_convokit_reconcile.py` or similar — placement left to planner per CONTEXT.md's discretion note) covering D-01 through D-13's mechanics.
- [ ] `test_import_convokit_adminjob.py`'s disposition decided explicitly (rewrite vs. retire) — do not leave it silently red or silently deleted without a plan note.
- [ ] `api/services/admin_dev.py::reset_to_fixture`'s rework test coverage (its own existing tests, if any, will need updating — check `api/tests/` for `test_admin_dev*.py` at plan time).
- [ ] A negative-space test asserting a fresh corpus import creates zero `AdminJob` rows.

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (absent key = enabled), so this section is required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | This phase touches no auth surface — the pipeline is offline CLI (CLAUDE.md), and the new argument-scoped approve reuses the existing `/admin` auth already gating every admin route |
| V3 Session Management | No | No new session surface |
| V4 Access Control | Yes | The new argument-scoped approve (D-14) must be reachable only through the existing `/admin` authenticated surface — no new unauthenticated endpoint. Verify the router placement (`/admin/arguments` or `/admin/review`, per D-14) inherits the existing admin auth dependency, not a bare new route. |
| V5 Input Validation | Yes | Reconcile pass consumes untrusted-ish corpus fixture data (ConvoKit dataset) — existing apolitical allow-list stripping (`apolitical.extract_conversation_fields`/`extract_case_fields`, Phase 29 CR-01 precedent noted in STATE.md) already governs this and must be preserved unchanged for the reconcile branch, not just the first-import branch |
| V6 Cryptography | No | D-13's digest is an integrity/change-detection hash, not a security control — `sha256` via stdlib `hashlib` is adequate; no key management, no secret involved |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A malicious or malformed corpus fixture forcing an unbounded reconcile write (e.g. a crafted name-part value) | Tampering | Already mitigated by the existing `_values_differ`/`normalize_name_part` normalization contract and `decide_write`'s fail-closed `UNKNOWN` rank for any unrecognised `(source, method)` pair — an unrecognised incoming provenance can never outrank a stored value |
| A reconcile pass silently overwriting a published argument's live public data (the "seventh path" D-08 exists to close) | Tampering / Repudiation | D-08: compare-and-record but never write on PUBLISHED; this is a NEW check `decide_write` alone does not provide (authority answers "may this value overwrite," not "may anything write here at all" — the two gates compose, per code_context's own framing). Must be implemented as an explicit status check in the reconcile branch, not assumed to fall out of the authority ladder. |
| An unauthenticated or IDOR-style call reaching the new argument-scoped approve for an argument the caller shouldn't control | Elevation of Privilege | Reuse the existing `/admin` auth dependency and the existing scoped-select-then-update pattern (`T-49-idor` precedent in `resolve_participant_review`, admin_review.py:807-825) — select by argument_id, 404 on missing, never trust a client-supplied argument_id without a matching row |

## Sources

### Primary (HIGH confidence — read directly this session)
- `api/domain/authority.py` (full file, 183 lines) — `AuthorityRank`, `WriteDecision`, `authority_rank`, `decide_write`
- `api/services/admin_review.py` (lines 1-930, key ranges read in full: 1-290, 807-930) — the gated writer, discrepancy recorder, resolve actions
- `api/services/admin_jobs.py` (key ranges: 140-280, 377-423, 560-630, 653-746, 990-1035) — `get_run_id_for_step`, `approve_job`, resolve/update-resolve-row provenance handling, corpus EXISTS subqueries
- `api/services/admin_arguments.py` (key ranges: 505-745, 983-1080) — `update_argument`, `update_argument_metadata`, `publish_argument`, `delete_argument`
- `api/services/arguments.py` (full file, 153 lines) — the `MAX(ImportRun.id)` read path / blank-page hazard
- `api/services/admin_dev.py` (key ranges: 96-150, 167-335) — `FIXTURE_SET`, `reset_to_fixture`, `TRUNCATE_SQL`
- `api/models/models.py` (full enum block 38-109; full model bodies 121-700+ for Person, Case, Argument, CaseArgument, ArgumentParticipant, ImportRun, Utterance, ArgumentStatusLog, AdminJob, ValueDiscrepancy)
- `pipeline/commands/import_convokit.py` (full file read in sections: 1-60, 155-405, 445-945, 979-1355) — `_import_conversation`, `_resolve_and_link_participant`, `_import_utterances`, `run_import_convokit`, `_apply_extracted_name_provenance`
- `pipeline/commands/parse.py` (lines 260-340) — `ImportRun`/`ArgumentParticipant` writes on the PDF path
- `pipeline/commands/resolve.py` (lines 100-230) — the ungated bulk `person_id` UPDATE
- `pipeline/commands/import_justices_csv.py` (lines 1-40, 240-345) — the hand-rolled blank-only Person prefill
- `pipeline/commands/recompute_trust.py` (full docstring + top of function) — the `prune-runs` CLI shape precedent
- `pipeline/__main__.py` (lines 289-360) — CLI subcommand registration pattern
- `alembic/versions/0028_review_state_and_discrepancy.py` (full file, 165 lines) — DDL precedent for the new migration
- `alembic heads` (command run this session) — confirmed head is `0029`
- `api/tests/test_authority_matrix.py` (docstring + structure, 969 lines total) — existing exhaustive coverage
- `pipeline/tests/test_import_convokit_adminjob.py` (docstring, 22 lines) — the test file this phase's deletion invalidates
- `.planning/notes/import-architecture-diagnosis.md` (full file) — "Agreed direction" §2
- `.planning/notes/import-entity-sketch.md` (ADMIN_JOB/IMPORT_RUN entity block) — the sketch D-17 deviates from

### Secondary (MEDIUM confidence)
- None — every claim above was verified directly against source this session; no WebSearch was needed since this is a pure internal-codebase rework with no new external technology.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency; every module cited was read directly.
- Architecture: HIGH — every call site, model field, and migration cited was read directly this session, not inferred from the (stale) codebase maps.
- Pitfalls: HIGH for Pitfalls 1, 2, 3, 5 (all directly verified by reading the affected function bodies in full); MEDIUM for Pitfall 4 (the gap is verified — the models genuinely lack the columns — but the correct resolution is an open design question, not a verified fact).

**Research date:** 2026-08-25
**Valid until:** 30 days (stable internal codebase, no external API surface) — but re-verify against source again if any other phase or hotfix touches `import_convokit.py`, `admin_review.py`, `admin_jobs.py`, `admin_arguments.py`, or `admin_dev.py` before this phase's plan is executed, since all are actively-changing files.
