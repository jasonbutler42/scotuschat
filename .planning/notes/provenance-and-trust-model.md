# Provenance Vocabulary & Trust Model

**Date:** 2026-08-13
**Status:** Draft for review. Paper design only, no code / no DDL.
**Depends on:** `import-architecture-diagnosis.md` (unified-import-with-provenance direction)
**Scope:** The keystone data model for the import re-model. Column names below are
illustrative — Alembic remains the sole DDL authority; nothing here is final schema.

---

## Purpose

Make "how much do I trust this row, and where did it come from?" a **declared,
uniform attribute** instead of archaeology across `strategy` strings and nullable
`oyez_*` columns. This is what buys back confidence in the data.

## Intended mental model (read this first)

**Nothing is ever born public. Every argument enters as a candidate, is checked,
and is promoted.** Existence != visibility.

The natural gut model is a gate *before creation* — hold the data, check it, and
only then let a row exist. This design deliberately puts the gate one step later,
at **promotion to published**, not at row-creation. The pre-published, tiered,
review-queued state *is* the holding pen; there is no separate limbo.

Why the gate sits at promotion, not creation (all three are trust reasons):
- You cannot review what was never written — the candidate must exist to appear in
  the review queue.
- You cannot flag a discrepancy without both values present — re-import compares
  incoming against the held record.
- Idempotent re-import needs a stable row identity to update, not duplicate.

The reframe: the goal is not a **clean** database (bad data excluded at the door)
but a **fully-labeled** one (everything enters, every row states its trust). For
auditable legal transcripts, labeled beats clean — confidence comes from the
verdict on each row, not from faith that a door-check was perfect. The promotion
concept already exists latently in CLAUDE.md's rule "prior rows are not deleted
until the new run is promoted."

Open sub-choice: the holding pen is the status-based staging we already have
(candidate rows live in `arguments`, marked unpublished / UNCERTAIN) vs. a literal
separate staging table. Recommendation: status-based (same guarantee, no duplicated
schema). Revisit only if label-based staging stops feeling safe in practice.

## Design principles (guardrails)

1. **Provenance is a record, trust is derived.** Store *where/how* a value came
   from. Compute the trust tier from it via one documented function. Never store a
   subjective "trust score" a human can hand-wave.
2. **Operator work is sacred.** A re-import never overwrites a human-confirmed or
   human-edited value. This is the single most important invariant. It generalizes
   today's `name_extraction_metadata` rule ("an operator edit never clears or
   rewrites it") to the whole model.
3. **Trust is operator-facing, never public.** Trust tiers drive the review queue
   and the publish gate. They are never shown on the public site. The public sees
   only published-or-not. This protects the apolitical constraint.
4. **Trust means transcription/attribution accuracy, never content judgment.**
   It answers "did we capture and attribute this turn correctly," never anything
   about what was said. Every speaker (bench or advocate) uses identical schema and
   treatment, uniform across the board.
5. **Idempotent by construction.** Re-import is safe to run repeatedly because the
   authority ladder plus discrepancy-recording prevent silent clobbering.

---

## The provenance record

Four dimensions travel with an import unit (and with any individually-editable row):

**1 — `source` (where it came from).** Small closed vocabulary:

| value | meaning |
|-------|---------|
| `operator` | a human entered or edited it in the admin UI |
| `corpus` | structured import (ConvoKit / Oyez), carries authoritative external IDs |
| `pdf_pipeline` | parsed from a supremecourt.gov transcript PDF |
| `seed` | reference data loaded from a curated file (justices CSV, alias seeds) |

**2 — `method` (how, within that source).** Sub-dimension, replaces the overloaded
`strategy` string:

| value | applies to | meaning |
|-------|-----------|---------|
| `manual` | operator | typed / corrected by a human |
| `direct` | corpus, seed | verbatim from a structured field |
| `normalized` | corpus, pdf | derived by a deterministic transform (docket norm, name split) |
| `rule_based` | pdf_pipeline | deterministic parse of PDF text |
| `llm_corrective` | pdf_pipeline | LLM fallback where rules failed |

**3 — lineage pointers.** `import_run_id` (the batch that produced it),
`external_id` (oyez transcript/case/speaker id), `imported_at`.

**4 — `review_state` (human verification).** Orthogonal to source:

| value | meaning |
|-------|---------|
| `unreviewed` | no human has looked; may still be high-trust if corpus-direct |
| `needs_review` | flagged for a human (low-confidence extraction, or a detected conflict) |
| `operator_confirmed` | a human checked it and left it as-is |
| `operator_edited` | a human changed it |

---

## The authority ladder (the overwrite rule)

Every source has a fixed **authority rank**, highest to lowest:

