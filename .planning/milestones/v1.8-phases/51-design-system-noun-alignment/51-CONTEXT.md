# Phase 51: Design System & Noun Alignment - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning

<domain>
## Phase Boundary

The public side finally reflects the corrected domain language. Four deliverables:
the public noun aligns to "arguments" (DS-01), a shared component library is
extracted (DS-02), design tokens become the visual foundation (DS-03), and the
arguments listing style is decided and implemented (DS-04). Absorbs backlog
999.4 / 999.6 / 999.8. Sequenced last so the UI reflects the corrected domain
model rather than being reworked twice.

**Not in this phase:** deployment (DEPLOY-01, later milestone), the PDF route
(999.11), any change to the import/provenance/trust/review model settled in
phases 47-50.

</domain>

<decisions>
## Implementation Decisions

### Design tokens & the styling mechanism

- **D-01:** **Remove Tailwind entirely.** Delete `tailwindcss`, `postcss`,
  `@tailwindcss/typography`, `app/tailwind.config.js`, `app/postcss.config.js`,
  and the three `@tailwind` directives in `app/src/app.css`. It is installed and
  configured but used in exactly **3** places against **877** inline `style=`
  attributes — cost with no benefit. CSS custom properties become the token
  layer. Reinforced by D-05: Figma Variables map 1:1 onto CSS custom properties
  with no translation layer, where a Tailwind config would add a hand-maintained
  hop. Operator volunteered a standing preference: "I kind of hate tailwind."
  — **Reversibility:** costly — re-adopting Tailwind later means re-converting
  every component the phase touches; the dependency removal itself is trivial to
  undo but the 877-site conversion is not.

- **D-02:** **Dark only, structured for light later.** Two-layer token
  architecture: primitive palette -> semantic role. Ship only dark values. Adding
  a light theme later must be a contained change (add a second value set), never
  a rewrite. Semantic naming is mandatory — `--color-surface`, never
  `--color-slate-800`.
  — **Reversibility:** costly — the two-layer structure is what keeps it costly
  rather than one-way; a flat single-layer token set would have made light mode a
  full rewrite.

- **D-03:** **Tight named type scale, ~5 semantic steps** (caption / body / lead
  / heading / display). Today **9** distinct sizes (11, 12, 13, 14, 16, 18, 20,
  28, 32px) and 3 weights are in use — drifted well past the "3 sizes, 2 weights"
  that `.planning/codebase/DESIGN-SYSTEM.md` documents (that map was accurate for
  admin in July 2026 and is now stale). Collapsing is the point: 11/13/14 round to
  caption or body, 28 rounds to display. Both surfaces draw from one scale; admin
  uses the small end, public the large.

- **D-04:** **Convert every inline style.** All 877 `style=` attributes are
  converted; **zero inline styles remain at phase end**, across both public and
  admin. Rationale recorded from the operator: a half-converted codebase is
  exactly the ambiguity that made recent phases feel complex.

### Figma's role

- **D-05:** **Figma first, code follows.** The token set and component library are
  designed in Figma before implementation. Operator rationale, verbatim and
  load-bearing: *"I think I want Figma first specifically because it forces us to
  be explicit and disciplined instead of just recreating what's in the code."*
  A code-first pass would have produced documentation of the status quo, which is
  the outcome this decision exists to avoid.

- **D-06:** **Figma file structure mirrors the code.** Figma **Variables** (not
  Styles) hold color/space/type, because Variables export to CSS custom
  properties cleanly. Pages mirror the code layout: `Tokens` -> `app.css :root`,
  `Primitives` -> `lib/primitives/`, `Public` -> `lib/public/`, `Admin` ->
  `lib/admin/`. A component's Figma name equals its file name so drift is visible
  rather than silent.

- **D-07:** **Work happens in the operator's personal Figma team.** Verified
  2026-08-27: the account holds a **Full** seat on "Jason Butler's team" and a
  **View-only** seat on "Offen Petroleum Design Team". Writes against the Offen
  team will fail on permissions. Beyond permissions, this is a personal project
  and Offen's design team is company work — SCOTUS Chat files stay out of the
  Offen team and Offen design assets stay out of this repository.

### What gets redesigned vs refactored

- **D-08:** **Redesign public; refactor admin.** Public is the least-iterated
  surface and the product itself, so the Figma pass pays off there. Admin has been
  through nine phases of operator review and gets tokens and components without a
  visual rethink.
  **CRITICAL CAVEAT — do not read this as "don't change admin".** Operator's own
  words: admin *"needs a refactor but there are also some artifacts that survived
  through various changes so I expect I'll bring those up."* The admin conversion
  pass MUST **surface** leftover visual and UX artifacts for operator judgment as
  it encounters them, rather than faithfully preserving them into the new system.
  Plans should include an explicit mechanism for reporting these, not a silent
  1:1 conversion.

