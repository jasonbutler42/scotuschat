# Phase 27: People Admin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-08
**Phase:** 27-People Admin
**Areas discussed:** Tabs & per-tab filters, Create-person flow, Justice Details card (partial — paused pending mockup)

**Note:** Discussion was explicitly paused by the user before the "Tenure appointment fields" area and before finishing "Justice Details card" — they are providing a mockup of the People pages before those items and final planning proceed.

---

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
- Exact wording/styling of the reserved placeholder space for the deferred "reason tenure ended" field.

## Deferred Ideas

- "Reason tenure ended" field (death/retirement/promotion/still serving) per tenure row — needs new `court_tenures` column + migration. Deferred to a future phase; this phase reserves layout space only.

## Not Yet Discussed (blocked pending mockup)

- Tenure appointment field input types (Appointed by, Appointing president's party — free text vs. constrained select).
- Remaining Justice Details card layout details beyond D-10/D-11/D-12.
