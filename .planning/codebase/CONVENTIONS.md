# Coding Conventions

**Analysis Date:** 2026-06-15

## Naming Patterns

**Files:**
- Python modules: `snake_case.py` (e.g., `state_machine.py`, `parse.py`, `resolve.py`)
- Components (Svelte): PascalCase with `.svelte` extension (e.g., `ChatBubble.svelte`, `SectionRail.svelte`)
- Route files (SvelteKit): `+page.server.ts` and `+page.svelte` for page routes; `+layout.svelte` for layouts
- Test files: `test_*.py` (e.g., `test_arguments.py`, `test_people.py`, `test_seed_aliases.py`)

**Functions and Methods:**
- Python: `snake_case` for all functions and async functions (e.g., `get_cases()`, `async def run_parse()`, `_normalize_dashes()`)
- TypeScript/JavaScript: `camelCase` for functions and handlers (e.g., `formatDate()`, `onclick()`)
- Private/internal helpers: Prefix with underscore (e.g., `_db_configured()`, `_fail_run()`, `_normalize_label()`)

**Variables:**
- Python: `snake_case` (e.g., `max_run_id`, `speaker_name`, `is_lead`)
- TypeScript/JavaScript: `camelCase` (e.g., `activeSection`, `isBench`, `avatarBg`)
- Constants: UPPERCASE_SNAKE_CASE (e.g., `SYSTEM_PROMPT`, `LINE_NUM_RE`, `TOC_SECTION_RE`)

**Types:**
- Pydantic models: PascalCase (e.g., `CaseItem`, `UtteranceResponse`, `ParseResponse`, `ParsedUtterance`)
- SQLAlchemy ORM models: PascalCase (e.g., `Case`, `Argument`, `Utterance`, `Person`)
- Python enums: PascalCase (e.g., `SideEnum`, `PipelineRunStatus`)
- TypeScript types: PascalCase (e.g., `SectionAnchor`, `AsyncClient`)

## Code Style

**Formatting:**
- **Python:** No explicit formatter configured. Follow PEP 8:
  - 4-space indentation
  - Max line length ~88 chars (inferred from code samples)
  - Double quotes for strings (mixed usage observed; prefer consistency)
  - Type hints on function signatures required
  
- **TypeScript/JavaScript:** No ESLint/Prettier config detected. Inferred standards:
  - 2-space indentation
  - Semicolons at end of statements
  - Double quotes for strings
  - Type annotations on parameters and returns

- **Svelte:** 2-space indentation, embedded TypeScript with strict checking enabled (`"strict": true` in tsconfig.json)

**Linting:**
- **Python:** No `.flake8`, `pyproject.toml`, or similar config found. Implicit adherence to PEP 8.
- **TypeScript:** `svelte-check --tsconfig ./tsconfig.json` runs type checking; `allowJs: true` and `checkJs: true` in tsconfig.json enable strict checking
- No automated formatters (Prettier, Black) detected in the stack

## Import Organization

**Order (Python):**
1. Standard library imports (`import os`, `from typing import Optional`)
2. Third-party imports (`from fastapi import`, `from sqlalchemy import`, `import instructor`)
3. Local/relative imports (`from api.models.models import`, `from pipeline.parser import`)

Example from `api/services/arguments.py`:
```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.models import Argument, Case, CaseArgument, ...
```

**Order (TypeScript/Svelte):**
1. Standard library and built-in imports (none typically)
2. Third-party library imports (`import { browser } from '$app/environment'`)
3. Relative imports from `$lib` (`import ChatBubble from '$lib/components/...'`)
4. SvelteKit-specific imports (`import type { PageServerLoad }`)

Example from `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`:
```typescript
import ChatBubble from '$lib/components/ChatBubble.svelte';
import StageDirection from '$lib/components/StageDirection.svelte';
import SectionRail from '$lib/components/SectionRail.svelte';
```

**Path Aliases:**
- SvelteKit: `$lib` resolves to `src/lib/`; `$env` resolves to environment module
- Python: No path aliases; absolute imports from project root (e.g., `from api.models.models import Case`)

## Error Handling

**Python (FastAPI/Async):**
- Explicit HTTP exceptions: `from fastapi import HTTPException` with `status_code` and `detail` (see `api/routers/arguments.py`)
  ```python
  if result is None:
      raise HTTPException(status_code=404, detail="Argument not found")
  ```
- Database nulls: Check with `scalar_one_or_none()` and return `None` on miss; let router handle 404
- Async context managers for resources (`async with AsyncClient(...)`)
- No bare `except`; catch specific exceptions (e.g., `anthropic.RateLimitError`, `instructor.InstructorRetryException`)

**TypeScript (SvelteKit):**
- SvelteKit error handling: `throw error(status_code, message)` from `@sveltejs/kit` (see `app/src/routes/cases/+page.server.ts`)
  ```typescript
  if (!res.ok) throw error(res.status, 'Failed to load cases');
  ```
- Optional chaining and nullish coalescing: `utterance.speaker_name ?? utterance.raw_speaker_label ?? ''`
- Null guards on dates: `if (!dateStr) return 'Date unknown';` (see `formatDate()` in both pages)

## Logging

**Framework:** Console-only (no structured logging detected)

**Patterns:**
- Python: `print()` calls for CLI output; no logger imported in routers/services
- Pydantic validation errors logged implicitly by FastAPI (returns 422)
- Test output via pytest captured; no explicit logging in tests

