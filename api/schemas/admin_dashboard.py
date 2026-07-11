"""Pydantic v2 response models for the admin dashboard stat-card / Needs-Attention API.

Phase 28 additions (DASH-01, DASH-03):
  - ArgumentStats     — Arguments stat-card counts (total/published/draft/unpublished)
  - RecentDraft       — one row in the Arguments "recent drafts" sub-list
  - PeopleStats       — People stat-card counts (total/incomplete), combined both tabs
  - IncompletePerson  — one row in the People "Needs Attention" sub-list (combined tabs)
  - TenureGapJustice  — one row in the Justices "tenure gap" sub-list (Bench only)
  - PipelineStats     — Pipeline runs stat-card (30-day recent_count + unbounded last_activity_at)
  - UtteranceCount    — Utterances stat-card (single total)

All seven models are plain BaseModel classes (no from_attributes) — every service
function that backs them returns a hand-built dict, not an ORM row, so there is no
attribute-mapped model to validate against (mirrors api/schemas/admin_arguments.py's
convention for its non-ORM response shapes).

Apolitical constraint: these schemas carry only counts and identifying labels
(id, full_name, case_name, docket_number, missing-field labels) — no derived-insight,
outcome, or vote-margin field, and no external case-outcome-database identifier,
appears anywhere here.
"""

import datetime
from typing import Optional

from pydantic import BaseModel


class ArgumentStats(BaseModel):
    total: int
    published: int
    draft: int
    unpublished: int


class RecentDraft(BaseModel):
    id: int
    case_name: str
    docket_number: str


class PeopleStats(BaseModel):
    total: int
    incomplete: int


class IncompletePerson(BaseModel):
    id: int
    full_name: str
    missing: list[str]


class TenureGapJustice(BaseModel):
    id: int
    full_name: str


class PipelineStats(BaseModel):
    recent_count: int
    last_activity_at: Optional[datetime.datetime]


class UtteranceCount(BaseModel):
    total: int
