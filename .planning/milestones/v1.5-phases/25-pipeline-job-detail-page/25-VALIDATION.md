# Phase 25: Pipeline Job Detail Page - Validation

**Status:** Intentionally skipped.

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` for this project. Per `25-RESEARCH.md`'s "Validation Architecture" section: "`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json`, so the required GSD Validation Architecture section is skipped."

This file exists only to record that the skip was intentional (project-wide config choice, not an oversight for this phase specifically) — see `.planning/PROJECT.md` and `.planning/config.json` for the current setting.

Recommended verification despite Nyquist being disabled (carried from `25-RESEARCH.md`, not executed as formal Nyquist validation):

| Area | Command / Check | Notes |
|------|-----------------|-------|
| Svelte typecheck | `cd app; npm run check` | Validates Svelte 5 runes and component props. |
| Backend targeted tests | `.\.venv\Scripts\python.exe -m pytest api/tests/test_admin_jobs_stats.py api/tests/test_admin_people_schemas_service.py api/tests/test_admin_jobs_service.py -q` | Extend these or add adjacent tests for new schemas/service helpers. |
| Full backend suite | `.\.venv\Scripts\python.exe -m pytest` | Configured in `.planning/config.json`; may skip DB tests without `DATABASE_URL`. |
| Manual UI smoke | Open `/admin/pipeline/[id]` for not-ready, paused, failed, and already-created runs | Required because no frontend e2e suite was found in bounded inputs. |
