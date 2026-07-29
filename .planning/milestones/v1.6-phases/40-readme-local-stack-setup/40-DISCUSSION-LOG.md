# Phase 40: README - How to Start the Local Stack - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md; this log preserves the alternatives considered.

**Date:** 2026-07-13
**Phase:** 40-readme-local-stack-setup
**Areas discussed:** Supported platforms, Primary startup path, Clean-checkout depth, Environment files

---

## Supported Platforms

| Question | Options considered | Selected |
|----------|--------------------|----------|
| Platform promise | Windows-first with notes; Windows only; full cross-platform | Windows-first with notes |
| Windows PostgreSQL installation | Portable canonical; system canonical; both equally | Both equally |
| macOS/Linux detail | Runnable app commands; conceptual notes; package-manager setup | Runnable app commands |
| Verification labels | Windows verified/POSIX equivalent; no labels; verify all | Windows verified/POSIX equivalent |

**User's choice:** Windows-first with full portable and system-PostgreSQL paths, plus runnable POSIX project commands.
**Notes:** POSIX PostgreSQL installation and service management remain platform-owned.

---

## Primary Startup Path

| Question | Options considered | Selected |
|----------|--------------------|----------|
| First path | One-command quick start; manual startup; equal paths | One-command quick start |
| Script responsibility | Start-time only; full bootstrap; services only | Start-time only |
| System-PostgreSQL servers | Two terminals; background jobs; adapt script | Two terminals |
| Running-stack proof | Verify all layers; frontend only; process output | Verify all layers |

**User's choice:** Lead with the existing PowerShell script after one-time setup; retain visible manual commands.
**Notes:** Verify API health, public UI, admin login, and ports.

---

## Clean-Checkout Depth

| Question | Options considered | Selected |
|----------|--------------------|----------|
| Guaranteed state | Empty usable stack; sample content; services only | Empty usable stack |
| Dependency setup | Complete bootstrap; installs only; prerequisites only | Complete bootstrap |
| Portable DB initialization | Full bootstrap; assume files; system DB first | Full bootstrap |
| Optional workflows | Test DB plus content pointers; test DB only; neither | Test DB plus content pointers |

**User's choice:** A literal clean checkout reaches a migrated, empty, usable stack.
**Notes:** Test DB provisioning and content import are optional follow-ons.

---

## Environment Files

| Question | Options considered | Selected |
|----------|--------------------|----------|
| Configuration layout | Root plus app env files; one root file; shell env | Root plus app env files |
| Secret values | Generation commands; placeholders; fixed credentials | Generation commands |
| Required/optional variables | Feature groups; exhaustive table; example only | Feature groups |
| Template alignment | Align two templates; README only; combined template | Align two templates |

**User's choice:** Separate runtime-specific env files with matching shared values and safe secret-generation commands.
**Notes:** Add `app/.env.example` and keep root `.env.example` backend-focused.

## the agent's Discretion

- README ordering, copy, and troubleshooting wording.
- Exact safe PowerShell and POSIX secret-generation commands.
- Verified current CLI command for the optional first-content pointer.

## Deferred Ideas

None.
