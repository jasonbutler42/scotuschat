---
status: resolved
trigger: "Add New Person — Save Silently Fails: Save Person button flashes Saving... then nothing happens, form stays visible, person not persisted"
created: 2026-06-17T00:00:00Z
updated: 2026-06-18T00:00:00Z
goal: find_root_cause_only
resolved_by: "07-07-PLAN — AddNewPersonForm converted from raw fetch to use:enhance; SvelteKit handles devalue deserialization automatically; human verified (all 5 checks approved 2026-06-17)"
---

## Current Focus

hypothesis: "handleAddPerson calls res.json() and reads envelope.data.person directly, but SvelteKit serializes the action response data field using devalue.stringify() — not plain JSON — so envelope.data is a devalue-encoded string, not an object. Accessing .person on a string yields undefined, so the success branch never fires."
test: "Traced SvelteKit internals: actions.js stringify_action_response → devalue.stringify; forms.js deserialize → devalue.parse. Compared against the raw fetch in handleAddPerson which only calls res.json()."
expecting: "envelope.data is a devalue string like \"[{personCreated:true,person:{id:1,...}}]\" at runtime. envelope.data.person is undefined. if (person) is false. finallyblock executes, submittingNewPerson = false, button reverts, form stays open."
next_action: "DIAGNOSED — root cause confirmed. Return structured result."

## Symptoms

expected: "Selecting '— Add new person —' in the discrepancy table reveals a form with Full Name and Role fields. Submitting it creates the person server-side, dismisses the form, and auto-selects the new person in that row."
actual: "Clicking Save Person briefly changes the button text to 'Saving...' then nothing else happens. The form stays visible; no selection is made in the row. After a page refresh, the person was NOT persisted."
errors: "No visible JS error. Network request may succeed (2xx) but client-side state is never updated."
reproduction: "Open a paused job, click Correct on a row, type '— Add new person —' in typeahead, fill Full Name and Role, click Save Person."
started: "Since initial implementation in plan 07-05. Plan 07-06 added x-sveltekit-action header which correctly gets JSON back from the server, but did not fix the devalue deserialization problem."

## Eliminated

- hypothesis: "Server-side FastAPI create_person_for_job fails silently"
  evidence: "Server action reads FormData, calls FastAPI POST /api/admin/jobs/{id}/people, returns {personCreated:true, person} on success. Even if FastAPI returns an error, the failure branch in handleAddPerson sets newPersonError and stops — it does not cause the 'silent' behavior described."
  timestamp: 2026-06-17

- hypothesis: "x-sveltekit-action header missing so SvelteKit returned HTML redirect instead of JSON"
  evidence: "Plan 07-06 added the header. The fetch now sends 'x-sveltekit-action: true'. SvelteKit sees this (via is_action_json_request which checks Accept: application/json — NB: the raw fetch does NOT set Accept: application/json, only x-sveltekit-action). Checking SvelteKit internals: is_action_json_request checks Accept header via negotiate(), NOT the x-sveltekit-action header. This means the raw fetch may not actually trigger the JSON path."
  timestamp: 2026-06-17

- hypothesis: "PersonResponse.role_name is always null because Person ORM model lacks a role_name attribute"
  evidence: "True — Person model has only role_id, not role_name. PersonResponse.model_config = from_attributes, so role_name reads from Person ORM and gets None. BUT this only makes role_name null in the response, it does not cause the failure. The person object itself (id, full_name) would still be returned."
  timestamp: 2026-06-17

## Evidence

- timestamp: 2026-06-17
  checked: "app/src/routes/admin/pipeline/[job_id]/+page.svelte — handleAddPerson function (lines 224-266)"
  found: "Uses raw fetch with 'x-sveltekit-action: true' header and no 'Accept: application/json' header. Calls res.json() then reads envelope.data.person directly."
  implication: "The code assumes envelope.data is a plain JS object after JSON.parse. This assumption is wrong — see devalue finding below."

- timestamp: 2026-06-17
  checked: "app/node_modules/@sveltejs/kit/src/runtime/server/page/actions.js — handle_action_json_request and stringify_action_response"
  found: "On success (line 78-88): action_json({ type: 'success', status: 200, data: stringify_action_response(data, ...) }). stringify_action_response calls devalue.stringify(value, encoders) — NOT JSON.stringify. The 'data' field in the HTTP response is a devalue-encoded string."
  implication: "res.json() correctly parses the outer envelope object, but envelope.data is a devalue string like \"[{\\\"personCreated\\\":true,...}]\" rather than a JS object. Accessing envelope.data.person on a string yields undefined."

