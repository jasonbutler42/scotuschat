---
status: diagnosed
trigger: "create-person-discards-name-parts"
created: 2026-07-09T12:10:00Z
updated: 2026-07-09T12:35:00Z
---

## Current Focus

hypothesis: CONFIRMED — the create route's form (+page.svelte) renders First/Middle/Last/Suffix name-part inputs inside <form id="create-form">, but the `create` action in new/+page.server.ts only destructures `full_name` and `is_justice` from the submitted FormData (never calls formData.get('first_name'/'middle_name'/'last_name'/'name_suffix')), and the PersonCreateRequest schema + create_person service function only accept/persist full_name+is_justice by design (D-08). The name-part values are discarded at the SvelteKit server-action layer — they never reach the FastAPI call at all.
test: Traced formData reads in new/+page.server.ts create action vs. the fields rendered/named in new/+page.svelte vs. the [id]/+page.server.ts save action (working path) vs. api/schemas/admin_people.py PersonCreateRequest vs. api/services/admin_people.py create_person.
expecting: N/A — root cause confirmed via direct code reading, not a runtime experiment.
next_action: DIAGNOSED — root cause confirmed. Return structured result (goal: find_root_cause_only).

## Symptoms

expected: Creating a person with both Full Name and name-part fields filled in should persist all of them, matching the behavior of the [id] editor's save action.
actual: User reported (verbatim): "What is a real bug is that if I enter something into full name AND into the component parts it only saves the full name and discards the components. That only happens on person creation; it saves properly on saving an existing person." (Note: name-part-only auto-backfill of Full Name is a separate, already-captured future enhancement — BACKLOG.md B-019 — NOT part of this bug.)
errors: None reported — person is created successfully; name-part fields are simply missing afterward.
reproduction: Test 3 in UAT (Phase 27, .planning/phases/27-people-admin/27-UAT.md) — on /admin/people/new, fill in Full Name plus First/Middle/Last/Suffix, submit, then check the created person's editor.
started: Discovered during UAT for Phase 27 (People Admin), 2026-07-09.

## Eliminated

- hypothesis: "FastAPI/create_person service silently drops name-part fields even when sent by the client"
  evidence: "Irrelevant to reproduction — the SvelteKit `create` action in new/+page.server.ts never reads first_name/last_name/middle_name/name_suffix from FormData in the first place, so they are never included in the JSON body POSTed to FastAPI. The backend never receives them to drop. (Separately, PersonCreateRequest/create_person also only accept full_name+is_justice by design — see Evidence — but that is a second, compounding restriction, not the point where the reported data loss first occurs.)"
  timestamp: 2026-07-09

## Evidence

- timestamp: 2026-07-09
  checked: "app/src/routes/admin/people/new/+page.svelte lines 73-154 (Identity card)"
  found: "Full Name input (name='full_name') plus a 4-column name-parts grid with First name (name='first_name'), Middle name (name='middle_name'), Last name (name='last_name'), and Suffix (name='name_suffix') inputs, ALL inside <form id='create-form' method='POST' action='?/create'>. Values are bound to data.person.first_name/middle_name/last_name/name_suffix (all null on the blank create form) but are ordinary editable text inputs with real `name` attributes that submit with the form."
  implication: "The rendered UI gives the operator every reason to believe filling in these fields will persist them — there is no visual cue (unlike Birth Date/Tenure, which show a WR-03-flagged discard risk) that they are inert on this route."

- timestamp: 2026-07-09
  checked: "app/src/routes/admin/people/new/+page.server.ts lines 56-95 (create action)"
  found: "const formData = await request.formData(); then only `full_name` and `is_justice` are read via formData.get(...). No formData.get('first_name'/'middle_name'/'last_name'/'name_suffix') anywhere in the function. The POST body sent to FastAPI is JSON.stringify({ full_name, is_justice }) — exactly two keys."
  implication: "This is the exact point where the name-part values are discarded. They are present in the submitted FormData (per the form's `name` attributes) but the action code never reads them, so they never make it into the outbound fetch body."

- timestamp: 2026-07-09
  checked: "app/src/routes/admin/people/[id]/+page.server.ts lines 131-184 (save action — the working comparison path)"
  found: "The [id] editor's `save` action explicitly reads formData.get('first_name'/'last_name'/'middle_name'/'name_suffix'), trims each, coerces '' to null, and includes all four in the PATCH body sent to FastAPI (body: JSON.stringify({ full_name, tenures, first_name, last_name, middle_name, name_suffix, is_justice, birthdate })). This confirms the [id] route's correct behavior and shows exactly what's missing from the create action by comparison."
  implication: "The two actions are not symmetric. [id]'s save action was built to carry all Identity-card fields through to the PATCH; new's create action was deliberately scoped down to only full_name+is_justice per D-08, but D-08's own text only calls out tenure/bio/photo/birthdate as deferred — it does not mention structured name parts — yet the implementation defers those too, silently, with no operator-facing signal."

