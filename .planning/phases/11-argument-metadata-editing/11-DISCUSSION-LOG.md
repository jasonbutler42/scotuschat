# Phase 11: Argument Metadata Editing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 11-argument-metadata-editing
**Areas discussed:** Editor location, Consolidated arguments, Edit availability window, Read-only mode presentation (evolved into Publish model), Admin nav link, Post-resolve publish prompt, Slug behavior

---

## Editor Location

| Option | Description | Selected |
|--------|-------------|----------|
| Job detail page | Editor embedded in /admin/pipeline/[job_id] | |
| Dedicated /admin/arguments/[id] page | New route independent of any job | ✓ |
| Both | Editor on job detail + standalone page | |

**User's choice:** Dedicated `/admin/arguments/[id]` page.
**Notes:** Operator wanted to be able to access and edit argument metadata outside the context of a pipeline run.

### Follow-up: Navigation from job detail page

| Option | Description | Selected |
|--------|-------------|----------|
| Link on job detail page | Read-only preview + "Edit argument metadata" link | ✓ |
| Inline mini-form on job detail | Full page separate too | |
| No link — navigate separately | | |

### Follow-up: Arguments list page

| Option | Description | Selected |
|--------|-------------|----------|
| Per-argument page only | No index list | |
| List page + per-argument edit | /admin/arguments index + edit pages | ✓ |

### Follow-up: Arguments list scope

| Option | Description | Selected |
|--------|-------------|----------|
| All arguments (pending + resolved + published) | Show everything with status badge | ✓ |
| Pending only | Filter to unresolved arguments | |

---

## Read-only Mode / Published State

**Initial question:** Once `resolved_at` is set, how should the editor present the read-only state?

**User's clarification:** User questioned whether the read-only lock was actually necessary. The admin is already protected by auth; making metadata fully locked down seemed unnecessary. User proposed a separate "published" state — an argument doesn't go live until explicitly published; it can still be edited and unpublished at any time.

This evolved the discussion into a full publish model, replacing the ARG-02 read-only gate.

### Publish model structure

| Option | Description | Selected |
|--------|-------------|----------|
| Keep resolved_at + add published_at | resolved_at = pipeline signal; published_at = visibility gate | ✓ |
| Replace resolved_at with published_at | One column; operator always publishes manually | |

**Notes:** `resolved_at` retains its pipeline meaning. New `published_at` controls `/cases/` visibility.

### Publish gating

| Option | Description | Selected |
|--------|-------------|----------|
| Publish only after resolve completes | Button enabled when resolved_at IS NOT NULL | ✓ |
| Publish any time | No gate | |

### Publish controls location

| Option | Description | Selected |
|--------|-------------|----------|
| Button on edit page only | | |
| Toggle on list row only | | |
| Both | List row toggle + edit page button | ✓ |

### Edit availability

**Decision:** Always editable — no read-only lock at any state (pending, resolved, or published). ARG-02 is dropped.

---

## Consolidated Arguments

| Option | Description | Selected |
|--------|-------------|----------|
| Lead case only | Edit lead docket's title and docket number via is_lead=true | You decide → ✓ |
| One row per case | Edit all consolidated cases | |

**User's choice:** "You decide."
**Claude's decision:** Lead case only. Minimal UI complexity; non-lead dockets shown as a read-only reference list.

---

## Edit Availability Window

| Option | Description | Selected |
|--------|-------------|----------|
| Any stage after ingest, until resolved | Available as soon as argument_id is set | ✓ |
| Only after resolve completes | | |

### Job detail page placement

| Option | Description | Selected |
|--------|-------------|----------|
| Top section — above step status | | ✓ |
| Below step status badges | | |

---

## Admin Nav Link for Arguments

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add Arguments to admin TopNav | Pipeline Runner \| Arguments \| People Editor \| Log out | ✓ |
| No — only reachable from job detail | | |

---

## Post-Resolve Publish Prompt

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — show "Ready to publish" CTA on job detail | When COMPLETED and not yet published | ✓ |
| No — operator navigates independently | | |

---

## Slug Behavior

**User asked:** What does a slug look like under option 1 (frozen at ingest)?
**Claude explained:** `"Obergefell v. Hodges"` → slug `obergefell-v-hodges`. Slug is a stable identifier decoupled from the display title from the moment of ingest.

| Option | Description | Selected |
|--------|-------------|----------|
| Slug frozen at ingest | Edits only update case_name | |
| Slug re-derives only pre-publish | Pre-publish: slug updates; post-publish: slug frozen | ✓ |
| Slug always re-derives | Can break published URLs | |

**Notes:** Slug re-derivation logic mirrors `pipeline/commands/ingest.py` `_derive_slug()`. Slug unique constraint requires a validation error on collision, not a DB crash.

---

## Claude's Discretion

- Visual badge styling for Pending / Resolved / Published states
- Label wording for publish/unpublish button ("Publish" / "Unpublish")
- Whether list-row publish control is a button or styled toggle
- Date display format on the arguments list
- Whether the argument edit page heading shows the case title or a generic label
- Consolidated docket display: non-lead dockets shown read-only below editable fields

## Deferred Ideas

- Unpublish → re-resolve workflow (post-publish speaker corrections)
- Bulk publish from the arguments list
- Post-resolve utterance or speaker editing
- ADV-01 (advocate firm/organization in popover) — v1.3
