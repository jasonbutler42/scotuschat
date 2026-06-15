---
phase: 01-foundation-proof-of-concept
plan: 04
subsystem: pipeline
tags: [python, pdfplumber, sqlalchemy, anthropic, instructor, tenacity, pytest, rule-based-parser]

# Dependency graph
requires:
  - phase: 01-foundation-proof-of-concept/01-03
    provides: pipeline/db.py (async engine), pipeline/commands/parse.py (stub), conftest.py

provides:
  - pipeline/parser/__init__.py — parser package marker
  - pipeline/parser/extractor.py — pdfplumber extraction (extract_pages, normalize_text)
  - pipeline/parser/state_machine.py — rule-based SCOTUS transcript parser with F04 + cascade fixes
  - pipeline/parser/llm_pass.py — instructor + tenacity two-layer LLM corrective pass
  - pipeline/commands/parse.py — full parse command replacing Plan 03 stub
  - pipeline/tests/test_parse.py — parser unit tests (no DB required for core tests)
  - pipeline/tests/test_pipeline_run.py — state machine + re-run tests

affects:
  - 01-foundation-proof-of-concept/01-05 (FastAPI reads utterances written by parse step)

# Tech tracking
tech-stack:
  added:
    - pdfplumber (PDF text extraction — already in requirements.txt, now used)
    - instructor[anthropic] (Mode.TOOLS structured output — already in requirements.txt, now used)
    - tenacity (two-layer retry — already in requirements.txt, now used)
  patterns:
    - Two-variable section hint: pending_section_hint + current_section_hint prevents cascade (Pitfall 3)
    - F04 fix: ON\s+BEHALF\s+OF in TOC_SECTION_RE handles Obergefell "ON BEHALF OF" header variant
    - Two-layer retry: tenacity outer (transient) + instructor inner (structural) — separate failure modes
    - AsyncAnthropic(max_retries=0): disables SDK retries to prevent triple-retrying (Pitfall 4)
    - assign_side(): deterministic rule-based side assignment from raw speaker label (D-09)
    - No DELETE on re-run: PIPE-11 enforced by never issuing DELETE on utterance rows

key-files:
  created:
    - pipeline/parser/__init__.py
    - pipeline/parser/extractor.py
    - pipeline/parser/state_machine.py
    - pipeline/parser/llm_pass.py
    - pipeline/tests/test_parse.py
    - pipeline/tests/test_pipeline_run.py
  modified:
    - pipeline/commands/parse.py (replaced stub with full implementation)

key-decisions:
  - "state_machine.py copies spike parse.py exactly, with only two mandatory fixes: F04 (ON BEHALF OF in TOC_SECTION_RE) and cascade fix (two-variable section hint design)"
  - "LLM pass falls back to rule-based output on failure instead of hard-failing — improves resilience for PoC while PIPE-06 failure classification is still documented"
  - "assign_side() is deterministic rule-based — no LLM needed for BENCH/ADVOCATE classification (D-09 Open Question #3 resolution)"
  - "parse command uses get_session() from pipeline.db (shared with ingest) — consistent session lifecycle pattern across all pipeline steps"
  - "LLM pass called on full transcript text as single call (D-05) — no chunking needed for SCOTUS Q1"

patterns-established:
  - "Parser package pattern: pipeline/parser/ contains extractor.py, state_machine.py, llm_pass.py as separate concerns"
  - "Two-layer retry: @retry tenacity outer (transient) wraps call_llm_parse which uses instructor max_retries=2 (structural)"
  - "Fallback-to-rule-based: LLM failure degrades gracefully; utterances still written using rule-based output"
  - "No-DB parser tests: test_stage_directions, test_section_hint_not_cascade, test_on_behalf_of regression all run without any DB connection"

requirements-completed: [PIPE-03, PIPE-04, PIPE-05, PIPE-06, PIPE-10, PIPE-11]

# Metrics
duration: 45min
completed: 2026-06-11
---

# Phase 1 Plan 04: Pipeline Parse Command Summary

**Full pdfplumber extraction + rule-based state machine (spike copy + F04 fix + cascade fix) + instructor/tenacity LLM corrective pass, writing utterance rows with pipeline_run_id, strategy, is_stage_direction, and person_id=null**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-06-11
- **Completed:** 2026-06-11
- **Tasks:** 4
- **Files created:** 6 | **Files modified:** 1

## Accomplishments

