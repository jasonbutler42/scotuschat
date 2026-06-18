---
status: resolved
trigger: "Discrepancy table UX — single Change button + typeahead candidates"
created: 2026-06-17T00:00:00Z
updated: 2026-06-18T00:00:00Z
resolved_by: "07-06-PLAN (HIT rows in discrepancies JSONB with auto_resolved=True) + 07-07-PLAN (HIT rows pre-dispositioned confirmed; single Change button; people-backed typeahead via server-loaded data.people; human verified all 5 checks approved 2026-06-17)"
---

## Current Focus

hypothesis: Two separate root causes confirmed — (1) resolve.py writes HIT rows with candidates:[] and auto_resolved:True, and the Svelte component renders Confirm+Override instead of a single Change button for HIT rows because no special HIT branch exists; (2) The typeahead datalist for HIT rows is always empty because candidates:[] is written for HITs by design in resolve.py, and the Svelte component does not load all people independently for HIT rows.
test: N/A — root causes confirmed via static analysis
expecting: N/A
next_action: diagnosed — return ROOT CAUSE FOUND

## Symptoms

expected: Auto-matched HIT rows show a single "Change" button. No explicit Confirm step. Clicking Change opens typeahead listing ALL existing people. Selecting one corrects the auto-match.
actual: (1) HIT rows show Confirm + Override buttons instead of single Change button. (2) Typeahead datalist on HIT rows shows only "Add new person" — no existing people.
errors: None (UI renders but with wrong pattern and empty candidate list)
reproduction: Run pipeline until resolve step pauses; open /admin/pipeline/{job_id}; observe HIT rows.
started: Phase 07 UAT test 10

## Eliminated

- hypothesis: People list API is not being called at all
  evidence: No separate people API call exists anywhere — candidates are embedded in the discrepancy JSONB written by the pipeline, not fetched by the page load
  timestamp: 2026-06-17

- hypothesis: The +page.server.ts load function fetches people but filters them for HIT rows
  evidence: load() only fetches job data — GET /api/admin/jobs/{id}. There is no separate people fetch in load(). The candidates list lives inside discrepancies JSONB on the job row.
  timestamp: 2026-06-17

- hypothesis: The Svelte component renders HIT rows differently from MISS rows in Column 3
  evidence: Disproved — Column 3 (action buttons) uses a SINGLE branch: if s?.disposition !== null show Override, else show Confirm+Correct div. There is no HIT vs MISS distinction in the button rendering logic at all. Both HIT (auto_resolved=True) and MISS (auto_resolved=None/null) rows get the same Confirm+Correct button pair until dispositioned.
  timestamp: 2026-06-17

## Evidence

- timestamp: 2026-06-17
  checked: pipeline/commands/resolve.py lines 232-249 (HIT path) and 254-275 (MISS path)
  found: HIT rows are appended to discrepancies with candidates:[] (empty list, explicitly set). Comment says "HIT rows need no candidates — operator confirms or overrides". MISS rows get the full people list in candidates.
  implication: The typeahead datalist for any HIT row will always be empty because candidates:[] is baked into the JSONB at pipeline time. The page load does not fetch all people separately to supplement HIT row candidates.

- timestamp: 2026-06-17
  checked: app/src/routes/admin/pipeline/[job_id]/+page.server.ts load function
  found: load() calls GET /api/admin/jobs/{id} only. Returns { job }. No people list is fetched. No supplemental data source for candidate names exists.
  implication: The Svelte component has zero access to "all people" for HIT rows. The only candidates available are row.candidates from the JSONB, which are [] for HITs.

- timestamp: 2026-06-17
  checked: +page.svelte Column 3 action button rendering (lines 553-618)
  found: Single conditional: if s?.disposition !== null → Override button; else → div with Confirm button (when auto_match_id exists) AND Correct button. The auto_resolved flag on the discrepancy row is never read. HIT rows (auto_match_id set, auto_resolved=True) get the exact same Confirm+Correct pair as MISS rows. There is no branch that renders a single "Change" button.
  implication: This is root cause 1. The component has no HIT-specific UX branch. The correct behavior — a single "Change" button, with the row pre-treated as accepted — is not implemented.

