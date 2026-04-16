"""Endpoints para identidade médica e governança administrativa."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..config.database import get_db
from ..models import User
from ..services import MedicalProfileService
from ..utils.dependencies import get_current_user, require_admin
from .schemas import MedicalProfileCreate, MedicalProfileResponse, MedicalProfileUpdate

router = APIRouter(prefix="/api/v1/medical-profiles", tags=["Perfis Médicos"])


def _translate_service_error(exc: ValueError) -> HTTPException:
    """Converter erros de regra de negócio em resposta HTTP estável."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/", response_model=MedicalProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: MedicalProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Criar perfil médico do usuário autenticado."""
    try:
        return MedicalProfileService.create_profile(db, current_user.id, profile_data)
    except ValueError as exc:
        raise _translate_service_error(exc) from exc


@router.get("/me", response_model=MedicalProfileResponse)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consultar o próprio perfil médico."""
    profile = MedicalProfileService.get_profile_by_user(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil médico não encontrado")
    return profile


@router.put("/me", response_model=MedicalProfileResponse)
def update_my_profile(
    profile_data: MedicalProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualizar o próprio perfil médico."""
    profile = MedicalProfileService.get_profile_by_user(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil médico não encontrado")

    try:
        return MedicalProfileService.update_profile(db, profile, profile_data)
    except ValueError as exc:
        raise _translate_service_error(exc) from exc


@router.get("/", response_model=List[MedicalProfileResponse])
def list_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Listar perfis médicos para administração."""
    return MedicalProfileService.list_profiles(db, skip, limit)


@router.get("/{profile_id}", response_model=MedicalProfileResponse)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Detalhar perfil médico por ID administrativo."""
    profile = MedicalProfileService.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil médico não encontrado")
    return profile


@router.put("/{profile_id}", response_model=MedicalProfileResponse)
def update_profile(
    profile_id: int,
    profile_data: MedicalProfileUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Editar perfil médico por ID administrativo."""
    profile = MedicalProfileService.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil médico não encontrado")

    try:
        return MedicalProfileService.update_profile(db, profile, profile_data)
    except ValueError as exc:
        raise _translate_service_error(exc) from exc


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Remover perfil médico por ID administrativo."""
    profile = MedicalProfileService.get_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil médico não encontrado")

    MedicalProfileService.delete_profile(db, profile)
    return None
