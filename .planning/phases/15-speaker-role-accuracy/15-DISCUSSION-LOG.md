# Phase 15: Speaker Role Accuracy - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-25
**Phase:** 15-speaker-role-accuracy
**Areas discussed:** Advocate role storage, Role editor location, Justice role fallback

---

## Advocate Role Storage

| Option | Description | Selected |
|--------|-------------|----------|
| Expand SideEnum | ADD PETITIONER/RESPONDENT/AMICUS via ALTER TYPE ADD VALUE IF NOT EXISTS; ADVOCATE stays as legacy value | ✓ |
| Add role_id FK column | Keep side as BENCH/ADVOCATE/UNKNOWN; add nullable argument_participants.role_id → roles.id | |

**User's choice:** Expand SideEnum

---

| Option | Description | Selected |
|--------|-------------|----------|
| Backfill ADVOCATE → UNKNOWN | All existing advocate rows become UNKNOWN so Phase 16 can assign specific roles | ✓ |
| Leave ADVOCATE rows as-is | Service layer treats ADVOCATE and UNKNOWN as equivalent | |

**User's choice:** Backfill ADVOCATE → UNKNOWN

---

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-coded label map | PETITIONER → "Petitioner's Counsel", RESPONDENT → "Respondent's Counsel", AMICUS → "Amicus Curiae", UNKNOWN/ADVOCATE → "Counsel" | ✓ |
| Look up via roles table | Each SideEnum value maps to a row in the roles table; requires seeded rows and a join | |

**User's choice:** Hard-coded label map in service layer

---

## Role Editor Location

**Note:** This area evolved significantly through conversation — the user articulated a broader architectural principle during discussion.

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline job detail only | Advocate role dropdowns live on the pipeline job detail alongside resolve review | |
| Argument edit page only | Canonical home; pipeline job detail is pure historical record | |
| Both (context-sensitive) | Pipeline job detail: prebirth state only. Argument edit page: draft + published state. | ✓ |

**User's choice:** Both — pipeline job detail during prebirth (resolve review), argument edit page as canonical home after approval.

**Notes:** User articulated a key mental model: *the pipeline is a factory; the argument is the product.* An argument "exists" (in the user's sense) when the operator approves the resolve step. Before that, the argument row is DB scaffolding. This led to three significant decisions:

1. **Three-state argument status**: Add `arguments.status` enum column — `pipeline` (prebirth) / `draft` (unpublished) / `published`. Admin arguments list shows draft + published only.

2. **Manual approval always required**: Amends PIPE-14. The resolve step no longer auto-advances even when all speakers are auto-resolved. Every pipeline run ends with an explicit "Approve" action that triggers the `pipeline → draft` transition.

3. **Re-run button**: After approval, pipeline job detail is read-only but shows a "Re-run with same source" button. New run goes through prebirth again; existing draft/published argument is unaffected until the operator approves the new run.

4. **Phase 15 expands to 4 plans** (from 3 in the roadmap) to fold in the status/approval changes.

---

## Justice Role Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Most recent tenure row | Use highest start_date tenure when argued_date falls outside all rows | ✓ (display fallback) |
| Fall back to Person.role_id | Use person's primary role field as stored | |
| Show nothing | Leave role_name null; popover renders without a role line | |

**User's choice:** Most recent tenure row as display fallback.

**Notes:** User reframed this area — the fallback only matters when tenure data is incomplete, which is an operator data quality issue. The more important thing is surfacing the gap so the operator can fix it. User selected "Both" for surfacing:
- **Argument edit page**: Inline warning when argued_date is outside all tenure rows, with link to person edit page.
- **People directory**: New "Justices with tenure gaps" filter for bulk auditing across all people.

---

## Claude's Discretion

- Exact label for the "Approve" button (e.g., "Create Argument", "Approve Run", "Accept")
- Whether advocate role dropdown on pipeline job detail and argument edit page share a component
- Visual treatment of inline tenure gap warning (banner, icon tooltip, etc.)
- Whether the Re-run button requires a confirmation dialog before starting

## Deferred Ideas

- **Multi-appointer tenure attribution** — Different appointing presidents per tenure row; requires data model change. Still deferred from Phase 14.
- **Full pipeline-as-form redesign** — User's mental model is "the pipeline fills out a form for me." Current approach implements the correct conceptual model without a UI redesign. Noted for a potential future milestone.
- **Advocate firm/organization in popover** — REQUIREMENTS.md ADV-01. Not in scope.
