"""
SQLAlchemy ORM models for SCOTUS Chat.

All 13 tables are defined here (including admin_jobs and argument_status_log
added in phases 15 and 22 respectively). Alembic is the sole DDL authority —
schema is managed exclusively via migrations in alembic/versions/.
"""

import enum

from api.domain.trust import TrustTier
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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


class ImportRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"


class ImportSource(str, enum.Enum):
    OPERATOR = "operator"
    CORPUS = "corpus"
    PDF_PIPELINE = "pdf_pipeline"
    SEED = "seed"


class ImportMethod(str, enum.Enum):
    MANUAL = "manual"
    DIRECT = "direct"
    NORMALIZED = "normalized"
    RULE_BASED = "rule_based"
    LLM_CORRECTIVE = "llm_corrective"


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
    PIPELINE = "pipeline"  # dead-but-permanent after migration 0027 (PG cannot drop enum values)
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"
    CANDIDATE = "candidate"  # Phase 48 (D-01): the new born state, replaces PIPELINE


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
    # Phase 27 — migration 0016
    birthdate = Column(Date, nullable=True)
    # Phase 39 — migration 0023
    death_date = Column(Date, nullable=True)
    # Phase 29 — migration 0017: Oyez/ConvoKit external speaker ID (historical corpus import)
    oyez_speaker_id = Column(String(100), nullable=True)
    # Phase 38 — migration 0022: durable review flag + independently-persisted
    # extraction provenance for the Full Name vs. name-parts authority rework
    # (D-04, D-10-D-12, D-14-D-18). name_needs_review surfaces the People
    # directory's `Name review` attention filter for any full_name this
    # migration (or later pipeline/import extraction) could not confidently
    # split into structured parts. name_extraction_metadata persists
    # independently of operator-edited name parts — an operator edit never
    # clears or rewrites it, and it is never used to overwrite an existing
    # operator value.
    name_needs_review = Column(Boolean, nullable=False, server_default=false())
    name_extraction_metadata = Column(JSONB, nullable=True)


# ---------------------------------------------------------------------------
# Table 3: court_tenures
# Service periods for Justices (office, start date, end date)
#
# Phase 37 (D-01, D-17): office is a binary Chief/Associate value — the
# legacy free-text `seat` column (e.g. "Associate Justice Seat 3") was
# renamed to `office` by migration 0020 and constrained to exactly the two
# canonical values below by migration 0021's named CHECK constraint
# (ck_court_tenures_office) + NOT NULL. There is no `seat` compatibility
# alias anywhere in the active model (D-17).
# ---------------------------------------------------------------------------

OFFICE_CHIEF = "chief"
OFFICE_ASSOCIATE = "associate"
VALID_OFFICES = (OFFICE_CHIEF, OFFICE_ASSOCIATE)

# Canonical -> formal display title (D-15). Editor labels stay compact
# ("Chief"/"Associate", D-14) — this mapping is only for read-only summaries
# and popovers that must render the formal "Chief Justice"/"Associate
# Justice" wording.
OFFICE_TITLES = {
    OFFICE_CHIEF: "Chief Justice",
    OFFICE_ASSOCIATE: "Associate Justice",
}


def office_title(office: str) -> str:
    """Return the formal display title for a canonical office value (D-15).

    Exhaustive over VALID_OFFICES — raises KeyError for any other input.
    An office value outside VALID_OFFICES reaching this helper indicates a
    data-integrity bug the DB CHECK constraint (ck_court_tenures_office)
    should already have prevented; it must not be silently coerced.
    """
    return OFFICE_TITLES[office]


# Phase 39 (D-01, D-15): the reason a tenure ended — a constrained enum with
# exactly three values, nullable PERMANENTLY (D-02: an open/active tenure
# never has a reason, and a few historical rows have no recorded value).
# Named reason_left-specific (not a generic REASON_*/VALID_REASONS name) to
# avoid colliding with any future unrelated "reason X" enum (39-RESEARCH.md
# Pitfall 7).
REASON_RETIRED = "retired"
REASON_DIED = "died"
REASON_PROMOTED = "promoted"
VALID_REASONS_LEFT = (REASON_RETIRED, REASON_DIED, REASON_PROMOTED)

