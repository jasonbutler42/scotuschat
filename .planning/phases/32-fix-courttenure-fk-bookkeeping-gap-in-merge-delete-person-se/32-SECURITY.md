---
phase: 32
slug: fix-courttenure-fk-bookkeeping-gap-in-merge-delete-person-se
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-13
---

# Phase 32 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| admin client → FastAPI admin router | Operator-authenticated requests (`X-Admin-Token`) cross here carrying `person_id` path params | Integer path params, no PII in this phase's diff |
| service layer → PostgreSQL | Bulk UPDATE/DELETE/COUNT statements cross here inside a single transaction | `court_tenures` row data (seat/date ranges — no customer/pricing data) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-32-ATOMIC | Tampering | `merge_people` transaction | high | mitigate | All 5 UPDATEs + the source DELETE run inside the session's single implicit transaction with one `db.commit()` at line 630; a mid-merge failure rolls back every table together. Confirmed via `git show 3f9d2059`: no second `db.commit()` was added — exactly one commit remains. | closed |
| T-32-ORPHAN | Denial of Service (data integrity) | `delete_person_if_orphan` | high | mitigate | Server-side COUNT over all 5 FK tables (now incl. `CourtTenure`) is authoritative; a person with tenure rows returns `False` → 409, preventing the previously-unhandled `IntegrityError` (500). Confirmed: `CourtTenure` appended to the blocking-tier loop at `api/services/admin_people.py:661`, distinct from the unconditional `SpeakerAlias`-delete tier (byte-unchanged). Router maps `False` → `HTTPException(409, ...)`. | closed |
| T-32F-STALE | Information Disclosure (misleading UI) | client `can_delete` derivation | medium | mitigate | `tenures` added to the client `can_delete`/`delete_block_count` computation in `+page.server.ts`, keeping the disabled-state accurate. Defense-in-depth only — the server-side COUNT (T-32-ORPHAN) remains authoritative and returns 409 regardless of client state. Confirmed present in the diff and by `npm run check` (0 errors). | closed |
| T-32F-CONTRACT | Tampering (silent field drop) | fixed-shape merge-preview contract | medium | mitigate | `tenures` field name is hardcoded identically in the Pydantic schema (`api/schemas/admin_people.py`) and both TS surfaces (`+page.server.ts`, `+page.svelte`); confirmed by direct read of all three files — no name mismatch, no silent-drop risk. | closed |
| T-32-AUTHZ | Spoofing / Elevation | `DELETE /people/{person_id}`, merge endpoint | low | accept | Authorization is unaffected by this phase — the existing admin `X-Admin-Token` gate on the admin router already protects these endpoints; no new auth surface introduced. | closed |
| T-32-DOS | Denial of Service | repeated merge/delete against large tenure counts | low | accept | Out of scope — tenure counts per Justice are small (single-digit historical seats), and the endpoints are already behind the admin auth gate. | closed |
| T-32-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs in this phase — `CourtTenure` was already imported; no new dependency added. | closed |
| T-32F-AUTHZ | Elevation | `+page.server.ts` fetch | low | accept | Unaffected — `FASTAPI_BASE_URL` and the admin token stay server-only (never `PUBLIC_`), matching the existing architecture rule; no new client-exposed secret or endpoint introduced. | closed |
| T-32F-SC | Tampering | npm installs | low | accept | No package installs — a two-file edit against existing SvelteKit code. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-32-01 | T-32-AUTHZ | Existing admin `X-Admin-Token` gate already covers this surface; no new auth boundary introduced by this phase | Phase 32 plan (32-01-PLAN.md, D-authored at plan time) | 2026-07-13 |
| AR-32-02 | T-32-DOS | Tenure counts per Justice are single-digit; no realistic abuse vector introduced | Phase 32 plan (32-01-PLAN.md) | 2026-07-13 |
| AR-32-03 | T-32-SC | No package installs in backend plan | Phase 32 plan (32-01-PLAN.md) | 2026-07-13 |
| AR-32-04 | T-32F-AUTHZ | Server-only token/base-URL architecture rule unaffected by this phase | Phase 32 plan (32-02-PLAN.md) | 2026-07-13 |
| AR-32-05 | T-32F-SC | No package installs in frontend plan | Phase 32 plan (32-02-PLAN.md) | 2026-07-13 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-13 | 9 | 9 | 0 | Claude (orchestrator, L1/ASVS-1 short-circuit — register authored at plan time, threats_open resolved to 0 via verifier/code-review evidence, no auditor spawn required per gsd-secure-phase short-circuit rule) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-13
