from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from calendar import monthrange
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from ..models import (
    RecurringBatchStatus,
    RecurringItemDecisionStatus,
    RecurringShiftBatch,
    RecurringShiftBatchItem,
    Shift,
    User,
)


@dataclass
class RecurringInput:
    user_id: int
    weekday: int
    shift_label: str
    start_time: str
    end_time: str
    start_date: date
    months_ahead: int
    notes: Optional[str]


def _parse_hhmm(raw: str) -> time:
    hh, mm = raw.split(":")
    return time(int(hh), int(mm))


def _add_months(base: date, months: int) -> date:
    total = (base.month - 1) + months
    year = base.year + total // 12
    month = total % 12 + 1
    day = min(base.day, monthrange(year, month)[1])
    return date(year, month, day)


def _compute_occurrence_range(start_date: date, months_ahead: int) -> Tuple[date, date]:
    capped = min(max(months_ahead, 1), 6)
    range_end = _add_months(start_date, capped)
    return start_date, range_end


def _build_occurrences(input_data: RecurringInput) -> Tuple[date, date, List[tuple[date, datetime, datetime]]]:
    start_date, end_date = _compute_occurrence_range(input_data.start_date, input_data.months_ahead)
    t_start = _parse_hhmm(input_data.start_time)
    t_end = _parse_hhmm(input_data.end_time)

    cursor = start_date
    while cursor.weekday() != input_data.weekday:
        cursor += timedelta(days=1)

    items: List[tuple[date, datetime, datetime]] = []
    while cursor <= end_date:
        start_dt = datetime.combine(cursor, t_start)
        end_dt = datetime.combine(cursor, t_end)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        items.append((cursor, start_dt, end_dt))
        cursor += timedelta(days=7)

    return start_date, end_date, items


def _detect_duplicate_or_conflict(existing_shifts: List[Shift], start_dt: datetime, end_dt: datetime) -> tuple[bool, bool, Optional[int], List[str]]:
    duplicate = False
    conflict = False
    existing_shift_id = None
    messages: List[str] = []
    for shift in existing_shifts:
        if shift.start_time == start_dt and shift.end_time == end_dt:
            duplicate = True
            existing_shift_id = shift.id
            messages.append(f"Duplicata com shift {shift.id}")
            break

    for shift in existing_shifts:
        if start_dt < shift.end_time and shift.start_time < end_dt:
            conflict = True
            existing_shift_id = existing_shift_id or shift.id
            messages.append(f"Conflito de sobreposição com shift {shift.id}")
            if duplicate:
                break

    return duplicate, conflict, existing_shift_id, messages


def build_preview(db: Session, payload: RecurringInput, created_by: int) -> tuple[RecurringShiftBatch, List[RecurringShiftBatchItem]]:
    user = db.query(User).filter(User.id == payload.user_id, User.is_active == True).first()  # noqa: E712
    if not user:
        raise ValueError("Profissional não encontrado ou inativo")

    start_date, end_date, occurrences = _build_occurrences(payload)
    existing_shifts = db.query(Shift).filter(Shift.agent_id == payload.user_id).all()

    batch = RecurringShiftBatch(
        user_id=payload.user_id,
        weekday=payload.weekday,
        shift_label=payload.shift_label,
        start_time=payload.start_time,
        end_time=payload.end_time,
        start_date=start_date,
        end_date=end_date,
        months_ahead=min(payload.months_ahead, 6),
        notes=payload.notes,
        status=RecurringBatchStatus.PREVIEW,
        created_by=created_by,
    )
    db.add(batch)
    db.flush()

    items: List[RecurringShiftBatchItem] = []
    total_conflicts = 0
    total_duplicates = 0

    for target_date, start_dt, end_dt in occurrences:
        duplicate, conflict, existing_shift_id, messages = _detect_duplicate_or_conflict(existing_shifts, start_dt, end_dt)
        if duplicate:
            total_duplicates += 1
        if conflict:
            total_conflicts += 1
        item = RecurringShiftBatchItem(
            batch_id=batch.id,
            target_date=target_date,
            start_datetime=start_dt,
            end_datetime=end_dt,
            existing_shift_id=existing_shift_id,
            conflict_status=conflict,
            duplicate_status=duplicate,
            decision_status=RecurringItemDecisionStatus.PENDING,
            validation_messages=json.dumps(messages),
        )
        db.add(item)
        items.append(item)

    batch.summary_json = json.dumps(
        {
            "total_generated": len(items),
            "total_conflicts": total_conflicts,
            "total_duplicates": total_duplicates,
            "created_by": created_by,
            "created_at": datetime.utcnow().isoformat(),
        }
    )
    db.commit()
    db.refresh(batch)
    for item in items:
        db.refresh(item)
    return batch, items


