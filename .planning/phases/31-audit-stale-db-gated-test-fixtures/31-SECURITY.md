---
phase: 31
slug: audit-stale-db-gated-test-fixtures
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-13
---

# Phase 31 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Provisioning/reset tooling → PostgreSQL | Test setup creates and destructively resets a dedicated database on infrastructure that may also host the shared dev DB | Database URLs, DDL, and test records |
| Test process environment → application configuration | Root pytest configuration redirects production-style database settings to the dedicated test DB | `DATABASE_URL` and `TEST_DATABASE_URL` |
| Leak detector → shared dev DB | Session hooks take read-only row-count snapshots before and after the suite | Aggregate `people` and `arguments` counts |
| Cleanup operator/script → shared dev DB | An explicitly authorized maintenance command updates/deletes identified leaked rows | Person, argument, and dependent FK records |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-31-01 | Tampering | `_reset_test_db` and provisioning | high | mitigate | Reset reads `TEST_DATABASE_URL` directly and no-ops unless its database is exactly `scotus_test`; provisioning rejects `postgres` and the configured dev database name. | closed |
| T-31-02 | Tampering | Cleanup execution | high | mitigate | Dry-run is default; execute requires an explicit flag and confirmation, re-detects candidates inside one transaction, and uses targeted UPDATE/DELETE operations only. | closed |
| T-31-03 | Information disclosure | Test DB target | high | mitigate | The committed example points to local `scotus_test`, explicitly forbids remote/shared hosts, and runtime guards require the dedicated database name; live credentials remain uncommitted. | closed |
| T-31-04 | Information disclosure | Test credentials | medium | mitigate | Only a placeholder test URL is committed in `.env.example`; real values remain in the gitignored environment file. | closed |
| T-31-05 | Tampering | Dev-DB leak monitor | high | mitigate | `_REAL_DATABASE_URL` is captured before any test-DB override, and both leak hooks use that preserved value. | closed |
| T-31-06 | Repudiation | Leak-hook skip behavior | medium | mitigate | Hooks no-op only for an unset/recognized-placeholder URL; configured runs perform mandatory before/after comparisons. | closed |
| T-31-07 | Denial of service | Leak-hook connection | low | mitigate | One-shot COUNT connections use `statement_cache_size: 0` and are disposed immediately after each snapshot. | closed |
| T-31-08 | Tampering | Fixture consolidation | medium | mitigate | The seven duplicate fixture definitions were compared before removal; consolidation results and deviations are recorded in the plan summary. | closed |
| T-31-09 | Denial of service | Fixture removal | low | mitigate | Collection gates verified fixture resolution after consolidation. | closed |
| T-31-10 | Tampering | Cleanup target selection | high | mitigate | Cleanup refuses unset/placeholder `DATABASE_URL` values, deliberately targets the reviewed shared-dev dataset, and destructive execution was held behind the Phase 31 operator checkpoint. | closed |
| T-31-11 | Tampering | Duplicate-person survivor selection | high | mitigate | Survivor selection prefers tenure/bio-backed rows; dependent FKs are reassigned before deletion; the reviewed dry-run and live execution confirmed the chosen survivors. | closed |
| T-31-12 | Tampering | API fixture repairs | high | mitigate | API test fixes did not weaken production schema/models; test data was corrected and genuine stale-identity bugs were fixed with targeted refreshes. | closed |
| T-31-13 | Repudiation | API skips/xfails | medium | mitigate | Existing skips/xfails and all deviations are explained in `31-05-SUMMARY.md`; failures were not silently masked. | closed |
| T-31-14 | Tampering | Pipeline fixture repairs | high | mitigate | Pipeline fixture fixes preserved production schema constraints; production changes were limited to documented correctness fixes. | closed |
| T-31-15 | Repudiation | Pipeline skips/xfails | medium | mitigate | Known stubs, skips, and out-of-scope findings are documented in `31-06-SUMMARY.md` and `deferred-items.md`. | closed |
| T-31-16 | Repudiation | Full-suite isolation | high | mitigate | The full suite completed 429 passed / 5 documented xfailed with the shared-dev leak hook active and silent across repeated runs. | closed |
| T-31-17 | Tampering | Inner-commit regression coverage | medium | mitigate | The regression test relies on the always-on session-level dev-DB count comparison, preventing a per-test omission from hiding leakage. | closed |
| T-31-18 | Tampering | Authorized shared-DB cleanup | high | mitigate | The operator reviewed the verbatim dry-run, authorized the exact 81-row candidate set, and execution retained confirmation plus transactional re-detection. | closed |
| T-31-19 | Repudiation | Cleanup auditability | medium | mitigate | `31-08-SUMMARY.md` records the dry-run report, authorization scope, command, re-detection result, and deletion outcome. | closed |
| T-31-20 | Denial of service | Post-cleanup import | medium | mitigate | `import-justices` and the full pytest suite completed cleanly after cleanup; follow-up counts remained stable at 333 people / 163 arguments. | closed |
| T-31-SC | Tampering | Dependency supply chain | low | accept | Phase 31 installed no new packages; existing asyncpg, SQLAlchemy, Alembic, and pytest dependencies were reused. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-31-01 | T-31-SC | No dependency installation or version change occurred; existing project dependencies were reused. | Phase 31 plans 01–08 | 2026-07-13 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-13 | 21 | 21 | 0 | Codex (L1/ASVS-1 short-circuit — plan-time STRIDE register verified against implementation and execution summaries) |

## Security Audit 2026-07-13

| Metric | Count |
|--------|-------|
| Threats found | 21 |
| Closed | 21 |
| Open | 0 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-13
