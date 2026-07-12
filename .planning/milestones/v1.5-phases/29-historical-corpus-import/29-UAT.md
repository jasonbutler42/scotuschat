---
status: complete
phase: 29-historical-corpus-import
source: [29-01-SUMMARY.md, 29-02-SUMMARY.md, 29-03-SUMMARY.md, 29-04-SUMMARY.md, 29-05-SUMMARY.md, 29-06-SUMMARY.md, 29-07-SUMMARY.md, 29-08-SUMMARY.md, 29-09-SUMMARY.md]
started: 2026-07-10T15:08:32Z
updated: 2026-07-10T15:16:00Z
---

## Current Test

[testing complete]

## Tests

### 1. [29-01/D1] data/corpus/ scaffolding tracked correctly
expected: data/corpus/ directory exists in the repo, tracked only via .gitkeep, with corpus file types (*.jsonl/*.json/*.csv) gitignored exactly like data/pdfs/
result: pass
source: automated
coverage_id: 29-01/D1

### 2. [29-01/D2] python-dateutil dependency installed
expected: python-dateutil declared in requirements.txt and importable in the project venv
result: pass
source: automated
coverage_id: 29-01/D2

### 3. [29-01/D3] Migration 0017 nullable oyez_* columns
expected: Migration 0017 adds three nullable oyez_* columns (cases.oyez_case_id, arguments.oyez_transcript_id, people.oyez_speaker_id), verified against the live database, with ORM models matching and a clean downgrade/upgrade round-trip
result: pass
source: automated
coverage_id: 29-01/D3

### 4. [29-02/D1] Streaming JSONL loader
expected: Streaming JSONL loader yields one utterance dict per line without loading the whole file into memory, plus term-scoped conversations/speakers/cases loaders
result: pass
source: automated
coverage_id: 29-02/D1

### 5. [29-02/D2] Stage-direction detector
expected: Stage-direction detector classifies curated markers (brackets or parens, typo-tolerant) and rejects legal-list/phonetic markers
result: pass
source: automated
coverage_id: 29-02/D2

### 6. [29-02/D3] Apolitical allowlist extractors
expected: Apolitical allowlist extractors provably exclude win_side/votes_side/scdb_docket_id and all related outcome fields, and never let unrecognized source keys pass through
result: pass
source: automated
coverage_id: 29-02/D3

### 7. [29-03/D1] Justice full_name reconstruction
expected: reconstruct_full_name() reproduces all 13 existing seed_aliases.py Person.full_name literals byte-for-byte from CSV-shaped name parts, with documented no-middle/no-suffix edge case handling
result: pass
source: automated
coverage_id: 29-03/D1

### 8. [29-03/D2] Upgrade existing Person in place
expected: run_import_justices_csv() upgrades an existing Person row in place (is_justice=True + one CourtTenure) matched by exact full_name, without duplicating the row or touching role_id/speaker_alias
result: pass
source: automated
coverage_id: 29-03/D2

### 9. [29-03/D3] Elevated justice dual tenures
expected: A justice appearing in both the Chief and Associate CSV sections gets both court_tenures rows auto-created for one Person row, not flagged for manual review
result: pass
source: automated
coverage_id: 29-03/D3

### 10. [29-03/D4] Idempotent justice CSV re-run
expected: Re-running the same CSV import twice creates zero duplicate people and zero duplicate tenures, including for the elevated-justice dual-tenure case
result: pass
source: automated
coverage_id: 29-03/D4

### 11. [29-03/D5] Blank end-date and no unintended fields
expected: Blank 'Date Service Terminated' CSV cells (currently-active justices) yield CourtTenure.end_date = None; the command never writes role_id and never creates speaker_alias rows
result: pass
source: automated
coverage_id: 29-03/D5

### 12. [29-03/D6] import-justices CLI registered
expected: import-justices subcommand (with --csv) is registered in the pipeline CLI and dispatches to run_import_justices_csv
result: pass
source: automated
coverage_id: 29-03/D6

### 13. [29-04/D1] import-convokit CLI validated
expected: import-convokit CLI subcommand with --term/--term-range (mutually exclusive, validated) and --corpus-dir (validated to exist before any file load)
result: pass
source: automated
coverage_id: 29-04/D1

### 14. [29-04/D2] Idempotent entity scaffolding
expected: Idempotent Case/Argument/CaseArgument/PipelineRun scaffolding at status=draft with Oyez external IDs, term_year sourced from cases.jsonl year, apolitical fields never persisted
result: pass
source: automated
coverage_id: 29-04/D2

### 15. [29-04/D3] Speaker resolution + side mapping
expected: Bench/advocate speaker resolution into Person (oyez_speaker_id-first, full_name fallback) and ArgumentParticipant rows with correct side, idempotent on (argument_id, raw_speaker_label)
result: pass
source: automated
coverage_id: 29-04/D3

### 16. [29-05/D1] Utterance rows preserve newline boundaries
expected: Each ConvoKit turn becomes one Utterance row with \n-delimited segment boundaries preserved verbatim in Text
result: pass
source: automated
coverage_id: 29-05/D1

### 17. [29-05/D2] Stage-direction row splitting
expected: Detected stage directions become separate Utterance rows with is_stage_direction=true and raw_speaker_label=None, in transcript sequence, including inline markers mixed with spoken segments
result: pass
source: automated
coverage_id: 29-05/D2

### 18. [29-05/D3] Streaming memory + sequence invariants
expected: Utterance streaming never loads utterances.jsonl fully into memory; one streaming pass per term, monotonic sequence unique per (argument_id, pipeline_run_id), pipeline_run_id always non-null; malformed rows flagged not crashed
result: pass
source: automated
coverage_id: 29-05/D3

### 19. [29-05/D4] Per-batch summary report
expected: Per-term/rollup summary report printed at the end of each term/batch run: term year, created/skipped/flagged/errored counts; broken cases.jsonl joins counted as errored rather than crashing the batch
result: pass
source: automated
coverage_id: 29-05/D4

### 20. [29-07/D1] Optional argued_date schema fields
expected: ArgumentMetadataResponse and CaseItem accept argued_date=None without raising pydantic.ValidationError
result: pass
source: automated
coverage_id: 29-07/D1

### 21. [29-07/D3] Frontend formatDate null-guard parity
expected: app/src/routes/cases/[slug]/+page.svelte's formatDate() null-guards argued_date, matching its two sibling pages
result: pass
source: automated
coverage_id: 29-07/D3

### 22. [29-08/D1] PipelineRun.step relabeled to "parse"
expected: pipeline/commands/import_convokit.py's PipelineRun creation writes step="parse", not step="ingest"
result: pass
source: automated
coverage_id: 29-08/D1

### 23. [29-08/D2] Corpus-imported utterances readable end-to-end
expected: get_argument_with_utterances (and therefore GET /arguments/{id}/utterances) returns the actual, non-empty, correctly-ordered, correctly-attributed Utterance rows for a corpus-imported Argument
result: pass
source: automated
coverage_id: 29-08/D2

### 24. [29-08/D3] PDF-ingest pipeline contract unaffected
expected: The PDF-ingest pipeline's separate ingest/parse/resolve PipelineRun contract and admin_jobs.py's job-resolution helpers are unaffected
result: pass
source: automated
coverage_id: 29-08/D3

### 25. [29-09/D1] Per-docket question_number derivation
expected: _next_question_number derives the next available question_number per source_docket (select max, +1, or 1 when none) so a reargued case or a PDF-ingested docket imports at question_number=2+ instead of colliding
result: pass
source: automated
coverage_id: 29-09/D1

### 26. [29-09/D2] IntegrityError safety net + distinct counter
expected: IntegrityError at the Argument flush is caught, rolled back, and counted in a distinct docket_question_conflict counter (never folded into conversations_errored), surfaced as its own labeled field in the per-batch summary
result: pass
source: automated
coverage_id: 29-09/D2

### 27. [29-06/D2] Attributions page renders three credit blocks + CC BY-NC 4.0 callout
expected: Visit /attributions. Page shows three credit blocks — Oyez.org, Cornell ConvoKit (with its two academic citations), and SCDB — plus a CC BY-NC 4.0 license callout, styled with the site's existing inline-style convention (no unstyled/broken layout).
result: pass

### 28. [29-06/D3] TopNav "Attributions" link + README credits
expected: Public TopNav shows an "Attributions" link (positioned after Cases, before Admin) that navigates to /attributions. README.md has a credits/attribution section mentioning Oyez, ConvoKit, and SCDB.
result: pass

### 29. [29-06/D4] Per-argument attribution note gated to corpus-sourced arguments
expected: Opening an existing PDF-ingested argument page shows NO attribution note (oyez_transcript_id is null for these rows). No corpus-sourced argument exists yet in this environment, so there is nothing to visually confirm on the "present" side of this gate — confirm the PDF-ingested case shows no note.
result: pass

### 30. [29-06/D1] oyez_transcript_id present on public argument payload
expected: For any argument's utterances API response (e.g. via the argument detail page's network payload or GET /arguments/{id}/utterances), the JSON includes an "oyez_transcript_id" key (null for PDF-ingested arguments, non-null once corpus-imported arguments exist).
result: pass

### 31. [29-07/D2] Utterances endpoint survives a null argued_date
expected: GET /arguments/{argument_id}/utterances returns 200 (not a 500 error) for an Argument with a null argued_date. This was independently verified via a bypass script in this environment due to a pre-existing test-infra limitation (documented FastAPI test lifespan/session-factory failure) — confirm no 500 errors are observed when browsing argument pages generally.
result: pass

## Summary

total: 31
passed: 31
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
