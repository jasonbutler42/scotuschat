---
phase: 47
slug: provenance-foundation
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-18
---

# Phase 47 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register origin: authored at plan time (`<threat_model>` blocks present in all six
PLAN files). Verified at ASVS L1 grep depth; `workflow.security_block_on: high`.
Per the `secure-phase` short-circuit rule (`threats_open: 0` +
`register_authored_at_plan_time: true` + `asvs_level == 1`), no auditor subagent
was spawned — L1 grep depth is sufficient.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Alembic CLI → PostgreSQL | Destructive DDL (`DROP TABLE`, `TRUNCATE`) crosses here against whatever `DATABASE_URL` resolves to | Schema definitions; all transcript rows at risk |
| pytest harness → PostgreSQL | The rootdir `conftest.py` redirect decides whether tests hit `scotus_test` or the shared dev DB | Test fixture rows vs. live dev data |
| operator CLI (`python -m pipeline import-convokit`) → PostgreSQL | Untrusted ConvoKit corpus content written into `import_run` / `Argument` rows | Third-party corpus text |
| operator CLI (`ingest`/`parse`/`resolve`) → PostgreSQL | Untrusted PDF content and a caller-supplied `--url` cross into `import_run.pdf_url` | PDF bytes, operator-supplied URL string |
| `parse.py` → Anthropic API | Transcript text leaves the process; the response drives which `method` is stamped | Public oral-argument transcript text |
| test harness → Anthropic API | A test that forgets to monkeypatch `parse_with_llm` would make a real, billable call | Transcript text; API credentials |
| public HTTP → FastAPI read path | Anonymous visitors receive whatever `UtteranceResponse` / `ArgumentMetadataResponse` expose | Public transcript content; provenance must NOT cross |
| admin HTTP → FastAPI admin router | Operator-authenticated requests read run rows and stream PDFs by `run_id` | Operator-facing lineage |
| FastAPI → PostgreSQL | Read-only queries; the API never writes `import_run` rows (CLAUDE.md architecture rule 1) | Read-only |
| `reset_to_fixture` → PostgreSQL | Nine-table `TRUNCATE ... CASCADE` against whatever `DATABASE_URL` resolves to | All transcript rows |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-47-01 | Tampering | `alembic upgrade head` / `reset_to_fixture` TRUNCATE vs wrong DB | high | mitigate | `_require_corpus_files` pre-flight runs as step 1 before the step-2 TRUNCATE (`api/services/admin_dev.py:167-170`); 47-06 recorded `alembic current` = `0026 (head)` and the resolved DB name before the reseed, executed under explicit operator authorization | closed |
| T-47-02 | Repudiation | `conftest.py::_WATCHED_TABLES` leak tripwire | high | mitigate | `conftest.py:78` watches `import_run` — no stale `pipeline_runs` string; renamed in the same commit as migration 0026. `tests/test_pytest_isolation_invocation_shapes.py` passes 3/3 | closed |
| T-47-03 | Tampering | `TRUNCATE_SQL` lists in `admin_dev.py` and `pipeline/tests/conftest.py` | high | mitigate | Both lists carry `import_run` (`api/services/admin_dev.py:123`, `pipeline/tests/conftest.py:130`); all three hardcoded sites updated in one commit | closed |
| T-47-13 | Tampering | Explicit-path pytest invocation against the shared dev DB | high | mitigate | Module-level redirect in the repo-root `conftest.py:59-60` fires for every invocation shape; the CLAUDE.md-named regression test covers all three shapes and passes | closed |
| T-47-16 | Tampering | `test_admin_dev_routes.py` executing the real `reset_to_fixture` | high | mitigate | Patching harness preserved verbatim — `patch("api.routers.admin_dev.admin_dev_service.reset_to_fixture")` at `api/tests/test_admin_dev_routes.py:263-264`, with the file-level guard docstring intact at line 9 | closed |
| T-47-19 | Information Disclosure | Provenance vocabulary rendered on the public argument page | high | mitigate | No `corpus` / `pdf_pipeline` / `rule_based` / `llm_corrective` string reaches `app/src/routes/cases/`. The only attribution on the public page is the pre-existing Phase 29 (D-22/T-29-11) Oyez caption gated on `is_corpus_sourced`, derived from `oyez_transcript_id` — not from Phase 47 provenance | closed |
| T-47-04 | Information Disclosure | `api/schemas/utterance.py` public response | medium | mitigate | No `strategy` / `source` / `method` / `external_id` field in the schema (grep returns none); only `import_run_id: int` at line 33 | closed |
| T-47-07 | Spoofing | `parse.py` method stamping | medium | mitigate | `parse_method` derived at `pipeline/commands/parse.py:266` from whether `parse_with_llm` returned or raised — never caller-supplied; both branches test-covered | closed |
| T-47-08 | Information Disclosure | Test suite calling the live Anthropic API | medium | mitigate | `parse_with_llm` monkeypatched in every leg; `grep -c anthropic pipeline/tests/test_import_run_provenance.py` returns 0 | closed |
| T-47-14 | Repudiation | Deleting a failing test instead of translating it | medium | mitigate | Collected test counts compared against pre-phase counts; `pipeline/tests` at 239 passed / 5 xfailed with zero `PipelineRun` residue, no test deleted | closed |
| T-47-17 | Information Disclosure | `api/tests/test_arguments.py` public contract assertions | medium | mitigate | Four standing negative assertions at `api/tests/test_arguments.py:261-264` prove `strategy`, `source`, `method`, `external_id` are absent from a serialized utterance | closed |
| T-47-18 | Tampering | Editing a table-count assertion to make a contract test pass | medium | mitigate | Literal `assert len(tables) == 13` intact at `tests/test_models_import.py:13` — count unchanged across the phase | closed |
| T-47-20 | Repudiation | Evidence recorded as prose rather than actual row values | medium | mitigate | `47-PROVENANCE-EVIDENCE.md` carries the three named sections with real query output and unrounded row counts | closed |
| T-47-06 | Tampering | `import_run.source` / `method` writes | low | mitigate | Native PG enum types + NOT NULL reject out-of-vocabulary and missing values at the storage boundary (ASVS V5); covered by `test_import_run_rejects_missing_source_and_method` | closed |
| T-47-15 | Spoofing | Hand-built `ImportRun` fixtures declaring an unproducible provenance | low | mitigate | Conversion rules pin each fixture's `source`/`method` to what the production writer actually stamps | closed |
| T-47-09 | Tampering | `import_run.pdf_url` from `args.url` | low | accept | Operator-supplied string stored verbatim for lineage, rendered only on the dev-only admin surface; ASVS L1 requires no control for an offline CLI argument the operator supplies themselves | closed |
| T-47-10 | Information Disclosure | `admin_jobs.py` `is_corpus` derivation | low | accept | Admin-only field already rendered on the operator job list; the phase changes how it is computed, not who can see it | closed |
| T-47-11 | Tampering | `admin.py` PDF streaming by `run_id` | low | accept | Unchanged primary-key fetch on an admin-gated route; the phase renames the model class only | closed |
| T-47-12 | Denial of Service | `get_run_id_for_step` `created_at` ordering tie | low | accept | A tie returns an arbitrary but valid run id — degrades determinism, not availability; deferred to the Path-rework phase per the scope fence | closed |
| T-47-SC | Tampering | npm/pip/cargo installs | low | accept | No packages installed this phase; RESEARCH.md records "Package Legitimacy Audit: Not applicable" with no `[ASSUMED]`/`[SUS]`/`[SLOP]` entries | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above `workflow.security_block_on` count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-47-01 | T-47-09 | `pdf_url` is an operator-supplied CLI argument stored verbatim for lineage; rendered only on the dev-only admin surface. No ASVS L1 control required for an offline operator-authored string. | plan-time disposition (47-02-PLAN.md) | 2026-08-18 |
| R-47-02 | T-47-10 | Corpus-vs-PDF Source tag is already admin-only; the phase changes its derivation, not its audience. | plan-time disposition (47-03-PLAN.md) | 2026-08-18 |
| R-47-03 | T-47-11 | Admin-gated primary-key PDF fetch; the phase renames the model class only. Route access control is out of scope and unmodified. | plan-time disposition (47-03-PLAN.md) | 2026-08-18 |
| R-47-04 | T-47-12 | An ordering tie yields an arbitrary but valid run id — determinism, not availability. Recorded as a backstop truth and deferred to the Path-rework phase. | plan-time disposition (47-03-PLAN.md) | 2026-08-18 |
| R-47-05 | T-47-SC | No packages installed this phase; no supply-chain surface introduced. | plan-time disposition (all six PLANs) | 2026-08-18 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-18 | 20 | 20 | 0 | `/gsd-secure-phase 47` (orchestrator, ASVS L1 grep depth — short-circuit rule, no auditor subagent) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-18
