# Phase 25: Pipeline Job Detail Page - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-07-07
**Phase:** 25-pipeline-job-detail-page
**Areas discussed:** Run status card states, Failed step recovery, Resolve card interaction model, Post-creation read-only model

---

## Run Status Card States

| Option | Description | Selected |
|--------|-------------|----------|
| Operator checklist | Show status, PDF link, and a compact list of blockers or next action. | |
| Summary snapshot | Show status, source, timestamps, and linked argument, but keep blockers/actions minimal. | |
| Hybrid | Checklist when action is needed; summary snapshot once the argument is already created. | yes |
| Other | Freeform. | |

**User's choice:** Hybrid.
**Notes:** Not ready uses strict blockers. Ready CTA remains `Create Argument`. Already-created shows argument link only.

---

## Failed Step Recovery

| Option | Description | Selected |
|--------|-------------|----------|
| Error plus Re-run only | Show error and contextual rerun with same source. | |
| Error plus Re-run plus back to list | Include rerun plus all-runs link. | |
| Error plus start-new-run guidance | Give guidance and route to start a corrected new run. | yes |
| Other | Freeform. | |

**User's choice:** Start-new-run guidance.
**Notes:** User reasoned that rerunning with exact same settings is unlikely to yield different results. Guidance should be step-specific; raw errors go in expandable details; Danger Zone remains unchanged. User also raised a deferred bug: source PDF reuse should not be blocked across multiple pipeline runs.

---

## Resolve Card Interaction Model

| Option | Description | Selected |
|--------|-------------|----------|
| Strict two-step | Side must be chosen before person controls are enabled. | |
| Soft ordering | Show all controls but guide side first and validate on submit. | |
| Auto infer with override | Prefill parser/system inference and allow changing it before submit. | yes |
| Other | Freeform. | |

**User's choice:** Auto infer with override.
**Notes:** Keep the current mostly automatic matching where the system matches people when it can. Create-new-person should become a mini popover/dialog with name plus Bench/Advocate side only. Advocate role/title should be editable before Create Argument with extracted hints visible. Missing tenure shows a warning plus person-editor link. Metadata saves should immediately refresh tenure-derived roles.

---

## Post-Creation Read-Only Model

| Option | Description | Selected |
|--------|-------------|----------|
| Read-only provenance page | Show status, source PDF, step results, and argument editor link; no editing. | yes |
| Mostly read-only with limited rerun controls | Same, but keep rerun affordances. | |
| Still editable until published | Allow resolve/metadata edits while draft. | |
| Other | Freeform. | |

**User's choice:** Read-only provenance page.
**Notes:** User stated that once an argument is created, the run that made it exists only for historical reasons. Remove rerun from created-run pages. Keep full provenance visible and leave Danger Zone available for delete-run-only behavior.

---

## Agent's Discretion

- Planner may choose inline or edit-on-demand presentation for advocate role/title controls, provided the fields are editable before Create Argument and extracted hints are visible.
- Exact failed-step guidance copy is open, but must be step-specific.
- Exact popover UI structure is open, but Phase 25 should not become the full person editor.

## Deferred Ideas

- Bug: source PDF reuse should not be blocked across multiple pipeline runs.
- Full create-person interface belongs to Phase 27 People Admin.
