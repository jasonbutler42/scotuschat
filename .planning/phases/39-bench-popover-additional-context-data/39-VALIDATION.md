---
phase: 39
slug: bench-popover-additional-context-data
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-22
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (`pytest.ini` — `asyncio_mode = auto`, session-scoped loop); `svelte-check` for frontend type-checking only — no frontend test framework (`vitest`/`@testing-library/svelte`) is present in `app/package.json` |
| **Config file** | `pytest.ini`, `app/package.json` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py api/tests/test_admin_people_schemas_service.py -x` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest` (followed by `npm run check --prefix app` when frontend files changed) |
| **Estimated runtime** | Measure during Wave 0; focused checks should remain under 30 seconds where possible |

---

## Sampling Rate

- **After every task commit:** Run the quick run command above (targeted files only).
- **After every plan wave:** Run the full pytest suite; run `npm run check --prefix app` when `SpeakerPopover.svelte` or the admin edit page changed.
- **Before `/gsd-verify-work`:** Full suite green, plus manual UAT of the popover for at least one multi-tenure Justice (e.g. Rehnquist) and one advocate.
- **Max feedback latency:** 30 seconds for focused checks where possible; DB-gated import tests may run at wave boundaries.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 39-REASON | TBD | TBD | PUB-04 | T-39-01 | `reason_left_title()` degrades gracefully on an invalid/out-of-vocabulary value (mirrors Phase 37 CR-01 `office_title()` fix), never silently coerces or crashes the popover | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py -k reason -x` | ❌ W0 | ⬜ pending |
| 39-BACKFILL | TBD | TBD | PUB-04 | — | `import_justices_csv.py` backfills `birthdate`/`death_date`/`reason_left` onto pre-existing rows only when currently null; never overwrites an operator-set value | DB integration | `.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_import_justices_csv.py -x` | ✅ update | ⬜ pending |
| 39-ASSEMBLY | TBD | TBD | PUB-04 | — | `get_argument_speakers` assembles `birthdate`/`death_date`/`bio_text` and per-tenure `appointed_by`/`appointing_president_party`/`reason_left` correctly | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_speakers_service.py -x` | ✅ update | ⬜ pending |
| 39-SCHEMA | TBD | TBD | PUB-04 | T-39-02 | Public schema no longer excludes `appointing_president_party` (T-14-02 reversal); explicit regression test guards against a future accidental re-exclusion | unit | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py -k schema -x` | ❌ W0 | ⬜ pending |
| 39-UI | TBD | TBD | PUB-04 | — | Popover renders birthdate/death date, bio text with expand, and full tenure list for a multi-tenure Justice without visual overflow; advocate descriptor placeholder slot renders | manual-only | N/A (UAT) | ❌ no framework | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `api/tests/test_speakers_service.py` — new cases covering the reworked assembly shape (per-tenure `appointed_by`/`appointing_president_party`/`reason_left`, top-level `birthdate`/`death_date`/`bio_text`).
- [ ] `api/tests/test_admin_people_schemas_service.py` — new cases for `TenureWrite`/`TenureRow` accepting/rejecting `reason_left` values, mirroring the existing `test_tenure_write_rejects_*` shape.
- [ ] A direct exhaustiveness test for `reason_left_title()`/`REASON_LEFT_TITLES` — no precedent unit test exists for `office_title()` itself, but this phase reverses a security-relevant exclusion (T-14-02) and warrants an explicit regression guard from day one.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|--------------------|
| Popover visual layout for a multi-tenure Justice (e.g. Rehnquist: 2 tenures, birthdate, death date, bio) | PUB-04 | No frontend test framework in this repo (`svelte-check` is type-only) | Open the public argument view, click a multi-tenure Justice's avatar, confirm birthdate/death date/bio/tenure list render without overflow or truncation issues, and identically in structure to a single-tenure Justice. |
| Advocate descriptor placeholder slot | PUB-04 | Same — no frontend test framework | Click an advocate's avatar, confirm the placeholder descriptor line renders per D-16. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (frontend remains UAT-only, the established pattern for every prior phase touching `SpeakerPopover.svelte`)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
