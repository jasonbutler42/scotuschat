---
phase: 38
slug: full-name-vs-name-parts-rethink
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-27
updated: 2026-07-27
---

# Phase 38 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Caller to domain helper | Untrusted API/import/migration strings enter canonicalization (`api/domain/person_names.py`) | Person name strings |
| Extractor to provenance envelope | Raw extracted text and confidence labels are untrusted data | Extraction metadata |
| Existing database to migration | Legacy production strings and relationships are authoritative state (0022 backfill) | `people.full_name` rows |
| Migration runtime to target database | Revision must not run against or report from the wrong database | DB connection identity |
| Admin client to FastAPI | Authenticated requests remain untrusted for fields, IDs, lengths, and JSON shape | Person create/update payloads |
| Job request to participant mutation | Job/argument/speaker identifiers cross an object-ownership boundary | `create_person_for_job` inputs |
| CSV/corpus files to import commands | External dataset text, IDs, and metadata enter persistent people records | Justice CSV, ConvoKit corpus |
| Import matching to existing Person rows | Canonicalization could accidentally bind or duplicate identities | `oyez_speaker_id`/`full_name` match keys |
| API metadata to Svelte DOM | Raw extraction text is untrusted display data | `name_extraction_metadata` |
| Browser component to clipboard | Only the interpreted value may leave the page through copy | Copy-to-clipboard payload |
| Browser forms to SvelteKit/FastAPI | Form fields and attempted values are untrusted despite admin authentication | People editor form submissions |
| API provenance to people editor DOM/clipboard | Exact raw extraction text crosses into rendering and copy UI | Per-part provenance stack |
| Admin browser → SvelteKit action → FastAPI `create_job` (G-38-6, added by Plans 38-07–38-10) | Operator-typed docket strings are untrusted despite admin-token auth | Docket value strings |
| FastAPI route → spawned ingest subprocess argv (G-38-6) | Accepted docket values become CLI arguments and later filesystem path components | Docket value → `pdf_filename`/`case_slug` |
| Direct CLI invocation → ingest (G-38-6) | `python -m pipeline ingest` bypasses FastAPI entirely, so the route-level guard alone does not apply | Docket value |
| Browser DOM → SvelteKit form action (G-38-6) | Hidden `docket[]` form inputs are trivially forgeable; the browser check is UX, not enforcement | Forged `docket[]` field |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-38-01 | Tampering | person_names.py | high | mitigate | Explicit allow-listed parts, length bounds, qualitative confidence validation, fixture-backed normalization | closed |
| T-38-02 | Denial of Service | normalization/splitter | medium | mitigate | Bounded inputs before whitespace/split processing; deterministic linear rules, no open-ended parsing | closed |
| T-38-03 | Information Disclosure | provenance raw text | low | accept | Raw source intentionally retained for authenticated operator review; UI escapes it as plain text | closed |
| T-38-04 | Tampering | 0022 backfill | high | mitigate | Exact pre/post snapshots, round-trip gate (CR-01 bug found by code review and fixed — now compares against stripped value), deterministic ordering/counts, abort-on-blank invariants | closed |
| T-38-05 | Repudiation | migration report | medium | mitigate | Deterministic applied/reviewed totals and reasons, covered by fixture tests; confirmed live (`215 applied, 3 flagged for review`) | closed |
| T-38-06 | Elevation of Privilege | migration target | high | mitigate | Alembic's bound connection only (`op.get_bind()`); no external connection fallback | closed |
| T-38-07 | Tampering | writable schemas | high | mitigate | `extra="forbid"` on PersonUpdate/PersonCreateRequest/admin_jobs.PersonCreate; `full_name` fully removed as a client-writable field | closed |
| T-38-08 | Elevation of Privilege | create_person_for_job | high | mitigate | Job state, argument ID, raw-label participant lookup, and admin auth guards retained before mutation | closed |
| T-38-09 | Repudiation | partial PATCH | medium | mitigate | `model_fields_set` merge semantics + atomic commit; omitted vs. explicitly-cleared fields are deterministic and tested | closed |
| T-38-10 | Spoofing | ConvoKit person matching | high | mitigate | `_resolve_person` checks `Person.oyez_speaker_id` first, then `full_name` fallback, then create — verified unchanged in `import_convokit.py` | closed |
| T-38-11 | Tampering | provenance refresh | high | mitigate | `_apply_extracted_name_provenance` validates envelopes and prefills only null/blank fields; `full_name` never rewritten on matched paths | closed |
| T-38-12 | Denial of Service | batch strings | medium | mitigate | Shared `person_names` length bounds applied before persistence in all three import/seed writers | closed |
| T-38-13 | Information Disclosure | clipboard payload | medium | mitigate | `CopyableExtractedValue` copies only the interpreted value; confirmed by source contract and by live UAT (Test 3: "copies only the interpreted value") | closed |
| T-38-14 | Tampering | raw rendering | high | mitigate | Normal Svelte `{expression}` interpolation only — no `{@html}` usage found in any Phase 38 frontend file (grep-verified) | closed |
| T-38-15 | Denial of Service | stale clipboard state | low | mitigate | Phase 36's payload-generation invalidation, timer cleanup, and failure handling retained (additive-only extension) | closed |
| T-38-16 | Tampering | people server actions | high | mitigate | Server actions post only explicit name parts, never `full_name`; X-Admin-Token forwarding and backend validation retained | closed |
| T-38-17 | Information Disclosure | raw provenance UI | medium | mitigate | Authenticated admin route, normal Svelte interpolation, interpreted-only clipboard payload (same control family as T-38-13/14) | closed |
| T-38-18 | Elevation of Privilege | Name review query | low | mitigate | `missing_filters` is a fixed Python dict keyed by literal strings (`Person.name_needs_review.is_(True)`); no dynamic SQL/interpolated predicate (grep-verified) | closed |
| T-38-19 | Tampering | `pipeline/commands/ingest.py` PDF path construction | high | mitigate | Docket path-component guard before `pdf_filename` construction plus a resolved-path containment assertion placed before every read/write branch, so the write cannot escape `data/pdfs` even if the character rule is bypassed (G-38-6) | closed |
| T-38-20 | Tampering | `api/routers/admin.py::_normalize_dockets` | high | mitigate | Shared `normalize_docket_value` allow-list plus 64-character cap raises 422 before job creation and before `spawn_pipeline_step`, closing the authenticated-admin arbitrary-file-write primitive at its authoritative boundary (G-38-6) | closed |
| T-38-21 | Denial of Service | over-length docket values | medium | mitigate | 64-character cap enforced at the boundary; error messages bounded to a 32-character echo so a multi-kilobyte value cannot inflate a 422 body or `admin_jobs.error_message` | closed |
| T-38-22 | Tampering | `Case.slug` construction from docket values | medium | mitigate | The same guard runs on every docket used in `case_slug`, so a separator cannot inject a phantom public URL path segment | closed |
| T-38-23 | Tampering | forged `docket[]` hidden inputs | medium | mitigate | The SvelteKit action re-checks every raw docket value server-side and the FastAPI boundary remains authoritative, so bypassing the browser gains nothing | closed |
| T-38-24 | Information Disclosure | 422 detail text | low | accept | The 422 detail echoes a bounded prefix of the operator's own submitted value on an admin-token-gated route; no server-side state, path, or credential is revealed | closed |
| T-38-25 | Tampering | divergent copies of the docket rule | medium | mitigate | One canonical module (`api/domain/docket_values.py`) plus a fixture that asserts its own declared pattern and cap equal the module constants, so a second enforcement point cannot silently carry a weaker rule | closed |
| T-38-26 | Repudiation | job-driven ingest failure reporting | medium | mitigate | The guard raises `ValueError` so `run_ingest`'s existing handler records `AdminJobStatus.FAILED` with a readable `error_message` instead of leaking a raw `[Errno 22]` OSError | closed |
| T-38-27 | Tampering | guard removed by a later refactor | medium | mitigate | `inspect.getsource` static asserts fail if the guard invocation or the containment assertion disappears from the executed code path | closed |
| T-38-28 | Tampering | TypeScript/Python docket rule divergence | medium | mitigate | `test_docket_ui_contract.py` extracts the client pattern literal and cap and asserts equality with the Python constants, then replays the shared fixture through the extracted rule | closed |
| T-38-29 | Information Disclosure | SvelteKit failure copy | low | mitigate | The docket failure message is fixed text plus the shared cap; the submitted value is never echoed and FastAPI's 422 detail is never forwarded verbatim | closed |
| T-38-30 | Denial of Service | regression on the metadata editor | low | mitigate | `enforceShape` defaults to false and only the Pipeline Runner opts in, so `ArgumentDetailsCard`'s already-persisted legacy docket values keep rendering/saving unchanged (contract-test asserted) | closed |
| T-38-31 | Tampering | end-to-end docket path (G-38-6 reproduction) | high | mitigate | Operator re-ran the original reported reproduction plus traversal and absolute-path variants against the running stack, confirming rejection before job creation and no write outside `data/pdfs` — explicit "Approved" sign-off recorded in 38-UAT.md | closed |
| T-38-32 | Denial of Service | regression in existing job creation | medium | mitigate | Consolidated regression gate over every suite that exercises `create_job`, `_normalize_dockets`, and ingest — 119 passed, 0 failures, independently re-run by both the executor and the phase verifier | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-38-01 | T-38-03 | Provenance raw text is intentionally retained for authenticated-operator review of legacy/extracted name data; it is never exposed to unauthenticated users and the UI renders it as escaped plain text only. | Plan 38-01 (authored at plan time) | 2026-07-27 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-27 | 18 | 18 | 0 | Claude (orchestrator, L1 grep-depth — register authored at plan time, ASVS level 1, short-circuit per workflow) |
| 2026-07-27 | 32 | 32 | 0 | Claude (orchestrator) — added T-38-19 through T-38-32 for UAT gap G-38-6 (authenticated-admin path-traversal / arbitrary-file-write in docket-value handling), closed by Plans 38-07–38-10. Independently cross-checked against `38-REVIEW-GAPCLOSURE.md` (adversarial code review, no bypass found) and `38-VERIFICATION.md` (independent re-execution of the 9-suite regression gate: 119 passed, 0 failures) rather than only citing plan-authored dispositions. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-27 (original scope, plans 38-01–38-06); re-verified 2026-07-27 to cover the full 10-plan final state including G-38-6 gap closure
