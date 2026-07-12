---
phase: 27
slug: people-admin
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-09
---

# Phase 27 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| operator CLI → database (DDL) | Alembic migration 0016 alters the `people` table schema | schema-only, no data |
| API request body → ORM write | `PersonUpdate` / `PersonCreateRequest` fields become `Person`/`CourtTenure` column writes | operator-submitted person/tenure fields |
| unauthenticated client → `POST /people` | New create-person endpoint (D-09) — the phase's primary new attack surface | full_name, is_justice |
| SvelteKit server load → FastAPI query params | `tab`/`missing`/`tenure_gaps` arrive as untrusted strings | URL query params |
| browser form → SvelteKit save/create actions | full_name / name parts / birthdate / tenures JSON / is_justice (untrusted) | operator-submitted form fields |
| SvelteKit action → FastAPI (server-only) | Forwarded as JSON behind admin auth; `FASTAPI_BASE_URL` and admin token never reach the client bundle | JSON body + server-only admin token |
| SvelteKit soft navigation → reused component instance | Person-id-change reset `$effect` keeps per-person client `$state` correct across soft navigations (CR-01/CR-02, and the 27-11 loop fix) | client-side reactive state only |
| operator browser (client-side reactivity) → Svelte 5 effect scheduler | Client-side availability boundary — an unbounded reactive read+write cycle inside an effect (27-11) | none (runtime scheduler behavior, not data) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-27-01 | Tampering | `PersonUpdate`/`PersonCreateRequest` mass-assignment | high | mitigate | Explicit-field allow-list discipline (T-09-01); `birthdate` added as a declared field only | closed |
| T-27-05 | Spoofing / Broken Auth | `POST /people` | high | mitigate | Same admin-auth `Depends(...)` as every other `/admin/people*` route; no new/weaker auth path | closed |
| T-27-06 | Elevation of Privilege (IDOR) | `POST /people` | high | mitigate | No cross-entity linkage on create — no object reference exists to confuse; admin boundary is sufficient | closed |
| T-27-09 | Information Disclosure | `FASTAPI_BASE_URL` / admin token | high | mitigate | All API calls stay in `+page.server.ts`; no `PUBLIC_` env leak (CLAUDE.md architecture rule 2) | closed |
| T-27-13 | Spoofing / Broken Auth | create action → `POST /people` | high | mitigate | Server-only `X-Admin-Token` attached; FastAPI route enforces same admin-auth dependency | closed |
| T-27-14 | Information Disclosure | admin token exposure | high | mitigate | Token used only in `+page.server.ts`; never shipped to client bundle | closed |
| T-27-10-01 | Tampering (integrity / data destruction) | `[id]/+page.svelte` save-form + `_replace_tenures` write path | high | mitigate | CR-01/CR-02 fix (Plan 27-10): data-carrying inputs relocated outside conditional; reset effect completed. Independently re-verified intact by this pass's code review and phase verification | closed |
| T-27-11-01 | Denial of Service (client-side, self-inflicted) | `[id]/+page.svelte` person-id-change `$effect` | high | mitigate | `effect_update_depth_exceeded` infinite loop (introduced by 27-10) fixed by Plan 27-11: reactive `nextKey++` read+write replaced with local non-reactive counter, write-only `nextKey` assignment. Independently re-traced and confirmed correct by this pass's code review and phase verification | closed |
| T-27-03 | Tampering | `missing` query param / free-text appointment fields | medium | mitigate | Allow-listed query params (never interpolated into SQL); SQLAlchemy parameterizes all writes; Svelte auto-escapes render | closed |
| T-27-08 | Tampering | `missing`/`tab` URL params (frontend) | medium | mitigate | Forwarded as opaque strings to FastAPI's allow-list; never interpolated into HTML sinks | closed |
| T-27-10 | Tampering | disabled Death Date / Reason Left inputs | medium | mitigate | Disabled inputs submit no value AND backend schema declares no matching field — no silent-drop illusion (D-19) | closed |
| T-27-11 | Tampering | `tenures` JSON hidden field | medium | mitigate | Server re-parses JSON, maps only allow-listed keys into `TenureRow`; dates parsed via `fromisoformat` (ValueError→422); no extra keys reach the ORM | closed |
| T-27-12 | Cross-Site Scripting | free-text appointment/name/bio fields | medium | mitigate | Svelte auto-escapes all interpolated text; no `{@html}` sink introduced | closed |
| T-27-11-02 | Tampering (regression risk) | person-id-change `$effect` block (27-11) | medium | mitigate | Fix scoped to only the counter mechanism; CR-01/CR-02 statements left byte-for-byte unchanged; verify gates assert field-mapping intact. Confirmed by code review and phase verification | closed |
| T-27-08-01 | Tampering | `PersonCreateRequest` name-part fields | low | mitigate | Only the four explicitly-declared `Optional[str]` name-part fields added to the allow-list (T-09-01 discipline) | closed |
| T-27-02 | Denial of Service | 0016 migration on large `people` table | low | accept | Additive nullable column, no backfill, no table rewrite — negligible lock time | closed |
| T-27-04 | Information Disclosure | `argument_count` / list rows | low | accept | Admin-only route behind existing admin-auth boundary; no PII beyond existing directory exposure | closed |
| T-27-07 | Denial of Service | bulk junk-record creation via minimal D-08 validation | low | accept | Behind admin auth (single trusted operator); records mergeable/deletable via existing tools | closed |
| T-27-07-01 | Tampering | `+page.svelte` padding edit (27-07) | low | accept | Padding-only CSS change; no logic, data, or auth surface touched | closed |
| T-27-08-02 | Elevation of Privilege | `POST /api/admin/people` | low | accept | Endpoint inherits router-level admin-auth dependency (D-09); no new endpoint or auth surface | closed |
| T-27-09-01 | Tampering | `appointing_president_party` value (27-09) | low | accept | Free-text column by design; `<select>` narrows UI only, no new validation surface removed/added | closed |
| T-27-09-02 | Information Disclosure | curated party list (27-09) | low | accept | Public historical fact, not confidential customer/pricing data | closed |
| T-27-10-02 | Denial of Service | client-side `$effect` re-derivation (27-10) | low | accept | Re-maps a small, bounded tenure array on person-id change only; no unbounded loop | closed |
| T-27-SC | Tampering | npm/pip/cargo installs (all plans) | high | accept | No new dependencies installed anywhere in this phase (Svelte `slide`/`fromisoformat` are built-in); no Package Legitimacy Audit required | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-27-01 | T-27-SC | No new dependencies installed anywhere in Phase 27 — supply-chain checkpoint does not apply | Plan authors (27-01 through 27-11) | 2026-07-09 |
| AR-27-02 | T-27-02, T-27-04, T-27-07, T-27-07-01, T-27-08-02, T-27-09-01, T-27-09-02, T-27-10-02 | Low-severity, admin-only-boundary or non-data-flow risks; residual risk accepted within the existing admin trust boundary | Plan authors (27-01 through 27-10) | 2026-07-09 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-09 | 24 | 24 | 0 | gsd-secure-phase (State B, plan-time register; short-circuited — threats_open: 0, register_authored_at_plan_time: true, asvs_level: 1) |

**Note (out-of-scope, tracked separately):** This phase's code review (`27-REVIEW.md`) surfaced one new Critical finding — `CourtTenure` rows are unaccounted for in the merge/delete FK bookkeeping in `api/services/admin_people.py`, causing an unhandled `IntegrityError` when merging/deleting a Bench person with tenure rows. The `CourtTenure` table and merge/delete logic predate Phase 27 (Phase 22), and no Phase 27 plan's threat model covers merge/delete paths — Phase 27's phase verification (`27-VERIFICATION.md`) assessed this as out of this phase's declared scope. It is not added to this register; recommend a standalone backlog item with its own threat assessment when addressed.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-09