- timestamp: 2026-06-17
  checked: +page.svelte rowStates initialization ($effect lines 71-89)
  found: For ALL rows (HIT and MISS alike), rowStates[label].disposition is initialized to null. HIT rows start with person_id=row.auto_match_id (correctly set) but disposition=null. Because disposition is null, the Override button branch is not reached, and instead Confirm+Correct are shown.
  implication: HIT rows are not pre-dispositioned as "confirmed" at initialization time. They require an explicit Confirm click to transition disposition from null → 'confirmed'. This is the UX mismatch — the desired behavior is that HITs are implicitly accepted without a click.

- timestamp: 2026-06-17
  checked: +page.svelte getRowCandidates() helper (lines 268-271) and Column 2 typeahead datalist
  found: getRowCandidates() returns [...row.candidates, ...rowStates[label].extraCandidates]. For HIT rows, row.candidates is [] and extraCandidates starts as []. The datalist therefore renders zero candidate options (only the hardcoded "— Add new person —" option).
  implication: This is root cause 2. The typeahead for HIT rows is empty because candidates:[] is stored in JSONB for HITs, no supplemental people list is loaded by the page, and getRowCandidates() has no fallback to fetch or use all people.

- timestamp: 2026-06-17
  checked: api/schemas/admin_jobs.py PersonResponse and api/services/admin_jobs.py create_person_for_job
  found: PersonResponse declares role_name: Optional[str] = None but the Person ORM model has no role_name column (only role_id). create_person_for_job returns the Person ORM object directly. With from_attributes=True, Pydantic will serialize role_name as None always (field not on model). The addPerson action in +page.server.ts (line 97) returns { personCreated: True, person } — the person object will have role_name: null regardless of what role was created.
  implication: This is a separate bug (UAT test 11 scope) but also relevant: even when addPerson succeeds, the person returned won't carry role_name. Not the cause of the typeahead empty-candidates bug but explains why the corrected display (selectedPerson.role_name) won't show the role for newly-added people.

- timestamp: 2026-06-17
  checked: STATE.md decision log for [07-06]
  found: "[07-06]: HIT rows now in discrepancies JSONB with auto_resolved=True — operator must confirm all aliases before pipeline advances." This confirms the current implementation matches the Phase 07-06 plan. However the UAT report says the required UX is the opposite: auto-matched rows should be pre-accepted, with only a Change option if the operator wants to override.
  implication: The Phase 07-06 decision and implementation intentionally kept Confirm+Override for HIT rows, but the UAT truth statement requires a simpler Change-only UX. This is a spec mismatch, not a regression.

## Resolution

root_cause: |
  TWO SEPARATE ROOT CAUSES:

  Root Cause 1 — Wrong button UX for HIT rows:
  In +page.svelte, rowStates initialization sets disposition=null for ALL rows,
  including auto-resolved HITs. The Column 3 button rendering has no branch that
  checks auto_resolved. HIT rows therefore show the full Confirm+Correct pair
  (same as MISS rows) instead of a single Change button with implicit acceptance.
  The fix requires: (a) initialize HIT row disposition to 'confirmed' (or a new
  'auto_accepted' state) so they are pre-dispositioned, and (b) render a single
  "Change" button when the row has auto_resolved=True and is not yet being corrected.

  Root Cause 2 — Empty typeahead candidates for HIT rows:
  resolve.py writes candidates:[] for HIT rows (line 243, by design — "HIT rows need
  no candidates — operator confirms or overrides"). The +page.server.ts load() does
  not fetch all people to supplement HIT rows. getRowCandidates() returns only
  row.candidates + extraCandidates, both empty for HITs. The datalist therefore
  renders only the hardcoded "— Add new person —" option.
  The fix requires either: (a) resolve.py writes the full people list in candidates
  for HIT rows too (same as MISS rows), OR (b) +page.server.ts load() fetches all
  people from a GET /api/people endpoint and passes them as pageData.allPeople,
  and the Svelte component uses allPeople as the candidate list when row.candidates
  is empty (i.e., for HIT rows).

fix: not applied (diagnose-only mode)
verification: not applied
files_changed: []
