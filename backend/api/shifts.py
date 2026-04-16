from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from ..config.database import get_db
from ..models import User
from ..services import SchedulePresentationService, ShiftService
from ..utils import ExcelExporter, ICSExporter
from ..utils.dependencies import get_current_user, require_admin
from .schemas import FinalScheduleRow, ShiftCreate, ShiftUpdate, ShiftResponse, ShiftWithAgent

router = APIRouter(prefix="/shifts", tags=["Turnos"])


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


@router.post("/", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(
    shift: ShiftCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Criar um novo turno"""
    return ShiftService.create_shift(
        db,
        shift.agent_id,
        shift.start_time,
        shift.end_time,
        shift.title,
        shift.description,
        shift.location
    )


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


@router.get("/export", response_class=StreamingResponse)
def export_shifts_standardized(
    skip: int = 0,
    limit: int = 1000,
    export_format: str = Query("xlsx", alias="format", pattern="^(xlsx|ics)$"),
    view: str = Query("full", pattern="^(full|essential)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos por endpoint padronizado."""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    return _build_shift_export_response(shifts, export_format, view)


@router.get("/export/excel", response_class=StreamingResponse)
def export_shifts_excel(
    skip: int = 0,
    limit: int = 1000,
    view: str = Query("full", pattern="^(full|essential)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos para Excel. Mantido por compatibilidade."""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    return _build_shift_export_response(shifts, "xlsx", view)


@router.get("/final-schedule", response_model=List[FinalScheduleRow])
def list_final_schedule_rows(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Listar linhas essenciais para a futura tabela final da escala."""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    return SchedulePresentationService.build_essential_rows(shifts)


@router.get("/export/ics", response_class=StreamingResponse)
def export_shifts_ics(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    """Exportar turnos para ICS. Mantido por compatibilidade."""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    return _build_shift_export_response(shifts, "ics", "full")


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
    shift = ShiftService.update_shift(db, shift_id, **update_data)
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
