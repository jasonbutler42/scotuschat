# Canonical Corpus Fixture Set

## Status

Status: PROPOSED (2026-07-29). No downstream phase may treat this four-fixture set as final until Plan 03 records the operator's explicit confirmation (or redirect) and rewrites this status line.

## Ranked Shortlist (evidence)

| Rank | Coverage | Conversation ID | Case Name | Docket | Term | Advocates | Distinct Speakers | Bench Speakers | Turns | Transcripts | Flags hit |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 3/4 | 15169 | Baltimore & Ohio Railroad Company v. United States | 642 | 1966 | 9 | 15 | 8 | 479 | 2 | multi_advocate_resolution, high_speaker_dedup, reargument_question_number |
| 2 | 3/4 | 14969 | Shapiro v. Thompson | 9 | 1967 | 9 | 14 | 7 | 447 | 3 | multi_advocate_resolution, high_speaker_dedup, reargument_question_number |
| 3 | 2/4 | 15428 | United States v. First City National Bank of Houston | 914 | 1966 | 5 | 12 | 7 | 1080 | 2 | long_transcript_streaming, reargument_question_number |
| 4 | 2/4 | 14852 | Allen v. State Board of Elections | 3 | 1968 | 7 | 13 | 8 | 868 | 2 | long_transcript_streaming, reargument_question_number |
| 5 | 2/4 | 15463 | Interstate Circuit, Inc. v. City of Dallas | 56 | 1967 | 3 | 11 | 8 | 767 | 2 | long_transcript_streaming, reargument_question_number |

Signal distributions across all 7,817 scored conversations (from the same full-corpus run):

- `advocate_count`: max=16, top10=[16, 16, 16, 16, 12, 12, 10, 9, 9, 9], mean=2.6, median=2
- `distinct_speaker_count`: max=18, top10=[18, 15, 15, 14, 14, 14, 14, 14, 13, 13], mean=8.5, median=9
- `bench_speaker_count`: max=10, top10=[10, 10, 10, 10, 9, 9, 9, 9, 9, 9], mean=6.3, median=7
- `turn_count`: max=1080, top10=[1080, 1049, 868, 858, 835, 767, 746, 742, 736, 728], mean=217.6, median=213
- `n_transcripts` distribution: {1: 5781, 2: 1716, 3: 192, 4: 108, 5: 5, 6: 6, 9: 9}

This durably preserves the shortlist evidence (D-05, D-06) so nobody re-runs the 900MB streaming pass to reconstruct the reasoning (RESEARCH OQ #2).

## Signal definitions and thresholds

Four path-coverage flags, each an independent boolean (D-03: ranked by how many are true, never by a weighted composite):

- `multi_advocate_resolution` — threshold `advocate_count >= 9`. Source: the per-conversation `advocates` mapping from `conversations.json` (never the case-level `advocates` dict in `cases.jsonl`).
- `high_speaker_dedup` — threshold `distinct_speaker_count >= 14`. Source: distinct, non-unattributed speaker ids seen in `utterances.jsonl`'s `speaker` field for the conversation, cross-referenced against `speakers.json`'s own `type` field (never a naming-convention guess).
- `long_transcript_streaming` — threshold `turn_count >= 700`. Source: total utterance row count for the conversation, streamed once from `utterances.jsonl`.
- `reargument_question_number` — threshold `n_transcripts >= 2`. Source: count of `transcripts[]` entries on the conversation's joined `cases.jsonl` row (by `case_id`, never `docket_no`).

Scoring reads only structural fields via the project's apolitical allowlist extractors (`pipeline.corpus.apolitical`'s `extract_case_fields` / `extract_conversation_fields`), so no outcome-derived or SCDB-derived field influenced any ranking (D-04).

## Fixture Set

| Role | Conversation ID | Case Name | Docket(s) | Term | Argued Date |
|---|---|---|---|---|---|
| Complexity fixture | 15169 | Baltimore & Ohio Railroad Company v. United States | 642 | 1966 | 1967-01-09 |
| unpublished/DRAFT target | 13015 | Archawski v. Hanioti | 351 | 1955 | 1956-03-05 |
| Published target | 18897 | Anderson v. Liberty Lobby, Inc. | 84-1602 | 1985 | 1985-12-03 |
| Mid-pipeline target | 22372 | Abbott v. United States | 09-479 | 2010 | 2010-10-04 |

All four rows share this one shape and differ only in the Role cell and its values (D-01, D-08).

