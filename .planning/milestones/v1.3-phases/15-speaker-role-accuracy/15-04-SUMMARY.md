---
phase: 15-speaker-role-accuracy
plan: 04
status: complete
completed: 2026-06-26
commits:
  - 828ccb6
  - 3c2c41c
  - (this session — bug fix + cleanup)
---

# Plan 15-04 Summary: Advocate Roles Editor, Tenure-Gap Warnings, Status Badge, People Toggle

## What Was Built

**arguments/[id]/+page.server.ts**
- `updateParticipantSide` action: reads `participant_id` + `side` from formData, PATCHes `/api/admin/arguments/${params.id}/participants/${participant_id}` with `X-Admin-Token`, returns `fail(422/502, { roleError })` on error, redirects 303 on success
- Load surfaces `tenure_gap_warnings` and advocate participants from the 15-02 `ArgumentDetail` schema (no second fetch)
- Existing `save`/`publish` actions unchanged; `ADMIN_TOKEN`/`FASTAPI_BASE_URL` from `$env/static/private` only

**arguments/[id]/+page.svelte**
- "Advocate Roles" section with helper text, per-advocate `<select>` (PETITIONER/RESPONDENT/AMICUS/UNKNOWN), Save button submitting `?/updateParticipantSide` via `use:enhance`; editable in both draft and published states; `role="alert"` error on `roleError`
- TenureGapWarning banners: `role="status"`, amber border `#fbbf24`, warning copy + "Edit person" link to `/admin/people/{person_id}`, placed below metadata above publish/unpublish
- Status badge reads `argument.status` enum: pipeline→#94a3b8, draft→#a78bfa, published→#4ade80

**arguments/+page.svelte**
- `badgeStyle`/`badgeLabel` rewritten to read `status` string (draft→#a78bfa, published→#4ade80)
- "Status" column added to table with per-row badge; no pipeline rows (filtered by 15-02 backend)

**people/+page.svelte + people/+page.server.ts**
- `tenureGaps` `$derived(data.tenure_gaps ?? false)` toggle with `role="switch"`, `aria-checked`, #93c5fd when active
- Navigates to `?tenure_gaps=1` / clears param; empty state "No Justices with tenure gaps found." at 14px #94a3b8
- Server module forwards `tenure_gaps=1` to the people API

## Bug Fixed This Session

**`each_key_duplicate` crash on `/admin/pipeline/[job_id]`**

The `{#each data.participants as p, i (p.person_id)}` key was `person_id`, which is NOT unique — the same person can appear as multiple `ArgumentParticipant` rows (matched from two different raw speaker labels). This caused Svelte to throw `each_key_duplicate` during hydration, collapsing the entire component above the list.

Fix: changed key to `(p.participant_id)` — the table primary key, always unique.

Also hardened `lastKnownStep` initialization to `data?.job?.current_step ?? null` (safe access).

## Decisions

- D-12: Advocate role editor uses `?/updateParticipantSide` per-participant form action, not auto-save; consistent with existing save CTA pattern
- D-15: TenureGapWarning banners are informational only (`role="status"`); no blocking gate on publish
- Participants each-key: `participant_id` is the correct key (PK); `person_id` is a FK that can repeat across argument_participants rows for the same argument

## Threats Mitigated

- T-15-04-IDOR: `updateParticipantSide` passes `argument_id` (from URL params) + `participant_id`; backend scopes WHERE to both, 404s on mismatch
- T-15-04-TOKENLEAK: `ADMIN_TOKEN` attached server-side only; never PUBLIC_ or client-visible
- T-15-04-LEAKSTATE: Arguments list relies on 15-02 status filter; pipeline rows never reach the list

## UAT Result

All criteria passed (2026-06-26):
- Role save is isolated per argument (ROLE-03 confirmed)
- Tenure-gap banners render with amber border and correct "Edit person" links
- Arguments list shows Status column with Draft/Published badges; no pipeline rows
- People tenure-gaps toggle filters correctly and adds `?tenure_gaps=1` to URL
- Advocate role dropdowns visible on pipeline job detail page for non-BENCH participants
