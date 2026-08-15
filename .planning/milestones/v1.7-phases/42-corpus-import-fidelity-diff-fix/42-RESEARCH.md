# Phase 42: Corpus Import Fidelity Diff & Fix - Research

**Researched:** 2026-07-30
**Domain:** Offline data-import fidelity auditing (Python/SQLAlchemy pipeline code, ConvoKit JSON/JSONL corpus source, PostgreSQL ORM)
**Confidence:** HIGH (every field list and code path below was read directly from the repo's own source and the actual `data/corpus/` files for conversation 15169 / case 1966_642, not from training-data recall)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Conversation 15169 (1966 term) has never been imported. Build a new, scoped single-conversation import path (e.g. a conversation-id-targeted option on the importer) so only conversation 15169 lands in the database — not the accept-the-side-effect alternative of running the full `--term 1966` (135 conversations) and relying on Phase 43's later wipe to clean up.
- **D-02:** `import-convokit` never writes to `court_tenures`. For this table the diff verifies that the fixture's Justices already have correct, complete tenure data from the separate `import_justices_csv.py` tool — an integrity check, not a diff against ConvoKit source (ConvoKit has no tenure-equivalent data).
- **D-03:** A gap found in the judges'-history data is flagged in the findings but NOT fixed in this phase — that belongs to whatever tool normally maintains `court_tenures`.
- **D-04:** The field-by-field comparison and its classifications are written to a saved, durable document (same pattern as `.planning/FIXTURES.md`), not console/log output.
- **D-05:** Every real-defect-vs-intentional-exclusion classification requires the operator's explicit review and approval before any code fix is applied. Claude does not self-approve a classification and start fixing.
- **D-06:** Review happens as one batch — the full comparison document is finished first (every gap found and classified), then the operator reviews the whole thing at once — not a stop-and-confirm loop per gap.

### Claude's Discretion

Not explicitly separated into its own CONTEXT.md subsection this phase, but the following are implicitly left to planner/executor judgment within the locked decisions above:
- Exact CLI flag name/shape for the new scoped single-conversation import option (D-01 only fixes the requirement, not the interface).
- Exact form of the delete-then-reimport mechanism needed to re-run the fixture cleanly after a fix (see Pitfall 1 below — this is NOT solved by any existing admin code path).
- Where the diff-generation script itself lives (`scripts/` is the established precedent per Phase 41's `scripts/select_corpus_fixtures.py`).

### Deferred Ideas (OUT OF SCOPE)

- Full-corpus backfill of any fix across the other ~7,800 arguments — explicitly out of scope this milestone (REQUIREMENTS.md "Out of Scope").
- Fixing any `court_tenures` gap found (D-03) — belongs to a different tool/process.
- The two reviewed-but-not-folded todos (unpublished-argument-visible-in-cases-list, popover-scrollbar) — both already assigned to Phase 45.
- Renaming "Case" to "Argument" across schema/routes/frontend — out of scope, candidate for a future milestone.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORPUS-13 | A field-by-field comparison exists between the fixture's raw ConvoKit source and what lands in the DB (cases, arguments, utterances, people, argument_participants, court_tenures) after `import-convokit`, surfacing dropped/mis-mapped/silently-defaulted fields | The "Field Inventory" tables below (Standard Stack → Architecture Patterns section) give the exact raw field lists for conversation 15169 / case 1966_642 cross-referenced against the exact allow-list extractors and ORM columns — this is the raw material the diff document is built from |
| CORPUS-14 | Every gap found for the fixture is fixed in the importer and verified by re-importing the fixture cleanly (fixes apply to this one fixture's import path; full-corpus backfill out of scope) | Pitfall 1 (delete-then-reimport lifecycle), Pitfall 2 (Marshall bench misclassification), Pitfall 3 (`section_hint` never set) give concrete, verified fix candidates; "Fixture Delete-and-Reimport Lifecycle" section gives the exact mechanism the re-import step needs since the existing admin delete path cannot be reused |

</phase_requirements>

## Summary

Conversation 15169 (Baltimore & Ohio Railroad Co. v. United States, docket 642, 1966 term, argued 1967-01-09) has never been imported. Its raw ConvoKit records were read directly from `data/corpus/` for this research: the case record (`cases.jsonl`, keyed `"1966_642"`), the conversation record (`conversations.json`, keyed `"15169"`), the 9-entry advocate roster embedded in both, the 16 distinct raw speaker ids appearing across its 479 utterance rows (`utterances.jsonl`), and the corresponding `speakers.json` entries for each. Every one of those fields was cross-referenced against `pipeline/corpus/apolitical.py`'s two allow-list extractors and against the exact ORM column lists in `api/models/models.py` for `Case`, `Argument`, `Utterance`, `Person`, `ArgumentParticipant`, and `CourtTenure`.

Three concrete, verified findings stand out as the highest-value material for planning the fix work (all three are documented in detail below, with exact evidence): (1) the pre-identified `decided_date`/`citation`/`court` schema-absent gap from CONTEXT.md is confirmed exactly as described — `Case` has no columns for any of the three; (2) this specific fixture actually triggers a real, non-hypothetical bench-misclassification bug — a raw ConvoKit speaker id `j__thurgood_marshall` appears 62 times in this transcript arguing on behalf of the United States (he was Solicitor General at the time), but `speakers.json`'s authoritative `type`/`role` fields mark him globally as a Justice, so the importer's existing `_is_justice_type` logic will resolve him as BENCH and create a phantom Justice-side `ArgumentParticipant` row for an argument nine months before his actual Court tenure began (verified against `data/corpus/supreme_court_justices_sections.csv`: oath taken 1967-10-02); and (3) the `Utterance.section_hint` column — which the frontend's transcript page actually consumes to render Petitioner/Respondent/Rebuttal section-jump anchors — is never populated anywhere in `import_convokit.py`, even though the raw data (advocate `side` codes plus turn order) contains enough signal to derive it the way the PDF pipeline's `parse.py` already does for ordinary arguments.

A fourth structural fact changes how the "re-import the fixture cleanly" verification step (Success Criterion 3) must be built: `_import_conversation`'s own dedup logic silently **skips** re-import when an `Argument.oyez_transcript_id` row already exists (D-08 idempotency), and the only existing delete path — `api/services/admin_arguments.py::delete_argument` — is hard-gated to `status == DRAFT` only, while every corpus-imported argument starts at `status == PIPELINE` (Phase 30's rule) and is never DRAFT. **Neither existing code path can delete-and-reimport this fixture as-is** — the plan must design its own delete mechanism for this one fixture. This is unrelated to the previously-known `argument_status_log` FK-cascade bug (see Pitfall 1 for why that bug specifically does not apply here).

**Primary recommendation:** Build the diff as a standalone script under `scripts/` (Phase 41 precedent) that (a) reads the raw fixture records straight from `data/corpus/*` with stdlib `json` (no DB needed for this half — confirmed runnable from WSL with zero extra dependencies), (b) reads the imported DB rows via the existing async SQLAlchemy session helpers, and (c) walks every raw field against the two apolitical allow-lists and the six ORM models' column lists, emitting one row per field with a faithful/dropped/mis-mapped/defaulted verdict and a classification. Do the DB-touching halves (reading imported rows, deleting the fixture, re-importing) either from the Windows-side terminal (which already has a fully provisioned `.venv` and portable Postgres) or via an ephemeral `pgserver`-backed Postgres from WSL — see Environment Availability below; the current WSL system Python has neither `pip` nor any project dependency installed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Raw ConvoKit field enumeration (reading `data/corpus/*`) | Pipeline / offline tooling (`scripts/`) | — | Pure stdlib JSON parsing, no DB, no app-tier involvement — same as Phase 41's `select_corpus_fixtures.py` |
| Field-by-field diff generation + classification document | Pipeline / offline tooling (`scripts/`) | Database (read-only query of imported rows) | Diff needs both raw JSON and the imported ORM rows; still fully offline/operator-run per CLAUDE.md's "pipeline is offline only" rule |
| Importer code fixes (allow-list, speaker resolution, `section_hint`) | Pipeline (`pipeline/commands/import_convokit.py`, `pipeline/corpus/apolitical.py`) | Database (schema is fixed via Alembic if a new column is ever needed — not expected this phase) | All identified fixes are Python logic changes inside the existing importer; no ORM/schema change is currently indicated (the schema-absent fields are classified, not restored, per the apolitical hard constraint reasoning already settled for `decided_date`/`citation`/`court`) |
| Scoped single-conversation import CLI option (D-01) | Pipeline (`pipeline/commands/import_convokit.py` CLI arg handling) | — | New `--conversation-id`-style option hooking into `_resolve_terms`/`run_import_convokit`'s existing per-conversation loop |
| `court_tenures` integrity check (D-02) | Pipeline / offline tooling (read-only query against `CourtTenure`) | — | Explicitly NOT a diff against ConvoKit source (no ConvoKit tenure-equivalent data exists) — it is a DB-side lookup cross-referenced against the CSV in `data/corpus/supreme_court_justices_sections.csv` |
| Delete-and-reimport mechanism for the fixture | Pipeline / offline tooling (new script or CLI option, NOT the existing admin API) | Database | `api/services/admin_arguments.py::delete_argument` cannot be reused — see Pitfall 1 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.x (repo runs 3.12 per CLAUDE.md; WSL system python is 3.14) | Parse `data/corpus/*.jsonl`/`*.json` for the raw side of the diff | Already the exclusive parsing mechanism in `pipeline/corpus/loader.py` — no reason to introduce a new JSON library |
| SQLAlchemy 2.0 async | Already pinned in `requirements.txt` (project stack per CLAUDE.md) | Query imported rows for the DB side of the diff; execute the delete/reimport cycle | Same ORM the importer itself uses (`api/models/models.py`) — reusing it keeps the diff script's DB-row shape identical to what the importer actually wrote |
| `pipeline.db.get_session` | Existing project helper | Async session context manager, already used by `import_convokit.py` and every pipeline command | Don't hand-roll a second session factory |
| `pipeline.corpus.loader` (`load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids`) | Existing project module | Load the raw corpus files for the diff's raw side | D-01/D-04's canonical-refs and CONTEXT.md's Reusable Assets note both require reuse here rather than re-parsing JSON by hand |
| `pipeline.corpus.apolitical` (`extract_case_fields`, `extract_conversation_fields`, `FORBIDDEN_FIELDS`) | Existing project module | Canonical allow-list translation layer — the diff's classification of "intentional exclusion" for any case/conversation field is defined by whether that field appears in these two functions' return dicts | This module IS the ground truth for "apolitical allow-list" classification, not something to reimplement |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pgserver` (PyPI) | Not currently in `requirements.txt`/`requirements-dev.txt` — ad hoc per prior sessions (see WSL/Windows note in Environment Availability) | Ephemeral, Unix-socket-only local Postgres, usable from WSL where the real dev Postgres is unreachable | Only if executing the DB-touching parts of this phase from a WSL Claude Code session rather than the Windows terminal |
| `python-dateutil` | Already pinned (used by `import_convokit.py`'s `_parse_argued_date` and `scripts/select_corpus_fixtures.py`) | Fuzzy-parse the fixture's `transcripts[].name` date string if the diff needs to independently re-derive `argued_date` | Only if the diff script needs its own date derivation outside calling the importer's own `_parse_argued_date` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `pipeline.corpus.loader`'s streaming reader for `utterances.jsonl` | A one-off `grep`/`awk` pass over the 900MB file | `grep -c '"conversation_id": "15169"'` (used during this research to get an instant 479-row count) is fine for a quick sanity check, but the actual diff script must use the real loader so its notion of "turn" exactly matches what the importer consumed — do not have two independent parsers of the same file |
| Deleting the fixture via `api/services/admin_arguments.py::delete_argument` | A new, purpose-built delete routine (script or CLI flag) mirroring its documented FK-ordered cascade | `delete_argument` is hard-gated to `status == DRAFT`; a corpus-imported argument is always `status == PIPELINE` and never reaches DRAFT through any normal flow — see Pitfall 1 |

**Installation:** No new packages are required for the importer-code-fix half of this phase (all fixes are pure Python logic changes to existing modules — `pipeline/commands/import_convokit.py`, `pipeline/corpus/apolitical.py`). If the diff/re-import work is executed from WSL rather than the Windows terminal, `pgserver` needs an ad hoc `pip install pgserver` inside a working WSL Python environment — see Environment Availability, since the current WSL system Python has neither `pip` nor any project dependency installed at all.

**Version verification:** Not applicable — no new package versions are being introduced by this phase's expected fixes. If a planner later decides a new package IS needed (unlikely given the findings), verify it via `pip index versions <pkg>` before adding it to `requirements.txt`, per the Package Legitimacy Gate.

## Package Legitimacy Audit

No new external packages are indicated by this phase's research. All identified fixes are logic changes inside existing, already-vetted project modules (`pipeline/commands/import_convokit.py`, `pipeline/corpus/apolitical.py`). The only package that MIGHT be newly installed is `pgserver`, and only as a WSL-local dev-environment workaround (not a project dependency added to `requirements.txt`) — it is not part of the shipped fix and does not need a legitimacy audit gate, but the planner should still confirm it via `pip index versions pgserver` before an executor runs `pip install pgserver` in any session, since it is currently absent from both requirements files.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### Field Inventory: raw ConvoKit source → allow-list → ORM (conversation 15169 / case 1966_642)

This is the actual field-by-field material CORPUS-13's diff document needs, verified directly against the fixture's own raw records (not a generic/other-fixture example).

**Raw `cases.jsonl` row (`id == "1966_642"`) — every field present:**

```
id, year, citation, title, petitioner, respondent, docket_no, court,
decided_date, url, transcripts, adv_sides_inferred, known_respondent_adv,
advocates, win_side, win_side_detail, scdb_docket_id, votes, votes_detail,
is_eq_divided, votes_side
```

`extract_case_fields()` (in `pipeline/corpus/apolitical.py`) allow-lists exactly: `title, petitioner, respondent, docket_no, decided_date, citation, court, year, transcripts, advocates, case_id` (the last sourced from raw `"id"`, not raw `"case_id"` — real rows have no top-level `"case_id"` key; it only appears nested per-transcript).

| Raw field | In allow-list? | Reaches a `Case`/`Argument` ORM column? | Classification |
|---|---|---|---|
| `id` → `case_id` | yes | No `Case.oyez_case_id`-equivalent read directly — `_get_or_create_case` DOES use `case_fields.get("case_id")` → `Case.oyez_case_id` | Faithful |
| `year` | yes | `Case.term_year` | Faithful |
| `docket_no` | yes | `Case.docket_number` (+ `docket_number_norm`) | Faithful |
| `title`/`petitioner`/`respondent` | yes | `Case.case_name` (derived via `_case_name_from_fields`) | Faithful (title preferred; petitioner/respondent are a fallback only, never stored as their own columns — `Case` has no separate petitioner/respondent columns) |
| `transcripts` | yes | Not stored as a column — consumed only transiently by `_parse_argued_date` to derive `Argument.argued_date` | Faithful (used, not persisted verbatim — expected, no column exists for it) |
| `advocates` | yes | Not stored as a column — consumed only transiently by the advocate-resolution loop | Faithful (used, not persisted — expected) |
| `decided_date` | yes (extracted) | **No `Case` column exists** | **Confirmed schema-absent field** — matches CONTEXT.md's pre-identified gap exactly. `Case` has only: `id, docket_number, docket_number_norm, case_name, term_year, slug, oyez_case_id` |
| `citation` | yes (extracted) | **No `Case` column exists** | **Confirmed schema-absent field** — same as above |
| `court` | yes (extracted) | **No `Case` column exists** | **Confirmed schema-absent field** — same as above |
| `url` | **not in allow-list** | No column | Dropped before it ever reaches the extractor — not in `FORBIDDEN_FIELDS` either. Not politically sensitive (an Oyez case-page URL). Candidate for classification as "real defect" (silently dropped, could be a useful external-link field) OR "schema-absent field" depending on operator judgment — flag for D-05 review, do not pre-decide |
| `adv_sides_inferred` (bool) | not in allow-list | No column | Dropped. Signals whether the `advocates[].side` codes were inferred vs. confirmed for this case — `true` for this fixture. Candidate: schema-absent / low-value, flag for review |
| `known_respondent_adv` (bool) | not in allow-list | No column | Dropped. `false` for this fixture. Same category as above |
| `is_eq_divided` (bool) | not in allow-list, **also not in `FORBIDDEN_FIELDS`** | No column | Dropped (correctly, since positive-allowlist architecture means omission = safe), but this is an outcome-adjacent field (relates to the Court's vote) that is not explicitly documented in `FORBIDDEN_FIELDS`. Worth flagging as a documentation-completeness improvement for `apolitical.py` even though nothing is currently leaking it |
| `win_side`, `win_side_detail`, `scdb_docket_id`, `votes`, `votes_detail`, `votes_side` | **explicitly in `FORBIDDEN_FIELDS`** | No column | Intentional exclusion (apolitical hard constraint) — do not classify as a defect, do not "restore" |

**Raw `conversations.json` entry (key `"15169"`) — every field present across the ENTIRE 7,817-conversation file (verified by unioning keys across all records, not just this one):**

```
case_id, advocates, win_side, votes_side
```

This fixture's own record: `{"case_id": "1966_642", "advocates": {...9 entries...}, "win_side": 1, "votes_side": {...9 justices...}}`.

`extract_conversation_fields()` allow-lists: `conversation_id, case_id, advocates`.

| Raw field | Verified fact | Classification |
|---|---|---|
| `conversation_id` | **No raw conversation record anywhere in the 7,817-record file has a `"conversation_id"` key** — it is always only the dict's own key (e.g. `"15169"`), passed separately as a Python parameter by the caller. `extract_conversation_fields(raw_conversation).get("conversation_id")` therefore **always evaluates to `None`** for every real record, and the resulting `conversation["conversation_id"]` value is never read anywhere downstream (the real conversation id is threaded through as its own function argument, not via this dict key) | Dead/unused key in the allow-list output — harmless (nothing consumes it), but worth a one-line cleanup note; not a data-fidelity defect since no information is actually lost |
| `case_id` | Faithful — used for the case-record join (`raw_case = cases_by_case_id.get(conversation["case_id"])`) | Faithful |
| `advocates` (dict of 9 entries, each `{"side": int, "role": "inferred"}`) | The full sub-dict is allow-listed through, but only `advocate_meta.get("side")` is ever read by `_import_conversation`; the per-advocate `"role"` value (e.g. `"inferred"`) is never read or persisted anywhere — `ArgumentParticipant` has no confidence/role-provenance column | Schema-absent field (per-advocate `role`) — flag for review, low urgency (advisory-only metadata) |
| `win_side`, `votes_side` | In `FORBIDDEN_FIELDS`; correctly never extracted | Intentional exclusion |

**Raw `speakers.json` entries — every key present across all 9,651 speakers:** `name, type, role`. `type` values seen: `A` (9,535 advocates), `J` (114 justices/justice-type speakers), `U` (2 unattributed/`<INAUDIBLE>`-class sentinels). `role` values seen: `justice` (114), `unknown` (1), `inaudible` (1), and `None` (9,535 — advocates carry no `role` key at all). `_is_justice_type`'s `_JUSTICE_TYPE_VALUES = {"justice", "j", "bench"}` correctly matches `"J".lower() == "j"`; `_is_unattributed_speaker_type`'s `_UNATTRIBUTED_TYPE_VALUES = {"u", "unattributed", "unknown"}` correctly matches `"U".lower() == "u"`. Both checks work as intended for this fixture's vocabulary — **the type-classification logic itself is not the defect; see Pitfall 2 for the actual, verified problem this fixture surfaces.**

**Raw `utterances.jsonl` rows for `conversation_id == "15169"` — 479 rows confirmed (`grep -c '"conversation_id": "15169"'`), every field present on a sample row:**

```
id, conversation_id, text, meta: {case_id, start_times, stop_times, speaker_type, side, timestamp}, reply_to, speaker
```

`_import_utterances` reads only `turn.get("conversation_id")`, `turn["text"]`, `turn.get("speaker")`. It never reads: the turn's own `id` (ConvoKit's stable per-turn identifier, e.g. `"15169__0_000"`), `meta` (`start_times`/`stop_times` — per-segment audio timing arrays; `speaker_type`/`side` — a per-turn, not per-conversation, speaker classification; `timestamp`), or `reply_to` (the turn's reply-threading pointer).

| Raw field | Reaches an `Utterance` column? | Classification |
|---|---|---|
| `text` | `Utterance.text` (split on `\n` per D-18/D-16 stage-direction logic) | Faithful |
| `speaker` | Resolved to `Utterance.person_id`/`raw_speaker_label`/`side` via `_resolve_and_link_participant` | Faithful (subject to Pitfall 2's classification question) |
| `id` (e.g. `"15169__0_001"`) | **No `Utterance` column stores ConvoKit's own turn id** | Schema-absent field — no way to trace an `Utterance` row back to its exact source turn id without recomputing sequence order. Flag for review; could matter for future re-import diffing/audit trails |
| `meta.start_times`/`meta.stop_times` (per-segment audio timing, seconds) | **No `Utterance` column stores timing** | Schema-absent field — real audio-alignment data is silently dropped. Flag for review — this is potentially valuable data (e.g. a future "jump to audio" feature) being dropped, not politically sensitive |
| `meta.speaker_type`/`meta.side` (per-turn side, distinct from the conversation-level `advocates[].side`) | Not read at all — the importer derives side from the conversation-level `advocates` dict lookup instead | For this fixture the two sources agree (verified: `howard_j_trienens` has conversation-level `side: 1` and turn-level `meta.side: 1`), so no observed discrepancy — but the importer has no mechanism to detect or flag it if they ever disagreed. Flag as a robustness gap, not a currently-observed defect on this fixture |
| `reply_to` (turn-to-turn reply chain) | **No `Utterance` column stores it** | Schema-absent field — the DB's only ordering signal is `sequence` (a fresh monotonic counter), which does preserve transcript order faithfully for this fixture (verified: file order for conversation 15169 matches the `_0_000`, `_0_001`, `_0_002`… turn-id ordering), but the actual reply-graph structure itself is lost |

## Fixture Delete-and-Reimport Lifecycle (directive #8 — resolved)

**This directly answers CONTEXT.md's open question and the task's directive #8: corpus import is effectively insert-only (idempotent-skip on re-run), and the existing admin delete path cannot be used to clear the fixture for a clean re-import.**

Verified facts:
1. `_import_conversation` does an "Idempotent Argument dedup on `oyez_transcript_id`" check FIRST: if `Argument.oyez_transcript_id == conversation_id` already exists, it increments `counters["skipped_existing"]` and **returns without writing or updating anything**. Re-running `import-convokit` (scoped or not) after the fix is applied will silently no-op on this fixture unless its existing rows are deleted first.
2. Every corpus-imported argument is created with `status=ArgumentStatusEnum.PIPELINE` (Phase 30's rule, enforced directly in `_import_conversation`) and is paired with a `PAUSED`/`RESOLVE` `AdminJob`. It never starts at, or is moved to, `DRAFT` by the corpus import path itself.
3. `api/services/admin_arguments.py::delete_argument` returns `False` (refuses to delete) for any argument whose `status != ArgumentStatusEnum.DRAFT` — this is checked BEFORE any cascade-delete logic runs. **A freshly corpus-imported, never-resolved argument can never be deleted through this service.**
4. Because `delete_argument` never reaches its cascade-delete body for a PIPELINE-status argument, the previously-known STATE.md blocker ("`delete_argument` omits `argument_status_log` from its FK cascade") **does not apply to this fixture** as long as it is deleted before ever being routed through the Resolve/publish/approve flows that write `ArgumentStatusLog` rows (`api/services/admin_jobs.py`'s `approve_job` and `admin_arguments.py`'s publish/unpublish paths are the only three `ArgumentStatusLog` writers in the codebase — none of them run as part of a bare corpus import). Do not assume this immunity holds if the plan's verification flow ever runs the fixture through Resolve/approve/publish between import attempts.

**What the plan needs to build instead:** a small, purpose-built delete routine (script or CLI flag, not reusing `delete_argument`) that replicates `delete_argument`'s own documented FK-ordered cascade, but without its `status == DRAFT` gate:
1. `Utterance` rows where `argument_id == <this argument>` (must precede `PipelineRun` deletion — `Utterance.pipeline_run_id` FK)
2. `PipelineRun` rows where `argument_id == <this argument>`
3. `ArgumentParticipant` rows where `argument_id == <this argument>`
4. `CaseArgument` rows where `argument_id == <this argument>`
5. `AdminJob.argument_id` set NULL for any `AdminJob` referencing this argument (FK is nullable, no `ondelete`)
6. `ArgumentStatusLog` rows where `argument_id == <this argument>` — defensive; should be zero rows for a never-resolved corpus import, but delete them anyway since this new routine has no status gate protecting it the way `delete_argument` does
7. `Argument` row itself
8. Decide explicitly whether to also delete the `Case` row (docket 642, term 1966) and its `CaseArgument` link, or leave it in place for `_get_or_create_case` to reuse on re-import — either is safe (idempotent lookup by `oyez_case_id` then `(docket_number, term_year)`), but leaving it in place means the re-import never re-exercises the Case-CREATE branch, only the Case-REUSE branch. Recommend deleting it too, so the verification re-import exercises the full code path, not a subset.
9. Advocate `Person` rows created by the first import attempt (7 of them, matched by `full_name`) do NOT need deletion between attempts — re-import matches them idempotently by `full_name`/`oyez_speaker_id`. Deleting them would just force a re-create with identical values; either is technically safe, but skipping their deletion is fewer moving parts.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading `cases.jsonl`/`conversations.json`/`speakers.json`/`utterances.jsonl` | A second ad hoc JSON parser inside the diff script | `pipeline.corpus.loader`'s `load_cases`, `load_conversations_for_term`, `load_speakers`, `stream_utterances_for_conversation_ids` | These already handle the 900MB-streaming constraint, the term-prefix filtering, and the exact same field access the importer itself uses — a second parser risks silently drifting from what the importer actually consumes |
| Deciding which case/conversation fields are "safe" to show in the diff | A fresh blocklist or manual field list in the diff script | `pipeline.corpus.apolitical.extract_case_fields`/`extract_conversation_fields`/`FORBIDDEN_FIELDS` | This module is explicitly documented as "the ONLY sanctioned translation layer" — re-deriving the same list elsewhere creates two sources of truth that can drift apart, which is exactly the apolitical hard constraint's failure mode |
| Deleting the fixture's Argument row for re-import | Reusing or patching `api/services/admin_arguments.py::delete_argument` | A new, narrowly-scoped delete routine (see Fixture Delete-and-Reimport Lifecycle above) | `delete_argument` is intentionally status-gated for the admin UI's DRAFT-only delete affordance; weakening that gate to accommodate this one dev/audit use case would reopen a production safety hole for an unrelated reason |
| Deriving `Argument.argued_date` a second way inside the diff script | A second date-parsing routine | Call the importer's own `_parse_argued_date` (or document any deliberate divergence) | `.planning/FIXTURES.md` already flags this exact risk: "A later reader comparing these dates against the importer's own `_parse_argued_date` output should confirm which parser produced both sides before treating a mismatch as a bug" |

**Key insight:** every reusable helper this phase needs already exists in the codebase (`loader.py`, `apolitical.py`, `_parse_argued_date`, `_next_question_number`) — the risk in this phase is NOT missing infrastructure, it's building a second, slightly-different parallel implementation of logic that already exists and then treating any resulting discrepancy as a "finding" when it's actually just parser drift.

## Common Pitfalls

### Pitfall 1: Corpus import is idempotent-skip, not idempotent-upsert — re-import after a fix silently no-ops unless the fixture's old rows are deleted first

**What goes wrong:** After fixing an importer defect and re-running `import-convokit` (or the new scoped single-conversation option) against this fixture, nothing changes — the fixed code path never executes for this conversation.
**Why it happens:** `_import_conversation`'s dedup check on `Argument.oyez_transcript_id` fires before any other logic runs and returns early on any match.
**How to avoid:** Build the delete routine described in "Fixture Delete-and-Reimport Lifecycle" above BEFORE attempting the "fix, then re-verify" step of Success Criterion 3; do not reuse `delete_argument`.
**Warning signs:** Re-running the import and seeing `skipped_existing` increment in the printed summary instead of `arguments_created`.

### Pitfall 2: `speakers.json`'s `type`/`role` fields are per-speaker-identity, not per-appearance — this fixture actually hits the failure mode

**What goes wrong:** Speaker id `j__thurgood_marshall` (62 turns in this transcript, all clearly arguing on behalf of the United States, e.g. "The position of the United States Government is...") gets `speakers.json` metadata `{"type": "J", "role": "justice"}` — globally, because Marshall LATER became a Justice (confirmed sworn in 1967-10-02 per `data/corpus/supreme_court_justices_sections.csv`), nine months AFTER this argument (1967-01-09). `_is_justice_type()` correctly reads the authoritative `type` field per its own documented design (D-12/Open Question 3 — never a name-prefix guess), so it will classify this speaker as BENCH for this argument, creating an `ArgumentParticipant(side=BENCH)` row and very likely matching/merging into the SAME `Person` row `import_justices_csv.py` already created for the real Justice Thurgood Marshall (exact `full_name` match: `"Thurgood Marshall"`).
**Why it happens:** ConvoKit's corpus creators appear to have built `speakers.json` using each speaker's eventual/best-known role rather than their role at the time of each specific argument. This is an upstream corpus data-quality characteristic, not something the importer introduced.
**How to avoid:** This is exactly the kind of judgment call D-05/D-06's operator-review gate exists for. Do not pre-decide the fix; document it as a finding with all the verified facts above (the 62-turn count, the exact quoted text, the exact tenure-start date, the exact `speakers.json` payload) so the operator can classify it — most plausibly as "real defect" (the importer has the `Argument.argued_date` available at speaker-resolution time and COULD cross-check it against `CourtTenure` before trusting `type=="J"`) or "upstream-missing/incorrect data" (accept that ConvoKit's speaker metadata is appearance-insensitive and there is no cheap general fix). Verify: 8 of the 9 justices scored as "bench speakers" in `.planning/FIXTURES.md`'s Ranked Shortlist table for this exact conversation match the real 8-justice Warren Court bench for this case (Warren, Black, Douglas, Stewart, Brennan, White, Clark, Fortas — all independently confirmed present in `supreme_court_justices_sections.csv` with tenures covering 1967-01-09); Marshall is the anomalous 8th-vs-9th count discrepancy hiding inside that same "8 bench speakers" figure.
**Warning signs:** D-02's `court_tenures` integrity check flags a "missing tenure" for a Justice on this fixture's argued date — before concluding this is a `court_tenures` data gap (D-03's "not fixed here" category), verify whether the flagged Justice's tenure dates are ACTUALLY correct (as Marshall's are) and the real problem is upstream speaker misclassification instead. Conflating these two categories would misdirect the D-03 "flag but don't fix" outcome onto the wrong table.

### Pitfall 3: `Utterance.section_hint` is a real, frontend-consumed column that `import_convokit.py` never populates

**What goes wrong:** The fixture's transcript page (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`) derives its Petitioner/Respondent/Rebuttal section-jump navigation anchors entirely from `utterance.section_hint`, filtering out any utterance where it is `null`. Since `_import_utterances` never sets `section_hint` (it sets `side`, `person_id`, `raw_speaker_label`, `is_stage_direction`, `text`, `sequence`, `strategy` — never `section_hint`), the fixture's rendered transcript page will have ZERO section anchors, a directly observable, user-visible fidelity gap.
**Why it happens:** `section_hint` was introduced for the PDF-ingest pipeline (`parse.py` passes through an already-computed value); the corpus importer was never retrofitted to compute an equivalent.
**How to avoid:** This is a strong "real defect" candidate (not schema-absent — the column and its consumer both already exist; not forbidden; not upstream-missing — the raw `advocates[].side` codes plus turn order carry enough signal to derive petitioner/respondent/rebuttal sections the same way the PDF pipeline's parse step does). Flag prominently for the operator's D-05 review with this exact evidence rather than assuming it's out of scope.
**Warning signs:** Loading the fixture's re-imported transcript page after the fix and seeing no section-jump links at all.

### Pitfall 4: The consolidated multi-docket text in the fixture's opening remarks has NO corresponding structured data anywhere in the raw corpus for this term

**What goes wrong:** The very first utterance turn (`15169__0_000`) names six consolidated dockets — 642, 680, 691, 813, 814, 815 — read aloud by the Chief Justice. It would be easy to assume this is a "dropped consolidated-case" defect (the importer's documented D-19 "lead-docket-only" behavior only creates a `Case`/`CaseArgument` row for docket 642). It is NOT that kind of gap for this fixture: `cases.jsonl` under term 1966 has **no case records at all** for dockets 680, 691, 813, 814, or 815 (verified directly — only docket 691 exists anywhere in the file, and it is an unrelated 1967-term case, "Rockefeller v. Wells", confirming the importer's own docstring warning that docket numbers recycle across terms).
**Why it happens:** The ConvoKit corpus export appears to only carry structured case records for the LEAD docket of a consolidated argument; the companion dockets are only ever mentioned in the free-text transcript, never as their own `cases.jsonl`/`conversations.json` records.
**How to avoid:** Classify this specific gap (companion dockets 680/691/813/814/815 never becoming their own `Case` rows) as **upstream-missing data**, not as a defect in the importer's D-19 lead-docket-only design — there is no structured companion-case data in the raw corpus for the importer to have dropped in the first place. Do not let this be the thing that reopens D-19 as a design question during this phase; D-19 is an existing, already-settled Phase 29 decision, and CORPUS-14's fix scope is about THIS fixture's field fidelity, not about redesigning consolidated-case handling.
**Warning signs:** Spending fix effort trying to make the importer discover/create Case rows for 680/691/813/814/815 — there is no source data to create them FROM for this fixture.

## Code Examples

### The exact existing test-fixture-writing pattern to reuse for any new/updated test

```python
# Source: pipeline/tests/test_import_convokit_core.py (verified in-repo, lines ~143-163)
def _write_corpus_fixture(
    tmp_path: Path,
    conversations: dict,
    cases: list[dict],
    speakers: dict,
) -> Path:
    """Write a small synthetic corpus_dir tree (never the real corpus files)."""
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    (corpus_dir / "conversations.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )
    with (corpus_dir / "cases.jsonl").open("w", encoding="utf-8") as f:
        for case in cases:
            f.write(json.dumps(case) + "\n")
    (corpus_dir / "speakers.json").write_text(json.dumps(speakers), encoding="utf-8")
    (corpus_dir / "utterances.jsonl").write_text("", encoding="utf-8")
    return corpus_dir
```

Any new test exercising the Marshall-misclassification fix or the `section_hint` fix should follow this exact pattern — small synthetic records shaped like the real fixture's fields (verified above), written to `tmp_path`, never the real 900MB `utterances.jsonl`. All existing DB-dependent tests in this file are skipped automatically when `DATABASE_URL`/`TEST_DATABASE_URL` is unset (via `conftest.py`), so this pattern works even before the environment question below is resolved.

### Reading the raw fixture directly (verified working, zero extra dependencies, runnable from WSL system Python as-is)

```python
import json

with open("data/corpus/conversations.json") as f:
    conv = json.load(f)["15169"]  # {"case_id": "1966_642", "advocates": {...}, "win_side": ..., "votes_side": {...}}

with open("data/corpus/cases.jsonl") as f:
    case = next(json.loads(line) for line in f if json.loads(line).get("id") == "1966_642")
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `url`, `adv_sides_inferred`, `known_respondent_adv`, and per-advocate `role` fields are low-value/advisory and belong in the "schema-absent, low-urgency" classification rather than "real defect" | Field Inventory table | If the operator actually wants any of these surfaced (e.g. `url` as a citation/reference link), this pre-judgment could bias the diff document's framing — the diff document itself should present these neutrally and let D-05 review decide, not adopt this research's tentative lean |
| A2 | Deleting the fixture's `Case` row between re-import attempts (not just the `Argument` and its children) is safe and recommended | Fixture Delete-and-Reimport Lifecycle | If any other already-imported argument ever links to the same Case row (not true today since this fixture is un-imported, but could become true if Phase 43 or a later action imports something sharing docket 642/term 1966 first), deleting the Case row would need to also check for other `CaseArgument` links before deleting it — the plan should add that check defensively even though it does not apply to the fixture's current state |
| A3 | The `meta.speaker_type`/`meta.side` per-turn fields would always agree with the conversation-level `advocates[].side` lookup, for any OTHER fixture, the way they happen to agree for this one | Pitfall on utterance meta fields | If a future full-corpus backfill (explicitly out of scope this phase, but informative for that later effort) relies on this research, a conversation where the two disagree would need separate handling this research did not verify |

## Open Questions

1. **Should `role_id`/`title`/`bio_text`/`photo_url` on `Person`, and `title` on `ArgumentParticipant`, be listed in the diff document at all, given they are structurally unpopulated by ANY corpus import (not specific to this fixture)?**
   - What we know: These columns exist and are legitimately never set by `import_convokit.py` for any conversation — `title` (ArgumentParticipant) is explicitly documented as sourced "from cover extractor" (PDF pipeline only); `role_id`/`bio_text`/`photo_url` (Person) have no ConvoKit-source equivalent at all.
   - What's unclear: Whether CORPUS-13's "field-by-field comparison... for all six affected tables" wants these enumerated explicitly (as "upstream-missing data, not a defect") for completeness, or whether the diff document should only list fields that HAVE a raw-source counterpart.
   - Recommendation: List them explicitly, tagged "upstream-missing data (no ConvoKit source exists for this column)" — matches the phase's own instruction to separate real defects from deliberate/structural exclusions, and costs nothing to include since the raw side is simply "N/A" for these rows.

2. **Does the operator want the Marshall bench-misclassification (Pitfall 2) fixed as a general importer improvement (cross-check `argued_date` against `court_tenures` before trusting `speakers.json.type`), or only worked around/flagged for THIS fixture?**
   - What we know: A general fix (checking tenure coverage before classifying BENCH) would be a real, reusable importer improvement that could also protect the other ~7,800 arguments during any future backfill (out of scope to RUN this phase, but the code change itself is in-scope if the operator wants it).
   - What's unclear: Whether building that general check is proportionate for a single-fixture-scoped phase, or whether a fixture-specific override/exception is preferred instead.
   - Recommendation: Bring both options to the D-05/D-06 review with their respective effort/reuse tradeoffs rather than the planner deciding unilaterally — this is squarely the kind of judgment call the CONTEXT.md review gate exists for.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| WSL system Python | Reading raw `data/corpus/*` files (stdlib `json` only) | ✓ | 3.14.4 | — |
| `pip`/`ensurepip` in WSL system Python | Installing any project dependency in WSL to run DB-touching diff/re-import code | ✗ (confirmed: `python3 -m pip` → "No module named pip"; `python3 -m ensurepip` → "No module named ensurepip") | — | Use the Windows-side `.venv` (confirmed present at `.venv/Scripts/`, includes `alembic.exe`) via the Windows terminal instead of WSL for any DB-touching step; OR install a system package (`apt-get install python3-pip python3-venv`, requires sudo) inside WSL first |
| Real dev PostgreSQL (portable, Windows-loopback-only) | Reading imported rows; executing delete/reimport | ✗ from WSL (confirmed unreachable in prior sessions — Windows-loopback-only, separate WSL network namespace); ✓ from Windows terminal | — | Ephemeral `pgserver`-backed Postgres from WSL (requires the `pip` fix above first), OR run the DB-touching half of this phase's work from the Windows terminal where `.venv` + the portable Postgres already work end-to-end |
| `sqlalchemy`/`asyncpg`/`alembic`/`pgserver` (WSL) | Any DB-touching diff/re-import step run from a WSL Claude Code session | ✗ (confirmed: none importable from WSL system Python) | — | `pip install` inside a working WSL venv once `pip` itself is available; OR skip WSL entirely for these steps |
| `pytest` + this repo's `pytest.ini` (`testpaths = tests pipeline/tests api/tests`, `asyncio_mode = auto`) | Automated tests for any importer fix | ✓ on Windows `.venv` (not directly verified from WSL — same `pip`-availability gap as above) | pytest>=8.0, pytest-asyncio>=0.23 (per `requirements-dev.txt`) | Run from Windows terminal, or provision a WSL venv first |
| `data/corpus/*` raw fixture files | The entire diff's raw-source half | ✓ (confirmed present and readable: `cases.jsonl` 13MB, `conversations.json` 3.8MB, `speakers.json` 0.6MB, `utterances.jsonl` 900MB) | — | — |

**Missing dependencies with no fallback:** none — every gap above has a documented fallback (Windows terminal, or a WSL venv bootstrap).

**Missing dependencies with fallback:** WSL's lack of `pip`/DB connectivity blocks any DB-touching step from a WSL Claude Code session; the fallback is to either (a) do those specific steps from the Windows terminal, or (b) bootstrap a WSL venv (`apt-get install python3-venv python3-pip` or equivalent, then `pip install -r requirements.txt -r requirements-dev.txt pgserver`) before attempting them from WSL. The planner should explicitly assign each DB-touching task to whichever environment will run it, rather than assuming a `psql`/pytest command will just work wherever the executing agent happens to be.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest>=8.0 with pytest-asyncio>=0.23 (both pinned in `requirements-dev.txt`) |
| Config file | `pytest.ini` (repo root) — `asyncio_mode = auto`, `testpaths = tests pipeline/tests api/tests`, `pythonpath = .` |
| Quick run command | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_convokit_core.py -x` (Windows terminal — `workflow.test_command` in `.planning/config.json`); from WSL, only usable once a working venv exists per Environment Availability above |
| Full suite command | `.\.venv\Scripts\python.exe -m pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORPUS-13 | Diff document correctly classifies a known schema-absent field (`decided_date`/`citation`/`court`) | unit (assert on the diff script's own output, or a documentation-only artifact review — no DB needed for this half) | New test target TBD by planner; existing precedent: `pipeline/tests/test_corpus_apolitical.py` tests `apolitical.py`'s extractors directly | ❌ Wave 0 (new diff script has no tests yet) |
| CORPUS-13 | Diff document correctly flags the Marshall bench-misclassification scenario (Pitfall 2) using a synthetic fixture shaped like the real one | unit, using `_write_corpus_fixture`'s established pattern with a synthetic speaker whose `type=="J"` but whose case's `argued_date` precedes any `CourtTenure` for that Person | ❌ Wave 0 | ❌ Wave 0 |
| CORPUS-14 | After the `section_hint` fix, a re-imported fixture's utterances have non-null `section_hint` values matching the advocate side transitions | Extends existing `pipeline/tests/test_import_convokit_utterances.py` patterns | `pytest pipeline/tests/test_import_convokit_utterances.py -x` | ✅ (file exists; new test cases needed inside it) |
| CORPUS-14 | Re-importing the fixture after ALL fixes reproduces exact utterance count (479), speaker roster, and source-docket set — no dropped/duplicated/merged turns | integration, against the delete-then-reimport lifecycle this research defines | New test target TBD by planner — likely a dedicated fixture-specific integration test, since no existing test targets this exact real fixture (all current tests use small synthetic corpus trees, per design) | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** targeted test file for whichever importer function was touched (e.g. `pytest pipeline/tests/test_import_convokit_core.py -x` after an `apolitical.py`/`_resolve_and_link_participant` change)
- **Per wave merge:** `pytest pipeline/tests/` (full pipeline suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`, plus the actual fixture re-import against a real (or ephemeral) Postgres — the automated suite alone cannot verify Success Criterion 4 (exact utterance count/speaker roster/docket-set match against the REAL 479-row fixture, as opposed to synthetic test fixtures)

### Wave 0 Gaps

- [ ] A new diff-generation script under `scripts/` (no test file exists yet — mirrors `scripts/select_corpus_fixtures.py`'s precedent of being a standalone, testable script, not a pipeline CLI subcommand)
- [ ] A new delete-and-reimport routine/script (no test file exists yet — must NOT reuse `admin_arguments.py::delete_argument`, see Pitfall 1)
- [ ] Test coverage for the Marshall-misclassification scenario specifically (no existing test constructs a speaker whose `type` disagrees with their actual role at the argument's date)
- [ ] Test coverage confirming `section_hint` gets populated by any importer fix (no existing test asserts on `section_hint` for corpus-imported utterances at all — `pipeline/tests/test_import_convokit_utterances.py` should be checked for whether it currently asserts `section_hint is None`, which would need updating rather than just extending)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V1 Architecture | Partially | No new attack surface — this phase only touches offline pipeline code and a new operator-run script; CLAUDE.md's "pipeline is offline only" rule is unaffected (no new HTTP endpoint is introduced) |
| V2 Authentication | No | No auth surface touched |
| V3 Session Management | No | No session surface touched |
| V4 Access Control | No | No access-control surface touched — the new delete-and-reimport routine is a standalone offline script/CLI option, not an admin API endpoint, so it does not need to respect (or risk weakening) `delete_argument`'s DRAFT-only gate |
| V5 Input Validation | Yes | Any new CLI flag (D-01's scoped conversation-id option) should validate the id exists in the loaded `conversations.json` before use, matching the existing fail-fast pattern in `_resolve_corpus_dir`/`_resolve_terms` (`argparse.ArgumentTypeError` on malformed input, `FileNotFoundError` on missing paths) |
| V6 Cryptography | No | Not touched |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A new delete routine accidentally deleting rows belonging to a DIFFERENT argument/case if the WHERE-clause scoping is wrong | Tampering / Repudiation (destroys audit-relevant data) | Scope every delete strictly to the fixture's own `argument_id`/`case_id`, verified by id lookup first (never a bulk delete by docket/term alone) — mirror `delete_argument`'s own pattern of `.where(Model.argument_id == argument_id)` on every statement |
| Forbidden apolitical fields (`win_side`, `votes`, etc.) leaking into the new diff script's OWN output (e.g. printing the raw dict for debugging) | Information Disclosure (violates the apolitical hard constraint even in an internal diagnostic artifact) | The diff script must read raw fields only through `extract_case_fields`/`extract_conversation_fields` for anything that gets written into the durable diff document — if the raw dict is inspected for the "what's NOT in the allow-list" analysis (as this research did), that inspection must stay in throwaway/ephemeral research output, never in the committed diff document itself |

## Sources

### Primary (HIGH confidence — read directly from this repo/data during this research session)

- `pipeline/commands/import_convokit.py` (full file, 1099 lines) — the importer under audit
- `pipeline/corpus/apolitical.py` (full file) — the allow-list extractors and `FORBIDDEN_FIELDS`
- `pipeline/corpus/loader.py` (full file) — the reusable loader functions
- `api/models/models.py` (lines 1-514, all 13 tables) — exact ORM column lists
- `api/services/admin_arguments.py::delete_argument` (lines 743-800+) — the DRAFT-only delete gate
- `data/corpus/conversations.json` — direct read of key `"15169"` and a full-file key-union scan
- `data/corpus/cases.jsonl` — direct read of `id == "1966_642"` and a targeted scan for dockets 680/691/813/814/815
- `data/corpus/speakers.json` — direct read of `j__thurgood_marshall` and other fixture speakers, plus a full-file `type`/`role` value-count scan
- `data/corpus/utterances.jsonl` (900MB) — `grep -c`/`grep -m` targeted reads for `conversation_id == "15169"` (479 rows confirmed) and the `j__thurgood_marshall` speaker specifically (62 rows confirmed)
- `data/corpus/supreme_court_justices_sections.csv` — direct read confirming all 9 justices' tenure dates, including Marshall's 1967-10-02 oath date
- `.planning/FIXTURES.md` — the confirmed fixture set and Phase 41's independent "8 bench speakers" count for this same conversation
- `pipeline/tests/test_import_convokit_core.py` — existing test patterns, including `_write_corpus_fixture`
- `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` (lines ~96-120, ~313-320) — confirms `section_hint` drives real frontend UI
- `pytest.ini`, `requirements.txt`, `requirements-dev.txt` — test framework and dependency versions
- `/home/jason/.claude/projects/-mnt-c-workspace-scotuschat/memory/project_scotuschat_wsl_windows_split.md` — WSL/Windows environment split, verified against this session's own WSL `pip`/DB-connectivity probes

### Secondary (MEDIUM confidence)

- `.planning/CONTEXT.md`, `.planning/STATE.md`, `.planning/REQUIREMENTS.md` — phase scope and carried-forward constraints (authoritative for scope, not independently re-verified against code beyond what's cited above)

### Tertiary (LOW confidence)

- None — every claim above was checked against the actual repo/data files in this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries needed; all reused helpers read directly from source
- Architecture / field inventory: HIGH — every field list was read from the actual fixture's raw records and the actual ORM/extractor source, not recalled from training data
- Pitfalls: HIGH — Pitfalls 1, 2, and 4 are backed by direct, reproducible evidence gathered this session (exact grep counts, exact CSV rows, exact code line behavior); Pitfall 3 is backed by direct code+frontend cross-reference
- Environment availability: HIGH — every WSL probe (`pip`, `ensurepip`, `sqlalchemy`, `asyncpg`, `pgserver` imports) was actually run this session, not assumed

**Research date:** 2026-07-30
**Valid until:** Effectively pinned to the current `data/corpus/` snapshot and the current state of `import_convokit.py`/`apolitical.py`/`models.py` — re-verify the Field Inventory tables if any of those files change before this phase is planned/executed, or if `data/corpus/` is ever replaced with an updated ConvoKit export (`.planning/FIXTURES.md` carries the same caveat).
