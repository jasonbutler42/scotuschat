# Phase 18: People Schema + Editor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-29
**Phase:** 18-People Schema + Editor
**Areas discussed:** Toggle placement, Role field conditionality, Editor reactivity on toggle

---

## Toggle Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top of Basic Info | Checkbox at the very top of the Basic Info card, before name fields. Most discoverable — operator sees it immediately. | ✓ |
| Standalone card | A separate card between Basic Info and the conditional sections — clean visual separator. | |

**User's choice:** Top of Basic Info
**Notes:** None

---

## Toggle Label

| Option | Description | Selected |
|--------|-------------|----------|
| Is Justice | Short and direct. Matches schema column name and REQUIREMENTS.md language. | ✓ |
| Supreme Court Justice | More descriptive but verbose. | |
| You decide | Claude picks the most idiomatic label. | |

**User's choice:** Is Justice

---

## Role Field Conditionality

| Option | Description | Selected |
|--------|-------------|----------|
| Inline hide within Basic Info | Wrap Role select in `{#if isJustice}`. Minimal restructuring. | ✓ |
| Move Role to a conditional section | Extract Role out of Basic Info into a card alongside Tenure and Appointment. | |
| Role always visible | Leave Role in Basic Info, always shown (deviates from REQUIREMENTS). | |

**User's choice:** Inline hide within Basic Info

---

## Role ID on Save (when is_justice = False)

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve in DB | Hiding doesn't delete data. role_id survives save while is_justice = False. | ✓ |
| Clear on save | If is_justice = False, set role_id = null on save. | |

**User's choice:** Preserve in DB

---

## Court Tenure Rows on Save (when is_justice = False)

| Option | Description | Selected |
|--------|-------------|----------|
| Preserve tenure rows | Hiding section doesn't delete court_tenure rows. | ✓ |
| Delete tenure rows on save | If is_justice = False, delete all court_tenures. | |

**User's choice:** Preserve tenure rows

---

## Directory Listing Indicator

| Option | Description | Selected |
|--------|-------------|----------|
| No indicator | Directory listing stays as-is. | |
| Justice badge on row | Add a small badge/indicator to rows where is_justice = True. | ✓ |

**User's choice:** Justice badge on row

---

## Editor Reactivity on Toggle

| Option | Description | Selected |
|--------|-------------|----------|
| Reactive immediately | Sections show/hide in real-time as checkbox is toggled — same pattern as showAddRoleForm. | ✓ |
| Only after save+redirect | Sections change only after form is saved and page reloads. | |

**User's choice:** Reactive immediately — `isJustice` bound to `$state`, sections in `{#if isJustice}`

---

## Hidden Field Submission

| Option | Description | Selected |
|--------|-------------|----------|
| Omit hidden fields | `{#if isJustice}` removes inputs from DOM; absent = leave unchanged (PersonUpdate pattern). | ✓ |
| Submit via hidden inputs | Keep hidden inputs carrying current values even when sections are hidden. | |

**User's choice:** Omit hidden fields — consistent with existing PersonUpdate behavior

---

## is_justice Save Mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Part of main save action | Add is_justice to ?/save form action and PersonUpdate. One save covers everything. | ✓ |
| Separate ?/setJustice action | Dedicated action triggered immediately on checkbox change. | |

**User's choice:** Part of main save action

---

## Claude's Discretion

None — all areas had explicit user selections.

## Deferred Ideas

- Live polling for pipeline list page job cards → Phase 20 (folded at user request, out of Phase 18 scope)
- Prevent duplicate argument creation during ingest → Phase 19 (folded at user request, out of Phase 18 scope)
