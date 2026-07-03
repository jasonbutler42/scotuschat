---
phase: 23-shared-argument-details-component
verified: 2026-07-02T18:00:00Z
status: human_needed
score: 9/13
behavior_unverified: 4
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Save with all docket pills removed — confirm source_docket becomes NULL in DB"
    expected: "After removing all docket pills in ArgumentDetailsCard and clicking Save, reload the page and confirm no docket pill appears. Confirm via DB or API that Argument.source_docket is NULL."
    why_human: "Requires a live PATCH round-trip through saveJobMetadata action -> FastAPI service -> PostgreSQL. The empty-string sentinel logic (dockets[0] ?? '' -> body.source_docket or None) is wired correctly in code but the DB NULL outcome is a state transition that cannot be verified by static analysis."
  - test: "Save a question number, reload — confirm hints row still shows italic N/A"
    expected: "After typing '42' in the Question number field and saving, reload the page. The 'Extracted: N/A' hint row below Question number must remain italic N/A — it must NOT change to 'Extracted: 42'."
    why_human: "hints.question_number is frozen to null in load() — code is correct — but the immutability of the hint through a real save/reload cycle is a runtime state invariant that static analysis cannot confirm."
  - test: "Ready-to-publish CTA appears when job is completed and argument is in draft status"
    expected: "On a pipeline job detail page where liveJob.status === 'completed' and the linked argument has resolved_at set (but not published_at), the 'Ready to publish' CTA block appears immediately after the ArgumentDetailsCard, with 'Go to argument editor' link. The old static Argument preview card must NOT appear."
    why_human: "The CTA logic depends on runtime argument state (status/resolved_at/published_at fields). The argStatus derivation chain (arg.status ?? resolved_at/published_at check) produces the correct rendering only with real DB state."
  - test: "Saving docket pills correctly persists and pre-populates on reload"
    expected: "Add two docket pills (e.g., '21-1271' and '22-100'), save, reload. Both pills appear pre-populated. Remove one pill, save, reload — only the remaining pill appears. Add a new pill, save, reload — the new pill appears."
    why_human: "Docket pill persistence involves FormData.getAll('docket[]') -> saveJobMetadata action -> PATCH /arguments/{id}/metadata -> source_docket saved. The pre-population on reload requires savedValues.dockets = [argument.source_docket] which only works with real DB state."
behavior_unverified_items:
  - truth: "Clearing all docket pills and saving persists the cleared state (source_docket becomes NULL in DB)"
    test: "Remove all docket pills in ArgumentDetailsCard, click Save, reload page"
    expected: "No docket pills shown on reload; DB Argument.source_docket is NULL"
    why_human: "Empty-string sentinel path (dockets[] empty -> source_docket '' -> service 'or None' -> DB NULL) is fully wired in code, but the state transition through a real DB write cannot be verified by grep/file checks"
  - truth: "The hints.question_number shown below the question number input is always null / italic N/A regardless of what the operator saves"
    test: "Save a question number value, reload the page"
    expected: "The Extracted hint row for question number remains italic 'N/A' after save and reload"
    why_human: "hints.question_number is hardcoded to null in load() — code is correct — but the runtime invariant that the hint never reflects an operator-saved value requires a real save/reload cycle to confirm"
  - truth: "The 'Ready to publish' CTA renders as a standalone block immediately after ArgumentDetailsCard when liveJob.status === 'completed' && argStatus === 'draft'"
    test: "Navigate to a pipeline job where the linked argument has resolved_at set and published_at is null"
    expected: "CTA block with 'Ready to publish' heading and 'Go to argument editor' link appears after ArgumentDetailsCard; old static Argument card does not appear"
    why_human: "CTA depends on liveJob.status polled from server and argStatus derived from argument.status/resolved_at/published_at — cannot be confirmed without a real completed run with a draft argument"
  - truth: "Saving Argument Details persists dockets + question number + argued date to the linked argument and does NOT create the argument"
    test: "Fill all three fields (add a docket pill, enter question number, set argued date), click Save"
    expected: "All three values saved; page shows 'Saved.' in green; reload confirms values pre-populated; no new Argument record created; argument_id unchanged"
    why_human: "The PATCH /api/admin/arguments/{id}/metadata round-trip and the 'never creates an argument' invariant (saveJobMetadata fail-400 on null argument_id) are wired correctly but the combined save behavior requires live execution to confirm"
