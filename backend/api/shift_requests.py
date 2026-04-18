from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import User
from ..services import ShiftRequestService
from ..utils.dependencies import get_current_user, require_admin
from .schemas import (
    ShiftRequestCreate,
    ShiftRequestResponse,
    ShiftRequestTargetResponsePayload,
    ShiftRequestAdminReviewPayload,
)

router = APIRouter(prefix="/shift-requests", tags=["Solicitações de Plantão"])


@router.post("/", response_model=ShiftRequestResponse, status_code=status.HTTP_201_CREATED)
def create_shift_request(
    payload: ShiftRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ShiftRequestService.create_request(
            db=db,
            requester_id=current_user.id,
            requested_date=payload.requested_date,
            shift_period=payload.shift_period,
            note=payload.note,
            target_shift_id=payload.target_shift_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/", response_model=list[ShiftRequestResponse])
def list_shift_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ShiftRequestService.list_for_user(db, current_user)


@router.post("/{request_id}/respond", response_model=ShiftRequestResponse)
def respond_target_shift_request(
    request_id: int,
    payload: ShiftRequestTargetResponsePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ShiftRequestService.respond_target(
            db=db,
            request_id=request_id,
            current_user_id=current_user.id,
            accept=payload.accept,
            note=payload.note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{request_id}/admin-review", response_model=ShiftRequestResponse)
def review_shift_request_admin(
    request_id: int,
    payload: ShiftRequestAdminReviewPayload,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    try:
        return ShiftRequestService.admin_review(
            db=db,
            request_id=request_id,
            admin_id=admin_user.id,
            approve=payload.approve,
            admin_notes=payload.admin_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{request_id}/cancel", response_model=ShiftRequestResponse)
def cancel_shift_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return ShiftRequestService.cancel_request(db=db, request_id=request_id, requester_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
