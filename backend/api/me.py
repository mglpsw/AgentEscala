from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..config.settings import settings
from ..models import User
from .schemas import MeUpdatePayload
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
        "phone": current_user.phone,
        "specialty": current_user.specialty,
        "profile_notes": current_user.profile_notes,
        "avatar_url": f"/api/media/avatars/{current_user.avatar_path}" if current_user.avatar_path else None,
    }


@router.put("")
def update_me(
    payload: MeUpdatePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.email and payload.email != current_user.email:
        duplicate = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="E-mail já está em uso")
        current_user.email = payload.email

    update_data = payload.model_dump(exclude_unset=True, exclude={"email"})
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return get_me(current_user=current_user)


def _avatar_root() -> Path:
    raw_dir = os.getenv("AGENTESCALA_AVATAR_DIR", "backend/uploads/avatars").strip()
    return Path(raw_dir).resolve()


@router.post("/avatar")
async def upload_my_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    allowed = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    if content_type not in allowed:
        raise HTTPException(status_code=415, detail="Formato inválido. Use PNG, JPG ou WEBP.")

    content = await file.read()
    max_size = 2 * 1024 * 1024
    if not content or len(content) > max_size:
        raise HTTPException(status_code=400, detail="Arquivo vazio ou acima de 2MB.")

    avatars_dir = _avatar_root()
    avatars_dir.mkdir(parents=True, exist_ok=True)
    filename = f"user_{current_user.id}_{uuid.uuid4().hex}{allowed[content_type]}"
    target = avatars_dir / filename
    target.write_bytes(content)

    if current_user.avatar_path and current_user.avatar_path != filename:
        old_file = avatars_dir / current_user.avatar_path
        if old_file.exists():
            old_file.unlink()

    current_user.avatar_path = filename
    db.commit()
    db.refresh(current_user)

    return {
        "avatar_url": f"/api/media/avatars/{filename}",
        "max_size_bytes": max_size,
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
        try:
            year_num = int(year)
            month_num = int(mon)
            parsed_start = date(year_num, month_num, 1)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mês inválido. Use valores entre 01 e 12 no formato YYYY-MM.",
            ) from exc

        if month_num == 12:
            parsed_end = date(year_num + 1, 1, 1)
            parsed_end = parsed_end.fromordinal(parsed_end.toordinal() - 1)
        else:
            next_month = date(year_num, month_num + 1, 1)
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
