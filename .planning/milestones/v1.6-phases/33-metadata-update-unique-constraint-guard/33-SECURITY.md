---
phase: 33
slug: metadata-update-unique-constraint-guard
status: verified
threats_open: 0
asvs_level: 1
created: 2026-07-14
---

# Phase 33 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Admin client -> FastAPI | Authenticated metadata edits enter the API as untrusted values. | Docket, question number, argued date |
| Service/router -> PostgreSQL | Pre-checks and concurrent writes cross a TOCTOU boundary. | Final metadata pair, constraint identity |
| Corpus -> pipeline | Imported corpus metadata is untrusted and may collide with stored rows. | Docket and question metadata |
| FastAPI -> SvelteKit action | Backend error JSON is validated before becoming form state. | Error code, message, conflict ID |
| Action data -> browser/new tab | A server-derived identifier controls local recovery navigation. | Conflicting argument ID |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-33-01 | Tampering | Update transaction | high | mitigate | Shared final-pair pre-check plus authoritative `uq_arguments_source_docket_question` classification; target-race tests verify rollback and winner lookup. | closed |
| T-33-02 | Information Disclosure | Error response | high | mitigate | Duplicate responses contain stable structured fields; unrelated constraint failures return sanitized `constraint_violation` detail without driver text. | closed |
| T-33-03 | Elevation of Privilege | Admin PATCH | low | accept | Phase changes duplicate handling only and leaves the existing admin authentication boundary unchanged. | closed |
| T-33-04 | Tampering | Offline writers | high | mitigate | Ingest, ConvoKit import, and parse use the shared pair lookup and exact named-constraint classifier. | closed |
| T-33-05 | Information Disclosure | Command output | high | mitigate | Offline duplicate handling is entered only for the named constraint; unrelated integrity failures do not receive duplicate wording. | closed |
| T-33-06 | Repudiation | Import counters | medium | mitigate | ConvoKit increments the duplicate/conflict path only for the exact named violation, with regression coverage. | closed |
| T-33-07 | Spoofing | Conflict link | high | mitigate | Both actions require a positive integer conflict ID; the component constructs a local `/admin/arguments/{id}` path with `noopener noreferrer`. | closed |
| T-33-08 | Information Disclosure | Error parsing | high | mitigate | SvelteKit actions accept only validated `duplicate_argument` detail and use generic handling for all other responses. | closed |
| T-33-09 | Denial of Service | Keyboard recovery | medium | mitigate | The shared component renders one alert and performs update, tick, then focus; source-contract tests lock the order. | closed |
| T-33-10 | Information Disclosure | Duplicate and constraint payloads | high | mitigate | Duplicate copy is limited to the submitted pair and conflict ID; unrelated constraint payloads remain sanitized. | closed |
| T-33-11 | Spoofing | Conflict navigation | high | mitigate | Positive-integer validation, server-derived IDs, and local path construction are covered by regression tests. | closed |
| T-33-12 | Elevation of Privilege | New-tab opener | medium | mitigate | The recovery link retains `target="_blank"` with `rel="noopener noreferrer"`, asserted by tests. | closed |
| T-33-SC | Tampering | Dependency installation | low | accept | All four plan summaries record `tech-stack.added: []`; no package or external dependency was introduced. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-33-01 | T-33-03 | Existing admin authentication is outside this phase; the PATCH authorization boundary was not weakened or expanded. | Phase plan | 2026-07-14 |
| AR-33-02 | T-33-SC | No dependencies were installed, so no new supply-chain exposure was introduced. | Phase plan | 2026-07-14 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-14 | 13 | 13 | 0 | Codex secure-phase ASVS L1 verification |

## Security Audit 2026-07-14

| Metric | Count |
|--------|-------|
| Threats found | 13 |
| Closed | 13 |
| Open | 0 |

Plan-time STRIDE registers were present in all four plans. Grep-depth verification confirmed the named-constraint controls, sanitized error paths, defensive conflict-ID parsing, local recovery navigation, opener isolation, and their focused regression tests. Per the ASVS Level 1 short-circuit, no deeper auditor pass was required after preliminary classification reached `threats_open: 0`.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-14
