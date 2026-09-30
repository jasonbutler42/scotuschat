# Phase 54: Publishing at Scale & Verification Debt - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-30
**Phase:** 54-publishing-at-scale-verification-debt
**Areas discussed:** Bulk approval, Harlan misattribution (moved to Phase 53.1), Where the corpus lives, Operator report & scope

---

## Bulk approval

| Option | Description | Selected |
|--------|-------------|----------|
| Separate bulk-approve | Two commands, each with --dry-run; approval is its own logged act | ✓ |
| bulk-publish approves too | One command walks candidate → draft → published | |
| Approve only the clean ones | Skip arguments with open review items | |

**User's choice:** Separate bulk-approve

| Option | Description | Selected |
|--------|-------------|----------|
| Skip them, list them | Open needs_review items stay candidate for the review queue | ✓ |
| Approve everything | Trust gate is the only filter | |
| You decide | Decide once counts are known | |

**User's choice:** Skip them, list them

| Option | Description | Selected |
|--------|-------------|----------|
| Mark it as bulk | Status-log row records the bulk run | ✓ |
| Identical to a manual publish | No distinction, no schema change | |

**User's choice:** Mark it as bulk

---

## Harlan misattribution (moved to Phase 53.1)

| Option | Description | Selected |
|--------|-------------|----------|
| Fix it in this phase | Correct before bulk publish | ✓ |
| Hold back affected arguments | Publish the rest | |
| Publish now, fix later | Separate phase before launch | |

**User's choice:** Fix it before publishing.
**Notes:** The follow-up questions (general vs narrow rule; the stray 2003 utterance) were interrupted.
The operator raised a screenshot of the admin "Justices with tenure gaps" filter flagging Thurgood
Marshall. Investigation found he was credited with his justice id while arguing as Solicitor General
in 1967, and a corpus-wide scan found ~4,300 tenure-impossible turns in three classes. The operator
agreed they need different handling, chose an advocate-card note for future justices ("showing
that they eventually become a justice can eliminate the confusion…"), and chose to **insert Phase
53.1** rather than fold the work into 54. Recorded in `53.1-PRE-DISCUSSION-NOTES.md`.

---

## Where the corpus lives

| Option | Description | Selected |
|--------|-------------|----------|
| Separate full-corpus database | Own DB; fixtures reset stays fast; config switch | ✓ |
| Full corpus in the dev DB | One DB; resets slow or lose the corpus | |
| Reset gets a 'full corpus' mode | One DB, two reset targets | |

**User's choice:** Option 1 — "Is it kind of like a 'staging' database?"
**Notes:** Clarified: not staging (a deployment environment, v2.0); a local database holding launch
data. The launch script is the reusable piece a future staging would replay.

---

## Operator report & scope

| Option | Description | Selected |
|--------|-------------|----------|
| Totals + every exception | Counts per outcome, one line per non-success | ✓ |
| Every row | ~7,800 lines | |
| Totals only | Exceptions via admin UI | |

| Option | Description | Selected |
|--------|-------------|----------|
| Scoped, like import-convokit | --term / --term-range / --conversation-id | ✓ |
| Whole corpus only | No flags | |

---

## Claude's Discretion

- Chunking/commit strategy under PgBouncer (services commit internally today)
- DB-switch config mechanism
- Shape of the bulk-run marker
- Which surfaces/terms beyond 1955 and which DB each VERIFY check uses

## Deferred Ideas

- A real staging environment seeded by the launch script — v2.0
