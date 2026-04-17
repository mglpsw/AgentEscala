"""Schemas de apoio para a base de OCR (pré-integração)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OCRScheduleRow:
    """Representa uma linha de plantão extraída de OCR."""

    profissional: str | None
    data: str | None
    hora_inicio: str | None
    hora_fim: str | None
    observacoes: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRExtractionResult:
    """Payload padrão da extração OCR, sem acoplamento ao fluxo atual."""

    rows: list[OCRScheduleRow]
    errors: list[dict[str, str]] = field(default_factory=list)
