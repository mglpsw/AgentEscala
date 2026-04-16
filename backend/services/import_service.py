"""Serviço de importação de escala base.

Separa claramente:
  1. leitura do arquivo (CSV / Excel)
  2. parsing tabular
  3. normalização de turnos
  4. validação de consistência
  5. detecção de duplicatas e sobreposições
  6. persistência no banco (staging)
  7. confirmação: staging → Shift
  8. resumo da importação
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..models.models import (
    ImportStatus,
    RowStatus,
    ScheduleImport,
    ScheduleImportRow,
    Shift,
    User,
)

from .schedule_validation_service import validate_shift

logger = logging.getLogger("agentescala.import_service")

# ─── Turnos padrão reconhecidos ──────────────────────────────────────────────
# (hora_inicio, hora_fim_no_mesmo_dia_ou_proximo)
STANDARD_SHIFTS: List[Tuple[time, time]] = [
    (time(8, 0),  time(20, 0)),
    (time(20, 0), time(8, 0)),   # vira dia
    (time(10, 0), time(22, 0)),
]

# ─── Aliases de colunas aceitos ──────────────────────────────────────────────
_COL_ALIASES: Dict[str, List[str]] = {
    "profissional":  ["profissional", "professional", "nome", "name", "agente", "agent", "colaborador"],
    "data":          ["data", "date", "data_turno", "shift_date", "dia_data"],
    "dia_semana":    ["dia_semana", "dia", "day", "weekday", "semana"],
    "hora_inicio":   ["hora_inicio", "hora_inicial", "start_time", "inicio", "start", "start_hour",
                      "hora de inicio", "hora de início", "início"],
    "hora_fim":      ["hora_fim", "hora_final", "end_time", "fim", "end", "end_hour",
                      "hora de fim", "hora de termino", "hora de término", "término"],
    "total_horas":   ["total_horas", "horas", "hours", "duration", "duracao", "duração", "total"],
    "observacoes":   ["observacoes", "observação", "observacoes", "obs", "notes", "nota",
                      "observations", "observação"],
    "origem":        ["origem", "source", "origin", "fonte"],
}


def _build_column_map(headers: List[Any]) -> Dict[str, str]:
    """Mapeia cabeçalhos reais do arquivo para nomes canônicos."""
    norm = {str(h).strip().lower() if h else "": str(h) for h in headers}
    result: Dict[str, str] = {}
    for canonical, aliases in _COL_ALIASES.items():
        for alias in aliases:
            if alias in norm:
                result[canonical] = norm[alias]
                break
    return result


# ─── Parsing de data ─────────────────────────────────────────────────────────

_DATE_FORMATS = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y", "%d.%m.%Y"]


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    # Tenta conversão para int (número serial do Excel)
    try:
        serial = int(float(raw))
        # Excel date serial: 1 = 1900-01-01
        base = date(1899, 12, 30)
        return base + timedelta(days=serial)
    except (ValueError, TypeError):
        pass
    return None


# ─── Parsing de hora ─────────────────────────────────────────────────────────

_TIME_FORMATS = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M%p"]


def _parse_time(raw: Optional[Any]) -> Optional[time]:
    if raw is None:
        return None
    # openpyxl pode devolver um objeto time diretamente
    if isinstance(raw, time):
        return raw
    if isinstance(raw, datetime):
        return raw.time()
    raw = str(raw).strip()
    if not raw:
        return None
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt).time()
        except ValueError:
            pass
    return None


# ─── Leitura de arquivo ───────────────────────────────────────────────────────

def _read_csv(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    text = content.decode("utf-8-sig", errors="replace")
    # Detecta separador
    sep = ";"
    first_line = text.split("\n")[0]
    if first_line.count(",") >= first_line.count(";"):
        sep = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=sep)
    headers = reader.fieldnames or []
    rows = list(reader)
    return list(headers), rows


def _read_excel(content: bytes) -> Tuple[List[str], List[Dict[str, Any]]]:
    wb = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    if ws is None:
        return [], []
    rows_iter = ws.iter_rows(values_only=True)
    headers_raw = next(rows_iter, None)
    if not headers_raw:
        return [], []
    headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(headers_raw)]
    rows: List[Dict[str, Any]] = []
    for row in rows_iter:
        rows.append(dict(zip(headers, row)))
    wb.close()
    return headers, rows


def read_file(content: bytes, filename: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    fn_lower = filename.lower()
    if fn_lower.endswith(".xlsx") or fn_lower.endswith(".xls"):
        return _read_excel(content)
    return _read_csv(content)


# ─── Matching de profissional ─────────────────────────────────────────────────

def _find_agent(db: Session, name: Optional[str]) -> Tuple[Optional[User], List[str]]:
    if not name:
        return None, ["Profissional não informado"]
    name_clean = name.strip().lower()
    # Busca exata de nome (case-insensitive) ou email
    users: List[User] = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    # Exact match
    for u in users:
        if u.name.lower() == name_clean or u.email.lower() == name_clean:
            return u, []
    # Partial match
    matches = [u for u in users if name_clean in u.name.lower() or u.name.lower() in name_clean]
    if len(matches) == 1:
        return matches[0], [f"Profissional '{name}' resolvido por correspondência parcial com '{matches[0].name}'"]
    if len(matches) > 1:
        names = ", ".join(u.name for u in matches)
        return None, [f"Profissional '{name}' ambíguo: múltiplas correspondências ({names})"]
    return None, [f"Profissional '{name}' não encontrado no sistema"]


# ─── Normalização de turno ────────────────────────────────────────────────────

def _normalize_shift(
    shift_date: date,
    t_start: time,
    t_end: time,
) -> Tuple[datetime, datetime, int, bool, bool]:
    """
    Retorna (normalized_start, normalized_end, duration_minutes, is_overnight, is_standard).
    Trata virada de dia quando t_end <= t_start.
    """
    dt_start = datetime.combine(shift_date, t_start)
    dt_end = datetime.combine(shift_date, t_end)
    is_overnight = False
    if t_end <= t_start:
        dt_end += timedelta(days=1)
        is_overnight = True
    duration = int((dt_end - dt_start).total_seconds() / 60)
    is_standard = (t_start, t_end) in STANDARD_SHIFTS
    return dt_start, dt_end, duration, is_overnight, is_standard


# ─── Validação de linha ───────────────────────────────────────────────────────

def _validate_row(
    row_num: int,
    raw: Dict[str, Any],
    col_map: Dict[str, str],
    db: Session,
) -> Dict[str, Any]:
    """
    Valida e normaliza uma linha do arquivo.
    Retorna dicionário com campos normalizados e lista de issues.
    row_status: VALID / WARNING / INVALID
    """
    issues: List[str] = []
    fatal = False

    def get_raw(canonical: str) -> Optional[str]:
        mapped_col = col_map.get(canonical)
        if not mapped_col:
            return None
        val = raw.get(mapped_col)
        return str(val).strip() if val is not None and str(val).strip() else None

    raw_professional = get_raw("profissional")
    raw_date_str = get_raw("data")
    raw_start = get_raw("hora_inicio")
    raw_end = get_raw("hora_fim")
    raw_hours = get_raw("total_horas")
    raw_obs = get_raw("observacoes")
    raw_src = get_raw("origem")

    # Profissional
    agent, agent_issues = _find_agent(db, raw_professional)
    issues.extend(agent_issues)
    if agent is None and not agent_issues:
        issues.append("Profissional inválido")
    if agent is None and raw_professional:
        # Profissional não resolvido - é um alerta mas não necessariamente fatal
        # (pode ser importado manualmente depois da confirmação)
        issues.append("Linha não poderá ser confirmada sem profissional válido")

    # Data
    parsed_date = _parse_date(raw_date_str)
    if parsed_date is None:
        issues.append(f"Data inválida ou ausente: '{raw_date_str}'")
        fatal = True

    # Horas
    t_start: Optional[time] = None
    t_end: Optional[time] = None

    # Para xlsx, o campo pode já ser um time object
    raw_start_raw = raw.get(col_map.get("hora_inicio", "")) if col_map.get("hora_inicio") else None
    raw_end_raw = raw.get(col_map.get("hora_fim", "")) if col_map.get("hora_fim") else None

    t_start = _parse_time(raw_start_raw) if raw_start_raw is not None else _parse_time(raw_start)
    t_end = _parse_time(raw_end_raw) if raw_end_raw is not None else _parse_time(raw_end)

    if t_start is None:
        issues.append(f"Hora inicial inválida ou ausente: '{raw_start}'")
        fatal = True
    if t_end is None:
        issues.append(f"Hora final inválida ou ausente: '{raw_end}'")
        fatal = True

    # Normalização
    normalized_start = normalized_end = None
    duration_minutes = None
    is_overnight = is_standard = False

    if parsed_date and t_start and t_end:
        normalized_start, normalized_end, duration_minutes, is_overnight, is_standard = _normalize_shift(
            parsed_date, t_start, t_end
        )
        # Valida duração declarada
        if raw_hours:
            try:
                declared_h = float(raw_hours.replace(",", ".").replace("h", "").strip())
                declared_min = int(declared_h * 60)
                if abs(declared_min - duration_minutes) > 10:
                    issues.append(
                        f"Duração declarada ({declared_h}h) diverge do calculado "
                        f"({duration_minutes // 60}h{duration_minutes % 60:02d}min)"
                    )
            except (ValueError, AttributeError):
                pass

        # Duração suspeita (< 30 min ou > 24h)
        if duration_minutes < 30:
            issues.append(f"Duração muito curta: {duration_minutes} min")
            fatal = True
        elif duration_minutes > 24 * 60:
            issues.append(f"Duração excede 24h: {duration_minutes} min — possível erro na virada de dia")
            fatal = True

    row_status = RowStatus.INVALID if fatal else (RowStatus.WARNING if issues else RowStatus.VALID)

    return {
        "row_number": row_num,
        "raw_professional": raw_professional,
        "raw_date": raw_date_str,
        "raw_start_time": raw_start,
        "raw_end_time": raw_end,
        "raw_total_hours": raw_hours,
        "raw_observations": raw_obs,
        "raw_source": raw_src,
        "agent_id": agent.id if agent else None,
        "normalized_start": normalized_start,
        "normalized_end": normalized_end,
        "duration_minutes": duration_minutes,
        "is_overnight": is_overnight,
        "is_standard_shift": is_standard,
        "row_status": row_status,
        "issues": json.dumps(issues) if issues else None,
        "is_duplicate": False,
        "has_overlap": False,
    }


# ─── Detecção de duplicatas e sobreposições ────────────────────────────────────

def _detect_duplicates_and_overlaps(validated: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Marca duplicatas e sobreposições intra-lote (mesmos dados ou mesmo agente/período)."""
    seen: Dict[Tuple, int] = {}  # (agent_id, start, end) → row_number

    for row in validated:
        if row["row_status"] == RowStatus.INVALID:
            continue
        aid = row["agent_id"]
        s = row["normalized_start"]
        e = row["normalized_end"]
        if aid is None or s is None or e is None:
            continue

        key = (aid, s, e)
        if key in seen:
            row["is_duplicate"] = True
            issues_list = json.loads(row["issues"]) if row["issues"] else []
            issues_list.append(f"Possível duplicata da linha {seen[key]}")
            row["issues"] = json.dumps(issues_list)
            if row["row_status"] == RowStatus.VALID:
                row["row_status"] = RowStatus.WARNING
        else:
            seen[key] = row["row_number"]

    # Sobreposição: mesmo agente, intervalos que se intersectam mas não são idênticos
    by_agent: Dict[int, List[Dict[str, Any]]] = {}
    for row in validated:
        if row["agent_id"] and row["normalized_start"] and row["normalized_end"]:
            by_agent.setdefault(row["agent_id"], []).append(row)

    for agent_rows in by_agent.values():
        for i, a in enumerate(agent_rows):
            for b in agent_rows[i + 1:]:
                if a["is_duplicate"] or b["is_duplicate"]:
                    continue
                # Sobreposição: a.start < b.end AND b.start < a.end
                if a["normalized_start"] < b["normalized_end"] and b["normalized_start"] < a["normalized_end"]:
                    for row in (a, b):
                        row["has_overlap"] = True
                        issues_list = json.loads(row["issues"]) if row["issues"] else []
                        msg = "Sobreposição de turno detectada com outra linha do mesmo agente neste lote"
                        if msg not in issues_list:
                            issues_list.append(msg)
                            row["issues"] = json.dumps(issues_list)
                        if row["row_status"] == RowStatus.VALID:
                            row["row_status"] = RowStatus.WARNING

    return validated


