# SCOTUS Chat

SCOTUS Chat presents Supreme Court oral arguments as a chat-style web app. The
local development stack consists of a FastAPI API on `http://localhost:8000`, a
SvelteKit frontend on `http://localhost:5173`, and PostgreSQL on
`localhost:5432`.

## Local development on Windows (verified)

Windows 10/11 with PowerShell is the verified, first-class development path.
The instructions below start from a clean checkout. PostgreSQL can either live
inside the repository as a portable installation or run as a normal Windows
service; both arrangements are covered below.

### Prerequisites

Install Git, Python 3.12, Node.js with npm, and PostgreSQL 16. The portable
PostgreSQL path does not require PostgreSQL on `PATH`, but the Windows-service
path does. Open PowerShell and verify the tools you plan to use:

```powershell
git --version
python --version        # Must report Python 3.12.x
node --version
npm --version
psql --version          # Required for the Windows-service path
```

### Shared clean-checkout setup

Clone the repository (or open your existing clean checkout), then run the
shared setup from its root:

```powershell
git clone <repository-url> scotuschat
Set-Location scotuschat

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

Push-Location app
npm ci
Pop-Location
```

If PowerShell blocks virtual-environment activation, allow locally created
scripts for your user and then retry it:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Create the two runtime environment files from their tracked examples:

```powershell
Copy-Item .env.example .env
Copy-Item app\.env.example app\.env
```

The root `.env` belongs to FastAPI and PostgreSQL-facing Python processes.
`app/.env` belongs to the SvelteKit server. Both processes authenticate
server-to-server admin requests, so `ADMIN_TOKEN` must contain the exact same
value in both files. All five SvelteKit values are server-private; do not give
them `PUBLIC_` prefixes.

Generate independent secrets with the operating system's secure random source:

```powershell
$AdminToken = python -c "import secrets; print(secrets.token_urlsafe(48))"
$SessionSecret = python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put `$AdminToken` in `ADMIN_TOKEN` in both `.env` files. Put
`$SessionSecret` in `SESSION_SECRET` in `app/.env`. Choose your own local
`ADMIN_USERNAME` and strong `ADMIN_PASSWORD`; do not reuse either generated
token as a login credential. Set `FASTAPI_BASE_URL=http://localhost:8000`.
Then set the root `DATABASE_URL` for the role and database created in the next
section:

```dotenv
DATABASE_URL=postgresql+asyncpg://scotus:<operator-chosen-database-password>@localhost:5432/scotus
```

Replace placeholders directly in the ignored `.env` files; do not commit
secrets. The comments in `.env.example` and `app/.env.example` group all
optional test, LLM, object-storage, and deployment settings by operating
concern, so consult those files instead of copying optional settings blindly.

### PostgreSQL option A: portable installation