```
operator  >  corpus  >  pdf_pipeline/rule_based  >  pdf_pipeline/llm_corrective
```

**Re-import rule:** an incoming value replaces an existing one *only if*
`incoming.authority >= existing.authority`.

- Equal authority (corpus refreshing corpus) → allowed, that is a normal refresh.
- Lower authority (a pdf re-parse hitting an operator-edited field) → **rejected**,
  the human value stands.
- Conflicting value at **higher-or-equal** authority that disagrees with what's
  there → do not silently overwrite; **record a discrepancy** for operator review
  (generalizes today's `admin_jobs.discrepancies`).

This one rule is what makes re-import both idempotent and safe.

---

## Trust tiers (derived)

Four ordered tiers, computed from `(authority, method, review_state)`:

| tier | derived when | operator meaning |
|------|-------------|------------------|
| **VERIFIED** | `review_state ∈ {operator_confirmed, operator_edited}` | human signed off, done |
| **TRUSTED** | `corpus` + `direct` (or `seed/direct`), unreviewed | safe to publish as-is |
| **PROVISIONAL** | `normalized`, or `pdf/rule_based`, unreviewed | usable, worth a glance |
| **UNCERTAIN** | `pdf/llm_corrective`, or anything with `review_state = needs_review` | review before publish |

Derivation order: `review_state` wins first (a confirmed row is VERIFIED whatever
its origin), otherwise fall to source/method. A `needs_review` flag floors the tier
at UNCERTAIN regardless of source.

**Argument-level rollup:** an argument's tier is the **floor (minimum)** of its
constituent utterances and attributions. One uncertain speaker attribution drags
the whole argument to UNCERTAIN, which is exactly the review signal the operator
wants before publishing.

**Recommended publish gate (open decision):** block publish while any UNCERTAIN
element remains, unless the operator explicitly confirms past it. Operator has final
authority, so this is a surfaced gate, not a hard lock. Flagged below for your call.

---

## Granularity — what carries provenance

Do not stamp provenance on every field. Stamp it where values can independently
diverge from their batch:

- **`import_run`** (the generalized `pipeline_runs` / `admin_jobs`): carries the
  batch `source`, `method`, external ids, timestamps. The lineage backbone.
- **Argument:** a materialized rolled-up `trust_tier` (floor of its parts) for cheap
  querying and the review queue. Derived, recomputed on change.
- **Utterance:** inherits its `import_run` provenance. Transcript text is not
  operator-edited today, so utterance trust = its run's trust. No per-row record
  needed unless that changes.
- **Person name-parts and `ArgumentParticipant` identity:** these *are*
  operator-editable, so they carry their own `review_state` + method independent of
  the run. This is where `name_needs_review` / `name_extraction_metadata` already
  live; generalize that pattern, don't reinvent it.

---

## Worked example

An 1980 argument imported from corpus, one speaker later fixed by an operator:

- Utterances: `source=corpus, method=direct, review_state=unreviewed` → **TRUSTED**.
- Speaker "Mr. Jones" the corpus mislabeled, operator corrects the person link:
  that `ArgumentParticipant` → `review_state=operator_edited` → **VERIFIED**.
- A later corpus re-import ships a *different* label for that same speaker. Authority
  check: incoming `corpus` < existing `operator`. **Rejected; discrepancy recorded.**
  The human fix stands, and the operator sees a note that the corpus disagrees.
- Argument rollup tier = floor(TRUSTED, VERIFIED, …) = **TRUSTED**. Publishable.

The operator never had to reconstruct any of this. It is stated on the rows.

---

## Backfill mapping (old → new)

Deterministic, no data loss:

| today | becomes |
|-------|---------|
| `pipeline_runs.strategy = "convokit_import"` | `source=corpus, method=direct` |
| `strategy = "rule_based"` | `source=pdf_pipeline, method=rule_based` |
| `strategy = "llm_corrective"` | `source=pdf_pipeline, method=llm_corrective` |
| `Person.name_needs_review = true` | `review_state=needs_review` |
| `name_extraction_metadata` present | seeds `method` + lineage for name parts |
| `oyez_*` non-null | populates `external_id`, corroborates `source=corpus` |

---

## Open decisions (for next session)

**1 →** Is `review_state` two states (`unreviewed` / `operator_touched`) or the four
above? Four gives a real review queue; two is simpler. Leaning four.

**2 →** Hard publish gate on UNCERTAIN, or advisory only? (Principle: operator is the
authority, but you asked for confidence in published data.)

**3 →** Does `import_run` fully replace both `pipeline_runs` and `admin_jobs`, or
replace `pipeline_runs` and re-point `admin_jobs` at it?

**4 →** Do we materialize `trust_tier` on Argument (fast, needs recompute triggers),
or derive it on read every time (always correct, slower)?
