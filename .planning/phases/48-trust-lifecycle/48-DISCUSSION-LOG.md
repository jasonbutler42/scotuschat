# Phase 48: Trust & Lifecycle - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-18
**Phase:** 48-Trust & Lifecycle
**Areas discussed:** Status vocabulary, Tier storage + recompute, Review-signal gap, Override shape + log, Verification coverage, Carried defect repro, Migration + initial tier

---

## Todo cross-reference

| Option | Description | Selected |
|--------|-------------|----------|
| None — all five are noise | Five keyword matches, none about trust or lifecycle; leave for `/gsd-review-backlog` | ✓ |
| Bench classification silent fallback | Trust-adjacent: a silently wrong attribution is what a tier should catch | |
| Create-person popover side/selection | Operator-workflow polish, not lifecycle | |

**User's choice:** None folded.
**Notes:** All five recorded in CONTEXT.md's Reviewed Todos so future phases know they were considered.

---

## Status vocabulary

| Option | Description | Selected |
|--------|-------------|----------|
| candidate replaces pipeline; draft survives | Four-state lifecycle preserved; `admin_jobs` PIPELINE guards and the DRAFT-only delete gate keep working with a one-word rename | ✓ |
| candidate collapses pipeline + draft | One holding pen, closest to the design note's wording — but breaks `approve_job`'s DRAFT transition, the delete gate, and the status filters/counts | |
| You decide | Leave it to planning | |

**User's choice:** candidate replaces pipeline; draft survives.

| Option | Description | Selected |
|--------|-------------|----------|
| candidate → draft → published, draft required | Preserves today's Publish-button visibility rule; approve_job remains the minting step | ✓ |
| candidate can publish directly | One promotion, but the Publish control has to appear for candidates and approve_job's role becomes ambiguous | |
| You decide | | |

**User's choice:** draft required.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — log candidate at birth | Status history starts at the first state; makes the carried cascade defect reachable for every row | ✓ |
| No — keep logging from draft onward | Birth timestamp already recoverable from `import_run.created_at` | |
| You decide | | |

**User's choice:** Log candidate at birth.

| Option | Description | Selected |
|--------|-------------|----------|
| Stay hidden — Phase 49 surfaces them | Phase 48 stays a backend/data phase; the review queue is the screen meant to show candidates | ✓ |
| Show candidates in the arguments list now | Real frontend scope Phase 49 would then rework | |
| Backend only, but expose tier on the detail endpoint | Middle ground | |

**User's choice:** Stay hidden.
**Notes:** Superseded in part later — D-19/D-20 do add a minimal block-message UI and the detail-endpoint field, because the override would otherwise have no control. The list endpoints stayed untouched as chosen here.

| Option | Description | Selected |
|--------|-------------|----------|
| No — keep DRAFT-only, fix the cascade only | Phase 48's delete work is exactly the carried defect | ✓ |
| Yes — allow deleting candidates too | Needs a guard for candidates a running AdminJob owns | |

**User's choice:** Keep DRAFT-only.

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-exclude, unchanged | `list_arguments` / `get_argument_stats` untouched | ✓ |
| Default-exclude, filterable | Adds `candidate` to `valid_status_values`; read-layer scope this phase otherwise avoids | |

**User's choice:** Hard-exclude, unchanged.

---

## Tier storage + recompute

| Option | Description | Selected |
|--------|-------------|----------|
| Argument only — constituents computed on the fly | One materialized column, one drift surface; matches the design note | ✓ |
| Argument + participant columns | Faster Phase 49 queue queries, two surfaces to sync | |
| Argument + participant + utterance columns | Fastest reads, three drift surfaces | |

**User's choice:** Argument only.

| Option | Description | Selected |
|--------|-------------|----------|
| One shared Python function every writer calls | Pure derivation in `api/domain/` + a service helper called in-transaction; unit-testable, works offline and in the API | ✓ |
| A PostgreSQL trigger | Cannot drift, but duplicates vocabulary in PL/pgSQL and escapes the Python suite | |
| Function now, trigger as a later safety net | | |

**User's choice:** One shared Python function.

