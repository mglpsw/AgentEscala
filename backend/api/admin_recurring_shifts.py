from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import RecurringShiftBatch, RecurringShiftBatchItem, User
from ..services.recurring_shift_service import RecurringInput, build_preview, confirm_batch
from ..utils.dependencies import require_admin
from .schemas import (
    RecurringShiftBatchResult,
    RecurringShiftConfirmRequest,
    RecurringShiftPreviewItem,
    RecurringShiftPreviewRequest,
    RecurringShiftPreviewResponse,
)

router = APIRouter(prefix="/admin/recurring-shifts", tags=["Admin Recurring Shifts"])


def _to_preview_item(item: RecurringShiftBatchItem, weekday: int, shift_label: str) -> RecurringShiftPreviewItem:
    duration = round((item.end_datetime - item.start_datetime).total_seconds() / 3600, 2)
    messages = []
    if item.validation_messages:
        try:
            messages = json.loads(item.validation_messages)
        except ValueError:
            messages = [item.validation_messages]
    return RecurringShiftPreviewItem(
        target_date=item.target_date,
        weekday=weekday,
        shift_label=shift_label,
        start_datetime=item.start_datetime,
        end_datetime=item.end_datetime,
        duration_hours=duration,
        duplicate_status=item.duplicate_status,
        conflict_status=item.conflict_status,
        existing_shift_id=item.existing_shift_id,
        validation_messages=messages,
    )


@router.post("/preview", response_model=RecurringShiftPreviewResponse)
def preview_recurring_shifts(
    body: RecurringShiftPreviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    payload = RecurringInput(**body.model_dump())
    try:
        batch, items = build_preview(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return RecurringShiftPreviewResponse(
        batch_id=batch.id,
        interval_start=batch.start_date,
        interval_end=batch.end_date,
        total_generated=len(items),
        total_conflicts=sum(1 for i in items if i.conflict_status),
        total_duplicates=sum(1 for i in items if i.duplicate_status),
        items=[_to_preview_item(i, batch.weekday, batch.shift_label) for i in items],
    )


@router.post("/confirm", response_model=RecurringShiftBatchResult)
def confirm_recurring_shifts(
    body: RecurringShiftConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    payload = RecurringInput(
        user_id=body.user_id,
        weekday=body.weekday,
        shift_label=body.shift_label,
        start_time=body.start_time,
        end_time=body.end_time,
        start_date=body.start_date,
        months_ahead=body.months_ahead,
        notes=body.notes,
    )
    try:
        batch, created_ids, conflicts, duplicates, skipped = confirm_batch(
            db,
            payload,
            created_by=current_user.id,
            include_conflicts=body.include_conflicts,
            include_duplicates=body.include_duplicates,
            batch_id=body.batch_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    total_generated = len(db.query(RecurringShiftBatchItem).filter(RecurringShiftBatchItem.batch_id == batch.id).all())
    return RecurringShiftBatchResult(
        batch_id=batch.id,
        total_generated=total_generated,
        total_conflicts=conflicts,
        total_duplicates=duplicates,
        total_created=len(created_ids),
        skipped=skipped,
        created_shift_ids=created_ids,
    )


@router.get("", response_model=list[RecurringShiftBatchResult])
def list_recurring_batches(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    batches = (
        db.query(RecurringShiftBatch)
        .order_by(RecurringShiftBatch.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    results: list[RecurringShiftBatchResult] = []
    for batch in batches:
        summary = {}
        if batch.summary_json:
            try:
                summary = json.loads(batch.summary_json)
            except ValueError:
                summary = {}
        results.append(
            RecurringShiftBatchResult(
                batch_id=batch.id,
                total_generated=int(summary.get("total_generated") or 0),
                total_conflicts=int(summary.get("total_conflicts") or 0),
                total_duplicates=int(summary.get("total_duplicates") or 0),
                total_created=int(summary.get("total_created") or 0),
                skipped=int(summary.get("skipped") or 0),
                created_shift_ids=list(summary.get("created_shift_ids") or []),
            )
        )
    return results


@router.get("/{batch_id}", response_model=RecurringShiftPreviewResponse)
def get_recurring_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    batch = db.query(RecurringShiftBatch).filter(RecurringShiftBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch de recorrência não encontrado")
    items = db.query(RecurringShiftBatchItem).filter(RecurringShiftBatchItem.batch_id == batch_id).all()
    return RecurringShiftPreviewResponse(
        batch_id=batch.id,
        interval_start=batch.start_date,
        interval_end=batch.end_date,
        total_generated=len(items),
        total_conflicts=sum(1 for i in items if i.conflict_status),
        total_duplicates=sum(1 for i in items if i.duplicate_status),
        items=[_to_preview_item(i, batch.weekday, batch.shift_label) for i in items],
    )
