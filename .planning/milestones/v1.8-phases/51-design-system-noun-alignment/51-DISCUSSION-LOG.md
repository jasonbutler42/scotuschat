# Phase 51: Design System & Noun Alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-27
**Phase:** 51-Design System & Noun Alignment
**Areas discussed:** Figma's role, Design tokens & Tailwind's fate, URL shape & redirects, Listing style & scale, Component library scope, Transcript redesign, Type scale, Term-list row content, Figma file structure

---

## Figma's Role

| Option | Description | Selected |
|--------|-------------|----------|
| Code first, Figma documents it | Settle tokens/components in code, push to Figma as reference | |
| Figma first, code follows | Design in Figma, then implement against it | ✓ |
| Skip Figma this phase | Tokens/components in code only | |

**User's choice:** Figma first, code follows.
**Notes:** Verbatim rationale — *"I think I want Figma first specifically because it forces us to be explicit and disciplined instead of just recreating what's in the code."* This is the load-bearing reason, not the choice itself: a code-first pass would have documented the status quo, which is what the decision exists to prevent.

---

## Design Tokens & Tailwind's Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Remove it; CSS custom properties | Delete 3 deps + 2 configs; expand `:root` variables | ✓ |
| Adopt it properly | Keep Tailwind, rewrite 877 inline styles as utilities | |
| Keep it installed, decide later | Build CSS custom properties anyway, leave the dep | |

**User's choice:** Remove it.
**Notes:** *"Option 1 all the way. I kind of hate tailwind and just want to say that."* Recorded as a standing preference, not just a phase decision.

| Option | Description | Selected |
|--------|-------------|----------|
| Dark only | One palette, semantic names | |
| Light + dark from the start | Both palettes, toggle or `prefers-color-scheme` | |
| Dark only, structured for light later | Primitive palette -> semantic role, dark values only | ✓ |

**User's choice:** Dark only, structured for light later.

| Option | Description | Selected |
|--------|-------------|----------|
| Visual refactor — look stays | Same pixels, tokens/components replace inline styles | |
| Redesign public, refactor admin | Figma pass on public; admin gets tokens without a rethink | ✓ |
| Full redesign, both surfaces | Whole app through Figma | |

**User's choice:** Redesign public, refactor admin.
**Notes:** Important qualifier — *"Admin needs a refactor but there are also some artifacts that survived through various changes so I expect I'll bring those up."* This makes the admin pass a surfacing exercise, not a faithful 1:1 conversion. Captured as the CRITICAL CAVEAT on D-08.

| Option | Description | Selected |
|--------|-------------|----------|
| Everything — no inline styles left | Convert all 877 | ✓ |
| Public fully, admin opportunistically | Convert public; admin only where components reach | |
| You decide | Claude picks based on what extraction reaches | |

**User's choice:** Everything.

---

## URL Shape & Redirects

| Option | Description | Selected |
|--------|-------------|----------|
| Flat, slug-based | `/arguments`, `/arguments/{slug}` — case leaves the path | ✓ |
| Flat, id-based | `/arguments/{id}` — no slug scheme needed | |
| Keep two levels, rename the root | `/arguments/{case-slug}/{id}` | |

**User's choice:** Flat, slug-based.
**Notes:** Claude surfaced the deciding fact — `case_arguments` is M:M, so an argument covering two consolidated cases has no single correct parent slug.

| Option | Description | Selected |
|--------|-------------|----------|
| Build them anyway | Redirect handlers satisfying DS-01 as written | |
| Skip them — nothing to preserve | Change routes outright, amend DS-01 | ✓ |
| Build them, remove at deploy | Redirects now, deleted as part of DEPLOY-01 | |

**User's choice:** Skip them.
**Notes:** Claude verified before asking that DEPLOY-01 is unchecked, no deploy config exists, and the app has never been deployed — so the "existing URLs" DS-01 protects are localhost-only. Requires a requirements amendment (D-11).

| Option | Description | Selected |
|--------|-------------|----------|
| Stored column, set once | `Argument.slug`, unique, never rewritten | ✓ |
| Derived from case name at request time | Slugify on the fly, no migration | |

**User's choice:** Stored column.
**Notes:** *"option 1 for now but I promise you that someday I'm going to need to change an existing slug. Record a future improvement that would make that not suck."* Recorded as a concrete deferred design (alias table + 301), not a vague wish.

| Option | Description | Selected |
|--------|-------------|----------|
| Bare slug, suffix only when needed | Clean common case, discriminator for multiples | |
| Always suffixed | Every slug carries a discriminator | |
| You decide | Claude picks against real corpus distribution | ✓ |

**User's choice:** You decide.

