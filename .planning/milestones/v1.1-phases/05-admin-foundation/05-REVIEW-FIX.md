---
phase: 05-admin-foundation
fixed_at: 2026-06-16T00:00:00Z
review_path: .planning/phases/05-admin-foundation/05-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-06-16
**Source review:** .planning/phases/05-admin-foundation/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Token comparison is not constant-time — timing oracle on the admin token

**Files modified:** `api/routers/admin.py`
**Commit:** a4df0b4
**Applied fix:** Added `import hmac` at the top of the file and replaced `if x_admin_token != settings.admin_token` with `if not hmac.compare_digest(x_admin_token, settings.admin_token)`. This eliminates the short-circuit timing oracle. Note: WR-02 was fixed in the same commit since both touch the same file.

---

### WR-01: `updated_at` has no update mechanic — will silently hold the creation timestamp forever

**Files modified:** `alembic/versions/0003_add_admin_jobs.py`, `api/models/models.py`
**Commit:** f0bcf85
**Applied fix:**
- Migration `upgrade()`: Added `set_admin_jobs_updated_at()` PL/pgSQL function and `trg_admin_jobs_updated_at` BEFORE UPDATE trigger after `op.create_table`.
- Migration `downgrade()`: Added `DROP TRIGGER IF EXISTS trg_admin_jobs_updated_at ON admin_jobs` and `DROP FUNCTION IF EXISTS set_admin_jobs_updated_at()` before `op.drop_table("admin_jobs")`.
- ORM `AdminJob.updated_at`: Added `onupdate=func.now()` as a belt-and-suspenders measure for ORM-driven updates.

---

### WR-02: Two unused imports in `admin.py` — dead code that creates a misleading contract

**Files modified:** `api/routers/admin.py`
**Commit:** a4df0b4
**Applied fix:** Removed both `from sqlalchemy.ext.asyncio import AsyncSession` and `from api.core.database import get_db`. Fixed in the same commit as CR-01 since both findings are in the same file.

---

### WR-03: `pytest.ini` missing `pythonpath = .` — tests fail in clean CI environments

**Files modified:** `pytest.ini`
**Commit:** 6328366
**Applied fix:** Added `pythonpath = .` to `pytest.ini`. This ensures `api.*` modules are importable without manual `sys.path` manipulation or `PYTHONPATH` environment variable in any environment where pytest is run from the project root.

---

_Fixed: 2026-06-16_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
