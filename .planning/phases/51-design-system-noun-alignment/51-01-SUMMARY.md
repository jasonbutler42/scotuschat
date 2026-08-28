---
phase: 51-design-system-noun-alignment
plan: 01
subsystem: design
tags: [figma, design-tokens, design-system, accessibility, decisions]

requires:
  - phase: 51-design-system-noun-alignment
    provides: 51-UI-SPEC.md, whose token tables are the authoritative values this plan transcribes into Figma Variables
provides:
  - "Figma file `SCOTUS Chat Design System` in the operator's personal team, pages Tokens / Primitives / Public / Admin"
  - "Two-layer Figma Variable architecture: 14-entry `primitive` collection + 37-entry `semantic` collection, every semantic colour aliasing a primitive"
  - "Semantic variable names that plan 51-03 consumes verbatim as app/src/app.css :root custom properties"
  - "Primitive frame names (Button, Badge, Input, Card) that plan 51-06 consumes verbatim as app/src/lib/primitives/*.svelte filenames"
  - "D-16 ruling: Variant A (minimal term row); advocate join deferred, not discarded"
  - "D-18 ruling: lucide-svelte, gated on the plan 51-06 package-legitimacy checkpoint"
  - "UI-SPEC E4 ruling: Button loading variant lives on the shared primitive"
affects: [51-03-design-tokens, 51-04-term-grouped-api, 51-06-shared-primitives, 51-08-arguments-listing]

actuals:
  tokens: 62000
  tasks: 3
  commits: 1

tech-stack:
  added:
    - "lucide-svelte (DECIDED, NOT YET INSTALLED — blocked on the plan 51-06 package-legitimacy checkpoint, threat T-51-SC)"
  patterns:
    - "Figma Variables (never Styles) in two collections, semantic aliasing primitive via VARIABLE_ALIAS — exports to CSS custom properties with no translation layer, and makes a light theme a second value set rather than a rewrite (D-02)."
    - "Alias integrity asserted programmatically at build time rather than by eye: read valuesByMode for every semantic colour, require type === 'VARIABLE_ALIAS' and require the target id to be a member of the primitive collection. Catches a flattened token layer, which is the expensive-to-reverse failure mode this plan's reversibility rating names."
    - "Apolitical constraint verified as a structural sweep over every TEXT node on every page, not by inspection — the same absence-across-a-computed-set argument the Testing Policy sanctions for test_trust_public_leak_ban.py."
    - "Frame name == eventual .svelte filename, and Figma semantic variable name == eventual CSS custom-property name, so drift between design and code is visible by diffing two name lists instead of reading both artifacts."

key-files:
  created:
    - .planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md
  modified: []
  external:
    - "Figma file KICu66PtMLHk4fmxJYPggx (SCOTUS Chat Design System) — 4 pages, 51 variables, 11 frames"

key-decisions:
  - "D-16 term row: Variant A (case name + argued date + docket number). Operator chose the minimal row on sight after both variants were rendered at 150 rows. The advocate join is DEFERRED per D-16's deferral clause, not rejected on merit."
  - "D-18 icons: lucide-svelte, decided against a measured count of 6 distinct icons (7 once the E4 decision added a spinner) versus the UI-SPEC's ~5 threshold. Count was measured in the codebase (2 hand-rolled today across 2 files) plus the 4 the Phase 51 surfaces call for, not estimated."
  - "UI-SPEC E4: the Button loading variant lives on the shared primitive rather than admin-only. The operator preferred one implementation and a simpler component API over two code paths, accepting that the public site can never reach the state."
  - "The documented scale fallback was NOT taken. Figma populated both 150-row variants on the first attempt, so no static HTML mocks were produced and mocks/ was never created. The plan's files_modified listed those two mock paths conditionally; they are correctly absent."
  - "Executed INLINE in the orchestrator session rather than by a gsd-executor subagent. The Figma MCP tools are deferred, and ToolSearch — the only mechanism to load a deferred schema — is disabled inside subagents, so no subagent in this project can reach Figma. The seat precondition itself was satisfied; the constraint was purely the harness tool boundary."

