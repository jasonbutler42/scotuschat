# Phase 33: update_argument_metadata unique-constraint guard - Research

**Researched:** 2026-07-14
**Domain:** PostgreSQL composite uniqueness across FastAPI/SQLAlchemy writers and SvelteKit operator feedback
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### HTTP conflict contract
- **D-01:** A docket/question collision returns **\`409 Conflict\`**, not \`422\`.
- **D-02:** The response uses FastAPI's structured \`detail\` object with a stable \`code\` of \`duplicate_argument\`, a clear human-readable \`message\`, and \`conflicting_argument_id\`.
- **D-03:** The message identifies the submitted pair: **“An argument already uses docket {docket}, question {number}. Open conflicting argument.”** The final phrase is rendered as a link to \`/admin/arguments/{conflicting_argument_id}\` that opens in a new tab.

### Operator feedback and recovery
- **D-04:** Render the collision in the existing inline \`role="alert"\` area inside \`ArgumentDetailsCard.svelte\`; do not add a separate page-level banner. Because both admin routes reuse this component, both surfaces must behave identically.
- **D-05:** Preserve every submitted value after the failed save — docket pills, question number, and argued date — so the operator can compare or correct the attempted values.
- **D-06:** Move keyboard focus to the collision alert after the failed save. The conflicting-record link must remain keyboard accessible and open in a new tab using the safe external-tab attributes appropriate for the component.

### Guard consistency
- **D-07:** Use a pre-write existence check for precise conflict data **plus** an \`IntegrityError\` fallback for race safety. A pre-check alone is insufficient.
- **D-08:** Evaluate the **final combined pair** on partial PATCHes: combine submitted values with the argument's stored values and exclude the current argument row from the collision query. An unchanged save must not conflict with itself.
- **D-09:** Audit every code path that writes \`source_docket\` and/or \`question_number\` against the same uniqueness predicate. HTTP metadata saves use the new \`409\` contract; offline ingest/import paths retain their existing channel-specific duplicate handling rather than being forced into HTTP wording.
- **D-10:** In the fallback, rollback first and map only the named \`uq_arguments_source_docket_question\` violation to \`duplicate_argument\`. Other constraint failures must remain sanitized and separately identifiable; they must not be mislabeled as duplicates or expose raw asyncpg/database text.

### Agent's Discretion
- Exact helper/function placement for the shared collision predicate and conflict payload construction.
- Internal logging structure for sanitized non-duplicate constraint failures.
- Test file organization, provided coverage proves the service pre-check, router fallback, both SvelteKit actions, shared component behavior, partial-update/self-exclusion rules, and the existing ingest/import guarantees.

### Deferred Ideas (OUT OF SCOPE)

### Reviewed Todos (not folded)
- **Edit affordance on utterances and speaker popover** — explicitly kept out of Phase 33. It was moved from the recurring pending-todo queue to backlog Phase 999.9 so it can be prioritized later through \`$gsd-review-backlog\`.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PIPE-27 | Saving argument metadata that collides with an existing \`(source_docket, question_number)\` returns a clean 409/422 instead of an unhandled 500. | Locked D-01 narrows this to 409. The shared final-pair predicate, named-constraint fallback, structured response, two action adapters, shared alert, and behavioral tests below cover the complete path. [VERIFIED: .planning/REQUIREMENTS.md, 33-CONTEXT.md] |
</phase_requirements>

## Summary

The database already has the correct authority: \`Argument.__table_args__\` names the composite constraint \`uq_arguments_source_docket_question\` over \`source_docket\` and \`question_number\`. Both columns are nullable, so a collision is possible only when the effective final pair is concrete. The admin service currently computes normalized update values and commits without checking that pair; the router catches every \`IntegrityError\` and reduces it to an unstructured \`constraint_violation\`. [VERIFIED: api/models/models.py, api/services/admin_arguments.py, api/routers/admin.py]

The planner should make one service-level collision query the canonical predicate: accept a concrete docket/question pair, optionally exclude an argument id, and return the conflicting id. The metadata path must derive its final pair from the already-loaded row plus the normalized/parsed values it will actually write, run the query before any UPDATE, and surface a domain result/exception containing the pair and id. The router must additionally catch commit-time \`IntegrityError\`, rollback before any query, identify the named constraint through the asyncpg cause chain, and only then re-query the same final pair to construct the same conflict object. [VERIFIED: 33-CONTEXT.md D-07/D-08/D-10; installed SQLAlchemy asyncpg dialect and asyncpg 0.31.0 introspection]

All four writers require explicit treatment. Admin PATCH gains pre-check plus race fallback. Ingest retains its CLI \`ValueError("Duplicate argument...")\` behavior but should classify only the named constraint. ConvoKit retains next-question selection plus its distinct conflict counter, likewise narrowing its fallback to the named constraint. Parse can fill \`source_docket\` on a row whose question is already set, thereby completing a colliding pair; it needs the shared pre-check and named-constraint fallback with its existing offline failure semantics. [VERIFIED: pipeline/commands/ingest.py, import_convokit.py, parse.py]

**Primary recommendation:** Build a small shared backend uniqueness seam (final-pair computation, conflict lookup, named-constraint recognition, and structured conflict payload), route every writer through it without changing channel-specific UX, then adapt both SvelteKit actions to preserve the full submission and let the shared card own alert rendering and focus.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Uniqueness authority | Database / Storage | API / Backend | PostgreSQL constraint is the race-safe authority; service pre-check supplies precise conflict data. [VERIFIED: api/models/models.py; D-07] |
| Final-pair and self-exclusion logic | API / Backend | Database / Storage | Only the service knows stored values plus normalized partial PATCH semantics; SQL supplies exclusion and lookup. [VERIFIED: admin_arguments.py; D-08] |
| HTTP 409 mapping and sanitization | API / Backend | — | FastAPI router owns status/detail and transaction recovery. [VERIFIED: admin.py; D-01/D-02/D-10] |
| SvelteKit action adaptation | Frontend Server (SSR) | API / Backend | Server actions call FastAPI, validate the structured detail, and return typed form state. [VERIFIED: both +page.server.ts files] |
| Inline alert, recovery values, and focus | Browser / Client | Frontend Server (SSR) | Shared Svelte component renders both surfaces; action data supplies conflict and submitted values. [VERIFIED: ArgumentDetailsCard.svelte; D-04/D-06] |
| Offline duplicate reporting | API / Backend | Database / Storage | CLI/import channels keep their established ValueError/counter/log behavior while using the same predicate. [VERIFIED: ingest.py, import_convokit.py; D-09] |

## Standard Stack

### Core

| Library | Project Version | Purpose | Why Standard Here |
|---------|-----------------|---------|-------------------|
| SQLAlchemy | requirement \`>=2.0\`; installed 2.x | Async selects/updates, \`IntegrityError\`, transaction rollback | Existing data-access layer; no new abstraction or package is needed. [VERIFIED: requirements.txt, codebase imports] |
| asyncpg | requirement \`>=0.29\`; installed 0.31.0 | PostgreSQL driver diagnostics including \`constraint_name\` | Existing SQLAlchemy dialect driver; its underlying PostgreSQL exception exposes the named constraint. [VERIFIED: requirements.txt and local runtime introspection] |
| FastAPI | requirement \`>=0.115\` | Structured \`HTTPException(detail={...})\` response | Existing router contract and locked D-02. [VERIFIED: requirements.txt, api/routers/admin.py] |
| SvelteKit / Svelte | package ranges \`^2.21.0\` / \`^5.30.0\` | Form actions, failure data, shared reactive alert/focus | Existing frontend stack and both current operator surfaces. [VERIFIED: app/package.json] |
| pytest / pytest-asyncio / httpx | existing test stack | Service, route, writer, and source-contract regression tests | Existing backend tests and ASGI client fixtures already use these tools. [VERIFIED: api/tests and pipeline/tests] |

### Supporting

No new package is required. Use existing SQLAlchemy expressions, FastAPI responses, Svelte component state, and pytest infrastructure. [VERIFIED: codebase audit]

## Package Legitimacy Audit

Not applicable: Phase 33 should install no external packages. [VERIFIED: recommended architecture uses only existing dependencies]

## Writer Audit and Required Disposition

| Writer | Current Behavior | Required Phase 33 Treatment |
|--------|------------------|-----------------------------|
| \`api/services/admin_arguments.update_argument_metadata\` | Normalizes docket array, parses question text, updates, commits; no pre-check. [VERIFIED: lines 818-909] | Compute effective final pair after normalization, self-excluding pre-check before writes, raise/return conflict with id, retain commit so router can catch races. |
| \`api/routers/admin.update_argument_metadata\` | Rolls back every \`IntegrityError\`, returns generic string 409. [VERIFIED: lines 1087-1114] | Catch domain pre-check conflict; on \`IntegrityError\`, rollback first, classify exact named constraint, recompute/query conflict, return structured duplicate detail; sanitize other constraints separately. |
| \`pipeline/commands/ingest.run_ingest\` | Inserts concrete pair, converts any flush \`IntegrityError\` to duplicate \`ValueError\`. [VERIFIED: lines 398-415] | Preserve CLI wording/exception, but map only \`uq_arguments_source_docket_question\`; re-raise or separately sanitize other integrity failures. Existing idempotency regression must stay green. |
| \`pipeline/commands/import_convokit._import_conversation\` | Uses \`max(question)+1\`; catches any flush \`IntegrityError\`, rolls back, increments \`docket_question_conflict\`. [VERIFIED: lines 308-330, 425-465] | Preserve next-number and distinct counter, but classify only named constraint as docket/question conflict. Other failures remain generic conversation errors/sanitized logs. |
| \`pipeline/commands/parse.run_parse\` | If cover has primary docket, conditionally fills \`source_docket\` only when NULL; no uniqueness handling. [VERIFIED: lines 367-376] | Before fill, load effective question and run shared predicate excluding current id. Keep operator-entered docket protection. Add named-constraint race fallback around the transaction/channel boundary; do not use HTTP wording. |

The repo-wide search found no other production assignment/update of either constrained column. Admin job services only read/carry arguments; public services only read. [VERIFIED: repo-wide \`rg source_docket|question_number\` audit]

## Architecture Patterns

### System Architecture Diagram

\`\`\`text
submitted PATCH
    |
    v
normalize docket list + parse question exactly as write path
    |
    v
combine submitted fields with stored Argument fields
    |
    +-- either value NULL --------------------------> no collision pre-check
    |
    v
SELECT conflicting Argument.id
WHERE pair matches AND id != current_id
    |
    +-- found --> domain duplicate --> router 409 structured detail
    |
    v
perform UPDATE(s) and COMMIT
    |
    +-- success ------------------------------------> {"success": true}
    |
    +-- IntegrityError --> ROLLBACK --> inspect named constraint
                               |
                               +-- target constraint --> re-query pair --> same 409 detail
                               |
                               +-- other constraint --> sanitized distinct constraint error

SvelteKit action receives 409 detail
    |
    v
fail(409, conflict + dockets + question_number + argued_date)
    |
    v
shared ArgumentDetailsCard: preserve values, render inline alert/link, focus alert
\`\`\`

### Pattern 1: One canonical concrete-pair lookup

Use a helper in \`api/services/admin_arguments.py\` (or a narrowly shared service module if pipeline imports would otherwise create a cycle):

\`\`\`python
async def find_argument_pair_conflict(
    db: AsyncSession,
    docket: str | None,
    question: int | None,
    *,
    exclude_argument_id: int | None = None,
) -> int | None:
    if docket is None or question is None:
        return None
    stmt = select(Argument.id).where(
        Argument.source_docket == docket,
        Argument.question_number == question,
    )
    if exclude_argument_id is not None:
        stmt = stmt.where(Argument.id != exclude_argument_id)
    return (await db.execute(stmt)).scalar_one_or_none()
\`\`\`

This generalizes the existing \`check_duplicate_argument\` query without changing its public preflight response. Have that endpoint delegate to the helper with no exclusion. [VERIFIED: existing check_duplicate_argument; D-08]

### Pattern 2: Compute effective values once

Refactor the existing normalization/parsing into a pure preparation step or keep it adjacent to \`values_to_set\`, then derive:

\`\`\`python
final_docket = values_to_set.get("source_docket", argument.source_docket)
final_question = values_to_set.get("question_number", argument.question_number)
\`\`\`

Do not derive from raw request fields: \`source_dockets\` determines canonical docket, invalid nonnumeric question text is currently skipped, explicit clears become NULL, and omitted fields retain stored values. [VERIFIED: MetadataUpdate and update_argument_metadata lines 848-882]

### Pattern 3: Named-constraint recognition through the cause chain

The installed SQLAlchemy asyncpg dialect translates the asyncpg error and raises the adapter error \`from\` the original asyncpg exception; the underlying asyncpg PostgreSQL error exposes \`constraint_name\`. Therefore use a small tested helper that walks \`exc\`, \`exc.orig\`, and chained \`__cause__\`/\`__context__\` objects with cycle protection and compares \`constraint_name == "uq_arguments_source_docket_question"\`. Do not classify by message substring. [VERIFIED: local introspection of SQLAlchemy asyncpg \`_handle_exception\`; asyncpg 0.31.0 exception attributes; D-10]

### Pattern 4: Rollback, then recover conflict data

Once flush/commit raises, issue no SQL until \`await db.rollback()\`. After rollback, recompute the effective pair from the request plus the restored stored row and call the same conflict lookup. The concurrent winner necessarily committed before PostgreSQL rejected this writer, so the re-query is the correct source for \`conflicting_argument_id\`. [VERIFIED: D-07/D-10 and SQLAlchemy failed-transaction behavior represented by existing rollback patterns]

### Pattern 5: Typed action failure payload shared by both routes

Both actions should preserve the exact submission on every failure, not only collision failures:

\`\`\`typescript
{
  saveError: 'Could not save. Try again.',
  dockets,
  question_number,
  argued_date,
  conflict?: {
    code: 'duplicate_argument';
    message: string;
    conflicting_argument_id: number;
  }
}
\`\`\`

For a valid structured 409, use \`fail(409, ...)\`; malformed JSON, wrong code, absent numeric id, network failure, and non-409 responses use generic sanitized copy but still echo all three fields. [VERIFIED: current actions collapse failures and preserve only dockets; D-02/D-05]

### Pattern 6: Shared component owns collision rendering and focus

Extend the form prop type with submitted question/date and typed conflict. Drive the input values from returned form values when present, as the component already does for docket pills. Bind the existing \`role="alert"\` element, give it \`tabindex="-1"\`, and focus it after the enhanced failure update and DOM tick. Render the final phrase as:

\`\`\`svelte
<a
  href={\`/admin/arguments/\${form.conflict.conflicting_argument_id}\`}
  target="_blank"
  rel="noopener noreferrer"
>Open conflicting argument</a>.
\`\`\`

Keep the alert as a single inline region; do not add a route-specific banner. [VERIFIED: shared component/current enhance callback; D-03/D-04/D-06]

### Component Responsibilities

| File | Responsibility |
|------|----------------|
| \`api/services/admin_arguments.py\` | Canonical pair lookup, final-pair computation, pre-check, conflict domain data. |
| \`api/routers/admin.py\` | Rollback/classification fallback and structured/sanitized HTTP detail. |
| \`pipeline/commands/ingest.py\` | Preserve CLI duplicate error; narrow classification. |
| \`pipeline/commands/import_convokit.py\` | Preserve next-number/counter behavior; narrow classification. |
| \`pipeline/commands/parse.py\` | Guard conditional docket fill and report collision in pipeline channel. |
| two \`+page.server.ts\` files | Parse exact duplicate detail and return full attempted values. |
| \`ArgumentDetailsCard.svelte\` | Identical alert/link/focus/value recovery on both admin pages. |

### Anti-Patterns to Avoid

- **Pre-check only:** loses the race between SELECT and COMMIT. Keep the DB fallback. [VERIFIED: D-07]
- **Catch every IntegrityError as duplicate:** mislabels unrelated constraints and may disclose the wrong recovery link. [VERIFIED: current broad catches; D-10]
- **Match rendered exception text:** driver/dialect text is unstable and risks leaking raw database details. Inspect \`constraint_name\`. [VERIFIED: D-10]
- **Query before rollback:** the session is in failed transaction state. Roll back first. [VERIFIED: D-10]
- **Use raw PATCH fields as final pair:** breaks partial updates, invalid-question skip semantics, canonical first-docket selection, and self-exclusion. [VERIFIED: D-08 and current service]
- **Reset form after failure:** destroys attempted values. Preserve all three fields and keep \`reset:false\` success behavior. [VERIFIED: current component comments; D-05]
- **Duplicate alert markup in routes:** the component is shared precisely to guarantee parity. [VERIFIED: D-04]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Race-safe uniqueness | Application lock/in-memory registry | Existing PostgreSQL named unique constraint | Database is authoritative across processes. [VERIFIED: model constraint; D-07] |
| SQL comparison | Interpolated SQL | SQLAlchemy \`select\` expressions | Existing parameterized pattern. [VERIFIED: check_duplicate_argument] |
| HTTP error envelope | Custom response class | FastAPI \`HTTPException(status_code=409, detail=dict)\` | Locked response contract and existing framework. [VERIFIED: D-01/D-02] |
| Per-route collision UI | Two separate banners | Shared \`ArgumentDetailsCard.svelte\` | Prevents behavioral divergence. [VERIFIED: D-04] |
| New frontend test framework | Vitest/Playwright installation solely for this bug | Existing pytest source-contract tests plus \`svelte-check\` and focused manual accessibility verification | Repo has no frontend test runner today; Phase 33 needs no dependency expansion. [VERIFIED: app/package.json and repo test-file audit] |

## Common Pitfalls

### Pitfall 1: Self-conflict on unchanged/partial saves
**What goes wrong:** Query finds the row being edited.  
**Avoidance:** Always exclude current id and use stored values for omitted fields.  
**Verification:** unchanged save and docket-only/question-only tests. [VERIFIED: D-08]

### Pitfall 2: Losing attempted question/date values
**What goes wrong:** actions return only \`dockets\`; load-derived \`savedValues\` repaint the other inputs.  
**Avoidance:** every failure branch echoes \`question_number\` and \`argued_date\`; component prioritizes form values. [VERIFIED: both current actions; D-05]

### Pitfall 3: Fallback cannot produce conflicting id
**What goes wrong:** handler knows only that commit failed.  
**Avoidance:** after rollback, recompute exact final pair with the same preparation logic and query the winner. [VERIFIED: D-02/D-07/D-10]

### Pitfall 4: Parse silently hits the constraint
**What goes wrong:** a row already has question number and parse fills a docket held by another row.  
**Avoidance:** treat conditional parse update as a full uniqueness writer, including race fallback. [VERIFIED: parse.py lines 367-376; D-09]

### Pitfall 5: Broad offline catches hide unrelated corruption
**What goes wrong:** ingest/import label every IntegrityError as docket/question collision.  
**Avoidance:** reuse named-constraint helper; retain channel-specific output only for the named violation. [VERIFIED: ingest.py/import_convokit.py; D-09/D-10]

### Pitfall 6: Focus runs before alert exists
**What goes wrong:** \`focus()\` sees null immediately after action update.  
**Avoidance:** await enhanced \`update()\`, then Svelte DOM tick, then focus bound alert. Keep \`tabindex="-1"\`. [VERIFIED: current enhance flow and D-06]

## Validation Architecture

Nyquist validation is explicitly disabled in \`.planning/config.json\`, so no formal Wave 0 validation section is required by workflow. The following test strategy is still required by locked discretion and PIPE-27. [VERIFIED: .planning/config.json, 33-CONTEXT.md]

### Backend behavioral coverage

1. In \`api/tests/test_admin_arguments_service.py\`, use isolated DB/session fixtures to prove:
   - concrete collision returns/raises conflict with other id;
   - docket-only partial PATCH combines stored question;
   - question-only partial PATCH combines stored docket;
   - unchanged pair excludes self;
   - NULL in either final field does not collide;
   - unique update succeeds and preserves prior semantics.
2. In \`api/tests/test_admin_arguments_routes.py\`, prove exact 409 JSON:
   \`{"detail":{"code":"duplicate_argument","message":"An argument already uses docket X, question N. Open conflicting argument.","conflicting_argument_id":ID}}\`.
3. Force a synthetic commit-time target \`IntegrityError\` (pre-check reports clear) and assert rollback occurs before the post-failure lookup and response.
4. Force a non-target IntegrityError and assert it is not \`duplicate_argument\`, contains no raw driver text, and remains separately identifiable (recommended stable code: \`constraint_violation\`).
5. Replace the weak router-wide source assertion in \`test_question_number_nullable.py\` with targeted behavioral classification coverage; a mere occurrence of the string \`IntegrityError\` proves neither rollback nor correct mapping. [VERIFIED: existing test content]

### Writer regression coverage

- Keep \`pipeline/tests/test_ingest.py::test_ingest_idempotent\` green; add a unit classification test proving unrelated IntegrityError is not converted to duplicate ValueError. [VERIFIED: existing test]
- Keep both ConvoKit question-number and forced-collision tests green; add non-target classification behavior. [VERIFIED: test_import_convokit_core.py]
- Add parse tests for (a) collision detected before conditional docket fill, (b) current-row exclusion, (c) NULL question allowed, and (d) forced named race fallback versus non-target failure. Existing \`test_parse.py\` has no source-docket collision coverage. [VERIFIED: test audit]

### Frontend contract coverage

The repository has no Vitest/Playwright runner or existing frontend tests. Add focused pytest source-contract tests (consistent with current lightweight source regressions) that inspect both action blocks and the shared component for:

- both actions branch on status 409 and validate \`detail.code === "duplicate_argument"\` plus numeric \`conflicting_argument_id\`;
- all failure branches return \`dockets\`, \`question_number\`, and \`argued_date\`;
- component form type carries structured conflict and all attempted values;
- exactly the existing inline \`role="alert"\` renders the conflict;
- link path uses the id and includes \`target="_blank"\` plus \`rel="noopener noreferrer"\`;
- alert is focusable and the enhanced failure path focuses it after update/tick.

Run \`npm --prefix app run check\` to type-check both action payloads and component props. Because source-contract tests cannot prove live focus movement, include one focused manual verification on each route: submit the same collision, confirm values remain, active element is the alert, Enter/Tab reaches the link, and the link opens the argument editor in a new tab. [VERIFIED: app/package.json and absence of frontend runner]

### Suggested commands

\`\`\`powershell
.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_service.py -q
.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_arguments_routes.py api/tests/test_question_number_nullable.py -q
.\.venv\Scripts\python.exe -m pytest pipeline/tests/test_ingest.py pipeline/tests/test_import_convokit_core.py pipeline/tests/test_parse.py -q
npm --prefix app run check
\`\`\`

## Security Domain

### Applicable ASVS Categories

| Category | Applies | Control |
|----------|---------|---------|
| V2 Authentication | Existing, unchanged | Router-level admin token dependency remains authoritative. [VERIFIED: admin.py router] |
| V3 Session Management | No new behavior | No session/cookie change. [VERIFIED: phase scope] |
| V4 Access Control | Yes | Argument id comes from authenticated route/job lookup, never form data; conflict link contains only an existing numeric admin id. [VERIFIED: both actions and D-02] |
| V5 Input Validation | Yes | Pydantic mass-assignment schema, existing date/question parsing, normalized docket list, and parameterized SQL remain in force. Blank validation is deferred to Phase 34. [VERIFIED: MetadataUpdate, service, CONTEXT boundary] |
| V6 Cryptography | No new behavior | No cryptographic change. [VERIFIED: phase scope] |

### Threats and mitigations

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Raw DB error disclosure | Information Disclosure | Stable structured detail for target constraint; sanitized code/message for others; log server-side without returning driver text. [VERIFIED: D-10] |
| TOCTOU duplicate write | Tampering / Integrity | PostgreSQL constraint fallback after friendly pre-check. [VERIFIED: D-07] |
| Incorrect-record link | Integrity | Re-query exact pair after rollback and use returned numeric id. [VERIFIED: D-02/D-08] |
| Reverse-tabnabbing | Spoofing | \`rel="noopener noreferrer"\` with \`target="_blank"\`. [VERIFIED: D-06] |
| SQL injection | Tampering | SQLAlchemy bound expressions; never interpolate docket into SQL. [VERIFIED: existing query pattern] |

## State of the Art

| Existing Approach | Phase 33 Approach | Impact |
|-------------------|-------------------|--------|
| Broad generic \`IntegrityError -> 409 constraint_violation\` | Friendly pre-check plus exact named-constraint fallback | Precise recovery without race gap or misclassification. |
| Actions collapse all failures and echo only docket pills | Typed duplicate parsing and complete attempted-value echo | Both admin surfaces retain operator context. |
| Plain alert text | Shared focusable alert with linked conflict record | Actionable keyboard-accessible recovery. |
| Parse conditional write unaudited | Same concrete-pair predicate and fallback | Every writer respects the constraint. |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | None. All implementation claims were verified from locked context, repository code/tests/config, or local installed-library introspection. | — | — |

## Open Questions (RESOLVED)

1. **RESOLVED — Stable code for non-target constraint failures**
   - Adopted resolution: preserve structured generic \`constraint_violation\` for non-target integrity failures, with sanitized generic copy and no driver text. Reserve \`duplicate_argument\` exclusively for \`uq_arguments_source_docket_question\`. [VERIFIED: 33-01-PLAN.md Task 2]
2. **RESOLVED — Parse channel failure state**
   - Adopted resolution: handle the fallback at parse's smallest safe transaction boundary, where it can rollback and classify the raced violation, then report through parse's existing failure channel. Do not import FastAPI or HTTP wording into the pipeline command. [VERIFIED: 33-02-PLAN.md Task 3]

## Environment Availability

Step 2.6: SKIPPED — Phase 33 is a code/config-only change using the project's existing Python, PostgreSQL driver, Node, and test/check tooling; it introduces no external dependency. [VERIFIED: stack and package audit]

## Sources

### Primary (HIGH confidence)

- \`.planning/phases/33-metadata-update-unique-constraint-guard/33-CONTEXT.md\` — locked D-01 through D-10, scope, and canonical references.
- \`.planning/ROADMAP.md\` Phase 33 and \`.planning/REQUIREMENTS.md\` PIPE-27 — goal and acceptance boundary.
- \`api/services/admin_arguments.py\`, \`api/routers/admin.py\`, \`api/schemas/admin_arguments.py\`, \`api/models/models.py\` — backend contract and exact write semantics.
- \`ArgumentDetailsCard.svelte\` and both admin \`+page.server.ts\` files — current shared UI/action behavior.
- \`pipeline/commands/ingest.py\`, \`import_convokit.py\`, \`parse.py\` — complete production writer audit.
- Existing API/pipeline tests and \`app/package.json\` — test infrastructure and gaps.
- Local installed SQLAlchemy asyncpg dialect source and asyncpg 0.31.0 exception introspection — cause chain and \`constraint_name\` diagnostic.

### Secondary / Tertiary

- None required; this is a codebase-only research phase with locked architecture and no new package selection.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing locked project dependencies, no additions.
