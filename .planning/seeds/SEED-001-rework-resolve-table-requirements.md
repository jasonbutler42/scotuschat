---
id: SEED-001
status: dormant
planted: 2026-07-07
planted_during: 25-pipeline-job-detail-page
trigger_when: next milestone planning (/gsd-new-milestone scan)
scope: small
audit_acknowledged:
  milestone: v1.8
  at: 2026-09-23
  status: dormant
---

# SEED-001: Rework the Resolve card/table beyond what Phase 25 delivered

## Why This Matters

Surfaced during Phase 25 UAT (`.planning/phases/25-pipeline-job-detail-page/25-UAT.md`). The user noted the Resolve table "still needs more work, but it's getting closer" and intends to write up detailed requirements for further changes to `ResolveCard.svelte` / the resolve-row workflow as part of this milestone. This is explicitly a placeholder — the actual requirements have not been written yet.

## When to Surface

**Trigger:** next milestone planning (`/gsd-new-milestone` scan)

This seed will surface during the next `/gsd-new-milestone` run, whenever that happens. Enriched 2026-07-12 — the requirements write-up (mockup deltas, open design question) is already detailed enough to plan against once surfaced; no further wait on requirements.

## Scope Estimate

**Small** — frontend-only rework of `ResolveCard.svelte`. Per the seed's own finding (delta #3), the backend is already ready: `SideEnum` already has `PETITIONER`/`RESPONDENT`/`AMICUS`, `ADVOCATE_LABEL_MAP` already maps them to display labels, and `ResolveRowUpdate.side` / `update_resolve_row_for_job` already accept these values. No new schema, service, or endpoint work anticipated — confirm during actual planning.

**Core driver (confirmed 2026-07-12):** the Argument Role column is currently a read-only mirror of the overloaded Bench/Advocate `<select>`, not a real control — operators can't directly set Petitioner's/Respondent's Counsel. That's the primary "why" for this rework (the visual stacked-card issue in the Open Design Question below is a secondary, related concern).

## Breadcrumbs

- `app/src/lib/components/ResolveCard.svelte` — the current Resolve card implementation from Phase 25.
- `app/src/routes/admin/pipeline/[job_id]/+page.svelte` — step-cards loop (line ~235) and where `ResolveCard` is composed as a sibling after it (line ~404).
- `.planning/phases/25-pipeline-job-detail-page/25-UAT.md` — UAT session where this was raised, including two related confirmed issues (missing create/switch-person trigger, WR-04 Continue Resolve visibility, both resolved as a test-precondition gap) and a cosmetic spacing/header gap (fixed 2026-07-07, commit c126ef5b).
- `.planning/phases/25-pipeline-job-detail-page/25-UI-SPEC.md` (Layout Contract) and `25-04-SUMMARY.md` key-decisions — the locked Phase 25 decision that the pipeline "Resolve" step-status card and `ResolveCard`'s "Resolve" workflow card are intentional separate siblings (D-05/D-20), not a naming collision.

## Open Design Question (added 2026-07-07)

User reviewed a live screenshot and pushed back on the Phase 25 sibling-card decision above: two cards both titled "Resolve" stacked directly on top of each other reads as one broken/malformed card, not two purposeful ones, regardless of the underlying "step status vs. workflow" conceptual split. When this seed is worked, consider whether the pipeline step-status treatment (badge, "Needs review" pill, etc.) for the Resolve step specifically should be folded into the top of `ResolveCard` itself, superseding D-05/D-20 — while leaving Ingest/Parse as plain step-status cards (they have no equivalent "workflow" card of their own).

## Mockup: Target Resolve Table Design (added 2026-07-07)

User provided a concrete mockup image (`resolve-speakers-panel.png`, originally at `C:\workspace\scotuschat\resolve-speakers-panel.png` — outside the repo, so re-request/re-attach it when this seed is worked if the file is no longer available) with 5 sample rows: a resolved Bench row with valid tenure (Chief Justice Roberts), a resolved Advocate row (Prelogar), an unresolved intervention row needing a person search (Bopp), a fully-unresolved row (Unknown Speaker), and a resolved Bench row with a tenure gap (Souter, "Missing tenure").

**Columns (5, not 6):** RAW LABEL | RESOLVED AS | BENCH/ADVOCATE | ARGUMENT ROLE | DESCRIPTOR — no separate "Action" column.

