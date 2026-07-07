"""
SQLAlchemy ORM models for SCOTUS Chat.

All 13 tables are defined here (including admin_jobs and argument_status_log
added in phases 15 and 22 respectively). Alembic is the sole DDL authority —
schema is managed exclusively via migrations in alembic/versions/.
"""

import enum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SAEnum,
    false,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Python enums — stored as database-level PG enum types via SAEnum
# ---------------------------------------------------------------------------


class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"  # legacy — never remove (PG cannot drop enum values)
    UNKNOWN = "UNKNOWN"
    PETITIONER = "PETITIONER"
    RESPONDENT = "RESPONDENT"
    AMICUS = "AMICUS"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class AdminJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AdminJobStep(str, enum.Enum):
    INGEST = "ingest"
    PARSE = "parse"
    RESOLVE = "resolve"


class ArgumentStatusEnum(str, enum.Enum):
    PIPELINE = "pipeline"
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Table 1: roles
# Lookup table for human roles (Associate Justice, Petitioner's Counsel, etc.)
# ---------------------------------------------------------------------------


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)  # "Associate Justice", "Petitioner's Counsel"


# ---------------------------------------------------------------------------
# Table 2: people
# Every speaker who appears in any argument — Justices, advocates, amicus
# ---------------------------------------------------------------------------


class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(300), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)
    bio_text = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    # Phase 9 additions — migration 0006
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    middle_name = Column(String(150), nullable=True)
    name_suffix = Column(String(50), nullable=True)
    # Phase 22 — migration 0013: appointment columns moved to court_tenures
    # Phase 18 — migration 0010
    is_justice = Column(Boolean, nullable=False, server_default=false())


# ---------------------------------------------------------------------------
# Table 3: court_tenures
# Service periods for Justices (seat, start date, end date)
# ---------------------------------------------------------------------------


class CourtTenure(Base):
    __tablename__ = "court_tenures"

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    seat = Column(String(100))  # e.g. "Associate Justice Seat 3"
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)  # null = currently active
    # Phase 22 — migration 0013: moved from people table (PEDIT-10)
    appointed_by = Column(String(200), nullable=True)
    appointing_president_party = Column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# Table 4: cases
# One row per docket number.
# Consolidated dockets (e.g. Obergefell 14-556/562/571/574) produce 4 case rows,
# all linked to the same argument row via case_arguments.
# ---------------------------------------------------------------------------


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True)
    docket_number = Column(String(50), nullable=False, unique=True)  # "14-556"
    docket_number_norm = Column(String(50), nullable=False)           # normalized form
    case_name = Column(String(500), nullable=False)
    term_year = Column(Integer, nullable=False)
    slug = Column(String(200), nullable=False, unique=True)           # URL slug


# ---------------------------------------------------------------------------
# Table 5: arguments
# One row per hearing session.  Multiple cases link here via case_arguments.
# ---------------------------------------------------------------------------


class Argument(Base):
    __tablename__ = "arguments"

    id = Column(Integer, primary_key=True)
    # Phase 19 (D-08): nullable — job-driven ingest leaves NULL instead of a synthetic date.
    argued_date = Column(Date, nullable=True)
    question_number = Column(Integer, nullable=False, default=1)  # Q1 or Q2
    # NULL = resolve not yet completed; retains its pipeline-completion meaning.
    # resolved_at IS NOT NULL means the pipeline resolve step has stamped this argument.
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    # Phase 11 (D-05): public visibility gate — replaces resolved_at as the public filter.
    # NULL = unpublished (hidden from /cases/); Non-NULL = published and publicly visible.
    # resolved_at retains its pipeline-completion meaning and is unchanged.
    published_at = Column(DateTime(timezone=True), nullable=True)
    # Phase 15 (D-01): explicit lifecycle status — pipeline/draft/published.
    # Backfilled from published_at/resolved_at by migration 0008.
    # The public /cases route continues to filter on published_at IS NOT NULL (D-03).
    status = Column(
        SAEnum(ArgumentStatusEnum, name="argument_status",
               values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=ArgumentStatusEnum.PIPELINE,
    )
    # Phase 19 (D-01): primary docket used at ingest time; NULL when operator did not supply one.
    # Used with question_number for the unique deduplication constraint (see __table_args__).
    source_docket = Column(String(50), nullable=True)
    # Phase 23 (D-MULTI-DOCKET): full ordered list of dockets for consolidated cases.
    # source_docket = source_dockets[0] — service keeps these in sync on every write.
    # UNIQUE constraint remains on source_docket (not this array) — dedup logic unchanged.
    source_dockets = Column(ARRAY(String(50)), nullable=True)
    # Phase 19 (D-07): raw cover extractor output written unconditionally by parse step.
    # Read by the job detail page to render "Extracted: [value]" hint text.
    cover_metadata = Column(JSONB, nullable=True)
    # cases linked via case_arguments M:M join table

    __table_args__ = (
        # Prevents duplicate argument rows when docket is known (D-01).
        # NULL semantics: multiple rows with source_docket = NULL do NOT violate
        # this constraint — deduplication only applies when docket is known.
        UniqueConstraint(
            "source_docket",
            "question_number",
            name="uq_arguments_source_docket_question",
        ),
    )


# ---------------------------------------------------------------------------
# Table 6: case_arguments
# M:M join table — one argument can cover multiple consolidated cases (INFRA-02).
# Composite PK (case_id, argument_id) prevents duplicate rows.
# ---------------------------------------------------------------------------


class CaseArgument(Base):
    """M:M join table — one argument can cover multiple consolidated cases (INFRA-02)."""

    __tablename__ = "case_arguments"

    case_id = Column(Integer, ForeignKey("cases.id"), primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), primary_key=True)
    is_lead = Column(Boolean, nullable=False, default=False)  # True for lead docket (14-556)


