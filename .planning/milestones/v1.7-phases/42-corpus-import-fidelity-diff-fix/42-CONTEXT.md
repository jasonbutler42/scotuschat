# Phase 42: Corpus Import Fidelity Diff & Fix - Context

**Gathered:** 2026-07-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a field-by-field comparison of the confirmed complexity fixture (ConvoKit conversation 15169 — Baltimore & Ohio Railroad Company v. United States, docket 642, 1966 term) against what actually lands in the database via `import-convokit`, across all six affected tables (cases, arguments, utterances, people, argument_participants, court_tenures). Classify every gap as a real importer defect or an intentional exclusion (apolitical allow-list, schema-absent field, upstream-missing data). Fix every real defect in the importer's code path, then prove the fix by re-importing the fixture cleanly and re-running the same comparison. Backfilling the other ~7,800 arguments is explicitly out of scope — fixes apply only to this fixture's import path this milestone.

</domain>

<decisions>
## Implementation Decisions

### Getting the fixture into the database
- **D-01:** Conversation 15169 (1966 term) has never been imported — the only existing entrypoint (`import-convokit --term`) would pull in all 135 conversations from the 1966 term as a side effect of loading this one fixture. Build a new, scoped single-conversation import path (e.g., a conversation-id-targeted option on the importer) so only conversation 15169 lands in the database — not the accept-the-side-effect alternative of running the full term and relying on Phase 43's later database wipe to clean it up.

### court_tenures (judges' history table)
- **D-02:** `import-convokit` never writes to `court_tenures` at all — a separate tool (`import_justices_csv.py`) maintains judges' appointment/tenure history. For this table, the diff still verifies that the fixture's Justices already have correct, complete tenure data from that separate tool (an integrity check, not a diff against ConvoKit source, which has no tenure-equivalent data).
- **D-03:** If a gap is found in the judges' history data, it gets flagged in the findings but is NOT fixed as part of this phase — fixing it belongs to whatever tool/process normally maintains that data, a different system than the one this phase repairs.

