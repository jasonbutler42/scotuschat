---
phase: 28
slug: dashboard
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-11
---

# Phase 28 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| SvelteKit server `load()` → FastAPI `/api/admin/*` | Server-to-server; authenticated via `X-Admin-Token` header (`verify_admin_token` router dependency). No end-user input reaches these service functions. | Aggregate stat counts, incomplete-people/tenure-gap/draft lists |
| Postgres ← aggregation queries | New read-only COUNT/MAX/LIMIT queries; no client-supplied predicates. | Aggregate counts only |
| Browser → SvelteKit server `load()` | Authenticated operator session (gated by Phase 6 `hooks.server.ts`); `load()` adds no client-controlled input. | Rendered dashboard HTML only |
| `+page.server.ts` → `+page.svelte` | `FASTAPI_BASE_URL`/`ADMIN_TOKEN` imported from `$env/static/private`, server-only | Fetched stat/list data, never the credentials themselves |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-28-01 | Information Disclosure | New stat service functions (aggregate counts) | low | mitigate | Called only from routes under the router-level `verify_admin_token` dependency; no new auth surface; data already exposed via existing authenticated endpoints. | closed |
| T-28-02 | Denial of Service | Dashboard aggregation over corpus-scale tables (~7,800 arguments, millions of utterances) | medium | mitigate | Every count uses `func.count()`/`func.max()`/`LIMIT` at the SQL layer (verified via grep in `admin_arguments.py`, `admin_jobs.py`, `admin_people.py`); unbounded `list_*` functions are never reused for counting. | closed |
| T-28-03 | Tampering | Apolitical-field leakage into new schemas | low | mitigate | `admin_dashboard.py` schemas define only count/label fields; no `win_side`/`votes_side`/`scdb_docket_id` columns selected or returned (grep-confirmed). | closed |
| T-28-04 | Elevation of Privilege | New unauthenticated route exposure | low | mitigate | All seven routes sit under `router = APIRouter(prefix="/api/admin", dependencies=[Depends(verify_admin_token)])`; no per-route override removes it (confirmed at `api/routers/admin.py`). | closed |
| T-28-05 | Denial of Service / correctness | Route-shadowing (literal route swallowed by `{id}` route → silent 422) | medium | mitigate | Literal routes registered before `{id}` siblings; line-number ordering confirmed for all 7 routes; route test asserts 200-not-422. | closed |
| T-28-06 | Information Disclosure | IDOR on new routes | low | accept | No route accepts a client-supplied resource id; all return aggregate/global data — no per-row ownership surface exists to guard. | closed |
| T-28-07 | Input Validation | Injection via new query params | low | accept | New routes take no query params (fixed server-side 30-day constant); nothing to validate. | closed |
| T-28-08 | Information Disclosure | `FASTAPI_BASE_URL`/`ADMIN_TOKEN` leaking to the browser | high | mitigate | Both imported from `$env/static/private` in `+page.server.ts` only; never referenced in `+page.svelte` (grep-confirmed); matches Architecture Rule 2. | closed |
| T-28-09 | Denial of Service | One failed FastAPI fetch hard-erroring the whole dashboard | medium | mitigate | Each of 7 fetches wrapped in its own try/catch with a safe default; `load()` never throws. Confirmed by source (7 try/catch blocks) AND by human UAT test 2 (live load-failure test passed: page renders with N/A values, no hard error). | closed |
| T-28-10 | Tampering | Reintroducing the removed generic "incomplete" people filter via CTA | low | mitigate | People CTA/View-all hrefs land on the unfiltered `/admin/people` view; grep-confirmed no `missing=`/`incomplete=` param appended. | closed |
| T-28-SC | Tampering | npm/pip/cargo installs | low | accept | No new packages introduced across all three plans (schema/service/route/component work only, no new dependencies). | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-28-01 | T-28-06 | No client-supplied resource id on any new route — no per-row ownership surface exists to guard against IDOR. | Plan 28-02 threat model | 2026-07-11 |
| AR-28-02 | T-28-07 | New routes take fixed server-side parameters only, no query params accepted — no injection surface. | Plan 28-02 threat model | 2026-07-11 |
| AR-28-03 | T-28-SC | No new packages installed in any of the three plans. | Plans 28-01/28-02/28-03 threat models | 2026-07-11 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-11 | 11 | 11 | 0 | Claude (gsd-secure-phase, L1 grep-depth verification — register authored at plan time, short-circuit per ASVS L1 rule, no auditor spawn required) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-11