# Canonical -> formal display title (D-15), locked by 39-UI-SPEC.md's
# Copywriting Contract.
REASON_LEFT_TITLES = {
    REASON_RETIRED: "Retired",
    REASON_DIED: "Died in office",
    REASON_PROMOTED: "Promoted",
}


def reason_left_title(reason: str) -> str:
    """Return the formal display title for a canonical reason_left value (D-15).

    Exhaustive over VALID_REASONS_LEFT — raises KeyError for any other input,
    including None. An out-of-vocabulary reason_left value reaching this
    helper indicates a data-integrity bug the DB CHECK constraint
    (ck_court_tenures_reason_left) should already have prevented; it must
    not be silently coerced. Callers render no reason line for a null
    reason_left (D-02) without calling this helper at all.
    """
    return REASON_LEFT_TITLES[reason]


class CourtTenure(Base):
    __tablename__ = "court_tenures"
    __table_args__ = (
        CheckConstraint(
            "office IN ('chief', 'associate')",
            name="ck_court_tenures_office",
        ),
        CheckConstraint(
            "reason_left IS NULL OR reason_left IN ('retired', 'died', 'promoted')",
            name="ck_court_tenures_reason_left",
        ),
    )

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=False)
    office = Column(String(100), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date, nullable=True)  # null = currently active
    # Phase 22 — migration 0013: moved from people table (PEDIT-10)
    appointed_by = Column(String(200), nullable=True)
    appointing_president_party = Column(String(50), nullable=True)
    # Phase 39 — migration 0024 (D-01/D-02): permanently nullable — an open
    # tenure and a tenure with no recorded reason are both storable. The ORM
    # CheckConstraint above is self-documentation only; Alembic remains the
    # sole DDL authority (CLAUDE.md).
    reason_left = Column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# Table 4: cases
# One row per docket number.
# Consolidated dockets (e.g. Obergefell 14-556/562/571/574) produce 4 case rows,
# all linked to the same argument row via case_arguments.
# ---------------------------------------------------------------------------


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        # Migration 0018: historical docket numbers recycle across October
        # Terms (e.g. docket "71" is a different, unrelated case in nearly
        # a dozen different terms) -- modern dockets embed the term and stay
        # unique on their own, so this composite constraint is a superset,
        # not a narrowing, of the old bare UNIQUE(docket_number).
        UniqueConstraint(
            "docket_number", "term_year", name="uq_cases_docket_number_term_year"
        ),
    )

    id = Column(Integer, primary_key=True)
    docket_number = Column(String(50), nullable=False)  # "14-556"
    docket_number_norm = Column(String(50), nullable=False)           # normalized form
    case_name = Column(String(500), nullable=False)
    term_year = Column(Integer, nullable=False)
    slug = Column(String(200), nullable=False, unique=True)           # URL slug
    # Phase 29 — migration 0017: Oyez external case ID (historical corpus import)
    oyez_case_id = Column(String(50), nullable=True)


# ---------------------------------------------------------------------------
# Table 5: arguments
# One row per hearing session.  Multiple cases link here via case_arguments.
# ---------------------------------------------------------------------------