| Option | Description | Selected |
|--------|-------------|----------|
| Keep recomputing; drop recorded, never auto-unpublishes | Tier stays truthful; pulling public content stays an operator decision | ✓ |
| Auto-unpublish on drop to UNCERTAIN | Strongest confidence stance, but content vanishes without an operator acting | |
| Freeze the tier at publish | Simpler writes, but the stored value silently goes stale | |

**User's choice:** Keep recomputing, never auto-unpublish.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — an offline CLI recompute command | Repair tool and verification vehicle: recompute --all after a reseed must change 0 rows | ✓ |
| No — write paths only | Less scope, but no way to prove stored values match the derivation | |

**User's choice:** Ship the CLI command.

---

## Review-signal gap

| Option | Description | Selected |
|--------|-------------|----------|
| Adapt today's signal behind the final signature | Map `name_needs_review` / `name_extraction_metadata` so the gate has teeth day one | |
| Pass `unreviewed` for everything | No throwaway adapter; gate ships unexercised outside unit tests | |
| You decide | | ✓ |

**User's choice:** You decide.
**Notes:** Resolved by the later fan-out answer plus a source check — `argument_participants` has no review or method column today (`api/models/models.py:380-392`), and the floor reads per-argument rows only, so no per-argument review signal exists. Outcome recorded as D-13: keep the parameter, supply `unreviewed`, write no adapter.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — unresolved floors to UNCERTAIN | Unattributed speech is the attribution failure the tier measures; gives the gate teeth on corpus data | ✓ |
| No — unresolved is orthogonal to trust | Keeps the tier purely about provenance + review state | |
| Floors to PROVISIONAL, not UNCERTAIN | Visible without hard-blocking | |

**User's choice:** Floors to UNCERTAIN.

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude stage directions from the floor | Narrow carve-out on the existing `is_stage_direction` boolean | ✓ |
| Exclude stage directions AND UNKNOWN side | Risks excusing the rows most likely to be wrong | |
| You decide | | |

**User's choice:** Exclude stage directions only.

| Option | Description | Selected |
|--------|-------------|----------|
| Floor reads per-argument rows only | Recompute bounded to one argument by construction; no fan-out to design | ✓ |
| Fan out synchronously on person change | Always correct, but a justice name fix could recompute thousands of rows in one request | |
| Mark dirty, recompute in the CLI sweep | Bounded request time, knowingly stale until swept | |

**User's choice:** Per-argument rows only.

---

## Override shape + log

| Option | Description | Selected |
|--------|-------------|----------|
| Extend `argument_status_log` | Publishing past a block is a status transition; one table tells the whole story | ✓ |
| A dedicated `publish_override` table | Cleanest separation, second table to join | |
| Columns on `arguments` | Simplest read, but only holds the most recent override | |

**User's choice:** Extend `argument_status_log`.
**Notes:** Consciously revisits Phase 15's D-06 minimalism, which was scoped to v1.5 and predates trust.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — minimal: block message + reason prompt | Narrow scope on an existing page; without it the gate is a dead end | ✓ |
| Backend only — override via API, UI in Phase 49 | Leaves a period where UNCERTAIN arguments can't be published through the app | |
| Backend only, and don't block — warn in Phase 48 | Would contradict success criterion 4 and need a roadmap edit | |

**User's choice:** Minimal block-message + reason UI.

| Option | Description | Selected |
|--------|-------------|----------|
| Per publish attempt | Each publish carries its own acknowledgment and log row | ✓ |
| Sticky per argument | Less friction, but a lasting exemption that outlives its reason | |

**User's choice:** Per publish attempt.

| Option | Description | Selected |
|--------|-------------|----------|
| Required, non-empty free text | Enforced server-side; what makes "deliberate" real | ✓ |
| Optional — the acknowledgment alone is the record | Lower friction, but the entries that matter most may be empty | |
| Required, and must name the blocking elements | Strongest record, disproportionate scope | |

**User's choice:** Required, non-empty free text.

| Option | Description | Selected |
|--------|-------------|----------|
| Two distinct gates; only UNCERTAIN is overridable | `resolved_at` stays a hard precondition — incompleteness isn't a judgment call | ✓ |
| Fold `resolved_at` into the tier | One gate, but makes "the pipeline never finished" overridable | |
| You decide | | |

