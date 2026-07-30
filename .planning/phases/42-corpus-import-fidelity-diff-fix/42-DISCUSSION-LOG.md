# Phase 42: Corpus Import Fidelity Diff & Fix - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-29
**Phase:** 42-corpus-import-fidelity-diff-fix
**Areas discussed:** Fixture import mechanism, court_tenures' role in the diff, Diff artifact form, Classification confirmation gate

---

## Fixture import mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Build a one-case loader | Add a new option to the import tool that loads just one specific case instead of a whole year — cleaner, database only ever has the 1 test case | ✓ |
| Load the whole year, clean up after | Run the existing `import-convokit --term 1966` tool as-is (135 conversations), rely on Phase 43's later full database wipe to clean up the extras | |
| You decide | Let Claude pick based on simplicity/risk | |

**User's choice:** Build a one-case loader (recommended).
**Notes:** Term 1966 has 135 conversations total; running the existing term-based CLI would import 134 unwanted arguments as a side effect of loading the one fixture.

---

## court_tenures' role in the diff

| Option | Description | Selected |
|--------|-------------|----------|
| Double-check it anyway | Confirm the fixture's Justices already have correct, complete tenure data from the separate tool that maintains it | ✓ |
| Skip it, mark not applicable | Don't check this table at all since import-convokit never writes to it | |

**User's choice:** Double-check it anyway (recommended).
**Notes:** import-convokit never writes to `court_tenures` — a separate tool (`import_justices_csv.py`) maintains judges' history. Follow-up question: if a gap is found in the judges' history data —

| Option | Description | Selected |
|--------|-------------|----------|
| Just flag it, don't fix it here | Note the problem in the findings; leave the fix to whatever tool/process normally maintains judges' history | ✓ |
| Fix it as part of this phase too | Treat it like any other bug found and fix it directly | |

**User's choice:** Just flag it, don't fix it here (recommended).

---

## Diff artifact form

| Option | Description | Selected |
|--------|-------------|----------|
| Save it as a document | Write a saved file (same pattern as Phase 41's FIXTURES.md) listing every field checked, whether it matched, and why | ✓ |
| Screen output only | Print the comparison results while the check runs; nothing saved for later | |

**User's choice:** Save it as a document (recommended).

---

## Classification confirmation gate

| Option | Description | Selected |
|--------|-------------|----------|
| Review each call before fixing | Operator personally reviews and approves each "bug vs. on-purpose" classification before anything gets fixed, mirroring Phase 41's confirm-before-proceed gate | ✓ |
| Claude decides, you review at the end | Claude classifies using established rules and fixes real bugs directly; operator reviews the final writeup only | |

**User's choice:** Review each call before fixing (recommended).
**Notes:** Follow-up — should the review happen as one batch, or one gap at a time?

| Option | Description | Selected |
|--------|-------------|----------|
| One batch review | Full comparison document finished first (all gaps found and classified), operator reviews the whole thing at once | ✓ |
| One at a time as we go | Stop and confirm each gap's classification right when it's found | |

**User's choice:** One batch review (recommended).

---

## Claude's Discretion

None — every area reached an explicit user choice.

## Deferred Ideas

None new this phase. The two previously-pending todos (unpublished-argument-visible-in-cases-list, popover-scrollbar-outside-card) were reviewed but confirmed as already assigned to Phase 45 — not folded here.

## Session Note

The user asked partway through this discussion to keep language plain and avoid tech-industry jargon (late-evening session) — the remaining questions in this log were phrased accordingly, which is why the wording above reads more conversationally than a typical technical discussion log.
