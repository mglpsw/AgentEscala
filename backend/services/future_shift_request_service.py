from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from ..models import FutureShiftRequest, FutureShiftRequestStatus

ALLOWED_SHIFT_PERIODS = {
    "12H DIA",
    "12H NOITE",
    "10-22H",
    "24 HORAS",
}


class FutureShiftRequestService:
    """Gerencia solicitações prévias de plantões futuros (separadas da escala oficial)."""

    @staticmethod
    def _max_allowed_date(today: date) -> date:
        year = today.year
        month = today.month + 3
        while month > 12:
            year += 1
            month -= 12

        month_lengths = [31, 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28,
                         31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        day = min(today.day, month_lengths[month - 1])
        return date(year, month, day)

    @staticmethod
    def validate_requested_date(requested_date: date, today: Optional[date] = None) -> None:
        current = today or date.today()
        max_date = FutureShiftRequestService._max_allowed_date(current)
        if requested_date < current:
            raise ValueError("Não é permitido solicitar plantão em data passada.")
        if requested_date > max_date:
            raise ValueError("Não é permitido solicitar plantão com antecedência superior a 3 meses.")

    @staticmethod
    def validate_payload(shift_period: str) -> None:
        normalized = (shift_period or "").strip().upper()
        if normalized not in ALLOWED_SHIFT_PERIODS:
            raise ValueError(
                "Período inválido. Use um dos valores: 12H DIA, 12H NOITE, 10-22H, 24 HORAS."
            )

    @staticmethod
    def create_request(
        db: Session,
        user_id: int,
        requested_date: date,
        shift_period: str,
        notes: Optional[str] = None,
    ) -> FutureShiftRequest:
        FutureShiftRequestService.validate_requested_date(requested_date)
        FutureShiftRequestService.validate_payload(shift_period)

        request = FutureShiftRequest(
            user_id=user_id,
            requested_date=requested_date,
            shift_period=shift_period.strip().upper(),
            notes=notes,
            status=FutureShiftRequestStatus.ACTIVE,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def list_requests(
        db: Session,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        include_cancelled: bool = False,
    ) -> list[FutureShiftRequest]:
        query = db.query(FutureShiftRequest).filter(FutureShiftRequest.user_id == user_id)
        if not include_cancelled:
            query = query.filter(FutureShiftRequest.status == FutureShiftRequestStatus.ACTIVE)
        if start_date:
            query = query.filter(FutureShiftRequest.requested_date >= start_date)
        if end_date:
            query = query.filter(FutureShiftRequest.requested_date <= end_date)
        return query.order_by(FutureShiftRequest.requested_date.asc(), FutureShiftRequest.id.asc()).all()

    @staticmethod
    def cancel_request(db: Session, request_id: int, user_id: int) -> Optional[FutureShiftRequest]:
        request = (
            db.query(FutureShiftRequest)
            .filter(
                FutureShiftRequest.id == request_id,
                FutureShiftRequest.user_id == user_id,
            )
            .first()
        )
        if not request:
            return None

        request.status = FutureShiftRequestStatus.CANCELLED
        db.commit()
        db.refresh(request)
        return request