Argued dates above were produced by `scripts/select_corpus_fixtures.py`'s `_argued_date` helper, which prefers the project's `dateutil` fuzzy parse of the selected `transcripts[]` entry's `name` string and falls back to a stdlib regex + `strptime` match on a `"Month DD, YYYY"` substring when `dateutil` is unavailable. This run had `dateutil` installed, so every date above is a `dateutil` fuzzy parse. A later reader comparing these dates against the importer's own `_parse_argued_date` output should confirm which parser produced both sides before treating a mismatch as a bug.

## Why the complexity fixture ranked first

Recommended: conversation 15169 (Baltimore & Ohio Railroad Company v. United States), coverage 3/4.

Flags hit: multi_advocate_resolution, high_speaker_dedup, reargument_question_number. Flags missed: long_transcript_streaming.

9 advocates (clears the `multi_advocate_resolution` threshold, exercising the importer's per-conversation advocate-resolution loop against `conversations.json`'s own `advocates` dict), 15 distinct non-unattributed speakers (clears `high_speaker_dedup`, exercising `_resolve_person` dedup across many `Person` rows), 2 transcript entries for the same docket (clears `reargument_question_number`, exercising `_next_question_number`'s per-docket increment and `_parse_argued_date`'s per-transcript-id date matching). It does not clear the 700-turn `long_transcript_streaming` threshold (479 turns).

Runners-up (operator-selectable):

- Conversation 14969 (Shapiro v. Thompson) — tied at 3/4 coverage, same three flags hit (multi_advocate_resolution, high_speaker_dedup, reargument_question_number), 9 advocates, 14 distinct speakers, 3 transcript entries, 447 turns.

This tie is settled by the operator's confirmation, not by the script's ordering. Both candidates are justified strictly by which importer code paths they exercise — advocate-resolution volume, speaker-dedup volume, and per-docket re-argument/question-number handling — never by either case's subject matter, notability, or outcome.

Reconciliation note: RESEARCH.md's earlier exploratory pass (produced during discuss-phase research, before the scoring script existed in its current form) expected conversation 14837 (Permian Basin Area Rate Cases) to lead with 15169, 14852, and 14969 tied as runners-up. This full-corpus, script-driven run does not reproduce that result: 14837 does not appear in the top 5 at all, because it clears only 2 of 4 flags (multi_advocate_resolution, reargument_question_number) — it misses high_speaker_dedup once real per-conversation distinct-speaker counts (excluding the ConvoKit unattributed sentinel, cross-referenced against `speakers.json`'s own `type` field) are streamed from the complete `utterances.jsonl`, rather than approximated during the earlier research pass. 14852 (Allen v. State Board of Elections) similarly clears only 2/4 in this run (long_transcript_streaming, reargument_question_number), missing multi_advocate_resolution. This document's numbers are the authoritative full-corpus, complete-cache result (`data/corpus/fixture_scan_cache.json`, complete=true, rows_scanned=1700789); RESEARCH.md's table is the prior, superseded expectation.

## State-variety roles are Phase 43 targets

`cases.jsonl` and `conversations.json` carry no publish or pipeline state at all. A freshly-imported argument always lands at the importer's own initial pipeline status (status=PIPELINE, paired with a PAUSED/RESOLVE AdminJob per Phase 30). The three role labels above — unpublished/DRAFT target, Published target, Mid-pipeline target — are therefore *targets* for Phase 43's reset tool to realize, not states discovered in the data (RESEARCH Pitfall 4).

These three were chosen for structural cleanliness (single-session, near-median signal values) and era spread across the 1955, 1985, and 2010 terms. D-02 imposes no complexity floor on them, so the operator may swap any of them at confirmation time at zero rework cost.

## Regenerating this evidence

```
python3 scripts/select_corpus_fixtures.py --cache-out data/corpus/fixture_scan_cache.json
python3 scripts/select_corpus_fixtures.py --cache data/corpus/fixture_scan_cache.json
```

The cache is derived data and gitignored (`data/corpus/*.json` is excluded); it is never committed. The numbers in this document hold only for the current `data/corpus/` snapshot. If that snapshot is ever replaced with an updated ConvoKit export, re-run both commands above and re-score rather than trusting this table.

## Consumers

- Phase 42 reads the Complexity fixture row only, for its field-by-field diff of raw ConvoKit source against what actually lands in the DB via import-convokit.
- Phase 43 reads all four rows as its reseed target and is responsible for landing each state-variety fixture in its labelled publish/pipeline state after reseeding through the real import-convokit path.
- Phase 45 uses the Published target and unpublished/DRAFT target fixtures for its publish-visibility bug work (unpublished arguments leaking into /cases/ or direct URLs).
