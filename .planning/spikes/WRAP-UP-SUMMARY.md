# Spike Wrap-Up Summary

**Date:** 2026-06-11
**Spikes processed:** 3
**Feature areas:** pdf-extraction, parse-utterances
**Skill output:** `.claude/skills/spike-findings-scotuschat/`

## Processed Spikes

| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001 | pdf-text-extraction | standard | VALIDATED ✓ | pdf-extraction |
| 002 | parse-prompt-schema | standard | VALIDATED ✓ | parse-utterances |
| 003 | failure-taxonomy | standard | VALIDATED ✓ | parse-utterances |

## Key Findings

**pdfplumber is the right tool.** Proven across 4 transcripts (2015–2023), two reporter
formats (Alderson, Heritage). Line-number stripping is reliable. Page structure is consistent.

**Rule-based parser covers ~95% of utterances.** A state machine with speaker-turn detection,
continuation-line merging, and three stage-direction patterns (standalone, inline, terminal)
produces 1,553 correctly parsed utterances across all 4 transcripts.

**LLM is a corrective pass, not the primary parser.** Running every page through Claude
is unnecessary. The rule-based pass handles almost everything; the LLM adds value only for
novel TOC format variants and complex inline stage directions.

**Schema is locked.** `ParsedUtterance` with `sequence`, `raw_speaker_label`, `text`,
`is_stage_direction`, `section_hint` — all constraints are in MANIFEST.md and the skill.

**12 failure modes catalogued** — 3 critical bugs found and fixed during spiking, 4 known
low-severity issues documented for Phase 1 implementation, 2 false-positive QA detectors
to remove, 3 cosmetic/benign patterns the UI team should know about.

**STATE.md blocker resolved.** The parse-step blocker from STATE.md ("Research recommends
spiking LLM parse prompt design before finalizing ParsedUtterance schema") is cleared.
Phase 1 planning can proceed.
