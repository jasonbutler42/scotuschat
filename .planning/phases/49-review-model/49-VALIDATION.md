---
phase: 49
slug: review-model
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-21
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Seeded from `49-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`.venv/bin/pytest`, verified present) |
| **Config file** | `pytest.ini` at repo root, with the isolation-critical `conftest.py` beside it |
| **Quick run command** | `./.venv/bin/python -m pytest api/tests/test_<module>.py -x` |
| **Full suite command** | `./.venv/bin/python -m pytest` |
| **Estimated runtime** | ~full suite baseline at Phase 48 close: 1209 passed / 5 xfailed / 0 failed / 0 skipped |

**Invocation-shape caution (CLAUDE.md, Phase 45 D-03):** the `TEST_DATABASE_URL` redirect lives in the
repo-root `conftest.py`. Never invoke a subset of tests in a way that bypasses it. The regression guard is
`tests/test_pytest_isolation_invocation_shapes.py`.

---

## Sampling Rate

- **After every task commit:** the relevant new/extended test file only, fail-fast (`-x`)
- **After every plan wave:** `./.venv/bin/python -m pytest api/tests -q`
- **Before `/gsd-verify-work`:** full suite green (`./.venv/bin/python -m pytest`) **plus** D-32's one live
  browser walkthrough of an authority conflict (operator edits a corpus value, a second writer disagrees)
- **Max feedback latency:** single-file quick run — target < 60s

**Why the browser walkthrough is non-negotiable:** three of Phase 48's defects were found by operator
browser testing and none by the 1209-test suite. Automated green is necessary, not sufficient.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | 0 | REVIEW-01 | — | N/A | unit | `./.venv/bin/python -m pytest api/tests/test_review_state_schema.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REVIEW-02 | T-49-authority | Equal-or-higher-authority disagreement records a discrepancy, never overwrites | unit + integration | `./.venv/bin/python -m pytest api/tests/test_authority_matrix.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REVIEW-03 | T-49-idor | Queue query scoped by admin auth; no cross-argument leakage | integration | `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REVIEW-04 | T-49-idor, T-49-massassign | Scoped-SELECT-then-UPDATE; Pydantic allow-list body | integration | `./.venv/bin/python -m pytest api/tests/test_admin_review_service.py::test_resolve_recomputes_trust -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | REVIEW-05 | — | N/A | static/structural | `./.venv/bin/python -m pytest api/tests/test_legacy_review_mechanism_removed.py -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | 0 | D-34 | T-49-leak | `review_state`/`source`/`method`/discrepancy fields never reach a public response | structural | `./.venv/bin/python -m pytest api/tests/test_trust_public_leak_ban.py -x` | ✓ needs extension | ⬜ pending |

*Task IDs are filled in by the planner; this table is the requirement→command contract the plans must satisfy.*

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/tests/test_review_state_schema.py` — REVIEW-01 (enum presence + all four values on both `people` and `argument_participants`)
- [ ] `api/tests/test_authority_matrix.py` — REVIEW-02 (every (incoming-authority, stored-authority) combination; D-32 calls this *exhaustive*)
- [ ] `api/tests/test_admin_review_service.py` — REVIEW-03 / REVIEW-04 (queue query with tier × review_state × status filters, resolve action, trust recompute)
- [ ] `api/tests/test_legacy_review_mechanism_removed.py` — REVIEW-05 (structural check that `name_needs_review` / `name_extraction_metadata` appear nowhere outside migration history and the `downgrade()` path)
- [ ] Extend `api/tests/test_trust_public_leak_ban.py` — D-34 (no new file; a real change to an existing structural contract)
- [ ] **Dev-only fixture mechanism for the unresolved-speaker case (D-33)** — infrastructure, not a test file, but it gates every test needing a NULL-`person_id` `ArgumentParticipant`. See RESEARCH Pitfall 4: no live corpus path produces one today because `_resolve_person` always resolves-or-creates.

*Framework install: none needed — pytest and all fixtures already exist project-wide.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Authority-conflict walkthrough (D-32) | REVIEW-02, REVIEW-04 | Cross-writer race and UI affordance correctness are exactly what the automated suite missed three times in Phase 48 | Operator edits a corpus-derived value in the browser, then triggers a re-import that disagrees; confirm a discrepancy row appears in the queue and the operator value survives untouched |
| Review-queue filter combinations render correctly | REVIEW-03 | Visual/layout correctness of the filter UI and the dashboard StatCard grid | Exercise each tier × review_state filter pair; confirm the fifth StatCard lays out correctly — RESEARCH Pitfall 3 found the grid is hardcoded `repeat(4, 1fr)` at `app/src/routes/admin/+page.svelte:240`, contradicting the UI-SPEC's "absorbs the fifth card without change" |

---

## Security Domain (ASVS L1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | `/admin/review` inherits the existing router-level `verify_admin_token` dependency |
| V3 Session Management | No | No change to session handling |
| V4 Access Control | **Yes** | Scoped-SELECT-then-UPDATE (WHERE both parent id AND child id match), per `update_participant_side` at `api/services/admin_arguments.py:725-727` |
| V5 Input Validation | **Yes** | Pydantic allow-list-only-writable-fields, per `ParticipantSideUpdate` at `api/schemas/admin_arguments.py:44-55` |
| V6 Cryptography | No | Not implicated |

| Threat Ref | Pattern | STRIDE | Mitigation |
|---|---|---|---|
| T-49-leak | Public disclosure of operator-only trust/review data | Information Disclosure | Extend `test_trust_public_leak_ban.py` per D-34 |
| T-49-idor | IDOR on cross-argument / cross-person writes | Tampering | Scoped-SELECT-then-UPDATE |
| T-49-massassign | Mass assignment via overly permissive PATCH body | Tampering | Pydantic schema exposing only intended writable fields |
| T-49-authority | Re-import silently overwriting human-confirmed work | Tampering | Authority-ladder gate + discrepancy record; "operator work is sacred" |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for quick runs
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
