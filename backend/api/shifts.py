import re
from datetime import date, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import User
from ..services import SchedulePresentationService, ShiftService
from ..utils import ExcelExporter, ICSExporter
from ..utils.dependencies import get_current_user, require_admin
from .schemas import (
    FinalScheduleExportResponse,
    FinalScheduleRow,
    ShiftCreate,
    ShiftUpdate,
    ShiftResponse,
    ShiftWithAgent,
)

router = APIRouter(prefix="/shifts", tags=["Turnos"])
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_export_date(value: Optional[str]) -> Optional[date]:
    """Validar datas de exportação mantendo erro 400 com mensagem em português."""
    if value is None:
        return None

    if not DATE_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de data inválido. Use YYYY-MM-DD."
        )

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de data inválido. Use YYYY-MM-DD."
        ) from exc


def _parse_export_period(
    start_date: Optional[str],
    end_date: Optional[str],
) -> tuple[Optional[date], Optional[date]]:
    """Validar o período uma única vez para todos os endpoints de exportação."""
    parsed_start_date = _parse_export_date(start_date)
    parsed_end_date = _parse_export_date(end_date)

    if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial não pode ser maior que a data final."
        )

    return parsed_start_date, parsed_end_date


def _build_shift_export_response(shifts, export_format: str, view: str) -> StreamingResponse:
    if export_format == "xlsx":
        if view == "essential":
            rows = SchedulePresentationService.build_essential_rows(shifts)
            export_file = ExcelExporter.export_final_schedule(rows)
            filename = "escala_final.xlsx"
        else:
            export_file = ExcelExporter.export_shifts(shifts, include_agent_info=True)
            filename = "shifts.xlsx"

        return StreamingResponse(
            export_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    if export_format == "ics":
        if view != "full":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A visualização essencial está disponível apenas para exportação xlsx"
            )

        export_file = ICSExporter.export_shifts(shifts)
        return StreamingResponse(
            export_file,
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=shifts.ics"}
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Formato de exportação inválido"
    )


def _build_final_schedule_payload(
    shifts,
    start_date: Optional[date],
    end_date: Optional[date],
) -> dict:
    """Montar payload JSON da escala final reutilizado por rotas equivalentes."""
    rows = SchedulePresentationService.build_essential_rows(shifts)
    return {
        "shifts": rows,
        "metadata": {
            "total": len(rows),
            "generated_at": datetime.utcnow().isoformat(),
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
        },
    }


