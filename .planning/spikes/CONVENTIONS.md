# Spike Conventions

Patterns and stack choices established across spike sessions. New spikes follow these
unless the question requires otherwise.

## Stack

- **Language:** Python 3.12+
- **PDF extraction:** pdfplumber (`extract_text(layout=False)`) — no alternatives considered;
  mandated by PIPE-03 and proven reliable across 2015–2023 SCOTUS transcripts
- **LLM SDK:** anthropic (when API access is available) with `tool_use` + strict JSON schema
  for structured output — no instructor dependency needed
- **Viewer:** Vanilla HTML + inline CSS + `<script>` (no build step, no framework)
- **Output format:** JSON + HTML viewer in the same spike directory

## Structure

```
NNN-spike-name/
  README.md          # frontmatter + investigation trail + results
  *.py               # main script(s)
  data/              # extracted JSON artifacts
  results/           # parse results JSON
  pdfs/              # downloaded source PDFs (spike 001 only; others reference it)
  viewer.html        # self-contained HTML viewer
```

- Port conventions: not yet established (no server-side spikes yet)
- PDFs live in `001-pdf-text-extraction/pdfs/` — reused by subsequent spikes via relative path
- Scripts use `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")` for Windows CP1252 safety

## Patterns

- **Page skipping:** Skip first 3 PDF pages (cover, caption, TOC). Detect word-index pages
  dynamically via `WORD_INDEX_RE = r"^\w[\w...]{0,30}\s+\[\d+\]\s+\d+:\d+"` — stop at first
  page where 3+ lines match.
- **Line number stripping:** `LINE_NUM_RE = r"^\s{0,3}(\d{1,2})\s"` — reliably strips 1–25
  left-column line numbers from all SCOTUS transcripts tested.
- **Section hint application:** `pending_section_hint` is set by a TOC marker and consumed
  exactly once (as `current_section_hint`) by the next speaker flush. Never cascades.
- **Stage direction variants:** Standalone `(text)`, inline (split via `_split_inline_stages`),
  and terminal `sentence. (Whereupon, ...)` — all three patterns must be handled.
- **Soft hyphen normalization:** Strip U+00AD (soft hyphen) or replace with `--` before
  writing utterance text to the database.

## Tools & Libraries

| Package | Version | Notes |
|---------|---------|-------|
| pdfplumber | 0.11.9 | Works on all 4 tested transcripts (2015–2023) |
| anthropic | 0.109.1 | Installed; requires ANTHROPIC_API_KEY env var |
| Python | 3.14.4 | Project uses 3.12+ features (dataclasses, match, etc.) |
