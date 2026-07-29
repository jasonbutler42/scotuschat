# Phase 38: Rethink Full Name vs. name-part fields in the people editor - Research

**Researched:** 2026-07-15
**Domain:** Person-name authority, legacy data migration, extraction provenance, and Svelte admin UX
**Confidence:** HIGH

## User Constraints

### Name authority and storage
- **D-01:** Structured name parts are authoritative. Full Name is generated and is not independently operator-editable.
- **D-02:** People create/edit surfaces show a live, read-only Full Name preview labeled as generated from name parts.
- **D-03:** One shared derivation rule applies everywhere a person is created or updated, including the main people editor, standalone create page, pipeline mini-create, API writes, CSV/corpus imports, and seeds.
- **D-04:** Keep the existing `full_name` database field as a synchronized compatibility value so current display, sorting, alias, deduplication, and API consumers continue to work.

### Canonical formatting
- **D-05:** Canonical Full Name format is `First Middle Last, Suffix`; omit blank Middle and Suffix components without leaving extra spaces or punctuation.
- **D-06:** Normalize whitespace only: trim components and collapse repeated spaces. Preserve authored capitalization and punctuation.
- **D-07:** Treat each component as authored text. Preserve initials, hyphens, apostrophes, particles, compound surnames, and suffix spelling; do not synthesize periods, title-case text, or otherwise rewrite content.
- **D-08:** Display the canonical Full Name everywhere. Lists may continue sorting by Last Name without changing displayed ordering.

### Minimum data and legacy migration
- **D-09:** A new person requires at least First Name or Last Name. This supports incomplete pipeline knowledge and legitimate single-part names while guaranteeing a non-empty derived Full Name.
- **D-10:** Automatically split existing Full Names into component fields rather than requiring immediate manual cleanup or leaving all legacy rows unconverted.
- **D-11:** Auto-apply only confident splits. When a Full Name cannot be split confidently, preserve the original Full Name unchanged and flag the record for name review; do not silently replace it with a guess.
- **D-12:** Surface ambiguous legacy records through a specific `Name review` attention indicator/filter in the People directory, following the existing missing-data cleanup pattern.
- **D-13:** Do not add or defer a generic cross-feature Admin Dashboard queue unless the focused People directory solution later proves insufficient.

### Extracted name-part provenance
- **D-14:** Pipeline parsing and import paths extract First, Middle, Last, and Suffix as persistent reference metadata rather than producing only a Full Name.
- **D-15:** Show the extracted reference beneath each corresponding editable saved field. Extracted metadata persists independently when an operator edits the saved value.
- **D-16:** When extraction first becomes available, prepopulate only blank saved fields. Never overwrite an existing operator value.
- **D-17:** If extraction/reprocessing occurs later, replace the extracted reference with the latest result while leaving saved fields untouched. This consistency rule does not restore the removed job-rerun UI.
- **D-18:** Retain the extractor's best-effort interpretation for every name part, including uncertain guesses, so the operator can see what the system thought it saw and correct the editable value.

### Shared extracted-value presentation
- **D-19:** Evolve the shared extracted-value component globally, not only for name fields. Extracted fields with an editable destination use the same stacked treatment.
- **D-20:** The stacked treatment exposes three distinct facts per field: the interpreted extracted value, a confidence rating, and the exact raw source text.
- **D-21:** First line: `Extracted: {interpreted value}` with the Phase 36 copy affordance attached to the interpreted displayed value. Second line: `{confidence band} confidence · Raw: {exact source text}`.
- **D-22:** Confidence is presented as `High`, `Medium`, or `Low`, not a percentage. Avoid implying calibrated statistical precision; research/planning may define a consistent confidence contract and thresholds.
- **D-23:** The stacked layout must remain usable beneath both narrow fields such as Suffix and wider fields such as Last Name.

### Agent's Discretion
- Exact shared formatter/module boundary and enforcement mechanism, provided every write path uses the same canonical rule.
- Exact migration splitting algorithm, confidence contract, and thresholds, provided ambiguous legacy values remain intact and reviewable.
- Exact storage schema for extracted value, raw text, and confidence, provided provenance persists independently of operator edits and all relevant paths behave consistently.
- Exact responsive spacing and accessible markup for the stacked extracted-value component, constrained by the Phase 36 copy/accessibility contract and the canonical mockup.

