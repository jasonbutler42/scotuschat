# Phase 34: Blank case_name/docket_number validation - Research

**Researched:** 2026-07-14
**Domain:** Pydantic v2 PATCH validation and SvelteKit enhanced-form recovery
**Confidence:** HIGH

## User Constraints

### Docket collection and canonical value
- **D-01:** When `source_dockets` contains valid and blank entries, trim entries, drop blanks, de-duplicate valid values in first-seen order, and accept the result when the applicable minimum rule is satisfied.
- **D-02:** Normalize the collection before selecting the canonical docket. The first remaining valid entry becomes `source_docket`, even when blank entries preceded it.
- **D-03:** Explicit `null` for a required case-name or docket field is invalid. Field omission retains PATCH semantics and means “leave unchanged.”
- **D-04:** When an operator submits no docket pills, preserve the visibly empty attempted state after failure; do not silently restore the saved docket.
- **D-05:** The pill-based docket control must provide an equivalent client-side required check. Backend schema validation remains authoritative.

### Whitespace normalization
- **D-06:** Schema validators strip leading and trailing whitespace and return the normalized value. Otherwise-valid trimmed values are accepted; values empty after trimming are rejected.
- **D-07:** Preserve internal whitespace exactly. Do not collapse repeated internal spaces or otherwise rewrite case titles or docket text.
- **D-08:** Blank detection follows Python `str.strip()` semantics, including tabs, newlines, and recognized Unicode whitespace.

### Operator feedback and recovery
- **D-09:** Render required-value failures in each form's existing inline `role="alert"` region rather than adding a new error component or page-level banner.
- **D-10:** Use field-specific operator copy: **“Case name is required.”** and **“Add at least one docket.”**
- **D-11:** When multiple required fields fail, show every field-specific error together and move keyboard focus to the first invalid field.
- **D-12:** Preserve the full attempted submission after failure, including blank invalid values and all other submitted values, so the operator corrects only what failed.

### API validation contract
- **D-13:** Keep FastAPI/Pydantic's standard structured `422` validation-error envelope; do not introduce application-specific blank-field codes.
- **D-14:** Explicit null, empty strings, whitespace-only strings, and empty docket collections share the same missing-required-value classification.
- **D-15:** SvelteKit actions identify required-field failures from structured Pydantic error `loc` values, never by matching human-readable validation messages. Other `422` conditions retain their existing distinct handling.

### Agent's Discretion
- Choose whether explicitly supplied `source_dockets` must contain at least one nonblank docket at schema validation time or whether an equally strict PIPE-28-compatible enforcement point is more appropriate. The result must still make it impossible for either save path to clear the canonical docket.
- Choose whether a request that supplies disagreeing `source_docket` and `source_dockets` is rejected or uses the array as authoritative. The choice must be deterministic, tested, and preserve D-01 through D-05.
- Exact validator/helper placement, error parsing helper structure, focus implementation, and test organization are left to research and planning.

### Deferred Ideas

None — discussion stayed within phase scope.

## Summary

Phase 34 should move required-value normalization to `ArgumentUpdate` and `MetadataUpdate`, before either service can derive a slug, change a case dedup field, or clear `Argument.source_docket`. Both models currently use `Optional[...] = None`, while the services distinguish omission via `model_fields_set`; therefore the validator must run for explicitly supplied values, reject explicit `None`, and leave omitted fields untouched. [VERIFIED: `api/schemas/admin_arguments.py`, `api/services/admin_arguments.py`]

For metadata PATCHes, make `source_dockets` authoritative whenever supplied. Normalize each member with `str.strip()`, discard blank members, de-duplicate in first-seen order, then reject the collection if none remain. This exactly preserves the service's existing mixed-entry behavior while closing its current `normalized else None` corruption path. If only legacy `source_docket` is supplied, validate and trim it independently. If both are supplied, the normalized array wins; document and test that deterministic precedence. [VERIFIED: `api/services/admin_arguments.py`; Phase 34 D-01–D-03]

The frontend needs two distinct recovery paths. The Case form currently trims attempts before sending them and returns only a generic `error`, so it loses blank/raw attempts. The shared metadata actions also filter empty docket entries before sending, but an empty array still reaches the API and their failure payload already preserves `dockets`, `question_number`, and `argued_date`. Extend both paths to parse Pydantic `detail[]` by `loc`, return field-specific flags/messages, and preserve submitted values. `ArgumentDetailsCard` must focus `#docket-input` for required errors instead of its current alert focus. [VERIFIED: both `+page.server.ts` actions and `ArgumentDetailsCard.svelte`]

