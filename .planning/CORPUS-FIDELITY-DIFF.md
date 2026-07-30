# Corpus Fidelity Diff

Generated: 2026-07-30T17:19:01.507802+00:00 (only this line is expected to differ between two runs against an unchanged database and corpus snapshot).

## Status

- **Fixture:** ConvoKit conversation 15169 -- Baltimore & Ohio Railroad Company v. United States, docket 642, October Term 1966, argued 1967-01-09 (`.planning/FIXTURES.md`'s Complexity fixture row).
- **Generated:** 2026-07-30, from the real dev database (fixture landed by 42-01, round-trip-proven by 42-02) and the real `data/corpus/` snapshot.
- **Review state:** PENDING. Every non-Faithful classification below is a proposal, not a final decision (D-05). The operator reviews this whole document in one batch (D-06) via the Review Gate section below. **No importer fix has been applied as of this document's generation.**

## cases

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

## arguments

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

## utterances

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

## people

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

## argument_participants

| Raw field | Raw value | Destination column | Verdict | Classification | Reason |
|---|---|---|---|---|---|
| speaker registry entry: name/full_name (or speaker_id fallback) | Howard J. Trienens | ArgumentParticipant.raw_speaker_label | Faithful |  |  |
| resolved Person | 1562 | ArgumentParticipant.person_id | Faithful |  |  |
| is_justice (speaker registry type) + advocates[].side (conversation-level) | PETITIONER | ArgumentParticipant.side | Faithful |  | BENCH always wins over the advocate side code when is_justice is True; see court_tenures section for this fixture's one date-inconsistent case. |
| advocates[speaker_id].role (per-advocate, conversation-level) | inferred | (no column) | Dropped | schema-absent field | Only advocates[].side is ever read; the per-advocate role/confidence value (e.g. "inferred") has no ArgumentParticipant column and is never persisted. |
| (none -- no ConvoKit source) | (n/a) | ArgumentParticipant.title | Dropped | upstream-missing data | no ConvoKit source exists for this column -- TOC subtitle from the PDF pipeline's cover extractor only |

## court_tenures

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

## Volume and Roster Exactness

- Raw source turns for this conversation (streamed from the utterance stream via the loader): **479**
- Imported Utterance rows: **480**
- Raw turns that produced at least one Utterance row (via import_convokit._split_turn_into_rows): **479**
- Raw distinct speaker roster (16): <INAUDIBLE>, edward_w_bourne, gordon_p_macdougall, harry_g_silleck_jr, howard_j_trienens, j__byron_r_white, j__earl_warren, j__hugo_l_black, j__potter_stewart, j__thurgood_marshall, j__tom_c_clark, j__william_j_brennan_jr, j__william_o_douglas, leon_keyserling, lloyd_n_cutler, robert_w_ginnane
- Imported ArgumentParticipant roster (17): Byron R. White, Earl Warren, Edward W. Bourne, Gordon P. Macdougall, Harry G. Silleck, Jr., Howard J. Trienens, Hugh B. Cox, Hugo L. Black, Joseph Auerbach, Leon Keyserling, Lloyd N. Cutler, Potter Stewart, Robert W. Ginnane, Thurgood Marshall, Tom C. Clark, William J. Brennan, Jr., William O. Douglas
- Raw source-docket set: ['642']
- Imported Argument.source_docket set: ['642']
- Docket sets match: **True**

## Regenerating this evidence

```
python scripts/diff_corpus_fixture.py --conversation-id 15169 --out .planning/CORPUS-FIDELITY-DIFF.md
```

Re-running this exact command against the same database and the same `data/corpus/` snapshot reproduces every verdict and classification above byte-for-byte (apart from the Generated timestamp line).

## Review status

Every non-Faithful classification in this document is a **proposal**, not a final decision (D-05). The operator reviews the whole document in one batch (D-06) and approves, adjusts, or rejects each proposal before any code fix is applied. **No importer fix has been applied as of this document's generation.**

## Review Gate

The operator reviews every item below in one pass (D-05/D-06) and approves, adjusts, or rejects each proposed classification before any importer fix is written. Items 1-7 were anticipated by `42-RESEARCH.md`; item 8 is a new finding this run's court_tenures integrity check surfaced.

1. **`Utterance.section_hint` is never populated (Pitfall 3).** `_import_utterances` never sets `section_hint` while `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` filters out null-hint utterances to build its section-jump anchors. Verified: 480 of 480 imported Utterance rows for this fixture have `section_hint IS NULL`, so the fixture's rendered transcript page currently has zero section-jump anchors. Proposed classification: **real defect** (the raw `advocates[].side` codes plus turn order carry enough signal to derive petitioner/respondent/rebuttal sections, the same way the PDF pipeline's `parse.py` already does for ordinary arguments).

