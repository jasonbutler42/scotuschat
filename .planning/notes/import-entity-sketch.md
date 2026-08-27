# Import Re-model — Entity Sketch

**Date:** 2026-08-13
**Status:** Draft sketch for review. Paper design only, no DDL. Names illustrative.
**Depends on:** `provenance-and-trust-model.md`, `import-architecture-diagnosis.md`
**Scope:** The import/provenance slice and its immediate neighbors. Tables outside
this slice (roles, court_tenures, speaker_alias, argument_status_log, case_appearances)
are unchanged and omitted for altitude.

---

## Lifecycle (the mental model, as data)

```
   import_run writes rows          operator reviews          operator promotes
        (candidate)          →        (checks out)        →      (published)
   Argument.status=candidate      review_state / tiers       published_at set
   trust_tier set on arrival      resolves needs_review       gate: no UNCERTAIN
```

An `Argument` is **born as a candidate** (`status=candidate`, not public) and
carries a `trust_tier` from the moment it exists. It becomes public only when an
operator promotes it (`published_at` set). The pre-published row *is* the holding
pen. "Candidate" is a status, not a separate table.

Legend for field notes: **[NEW]** field/table added, **[CHG]** changed from today,
**[RET]** retired, plain = unchanged.

---

## Diagram

```mermaid
erDiagram
    CASE ||--o{ CASE_ARGUMENT : "linked via"
    ARGUMENT ||--o{ CASE_ARGUMENT : "linked via"
    ARGUMENT ||--o{ IMPORT_RUN : "produced by (1+ over time)"
    IMPORT_RUN ||--o{ UTTERANCE : "produces"
    ARGUMENT ||--o{ UTTERANCE : "contains"
    ARGUMENT ||--o{ ARGUMENT_PARTICIPANT : "has"
    PERSON ||--o{ ARGUMENT_PARTICIPANT : "resolved to"
    PERSON |o--o{ UTTERANCE : "speaks (null until resolved)"
    ADMIN_JOB |o--o| IMPORT_RUN : "spawns (operator PDF path only)"
    ADMIN_JOB |o--o| ARGUMENT : "targets"

    IMPORT_RUN {
        int id PK
        int argument_id FK "set once argument exists"
        enum source "operator|corpus|pdf_pipeline|seed  [NEW]"
        enum method "manual|direct|normalized|rule_based|llm_corrective  [NEW]"
        string external_id "oyez transcript id  [CHG from oyez_transcript_id]"
        enum status "pending|running|completed|failed|needs_review"
        string pdf_path "nullable, pdf_pipeline only  [CHG no longer fabricated]"
        string pdf_url "nullable, pdf_pipeline only"
        string prompt_version "llm_corrective only"
        timestamp created_at
        timestamp completed_at
        text failure_reason
    }

    ARGUMENT {
        int id PK
        date argued_date "nullable"
        int question_number "nullable"
        enum status "candidate|draft|published|unpublished  [CHG pipeline->candidate]"
        enum trust_tier "verified|trusted|provisional|uncertain  [NEW materialized rollup]"
        timestamp published_at "promotion gate (null=candidate)"
        timestamp resolved_at "pipeline-completion meaning retained"
        string source_docket "nullable dedup key"
        array source_dockets "full ordered docket list"
        jsonb cover_metadata
    }

    UTTERANCE {
        bigint id PK
        int argument_id FK
        int import_run_id FK "[CHG from pipeline_run_id]"
        int sequence
        text text
        bool is_stage_direction
        string raw_speaker_label "null for stage directions"
        enum side "BENCH|ADVOCATE|PETITIONER|RESPONDENT|AMICUS|UNKNOWN"
        int person_id FK "null until resolved"
        string section_hint
    }

    ARGUMENT_PARTICIPANT {
        int id PK
        int argument_id FK
        int person_id FK "null until resolved"
        string raw_speaker_label
        enum side "BENCH|ADVOCATE|..."
        string descriptor
        enum review_state "unreviewed|needs_review|operator_confirmed|operator_edited  [NEW]"
        enum method "how person link derived  [NEW]"
    }

    PERSON {
        int id PK
        string full_name
        string first_name
        string last_name
        bool is_justice
        string oyez_speaker_id
        enum review_state "generalizes name_needs_review  [CHG]"
        jsonb provenance_metadata "generalizes name_extraction_metadata  [CHG]"
    }

    CASE {
        int id PK
        string docket_number
        int term_year
        string case_name
        string slug
        string oyez_case_id
    }

    CASE_ARGUMENT {
        int case_id PK,FK
        int argument_id PK,FK
        bool is_lead
    }

    ADMIN_JOB {
        int id PK
        int import_run_id FK "[NEW] references run instead of fabricating one"
        int argument_id FK "nullable"
        enum status "pending|running|paused|completed|failed"
        text pdf_url
        text original_filename
        jsonb discrepancies "re-import conflicts surfaced for review"
    }
```

---

## What changed and why (per the four decisions)

**IMPORT_RUN replaces PIPELINE_RUN (Q3).** The provenance/lineage backbone.
`source` + `method` replace the single overloaded `strategy` string. `pdf_path`/
`pdf_url` are now nullable and only populated for `pdf_pipeline` — the corpus path
stops fabricating them. Utterances FK here (`import_run_id`). `ADMIN_JOB` now
*references* an import_run rather than the corpus path inventing a fake job; the
corpus CLI batch needs no admin_job at all.

**ARGUMENT gains `trust_tier` (materialized, Q4) and a candidate status.**
`trust_tier` is the floor rollup of its utterances + participants, recomputed by a
single function on every mutation path (import, edit, review). `status=candidate`
is the born-not-public state; `published_at` is the promotion gate. Publish is
hard-blocked while any UNCERTAIN element remains, override logged (Q2).

**Provenance sits where values diverge.** ARGUMENT_PARTICIPANT and PERSON are the
operator-editable rows, so they carry their own `review_state` (four states, Q1) +
`method`. UTTERANCE inherits provenance from its IMPORT_RUN (no per-row provenance;
`strategy` column **[RET]**). This generalizes the existing `name_needs_review` /
`name_extraction_metadata` pattern instead of reinventing it.

## Deliberately unchanged

CASE, CASE_ARGUMENT, and the utterance/participant/person *shapes* are stable. The
read model and public site are untouched by this slice. `roles`, `court_tenures`,
`speaker_alias`, `argument_status_log`, `case_appearances` are outside the re-model.

## Open items carried forward

- Confirm `import_run` is per-argument (preserves Utterance FK) vs. adding a
  separate `import_batch` grouping for corpus term-range runs. Leaning per-argument
  now, batch as a later optional grouping.
- Whether `status=candidate` reuses the existing `argument_status` PG enum (add a
  value) or is a rename of `pipeline`. Enum values can't be dropped in PG, so likely
  add `candidate` and stop using `pipeline`.
- Exact `method` vocabulary on ARGUMENT_PARTICIPANT for the person-link derivation.
