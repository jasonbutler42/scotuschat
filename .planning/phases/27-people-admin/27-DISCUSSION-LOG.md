# Phase 27: People Admin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-08
**Phase:** 27-People Admin
**Areas discussed:** Tabs & per-tab filters, Create-person flow, Justice/Bench Details card, Tenure appointment fields (resolved via mockup review)

**Note:** Discussion was paused mid-session (see below) pending operator mockups, then resumed and completed the same day.

---

## Session 2 — Mockup review (same day, after pause)

The operator provided three mockups (`.planning/phases/27-people-admin/mockups/`): a filled Create Person example (Bench, William Rehnquist), a blank Bench version, and a blank Advocate version. Explicit instruction: use them for layout/flow patterns only, not exact visual styling — the existing design system (`.planning/codebase/DESIGN-SYSTEM.md`) governs colors/spacing/typography.

**Unrelated capture during this session:** the operator asked to capture an idea — authenticated "Edit" affordance on every utterance plus an "Edit" link on the speaker popover card. Saved as `.planning/todos/pending/2026-07-08-edit-affordance-on-utterances-and-speaker-popover.md`, no phase assigned. Not part of Phase 27.

| Question | Options offered | Selected |
|---|---|---|
| Reason Left field is fully built in the mockup — build now (new migration) or still defer? | Build now / Still defer | **Still defer** |
| Death Date field (new, not in PEDIT-02) — include it? | Yes, add it / No, birthdate only | **Handle like Reason Left** — add to layout, wire up in a future phase |
| Reserved fields (Death Date, Reason Left) — how should they behave when interacted with? | Disabled/greyed out / Fully editable but not persisted | **Disabled/greyed out** |
| Photo button label: mockup says "Save photo," PEDIT-05 says "Upload photo" | Upload photo (per requirement) / Save photo (per mockup) | User declined to pick — delegated to Claude's discretion generally for this class of conflict (see feedback memory `feedback_copy_discretion.md`). **Resolved: "Upload photo"** (favor existing locked requirement). |
| Card model: consolidate checkbox + separate Justice Details card into one "Person Type" card as shown? | Yes, adopt as shown / Keep separate cards | **Yes, adopt as shown** — but renamed: no visible card title, referred to as "Bench Details" internally, not "Person Type" |

**Notes:** The user was mildly annoyed at being asked to resolve a pure wording conflict (Photo button label) — this produced a standing feedback preference (see memory) to resolve such conflicts without asking in the future.

---

## Session 1 — Initial discussion (before pause)

## Tabs & per-tab filters

| Option | Description | Selected |
|--------|-------------|----------|
| Query param on one page | `/admin/people?tab=advocate`, consistent with existing `?incomplete=1`/`?tenure_gaps=1` | ✓ |
| Separate routes | `/admin/people/bench` and `/admin/people/advocate` | |
| Client-side only toggle | Single load, pure client-side tab state | |

**User's choice:** Query param on one page.

| Option | Description | Selected |
|--------|-------------|----------|
| Split strictly by is_justice | is_justice=true → Bench, false → Advocate, no default specified | |
| Split by is_justice, default tab = Bench | Same split, explicit default | (superseded — see below) |

**User's choice:** Asked for clarification ("How do options 1 & 2 differ?") — both use identical split logic; the only difference is default-tab behavior. Re-asked as a standalone question:

| Option | Description | Selected |
|--------|-------------|----------|
| Bench | Default tab when no `?tab=` param | ✓ |
| Advocate | Default tab when no `?tab=` param | |

**User's choice:** Bench.

**Incomplete filtering redesign:**

| Option | Description | Selected |
|--------|-------------|----------|
| Bio + photo only (Advocate) | Drop role check entirely for advocates | (superseded) |
| Bio + photo + title history (Advocate) | Also check title on argument_participants | (superseded) |
| No — role/bio/photo only (Bench) | Keep 3-field check, birthdate not counted | (superseded) |
| Yes — add birthdate to the check (Bench) | role/bio/photo/birthdate | ✓ (partially — see below) |

**User's choice (free text):** Rejected the toggle-based framing entirely. Wants an "Incomplete" column with pills for: first name, last name, photo, bio (all people); Justices additionally get a "no tenures" pill. Wants the "Incomplete only" toggle removed and to explore what filtering interface should replace it.

**Follow-up — Bench role pill:**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, keep it | Bench pills include role (Chief/Associate Justice not set) | |
| No, drop it | Role excluded from Bench pills | ✓ |

**User's choice:** Drop role entirely — "Roles are argument specific."

**Follow-up — filter UI to replace the toggle:**

| Option | Description | Selected |
|--------|-------------|----------|
| Click a pill to filter | Clicking a pill filters the table to that gap; click again / clear control resets | ✓ |
| No filter — pills + sort only | Pills for visual scanning, incomplete-first sort, no interaction | |
| Dropdown filter | Separate "Filter by gap" dropdown | |

