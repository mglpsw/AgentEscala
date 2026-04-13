from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from ..config.database import get_db
from ..services import SwapService
from ..utils import ExcelExporter
from .schemas import (
    SwapRequestCreate,
    SwapRequestResponse,
    SwapRequestDetail,
    SwapApproval,
    SwapRejection
)

router = APIRouter(prefix="/swaps", tags=["Trocas"])


@router.post("/", response_model=SwapRequestResponse, status_code=status.HTTP_201_CREATED)
def create_swap_request(
    swap: SwapRequestCreate,
    requester_id: int,
    db: Session = Depends(get_db)
):
    """
    Criar uma nova solicitação de troca

    Observação: em produção, o requester_id deve vir da sessão autenticada do usuário
    """
    try:
        return SwapService.create_swap_request(
            db,
            requester_id,
            swap.target_agent_id,
            swap.origin_shift_id,
            swap.target_shift_id,
            swap.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[SwapRequestDetail])
def list_swap_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Listar todas as solicitações de troca"""
    # Em uma implementação real, seria filtrado por papel/permissões do usuário
    return SwapService.get_all_swaps(db, skip, limit)


@router.get("/pending", response_model=List[SwapRequestDetail])
def list_pending_swaps(db: Session = Depends(get_db)):
    """Listar todas as solicitações de troca pendentes (para revisão do administrador)"""
    return SwapService.get_pending_swaps(db)


@router.get("/agent/{agent_id}", response_model=List[SwapRequestDetail])
def list_agent_swaps(agent_id: int, db: Session = Depends(get_db)):
    """Listar todas as solicitações de troca que envolvem um agente específico"""
    return SwapService.get_swaps_by_agent(db, agent_id)


@router.get("/{swap_id}", response_model=SwapRequestDetail)
def get_swap_request(swap_id: int, db: Session = Depends(get_db)):
    """Obter uma solicitação de troca pelo ID"""
    swap = SwapService.get_swap_request(db, swap_id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
    return swap


@router.post("/{swap_id}/approve", response_model=SwapRequestResponse)
def approve_swap_request(
    swap_id: int,
    approval: SwapApproval,
    admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Aprovar uma solicitação de troca (somente administrador)

    Observação: em produção, o admin_id deve vir da sessão autenticada do usuário
    """
    try:
        swap = SwapService.approve_swap(db, swap_id, admin_id, approval.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{swap_id}/reject", response_model=SwapRequestResponse)
def reject_swap_request(
    swap_id: int,
    rejection: SwapRejection,
    admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Rejeitar uma solicitação de troca (somente administrador)

    Observação: em produção, o admin_id deve vir da sessão autenticada do usuário
    """
    try:
        swap = SwapService.reject_swap(db, swap_id, admin_id, rejection.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{swap_id}/cancel", response_model=SwapRequestResponse)
def cancel_swap_request(
    swap_id: int,
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancelar uma solicitação de troca (somente o solicitante)

    Observação: em produção, o user_id deve vir da sessão autenticada do usuário
    """
    try:
        swap = SwapService.cancel_swap(db, swap_id, user_id)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitação de troca não encontrada")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/export/excel", response_class=StreamingResponse)
def export_swaps_excel(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Exportar todas as solicitações de troca para Excel"""
    swaps = SwapService.get_all_swaps(db, skip, limit)
    excel_file = ExcelExporter.export_swap_requests(swaps)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=swap_requests.xlsx"}
    )
