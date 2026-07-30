# Corpus Fidelity Diff

Generated (pre-fix, Plan 03): 2026-07-30T17:19:01.507802+00:00
Generated (post-fix, Plan 05, this run): 2026-07-30T18:44:05.375274+00:00 (only
this line and the pre-fix timestamp are expected to differ between two runs
against an unchanged database and corpus snapshot).

## Status

- **Fixture:** ConvoKit conversation 15169 -- Baltimore & Ohio Railroad Company v. United States, docket 642, October Term 1966, argued 1967-01-09 (`.planning/FIXTURES.md`'s Complexity fixture row).
- **Review state: RESOLVED (2026-07-30).** Plan 04 recorded the operator's D-05/D-06 batch disposition for all 8 Review Gate items and applied the two approved code fixes (item 1 `section-hint-derive`, item 2 `bench-warn-only`). Plan 05 then deleted the fixture, re-imported it through the fixed code path (`scripts/delete_fixture_argument.py` --> `import-convokit --conversation-id 15169`), and re-ran the same comparison (`scripts/diff_corpus_fixture.py`) against the fresh rows -- not assumed. This document now carries both the **Pre-Fix Baseline** (Plan 03's original tables, unchanged) and the **regenerated post-fix tables** below, plus a **Post-Fix Verification** section stating, per approved fix, whether the post-fix verdict is now Faithful.
- The re-import printed `1 arguments created, 0 arguments skipped (already imported), 1 cases created, 467 utterances created, 13 stage-direction utterances created, 0 people created, 17 people matched (reused), 0 speakers flagged, 0 conversations errored, 0 utterance rows errored, 0 docket/question conflicts, 1 unattributed speakers skipped, 5 bench tenure mismatches` -- confirming the fixes were actually exercised (not a silent `skipped_existing` no-op).

## Pre-Fix Baseline (Plan 03's original tables, unchanged, generated 2026-07-30T17:19:01.507802+00:00)

The tables in this section are Plan 03's original output, preserved verbatim (apart
from this subsection's `(pre-fix)` heading suffixes) as the baseline every post-fix
verdict below is compared against. **No importer fix had been applied when these
tables were generated.**

