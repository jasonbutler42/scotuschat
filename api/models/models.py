"""
SQLAlchemy ORM models for SCOTUS Chat.

All 10 tables are defined here. Alembic is the sole DDL authority —
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
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Python enums — stored as database-level PG enum types via SAEnum
# ---------------------------------------------------------------------------


class SideEnum(str, enum.Enum):
    BENCH = "BENCH"
    ADVOCATE = "ADVOCATE"
    UNKNOWN = "UNKNOWN"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


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
    argued_date = Column(Date, nullable=False)
    question_number = Column(Integer, nullable=False, default=1)  # Q1 or Q2
    # cases linked via case_arguments M:M join table


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
    side = Column(SAEnum(SideEnum, name="side"), nullable=False)


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
        SAEnum(PipelineRunStatus, name="pipeline_run_status"),
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
    side = Column(SAEnum(SideEnum, name="side"), nullable=False, default=SideEnum.UNKNOWN)
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
