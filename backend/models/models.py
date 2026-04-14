from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text
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


# ─── Import Schedule ────────────────────────────────────

class ImportStatus(str, enum.Enum):
    """Status de um lote de importação de escala"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RowStatus(str, enum.Enum):
    """Status individual de uma linha importada"""
    VALID = "valid"
    WARNING = "warning"    # inconsistência não fatal – importável com ressalva
    INVALID = "invalid"    # erro fatal – não pode ser importado


class ScheduleImport(Base):
    """Lote de importação de escala anterior"""
    __tablename__ = "schedule_imports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    reference_period = Column(String, nullable=True)   # ex.: "2026-03" ou "Março 2026"
    source_description = Column(String, nullable=True)
    status = Column(SQLEnum(ImportStatus), default=ImportStatus.PENDING, nullable=False)

    # Contadores de resumo
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    warning_rows = Column(Integer, default=0, nullable=False)
    invalid_rows = Column(Integer, default=0, nullable=False)
    duplicate_rows = Column(Integer, default=0, nullable=False)

    imported_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    rows = relationship("ScheduleImportRow", back_populates="schedule_import", cascade="all, delete-orphan")
    importer = relationship("User", foreign_keys=[imported_by])
    confirmer = relationship("User", foreign_keys=[confirmed_by])


class ScheduleImportRow(Base):
    """Linha individual de uma importação de escala (staging)"""
    __tablename__ = "schedule_import_rows"

    id = Column(Integer, primary_key=True, index=True)
    import_id = Column(Integer, ForeignKey("schedule_imports.id"), nullable=False)
    row_number = Column(Integer, nullable=False)

    # Dados brutos do arquivo
    raw_professional = Column(String, nullable=True)
    raw_date = Column(String, nullable=True)
    raw_start_time = Column(String, nullable=True)
    raw_end_time = Column(String, nullable=True)
    raw_total_hours = Column(String, nullable=True)
    raw_observations = Column(String, nullable=True)
    raw_source = Column(String, nullable=True)

    # Dados normalizados
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    normalized_start = Column(DateTime, nullable=True)
    normalized_end = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    is_overnight = Column(Boolean, default=False, nullable=False)
    is_standard_shift = Column(Boolean, default=False, nullable=False)

    # Diagnóstico
    row_status = Column(SQLEnum(RowStatus), default=RowStatus.VALID, nullable=False)
    issues = Column(Text, nullable=True)   # JSON: lista de strings descrevendo problemas
    is_duplicate = Column(Boolean, default=False, nullable=False)
    has_overlap = Column(Boolean, default=False, nullable=False)

    # Shift criado após confirmação
    created_shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    schedule_import = relationship("ScheduleImport", back_populates="rows")
    agent = relationship("User", foreign_keys=[agent_id])
    created_shift = relationship("Shift", foreign_keys=[created_shift_id])
