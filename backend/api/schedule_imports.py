"""Endpoints de importação de escala base.

Todos os endpoints são protegidos por JWT e requerem papel admin.
"""
from __future__ import annotations

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models.models import RowStatus, ScheduleImport, ScheduleImportRow
from ..services.import_service import confirm_import, export_issues_csv, process_import_file
from ..utils.dependencies import require_admin
from .import_schemas import (
    ScheduleImportDetailResponse,
    ScheduleImportResponse,
    ScheduleImportRowResponse,
    ScheduleImportSummary,
)

router = APIRouter(prefix="/schedule-imports", tags=["Importação de Escala"])


@router.post(
    "/",
    response_model=ScheduleImportSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Importar arquivo de escala base (admin)",
)
async def upload_schedule(
    file: UploadFile = File(..., description="Arquivo CSV ou XLSX com a escala anterior"),
    reference_period: Optional[str] = Form(None, description="Período de referência, ex.: '2026-03'"),
    source_description: Optional[str] = Form(None, description="Descrição da origem do arquivo"),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Faz upload e processa um arquivo de escala anterior.

    Aceita CSV (separador , ou ;) e XLSX.
    Campos esperados no cabeçalho (case-insensitive, aliases aceitos):
      profissional, data, hora_inicio, hora_fim, [total_horas], [observacoes], [origem]
    """
    allowed = {
        "text/csv", "text/plain",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }
    content_type = (file.content_type or "").split(";")[0].strip()
    filename = file.filename or "upload"
    if content_type not in allowed and not (filename.endswith(".csv") or filename.endswith(".xlsx")):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Somente arquivos CSV e XLSX são aceitos",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")

    try:
        sched_import = process_import_file(
            db=db,
            file_content=content,
            filename=filename,
            reference_period=reference_period,
            source_description=source_description,
            imported_by_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return _to_summary(sched_import)


@router.get(
    "/",
    response_model=List[ScheduleImportResponse],
    summary="Listar importações realizadas (admin)",
)
def list_imports(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Lista todos os lotes de importação, do mais recente ao mais antigo."""
    return (
        db.query(ScheduleImport)
        .order_by(ScheduleImport.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/{import_id}",
    response_model=ScheduleImportDetailResponse,
    summary="Detalhe de uma importação (admin)",
)
def get_import(
    import_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    sched_import = db.query(ScheduleImport).filter(ScheduleImport.id == import_id).first()
    if not sched_import:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importação não encontrada")

    rows = db.query(ScheduleImportRow).filter(
        ScheduleImportRow.import_id == import_id
    ).order_by(ScheduleImportRow.row_number).all()

    data = ScheduleImportDetailResponse.from_orm(sched_import)
    data.rows = [ScheduleImportRowResponse.from_orm_with_issues(r) for r in rows]
    return data


@router.get(
    "/{import_id}/summary",
    response_model=ScheduleImportSummary,
    summary="Resumo de uma importação (admin)",
)
def get_import_summary(
    import_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    sched_import = db.query(ScheduleImport).filter(ScheduleImport.id == import_id).first()
    if not sched_import:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importação não encontrada")
    return _to_summary(sched_import)


@router.get(
    "/{import_id}/rows",
    response_model=List[ScheduleImportRowResponse],
    summary="Linhas de uma importação com filtro opcional de status (admin)",
)
def list_import_rows(
    import_id: int,
    row_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 500,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Lista as linhas de uma importação.
    Use `?row_status=invalid` ou `?row_status=warning` para filtrar.
    """
    _assert_import_exists(db, import_id)
    q = db.query(ScheduleImportRow).filter(ScheduleImportRow.import_id == import_id)
    if row_status:
        try:
            status_enum = RowStatus(row_status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"row_status inválido. Valores aceitos: {[s.value for s in RowStatus]}",
            )
        q = q.filter(ScheduleImportRow.row_status == status_enum)
    rows = q.order_by(ScheduleImportRow.row_number).offset(skip).limit(limit).all()
    return [ScheduleImportRowResponse.from_orm_with_issues(r) for r in rows]


@router.post(
    "/{import_id}/confirm",
    response_model=ScheduleImportSummary,
    summary="Confirmar importação e criar turnos normalizados (admin)",
)
def confirm_schedule_import(
    import_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """Converte linhas válidas/warning (não duplicadas) em Shifts reais.

    Linhas inválidas ou sem agente resolvido são ignoradas silenciosamente.
    Sobreposições com turnos já existentes são registradas mas não bloqueiam o restante.
    """
    _assert_import_exists(db, import_id)
    try:
        sched_import, created = confirm_import(db, import_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    summary = _to_summary(sched_import)
    # Injeta número de turnos criados como nota extra no source_description temporariamente
    # (não persiste — apenas no response)
    summary_dict = summary.model_dump()
    summary_dict["source_description"] = (
        (sched_import.source_description or "")
        + f" [Turnos criados nesta confirmação: {created}]"
    ).strip()
    return ScheduleImportSummary(**summary_dict)


@router.get(
    "/{import_id}/report",
    summary="Exportar relatório de inconsistências em CSV (admin)",
)
def export_issues_report(
    import_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    """Baixa CSV com linhas que apresentaram alertas ou erros."""
    _assert_import_exists(db, import_id)
    csv_bytes = export_issues_csv(db, import_id)
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=import_{import_id}_issues.csv"},
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _assert_import_exists(db: Session, import_id: int) -> None:
    exists = db.query(ScheduleImport.id).filter(ScheduleImport.id == import_id).scalar()
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Importação não encontrada")


def _to_summary(sched_import: ScheduleImport) -> ScheduleImportSummary:
    importable = (sched_import.valid_rows or 0) + (sched_import.warning_rows or 0) - (sched_import.duplicate_rows or 0)
    return ScheduleImportSummary(
        import_id=sched_import.id,
        filename=sched_import.filename,
        reference_period=sched_import.reference_period,
        status=sched_import.status,
        total_rows=sched_import.total_rows or 0,
        valid_rows=sched_import.valid_rows or 0,
        warning_rows=sched_import.warning_rows or 0,
        invalid_rows=sched_import.invalid_rows or 0,
        duplicate_rows=sched_import.duplicate_rows or 0,
        importable_rows=max(0, importable),
        confirmed=sched_import.confirmed_at is not None,
        confirmed_at=sched_import.confirmed_at,
    )
