# Positioning — index

Seven documents from 2026-07-09, written before any homepage design work. They remain the
foundation for that work. **None of them has been superseded.**

| Document | What it holds |
|---|---|
| `FOUNDATION.md` | what the product is and is not |
| `PRINCIPLES.md` | the non-editorial boundary, stated as rules |
| `VOICE.md` | copy guidelines, with explicit do/don't language |
| `AUDIENCE.md` | who this is for |
| `MESSAGING.md` | the promise and how to phrase it |
| `HOMEPAGE-BRIEF.md` | the homepage's job, content priority, blocks, success criteria |
| `BACKLOG.md` | positioning-side open items |

## The Figma exploration that goes with these

**File `9PDECvbdHM2vYVxt3SCwru`, page "Homepage concepts - positioning pass", node `4060:2`.**
Three full-width concepts:

| Node | Concept | Shape |
|---|---|---|
| `4060:3` | **1 — Search-first archive** | hero, large search field, term chips, recent arguments, term rows, trust strip |
| `4060:60` | **2 — Archive-first reading room** | hero, Browse/How-it-works buttons, recent arguments, term rows, format-note panel, trust strip |
| `4060:117` | **3 — Format-first orientation** | hero, buttons, live transcript preview, three benefit cards, recent arguments, source note |

**Status per the operator, 2026-09-23: "That exploration did not have any conclusions. We
should use it as a starting point not as a place where we are ready to make a lot of
decisions."** Treat the three concepts as material, not as a shortlist to pick from.

`HOMEPAGE-BRIEF.md`'s own working direction — *"archive-first, search-forward, source-oriented,
and calm"* — predates the exploration and is the stronger statement of intent.

## What has changed since July that the brief and the concepts do not know

Recorded so the next person does not design against stale assumptions. **These are facts, not
decisions.**

1. **There is no search.** No endpoint, no service function, no UI. The brief is
   "search-forward" and Concept 1 leads with a search field; both assume a capability that has
   never been built. It is net-new work, not a layout choice.
2. **The corpus is 1955-2019** — 65 terms, 7,817 conversations, most recent OT 2019. All three
   concepts show OT 2024/2023/2022/2021 term rows and feature *Trump v. United States*,
   *Moyle*, *Loper Bright*, *Fischer*, *Snyder*, *Grants Pass* and *FDA v. Alliance* — every one
   an OT 2023 case that does not exist in the data. Reaching recent terms means the deferred PDF
   route (Phase 999.11).
3. **Archive inventory at launch is answerable now:** 7,811 of 7,817 arguments are publishable
   under the 2026-09-23 trust decisions; 6 are held back for being more than 50% undetermined.
   This answers the brief's open question *"How much archive inventory will exist at launch?"*
4. **`/` has no route at all.** `app/src/routes/` has a `+layout.svelte` and no `+page.svelte`,
   so the root currently renders the nav bar and a 404.
5. **The transcript format the concepts preview has since shipped and changed** — Phase 51's
   D-19 Style B2 (outside avatar rail, run-grouped utterances, 6/2px grouped corners) is the
   real thing now. Concept 3's preview panel predates it. Current source of truth is the
   design-system file `KICu66PtMLHk4fmxJYPggx`, page Public.

## Other open questions the brief raises that are still open

Verbatim from `HOMEPAGE-BRIEF.md`, minus the two answered above:

- Should the homepage lead with search, recent arguments, or both?
- Will source transcript links be available for every public argument?
- Should the homepage include the creator-origin story, or reserve that for an About page?
- How much explanation is needed for "term", "argument", "case", and "docket"?
- Should utterance-level sharing be hinted at only inside argument pages, not on the homepage?