### Deferred Ideas

None. A general Admin Dashboard attention queue was considered, but the user decided the focused People directory `Name review` filter may fully satisfy the need and should be tried first rather than captured as a new capability.

## Summary

Phase 38 should be planned as a staged data-authority migration, not a form-only refinement. `people.full_name` is non-null and widely used for display and matching, while structured fields are nullable and only partially drive updates today. The existing service formatter omits the required comma before suffix and only derives when both first and last are submitted; standalone creation and job mini-create still accept direct `full_name`, while corpus import and seeds construct `Person` rows directly. [VERIFIED: codebase]

The safe architecture is one pure canonical formatter plus one server-owned normalization/validation boundary reused by every writer. Add persistent migration-review state and extraction provenance through an Alembic migration, backfill only high-confidence legacy splits, and preserve ambiguous `full_name` byte-for-byte until an operator supplies authoritative parts. [VERIFIED: 38-CONTEXT.md; codebase]

The extracted-value work should extend `CopyableExtractedValue.svelte` rather than introduce a name-only component. Its existing race-safe clipboard lifecycle, disabled `N/A`, tooltip, and live feedback remain intact; new optional raw/confidence props render the approved two-line stacked treatment at every editable extracted field consumer. [VERIFIED: Phase 36 canonical references; codebase]

**Primary recommendation:** Plan separate waves for contract/tests, schema and legacy backfill, centralized write enforcement/import adoption, provenance extraction, and frontend/global component adoption.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Canonical normalization/formatting | Python domain helper | Pydantic schemas | Every backend/import writer can call one pure function; schemas reject missing first+last combination. [VERIFIED: codebase] |
| Compatibility synchronization | Service/import write boundary | DB constraints/tests | `full_name` remains stored, but clients never own it. [VERIFIED: D-01–D-04] |
| Legacy splitting/backfill | Alembic migration plus testable pure splitter | People directory review UI | Migration must be reproducible and preserve ambiguous source values. [VERIFIED: D-10–D-12] |
| Extracted provenance | Persistent person-adjacent JSONB or typed columns | Pipeline/import adapters | Metadata must survive operator edits independently. [VERIFIED: D-14–D-18] |
| Generated preview | Shared TypeScript formatter mirroring contract | API response | Immediate UX feedback; backend remains authoritative. [VERIFIED: D-02; codebase] |
| Stacked extracted hint | `CopyableExtractedValue.svelte` | All editable-field consumers | Phase 36 already establishes the shared primitive and accessibility contract. [VERIFIED: Phase 36 references] |

## Standard Stack

No new packages are required. Use the existing Svelte 5/SvelteKit frontend, FastAPI/Pydantic v2 service contracts, SQLAlchemy 2 async models, PostgreSQL JSONB, Alembic migrations, and pytest/Svelte checks. [VERIFIED: PROJECT.md; app/package.json; codebase]

| Existing tool | Purpose in Phase 38 |
|---|---|
| Alembic | Add review/provenance storage and perform guarded backfill. |
| Pydantic v2 | Explicit name-part allow-lists and at-least-one-of validation. |
| SQLAlchemy async | Central service writes and import persistence. |
| Svelte 5 runes | Live generated preview and responsive stacked hints. |
| pytest + svelte-check | Nyquist behavioral coverage and frontend contract checking. |

## Package Legitimacy Audit

Not applicable: the phase should install no external package. [VERIFIED: codebase requirements]

## Architecture Patterns

### System Architecture Diagram

```text
operator form / job mini-create / CSV / corpus / seeds
                         |
                         v
        normalize authored components (trim + collapse spaces)
                         |
              first OR last present?
                  /             \
                no               yes
             reject 422          |
                                  v
                  canonical formatter
               First Middle Last, Suffix
                                  |
                                  v
       atomic write: parts + synchronized full_name
                                  |
                                  v
          existing display / sort / alias / dedup consumers

legacy full_name rows -> deterministic splitter -> confident?
                                      /          \
                                    yes           no
                         backfill parts+canonical  preserve full_name
                                                + name_review=true
```

### Recommended Project Structure

