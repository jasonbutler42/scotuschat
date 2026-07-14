---
phase: 40-readme-local-stack-setup
verified: 2026-07-14T15:02:48Z
status: passed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 40: README - How to Start the Local Stack Verification Report

**Phase Goal:** No README documents how to start the full local stack (SvelteKit dev server, FastAPI backend, Postgres). Add one so setup steps don't have to be rediscovered each session.
**Verified:** 2026-07-14T15:02:48Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | A README documents step-by-step startup of PostgreSQL, FastAPI, and SvelteKit end to end. | VERIFIED | `README.md` covers prerequisites, dependency installation, both Windows PostgreSQL arrangements, Alembic, Uvicorn, Vite, recurring startup, and success checks. Every named entry point was traced to the current repository. |
| 2 | Required local environment configuration is documented without exposing secrets. | VERIFIED | Root and app examples contain placeholders only, keep SvelteKit values private, identify the exact-match `ADMIN_TOKEN`, generate independent secrets, and separate optional test, LLM, object-storage, and deployment settings. Static contract check passed. |
| 3 | A contributor can follow the guide from a clean checkout to a running stack without relying on memory or git history. | VERIFIED | The guide includes runtime checks, venv and npm bootstrap, env creation, role/database creation, migration, startup, objective acceptance checks, and symptom-driven troubleshooting. The disposable Windows walkthrough passed end to end. |
| 4 | Windows is first-class, with portable and service-managed PostgreSQL both runnable and accurately qualified. | VERIFIED | Portable setup is explicitly verified. Service-managed setup has equivalent commands and is explicitly labeled unverified because no service was discoverable during validation. No unexercised branch is called verified. |
| 5 | The recurring portable startup path leads with `scripts/dev-start.ps1` and states its true boundary. | VERIFIED | README prerequisites and lifecycle match the script: it starts portable PostgreSQL, runs Alembic, and launches Uvicorn/Vite; it does not install, initialize, create env files, or import data. |
| 6 | macOS/Linux users receive runnable project commands with externally managed PostgreSQL. | VERIFIED | README includes venv, locked dependencies, separate env files, secret generation, role/database creation, migration, and two-terminal startup without distribution-specific package-manager recipes, and labels the path equivalent guidance. |
| 7 | Verification proves PostgreSQL, API health, public UI, admin login/session, and ports. | VERIFIED | `40-WINDOWS-VALIDATION.md` records authenticated PostgreSQL, Alembic head, HTTP 200 `{"status":"ok"}`, `/cases`, real browser login to `/admin`, and a full reload that preserved authenticated navigation and logout. Cleanup closed all walkthrough ports and removed temporary credentials/resources. |
| 8 | An empty migrated stack is success; test DB, content import, and integrations remain optional. | VERIFIED | README states the empty Alembic-head database is sufficient, and separately points to guarded `provision_test_db.py` and `python -m pipeline import-justices`. These commands and guards exist in current source. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `README.md` | Complete cross-platform local-stack guide | VERIFIED | Substantive clean-checkout, recurring-start, verification, optional next-step, troubleshooting, and preserved attribution sections. |
| `.env.example` | Backend/PostgreSQL environment contract | VERIFIED | Required backend keys, empty optional groups, and placeholder-only shared token contract match `api/core/config.py`. |
| `app/.env.example` | SvelteKit private environment contract | VERIFIED | Exactly the five runtime keys consumed by SvelteKit server code; no `PUBLIC_` variables. |
| `.gitignore` | Portable PostgreSQL ignore coverage | VERIFIED | `data/pgsql/` and `data/pgdata/` are ignored; `app/.env.example` remains trackable. |
| `40-WINDOWS-VALIDATION.md` | Dated disposable Windows runtime evidence | VERIFIED | Identifies versions, commit, branch, resources, redacted commands, every required gate, cleanup, qualification, and overall PASS. |