**User's choice:** Click a pill to filter.

**Notes:** Final missing-field pill sets: Advocate = first name, last name, photo, bio (no role check — role never structurally applies to advocates). Bench = first name, last name, photo, bio, birthdate, no tenures (role explicitly excluded per the follow-up above, superseding this area's earlier framing).

---

## Create-person flow

| Option | Description | Selected |
|--------|-------------|----------|
| Full name only | Blank editor, only full_name required to save | (superseded) |
| Full name + Bench/Advocate choice upfront | Operator must pick side before saving | ✓ |

**User's choice:** Full name + Bench/Advocate choice upfront.

| Option | Description | Selected |
|--------|-------------|----------|
| List page button → blank /admin/people/new → redirect to edit page | Full page navigation, reuses edit template | (revisited, then reaffirmed) |
| Modal/dialog on the list page | Popover reused/expanded from Phase 25's mini create-person pattern | (briefly chosen, then reversed) |

**User's choice (evolved over the conversation):** Initially picked the popover/modal option, reasoning that popovers suit transient creation flows and enable reuse of the Phase 25 pattern. Asked a follow-up about what happens after popover submit; two sub-options were offered (immediate create + redirect to edit page, vs. prefill-and-stay-on-list). Before answering that sub-question, the user reversed the decision entirely: no popover — "I like the idea of the 'create' and 'edit' pages being the same more." Final decision: full page navigation to `/admin/people/new` using the same editor template, save redirects to `/admin/people/{id}` — this is the option originally offered and ultimately reaffirmed (D-07 in CONTEXT.md).

**Notes:** The reversal itself is a preference worth carrying forward — the operator generally prefers unifying create/edit UI surfaces over transient popovers, even though popovers have situational appeal.

---

## Justice Details card (partial — paused before completion)

| Option | Description | Selected |
|--------|-------------|----------|
| Role, then tenure rows | Role field first, tenure rows below — matches today's order | (superseded) |
| Tenure rows, then Role | Tenure rows first | (superseded) |

**User's choice (free text):** Role is not needed at all — "argument dependent" — and listed new desired per-tenure fields: start date, end date, appointed by, president's party, and a new "reason tenure term ending" field (death/retirement/promotion/still serving).

**Flagged conflicts surfaced to user:**
1. Dropping Role overrides locked requirements PEDIT-04/PEDIT-08.
2. "Reason tenure ended" has no existing schema column and would require a new migration outside this phase's original schema scope (Phase 22 already shipped).

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, drop Role — amend requirements | Override PEDIT-04/08 | ✓ |
| Keep Role per current requirements | No requirements change | |

**User's choice:** Drop Role, amend requirements (D-10).

| Option | Description | Selected |
|--------|-------------|----------|
| Add "reason tenure ended" now — new migration in this phase | Schema addition alongside UI work | |
| Defer to backlog | Ship with the 5 fields already in PEDIT-09 | ✓ (with a caveat) |

**User's choice:** Defer to backlog, but reserve layout space in the tenure row for it since it's expected soon (D-12). Also stated explicitly: **"Before finalizing your plans, I will provide a mockup of the people page. DO NOT proceed unless I give that to you."**

**Animation question (answered before the pause):**

| Option | Description | Selected |
|--------|-------------|----------|
| Height/slide transition | Card expands/collapses via slide transition | ✓ |
| Fade only | Contents fade in place, no height animation | |

**User's choice:** Height/slide transition (D-11).

**Pause point:** Given the incoming mockup, the user was asked whether to keep discussing the remaining sub-items (rest of Justice Details layout, Tenure appointment field input types) or pause. User chose to pause.

---

## Claude's Discretion

- Exact visual treatment of the click-to-filter pill interaction (active state, clear affordance).
- Advocate argument count (PDIR-04) computation method (distinct arguments vs. total participations).
- Exact wording/styling of the disabled Reason Left / Death Date fields.
- Whether Merge/Delete sections render on `/admin/people/new` (logically no — nothing to merge/delete pre-save).
- Whether to adopt the mockup's breadcrumb-style header ("People > Create Person") consistently on both create and edit pages.

## Deferred Ideas

- **Reason Left** field (died/retired/promoted/still in office, free text) per tenure row — needs new `court_tenures` column + migration. Deferred to a future phase (D-12); renders disabled (D-19) in this phase.
- **Death Date** field on the person record — needs a new nullable column + migration. Deferred to a future phase (D-14); renders disabled (D-19) in this phase.

## Resolved After Mockup Review (see Session 2 above)

- Tenure appointment field input types: both Appointed by and Appointing president's party are plain free text (D-16).
- Bench Details card layout: single consolidated card, no visible title, Bench/Advocate toggle replaces the is_justice checkbox, Birth/Death Date + Tenure Periods appear inline for Bench only (D-13, D-15).
- Photo button label conflict resolved in favor of the locked requirement ("Upload photo," D-17).
