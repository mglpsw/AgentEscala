"""Schemas da camada documental de importação (XLSX/PDF/OCR)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DetectedMonth(BaseModel):
    month: int
    year: int
    label: str
    source_sheet: Optional[str] = None
    confidence: float = 0.0


class NormalizedShiftRowResponse(BaseModel):
    source_sheet: Optional[str] = None
    source_page: Optional[int] = None
    source_row_index: int
    source_layout_type: Optional[str] = None
    day_group_id: Optional[str] = None
    competency_month: Optional[int] = None
    competency_year: Optional[int] = None
    professional_name_raw: Optional[str] = None
    professional_name_normalized: Optional[str] = None
    canonical_name: Optional[str] = None
    alias_applied: bool = False
    crm_raw: Optional[str] = None
    crm_normalized: Optional[str] = None
    crm_detected: Optional[str] = None
    crm_confidence: float = 0.0
    specialty_raw: Optional[str] = None
    location_raw: Optional[str] = None
    unit_raw: Optional[str] = None
    date_raw: Optional[str] = None
    date_iso: Optional[str] = None
    weekday_raw: Optional[str] = None
    shift_label_raw: Optional[str] = None
    shift_kind: Optional[str] = None
    schedule_pattern_type: Optional[str] = None
    start_time_raw: Optional[str] = None
    end_time_raw: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    duration_hours: Optional[float] = None
    role_raw: Optional[str] = None
    notes: Optional[str] = None
    confidence: float = 0.0
    match_status: str
    matched_user_id: Optional[int] = None
    suggested_existing_user_id: Optional[int] = None
    suggested_profile_enrichment: Optional[Dict[str, Any]] = None
    multiple_professionals_detected: bool = False
    grouped_day_validation: List[str] = Field(default_factory=list)
    llm_fallback_recommended: bool = False
    validation_messages: List[str] = Field(default_factory=list)


class NormalizedPreviewResponse(BaseModel):
    id: str
    source_type: str
    source_filename: str
    detected_months: List[DetectedMonth] = Field(default_factory=list)
    raw_headers: List[str] = Field(default_factory=list)
    normalized_headers: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    rows: List[NormalizedShiftRowResponse] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class ParseDocumentResponse(BaseModel):
    document_import_id: str
    source_type: str
    source_filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    ambiguous_rows: int
    new_user_candidates: int
    warnings: List[str] = Field(default_factory=list)


class ParseOcrPayloadRequest(BaseModel):
    source_filename: str = "ocr_payload.json"
    payload: Dict[str, Any]


class ApplyToStagingResponse(BaseModel):
    document_import_id: str
    schedule_import_id: int
    total_rows: int
    valid_rows: int
    warning_rows: int
    invalid_rows: int
    duplicate_rows: int


class CreateMissingUsersRequest(BaseModel):
    create_for_row_indexes: Optional[List[int]] = None
    default_password: str = "Alterar123!"


class CreateMissingUsersResponse(BaseModel):
    created_user_ids: List[int] = Field(default_factory=list)
    skipped_rows: List[int] = Field(default_factory=list)


class ConfirmDocumentImportResponse(BaseModel):
    document_import_id: str
    schedule_import_id: int
    created_shifts: int
