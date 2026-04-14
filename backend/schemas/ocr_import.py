from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OcrRow(BaseModel):
    row_id: str
    raw_text: str
    parsed_name: str | None
    matched_user_id: str | None
    match_score: float | None
    candidates: list[dict[str, Any]]
    start_time: str | None   # ISO 8601
    end_time: str | None     # ISO 8601
    location: str | None
    row_status: str          # "ok", "warning", "error"


class OcrImportCreate(BaseModel):
    """Vazio — o registro é criado pelo servidor ao receber o upload."""


class OcrImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    file_name: str | None
    file_type: str | None
    parsed_rows: list[OcrRow] | None
    errors: list[dict[str, Any]] | None
    created_by: int | None
    confirmed_by: int | None
    created_at: datetime
    confirmed_at: datetime | None


class OcrImportPatchRow(BaseModel):
    """Payload para edição manual de uma linha específica."""

    parsed_name: str | None = None
    matched_user_id: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    location: str | None = None
    row_status: str | None = None