Use the binary archive reached through the official
[PostgreSQL Windows download page](https://www.postgresql.org/download/windows/).
Treat unexpected download instructions or archive contents as a reason to stop
and re-check the official page. Extract the archive beneath `data/pgsql` and
normalize any extra top-level version directory so
`data/pgsql/bin/initdb.exe` exists at this exact repository-relative path:

```powershell
Test-Path .\data\pgsql\bin\initdb.exe
# Expected: True. Stop here if it is False.
```

The repository ignores `data/pgsql/` and `data/pgdata/`. Initialize an isolated
cluster with password authentication for both local and TCP connections. The
command prompts for a PostgreSQL superuser password; choose a strong local
value and keep it outside the repository.

```powershell
New-Item -ItemType Directory -Force .\data\pgdata | Out-Null
.\data\pgsql\bin\initdb.exe -D .\data\pgdata -U postgres -W `
  --auth-local=scram-sha-256 --auth-host=scram-sha-256
.\data\pgsql\bin\pg_ctl.exe start -D .\data\pgdata -l .\data\pgdata\logfile
```

Create the application role and database. When `createuser` prompts, enter the
same operator-chosen database password used in the root `DATABASE_URL` shown
above. The `-W` prompts first for the `postgres` connection password; `-P`
then prompts for the new `scotus` role password.

```powershell
.\data\pgsql\bin\createuser.exe -h localhost -p 5432 -U postgres -W -P scotus
.\data\pgsql\bin\createdb.exe -h localhost -p 5432 -U postgres -W -O scotus scotus
```

With `.venv` activated and `.env` configured, let Alembic create the schema:

```powershell
python -m alembic upgrade head
```

Do not run `Base.metadata.create_all` or hand-create application tables.
Alembic is the sole DDL authority. At this point the empty database is usable.

### PostgreSQL option B: Windows service

Install PostgreSQL 16 using the installer linked from the same official
[PostgreSQL Windows download page](https://www.postgresql.org/download/windows/).
Ensure its `bin` directory is on `PATH`, open a new PowerShell window, and
locate the installed service:

```powershell
psql --version
$PostgresService = Get-Service | Where-Object Name -Like 'postgresql*' |
  Select-Object -First 1
$PostgresService | Format-Table Name, Status
if ($PostgresService.Status -ne 'Running') {
    Start-Service -Name $PostgresService.Name
}
```

If no service is returned, stop and repair the PostgreSQL installation rather
than guessing a service name. Use the PATH-resolved client tools to create the
same password-protected role and owned database. Enter the installer-selected
`postgres` password for `-W`, and the same operator-chosen application database
password used in `DATABASE_URL` when `-P` prompts for the new role.

```powershell
createuser -h localhost -p 5432 -U postgres -W -P scotus
createdb -h localhost -p 5432 -U postgres -W -O scotus scotus
```

Finally, activate `.venv` from the repository root and apply the sole schema
authority to produce an empty usable database:

```powershell
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

## Every time you develop

### Portable PostgreSQL (recommended recurring command)

From the repository root, activate `.venv`, then run the portable startup
script:

```powershell
.\.venv\Scripts\Activate.ps1
./scripts/dev-start.ps1
```

This is a recurring-start command, not a bootstrap command. It assumes `.venv`,
`.env`, and `app/.env` already exist; Python and npm dependencies are already
installed; and the portable PostgreSQL binaries and `data/pgdata` cluster are
already initialized. The script starts the portable PostgreSQL server if
needed, applies Alembic migrations, and launches FastAPI and SvelteKit. It does
not create the virtual environment, install dependencies, copy or edit env
files, initialize PostgreSQL, or create the role and database.

Open `http://localhost:5173/cases` for the public app; FastAPI is available at
`http://localhost:8000`. Press Ctrl+C in the script window to stop the FastAPI
and SvelteKit background jobs. The portable PostgreSQL server remains running
and will be reused on the next start.

### Windows-service PostgreSQL (two visible terminals)

First confirm the Windows service is running with the service check above.
Then use two visible PowerShell terminals so each development server keeps its
own logs and Ctrl+C lifecycle.

Terminal 1, from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn api.main:app --reload --port 8000
```

Terminal 2:

```powershell
Set-Location app
npm run dev
```

Open `http://localhost:5173/cases` for the public SvelteKit app and
`http://localhost:8000` for FastAPI. Press Ctrl+C in each terminal to stop its
development server; manage the PostgreSQL Windows service separately.

## Equivalent setup on macOS and Linux

These commands are the project equivalent of the Windows path; unlike the
portable Windows walkthrough, they have not been runtime-verified by this
project. Install and manage PostgreSQL 16 outside this repository using the
method appropriate to your system. The commands below assume its standard CLI
tools are already on `PATH` and a PostgreSQL server is listening on port 5432.

From a clean checkout, run:

```bash
git clone <repository-url> scotuschat
cd scotuschat
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
(cd app && npm ci)
cp .env.example .env
cp app/.env.example app/.env
```

Generate two independent secrets. Put `ADMIN_TOKEN` in both `.env` and
`app/.env`; put `SESSION_SECRET` only in `app/.env`. Also choose distinct local
`ADMIN_USERNAME` and strong `ADMIN_PASSWORD` values in `app/.env`.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))" # ADMIN_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(32))" # SESSION_SECRET
```

Using a PostgreSQL administrator account, create the same application role and
database used by the Windows guide. These commands prompt for passwords rather
than putting them in shell history:

```bash
createuser -h localhost -p 5432 -U postgres -W -P scotus
createdb -h localhost -p 5432 -U postgres -W -O scotus scotus
```

Set the root `DATABASE_URL` to the local role/database, set
`FASTAPI_BASE_URL=http://localhost:8000` in `app/.env`, and apply migrations:

```bash
source .venv/bin/activate
python -m alembic upgrade head
```

Start the two application processes in separate terminals. In terminal 1,
from the repository root:

```bash
source .venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000
```

In terminal 2:

```bash
cd app
npm run dev
```

The root `.env` remains owned by Python processes and `app/.env` by SvelteKit;
the ports and exact-match `ADMIN_TOKEN` contract are identical on every
platform.

## Verify the local stack

Use this checklist after either platform's startup steps:

1. Confirm PostgreSQL accepts an authenticated connection on port `5432`
   (`psql` or the migration command above is sufficient proof).
