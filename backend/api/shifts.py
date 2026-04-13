from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from ..config.database import get_db
from ..services import ShiftService
from ..utils import ExcelExporter, ICSExporter
from .schemas import ShiftCreate, ShiftUpdate, ShiftResponse, ShiftWithAgent

router = APIRouter(prefix="/shifts", tags=["Turnos"])


@router.post("/", response_model=ShiftResponse, status_code=status.HTTP_201_CREATED)
def create_shift(shift: ShiftCreate, db: Session = Depends(get_db)):
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
def list_shifts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Listar todos os turnos"""
    return ShiftService.get_all_shifts(db, skip, limit)


@router.get("/agent/{agent_id}", response_model=List[ShiftResponse])
def list_agent_shifts(agent_id: int, db: Session = Depends(get_db)):
    """Listar todos os turnos de um agente específico"""
    return ShiftService.get_shifts_by_agent(db, agent_id)


@router.get("/export/excel", response_class=StreamingResponse)
def export_shifts_excel(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Exportar turnos para Excel"""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    excel_file = ExcelExporter.export_shifts(shifts, include_agent_info=True)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=shifts.xlsx"}
    )


@router.get("/export/ics", response_class=StreamingResponse)
def export_shifts_ics(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Exportar turnos para o formato ICS (iCalendar)"""
    shifts = ShiftService.get_all_shifts(db, skip, limit)
    ics_file = ICSExporter.export_shifts(shifts)

    return StreamingResponse(
        ics_file,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=shifts.ics"}
    )


@router.get("/{shift_id}", response_model=ShiftWithAgent)
def get_shift(shift_id: int, db: Session = Depends(get_db)):
    """Obter um turno pelo ID"""
    shift = ShiftService.get_shift(db, shift_id)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return shift


@router.patch("/{shift_id}", response_model=ShiftResponse)
def update_shift(shift_id: int, shift_update: ShiftUpdate, db: Session = Depends(get_db)):
    """Atualizar um turno"""
    update_data = shift_update.model_dump(exclude_unset=True)
    shift = ShiftService.update_shift(db, shift_id, **update_data)
    if not shift:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return shift


@router.delete("/{shift_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    """Excluir um turno"""
    success = ShiftService.delete_shift(db, shift_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno não encontrado")
    return None


@router.get("/{shift_id}/export/ics", response_class=StreamingResponse)
def export_single_shift_ics(shift_id: int, db: Session = Depends(get_db)):
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
