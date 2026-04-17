"""Schemas Pydantic para importação de escala base."""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from ..models import ImportStatus, RowStatus


# ─── ScheduleImportRow ────────────────────────────────────────────────────────

class ScheduleImportRowResponse(BaseModel):
    id: int
    import_id: int
    row_number: int

    raw_professional: Optional[str] = None
    raw_date: Optional[str] = None
    raw_start_time: Optional[str] = None
    raw_end_time: Optional[str] = None
    raw_total_hours: Optional[str] = None
    raw_observations: Optional[str] = None
    raw_source: Optional[str] = None

    agent_id: Optional[int] = None
    normalized_start: Optional[datetime] = None
    normalized_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    is_overnight: bool = False
    is_standard_shift: bool = False

    row_status: RowStatus
    confidence_score: Optional[float] = None
    parse_status: str = "ok"
    match_status: str = "unmatched"
    validation_status: str = "pending"
    issues: Optional[List[str]] = None
    is_duplicate: bool = False
    has_overlap: bool = False
    created_shift_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_issues(cls, obj) -> "ScheduleImportRowResponse":
        data = {
            col.name: getattr(obj, col.name)
            for col in obj.__table__.columns
        }
        raw_issues = data.pop("issues", None)
        parsed_issues: Optional[List[str]] = None
        if raw_issues:
            try:
                parsed_issues = json.loads(raw_issues)
            except (ValueError, TypeError):
                parsed_issues = [raw_issues]
        return cls(**data, issues=parsed_issues)


# ─── ScheduleImport ───────────────────────────────────────────────────────────

class ScheduleImportResponse(BaseModel):
    id: int
    filename: str
    reference_period: Optional[str] = None
    source_description: Optional[str] = None
    status: ImportStatus
    total_rows: int
    valid_rows: int
    warning_rows: int
    invalid_rows: int
    duplicate_rows: int
    imported_by: int
    confirmed_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleImportDetailResponse(ScheduleImportResponse):
    rows: List[ScheduleImportRowResponse] = []

    class Config:
        from_attributes = True


class ScheduleImportSummary(BaseModel):
    import_id: int
    filename: str
    reference_period: Optional[str] = None
    status: ImportStatus
    total_rows: int
    valid_rows: int
    warning_rows: int
    invalid_rows: int
    duplicate_rows: int
    importable_rows: int   # valid + warning (non-duplicate)
    confirmed: bool
    confirmed_at: Optional[datetime] = None
