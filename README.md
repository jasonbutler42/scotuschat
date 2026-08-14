# SCOTUS Chat

SCOTUS Chat presents Supreme Court oral arguments as a chat-style web app. The
local development stack runs FastAPI on `http://localhost:8000` and SvelteKit
on `http://localhost:5173` as WSL-native processes, with PostgreSQL 18 running
as a Windows service reached from WSL over the WSL2 NAT gateway — never over
loopback.

## WSL2 Ubuntu + Windows PostgreSQL service (verified)

WSL2 Ubuntu running the Python and Node processes natively, against a
PostgreSQL 18 instance installed as a normal Windows service, is the verified,
first-class development path. There is exactly one supported PostgreSQL
arrangement — the Windows service below — and exactly one place the working
copy lives.

### Where your working copy lives

Clone the repository into the WSL filesystem, under your Linux user's home
directory (for example `~/scotuschat/project` — the exact convention this
project follows, recorded in
`.planning/phases/46-dev-environment-reliability/46-RELOCATION.md`). Do this
before you run any setup command below.

**Do not clone onto a Windows-mounted drive** (a path under a Windows drive
letter, reached from WSL through the DrvFs/9p bridge). That mount is served
over a network-style filesystem where file-change notifications are
unreliable, so saving a file there does not reliably trigger FastAPI's
`--reload` or SvelteKit's hot-module replacement — you can save a change and
watch nothing happen. WSL-native ext4 delivers real `inotify` events and does
not have this problem.

The companion rule: **save from an editor that is itself connected into
WSL** (for example VS Code's "WSL: Ubuntu" remote window, or any editor
running inside the WSL shell). Change notifications are produced by
processes running inside WSL; a Windows-native editor writing through the
`\\wsl.localhost\<distro>\...` share path produces none, even though the
working copy itself is on ext4. Browsing or reading files from Windows
through that share path is fine — editing through it is not.

### Prerequisites

Install these from a WSL2 Ubuntu shell, not from Windows PowerShell:

```bash
git --version
python3.12 --version    # Must report Python 3.12.x — see note below
node --version
npm --version
```

Node and npm are commonly provided via [nvm](https://github.com/nvm-sh/nvm)
inside WSL.

WSL's default `python3` on a current Ubuntu release is newer than 3.12.
CLAUDE.md pins this project to Python 3.12, so always invoke the 3.12
interpreter explicitly by name (`python3.12`), never the bare `python3`
default, when creating the virtual environment below.

PostgreSQL itself is installed on the Windows side, as a Windows service —
see the PostgreSQL section below. WSL does not need any PostgreSQL packages
installed.

### Shared clean-checkout setup

Clone the repository (or open your existing clean checkout, at the WSL-native
path described above), then run the shared setup from its root, in a WSL
bash shell:

```bash
git clone <repository-url> scotuschat
cd scotuschat

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

(cd app && npm ci)

cp .env.example .env
cp app/.env.example app/.env
```

The root `.env` belongs to FastAPI and PostgreSQL-facing Python processes.
`app/.env` belongs to the SvelteKit server. Both processes authenticate
server-to-server admin requests, so `ADMIN_TOKEN` must contain the exact same
value in both files. All five SvelteKit values are server-private; do not give
them `PUBLIC_` prefixes.

Generate independent secrets with the operating system's secure random
source:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"   # ADMIN_TOKEN
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SESSION_SECRET
python -c "import secrets; print(secrets.token_urlsafe(32))"   # database role password
```

Put the first value in `ADMIN_TOKEN` in both `.env` files. Put the second
value in `SESSION_SECRET` in `app/.env`. Choose your own local
`ADMIN_USERNAME` and strong `ADMIN_PASSWORD`; do not reuse either generated
token as a login credential. Set `FASTAPI_BASE_URL=http://localhost:8000`.
Use the URL-safe database password value when PostgreSQL prompts for the
`scotus` role password in the PostgreSQL section below, then put that same
value in the root `DATABASE_URL`. If you choose a password containing
URI-reserved characters instead, percent-encode it in `DATABASE_URL` while
entering the original value at PostgreSQL prompts.

Because PostgreSQL runs on the Windows side and this stack runs under WSL2,
the database host in `DATABASE_URL` is **not** `localhost` — it is the
Windows host's WSL2 NAT gateway address, resolved fresh with:

```bash
ip route show default | awk '{print $3}'
```

```dotenv
DATABASE_URL=postgresql+asyncpg://scotus:<url-safe-database-password>@<resolved-gateway-ip>:5432/scotus
```

That gateway address can change across Windows or WSL restarts.
`scripts/dev-start.sh` re-syncs `DATABASE_URL`/`TEST_DATABASE_URL` to the
current value automatically at startup, and
`tests/test_wsl_postgres_reachability.py` fails loudly with the corrected
value if the two ever drift apart.

Replace placeholders directly in the ignored `.env` files; do not commit
secrets. The comments in `.env.example` and `app/.env.example` group all
optional test, LLM, object-storage, and deployment settings by operating
concern, so consult those files instead of copying optional settings blindly.

### PostgreSQL (Windows service)

PostgreSQL 18 runs as a normal Windows service (`postgresql-x64-18`), not
inside this repository. Configuring it correctly means clearing three
independent access gates — missing any single one produces the exact same
connection-refused symptom from WSL, so check all three, in order, if a
connection fails. For this machine's actual recorded values (data directory,
subnet, exact commands run), see
`.planning/phases/46-dev-environment-reliability/46-WINDOWS-POSTGRES-SETUP.md`.