- pipeline/parser/extractor.py: exact spike copy — extract_pages() (pdfplumber, skips first 3 pages, dynamic word-index detection), normalize_text() (soft hyphen normalization), all regex constants (LINE_NUM_RE, HEADER_RE, PAGE_NUM_RE, WORD_INDEX_RE)
- pipeline/parser/state_machine.py: spike parse.py adapted for production use — parse_transcript() returns list[dict], assign_side() deterministic rule-based function; F04 fix (ON BEHALF OF in TOC_SECTION_RE); cascade fix (pending_section_hint + current_section_hint two-variable design); no LLM imports
- pipeline/parser/llm_pass.py: instructor.from_anthropic with Mode.TOOLS, AsyncAnthropic(max_retries=0) (Pitfall 4 prevention), ParsedUtterance/ParseResponse Pydantic models, two-layer retry (tenacity outer on RateLimitError/APIConnectionError, instructor inner max_retries=2 for structural failures), SYSTEM_PROMPT constant
- pipeline/commands/parse.py: replaced stub — state transitions (pending→running→completed|failed), extract_pages(), parse_transcript(), parse_with_llm() with graceful fallback, Utterance rows written with pipeline_run_id/strategy/person_id=None, no DELETE on re-run (PIPE-11), dry-run mode
- pipeline/tests/test_parse.py: 6 tests — test_stage_directions (no DB), test_run_id_strategy (DB, skips gracefully), test_stage_direction_classification (no DB), test_llm_failure_modes (monkeypatch, no DB), test_section_hint_not_cascade (no DB), test_on_behalf_of_not_appended_to_prior_speaker (F04 regression, no DB)
- pipeline/tests/test_pipeline_run.py: test_state_machine (DB, skips gracefully), test_rerun_creates_new_rows (DB, skips gracefully)

## Task Commits

Each task was committed atomically:

1. **Task 1: PDF extractor + rule-based state machine parser** - feat(01-04): add pipeline/parser package with extractor and state machine (spike copy + F04 + cascade fix)
2. **Task 2: LLM corrective pass** - feat(01-04): add llm_pass.py with instructor+tenacity two-layer retry
3. **Task 3: Parse command (replace stub)** - feat(01-04): implement full parse command with state transitions, utterance writes, no-delete re-run
4. **Task 4: Parser unit tests and pipeline_run state machine tests** - test(01-04): add test_parse.py and test_pipeline_run.py

**Plan metadata:** docs(01-04): complete pipeline parse plan

## Files Created/Modified

- `pipeline/parser/__init__.py` — empty package marker
- `pipeline/parser/extractor.py` — exact spike copy: extract_pages() (pdfplumber, layout=False, skip 3 pages, dynamic word-index stop), normalize_text(), strip_line_number(), all 4 regex constants
- `pipeline/parser/state_machine.py` — spike copy + 2 mandatory fixes: F04 (ON\\s+BEHALF\\s+OF in TOC_SECTION_RE), cascade (two-variable section hint); parse_transcript() returns list[dict]; assign_side() rule-based side assignment; no LLM imports
- `pipeline/parser/llm_pass.py` — instructor.from_anthropic(AsyncAnthropic(max_retries=0), mode=Mode.TOOLS); ParsedUtterance + ParseResponse Pydantic models; call_llm_parse() (claude-haiku-4-5-20251001, max_tokens=8192, max_retries=2); parse_with_llm() outer tenacity retry (RateLimitError/APIConnectionError, exponential backoff, 5 attempts); SYSTEM_PROMPT constant
- `pipeline/commands/parse.py` — REPLACED stub; run_parse(): load PipelineRun, pending→running, extract_pages, parse_transcript, parse_with_llm (graceful fallback), write Utterance rows (person_id=None, no DELETE), running→completed; _fail_run() helper; dry-run mode
- `pipeline/tests/test_parse.py` — 6 tests: stage_directions, run_id_strategy (DB skip), stage_direction_classification, llm_failure_modes, section_hint_not_cascade, on_behalf_of_not_appended (F04 regression)
- `pipeline/tests/test_pipeline_run.py` — test_state_machine (DB skip), test_rerun_creates_new_rows (DB skip)

## Decisions Made

