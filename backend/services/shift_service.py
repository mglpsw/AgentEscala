from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, datetime, time, timedelta
import sqlalchemy as sa
from sqlalchemy import and_, or_

from ..models import Shift, User
from .schedule_validation_service import validate_shift

PLANTAO_TYPE_RULES = {
    "12H DIA": (8, 20),
    "12H NOITE": (20, 8),
    "10-22H": (10, 22),
    "24 HORAS": (0, 0),
}


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
    def get_shifts_by_agent(
        db: Session,
        agent_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Shift]:
        """Listar todos os turnos de um agente com filtro opcional por período."""
        query = db.query(Shift).filter(Shift.agent_id == agent_id)
        if start_date:
            query = query.filter(Shift.start_time >= datetime.combine(start_date, time.min))
        if end_date:
            exclusive_end = datetime.combine(end_date + timedelta(days=1), time.min)
            query = query.filter(Shift.start_time < exclusive_end)
        return query.order_by(Shift.start_time.asc()).all()

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
    def get_all_shifts(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Shift]:
        """Listar todos os turnos com paginação e filtro opcional por período."""
        query = db.query(Shift)
        if start_date:
            query = query.filter(Shift.start_time >= datetime.combine(start_date, time.min))
        if end_date:
            exclusive_end = datetime.combine(end_date + timedelta(days=1), time.min)
            query = query.filter(Shift.start_time < exclusive_end)
        return query.order_by(Shift.start_time.asc()).offset(skip).limit(limit).all()

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

    @staticmethod
    def infer_plantao_type(shift: Shift) -> str | None:
        start_hour = shift.start_time.hour
        end_hour = shift.end_time.hour
        duration_hours = int((shift.end_time - shift.start_time).total_seconds() // 3600)

        if duration_hours >= 23:
            return "24 HORAS"
        if start_hour == 8 and end_hour == 20:
            return "12H DIA"
        if start_hour == 20 and end_hour in {7, 8}:
            return "12H NOITE"
        if start_hour == 10 and end_hour == 22:
            return "10-22H"
        title = (shift.title or "").upper().strip()
        return title if title in PLANTAO_TYPE_RULES else None

    @staticmethod
    def get_daily_coverage_flags(
        db: Session,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        query = ShiftService.get_filtered_shifts(db, start_date=start_date, end_date=end_date, skip=0, limit=5000)
        grouped: dict[str, dict] = {}

        cursor = start_date
        while cursor <= end_date:
            key = cursor.isoformat()
            grouped[key] = {
                "date": key,
                "counts": {"12H DIA": 0, "10-22H": 0, "12H NOITE": 0},
                "required": {"12H DIA": 2, "10-22H": 1, "12H NOITE": 1},
            }
            cursor += timedelta(days=1)

        for shift in query:
            day_key = shift.start_time.date().isoformat()
            if day_key not in grouped:
                continue
            plantao_type = ShiftService.infer_plantao_type(shift)
            if plantao_type in grouped[day_key]["counts"]:
                grouped[day_key]["counts"][plantao_type] += 1

        result: list[dict] = []
        for item in grouped.values():
            counts = item["counts"]
            required = item["required"]
            missing = {
                key: max(required[key] - counts.get(key, 0), 0)
                for key in required
            }
            item["complete"] = all(missing[key] == 0 for key in missing)
            item["missing"] = missing
            result.append(item)

        return result


    @staticmethod
    def get_dynamic_day_slots(
        db: Session,
        start_date: date,
        end_date: date,
    ) -> list[dict]:
        """Configuração dinâmica de turnos por dia com limite de médicos por tipo de plantão."""
        flags = ShiftService.get_daily_coverage_flags(db, start_date, end_date)
        shifts = ShiftService.get_filtered_shifts(db, start_date=start_date, end_date=end_date, skip=0, limit=5000)

        indexed: dict[str, dict[str, list[dict]]] = {}
        for item in flags:
            indexed[item["date"]] = {
                "12H DIA": [],
                "10-22H": [],
                "12H NOITE": [],
                "24 HORAS": [],
            }

        for shift in shifts:
            day_key = shift.start_time.date().isoformat()
            if day_key not in indexed:
                continue
            plantao_type = ShiftService.infer_plantao_type(shift) or "24 HORAS"
            if plantao_type not in indexed[day_key]:
                indexed[day_key][plantao_type] = []
            indexed[day_key][plantao_type].append({
                "shift_id": shift.id,
                "agent_id": shift.agent_id,
                "agent_name": shift.agent.name if shift.agent else shift.legacy_agent_name,
                "start_time": shift.start_time.isoformat(),
                "end_time": shift.end_time.isoformat(),
            })

        response: list[dict] = []
        for item in flags:
            date_key = item["date"]
            required = item["required"]
            slots = []
            for period, required_count in required.items():
                occupied = indexed[date_key].get(period, [])
                slots.append({
                    "period": period,
                    "max_doctors": required_count,
                    "occupied_count": len(occupied),
                    "remaining": max(required_count - len(occupied), 0),
                    "occupied_shifts": occupied,
                })
            response.append({"date": date_key, "slots": slots})

        return response
