---
phase: 39-bench-popover-additional-context-data
verified: 2026-07-29T18:00:00Z
status: passed
score: 4/4 roadmap success criteria verified (18/18 plan-level truths verified)
behavior_unverified: 0
overrides_applied: 0
prohibitions_reviewed: 9
prohibitions_flagged: 0
requirements_coverage:
  - id: PUB-04
    status: satisfied
    phase_plans: [39-01, 39-02, 39-03, 39-04, 39-05, 39-06, 39-07, 39-08, 39-09]
---

# Phase 39: Bench Popover Additional Context Data Verification Report

**Phase Goal:** When a visitor clicks a Justice's avatar on the public argument view, the popover should show richer persistent context about them: birthdate, death date, and a list of tenures with start/end dates, appointing president, that president's party affiliation, and why they left that tenure (death, retirement, promotion) — presented identically for every Justice per the apolitical-framing constraint.
**Verified:** 2026-07-29T18:00:00Z
**Status:** passed
**Re-verification:** No — initial verification (this phase's own internal gap-closure cycle across plans 39-06 through 39-09 is treated as prior work, not a prior VERIFICATION.md cycle — no `39-VERIFICATION.md` existed before this run)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Popover displays birthdate/death date when known | ✓ VERIFIED | `api/models/models.py:122` (`death_date` column), `alembic/versions/0023_add_person_death_date.py` (nullable DATE), `api/schemas/speakers.py:68-69` (`birthdate`/`death_date` on `SpeakerPopoverEntry`), `api/services/speakers.py:233-234` (real DB values serialized, null-safe), `SpeakerPopover.svelte:172-174` (renders `b. {date} · d. {date}`, each half independently omitted). Operator UAT test 4/5 (39-UAT.md): pass — birth/death line confirmed live on both a two-tenure deceased Justice and a living Justice. |
| 2 | Popover displays each tenure with start/end dates, appointing president, party affiliation, and reason for leaving when known | ✓ VERIFIED | `alembic/versions/0024_add_constrain_tenure_reason_left.py` (nullable `reason_left`, CHECK-constrained); `api/schemas/speakers.py:20-48` (`TenureEntry.appointed_by`/`.appointing_president_party`/`.reason_left`); `api/services/speakers.py:180-194` (Step 3a emits all three per tenure from real column reads, not derived); `SpeakerPopover.svelte:204-229` (two-column tenure block: office+range row, appointed_by+party / reason_left row, each independently omitted when null). Operator UAT test 4 (Rehnquist two-tenure card, 39-UAT.md): pass — "Chief 1986-2005 Died in office, Associate 1972-1986 Promoted" confirmed live post-39-08 restyle. |
| 3 | All added fields presented identically for every Justice, no differential framing by political consideration | ✓ VERIFIED | Code: `SpeakerPopover.svelte:220-224` renders `appointed_by`, `appointing_president_party`, and `reason_left` with identical color/size/weight spans regardless of value — the one new font-weight distinction introduced by 39-08 applies only to the office title (`officeTitle` span, line 212), never to party or reason. `api/services/speakers.py` header docstring (lines 8-17) and `api/schemas/speakers.py` header docstring (lines 4-13) both document the T-14-02 reversal rationale as neutral/factual, with an explicit closed allow-list assembly (no conditional/differential emission). Operator UAT test 6 (39-UAT.md): pass, explicitly re-verified at 39-09 checkpoint — this was the one prohibition classified as "the one explicitly blocking check" (because 39-08 introduced the tenure block's first font-weight distinction and the operator was specifically asked to re-confirm party-neutrality survived it). Result: "yes, all parties render identically." |
| 4 | Case-specific presentation (age at argument, tenure-length, case-heard counts) remains out of scope | ✓ VERIFIED | No age/tenure-length/case-count computation exists anywhere in `api/services/speakers.py`, `api/schemas/speakers.py`, or `SpeakerPopover.svelte` — confirmed by direct read of all three files. Operator UAT test 9 (39-UAT.md, bundled 39-09 confirmation): pass — "No age, tenure-length, case-count, or 'Edit person' link on any card." |

**Score:** 4/4 roadmap success criteria verified, 0 behavior-unverified.

### Plan-Level Must-Have Truths (all 9 plans)

All plan-level `must_haves.truths` across 39-01 through 39-09 were cross-checked against the current codebase (not just the SUMMARY narratives). All verified:

| Plan | Truth (abbreviated) | Status | Evidence |
|------|---------------------|--------|----------|
| 39-01 | `reason_left`/`death_date` columns, nullable, `reason_left_title()` exhaustive | ✓ VERIFIED | Migrations 0023/0024 read directly; `api/models/models.py:181-205` (`REASON_LEFT_TITLES`, `reason_left_title()`); `api/tests/test_tenure_reason_left.py` — 38 combined phase-39 tests pass (see Behavioral Spot-Checks) |
| 39-02 | Importer backfills birthdate/death_date/reason_left, null-only, idempotent, no derivation | ✓ VERIFIED | `pipeline/commands/import_justices_csv.py:35-54,247-368` (`_REASON_LEFT_CSV_MAP`, blank-only prefill logic, unmatched-value counting) read directly. Operator UAT test 2 (39-UAT.md): pass — "First run backfills ... second consecutive run creates 0 people and 0 tenures." |
| 39-03 | Admin editor Death Date + Reason Left round-trip, TenureWrite strict validation | ✓ VERIFIED | `api/schemas/admin_people.py:66,88,192,252`; `api/services/admin_people.py:559-568` (`model_fields_set`-guarded write); `+page.svelte:708-709,941-949` (hidden inputs, dropdown with escape hatch). Operator UAT test 10 (39-UAT.md, post-39-07 fix): pass. |
| 39-04 | Speakers endpoint widened: `appointed_by`/`appointing_president_party` per tenure, top-level `appointing_president` removed, `birthdate`/`death_date`/`bio_text` added, closed allow-list | ✓ VERIFIED | `api/schemas/speakers.py` and `api/services/speakers.py` read in full — matches every stated truth exactly, including the explicit allow-list assembly (Step 5) and the retirement of the top-level field. |
| 39-05 | Popover renders birth/death line, tenure blocks, bio clamp/toggle, advocate descriptor, neutral styling, scroll containment, timezone-independent dates | ✓ VERIFIED | `SpeakerPopover.svelte` read in full — `formatShort`/`formatMonthYear` both pin `timeZone: 'UTC'`; bio clamp/toggle logic present (lines 82-93, 184-199); advocate "Coming soon" slot (line 179). |
| 39-06 | Operator checkpoint (live-stack UAT of the above) | ✓ VERIFIED (checkpoint) | 39-UAT.md tests 2-13 — found 3 real defects (bio save bug, separator spacing, style mismatch vs. Figma), all filed as gaps. |
| 39-07 | Bio save bug fixed: bio owned by save-form, photo action no longer PATCHes person | ✓ VERIFIED | `+page.svelte:610-638` (`bio_text` textarea, `form="save-form"`, `bind:value`); `+page.server.ts:180-181,258` (presence-guarded conditional spread), `295-335` (photo action has no person PATCH). `api/tests/test_phase39_bio_save_contract.py` passes. |
| 39-08 | Separator spacing fixed, two-column tenure rows, hairline dividers, month-year granularity, weight distinction confined to office title | ✓ VERIFIED | `SpeakerPopover.svelte:136` (`{#snippet separator(pad)}`), `204-229` (two-column rows), `118-124` (`formatMonthYear`). `api/tests/test_phase39_popover_ui_contract.py` passes. |
| 39-09 | Second operator checkpoint: all 3 gaps re-verified closed, party-neutrality re-confirmed post-39-08 | ✓ VERIFIED (checkpoint) | 39-UAT.md gaps section: 3 of 4 total findings `status: resolved`; the 4th (scrollbar) is `status: failed` but explicitly filed as a separate non-blocking todo per the operator's own "minor" framing, not folded into this phase. |

### Deferred / Accepted Minor Finding (not a gap)

A new minor finding surfaced during the 39-09 checkpoint, outside the original 3-gap scope and outside the phase's 4 success criteria: the popover's native scrollbar renders outside the visible card boundary on long content (`app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` line 145's `max-height`/`overflow-y` lives on `Popover.Content`, while the visible rounded-card styling lives on an inner element in `SpeakerPopover.svelte`). The operator explicitly framed this as "minor" and it does not affect any of the four ROADMAP success criteria (birthdate/death date display, tenure field display, apolitical presentation, or scope exclusion of case-specific stats). It was filed as `.planning/todos/pending/2026-07-29-popover-scrollbar-outside-card.md` per 39-UAT.md's own `status_note`. Confirmed this file exists and this is not silently dropped:

- `.planning/todos/pending/2026-07-29-popover-scrollbar-outside-card.md` — filed, not blocking.

This is not counted as a gap against phase 39's goal.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/0023_add_person_death_date.py` | `people.death_date` nullable DATE | ✓ VERIFIED | Read directly, matches exactly |
| `alembic/versions/0024_add_constrain_tenure_reason_left.py` | `court_tenures.reason_left` + CHECK constraint | ✓ VERIFIED | Read directly, matches exactly |
| `api/models/models.py` | `REASON_*` constants, `REASON_LEFT_TITLES`, `reason_left_title()`, `Person.death_date`, `CourtTenure.reason_left` | ✓ VERIFIED | All present |
| `api/schemas/speakers.py` | Widened `TenureEntry`/`SpeakerPopoverEntry` | ✓ VERIFIED | All present, top-level field correctly removed |
| `api/services/speakers.py` | Real DB reads for all new fields, closed allow-list assembly | ✓ VERIFIED | All present |
| `pipeline/commands/import_justices_csv.py` | CSV backfill for 3 new fields, null-only, idempotent | ✓ VERIFIED | All present |
| `api/schemas/admin_people.py`, `api/services/admin_people.py` | Editable Death Date + Reason Left, `model_fields_set` guard | ✓ VERIFIED | All present |
| `app/src/routes/admin/people/[id]/+page.svelte`, `+page.server.ts` | Death Date input, Reason Left dropdown, bio owned by save-form, photo action has no person PATCH | ✓ VERIFIED | All present, bio bug fix confirmed |
| `app/src/lib/components/SpeakerPopover.svelte` | Birth/death line, tenure blocks, bio clamp, advocate slot, party-neutral styling, padded separator, two-column tenure rows | ✓ VERIFIED | All present |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` | Widened `SpeakerDetail`/`TenureRow` types, scroll wrapper | ✓ VERIFIED | Present; scroll wrapper has the known minor styling gap noted above (non-blocking) |
| `api/tests/test_tenure_reason_left.py`, `test_phase39_bio_save_contract.py`, `test_phase39_popover_ui_contract.py` | DB-free contract tests | ✓ VERIFIED | All exist, substantive, and pass (see Behavioral Spot-Checks) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `api/services/speakers.py` | `api/models/models.py` | `CourtTenure.reason_left`/`.appointed_by`/`.appointing_president_party` reads | ✓ WIRED | Confirmed lines 172-194 |
| `app/src/lib/components/SpeakerPopover.svelte` | `api/schemas/speakers.py` | `TenureEntry` fields consumed at render boundary | ✓ WIRED | Confirmed `TenureRow` interface mirrors `TenureEntry` exactly |
| `app/src/routes/admin/people/[id]/+page.svelte` | `+page.server.ts` | `bio_text` textarea `form="save-form"`, `death_date` hidden input | ✓ WIRED | Confirmed lines 636-637, 708-709 |
| `+page.server.ts` (save action) | `api/services/admin_people.py` | PATCH body with conditional `bio_text`/`death_date` | ✓ WIRED | Confirmed presence-guarded conditional spread, line 258 |
| `app/src/routes/cases/[slug]/arguments/[id]/+page.server.ts` | `api/services/speakers.py` (via router) | `fetch(.../speakers)`, real response mapped to `SpeakerDetail[]` | ✓ WIRED | Confirmed — no static/hardcoded fallback; degrades to `[]` only on non-OK/network error |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `SpeakerPopover.svelte` | `speaker` prop | `+page.svelte` `currentSpeaker` ← `data.speakers` Map | `+page.server.ts` fetches live `GET /arguments/{id}/speakers`, which runs real SQLAlchemy queries against `Person`/`CourtTenure` (no static/empty return) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 39 DB-free contract tests exist and pass | `pytest api/tests/test_phase39_bio_save_contract.py api/tests/test_phase39_popover_ui_contract.py api/tests/test_tenure_reason_left.py -q` | `38 passed in 20.83s` | ✓ PASS |
| Admin people schema/service unit tests pass | `pytest api/tests/test_admin_people_schemas_service.py -q` | `41 passed, 3 skipped` (skips are pre-existing DB-gated cases, unrelated to Phase 39) | ✓ PASS |
| DB-gated speaker/pipeline integration tests | `pytest api/tests/test_speakers_service.py pipeline/tests/test_import_justices_csv.py -q` | Hung attempting a live Postgres connection and was killed after 2+ minutes | ? SKIP — consistent with the documented WSL/Windows split dev environment (real Postgres is unreachable from this WSL session); not a phase defect. These paths are independently covered by the operator's live-stack UAT (39-UAT.md test 2: importer backfill/idempotency — pass) and by REVIEW.md's code review of the same files (0 critical findings). |

No probes (`scripts/*/tests/probe-*.sh`) apply to this phase — skipped, no runnable entry points of that kind.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PUB-04 | 39-01 through 39-09 (all) | Justice bench popover shows richer persistent context (birthdate, death date, per-tenure appointing president + party + reason for leaving), presented apolitically | ✓ SATISFIED | All 4 ROADMAP success criteria verified above; REQUIREMENTS.md already marks PUB-04 `[x]` / "Complete" for Phase 39, consistent with this independent verification |

No orphaned requirements: REQUIREMENTS.md's Phase 39 row maps only PUB-04, and every one of the 9 plans declares `requirements: [PUB-04]` — full agreement, nothing unaccounted for.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any Phase 39-modified file | — | None — clean |

**Advisory findings from 39-REVIEW.md (0 critical, 3 warning, 2 info) — none block the phase goal, but are worth carrying forward:**

- **WR-01** (data-integrity): No cross-field validation ties `reason_left` to `end_date` — an operator could theoretically save `reason_left` on an open tenure, which would render as a contradictory "... – present / Retired" popover row. Does not currently manifest in any tested data path; a follow-up fix is recommended but does not block this phase's goal (the popover does not fabricate or mis-derive data — it would only mis-render already-bad hand-entered data).
- **WR-02** (UX robustness): The `reason_left` legacy-value escape hatch lacks the same client/server preflight validation `office` has, which could block all future saves if a bad legacy value exists. No evidence any such legacy value currently exists in the dataset.
- **WR-03** (test coverage): The CR-01 partial-PATCH regression test covers `birthdate` but not the newly added `death_date`, despite an identical documented silent-wipe risk pattern. A regression here would be a future silent-wipe bug, not a currently-failing behavior.
- **IN-01/IN-02**: Dead code / redundant defensive code — cosmetic only.

These are legitimate follow-up items but do not fail any of the phase's declared must-haves or ROADMAP success criteria; recommend a lightweight follow-up task rather than blocking phase 39.

### Prohibition Review

9 prohibitions were declared across the 9 plans (transparency/values/scope categories — e.g. "MUST NOT derive reason_left from other stored data," "MUST NOT apply differential styling by party or reason," "MUST NOT introduce cross-Justice aggregation," "MUST NOT reintroduce an unchecked fetch whose failure is discarded"). None declare an explicit `verification: test|judgment` tier (schema variance from the newer convention), so all were treated as judgment-tier and checked by direct code read:

- No derivation logic for `reason_left` exists anywhere (confirmed: `pipeline/commands/import_justices_csv.py` reads a raw CSV column via `_REASON_LEFT_CSV_MAP`; `api/services/speakers.py` reads the stored column directly).
- No aggregation/count/ranking logic exists anywhere in the touched files (confirmed by direct read of `api/services/speakers.py`, `api/schemas/speakers.py`, `SpeakerPopover.svelte`).
- No party/reason-based styling differential exists (confirmed: identical style spans in `SpeakerPopover.svelte:220-224`; independently re-confirmed live by the operator at the 39-09 checkpoint, explicitly framed as the one blocking check).
- No unchecked/error-swallowing person PATCH remains (confirmed: `+page.server.ts` photo action no longer PATCHes person at all, per 39-07's fix).
- `PersonUpdate`'s `extra="forbid"` allow-list contract is intact; the save action still reads each field by name rather than passing through the raw form body.

All 9 resolve to satisfied. This is a code-read-based judgment, not a mechanically-enforced test gate — flagged here for visibility, consistent with the judgment-tier prohibition handling convention, but not treated as blocking given the volume of corroborating live-operator confirmation already on record for the two hardest-to-mechanically-verify prohibitions (party-neutral rendering, no unchecked fetch).

### Human Verification Required

None outstanding. This phase's structure already routed every truth that requires live-stack/visual observation through two dedicated operator checkpoints (39-06, 39-09; both `autonomous: false`), and 39-UAT.md records `status: complete` with 12 of 14 tests passing, 1 skipped (a migration-state check the operator didn't explicitly report, judged low-risk since STATE.md records an earlier accidental apply), and 1 minor non-blocking issue (scrollbar, filed separately, not part of the phase's success criteria). The one criterion this verifier could not exercise itself — apolitical, party-neutral rendering across real historical Justices with different party-affiliated appointing presidents — was explicitly re-tested live by the operator after the phase's single font-weight change, and is the item 39-UAT.md itself calls "the one explicitly blocking check." No further human verification is being requested.

### Gaps Summary

No gaps. All four ROADMAP success criteria for PUB-04 are verified in the codebase (schema, service, migrations, and rendering component), backed by 38 passing DB-free contract tests, a clean code review (0 critical findings), and a completed two-round operator UAT cycle that surfaced and closed all three real defects found (bio save bug, separator spacing, style mismatch vs. Figma). The one new minor finding from the second UAT round (scrollbar rendering outside the card boundary) is outside the phase's four success criteria and was deliberately filed as a separate backlog todo rather than folded into this phase's closure, consistent with the operator's own "minor" framing — this verifier concurs it does not block phase 39's goal achievement.

---

_Verified: 2026-07-29T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
