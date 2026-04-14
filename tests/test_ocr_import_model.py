"""Testes mínimos de smoke para o modelo OcrImport (E2)."""
import uuid
from datetime import datetime

import pytest

from backend.models import OcrImport


def test_ocr_import_importable():
    """OcrImport pode ser importado do pacote models."""
    assert OcrImport.__tablename__ == "ocr_imports"


def test_ocr_import_columns():
    """Todas as colunas especificadas existem na tabela."""
    expected = {
        "id", "status", "file_name", "file_type",
        "raw_payload", "parsed_rows", "errors", "action_log",
        "created_by", "confirmed_by", "created_at", "confirmed_at",
    }
    actual = {c.name for c in OcrImport.__table__.columns}
    assert expected == actual


def test_ocr_import_instantiation():
    """Instancia OcrImport sem persistir — SQLAlchemy aplica defaults no INSERT,
    portanto setamos os valores explicitamente aqui."""
    row = OcrImport(
        id=str(uuid.uuid4()),
        status="draft",
        file_name="escala_abril.pdf",
        file_type="pdf",
    )
    assert row.status == "draft"
    uuid.UUID(row.id)                        # id é um UUID válido
    assert row.file_name == "escala_abril.pdf"
    assert row.parsed_rows is None
    assert row.confirmed_at is None


def test_ocr_import_repr():
    """__repr__ não lança exceção."""
    row = OcrImport(id=str(uuid.uuid4()), status="draft",
                    file_name="test.csv", file_type="csv")
    r = repr(row)
    assert "OcrImport" in r
    assert "draft" in r


def test_ocr_import_fk_columns_are_integer():
    """created_by e confirmed_by são Integer (batem com users.id)."""
    from sqlalchemy import Integer
    cols = {c.name: c for c in OcrImport.__table__.columns}
    assert isinstance(cols["created_by"].type, Integer)
    assert isinstance(cols["confirmed_by"].type, Integer)


def test_ocr_import_relationships():
    """Relacionamentos 'creator' e 'confirmer' estão configurados."""
    from sqlalchemy.orm import RelationshipProperty
    mapper = OcrImport.__mapper__
    assert "creator" in mapper.relationships
    assert "confirmer" in mapper.relationships
    assert mapper.relationships["creator"].uselist is False
    assert mapper.relationships["confirmer"].uselist is False
