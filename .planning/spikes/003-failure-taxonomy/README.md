---
spike: "003"
name: failure-taxonomy
type: standard
validates: "Given the rule-based parser run across Obergefell Q1, Masterpiece Cakeshop, Dobbs, and Rahimi, then all failure modes are catalogued with type (structural vs false-positive), severity, frequency, and remediation path"
verdict: VALIDATED
related: ["001-pdf-text-extraction", "002-parse-prompt-schema"]
tags: [failures, taxonomy, validation, edge-cases, qa]
---

# Spike 003: Failure Taxonomy

## What This Validates

Given the rule-based parser (Spike 002) run across all 4 transcripts, then every failure mode
observed is classified and documented with enough detail to inform Phase 1 implementation decisions.

## How to Run

```
cd .planning/spikes/003-failure-taxonomy
# No script — analysis is in taxonomy.md
# All evidence is in ../002-parse-prompt-schema/results/*.json
```

## Results

**Verdict: VALIDATED ✓**

See `taxonomy.md` for the full taxonomy. Summary:

### Failure Mode Count

| Type | Count |
|------|-------|
| Structural (real bugs, now fixed) | 3 (F01, F02, F03) |
| Structural (known, low severity, unfixed) | 4 (F04, F05, F10, F12) |
| False positives (QA detector wrong, not parser) | 2 (F06, F07) |
| Cosmetic / benign | 3 (F08, F09, F11) |

### Critical Finding: Rule-Based Parser as Foundation

The LLM is NOT needed to parse the majority of SCOTUS transcript content. A rule-based
state machine handles ~95% of utterances correctly. The LLM's role in Phase 1 should be:

1. **Rule-based parser first** — handles 95% correctly, produces structured log
2. **LLM corrective pass** — only needed for F04 (TOC variants), F05 (complex inline stage
   directions), and future unknown transcript format variations

This hybrid approach:
- Keeps API costs low (only ambiguous pages go to the LLM)
- Makes failures debuggable (compare rule-based vs LLM output)
- Aligns with PIPE-06: "classify LLM failures as transient vs. structural"

### Remaining Work for Phase 1

| Priority | Item |
|----------|------|
| Must fix | F04: extend `TOC_SECTION_RE` to catch "ON BEHALF OF" variant |
| Must fix | F11: strip soft hyphens (U+00AD → "--") in text cleaning |
| Should fix | F06/F07: remove false-positive QA detectors |
| Acceptable as-is | F08, F09, F10, F12 |
