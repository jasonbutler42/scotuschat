---
phase: "09"
slug: people-data-model-migration
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-22
---

# Phase 09 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Admin API → PostgreSQL | PATCH /api/admin/people/{id} writes six new nullable columns via SQLAlchemy ORM | Structured name parts + appointment metadata (public record, admin-only write path) |
| SvelteKit server action → FastAPI | FormData extracted in +page.server.ts, JSON-serialized, sent to FastAPI PATCH endpoint | Six new form fields; FASTAPI_BASE_URL server-only |
| Browser → SvelteKit server | Form submission via use:enhance; no client-side fetch to API | Plain HTML form values (text + select) |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-09-01 | Tampering (mass assignment) | `PersonUpdate` schema | mitigate | Only the six explicitly-declared fields are writable; PATCH cannot set arbitrary Person attributes (`id`, `role_name`, etc.). Six fields added to allow-list deliberately and minimally. Verified: no extra writable surface introduced. | closed |
| T-09-02 | Tampering (DDL bypass) | migration 0006 | mitigate | DDL goes exclusively through Alembic `op.add_column`; `Base.metadata.create_all` forbidden and grep-verified absent from all three plan-01 files. | closed |
| T-09-03 | Denial of data integrity | `full_name` resolution anchor | mitigate | Migration does not touch `full_name`; ORM keeps `full_name nullable=False`; new columns are additive-only. Full_name derivation gated on both first_name AND last_name non-empty (D-05 / Pitfall 3) to prevent anchor corruption from partial saves. | closed |
| T-09-04 | Information disclosure | `appointing_president_party` | accept | Field is admin-only; `PersonDetail` returned only by admin-authed `GET /api/admin/people/{id}`. No public read path introduced this phase. No PII beyond already-stored public-record names. | closed |
| T-09-05 | Tampering (data integrity) | `update_person` derivation | mitigate | Derivation gated on BOTH `first_name` AND `last_name` (Phase 9 plan-02 deviation from D-04 literal); partial save can never overwrite a valid full_name anchor. | closed |
| T-09-06 | Repudiation / data quality | empty-string normalization | mitigate | `if body.field else None` normalization applied to all six new fields; stores NULL not `''`, keeping IS NULL completeness filters honest. | closed |
| T-09-07 | Information disclosure | `get_person_detail` return dict | accept | Returned only via admin-authed `GET /api/admin/people/{id}`; six fields are public-record metadata, no new PII beyond names already stored. | closed |
| T-09-08 | Information disclosure | `FASTAPI_BASE_URL` env var | mitigate | Imported only from `$env/static/private`; never `PUBLIC_`; grep-verified absent in plan-03 Task 1 automated check. | closed |
| T-09-09 | Elevation / IDOR | person id route param | accept | Admin section gated by HMAC session cookie in `hooks.server.ts` (Phase 6). Any authenticated operator may edit any person by design — single trusted operator role. No per-record ownership model required. | closed |
| T-09-10 | Tampering (form injection) | six text/select inputs | mitigate | Values flow through Pydantic `PersonUpdate` (string fields) and written via SQLAlchemy parameterized statements (no string-built SQL). Party value constrained in UI select. Svelte escapes interpolated values on render, mitigating stored-XSS on reload. | closed |
| T-09-SC | Tampering (supply chain) | npm/pip/cargo installs | accept | No package installs in Phase 9. No new dependencies introduced across any of the three plans. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-01 | T-09-04 | appointing_president_party is public-record metadata; admin-only access path; no PII. Public read path deferred to Phase 14. | operator | 2026-06-22 |
| AR-09-02 | T-09-07 | get_person_detail six new fields are public-record metadata returned only via admin-authed endpoint. | operator | 2026-06-22 |
| AR-09-03 | T-09-09 | Single trusted operator role; any authenticated operator may edit any person by design. No per-record ownership required. | operator | 2026-06-22 |
| AR-09-04 | T-09-SC | No new packages introduced in Phase 9; supply chain risk is not applicable. | operator | 2026-06-22 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-22 | 11 | 11 | 0 | gsd-secure-phase (short-circuit: register_authored_at_plan_time=true, threats_open=0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-22