**Primary recommendation:** Implement strict schema-boundary validators, use normalized `source_dockets` as authoritative when present, and carry structured field-error state through each existing form without changing the FastAPI envelope.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Trim/reject required scalar fields | Pydantic request schemas | Services | Prevent invalid values before any write/slug/dedup logic. [VERIFIED: codebase] |
| Normalize and require docket collection | `MetadataUpdate` schema | Metadata service | One canonical representation enters all downstream logic. [VERIFIED: codebase] |
| Canonical docket selection | Metadata service | Schema | Existing service derives `source_docket` from the first normalized list item. [VERIFIED: codebase] |
| Map 422 fields to operator errors | SvelteKit server actions | Svelte components | API errors stay structured and UI copy remains presentation-owned. [VERIFIED: codebase] |
| Preserve attempts and focus invalid control | Svelte components/actions | `DocketPillInput` | Enhanced forms own recovery and visible client state. [VERIFIED: codebase] |

## Standard Stack

No new package is required. Use the installed Pydantic v2 `field_validator`/`model_validator` facilities, FastAPI's automatic request validation response, SvelteKit `fail`, Svelte 5 state/effects, and the existing `DocketPillInput`. [VERIFIED: `CLAUDE.md`, package manifests, codebase]

| Library/framework | Project version contract | Purpose |
|---|---:|---|
| Pydantic | v2 | Normalize and validate PATCH request fields. [VERIFIED: `CLAUDE.md`] |
| FastAPI | 0.115+ | Preserve automatic structured 422 responses. [VERIFIED: `CLAUDE.md`] |
| SvelteKit / Svelte | 2.x / 5 | Actions, enhanced forms, state restoration, and focus. [VERIFIED: `CLAUDE.md`, `app/package.json`] |

## Package Legitimacy Audit

Not applicable: Phase 34 installs no external packages.

## Architecture Patterns

### Request and recovery flow

```text
Native Case form ───────┐
                       ├─> SvelteKit action ─> PATCH schema validators
Pill metadata form ─────┘                         │
                                                 ├─ valid normalized model ─> existing service writes
                                                 └─ invalid ─> standard 422 detail[]
                                                                    │
Svelte component <─ fail(payload + raw attempted values + loc-derived errors) <─┘
       ├─ render exact messages in existing role=alert
       ├─ aria-invalid / aria-describedby on affected controls
       └─ focus first invalid control after DOM update
```

### Pattern 1: Validate explicit PATCH values without breaking omission

Use field validators that receive an explicitly supplied scalar, reject `None`, apply `str.strip()`, reject the empty result, and return the stripped string. Omitted fields retain their default and remain absent from `model_fields_set`; services continue using that set for PATCH behavior. Test both construction and `model_fields_set`. [VERIFIED: current schemas/services; Phase 34 D-03/D-06]

The clean implementation may keep `Optional[str] = None` for omission compatibility, with a `field_validator(..., mode="before")` that raises for explicit null. Do not change the service conditions to truthiness checks, because omission and explicit values are semantically different. [VERIFIED: current service PATCH pattern]

### Pattern 2: Normalize collections once, before canonical selection

The `source_dockets` validator should:

1. Reject explicit `None` when the field is supplied.
2. Iterate the supplied list, applying Python `str.strip()`.
3. Drop blank results and de-duplicate nonblank results in first-seen order.
4. Reject if the normalized list is empty.
5. Return the normalized list.

The service should then assign the returned list directly and set canonical `source_docket = source_dockets[0]`; it should no longer repeat normalization or contain an empty-to-`None` branch for validated requests. Legacy singular-only callers remain supported through the validated `source_docket`. When both fields exist, ignore the singular value and use the array as authoritative, matching the current `if source_dockets ... elif source_docket` control flow. [VERIFIED: current service; Phase 34 D-01/D-02]

### Pattern 3: Parse Pydantic locations, not messages