- **D-09:** **Transcript view gets reading polish, not a rethink.** The chat
  bubble metaphor, the speaker popover model, and the section rail are validated
  by v1.0 and are KEPT. What is redesigned is the reading layer: type scale and
  measure, vertical rhythm between turns, speaker-change emphasis,
  stage-direction treatment, and color roles via tokens. Scope is
  `app/src/routes/.../+page.svelte` (349 lines) plus `ChatBubble.svelte` (107),
  `StageDirection.svelte` (33), `SectionRail.svelte` (62),
  `SpeakerPopover.svelte` (259) — 810 lines total.

### URL shape & the noun

- **D-10:** **Flat, slug-based public URLs.** `/arguments` (list) and
  `/arguments/{slug}` (the argument). The case is removed from the path entirely.
  Decisive reason: `case_arguments` is an **M:M** join, so an argument covering
  two consolidated cases has no single correct parent slug — nesting is
  structurally wrong, not merely verbose.
  — **Reversibility:** one-way — public URL shape is the contract shared links
  depend on; changing it after DEPLOY-01 would require a permanent redirect layer.

- **D-11:** **No `/cases` redirects. DS-01 must be amended.** Verified
  2026-08-27: DEPLOY-01 is unchecked and carried to a later milestone, there is no
  deploy config in the repository, and the app has never been deployed. The
  "existing shareable URLs" DS-01 promises to preserve exist only on localhost.
  **ACTION for the planner:** amend DS-01 in `.planning/REQUIREMENTS.md` and
  `.planning/ROADMAP.md` to strike the redirect clause, recording this rationale.
  Do not silently leave the requirement and the implementation disagreeing.

- **D-12:** **Stored `Argument.slug`, never rewritten.** New column, unique
  constraint, generated at import, and NOT recomputed when a case name is later
  edited — so a shared URL survives an operator correcting a typo. Requires an
  Alembic migration (Alembic remains the sole DDL authority; see CLAUDE.md). The
  alternative (deriving the slug from the case name per request) would silently
  break every URL for an argument whenever its case name changed.
  — **Reversibility:** one-way — adding the column is a migration, and once URLs
  are in use the immutability guarantee cannot be withdrawn without breaking them.

- **D-13:** **`term` is a reserved slug word.** `/arguments/term/{year}` (D-14)
  coexists with `/arguments/{slug}`. Slug generation must refuse to mint a slug
  that shadows the term route.

### Listing information architecture

- **D-14:** **Grouped by term, drill in.** `/arguments` lists October Terms with
  counts; `/arguments/term/{year}` lists that term's arguments. Term is the
  Court's own organizing unit, `term_year` is **already on the `CaseItem`
  response model** (no new field needed), and grouping caps any single page at
  ~150 rows with no pagination widget to design. Costs one extra click to reach an
  argument.

- **D-15:** **Design for the full corpus (~7,800 arguments), not the current 4.**
  The operator expects to eventually publish the whole corpus. Term grouping is
  therefore required infrastructure, not decoration. **API work is implied:**
  `GET /cases` today returns every row with no limit/offset and
  `api/services/cases.py` has no pagination — term grouping and filtering must be
  added.

- **D-16:** **Term-list row: two variants, decided visually.** The minimal row
  (case name + argued date + docket number) is the **definite shipping fallback**
  — it uses only fields already on `CaseItem`, needs no new joins, and docket is
  how the Court itself disambiguates similar names. The operator likes the idea of
  adding **advocate names** but explicitly will not commit without seeing it:
  *"I'd have to see how it looks before saying it's the right call."* The Figma
  pass MUST produce BOTH variants for a visual decision. The advocate variant
  needs a join through `argument_participants` -> `people` on the list endpoint;
  evaluate query cost at term scale before proposing it.
  **Apolitical constraint check:** listing advocates is permitted — advocates and
  justices receive identical treatment. Utterance counts, speaking time, and
  duration are BANNED as derived statistics (CLAUDE.md, hard constraint) and were
  excluded from the options for that reason.

### Component library

- **D-17:** **One token set, two component layers.** Shared tokens and shared
  primitives (`Button`, `Badge`, `Input`, `Card`) in `lib/primitives/`; then
  `lib/public/` reading-optimized components (wider measure, larger type, more
  air) and `lib/admin/` density-optimized components. One source of truth, two
  expressions of it — public can feel different without a second palette to
  maintain. Directory layout mirrors the Figma pages in D-06.

