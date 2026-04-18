from __future__ import annotations

import csv
import io
import json
import re
import secrets
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import OcrImport, ScheduleImport, User, UserRole
from ..services.document_normalization_service import normalize_ocr_payload_document, normalize_xlsx_document
from ..services.import_service import confirm_import, process_import_file
from ..utils.auth import get_password_hash
from ..utils.dependencies import require_admin
from .admin_import_schemas import (
    ApplyToStagingResponse,
    ConfirmDocumentImportResponse,
    CreateMissingUsersRequest,
    CreateMissingUsersResponse,
    NormalizedPreviewResponse,
    ParseDocumentResponse,
    ParseOcrPayloadRequest,
)

router = APIRouter(prefix="/admin/imports", tags=["Admin Document Imports"])


def _summarize_document(doc: Dict[str, Any], ocr_import_id: str) -> ParseDocumentResponse:
    rows = doc.get("rows", [])
    return ParseDocumentResponse(
        document_import_id=ocr_import_id,
        source_type=doc.get("source_type", "unknown"),
        source_filename=doc.get("source_filename", "upload"),
        total_rows=len(rows),
        valid_rows=sum(1 for r in rows if r.get("match_status") in {"matched", "new_user_candidate", "ambiguous"}),
        invalid_rows=sum(1 for r in rows if r.get("match_status") == "invalid"),
        ambiguous_rows=sum(1 for r in rows if r.get("match_status") == "ambiguous"),
        new_user_candidates=sum(1 for r in rows if r.get("match_status") == "new_user_candidate"),
        warnings=list(doc.get("warnings") or []),
    )


def _persist_document_import(db: Session, normalized_doc: Dict[str, Any], created_by: int) -> OcrImport:
    ocr_import = OcrImport(
        status="draft",
        file_name=normalized_doc.get("source_filename"),
        file_type=normalized_doc.get("source_type"),
        source_origin="admin_document_pipeline",
        processing_strategy="document-normalizer-v2",
        raw_payload=normalized_doc,
        parsed_rows=normalized_doc.get("rows") or [],
        errors=normalized_doc.get("errors") or [],
        action_log=[],
        created_by=created_by,
        extracted_lines=len(normalized_doc.get("rows") or []),
        valid_lines=sum(1 for r in (normalized_doc.get("rows") or []) if r.get("match_status") == "matched"),
        ambiguous_lines=sum(1 for r in (normalized_doc.get("rows") or []) if r.get("match_status") == "ambiguous"),
        conflict_lines=sum(1 for r in (normalized_doc.get("rows") or []) if r.get("match_status") == "invalid"),
    )
    db.add(ocr_import)
    db.commit()
    db.refresh(ocr_import)
    return ocr_import


