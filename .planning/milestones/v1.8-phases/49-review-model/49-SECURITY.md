---
phase: 49
slug: review-model
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-08-23
---

# Phase 49 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register origin: `register_authored_at_plan_time: true` — all six PLAN files
(49-01 … 49-06) carried a parseable `<threat_model>` block. Verification depth
is ASVS L1 (grep/structural), per `workflow.security_asvs_level: 1`. Blocking
threshold is `workflow.security_block_on: high`.

The six plans reused four threat ids rather than numbering per-plan, so the
register below consolidates each id across the plans that raised it. Severity
is the maximum asserted by any plan; disposition is the strongest control any
plan applied.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| operator browser → SvelteKit `+page.server.ts` | The only place `FASTAPI_BASE_URL` / `ADMIN_TOKEN` exist; untrusted form bodies and query params (`tab`, `status`, `tier`, `review_state`, `missing`) cross here | Untrusted operator input; server-only secrets |
| SvelteKit server → FastAPI `/api/admin/**` | Admin-token authenticated; router-level `verify_admin_token` dependency is the gate | Admin token; review actions |
| incoming import value → stored operator value | The authority boundary Phase 49 exists to enforce; a lower-or-equal-authority write must never cross it | Provenance-ranked field values |
| FastAPI service → PostgreSQL | Every write is a scoped SELECT-then-UPDATE; no client-supplied identifier reaches SQL unparameterised | `argument_participants`, `people`, `value_discrepancy` rows |
| operator-only review data → public routes | The apolitical hard constraint: `review_state` / `trust_tier` / `source` / `method` / discrepancy vocabulary must never reach a public response | Operator review state, provenance, trust tier |
| deployment environment → `admin_dev` router | The `settings.environment == "development"` conditional mount in `api/main.py` is the only thing between production and a state-fabricating endpoint | Dev-only fixture seeding |
| Alembic migration → live `people` rows | Destructive DDL boundary (plan 49-02): two columns dropped, their data unrecoverable afterward | Legacy person columns |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-49-authority | Tampering | `api/domain/authority.py::decide_write`; `api/services/admin_review.py::apply_participant_value_change` / `apply_person_value_change`; `api/services/admin_dev.py::seed_unresolved_speaker_fixture` | high | mitigate | Single gate function `decide_write` (`api/domain/authority.py:116`) returning `REJECT_AND_RECORD` (`:183`) for equal-or-lower incoming authority, with a fail-closed `UNKNOWN = 0` rung (`:50`, `:100`, `:113`) so an unrecognised source can never outrank anything. Verified as the only gate: the two call sites are `api/services/admin_review.py:187` and `:254`, both importing from `api.domain.authority:33`. `OPERATOR/OPERATOR` is deliberately carved out to `ACCEPT_AND_RECORD` (`:165`) to preserve the operator round-trip; every other equal-rank pair rejects. Dev seeder writes only `person_id` + `review_state`, never an operator state, and its router is unregistered outside development (`api/main.py:43-44`). Exhaustively tested by `api/tests/test_authority_matrix.py` (969 lines, rank×rank×differs matrix with a count guard). | closed |
| T-49-idor | Tampering | `api/services/admin_review.py::resolve_participant_review` / `resolve_person_review` / `apply_participant_value_change` / `close_open_discrepancies`; `api/services/admin_people.py::update_person`; `api/services/admin_dev.py` seeder | high | mitigate | Scoped SELECT before every write, returning `None` → router 404 on a missing row (`api/services/admin_review.py:847-851`, `:900-903`). `apply_participant_value_change` repeats the parent scope in its UPDATE WHERE (`ArgumentParticipant.argument_id == participant.argument_id`, `:205`). `close_open_discrepancies` filters on `target_type` AND `target_id` (`:139`, `:149-150`), so a person action can never close a participant's discrepancy. See the Accepted Risks Log for the one place the implementation scopes by primary key alone. | closed |
| T-49-massassign | Tampering | `api/schemas/admin_review.py::ReviewActionRequest`; `api/schemas/admin_people.py::PersonUpdate`; `POST /api/admin/dev/seed-unresolved-speaker` | high | mitigate | `ReviewActionRequest` (`api/schemas/admin_review.py:114-126`) exposes only `action` as a closed `Literal` — no id, no target scope, no column name or value is accepted from the client; scope comes from the URL path and the field written is chosen server-side by the action verb. `PersonUpdate` (`api/schemas/admin_people.py:203`) allow-lists only `bio_text`, `photo_url`, `tenures`, `first_name`, `last_name`, `middle_name`, `name_suffix` — verified that neither `review_state` nor `provenance_metadata` is a writable field, so no client can set an operator state or overwrite a provenance envelope directly. The dev seeder endpoint (`api/routers/admin_dev.py:60-61`) declares no request body, no query parameter, and no header — the target conversation is a module constant (`DEFAULT_UNRESOLVED_SPEAKER_CONVERSATION_ID`), and `api/tests/test_admin_dev_unresolved_fixture.py` carries a `conversation_id` grep gate. | closed |
| T-49-leak | Information Disclosure | Public response models; `api/schemas/admin_review.py`; `api/schemas/admin_people.py`; `/admin/review` SSR load; `app/src/routes/admin/help/+page.svelte` | high | mitigate | `api/tests/test_trust_public_leak_ban.py` bans seven keys — `trust_tier`, `review_state`, `source`, `method`, `incoming_value`, `existing_value`, `resolved_at` (`:53-61`) — iterated over the derived public-model graph as parametrized cases (`:156-161`), plus an AST import ban on `api.domain.authority` / `api.schemas.admin_review` from public schema modules. Independently confirmed: a grep for that vocabulary across `api/schemas/people.py`, `api/schemas/cases.py`, and `api/schemas/arguments.py` returns nothing. Review vocabulary lives only in the admin-only schemas, reached only by `api/routers/admin_review.py`. `/admin/**` routes sit behind the existing session gate with `FASTAPI_BASE_URL` / `ADMIN_TOKEN` as `$env/static/private`. | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

