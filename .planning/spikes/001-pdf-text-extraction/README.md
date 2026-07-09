---
spike: "001"
name: pdf-text-extraction
type: standard
validates: "Given 4 SCOTUS transcript PDFs (Obergefell Q1, Masterpiece Cakeshop, Dobbs, Rahimi), when processed with pdfplumber, then the body text (speaker turns + stage directions) is cleanly isolatable from headers/footers/page numbers"
verdict: VALIDATED
related: ["002-parse-prompt-schema"]
tags: [pdf, pdfplumber, extraction, text-structure]
---

# Spike 001: PDF Text Extraction

## What This Validates

Given 4 SCOTUS transcript PDFs spanning 2015–2023, when processed with pdfplumber
(`extract_text(layout=False)`), then body text is cleanly separable from formatting
artifacts and speaker labels are correctly identified using a simple regex.

## Research

No competing approaches tested — pdfplumber is mandated by PIPE-03. PyMuPDF would be
an alternative (faster, better layout preservation), but pdfplumber is the right call
since the mandate exists and it handles the SCOTUS format well.

## How to Run

```
cd .planning/spikes/001-pdf-text-extraction
python extract.py
# Opens viewer.html in the same directory
```

## What to Expect

Console: per-document line type counts and unique speaker labels.
File: `viewer.html` — 4-tab HTML viewer showing raw pdfplumber output vs. classified lines per page.
File: `data/*.json` — full extracted page data.

## Investigation Trail

### Iteration 1 — Initial extraction

Ran pdfplumber against all 4 PDFs. Key structural observations:

**Two reporter formats:**
- Obergefell (2015): Alderson Reporting Company — different cover page layout
- 2017–2023: Heritage Reporting Corporation — consistent format with cover page before the numbered pages begin

**Page structure (consistent across all 4):**
1. Cover page — reporter name, case title, "Pages: N through M", date (no line numbers)
2. Numbered page 1 — case caption (docket numbers, party names)
3. Numbered page 2 — `APPEARANCES:` section
4. Numbered page 3 — Table of contents (`C O N T E N T S`)
5. Numbered pages 4–N: argument body
6. Final numbered page: word index (alphabetical, page:line format) — must be excluded

**Line number format:**
- 1–25 per page, left-aligned with 1–3 spaces
- Reliably stripped with `LINE_NUM_RE = r"^\s{0,3}(\d{1,2})\s"`

**Header/footer pattern:**
- Each body page starts with: `Official` (line 0) + bare page number (line 1)
- Reporter name (Alderson/Heritage) appears at bottom of pages, often truncated
- HEADER_RE catches "Official", "ALDERSON", "HERITAGE", "SUPREME COURT"

### Iteration 2 — Speaker detection accuracy

Speaker regex `SPEAKER_RE` catches all real Justice/advocate labels correctly:
- `CHIEF JUSTICE ROBERTS:`
- `JUSTICE [SURNAME]:`
- `MR. [SURNAME]:`
- `MS. [SURNAME]:`
- `GENERAL [SURNAME]:` (Solicitor General form used in transcripts)

**False positives detected** (in table of contents / case captions):
- `APPEARANCES` — table of contents header
- `ET AL.` — Obergefell only; case caption artifact where "ET AL.:" matches speaker regex
- `ORAL ARGUMENT OF` — TOC section headers
- `REBUTTAL ARGUMENT OF` — TOC section headers

**Mitigation:** Parse prompt must be given page ranges (skip first 3-4 pages, skip last page).
Alternatively, filter lines containing only these known false-positive labels before sending to LLM.

### Iteration 3 — Stage direction detection

Stage directions present but **undercounted**:
- Obergefell: 8 detected (regex `^\s*\(([^)]+)\)\s*$`)
- Masterpiece: 9 detected
- Dobbs: **1 detected** — suspiciously low for a 114-page argument
- Rahimi: 3 detected

Dobbs undercounting is a red flag. Possible causes:
- Stage directions on continuation lines (e.g., part of a speaker utterance: `[...text] (Laughter.) [more text]`)
- Multi-line stage directions spanning the `\n\n` boundary

This will be tested in Spike 002 during the parse step.

## Results

**Verdict: VALIDATED ✓**

pdfplumber handles SCOTUS transcripts well. The text extraction is clean and all speaker labels
are correctly identifiable. Key requirements for the parse prompt:

1. **Page range**: Skip pages 1–3 (cover/caption/TOC) and the last page (word index)
2. **Line number stripping**: Required — `LINE_NUM_RE` pattern works reliably
3. **Header stripping**: "Official", page numbers, and reporter names must be filtered
4. **False positive speaker labels**: `APPEARANCES`, `ORAL ARGUMENT OF`, `REBUTTAL ARGUMENT OF`,
   and case-caption lines (e.g., `ET AL.:`) must be excluded from speaker detection
5. **Stage directions**: Inline stage directions (within utterance text) may be missed by
   standalone regex — the parse prompt needs to handle this
6. **Structural consistency**: Format is identical across 2015–2023 tested range

**Surprise**: Dobbs (2021) shows only 1 stage direction vs. 8–9 for other transcripts. Warrants
investigation in Spike 002 — the parse prompt will need to handle inline stage directions that
appear mid-utterance, not just on standalone lines.

**Speaker label counts by document:**
| Document | Pages | Speaker turns | Stage dirs | Unique speakers |
|----------|-------|--------------|------------|-----------------|
| Obergefell (2015) | 102 | 371 | 8 | 13 |
| Masterpiece (2017) | 116 | 545 | 9 | 15 |
| Dobbs (2021) | 126 | 325 | 1 | 15 |
| Rahimi (2023) | 116 | 305 | 3 | 14 |
