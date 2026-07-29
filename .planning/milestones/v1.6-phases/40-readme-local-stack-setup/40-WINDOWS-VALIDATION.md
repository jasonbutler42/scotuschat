# Phase 40 Windows Local Stack Validation

- Date: 2026-07-14 (America/Chicago)
- Windows: Windows 11
- PowerShell: 7.6.3
- Python: 3.14.4 (`.venv` used for all project Python commands)
- Node.js: v24.15.0
- npm: 11.12.1
- PostgreSQL: 18.4 portable binaries
- Commit SHA: `d955374a548afe32e6d58127273c7f4bbb219a7b`
- Selected PostgreSQL branch: Portable PostgreSQL on disposable port `55432`
- Disposable cluster: `.tmp-phase40-c794555c0439/cluster` (removed after validation; never `data/pgdata`)
- Disposable role/database: `scotus_p40_bfe5ac0a24be` / `scotus_p40_bfe5ac0a24be`

Secrets and passwords were generated independently for this session. They were
passed through process-scoped environment variables, stored only in the
walkthrough-owned runtime directory while the browser check was pending, and
removed during cleanup. Commands below use `[REDACTED]` in their place. No
tracked `.env` file was read, replaced, or modified.

## Branch status

Portable PostgreSQL: PASS - a new scratch cluster accepted an authenticated
query, migrated to Alembic head, served the API and public UI, and supported a
real browser login whose authenticated session survived a full reload.

Windows service PostgreSQL: NOT EXERCISED - discovery found no service matching
`postgresql*`, so there was no authorized service name or connection target to
exercise. The README service path remains equivalent, unverified guidance.

## Gate record

| Gate | Command/evidence | Expected result | Actual result | Status |
|---|---|---|---|---|
| Bootstrap | `initdb -D .tmp-phase40-c794555c0439/cluster ...`; `pg_ctl start ... -o "-p 55432 -h 127.0.0.1"`; create disposable role/database; start Uvicorn and Vite with process-scoped environment overrides | Scratch database and application prerequisites complete without modifying tracked env files | PostgreSQL initialized and reached ready state; the disposable role/database were created; FastAPI listened on 8000 and SvelteKit listened on 5173. Existing repository env files were untouched. | PASS |
| Authenticated query | `psql -h 127.0.0.1 -p 55432 -U scotus_p40_bfe5ac0a24be -d scotus_p40_bfe5ac0a24be -tAc "SELECT current_user || '@' || current_database();"` with `PGPASSWORD=[REDACTED]` | Authenticated query succeeds as the disposable application role | Returned `scotus_p40_bfe5ac0a24be@scotus_p40_bfe5ac0a24be`. | PASS |
| Alembic head | `DATABASE_URL=postgresql+asyncpg://scotus_p40_bfe5ac0a24be:[REDACTED]@127.0.0.1:55432/scotus_p40_bfe5ac0a24be`; `python -m alembic upgrade head`; query `alembic_version` | Migration completes and reports repository head | Migration completed without error; `alembic_version` returned `0019`. | PASS |
| `/health` | `GET http://127.0.0.1:8000/health` | HTTP 200 with `{"status":"ok"}` | Returned HTTP 200 with `{"status":"ok"}` from the walkthrough-started API. | PASS |
| Public UI | `GET http://127.0.0.1:5173/cases` | Successful response renders the public app on port 5173 | `/cases` returned HTTP 200. Discovery also showed that `/` returns 404 because the application has no root route; the README was corrected to use the verified `/cases` URL. | PASS |
| Admin login | In-app Browser at `http://127.0.0.1:5173/admin/login` using temporary local credentials, followed by a full reload of the authenticated page | Login reaches an authenticated admin page and reload preserves the session | Login redirected to `http://127.0.0.1:5173/admin` with title `Admin - SCOTUS Chat`. After a full reload the URL and title remained authenticated, and admin navigation plus the Log out control remained present. | PASS |
| Cleanup | Stop only the recorded Vite and Uvicorn processes; `pg_ctl stop -D .tmp-phase40-c794555c0439/cluster -m fast -w`; remove only `.tmp-phase40-c794555c0439` | Walkthrough-owned processes and cluster stop, credentials and scratch files are removed, and required ports close | Recorded app processes stopped, PostgreSQL reported `server stopped`, the runtime directory was removed, and ports 55432/8000/5173 had no listeners. | PASS |
| `git status --short` | Compare final status with the pre-walkthrough baseline | No new runtime artifacts outside planned documentation files | The temporary runtime directory was absent. Existing unrelated dirty/untracked items were preserved; the walkthrough added no runtime artifact outside the planned Phase 40 documentation. | PASS |

Overall result: PASS

## Qualification

This run verifies the portable PostgreSQL path only. It does not verify the
Windows-service PostgreSQL path, and the README must not describe that branch
as verified. The successful empty database at Alembic head is the intended
setup completion point; no imported content or optional integration was needed.