```text
api/
├── domain/person_names.py          # pure normalize, format, validate, split contract
├── schemas/admin_people.py         # API allow-lists/validation; no client full_name authority
├── services/admin_people.py        # atomic person mutations and review clearing
└── services/admin_jobs.py          # mini-create delegates to shared domain contract
alembic/versions/0021_*.py          # schema plus guarded legacy backfill
pipeline/commands/                  # import/seed paths call the shared contract
app/src/lib/
├── personNames.ts                  # preview-only mirror with parity tests/fixtures
└── components/CopyableExtractedValue.svelte
```

### Pattern 1: Normalize Once, Derive Always

Normalize each supplied component by trimming and collapsing internal whitespace, convert empty strings to `None`, require first or last, then derive `full_name` on every create/update. On partial PATCH, merge submitted values with stored components before deriving; never derive from only the request payload. [VERIFIED: D-05–D-09; current partial-update bug in codebase]

### Pattern 2: Conservative Legacy Splitter

Make the splitter a pure, fixture-driven function returning parts, confidence band, and reason. High confidence should be limited to structurally unambiguous project data patterns; suffix recognition may use a small explicit set derived from repository data. Any unrecognized punctuation/order/particle ambiguity remains unchanged and is flagged. The migration should report deterministic counts and assert that no row becomes blank. [VERIFIED: D-10–D-12; codebase literals]

### Pattern 3: Provenance Envelope

Store each extracted field as `{value, raw, confidence}` under a stable typed envelope, separate from `first_name`/`middle_name`/`last_name`/`name_suffix`. Initial ingestion fills blank saved parts only; later extraction replaces only the envelope. Prefer a dedicated `Person.name_extraction_metadata` JSONB column plus schema helpers, consistent with existing `Argument.cover_metadata`, unless query/filter requirements discovered during implementation justify typed columns. [VERIFIED: D-14–D-18; models.py JSONB pattern]

### Pattern 4: Backward-Compatible Shared Component

Extend `CopyableExtractedValue` with optional `label`, `raw`, and `confidence` props. Preserve its existing value-only and pill states so consumers can migrate incrementally; stacked mode renders the exact two-line contract and copies only interpreted `value`, never raw text. [VERIFIED: D-19–D-23; Phase 36 contract]

### Anti-Patterns to Avoid

- Accepting or trusting client-supplied `full_name`; it reintroduces divergence. [VERIFIED: D-01–D-04]
- Formatting independently in API, CSV import, corpus import, seeds, and TypeScript without shared fixtures. [VERIFIED: current duplicate implementations]
- Splitting all legacy names with a generic whitespace rule; particles, compound surnames, and suffix punctuation make silent corruption possible. [VERIFIED: D-07, D-11]
- Using migration confidence percentages in UI; the locked contract is only High/Medium/Low. [VERIFIED: D-22]
- Overwriting operator fields when extraction refreshes. [VERIFIED: D-16–D-17]
- Replacing the Phase 36 copy component or changing copied payload to include prefixes/raw text. [VERIFIED: Phase 36 contract]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Schema changes/backfill | startup-time DDL or `create_all` | Alembic revision | Alembic is sole DDL authority. [VERIFIED: PROJECT.md] |
| Mutation validation | per-route string checks | Pydantic plus shared domain helper | Covers API and non-HTTP writers consistently. [VERIFIED: codebase] |
| Copy feedback | new per-field clipboard handlers | evolved `CopyableExtractedValue` | Existing component already handles races, failures, N/A, and accessibility. [VERIFIED: Phase 36 code] |
| Human-name “intelligence” | capitalization/punctuation heuristics | authored-text preservation and conservative splitter | Locked decisions forbid rewriting authored content. [VERIFIED: D-06–D-07] |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | PostgreSQL `people` rows may have non-null `full_name` with nullable/partial structured parts; imported Oyez IDs and aliases depend on those rows. [VERIFIED: models/import code] | Alembic schema plus guarded backfill; preserve ambiguous original full name and all IDs/FKs. |
| Live service config | None found; name authority is code/database behavior, not service configuration. [VERIFIED: project config search] | None. |
| OS-registered state | None found; no scheduled task or registry binding contains this field contract. [VERIFIED: repository scope] | None. |
| Secrets/env vars | None found; no name-related secret or environment setting. [VERIFIED: repository scope] | None. |
| Build artifacts | SvelteKit generated/type artifacts may be stale after prop/schema changes. [VERIFIED: app scripts] | Run `npm run check`/build; do not edit generated output. |

## Current Write-Path Inventory

