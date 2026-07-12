---
phase: 23
slug: shared-argument-details-component
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-07
---

# Phase 23 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Note: Plan 23-06 has no `<threat_model>` block (UI-only refactor with no new trust boundary).
> `register_authored_at_plan_time: true` — 6 of 7 plans authored a threat model at plan time.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| SvelteKit action → FastAPI `PATCH /arguments/{id}/metadata` | Operator-supplied `question_number`/docket/date fields cross here | Metadata fields (allowlisted) |
| Operator keyboard input → docket pill `$state` | Untrusted text becomes hidden form inputs, then DOM-rendered pills | Docket strings |
| Browser form POST → `saveJobMetadata` action | Operator-supplied `docket[]`/`question_number`/`argued_date`; server derives `argument_id` independently | Metadata fields, never `argument_id` |
| `+page.server.ts` action → FastAPI PATCH | Server-side fetch sends JSON body; `ADMIN_TOKEN` in header | Metadata JSON, admin auth header |
| FastAPI PATCH handler → PostgreSQL | SQLAlchemy update with parameterized values | Normalized docket array, dates, ints |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-23-01 | Tampering | `MetadataUpdate` mass-assignment | medium | mitigate | Verified in `api/schemas/admin_arguments.py:155-170` and `api/services/admin_arguments.py:512-590`: only `case_name`, `source_docket`/`source_dockets`, `argued_date`, `question_number` are ever written; no other `Argument`/`Case` field is settable. | closed |
| T-23-02 | Denial of Service | `question_number` int parse | low | mitigate | Verified in `api/services/admin_arguments.py:564-568`: `int(body.question_number)` wrapped in `try/except ValueError: pass` — non-numeric input is silently skipped, never raises 500. | closed |
| T-23-03 | Information Disclosure | IDOR on `argument_id` | medium | mitigate | Verified: `argument_id` is fetched server-side from the job record in `saveJobMetadata` (`+page.server.ts:375-389`), never accepted from form data; existing 404-on-missing guard retained in the metadata endpoint. | closed |
| T-23-02-01 | Tampering | `docket[]` hidden inputs | low | accept | Accepted per plan — client is not a trust boundary for persistence; server-side trim + validation happens in the SvelteKit action and FastAPI. | closed |
| T-23-02-02 | Injection | pill value rendered in DOM | low | mitigate | Verified: `DocketPillInput.svelte` interpolates pill text via `{pill}` (Svelte auto-escaping); no `{@html}` or `innerHTML` usage found in the component. | closed |
| T-23-03-01 | Information Disclosure | IDOR via `argument_id` | medium | mitigate | Verified in `+page.server.ts:375-389`: `argumentId` is read from the server-side job fetch response (`job.argument_id`), never from client form data. | closed |
| T-23-03-02 | Elevation of Privilege | Accidental argument creation | high | mitigate | Verified in `+page.server.ts:391-397`: `saveJobMetadata` never calls an approve/create-argument endpoint; returns `fail(400, ...)` when `argumentId === null` — PJOB-07 enforced in code, not just by convention. | closed |
| T-23-03-03 | Tampering | `docket[]` array | low | mitigate | Verified: `dockets` are trimmed and empty-filtered (`.map(v => v.trim()).filter(Boolean)`) before the PATCH body is built; `source_docket` derives from `dockets[0]`. | closed |
| T-23-04-01 | Tampering | Empty-string sentinel in `source_docket` | low | accept | Accepted per plan; verified `values_to_set["source_docket"] = body.source_docket or None` — empty string never persisted to DB. | closed |
| T-23-04-02 | Information Disclosure | Removed "View Source PDF" card | low | accept | Accepted per plan — card removed from UI; the underlying `/admin/pipeline/[id]/pdf` route is untouched and remains admin-gated. | closed |
| T-23-04-03 | Denial of Service | `svelte-check` failure leaving page broken | low | mitigate | Plan 23-04's Task 5 ran `svelte-check` as a mandatory completion gate — 0 errors reported in 23-04-SUMMARY.md. | closed |
| T-23-05-01 | Tampering | `addPill()` client guard | low | accept | Accepted per plan — client guard is UX convenience only; the authoritative server-side CR-02 guard in `+page.server.ts` is unchanged by this plan. | closed |
| T-23-07-01 | Tampering | `saveJobMetadata` `source_dockets` input | medium | mitigate | Verified in `api/services/admin_arguments.py:548-559`: array is stripped, empty-filtered, and order-preserving-deduplicated before write; `MetadataUpdate` remains a strict allowlist. | closed |
| T-23-07-02 | Denial of Service | Unbounded docket array | low | accept | Accepted per plan — consolidated cases have a handful of dockets, each `String(50)`; authenticated offline operator tool behind `X-Admin-Token`, no practical abuse vector. | closed |
| T-23-07-03 | Tampering | Dedup constraint bypass via array | medium | mitigate | Verified in `api/services/admin_arguments.py:558-559`: `source_docket` (the `UNIQUE(source_docket, question_number)` key) is kept in sync with `normalized[0]`, so multi-docket support cannot introduce duplicate primary-docket arguments. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

*Supply-chain check: `git show --stat` across all Phase 23 commits shows zero changes to `requirements.txt`, `package.json`, or `pyproject.toml` — no new packages installed in this phase.*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-23-01 | T-23-02-01 | Client is not a trust boundary for persistence — server-side validation is authoritative. | Plan 23-02 (authored) | 2026-07-03 |
| AR-23-02 | T-23-04-01 | Empty-string sentinel is a deliberate server-side convention, converted to `None` before write; operator-facing only. | Plan 23-04 (authored) | 2026-07-04 |
| AR-23-03 | T-23-04-02 | Removed UI card reduces surface area; underlying admin-gated route untouched. | Plan 23-04 (authored) | 2026-07-04 |
| AR-23-04 | T-23-05-01 | Client-side pill guard is UX convenience only; authoritative server guard (CR-02) unchanged. | Plan 23-05 (authored) | 2026-07-04 |
| AR-23-05 | T-23-07-02 | Unbounded docket array has no practical abuse vector for an authenticated single-operator offline tool. | Plan 23-07 (authored) | 2026-07-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-07 | 15 (T-23-01..03, T-23-02-01/02, T-23-03-01..03, T-23-04-01..03, T-23-05-01, T-23-07-01..03) | 15 | 0 | Claude (orchestrator, L1 grep-depth verification — short-circuit per ASVS level 1, register authored at plan time for 6/7 plans) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-07