---

# Phase 23: Shared Argument Details Component — Verification Report

**Phase Goal:** A single reusable Argument Details card component exists that renders docket pill/tag input, free-text question number, argued date, and extracted hints from `cover_metadata` — wired up on the pipeline job detail page as its first consumer
**Verified:** 2026-07-02T18:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All 13 must-haves are drawn from the merged set of ROADMAP success criteria (5) and PLAN frontmatter truths (13-01, 13-02, 13-03, 13-04 plans combined). Overlapping truths are deduplicated; ROADMAP SCs take precedence in wording.

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Pipeline job detail page shows "Argument Details" card with docket pill/tag input, free-text question number, argued date, and extracted hints (or N/A) | VERIFIED | ArgumentDetailsCard rendered in +page.svelte lines 416-423 with action="?/saveJobMetadata"; heading "Argument Details" confirmed in component line 73; all three fields present with always-visible hint rows |
| 2 | Docket pill/tag UI allows adding multiple dockets one at a time (Enter) and removing individual pills | VERIFIED | addPill()/removePill() in ArgumentDetailsCard.svelte; Enter keydown with e.preventDefault() at line 178; hidden docket[] inputs per pill at line 95; duplicate/empty silently rejected |
| 3 | Parse stat card shows utterance count, Bench / Advocate / Total speakers, case name, argued date, docket(s), question number — N/A (italic) for unextracted | VERIFIED | +page.svelte lines 519-602: 8 fields confirmed; all sourced from ps.* (cover_metadata passthrough per PJOB-12); italic N/A for each null field |
| 4 | Saving Argument Details saves run metadata only and does NOT create the argument | PRESENT_BEHAVIOR_UNVERIFIED | saveJobMetadata action contains fail(400) guard when argumentId === null (line 443) and never calls approve; PATCH only targets /arguments/{id}/metadata — code is wired correctly but save behavior is a runtime state transition |
| 5 | Ingest card no longer shows the source file | VERIFIED | grep returns 0 for "View Source PDF", "View source PDF", "Source file", "liveJob.spaces_key", "liveJob.pdf_url", "liveJob.original_filename" in any render context in +page.svelte (fields exist only in the TypeScript interface, not in any template rendering) |
| 6 | GET /api/admin/jobs/{id} returns parse_stats with bench_count, advocate_count, total_speaker_count, case_name, argued_date, primary_docket, question_number | VERIFIED | ParseStats Pydantic model confirms all 9 fields (admin_jobs.py lines 30-40); get_job service populates all 9 keys in parse_stats dict (admin_jobs.py lines 181-191); Python AST parse passes |
| 7 | PATCH /api/admin/arguments/{id}/metadata accepts and persists question_number without creating an argument | VERIFIED | MetadataUpdate.question_number field at admin_arguments.py line 172; update_argument_metadata persists via guarded int() at lines 550-554; no approve call in the service |
| 8 | ArgumentDetailsCard component uses only Svelte 5 Runes ($props, $state, $effect) — no legacy patterns | VERIFIED | Zero matches for `export let`, `$:`, `import from 'svelte/store'` in ArgumentDetailsCard.svelte; component uses $props/$state/$effect exclusively |
| 9 | Each editable field shows an always-visible "Extracted: [value]" hint row below it, italic "N/A" when nothing extracted | VERIFIED | All 3 hint rows unconditionally rendered in ArgumentDetailsCard.svelte (lines 196-224, 253-265, 294-306); no conditional hiding; italic applied via font-style when hint is null |
| 10 | No "View Source PDF" card renders anywhere on the pipeline job detail page | VERIFIED | grep "View Source PDF\|View source PDF" in +page.svelte returns 0; entire card block confirmed removed in commit 4278c9fb |
| 11 | No residual static "Argument" metadata preview card renders on the pipeline job detail page | VERIFIED | grep "Argument metadata preview card" in +page.svelte returns 0; static preview card removed in commit 4278c9fb |
| 12 | The "Ready to publish" CTA renders as a standalone block immediately after ArgumentDetailsCard when run is completed and argument is in draft status | PRESENT_BEHAVIOR_UNVERIFIED | Standalone CTA block confirmed at +page.svelte lines 425-461 with own const declarations for arg/argStatus; no longer nested inside deleted outer guard — code wired correctly but argStatus === 'draft' rendering requires a real completed run with draft argument |
| 13 | Clearing all docket pills and saving persists the cleared state (source_docket becomes NULL in DB) | PRESENT_BEHAVIOR_UNVERIFIED | source_docket: dockets[0] ?? '' confirmed at +page.server.ts line 462; body.source_docket or None confirmed at admin_arguments.py line 547; logic chain is correct but DB NULL outcome requires runtime confirmation |