---

## Listing Style & Scale

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by term, drill in | `/arguments` lists terms; `/arguments/term/{year}` lists arguments | ✓ |
| Search-first | Search box primary, browse list as fallback | |
| One paginated chronological list | Reverse-chronological, ~150 pages | |
| You decide | Claude picks from corpus shape | |

**User's choice:** Grouped by term, drill in.
**Notes:** `term_year` already exists on `CaseItem`, so no new field is needed — only grouping and filtering on an API that currently returns every row.

| Option | Description | Selected |
|--------|-------------|----------|
| Eventually the whole corpus (~7,800) | Design for thousands from day one | ✓ |
| A curated subset, growing slowly | Dozens to hundreds; simpler listing adequate | |
| Unknown — design for both | Reads well at 20, works at 7,800 | |

**User's choice:** Whole corpus.

---

## Component Library Scope

| Option | Description | Selected |
|--------|-------------|----------|
| One token set, two component layers | Shared primitives; public and admin layers | ✓ |
| One system, one set of components | Identical components everywhere | |
| Fully separate systems | Independent tokens and components | |

**User's choice:** One token set, two component layers.

| Option | Description | Selected |
|--------|-------------|----------|
| Use it for interactive primitives | `bits-ui` for focus/keyboard/ARIA work | |
| Hand-roll everything, drop `bits-ui` | One less dependency | |
| You decide, per component | Claude picks per component and reports | ✓ |

**User's choice:** You decide, per component — **generalized by the user**.
**Notes:** *"Option 3 but this also should apply to other potential libraries. If there are existing options that fit, let me know and we can figure out if we want those as dependencies."* Escalated into a standing rule (D-18): Claude identifies candidates, the operator decides adoption. Never silently add a dependency; never silently hand-roll past a good fit.

---

## Transcript Redesign

| Option | Description | Selected |
|--------|-------------|----------|
| Reading polish, not a rethink | Keep chat metaphor; redesign the reading layer | ✓ |
| Full rethink | No assumptions preserved, including chat bubbles | |
| Out of scope — listing and navigation only | Transcript gets tokens only | |

**User's choice:** Reading polish.

---

## Type Scale

| Option | Description | Selected |
|--------|-------------|----------|
| Tight named scale, ~5 steps | caption / body / lead / heading / display | ✓ |
| Modular ramp from a base | Generated from base + ratio | |
| Keep the range, just formalize it | Name all 9 current sizes | |

**User's choice:** Tight named scale.
**Notes:** Claude found that `DESIGN-SYSTEM.md`'s "three sizes and two weights" claim is stale — 9 sizes and 3 weights are actually in use.

---

## Term-List Row Content

| Option | Description | Selected |
|--------|-------------|----------|
| Name + argued date + docket | Fields already on `CaseItem`; no new joins | ✓ (fallback) |
| Add advocate names | Join through `argument_participants` -> `people` | ✓ (conditional) |
| You decide | Claude designs against the corpus | |

**User's choice:** *"option 1 as a definite fallback. I like the idea of option 2 but I'd have to see how it looks before saying it's the right call."*
**Notes:** Resolved as an explicit Figma deliverable — produce BOTH variants for a visual decision, with the minimal row shipping if the advocate variant does not earn its place. Claude flagged that utterance counts / speaking time / duration were excluded from the options entirely because CLAUDE.md bans derived statistics.

---

## Figma File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Variables for tokens, pages mirror `lib/` | Tokens / Primitives / Public / Admin pages | ✓ |
| Single page, Figma Styles | One canvas, classic Styles | |
| You decide | Claude sets it up and shows the structure | |

**User's choice:** Variables for tokens, pages mirror `lib/`.

---

## Claude's Discretion

- Multi-argument slug disambiguation scheme, decided against real corpus distribution.
- Which components use `bits-ui` vs hand-rolled, with a report of which went which way.
- Row design details beyond the two variants named for the Figma comparison.

The user noted appreciation for this grouping being made explicit, and added that they *"will likely still want to look"* — delegation here means decide without asking, not don't show me.

## Deferred Ideas

- **Slug-change mechanism** — `argument_slug_alias` table + editable current slug + 301 fallback. Explicitly requested to be recorded; explicitly not this phase.
- **Light theme** — D-02 structures for it; shipping it is a later decision.
- **Advocate names on rows** — deferred rather than discarded if the Figma comparison does not justify it.

## Todos Reviewed, Not Folded

- Speakers bench-classification silent fallback (api) — correctness, not design.
- Pre-relocation checkout removal (dev-environment) — unrelated.
- PDF provenance live-fixture verification (pipeline) — deferred with the PDF route (999.11).