Add a small typed helper in the SvelteKit server layer (shared module if practical, otherwise identical local helper with tests) that accepts unknown JSON, verifies `detail` is an array, and extracts string/number `loc` arrays. A required case-name failure matches a terminal field of `case_name`; docket failures match `docket_number`, `source_docket`, or `source_dockets`. Never inspect `msg`. Preserve the Phase 33 structured 409 parser as a separate branch. [VERIFIED: current Phase 33 parser pattern; Phase 34 D-13/D-15]

### Pattern 4: Raw attempt preservation is separate from API normalization

For the Case action, capture raw form strings before any trimming and return them on every failure. Send the raw values to FastAPI so Pydantic is authoritative; successful response data is already normalized. Bind inputs to `form` attempted values when present, otherwise saved values. For pill metadata, retain `dockets: []` as a meaningful failed state: change truthy checks such as `if (form?.dockets)` to presence checks so an empty array re-seeds the component rather than restoring saved dockets. [VERIFIED: current actions and `ArgumentDetailsCard.svelte`]

### Pattern 5: Equivalent custom-control required behavior

`DocketPillInput` cannot rely on native `required`, because its visible text box is a pill-entry staging control and hidden inputs represent committed values. Expose required/error props plus a focus method or bindable element contract. At form submission, if editable and pills are empty, prevent submission, set the same docket error state, and focus the visible text input. Server-detected docket errors must drive the same visual and ARIA state. Enter must continue to prevent default and add a nonblank pill. [VERIFIED: `DocketPillInput.svelte`, UI-SPEC]

### Anti-Patterns to Avoid

- **Service-only validation:** invalid data can reach slug, collision, and canonical-docket logic; schema validation is the required authoritative boundary.
- **Message matching:** Pydantic wording can change; D-15 locks routing to `loc`.
- **Truthiness for failed docket state:** `[]` is the important attempted value and must not fall back to saved values.
- **Restoring server values after failure:** violates D-04/D-12 and forces re-entry of unrelated fields.
- **Focusing the alert for required failures:** Phase 33 conflict behavior focuses the alert, but Phase 34 required errors focus the first invalid control.
- **Using only HTML `required`:** it cannot protect direct API calls and is insufficient for the pill representation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| API error envelope | Custom error codes/envelope | FastAPI/Pydantic standard 422 `detail[]` | Locked by D-13; locations already identify fields. |
| Whitespace classification | Regex/ASCII-only blank test | Python `str.strip()` | Locked Unicode/whitespace semantics in D-08. |
| Form transport | New client fetch/state framework | Existing SvelteKit actions and `use:enhance` | Already preserves server-rendered failure state. |
| Docket UI | New collection widget | Existing `DocketPillInput` | Shared control already owns pills and hidden inputs. |

## Common Pitfalls

1. A normal `field_validator` can fail to run for an omitted default; that is desirable, but explicit `None` must still be observed and rejected. Prove omission and explicit-null separately. [VERIFIED: phase contract]
2. Validating only `source_docket` misses the live forms, which send `source_dockets`. [VERIFIED: both metadata actions]
3. Leaving normalization duplicated in the service risks schema/service drift. Make the validated collection the service input. [VERIFIED: current duplication]
4. The Case action currently trims before submission, which prevents exact attempted-state preservation. Capture and return raw values. [VERIFIED: argument page action]
5. `ArgumentDetailsCard` currently uses `if (form?.dockets)`, so empty attempts do not replace saved dockets. Use key/presence semantics. [VERIFIED: component]
6. The component currently focuses the alert for every failure. Branch required errors to the field while retaining conflict-alert focus. [VERIFIED: component]
7. Multiple Pydantic errors must be accumulated, not handled with `else if`, so both required messages render and the first field wins focus. [VERIFIED: D-11]
8. Do not accidentally make `question_number` or `argued_date` required; their optional/nullable behavior is explicitly out of scope. [VERIFIED: context]
9. Keep native Case docket and metadata source dockets distinct in locations and UI ownership. [VERIFIED: existing two-card architecture]

## Security and ASVS L1

- **V5 Validation, Sanitization and Encoding:** authoritative Pydantic validation prevents null/blank values from reaching database writes and derived identifiers; retain output escaping through Svelte defaults. [VERIFIED: codebase architecture]
- **V4 Access Control / IDOR:** preserve server-derived route IDs and existing admin-token calls; no form-provided argument ID is introduced. [VERIFIED: current actions]
- **V7 Error Handling:** return standard sanitized validation details and existing generic handling for unrelated failures; never expose raw database exceptions. [VERIFIED: Phase 33 contract]
- **V14 Configuration:** no dependency, environment, migration, or deployment configuration change is required. [VERIFIED: phase scope]

