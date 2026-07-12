---
phase: 29
slug: historical-corpus-import
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-10
---

# Phase 29 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register origin: authored at plan time — all 9 plans (29-01 through 29-09) carried a `<threat_model>` block. Verified retroactively via `/gsd-secure-phase` against the implemented code (L1 grep-depth, ASVS level 1, short-circuit path — no auditor subagent spawn required since preliminary classification found `threats_open: 0`).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| PyPI → dev/CI environment | External package (python-dateutil) installed into the runtime | Third-party package source |
| Migration → live database | Alembic DDL mutates the production schema | Schema structure only, no data |
| Local filesystem → git | Large external corpus source files could be accidentally committed | 900MB+ JSON/JSONL/CSV files |
| External corpus files → application memory | Untrusted third-party ConvoKit JSON/JSONL is parsed | conversations.json, cases.jsonl, speakers.json, utterances.jsonl |
| Raw source dict → ORM/DB | Outcome/vote fields must never cross into persistence | win_side, votes_side, scdb_docket_id, etc. |
| Operator CLI args → filesystem | `--csv` / `--term` / `--term-range` / `--corpus-dir` are operator-supplied | Local file paths, term selectors |
| CSV/JSONL files → database | External name/tenure/case/argument data written to people/court_tenures/cases/arguments | Justice bios, case metadata, transcripts |
| FastAPI payload → SvelteKit server load (SSR) | `oyez_transcript_id` crosses into SSR; visibility decided server-side | Corpus-sourced flag, transcript ID |
| SSR → browser | `FASTAPI_BASE_URL` must never reach the client (Architecture Rule 2) | N/A — boundary enforced, nothing crosses |
| API response boundary (server → client) | `GET /arguments/{id}/utterances`, `GET /cases`, consumed by `+page.server.ts` | Argument/case metadata, incl. nullable `argued_date` |
| Pipeline CLI (operator-only, offline) → PostgreSQL | `import_convokit.py` writes `PipelineRun.step`; no network input crosses | Hardcoded step literal, operator term selectors only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-29-SC | Tampering | pip install python-dateutil (29-01) | high | mitigate | Blocking human-verify checkpoint confirmed PyPI page + source repo match `github.com/dateutil/dateutil` before install | closed |
| T-29-05 | Tampering | Alembic migration 0017 (29-01) | medium | mitigate | Columns nullable, no backfill, reversible; `alembic/versions/0017_add_oyez_external_ids.py` downgrade drops all 3 columns cleanly | closed |
| T-29-06 | Information Disclosure | data/corpus/ 900MB source files (29-01) | medium | mitigate | `.gitignore:16` excludes `data/corpus/*.jsonl`; only `.gitkeep`/`.gitignore` tracked | closed |
| T-29-02 | Information Disclosure | apolitical.py allowlist extractors (29-02) | high | mitigate | `pipeline/corpus/apolitical.py` — positive allowlist, `FORBIDDEN_FIELDS` frozenset, never `{**raw}`; `test_apolitical_fields_never_persisted_to_any_column` in `test_import_convokit_core.py` | closed |
| T-29-03 | Denial of Service | utterance streaming (29-02, 29-05) | high | mitigate | `loader.py:24 stream_utterances_for_conversation_ids` is generator-based, line-by-line; never `.read()`/`json.load()`s the 900MB file | closed |
| T-29-07 | Tampering | stage_directions.detect_stage_direction (29-02, 29-05) | medium | mitigate | `pipeline/corpus/stage_directions.py` — curated typo-tolerant vocabulary; split is losslessly reversible per D-16 | closed |
| T-29-04 | Tampering | Person/CourtTenure dedup (29-03); Argument/Person/ArgumentParticipant dedup (29-04) | high | mitigate | Check-before-insert confirmed: `select(Argument).where(Argument.oyez_transcript_id == ...)`, `select(Person).where(Person.oyez_speaker_id == ...)` w/ full_name fallback, in `import_convokit.py` | closed |
| T-29-08 | DoS (input validation) | `--csv` path arg (29-03) | low | mitigate | `import_justices_csv.py:158` validates path existence, raises `FileNotFoundError` before opening | closed |
| T-29-05b | DoS (input validation) | `--term`/`--term-range`/`--corpus-dir` (29-04) | medium | mitigate | Integer/range well-formedness and directory existence validated before use; per-conversation try/except isolates failures | closed |
| T-29-09 | Tampering (referential integrity) | PipelineRun before Utterance (29-04, 29-05) | medium | mitigate | PipelineRun created/flushed before any Utterance write; `pipeline_run_id` NOT NULL invariant preserved (D-09) | closed |
| T-29-10 | Tampering (data integrity) | malformed turn rows mid-batch (29-05) | medium | mitigate | Per-row key validation + try/except captured in batch counter; one bad row flagged, not fatal | closed |
| T-29-11 | Information Disclosure | +page.server.ts note gating (29-06) | low | mitigate | `is_corpus_sourced` computed server-side from `oyez_transcript_id`; confirmed in `+page.server.ts:48-50` | closed |
| T-29-02 | Information Disclosure | argument payload field addition (29-06) | medium | mitigate | Only `oyez_transcript_id` added to payload; no win_side/votes_side/scdb_docket_id crosses SSR boundary | closed |
| T-29-12 | Denial of Service | ArgumentMetadataResponse/get_utterances argued_date (29-07) | high | mitigate | `argued_date: Optional[datetime.date]` confirmed in `api/schemas/*.py`; eliminates `ResponseValidationError` → HTTP 500 | closed |
| T-29-13 | Information Disclosure | FastAPI default 500 error handler (29-07) | low | mitigate | Underlying validation failure eliminated as a side effect of the T-29-12 fix — no field/type details to leak | closed |
| T-29-16 | Tampering (data integrity) | PipelineRun.step literal (29-08) | low | mitigate | Regression assertions confirmed asserting `run.step == "parse"` in `test_import_convokit_core.py`, `test_import_convokit_utterances.py`, `test_resolve.py` | closed |
| T-29-09-01 | Integrity (Tampering) | `_import_conversation` vs `uq_arguments_source_docket_question` (29-09) | high | mitigate | `_next_question_number` confirmed at `import_convokit.py:256`; per-docket derivation aligns write with DB uniqueness contract; regression tests prove no silent drop | closed |
| T-29-09-02 | Repudiation / auditability | `docket_question_conflict` counter (29-09) | medium | mitigate | Confirmed distinct counter + WARNING logging naming conversation_id + docket in `import_convokit.py` | closed |

