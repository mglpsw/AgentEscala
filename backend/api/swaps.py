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

router = APIRouter(prefix="/swaps", tags=["swaps"])


@router.post("/", response_model=SwapRequestResponse, status_code=status.HTTP_201_CREATED)
def create_swap_request(
    swap: SwapRequestCreate,
    requester_id: int,
    db: Session = Depends(get_db)
):
    """
    Create a new swap request

    Note: In production, requester_id should come from authenticated user session
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
    """List all swap requests"""
    # In a real implementation, this would be filtered by user role/permissions
    return SwapService.get_all_swaps(db, skip, limit)


@router.get("/pending", response_model=List[SwapRequestDetail])
def list_pending_swaps(db: Session = Depends(get_db)):
    """List all pending swap requests (for admin review)"""
    return SwapService.get_pending_swaps(db)


@router.get("/agent/{agent_id}", response_model=List[SwapRequestDetail])
def list_agent_swaps(agent_id: int, db: Session = Depends(get_db)):
    """List all swap requests involving a specific agent"""
    return SwapService.get_swaps_by_agent(db, agent_id)


@router.get("/{swap_id}", response_model=SwapRequestDetail)
def get_swap_request(swap_id: int, db: Session = Depends(get_db)):
    """Get a swap request by ID"""
    swap = SwapService.get_swap_request(db, swap_id)
    if not swap:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found")
    return swap


@router.post("/{swap_id}/approve", response_model=SwapRequestResponse)
def approve_swap_request(
    swap_id: int,
    approval: SwapApproval,
    admin_id: int,
    db: Session = Depends(get_db)
):
    """
    Approve a swap request (admin only)

    Note: In production, admin_id should come from authenticated user session
    """
    try:
        swap = SwapService.approve_swap(db, swap_id, admin_id, approval.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found")
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
    Reject a swap request (admin only)

    Note: In production, admin_id should come from authenticated user session
    """
    try:
        swap = SwapService.reject_swap(db, swap_id, admin_id, rejection.admin_notes)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found")
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
    Cancel a swap request (requester only)

    Note: In production, user_id should come from authenticated user session
    """
    try:
        swap = SwapService.cancel_swap(db, swap_id, user_id)
        if not swap:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Swap request not found")
        return swap
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/export/excel", response_class=StreamingResponse)
def export_swaps_excel(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    """Export all swap requests to Excel"""
    swaps = SwapService.get_all_swaps(db, skip, limit)
    excel_file = ExcelExporter.export_swap_requests(swaps)

    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=swap_requests.xlsx"}
    )