@router.post("/", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift: ShiftCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Criar um novo turno"""
    try:
        return ShiftService.create_shift(
            db,
            shift.agent_id,
            shift.start_time,
            shift.end_time,
            shift.title,
            shift.description,
            shift.location,
            shift.user_id,
            shift.legacy_agent_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/", response_model=List[ShiftWithAgent])
def list_shifts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Listar todos os turnos"""
    return ShiftService.get_all_shifts(db, skip, limit)


@router.get("/agent/{agent_id}", response_model=List[ShiftResponse])
def list_agent_shifts(
    agent_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Listar todos os turnos de um agente específico"""
    return ShiftService.get_shifts_by_agent(db, agent_id)


@router.get("/export")
def export_shifts_standardized(
    skip: int = 0,
    limit: int = 1000,
    export_format: str = Query("xlsx", alias="format", pattern="^(xlsx|json|ics)$"),
    view: str = Query("full", pattern="^(full|essential)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos por endpoint padronizado."""
    parsed_start_date, parsed_end_date = _parse_export_period(start_date, end_date)
    shifts = ShiftService.get_filtered_shifts(
        db,
        parsed_start_date,
        parsed_end_date,
        skip,
        limit,
    )
    if export_format == "json":
        return JSONResponse(
            content=jsonable_encoder(
                _build_final_schedule_payload(shifts, parsed_start_date, parsed_end_date)
            )
        )

    return _build_shift_export_response(shifts, export_format, view)


@router.get("/export/final/json", response_model=FinalScheduleExportResponse)
def export_final_schedule_json(
    skip: int = 0,
    limit: int = 1000,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar a escala final em JSON com a mesma fonte usada pelo Excel."""
    parsed_start_date, parsed_end_date = _parse_export_period(start_date, end_date)
    shifts = ShiftService.get_filtered_shifts(
        db,
        parsed_start_date,
        parsed_end_date,
        skip,
        limit,
    )
    return _build_final_schedule_payload(shifts, parsed_start_date, parsed_end_date)


@router.get("/export/excel", response_class=StreamingResponse)
def export_shifts_excel(
    skip: int = 0,
    limit: int = 1000,
    view: str = Query("full", pattern="^(full|essential)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos para Excel. Mantido por compatibilidade."""
    parsed_start_date, parsed_end_date = _parse_export_period(start_date, end_date)
    shifts = ShiftService.get_filtered_shifts(
        db,
        parsed_start_date,
        parsed_end_date,
        skip,
        limit,
    )
    return _build_shift_export_response(shifts, "xlsx", view)


@router.get("/final-schedule", response_model=List[FinalScheduleRow])
def list_final_schedule_rows(
    skip: int = 0,
    limit: int = 1000,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Listar linhas essenciais para a futura tabela final da escala."""
    parsed_start_date, parsed_end_date = _parse_export_period(start_date, end_date)
    shifts = ShiftService.get_filtered_shifts(
        db,
        parsed_start_date,
        parsed_end_date,
        skip,
        limit,
    )
    return SchedulePresentationService.build_essential_rows(shifts)


@router.get("/export/ics", response_class=StreamingResponse)
def export_shifts_ics(
    skip: int = 0,
    limit: int = 1000,
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos para ICS. Mantido por compatibilidade."""
    parsed_start_date, parsed_end_date = _parse_export_period(start_date, end_date)
    shifts = ShiftService.get_filtered_shifts(
        db,
        parsed_start_date,
        parsed_end_date,
        skip,
        limit,
    )
    return _build_shift_export_response(shifts, "ics", "full")


@router.get("/coverage/flags")
def get_coverage_flags(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Retorna flag diária de cobertura de plantão (completo/incompleto)."""
    today = date.today()
    default_start = today.replace(day=1)
    if today.month == 12:
        default_end = date(today.year + 1, 1, 1).fromordinal(date(today.year + 1, 1, 1).toordinal() - 1)
    else:
        default_end = date(today.year, today.month + 1, 1).fromordinal(
            date(today.year, today.month + 1, 1).toordinal() - 1
        )

    parsed_start = _parse_export_date(start_date) if start_date else default_start
    parsed_end = _parse_export_date(end_date) if end_date else default_end
    if parsed_start > parsed_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial não pode ser maior que a data final."
        )
    return ShiftService.get_daily_coverage_flags(db, parsed_start, parsed_end)


@router.get("/consistency-report")
def get_shift_consistency_report(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Resumo simples de consistência entre vínculo relacional e campos legados."""
    return ShiftService.get_link_consistency_report(db)


@router.get("/{shift_id}", response_model=ShiftWithAgent)
def get_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Obter um turno pelo ID"""
    shift = ShiftService.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return shift


@router.patch("/{shift_id}", response_model=ShiftResponse)
def update_shift(
    shift_id: int,
    shift_update: ShiftUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Atualizar um turno"""
    update_data = shift_update.model_dump(exclude_unset=True)
    try:
        shift = ShiftService.update_shift(db, shift_id, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(
    shift_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Excluir um turno"""
    success = ShiftService.delete_shift(db, shift_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return None


@router.get("/{shift_id}/export/ics", response_class=StreamingResponse)
def export_single_shift_ics(
    shift_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar um turno para o formato ICS"""
    shift = ShiftService.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")

    ics_file = ICSExporter.export_single_shift(shift)

    return StreamingResponse(
        ics_file,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=shift_{shift_id}.ics"}
    )