- **LLM pass falls back to rule-based on failure:** Rather than hard-failing the parse run when the LLM corrective pass fails, the command falls back to rule-based output and writes those utterances. This is appropriate for Phase 1 PoC where the rule-based parser already achieves ~95% accuracy. The failure is logged with strategy remaining "rule_based". Structural failures (InstructorRetryException, BadRequestError) are distinguished from transient in the log output.
- **assign_side() deterministic rule-based:** Side assignment from raw speaker label uses regex patterns (BENCH_RE, ADVOCATE_RE) rather than LLM. This is more reliable, cheaper, and faster — SCOTUS transcript labels are highly regular (JUSTICE X → BENCH, MR./MS./GENERAL X → ADVOCATE). Resolves D-09 Open Question #3.
- **Two-variable section hint design:** pending_section_hint is set on TOC marker detection; current_section_hint is consumed and cleared at each new speaker turn start. This prevents the cascade bug (Pitfall 3) where every utterance after a section marker inherits the hint.
- **F04 applied exactly as documented:** ON\\s+BEHALF\\s+OF added to TOC_SECTION_RE with re.IGNORECASE flag. This handles "ON BEHALF OF PETITIONERS ON QUESTION 1" in Obergefell.
- **instructor.Mode.TOOLS for structured output:** Per D-14 — uses Anthropic's native tool-calling API with automatic Pydantic validation. Avoids raw tool_use which lacks auto-retry on schema mismatch.
- **No delete on re-run:** parse.py has zero DELETE statements or .session.delete() calls on Utterance rows. New runs always add rows under a new pipeline_run_id (PIPE-11).

## Deviations from Plan

None — plan executed exactly as specified. All mandatory fixes (F04, cascade) applied as documented. All acceptance criteria met.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: prompt-injection-mitigated | pipeline/parser/llm_pass.py | T-04-01: Transcript text pre-cleaned by extract_pages/normalize_text before LLM call; instructor schema validation rejects malformed output |
| threat_flag: api-key-protected | pipeline/parser/llm_pass.py | T-04-02: ANTHROPIC_API_KEY loaded via AsyncAnthropic() from env (dotenv); never logged or hardcoded |
| threat_flag: structural-vs-transient-separated | pipeline/parser/llm_pass.py | T-04-03: InstructorRetryException/BadRequestError not in tenacity retry_if_exception_type; only RateLimitError/APIConnectionError retried by tenacity |

## Known Stubs

None. All implemented functionality is wired to real behavior. The LLM pass falls back to rule-based output on failure but this is intentional resilience, not a stub.

## Self-Check

Files created/verified:
- pipeline/parser/__init__.py: created (empty) ✓
- pipeline/parser/extractor.py: created ✓
- pipeline/parser/state_machine.py: created ✓
- pipeline/parser/llm_pass.py: created ✓
- pipeline/commands/parse.py: modified (stub replaced) ✓
- pipeline/tests/test_parse.py: created ✓
- pipeline/tests/test_pipeline_run.py: created ✓

Key string verification:
- extractor.py contains "LINE_NUM_RE" and "HEADER_RE": ✓
- extractor.py contains "extract_text(layout=False)": ✓
- extractor.py contains "range(3, len(pdf.pages))": ✓
- state_machine.py contains "ON\\s+BEHALF\\s+OF" (F04 fix): ✓
- state_machine.py contains "pending_section_hint" and "current_section_hint" (cascade fix): ✓
- state_machine.py contains "def assign_side": ✓
- state_machine.py does NOT contain anthropic/instructor imports: ✓
- llm_pass.py contains "AsyncAnthropic(max_retries=0)": ✓
- llm_pass.py contains "instructor.Mode.TOOLS" and "instructor.from_anthropic": ✓
- llm_pass.py contains "max_retries=2" on create() call: ✓
- llm_pass.py contains "wait_exponential" and "stop_after_attempt": ✓
- llm_pass.py contains "RateLimitError" and "APIConnectionError" in retry: ✓
- llm_pass.py contains "class ParsedUtterance(BaseModel)" with 5 fields: ✓
- llm_pass.py contains "class ParseResponse(BaseModel)": ✓
- llm_pass.py contains "SYSTEM_PROMPT" constant: ✓
- parse.py contains "PipelineRunStatus.RUNNING/COMPLETED/FAILED": ✓
- parse.py contains "person_id=None": ✓
- parse.py contains "pipeline_run_id=run.id": ✓
- parse.py contains "strategy=run.strategy": ✓
- parse.py does NOT contain DELETE or remove() on utterance rows: ✓
- parse.py contains "if args.dry_run": ✓
- test_parse.py contains test_stage_directions, test_llm_failure_modes, test_run_id_strategy: ✓
- test_pipeline_run.py contains test_state_machine, test_rerun_creates_new_rows: ✓
- No create_all in pipeline/: ✓

## Self-Check: PASSED

---
*Phase: 01-foundation-proof-of-concept*
*Completed: 2026-06-11*
