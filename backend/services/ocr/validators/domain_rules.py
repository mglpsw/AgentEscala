"""Regras de domínio seguras para normalização/validação de plantões.

Módulo ainda não conectado ao fluxo principal.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def normalize_doctor_name(name: str | None) -> str | None:
    """Normaliza nome médico sem alterar identidade semântica."""
    if name is None:
        return None
    compact = re.sub(r"\s+", " ", name.strip())
    return compact.upper() if compact else None


def normalize_shift_time(value: str | None) -> str | None:
    """Normaliza horário para HH:MM quando possível."""
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None

    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%H:%M")
        except ValueError:
            continue

    return raw


def validate_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    """True quando existe sobreposição de intervalos."""
    return start_a < end_b and start_b < end_a


def validate_duplicate(candidate: dict[str, Any], existing: dict[str, Any]) -> bool:
    """True quando registros representam o mesmo plantão lógico."""
    return (
        normalize_doctor_name(candidate.get("profissional")) == normalize_doctor_name(existing.get("profissional"))
        and candidate.get("data") == existing.get("data")
        and normalize_shift_time(candidate.get("hora_inicio")) == normalize_shift_time(existing.get("hora_inicio"))
        and normalize_shift_time(candidate.get("hora_fim")) == normalize_shift_time(existing.get("hora_fim"))
    )


def validate_invalid_duration(start: datetime, end: datetime) -> bool:
    """True quando a duração é inválida (fim <= início)."""
    return end <= start
