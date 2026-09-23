---
phase: 48
slug: trust-lifecycle
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-21
---

# Phase 48 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register origin: **authored at plan time** — all 10 plans (48-01 … 48-10) carried a
`<threat_model>` block. This audit verifies the declared mitigations exist in the
implementation; it does not scan for new threats. ASVS L1 (grep-depth) per
`workflow.security_asvs_level`; blocking threshold `high` per `workflow.security_block_on`.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Alembic migration → live database | DDL executed against whichever database `DATABASE_URL` resolves to; a wrong resolution is destructive and irreversible | Schema DDL (migration 0027) |
| `api.domain.trust` → every runtime | One pure function is the sole authority for the tier vocabulary; a second copy anywhere is a silent divergence surface | Tier vocabulary / derivation rule |
| admin UI Danger Zone → `DELETE /api/admin/arguments/{id}` | Operator-triggered destructive write; the DRAFT-only gate is the authoritative server-side check | Argument + all dependent rows |
| FastAPI public routers → anonymous internet | Every byte crossing this boundary is untrusted output; an operator-facing signal leaking here breaches the project's hard apolitical constraint | Public response models (cases, utterances, speakers, people) |
| admin UI → `/api/admin/jobs/*` mutations | Operator-triggered writes gated by `X-Admin-Token`; the status guards decide whether a row is still editable | Resolve-row edits, job approval |
| `Argument.status` → five independent readers | One value read by five guards across three modules; disagreement between them is a correctness failure | Lifecycle state |
| ConvoKit corpus files / transcript PDFs → the database | Untrusted external content crossing into persisted rows; the born state and tier are the labels applied at that crossing | Transcript content, provenance |
| operator shell → offline CLI → shared database | Unauthenticated local process with full write access; its only guard is that it is not reachable over the network | Trust-tier UPDATEs |
| admin browser → SvelteKit server action → FastAPI admin API | Form data crossing into a server-side fetch; the action holds the admin token, the browser never does | `override_reason`, publish intent |
| `publish_argument` → `published_at` | The single promotion gate; everything downstream of it is public | Publication state |
| dev-only reset route → shared dev database | `reset_to_fixture` TRUNCATEs nine tables; a wrong database resolution is destructive | All fixture tables |
| the evidence record → the phase seal | What 48-EVIDENCE.md claims is what `/gsd-verify-work` believes; an unrecorded failure becomes an invisible one | Verification claims |

---

## Threat Register

