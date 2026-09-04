---
created: 2026-09-03
kind: note
source: Phase 51 plan 51-10 Task 3 walkthrough — operator asked how to test consolidated dockets
resolves_phase: null
priority: low
---

# Consolidated dockets cannot be created on a corpus-only project

Filed to stop the next person re-deriving this. It cost a chain of greps during
the 51-10 walkthrough, and the answer is not visible from any one file.

**There is no visual defect.** The block on `/admin/arguments/[id]` is wrapped in
`{#if data.argument.consolidated_dockets.length > 0}`, so it is hidden rather
than rendered empty. The problem is that the feature is unreachable and nothing
says so.

## The reachability chain

- The admin detail page **displays** consolidated dockets read-only
  (`app/src/routes/admin/arguments/[id]/+page.svelte`, the `{#if}` above).
- They are **derived**, not stored: `api/services/admin_arguments.py` selects
  `CaseArgument` rows joined to `Case` where `is_lead == False`. There is no
  `consolidated_dockets` column on any model.
- `update_argument` does **not** touch them — it handles `argued_date`,
  `case_name` and `docket_number` only. Nothing in the admin API writes them.
- The **only** writer of a non-lead row in the whole codebase is
  `pipeline/commands/ingest.py`, which sets
  `is_lead=(case.docket_number == lead_docket)` when a run supplies more than
  one docket. That is the **PDF ingest path**.
- `pipeline/commands/import_convokit.py` — the corpus path — hardcodes
  `is_lead=True` and creates exactly one case per argument.
- The corpus carries no consolidation data to import even in principle: across
  all 7,748 records in `data/corpus/cases.jsonl`, `docket_no` is always a single
  docket and the schema has no consolidated or related-docket field.

So on the corpus-first route (2026-08-18 decision) a consolidated docket cannot
exist, and no amount of operator action in the admin UI will produce one.

## Why this is easy to get wrong

`DocketPillInput` — the multi-docket entry control — lives on `/admin/pipeline`'s
**New Run** form, which feeds the ingest path. It is *not* on the argument detail
page. Seeing that control, and seeing the detail page render consolidated
dockets, makes operator entry look supported. It is not.

## What was verified, and how

Two non-lead `Case` + `CaseArgument` rows were seeded directly against argument
1841 in the dev database on 2026-09-03 to exercise the **render** path, which is
what Phase 51 shipped. It rendered correctly:
`[{'docket_number': '84-1494'}, {'docket_number': '84-1495'}]`. Those rows are
dev-only and disappear on the next `reset-to-fixture`.

The **public** payload does not carry consolidated dockets at all — the term
endpoint returns `argued_date, argument_id, case_name, docket_number,
question_number, slug, term_year`. Whether public should ever show them is an
open question nobody has been asked; today the answer is no by construction.

## Options when this is picked up

1. **Leave it.** The display is correct for the day the PDF route returns, and it
   is hidden meanwhile. Cost is only the rediscovery this note now prevents.
2. **Say so in the UI** — a line on the detail page explaining that consolidated
   dockets arrive with a multi-docket import, so an operator looking for a way to
   add one stops looking.
3. **Decide the public question** — whether a consolidated case's other dockets
   belong on the public listing. That is a product call, not a code gap.

Related: Phase 999.11 (BACKLOG) covers the PDF import path's adaptation
generally, but not this specific reachability gap.
