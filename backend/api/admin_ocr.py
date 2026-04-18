from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..config.settings import settings
from ..models import User
from ..services.ocr.agent_router_client import OcrAgentRouterError, extract_text_via_agent_router
from ..services.ocr.calibration_service import OcrCalibrationService
from ..utils.dependencies import require_admin

router = APIRouter(prefix="/admin/ocr", tags=["Admin OCR"])
logger = logging.getLogger("agentescala.admin_ocr")


class OcrCalibrationRow(BaseModel):
    raw_line: str
    date: str | None = None
    weekday: str | None = None
    shift_label: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    professional_name: str | None = None
    crm_number: str | None = None
    match_status: str
    matched_user_id: int | None = None
    match_reason: str
    matched_name: str | None = None


class OcrCalibrationResponse(BaseModel):
    filename: str
    total_rows: int
    matched_rows: int
    ambiguous_rows: int
    unmatched_rows: int
    rows: list[OcrCalibrationRow]


@router.post("/calibration/preview", response_model=OcrCalibrationResponse)
async def calibration_preview(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    filename = file.filename or "upload"
    logger.info("ocr_calibration_preview_started filename=%s", filename)
    allowed_ext = (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff")
    if not filename.lower().endswith(allowed_ext):
        logger.warning("ocr_calibration_preview_rejected_invalid_format filename=%s", filename)
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato não suportado para calibração OCR. Use PDF ou imagem.",
        )

    if not settings.FEATURE_OCR_REMOTE_IMPORT:
        logger.warning("ocr_calibration_preview_blocked_feature_disabled filename=%s", filename)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feature OCR remoto desativada. Ative FEATURE_OCR_REMOTE_IMPORT para usar a calibração.",
        )

    content = await file.read()
    if not content:
        logger.warning("ocr_calibration_preview_empty_file filename=%s", filename)
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    try:
        result = extract_text_via_agent_router(
            file_content=content,
            filename=filename,
            base_url=settings.OCR_API_BASE_URL,
            timeout_seconds=settings.OCR_API_TIMEOUT_SECONDS,
            verify_ssl=settings.OCR_API_VERIFY_SSL,
        )
    except OcrAgentRouterError as exc:
        logger.warning("ocr_calibration_preview_remote_error filename=%s reason=%s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Não foi possível extrair texto do arquivo no OCR remoto. Tente novamente.",
        ) from exc

    candidates = OcrCalibrationService.parse_raw_text(result["raw_text"])
    rows: list[OcrCalibrationRow] = []
    matched = ambiguous = unmatched = 0

    for item in candidates:
        match = OcrCalibrationService.match_candidate(db, item)
        status_value = match["status"]
        if status_value == "matched":
            matched += 1
        elif status_value == "ambiguous":
            ambiguous += 1
        else:
            unmatched += 1

        rows.append(
            OcrCalibrationRow(
                raw_line=item.raw_line,
                date=item.date,
                weekday=item.weekday,
                shift_label=item.shift_label,
                start_time=item.start_time,
                end_time=item.end_time,
                professional_name=item.professional_name,
                crm_number=item.crm_number,
                match_status=status_value,
                matched_user_id=match.get("user_id"),
                match_reason=match["match_reason"],
                matched_name=match.get("matched_name"),
            )
        )

    logger.info(
        "ocr_calibration_preview_completed filename=%s total=%s matched=%s ambiguous=%s unmatched=%s",
        filename,
        len(rows),
        matched,
        ambiguous,
        unmatched,
    )
    return OcrCalibrationResponse(
        filename=filename,
        total_rows=len(rows),
        matched_rows=matched,
        ambiguous_rows=ambiguous,
        unmatched_rows=unmatched,
        rows=rows,
    )
