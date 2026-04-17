"""Serviço OCR base (não integrado ao pipeline atual)."""

from __future__ import annotations

from typing import Any, BinaryIO

from .parsers.pdf_parser import parse_pdf_to_schedule_rows
from .validators.domain_rules import normalize_doctor_name, normalize_shift_time


def extract_schedule_from_pdf(file: BinaryIO | bytes) -> dict[str, Any]:
    """Extrai estrutura de escala de um PDF e retorna JSON serializável.

    IMPORTANTE: função preparada para uso futuro, sem ativação de endpoint.
    """
    if hasattr(file, "read"):
        file_content = file.read()
    else:
        file_content = file

    rows, errors = parse_pdf_to_schedule_rows(file_content)

    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(
            {
                "profissional": normalize_doctor_name(row.get("profissional")),
                "data": row.get("data"),
                "hora_inicio": normalize_shift_time(row.get("hora_inicio")),
                "hora_fim": normalize_shift_time(row.get("hora_fim")),
                "observacoes": row.get("observacoes"),
            }
        )

    return {
        "source": "pdf",
        "rows": normalized_rows,
        "errors": errors,
        "total_rows": len(normalized_rows),
    }