### Diff artifact form
- **D-04:** The field-by-field comparison and its classifications are written to a saved, durable document (same pattern as Phase 41's `.planning/FIXTURES.md`) — not console/log output that disappears after the run.

### Classification review process
- **D-05:** Every real-defect-vs-intentional-exclusion classification requires the operator's explicit review and approval before any code fix is applied — mirrors Phase 41's confirm-before-proceed gate. Claude does not self-approve a classification and start fixing.
- **D-06:** Review happens as one batch: the full comparison document is finished first (every gap found and classified), then the operator reviews the whole thing at once and approves/adjusts per gap — not a stop-and-confirm loop on each individual gap as it's discovered.

### Folded Todos
None — the two todo matches (`2026-07-28-unpublished-argument-visible-in-cases-list.md`, `2026-07-29-popover-scrollbar-outside-card.md`) don't fit this phase's domain; both are already assigned to Phase 45 per STATE.md. See Deferred > Reviewed Todos below.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/ROADMAP.md` §"Phase 42: Corpus Import Fidelity Diff & Fix" — goal, success criteria, dependency on Phase 41
- `.planning/REQUIREMENTS.md` — CORPUS-13 (field-by-field comparison), CORPUS-14 (fix + re-verify)

### Fixture Identity
- `.planning/FIXTURES.md` — confirmed fixture set; this phase reads only the "Complexity fixture" row (conversation 15169, docket 642, 1966 term, argued 1967-01-09)

### Apolitical Constraint
- `CLAUDE.md` §"Key Constraints" — apolitical framing hard constraint; governs how the diff must classify outcome/vote fields as forbidden, never "restorable"
- `pipeline/corpus/apolitical.py` — the sole sanctioned allow-list extractor module; `FORBIDDEN_FIELDS` is the canonical list of fields that must never be persisted anywhere

### Carry-Forward Constraints (from STATE.md, relevant to this phase)
- `.planning/STATE.md` §"Accumulated Context > Decisions" — Phase 29's positive apolitical allow-list rule (governs classification here); Phase 29 CR-01's `question_number` derivation rule (`select(func.max(...))` per docket — any new scoped-import path must preserve this, never hardcode `1`); Phase 30's requirement that corpus-imported arguments land at `status=PIPELINE` paired with a PAUSED/RESOLVE AdminJob

### Code Being Diffed and Fixed
- `pipeline/commands/import_convokit.py` — the importer under audit; its module docstring documents the case/conversation join key (`raw_case["id"] == conversation["case_id"]`, never `docket_no`)
- `api/models/models.py` — `Case`, `Argument`, `Utterance`, `Person`, `ArgumentParticipant`, `CourtTenure` ORM models — the "what actually lands in the DB" side of every comparison row

No other external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pipeline/corpus/loader.py` — `load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids` already parse the raw corpus files; a scoped single-conversation import path (D-01) should reuse these loaders, not re-parse JSON/JSONL by hand.
- `scripts/` directory already holds one-off analysis/audit scripts outside the `pipeline/` package (precedent from Phase 41) — a throwaway diff-generation script could live here if it isn't wired into the importer CLI itself.

### Established Patterns
- `pipeline/corpus/apolitical.py`'s positive-allowlist extractor pattern (`extract_case_fields`, `extract_conversation_fields`) is the single sanctioned translation layer from raw ConvoKit dicts into ORM-bound values — any newly-discovered field must be checked against this allow-list before being added anywhere, per the apolitical hard constraint.
- `_next_question_number` (in `import_convokit.py`) derives `question_number` via `select(func.max(...))` against the real `(source_docket, question_number)` DB constraint — any new scoped-import path (D-01) must call this same helper, not hardcode a value.

### Integration Points
- `pipeline/commands/import_convokit.py`'s CLI arg handling (`_resolve_terms`, `_resolve_corpus_dir`) and its per-conversation entry point (`_import_conversation`) are where a new scoped single-conversation import path (D-01) would hook in.
- A scoped single-conversation import capability, once built for this phase, is very likely reusable by Phase 43 (Dev-Only Reset to Fixture) — that phase needs to seed exactly 4 specific conversations spanning 4 different terms (1955, 1966, 1985, 2010), and running `--term` for each would pull in unwanted extra conversations from every one of those terms, the same problem this phase is solving for just conversation 15169. Not a decision for this phase, but worth flagging for whoever plans Phase 43.

</code_context>

<specifics>
## Specific Ideas

- Term 1966 (the fixture's term) has 135 conversations total in `conversations.json`; the fixture's own case id is `"1966_642"`.
- Already spotted during scouting (not a new decision — just confirming the phase's own classification framework already covers it): `apolitical.extract_case_fields()` reads `decided_date`, `citation`, and `court` from the raw case record, but the `Case` ORM model has no columns for any of the three. This is a pre-identified "schema-absent field" case per CORPUS-14's own classification categories (real defect / apolitical allow-list / schema-absent field / upstream-missing data) — flag it in the comparison document under that category rather than treating its discovery as new information requiring a fresh decision.
- Corpus source data is already present locally at `data/corpus/` (`cases.jsonl`, `conversations.json`, `speakers.json`, `utterances.jsonl`) — no re-download needed to build or run the diff.

</specifics>

<deferred>
## Deferred Ideas

None new this phase — discussion stayed within phase scope.

### Reviewed Todos (not folded)
- `2026-07-28-unpublished-argument-visible-in-cases-list.md` — publish-visibility bug, already assigned to Phase 45 (BUG-01) per STATE.md. Not folded here.
- `2026-07-29-popover-scrollbar-outside-card.md` — popover styling bug, already assigned to Phase 45 (BUG-02) per STATE.md. Not folded here.

</deferred>

---

*Phase: 42-corpus-import-fidelity-diff-fix*
*Context gathered: 2026-07-29*
