from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from ..config.database import Base


class UserRole(str, enum.Enum):
    """Papéis de usuário no sistema"""
    ADMIN = "admin"
    AGENT = "agent"


class SwapStatus(str, enum.Enum):
    """Status de uma solicitação de troca"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class User(Base):
    """Modelo de usuário que representa agentes e administradores"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.AGENT, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    shifts = relationship("Shift", back_populates="agent", foreign_keys="Shift.agent_id")
    swap_requests_initiated = relationship(
        "SwapRequest",
        back_populates="requester",
        foreign_keys="SwapRequest.requester_id"
    )
    swap_requests_received = relationship(
        "SwapRequest",
        back_populates="target_agent",
        foreign_keys="SwapRequest.target_agent_id"
    )


class Shift(Base):
    """Modelo de turno que representa períodos de trabalho"""
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    title = Column(String, default="Turno de trabalho")
    description = Column(String, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    agent = relationship("User", back_populates="shifts", foreign_keys=[agent_id])
    swap_requests_origin = relationship(
        "SwapRequest",
        back_populates="origin_shift",
        foreign_keys="SwapRequest.origin_shift_id"
    )
    swap_requests_target = relationship(
        "SwapRequest",
        back_populates="target_shift",
        foreign_keys="SwapRequest.target_shift_id"
    )


class SwapRequest(Base):
    """Modelo SwapRequest para o fluxo de troca de turnos"""
    __tablename__ = "swap_requests"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_agent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    origin_shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    target_shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    status = Column(SQLEnum(SwapStatus), default=SwapStatus.PENDING, nullable=False)
    reason = Column(String, nullable=True)
    admin_notes = Column(String, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relacionamentos
    requester = relationship("User", back_populates="swap_requests_initiated", foreign_keys=[requester_id])
    target_agent = relationship("User", back_populates="swap_requests_received", foreign_keys=[target_agent_id])
    origin_shift = relationship("Shift", back_populates="swap_requests_origin", foreign_keys=[origin_shift_id])
    target_shift = relationship("Shift", back_populates="swap_requests_target", foreign_keys=[target_shift_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
