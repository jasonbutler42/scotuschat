---
phase: 44
slug: resolve-table-rework
doc: figma-canonical-reconciliation
status: ready-for-execution
created: 2026-08-04
figma_file: 9PDECvbdHM2vYVxt3SCwru  # "SCOTUS-chat", page "screen mockups for GSD"
---

# Phase 44 — Figma Canonical Reconciliation

Design exploration converged on a **new canonical layout** for the Resolve flow that
differs materially from what shipped in plans 44-01→44-04. This doc locks the design
decisions and gives a prioritized fix-list to reconcile `ResolveCard.svelte` (and a
little of the pipeline route + API) with the Figma spec.

The mockup that seeded this phase (`resolve-speakers-panel.png`, a standalone
"Resolve Speakers" modal with Apply/Cancel) is **superseded and discarded** — it never
matched the pipeline-embedded, per-row-save reality of the build. The canonical spec
below replaces it.

## Canonical Figma states (source of truth)

Page "screen mockups for GSD" in the SCOTUS-chat file:

- Working card · PDF/Extracted — node `4205:81`
- Corpus card · all-resolved/Imported (Continue enabled) — node `4210:81`
- Read-only card · completed — node `4206:111`
- States & feedback (Continue / degraded / saving / error) — node `4194:72`
- Components (Toggle, Tag, Resolved-As dropdown, Badge/Avatar/Hint) — node `4202:127`, `4183:22`, `4183:27`, `4184:2`

## Canonical design (locked)

1. **Four columns**, not five: `Raw Label | Resolved As (side + person) | Argument Role | Descriptor`.
   The Bench/Advocate toggle and the person control live **stacked in one cell** (toggle on top,
   person control below). The standalone Bench/Advocate column is removed.
2. **Resolved As = a single dropdown control** (the "dropdown-only" model), pre-filled when matched,
   "Select person…" when not. This **eliminates** the "Change" link, the standalone "Select person…"
   link, and the entire confirm-vs-correct state machine (`disposition: 'confirmed' | 'corrected'`,
   the "✓ Corrected" banner, `openPersonSearch`). You just change the value; the control is always
   the entry point.
3. **Person search is scoped to the selected side** — bench-only when Bench is chosen, advocate-only
   when Advocate is chosen ("Select advocate…" / "Select bench…"; "Create new advocate"). The side
   gate is now structural: the toggle sits above the search.
4. **Hint prefix reflects ingestion source, uniform per card**: `Imported:` for a corpus-import run,
   `Extracted:` for a PDF-extract run. (A single AdminJob is one source, so it never mixes within a card.)
5. **Bench Argument Role is a live-derived value, never a snapshot.** Displayed identically in the
   editable card and the read-only/published card:
   - tenure covers the argument → `Calculated from tenure` + the derived role in a locked box.
   - tenure missing → `⚠ Missing tenure` + `Tenure not found` + `Edit person ↗` (opens a **new tab**).
   Fixing tenure elsewhere (e.g. another tab) must make this cell recompute — including on an argument
   that has already left the pipeline.
6. **Bench Descriptor**: renders a dash, **no hint line**, and the stored value is **preserved, not
   wiped**, when a row switches advocate→bench (hidden, not shown, not cleared).
7. **Unresolved bench role** shows `(resolve person first)` — no em dash, no hint.
8. **Progress + always-visible Continue**: header shows `N of M speakers still need review`; the
   Continue button is always visible, disabled with a reason (`Resolve N more to continue`) until done,
   then enabled (`Continue Resolve`). Replaces "button only appears when all dispositioned."
9. **Row cue**: auto-matched rows carry an `AUTO-MATCHED` tag; rows needing operator input carry a
   `NEEDS YOU` tag, so the eye finds the misses first.
10. **Read-only keeps table headers** and the same hint logic (Imported/Extracted where ingested,
    Calculated where derived, dash where a value can never exist).

## New/locked requirements (continue numbering from RESOLVE-06)

- **RESOLVE-07** — Resolve table is 4 columns; Bench/Advocate toggle and person control are stacked in the Resolved As cell.
- **RESOLVE-08** — Resolved As is a single always-editable dropdown; remove Change/Select links and the confirm/correct disposition state machine.
- **RESOLVE-09** — Person search candidates are filtered to the currently-selected side (bench vs advocate).
- **RESOLVE-10** — Hint prefix is source-aware (`Imported:` corpus / `Extracted:` PDF), uniform per run.
- **RESOLVE-11** — Bench role + missing-tenure state is live-derived on every read (incl. published arguments), rendered identically in editable and read-only; `Edit person` opens in a new tab.
- **RESOLVE-12** — Bench role hint copy is `Calculated from tenure` / `Tenure not found` (not `Imported: N/A - …`).
- **RESOLVE-13** — Bench rows show no descriptor hint and a dash; the stored descriptor is preserved (not cleared) on a side switch.
- **RESOLVE-14** — Unresolved bench role renders `(resolve person first)` with no dash and no hint.
- **RESOLVE-15** — Persistent progress indicator + always-visible, reason-disabled Continue.
- **RESOLVE-16** — Auto-matched / Needs-you row cue tags.

