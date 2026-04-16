from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import User
from ..services import ShiftService
from ..utils.dependencies import get_current_user
from ..utils.ics_exporter import ICSExporter

router = APIRouter(prefix="/me", tags=["Usuário autenticado"])


@router.get("")
def get_me(current_user: User = Depends(get_current_user)):
    """Retorna os dados básicos do usuário autenticado."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "is_admin": current_user.is_admin,
        "is_active": current_user.is_active,
    }


@router.get("/shifts")
def get_my_shifts(
    month: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista plantões do usuário autenticado com filtro simples por período/mês."""
    parsed_start = start_date
    parsed_end = end_date

    if month:
        year, mon = month.split("-")
        parsed_start = date(int(year), int(mon), 1)
        if int(mon) == 12:
            parsed_end = date(int(year) + 1, 1, 1)
            parsed_end = parsed_end.fromordinal(parsed_end.toordinal() - 1)
        else:
            next_month = date(int(year), int(mon) + 1, 1)
            parsed_end = next_month.fromordinal(next_month.toordinal() - 1)

    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial não pode ser maior que data final.",
        )

    return ShiftService.get_shifts_for_user(
        db=db,
        user_id=current_user.id,
        user_name=current_user.name,
        start_date=parsed_start,
        end_date=parsed_end,
    )


@router.get("/shifts/export.ics", response_class=StreamingResponse)
def export_my_shifts_ics(
    month: Optional[str] = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shifts = get_my_shifts(
        month=month,
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
    )
    export_file = ICSExporter.export_shifts(shifts, calendar_name=f"Escala de {current_user.name}")
    return StreamingResponse(
        export_file,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=minha_escala.ics"},
    )