- timestamp: 2026-06-17
  checked: "app/node_modules/@sveltejs/kit/src/runtime/app/forms.js — deserialize function (lines 32-42)"
  found: "export function deserialize(result) { const parsed = JSON.parse(result); if (parsed.data) { parsed.data = devalue.parse(parsed.data, ...decoders); } return parsed; }. The correct deserialization pipeline is: JSON.parse the text, then devalue.parse the data field."
  implication: "handleAddPerson must use deserialize(await res.text()) instead of res.json(). OR use the $app/forms enhance mechanism instead of raw fetch."

- timestamp: 2026-06-17
  checked: "app/node_modules/@sveltejs/kit/src/runtime/server/page/actions.js — is_action_json_request (lines 14-21)"
  found: "function is_action_json_request(event) { const accept = negotiate(event.request.headers.get('accept') ?? '*/*', ['application/json', 'text/html']); return accept === 'application/json' && event.request.method === 'POST'; }. This checks the Accept header, NOT the x-sveltekit-action header."
  implication: "The raw fetch in handleAddPerson does NOT set 'Accept: application/json'. SvelteKit may not route the request through handle_action_json_request. However, the use:enhance path in forms.js (line 173) sets both Accept: application/json AND x-sveltekit-action: true. The raw fetch is missing Accept: application/json — so the server may return an HTML redirect rather than JSON, causing res.json() to throw or return unexpected data."

- timestamp: 2026-06-17
  checked: "app/node_modules/@sveltejs/kit/src/runtime/app/forms.js — enhance submit handler (lines 170-201)"
  found: "enhance sets: headers = new Headers({ accept: 'application/json', 'x-sveltekit-action': 'true' }). Then result = deserialize(await response.text()). Both headers are required; only the deserialized result has data as a JS object."
  implication: "The raw fetch in handleAddPerson sets only x-sveltekit-action: true but not Accept: application/json. TWO bugs exist: (1) missing Accept header means server may return HTML not JSON; (2) even if JSON returns, data field is devalue-encoded and must be deserialized with deserialize() not res.json()."

- timestamp: 2026-06-17
  checked: "+page.server.ts addPerson action return value (line 97)"
  found: "return { personCreated: true, person }; — where person is the FastAPI JSON response (a plain dict after res.json()). This is valid and serializable by devalue."
  implication: "Server side is correct. Person creation works and returns data. The failure is entirely on the client-side deserialization path."

- timestamp: 2026-06-17
  checked: "PersonResponse schema vs Person ORM model"
  found: "PersonResponse has role_name: Optional[str] = None with from_attributes=True. Person ORM model has role_id (int FK) but no role_name attribute. So PersonResponse.role_name is always None when constructed from a Person ORM object."
  implication: "Secondary bug: role_name is always null in the addPerson response even when a role was set. This means the new person shows no role in the dropdown after being created. NOT the cause of the primary silent fail, but a companion defect in the same flow."

## Resolution

root_cause: "handleAddPerson uses raw fetch with two compounding errors that prevent the success branch from ever executing: (1) The Accept: application/json header is missing, so SvelteKit's is_action_json_request() returns false and the server returns an HTML redirect response instead of a JSON action envelope — causing res.json() to either throw or parse the redirect HTML as broken JSON; (2) Even if Accept were set correctly, the code does res.json() then reads envelope.data.person directly, but SvelteKit serializes the action data field with devalue.stringify(), not JSON.stringify() — so envelope.data is a devalue-encoded string, not an object, and .person on it is undefined. Either bug alone is sufficient to cause the silent fail. Together they guarantee it."
fix: "Replace the raw fetch in handleAddPerson with SvelteKit's deserialize() from $app/forms. Set both headers (Accept: application/json AND x-sveltekit-action: true) and call deserialize(await res.text()) instead of res.json(). Alternatively — and more robustly — convert the AddNewPersonForm to use a <form method='POST' action='?/addPerson' use:enhance={...}> element with a custom enhance callback, which handles both headers and deserialization automatically."
verification: ""
files_changed: []