- **D-18:** **Dependency adoption is the operator's call; identifying candidates
  is Claude's.** Generalized by the operator from a `bits-ui` question to a
  standing rule: *"this also should apply to other potential libraries. If there
  are existing options that fit, let me know and we can figure out if we want
  those as dependencies."* Never silently add a dependency; never silently
  hand-roll past a good fit. `bits-ui` is already a dependency (used only by
  `SpeakerPopover`) and is used per-component where focus management, keyboard
  navigation, or ARIA state is genuinely hard — this project committed to WCAG
  2.1 AA in Phase 4. Report which components used it and which were hand-rolled.
  **Assignment for the researcher:** enumerate candidate libraries for the
  components this phase needs, with tradeoffs, for an operator decision.

### Claude's Discretion

The operator explicitly delegated these. They still want to *look* at the
results — delegation here means "decide without asking", not "don't show me".

- **Multi-argument slug disambiguation scheme** (D-12's open half). Decide against
  the real corpus distribution: how many cases actually carry multiple arguments,
  and whether `question_number` or `argued_date` is the more reliable
  discriminator across ~7,800 rows. Bare slug for the single-argument common case
  is the expected shape; suffix only where genuinely needed.
- **Which components use `bits-ui` vs hand-rolled** (per D-18), with a report of
  which went which way.
- **Row design details** beyond the two variants named in D-16.

### Folded Todos

- **`2026-08-12-speaker-popover-frontend-duplication-cleanup.md`** (area: ui,
  `resolves_phase: 51`, surfaced by Phase 45's code review as IN-02/IN-03).
  Two items, both squarely DS-02 work: (1) `SpeakerPopover.svelte` computes
  `avatarBg` and `sideColor` with the identical expression
  (`isBench ? '#94a3b8' : '#93c5fd'`) and uses them interchangeably — dead
  duplication that can drift; collapse to one token reference. (2)
  `SpeakerPopover.svelte` and `.../arguments/[id]/+page.svelte` declare
  byte-for-byte identical `TenureRow` and `SpeakerDetail` TypeScript interfaces;
  extract to a shared module (e.g. `$lib/types/speaker.ts`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project constraints and policy
- `CLAUDE.md` — the apolitical hard constraint (no derived insight, summaries,
  sentiment, or statistics — governs D-16), Alembic as sole DDL authority
  (governs D-12), and the **Defect Policy / Testing Policy** added 2026-08-27.
  The testing policy directly governs how this phase is verified: static
  source-text contract tests for frontend behavior are BANNED. This is a visual
  phase; the operator's eye and real-browser checks are the verification, not
  green greps.
- `.planning/PROJECT.md` — core value statement; the chat format making speaker
  identity and turn-taking self-evident is what D-09 protects.

### Phase inputs
- `.planning/ROADMAP.md` § Phase 51 — goal, DS-01..DS-04 success criteria, and
  the absorbed backlog items 999.4 / 999.6 / 999.8.
- `.planning/REQUIREMENTS.md` — DS-01 through DS-04. **DS-01 needs amending per
  D-11.**
- `.planning/todos/pending/2026-08-12-speaker-popover-frontend-duplication-cleanup.md`
  — folded into scope.

### Design system starting state
- `.planning/codebase/DESIGN-SYSTEM.md` — the July 2026 palette/type/spacing
  snapshot. **Partially stale:** it claims "no Tailwind" (Tailwind IS a
  dependency, see D-01) and "only three sizes and two weights" (nine sizes are in
  use, see D-03). Treat as a starting checklist of values, not as current truth.
  Update it as part of this phase.
- `app/src/app.css` — the 8 existing `:root` custom properties that D-01/D-02
  expand into the full token set.
- `.planning/codebase/CONVENTIONS.md` — established code conventions.

### Code the phase rewrites
- `app/src/routes/cases/` — 6 files; the routes D-10 renames.
- `app/src/lib/components/` — 15 components to split into
  primitives/public/admin per D-17.
- `api/schemas/cases.py` — `CaseItem` / `CaseListResponse`; already carries
  `term_year` (D-14) and lacks advocate data (D-16 variant B).
- `api/services/cases.py`, `api/routers/cases.py` — no pagination or filtering
  today; D-14/D-15 require term grouping.
- `app/package.json` — the Tailwind dependencies D-01 removes.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **8 CSS custom properties already in `app/src/app.css`** — `--color-bg`,
  `--color-surface`, `--color-border`, `--color-text-primary`,
  `--color-text-secondary`, `--color-text-advocate`, `--color-stage-accent`,
  `--color-stage-text`. DS-03 is less "establish tokens" than "adopt the ones
  that exist, then extend to type and spacing".
- **`term_year` on `CaseItem`** — D-14's grouping needs no new field.
- **`Case.slug`** (varchar 200, unique) — the pattern D-12 follows for
  `Argument.slug`.
- **`bits-ui`** — already a dependency, proven on `SpeakerPopover`.
- **The existing 307 redirect** in `cases/[slug]/+page.server.ts` (single-argument
  case jumps straight to its argument) — the behavior D-10's flat shape makes
  unnecessary.
- **`app/tests/*.browser.test.mjs`** — four real-browser tests driving Chromium
  over CDP. This is the *right* kind of frontend test under the new testing
  policy and the pattern to extend, not replace.

### Established Patterns
- **Components are the source of truth for styling today; there is no theme
  file.** 877 inline `style=` attributes vs 9 `<style>` blocks.
- **Tokens exist but are bypassed.** `#94a3b8` appears **276** times, `#334155`
  **240**, `#e2e8f0` **210** — all three are existing custom properties written
  longhand. 24 distinct hex values total.
- **No component library or icon library.** Every element is plain HTML with
  inline styles; `bits-ui` is the single exception.
- **Card pattern**, applied identically everywhere:
  `background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 24px;`
- **Accent discipline** worth preserving into tokens: `#93c5fd` is reserved for
  primary actions and navigation, never status badges or muted text; status
  colors are never reused for non-status meaning.
- **Touch targets** are `min-height: 44px` (WCAG 2.1 AA), except dense in-table
  row buttons at 36px.
- **Phase 44 precedent:** the Resolve table converged "through live Figma-driven
  design iteration" — D-05 is not a new way of working on this project.

### Integration Points
- **SvelteKit routing** — `/cases/**` becomes `/arguments/**`; only **7**
  `/cases` references exist in `app/src`, so the rename surface is small.
- **`+page.server.ts` load functions** — all FastAPI calls go through these
  (`FASTAPI_BASE_URL` is server-only, never `PUBLIC_`). Term filtering added in
  D-14/D-15 flows through this boundary.
- **Alembic** — D-12's `Argument.slug` needs a migration; `Base.metadata.create_all`
  is banned.
- **`TopNav.svelte`** — carries the `/cases` link; part of the D-10 rename.

</code_context>

<specifics>
## Specific Ideas

- **"Explicit and disciplined instead of just recreating what's in the code"** —
  the operator's stated reason for Figma-first (D-05). This is the test to apply
  when the Figma pass feels slow: if the output merely documents current code, the
  decision's purpose has been missed.
- **"I kind of hate tailwind"** — unprompted standing preference (D-01). Do not
  propose Tailwind or Tailwind-adjacent utility frameworks on this project.
- **"Someday I'm going to need to change an existing slug"** — the operator
  accepted D-12's immutability knowing this, and asked for the future fix to be
  recorded. See Deferred Ideas.
- **"Some artifacts that survived through various changes... I expect I'll bring
  those up"** — admin refactor must surface cruft, not preserve it (D-08).
- **Grouping delegated vs owned work is appreciated.** The operator explicitly
  thanked the practice of separating "things you could decide on your own" from
  real decisions, and noted they will likely still want to look at the delegated
  ones. Keep flagging which is which; delegation means "decide without asking",
  not "don't show me".

</specifics>

<deferred>
## Deferred Ideas

- **Slug-change mechanism** (operator-requested, 2026-08-27). D-12 makes
  `Argument.slug` immutable, which is right for URL stability but means a bad slug
  is permanent. Concrete future design, not a vague wish: an
  `argument_slug_alias` table (`old_slug` UNIQUE, `argument_id` FK, `created_at`)
  plus an operator-editable current slug. Changing a slug writes the old value to
  the alias table; the route resolves the current slug first, then falls back to
  the alias table and issues a **301** to the current URL. Result: editable slugs,
  zero broken links, and a full rename history. Explicitly NOT this phase.
- **Light theme.** D-02 structures for it; shipping it is a later decision.
- **Advocate names on term-list rows** — if the Figma comparison in D-16 does not
  justify the variant, the join work and the idea are deferred rather than
  discarded.

### Reviewed Todos (not folded)
- `2026-08-12-speakers-bench-classification-silent-fallback.md` (area: api) — a
  correctness concern about a silent wrong-label fallback when
  `ArgumentParticipant.side` is missing. Real, but it is API correctness, not
  design-system work. Under the CLAUDE.md Defect Policy this is Claude's to fix
  when encountered, not an operator decision.
- `2026-08-14-revisit-pre-relocation-checkout-removal.md` (area: dev-environment)
  — unrelated to this phase.
- `2026-08-18-pdf-provenance-live-fixture-verification.md` (area: pipeline) —
  deferred with the PDF route (999.11).

</deferred>

---

*Phase: 51-Design System & Noun Alignment*
*Context gathered: 2026-08-27*
