# Phase 26: Arguments Admin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 26-Arguments Admin
**Areas discussed:** Publish/Unpublish UX, Delete gate for Unpublished, Speakers section design, Status log 'Created' entry

---

## Todo Match Review

**Matched todo:** "Add Archived pipeline run status" (`.planning/todos/pending/2026-07-07-add-archived-pipeline-run-status.md`), score 0.9.

| Option | Description | Selected |
|--------|-------------|----------|
| Leave as pending todo (recommended) | It's about RunStatusCard/pipeline run status, a different status field than Argument.status this phase touches. | |
| Fold into Phase 26 | Pull it into this phase's scope since it's status-badge-adjacent work. | ✓ |

**User's choice:** Fold into Phase 26.
**Notes:** Explicitly folded in despite touching a different status field (`AdminJob` run readiness, not `Argument.status`) — recorded in CONTEXT.md as a Folded Todo with the caveat noted.

---

## Publish/Unpublish UX

**Question 1: Should Unpublish require a confirmation step before it takes effect?**

| Option | Description | Selected |
|--------|-------------|----------|
| One-click (current) | Matches today's behavior — Unpublish fires immediately on click, same as Publish. | ✓ |
| Two-step confirm | Reuse the existing Danger Zone pattern (first click reveals Confirm/Cancel). | |
| You decide | Let the planner pick based on what fits the redesigned page layout best. | |

**User's choice:** One-click (current).

**Question 2: On re-Publish, what should the Status card's "Published" date show?**

| Option | Description | Selected |
|--------|-------------|----------|
| Latest publish timestamp | 'Published' always reflects the most recent transition into Published. | ✓ |
| Original first-publish date | Track the first time it went live separately from current published_at. | |
| You decide | Let the planner choose based on what's simplest given the status log. | |

**User's choice:** Free-text — "We discussed a change log. Is that still an option?"
**Follow-up:** Claude confirmed: Status card shows current/latest `published_at` only; the full status log below is the source of complete history (including any original first-publish date), so no separate field is needed. User confirmed: "Yes, that's it."

---

## Delete gate for Unpublished

**Question: Should Unpublished arguments be blocked from deletion the same way Published ones are?**

| Option | Description | Selected |
|--------|-------------|----------|
| Block Unpublished too (recommended) | Delete blocked whenever status is PUBLISHED or UNPUBLISHED; only DRAFT deletable. | ✓ |
| Allow Unpublished to delete | Literal reading of AEDIT-09 "unchanged" — gate stays keyed on published_at. | |
| You decide | Let the planner pick the safer/more consistent option. | |

**User's choice:** Block Unpublished too (recommended).

---

## Speakers section design

**Question 1: Reuse ResolveCard's inline-save pattern, or a simpler read-mostly table?**

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse ResolveCard pattern | Same table shape and inline-save mechanism as ResolveCard.svelte. | |
| Simpler read-mostly table | A plainer list, avoiding Resolve's pause/discrepancy/auto-match machinery. | ✓ |
| You decide | Let the planner choose the closest-fit pattern. | |

**User's choice:** Simpler read-mostly table.
**Follow-up:** Claude confirmed this means extending the CURRENT "Advocate Roles" card's existing per-row dropdown + Save button + `use:enhance` pattern, adding a Title input, utterance count column, and read-only bench rows. User confirmed: "Yes, extend that pattern."

**Question 2: Should advocate title fields show the extracted TOC hint when not overridden?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, show hint | Matches AEDIT-06/07's "extracted hints visible" pattern from Phase 23/25. | ✓ |
| No, just the field | Extraction hint is less relevant once an argument is settled. | |

**User's choice:** Yes, show hint.

---

## Status log 'Created' entry

**Question 1: Should Phase 26 add the missing ArgumentStatusLog write for the 'Created' transition?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, add it in Phase 26 | Without this, every argument created after Phase 22 has an empty status log. | ✓ |
| Defer / out of scope | Leave admin_jobs.py untouched in this phase. | |

**User's choice:** Yes, add it in Phase 26.

**Question 2: Where should the ArgumentStatusLog write logic live?**

| Option | Description | Selected |
|--------|-------------|----------|
| Shared helper function | A small function both admin_jobs.approve_job and admin_arguments.py call. | |
| Inline in each call site | Each transition point writes its own insert inline. | |
| You decide | Let the planner pick based on existing module boundaries. | ✓ |

**User's choice:** You decide.

---

## Claude's Discretion

- Exact placement/naming of the shared status-log-write helper (or inline duplication) — D-10.
- Visual treatment details for the Speakers section (spacing, column order) beyond what's locked in.

## Deferred Ideas

None — discussion stayed within phase scope. The one adjacent-scope item raised (Archived pipeline run status todo) was explicitly folded into Phase 26 rather than deferred.
