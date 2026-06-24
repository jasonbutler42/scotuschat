# Phase 13: Ingestion Flow Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 13-ingestion-flow-polish
**Areas discussed:** Typeahead UI pattern, "Incomplete" job definition, Progress badge stale state, Uncommitted working-tree changes

---

## Typeahead UI Pattern (PIPE-19)

### Q1: Replace native datalist or fix it?

| Option | Description | Selected |
|--------|-------------|----------|
| Custom combobox | Plain `<input>` + filtered `<ul>` in Svelte — consistent across browsers, full control | ✓ |
| Bits UI Combobox | Reuse bits-ui already installed from Phase 12 merge picker | |
| Fix native datalist | Keep `<datalist>` but improve the event handler | |

**User's choice:** Custom combobox (no new library)

### Q2: Where to filter candidates?

| Option | Description | Selected |
|--------|-------------|----------|
| Client-side on data.people | Full people roster already loaded; filter in $derived on full_name + role | ✓ |
| Client-side on row.candidates only | Smaller set from API, but empty for MISS rows with no API candidates | |

**User's choice:** Filter client-side on data.people (full roster)

### Q3: Add new person placement

| Option | Description | Selected |
|--------|-------------|----------|
| At bottom of dropdown | Same as before — selecting it shows inline AddNewPersonForm below combobox | ✓ |
| Separate button below combobox | Cleaner separation but changes the existing operator flow | |

**User's choice:** Keep Add new person at bottom of dropdown

---

## "Incomplete" Job Definition (PIPE-20)

### Q1: Which statuses count as incomplete?

| Option | Description | Selected |
|--------|-------------|----------|
| paused + failed | Both require operator action before the argument can proceed | ✓ |
| paused only | Only paused needs immediate review; failed is terminal | |
| paused + failed + running | Include running so operators can monitor active work | |

**User's choice:** paused + failed

### Q2: URL param or in-page state?

| Option | Description | Selected |
|--------|-------------|----------|
| URL query param ?incomplete=1 | Matches /admin/people?incomplete=1 pattern; survives reload, bookmarkable | ✓ |
| In-page toggle (no URL change) | No server round-trip but state lost on reload | |

**User's choice:** URL query param

### Q3: Server-side or client-side filter?

| Option | Description | Selected |
|--------|-------------|----------|
| Server-side via API param | Pass incomplete=true to GET /api/admin/jobs; filters at DB level | ✓ |
| Client-side filter | Filter data.jobs in Svelte; no API change needed but over-fetches | |

**User's choice:** Server-side API param

---

## Progress Badge Stale State (PIPE-18)

### Q1: What symptoms have you observed?

| Option | Description | Selected |
|--------|-------------|----------|
| Logic bug (wrong statuses) | stepStatus() produces wrong badge for a step | |
| Poll lag (badges behind reality) | Badges lag ~2.5s after step completes | |
| Both — wrong statuses and delays | | ✓ |
| Not sure — fix defensively | | |

**User's choice:** Both — wrong statuses AND delays

### Q2: Frontend only or also server-side?

| Option | Description | Selected |
|--------|-------------|----------|
| Frontend only | Fix stepStatus() edge cases + reduce poll interval | ✓ |
| Frontend + server-side | Also audit GET endpoint auto-advancement | |

**User's choice:** Frontend only

### Q3: What should Parse show when job is paused?

| Option | Description | Selected |
|--------|-------------|----------|
| Completed | Parse finished before resolve paused | |
| Running | Wrong — Parse already finished | |
| Need to test — unsure | Haven't confirmed what current_step value API returns when paused | ✓ |

**User's choice:** Need to test — diagnostic step first

### Q4: What to show during null current_step transition window?

| Option | Description | Selected |
|--------|-------------|----------|
| Show last known state (don't flash) | Preserve last valid step as 'running' rather than all-pending flash | ✓ |
| Show pending for all | Current behavior — causes the all-pending flash the user sees | |

**User's choice:** Preserve last known state

---

## Uncommitted Working-Tree Changes

### Q1: How to handle?

| Option | Description | Selected |
|--------|-------------|----------|
| Commit as pre-Phase-13 cleanup | Single cleanup commit before Phase 13 execution | ✓ |
| Fold into Phase 13 as its own plan | Add 13-00-PLAN.md to commit them | |
| Commit separately anytime | Outside the phase plan structure | |

**User's choice:** Pre-Phase-13 cleanup commit

### Q2: Is the publish gate removal intentional?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — intentional relaxation | Keep the change | |
| No — accidental edit, revert | Revert admin_arguments.py + +page.svelte; T-11-PUBGATE must remain | ✓ |
| Partial — keep logging, revert gate | | |

**User's choice:** Revert the publish gate removal (it was accidental). Keep logging improvement and --local-file flag.

---

## Claude's Discretion

- Exact visual treatment of the custom combobox dropdown (border, max-height, shadow)
- Whether combobox input clears on Escape or restores to last confirmed value
- Wording of the incomplete filter toggle button
- Combobox item hover/focus highlight color within the admin dark theme

## Deferred Ideas

- Server-side auto-advancement logic audit (GET /api/admin/jobs/{job_id}) — working per Phase 7 validation; not warranted by PIPE-18
- Animated step transitions (badge pulse on flip) — cosmetic; out of PIPE-18 scope
- Jobs list pagination — out of PIPE-20 scope
