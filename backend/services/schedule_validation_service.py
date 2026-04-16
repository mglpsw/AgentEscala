from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..config.settings import settings


@dataclass
class _ShiftInput:
    agent_id: Optional[int]
    start_time: datetime
    end_time: datetime
    shift_id: Optional[int]
    source: str


def _parse_shift_input(raw_shift: Any, source: str = "payload") -> Tuple[Optional[_ShiftInput], List[Dict[str, Any]]]:
    """Converte diferentes formatos de turno em estrutura única sem lançar exceções."""
    errors: List[Dict[str, Any]] = []

    def _get(field: str, default: Any = None) -> Any:
        if isinstance(raw_shift, dict):
            return raw_shift.get(field, default)
        return getattr(raw_shift, field, default)

    agent_id = _get("agent_id")
    start_time = _get("start_time")
    end_time = _get("end_time")
    shift_id = _get("id") or _get("shift_id")

    if agent_id is None:
        errors.append(
            {
                "code": "MISSING_AGENT_ID",
                "message": "agent_id é obrigatório para validação de escala.",
                "source": source,
                "shift_id": shift_id,
            }
        )

    if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
        errors.append(
            {
                "code": "INVALID_DATETIME",
                "message": "start_time e end_time devem ser datetimes válidos.",
                "source": source,
                "shift_id": shift_id,
                "agent_id": agent_id,
            }
        )
        return None, errors

    return _ShiftInput(agent_id=agent_id, start_time=start_time, end_time=end_time, shift_id=shift_id, source=source), errors


def _interval_overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _split_hours_by_day(start: datetime, end: datetime) -> Dict[datetime.date, float]:
    """Divide a duração do turno por dia de calendário para cálculo de carga diária/semanal."""
    remaining_start = start
    result: Dict[datetime.date, float] = {}

    while remaining_start < end:
        next_midnight = datetime.combine(remaining_start.date() + timedelta(days=1), datetime.min.time())
        segment_end = min(end, next_midnight)
        hours = (segment_end - remaining_start).total_seconds() / 3600
        result[remaining_start.date()] = result.get(remaining_start.date(), 0.0) + hours
        remaining_start = segment_end

    return result


def validate_schedule(
    shifts: Iterable[Any],
    max_daily_hours: Optional[float] = None,
    max_weekly_hours: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Valida uma coleção de turnos e retorna lista detalhada de erros."""
    daily_limit = max_daily_hours if max_daily_hours is not None else settings.SCHEDULE_MAX_DAILY_HOURS
    weekly_limit = max_weekly_hours if max_weekly_hours is not None else settings.SCHEDULE_MAX_WEEKLY_HOURS

    parsed: List[_ShiftInput] = []
    errors: List[Dict[str, Any]] = []

    for index, raw_shift in enumerate(shifts):
        shift, parse_errors = _parse_shift_input(raw_shift, source=f"shifts[{index}]")
        errors.extend(parse_errors)
        if shift is None:
            continue

        if shift.end_time <= shift.start_time:
            errors.append(
                {
                    "code": "INVALID_TIME_RANGE",
                    "message": "end_time deve ser maior que start_time.",
                    "source": shift.source,
                    "shift_id": shift.shift_id,
                    "agent_id": shift.agent_id,
                    "start_time": shift.start_time.isoformat(),
                    "end_time": shift.end_time.isoformat(),
                }
            )
            continue

        parsed.append(shift)

    by_agent: Dict[int, List[_ShiftInput]] = {}
    for shift in parsed:
        by_agent.setdefault(shift.agent_id, []).append(shift)

    for agent_id, agent_shifts in by_agent.items():
        sorted_shifts = sorted(agent_shifts, key=lambda s: s.start_time)

        # Conflitos de horário
        for i, current in enumerate(sorted_shifts):
            for candidate in sorted_shifts[i + 1:]:
                if candidate.start_time >= current.end_time:
                    break
                if _interval_overlap(current.start_time, current.end_time, candidate.start_time, candidate.end_time):
                    errors.append(
                        {
                            "code": "OVERLAPPING_SHIFTS",
                            "message": "Usuário com plantões sobrepostos no mesmo período.",
                            "agent_id": agent_id,
                            "shift_id": current.shift_id,
                            "other_shift_id": candidate.shift_id,
                            "source": f"{current.source} ↔ {candidate.source}",
                            "interval_a": {
                                "start": current.start_time.isoformat(),
                                "end": current.end_time.isoformat(),
                            },
                            "interval_b": {
                                "start": candidate.start_time.isoformat(),
                                "end": candidate.end_time.isoformat(),
                            },
                        }
                    )

        # Carga diária e semanal
        hours_per_day: Dict[datetime.date, float] = {}
        for shift in sorted_shifts:
            for day_key, hours in _split_hours_by_day(shift.start_time, shift.end_time).items():
                hours_per_day[day_key] = hours_per_day.get(day_key, 0.0) + hours

        hours_per_week: Dict[Tuple[int, int], float] = {}
        for day_key, hours in hours_per_day.items():
            iso_year, iso_week, _ = day_key.isocalendar()
            week_key = (iso_year, iso_week)
            hours_per_week[week_key] = hours_per_week.get(week_key, 0.0) + hours

            if hours_per_day[day_key] > daily_limit:
                errors.append(
                    {
                        "code": "DAILY_HOURS_EXCEEDED",
                        "message": "Carga horária diária excede o limite configurado.",
                        "agent_id": agent_id,
                        "date": day_key.isoformat(),
                        "hours": round(hours_per_day[day_key], 2),
                        "limit": daily_limit,
                    }
                )

        for (iso_year, iso_week), week_hours in hours_per_week.items():
            if week_hours > weekly_limit:
                errors.append(
                    {
                        "code": "WEEKLY_HOURS_EXCEEDED",
                        "message": "Carga horária semanal excede o limite configurado.",
                        "agent_id": agent_id,
                        "iso_year": iso_year,
                        "iso_week": iso_week,
                        "hours": round(week_hours, 2),
                        "limit": weekly_limit,
                    }
                )

    return errors


def validate_shift(
    shift: Any,
    existing_shifts: Optional[Iterable[Any]] = None,
    max_daily_hours: Optional[float] = None,
    max_weekly_hours: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Valida um turno individualmente (incluindo comparação contra turnos existentes)."""
    candidate_marker = "__candidate__"

    candidate_dict: Dict[str, Any]
    if isinstance(shift, dict):
        candidate_dict = dict(shift)
    else:
        candidate_dict = {
            "id": getattr(shift, "id", None),
            "agent_id": getattr(shift, "agent_id", None),
            "start_time": getattr(shift, "start_time", None),
            "end_time": getattr(shift, "end_time", None),
        }

    if candidate_dict.get("id") is None:
        candidate_dict["id"] = candidate_marker

    all_shifts: List[Any] = list(existing_shifts or []) + [candidate_dict]
    all_errors = validate_schedule(
        all_shifts,
        max_daily_hours=max_daily_hours,
        max_weekly_hours=max_weekly_hours,
    )

    filtered: List[Dict[str, Any]] = []
    for error in all_errors:
        if error.get("shift_id") == candidate_marker or error.get("other_shift_id") == candidate_marker:
            normalized = dict(error)
            if normalized.get("shift_id") == candidate_marker:
                normalized["shift_id"] = None
            if normalized.get("other_shift_id") == candidate_marker:
                normalized["other_shift_id"] = None
            filtered.append(normalized)
            continue

        source = str(error.get("source", ""))
        if "shifts[" in source and source.endswith(f"{len(all_shifts) - 1}]"):
            filtered.append(error)

    return filtered