**User's choice:** Two distinct gates.

| Option | Description | Selected |
|--------|-------------|----------|
| No — same admin auth as every other mutation | Protection is the required reason plus the permanent log row | ✓ |
| Yes — require a typed confirmation phrase | Danger-Zone-style deliberateness | |

**User's choice:** No extra guard.

---

## Verification coverage

| Option | Description | Selected |
|--------|-------------|----------|
| Tests own tier coverage; fixture proves the happy path | Each vehicle proves what it honestly can; no synthetic fixture | ✓ |
| Build an unresolved-speaker fixture | Live end-to-end evidence, would close 14-UAT Test 8 — but partly synthetic | |
| Both — tests now, fixture as a stretch | | |

**User's choice:** Tests own tier coverage.
**Notes:** Accepted consequence — 14-UAT Test 8 and 26-UAT Test 26 stay open after this phase.

| Option | Description | Selected |
|--------|-------------|----------|
| An explicit test asserting public responses exclude `trust_tier` | Turns the apolitical constraint into a build failure | ✓ |
| Structural only — public schemas simply don't include it | True today, relies on nobody adding it later | |

**User's choice:** Explicit contract test.

| Option | Description | Selected |
|--------|-------------|----------|
| Detail endpoint + publish-block error | Detail page already fetches that endpoint; Phase 49 inherits a working field | ✓ |
| Publish-block error only | Minimum exposure, but the tier is invisible until something blocks | |
| You decide | | |

**User's choice:** Detail endpoint + publish-block error.

---

## Carried defect repro

| Option | Description | Selected |
|--------|-------------|----------|
| A failing-then-passing regression test | The test IS the live repro — reproducible, in CI forever, proves the fix | ✓ |
| Manual repro on the dev DB first | Highest confidence, but manual and needs credentials the audit lacked | |

**User's choice:** Failing-then-passing regression test.

---

## Migration + initial tier

| Option | Description | Selected |
|--------|-------------|----------|
| NOT NULL, default `uncertain`, then recompute | Fail-closed; unclassified reads as blocked, not publishable | |
| Nullable, populated by recompute | NULL honestly means "never computed", but pushes the question into every reader | |
| NOT NULL, computed inside the migration | Correct immediately, but duplicates the derivation in SQL | |

**User's choice (free text):** "I'm not concerned about existing arguments. We are going to be resetting to the fixture multiple times during development so I don't see much value in migration at this point. I leave this decision to you."
**Notes:** Taken as Claude's discretion. Recorded lean: NOT NULL with server default `uncertain`, no in-migration derivation — fail-closed and zero backfill logic, which matches the operator's point that backfill effort has no value here.

| Option | Description | Selected |
|--------|-------------|----------|
| Migration flips `pipeline` → `candidate` | One UPDATE; the dead enum value becomes genuinely dead | ✓ |
| Leave them; only new rows use `candidate` | DB is disposable, but every guard keeps accepting both values | |

**User's choice:** Migration flips them.

---

## Claude's Discretion

- How `trust_tier` arrives (column nullability / default) — operator explicitly deferred.
- Review-dimension sourcing — originally "you decide"; effectively resolved by the
  per-argument-rows-only decision and a source check.
- `trust_tier` column representation (native PG enum vs. ordered smallint).
- What tier an argument with zero utterances carries.
- Endpoint shape for the override (body flag on `POST .../publish` vs. its own route).

## Deferred Ideas

- Candidate visibility and any tier badge in the admin UI → Phase 49.
- Widening the delete gate to candidates → Phase 50.
- Person-level review signals reaching the argument floor → Phase 49.
- Auto-unpublish on a tier drop → rejected for this phase; revisit only if it proves real.
- A PostgreSQL trigger as a recompute safety net → possible after Phase 50.
- An unresolved-speaker fixture → rejected as partly synthetic; still the missing
  ingredient for 14-UAT Test 8 and 26-UAT Test 26.
- A structured per-constituent override acknowledgment → rejected as disproportionate.
