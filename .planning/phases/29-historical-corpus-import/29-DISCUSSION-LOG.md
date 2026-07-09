# Phase 29: Historical Corpus Import - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-09
**Phase:** 29-historical-corpus-import
**Areas discussed:** Justice roster prerequisite, Rollout / publish status, Advocate identity QA bar, Stage-direction fidelity, Attribution, Paragraphs and how to present them, Consolidated docket companions, Source file location

---

## Todo cross-reference (pre-area)

| Match | Score | Selected |
|---|---|---|
| Leave in backlog | Unrelated to a backend bulk-import script — same call Phase 28 made on this exact match. | ✓ |
| Fold into Phase 29 | Pull it in anyway. | |

**User's choice:** Leave in backlog.
**Notes:** "Edit affordance on utterances and speaker popover" todo, scored as a possible match — declined, matching Phase 28's precedent on the same todo.

---

## Justice roster prerequisite

| Question | Options | Selected |
|---|---|---|
| Fold backlog 999.10 into Phase 29, or keep separate? | Fold into Phase 29 ✓ / Keep as separate Phase 999.10 first | Fold into Phase 29 |
| Dedup match strategy against 13 already-seeded Person rows? | Exact full_name string match ✓ / Structured name-part match | Exact full_name string match |
| What happens to the 13 existing (old-model) Person rows? | Upgrade in place ✓ / Leave as-is, only add missing | Upgrade in place |
| Elevated justices (Rehnquist, Rutledge, appear in both CSV sections)? | Auto-create both tenure rows ✓ / Flag for manual review | Auto-create both tenure rows |

**User's choice:** All recommended options accepted.
**Notes:** None — straightforward acceptance of each recommendation.

---

## Rollout / publish status