2. **Speaker id `j__thurgood_marshall` resolves to BENCH nine months before his tenure begins (Pitfall 2).** Verified in the dev DB: person id 99 ("Thurgood Marshall"), exactly one `CourtTenure` row (id 103, `start_date` 1967-10-02, `end_date` 1991-10-01), and this fixture's `argued_date` is 1967-01-09 -- nine months earlier. The speaker registry marks him a Justice globally (his eventual role), so `_is_justice_type` resolves him to BENCH for this argument even though he argued 62 times in this transcript on behalf of the United States (he was Solicitor General at the time). This diff's court_tenures integrity check confirms no `CourtTenure` row covers 1967-01-09 for this Person, and the justices CSV corroborates that (no covering row there either) -- so this is not a `court_tenures` data gap. Three options for the operator:
   a. **General importer fix:** thread `argued_date` into `_resolve_and_link_participant`/`_is_justice_type` and cross-check `CourtTenure` coverage before trusting the speaker registry's `type` field. Reusable protection for any future full-corpus backfill; requires adding a new parameter through the resolution call chain.
   b. **Warn-and-count-only:** flag the mismatch in the per-batch summary counters without changing the resolved side. Lower effort, no side-reassignment risk, but leaves the phantom BENCH participant in place.
   c. **No code change:** classify as upstream-missing/incorrect data (the speaker registry's known limitation) and leave this fixture's Marshall row as BENCH. Zero effort, but the fixture's roster stays wrong for this one argument.

3. **`url`, `adv_sides_inferred`, `known_respondent_adv`, and the per-advocate `role` value are dropped before the allowlist.** None are in `FORBIDDEN_FIELDS`; none reach an ORM column. Proposed: schema-absent/low-urgency for all four -- presented neutrally; `42-RESEARCH.md`'s Assumptions Log A1 flags `url` in particular as a possible citation/reference link an operator might want restored, but this document does not adopt that lean.

4. **ConvoKit's per-turn `id`, `meta.start_times`, `meta.stop_times`, `meta.timestamp`, and `reply_to` are dropped.** No `Utterance` column stores any of them. Proposed: schema-absent, noting the per-segment audio-timing data's potential future value (e.g. a "jump to audio" feature) and that `reply_to`'s threading structure is lost (ordering relies solely on `Utterance.sequence`).

5. **`extract_conversation_fields` returns a `conversation_id` key that is always `None`.** No raw conversation record anywhere carries a top-level `conversation_id` key -- the real id is threaded through as a separate function parameter, not read from this dict key. Nothing consumes the dead key. Proposed: documentation/cleanup note, not a fidelity defect.

6. **`is_eq_divided` is outcome-adjacent but not listed in `FORBIDDEN_FIELDS`.** Nothing currently leaks it (the positive allowlist makes the omission safe), but it is not explicitly documented as excluded either. Proposed: documentation-completeness note on `apolitical.py`.

7. **court_tenures integrity findings are flagged, not fixed (D-03).** See items 2 and 8 -- both are court_tenures-adjacent findings this integrity check surfaced. Neither is fixed by this phase; ownership of any actual `court_tenures` data gap belongs to `pipeline/commands/import_justices_csv.py`. `42-RESEARCH.md` Pitfall 2's warning applies: a Justice whose tenure dates are actually correct (as Marshall's are) indicates upstream speaker misclassification, not a tenure data gap.

8. **NEW FINDING -- Person-dedup mismatch between the two justice-import paths, affecting 4 of this fixture's 6 bench participants.** The court_tenures integrity check found that Byron R. White, Hugo L. Black, Tom C. Clark, and William O. Douglas -- all sitting Justices on 1967-01-09 -- each resolve via this fixture's corpus import to a Person row with **zero** `CourtTenure` rows, while a **separate** Person row already exists for each of them (created by `import_justices_csv.py`, with their full first/middle names spelled out, e.g. "Byron Raymond White") that **does** have a `CourtTenure` row covering the argued date. `_resolve_person`'s dedup keys on an exact `Person.full_name` string match; the speaker registry's abbreviated name (e.g. "Byron R. White") never matches the CSV-imported justice's fuller name (e.g. "Byron Raymond White"), so the corpus importer creates a brand-new, duplicate Person row instead of reusing the existing justice. This is **not** the timing anomaly Pitfall 2 anticipated (Marshall's case) -- it is a distinct, more foundational Person-dedup gap that would recur for any justice whose speaker-registry name and CSV name differ this way. Proposed classification: **real defect candidate** (Person dedup should also try a name-normalization/fuzzy match, or a speaker-registry-to-justice cross-reference, before falling back to creating a new row) -- presented neutrally for the operator's review, since a general fix here also protects any future full-corpus backfill.

## Out of Scope

The fixture's opening turn (`15169__0_000`) names six consolidated dockets read aloud by the Chief Justice: 642, 680, 691, 813, 814, and 815. `data/corpus/cases.jsonl` carries **no case records at all** under term 1966 for dockets 680, 813, 814, or 815, and its only docket-691 record belongs to an unrelated 1967-term case ("Rockefeller v. Wells" -- historical docket numbers recycle across October Terms). This is **upstream-missing data**, not a defect in the importer's lead-docket-only design (D-19, an already-settled Phase 29 decision) -- there is no structured companion-case data in the raw corpus for the importer to have dropped. Full-corpus backfill of any approved fix across the other ~7,800 arguments is explicitly out of scope this milestone (REQUIREMENTS.md "Out of Scope").

## Consumers

- **Plan 04** reads this document's Review Gate section as its operator-review checkpoint agenda and applies whichever fixes the operator approves.
- **Plan 05** re-runs `scripts/diff_corpus_fixture.py` against the post-fix fixture to prove each approved fix landed and that nothing regressed.

