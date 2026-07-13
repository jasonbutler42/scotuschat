"""
Provision the dedicated local test database (scotus_test).

Standalone script — NOT a pipeline CLI subcommand (D-07, Phase 31). Run
directly:

    python scripts/provision_test_db.py

Two idempotent steps:
    1. CREATE DATABASE <target> on the same Postgres server as
       TEST_DATABASE_URL, if it does not already exist. Runs outside any
       transaction block — CREATE DATABASE cannot execute inside one.
    2. Run `alembic upgrade head` against the target database via
       subprocess, temporarily overriding DATABASE_URL in the subprocess
       environment (alembic/env.py reads os.environ["DATABASE_URL"]
       directly at line 24 — there is no TEST_DATABASE_URL awareness in
       env.py, so pointing DATABASE_URL at the test URL for the subprocess
       is the only way to migrate scotus_test without editing env.py).

Guards (T-31-01): refuses to run if TEST_DATABASE_URL is unset, if the
target database name is "postgres", or if it matches the DATABASE_URL
database name — this script must never provision over the shared dev DB.

No destructive flags exist by design — this script only CREATEs and
migrates; it never drops or truncates a database.

HARD CONSTRAINT (CLAUDE.md): Alembic is the sole DDL authority. This script
never calls Base.metadata.create_all(); schema is always applied via
`alembic upgrade head`.
"""

import argparse
import asyncio
import os
import subprocess
import sys

import asyncpg
from dotenv import load_dotenv
from sqlalchemy.engine import make_url


def _target_db_name(test_url: str) -> str:
    return make_url(test_url).database


def _maintenance_dsn(test_url: str) -> str:
    """
    Derive a raw asyncpg DSN to the `postgres` maintenance database on the
    same host/port/user as the target test database.

    Strips the `+asyncpg` SQLAlchemy driver suffix — asyncpg.connect() wants
    a plain `postgresql://` DSN, not a SQLAlchemy URL object.
    """
    url = make_url(test_url)
    maintenance_url = url.set(database="postgres", drivername="postgresql")
    return maintenance_url.render_as_string(hide_password=False)


async def _create_database_if_absent(test_url: str) -> None:
    target_db = _target_db_name(test_url)
    maintenance_dsn = _maintenance_dsn(test_url)

    conn = await asyncpg.connect(maintenance_dsn, statement_cache_size=0)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        if exists:
            print(f"Database '{target_db}' already exists — skipping CREATE DATABASE.")
            return
        # CREATE DATABASE cannot run inside a transaction block. asyncpg
        # connections execute statements directly (no implicit transaction
        # unless conn.transaction() is opened), so this runs in autocommit.
        await conn.execute(f'CREATE DATABASE "{target_db}"')
        print(f"Created database '{target_db}'.")
    finally:
        await conn.close()


def _run_alembic_upgrade(test_url: str) -> None:
    """
    Run `alembic upgrade head` in a subprocess with DATABASE_URL overridden
    to the test database URL for the duration of the subprocess only.
    """
    env = {**os.environ, "DATABASE_URL": test_url}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        check=True,
    )
    print("alembic upgrade head completed against the test database.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Provision the dedicated local scotus_test database: "
            "CREATE DATABASE (if absent) + alembic upgrade head. "
            "Idempotent — safe to run repeatedly. Never drops or truncates "
            "anything."
        )
    )
    # No destructive flags by design — this script only creates and
    # migrates; deletion/truncation is intentionally out of scope here.
    parser.parse_args()

    load_dotenv()

    test_url = os.environ.get("TEST_DATABASE_URL", "")
    if not test_url:
        print(
            "ERROR: TEST_DATABASE_URL is not set. Add it to your .env file "
            "(see .env.example) before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    target_db = _target_db_name(test_url)

    if target_db == "postgres":
        print(
            "ERROR: TEST_DATABASE_URL must not point at the 'postgres' "
            "maintenance database.",
            file=sys.stderr,
        )
        sys.exit(1)

    dev_url = os.environ.get("DATABASE_URL", "")
    if dev_url:
        dev_db = make_url(dev_url).database
        if target_db == dev_db:
            print(
                "ERROR: TEST_DATABASE_URL's database name matches "
                f"DATABASE_URL's database name ('{dev_db}'). Refusing to "
                "provision over the shared dev database.",
                file=sys.stderr,
            )
            sys.exit(1)

    asyncio.run(_create_database_if_absent(test_url))
    _run_alembic_upgrade(test_url)

    print(f"scotus_test provisioning complete: '{target_db}' is at alembic head.")


if __name__ == "__main__":
    main()
