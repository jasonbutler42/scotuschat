"""
Permanent regression test for D-02 (WSL-native code reaches the Windows
Postgres service).

Proves two things end to end:

1. `test_wsl_can_connect_to_windows_postgres` — a WSL-native process opens a
   real SQLAlchemy/asyncpg connection to the Windows-hosted Postgres 18
   service, using the *dynamically resolved* WSL2 NAT gateway IP (never a
   value cached in `.env`), and gets a row back from `SELECT 1`.
2. `test_env_db_host_matches_wsl_gateway` — if the host component recorded in
   `.env` has drifted from the currently-resolved gateway (WSL2's NAT
   gateway is documented to shift across Windows/WSL restarts —
   46-RESEARCH.md Pitfall 2), that drift fails LOUDLY with a copy-pasteable
   corrected DSN, instead of surfacing later as a confusing connection error.

Both tests skip cleanly (never fail) when not running under WSL, or when no
DSN is configured — this module is inert on any other platform and in any
environment where Postgres connectivity has not been set up yet (e.g. plan
46-02's checkpoint has not landed).

Neither test writes to any database — `SELECT 1` only.
"""

from __future__ import annotations

import pathlib
import subprocess

import pytest
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Same placeholder guard every DB-gated fixture in this suite uses (root
# conftest.py, api/tests/conftest.py) — a literal, never-real DSN.
_PLACEHOLDER_DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"


def _running_under_wsl() -> bool:
    """
    True when this process is running under WSL.

    Reads /proc/version rather than any DNS/network config — this is a
    platform check, independent of whatever networking mode WSL2 is in.
    """
    proc_version = pathlib.Path("/proc/version")
    if not proc_version.exists():
        return False
    try:
        return "microsoft" in proc_version.read_text().lower()
    except OSError:
        return False


def _wsl_gateway_ip() -> str | None:
    """
    Resolve the Windows host's IP by running `ip route show default` and
    taking the third whitespace-separated field of the first output line.

    Deliberately not the DNS resolver's own config file — 46-RESEARCH.md
    Pattern 2 establishes `ip route` as the semantically correct source (it
    reads the live routing table's default gateway, not a DNS config file);
    both were confirmed to return the identical address on this machine, but
    only one of them is the actual routing fact being relied on.

    Returns None when the command fails, times out, or produces no usable
    output — callers must treat that as "skip," never as an error.
    """
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    first_line = result.stdout.strip().splitlines()[0]
    fields = first_line.split()
    if len(fields) < 3:
        return None
    return fields[2]


pytestmark = pytest.mark.skipif(
    not _running_under_wsl(),
    reason="Not running under WSL — this module's WSL-to-Windows-Postgres reachability checks are inert off WSL (D-02).",
)


def test_env_db_host_matches_wsl_gateway():
    """
    The raw `.env` file's DATABASE_URL/TEST_DATABASE_URL host must match the
    currently-resolved WSL gateway, or fail loudly with the corrected DSN.

    Reads `.env` directly via `dotenv_values` — NOT `os.environ`, which the
    rootdir `conftest.py` (plan 46-01) has already overwritten
    (`DATABASE_URL` gets redirected to `TEST_DATABASE_URL`'s value), which
    would make a same-value comparison vacuous.
    """
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        pytest.skip("No .env file present at the repo root — nothing to check for host drift.")

    raw_values = dotenv_values(env_path)
    if not raw_values.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set in .env — nothing to check for host drift.")

    gateway = _wsl_gateway_ip()
    if gateway is None:
        pytest.skip("Could not resolve the WSL gateway IP via 'ip route show default'.")

    for var_name in ("DATABASE_URL", "TEST_DATABASE_URL"):
        raw_value = raw_values.get(var_name)
        if not raw_value:
            continue

        url = make_url(raw_value)
        corrected_dsn = url.set(host=gateway).render_as_string(hide_password=True)

        assert url.host == gateway, (
            f"{var_name}'s host in .env ('{url.host}') does not match the "
            f"currently-resolved WSL gateway IP ('{gateway}'). WSL2's NAT "
            "gateway is documented to shift across Windows/WSL restarts — "
            "this assertion failing is the expected, loud form of that "
            "drift, not a bug. Update .env's host to match. Corrected DSN: "
            f"{corrected_dsn}"
        )


async def test_wsl_can_connect_to_windows_postgres():
    """
    A WSL-native process opens a real connection to the Windows Postgres
    service over the dynamically-resolved gateway and gets SELECT 1 back.

    Rebuilds the configured URL with the freshly-resolved gateway as its
    host (rather than trusting whatever host happens to already be written
    in `.env`), so this test proves the dynamically-resolved path itself,
    not just "some DSN in .env happens to work."
    """
    gateway = _wsl_gateway_ip()
    if gateway is None:
        pytest.skip("Could not resolve the WSL gateway IP via 'ip route show default'.")

    env_path = REPO_ROOT / ".env"
    raw_values = dotenv_values(env_path) if env_path.exists() else {}
    configured_url = raw_values.get("TEST_DATABASE_URL") or raw_values.get("DATABASE_URL")
    if not configured_url or configured_url == _PLACEHOLDER_DATABASE_URL:
        pytest.skip("No real DATABASE_URL/TEST_DATABASE_URL configured in .env.")

    url = make_url(configured_url).set(host=gateway)

    # connect_args={"statement_cache_size": 0} is mandatory project-wide per
    # CLAUDE.md, even though local dev has no PgBouncer in front of it — every
    # other ad-hoc engine in this repo (pipeline/tests/conftest.py:65-70,
    # root conftest.py, scripts/provision_test_db.py's alembic subprocess)
    # carries it for consistency.
    engine = create_async_engine(
        url,
        connect_args={"statement_cache_size": 0},
        pool_size=2,
        echo=False,
    )
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    except Exception as exc:
        # All three of these gates (46-RESEARCH.md Pitfall 4) produce the
        # identical connection-failure symptom from WSL — enumerate them so
        # whoever hits this doesn't have to re-derive the failure taxonomy.
        #
        # `from None` deliberately suppresses exception chaining: asyncpg's
        # own internal connection frames carry the plaintext password as a
        # local variable (ConnectionParameters.password), and pytest's
        # default long traceback renders every frame's arguments — chaining
        # via `from exc` would print that traceback, leaking the password
        # into test output. Only the exception's own str() (never the
        # connection frames) reaches this message, and driver error
        # messages here never include the password itself.
        raise AssertionError(
            "WSL-native process could not reach the Windows Postgres "
            f"service at {gateway}:{url.port} (D-02). Three independent "
            "gates must all pass and any one of them failing produces this "
            "exact symptom: (1) the postgresql-x64-18 service is not "
            "running, (2) pg_hba.conf has no host rule for the current WSL "
            "subnet, (3) Windows Firewall has no inbound rule allowing TCP "
            f"5432 from the WSL subnet. Original error type: "
            f"{type(exc).__name__}: {exc}"
        ) from None
    finally:
        await engine.dispose()
