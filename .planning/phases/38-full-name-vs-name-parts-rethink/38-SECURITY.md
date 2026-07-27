---
phase: 38
slug: full-name-vs-name-parts-rethink
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-27
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

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-27