From an elevated Windows PowerShell prompt:

1. Locate the service and its real data directory — read the data directory
   from the service's own `PathName` rather than guessing a generic install
   path:

   ```powershell
   Get-Service -Name 'postgresql-x64-18'
   (Get-CimInstance Win32_Service -Filter "Name='postgresql-x64-18'").PathName
   ```

2. Set it to start automatically and start it:

   ```powershell
   Set-Service -Name 'postgresql-x64-18' -StartupType Automatic
   Start-Service -Name 'postgresql-x64-18'
   ```

3. **Gate 1 — `listen_addresses`.** In `postgresql.conf` (in the data
   directory found above), widen `listen_addresses` from the default
   `localhost`-only:

   ```
   listen_addresses = '*'
   ```

4. **Gate 2 — `pg_hba.conf`.** Add a `host` rule scoped to your WSL subnet's
   CIDR (found from WSL with `ip -o -4 addr show eth0`), using
   `scram-sha-256` — do not use an unscoped CIDR or a passwordless method:

   ```
   host    all    all    <your-wsl-subnet-cidr>    scram-sha-256
   ```

5. **Gate 3 — Windows Firewall.** Add an inbound rule for TCP 5432, scoped to
   the same CIDR — never an unrestricted remote address:

   ```powershell
   New-NetFirewallRule -DisplayName 'PostgreSQL 5432 from WSL' -Direction Inbound `
     -Protocol TCP -LocalPort 5432 -RemoteAddress <your-wsl-subnet-cidr> -Action Allow -Profile Any
   ```

6. Restart the service so the `postgresql.conf`/`pg_hba.conf` edits take
   effect:

   ```powershell
   Restart-Service -Name 'postgresql-x64-18'
   ```

7. Create the application role and the two databases. Passwords are prompted
   interactively (`-W`, `-P`), never passed on the command line:

   ```powershell
   createuser -h <resolved-gateway-ip> -p 5432 -U postgres -W -P scotus
   createdb   -h <resolved-gateway-ip> -p 5432 -U postgres -W -O scotus scotus
   createdb   -h <resolved-gateway-ip> -p 5432 -U postgres -W -O scotus scotus_test
   ```

With `.venv` activated and `.env` configured, let Alembic create the schema
from WSL:

```bash
python -m alembic upgrade head
```

Do not run `Base.metadata.create_all` or hand-create application tables.
Alembic is the sole DDL authority. At this point the empty database is
usable.

## Every time you develop

From the repository root, in WSL:

```bash
./scripts/dev-start.sh
```

This resolves the current Windows host IP, syncs (or refuses to silently
guess at) a drifted `.env` database host, verifies PostgreSQL is reachable at
that address, runs Alembic migrations, then launches FastAPI and SvelteKit as
their own process groups with real HTTP health checks before printing a
ready banner.

It deliberately does **not** create the virtual environment, install Python
or Node dependencies, create either `.env` file, or configure or start the
PostgreSQL Windows service — those are one-time setup steps above.

Press Ctrl+C to stop both processes cleanly. If a previous run was killed
without cleanup and a port is stuck, recover with:

```bash
./scripts/dev-start.sh --stop
```

Run `./scripts/dev-start.sh --help` for the full usage summary.

On the Windows side, `scripts/dev-start.ps1` is a thin wrapper: invoke it
from the repository's `\\wsl.localhost\<distro>\...` share path in
PowerShell and it forwards its arguments straight into the WSL script above.

If `DATABASE_URL`/`TEST_DATABASE_URL` legitimately point somewhere other than
the resolved WSL2 gateway (rare), set `SCOTUS_DEV_NO_ENV_SYNC=1` to skip the
automatic rewrite.

A short manual two-terminal fallback, if you need each server's own log and
Ctrl+C lifecycle instead of the combined script:

Terminal 1, from the repository root:

```bash
source .venv/bin/activate
python -m uvicorn api.main:app --host 0.0.0.0 --reload --port 8000
```

Terminal 2:

```bash
cd app
npm run dev
```

Binding uvicorn to all interfaces (`--host 0.0.0.0`) is what lets a
Windows-side browser reach the WSL-native server.

## Equivalent setup on macOS and Linux

The WSL path above is, at its core, this same POSIX flow — clone, create a
`.venv`, install dependencies, point `DATABASE_URL` at PostgreSQL, run
Alembic — with a networked PostgreSQL host standing in for a local one. These
commands are the direct macOS/Linux equivalent; unlike the WSL2 + Windows-
service path above, they have not been runtime-verified by this project.
Install and manage PostgreSQL 16+ outside this repository using the method
appropriate to your system. The commands below assume its standard CLI tools
are already on `PATH` and a PostgreSQL server is listening locally.

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
python -c "import secrets; print(secrets.token_urlsafe(32))" # database role password
```

