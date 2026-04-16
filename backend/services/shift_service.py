from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, time, timedelta
import sqlalchemy as sa
from sqlalchemy import and_, or_

from ..models import Shift, User
from .schedule_validation_service import validate_shift


class ShiftService:
    """Serviço para gerenciar turnos"""

    @staticmethod
    def _serialize_validation_errors(errors: List[dict]) -> str:
        details = []
        for error in errors:
            code = error.get("code", "VALIDATION_ERROR")
            message = error.get("message", "Erro de validação")
            details.append(f"{code}: {message}")
        return "; ".join(details)

    @staticmethod
    def _build_existing_shifts_for_validation(
        db: Session,
        agent_id: int,
        ignore_shift_id: Optional[int] = None,
    ) -> List[Shift]:
        query = db.query(Shift).filter(Shift.agent_id == agent_id)
        if ignore_shift_id is not None:
            query = query.filter(Shift.id != ignore_shift_id)
        return query.all()

    @staticmethod
    def create_shift(
        db: Session,
        agent_id: int,
        start_time: datetime,
        end_time: datetime,
        title: str = "Turno de trabalho",
        description: Optional[str] = None,
        location: Optional[str] = None,
        user_id: Optional[int] = None,
        legacy_agent_name: Optional[str] = None,
        validate_before_save: bool = True,
    ) -> Shift:
        """Criar um novo turno"""
        if validate_before_save:
            candidate = {
                "agent_id": agent_id,
                "start_time": start_time,
                "end_time": end_time,
            }
            existing_shifts = ShiftService._build_existing_shifts_for_validation(db, agent_id)
            validation_errors = validate_shift(candidate, existing_shifts=existing_shifts)
            if validation_errors:
                raise ValueError(ShiftService._serialize_validation_errors(validation_errors))

        shift = Shift(
            agent_id=agent_id,
            user_id=user_id if user_id is not None else agent_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            description=description,
            location=location,
            legacy_agent_name=legacy_agent_name,
        )
        db.add(shift)
        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def get_shift(db: Session, shift_id: int) -> Optional[Shift]:
        """Obter um turno pelo ID"""
        return db.query(Shift).filter(Shift.id == shift_id).first()

    @staticmethod
    def get_shifts_by_agent(db: Session, agent_id: int) -> List[Shift]:
        """Listar todos os turnos de um agente"""
        return db.query(Shift).filter(Shift.agent_id == agent_id).all()

    @staticmethod
    def get_shifts_for_user(
        db: Session,
        user_id: int,
        user_name: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Shift]:
        """Lista turnos do usuário logado, priorizando vínculo relacional."""
        has_unique_name = (
            db.query(sa.func.count(User.id))
            .filter(sa.func.lower(User.name) == user_name.strip().lower())
            .scalar()
            == 1
        )

        criteria = [
            Shift.user_id == user_id,
            Shift.agent_id == user_id,
        ]
        if has_unique_name:
            criteria.append(
                and_(
                    Shift.user_id.is_(None),
                    sa.func.lower(Shift.legacy_agent_name) == user_name.strip().lower(),
                )
            )

        query = db.query(Shift).filter(or_(*criteria))

        if start_date:
            query = query.filter(Shift.start_time >= datetime.combine(start_date, time.min))
        if end_date:
            exclusive_end = datetime.combine(end_date + timedelta(days=1), time.min)
            query = query.filter(Shift.start_time < exclusive_end)

        return query.order_by(Shift.start_time.asc()).all()

    @staticmethod
    def get_all_shifts(db: Session, skip: int = 0, limit: int = 100) -> List[Shift]:
        """Listar todos os turnos com paginação"""
        return db.query(Shift).offset(skip).limit(limit).all()

    @staticmethod
    def get_filtered_shifts(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 1000,
    ) -> List[Shift]:
        """
        Listar turnos para exportação com filtros opcionais por período.

        A regra fica centralizada no serviço para garantir que JSON, Excel e ICS
        exportem a mesma base de dados, com a mesma ordenação por início do turno.
        """
        query = db.query(Shift)

        # O filtro usa start_time porque a escala final é organizada pela data de início do plantão.
        if start_date:
            query = query.filter(Shift.start_time >= datetime.combine(start_date, time.min))

        if end_date:
            # Usar limite exclusivo no dia seguinte inclui todos os horários do end_date.
            exclusive_end = datetime.combine(end_date + timedelta(days=1), time.min)
            query = query.filter(Shift.start_time < exclusive_end)

        return query.order_by(Shift.start_time.asc()).offset(skip).limit(limit).all()

    @staticmethod
    def update_shift(
        db: Session,
        shift_id: int,
        validate_before_save: bool = True,
        **kwargs
    ) -> Optional[Shift]:
        """Atualizar um turno"""
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            return None

        candidate_payload = {
            "id": shift.id,
            "agent_id": kwargs.get("agent_id", shift.agent_id),
            "start_time": kwargs.get("start_time", shift.start_time),
            "end_time": kwargs.get("end_time", shift.end_time),
        }
        if validate_before_save:
            existing_shifts = ShiftService._build_existing_shifts_for_validation(
                db,
                candidate_payload["agent_id"],
                ignore_shift_id=shift.id,
            )
            validation_errors = validate_shift(candidate_payload, existing_shifts=existing_shifts)
            if validation_errors:
                raise ValueError(ShiftService._serialize_validation_errors(validation_errors))

        for key, value in kwargs.items():
            if hasattr(shift, key):
                setattr(shift, key, value)

        db.commit()
        db.refresh(shift)
        return shift

    @staticmethod
    def delete_shift(db: Session, shift_id: int) -> bool:
        """Excluir um turno"""
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            return False

        db.delete(shift)
        db.commit()
        return True

    @staticmethod
    def get_link_consistency_report(db: Session) -> dict:
        """Resumo de consistência entre vínculo relacional e dados legados por nome."""
        shifts = db.query(Shift).all()
        unresolved_user_link = [s.id for s in shifts if s.user_id is None and s.agent_id is None]
        legacy_name_only = [s.id for s in shifts if s.user_id is None and s.legacy_agent_name]
        no_link_data = [s.id for s in shifts if s.user_id is None and not s.legacy_agent_name]
        ambiguous_legacy_names = (
            db.query(Shift.legacy_agent_name)
            .filter(Shift.user_id.is_(None), Shift.legacy_agent_name.isnot(None))
            .group_by(Shift.legacy_agent_name)
            .having(sa.func.count(Shift.id) > 1)
            .all()
        )
        ambiguous_user_names = (
            db.query(User.name)
            .filter(User.is_active == True)  # noqa: E712
            .group_by(User.name)
            .having(sa.func.count(User.id) > 1)
            .all()
        )
        return {
            "total_shifts": len(shifts),
            "shifts_with_user_link": len([s for s in shifts if s.user_id is not None]),
            "legacy_name_only_shift_ids": legacy_name_only,
            "shifts_without_user_or_legacy_name": no_link_data,
            "shifts_without_any_relational_link": unresolved_user_link,
            "ambiguous_legacy_names": [name for (name,) in ambiguous_legacy_names],
            "ambiguous_user_names": [name for (name,) in ambiguous_user_names],
            "note": "Fallback por nome é temporário (legacy_agent_name). Priorize user_id.",
        }
