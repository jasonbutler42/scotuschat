---
phase: 24
slug: pipeline-list-page
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-07
---

# Phase 24 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| SvelteKit server → FastAPI | `X-Admin-Token` header on `/api/admin/*` | Admin auth token |
| Operator browser → SvelteKit form | Operator-entered docket strings serialized as `docket[]` form values | Docket identifiers |
| Operator browser → SvelteKit action → FastAPI `POST /api/admin/jobs` | Full ordered docket list + free-text question number forwarded with admin token | Docket list, question number |
| Browser → SvelteKit check-duplicate proxy | Per-pill duplicate preflight (same-origin, token injected server-side) | Docket string |
| FastAPI `_normalize_dockets` → subprocess argv | Normalized docket strings become `python -m pipeline ingest` process arguments | Docket strings as CLI argv |
| Spawned ingest subprocess → `admin_jobs` table (Postgres) | The child process is the sole writer of job status; a crash before this write leaves the job in a stale state | Job status, error message |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-24-01 | Denial of Service | `GET /api/admin/jobs` (unbounded result set) | low | accept | Accepted per plan — operator-only endpoint behind admin token; run volume is small (single operator, tens–hundreds of rows). | closed |
| T-24-02 | Tampering | Docket pill values (operator input) | low | accept | Accepted per plan — values stored as-is with no SQL string interpolation, rendered as text; downstream validated (V5). | closed |
| T-24-03 | Tampering | `ArgumentDetailsCard` save (regression risk from `DocketPillInput` refactor) | low | mitigate | Plan 24-03's `svelte-check` completion gate + focused failed-save acceptance criteria passed (per 24-03-SUMMARY.md); `docket[]` serialization contract and `reset:false` enhance pattern preserved. | closed |
| T-24-04 | Spoofing / Access Control | `POST /api/admin/jobs` via action | low | accept | Accepted per plan — existing `X-Admin-Token` injection in the server action is unchanged; repeated `source_dockets` travel through the same trusted server-side path (V4). | closed |
| T-24-05 | Input Validation | `question_number` free text | low | mitigate | Verified in `api/routers/admin.py:201`: `question_number: int = Form(1)` — FastAPI/Pydantic coerces and returns 422 on unparseable input before the value reaches argv or DB. | closed |
| T-24-06 | Tampering | Duplicate-preflight fail-open on error | low | accept | Accepted per plan — preflight is UX convenience only; on error it fails open and submits. The authoritative duplicate guard remains server-side (unchanged `UNIQUE(source_docket, question_number)` constraint). | closed |
| T-24-07 | Data Integrity | Run-start docket list | medium | mitigate | Verified in `api/routers/admin.py:222-306` and `pipeline/commands/ingest.py:398-406`: router normalizes/dedupes `source_dockets` and stores the ordered list on `admin_jobs`; ingest writes both `Argument.source_docket` (dedup key) and `Argument.source_dockets` (full list) in the same transaction, kept in sync. | closed |
| T-24-08 | Tampering | `_normalize_dockets` → subprocess argv (`api/routers/admin.py`) | high | mitigate | Closed by Plan 24-05. Independently verified three times this session (code review + phase verifier + direct trace): `_normalize_dockets` (`admin.py:111-149`) rejects any docket value whose stripped form begins with `-` via `HTTPException(422)`, raised inside the nested `_add()` helper, strictly before `jobs_service.create_job`/subprocess spawn in every branch. No bypass via `rerun_job` (reads already-normalized `source_dockets`) or the metadata-PATCH route (writes only `Argument.source_dockets`, never read by `spawn_pipeline_step`). | closed |
| T-24-09 | Denial of Service (availability) | Spawned ingest subprocess exit before `run_ingest` (`pipeline/__main__.py`, DEVNULL stdio) | high | mitigate | Closed by Plan 24-05. Independently verified three times this session: `pipeline/__main__.py:240-258` wraps `parser.parse_args()` in `try/except SystemExit`; on a truthy non-zero exit code, scrapes `--job-id` from argv and writes a best-effort `AdminJobStatus.FAILED` before re-raising. Runs entirely inside the child process — `api/services/pipeline_spawn.py` confirmed byte-for-byte unchanged (fire-and-forget invariant D-01 intact). | closed |
| T-24-10 | Information disclosure / log-injection | `_write_early_failure` message + `error_message` column | low | mitigate | Closed by Plan 24-05. Verified: the guard writes only a fixed diagnostic string plus `exc.code` (an int) — no operator-supplied argv token is echoed into `error_message`; message additionally sliced to `[:500]` before the DB write. `_scrape_job_id` parses only the integer job-id and discards all other argv. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on (high) count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

*Supply-chain check: `git show --stat` across all Phase 24 commits shows zero changes to `requirements.txt`, `package.json`, or `pyproject.toml` — no new packages installed in this phase.*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-24-01 | T-24-01 | Unbounded admin-only endpoint; run volume is small for a single-operator tool. Reintroduce pagination if volume grows (plan D-12). | Plan 24-01 (authored) | 2026-07-06 |
| AR-24-02 | T-24-02 | Docket pill values stored/rendered as plain text; no injection surface. | Plan 24-02 (authored) | 2026-07-06 |
| AR-24-03 | T-24-04 | Existing `X-Admin-Token` server-side injection unchanged by this plan. | Plan 24-04 (authored) | 2026-07-07 |
| AR-24-04 | T-24-06 | Duplicate preflight is UX convenience; authoritative guard is the server-side UNIQUE constraint. | Plan 24-04 (authored) | 2026-07-07 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-07 | 10 (T-24-01..10) | 10 | 0 | Claude (orchestrator, L1 grep-depth verification — short-circuit per ASVS level 1, register authored at plan time for all 5 plans). T-24-08/09/10 additionally cross-verified by a separate code-review agent and a separate phase-verifier agent earlier in this session. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-07
