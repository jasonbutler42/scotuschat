---
created: 2026-08-19T00:00:00.000Z
title: Admin Help page with a diagram explaining statuses, tiers, and publish gates
area: ui
severity: enhancement
scheduled: after Phase 49 (v1.8)
files:
  - app/src/routes/admin/ (new help route — no admin docs surface exists today)
---

## Request

Operator request, made during the Phase 48-08 checkpoint (2026-08-19): an Admin
"Help" surface containing a diagram that explains the different argument
statuses and how each one affects publishing. Approved for v1.8.

## Why it earns its place

By the end of Phase 48 the admin-side conceptual load is genuinely large:

- **4 lifecycle statuses** — `draft`, `candidate`, `published`, `unpublished`
  (`candidate` replaced the retired `pipeline` in migration 0027)
- **4 trust tiers** — `verified`, `trusted`, `provisional`, `uncertain`, derived
  by `api/domain/trust.py::derive_tier` from (source, method, review_state) and
  rolled up to an argument as the floor of its constituents
- **2 publish gates** — a non-overridable `resolved_at` gate (D-14) and an
  overridable trust gate (D-16, override is per-publish and not sticky)

Nothing currently explains how these interact. The rules live in
`.planning/notes/provenance-and-trust-model.md` and in phase CONTEXT files,
which are planning artifacts, not operator documentation.

## Deliberately scheduled AFTER Phase 49 — do not start earlier

**Phase 49 (Review Model) adds a four-state `review_state`** to operator-editable
rows. `review_state` is already one of `derive_tier`'s three inputs, so it is
part of the same picture. A diagram drawn before Phase 49 documents an
incomplete model and needs a revision pass immediately after. Drawn after 49, it
covers status × tier × review state × both gates in one coherent artifact.

Phase 51 was considered and rejected as the home: it is scoped to *public-facing*
noun alignment (`/cases` → arguments) plus the shared design system, whereas this
is admin-side operator documentation.

**Suggested placement:** its own small phase after 49, or folded into Phase 50.
Decide when 49 closes.

## Related

- [[2026-08-19-unpublish-does-not-hide-from-public-site]] — the unpublish
  semantics the diagram will need to describe correctly, once fixed
- Plan 48-10 adds the per-row tier indicator and list-page override, which the
  diagram should reflect