No new threat-model mitigation beyond strict input validation and safe error routing is required. The plan should still include its normal ASVS L1 threat-model block and verify direct API callers cannot bypass the client check.

## Test Strategy

### Backend schema tests

- `ArgumentUpdate`: omission accepted and absent from `model_fields_set`; explicit null, `""`, spaces, tabs/newlines, and Unicode-whitespace-only values rejected for `case_name` and `docket_number`; outer whitespace trimmed; repeated internal whitespace preserved.
- `MetadataUpdate`: same scalar cases for `case_name` and `source_docket`; `source_dockets=None`, `[]`, all-blank arrays rejected; mixed blank/valid input normalized; duplicates removed first-seen; first valid docket canonical downstream.
- Both singular and array supplied: array is authoritative, including when values disagree.
- Confirm field allow-lists remain unchanged.

### Backend route/service tests

- Invalid direct PATCH requests return 422 with standard `detail` entries whose `loc` ends in the correct field; services are not called for route-level validation failures.
- Valid trimmed values are what the service writes; empty collection cannot set `source_dockets`/`source_docket` to null.
- Omitted required fields continue to leave stored values unchanged.
- Existing collision handling (slug/docket 422 and duplicate-pair 409) remains distinct.

### SvelteKit/component verification

- Case action preserves raw blank case/docket plus valid companion value and maps `loc` to both exact messages.
- Both metadata actions preserve `dockets: []`, question number, and argued date on 422 and map `source_dockets` location to the docket message.
- Shared card renders the exact docket copy, `aria-invalid`, `aria-describedby`, red border, and focuses the docket input after update.
- Case form renders one or both messages in field order, retains attempted values, and focuses case name before docket.
- Client submission with zero pills is prevented; readonly mode has no required behavior; Enter still adds a pill without submitting.
- Run backend targeted pytest suites, then the broader API suite; run `npm run check` for frontend type/accessibility validation. The repository has no established frontend unit-test runner, so component behavior should be covered by source-level regression tests only if that is the existing project convention, supplemented by conversational/browser UAT. [VERIFIED: `app/package.json`]

## Planning Guidance

Use two implementation plans unless the planner finds a compelling dependency reason to split further:

1. **Backend contract:** schema validators, deterministic array precedence, simplified safe service write path, and schema/route/service tests.
2. **Operator recovery:** structured 422 parser, Case form attempted-state/error/focus behavior, shared pill control client validation, both metadata actions, accessibility state, and frontend checks/UAT.

Wave 2 should depend on Wave 1 because frontend parsing must target the actual validated locations. No migration, package install, AI spec, pipeline command, or public-site change belongs in this phase.

## Sources

### Primary (HIGH confidence)
- `.planning/phases/34-blank-case-name-docket-validation/34-CONTEXT.md` — locked decisions and scope.
- `.planning/phases/34-blank-case-name-docket-validation/34-UI-SPEC.md` — approved interaction/accessibility contract.
- `.planning/REQUIREMENTS.md` PIPE-28 and `.planning/ROADMAP.md` Phase 34 — acceptance contract.
- `api/schemas/admin_arguments.py`, `api/services/admin_arguments.py`, `api/routers/admin.py` — schema and write behavior.
- `app/src/routes/admin/arguments/[id]/+page.server.ts`, `app/src/routes/admin/pipeline/[job_id]/+page.server.ts` — action request/error behavior.
- `app/src/lib/components/ArgumentDetailsCard.svelte`, `app/src/lib/components/DocketPillInput.svelte` — shared UI state and focus behavior.
- `.planning/phases/33-metadata-update-unique-constraint-guard/33-CONTEXT.md` — preceding structured-error and preservation contract.

### Secondary
- None required; this phase uses established local framework patterns and adds no dependencies.

## Metadata

**Confidence breakdown:**
- Stack and existing behavior: HIGH — verified directly in repository files.
- Recommended schema/service split: HIGH — follows locked decisions and the current PATCH architecture.
- Frontend focus/attempt preservation: HIGH — dictated by the approved UI contract and current component implementation.

**Research date:** 2026-07-14
**Valid until:** 2026-08-13 (re-check if Phase 33/34-adjacent forms or schemas change first)
