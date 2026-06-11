"""
Root-level pytest conftest.

Loads .env so DATABASE_URL and other env vars are available to all test
modules in the `tests/` directory.
"""

from dotenv import load_dotenv

# Load .env before any tests run.
# Tests that need DATABASE_URL will get it from os.environ after this call.
load_dotenv()