| Path | Current behavior | Required plan action |
|---|---|---|
| `admin_people.update_person` | Accepts `full_name`; derives only when request has both first and last; formatter lacks suffix comma. [VERIFIED: codebase] | Remove client authority, merge PATCH with stored parts, normalize/derive every relevant update. |
| `admin_people.create_person` | Requires direct `full_name`, parts optional. [VERIFIED: codebase] | Require first or last, derive stored compatibility value. |
| Svelte new/edit server actions | Validate and forward editable `full_name`. [VERIFIED: codebase] | Stop reading/forwarding full name; preserve attempted name parts on validation failure. |
| Job `create_person_for_job` | `Person(full_name=body.full_name)` only. [VERIFIED: codebase] | Expand schema/form to parts and delegate shared derivation. |
| `import_justices_csv` | Has correct comma-suffix reconstruction locally. [VERIFIED: codebase] | Replace local formatter with shared helper while retaining override fixtures. |
| `import_convokit` | Creates/dedups by corpus `full_name`, with no parts. [VERIFIED: codebase] | Extract/store provenance, conservative parts, and retain stable Oyez-ID-first matching. |
| `seed_aliases` | Literal full-name tuples and direct Person insertion. [VERIFIED: codebase] | Seed structured fixtures; derive full name while preserving exact alias/dedup strings. |

## Common Pitfalls

### Pitfall 1: Partial PATCH corrupts the compatibility value
**What goes wrong:** Editing only suffix or middle name derives from request `None`s or leaves `full_name` stale.
**How to avoid:** Load the row, merge explicitly supplied fields using `model_fields_set`, then normalize/derive from the merged state in one transaction. [VERIFIED: existing CR-01 pattern]

### Pitfall 2: Backfill destroys ambiguous names
**What goes wrong:** A whitespace splitter guesses particles/compound surnames, and the recomputed value silently differs.
**How to avoid:** Require round-trip equality plus an explicit high-confidence rule before applying. Preserve original and set review state otherwise. [VERIFIED: D-10–D-12]

### Pitfall 3: Dedup changes create duplicate people
**What goes wrong:** Imports switch from an existing exact `full_name` key before canonicalization/backfill is aligned.
**How to avoid:** Preserve Oyez-ID-first resolution, stage migration before writer changes, and regression-test the 13 justice seed names byte-for-byte. [VERIFIED: import code/tests]

### Pitfall 4: Provenance is coupled to editable values
**What goes wrong:** Operator edits erase extraction history, or reprocessing overwrites corrections.
**How to avoid:** Persist separate provenance and implement blank-only prefill as an explicit transition. [VERIFIED: D-15–D-18]

### Pitfall 5: Global component evolution regresses Phase 36
**What goes wrong:** Copy includes `Extracted:`/raw text, N/A becomes interactive, or feedback races return.
**How to avoid:** Keep clipboard state machine untouched and add component tests for old value/pill mode plus stacked mode. [VERIFIED: Phase 36 contract/code]

## Security and ASVS Review

The phase changes authenticated admin mutations and imports but adds no new public authorization boundary. Preserve existing admin auth, explicit Pydantic allow-lists (ASVS V4/V5), ORM parameterization (V5), output escaping through Svelte text interpolation (V3), and ID-scoped service lookups (V4). Treat raw extracted text as untrusted data: store it as data, never render via `{@html}`, and never interpret it as markup or instructions. [VERIFIED: codebase; project constraints]