## Reconciliation diff — canonical vs. built

Built = `app/src/lib/components/ResolveCard.svelte` unless noted.

| # | Area | Built now | Canonical | Files | Priority |
|---|------|-----------|-----------|-------|----------|
| 1 | Table shape | 5 columns (separate Bench/Advocate column) | 4 columns; side+person stacked in Resolved As `<td>` | ResolveCard.svelte (`<thead>`, row `<td>` structure) | **High (structural)** |
| 2 | Resolved As model | resolved display + "Change", or "Select person…" link → opens combobox; `disposition` confirmed/corrected, "✓ Corrected" banner, `openPersonSearch`, `needsSideGate` gating a disabled link | single dropdown control, always the entry point; delete confirm/correct machinery | ResolveCard.svelte (rowMatchStates, openPersonSearch, personDisplay/link branches) | **High (structural)** |
| 3 | Side-scoped search | `getRowCandidates` merges all people + candidates, unfiltered by side | filter candidate list by `effectiveSide(row)` (bench vs advocate population) | ResolveCard.svelte `getRowCandidates`; may need a person `is_justice`/side field from API | High |
| 4 | Hint prefix | hardcoded `prefixLabel="Imported"` on all 4 hints (D-09) | source-aware: `Imported` (corpus) / `Extracted` (PDF); derive from the run's source | ResolveCard.svelte hint call sites + a `source` prop from `+page.server.ts` (job strategy: `convokit_import` → corpus, else PDF) | High |
| 5 | Bench role hint copy | `Imported: N/A - from tenure` / `Imported: N/A - tenure not found` via `argumentRoleHintValue` | `Calculated from tenure` / `Tenure not found` + `Edit person ↗`; not an `Imported:`/`Extracted:` hint at all | ResolveCard.svelte `argumentRoleHintValue`, argument-role cell | Medium |
| 6 | Bench descriptor hint | `descriptorCell` always renders the `Imported:` hint, incl. bench | suppress hint entirely on bench rows | ResolveCard.svelte `descriptorCell` | Medium |
| 7 | Descriptor preservation | verify: does switching side to BENCH clear `descriptor`? Must not. | keep stored value, don't render on bench, don't wipe on advocate→bench | `saveResolveRow` path + `PATCH …/resolve-rows` (api) | Medium |
| 8 | Unresolved bench role | locked box shows `–` (`bench_role ?? argument_role ?? '–'`) when bench + no person | render `(resolve person first)`, no dash, no hint | ResolveCard.svelte argument-role cell | Medium |
| 9 | Live tenure recompute | missing-tenure branch renders regardless of readonly (good). Confirm `bench_role`/`missing_tenure` are recomputed from `court_tenures` on every read of a **published** argument, not stored at resolve time | recompute live on read, everywhere | api resolve-rows / argument read path (`get_job_readiness` / argument detail) | High (verify) |
| 10 | Edit person target | link is same-tab | `target="_blank" rel="noopener"` | ResolveCard.svelte (both editable + read-only branches) | Low |
| 11 | Progress + Continue | Continue only when `allDispositioned`; no remaining count | persistent `N of M …` + always-visible reason-disabled Continue | ResolveCard.svelte footer + header | Medium |
| 12 | Row cue tags | none | `AUTO-MATCHED` / `NEEDS YOU` per row | ResolveCard.svelte Resolved As cell | Low |

Keep as-is (already correct): per-row inline save, "Continue Resolve" embedded model, saving-disabled
controls, per-row save error, people-load degraded banner, read-only table headers, apolitical/no-`{@html}`
constraints.

## Open questions / risks

- **RESOLVE-09 needs a side signal per candidate.** Confirm `people`/candidate payloads expose whether a
  person is bench (justice) vs advocate so the list can be filtered. If not, the API must add it.
- **RESOLVE-11 live recompute on published arguments** is the biggest correctness item — verify the read
  path derives role from `court_tenures` at query time rather than reading a persisted column.
- Column merge (RESOLVE-07/08) is the largest single change; sequence it first, then layer copy/behavior
  fixes on top.

## Next action

Execute as a follow-on plan (44-05 or a v1.8 phase). Sequence: structural (1,2) → data/behavior
(3,4,7,9) → copy/visual (5,6,8,11,12,10).