def confirm_batch(
    db: Session,
    payload: RecurringInput,
    created_by: int,
    include_conflicts: bool,
    include_duplicates: bool,
    item_decisions: Optional[Dict[int, dict]] = None,
    batch_id: Optional[int] = None,
) -> tuple[RecurringShiftBatch, List[int], int, int, int]:
    if batch_id:
        batch = db.query(RecurringShiftBatch).filter(RecurringShiftBatch.id == batch_id).first()
        if not batch:
            raise ValueError("Batch de recorrência não encontrado")
        if batch.status == RecurringBatchStatus.CONFIRMED:
            raise ValueError("Batch de recorrência já confirmado")
        items = db.query(RecurringShiftBatchItem).filter(RecurringShiftBatchItem.batch_id == batch.id).all()
    else:
        batch, items = build_preview(db, payload, created_by)

    created_ids: List[int] = []
    skipped = 0
    conflicts = 0
    duplicates = 0

    decision_map = item_decisions or {}

    for item in items:
        if item.created_shift_id or item.decision_status == RecurringItemDecisionStatus.CREATED:
            skipped += 1
            continue
        if item.duplicate_status:
            duplicates += 1
        if item.conflict_status:
            conflicts += 1
        explicit_decision = decision_map.get(item.id, {})
        action = explicit_decision.get("decision")
        notes = explicit_decision.get("notes")
        if action:
            item.decision_action = action
            item.decision_notes = notes
            item.decided_by = created_by
            item.decided_at = datetime.utcnow()

        if action == "overwrite":
            # Não suportado com segurança na modelagem atual de recorrência.
            raise ValueError("Decisão 'overwrite' ainda não suportada com segurança")
        if action in {"skip", "keep_existing"}:
            if item.duplicate_status:
                item.decision_status = RecurringItemDecisionStatus.SKIPPED_DUPLICATE
            elif item.conflict_status:
                item.decision_status = RecurringItemDecisionStatus.SKIPPED_CONFLICT
            else:
                item.decision_status = RecurringItemDecisionStatus.SKIPPED_CONFLICT
            skipped += 1
            continue
        if action == "create":
            pass

        if item.duplicate_status:
            if not include_duplicates:
                item.decision_status = RecurringItemDecisionStatus.SKIPPED_DUPLICATE
                item.decision_action = item.decision_action or "skip"
                skipped += 1
                continue
        if item.conflict_status:
            if not include_conflicts:
                item.decision_status = RecurringItemDecisionStatus.SKIPPED_CONFLICT
                item.decision_action = item.decision_action or "skip"
                skipped += 1
                continue

        shift = Shift(
            agent_id=batch.user_id,
            user_id=batch.user_id,
            start_time=item.start_datetime,
            end_time=item.end_datetime,
            title=batch.shift_label,
            description=f"Recorrência semanal (batch {batch.id})",
        )
        db.add(shift)
        db.flush()
        item.created_shift_id = shift.id
        item.decision_status = RecurringItemDecisionStatus.CREATED
        item.decision_action = item.decision_action or "create"
        item.decided_by = item.decided_by or created_by
        item.decided_at = item.decided_at or datetime.utcnow()
        created_ids.append(shift.id)

    batch.status = RecurringBatchStatus.CONFIRMED
    batch.confirmed_at = datetime.utcnow()
    batch.summary_json = json.dumps(
        {
            "total_generated": len(items),
            "total_conflicts": conflicts,
            "total_duplicates": duplicates,
            "total_created": len(created_ids),
            "skipped": skipped,
            "created_shift_ids": created_ids,
            "confirmed_by": created_by,
            "confirmed_at": datetime.utcnow().isoformat(),
        }
    )
    db.commit()
    db.refresh(batch)
    return batch, created_ids, conflicts, duplicates, skipped
