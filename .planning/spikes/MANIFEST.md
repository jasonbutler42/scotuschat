# Spike Manifest

## Idea

Spike the LLM parse prompt against real SCOTUS transcript PDFs to produce a validated
ParsedUtterance schema, a working prompt template, and a failure taxonomy before Phase 1
planning. STATE.md flags this as a blocker concern — the schema and prompt design can't be
finalized without knowing what the raw PDF text actually looks like and where the prompt fails.

## Requirements

Non-negotiable design decisions that must carry into the real build:

- Use pdfplumber for PDF text extraction (established in REQUIREMENTS.md / PIPE-03)
- Rule-based state machine parser is the primary parse strategy (~95% coverage)
- LLM parse step (when API access is available) is a corrective pass over rule-based output, not a replacement
- `is_stage_direction` must be a boolean field on every utterance — not inferred post-hoc
- `raw_speaker_label` must be the exact label from the transcript (e.g. "JUSTICE SOTOMAYOR", not "Sotomayor")
- `raw_speaker_label` is `None` for stage directions (not omitted)
- `section_hint` applies only to the FIRST utterance after a section transition — never cascades
- Short utterances ("I --", "Yes.", "Right.") are legitimate — never filter by length
- Long utterances (300+ words) are legitimate in contentious cases — no maximum length assumption
- Word-index page detection must be dynamic (WORD_INDEX_RE pattern), not a fixed page-count offset
- Soft hyphens (U+00AD) must be normalized to "--" during text cleaning before DB write
- Citations captured as raw text strings only — no resolution at parse time

## Spikes

| # | Name | Type | Validates | Verdict | Tags |
|---|------|------|-----------|---------|------|
| 001 | pdf-text-extraction | standard | Given 4 SCOTUS transcript PDFs (Obergefell Q1, Masterpiece Cakeshop, Dobbs, Rahimi), when processed with pdfplumber, then body text (speaker turns + stage directions) is cleanly isolatable from headers/footers/page numbers | VALIDATED ✓ | pdf, pdfplumber, extraction |
| 002 | parse-prompt-schema | standard | Given cleaned transcript pages, when run through a rule-based state-machine parser, then a correct ParsedUtterance array returns with accurate speaker labels, turn boundaries, stage direction classification, and section hints — across all 4 transcripts | VALIDATED ✓ | parser, schema, rule-based, utterances |
| 003 | failure-taxonomy | standard | Given the rule-based parser run across all 4 transcripts, then all failure modes are catalogued with type, severity, frequency, and remediation path | VALIDATED ✓ | failures, taxonomy, validation |
| 004 | argument-as-a-call | design | Given one argument rendered as a call in two arrangements — a uniform Teams-style grid and a courtroom layout — then which arrangement readers prefer, and whether either presents speaker prominence without asserting a conclusion P-03 forbids | OPEN — awaiting user testing | design, mockup, presentation, seed-002, p-03 |