**Score:** 9/13 truths verified (4 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `api/schemas/admin_jobs.py` | ParseStats with 7 new fields | VERIFIED | bench_count, advocate_count, total_speaker_count, case_name, argued_date, primary_docket, question_number all present as Optional fields |
| `api/schemas/admin_arguments.py` | MetadataUpdate.question_number and ArgumentDetail.question_number | VERIFIED | MetadataUpdate.question_number Optional[str] = None (line 172); ArgumentDetail.question_number Optional[int] = None (line 128) |
| `api/services/admin_jobs.py` | get_job populating expanded parse_stats dict | VERIFIED | 9-key parse_stats dict with SideEnum bench/advocate count queries and cover_metadata passthrough |
| `api/services/admin_arguments.py` | update_argument_metadata writing question_number; source_docket or None sentinel | VERIFIED | question_number persisted (lines 550-554); source_docket or None at line 547 |
| `app/src/lib/components/ArgumentDetailsCard.svelte` | Full shared component | VERIFIED | 358 lines; Svelte 5 Runes only; all fields, hints, pill mechanics, form, readonly mode implemented |
| `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` | saveJobMetadata action + savedValues/hints in load | VERIFIED | saveJobMetadata action at line 418; savedValues/hints constructed in load() lines 109-138; hints.question_number = null literal at line 132 |
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | ArgumentDetailsCard import + expanded parse stat card | VERIFIED | Import at line 4; rendered lines 416-423; parse stat card lines 519-602; all orphaned cards removed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `load()` savedValues/hints | ArgumentDetailsCard props | `data.savedValues!` / `data.hints!` in +page.svelte line 417-420 | WIRED | Non-null assertions inside `{#if data.argument != null}` guard; load() contract guarantees non-null |
| ArgumentDetailsCard `action="?/saveJobMetadata"` | saveJobMetadata action | `<form method="POST" {action}>` in component | WIRED | action prop drives form target (D-01) |
| saveJobMetadata action | PATCH /arguments/{id}/metadata | fetch() at +page.server.ts line 453 | WIRED | Two-step: fetch job to derive argument_id server-side; PATCH metadata endpoint |
| expanded parse_stats (get_job service) | parse stat card rows | `liveJob.parse_stats` / `ps.*` in +page.svelte | WIRED | ParseStats fields passed via AdminJobResponse; ps.* accessed in template |
| pills $state | hidden docket[] inputs | `{#each pills as pill}<input type="hidden" name="docket[]">` | WIRED | One hidden input per pill, server reads FormData.getAll('docket[]') |
| form.dockets (failed save) | pill state restore | `$effect(() => { if (form?.dockets) { pills = form.dockets; } })` at line 35-38 | WIRED | D-06 restore path confirmed |
| +page.server.ts action | source_docket NULL sentinel | `dockets[0] ?? ''` -> service `body.source_docket or None` | WIRED | Empty-string sentinel chain confirmed at both ends |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| ArgumentDetailsCard.svelte | savedValues, hints props | +page.server.ts load() fetching from FastAPI /api/admin/arguments/{id} | Yes — Argument DB row via FastAPI | FLOWING |
| +page.svelte parse stat card | ps (liveJob.parse_stats) | liveJob polled from FastAPI; get_job service queries ArgumentParticipant COUNT + Argument cover_metadata | Yes — DB queries in admin_jobs.py service | FLOWING |
| saveJobMetadata action | docket[], question_number, argued_date | FormData from ArgumentDetailsCard form | Yes — operator input -> PATCH -> DB write | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Python schemas parse cleanly with new fields | `python -c "import ast; s=open('api/schemas/admin_jobs.py').read(); assert 'bench_count' in s and 'question_number' in s; ast.parse(s); print('OK')"` | OK | PASS |
| Python services parse cleanly and reference new fields | `python -c "import ast; s=open('api/services/admin_jobs.py').read(); assert 'bench_count' in s and 'total_speaker_count' in s and 'SideEnum' in s; ast.parse(s); print('OK')"` | OK | PASS |
| View Source PDF card removed | `grep -c "View Source PDF\|View source PDF" +page.svelte` | 0 | PASS |
| Argument metadata preview card removed | `grep -c "Argument metadata preview card" +page.svelte` | 0 | PASS |
| Ready to publish CTA present (once as text) | `grep -c "Ready to publish" +page.svelte` | 2 (comment + H2) | PASS |
| source_docket empty-string sentinel | `grep -n "source_docket: dockets\[0\] ?? ''"  +page.server.ts` | line 462 | PASS |
| hints.question_number frozen to null | `grep -n "question_number: null," +page.server.ts` | line 132 | PASS |
| source_docket or None in service | `grep -n "source_docket or None" admin_arguments.py` | line 547 | PASS |
| placeholder removed from ArgumentDetailsCard | `grep -c "placeholder" ArgumentDetailsCard.svelte` | 0 | PASS |
| Static docket instruction label present | `grep -n "press Enter\|Type a docket" ArgumentDetailsCard.svelte` | line 169 | PASS |
| No legacy Svelte patterns | `grep -n "export let\|\$:\|from 'svelte/store'" ArgumentDetailsCard.svelte` | (no output) | PASS |
| All 9 phase commits exist in git log | `git log --oneline | grep -E "23351d00|508ec6a3|bb9bdcf8|..."` | all 9 confirmed | PASS |

### Probe Execution

No probes declared in PLAN.md files for this phase. Step 7c SKIPPED — no probe-*.sh files declared.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PJOB-03 | 23-02 | Argument metadata section renamed to "Argument Details" | SATISFIED | ArgumentDetailsCard h2 heading "Argument Details" line 73 |
| PJOB-04 | 23-02, 23-03 | Extracted hints always visible, N/A if nothing extracted | SATISFIED | Always-visible hint rows in component; N/A italic fallbacks |
| PJOB-05 | 23-02 | Docket pill/tag UI | SATISFIED | addPill/removePill + Enter-to-add + × button in ArgumentDetailsCard |
| PJOB-06 | 23-02 | Question number: free text field | SATISFIED | `<input type="text" name="question_number">` in component |
| PJOB-07 | 23-01, 23-03 | Save saves run metadata only — does not create argument | SATISFIED (code) | saveJobMetadata fail(400) guard on null argumentId; no approve call — runtime confirmation pending |
| PJOB-09 | 23-03, 23-04 | Ingest card: remove source file display | SATISFIED | grep confirmed 0 render occurrences; View Source PDF card also removed |
| PJOB-10 | 23-01, 23-03 | Parse card shows: Utterances, Speakers (Bench/Advocate/Total), Case Name, Argued Date, Docket(s), Question Number | SATISFIED | All 8 fields in +page.svelte parse stat card block lines 519-602 |
| PJOB-11 | 23-03 | Parse card shows unextracted fields as N/A rather than hidden | SATISFIED | Italic N/A for every nullable field in parse stat card |
| PJOB-12 | 23-01, 23-03 | Parse card extracted values match hints shown in Argument Details card | SATISFIED | Parse stat reads from ps.* (cover_metadata passthrough); hints.dockets also from cover_metadata.primary_docket |
| AEDIT-03 | 23-02 | Argument Details card mirrors pipeline job detail version | SATISFIED | Same ArgumentDetailsCard component; same hint rows, fields, styling |
| AEDIT-04 | 23-02, 23-03 | Argument Details card is a shared component — same UI on pipeline/[id] and arguments/[id], different save targets | SATISFIED | action prop drives save target (D-01); Phase 26 can plug in with different action |

All 11 requirement IDs from the PLAN frontmatter are accounted for. No orphaned requirements found for Phase 23 in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/src/routes/admin/pipeline/[job_id]/+page.svelte` | 736 | `placeholder="Type to search…"` | Info | Pre-existing placeholder in resolve combobox — not related to Phase 23 changes; not a stub |

No `TBD`, `FIXME`, or `XXX` markers found in any Phase 23-modified file. No debt markers requiring escalation.

No `export let`, `$:` reactive statements, or legacy store imports in `ArgumentDetailsCard.svelte`.

### Human Verification Required

#### 1. Docket Pill Save and Pre-population

**Test:** Add a docket pill (e.g., "21-1271"), save, reload page. Confirm pill is pre-populated. Remove the pill and add a different one, save, reload. Confirm only the new pill shows.
**Expected:** Docket pills are correctly saved and pre-populated on reload. The most recent save state is reflected.
**Why human:** Requires live PATCH round-trip through FormData -> saveJobMetadata -> FastAPI PATCH -> DB -> load() -> savedValues.dockets.

#### 2. Clearing All Docket Pills Persists NULL

**Test:** Remove all docket pills from ArgumentDetailsCard and click Save. Reload the page and confirm no docket pills appear (or check DB that Argument.source_docket is NULL).
**Expected:** After clearing all pills and saving, the docket field shows empty (no pre-populated pills). source_docket is NULL in the database.
**Why human:** The empty-string sentinel chain (dockets[0] ?? '' -> body.source_docket or None -> DB NULL) is fully wired in code, but the DB NULL outcome is a state transition that cannot be confirmed by static analysis.

#### 3. Question Number Hint Remains Italic N/A After Save

**Test:** Enter a question number (e.g., "3") in the Question number field and click Save. Reload. Confirm the "Extracted:" hint row below Question number still shows italic "N/A" — it must NOT reflect "3".
**Expected:** hints.question_number is always null in load(), so the hint always shows italic N/A regardless of the operator-saved value.
**Why human:** The immutability of the hint through a real save/reload cycle is a runtime state invariant; code is correct (hints.question_number = null literal at line 132) but requires execution to confirm.

#### 4. Ready-to-Publish CTA Renders After ArgumentDetailsCard

**Test:** Navigate to a pipeline job where the linked argument has `resolved_at` set (meaning it has been resolved through the resolve step) but `published_at` is null (not yet published). Confirm the "Ready to publish" CTA block appears immediately after the ArgumentDetailsCard. Confirm the old static "Argument" preview card does NOT appear.
**Expected:** Only the ArgumentDetailsCard and standalone CTA block are visible. No duplicate Argument card, no "Edit argument metadata" link from the old card.
**Why human:** CTA depends on `liveJob.status === 'completed'` (live-polled value) and `argStatus === 'draft'` (derived from argument DB state). Both conditions require a real completed run with a draft-state argument to trigger.

## Gaps Summary

No gaps blocking goal achievement. All infrastructure (backend schemas, services, component, page wiring, gap-closure fixes) is fully implemented and wired. The 4 behavior-unverified items are present-and-wired truths whose correctness at runtime requires human confirmation through live UI testing — they are not code gaps.

The phase goal is achieved at the code level. Human verification of the 4 runtime behavior truths is required before the phase can be marked fully passed.

---

_Verified: 2026-07-02T18:00:00Z_
_Verifier: Claude (gsd-verifier)_
