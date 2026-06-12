"""
LLM corrective pass for SCOTUS transcript parsing.

Uses instructor + tenacity two-layer retry strategy (PIPE-03, PIPE-06):
  - Inner layer: instructor max_retries=2 (Pydantic schema validation failures)
  - Outer layer: tenacity exponential backoff (transient API errors)

Pitfall 4 prevention:
  AsyncAnthropic(max_retries=0) — tenacity owns all transient retries;
  the Anthropic SDK's built-in retry (default 2) would cause triple-retrying
  on 429/503 errors if not disabled.

Failure classification (PIPE-06):
  - anthropic.RateLimitError (HTTP 429)         → transient → outer tenacity retry
  - anthropic.APIConnectionError (network)       → transient → outer tenacity retry
  - instructor.InstructorRetryException          → structural → caller must catch,
      set failure_reason, set pipeline_run.status="failed"
  - anthropic.BadRequestError (HTTP 400)         → structural → fail immediately;
      reraise; caller sets failure_reason

D-14: Use instructor.Mode.TOOLS — Anthropic's native tool-calling API.
D-04: Target model: claude-haiku-4-5-20251001 (Haiku for parse step).
D-05: Full transcript as single LLM call (no chunking needed for SCOTUS Q1
      at ~40-50k tokens).
"""

from typing import Optional

import anthropic
import instructor
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
# System prompt constant
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a transcript parser for U.S. Supreme Court oral argument transcripts.
Extract every utterance from the pages provided and return a structured list.

Rules:
- Each speaker turn is one utterance: starts at "LABEL: text", ends when the next speaker
  or stage direction begins. Continuation lines belong to the current speaker.
- Stage directions such as "(Laughter.)" or "(Brief pause.)" are their own utterance with
  is_stage_direction=true and raw_speaker_label=null.
- Inline stage directions embedded in a speaker's text: split into separate utterances —
  text-before (speaker), stage direction (null), text-after (speaker).
- Terminal stage directions ("The case is submitted. (Whereupon, ...)"): split into two —
  the spoken sentence, then the stage direction.
- Preserve speaker labels exactly as they appear in the transcript.
- Skip: page headers ("Official", reporter names), page numbers, TOC entries
  ("ORAL ARGUMENT OF", "REBUTTAL ARGUMENT OF", "APPEARANCES:", "ON BEHALF OF").
- section_hint: set ONLY on the FIRST utterance after a section transition marker.
  Use one of: "petitioner", "respondent", "rebuttal", "amicus". Null for all others.
- Sequence numbers are 1-indexed and global across the entire argument.
- Preserve all text verbatim — no summarization, paraphrasing, or editing.
"""

# ---------------------------------------------------------------------------
# Pydantic models — copied from RESEARCH.md Pattern 4 exactly
# ---------------------------------------------------------------------------


class ParsedUtterance(BaseModel):
    sequence: int
    raw_speaker_label: Optional[str]
    text: str
    is_stage_direction: bool
    section_hint: Optional[str]


class ParseResponse(BaseModel):
    utterances: list[ParsedUtterance]


# ---------------------------------------------------------------------------
# Inner LLM call — instructor handles Pydantic schema validation retries
# ---------------------------------------------------------------------------


async def call_llm_parse(pages_text: str) -> ParseResponse:
    """
    Call the Anthropic API via instructor to parse transcript text.

    Structural failures (Pydantic schema mismatch) are retried up to
    max_retries=2 times by instructor. If schema mismatch persists beyond
    that, InstructorRetryException is raised and must be caught by the
    caller (parse command) — it indicates a structural failure, not a
    transient one (PIPE-06).

    Args:
        pages_text: Full transcript text to parse.

    Returns:
        ParseResponse with list of ParsedUtterance objects.

    Raises:
        instructor.InstructorRetryException: Schema mismatch persisted > 2 retries.
        anthropic.BadRequestError: Invalid request (HTTP 400) — structural failure.
        anthropic.RateLimitError: Rate limited (HTTP 429) — caught by outer tenacity.
        anthropic.APIConnectionError: Network error — caught by outer tenacity.
    """
    # Lazy init — keeps import side-effect-free when no API key is present.
    # AsyncAnthropic(max_retries=0): tenacity owns transient retries (Pitfall 4).
    aclient = instructor.from_anthropic(
        anthropic.AsyncAnthropic(max_retries=0),
        mode=instructor.Mode.ANTHROPIC_TOOLS,
    )
    return await aclient.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=8192,
        max_retries=2,   # instructor retries on Pydantic validation failure — structural only
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": pages_text}],
        response_model=ParseResponse,
    )


# ---------------------------------------------------------------------------
# Outer tenacity wrapper — handles transient API errors only
# ---------------------------------------------------------------------------


@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def parse_with_llm(pages_text: str) -> ParseResponse:
    """
    Parse transcript text via LLM with two-layer retry strategy.

    Outer layer (this function): tenacity retries on transient errors only:
      - anthropic.RateLimitError (HTTP 429): exponential backoff, max 5 attempts
      - anthropic.APIConnectionError (network): exponential backoff, max 5 attempts

    Inner layer (call_llm_parse): instructor retries on schema validation failures:
      - Up to 2 structural retries if Pydantic validation fails

    Structural failures (InstructorRetryException, BadRequestError) are NOT
    retried by tenacity — they must be caught and handled by the caller.

    Args:
        pages_text: Full transcript text (D-05: entire session as one call).

    Returns:
        ParseResponse with list of ParsedUtterance objects.

    Raises:
        instructor.InstructorRetryException: Structural LLM failure — set
            pipeline_run.status="failed" and failure_reason.
        anthropic.BadRequestError: Invalid request — structural failure.
        anthropic.RateLimitError: Still failing after 5 tenacity retries.
        anthropic.APIConnectionError: Still failing after 5 tenacity retries.
    """
    return await call_llm_parse(pages_text)