### Plan-level dispositions folded into the consolidated register

| Plan | T-49-authority | T-49-idor | T-49-massassign | T-49-leak |
|------|----------------|-----------|-----------------|-----------|
| 49-01 | high / transfer → 49-04 | high / mitigate | medium / mitigate | high / mitigate |
| 49-02 | high / mitigate | medium / accept | medium / mitigate | high / mitigate |
| 49-03 | low / accept | low / accept | low / accept | medium / mitigate |
| 49-04 | high / mitigate | high / mitigate | high / mitigate | high / mitigate |
| 49-05 | medium / accept | high / mitigate | high / mitigate | high / mitigate |
| 49-06 | high / mitigate | medium / mitigate | medium / mitigate | medium / mitigate |

Plan 49-01 dispositioned `T-49-authority` as **transfer** to plan 49-04, which
owns REVIEW-02. That transfer resolved: `api/domain/authority.py` exists and is
the single gate. No transfer is left unowned.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-49-01 | T-49-idor | `resolve_participant_review`'s UPDATE is scoped by `ArgumentParticipant.id == participant_id` only (`api/services/admin_review.py:870-875`), not by `.id AND .argument_id` as plan 49-04's threat model asserted. Not exploitable: `participant_id` is a primary key taken from the URL path, and the client supplies no parent scope that could be crossed — the same rationale plan 49-02 accepted for `Person` (no parent scope to cross, row selected by PK from the path). The `argument_id` read at `:877` is used only to recompute the argument tier, not as an authorization scope. Recorded because the register's stated mitigation does not literally match the implementation, even though the residual risk is nil at ASVS L1. | jason.butler | 2026-08-23 |
| R-49-02 | T-49-massassign | Plan 49-03: `CreatePersonPopover`'s `initialSide` changes only which radio starts selected client-side; the posted value is still produced by the unchanged `resolvedSide()` and validated by the unchanged server-side create-person schema. No new writable field. Severity low. | jason.butler | 2026-08-23 |
| R-49-03 | T-49-idor | Plan 49-03: `ResolveCard::handlePersonCreated` adds a client-side display string on a row the operator already has open; write scope still comes from the unchanged `submitRow(participantId)` path and its server-side job→argument→participant guard. Severity low. | jason.butler | 2026-08-23 |
| R-49-04 | T-49-authority | Plan 49-05: the `/admin/review` queue reads and displays only — no new write path, cannot bypass the 49-04 gate. Residual risk is display-only (a mis-sorted queue could hide an item needing attention), mitigated by the deterministic tie-break and its repeated-call stability test rather than by an authority control. Severity medium — below the `high` blocking threshold. | jason.butler | 2026-08-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-08-23 | 4 | 4 | 0 | /gsd-secure-phase (ASVS L1, orchestrator grep-depth verification) |

Verification method: each consolidated threat's stated mitigation was read in
the implementation rather than taken from the SUMMARY/EVIDENCE claims. Note
that no SUMMARY file carried a `## Threat Flags` section; threat traceability
for this phase lives in `49-EVIDENCE.md:379-385`, which was cross-checked
against source. One claim in that traceability table did not hold literally —
recorded as R-49-01 rather than accepted at face value.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-08-23