*Status: open · closed · open — below `high` threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` (high) count toward `threats_open`*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|--------------|------|
| AR-29-01 | T-29-02 (29-03, CSV → court_tenures) | Justices CSV carries no outcome/vote data (win_side/votes_side/scdb_docket_id live in conversations.json/cases.jsonl, not the CSV) — apolitical leakage is not reachable from this file | Plan 29-03 author | 2026-07-09 |
| AR-29-02 | T-29-12 (29-06, attribution copy accuracy) | CC BY-NC 4.0 fact verified during discussion (D-24); copy is static and matches UI-SPEC — accepted as a content-accuracy note, not a runtime threat | Plan 29-06 author | 2026-07-09 |
| AR-29-03 | T-29-14 (29-07, scope note) | Narrow type-widening (non-optional → Optional on an already-public field); no new input parsing, user-controlled data path, or auth/authz change | Plan 29-07 author | 2026-07-09 |
| AR-29-04 | T-29-15 (29-08, PipelineRun.step write/read path) | Brings corpus-imported draft arguments to the same pre-existing exposure level PDF-ingested draft arguments already have via the same unauthenticated endpoint — parity, not a new or increased disclosure surface | Plan 29-08 author | 2026-07-09 |
| AR-29-05 | T-29-17 (29-08, admin_jobs.py lookups) | Structurally unreachable: corpus-imported arguments never have an `AdminJob` row, so the step-keyed lookup path has zero interaction with this change | Plan 29-08 author | 2026-07-09 |
| AR-29-06 | T-29-09-03 (29-09, malformed conversation DoS) | Existing per-conversation try/except already isolates a bad row; unchanged by this plan | Plan 29-09 author | 2026-07-10 |
| AR-29-07 | T-29-09-04 (29-09, apolitical fields) | Out of scope for this change; already stripped at extract time and covered by `test_apolitical_fields_never_persisted_to_any_column` | Plan 29-09 author | 2026-07-10 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-10 | 25 | 25 | 0 | /gsd-secure-phase (L1 grep-depth, short-circuit — ASVS level 1, register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-10
