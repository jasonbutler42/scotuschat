# Phase 38: Rethink Full Name vs. name-part fields in the people editor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-15
**Phase:** 38-full-name-vs-name-parts-rethink
**Areas discussed:** Name authority, Formatting rules, Legacy and gaps, Extracted name parts, Shared extracted-value presentation

---

## Name Authority

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Authoritative representation | Name parts authoritative; derived with override; independent fields | Name parts authoritative |
| Editor presentation | Live read-only preview; hide Full Name; show only after save | Live read-only generated preview |
| Applicability | Every path; operator interfaces only; main editor only | Every create/update/import/seed path |
| Compatibility storage | Keep synchronized; remove; keep temporarily | Keep and synchronize `full_name` |

**Notes:** Full Name must not remain independently editable. Existing consumers continue using the synchronized compatibility value.

---

## Formatting Rules

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Canonical pattern | `First Middle Last, Suffix`; no comma; last-name-first | `First Middle Last, Suffix` |
| Normalization | Whitespace only; normalize suffixes; preserve exactly | Whitespace only |
| Authored components | Preserve authored text; standardize initials; title case | Preserve authored text |
| Display ordering | Canonical everywhere; directory last-first; context-specific | Canonical everywhere |

**Notes:** Lists may still sort by Last Name. Formatting must preserve punctuation, casing, initials, particles, apostrophes, hyphens, and compound surnames.

---

## Legacy and Gaps

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Minimum new-person data | First or Last; both; First required | At least First or Last |
| Existing full-name-only rows | Preserve until conversion; auto-split; immediate manual cleanup | Automatically split |
| Ambiguous splits | Preserve and flag; guess everything; exception map | Preserve original and flag |
| Cleanup surface | People directory filter; migration report; stored flag only | People directory `Name review` attention filter |

**Notes:** A generic Admin Dashboard attention queue was explored as a possible future capability. The user concluded the focused People directory filter may be sufficient, so no general queue is currently requested or deferred.

---

## Extracted Name Parts

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Effect on saved fields | Fill blanks; explicit acceptance; always synchronize | Prepopulate blank saved fields only |
| Later extraction | Latest replaces reference; preserve first; full history | Latest replaces reference, saved values untouched |
| Partial/uncertain extraction | Confident parts only; complete names only; every best-effort guess | Store every best-effort interpretation |
| Transparency | Confidence only; extracted only; extracted plus raw; expanded stacked treatment | Confidence, extracted value, and raw text |

**User clarification:** The goal is transparency about what the system thought it saw so the operator can make corrections and improve future behavior. The removed job-rerun control is not being restored.

---

## Shared Extracted-Value Presentation

| Decision | Options considered | Selected |
|----------|--------------------|----------|
| Rollout scope | Global; name parts only; reusable now/global later | Global shared-component update |
| Layout | Existing inline hint; stacked two-line hint from mockup | Stacked two-line hint |
| Confidence presentation | High/Medium/Low; five levels; numeric; band plus score | High/Medium/Low |

**User clarification:** The supplied mockup was created after the extracted-value component had already been reworked. It is now the canonical design reference for the global component evolution. Its percentage example is superseded by the selected qualitative confidence band.

**Canonical mockup:** `.planning/phases/38-full-name-vs-name-parts-rethink/mockups/extracted-fields-stacked.png`

---

## Agent's Discretion

- Shared formatter/module boundary and enforcement mechanics.
- Migration parser, confidence model, and thresholds, within the locked preservation/review behavior.
- Persistence schema for extracted interpretations, confidence, and raw source text.
- Accessible responsive implementation details constrained by Phase 36 and the mockup.

## Deferred Ideas

None. The general Admin Dashboard queue idea is intentionally not deferred unless the focused People directory solution later proves inadequate.
