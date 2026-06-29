# Phase 16: Parser Improvements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 16-parser-improvements
**Areas discussed:** Cover page parsing, Re-run write behavior, Advocate side detection, Write targets

---

## Cover Page Parsing

| Option | Description | Selected |
|--------|-------------|----------|
| Regex-only | Targeted patterns for cover page structure — fast, zero LLM cost, proven approach | ✓ |
| LLM-assisted with regex fallback | Try regex first; on failure send first 3 pages to Claude | |
| LLM-only | Always send cover pages to Claude — maximally robust but adds latency/cost | |

**User's choice:** Regex-only  
**Notes:** Spike validated that Alderson and Heritage formats are highly consistent. Cover page structure is simpler than argument body pages, so regex is sufficient.

---

## Re-run Write Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Always overwrite | Parse step always updates fields unconditionally | ✓ |
| Write-if-blank only | Only write to null/empty fields; protects operator corrections | |
| Write to staging field | Parser writes to separate column; operator explicitly "applies" | |

**User's choice:** Always overwrite  
**Notes:** Simple rule, no conditional logic. Operator re-corrects after re-run if needed. Consistent with how utterance rows work (new run replaces output).

---

## Advocate Side Detection

| Option | Description | Selected |
|--------|-------------|----------|
| Appearances page | Read page 2 directly for explicit ON BEHALF OF lines | ✓ |
| Section hints in utterances | Scan section_hint values from already-parsed utterances | |

**User's choice:** Appearances page  
**Notes:** Appearances page is the authoritative source — explicit advocate name + side mapping. Section hints were designed for utterance ordering, not side assignment.

### Follow-up: Speaker label matching strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Exact match on raw_speaker_label | Straightforward — names should match exactly | |
| Normalized match | Strip punctuation/lowercase before matching | |
| You decide | Leave matching strategy to researcher/planner | ✓ |

**User's choice:** You decide  
**Notes:** Researcher should examine actual transcript samples to determine how consistently appearances page names match utterance raw_speaker_labels.

### Follow-up: Unmatched advocates

| Option | Description | Selected |
|--------|-------------|----------|
| Leave them UNKNOWN | Only update participants with confident side match | ✓ |
| Fail the side detection step | All-or-nothing — if any unmatched, write UNKNOWN for all | |
| You decide | Leave to planner | |

**User's choice:** Leave them UNKNOWN  
**Notes:** Partial updates accepted. Operator assigns remaining via Phase 15 dropdown.

---

## Write Targets

Initial question: parser writes only `argued_date` to Argument record (skipping case_name/docket complexity for consolidated arguments).

**Flagged divergence from roadmap:** Success criterion 1 requires case name, docket, AND argued_date. Scoping to argued_date-only would partially miss this.

| Option | Description | Selected |
|--------|-------------|----------|
| argued_date only | Simple, avoids consolidated-case complexity; SC-1 partially unmet | |
| argued_date + lead case name/docket | Write argued_date + update lead Case row's case_name | ✓ |
| Full scope as roadmapped | Extract and write all three fields including docket | |

**User's choice:** Update roadmap + write argued_date + lead case  
**Notes:** Write `argued_date` to Argument; write `case_name` to the lead Case row (is_lead=True via case_arguments). Docket_number already set at ingest — no docket write needed. Narrows roadmap SC-1 to lead case only.

---

## Claude's Discretion

- Exact regex patterns for cover page (case name line format, date line format)
- Speaker label matching strategy (exact vs. normalized) — defer to researcher examining actual transcript samples
- Which of pages 0–2 contains each piece of data — researcher confirms
- Whether to add a new helper module or extend extractor.py

## Deferred Ideas

- Docket number extraction from PDF (already set at ingest; future improvement if needed)
- Consolidated docket handling — updating all case rows with correct per-docket case names
- LLM-assisted extraction fallback for very old/non-standard formats (pre-2015)
- Extraction confidence / audit log for operator trust