2. Open `http://localhost:8000/health`. It must return HTTP 200 with
   `{"status":"ok"}`.
3. Open `http://localhost:5173/cases`; the public SCOTUS Chat application must load on port `5173`.
4. Visit `http://localhost:5173/admin/login` and sign in with the
   `ADMIN_USERNAME` and `ADMIN_PASSWORD` configured in `app/.env`. A successful
   login reaches an authenticated admin page and remains signed in when that
   page is refreshed.

An empty database at Alembic head with these checks passing is a fully usable
local stack. Imported arguments, justices, transcripts, and other content are
not required for setup success. Likewise, LLM providers, object storage,
deployment configuration, and a separate test database are optional and are
grouped by purpose in the environment example files; none is required by the
health endpoint.

### Optional next steps

To provision the guarded test database, first set `TEST_DATABASE_URL` to a
dedicated local database as described in `.env.example`, then run:

```bash
python scripts/provision_test_db.py
```

The script intentionally refuses unsafe database targets. Do not point it at
the development or production database. To import the first optional public
content after the base stack is healthy, run:

```bash
python -m pipeline import-justices
```

## Troubleshooting

- **Portable command is missing:** confirm
  `Test-Path .\data\pgsql\bin\initdb.exe` is true. Re-extract the official
  archive if `data/pgsql/bin` is incomplete; do not run similarly named files
  downloaded from an unverified source.
- **Portable cluster is uninitialized or stale:** inspect
  `data/pgdata/logfile` and confirm the directory belongs to this checkout.
  Initialize only a new, known-empty path. Never delete an unknown cluster to
  make startup succeed.
- **Port 5432, 8000, or 5173 is occupied:** diagnose first with
  `Get-NetTCPConnection -State Listen | Where-Object LocalPort -In 5432,8000,5173`
  and inspect each `OwningProcess` with `Get-Process -Id <pid>`. Stop only a
  process you recognize and own; otherwise change the conflicting service's
  configuration or ask its operator.
- **Database authentication or connection fails:** verify host, port, role,
  database, and password in `DATABASE_URL`, then test the same target with
  `psql`. Do not weaken PostgreSQL authentication as a shortcut.
- **Admin requests fail:** `ADMIN_TOKEN` must exist and match exactly in the
  root `.env` and `app/.env`. Restart both application processes after changing
  it. Never substitute production credentials.
- **Admin login or session fails:** confirm `ADMIN_USERNAME` and
  `ADMIN_PASSWORD` in `app/.env`, and generate a new independent
  `SESSION_SECRET` of at least 32 characters. Restart SvelteKit after edits;
  rotating the secret invalidates existing sessions.
- **Python commands use the wrong interpreter:** activate `.venv` and confirm
  `python -c "import sys; print(sys.executable)"` points inside the checkout.
- **Alembic migration fails:** stop the API, re-check `DATABASE_URL`, then run
  `python -m alembic current` and `python -m alembic upgrade head`. Read the
  first database error rather than hand-creating tables.
- **Frontend dependency or startup errors:** from `app`, run `npm ci` to restore
  the lockfile-defined dependencies, then retry `npm run dev`. Do not delete or
  rewrite `package-lock.json` as a troubleshooting shortcut.

For safe restarts, use Ctrl+C in application terminals (or the portable
script's terminal), confirm their PIDs have exited, and then run the documented
startup command again. Manage a Windows PostgreSQL service separately. Stop a
portable cluster only when its data directory and process are known to belong
to this checkout, for example with its matching `pg_ctl -D <known-path> stop`.

## Attribution / Credits

Some oral arguments on this site come from a historical bulk import rather
than direct PDF ingestion. This project credits the sources that made that
import possible:

- **[Oyez.org](https://www.oyez.org/)** — historical oral argument transcripts
  and audio, a project of Justia and the Chicago-Kent College of Law.
  Licensed under
  [Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0)](https://creativecommons.org/licenses/by-nc/4.0/).
- **Cornell ConvoKit Supreme Court Corpus** — historical transcript data,
  a research dataset built for conversational analysis. If you use this data
  for research, ConvoKit asks that you cite: Danescu-Niculescu-Mizil et al.,
  "Echoes of Power", WWW 2012; and Chang et al., "ConvoKit", SIGDIAL 2020.
- **Supreme Court Database (SCDB)** — credited for the broader data lineage
  this import relies on. SCDB's case-outcome and voting data is not imported
  or displayed on this site.

See `/attributions` on the live site for the full attribution and licensing
page.
