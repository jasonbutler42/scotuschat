# Phase 16: Parser Improvements - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 16 adds two extraction behaviors to the parse step:

1. **Cover-page metadata extraction (PARSE-01)** — Read the first 3 skipped pages of the transcript PDF (cover, caption, appearances) to extract `argued_date` and the lead case's `case_name`. Write `argued_date` to the `Argument` record; write `case_name` to the lead `Case` row (`case_arguments.is_lead = True`). Docket number is already set at ingest — no docket write. Operator sees pre-populated fields and can correct via Phase 11 argument edit UI.

2. **Advocate side detection (PARSE-02)** — Parse the appearances/TOC page (page 2) for explicit `ON BEHALF OF PETITIONER/RESPONDENT/AMICUS` lines. Build an advocate-name → side mapping and update matching `argument_participants.side` rows from `UNKNOWN` to `PETITIONER`/`RESPONDENT`/`AMICUS`. Unmatched participants stay `UNKNOWN`.

**Both extractions are fail-safe:** if extraction fails (non-standard/old format), the parse step continues without error and leaves existing fields unchanged. No new fallback fields or partial-write errors.

**Out of scope:**
- Updating `docket_number` or `docket_number_norm` on Case rows (set at ingest)
- Handling consolidated arguments specially (write to lead case only)
- LLM-assisted metadata extraction (regex-only in Phase 16)
- Any new admin UI for reviewing extracted values (operator uses existing Phase 11 edit UI)
- Testing with transcripts older than the spike's tested range (Obergefell 2015+)

</domain>

<decisions>
## Implementation Decisions

### Cover-Page Metadata Extraction (PARSE-01)

- **D-01:** Extraction is **regex-only** — no LLM call for cover page metadata. The spike confirmed Alderson and Heritage formats are highly consistent. A new function in `extractor.py` reads pages 0–2 (currently skipped by `extract_pages`).
- **D-02:** Writes `argued_date` to the `Argument` record (direct UPDATE on the existing row, same `argument_id` as the pipeline run).
- **D-03:** Writes `case_name` to the **lead Case row only** — the `Case` row where `case_arguments.is_lead = True` for this `argument_id`. Consolidated arguments have multiple Case rows; only the lead gets updated.
- **D-04:** **Always overwrite** — the parse step writes extracted values unconditionally, even if the operator previously edited them. On re-run (Phase 15 Re-run button), extraction replaces any prior values. Operator re-corrects if needed. No conditional "write-if-blank" logic.
- **D-05:** Failure fallback: if regex extraction returns `None` for any field, skip that field entirely (no write). Parse step continues normally — never raises or fails because of metadata extraction. Existing `argued_date`/`case_name` values remain as-is on extraction failure.

### Advocate Side Detection (PARSE-02)

- **D-06:** Source of truth for advocate sides is the **appearances/TOC page (page 2)**, which contains explicit lines like `ORAL ARGUMENT OF MR. CLEMENT, ON BEHALF OF PETITIONER`. This is parsed separately from the argument body pages.
- **D-07:** Build a `raw_speaker_label → SideEnum` mapping from the appearances page. Then `UPDATE argument_participants SET side = <mapped_value> WHERE argument_id = X AND raw_speaker_label = <label>`.
- **D-08:** Advocates in `argument_participants` that have **no match** in the extracted side mapping stay `UNKNOWN`. No all-or-nothing behavior — partial updates are accepted. Unmatched participants are left for the operator to assign via the Phase 15 advocate role dropdown.
- **D-09:** Failure fallback: if the appearances page yields zero side mappings (format unrecognized), skip the UPDATE entirely. All participants stay `UNKNOWN`. Parse step never fails because of side extraction.

### Claude's Discretion

- **Exact regex patterns** for cover page (case name line format, date line format — "Argued: [Month] [Day], [Year]" or similar). The researcher should look at actual cover page text from the 4 tested transcripts.
- **Speaker label matching strategy** for appearances → `argument_participants` — whether to use exact match or normalized match (strip punctuation, lowercase). The researcher should examine how consistently the appearances page name format matches the utterance `raw_speaker_label`.
- **Which of pages 0–2** contains each piece of data — the cover (page 0) has docket + case name + argued date; the appearances page (page 2) has advocate sides. Page 1 (case caption) may be redundant. Researcher confirms.
- Whether to add a new helper module (e.g. `pipeline/parser/cover_extractor.py`) or extend `extractor.py` directly.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Scope
- `.planning/REQUIREMENTS.md` §v1.3 Parser Improvements — PARSE-01, PARSE-02 (2 requirements this phase closes)
- `.planning/ROADMAP.md` §Phase 16 — Goal and 4 success criteria (all must be TRUE); note D-03 narrows SC-1 to lead case only

### Schema — Read Before Writing
- `api/models/models.py` — `Argument` model (line 157: `argued_date`, `status`, `argument_id`); `Case` model (line 140: `case_name`, `docket_number`); `CaseArgument` (line 189: `is_lead` flag — use this to find the lead Case row); `ArgumentParticipant` (line 223: `side` column, `raw_speaker_label`); `SideEnum` (Phase 15 expanded values: `PETITIONER`, `RESPONDENT`, `AMICUS`, `UNKNOWN`, `BENCH`, `ADVOCATE`)
- `api/alembic/versions/` — no migration needed for Phase 16 (no schema changes, only data writes)

