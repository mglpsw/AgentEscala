from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..models import Shift, ShiftRequest, ShiftRequestStatus, User, UserRole
from .future_shift_request_service import ALLOWED_SHIFT_PERIODS
from .shift_service import PLANTAO_TYPE_RULES


class ShiftRequestService:
    @staticmethod
    def _period_to_datetimes(requested_date: date, shift_period: str) -> tuple[datetime, datetime]:
        period = shift_period.strip().upper()
        start_hour, end_hour = PLANTAO_TYPE_RULES.get(period, (None, None))
        if start_hour is None:
            raise ValueError("Período de plantão inválido.")

        start = datetime.combine(requested_date, time(start_hour, 0))
        end_date = requested_date if end_hour > start_hour else requested_date + timedelta(days=1)
        end = datetime.combine(end_date, time(end_hour, 0))
        if period == "24 HORAS":
            end = start + timedelta(hours=24)
        return start, end

    @staticmethod
    def _find_shift_by_period(db: Session, requested_date: date, shift_period: str) -> Optional[Shift]:
        start, end = ShiftRequestService._period_to_datetimes(requested_date, shift_period)
        return (
            db.query(Shift)
            .filter(Shift.start_time == start, Shift.end_time == end)
            .first()
        )

    @staticmethod
    def create_request(
        db: Session,
        requester_id: int,
        requested_date: date,
        shift_period: str,
        note: Optional[str] = None,
        target_shift_id: Optional[int] = None,
    ) -> ShiftRequest:
        period = (shift_period or "").strip().upper()
        if period not in ALLOWED_SHIFT_PERIODS:
            raise ValueError("Período inválido para solicitação de plantão.")
        if requested_date < date.today():
            raise ValueError("Não é permitido solicitar plantão para data passada.")

        target_shift = None
        if target_shift_id is not None:
            target_shift = db.query(Shift).filter(Shift.id == target_shift_id).first()
            if not target_shift:
                raise ValueError("Plantão alvo não encontrado.")
        else:
            target_shift = ShiftRequestService._find_shift_by_period(db, requested_date, period)

        target_user_id = target_shift.agent_id if target_shift else None
        status = ShiftRequestStatus.PENDING_TARGET if target_shift else ShiftRequestStatus.PENDING_ADMIN

        if target_user_id == requester_id:
            raise ValueError("Você já é o responsável por este plantão.")

        request = ShiftRequest(
            requester_id=requester_id,
            target_user_id=target_user_id,
            target_shift_id=target_shift.id if target_shift else None,
            requested_date=requested_date,
            shift_period=period,
            note=note,
            status=status,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def list_for_user(db: Session, user: User) -> list[ShiftRequest]:
        query = db.query(ShiftRequest)
        if user.role == UserRole.ADMIN:
            return query.order_by(ShiftRequest.created_at.desc()).all()

        return (
            query.filter(
                (ShiftRequest.requester_id == user.id) |
                (ShiftRequest.target_user_id == user.id)
            )
            .order_by(ShiftRequest.created_at.desc())
            .all()
        )

    @staticmethod
    def respond_target(
        db: Session,
        request_id: int,
        current_user_id: int,
        accept: bool,
        note: Optional[str] = None,
    ) -> ShiftRequest:
        request = db.query(ShiftRequest).filter(ShiftRequest.id == request_id).first()
        if not request:
            raise ValueError("Solicitação não encontrada.")
        if request.target_user_id != current_user_id:
            raise ValueError("Apenas o usuário alvo pode responder a solicitação.")
        if request.status != ShiftRequestStatus.PENDING_TARGET:
            raise ValueError("Solicitação não está pendente de resposta do usuário alvo.")

        request.target_response_note = note
        request.status = ShiftRequestStatus.PENDING_ADMIN if accept else ShiftRequestStatus.REJECTED
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def admin_review(
        db: Session,
        request_id: int,
        admin_id: int,
        approve: bool,
        admin_notes: Optional[str] = None,
    ) -> ShiftRequest:
        request = db.query(ShiftRequest).filter(ShiftRequest.id == request_id).first()
        if not request:
            raise ValueError("Solicitação não encontrada.")

        admin = db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise ValueError("Somente administradores podem revisar solicitações.")

        if request.status != ShiftRequestStatus.PENDING_ADMIN:
            raise ValueError("Solicitação não está pendente de aprovação administrativa.")

        request.reviewed_by = admin_id
        request.admin_notes = admin_notes

        if not approve:
            request.status = ShiftRequestStatus.REJECTED
            db.commit()
            db.refresh(request)
            return request

        if request.target_shift_id:
            shift = db.query(Shift).filter(Shift.id == request.target_shift_id).first()
            if not shift:
                raise ValueError("Plantão alvo não encontrado para transferência.")
            shift.agent_id = request.requester_id
            shift.user_id = request.requester_id
        else:
            start, end = ShiftRequestService._period_to_datetimes(request.requested_date, request.shift_period)
            created_shift = Shift(
                agent_id=request.requester_id,
                user_id=request.requester_id,
                start_time=start,
                end_time=end,
                title=f"Plantão {request.shift_period}",
                description="Criado por aprovação de solicitação de plantão",
            )
            db.add(created_shift)

        request.status = ShiftRequestStatus.APPROVED
        db.commit()
        db.refresh(request)
        return request

    @staticmethod
    def cancel_request(db: Session, request_id: int, requester_id: int) -> ShiftRequest:
        request = db.query(ShiftRequest).filter(ShiftRequest.id == request_id).first()
        if not request:
            raise ValueError("Solicitação não encontrada.")
        if request.requester_id != requester_id:
            raise ValueError("Apenas quem solicitou pode cancelar.")
        if request.status not in {ShiftRequestStatus.PENDING_ADMIN, ShiftRequestStatus.PENDING_TARGET}:
            raise ValueError("Somente solicitações pendentes podem ser canceladas.")

        request.status = ShiftRequestStatus.CANCELLED
        db.commit()
        db.refresh(request)
        return request