All three `verify.artifacts` queries passed: Plan 01 (3/3), Plan 02 (1/1), and Plan 03 (2/2).

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `README.md` | `scripts/dev-start.ps1` | Portable recurring-start command | WIRED | Paths, lifecycle, ports, Alembic, Uvicorn, Vite, and Ctrl+C behavior agree with the script. |
| `README.md` | `.env.example`, `app/.env.example` | Copy/configure instructions | WIRED | Runtime ownership, shared token, required values, and optional groups agree with examples and consumers. |
| `app/.env.example` | `.env.example` | Matching `ADMIN_TOKEN` | WIRED | Both use the same placeholder and README requires one generated value in both files. |
| `README.md` | `api/main.py` | `/health` acceptance check | WIRED | Actual route returns `{"status": "ok"}`; README expects the same payload on port 8000. |
| `README.md` | SvelteKit login/session code | Browser admin acceptance check | WIRED | Login reads private credentials, signs the session, redirects to `/admin`, and the hook validates the cookie. Real login plus reload passed. |
| `README.md` | `scripts/provision_test_db.py` | Optional test database command | WIRED | Command exists and the script refuses missing, maintenance, or dev-database targets before migrating. |
| `README.md` | `pipeline/__main__.py` | Optional `import-justices` command | WIRED | Subcommand is registered and dispatches to the current import implementation. |

### Data-Flow Trace (Level 4)

Not applicable. Phase 40 artifacts are documentation, examples, and ignore rules; no artifact renders dynamic application data. Runtime claims were instead traced to source and the disposable end-to-end walkthrough.

### Behavioral Spot-Checks

| Behavior | Command/Evidence | Result | Status |
|---|---|---|---|
| Phase contract and README command checks | PowerShell static contract covering env keys, secrets, commands, qualification, attribution, evidence fields, ignores, and `git diff --check` | `PHASE40_STATIC_CONTRACT_PASS` | PASS |
| Health route source checks | `.venv\\Scripts\\python.exe -m pytest -q tests/test_admin_router.py::test_admin_router_has_health_route tests/test_admin_router.py::test_admin_router_health_returns_ok` | 2 passed | PASS |
| Frontend static analysis | `npm run check` with normal Windows process access | 0 errors, 16 pre-existing warnings | PASS |
| Configured regression suite | Full suite rerun by the phase orchestrator under normal Windows temp access | 444 passed, 5 xfailed | PASS |
| Admin session flow | In-app Browser login followed by full reload | Redirected to `/admin`; authenticated navigation and Log out remained present | PASS |

The first sandboxed frontend check could not start esbuild (`spawn EPERM`). The required retry outside the restricted process sandbox completed successfully; this was an execution-environment limitation, not an application failure.

### Probe Execution

No Phase 40 plan declares a probe script, and this documentation-only phase has no conventional phase probe. Not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| DOCS-01 | 40-01, 40-02, 40-03 | README documents the full SvelteKit, FastAPI, and PostgreSQL local stack end to end. | SATISFIED | All 8 merged roadmap/plan truths verified; artifacts, links, static checks, regression suite, and disposable runtime walkthrough passed. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| None | - | No placeholder secrets, public SvelteKit env keys, unsafe trust-auth guidance, handwritten DDL, package-manager-specific POSIX PostgreSQL recipe, or overstated verification claim found. | - | None |

The phase code review was rerun after its fixes and is clean with zero findings. Frontend warnings reported by `svelte-check` are pre-existing application concerns outside Phase 40's documentation/env scope and do not invalidate DOCS-01.

### Human Verification Required

None. Plan 40-03's deferred human check was completed during execution: a real in-app browser login reached `/admin`, and a full reload preserved the authenticated session. The evidence is specific, consistent with the login/session implementation, and recorded in `40-WINDOWS-VALIDATION.md`.

### Gaps Summary

No gaps. All merged roadmap and plan must-haves are verified, no behavior-dependent truth remains unexercised, and no additional human decision is required.

---

_Verified: 2026-07-14T15:02:48Z_
_Verifier: the agent (`gsd-verifier` generic-agent workaround)_
