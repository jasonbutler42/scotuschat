# Phase 5: Admin Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-15
**Phase:** 05-admin-foundation
**Areas discussed:** admin_jobs schema completeness, X-Admin-Token design, SvelteKit scope, admin_jobs status values, ORM model scope, FastAPI router prefix, Phase 5 route stubs, environment variable names, current_step enum values, pdf_url vs pdf_path, test coverage

---

## admin_jobs Schema Completeness

| Option | Description | Selected |
|--------|-------------|----------|
| Full schema now | Migration 0003 lands every column Phase 7 needs | ✓ |
| Minimal now, extend in Phase 7 | Migration 0003 creates minimal table; Phase 7 adds columns via migration 0004 | |

**User's choice:** Full schema now
**Notes:** None

---

## argument_id FK Design

| Option | Description | Selected |
|--------|-------------|----------|
| Nullable FK to arguments | Referential integrity; NULL until ingest creates the argument row | ✓ |
| Nullable integer, no FK | Simpler migration; avoids cascade concerns | |

**User's choice:** Nullable FK to arguments
**Notes:** None

---

## Discrepancy Data Storage

| Option | Description | Selected |
|--------|-------------|----------|
| JSONB column on admin_jobs | Single `discrepancies` column; read as batch during fire-and-poll | ✓ |
| Separate discrepancies table | Normalised rows per item; row-level status updates | |

**User's choice:** JSONB column on admin_jobs
**Notes:** None

---

## X-Admin-Token: Stub vs Permanent

| Option | Description | Selected |
|--------|-------------|----------|
| Throwaway — Phase 6 replaces entirely | Phase 6 rips out token check and replaces with cookie auth | ✓ |
| Permanent dev bypass | X-Admin-Token survives alongside cookie auth for CLI testing | |

**User's choice:** Throwaway — Phase 6 replaces it entirely
**Notes:** None

---

## Admin Router File Organization

| Option | Description | Selected |
|--------|-------------|----------|
| Single file api/routers/admin.py | Phase 5 is a stub; Phase 7 can split if needed | ✓ |
| Sub-package api/routers/admin/ | Anticipates Phase 7–8 growth; avoids future refactor | |

**User's choice:** Single file
**Notes:** None

---

## SvelteKit Scope in Phase 5

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI-only — zero SvelteKit changes | Clean separation: Phase 5 = backend plumbing, Phase 6 = frontend + auth | ✓ |
| Minimal SvelteKit admin scaffold | Add layout stub so /admin URL exists; gives Phase 6 a head start | |

**User's choice:** Phase 5 is FastAPI-only
**Notes:** None

---

## admin_jobs Status Values

| Option | Description | Selected |
|--------|-------------|----------|
| Add 'paused' — distinct from needs_review | pending / running / paused / completed / failed | ✓ |
| Mirror pipeline_runs exactly | pending / running / completed / failed / needs_review | |

**User's choice:** Add 'paused'
**Notes:** `paused` = UI frozen waiting for operator review. `needs_review` is a pipeline_run outcome — different semantics.

---

## ORM Model Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — Phase 5 adds the ORM model | Migration + ORM class land together | ✓ |
| No — Phase 7 adds the ORM model | Phase 5 delivers migration only | |

**User's choice:** Yes — Phase 5 adds the ORM model
**Notes:** None

---

## FastAPI Router Prefix

| Option | Description | Selected |
|--------|-------------|----------|
| /api/admin | Unambiguous; no collision with SvelteKit /admin/* page routes | ✓ |
| /admin | Shorter; matches SvelteKit route namespace but creates naming collision risk | |

**User's choice:** /api/admin
**Notes:** None

---

## Phase 5 Route Stubs

| Option | Description | Selected |
|--------|-------------|----------|
| One health/ping route | GET /api/admin/health — smoke-test target for 401 verification | ✓ (Claude's discretion) |
| Zero routes | Just the dependency; can't smoke-test auth without Phase 7 routes | |

**User's choice:** "You choose"
**Notes:** Claude chose one health route so the 401 auth dependency is verifiable before Phase 7.

---

## Environment Variable Names

| Option | Description | Selected |
|--------|-------------|----------|
| ADMIN_TOKEN | Matches X-Admin-Token header name; clear connection | ✓ |
| ADMIN_SECRET | More explicit about secret nature | |

**User's choice:** ADMIN_TOKEN
**Notes:** None

---

## current_step Enum Values

| Option | Description | Selected |
|--------|-------------|----------|
| ingest / parse / resolve (NULL = not started) | Mirrors pipeline step names; NULL is unambiguous | ✓ |
| not_started / ingest / parse / resolve | Explicit string for initial state | |

**User's choice:** ingest / parse / resolve
**Notes:** `current_step = NULL` combined with `status = 'pending'` is unambiguous; no sentinel needed.

---

## pdf_url vs pdf_path Column

| Option | Description | Selected |
|--------|-------------|----------|
| Both: pdf_url (nullable) + spaces_key (nullable) | Full provenance — distinguishes input source from storage location | ✓ |
| Single pdf_source column | Simpler schema; loses input vs. storage distinction | |

**User's choice:** Both columns
**Notes:** `pdf_url` = what operator entered (NULL for file uploads). `spaces_key` = DO Spaces object key after ingest (NULL until ingest completes).

---

## Test Coverage

**User's question:** When should we start building automated tests?

**Answer:** Phase 5 = smoke test only. Automated tests begin in Phase 6 (permanent HMAC session cookie auth is the right surface to test — X-Admin-Token is throwaway). Phase 7 job state machine transitions warrant unit tests.

---

## Claude's Discretion

- **Route stubs:** One health route (`GET /api/admin/health`) chosen over zero routes — makes 401 smoke-testable without Phase 7 routes.

## Deferred Ideas

None — discussion stayed within phase scope.
