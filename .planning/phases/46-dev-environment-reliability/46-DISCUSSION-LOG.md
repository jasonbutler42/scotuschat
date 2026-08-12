# Phase 46: Dev Environment Reliability - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-12
**Phase:** 46-dev-environment-reliability
**Areas discussed:** Run location, Postgres approach, Phase scope

---

## Run location

| Option | Description | Selected |
|--------|-------------|----------|
| Move everything to WSL-native | Run Postgres, Python (fresh WSL venv), and Node natively inside WSL — WSL-native Node (nvm) already available; plain ps/kill instead of crossing the Windows/WSL boundary | ✓ |
| Keep Windows-native, make it more robust | Keep current Windows venv + dev-start.ps1, harden start/stop and health checks | |
| Hybrid — Windows for browser-facing, WSL for tooling | Keep FastAPI/SvelteKit on Windows, move test/CI-style invocations to run consistently regardless of shell | |

**User's choice:** Move everything to WSL-native.
**Notes:** Framed against today's concrete incident — a live server on port 8000 that answered requests correctly but had no discoverable owning process via `tasklist.exe`/`Get-Process`/`Get-NetTCPConnection`.

---

## Postgres approach

| Option | Description | Selected |
|--------|-------------|----------|
| Switch to the installed Postgres service | Use the already-installed (but stopped) Windows `postgresql-x64-18` service instead of the portable pg_ctl-in-repo-folder setup | ✓ |
| Keep the portable pg_ctl setup | Self-contained to the repo; just harden dev-start.ps1's health checks around it | |

**User's choice:** Switch to the installed Postgres service.
**Notes:** The portable setup existed specifically to avoid needing admin rights — that constraint no longer applies on this machine.

---

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix the data-loss bug + basic reliability | Priority: fix the pytest DB-isolation bypass so it fails closed regardless of invocation, plus a dev-start script with real health checks | ✓ |
| Full stack rework | The above, plus treating run-location/Postgres as a real migration (new venv, new install/service, updated docs) | |

**User's choice:** Fix the data-loss bug + basic reliability (recommended option).

---

## Claude's Discretion

- Exact mechanism for the pytest isolation fix (`pytest_configure` hook vs. per-directory conftest duplication vs. fail-closed guard).
- Whether the new start/stop entry point is a rewritten `dev-start.ps1`, a new WSL-native shell script, or a thin Windows wrapper around a WSL script.
- Whether to delete the old portable `data/pgsql`/`data/pgdata` directories now or leave them unused.

## Deferred Ideas

- Full stack rework (containerization, CI integration, docs restructuring) — operator chose the narrower scope instead; could become its own future phase.
- Hybrid Windows/WSL split — considered, not chosen.
- Three other pending todos were checked against this phase's scope (`todo.match-phase`) but all matched only on generic keyword overlap, not actual dev-environment relevance: `2026-08-12-speaker-popover-frontend-duplication-cleanup.md`, `2026-08-12-speakers-bench-classification-silent-fallback.md`, `2026-08-11-create-person-popover-side-and-selection.md`. Left pending, not folded.
