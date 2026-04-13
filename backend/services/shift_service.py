from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..models import Shift, User


class ShiftService:
    """Serviço para gerenciar turnos"""

    @staticmethod
    def create_shift(
        db: Session,
        agent_id: int,
        start_time: datetime,
        end_time: datetime,
        title: str = "Turno de trabalho",
        description: Optional[str] = None,
        location: Optional[str] = None
    ) -> Shift:
        """Criar um novo turno"""
        shift = Shift(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            description=description,
            location=location
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
    def get_all_shifts(db: Session, skip: int = 0, limit: int = 100) -> List[Shift]:
        """Listar todos os turnos com paginação"""
        return db.query(Shift).offset(skip).limit(limit).all()

    @staticmethod
    def update_shift(
        db: Session,
        shift_id: int,
        **kwargs
    ) -> Optional[Shift]:
        """Atualizar um turno"""
        shift = db.query(Shift).filter(Shift.id == shift_id).first()
        if not shift:
            return None

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