requirements-completed: [DS-02, DS-03, DS-04]

coverage:
  - id: D1
    description: "Figma file exists in the operator's personal 'Jason Butler's team' with exactly four pages named Tokens, Primitives, Public, Admin"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "whoami -> Full seat on 'Jason Butler's team' (team::987360705165943187), View-only on 'Offen Petroleum Design Team'; figma.root.children names == ['Tokens','Primitives','Public','Admin']"
        status: pass
    human_judgment: false
  - id: D2
    description: "Colour, spacing and type held as Figma Variables (not Styles) in two collections; the semantic collection aliases the primitive collection and holds no literal hex of its own"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "getLocalVariableCollectionsAsync -> {primitive: 14, semantic: 37}; for all 16 semantic COLOR vars, valuesByMode[mode].type === 'VARIABLE_ALIAS' AND alias target id is a member of primitive.variableIds -> allAliasToPrimitive: true, violations: []"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every semantic variable name has a character-for-character counterpart in 51-UI-SPEC.md: 16 colour roles, 7 spacing steps, 5 type sizes, 5 line heights, 2 weights, 2 touch targets"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "name-family counts over the semantic collection: colorRoles 16, spacing 7, fontSize 5, lineHeight 5, fontWeight 2, touchTarget 2, total 37"
        status: pass
    human_judgment: false
  - id: D4
    description: "Primitives page contains exactly four frames named Button, Badge, Input, Card; Input shows default/focused/invalid with error text in color-destructive; Button shows primary/destructive at 44px plus the dense 36px variant and an icon-only example"
    requirement: "DS-02"
    verification:
      - kind: other
        ref: "Primitives page children == ['Button','Badge','Input','Card']; visual confirmation via get_screenshot of node 1:2"
        status: pass
    human_judgment: true
    rationale: "Frame names and structure are machine-verified. That the states read correctly as states — focused ring, invalid error treatment, dense-row density — is a visual judgment the operator should confirm in the live file."
  - id: D5
    description: "Public page contains frames arguments-term-index, arguments-term-detail-variant-A, arguments-term-detail-variant-B, arguments-transcript; both variants render at least 100 rows"
    requirement: "DS-04"
    verification:
      - kind: other
        ref: "Public page children include all four required names (plus 'arguments-term-index — empty state' and 'd16-comparison'); variant-A rowCount 150, variant-B rowCount 150"
        status: pass
    human_judgment: false
  - id: D6
    description: "The variant-B artifact contains at least one row rendered with no advocate line and no reserved empty space where it would be"
    requirement: "DS-04"
    verification:
      - kind: other
        ref: "8 of 150 variant-B rows have a 2-child left column (case name + date/docket) rather than 3; the advocate TEXT node is never appended, so auto-layout collapses rather than reserving height. Visually confirmed at row 19 (Kowalczyk) in the d16-comparison screenshot."
        status: pass
    human_judgment: false
  - id: D7
    description: "Each of the four Public frames carries a focal-point annotation naming a primary element, a secondary element, and at least one deliberately-quiet element, matching the UI-SPEC Focal points table"
    requirement: "DS-04"
    verification:
      - kind: other
        ref: "focal-points annotation frames present on arguments-term-index, arguments-transcript, arguments-term-detail-variant-A, arguments-term-detail-variant-B"
        status: pass
    human_judgment: false
  - id: D8
    description: "No frame shows a derived per-speaker or per-argument statistic — no count, ranking, sentiment, or most/busiest/notable framing"
    requirement: "DS-04"
    verification:
      - kind: other
        ref: "swept every TEXT node on all four pages against 10 banned patterns -> bannedHits: 0. (Argument-count-per-term on the index is sanctioned explicitly by the UI-SPEC Focal points table as the secondary element, and is a collection cardinality, not a per-speaker or per-argument metric.)"
        status: pass
    human_judgment: false
  - id: D9
    description: "In arguments-transcript, a Justice turn and an advocate turn use identical type size and identical font weight for utterance body text"
    requirement: "DS-04"
    verification:
      - kind: other
        ref: "across all 6 turn/bench and turn/advocate frames: distinct fontSize == [18], distinct fontName.style == ['Regular'], identical: true"
        status: pass
    human_judgment: false
  - id: D10
    description: "51-DESIGN-DECISIONS.md records the Figma URL and team, the icon-library choice with its informing count, the Button loading-variant answer, and the term-row variant with the deferral clause"
    requirement: "DS-03"
    verification:
      - kind: other
        ref: "grep: all three required section headings present; exactly one icon candidate on a Decision line; 'Decision: Variant A' present; Figma URL present; 'Jason Butler's team' present; 'DEFERRED, not discarded' present; banned literals ('utterance count','speaking time','duration') all 0 occurrences"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-08-28