- timestamp: 2026-07-09
  checked: "api/schemas/admin_people.py lines 132-146 (PersonCreateRequest) and api/services/admin_people.py lines 461-486 (create_person)"
  found: "PersonCreateRequest has exactly two fields: full_name: str and is_justice: bool. Its docstring explicitly states 'structured name parts' are 'filled in later via the existing PATCH ... update flow, not at creation time.' create_person's docstring likewise states 'Only full_name and is_justice are set on the new row — first_name, last_name, middle_name, name_suffix ... are left at their column defaults (None).'"
  implication: "Even if the SvelteKit action were fixed to forward first_name/middle_name/last_name/name_suffix, the backend schema and service function would need a matching change to accept and persist them — this is a second, compounding layer of the same restriction, not an independent bug. Both layers must change together for a fix."

- timestamp: 2026-07-09
  checked: ".planning/phases/27-people-admin/27-CONTEXT.md D-08 and .planning/phases/27-people-admin/27-REVIEW.md WR-03"
  found: "D-08: 'Minimum required to save a new person: full name and a Bench/Advocate choice ... Everything else (tenure, bio, photo, birthdate) is optional and filled in later on the same page.' D-08's own enumerated deferred-fields list does NOT include first_name/last_name/middle_name/name_suffix. WR-03 (an already-flagged, unresolved code-review finding from this same phase) documents the identical discard pattern for Birth Date and Tenure Period inputs specifically, and explicitly calls the current create-route behavior a UX defect requiring either disabling those inputs or adding a warning — but WR-03's scope is limited to birthdate/tenures and does not mention the name-part fields."
  implication: "The UAT-reported bug is a previously-unflagged sibling of WR-03: the same 'form renders fields the create action silently drops' pattern, but for first_name/middle_name/last_name/name_suffix rather than birthdate/tenures. Given D-08's text doesn't call out name-parts as intentionally deferred, this looks like an implementation gap/oversight in Plan 27-06 (and the corresponding schema/service work in 27-01/27-03) rather than a deliberate, documented scope decision — unlike birthdate/tenures, which D-08 explicitly names."

## Resolution

root_cause: >
  The /admin/people/new create form renders editable First/Middle/Last/Suffix
  name-part inputs (with real `name` attributes) alongside Full Name inside
  the same <form id="create-form">, implying they will be saved. But three
  layers of the create path silently exclude them: (1) the SvelteKit `create`
  action in app/src/routes/admin/people/new/+page.server.ts reads only
  `full_name` and `is_justice` from the submitted FormData and never reads
  first_name/middle_name/last_name/name_suffix, so those values never leave
  the browser's form submission alive past the server action; (2) the
  PersonCreateRequest Pydantic schema (api/schemas/admin_people.py) only
  declares full_name/is_justice fields; (3) the create_person service
  function (api/services/admin_people.py) only sets full_name/is_justice on
  the new Person row, leaving first_name/last_name/middle_name/name_suffix at
  their column defaults (None) by design. This is a scoped-down create path
  per decision D-08 ("minimum required to save a new person: full name and a
  Bench/Advocate choice ... everything else is optional and filled in later"),
  but D-08's own text enumerates only tenure/bio/photo/birthdate as deferred —
  it does not mention structured name parts — and there is no UI signal (no
  disabling, no warning) that the name-part inputs are inert on this route,
  unlike the flagged-but-unfixed WR-03 finding for Birth Date/Tenure. The [id]
  editor's `save` action (app/src/routes/admin/people/[id]/+page.server.ts)
  is the correct reference: it reads and forwards all four name-part fields
  in its PATCH body, which is why editing an existing person persists them
  correctly while creating a new one does not.
fix: "Not implemented (goal: find_root_cause_only). Fix requires changes at all three layers found above: (a) new/+page.server.ts create action must read first_name/middle_name/last_name/name_suffix from FormData (trim, coerce '' to null) and include them in the POST body — mirroring [id]/+page.server.ts's save action; (b) PersonCreateRequest schema must add the four fields as Optional[str] = None; (c) create_person service must set them on the new Person row (or reuse update_person's model_fields_set-based partial-update pattern per CR-01 if partial-omission semantics matter here too). A decision is also needed on whether this is a bug fix (align with [id] behavior, no D-08 change needed since D-08 never named name-parts as deferred) or a scope amendment to D-08 (explicitly add name-parts to the deferred list and instead disable/hide those inputs on create, matching WR-03's proposed remedy) — recommend the former since the UAT reporter's expectation is parity with the [id] editor, not further deferral."
verification: ""
files_changed: []