**Concrete deltas vs. the current Phase 25 `ResolveCard.svelte`:**

1. **No "Action" column.** The current Confirm/Select/Change buttons (column 6) move into the "Resolved as" cell itself: a blue "Select person..." (with search icon) link for unresolved rows, or the resolved name + a plain "Change" text link for resolved rows. This also removes the current visual redundancy of a whole extra column that, for most rows, just shows a dash.

2. **"Bench/Advocate" becomes a two-button segmented toggle** (Bench | Advocate, only one highlighted/active) instead of the current `<select>` dropdown.

3. **"Argument Role" becomes the actual write control for advocate granularity, not a read-only mirror.** This is the important one: the CURRENT `<select name="side">` in column 3 (`ResolveCard.svelte` ~563-586) already offers `BENCH`, `PETITIONER`, `RESPONDENT`, `AMICUS`, `UNKNOWN` as one overloaded dropdown, and the CURRENT "Argument Role" column (4) is a read-only mirror of whatever that select produced (`ADVOCATE_LABEL_MAP.get(side)` for advocates, tenure-derived `bench_role` for bench — see `api/services/admin_people.py:704` and `ResolveCard.svelte` 597-615). The mockup splits this correctly: "Bench/Advocate" toggle picks the coarse category only; "Argument Role" becomes a dropdown of "Respondent's Counsel / Petitioner's Counsel / Select role" for advocate rows (writable), while staying a locked, read-only, tenure-derived value (shown with a 🔒 lock icon when resolved, or the existing ⚠ "Missing tenure" + "Edit person" treatment when not) for bench rows.
   - **Backend is already ready for this.** `SideEnum` already has `PETITIONER`/`RESPONDENT`/`AMICUS` (`api/models/models.py:36-42`), `ADVOCATE_LABEL_MAP` already maps them to "Petitioner's Counsel"/"Respondent's Counsel"/"Amicus Curiae" (`api/services/speakers.py:34-37`), and `ResolveRowUpdate.side` / `update_resolve_row_for_job` already accept these values directly (see `api/tests/test_admin_jobs_phase25.py` using `side=SideEnum.PETITIONER`/`RESPONDENT`). **This looks like it can be a frontend-only rework of `ResolveCard.svelte` columns 3-4** — no new schema, service, or endpoint work anticipated, pending confirmation during actual planning.

4. **"Title" column renamed "Descriptor" and always rendered** (shown as "–" for bench rows) instead of being conditionally hidden entirely for BENCH rows (current PJOB-15 behavior, `ResolveCard.svelte` ~617-646).
   - **Rationale (user, 2026-07-07):** across real transcripts, the extracted value in this field isn't consistently a "title" — sometimes it's a formal title ("Attorney General, State of Missouri"), sometimes it's just a location ("Arlington, Texas"), sometimes something else. Splitting this into multiple structured fields (title / location / affiliation) isn't worth it since the source data doesn't reliably map to any fixed shape — a single generic free-text "Descriptor" field is the intentional choice, not an oversight.
   - **Implementation-detail question for plan time (not decided):** whether to rename the underlying `ArgumentParticipant.title`/`title_hint` DB columns to match, or keep the column name `title` and only rename in the UI/copy layer — a column rename is pure churn unless a future maintainer reading raw SQL/schema would genuinely be confused by `title` holding "Arlington, Texas."
   - The mockup's own placeholder text on the empty Bopp-row Descriptor input (`e.g. Attorney,...`) already does the work of signaling "this can be anything" to the operator, rather than needing it explained in the column label/copy — carry that placeholder-copy pattern forward.

5. **Every column gets an "Extracted: ..." hint consistently** (Resolved As, Bench/Advocate, Argument Role, Descriptor all show a raw-extraction subtext) — currently only the Title/Descriptor column has this treatment.

6. **Lock icon (🔒) on a resolved, tenure-valid Bench role** — a small visual affordance signaling "this is system-derived and not editable," distinct from the existing ⚠ "Missing tenure" warning state (which is unchanged from current behavior).

## Notes

Captured via one-shot seed capture during Phase 25 UAT. Enrich with trigger, why, and scope once the user's written requirements are available — the mockup above plus the backend-readiness finding suggest this could land as a single small-to-medium frontend-focused phase, but confirm during actual planning (discuss-phase/plan-phase) rather than assuming from this seed alone.
