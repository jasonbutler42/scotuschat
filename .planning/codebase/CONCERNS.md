# Codebase Concerns

**Analysis Date:** 2026-06-15

## Tech Debt

**PDF data corruption (em dash → soft hyphen/&shy;) — FIXED, data remains dirty**

- Issue: pdfplumber emits U+00AD (soft hyphen) or HTML entity `&shy;` where PDFs have em dashes (U+2014). The `normalize_text()` function in `pipeline/parser/extractor.py` now catches and corrects both forms, but existing database records created before the fix still contain corrupted text.
- Files: `pipeline/parser/extractor.py`, database utterance records pre-2026-06-12
- Impact: Read operations on old data return corrupted speaker text and utterance text with soft hyphens instead of em dashes. This breaks semantic correctness of the transcript (em dashes are meaningful interruption markers in SCOTUS transcripts). Phase 2 fixture data has not been updated; old arguments in the DB may have corrupted text visible to end users.
- Fix approach: Re-run the ingest + parse pipeline for all existing arguments to regenerate utterances with corrected text. This is a backward-compatible operation (pipeline re-runs create new pipeline_run_id rows; old rows accumulate and are hidden by the API's MAX(pipeline_run_id) filtering in `api/services/arguments.py`). Recommend as a maintenance task after Phase 2 completion.

---

## Known Bugs

**None currently documented.** Phase 4 verification (2026-06-15) reported zero remaining issues after accessibility hardening.

---

## Security Considerations

**SSRF mitigation in PDF ingest — already implemented**

- Risk: Pipeline ingest accepts a URL and downloads via httpx without validation. Malicious actors could supply internal URLs to enumerate/attack private infrastructure.
- Files: `pipeline/commands/ingest.py` (lines 35–55)
- Current mitigation: `_validate_url()` enforces HTTPS + `supremecourt.gov` domain only before any httpx call (T-03-01 in threat model). This is correct.
- Recommendations: Maintain strict URL scheme/netloc validation. Consider adding a domain whitelist if scope expands beyond supremecourt.gov in the future.

**PCI DSS scope — API is read-only, no credential handling**

- Risk: None — FastAPI endpoint never writes user-supplied data to the database; all data ingestion is CLI-only (pipeline step).
- Files: `api/routers/arguments.py`, `api/routers/cases.py`, `api/routers/people.py`
- Current mitigation: Read-only design by architecture. No payment data, PII, or sensitive user input is accepted via HTTP.
- Recommendations: Maintain read-only API design. If future phases add user-facing features (e.g., bookmarks, annotations), evaluate PCI scope.

**Environment variable exposure — .env file present, never committed**

- Risk: DATABASE_URL and ANTHROPIC_API_KEY are stored in .env file at project root. If accidentally committed or leaked, credentials are exposed.
- Files: `.env` (gitignored), `.env.example` (public template), `api/core/config.py`, `pipeline/db.py`
- Current mitigation: `.env` is in `.gitignore`. Settings use pydantic-settings for validation. No hardcoded credentials in source.
- Recommendations: Maintain .env in .gitignore. CI/CD should inject env vars via secure secrets manager (not .env files). Never commit .env to version control.

**LLM API key (ANTHROPIC_API_KEY) used only in pipeline CLI**

- Risk: API key is optional in FastAPI (default empty string), but required for parse step. If key is exposed, attacker can make API calls on Offen's billing account.
- Files: `api/core/config.py` (optional), `pipeline/parser/llm_pass.py` (used for instructor/tenacity retry logic)
- Current mitigation: Key is loaded from .env only; not in code. Pipeline is CLI-only (not HTTP-exposed), reducing attack surface.
- Recommendations: Rotate API key periodically. Monitor Anthropic usage for anomalies. Consider restricting key to the `claude-haiku-4-5-20251001` model only if API supports it.

---

## Performance Bottlenecks

**LLM parse pass is optional and gracefully degrades**

- Problem: The parse step has two phases: rule-based (primary) + optional LLM corrective pass. If the LLM call fails (rate-limited, network error, or structural failure), the parse run is marked FAILED and operator-visible. Subsequent parse runs can retry, but there is no automatic fallback to rule-based-only results.
- Files: `pipeline/commands/parse.py` (lines 53–200), `pipeline/parser/llm_pass.py` (lines 86–162)
- Cause: LLM failures are classified as either transient (tenacity retries 5×) or structural (fail immediately). Structural failures (Pydantic schema mismatch, BadRequestError) cannot be recovered by retrying. The codebase has no fallback to use rule-based output if LLM fails.
- Improvement path: Add a `--fallback-to-rule-based` flag to the parse command. If LLM pass fails with a structural error AND this flag is set, continue with rule-based results only. Mark the utterances as `strategy="rule_based"` instead of `"llm_corrective"`. This requires careful handling of the pipeline_run state machine to avoid ambiguity.

**Database query scalability — BigInteger PK for utterances**

- Problem: Utterance table uses BigInteger PK to accommodate millions of rows across many cases. No issues observed yet, but as the database grows, query performance on `utterances` (filtering by argument_id + pipeline_run_id, ordering by sequence) depends on index quality.
- Files: `api/models/models.py` (lines 222–246), database schema `alembic/versions/0001_initial_schema.py`
- Cause: SQLAlchemy select queries in `api/services/arguments.py` execute `.all()` to fetch all utterances for an argument. For large arguments (1000+ utterances), this could cause memory pressure if not paginated.
- Improvement path: Implement pagination at the API layer. Add `?limit=100&offset=0` query parameters to the arguments endpoint. Update the frontend to fetch utterances in batches if the UI implements lazy-loading.

**State machine regex compilation — run on every invocation**

- Problem: `pipeline/parser/state_machine.py` defines ~12 compiled regex patterns at module level (good). However, the main parse loop in `parse_transcript()` iterates line-by-line and calls these regexes repeatedly on every line.
- Files: `pipeline/parser/state_machine.py` (lines 22–92), parse logic (not shown in excerpt)
- Cause: Regex compilation is O(1) once, but matching is O(n*m) where n=lines and m=regex complexity. For large transcripts (~100 pages, ~5000 lines), this is acceptable but not optimal.
- Improvement path: Profile to confirm this is a bottleneck before optimizing. If needed, batch-compile regexes or use DFA instead of NFA for the state machine. Current performance is likely acceptable for SCOTUS transcripts (40–50k tokens).

---

## Fragile Areas

**Utterance sequence numbering and section hints — cascading state**

- Files: `pipeline/parser/state_machine.py` (lines 150–250, not fully shown)
- Why fragile: The parse state machine maintains `pending_section_hint` and `current_section_hint` to track section transitions. If a TOC marker is missed by the regex, or if the section hint mapping in `SECTION_HINT_MAP` (lines 83–89) is incomplete, subsequen utterances lose their section context. The F04 fix added `ON\s+BEHALF\s+OF` to `TOC_SECTION_RE`, but other variants (e.g., consolidated case section headers) might exist in transcripts the team hasn't tested.
- Safe modification: Add new TOC patterns to `TOC_SECTION_RE` with test coverage. Test against all spike-tested transcripts (Obergefell, Masterpiece, Dobbs, Rahimi) before committing. Add a new test case if modifying the state machine.
- Test coverage: `pipeline/tests/test_parse.py` has 397 lines and covers the rule-based pass extensively. Gaps: no test for all four section hint types ("petitioner", "respondent", "rebuttal", "amicus") across all spike transcripts. Adding parametrized tests for each transcript + section type would reduce fragility.

**API utterance serialization — manual dict construction**

- Files: `api/services/arguments.py` (lines 114–122)
- Why fragile: Utterances are fetched as SQLAlchemy Row tuples (not ORM objects), then manually converted to dicts by iterating `.all()` and constructing a dict from `__table__.columns`. If the Utterance model gains new columns (e.g., a `confidence_score` field for LLM-generated utterances), the dict will include it automatically, but if the API schema (`api/schemas/utterance.py`) is not updated, the response will include unexpected fields, breaking client expectations.
- Safe modification: Use Pydantic `from_attributes=True` to auto-map ORM models to schemas. Replace manual dict construction with `utterance_schema.model_validate(utterance_orm)`. This requires fetching as scalars (ORM objects) rather than raw tuples.
- Test coverage: `api/tests/test_arguments.py` has 188 lines; test the `/arguments/{id}` endpoint response schema against the documented ArgumentUtterancesResponse. Add a test that modifies the Utterance model and confirms the schema validation catches the change.

**Environment configuration — optional API key, required in pipeline**

- Files: `api/core/config.py` (line 17), `pipeline/parser/llm_pass.py` (line 110)
- Why fragile: The API loads `anthropic_api_key` as an optional empty string (default ""). The pipeline assumes it's set when the parse step runs. If a developer runs `python -m pipeline parse` without setting ANTHROPIC_API_KEY, the instructor call fails with a cryptic error ("no API key provided to Anthropic client"). There's no early validation.
- Safe modification: Add a guard in the parse command startup that checks `if not settings.anthropic_api_key: raise ValueError("ANTHROPIC_API_KEY not set")` before attempting LLM initialization. Alternatively, make `api/core/config.py` validate that the key is non-empty only if running the pipeline (requires refactoring to split API vs. pipeline config).
- Test coverage: Add a pytest fixture that unsets ANTHROPIC_API_KEY and confirms the parse command fails with a clear error message. Currently, only integration tests exist (`pipeline/tests/test_parse.py`); no unit test for missing API key.

**SectionRail and MobileNavBar scroll-spy logic — IntersectionObserver callback timing**

- Files: `app/src/lib/components/SectionRail.svelte`, `app/src/lib/components/MobileNavBar.svelte`
- Why fragile: Both components implement scroll-spy via IntersectionObserver to highlight the current section as the user scrolls. If a section has zero utterances (e.g., the "rebuttal" section_hint exists but no utterances are tagged with it), the anchor element is created but has no content, making it impossible for IntersectionObserver to trigger. The active pill will never highlight, confusing the user.
- Safe modification: Filter `sectionAnchors` (in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte`) to only include sections that have at least one utterance. Alternatively, ensure the rule-based parser always tags at least one utterance with each section_hint if the section header is detected. Add a test assertion: "Every detected section_hint must have at least one utterance."
- Test coverage: `pipeline/tests/test_parse.py` has parametrized test cases for each spike transcript. Add a test case that confirms every section_hint in the output has at least one utterance. This is a static analysis test; no browser required.

**Database migration idempotency — Alembic upgrade path**

- Files: `alembic/versions/0001_initial_schema.py`, `alembic/versions/0002_add_speaker_alias.py`
- Why fragile: The migrations use raw SQL (CREATE TABLE, ALTER TABLE). If a developer runs `alembic upgrade head` twice, the second run will fail with "table already exists". There's no explicit `IF NOT EXISTS` guards. Alembic is designed to be idempotent in theory, but raw-SQL migrations are fragile.
- Safe modification: Ensure all new migrations use Alembic's Operations API (op.create_table, op.add_column) instead of raw SQL. For existing migrations, add idempotency checks or document that they can only be applied once per database.
- Test coverage: Add a pytest fixture that runs `alembic upgrade head` twice on a fresh test database and confirms it succeeds both times (or fails gracefully the second time with a clear message). Currently, no test for migration safety.

---

## Scaling Limits

**PDF storage — local filesystem only**

- Current capacity: Project stores PDFs in `data/pdfs/` on the local filesystem. No size limit enforced; depends on available disk space.
- Limit: If the project scales to 1000+ SCOTUS transcripts, total storage could reach 10–20 GB (assuming ~10 MB per transcript). Local filesystem will eventually fill up.
- Scaling path: Migrate PDF storage to cloud object storage (Azure Blob Storage, AWS S3, or DO Spaces). Update `pipeline/commands/ingest.py` to write to cloud instead of local disk. Requires minimal API changes (pdf_path would still point to cloud URL, not local filesystem).

**Database connections — small pool for pipeline**

- Current capacity: `pipeline/db.py` sets `pool_size=2, max_overflow=10` (small pool for single-process CLI). FastAPI uses `pool_size=5, max_overflow=10` (larger for web server).
- Limit: If the pipeline CLI is upgraded to multi-process (parallel parse runs), the small pool will become a bottleneck. Connections will queue and timeout.
- Scaling path: Make pool size configurable via environment variable. For multi-process pipeline, use a connection pool manager (e.g., pgBouncer externally, or SQLAlchemy's QueuePool with size=20+).

**LLM token budget — full transcript as single call**

- Current capacity: Design decision D-05 sends the entire transcript (40–50k tokens for Q1) as a single LLM call to claude-haiku-4-5-20251001 (max_tokens=8192 output).
- Limit: If SCOTUS adds extra-long arguments (100k+ tokens), a single call will hit the context window. The LLM will fail with "max_tokens exceeded" or truncate output.
- Scaling path: Implement chunking strategy. Split transcript into 30k-token chunks, parse each separately, and merge results. Requires careful handling of cross-chunk speaker context (e.g., if a speaker's utterance spans a chunk boundary). Add a `--chunk-size` parameter to the parse command.

---

## Dependencies at Risk

**anthropic >= 0.40 — API compatibility risk**

- Risk: Instructor library depends on anthropic SDK. If Anthropic releases a major version (e.g., 1.0) with breaking changes, instructor may not support it immediately. The parse step will fail until instructor updates.
- Files: `requirements.txt` (line 7), `pipeline/parser/llm_pass.py` (lines 29–30)
- Impact: Parse step becomes inoperable until instructor is updated and tested.
- Migration plan: Monitor Anthropic SDK releases. Maintain a separate test for the parse step against the latest anthropic SDK version. Pin to a stable minor version (e.g., `anthropic >= 0.40, < 1.0`) to avoid surprise breakage.

**pdfplumber >= 0.11 — encoding edge cases**

- Risk: pdfplumber is a thin wrapper around pdfminer.six, which uses regex to extract text from PDFs. Edge cases in encoding (e.g., Type1 fonts, CID fonts) can cause extraction failures. The soft hyphen corruption issue (fixed in `normalize_text()`) is evidence that pdfplumber can produce unexpected characters.
- Files: `pipeline/parser/extractor.py`, `requirements.txt` (line 9)
- Impact: New SCOTUS transcript formats (different PDF encoder, different reporter vendor) could break extraction.
- Migration plan: Add a CI job that tests the extractor against all spike-tested transcripts. If a new transcript fails extraction, capture the raw text and add a new normalization rule to `normalize_text()`. Monitor pdfplumber GitHub issues for similar problems reported by other users.

**sqlalchemy >= 2.0 — async API stability**

- Risk: SQLAlchemy 2.0 is relatively new (released 2023). The async API (AsyncSession, async_engine) is stable but less battle-tested than sync API. Subtle bugs in expire_on_commit=False handling or transaction safety could surface.
- Files: `api/core/database.py`, `pipeline/db.py`, entire ORM models layer
- Impact: Race conditions, lost writes, or deadlocks could occur under concurrent load.
- Migration plan: Maintain comprehensive async integration tests (pipeline/tests/ already does this). Test parse runs in parallel to catch deadlocks. Pin to a stable SQLAlchemy version (>= 2.0, < 3.0). Monitor SQLAlchemy GitHub issues for async-related bugs.

---

## Missing Critical Features

**No data validation on argumentutterances response — nullable fields**

- Problem: The Utterance ORM model has several nullable fields: `raw_speaker_label`, `section_hint`, `speaker_role`, and `speaker_name` (from Person). The API returns these as-is (possibly null). The frontend in `app/src/routes/cases/[slug]/arguments/[id]/+page.svelte` has defensive checks (e.g., `u.speaker_name ?? u.raw_speaker_label ?? ''`) to handle nulls, but there's no clear API contract specifying which fields can be null and when. A client that doesn't know about nullable fields could crash.
- Blocks: Cannot add a TypeScript OpenAPI schema generator without explicit nullable/required annotations in the API schemas.
- Fix approach: Define explicit Pydantic schemas for ArgumentUtterancesResponse, UtteranceDetail, ArgumentMetadata in `api/schemas/`. Use `Field(..., description="...")` to document nullability. Add a route that returns the OpenAPI schema so clients can auto-generate types.

**No metrics or observability for pipeline failures**

- Problem: If a parse run fails (LLM error, Pydantic validation failure), the failure_reason is logged to the database in plaintext. There's no structured logging, no metrics export, and no alerting. An operator has to manually query the database to discover failures.
- Blocks: Cannot monitor pipeline health or alert on systematic failures (e.g., "parse is failing for all new transcripts").
- Fix approach: Add structured logging (JSON format) to the pipeline commands. Export metrics (parse success/failure count, LLM call latency) to a monitoring system (Prometheus, DataDog, etc.). Add a status endpoint to the API that returns the status of the latest pipeline runs so operators can monitor health from a dashboard.

**No rollback mechanism for failed pipeline runs**

- Problem: If a pipeline run fails partway through (e.g., parse succeeds, but resolve fails on speaker resolution), the partial results remain in the database. Re-running the same step creates a new run_id, but the old failed run's data is still visible if an operator queries it directly. There's no built-in way to "undo" a run.
- Blocks: Cannot easily clean up after a failed import or failed resolve.
- Fix approach: Add a `--delete-run` command that deletes all rows associated with a pipeline_run_id (utterances, argument_participants, etc.). Add a confirmation prompt. Document that this is a destructive operation and should only be used by operators who understand the pipeline state machine.

---

## Test Coverage Gaps

**API schema validation — no test for nullable fields**

- What's not tested: The API endpoints return Pydantic-serialized dicts. No test verifies that the returned data matches the declared schema (e.g., that `speaker_name` is indeed nullable when the Person record doesn't exist).
- Files: `api/tests/test_arguments.py`, `api/schemas/utterance.py`
- Risk: If a schema field is accidentally marked as required (non-nullable) but the code can return null, the response will fail JSON validation in a strict client.
- Priority: Medium — affects API contract stability.

**Pipeline command argument validation**

- What's not tested: The pipeline commands parse command-line arguments with argparse. No test verifies that invalid arguments are rejected with clear error messages. For example, `python -m pipeline ingest --url "http://evil.com/bad.pdf"` should be rejected by `_validate_url()`, but there's no test that confirms this.
- Files: `pipeline/commands/ingest.py`, `pipeline/__main__.py`
- Risk: A malformed or malicious argument could cause unexpected behavior or a crash with a cryptic error.
- Priority: Medium — affects operator experience and security.

**Concurrent parse runs — no stress test**

- What's not tested: The pipeline is designed to handle concurrent parse runs (each gets its own pipeline_run_id). No test spawns multiple parse commands in parallel and verifies that the database state remains consistent (no race conditions, no lost updates).
- Files: `pipeline/commands/parse.py`, `pipeline/tests/test_parse.py`
- Risk: If two parse commands for the same argument run in parallel, they might interfere with each other or corrupt the database state.
- Priority: Low — pipeline is intended to be single-process, but future scaling might add parallelism.

**Accessibility — cross-browser focus ring visibility**

- What's not tested: The focus ring styling in `app/src/app.css` (2px blue outline) is tested in Phase 4 via human UAT. No automated test verifies focus ring visibility across browsers (Chrome, Firefox, Safari, Edge) or that screen reader focuses match visual focus.
- Files: `app/src/app.css`, UI components
- Risk: Screen reader users might focus on an element that's not visually obvious, or vice versa.
- Priority: Low — Phase 4 completion includes human UAT, but ongoing regression testing is recommended.

---

*Concerns audit: 2026-06-15*