40 distinct threats across 10 plans. `T-48-SC` and `T-48-10-SC` are the same
supply-chain threat and are merged into one row; `T-48-LEAK`, `T-48-STALETIER`,
`T-48-CLIHTTP`, and `T-48-TOKEN` each appear in more than one plan and are
recorded once with all owning plans listed.

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-48-DDL | Tampering | `alembic upgrade head` for migration 0027 (48-01) | high | mitigate | `api/alembic/versions/0027_trust_tier_and_candidate_status.py` present and applied; Task 1 precondition asserted `alembic current == 0026 (head)` and echoed the resolved database name before upgrading (Phase 47 T-47-01 guard shape) | closed |
| T-48-DUP | Tampering | trust vocabulary duplicated in SQL or PL/pgSQL (48-01) | medium | mitigate | No `CREATE TRIGGER` / `plpgsql` anywhere in `api/` or `pipeline/`; no `trust_tier` computation in `api/alembic/`. `min()` computed in Python over `derive_tier` output in `api/services/trust.py` only | closed |
| T-48-CONTENT | Information Disclosure | trust derivation reading content fields (48-01) | medium | mitigate | `api/services/trust.py:68-75` selects exactly `Utterance.person_id`, `Utterance.is_stage_direction`, `ImportRun.source`, `ImportRun.method` — no `Utterance.text`, no `raw_speaker_label`, no `Person`/`Case` column | closed |
| T-48-DELGATE | Elevation of Privilege | `delete_argument`'s status gate (48-02) | high | mitigate | `api/services/admin_arguments.py:850-855` — single positive DRAFT-only gate; CANDIDATE (born state), PUBLISHED, UNPUBLISHED and the retired PIPELINE value all rejected. Locked by `test_delete_argument_still_refuses_candidate` | closed |
| T-48-DELORPHAN | Denial of Service | `delete_argument` FK cascade ordering (48-02) | medium | mitigate | `ArgumentStatusLog` delete lands at Step 5 (`admin_arguments.py:919-925`) — after child-row deletes, before the Step 7 `Argument` delete. FK is NOT NULL with no `ondelete` (RESTRICT, D-22) | closed |
| T-48-LEAK | Information Disclosure | public response models and the four public routes (48-03 / 48-07 / 48-08 / 48-09) | high | mitigate | `api/tests/test_trust_public_leak_ban.py` — structural ban over every model reachable from a public `response_model=`, plus recursive live-body assertions and `test_public_schema_modules_never_import_trust_tier` | closed |
| T-48-LEAKFUTURE | Information Disclosure | a public route added after this phase (48-03) | medium | mitigate | `_derive_public_response_models()` (`test_trust_public_leak_ban.py:99-124`) reads the live routers rather than a hardcoded list, so an uncovered new public route fails the test instead of passing unnoticed | closed |
| T-48-VACUOUS | Repudiation | the leak-ban test itself (48-03) | medium | mitigate | `test_public_model_derivation_is_non_empty` (line 179) plus `test_admin_detail_contract_does_declare_trust_tier` (line 210) — the ban cannot pass because nothing anywhere declares the field | closed |
| T-48-GUARD | Denial of Service | `update_resolve_row_for_job` / `list_resolve_rows_for_job` editability gates (48-04) | high | mitigate | Gates keyed on the born state at `api/services/admin_jobs.py:285`, `:719`, `:825`; completeness grep across `api/`, `pipeline/`, `scripts/`, `app/src` found no missed comparison | closed |
| T-48-GUARDUI | Denial of Service | job detail page `readonlyMode` (48-04) | high | mitigate | `app/src/routes/admin/pipeline/[job_id]/+page.server.ts:294` — `argument.status !== 'candidate'`; the TypeScript literal outside RESEARCH.md's Python-only inventory was swapped | closed |
| T-48-STALETIER | Tampering | recompute placed after commit / outside the session block (48-04 / 48-05) | high | mitigate | All `recompute_argument_tier` call sites precede their writer's commit (`admin_arguments.py:665,786,828`; `admin_jobs.py:545,615`). End-to-end falsifier in 48-EVIDENCE.md §4: `recompute-trust --all` reports `4 scanned, 4 unchanged, 0 changed`, reproduced twice | closed |
| T-48-DOUBLEAPPROVE | Elevation of Privilege | `approve_job` double-approve guard (48-04) | medium | mitigate | Guard swapped, not removed — `api/services/admin_jobs.py:591`; `test_approve_job_accepts_freshly_created_argument_and_rejects_second_call` asserts both halves | closed |
| T-48-CANDLEAK | Information Disclosure | `/admin/arguments` list and stats (48-04) | low | accept | Positive allow-list `status.in_([DRAFT, PUBLISHED, UNPUBLISHED])` in `list_arguments` (`admin_arguments.py:107-111`) and `get_argument_stats` (`:155-159`), plus a `valid_status_values` allow-list on the filter param — the new member is excluded with no code change (D-04). Phase 49 owns candidate visibility. See AR-02 | closed |
| T-48-BORNDEFAULT | Tampering | the two birth write sites (48-05) | high | mitigate | Corpus site carries the explicit kwarg (`pipeline/commands/import_convokit.py:522`); PDF site (`pipeline/commands/ingest.py:507,525`) carries no `status` kwarg and inherits the model default. Locked by `test_corpus_argument_is_born_candidate` | closed |
| T-48-BIRTHTXN | Tampering | born-state status-log row written outside the birth transaction (48-05) | high | mitigate | `import_convokit.py` uses `await session.flush()` only — no `session.commit()` anywhere in the birth path (comment at `:651` records the invariant); both writes are `session.add(...)` on the post-flush success path | closed |
| T-48-REIMPORT | Tampering | corpus re-import clobbering an existing row (48-05) | medium | mitigate | Idempotent-SKIP early return preserved at `import_convokit.py:488-493` (`counters["skipped_existing"]`), dedup on `oyez_transcript_id` (D-08); locked by `test_corpus_reimport_adds_no_second_birth_row` | closed |
| T-48-CLIHTTP | Elevation of Privilege | pipeline commands / `recompute-trust` exposed over HTTP (48-05 / 48-06) | high | mitigate | `pipeline/commands/recompute_trust.py` has no FastAPI/APIRouter import (only a docstring mention); the sole `recompute` string in `api/routers/` is a docstring at `admin.py:1148`. Reachable via `python -m pipeline` only (CLAUDE.md); recorded as a `must_haves.prohibitions` entry | closed |
| T-48-CLIDRIFT | Tampering | a CLI that re-derives tiers with its own logic (48-06) | high | mitigate | `pipeline/commands/recompute_trust.py:32` imports `recompute_argument_tier` from `api.services.trust` — the drift check cannot itself be the drift | closed |
| T-48-CLIWIPE | Denial of Service | `--all` writing against the wrong database (48-06) | medium | mitigate | No TRUNCATE, DELETE, DROP, or ALTER in the command — per-argument `UPDATE ... SET trust_tier` through the shared service only; `--dry-run` lets the operator inspect first; `pipeline/db.py` resolves `DATABASE_URL` as every other offline command does | closed |
| T-48-CLIVACUOUS | Repudiation | a zero-changed report that means "nothing was scanned" (48-06) | medium | mitigate | `recompute_trust.py:77-107` reports `scanned` / `unchanged` / `changed` separately; `test_recompute_all_on_empty_database_reports_zero` locks the distinction | closed |
| T-48-PUBGATE | Elevation of Privilege | the two publish gates (48-07) | high | mitigate | `admin_arguments.py:609-629` — `resolved_at IS NULL` is a non-overridable completeness precondition evaluated ahead of the trust gate and taking no override; `test_publish_blocked_when_resolve_incomplete_even_with_override_reason` asserts the behaviour (D-14, ASVS V4) | closed |
| T-48-REASON | Tampering | `override_reason` validation (48-07) | high | mitigate | Server-side `.strip()` check in the service layer (`admin_arguments.py:622-634`), not in the Pydantic schema — applies identically to a direct API call and to the UI; distinct tagged `ValueError("blank_override_reason")` (D-17, ASVS V5) | closed |
| T-48-MASS | Tampering | `PublishRequest` body (48-07) | medium | mitigate | `api/schemas/admin_arguments.py:263-271` — allow-list of exactly one field; `status`, `published_at`, `trust_tier` deliberately absent and never settable from a request body (T-11-MASS, T-26-04) | closed |
| T-48-AUTH | Spoofing | authorization for the override (48-07) | low | accept | D-18: no extra guard beyond the router-level `X-Admin-Token` dependency (`api/routers/admin.py:104-124`, ASVS V4). Protection is the required reason plus the permanent log row. See AR-01 | closed |
| T-48-STICKY | Elevation of Privilege | a persistent override that outlives its justification (48-07) | high | mitigate | Grep for `exempt` across `api/`, `pipeline/`, `app/src` returns nothing — no exemption column, flag, or symbol exists; `test_override_is_not_sticky_across_republish` proves a republish is blocked again (D-16) | closed |
| T-48-SWALLOW | Repudiation | `except ValueError` swallowing `TrustGateBlocked` (48-07) | medium | mitigate | `api/routers/admin.py:1164` catches `TrustGateBlocked` before the bare `except ValueError` at `:1178`; an AST criterion asserts the handler ordering so a future reorder fails the build | closed |
| T-48-UIGATE | Elevation of Privilege | the browser treated as the gate (48-08) | high | mitigate | `required` textarea attribute and disabled-button state annotated in source as defense-in-depth only; plan 48-07's server-side `.strip()` is the authority. Operator verification step 5 submitted whitespace-only and was refused | closed |
| T-48-UIDEADEND | Denial of Service | an uncertain argument unpublishable through the app (48-08) | high | mitigate | `app/src/routes/admin/arguments/[id]/+page.svelte:414` always renders the override form for `publishBlocked`, so the operator retains final authority through the UI (D-19); operator verification step 6 confirms | closed |
| T-48-UIOVERREACH | Elevation of Privilege | offering an override for the non-overridable gate (48-08) | high | mitigate | `[id]/+page.server.ts:383-395` sets `publishBlocked` only on the two overridable-gate codes (`uncertain_tier_blocked`, `blank_override_reason` — the latter reachable only after an override attempt on the same gate); a plain-string 422 takes the `form.error` path (`+page.svelte:562`) with no reason field | closed |
| T-48-TOKEN | Information Disclosure | the admin token reaching the browser (48-08 / 48-10) | high | accept | Unchanged by this phase: grep finds no `ADMIN_TOKEN` reference in any `.svelte` file; it appears only in eight `+page.server.ts` modules via `$env/static/private`. No new client-side fetch introduced. See AR-03 | closed |
| T-48-RESETDB | Tampering | `reset_to_fixture`'s TRUNCATE (48-09) | high | mitigate | Route gated on `settings.environment == "development"`; `_require_corpus_files` runs as a pre-flight before the TRUNCATE (`api/services/admin_dev.py:167-170`); Task 1's precondition required echoing the resolved database name and halting on mismatch (Phase 47 T-47-01 shape) | closed |
| T-48-VACUOUSGATE | Repudiation | a zero-changed report on an empty scan (48-09) | high | mitigate | 48-EVIDENCE.md §4 records `4 scanned, 4 unchanged, 0 changed` — `scanned > 0` satisfied and equal to the number of arguments the reseed created; plan 48-06's unit test locks the distinction | closed |
| T-48-SILENTSKIP | Repudiation | DB-gated tests skipping for want of `TEST_DATABASE_URL` (48-09) | high | mitigate | Full-suite gate required `0 skipped`, not merely `0 failed`: 48-EVIDENCE.md records **1208 passed, 0 failed, 5 xfailed, 0 skipped** — the exact failure mode the 2026-08-18 UAT audit found (finding N-2) | closed |
| T-48-WEAKEN | Repudiation | lowering a threshold to make the gate pass (48-09) | high | mitigate | Recorded as a `must_haves.prohibitions` entry; 48-EVIDENCE.md §5 routes each finding to its owning plan rather than adjusting a threshold, and records which sites were checked and deliberately not changed | closed |
| T-48-LEAK (48-09 instance) | Information Disclosure | trust visible on the public site (48-09) | high | mitigate | Operator verification step 4 inspected a live public page; the full-suite gate re-ran plan 48-03's structural and live leak-ban assertions | closed |
| T-48-10-UIGATE | Elevation of Privilege | the browser treated as the gate — list page (48-10) | high | mitigate | `required` textarea annotated as defense-in-depth only; the server's `.strip()` check is the authority. Checkpoint step 3 exercised a whitespace-only submission and it was refused | closed |
| T-48-10-ROWMISMATCH | Repudiation | per-row form-state addressing on a shared `form` prop (48-10) | high | mitigate | Every `fail(...)` in `app/src/routes/admin/arguments/+page.server.ts` carries `argumentId` (lines 96, 107, 116, 129, 132, 170, 178, 181); every conditional render is gated on `form.argumentId === arg.id` (`+page.svelte:462`, `:483`, `:544`). Task 4's contract test asserts `argumentId` on every branch | closed |
| T-48-10-UIOVERREACH | Elevation of Privilege | offering an override for the non-overridable gate — list page (48-10) | high | mitigate | `+page.server.ts:105-129` — `publishBlocked` set only on the overridable-gate codes; a plain-string 422 takes the row-scoped `form.error` path with no reason field. Checkpoint step 6 and the contract test both confirm | closed |
| T-48-10-LEAK | Information Disclosure | `ArgumentListItem.trust_tier` reaching a public response (48-10) | high | mitigate | Served only from the admin router (`/api/admin/arguments`), outside the leak-ban test's derivation scope; Task 1 re-ran `test_trust_public_leak_ban.py` green and non-vacuous | closed |
| T-48-10-VISIBILITY | Information Disclosure | Defect 2 — unpublish not actually hiding public content (48-10) | high | mitigate | All three public read paths now additionally gate on `status == PUBLISHED`: `api/services/cases.py:41`, `api/services/arguments.py:65`, `api/services/speakers.py:154`. A regression test proves the fix and fails without it; checkpoint step 7 confirms live | closed |
| T-48-SC | Tampering | npm/pip/cargo installs (all 10 plans; merged with T-48-10-SC) | low | accept | 48-RESEARCH.md § Package Legitimacy Audit: this phase introduces zero new third-party packages, so there is no install task and no `[ASSUMED]`/`[SUS]` package to gate. `npm run check` runs against already-installed devDependencies. See AR-04 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-48-AUTH | D-18: the publish override carries no guard beyond the router-level `X-Admin-Token` dependency. A typed-confirmation phrase (as the Danger Zone delete uses) was considered and rejected as inconsistent with every other admin mutation. The override's protection is the mandatory non-blank reason plus the permanent status-log row recording `override_reason` and `trust_tier_at_transition`. Severity low. | Plan 48-07 (D-18) | 2026-08-18 |
| AR-02 | T-48-CANDLEAK | D-04: `/admin/arguments` list and stats exclude the born state via a positive allow-list, so candidate rows are invisible on the admin list until Phase 49 designs their visibility deliberately. This is exclusion, not leakage; recorded because it is a known behavioural gap, not a defect. Severity low. | Plan 48-04 (D-04) | 2026-08-18 |
| AR-03 | T-48-TOKEN | `ADMIN_TOKEN` is imported from `$env/static/private` and used only inside SvelteKit server actions — the standing architecture (CLAUDE.md rule 2), unchanged by this phase. Accepted as the existing design rather than a new risk; no new client-side fetch was introduced. Severity high but pre-existing and architecturally enforced. | Plans 48-08 / 48-10 | 2026-08-18 |
| AR-04 | T-48-SC | Zero new third-party packages this phase, so there is no supply-chain surface to gate. Re-evaluate on the first phase that adds an install task. Severity low. | All 10 plans | 2026-08-18 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-21 | 41 | 41 | 0 | /gsd-secure-phase (orchestrator, ASVS L1 grep-depth) |