class Argument(Base):
    __tablename__ = "arguments"

    id = Column(Integer, primary_key=True)
    # Phase 19 (D-08): nullable — job-driven ingest leaves NULL instead of a synthetic date.
    argued_date = Column(Date, nullable=True)
    # Migration 0019 (AEDIT-04): nullable, no default — blank = NULL = "unknown",
    # parity with argued_date above (not a mandatory Q1/Q2 value anymore).
    question_number = Column(Integer, nullable=True)
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
        default=ArgumentStatusEnum.CANDIDATE,
    )
    # Phase 48 (D-06/D-07): materialized floor rollup of this argument's
    # constituent utterances/participants, recomputed in-transaction by
    # every writer via api.services.trust.recompute_argument_tier. NOT NULL
    # with server_default='uncertain' (migration 0027) — fail-closed, no
    # in-migration backfill (the project DB is disposable per operator lean).
    trust_tier = Column(
        SAEnum(TrustTier, name="trust_tier", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        server_default="uncertain",
        default=TrustTier.UNCERTAIN,
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
    # Phase 29 — migration 0017: Oyez/ConvoKit external transcript ID (historical corpus import)
    oyez_transcript_id = Column(String(50), nullable=True)
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
    # Phase 44 D-05 — migration 0025: renamed title -> descriptor (full-stack rename)
    descriptor = Column(String(500), nullable=True)


# ---------------------------------------------------------------------------
# Table 9: import_run
# One row per import unit (declared source + method).  Re-running any step
# produces a new row.  Prior rows are never deleted until the new run is
# promoted.  Phase 47: generalizes the old PDF-pipeline-only run model —
# source/method are declared explicitly at write time by every writer
# (corpus, pdf_pipeline), never defaulted or inferred at read time.
# ---------------------------------------------------------------------------


class ImportRun(Base):
    __tablename__ = "import_run"

    id = Column(Integer, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    step = Column(String(50), nullable=False)  # "ingest", "parse", "resolve"
    status = Column(
        SAEnum(ImportRunStatus, name="import_run_status", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=ImportRunStatus.PENDING,
    )
    # Phase 47 (D-02): declared explicitly by every writer, no default —
    # provenance is correct by construction on every new row, never inferred.
    source = Column(
        SAEnum(ImportSource, name="import_source", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    method = Column(
        SAEnum(ImportMethod, name="import_method", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )
    # Phase 47 (D-04 in provenance-and-trust-model.md / PROV-04): dual-write
    # of external-source lineage (e.g. the ConvoKit conversation id) for
    # source=corpus rows. Argument.oyez_transcript_id remains the live
    # dedup key / public API field — this is an addition, not a relocation.
    external_id = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)    # local path to immutable PDF
    pdf_url = Column(String(1000), nullable=True)    # original download URL
    prompt_version = Column(String(50), nullable=True)  # for schema version tracking


# ---------------------------------------------------------------------------
# Table 10: utterances
# One row per spoken turn or stage direction.
# BigInteger PK — could accumulate millions of rows over many arguments.
# person_id is null at parse time; populated by the Resolve step (Phase 2).
# import_run_id links each row to the import run that produced it (PIPE-04,
# PIPE-11). Phase 47 (D-05): the per-row `strategy` column is dropped —
# utterances inherit provenance from their parent import_run's source/method.
# ---------------------------------------------------------------------------


class Utterance(Base):
    __tablename__ = "utterances"

    id = Column(BigInteger, primary_key=True)
    argument_id = Column(Integer, ForeignKey("arguments.id"), nullable=False)
    import_run_id = Column(Integer, ForeignKey("import_run.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    raw_speaker_label = Column(String(200), nullable=True)   # None for stage directions
    text = Column(Text, nullable=False)
    is_stage_direction = Column(Boolean, nullable=False, default=False)
    section_hint = Column(String(50), nullable=True)  # "petitioner"|"respondent"|"rebuttal"|"amicus"
    side = Column(SAEnum(SideEnum, name="side", values_callable=lambda e: [x.value for x in e]), nullable=False, default=SideEnum.UNKNOWN)
    person_id = Column(Integer, ForeignKey("people.id"), nullable=True)  # null at parse time

    __table_args__ = (
        UniqueConstraint(
            "argument_id",
            "import_run_id",
            "sequence",
            name="uq_utterance_arg_run_seq",
        ),
        Index("ix_utterances_argument_id", "argument_id"),
        Index("ix_utterances_import_run_id", "import_run_id"),
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
# Minimal schema (D-06 of Phase 15): no previous_status, notes, or
# triggered_by in v1.5. Phase 48 D-15 deliberately revisits that minimalism:
# a publish-block override IS a status transition, so its audit fields
# belong on the row that transition already writes rather than a second
# table. override_reason/trust_tier_at_transition are both nullable —
# every non-override transition (CANDIDATE-at-birth, DRAFT, PUBLISHED,
# UNPUBLISHED without an override) legitimately carries NULL here.
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
    # Phase 48 (D-15, D-17): non-empty free text required server-side only
    # when this row records a publish override past the UNCERTAIN gate.
    override_reason = Column(Text, nullable=True)
    # Phase 48 (D-15): the argument's trust_tier at the moment of this
    # transition, populated only for override rows. Binds to the trust_tier
    # PG enum type (migration 0027) — does NOT create a shadow type.
    trust_tier_at_transition = Column(
        SAEnum(TrustTier, name="trust_tier", values_callable=lambda e: [x.value for x in e]),
        nullable=True,
    )


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
