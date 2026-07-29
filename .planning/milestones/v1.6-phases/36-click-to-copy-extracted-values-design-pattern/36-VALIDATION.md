---
phase: 36
slug: click-to-copy-extracted-values-design-pattern
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-07-15
---

# Phase 36 — Validation Strategy

> Retroactively reconstructed validation contract from the completed Phase 36 plans, summaries, verification report, implementation, and focused browser regression.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Node.js test runner with a test-only Vite/Svelte fixture and CDP-controlled browser |
| **Config file** | `app/tests/fixtures/copyable-extracted-value-vite.config.mjs` |
| **Quick run command** | `Set-Location app; node --test tests/copyable-extracted-value.browser.test.mjs` |
| **Full suite command** | `Set-Location app; node --test tests/copyable-extracted-value.browser.test.mjs; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; npm run check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; npm run build` |
| **Estimated runtime** | ~40 seconds |

---

## Sampling Rate

- **After every task commit:** Run `Set-Location app; node --test tests/copyable-extracted-value.browser.test.mjs`
- **After every plan wave:** Run the focused browser regression, `npm run check`, and `npm run build` fail-fast
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 36-01-01 | 01 | 1 | UX-01 | T-36-01 through T-36-04, T-36-SC | Exact escaped display string is copied; feedback and timer state remain local; raw errors are not disclosed | browser + static | `node --test tests/copyable-extracted-value.browser.test.mjs; npm run check` | ✅ | ✅ green |
| 36-01-02 | 01 | 1 | UX-01 | T-36-01 through T-36-04 | Shared argument-detail controls preserve exact payloads, individual docket targets, disabled N/A behavior, and native semantics | browser + build | `node --test tests/copyable-extracted-value.browser.test.mjs; npm run check; npm run build` | ✅ | ✅ green |
| 36-02-01 | 02 | 2 | UX-01 | T-36-05 through T-36-08 | Editable title hints reuse the sole clipboard state machine without page-local clipboard logic | static + build | `npm run check; npm run build` | ✅ | ✅ green |
| 36-02-02 | 02 | 2 | UX-01 | T-36-05 through T-36-08, T-36-SC | Eligible parsed outputs use exact final display strings and durable scope guidance remains present | static + build | `npm run check; npm run build; rg "operator-editable destination|explicitly opts out|read-only extracted value|CopyableExtractedValue" ../CLAUDE.md` | ✅ | ✅ green |
| 36-02-03 | 02 | 2 | UX-01 | T-36-05 through T-36-08 | Clipboard payload, keyboard/focus behavior, disabled semantics, feedback, and responsive presentation match the approved contract | automated regression + completed UAT | `node --test tests/copyable-extracted-value.browser.test.mjs; npm run check; npm run build` | ✅ | ✅ green |
| 36-03-01 | 03 | 3 | UX-01 | T-36-09 through T-36-11 | Only the newest activation may publish feedback or own the full 1500ms interval | browser | `node --test tests/copyable-extracted-value.browser.test.mjs` | ✅ | ✅ green |
| 36-03-02 | 03 | 3 | UX-01 | T-36-09 through T-36-11 | Payload changes and destruction invalidate stale promises and timers; failure remains fixed-copy and recoverable | browser + static + build | `node --test tests/copyable-extracted-value.browser.test.mjs; npm run check; npm run build` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage

| Requirement | Test File | Status | Evidence |
|-------------|-----------|--------|----------|
| UX-01 | `app/tests/copyable-extracted-value.browser.test.mjs` | COVERED | Current run passed 1/1; it covers newest-attempt ownership, full success timing, out-of-order settlement, fixed local rejection, retry, payload changes, and destruction. Static checking and production build also pass; completed Phase 36 UAT covers the visual/native interaction contract. |

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No test framework, dependency, fixture, or stub remains to be added.

---

## Manual-Only Verifications

All phase behaviors have automated verification or completed operator UAT recorded in `36-02-SUMMARY.md` and `36-VERIFICATION.md`. No outstanding manual-only verification remains.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none found)
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-15

## Validation Audit 2026-07-15

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