Using a PostgreSQL administrator account, create the same application role
and databases used by the WSL guide. Use the URL-safe database role password
generated above in both `DATABASE_URL` and the `createuser -P` prompt. These
commands prompt for passwords rather than putting them in shell history:

```bash
createuser -h <your-postgres-host> -p 5432 -U postgres -W -P scotus
createdb -h <your-postgres-host> -p 5432 -U postgres -W -O scotus scotus
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

The root `.env` remains owned by Python processes and `app/.env` by
SvelteKit; the ports and exact-match `ADMIN_TOKEN` contract are identical on
every platform.

## Verify the local stack

Use this checklist after either platform's startup steps:

1. Confirm PostgreSQL accepts an authenticated connection from WSL on port
   `5432` at the resolved gateway address (`python -m alembic current` is
   sufficient proof).
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

- **Port 8000 or 5173 already in use:** diagnose from WSL with
  `ss -ltnp | grep -E ':(8000|5173)'` to see the owning process, then recover
  with `./scripts/dev-start.sh --stop`, which terminates whatever is
  listening on either port. Stop only a process you recognize and own;
  otherwise change the conflicting service's configuration or ask its
  operator.
- **WSL can't reach PostgreSQL after a reboot:** the WSL2 NAT gateway address
  can shift across Windows or WSL restarts. Check the current value with
  `ip route show default`. `scripts/dev-start.sh` re-syncs `.env`
  automatically at every startup; if you instead run a bare `pytest`, the
  drift surfaces as a `tests/test_wsl_postgres_reachability.py` failure
  carrying the corrected DSN in its message.
- **PostgreSQL reachable from Windows but refused from WSL:** check the three
  access gates in `.planning/phases/46-dev-environment-reliability/46-WINDOWS-POSTGRES-SETUP.md`
  in order — `listen_addresses`, the `pg_hba.conf` host rule, and the
  Windows Firewall rule. The firewall rule is the usual culprit when a
  Windows-side client (e.g. `psql` run from PowerShell) already works but WSL
  gets connection-refused.
- **Reload or hot-module replacement doesn't fire on save:** check, in this
  order, (1) whether your editor is actually connected into WSL rather than
  writing through the `\\wsl.localhost\...` share path from a Windows-native
  editor, and (2) whether your working copy is on native ext4 rather than a
  Windows-mounted drive.
- A checkout sitting on a Windows-mounted drive is the root cause of the
  second of those two checks — it is not something to work around with
  watcher-polling settings; relocate the checkout instead.
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
- **Python commands use the wrong interpreter:** activate `.venv`
  (`source .venv/bin/activate`) and confirm
  `python -c "import sys; print(sys.executable)"` points inside the checkout.
- **Alembic migration fails:** stop the API, re-check `DATABASE_URL`, then run
  `python -m alembic current` and `python -m alembic upgrade head`. Read the
  first database error rather than hand-creating tables.
- **Frontend dependency or startup errors:** from `app`, run `npm ci` to restore
  the lockfile-defined dependencies, then retry `npm run dev`. Do not delete or
  rewrite `package-lock.json` as a troubleshooting shortcut.

For safe restarts, use Ctrl+C in the `dev-start.sh` window (or `./scripts/dev-start.sh --stop`
from another shell), confirm the ports are free, and then run
`./scripts/dev-start.sh` again. The PostgreSQL Windows service is managed
independently through normal Windows service tooling (`Services.msc`,
`Get-Service`/`Start-Service`/`Restart-Service`) and is not started or
stopped by this script.

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
