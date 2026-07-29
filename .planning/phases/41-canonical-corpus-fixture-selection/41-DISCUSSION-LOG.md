# Phase 41: Canonical Corpus Fixture Selection - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 41-canonical-corpus-fixture-selection
**Areas discussed:** Complexity scoring method, Fixture set scope (emerged mid-discussion), Durable fixture record, Shortlist size & shape, Apolitical scoring boundary

---

## Complexity scoring method

| Option | Description | Selected |
|--------|-------------|----------|
| Weighted sum | Normalize each signal and sum with equal weights | |
| Lexicographic priority | Sort by one signal first, break ties with the next | |
| Path-coverage checklist | Rank by how many distinct importer-stressing paths a single argument covers at once | ✓ |

**User's choice:** Path-coverage checklist.
**Notes:** User confirmed this directly ("option 3 makes the most sense").

---

## Fixture set scope (emerged mid-discussion)

Raised when a follow-up question about the multi-docket signal (0 clean matches found in cases.jsonl) led the user to reconsider the phase's single-fixture framing.

**User's request (verbatim intent):** "If we can't find one perfect candidate that covers everything then let's plan on using more than one. In fact, let's plan on using more than one anyway so I can verify the cases list and things like publishing and unpublishing. Do you think we can limit these sample arguments to four?"

**Claude's proposal, confirmed by user:**

| Option | Description | Selected |
|--------|-------------|----------|
| 1 complexity fixture + 3 state-variety fixtures | Complex fixture for Phase 42's diff; 3 more for publish/pipeline-state variety (unpublished/DRAFT, published, mid-pipeline) to support Phase 43/45 | ✓ |
| All 4 complexity-ranked | Top 4 from the path-coverage ranking, no dedicated state picks | |
| Custom mix | User describes a different combination | |

**User's choice:** 1 complexity fixture + 3 state-variety fixtures ("Yes, that composition").
**Notes:** This required editing already-committed planning docs — ROADMAP.md (Phase 41/42/43 goals + success criteria) and REQUIREMENTS.md (CORPUS-12, DEVTOOL-01) were updated in place during this discussion, and STATE.md's Roadmap Evolution log got a new dated entry. Phase 42's diff scope is unchanged (still only the complexity fixture); only Phase 41's selection deliverable and Phase 43's reseed target widened.

---

## Multi-docket ("consolidated case") signal reliability

Sub-discussion that led into the fixture-set-scope conversation above.

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it, use 3 signals | Score on advocate/speaker/utterance counts only | |
| Investigate title/case-name patterns | Check case titles for consolidation formatting before dropping | |
| Check scdb_docket_id or other fields | Check whether scdb_docket_id encodes consolidation differently | |

**User's choice:** Not directly answered — superseded by the fixture-set-scope discussion above.
**Notes:** Left as an open item for the researcher (see CONTEXT.md > Claude's Discretion): try `scdb_docket_id` / title patterns first; fall back to a 3-signal checklist if nothing surfaces.

---

## Durable fixture record

| Option | Description | Selected |
|--------|-------------|----------|
| Planning doc | Markdown file, e.g. .planning/phases/41-.../FIXTURE.md or .planning/FIXTURES.md | ✓ |
| Checked-in code constant | pipeline/corpus/fixtures.py imported by Phase 43 | |
| Both — doc canonical, constant generated from it | | |

**User's choice:** Planning doc.

**Follow-up — file location:**

| Option | Description | Selected |
|--------|-------------|----------|
| Inside the phase dir | .planning/phases/41-.../41-FIXTURES.md | |
| Project-root planning doc | .planning/FIXTURES.md | ✓ |

**User's choice:** Project-root — `.planning/FIXTURES.md`.
**Notes:** Chosen so Phase 42/43/45 don't need to know Phase 41's directory name to find it.

---

## Shortlist size & shape

| Option | Description | Selected |
|--------|-------------|----------|
| Top 5 | | ✓ |
| Top 10 | | |
| Top 3 | | |

**User's choice:** Top 5.

**Follow-up — detail per candidate:**

| Option | Description | Selected |
|--------|-------------|----------|
| Signal numbers + coverage checklist | Raw counts plus which importer paths each candidate covers | ✓ |
| Signal numbers only | | |

**User's choice:** Signal numbers + coverage checklist.

---

## Apolitical scoring boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, hard exclusion | Never use win_side/votes_side/outcome fields in scoring | ✓ |
| Exclude by default, flag if conflict | | |

**User's choice:** Hard exclusion.

**Follow-up — complexity floor for state-variety fixtures:**

| Option | Description | Selected |
|--------|-------------|----------|
| Any argument matching the state is fine | | ✓ |
| Prefer moderately complex ones too | | |

**User's choice:** Any argument matching the state is fine.

---

## Claude's Discretion

- Multi-docket signal resolution approach (scdb_docket_id / title-pattern check vs. 3-signal fallback) — left to the researcher, see CONTEXT.md.
- Exact `.planning/FIXTURES.md` formatting (table vs. prose) — left to planning.

## Deferred Ideas

- Rename "Case" to "Argument" across DB schema, API routes (`/cases/`), and frontend — raised by the user mid-discussion, logged as out-of-scope in REQUIREMENTS.md and STATE.md, not actioned this milestone.
- Two todo matches (unpublished-argument-visibility, popover-scrollbar) reviewed via `cross_reference_todos` but not folded — both already assigned to Phase 45 per STATE.md.