# ─── Persistência ─────────────────────────────────────────────────────────────

def process_import_file(
    db: Session,
    file_content: bytes,
    filename: str,
    reference_period: Optional[str],
    source_description: Optional[str],
    imported_by_id: int,
) -> ScheduleImport:
    """Lê, parseia, normaliza, valida e persiste um arquivo de importação."""

    schedule_import = ScheduleImport(
        filename=filename,
        reference_period=reference_period,
        source_description=source_description,
        status=ImportStatus.PROCESSING,
        imported_by=imported_by_id,
    )
    db.add(schedule_import)
    db.flush()  # obtém ID antes de inserir as linhas

    try:
        headers, raw_rows = read_file(file_content, filename)
    except Exception as exc:
        logger.exception("Falha ao ler arquivo de importação: %s", filename)
        schedule_import.status = ImportStatus.FAILED
        db.commit()
        raise ValueError(f"Não foi possível ler o arquivo '{filename}': {exc}") from exc

    if not raw_rows:
        schedule_import.status = ImportStatus.COMPLETED
        db.commit()
        return schedule_import

    col_map = _build_column_map(headers)

    # Validar que as colunas mínimas estão presentes
    missing = [c for c in ("profissional", "data", "hora_inicio", "hora_fim") if c not in col_map]
    if missing:
        schedule_import.status = ImportStatus.FAILED
        db.commit()
        raise ValueError(
            f"Arquivo sem colunas obrigatórias: {missing}. "
            f"Colunas encontradas: {headers}"
        )

    # Parsear e validar cada linha
    validated: List[Dict[str, Any]] = []
    for row_num, raw in enumerate(raw_rows, start=2):  # linha 1 = cabeçalho
        # Pula linhas completamente vazias
        values = [v for v in raw.values() if v is not None and str(v).strip()]
        if not values:
            continue
        row_data = _validate_row(row_num, raw, col_map, db)
        row_data["import_id"] = schedule_import.id
        validated.append(row_data)

    validated = _detect_duplicates_and_overlaps(validated)

    # Persistir linhas
    for row_data in validated:
        db_row = ScheduleImportRow(**row_data)
        db.add(db_row)

    # Atualizar contadores
    total = len(validated)
    valid = sum(1 for r in validated if r["row_status"] == RowStatus.VALID)
    warning = sum(1 for r in validated if r["row_status"] == RowStatus.WARNING)
    invalid = sum(1 for r in validated if r["row_status"] == RowStatus.INVALID)
    duplicate = sum(1 for r in validated if r["is_duplicate"])

    schedule_import.total_rows = total
    schedule_import.valid_rows = valid
    schedule_import.warning_rows = warning
    schedule_import.invalid_rows = invalid
    schedule_import.duplicate_rows = duplicate
    schedule_import.status = ImportStatus.COMPLETED

    db.commit()
    db.refresh(schedule_import)
    return schedule_import


