# Phase 12: People Admin Improvements - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 12-people-admin-improvements
**Areas discussed:** photo_url storage format, Photo upload UI, Merge UI flow, Delete entry point

---

## photo_url storage format

| Option | Description | Selected |
|--------|-------------|----------|
| Full public URL | Store https://…/people/123.jpg directly; usable as `<img src>` without transformation | |
| Spaces key only | Store people/123.jpg; requires env var for URL construction | |
| Dual-path (best practices) | Spaces if configured (full URL), local fallback (data/uploads/people/) | ✓ |

**User's choice:** Treat photo upload like the PDF ingestion flow — Spaces if configured, local fallback otherwise. Use best practices for storage.
**Notes:** User is not ready for external DO Spaces integration in this phase. The dual-path approach (mirroring Phase 7 PDF behavior) makes the feature work in local dev without Spaces configured. Also clarified that the `photo_url` text input already handles the URL path — the new work is file upload. Since URL input already exists, Phase 12's photo scope is the file upload path + replacing the text-only input with a combined widget.

---

## Photo upload UI

| Option | Description | Selected |
|--------|-------------|----------|
| Add file input above URL field | Two separate inputs; file upload + existing text field | |
| Replace with combined widget | Remove standalone text input; tabbed/toggled Upload file / Enter URL | ✓ |
| You decide | Claude picks based on minimal disruption | |

**User's choice:** Replace with a combined widget — cleaner UX, removes the standalone text input.
**Notes:** The existing `photo_url` text input in the Bio & Photo section is replaced entirely. The new widget shows a preview of the current photo (if set) above a tab/toggle for "Upload file" vs "Enter URL".

---

## Merge UI flow

| Option | Description | Selected |
|--------|-------------|----------|
| From the edit page | "Merge into another person" button on /admin/people/[id]; inline target picker + confirmation | ✓ |
| From the directory listing | Checkboxes + "Merge" button on /admin/people | |
| Dedicated /admin/people/merge page | Separate route with two dropdowns | |

**User's choice:** From the edit page (recommended).
**Notes:** After selecting a target, an inline confirmation section appears on the same page showing transfer counts (utterances, aliases, appearances). After merge completes, redirect to the target person's edit page.

### Merge confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Inline on same edit page | Count preview + Confirm button without navigation | ✓ |
| Separate confirmation page | Navigate to /admin/people/[id]/merge-confirm | |
| You decide | Claude picks confirmation UX | |

**User's choice:** Inline on the same edit page.

### Post-merge redirect

| Option | Description | Selected |
|--------|-------------|----------|
| Target person's edit page | Redirect to /admin/people/[target_id] | ✓ |
| People directory | Return to /admin/people listing | |
| You decide | Claude handles post-merge destination | |

**User's choice:** Redirect to the target person's edit page.

---

## Delete entry point

| Option | Description | Selected |
|--------|-------------|----------|
| Edit page only | Delete button at bottom of /admin/people/[id]; disabled with tooltip if not orphaned | ✓ |
| Both edit page and directory | Delete on edit page + delete icon in directory row for orphaned records | |
| You decide | Claude picks based on minimal surface area | |

**User's choice:** Edit page only (recommended).
**Notes:** After successful delete, redirect to /admin/people.

---

## Claude's Discretion

- Target-picker style for merge (searchable select vs. inline list)
- Disabled delete button tooltip wording
- Whether merge section is always visible or revealed by an expand button
- Photo preview styling in the combined widget
- Whether merge count preview is fetched eagerly on target selection or triggered manually

## Deferred Ideas

- DO Spaces ACL setup (enable public access for `people/` prefix) — deployment concern, not a code blocker
- Image crop UI — explicitly out of scope per REQUIREMENTS.md
- Bulk merge / bulk delete — single-record operations sufficient for v1.2
