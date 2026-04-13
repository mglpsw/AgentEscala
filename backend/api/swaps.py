from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from ..config.database import get_db
from ..models import SwapRequest, User, UserRole
from ..services import SwapService
from ..utils import ExcelExporter
from ..utils.dependencies import get_current_user, require_admin
from .schemas import (
    SwapRequestCreate,
    SwapRequestResponse,
    SwapRequestDetail,
    SwapApproval,
    SwapRejection
)

router = APIRouter(prefix="/swaps", tags=["Trocas"])


def _ensure_swap_visibility(swap: SwapRequest, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        return

    if current_user.id not in {swap.requester_id, swap.target_agent_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para consultar esta solicitação de troca"
        )


@router.post("/", response_model=SwapRequestResponse, status_code=status.HTTP_201_CREATED)
def create_swap_request(
    swap: SwapRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Criar uma nova solicitação de troca

    """
    try:
        return SwapService.create_swap_request(
            db,
            current_user.id,
            swap.target_agent_id,
            swap.origin_shift_id,
            swap.target_shift_id,
            swap.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[SwapRequestDetail])
def list_swap_requests(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar todas as solicitações de troca"""
    if current_user.role == UserRole.ADMIN:
        return SwapService.get_all_swaps(db, skip, limit)

    return SwapService.get_swaps_by_agent(db, current_user.id)


@router.get("/pending", response_model=List[SwapRequestDetail])
def list_pending_swaps(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Listar todas as solicitações de troca pendentes (para revisão do administrador)"""
    return SwapService.get_pending_swaps(db)


@router.get("/agent/{agent_id}", response_model=List[SwapRequestDetail])
def list_agent_swaps(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar todas as solicitações de troca que envolvem um agente específico"""
    if current_user.role != UserRole.ADMIN and current_user.id != agent_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode consultar as próprias solicitações de troca"
        )

    return SwapService.get_swaps_by_agent(db, agent_id)


@router.get("/export/excel", response_class=StreamingResponse)
def export_swaps_excel(
    skip: int = 0,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Exportar todas as solicitações de troca para Excel"""
    swaps = SwapService.get_all_swaps(db, skip, limit)
    excel_file = ExcelExporter.export_swap_requests(swaps)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=swap_requests.xlsx"}
    )


@router.get("/{swap_id}", response_model=SwapRequestDetail)
def get_swap_request(
    swap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter uma solicitação de troca pelo ID"""
    swap = SwapService.get_swap_request(db, swap_id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")

    _ensure_swap_visibility(swap, current_user)

    return swap


@router.post("/{swap_id}/approve", response_model=SwapRequestResponse)
def approve_swap_request(
    swap_id: int,
    approval: SwapApproval,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Aprovar uma solicitação de troca (somente administrador)

    """
    try:
        swap = SwapService.approve_swap(db, swap_id, current_user.id, approval.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{swap_id}/reject", response_model=SwapRequestResponse)
def reject_swap_request(
    swap_id: int,
    rejection: SwapRejection,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Rejeitar uma solicitação de troca (somente administrador)

    """
    try:
        swap = SwapService.reject_swap(db, swap_id, current_user.id, rejection.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{swap_id}/cancel", response_model=SwapRequestResponse)
def cancel_swap_request(
    swap_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancelar uma solicitação de troca (somente o solicitante)

    """
    try:
        swap = SwapService.cancel_swap(db, swap_id, current_user.id)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