### Security Audit 2026-08-21

| Metric | Count |
|--------|-------|
| Threats found | 41 |
| Closed | 41 |
| Open | 0 |

Row count is 41 because `T-48-LEAK` is recorded twice — once for its 48-03/48-07/48-08
model-contract form and once for the 48-09 live-public-page instance. 40 distinct
threat IDs.

Method: register built from the `<threat_model>` block of all 10 PLAN files
(`register_authored_at_plan_time: true`); no `## Threat Flags` section appeared in any
SUMMARY. Each declared mitigation was verified against the implementation at ASVS L1
grep depth, with 48-EVIDENCE.md supplying the end-to-end falsifiers for the four
Repudiation threats that are evidence-bound rather than code-bound (T-48-VACUOUSGATE,
T-48-SILENTSKIP, T-48-WEAKEN, T-48-CLIVACUOUS). The short-circuit rule applied
(`threats_open: 0` + register authored at plan time + `asvs_level == 1`), so no
deeper auditor pass was required.

Two register statements were checked closely and judged consistent with mitigation intent
rather than deviations:

1. **T-48-UIOVERREACH / T-48-10-UIOVERREACH** — both plans state `publishBlocked` is set
   "only for the `uncertain_tier_blocked` code", but the implementation also sets it on
   `blank_override_reason`. That second branch is reachable only after an override attempt
   against the same overridable gate and it carries `overrideReasonRequired: true`, so it
   re-renders the reason panel with a validation error rather than offering an override for
   the non-overridable resolve gate. The non-overridable path still returns a plain-string
   detail and takes the reason-free `form.error` branch. Mitigation intent holds; the plan
   prose is narrower than the shipped code.
2. **T-48-DDL / T-48-RESETDB** — both mitigations are operator-executed preconditions
   (echo the resolved database name, halt on mismatch) rather than standing code artifacts.
   They are verified through the migration's presence at head and 48-EVIDENCE.md's record
   of the runs, not by grep. This is the same evidence-bound shape Phase 47's T-47-01 used.

Related: 48-REVIEW.md carries two Info-severity findings (IN-01, IN-02) left open by
design. Neither is a threat-register item and neither is security-bearing; the one
Critical (CR-01) and both Warnings (CR-02, CR-03) are fixed and committed.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-21
