---
date: "2026-07-14 16:00"
promoted: false
---

Current testing state in the repo:

- Python tests are already wired through `pytest` with repo-specific fixtures and a test database path.
- `pytest` covers backend, API, and pipeline tests, and the suite includes leak guards so the real dev DB is protected from test writes.
- Frontend validation exists through `npm run check` and `npm run build`.
- There is no committed CI workflow yet, so these checks still run manually.
- There is also no dedicated automated security scanning in place yet.

Proposed automation to reduce chat-driven testing:

- Add GitHub Actions workflows for push, pull request, and manual dispatch.
- Run the full Python test suite against a disposable Postgres service.
- Run the frontend checks and build in CI.
- Add a separate security workflow with dependency scanning, Python package scanning, and static analysis.
- Add Dependabot so routine dependency updates surface without manual prompting.
- Document where to find workflow runs, logs, and reruns so the process is visible outside chat.

Decision state:

- This is not yet implemented in the repository.
- The note captures the intended direction so the next pass can turn it into files instead of re-deriving the plan from chat.