@router.post("/parse-document", response_model=ParseDocumentResponse, status_code=status.HTTP_201_CREATED)
async def parse_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    filename = file.filename or "upload"
    lower = filename.lower()

    if lower.endswith((".xlsx", ".xls")):
        normalized = normalize_xlsx_document(db, content, filename)
    elif lower.endswith(".json"):
        try:
            payload = json.loads(content.decode("utf-8"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="JSON inválido") from exc
        normalized = normalize_ocr_payload_document(db, payload, filename, source_type="pdf")
    else:
        raise HTTPException(status_code=415, detail="Formato suportado nesta fase: XLSX e payload OCR JSON")

    ocr_import = _persist_document_import(db, normalized, current_user.id)
    return _summarize_document(normalized, ocr_import.id)


@router.post("/parse-ocr-payload", response_model=ParseDocumentResponse, status_code=status.HTTP_201_CREATED)
def parse_ocr_payload(
    body: ParseOcrPayloadRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    normalized = normalize_ocr_payload_document(db, body.payload, body.source_filename, source_type="pdf")
    ocr_import = _persist_document_import(db, normalized, current_user.id)
    return _summarize_document(normalized, ocr_import.id)


@router.get("/{import_id}/normalized-preview", response_model=NormalizedPreviewResponse)
def get_normalized_preview(
    import_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    ocr_import = db.query(OcrImport).filter(OcrImport.id == import_id).first()
    if not ocr_import:
        raise HTTPException(status_code=404, detail="Importação documental não encontrada")
    doc = ocr_import.raw_payload or {}
    return NormalizedPreviewResponse(
        id=ocr_import.id,
        source_type=doc.get("source_type", ocr_import.file_type or "unknown"),
        source_filename=doc.get("source_filename", ocr_import.file_name or "upload"),
        detected_months=doc.get("detected_months") or [],
        raw_headers=doc.get("raw_headers") or [],
        normalized_headers=doc.get("normalized_headers") or [],
        warnings=doc.get("warnings") or [],
        errors=doc.get("errors") or [],
        rows=doc.get("rows") or [],
        metadata=doc.get("metadata") or {},
        created_at=ocr_import.created_at,
    )


@router.post("/{import_id}/apply-to-staging", response_model=ApplyToStagingResponse)
def apply_to_staging(
    import_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ocr_import = db.query(OcrImport).filter(OcrImport.id == import_id).first()
    if not ocr_import:
        raise HTTPException(status_code=404, detail="Importação documental não encontrada")
    doc = ocr_import.raw_payload or {}
    rows = doc.get("rows") or []
    if not rows:
        raise HTTPException(status_code=422, detail="Importação documental sem linhas")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["profissional", "data", "hora_inicio", "hora_fim", "total_horas", "observacoes", "origem"])
    for row in rows:
        if row.get("match_status") == "invalid":
            continue
        date_value = row.get("date_iso") or row.get("date_raw") or ""
        if date_value and "T" in date_value:
            date_value = date_value.split("T")[0]
        start_time_value = row.get("start_time_raw") or ""
        end_time_value = row.get("end_time_raw") or ""
        if (not start_time_value) and row.get("start_datetime"):
            try:
                start_time_value = datetime.fromisoformat(row["start_datetime"]).strftime("%H:%M")
            except (ValueError, TypeError):
                start_time_value = ""
        if (not end_time_value) and row.get("end_datetime"):
            try:
                end_time_value = datetime.fromisoformat(row["end_datetime"]).strftime("%H:%M")
            except (ValueError, TypeError):
                end_time_value = ""
        writer.writerow([
            row.get("professional_name_normalized") or row.get("professional_name_raw") or "",
            date_value,
            start_time_value,
            end_time_value,
            row.get("duration_hours") or "",
            " | ".join(row.get("validation_messages") or []),
            f"document-import:{import_id}",
        ])

    schedule_import = process_import_file(
        db=db,
        file_content=output.getvalue().encode("utf-8"),
        filename=f"normalized_{import_id}.csv",
        reference_period=None,
        source_description=f"document_import_id:{import_id}",
        imported_by_id=current_user.id,
    )

    action_log = list(ocr_import.action_log or [])
    action_log.append({"type": "apply_to_staging", "schedule_import_id": schedule_import.id, "at": datetime.utcnow().isoformat()})
    ocr_import.action_log = action_log
    db.commit()

    return ApplyToStagingResponse(
        document_import_id=import_id,
        schedule_import_id=schedule_import.id,
        total_rows=schedule_import.total_rows,
        valid_rows=schedule_import.valid_rows,
        warning_rows=schedule_import.warning_rows,
        invalid_rows=schedule_import.invalid_rows,
        duplicate_rows=schedule_import.duplicate_rows,
    )


@router.post("/{import_id}/create-missing-users", response_model=CreateMissingUsersResponse)
def create_missing_users(
    import_id: str,
    body: CreateMissingUsersRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ocr_import = db.query(OcrImport).filter(OcrImport.id == import_id).first()
    if not ocr_import:
        raise HTTPException(status_code=404, detail="Importação documental não encontrada")
    rows = (ocr_import.raw_payload or {}).get("rows") or []

    if body.create_for_row_indexes is not None and len(body.create_for_row_indexes) == 0:
        return CreateMissingUsersResponse(created_user_ids=[], skipped_rows=[])

    allowed_indexes = set(body.create_for_row_indexes or [])
    created: List[int] = []
    skipped: List[int] = []

    for row in rows:
        idx = int(row.get("source_row_index") or 0)
        if body.create_for_row_indexes and idx not in allowed_indexes:
            continue
        if row.get("match_status") != "new_user_candidate":
            continue

        name = (row.get("professional_name_normalized") or "").strip()
        if not name:
            skipped.append(idx)
            continue

        email_seed = re.sub(r"[^a-z0-9]+", ".", name.lower()).strip(".")
        email = f"{email_seed}.{secrets.token_hex(2)}@import.local"
        exists = db.query(User).filter(User.email == email).first()
        if exists:
            skipped.append(idx)
            continue

        user = User(
            email=email,
            name=name,
            hashed_password=get_password_hash(body.default_password),
            role=UserRole.MEDICO,
            is_admin=False,
            is_active=True,
            profile_notes=f"Criado via document import {import_id} por admin {current_user.id}",
        )
        db.add(user)
        db.flush()
        created.append(user.id)
        row["matched_user_id"] = user.id
        row["match_status"] = "matched"
        row.setdefault("validation_messages", []).append("Usuário criado via fluxo assistido")

    payload = dict(ocr_import.raw_payload or {})
    payload["rows"] = rows
    ocr_import.raw_payload = payload
    ocr_import.parsed_rows = rows
    ocr_import.valid_lines = sum(1 for r in rows if r.get("match_status") == "matched")
    ocr_import.ambiguous_lines = sum(1 for r in rows if r.get("match_status") == "ambiguous")
    ocr_import.action_log = list(ocr_import.action_log or []) + [
        {
            "type": "create_missing_users",
            "created_user_ids": created,
            "skipped_rows": skipped,
            "at": datetime.utcnow().isoformat(),
        }
    ]
    db.commit()
    return CreateMissingUsersResponse(created_user_ids=created, skipped_rows=skipped)


@router.post("/{import_id}/confirm", response_model=ConfirmDocumentImportResponse)
def confirm_document_import(
    import_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    ocr_import = db.query(OcrImport).filter(OcrImport.id == import_id).first()
    if not ocr_import:
        raise HTTPException(status_code=404, detail="Importação documental não encontrada")

    linked_schedule_id = None
    for event in reversed(ocr_import.action_log or []):
        if event.get("type") == "apply_to_staging" and event.get("schedule_import_id"):
            linked_schedule_id = int(event["schedule_import_id"])
            break
    if not linked_schedule_id:
        raise HTTPException(status_code=409, detail="Importação ainda não aplicada ao staging")

    schedule_import = db.query(ScheduleImport).filter(ScheduleImport.id == linked_schedule_id).first()
    if not schedule_import:
        raise HTTPException(status_code=404, detail="Staging vinculado não encontrado")

    try:
        _, created = confirm_import(db, linked_schedule_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConfirmDocumentImportResponse(
        document_import_id=import_id,
        schedule_import_id=linked_schedule_id,
        created_shifts=created,
    )