# ─── Confirmação: staging → Shift ─────────────────────────────────────────────

def confirm_import(
    db: Session,
    import_id: int,
    confirmed_by_id: int,
) -> Tuple[ScheduleImport, int]:
    """
    Converte linhas válidas/warning (não duplicadas) em Shifts reais.
    Retorna (import, shifts_created).
    """
    schedule_import = db.query(ScheduleImport).filter(ScheduleImport.id == import_id).first()
    if not schedule_import:
        raise ValueError(f"Importação {import_id} não encontrada")
    if schedule_import.confirmed_at is not None:
        raise ValueError(f"Importação {import_id} já foi confirmada")

    importable_rows = db.query(ScheduleImportRow).filter(
        ScheduleImportRow.import_id == import_id,
        ScheduleImportRow.row_status.in_([RowStatus.VALID, RowStatus.WARNING]),
        ScheduleImportRow.is_duplicate == False,  # noqa: E712
        ScheduleImportRow.agent_id != None,  # noqa: E711
        ScheduleImportRow.normalized_start != None,  # noqa: E711
        ScheduleImportRow.normalized_end != None,  # noqa: E711
        ScheduleImportRow.created_shift_id == None,  # noqa: E711
    ).all()

    shifts_created = 0
    shifts_buffer: Dict[int, List[Shift]] = {}

    for row in importable_rows:
        agent_existing_shifts = shifts_buffer.get(row.agent_id)
        if agent_existing_shifts is None:
            agent_existing_shifts = db.query(Shift).filter(Shift.agent_id == row.agent_id).all()
            shifts_buffer[row.agent_id] = agent_existing_shifts

        validation_errors = validate_shift(
            {
                "agent_id": row.agent_id,
                "start_time": row.normalized_start,
                "end_time": row.normalized_end,
            },
            existing_shifts=agent_existing_shifts,
        )
        if validation_errors:
            row.has_overlap = True
            issues_list = json.loads(row.issues) if row.issues else []
            for error in validation_errors:
                issues_list.append(error.get("message", "Erro de validação de escala"))
            row.issues = json.dumps(list(dict.fromkeys(issues_list)))
            if row.row_status == RowStatus.VALID:
                row.row_status = RowStatus.WARNING
            continue

        obs_parts = []
        if row.raw_observations:
            obs_parts.append(row.raw_observations)
        obs_parts.append(f"[Importado de: {schedule_import.filename}]")

        shift = Shift(
            agent_id=row.agent_id,
            user_id=row.agent_id,
            legacy_agent_name=row.raw_professional,
            start_time=row.normalized_start,
            end_time=row.normalized_end,
            title="Turno importado",
            description=" | ".join(obs_parts),
        )
        db.add(shift)
        db.flush()
        row.created_shift_id = shift.id
        shifts_buffer.setdefault(row.agent_id, []).append(shift)
        shifts_created += 1

    schedule_import.confirmed_at = datetime.utcnow()
    schedule_import.confirmed_by = confirmed_by_id
    db.commit()
    db.refresh(schedule_import)
    return schedule_import, shifts_created


# ─── Relatório de inconsistências ─────────────────────────────────────────────

def export_issues_csv(db: Session, import_id: int) -> bytes:
    """Gera CSV com linhas que têm inconsistências."""
    rows = db.query(ScheduleImportRow).filter(
        ScheduleImportRow.import_id == import_id,
        ScheduleImportRow.row_status.in_([RowStatus.WARNING, RowStatus.INVALID]),
    ).order_by(ScheduleImportRow.row_number).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "linha", "profissional", "data", "hora_inicio", "hora_fim",
        "status", "duplicata", "sobreposicao", "problemas",
    ])
    for row in rows:
        issues_list = json.loads(row.issues) if row.issues else []
        writer.writerow([
            row.row_number,
            row.raw_professional or "",
            row.raw_date or "",
            row.raw_start_time or "",
            row.raw_end_time or "",
            row.row_status.value,
            "sim" if row.is_duplicate else "não",
            "sim" if row.has_overlap else "não",
            "; ".join(issues_list),
        ])
    return output.getvalue().encode("utf-8-sig")
