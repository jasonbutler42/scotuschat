---
phase: 22
slug: schema-foundations
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-07
---

# Phase 22 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Alembic migration 0012 → production DB | DDL (enum expansion + new table) and a bulk backfill INSERT run against existing argument rows | Argument status values, timestamps |
| ORM model ↔ PG enum type | The ORM `status` column on `argument_status_log` must bind to the existing `argument_status` type, not create a shadow type | Enum type identity |
| Alembic migration 0013 → production DB | DDL drops two `people` columns and adds three columns across `court_tenures`/`argument_participants`; irreversible data loss on the dropped columns | Justice appointment metadata |
| ORM model ↔ live DB schema (post-0013) | A mismatch (ORM still referencing a dropped column) crashes every query touching `Person` | Person/CourtTenure column shape |
| PDF file → TOC parser | Untrusted/variable transcript text is parsed for the TOC subtitle line | Extracted title text |
| Parser output → DB write | Extracted title strings are written to `argument_participants.title` | Title text (public transcript content) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-22-01 | Denial of Service | Migration 0012 upgrade on existing data | medium | mitigate | Verified in `alembic/versions/0012_*.py`: backfill is a single set-based `INSERT...SELECT` (no per-row loop); `ALTER TYPE ... ADD VALUE IF NOT EXISTS` makes the enum expansion idempotent against a partial/re-run upgrade. | closed |
| T-22-02 | Tampering | Backfill status literal | high | mitigate | Verified: backfill casts `status::argument_status` from each argument's real column value — no hardcoded literal (e.g. `'created'`) is used anywhere in the migration. | closed |
| T-22-03 | Repudiation | `argument_status_log` audit trail (no actor attribution) | low | accept | Accepted per plan D-06 — operator-only offline admin tool with a single trusted operator; per-actor attribution out of scope for v1.5. | closed |
| T-22-04 | Denial of Service | ORM/service references to dropped `people` columns | high | mitigate | Verified: `grep -rn "appointing_president"` across the codebase shows zero references on the `Person` model; `CourtTenure` (api/models/models.py:135-136) now owns `appointed_by`/`appointing_president_party`. `api/services/speakers.py:199` returns `"appointing_president": None` (a documented functional deferral to Phase 27, not a crash) rather than raising `AttributeError`. | closed |
| T-22-05 | Tampering | Migration 0013 downgrade | medium | mitigate | Verified: `downgrade()` in `alembic/versions/0013_*.py` restores both dropped `people` columns as nullable and drops the three added columns in reverse order — self-consistent schema on rollback. | closed |
| T-22-06 | Information Disclosure | Removed person-level appointment data | low | accept | Accepted per plan D-08 — dropped data was known test/incorrect data; no real appointment data lost. | closed |
| T-22-07 | Denial of Service | `extract_toc_data`/`_parse_toc_titles` on malformed PDFs | medium | mitigate | Verified in `pipeline/parser/cover_extractor.py:349-360`: the entire extraction is wrapped in `try/except Exception: pass`, returning `{"sides": {}, "titles": {}}` on any failure. Never raises. | closed |
| T-22-08 | Tampering | `title` string length | low | accept | Accepted per plan — `title` column is `VARCHAR(500)`; DB enforces the bound. Real TOC subtitle lines are short; over-length is not a realistic case. | closed |
| T-22-09 | Information Disclosure | `title` reflects only TOC public text | low | accept | Accepted per plan — title is verbatim public transcript text; no derived insight or PII beyond the immutable source PDF, consistent with the apolitical/identical-treatment constraint. | closed |
| T-22-SC | Tampering | npm/pip/cargo installs (22-01, 22-02, 22-03) | high | mitigate | Verified: `git show --stat` across all Phase 22 commits shows zero changes to `requirements.txt`, `package.json`, or `pyproject.toml`. No new packages installed in this phase. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-22-01 | T-22-03 | No `triggered_by`/actor column on `argument_status_log` — single-operator offline admin tool, per-actor attribution out of scope for v1.5 (plan D-06). | Plan 22-01 (authored) | 2026-07-02 |
| AR-22-02 | T-22-06 | Dropped `people.appointing_president`/`appointing_president_party` data was known test/incorrect; no real appointment data lost (plan D-08). | Plan 22-02 (authored) | 2026-07-02 |
| AR-22-03 | T-22-08 | `title` VARCHAR(500) DB constraint is sufficient; over-length TOC subtitles are not a realistic case. | Plan 22-03 (authored) | 2026-07-02 |
| AR-22-04 | T-22-09 | Extracted title is verbatim public transcript text — no PII/derived-insight exposure beyond the source PDF. | Plan 22-03 (authored) | 2026-07-02 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-07 | 10 (T-22-01..09, T-22-SC) | 10 | 0 | Claude (orchestrator, L1 grep-depth verification — short-circuit per ASVS level 1, register authored at plan time) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-07
