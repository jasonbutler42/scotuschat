# Import Architecture — Diagnosis & Redesign Direction

**Date:** 2026-08-13
**Status:** Diagnosis complete; target design not yet started
**Author:** Jason + Claude (design conversation)
**Scope:** Design-only. No code touched. Does not affect Phase 46 / v1.7 delivery.

---

## Why this note exists

The import workflow has felt architecturally "off" for a while without a nameable
cause. This note pins down the cause, and records the agreed direction for a
design exercise (paper-first: ontology → pipeline design → wireframes + design
system) before any code changes.

Framing decision already made: this is **not** a rewrite. Same product, same
goals, same audience. The disappointment localizes to the import/provenance
layer. The fix is a **targeted re-model of that layer**, keeping the rest of the
app (read model, people, tenures, utterance display).

---

## What's actually in the model (as of this diagnosis)

The "we called arguments 'cases'" mistake is **mostly already corrected** in the
schema. The ontology is right:

- `cases` — one row per docket number (`14-556`). Consolidated dockets → multiple rows.
- `arguments` — one row per hearing session. **This is the real unit.**
- `case_arguments` — M:M join; one argument can cover several consolidated dockets.

Residual naming drift is now only at the **presentation layer**: the public route
is `/cases/`, but the thing it filters/publishes is an *argument*
(`published_at` lives on `arguments`). Users browse "cases" that are really
arguments. Cosmetic; cheap to fix; **not** the architectural problem.
(See also backlog `999.6-decide-listing-style-for-arguments`.)

## The two import paths

Two paths write into **one skeleton designed for only the first**:

```
PDF path (original)          admin_jobs → ingest → parse → resolve
  pipeline/commands/         INGEST/PARSE/RESOLVE steps, LLM corrective
  ingest, parse, resolve      passes, speaker_alias resolution, needs_review
                                        │
                                        ▼
                            Case / Argument / CaseArgument
                            PipelineRun / Utterance / ArgumentParticipant
                                        ▲
                                        │
Corpus path (newer)          import_convokit  ← reuses ingest._derive_slug,
  pipeline/commands/          resolve.normalize_label, and the SAME tables
  import_convokit
```

The schema treats **"a PDF that must be parsed with uncertainty"** as the
fundamental shape of an import. The corpus path — now the *primary, trustworthy*
source — is a guest in a house built for the PDF pipeline, and must pantomime
PDF-shaped artifacts to fit:

- **Fabricates a `pipeline_run` with no PDF.** `import_convokit.py:~115` stamps
  every imported argument with a synthetic run, `strategy="convokit_import"`,
  purely because `Utterance.pipeline_run_id` is `NOT NULL`. `PipelineRun`'s
  columns (`pdf_path`, `pdf_url`, `prompt_version`) are meaningless for corpus data.
- **Runs "resolution" for speakers that are already identified.** The corpus
  ships `oyez_speaker_id`; the whole `speaker_alias`/resolve machinery exists
  because the PDF path is *guessing*. The corpus path inherits the lifecycle anyway.
- **Touches `admin_jobs`** — a table modeled around an operator submitting one
  PDF at a time (`pdf_url`, `spaces_key`, `original_filename`,
  `current_step ∈ {INGEST, PARSE, RESOLVE}`).

## Root cause (one sentence)

> The import workflow feels wrong because the schema encodes the low-confidence
> PDF pipeline as the shape of reality, the new high-confidence corpus source has
> to disguise itself as a PDF parse to get in the door, and the thing most needed
> — **per-row provenance and trust** — was never made a first-class field.

Provenance today is *implied, never declared*. To answer "did this row come clean
from the corpus, or was it LLM-guessed from a smudgy PDF?" you must do
archaeology: join to `pipeline_runs` and read a free-text `strategy` string, or
check whether an `oyez_*` ID happens to be non-null. Trust is reconstructed, not
stated. That reconstruction burden is the source of the unease about data
trustworthiness.

---

## Agreed direction

**Unified import process with provenance as the discriminator** (chosen over two
separate lanes). PDF-parse and corpus-import become *peer strategies* of one
neutral import abstraction, distinguished by a declared source/trust attribute —
not by one impersonating the other.

Design targets (to be worked paper-first, in order):

1. **Make provenance first-class.** A declared `source`
   (e.g. `corpus` | `pdf_pipeline`) and trust level on the import unit, so
   accuracy is an attribute of the row, not an inference. This is the keystone
   that buys back confidence in the data.
2. **Generalize the run/job model.** Reshape `pipeline_runs` / `admin_jobs` into a
   neutral `import_run` where "parse a PDF" and "import a corpus record" are peer
   strategies. The corpus path should stop fabricating PDF artifacts; the PDF path
   keeps its parse/resolve lifecycle as one strategy among peers.
3. **Align the public noun.** Decide canonical argument-vs-case for routes/UI and
   follow through (ties to backlog `999.6`).
4. **Clean design system + low-fi wireframes** for the user-facing side, once the
   corrected domain language is settled (ties to backlog `999.8-figma-design-system`
   and `999.4-frontend-shared-component-library`).

Guardrails for the eventual re-model:
- Provenance/trust must survive **idempotent re-import** — re-running yields the
  same result, so trust is verifiable rather than one-shot.
- Migration path must preserve existing corpus + PDF data (backfill provenance
  from current `strategy` values / `oyez_*` nullability).

---

## Open design questions (next session)

- What is the exact provenance vocabulary and trust model? (binary source flag vs.
  richer confidence/lineage record)
- Does `import_run` fully replace both `pipeline_runs` and `admin_jobs`, or replace
  one and re-point the other?
- What happens to `Utterance.strategy` and `ArgumentParticipant` resolution fields
  under a unified model — do they become provenance-derived?
- Does the `/cases` → argument-centric route change land now (cheap) or wait for
  the design-system rework?

## Source references (verified during diagnosis)

- `api/models/models.py` — 13 tables; `Case`/`Argument`/`CaseArgument` separation;
  `PipelineRun` PDF-centric columns; no provenance column anywhere.
- `pipeline/commands/import_convokit.py` — corpus path; `PIPELINE_RUN_STRATEGY =
  "convokit_import"`; reuses ingest/resolve helpers; imports `AdminJob*` symbols.
- `pipeline/commands/ingest.py` — PDF path; `admin_jobs` job-aware mode; INGEST/
  PARSE/RESOLVE lifecycle.
- `CLAUDE.md` — architecture rules (pipeline offline-only; Alembic sole DDL
  authority; public `/cases` filters on `published_at`).