### cases (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| id | 1966_642 | Case.oyez_case_id | Faithful |  |  |
| year | 1966 | Case.term_year | Faithful |  |  |
| citation | 386 US 372 | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| title | Baltimore & Ohio Railroad Company v. United States | Case.case_name (via _case_name_from_fields, preferred over petitioner/respondent) | Faithful |  |  |
| petitioner | Baltimore & Ohio Railroad Company | Case.case_name (fallback only when title is absent; no dedicated column) | Faithful |  |  |
| respondent | United States | Case.case_name (fallback only when title is absent; no dedicated column) | Faithful |  |  |
| docket_no | 642 | Case.docket_number, Case.docket_number_norm | Faithful |  |  |
| court | Warren Court | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| decided_date | Mar 27, 1967 | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| url | https://www.oyez.org/cases/1966/642 | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| transcripts | [{'name': 'Oral Argument - January 09, 1967', 'url': 'https://apps.oyez.org/player/#/warren13/oral_argument_audio/15169', 'id': 15169, 'case_id': '1966_642'}... | (not persisted verbatim -- consumed transiently by Argument.argued_date via _parse_argued_date) | Faithful |  |  |
| adv_sides_inferred | True | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| known_respondent_adv | False | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| advocates | {'Howard J. Trienens': {'id': 'howard_j_trienens', 'name': 'Howard J. Trienens', 'side': 1}, 'Lloyd N. Cutler': {'id': 'lloyd_n_cutler', 'name': 'Lloyd N. Cu... | (not persisted verbatim -- consumed transiently by the advocate-resolution loop) | Faithful |  |  |
| win_side | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| win_side_detail | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| scdb_docket_id | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| votes | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| votes_detail | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| is_eq_divided | False | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| votes_side | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |

### arguments (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| case_id (conversation-level) | 1966_642 | (used for Case join only -- see cases section; no Argument column) | Faithful |  |  |
| conversation_id (dict key inside the raw conversation record) | (null) | (none -- dead key, nothing consumes it) | Dropped | PROPOSED -- awaiting operator review -- documentation/cleanup note, not a fidelity defect | No raw conversation record carries a top-level 'conversation_id' key; extract_conversation_fields()['conversation_id'] always evaluates to None. |
| conversation id (the dict key / CLI parameter, e.g. "15169") | 15169 | Argument.oyez_transcript_id | Faithful |  |  |
| docket_no (case-level, re-used for the Argument row) | 642 | Argument.source_docket | Faithful |  |  |
| transcripts[].name (matched by transcript id) | ['Oral Argument - January 09, 1967', 'Oral Argument - January 10, 1967'] | Argument.argued_date (via import_convokit._parse_argued_date) | Faithful |  | import_convokit._parse_argued_date(case_fields, '15169') -> 1967-01-09; DB Argument.argued_date = 1967-01-09. |
| advocates{speaker_id: {side, role}} (conversation-level) | 9 advocate entries | (consumed by the advocate-resolution loop; side -> ArgumentParticipant.side, see argument_participants section) | Faithful |  |  |
| votes_side (conversation-level) | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| win_side (conversation-level) | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| (none -- no ConvoKit source) | (n/a) | Argument.question_number | Dropped | upstream-missing data | no ConvoKit source exists for this column -- derived via _next_question_number's DB (source_docket) counter, not sourced from raw corpus data |
| (none -- no ConvoKit source) | (n/a) | Argument.status | Dropped | upstream-missing data | no ConvoKit source exists for this column -- hardcoded to PIPELINE for every corpus import (Phase 30), not derived from raw corpus data |
| (none -- no ConvoKit source) | (n/a) | Argument.resolved_at | Dropped | upstream-missing data | no ConvoKit source exists for this column -- left NULL by import-convokit; set only by the Resolve pipeline step |
| (none -- no ConvoKit source) | (n/a) | Argument.published_at | Dropped | upstream-missing data | no ConvoKit source exists for this column -- left NULL by import-convokit; set only by the publish action |
| (none -- no ConvoKit source) | (n/a) | Argument.source_dockets | Dropped | upstream-missing data | no ConvoKit source exists for this column -- consolidated-docket array; PDF pipeline only (D-19 lead-docket-only design) |
| (none -- no ConvoKit source) | (n/a) | Argument.cover_metadata | Dropped | upstream-missing data | no ConvoKit source exists for this column -- PDF cover-extractor output only |

### utterances (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| id (ConvoKit turn id, e.g. "15169__0_000") | 15169__0_000 | (no column) | Dropped | schema-absent field | No Utterance column stores ConvoKit's own per-turn id. |
| conversation_id | 15169 | (used to group turns into this argument's turns; not persisted per-row) | Faithful |  |  |
| text | Number 642, Baltimore and Ohio Railroad Company et al., Appellants, versus United States et al. <NL> Number 680, the Delaware and Hudson Railroad Corporation... | Utterance.text (split on \n per stage-direction detection) | Faithful |  |  |
| meta.start_times | [0.0, 8.907, 15.639, 23.562, 29.388, 35.139, 44.542, 78.993] | (no column) | Dropped | schema-absent field | Per-segment audio timing is not stored anywhere. |
| meta.stop_times | [8.907, 15.639, 23.562, 29.388, 35.139, 44.542, 78.993, 81.226] | (no column) | Dropped | schema-absent field | Per-segment audio timing is not stored anywhere. |
| meta.speaker_type | J | (no column -- not read at all) | Dropped | PROPOSED -- awaiting operator review -- robustness gap, not a currently-observed defect on this fixture | _import_utterances never reads this per-turn field; side is derived from the conversation-level advocates dict instead. |
| meta.side | (null) | (no column -- not read at all) | Dropped | PROPOSED -- awaiting operator review -- robustness gap, not a currently-observed defect on this fixture | _import_utterances never reads this per-turn field; side is derived from the conversation-level advocates dict instead -- the two sources happen to agree on ... |
| meta.timestamp | 0.0 | (no column) | Dropped | schema-absent field | No Utterance column stores this per-turn timestamp. |
| reply_to | (null) | (no column) | Dropped | schema-absent field | No Utterance column stores ConvoKit's reply-threading pointer; ordering relies solely on Utterance.sequence, a fresh monotonic counter. |
| speaker | j__earl_warren | Utterance.person_id, raw_speaker_label, side (via _resolve_and_link_participant) | Faithful |  |  |
| (none -- derivable from advocates[].side + turn order, but not read) | (n/a) | Utterance.section_hint | Silently defaulted | PROPOSED -- awaiting operator review -- real defect candidate | _import_utterances never sets section_hint; 480 of 480 imported Utterance rows have a null section_hint. The frontend's transcript page filters out null-hint... |

### people (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| speaker registry entry: name/full_name (or speaker_id fallback) | Howard J. Trienens | Person.full_name | Faithful |  |  |
| speaker registry entry key (speaker id, e.g. "j__thurgood_marshall") | howard_j_trienens | Person.oyez_speaker_id | Faithful |  |  |
| speaker registry entry type (via _is_justice_type) | False | Person.is_justice | Faithful |  | Authoritative per the speaker registry; see court_tenures section for any date-inconsistent bench classification this fixture surfaces. |
| full_name, split via split_legacy_full_name | ('Howard', 'J.', 'Trienens', None) | Person.first_name, middle_name, last_name, name_suffix | Faithful |  | Derived from full_name, not a direct raw field, but sourced faithfully from it. |
| full_name (provenance bookkeeping only) | (derived envelope, not a 1:1 raw field) | Person.name_needs_review, Person.name_extraction_metadata | Faithful |  | Provenance/audit bookkeeping written by _apply_extracted_name_provenance. |
| (none -- no ConvoKit source) | (n/a) | Person.role_id | Dropped | upstream-missing data | no ConvoKit source exists for this column |
| (none -- no ConvoKit source) | (n/a) | Person.bio_text | Dropped | upstream-missing data | no ConvoKit source exists for this column |
| (none -- no ConvoKit source) | (n/a) | Person.photo_url | Dropped | upstream-missing data | no ConvoKit source exists for this column |
| (none -- no ConvoKit source) | (n/a) | Person.birthdate | Dropped | upstream-missing data | no ConvoKit source exists for this column -- only import_justices_csv.py populates this for a Person the corpus importer creates fresh |
| (none -- no ConvoKit source) | (n/a) | Person.death_date | Dropped | upstream-missing data | no ConvoKit source exists for this column -- only import_justices_csv.py populates this for a Person the corpus importer creates fresh |

### argument_participants (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| speaker registry entry: name/full_name (or speaker_id fallback) | Howard J. Trienens | ArgumentParticipant.raw_speaker_label | Faithful |  |  |
| resolved Person | 1562 | ArgumentParticipant.person_id | Faithful |  |  |
| is_justice (speaker registry type) + advocates[].side (conversation-level) | PETITIONER | ArgumentParticipant.side | Faithful |  | BENCH always wins over the advocate side code when is_justice is True; see court_tenures section for this fixture's one date-inconsistent case. |
| advocates[speaker_id].role (per-advocate, conversation-level) | inferred | (no column) | Dropped | schema-absent field | Only advocates[].side is ever read; the per-advocate role/confidence value (e.g. "inferred") has no ArgumentParticipant column and is never persisted. |
| (none -- no ConvoKit source) | (n/a) | ArgumentParticipant.title | Dropped | upstream-missing data | no ConvoKit source exists for this column -- TOC subtitle from the PDF pipeline's cover extractor only |

### court_tenures (pre-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| Earl Warren (BENCH participant, person_id=14) | argued_date=1967-01-09 | CourtTenure id=14 start_date=1953-10-05 end_date=1969-06-23 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Potter Stewart (BENCH participant, person_id=95) | argued_date=1967-01-09 | CourtTenure id=99 start_date=1958-10-14 end_date=1981-07-03 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Byron R. White (BENCH participant, person_id=1570) | argued_date=1967-01-09 | CourtTenure (none on person_id=1570; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=96 ('Byron Raymond White') shares this participant's last_name and has CourtTenure id=100 (start_date=1962-04-16, end_date=1993-06-28) covering the... |
| William J. Brennan, Jr. (BENCH participant, person_id=93) | argued_date=1967-01-09 | CourtTenure id=97 start_date=1956-10-16 end_date=1990-07-20 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Hugo L. Black (BENCH participant, person_id=127) | argued_date=1967-01-09 | CourtTenure (none on person_id=127; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=81 ('Hugo Lafayette Black') shares this participant's last_name and has CourtTenure id=85 (start_date=1937-08-19, end_date=1971-09-17) covering the... |
| Tom C. Clark (BENCH participant, person_id=129) | argued_date=1967-01-09 | CourtTenure (none on person_id=129; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=90 ('Tom Campbell Clark') shares this participant's last_name and has CourtTenure id=94 (start_date=1949-08-24, end_date=1967-06-12) covering the a... |
| Thurgood Marshall (BENCH participant, person_id=99) | argued_date=1967-01-09 | CourtTenure (none covering) | Mis-mapped | PROPOSED -- awaiting operator review -- bench-classification anomaly to investigate | No CourtTenure row covers the argued date, the justices CSV corroborates that (no covering tenure there either), and no differently-named duplicate Person ro... |
| William O. Douglas (BENCH participant, person_id=119) | argued_date=1967-01-09 | CourtTenure (none on person_id=119; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=84 ('William Orville Douglas') shares this participant's last_name and has CourtTenure id=88 (start_date=1939-04-17, end_date=1975-11-12) covering ... |

### Volume and Roster Exactness (pre-fix)

- Raw source turns for this conversation (streamed from the utterance stream via the loader): **479**
- Imported Utterance rows: **480**
- Raw turns that produced at least one Utterance row (via import_convokit._split_turn_into_rows): **479**
- Raw distinct speaker roster (16): <INAUDIBLE>, edward_w_bourne, gordon_p_macdougall, harry_g_silleck_jr, howard_j_trienens, j__byron_r_white, j__earl_warren, j__hugo_l_black, j__potter_stewart, j__thurgood_marshall, j__tom_c_clark, j__william_j_brennan_jr, j__william_o_douglas, leon_keyserling, lloyd_n_cutler, robert_w_ginnane
- Imported ArgumentParticipant roster (17): Byron R. White, Earl Warren, Edward W. Bourne, Gordon P. Macdougall, Harry G. Silleck, Jr., Howard J. Trienens, Hugh B. Cox, Hugo L. Black, Joseph Auerbach, Leon Keyserling, Lloyd N. Cutler, Potter Stewart, Robert W. Ginnane, Thurgood Marshall, Tom C. Clark, William J. Brennan, Jr., William O. Douglas
- Raw source-docket set: ['642']
- Imported Argument.source_docket set: ['642']
- Docket sets match: **True**

## Post-Fix Tables (current, regenerated 2026-07-30T18:44:05.375274+00:00, after Plan 05's delete-and-reimport cycle)

The tables in this section were produced by re-running
`scripts/diff_corpus_fixture.py --conversation-id 15169` against the **fresh,
re-imported** rows (Argument id 1864, delete-then-reimport round trip: old
Argument id 1861 -> deleted -> new Argument id 1864), after Plan 04's approved
fixes landed in `pipeline/commands/import_convokit.py`.

### cases (post-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| id | 1966_642 | Case.oyez_case_id | Faithful |  |  |
| year | 1966 | Case.term_year | Faithful |  |  |
| citation | 386 US 372 | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| title | Baltimore & Ohio Railroad Company v. United States | Case.case_name (via _case_name_from_fields, preferred over petitioner/respondent) | Faithful |  |  |
| petitioner | Baltimore & Ohio Railroad Company | Case.case_name (fallback only when title is absent; no dedicated column) | Faithful |  |  |
| respondent | United States | Case.case_name (fallback only when title is absent; no dedicated column) | Faithful |  |  |
| docket_no | 642 | Case.docket_number, Case.docket_number_norm | Faithful |  |  |
| court | Warren Court | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| decided_date | Mar 27, 1967 | (no Case column exists) | Dropped | schema-absent field | No Case column exists for this allowlisted field. |
| url | https://www.oyez.org/cases/1966/642 | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| transcripts | [{'name': 'Oral Argument - January 09, 1967', 'url': 'https://apps.oyez.org/player/#/warren13/oral_argument_audio/15169', 'id': 15169, 'case_id': '1966_642'}... | (not persisted verbatim -- consumed transiently by Argument.argued_date via _parse_argued_date) | Faithful |  |  |
| adv_sides_inferred | True | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| known_respondent_adv | False | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| advocates | {'Howard J. Trienens': {'id': 'howard_j_trienens', 'name': 'Howard J. Trienens', 'side': 1}, 'Lloyd N. Cutler': {'id': 'lloyd_n_cutler', 'name': 'Lloyd N. Cu... | (not persisted verbatim -- consumed transiently by the advocate-resolution loop) | Faithful |  |  |
| win_side | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| win_side_detail | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| scdb_docket_id | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| votes | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| votes_detail | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| is_eq_divided | False | (no column) | Dropped | PROPOSED -- awaiting operator review -- dropped before the allowlist (not in FORBIDDEN_FIELDS, not read by the extractor); see the Review Gate section for th... | Present in the raw source but never reaches an ORM column via any code path. |
| votes_side | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |

**Post-fix comparison:** identical to the pre-fix `cases` table -- no field in this table was in scope for either approved fix (item 1 and item 2 both target `utterances`/`argument_participants`, not `cases`).

### arguments (post-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| case_id (conversation-level) | 1966_642 | (used for Case join only -- see cases section; no Argument column) | Faithful |  |  |
| conversation_id (dict key inside the raw conversation record) | (null) | (none -- dead key, nothing consumes it) | Dropped | PROPOSED -- awaiting operator review -- documentation/cleanup note, not a fidelity defect | No raw conversation record carries a top-level 'conversation_id' key; extract_conversation_fields()['conversation_id'] always evaluates to None. |
| conversation id (the dict key / CLI parameter, e.g. "15169") | 15169 | Argument.oyez_transcript_id | Faithful |  |  |
| docket_no (case-level, re-used for the Argument row) | 642 | Argument.source_docket | Faithful |  |  |
| transcripts[].name (matched by transcript id) | ['Oral Argument - January 09, 1967', 'Oral Argument - January 10, 1967'] | Argument.argued_date (via import_convokit._parse_argued_date) | Faithful |  | import_convokit._parse_argued_date(case_fields, '15169') -> 1967-01-09; DB Argument.argued_date = 1967-01-09. |
| advocates{speaker_id: {side, role}} (conversation-level) | 9 advocate entries | (consumed by the advocate-resolution loop; side -> ArgumentParticipant.side, see argument_participants section) | Faithful |  |  |
| votes_side (conversation-level) | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| win_side (conversation-level) | [REDACTED -- apolitical hard constraint / not extracted] | (no column -- never extracted) | Dropped | apolitical allow-list exclusion | Present in apolitical.FORBIDDEN_FIELDS; value never extracted or persisted. |
| (none -- no ConvoKit source) | (n/a) | Argument.question_number | Dropped | upstream-missing data | no ConvoKit source exists for this column -- derived via _next_question_number's DB (source_docket) counter, not sourced from raw corpus data |
| (none -- no ConvoKit source) | (n/a) | Argument.status | Dropped | upstream-missing data | no ConvoKit source exists for this column -- hardcoded to PIPELINE for every corpus import (Phase 30), not derived from raw corpus data |
| (none -- no ConvoKit source) | (n/a) | Argument.resolved_at | Dropped | upstream-missing data | no ConvoKit source exists for this column -- left NULL by import-convokit; set only by the Resolve pipeline step |
| (none -- no ConvoKit source) | (n/a) | Argument.published_at | Dropped | upstream-missing data | no ConvoKit source exists for this column -- left NULL by import-convokit; set only by the publish action |
| (none -- no ConvoKit source) | (n/a) | Argument.source_dockets | Dropped | upstream-missing data | no ConvoKit source exists for this column -- consolidated-docket array; PDF pipeline only (D-19 lead-docket-only design) |
| (none -- no ConvoKit source) | (n/a) | Argument.cover_metadata | Dropped | upstream-missing data | no ConvoKit source exists for this column -- PDF cover-extractor output only |

**Post-fix comparison:** identical to the pre-fix `arguments` table -- `Argument.argued_date` remains Faithful (1967-01-09 both raw-parsed and DB-stored); this table was never in scope for either approved fix.

### utterances (post-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| id (ConvoKit turn id, e.g. "15169__0_000") | 15169__0_000 | (no column) | Dropped | schema-absent field | No Utterance column stores ConvoKit's own per-turn id. |
| conversation_id | 15169 | (used to group turns into this argument's turns; not persisted per-row) | Faithful |  |  |
| text | Number 642, Baltimore and Ohio Railroad Company et al., Appellants, versus United States et al. <NL> Number 680, the Delaware and Hudson Railroad Corporation... | Utterance.text (split on \n per stage-direction detection) | Faithful |  |  |
| meta.start_times | [0.0, 8.907, 15.639, 23.562, 29.388, 35.139, 44.542, 78.993] | (no column) | Dropped | schema-absent field | Per-segment audio timing is not stored anywhere. |
| meta.stop_times | [8.907, 15.639, 23.562, 29.388, 35.139, 44.542, 78.993, 81.226] | (no column) | Dropped | schema-absent field | Per-segment audio timing is not stored anywhere. |
| meta.speaker_type | J | (no column -- not read at all) | Dropped | PROPOSED -- awaiting operator review -- robustness gap, not a currently-observed defect on this fixture | _import_utterances never reads this per-turn field; side is derived from the conversation-level advocates dict instead. |
| meta.side | (null) | (no column -- not read at all) | Dropped | PROPOSED -- awaiting operator review -- robustness gap, not a currently-observed defect on this fixture | _import_utterances never reads this per-turn field; side is derived from the conversation-level advocates dict instead -- the two sources happen to agree on ... |
| meta.timestamp | 0.0 | (no column) | Dropped | schema-absent field | No Utterance column stores this per-turn timestamp. |
| reply_to | (null) | (no column) | Dropped | schema-absent field | No Utterance column stores ConvoKit's reply-threading pointer; ordering relies solely on Utterance.sequence, a fresh monotonic counter. |
| speaker | j__earl_warren | Utterance.person_id, raw_speaker_label, side (via _resolve_and_link_participant) | Faithful |  |  |
| (none -- derivable from advocates[].side + turn order, but not read) | (n/a) | Utterance.section_hint | Silently defaulted | PROPOSED -- awaiting operator review -- real defect candidate | _import_utterances never sets section_hint; **479 of 480** imported Utterance rows have a null section_hint. The frontend's transcript page filters out null-hint... |

**Post-fix comparison:** the `section_hint` row's *observed number* changed from
`480 of 480 null` (pre-fix) to `479 of 480 null` (post-fix) -- i.e. exactly **1**
row (sequence 2, speaker Howard J. Trienens, hint `"petitioner"`) now carries a
non-null `section_hint`. This script's own generic classification text is
unchanged (it never decides "real defect" vs. "Faithful" -- D-05), but see
**Post-Fix Verification** below for why this fixture legitimately produces only
one non-null section hint rather than three (petitioner/respondent/rebuttal),
and what that means for the Task 3 checkpoint.

### people (post-fix)

Identical to the pre-fix `people` table (sample row unchanged: Howard J.
Trienens). No field in this table was in scope for either approved fix.

### argument_participants (post-fix)

Identical to the pre-fix `argument_participants` table (sample row unchanged).
`ArgumentParticipant.side` semantics were explicitly NOT changed by item 2's
`bench-warn-only` disposition -- see Post-Fix Verification below for the
per-participant `side` values this cycle actually produced.

### court_tenures (post-fix)

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| Earl Warren (BENCH participant, person_id=14) | argued_date=1967-01-09 | CourtTenure id=14 start_date=1953-10-05 end_date=1969-06-23 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Potter Stewart (BENCH participant, person_id=95) | argued_date=1967-01-09 | CourtTenure id=99 start_date=1958-10-14 end_date=1981-07-03 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Byron R. White (BENCH participant, person_id=1570) | argued_date=1967-01-09 | CourtTenure (none on person_id=1570; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=96 ('Byron Raymond White') shares this participant's last_name and has CourtTenure id=100 (start_date=1962-04-16, end_date=1993-06-28) covering the... |
| William J. Brennan, Jr. (BENCH participant, person_id=93) | argued_date=1967-01-09 | CourtTenure id=97 start_date=1956-10-16 end_date=1990-07-20 | Faithful |  | A CourtTenure row covers the argued date (inclusive start boundary) -- integrity check passed. |
| Hugo L. Black (BENCH participant, person_id=127) | argued_date=1967-01-09 | CourtTenure (none on person_id=127; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=81 ('Hugo Lafayette Black') shares this participant's last_name and has CourtTenure id=85 (start_date=1937-08-19, end_date=1971-09-17) covering the... |
| Tom C. Clark (BENCH participant, person_id=129) | argued_date=1967-01-09 | CourtTenure (none on person_id=129; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=90 ('Tom Campbell Clark') shares this participant's last_name and has CourtTenure id=94 (start_date=1949-08-24, end_date=1967-06-12) covering the a... |
| Thurgood Marshall (BENCH participant, person_id=99) | argued_date=1967-01-09 | CourtTenure (none covering) | Mis-mapped | PROPOSED -- awaiting operator review -- bench-classification anomaly to investigate | No CourtTenure row covers the argued date, the justices CSV corroborates that (no covering tenure there either), and no differently-named duplicate Person ro... |
| William O. Douglas (BENCH participant, person_id=119) | argued_date=1967-01-09 | CourtTenure (none on person_id=119; a covering tenure exists on a DIFFERENT Person row) | Mis-mapped | PROPOSED -- awaiting operator review -- likely Person-dedup mismatch (distinct from RESEARCH.md Pitfall 2's timing anomaly) | Person id=84 ('William Orville Douglas') shares this participant's last_name and has CourtTenure id=88 (start_date=1939-04-17, end_date=1975-11-12) covering ... |

**Post-fix comparison:** byte-for-byte identical to the pre-fix `court_tenures`
table -- expected and correct, since item 2's `bench-warn-only` disposition
explicitly does not reassign `side` and does not write to `CourtTenure` or
`Person.is_justice` (verified by the plan 04 grep acceptance gate). All five
Mis-mapped rows remain Mis-mapped by design; see Post-Fix Verification below.

### Volume and Roster Exactness (post-fix)

- Raw source turns for this conversation (streamed from the utterance stream via the loader): **479**
- Imported Utterance rows: **480**
- Raw turns that produced at least one Utterance row (via import_convokit._split_turn_into_rows): **479**
- Raw distinct speaker roster (16): <INAUDIBLE>, edward_w_bourne, gordon_p_macdougall, harry_g_silleck_jr, howard_j_trienens, j__byron_r_white, j__earl_warren, j__hugo_l_black, j__potter_stewart, j__thurgood_marshall, j__tom_c_clark, j__william_j_brennan_jr, j__william_o_douglas, leon_keyserling, lloyd_n_cutler, robert_w_ginnane
- Imported ArgumentParticipant roster (17): Byron R. White, Earl Warren, Edward W. Bourne, Gordon P. Macdougall, Harry G. Silleck, Jr., Howard J. Trienens, Hugh B. Cox, Hugo L. Black, Joseph Auerbach, Leon Keyserling, Lloyd N. Cutler, Potter Stewart, Robert W. Ginnane, Thurgood Marshall, Tom C. Clark, William J. Brennan, Jr., William O. Douglas
- Raw source-docket set: ['642']
- Imported Argument.source_docket set: ['642']
- Docket sets match: **True**

**Post-fix comparison:** identical to the pre-fix Volume and Roster Exactness
section, field for field. All 479 raw turns still produce at least one
Utterance row on the fresh import; the roster and docket set are unchanged.

## Post-Fix Verification

Per-item comparison of the pre-fix and post-fix verdicts, tied to each Review
Gate item's recorded disposition. Numbers below are recorded exactly as
observed against the fresh, re-imported rows (Argument id 1864) -- none were
adjusted, rounded, or explained away.

| Item | Field | Disposition | Pre-Fix Verdict | Post-Fix Verdict | Result |
|---|---|---|---|---|---|
| 1 | `Utterance.section_hint` | Approved real defect, `section-hint-derive` | Silently defaulted -- 480/480 rows null | Silently defaulted -- 479/480 rows null, **1/480 non-null** (`"petitioner"` at sequence 2) | **Faithful for the transitions this fixture's raw data actually contains** -- see note below; the fix reached its consumer (confirmed via the live page, Task 3) |
| 2 | Bench/advocate classification (`j__thurgood_marshall` et al.) | Approved real defect, `bench-warn-only` | `ArgumentParticipant.side`=BENCH for Marshall; no visibility mechanism | `ArgumentParticipant.side`=BENCH for Marshall, **unchanged** (confirmed by direct query below); new `bench_tenure_mismatch` counter = **5** printed during re-import, naming Byron R. White, Hugo L. Black, Tom C. Clark, Thurgood Marshall, William O. Douglas | **Matches the approved disposition exactly** -- visibility added, `side` never reassigned |
| 3 | `url`/`adv_sides_inferred`/`known_respondent_adv`/per-advocate `role` dropped before allowlist | Approved as proposed, no code change | Dropped, schema-absent/low-urgency | Dropped, schema-absent/low-urgency (unchanged) | **Unchanged as decided** -- intentional exclusion still non-Faithful |
| 4 | ConvoKit per-turn `id`/`meta.start_times`/`meta.stop_times`/`meta.timestamp`/`reply_to` dropped | Approved as proposed, no code change | Dropped, schema-absent | Dropped, schema-absent (unchanged) | **Unchanged as decided** -- intentional exclusion still non-Faithful |
| 5 | Dead `conversation_id` key in `extract_conversation_fields` | Approved as proposed, no code change | Dropped, documentation/cleanup note | Dropped, documentation/cleanup note (unchanged) | **Unchanged as decided** |
| 6 | `is_eq_divided` outcome-adjacent, not in `FORBIDDEN_FIELDS` | Approved as proposed, documentation-completeness note added | Dropped, no code change yet | Dropped; `pipeline/corpus/apolitical.py` module docstring now documents the outcome-adjacent-but-safe rationale (confirmed: `is_eq_divided` was NOT added to `FORBIDDEN_FIELDS`; neither extractor's returned keys changed) | **Documentation fix confirmed landed; no persistence-behavior change, as decided** |
| 7 | court_tenures integrity findings flagged, not fixed (D-03) | Approved as proposed, flag-only, ownership named as `import_justices_csv.py` | 5 Mis-mapped court_tenures rows (items 2 + 8 combined) | 5 Mis-mapped court_tenures rows, **byte-for-byte identical** to pre-fix (verified: no `CourtTenure` insert/update/delete, no `Person.is_justice` write) | **Unchanged as decided** -- flagged only, not fixed |
| 8 | Person-dedup mismatch (White/Black/Clark/Douglas duplicate Person rows) | Approved as real-defect candidate, flagged only, fix deferred to a later phase | 4 Mis-mapped court_tenures rows, each naming the duplicate Person row | 4 Mis-mapped court_tenures rows, **unchanged** -- same duplicate Person ids (96, 81, 90, 84) named as the covering-tenure holders; re-import matched (not recreated) the same duplicate corpus-side Person rows (1570, 127, 129, 119) | **Unchanged as decided** -- still deferred, not fixed |

### Note on item 1's single non-null section hint (important context for Task 3)

The re-imported fixture's raw `advocates` dict (`conversations.json`) has only
two advocates with a defined side code: Howard J. Trienens and Robert W.
Ginnane, both `side=1` -> `PETITIONER`. Every other named advocate
(Cutler, Bourne, Silleck, Keyserling, Macdougall, Cox, Auerbach) carries
`side=3` -> `SideEnum.UNKNOWN` (ConvoKit's own "unknown side" code, not an
importer defect -- `_ADVOCATE_SIDE_MAP` is a pre-existing, unmodified mapping).
**No advocate in the raw `advocates` dict carries `side=0` (RESPONDENT) for
this conversation at all.** The government's real respondent-side advocate at
this argument was Thurgood Marshall, then Solicitor General -- but
`speakers.json` types him `justice`, so `_is_justice_type` resolves him to
BENCH (item 2), and BENCH speakers never open or carry a `section_hint` by
design (non-cascading section semantics, Plan 04). Because the operator's
approved disposition for item 2 was `bench-warn-only` (not `bench-general`),
Marshall's `side` is not reassigned, so the only side transition this fixture's
resolved participants ever produce is the single PETITIONER-side turn at
sequence 2. **This means the fixture's transcript page will show exactly one
section-jump link ("Petitioner"), not three** -- this is the correct,
foreseeable consequence of the approved `bench-warn-only` disposition on this
specific fixture, not a new defect and not something this plan may fix (Rule 4
architectural changes and any un-approved fix are both out of scope here). Task
3's checkpoint below is worded to account for this.

### Ordering stability (CORPUS-14 ordering edge item)

Before the delete, the fixture's full `Utterance.sequence` -> text-prefix
mapping (480 rows) was captured to a scratch file outside the repository
(`%TEMP%\pre_delete_sequence_map_15169.txt`, Windows temp dir, not committed).
After the re-import, the same mapping was recaptured for the new Argument row
(`%TEMP%\post_reimport_sequence_map_15169.txt`) and compared via
`Compare-Object`: **0 differences across all 480 rows.** Every sequence number
from 1 to 480 maps to the identical text prefix before and after the
delete-and-reimport cycle -- `Utterance.sequence` is stable across the round
trip, as CORPUS-14 requires.

### Database counts confirming the cycle (recorded exactly as observed)

| Metric | Plan 01/02 recorded baseline | Post-Plan-05 cycle (observed) | Match |
|---|---|---|---|
| Fixture Argument id | 1860 -> 1861 (delete/reimport chain) | **1864** (new row; delete of 1861 -> reimport) | n/a -- new PK expected |
| `arguments` (total) | 166 | **166** | Match |
| `people` (total) | 343 | **343** | Match |
| `court_tenures` (total) | 123 | **123** | Match |
| `cases` where `term_year = 1966` | 1 | **1** | Match |
| Utterance rows for the fixture | 480 | **480** | Match |
| Utterance rows errored | 0 | **0** | Match |
| Post-delete `arguments` count for `oyez_transcript_id='15169'` | 0 (asserted before reimport) | **0** (confirmed) | Match |
| Re-import summary line | n/a (first appearance of this exact fix set) | `1 arguments created, 0 arguments skipped (already imported), 1 cases created, 467 utterances created, 13 stage-direction utterances created, 0 people created, 17 people matched (reused), 0 speakers flagged, 0 conversations errored, 0 utterance rows errored, 0 docket/question conflicts, 1 unattributed speakers skipped, 5 bench tenure mismatches` | Exercised the fix (not a `skipped_existing` no-op) |

## Regression Checks

Plan 05 Task 2 -- exactness cross-check against `.planning/FIXTURES.md`, no-backfill
confirmation, and full suite health. All numbers recorded exactly as observed against
the post-fix fixture (Argument id 1864) and the real dev database; none were adjusted.

### Exactness (ROADMAP success criterion 4)

| Check | Value | Source |
|---|---|---|
| Raw source turns for conversation 15169 | **479** | Volume and Roster Exactness (post-fix), streamed via `pipeline.corpus.loader` |
| Raw turns represented by at least one Utterance row | **479** (100%) | Volume and Roster Exactness (post-fix), via `import_convokit._split_turn_into_rows` |
| Errored utterance rows | **0** | Re-import summary line: `0 utterance rows errored` |
| Imported Utterance row count | **480** (467 spoken + 13 stage-direction rows -- one raw turn split into 2 rows by stage-direction detection, hence 480 rows from 479 turns) | Direct query: `select count(*) from utterances where argument_id = 1864` |
| Imported `Argument.source_docket` set | **{'642'}**, exactly the lead docket | Volume and Roster Exactness (post-fix): "Docket sets match: **True**" |

**Imported participant roster, with the unattributed sentinel and the two silent-advocate exceptions named explicitly:**

- Raw distinct speaker roster (turns' `speaker` field), 16 entries: `<INAUDIBLE>`, `edward_w_bourne`, `gordon_p_macdougall`, `harry_g_silleck_jr`, `howard_j_trienens`, `j__byron_r_white`, `j__earl_warren`, `j__hugo_l_black`, `j__potter_stewart`, `j__thurgood_marshall`, `j__tom_c_clark`, `j__william_j_brennan_jr`, `j__william_o_douglas`, `leon_keyserling`, `lloyd_n_cutler`, `robert_w_ginnane`.
- **Excluded sentinel:** `<INAUDIBLE>` -- `data/corpus/speakers.json` types it `"U"`, matching `_is_unattributed_speaker_type`'s `_UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}` (verified directly against the raw speakers file). This is ConvoKit's own "no identifiable speaker" placeholder and correctly never produces a Person/ArgumentParticipant row (D-12 gap-closure). Removing it leaves **15** real raw distinct speakers.
- The imported `ArgumentParticipant` roster has **17** rows, not 15 -- the two extra rows are **Hugh B. Cox** and **Joseph Auerbach**, both present in `conversations.json`'s conversation-level `advocates` dict (side code 3 -> `UNKNOWN`) as attorneys of record for this argument, but **neither ever speaks a turn** in this transcript's raw `utterances.jsonl` (they do not appear in the 16-entry raw speaker roster above). `_import_conversation`'s advocate-resolution loop iterates the `advocates` dict directly and creates an `ArgumentParticipant` row for every listed advocate regardless of whether that advocate personally spoke -- correct, intentional behavior (counsel of record who did not personally argue is a normal real-world occurrence), not an importer defect. So the precise relationship is: **imported roster (17) = raw distinct speakers minus the unattributed sentinel (15) + 2 listed-but-silent advocates (Cox, Auerbach)**, not a strict equality with the raw speaker roster alone. This is unchanged from the pre-fix document (same 17 names, same two silent advocates) -- neither approved fix touches advocate resolution.

**Cross-check against `.planning/FIXTURES.md`'s independently-derived row for conversation 15169** (line 19: 9 advocates, 15 distinct speakers, 8 bench speakers, 479 turns, 2 transcripts):

| Metric | FIXTURES.md (independent, full-corpus scan) | This diff (post-fix) | Divergence |
|---|---|---|---|
| Advocates | 9 | 9 (raw `advocates` dict entry count) | **None** |
| Distinct speakers | 15 | 15 (16 raw speakers minus the 1 unattributed sentinel) | **None** |
| Bench speakers | 8 | 8 (Earl Warren, Potter Stewart, Byron R. White, William J. Brennan Jr., Hugo L. Black, Tom C. Clark, Thurgood Marshall, William O. Douglas -- all BENCH-side `ArgumentParticipant` rows) | **None** |
| Turns | 479 | 479 (raw source turns, Volume and Roster Exactness) | **None** |
| Transcripts | 2 | 2 (`case_fields["transcripts"]` entry count, both consumed by `_parse_argued_date`) | **None** |

**No divergence found** -- all five independently-derived figures agree exactly.

### No backfill (ROADMAP success criterion 5)

| Query | Result |
|---|---|
| `select count(*) from cases where term_year = 1966` | **1** |
| `select count(*) from arguments` (total) | **166** (matches Plan 01's recorded post-import baseline) |
| `select count(*) from pipeline_runs where strategy = 'convokit_import'` | **164** total; **163** belong to arguments other than the fixture, and every one of those 163 rows has `created_at.date() = 2026-07-10` -- all pre-existing from before this phase started (2026-07-29/30), none created during Plan 05. Only the fixture's own row (`argument_id = 1864`) was created today. |
| Post-delete `select count(*) from arguments where oyez_transcript_id = '15169'` | **0** (confirmed immediately after the delete, before re-import) |

No conversation other than 15169 was imported, and no full-term or full-corpus backfill ran during this plan.

### Suite health

- `./.venv/Scripts/python.exe -m pytest -q` (full suite, matching this task's own verify command): **823 passed, 5 xfailed, 4 errors** in 63.91s.
- The 4 errors are all in `api/tests/test_phase38_people_ui_contract.py` (`test_personnames_ts_*`) -- the same pre-existing WSL/Windows Node.js path-mangling bug (`ENOENT` on `C:\workspace\scotuschat\project\workspacescotuschatprojectapi\tests\fixtures...`, a concatenated-not-joined path) first logged in `.planning/phases/42-corpus-import-fidelity-diff-fix/deferred-items.md` during Plan 02's Task 2 sanity check, and observed again during Plan 04's Task 3. `git status --porcelain pipeline api app scripts` (run immediately before this check) confirms this task modified none of those directories, so these errors predate and are unrelated to Plan 05's changes. **Not fixed here** -- out of scope per the scope-boundary rule (pre-existing, unrelated-file failures), consistent with how Plans 02 and 04 handled the identical failure.
- Run in isolation, `api/tests -q` alone additionally shows 5 failures in `api/tests/test_speakers_service.py` (`roles.name` UniqueViolation on `"Associate Justice"`) that do **not** reproduce when the full suite runs together (`pytest -q` from the repo root) -- consistent with the order-dependent test-pollution root-cause hypothesis Plan 04 already recorded in `deferred-items.md` (a stray `Role` row surviving `api/tests/conftest.py::db_session`'s rollback depending on execution order). This task's own required gate is the full-suite `pytest -q` invocation, which does not exhibit this failure mode.
- `pipeline/tests/ -q` alone: **226 passed, 5 xfailed** -- fully green, no code in this task's scope.
- The suite's synthetic-fixture design (small, hand-built corpus trees in `pipeline/tests/`) cannot prove the 479-turn exactness claim against the real 15169 fixture -- that is exactly why the direct database queries and the `.planning/FIXTURES.md` cross-check above exist as this plan's actual proof.

### No code changed by this task

`git status --porcelain pipeline api app scripts` was run before and after this task's checks; both show no modifications from this task (only `.planning/CORPUS-FIDELITY-DIFF.md` changed, via this document edit).

## Disposition (D-05/D-06 operator review, recorded 2026-07-30)

The operator reviewed all 8 numbered Review Gate items in one batch before any importer
code was touched. Recorded verbatim below.

1. **`Utterance.section_hint` never populated.** **Approved as real defect.** Option chosen:
   `section-hint-derive`. Implemented in `_import_utterances` (Plan 04 Task 2) with
   non-cascading petitioner/respondent/rebuttal/amicus semantics matching `parse.py`'s
   precedent.

2. **`j__thurgood_marshall` resolves to BENCH nine months before his tenure begins.**
   **Approved as real defect, option `bench-warn-only`.** The operator's own words: "This
   won't be common but this is a perfect situation to address. Ideally, someone who has been
   on both sides of the bench should resolve to the same person but for now, I'm okay with
   them being two separate entries. Defer resolving them into the same person until a later
   phase." Applied to item 2: the operator does not want `side` reassigned for this
   per-appearance mismatch -- that felt adjacent to the person-identity/classification-merging
   work they explicitly want deferred. Scope is strictly visibility: a tenure-coverage check, a
   new `bench_tenure_mismatch` summary counter, and a warning naming the speaker id and both
   dates. `ArgumentParticipant.side` for Marshall's row remains BENCH -- no behavior change.
   (An earlier round of operator feedback described item 8's duplicate-Person mechanism while
   discussing this item; once the two findings were distinguished, `bench-warn-only` was
   confirmed for item 2 specifically.)

3. **`url`/`adv_sides_inferred`/`known_respondent_adv`/per-advocate `role` dropped before the
   allowlist.** **Approved as proposed** -- schema-absent/low-urgency documentation exclusion
   for all four. No code change.

4. **ConvoKit's per-turn `id`/`meta.start_times`/`meta.stop_times`/`meta.timestamp`/`reply_to`
   dropped.** **Approved as proposed** -- schema-absent documentation exclusion. No code
   change.

5. **`extract_conversation_fields`'s dead `conversation_id` key.** **Approved as proposed** --
   documentation/cleanup note, not a fidelity defect. No code change.

6. **`is_eq_divided` outcome-adjacent but not in `FORBIDDEN_FIELDS`.** **Approved as
   proposed** -- documentation-completeness note added to `apolitical.py`'s module docstring
   (Plan 04 Task 3). `is_eq_divided` is NOT added to `FORBIDDEN_FIELDS`; neither extractor's
   returned keys changed.

7. **court_tenures integrity findings flagged, not fixed (D-03).** **Approved as proposed** --
   flag-only policy confirmed, ownership named as `import_justices_csv.py`. No code change
   (governs items 2 and 8 both).

8. **NEW FINDING -- Person-dedup mismatch (White/Black/Clark/Douglas duplicate Person
   rows).** **Approved as a real-defect candidate; flagged only, fix deferred to a later
   phase.** This is a deliberate scope decision, not a downgrade of the finding's severity: a
   proper fix (name-normalization/fuzzy match, or a speaker-registry-to-justice
   cross-reference, before creating a new Person row) touches every justice in the corpus and
   deserves its own research/plan cycle rather than an improvised mid-checkpoint fix. No code
   change in this plan. The operator's guidance quoted under item 2 applies here directly:
   they are okay with the duplicate Person rows existing as two separate entries for now, and
   want the merge deferred to a later phase.

## Fixes Applied (Plan 04, Tasks 2/3)

Every approved code change made in response to the Disposition section above, tied to the
Review Gate item number it closes.

- **Item 1 (`section_hint`, option `section-hint-derive`).** `pipeline/commands/import_convokit.py::_import_utterances`
  now derives `section_hint` for every spoken `Utterance` row: two locals
  (`current_section_side`, `respondent_section_started`) are tracked across the whole
  conversation's turns. A `PETITIONER`/`RESPONDENT`/`AMICUS`-side row whose resolved side
  differs from the side that opened the current section starts a new one (`"petitioner"`,
  `"respondent"`, or `"amicus"`), except that a petitioner side returning after a respondent
  section already opened yields `"rebuttal"` instead of a second `"petitioner"`. BENCH/UNKNOWN
  rows and rows with no attributable speaker never carry a hint and never change the section.
  The stage-direction `Utterance(...)` constructor now passes `section_hint=None` explicitly.
  Test coverage: `pipeline/tests/test_import_convokit_utterances.py` (6 new tests, including
  a zero-turns case and an exact-count assertion for a full
  petitioner/respondent/bench/rebuttal/amicus sequence).

- **Item 2 (bench-versus-advocate classification, option `bench-warn-only`).**
  `pipeline/commands/import_convokit.py::_resolve_and_link_participant` gained an `argued_date`
  keyword parameter (default `None`), threaded from `_import_conversation`'s local
  `argued_date` at both call sites (the advocates loop, and `_import_utterances`'s own
  resolution call, which needed `argued_date` threaded through its own signature too). When
  the resolved speaker is typed a Justice and `argued_date` is not null, a new read-only helper
  `_check_bench_tenure_mismatch` runs one `select(CourtTenure)` (inclusive start boundary,
  open-ended `end_date` treated as active) to check coverage. A mismatch increments the new
  `bench_tenure_mismatch` counter (added to `_SUMMARY_COUNTER_KEYS` and to `_print_summary`'s
  printed line) and prints a warning naming the speaker id, `argued_date`, and the earliest
  `CourtTenure.start_date` on record for that person. Per the operator's warn-only choice,
  `side` is NEVER reassigned -- Marshall's `ArgumentParticipant` row for this fixture remains
  BENCH, unchanged from before this plan. No `Person.is_justice` write and no `CourtTenure`
  write were added (verified by the plan's own grep acceptance criteria). Test coverage:
  `pipeline/tests/test_import_convokit_bench_tenure.py` (4 new tests: the exact-start-date
  inclusive-boundary case, the one-day-later mismatch case with warning/counter assertions, a
  no-write-to-CourtTenure/is_justice assertion, and the null-`argued_date` fallback case).

- **Item 3, 4, 5, 7 (schema-absent / dead-key / flag-only documentation items).** No code
  change -- approved as proposed, recorded in the Disposition section above.

- **Item 6 (`is_eq_divided` documentation-completeness).** `pipeline/corpus/apolitical.py`'s
  module docstring gained a paragraph documenting that outcome-adjacent fields not listed in
  `FORBIDDEN_FIELDS` (e.g. `is_eq_divided`) are still safe because both extractors are
  positive allow-lists. `is_eq_divided` was NOT added to `FORBIDDEN_FIELDS`; neither
  extractor's returned keys changed.

- **Item 8 (Person-dedup mismatch).** No code change -- flagged only, fix deferred to a later
  phase per the operator's explicit scope decision recorded in the Disposition section above.

## Out of Scope

The fixture's opening turn (`15169__0_000`) names six consolidated dockets read aloud by the Chief Justice: 642, 680, 691, 813, 814, and 815. `data/corpus/cases.jsonl` carries **no case records at all** under term 1966 for dockets 680, 813, 814, or 815, and its only docket-691 record belongs to an unrelated 1967-term case ("Rockefeller v. Wells" -- historical docket numbers recycle across October Terms). This is **upstream-missing data**, not a defect in the importer's lead-docket-only design (D-19, an already-settled Phase 29 decision) -- there is no structured companion-case data in the raw corpus for the importer to have dropped. Full-corpus backfill of any approved fix across the other ~7,800 arguments is explicitly out of scope this milestone (REQUIREMENTS.md "Out of Scope").

This remains true after Plan 05's re-import: the same six dockets are named in the opening
turn, and the same absence of companion-case data in `cases.jsonl` persists -- confirmed by
the unchanged raw source-docket set (`['642']`) in both the pre-fix and post-fix Volume and
Roster Exactness sections above.

## Consumers

- **Plan 04** read this document's Review Gate section as its operator-review checkpoint agenda and applied whichever fixes the operator approved.
- **Plan 05** re-ran `scripts/diff_corpus_fixture.py` against the post-fix fixture (this document) to prove each approved fix landed and that nothing regressed -- see Post-Fix Verification and Regression Checks above.