status: complete
---

# Phase 51 Plan 01: Figma Design Deliverable & Blocking Decisions Summary

## Accomplishments

Built the Figma deliverable D-05 puts ahead of code, and closed the three operator
decisions that four downstream plans were blocked on.

**Figma file:** https://www.figma.com/design/KICu66PtMLHk4fmxJYPggx — `SCOTUS Chat
Design System`, in *Jason Butler's team* (personal, Full seat). Four pages:

- **Tokens** — the two variable collections plus a visible swatch board, spacing scale
  rendered at true pixel widths, and the type scale rendered at real size/weight/line
  height. Every chip is bound to its variable, so the page is token-driven rather than
  hex-painted and cannot drift from the collections.
- **Primitives** — `Button`, `Badge`, `Input`, `Card`. Frame names equal the eventual
  `.svelte` filenames. Button carries the full accessible-name mechanism as an on-canvas
  annotation, not just a rule in a document.
- **Public** — `arguments-term-index` (+ a separate empty-state frame using the exact
  Copywriting Contract strings), `arguments-transcript`, and both D-16 term-detail
  variants at 150 rows each, plus a `d16-comparison` frame holding a readable
  side-by-side slice.
- **Admin** — density-optimized expressions of the four shared primitives only. No new
  admin screens and no new admin CTAs, per D-08's refactor-not-redesign constraint.

**Token architecture (D-02).** 14 `primitive` entries feed 37 `semantic` entries. All 16
semantic colour roles were asserted at build time to resolve through a `VARIABLE_ALIAS`
to a member of the primitive collection, with no literal hex in the semantic layer. This
is the one thing in the plan rated costly-to-reverse, so it was verified programmatically
rather than trusted.

**Decisions closed.** D-16 → Variant A (minimal row), advocate join deferred not
discarded. D-18 → `lucide-svelte`, on a measured count of 6 distinct icons rising to 7.
UI-SPEC E4 → loading variant on the shared primitive.

## Task Commits

- `9c95fd94e` — feat(51-01): Figma design system file plus the D-16/D-18/E4 operator rulings

Task 1 wrote no repository file by design; its output is an external Figma file whose URL
is recorded in the Task 2/3 deliverable. Tasks 2 and 3 both write the same file, so they
land in one commit rather than two empty ones.

## Files Created/Modified

Created: `.planning/phases/51-design-system-noun-alignment/51-DESIGN-DECISIONS.md`

External: Figma `KICu66PtMLHk4fmxJYPggx` — 4 pages, 51 variables, 11 top-level frames.

`mocks/term-detail-variant-A.html` and `mocks/term-detail-variant-B.html` appear in the
plan's `files_modified` but were correctly NOT created — see Deviations.

## Decisions Made

Recorded in full in `51-DESIGN-DECISIONS.md`. In brief:

| Decision | Ruling | Consequence |
|---|---|---|
| D-16 term row | Variant A — minimal | 51-04 needs no participant join; 51-08 `TermRow.svelte` ships the three-field shape |
| D-18 icons | `lucide-svelte` | 51-06 must clear the package-legitimacy gate before install |
| UI-SPEC E4 | Shared primitive | `Button.svelte` carries loading in `lib/primitives/`, spinner is the 7th icon |

## Deviations from Plan

**The scale fallback was not taken — and that is the plan working as written.** The plan
made the fallback conditional on the MCP being unable to populate ~150 rows after one
honest attempt. It populated both variants at 150 on the first attempt, so the Figma path
held and the two `mocks/*.html` paths in `files_modified` were never written. The plan
explicitly required naming which of the two paths was taken; it was the Figma one, and no
Figma call failed.

**Executed inline rather than in a subagent.** The first dispatch of this plan to a
`gsd-executor` returned a `blocking-human` halt: the Figma MCP tools are deferred, and
`ToolSearch` — the documented way to load a deferred schema — is disabled inside
subagents. That halt was correct for the subagent's environment but its conclusion did
not generalise. Verified from the orchestrator: the tools load, and `whoami` confirms the
exact seat configuration the precondition requires. The precondition was satisfied all
along; the blocker was the harness tool boundary. The operator chose to land 51-02 first
and then run this plan inline.

### Auto-fixed Issues

- `set_scopes` rejected `["ALL_FILLS","TEXT_FILL"]` — `ALL_FILLS` is exclusive of other
  fill scopes. The five status colours legitimately paint both a badge surface and badge
  text, so they use `ALL_FILLS` alone. `STROKE_COLOR` is not a fill scope and may
  accompany it.
- `createAutoLayout` rejected `counterAxisAlignItems: "START"` — the enum is
  `MIN | MAX | CENTER | BASELINE`.
- A stray character had slipped into the transcript headline
  (`Halloway v.三 Rivers…`); corrected via the canonical text-edit recipe, loading the
  node's current fonts from `getStyledTextSegments` before mutating.
- My own focal-point annotation on variant B tripped the apolitical sweep three times by
  *asserting* that banned figures are absent. Reworded to "no derived per-speaker or
  per-argument figure", so the sweep stays a real signal rather than one with a
  standing known-exception.

Each of the first two failed atomically — Figma applies nothing when a script throws — so
no partial nodes were left behind.

## Known Stubs

- The icon-only Button example uses a text glyph (`✕`) as a stand-in. The real glyph
  arrives with `lucide-svelte` in plan 51-06; drawing a hand-rolled vector now would
  contradict the decision this plan just recorded.
- The `Primitives` frames are ordinary frames, not Figma Components. The plan asked for
  frames whose names equal the eventual `.svelte` filenames, which is what 51-06 reads.
  Promoting them to a published component library is not in this phase's scope.

## Issues Encountered

**No corpus-scale query measurement was possible.** The plan asked for the advocate-join
cost at term scale if Variant B were in play. The dev database currently holds 4
arguments, so no honest measurement exists. What was established instead, and recorded
for whoever revives Variant B: `argument_participants` has **no index on `argument_id`**
(only a PK on `id`), so the join plans as a seq scan with a filter feeding a hash; at the
current 9.5-participants-per-argument ratio that projects to ~74,100 rows scanned per
listing request on a ~7,800-argument corpus. That is still only milliseconds, so scan
cost was never the reason to prefer A — but it means Variant B carries an index migration
that Variant A does not.

**Synthetic-data artifact, not a design signal.** Row 14 of variant B reads "Ms.
Underhill for petitioner · Mr. Underhill for respondent" — same surname on both sides, an
artifact of the deterministic name generator rather than a case shape to design for.

## User Setup Required

None outstanding. The Figma seat precondition was satisfied and re-verified at execution
time.

One thing to know for future phases: **a `gsd-executor` subagent cannot reach the Figma
MCP in this project**, because `ToolSearch` is disabled in subagents and the Figma tools
are deferred. Any future plan whose tasks require Figma writes must either run inline in
the orchestrator session or be planned around that boundary.

## Next Phase Readiness

Plan 51-03 is unblocked: it consumes the 37 `semantic` variable names verbatim as
`app/src/app.css :root` custom properties.

Plan 51-04 is unblocked and simplified: Variant A means the term-detail list endpoint
needs no `argument_participants` join.

Plan 51-06 is unblocked with a live prerequisite: it consumes the four `Primitives` frame
names as filenames, ships the loading variant on the shared `Button`, and must clear the
blocking package-legitimacy checkpoint before installing `lucide-svelte`.

Plan 51-08 is unblocked: `TermRow.svelte` ships case name + argued date + docket number,
and the advocate line does not ship.
