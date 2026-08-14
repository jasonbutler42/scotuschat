"""
Shared "is this DATABASE_URL actually configured" guard (WR-04).

Before this module existed, the root conftest.py and api/tests/conftest.py
each defined their own copy of this exact placeholder-detection logic
(`bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"`).
A future change to the placeholder-DSN literal, or the addition of a new
sentinel pattern, was easy to apply in one copy and miss in the others,
silently reopening the "ran against a fake/placeholder DB" gap this guard
exists to close. This module is the single source of truth for that check;
both conftest.py files import it rather than redefining it.
"""


def is_db_configured(url: str | None) -> bool:
    """
    Return True if `url` looks like a real, usable database DSN.

    False for:
        - unset/empty values
        - the Anthropic API key placeholder pattern ("sk-ant" substring,
          guarding against DATABASE_URL and ANTHROPIC_API_KEY env vars
          being mixed up in a .env file)
        - the literal example DSN from .env.example
          ("postgresql+asyncpg://user:pass@host/db")
    """
    return bool(url) and "sk-ant" not in url and url != "postgresql+asyncpg://user:pass@host/db"