**When to Log:**
- CLI pipeline steps: Print progress/status (e.g., `print(f"Parsed {count} utterances")` pattern not explicitly shown but implied)
- API endpoints: FastAPI logs requests/responses automatically; errors raise HTTPException (implicitly logged)
- No verbose debug logging observed; relies on error messages and test assertions

## Comments

**When to Comment:**
- **Mandatory:** Complex algorithms or non-obvious regex patterns (e.g., `state_machine.py` has detailed comments on every regex constant)
- **Mandatory:** Constraints and gotchas (e.g., `api/core/database.py` explains why `statement_cache_size=0` is in `connect_args`)
- **Mandatory:** Decision rationale (e.g., "PIPE-11 policy: show only latest run" comment in `services/arguments.py`)
- **Mandatory:** Section boundaries (e.g., `# --- Step 1: Verify the argument exists ` with dashes)

**Forbidden:** 
- Obvious comments on simple assignments (`x = 5  # set x to 5`)
- Commented-out code left in (use git history instead)

**JSDoc/TSDoc:**
- Python: Docstrings on all public functions and classes (triple-quoted, multiline)
  ```python
  async def get_argument_with_utterances(
      db: AsyncSession,
      argument_id: int,
  ) -> dict | None:
      """
      Return argument metadata + latest-run utterances, or None if not found.
      
      Returns a dict with shape:
          {...}
      """
  ```
- TypeScript: Comments above functions are sufficient; no JSDoc tags observed
  ```typescript
  /**
   * Format an argued_date string (e.g. "2015-04-28") as "April 28, 2015".
   * Uses Intl.DateTimeFormat per the UI-SPEC Copywriting Contract.
   */
  function formatDate(dateStr: string | null | undefined): string {
  ```

## Function Design

**Size:**
- Python: Service functions typically 10–50 lines (excluding docstrings); larger functions (50+) are broken into steps with section comments
  Example: `get_argument_with_utterances()` in `services/arguments.py` has 5 sequential steps, each commented
- TypeScript: Components and handlers are compact; utility functions like `formatDate()` are 5–10 lines

**Parameters:**
- Python: Type hints required (`argument_id: int`, `db: AsyncSession`); use positional for public functions
- TypeScript: Type annotations required for all parameters and returns
- Svelte: Props passed via `let { prop } = $props();` pattern (Svelte 5 Runes)

**Return Values:**
- Python: Explicit return types required (`-> dict | None`, `-> list[dict]`, `async def ... -> None`)
- TypeScript: Explicit return types (`:string`, `:SectionAnchor[]`)
- Null/undefined handling: Prefer explicit null checks over falsy checks (e.g., `if (!dateStr)` is acceptable for string check; `if (result)` for object)

## Module Design

**Exports:**
- Python: No `__all__` list observed; import directly from modules (e.g., `from api.services.cases import get_cases`)
- TypeScript: Components export default (e.g., `export default ChatBubble`); utilities as named exports
- SvelteKit: Route components are default exports; servers loads are named `export const load`

**Barrel Files:**
- Not used in this codebase; imports go directly to source files

**Circular Imports:**
- No circular imports detected; tight import organization prevents them

## Code Patterns

**Derived State (Svelte 5 Runes):**
- Use `$derived` for reactive computed values: `const roster = $derived.by(() => { ... })`
- Use `$state` for mutable state: `let activeSection = $state<string | null>(null)`
- Use `$effect` for side effects (e.g., IntersectionObserver setup in `SectionRail.svelte`)

**SQLAlchemy Patterns:**
- Use `async def` with `AsyncSession` and explicit `await db.execute()`
- Always use `select()` constructor for queries: `select(Case, Argument).join(...).where(...).order_by(...)`
- Filter conditions use SQLAlchemy column expressions: `.where(CaseArgument.is_lead == True)` (with `# noqa: E712` when comparing to `True`)
- Use `.scalar_one_or_none()` for single-row queries; `.all()` for lists

**API Response Patterns:**
- Return Pydantic models from endpoints; FastAPI auto-serializes to JSON
- Use `response_model=CaseListResponse` on router to ensure schema compliance
- Embed metadata in wrapper response (e.g., `ArgumentUtterancesResponse` wraps argument + utterances)

**Testing Patterns:**
- Mark async tests with `@pytest.mark.asyncio`
- Use `@pytest_asyncio.fixture` for async fixtures
- Guard DB-dependent tests with `@pytest.mark.skipif(not _db_configured(), reason="...")`
- Use `assert response.status_code in (404, 500)` to accept multiple valid outcomes when DB may or may not be available

---

*Conventions analysis: 2026-06-15*

## Incremental Remap — 2026-07-02

Root config files confirmed present as of 2026-07-02 (scope: `.gitignore`, `CLAUDE.md`, `requirements.txt`, `requirements-dev.txt`):

- `.gitignore` — Excludes `.env`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `app/.svelte-kit/`, and `data/pdfs/*.pdf`. Confirms Ruff is part of the Python toolchain (cache dir present).
- `CLAUDE.md` — Project guide checked into the codebase. Defines key constraints, stack, architecture rules, and GSD workflow. No convention changes detected.
- `requirements.txt` — Runtime dependencies confirmed: FastAPI 0.115+, SQLAlchemy 2.0, asyncpg, Alembic, instructor[anthropic], anthropic, tenacity, pdfplumber, httpx, pydantic-settings, boto3, uvicorn.
- `requirements-dev.txt` — Dev dependencies confirmed: pytest>=8.0, pytest-asyncio>=0.23, httpx>=0.27 (extends requirements.txt via `-r requirements.txt`).

No changes to existing conventions content.

---

*Conventions analysis: 2026-06-15 | Last incremental remap: 2026-07-02*