Threats to cover in plans: mass assignment of `full_name` despite removal, oversized provenance strings, malformed JSON envelope, IDOR on job mini-create, and migration rollback/data-loss behavior. Add length bounds consistent with existing columns and verify raw text is escaped. [VERIFIED: schema/model limits; existing service guards]

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest (backend/pipeline), Svelte compiler/type checks (frontend) [VERIFIED: config/scripts] |
| Config file | repository pytest configuration plus `app/package.json` |
| Quick run command | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_people_schemas_service.py pipeline/tests/test_import_justices_csv.py -q` |
| Full suite command | `.\.venv\Scripts\python.exe -m pytest` and `cd app; npm run check` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| PEOPLE-09 | Canonical whitespace and `First Middle Last, Suffix` fixtures, including first-only/last-only | unit | pytest targeted formatter tests | Existing file; Wave 0 extend |
| PEOPLE-09 | Create/update reject neither-part and ignore client `full_name`; partial PATCH synchronizes | service/API integration | pytest admin people tests | Existing files; Wave 0 extend |
| PEOPLE-09 | Confident migration round-trips; ambiguous names remain exact and flagged; downgrade restores schema | migration integration | pytest migration test | Missing: Wave 0 |
| PEOPLE-09 | Job mini-create/import/seed all use shared authority without duplicate people | integration | pytest job/import suites | Existing files; Wave 0 extend |
| PEOPLE-09 | Extraction blank-only prefill and later refresh leaves saved values untouched | unit/integration | pytest provenance tests | Missing: Wave 0 |
| PEOPLE-09 | Generated preview and stacked extracted-value accessibility/copy behavior | frontend component/browser | `cd app; npm run check` plus focused browser UAT | Component test harness absent; Wave 0 add or document browser gate |
| PEOPLE-09 | Every current editable extracted-field consumer adopts stacked value/confidence/raw contract | static/component integration | `cd app; npm run check` plus repository consumer assertion | Missing: Wave 0 |

### Sampling Rate

- Run pure formatter/splitter/component contract tests after each task.
- Run affected API/import suites after each wave.
- Run complete pytest and `npm run check` before phase verification.
- Perform browser UAT at narrow Suffix width and wider Last Name/docket fields, including keyboard copy, N/A, success, and error states.

### Wave 0 Gaps

1. Add shared canonical formatter parity fixtures consumed by Python and TypeScript tests.
2. Add migration tests with confident, ambiguous, single-part, punctuation, particle, suffix, whitespace, and downgrade cases.
3. Add provenance transition tests for first extraction, operator edit, and later extraction refresh.
4. Add a focused frontend/browser contract for `CopyableExtractedValue` because `npm run check` alone cannot prove clipboard feedback or accessible behavior.

## Planning Sequence Recommendation

1. **Wave 0 contract harness:** formatter/splitter fixtures, write-path inventory assertions, migration/provenance/component tests.
2. **Schema and migration:** review state + provenance storage, guarded backfill, immutable report/counts, rollback safety.
3. **Backend authority:** shared domain helper, Pydantic contracts, standalone/update/job writers.
4. **Import authority:** justice CSV, corpus, seeds, extraction adapters; preserve dedup identities.
5. **Frontend:** generated preview, `Name review` directory filter, name-part hints, global stacked component consumers.
6. **Nyquist closeout:** complete test matrix, migration dry-run evidence, browser accessibility/responsive UAT.

## Open Questions

No product questions remain. Planner discretion should choose the exact high-confidence splitter rules and JSONB envelope, but must encode them in fixtures before migration. The local image viewer could not open the canonical PNG because the Windows restricted-token sandbox rejected split writable roots; `38-FIGMA.md`, the offline snapshot references, and the textual locked two-line contract remain sufficient for planning, but implementation UAT should visually compare against the supplied artifact. [VERIFIED: tool result; canonical references]

## Sources

### Primary (HIGH confidence)
- `.planning/phases/38-full-name-vs-name-parts-rethink/38-CONTEXT.md` — locked decisions and canonical references.
- `.planning/phases/36-click-to-copy-extracted-values-design-pattern/{36-CONTEXT,36-UI-SPEC,36-PATTERNS}.md` — copy/accessibility/component contract.
- `.planning/PROJECT.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md` — milestone, constraints, PEOPLE-09.
- Canonical source files named in Phase 38 context — current write paths, schemas, model, UI, and import behavior.
- Existing tests under `api/tests` and `pipeline/tests` — current regression seams and gaps.

### Secondary (MEDIUM confidence)
- `.planning/phases/38-full-name-vs-name-parts-rethink/38-FIGMA.md` and approved local snapshots — visual implementation reference; direct image inspection was environment-blocked in this run.

### Tertiary (LOW confidence)
- None. No external packages or unverified ecosystem claims are recommended.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — existing project stack only.
- Architecture: HIGH — traced through all canonical code references and locked decisions.
- Migration splitting thresholds: MEDIUM — intentionally left to fixture-backed planner discretion because real-row distribution should drive exact thresholds.
- Pitfalls: HIGH — grounded in current service/import behavior and existing regression comments/tests.

**Research date:** 2026-07-15
**Valid until:** Stable until Phase 38 implementation changes these seams.