| Question | Options | Selected |
|---|---|---|
| Published immediately or draft pending spot-check? | Land as draft ✓ / Auto-publish everything | Land as draft |
| One shot or staged? | Staged with checkpoints ✓ / One shot, all at once | Staged with checkpoints, by October Term (user's own addition) |
| Resumable/idempotent? | Resumable/idempotent ✓ / Single uninterrupted run is fine | Resumable/idempotent |
| Pipeline run provenance? | Real pipeline_runs rows ✓ / Minimal placeholder rows only | Real pipeline_runs rows |

**User's choice:** Draft status, staged-by-term, resumable, real provenance rows.
**Notes:** Mid-discussion, user asked whether "October Term" (the SCOTUS term-naming convention, which can span two calendar years) is being captured, since they suspect wanting it for future public-facing browse-by-term navigation. Verified `cases.jsonl`'s `"year"` field already IS the October Term start year (confirmed via American Airlines case: argued/decided in 1956, `"year": 1955`). Locked as D-15 in CONTEXT.md: `Case.term_year` sourced directly from that field, never derived from `argued_date`'s calendar year.

---

## Advocate identity QA bar

| Question | Options | Selected |
|---|---|---|
| QA gate on advocate matches per batch? | Import everything, no gate ✓ / Flag inconsistent-side advocates for review | Import everything, no gate |
| Advocate dedup against pre-existing manual Person rows? | Exact full_name string match ✓ / Fuzzy/normalized match | Exact full_name string match |
| Per-batch reporting? | Print a per-batch summary report ✓ / No report, check admin UI | Print a per-batch summary report |

**User's choice:** No automated gate (draft status is the gate), exact-match dedup, printed reports.
**Notes:** Follow-up raised by user when asked whether to continue this area: should we use the corpus's own identifiers (case_id, transcript id, speaker slugs) rather than only name-string matching? Framed as "standalone project" vs. "ecosystem synergy" (e.g. clean oyez.org outbound links). Resulted in a new decision:

| Question | Options | Selected |
|---|---|---|
| Add nullable external-ID columns (Case.oyez_case_id, Argument.oyez_transcript_id, Person.oyez_speaker_id)? | Yes, add the columns ✓ / No, don't persist them | Yes, add the columns |
| Should oyez_speaker_id be the primary re-run match key? | Primary key with full_name fallback ✓ / Informational only | Primary key with full_name fallback |

---

## Stage-direction fidelity

| Question | Options | Selected |
|---|---|---|
| Leave inline or split into rows? | Leave inline ✓(orig rec) / Regex-split into separate rows | Split into separate rows (user reframed: wants a future display toggle; splitting now is strictly more flexible, no extra cost) |
| General marker pattern? | N/A / Handle a general bracketed-marker pattern | (superseded by data-driven follow-up below) |

**User's choice:** Split into rows.
**Notes:** User asked to see what marker delimiters actually exist before deciding — Claude scanned 400K rows of `utterances.jsonl` directly rather than guess. Findings: markers appear in both `[brackets]` and `(parens)`; parens are heavily overloaded with legitimate non-stage-direction content (`(a)`/`(b)`/`(1)` list markers, `(ph)` phonetic-spelling annotations — thousands of occurrences); `(Inaudible)` in parens (37,883 occurrences) far outnumbers `[Inaudible]` in brackets (6,054) — parens can't be skipped. Follow-up decision:

| Question | Options | Selected |
|---|---|---|
| Marker matching approach given real data? | Curated vocabulary match (either delimiter) ✓ / Brackets-only, ignore parens | Curated vocabulary match |

---

## Paragraphs and how to present them (user-added area)

**Notes:** User provided two mockup images (`paragraphs - together.png`, `paragraphs - split.png`) showing the same 2-paragraph turn as one bubble with an internal gap ("together") vs. two separate consecutive bubbles ("split") — wants the "split" outcome. Claude checked the actual DB: existing PDF-pipeline utterances are stored as one flowing paragraph (sentences joined by spaces, no boundaries at all) — a genuine divergence from ConvoKit's per-sentence-timed `\n` boundaries.

| Question | Options | Selected |
|---|---|---|
| Given a real 6-segment example turn, split on every `\n` boundary or group into fewer/larger paragraphs? | Split on every boundary ✓(orig rec) / Group into fewer paragraphs | Neither — user: "preserve the data now and decide how we show it later" |

**Resulting decision (D-18 in CONTEXT.md):** Store one `Utterance` row per ConvoKit turn, `\n` boundaries preserved verbatim inside `Text` — not collapsed, not pre-split into multiple rows. Reversible in either direction later (render as line breaks, split into bubbles with a future grouping heuristic, or collapse to flowing prose) — same "preserve now, decide display later" principle as stage directions.

---

## Attribution (user-added area, expanded from "make sure we have proper attributions")

| Question | Options | Selected |
|---|---|---|
| Where should attribution live? (multiSelect) | Public footer/about ✓ / Per-argument note ✓ / Codebase/README ✓ | All three |
| Who gets credited? (multiSelect) | Oyez.org ✓ / Cornell ConvoKit ✓ / SCDB ✓ | All three |

**User's choice:** All locations, all three sources credited.
**Notes:** User explicitly asked Claude to verify actual license terms rather than assume, suspecting Oyez is CC BY-NC 4.0. Claude verified via WebSearch against Creative Commons' own wiki/registry — **confirmed**: Oyez audio/transcripts are CC BY-NC 4.0 (NonCommercial). ConvoKit separately requests 2 academic citations (not a legal license). SCDB's exact terms inconclusive but moot (SCDB's actual vote/outcome data is excluded from import per the apolitical constraint).

Follow-up decisions:

| Question | Options | Selected |
|---|---|---|
| Flag the CC BY-NC 4.0 / monetization tension at project level now, or wait for milestone boundary? | Flag now ✓ / Just note in phase CONTEXT.md | Flag now — added directly to `.planning/PROJECT.md` Constraints table during this discussion |
| Build the dedicated Attributions/License page in this phase or as backlog? | Build in this phase ✓ / Separate backlog item | Build in this phase |

User's own framing: "I know you aren't a lawyer so just use your best judgement on how and where we give proper attribution." Claude verified the license fact directly rather than deferring entirely to judgment, then flagged (not resolved) the business-strategy tension.

---

## Consolidated docket companions (user-added area, second round)

| Question | Options | Selected |
|---|---|---|
| Accept lead-docket-only, or research a companion source now? | Accept lead-docket-only ✓ / Research a companion-docket source now | Accept lead-docket-only |

**User's choice:** Accept lead-docket-only for this phase; companion-docket sourcing deferred as a separate research item.

---

## Source file location (user-added area, second round)

| Question | Options | Selected |
|---|---|---|
| Copy into project repo, or read from external absolute paths as-is? | Copy into the project first ✓ / Read from external paths as-is | Copy into the project first |

**User's choice:** Copy into the project repo before import runs, matching the existing "raw source files are immutable" convention. Claude added an explicit note (not asked as a separate question, but flagged as a risk): only copy the 4 needed files (~918MB total) — do NOT copy the 3 large NLP-annotation files (~7.5GB combined, irrelevant to this project).

---

## Claude's Discretion

- Exact wording/placement of the per-argument attribution note.
- Exact per-batch summary report format (fields, console layout).
- Exact ROADMAP.md bookkeeping for marking Phase 999.10 superseded/absorbed.

## Deferred Ideas

- Public-facing browse-by-October-Term navigation.
- Outbound linking to oyez.org case/justice pages using the new external-ID columns.
- Public argument-page toggle between inline and split stage-direction rendering (possibly a future account setting).
- Bubble-splitting granularity for multi-sentence utterances (explicitly left unresolved).
- Consolidated-docket companion sourcing research.