### Existing Parser — Extend, Don't Rewrite
- `pipeline/parser/extractor.py` — `extract_pages()` (line 62): currently skips pages 0–2 via `range(3, len(pdf.pages))`; Phase 16 adds a new function that reads those same pages for metadata extraction. `normalize_text()` and `strip_line_number()` are reusable utilities.
- `pipeline/commands/parse.py` — `_run_parse_inner()`: the parse step sequence; Phase 16 adds metadata extraction calls between step 3 (extract pages) and step 4 (rule-based parse), and adds DB UPDATE calls before step 8 (transition to completed). Reads `source_run.argument_id` — use this to look up the Argument and its lead Case.
- `.claude/skills/spike-findings-scotuschat/references/pdf-extraction.md` — validated regex patterns and extraction function; `extract_pages` already proven; cover page structure documented (page 0 = cover with case name/docket/date)

### Phase 15 Context — Advocate Side Schema
- `.planning/phases/15-speaker-role-accuracy/15-CONTEXT.md` — D-05 through D-09: `SideEnum` expansion, `UNKNOWN` backfill, label map for popover display. Phase 16 writes initial sides; Phase 15 UI lets operator correct them.

### Phase 11 Context — Argument Edit UI (downstream recipient)
- `.planning/phases/11-argument-metadata-editing/11-CONTEXT.md` — D-05 (slug freeze on published), D-06 (published_at gate). The Phase 11 argument edit form is what the operator uses to review/correct Phase 16's pre-populated values — no new UI needed.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/parser/extractor.py` `strip_line_number()` — reusable for cleaning cover page lines before regex matching
- `pipeline/parser/extractor.py` `normalize_text()` — apply to cover page text before regex (handles soft hyphen artifacts)
- `pipeline/parser/extractor.py` `_is_word_index_page()` — not needed for cover pages, but shows the pattern: read raw page text, apply regex to classify
- `pipeline/commands/parse.py` `source_run.argument_id` — already available in `_run_parse_inner`; use to look up `Argument` and `CaseArgument` (is_lead) for DB writes

### Established Patterns
- **No new migrations** — Phase 16 only writes data to existing columns; `argued_date` and `case_name` columns already exist from earlier phases
- **Alembic DDL authority** — still applies; no `Base.metadata.create_all`
- **Dry-run check (CR-05)** — metadata writes must also be skipped in `args.dry_run` mode, same as utterance writes
- **asyncpg `statement_cache_size=0`** — already in engine config; no change needed
- **PIPE-11 re-run pattern** — a new parse creates a new `PipelineRun` row and new utterance rows; metadata writes to `Argument` and `Case` happen via UPDATE on existing rows (not tied to the PipelineRun row)

### Integration Points
- `pipeline/commands/parse.py` step sequence: metadata extraction slots in after `extract_pages()` (step 3) and before `parse_transcript()` (step 4). Cover page text is available from `pdf.pages[0]`–`pdf.pages[2]` directly inside pdfplumber context — open the PDF once and read both cover pages and argument pages in one pass.
- `argument_participants` rows are seeded in step 7b of the existing parse command. Side detection UPDATE should run in the same session, after step 7b (so the rows definitely exist before we UPDATE them).
- The `Case` update (case_name) requires a join through `case_arguments WHERE is_lead = True AND argument_id = X` to get the `case_id`, then `UPDATE cases SET case_name = X WHERE id = case_id`.

</code_context>

<specifics>
## Specific Ideas

- **Single PDF open pass**: Rather than opening the PDF twice (once for cover, once for argument pages), extend the pdfplumber `with` block to read all pages — cover pages (0–2) for metadata, then argument pages (3+) for utterances. One `pdfplumber.open()` call.
- **Appearances page format**: Lines on page 2 follow the pattern `ORAL ARGUMENT OF [SPEAKER], ON BEHALF OF [SIDE]` or `REBUTTAL ARGUMENT OF [SPEAKER], ON BEHALF OF [SIDE]`. The existing `TOC_SECTION_RE` in the state machine already matches this pattern — the researcher should check whether that regex can be reused directly to extract advocate names from appearances lines.

</specifics>

<deferred>
## Deferred Ideas

- **Docket number extraction** — The cover page contains the docket number, but the docket is already set at ingest. If the ingest-set docket ever needs to be corrected from the PDF, that's a future improvement.
- **Consolidated docket handling** — Updating all case rows (not just the lead) with the correct case name per docket from the PDF. Out of scope for Phase 16.
- **LLM-assisted extraction for non-standard formats** — Could be added as a fallback for older transcripts (pre-2015) if regex fails frequently. Note for a future parser improvement phase.
- **Extraction confidence / audit log** — Storing which fields were extracted vs. left blank, and whether they were overwritten on re-run. Useful for operator trust but adds complexity.

</deferred>

---

*Phase: 16-parser-improvements*
*Context gathered: 2026-06-26*
