# Phase 36: Click-to-copy extracted values design pattern - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 36-click-to-copy-extracted-values-design-pattern
**Areas discussed:** Scope boundary, Copied value rules, Copy feedback, Disabled `N/A`

---

## Scope boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Only source-derived fields | Only literal extracted PDF metadata and readouts. | |
| Include derived counts too | Include derived pipeline stats and counts too. | |
| Discuss a different boundary | Narrow the boundary first before locking a rule. | ✓ |

**User's choice:** Discuss a different boundary
**Notes:** User clarified the rule: click-to-copy is only relevant for fields the operator will populate, but if something is specified as extracted and has an operator-editable destination, it should include click-to-copy unless a phase explicitly says otherwise.

---

## Copied value rules

### Displayed text vs raw value

| Option | Description | Selected |
|--------|-------------|----------|
| Copy the displayed text | Copy exactly what the operator sees. | ✓ |
| Copy the raw stored value | Copy the underlying persisted value instead. | |
| Ask per field | Decide per field. | |

**User's choice:** Copy exactly what the operator sees.

### Extracted docket pills

| Option | Description | Selected |
|--------|-------------|----------|
| Copy the individual docket | Clicking a pill copies only that docket. | ✓ |
| Copy the full docket list | Copy the whole set of pills. | |
| Copy both | Copy individual and full list. | |

**User's choice:** Copy the individual docket only.

### Clickable target

| Option | Description | Selected |
|--------|-------------|----------|
| Make the value and icon one button | One generous button target covers both. | ✓ |
| Make only the icon clickable | The value is static text. | |
| Make the whole row clickable | Entire row triggers copy. | |

**User's choice:** The value and icon together should be one generous button target.

### Icon placement

| Option | Description | Selected |
|--------|-------------|----------|
| Trailing icon immediately after the value | Value first, icon second. | ✓ |
| Leading icon | Icon before the value. | |
| Right-aligned far edge | Icon pinned to the far edge. | |

**User's choice:** Trailing icon immediately after the value.

---

## Copy feedback

### Hover text

| Option | Description | Selected |
|--------|-------------|----------|
| Field-specific tooltip | Example: `Copy docket`. | ✓ |
| Generic tooltip | Example: `Copy value`. | |
| No tooltip text | No hover copy label. | |

**User's choice:** Field-specific tooltip, like `Copy docket`.

### Success state

| Option | Description | Selected |
|--------|-------------|----------|
| Brief `Copied` state | Tooltip changes briefly, then returns. | ✓ |
| Persistent inline confirmation | Confirmation stays visible in the layout. | |
| Toast | Show a global toast. | |

**User's choice:** Tooltip changes to `Copied` briefly, then returns.

### Repeat click behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Restart the timer | Repeat click restarts the brief success timer. | ✓ |
| Ignore extra clicks | No effect until the success state clears. | |
| Keep visible until dismiss | Confirmation stays until manual dismissal. | |

**User's choice:** Restart the brief success timer.

### Failure handling

| Option | Description | Selected |
|--------|-------------|----------|
| Local tooltip message | Example: `Couldn't copy`. | ✓ |
| Toast | Show a global error toast. | |
| No visible failure message | Fail silently. | |

**User's choice:** A local tooltip message, like `Couldn't copy`.

---

## Disabled `N/A`

### Visual treatment

| Option | Description | Selected |
|--------|-------------|----------|
| Visible disabled affordance | Keep the same slot, but disabled. | ✓ |
| Plain `N/A` text | No copy affordance. | |
| Hide entirely | Remove the value display. | |

**User's choice:** Keep the same slot with a visible disabled copy affordance.

### Disabled tooltip

| Option | Description | Selected |
|--------|-------------|----------|
| `Nothing extracted to copy` | Explain why the control is disabled. | ✓ |
| `Copy unavailable` | Generic disabled message. | |
| No tooltip | No hover copy label. | |

**User's choice:** `Nothing extracted to copy`.

### Focus behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Skip tab order | Disabled affordance is not focusable. | ✓ |
| Focusable | Allow keyboard focus for the tooltip. | |
| Conditional focus | Focusable only in some states. | |

**User's choice:** No, skip it in tab order.

### Visual style

| Option | Description | Selected |
|--------|-------------|----------|
| Muted text/icon | No hover accent. | ✓ |
| Lower opacity only | Only reduce opacity. | |
| Strikethrough | Use an explicit disabled mark. | |

**User's choice:** Muted text/icon with no hover accent.

---

## the agent's Discretion

None — the user supplied the scope boundary and all detailed interaction choices.

## Deferred Ideas

None — discussion stayed within phase scope.
