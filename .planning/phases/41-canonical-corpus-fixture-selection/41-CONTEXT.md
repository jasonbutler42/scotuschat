# Phase 41: Canonical Corpus Fixture Selection - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

This is a decision-gate phase, not an implementation phase. No importer code and no database rows change here. The deliverable is a **4-argument fixture set**, analyzed from the ~7,800-argument ConvoKit dataset and operator-confirmed:

- **1 complexity fixture** — the structurally-complex "canonical audit fixture" that Phase 42's field-by-field diff work targets exclusively.
- **3 state-variety fixtures** — chosen for publish/pipeline state (not complexity) so Phase 43's reset tool and Phase 45's publish/unpublish bug work have real states to exercise: one unpublished/DRAFT, one published, one mid-pipeline.

This widens the original single-fixture framing in ROADMAP.md/REQUIREMENTS.md (CORPUS-12) — both were updated during this discussion (see Implementation Decisions, D-03). Phase 42 still diffs only the complexity fixture; the full set matters starting at Phase 43.

</domain>

<decisions>
## Implementation Decisions

### Fixture Set Scope
- **D-01:** Fixture set widened from 1 to 4 arguments: 1 complexity fixture (Phase 42's diff target, unchanged in purpose) + 3 publish/pipeline-state variety fixtures (unpublished/DRAFT, published, mid-pipeline) for Phase 43/45. — **Reversibility:** costly — ROADMAP.md (Phase 41/42/43 goals + success criteria) and REQUIREMENTS.md (CORPUS-12, DEVTOOL-01) were already edited to reflect this during this discussion; reverting means re-editing both docs and re-narrowing three phases' success criteria.
- **D-02:** The 3 state-variety fixtures need no complexity floor — any argument matching the target publish/pipeline state is fine. Chosen for state-transition testing focus, not data complexity (that's what the complexity fixture is for).

### Complexity Scoring Method
- **D-03:** Score/rank candidates for the complexity fixture using a **path-coverage checklist**, not a weighted sum or lexicographic sort — rank by how many distinct importer-stressing paths a single argument covers at once (multi-advocate resolution, high-speaker-count dedup, long-transcript streaming, and — if resolvable, see Claude's Discretion below — multi-docket consolidation), rather than by raw magnitude on any one signal.
- **D-04:** Apolitical scoring boundary is a **hard exclusion rule**: the path-coverage checklist and any scoring must use only structural signals (advocate count, bench speaker count, utterance/turn count, docket/consolidation count) and must never read `win_side`, `votes_side`, `win_side_detail`, `votes_detail`, or any other outcome/SCDB-derived field from `cases.jsonl` — even though they sit in the same JSON record. — **Reversibility:** one-way — this is a direct instantiation of CLAUDE.md's apolitical hard constraint (identical treatment for every speaker, no derived political/outcome insight); relaxing it would violate a project-wide constraint, not just a phase decision.

### Shortlist Presentation
- **D-05:** Ranked shortlist shows the **top 5** candidates for the complexity fixture (state-variety fixtures aren't ranked — see D-02).
- **D-06:** Each shortlisted candidate shows raw signal numbers (advocate count, speaker count, utterance count) **plus** the path-coverage checklist annotation (which importer paths it covers) — matches the D-03 scoring method so the "why it ranked here" reasoning is visible, not just the numbers.

### Durable Fixture Record
- **D-07:** The confirmed fixture set is recorded as a **planning doc**, not a checked-in code constant — keeps this phase's "selection and confirmation only" boundary (no code changes) intact. Phase 43 (and any other consumer) reads the doc directly rather than importing a Python constant.
- **D-08:** File location: **`.planning/FIXTURES.md`** at the project root (not nested under the phase directory) — a cross-phase reference that Phase 42, 43, and 45 need to find without knowing Phase 41's directory name. Must record, per fixture: ConvoKit conversation id, case name, docket(s), term, argued date, and its role (complexity fixture, or which state variant).

### Claude's Discretion
- **Multi-docket consolidation signal is unresolved — needs one more research pass.** During this discussion, a naive check found 0 cases with comma-separated `docket_no` values and 0 conversations joined to more than one `cases.jsonl` row via `transcripts[].id`. `pipeline/commands/import_convokit.py`'s own module docstring notes the case/conversation join is done on `raw_case["id"] == conversation["case_id"]`, not on `docket_no` (which recycles across terms) — so a docket_no-format check was probably the wrong approach. Before dropping the multi-docket signal from the path-coverage checklist (D-03), the researcher should check `scdb_docket_id` and case-title patterns for a cleaner consolidation signal. If nothing surfaces, proceed with a 3-signal checklist (advocate count, speaker count, utterance count) — this is an acceptable fallback per D-03's intent, not a blocker.
- Exact wording/format of the `.planning/FIXTURES.md` doc (table vs. prose per fixture) is left to planning — D-08 only fixes location and required fields.

### Folded Todos
None — the two matches from `cross_reference_todos` didn't fit this phase's domain. See Deferred > Reviewed Todos below.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap (updated during this discussion)
- `.planning/ROADMAP.md` §"Phase 41: Canonical Corpus Fixture Selection" — goal, success criteria, and dependencies, now reflecting the 4-fixture set
- `.planning/ROADMAP.md` §"Phase 42" and §"Phase 43" — both reference the fixture set; Phase 42 depends on the complexity fixture only
- `.planning/REQUIREMENTS.md` — CORPUS-12 (this phase), DEVTOOL-01 (Phase 43, depends on this phase's output)

### Apolitical Constraint
- `CLAUDE.md` §"Key Constraints" — "Apolitical framing is a hard constraint. Every speaker (Justice or advocate) gets identical schema, depth, and treatment. No derived insight, summaries, sentiment, or statistics." Directly governs D-04.

### Carry-Forward Constraints (from STATE.md, relevant to this phase's neighbors)
- `.planning/STATE.md` §"Accumulated Context > Decisions" — Phase 29's positive apolitical allow-list (affects Phase 42, informs why D-04 matters here too); Phase 29 CR-01's `question_number` derivation rule (affects Phase 42/43 reseed); Phase 30's publish/AdminJob pairing requirement (affects Phase 43); Phase 31's test-DB isolation rule (affects any future reseed testing)

### No external specs beyond the above — requirements fully captured in Implementation Decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/corpus/loader.py` — `load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids` already parse the raw corpus files (`cases.jsonl`, `conversations.json`, `speakers.json`, `utterances.jsonl`); a fixture-analysis script should reuse these loaders rather than re-parsing JSON/JSONL by hand.
- `scripts/` directory already holds one-off analysis/audit scripts (`audit_tenure_seat_identifiers.py`, `cleanup_leaked_test_rows.py`, `migrate_tenure_offices.py`) outside the `pipeline/` package — an established precedent for where a throwaway fixture-selection script could live, consistent with this phase writing no importer code.

### Established Patterns
- `pipeline/commands/import_convokit.py`'s module docstring documents the case/conversation join key: `raw_case["id"] == conversation["case_id"]`, never `docket_no` (which recycles across terms per migration 0018's fix). Any multi-docket/consolidation analysis must follow this same join, not docket_no string matching.

### Integration Points
- The confirmed fixture set (`.planning/FIXTURES.md`, D-07/D-08) is the sole handoff artifact into Phase 42 (reads the complexity fixture) and Phase 43 (reads all 4, reseeds via the real `import-convokit` path per ROADMAP.md's Phase 43 goal).

</code_context>

<specifics>
## Specific Ideas

- Corpus scale observed during this discussion: 7,748 rows in `cases.jsonl`, 7,817 entries in `conversations.json`. Max advocate count seen in a single conversation is 16 (several conversations tie at that count).
- A naive multi-docket check (comma-separated `docket_no`, or a conversation id joined to >1 `cases.jsonl` row via `transcripts[].id`) found 0 matches either way — see Claude's Discretion above for the follow-up path.

</specifics>

<deferred>
## Deferred Ideas

- **Rename "Case" to "Argument" across DB schema, API routes (`/cases/`), and frontend.** Raised during this discussion as a valid observation (the product is arguments-only, "case" language is a holdover), but it's a cross-cutting rename spanning the DB model, routes, and corpus-loader naming — genuinely its own phase or milestone, not part of fixture selection. Logged in `.planning/REQUIREMENTS.md` Out of Scope and `.planning/STATE.md` Roadmap Evolution; not actioned this milestone.

### Reviewed Todos (not folded)
- `2026-07-28-unpublished-argument-visible-in-cases-list.md` — matched Phase 41 by keyword overlap (score 0.6) but its domain is the `/cases/` publish-visibility bug, already assigned to Phase 45 (BUG-01) per STATE.md. Not folded here.
- `2026-07-29-popover-scrollbar-outside-card.md` — matched Phase 41 by keyword overlap (score 0.9) but its domain is a popover styling bug, already assigned to Phase 45 (BUG-02) per STATE.md. Not folded here.

</deferred>

---

*Phase: 41-canonical-corpus-fixture-selection*
*Context gathered: 2026-07-29*