# ---------------------------------------------------------------------------
# Table 7: case_appearances
# Which people appeared in which cases (counsel of record, etc.)
# ---------------------------------------------------------------------------


class CaseAppearance(Base):
    """Which people appeared in which cases (counsel of record etc.)."""

    __tablename__ = "case_appearances"

    id = Column(Integer, primary_key=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=True)


# ---------------------------------------------------------------------------
# Table 8: argument_participants
# Which people spoke in which arguments (populated at parse time from raw labels).
# person_id is null until the Resolve step runs.
# ---------------------------------------------------------------------------


class ArgumentParticipant(Base):
    """Which people spoke in which arguments (populated at parse time from raw labels)."""

    __tablename__ = "argument_participants"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null until resolved
    raw_speaker_label = Column(String(200), nullable=False)
    side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False)
    # Phase 22 — migration 0013: TOC subtitle from cover extractor (PJOB-13)
    title = Column(String(500), nullable=True)


# ---------------------------------------------------------------------------
# Table 9: pipeline_runs
# One row per pipeline invocation.  Re-running any step produces a new row.
# Prior rows are never deleted until the new run is promoted.
# ---------------------------------------------------------------------------


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    step = Column(String(50), nullable=False)  # "ingest", "parse", "resolve"
    status = Column(
        SAEnum(PipelineRunStatus, name="pipeline_run_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=PipelineRunStatus.PENDING,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)    # local path to immutable PDF
    pdf_url = Column(String(1000), nullable=True)    # original download URL
    strategy = Column(String(100), nullable=True)    # "rule_based", "llm_corrective"
    prompt_version = Column(String(50), nullable=True)  # for schema version tracking


# ---------------------------------------------------------------------------
# Table 10: utterances
# One row per spoken turn or stage direction.
# BigInteger PK — could accumulate millions of rows over many arguments.
# person_id is null at parse time; populated by the Resolve step (Phase 2).
# pipeline_run_id links each row to the pipeline run that produced it (PIPE-04, PIPE-11).
# ---------------------------------------------------------------------------


class Utterance(Base):
    __tablename__ = "utterances"

    id = Column(BigInteger, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    pipeline_run_id = Column(Integer, ForeignKey("pipeline_runs.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    raw_speaker_label = Column(String(200), nullable=True)   # None for stage directions
    text = Column(Text, nullable=False)
    is_stage_direction = Column(Boolean, nullable=False, default=False)
    section_hint = Column(String(50), nullable=True)  # "petitioner"|"respondent"|"rebuttal"|"amicus"
    side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False, default=SideEnum.UNKNOWN)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null at parse time
    strategy = Column(String(100), nullable=False)   # PIPE-04: "rule_based" | "llm_corrective"

    __table_args__ = (
        UniqueConstraint(
            "argument_id",
            "pipeline_run_id",
            "sequence",
            name="uq_utterance_arg_run_seq",
        ),
        Index("ix_utterances_argument_id", "argument_id"),
        Index("ix_utterances_pipeline_run_id", "pipeline_run_id"),
    )


# ---------------------------------------------------------------------------
# Table 11: speaker_alias
# Maps normalized speaker labels to resolved people rows.
# Used by the Resolve step to match raw transcript labels to known people.
# ---------------------------------------------------------------------------


class SpeakerAlias(Base):
    __tablename__ = "speaker_alias"

    id = Column(Integer, primary_key=True)
    normalized_label = Column(String(300), nullable=False, unique=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Table 12: argument_status_log
# Audit log of argument status changes. One row per status transition.
# Seeded at migration 0012 with one row per existing argument (backfill).
# Minimal schema (D-06): no previous_status, notes, or triggered_by in v1.5.
# The status column binds to the existing argument_status PG enum type
# (name="argument_status") — it does NOT create a shadow type.
# ---------------------------------------------------------------------------


class ArgumentStatusLog(Base):
    __tablename__ = "argument_status_log"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    status = Column(
        SAEnum(ArgumentStatusEnum, name="argument_status",
               values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Table 13: admin_jobs
# Tracks operator-initiated pipeline jobs submitted via the admin UI.
# status and current_step use PG enums defined in migration 0003.
# argument_id is nullable FK — NULL until ingest creates the argument row (D-02).
# discrepancies is JSONB — read as a batch during fire-and-poll (D-03).
# ---------------------------------------------------------------------------


class AdminJob(Base):
    __tablename__ = "admin_jobs"

    id = Column(Integer, primary_key=True)
    status = Column(
        SAEnum(AdminJobStatus, name="admin_job_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=AdminJobStatus.PENDING,
    )
    current_step = Column(
        SAEnum(AdminJobStep, name="admin_job_step", values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=True)
    pdf_url = Column(Text, nullable=True)
    spaces_key = Column(Text, nullable=True)
    original_filename = Column(Text, nullable=True)
    # Run-start docket list (D-07 supersession, Phase 24 Plan 04): the full ordered
    # list of docket pills submitted at run creation, before Argument exists.
    # Carried through to Argument.source_dockets by the ingest subprocess.
    source_dockets = Column(ARRAY(String(50)), nullable=True)
    discrepancies = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
