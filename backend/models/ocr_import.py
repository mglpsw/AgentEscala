import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from ..config.database import Base


class OcrImport(Base):
    """Modelo para importação de escala via OCR ou arquivo estruturado."""

    __tablename__ = "ocr_imports"

    # String(36) é compatível com SQLite (testes) e PostgreSQL; a migração
    # usa postgresql.UUID para o tipo nativo em produção.
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="draft", nullable=False)
    # valores possíveis: "draft", "confirmed", "discarded"

    file_name = Column(String, nullable=True)
    file_type = Column(String, nullable=True)
    source_origin = Column(String, nullable=True)
    processing_strategy = Column(String, nullable=True)
    # valores possíveis para file_type: "pdf", "image", "xlsx", "csv"

    # Payload bruto extraído antes do parsing
    raw_payload = Column(JSON, nullable=True)

    # Lista de linhas parseadas — estrutura documentada no schema OcrRow
    parsed_rows = Column(JSON, nullable=True)

    # Erros globais do parse: [{"code": str, "message": str, "row_id": str|null}]
    errors = Column(JSON, nullable=True)

    # Trilha de edições manuais: [{"user_id", "timestamp", "row_id", "field",
    #                               "old_value", "new_value"}]
    action_log = Column(JSON, nullable=True)
    extracted_lines = Column(Integer, nullable=False, default=0)
    valid_lines = Column(Integer, nullable=False, default=0)
    ambiguous_lines = Column(Integer, nullable=False, default=0)
    conflict_lines = Column(Integer, nullable=False, default=0)

    # users.id é Integer — FK deve respeitar o tipo da PK referenciada
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    confirmed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)

    # Relacionamentos
    creator = relationship("User", foreign_keys=[created_by], uselist=False)
    confirmer = relationship("User", foreign_keys=[confirmed_by], uselist=False)

    def __repr__(self) -> str:
        return f"<OcrImport id={self.id} status={self.status!r} file={self.file_name!r}>"
