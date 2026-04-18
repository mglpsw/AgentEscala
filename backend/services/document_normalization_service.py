from __future__ import annotations

import io
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from openpyxl import load_workbook
from sqlalchemy.orm import Session

from ..models import User

_MONTHS_PT = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}

_COL_SYNONYMS: Dict[str, List[str]] = {
    "professional": ["profissional", "médico", "medico", "nome", "plantonista"],
    "crm": ["crm", "conselho", "registro"],
    "date": ["data", "dia", "plantão", "plantao"],
    "start_time": ["entrada", "início", "inicio", "hora início", "hora inicio"],
    "end_time": ["saída", "saida", "fim", "hora fim", "hora saída", "hora saida"],
    "shift_label": ["turno", "período", "periodo"],
    "specialty": ["especialidade"],
    "unit": ["unidade", "local", "setor"],
    "duration": ["total horas", "carga horária", "carga horaria", "horas"],
}

_PHONE_RE = re.compile(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-\s]?\d{4}")
_CRM_RE = re.compile(r"\bCRM\s*[:\-/]?\s*([A-Z]{0,2})\s*(\d{3,8})\b", re.IGNORECASE)
_DATE_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b")
_TIME_RE = re.compile(r"(\d{1,2})(?::|h)?(\d{2})?")


def _normalize_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _comparable_text(value: Optional[str]) -> str:
    text = _normalize_text(value).lower()
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text


def _extract_month_year(label: str) -> Tuple[Optional[int], Optional[int], float]:
    label_cmp = _comparable_text(label)
    year_match = re.search(r"\b(20\d{2})\b", label_cmp)
    year = int(year_match.group(1)) if year_match else None
    for name, month in _MONTHS_PT.items():
        if name in label_cmp:
            return month, year, 0.9 if year else 0.7
    slash = re.search(r"\b(\d{1,2})\s*/\s*(20\d{2})\b", label_cmp)
    if slash:
        return int(slash.group(1)), int(slash.group(2)), 0.85
    return None, year, 0.0


def _canonical_header(header: str) -> Optional[str]:
    cmp = _comparable_text(header)
    for canonical, synonyms in _COL_SYNONYMS.items():
        for s in synonyms:
            if _comparable_text(s) in cmp:
                return canonical
    return None


def _clean_professional(value: Optional[str]) -> Tuple[str, Optional[str], List[str]]:
    raw = _normalize_text(value)
    messages: List[str] = []
    if not raw:
        return "", None, ["Nome do profissional ausente"]

    crm = None
    crm_match = _CRM_RE.search(raw)
    if crm_match:
        uf = (crm_match.group(1) or "").upper()
        num = crm_match.group(2)
        crm = f"{uf}{num}" if uf else num
        raw = _CRM_RE.sub("", raw)

    cleaned = _PHONE_RE.sub("", raw)
    cleaned = re.sub(r"\bfaturamento\b.*$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\(.*?\)", "", cleaned)
    cleaned = _normalize_text(cleaned)

    if len(cleaned.split()) < 2:
        messages.append("Nome com baixa qualidade")

    return cleaned, crm, messages


def _parse_date_with_context(raw_date: Optional[str], month: Optional[int], year: Optional[int]) -> Optional[date]:
    if raw_date:
        raw_date = _normalize_text(raw_date)
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                parsed = datetime.strptime(raw_date, fmt).date()
                if parsed.year < 100:
                    parsed = parsed.replace(year=2000 + parsed.year)
                return parsed
            except ValueError:
                pass
        m = _DATE_RE.search(raw_date)
        if m:
            d = int(m.group(1))
            mm = int(m.group(2))
            yy = int(m.group(3)) if m.group(3) else (year or datetime.utcnow().year)
            if yy < 100:
                yy += 2000
            try:
                return date(yy, mm, d)
            except ValueError:
                return None
    if month and year and raw_date and raw_date.isdigit():
        try:
            return date(year, month, int(raw_date))
        except ValueError:
            return None
    return None


def _parse_hour(raw: Optional[str]) -> Optional[Tuple[int, int]]:
    if not raw:
        return None
    m = _TIME_RE.search(_comparable_text(raw))
    if not m:
        return None
    h = int(m.group(1))
    mm = int(m.group(2) or 0)
    if h > 23 or mm > 59:
        return None
    return h, mm


def _parse_time_window(start_raw: Optional[str], end_raw: Optional[str], shift_label: Optional[str]) -> Tuple[Optional[Tuple[int, int]], Optional[Tuple[int, int]]]:
    if start_raw and end_raw:
        return _parse_hour(start_raw), _parse_hour(end_raw)

    label = _normalize_text(shift_label)
    m = re.search(r"(\d{1,2}(?::\d{2}|h\d{2})?)\s*(?:-|às|as|a)\s*(\d{1,2}(?::\d{2}|h\d{2})?)", label, re.IGNORECASE)
    if m:
        return _parse_hour(m.group(1)), _parse_hour(m.group(2))
    if "noite" in _comparable_text(label) or "noturno" in _comparable_text(label):
        return (20, 0), (8, 0)
    if "manha" in _comparable_text(label):
        return (8, 0), (14, 0)
    if "tarde" in _comparable_text(label):
        return (14, 0), (20, 0)
    return None, None


def _resolve_user_match(db: Session, name: str, crm: Optional[str]) -> Tuple[str, Optional[int], List[str]]:
    notes: List[str] = []
    if not name:
        return "invalid", None, ["Nome obrigatório"]

    users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
    if crm:
        by_crm = [u for u in users if crm and crm in _comparable_text(u.profile_notes or "")]
        if len(by_crm) == 1:
            return "matched", by_crm[0].id, []
        if len(by_crm) > 1:
            return "ambiguous", None, ["CRM com múltiplos candidatos"]

    cmp_name = _comparable_text(name)
    exact = [u for u in users if _comparable_text(u.name) == cmp_name]
    if len(exact) == 1:
        return "matched", exact[0].id, []
    if len(exact) > 1:
        return "ambiguous", None, ["Nome exato com múltiplos usuários"]

    fuzzy = [u for u in users if cmp_name in _comparable_text(u.name) or _comparable_text(u.name) in cmp_name]
    if len(fuzzy) == 1:
        notes.append("Correspondência aproximada por nome")
        return "matched", fuzzy[0].id, notes
    if len(fuzzy) > 1:
        return "ambiguous", None, ["Correspondência aproximada ambígua"]
    return "new_user_candidate", None, []


def _build_row_from_values(
    db: Session,
    values: Dict[str, Any],
    source_sheet: Optional[str],
    source_page: Optional[int],
    row_index: int,
    month_ctx: Optional[int],
    year_ctx: Optional[int],
) -> Dict[str, Any]:
    name_raw = values.get("professional")
    cleaned_name, crm_from_name, messages = _clean_professional(name_raw)
    crm_raw = values.get("crm") or crm_from_name

    parsed_date = _parse_date_with_context(values.get("date"), month_ctx, year_ctx)
    start_h, end_h = _parse_time_window(values.get("start_time"), values.get("end_time"), values.get("shift_label"))

    start_dt = end_dt = None
    duration = None
    if parsed_date and start_h and end_h:
        start_dt = datetime(parsed_date.year, parsed_date.month, parsed_date.day, start_h[0], start_h[1])
        end_dt = datetime(parsed_date.year, parsed_date.month, parsed_date.day, end_h[0], end_h[1])
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        duration = round((end_dt - start_dt).total_seconds() / 3600, 2)

    match_status, matched_user_id, match_notes = _resolve_user_match(db, cleaned_name, crm_raw)
    messages.extend(match_notes)

    if not parsed_date:
        messages.append("Data ausente ou inválida")
    if not (start_h and end_h):
        messages.append("Horário/turno incompreensível")

    if not cleaned_name or not parsed_date or not (start_h and end_h):
        match_status = "invalid"

    confidence = 0.35
    if cleaned_name:
        confidence += 0.2
    if parsed_date:
        confidence += 0.2
    if start_h and end_h:
        confidence += 0.15
    if match_status == "matched":
        confidence += 0.1
    if match_status == "invalid":
        confidence -= 0.2

    return {
        "source_sheet": source_sheet,
        "source_page": source_page,
        "source_row_index": row_index,
        "competency_month": parsed_date.month if parsed_date else month_ctx,
        "competency_year": parsed_date.year if parsed_date else year_ctx,
        "professional_name_raw": name_raw,
        "professional_name_normalized": cleaned_name,
        "crm_raw": values.get("crm"),
        "crm_normalized": crm_raw,
        "specialty_raw": values.get("specialty"),
        "location_raw": values.get("location"),
        "unit_raw": values.get("unit"),
        "date_raw": values.get("date"),
        "date_iso": parsed_date.isoformat() if parsed_date else None,
        "weekday_raw": values.get("weekday"),
        "shift_label_raw": values.get("shift_label"),
        "start_time_raw": values.get("start_time"),
        "end_time_raw": values.get("end_time"),
        "start_datetime": start_dt.isoformat() if start_dt else None,
        "end_datetime": end_dt.isoformat() if end_dt else None,
        "duration_hours": duration,
        "role_raw": values.get("role"),
        "notes": values.get("notes"),
        "confidence": round(max(0.0, min(1.0, confidence)), 2),
        "match_status": match_status,
        "matched_user_id": matched_user_id,
        "validation_messages": list(dict.fromkeys(messages)),
    }


def normalize_xlsx_document(db: Session, content: bytes, filename: str) -> Dict[str, Any]:
    wb = load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    rows: List[Dict[str, Any]] = []
    detected_months: List[Dict[str, Any]] = []
    raw_headers: List[str] = []
    normalized_headers: List[str] = []
    warnings: List[str] = []

    for ws in wb.worksheets:
        matrix = list(ws.iter_rows(values_only=True))
        if not matrix:
            warnings.append(f"Aba '{ws.title}' vazia")
            continue

        best_header_idx = None
        best_score = -1
        best_header: List[str] = []
        for idx, row in enumerate(matrix[:15]):
            cells = [_normalize_text(str(c)) if c is not None else "" for c in row]
            score = sum(1 for cell in cells if _canonical_header(cell))
            if score > best_score:
                best_score = score
                best_header_idx = idx
                best_header = cells
        if best_header_idx is None or best_score < 2:
            warnings.append(f"Aba '{ws.title}' sem tabela válida detectada")
            continue

        sheet_label = " ".join([str(c) for r in matrix[:best_header_idx + 1] for c in r if c])
        month, year, m_conf = _extract_month_year(f"{ws.title} {sheet_label}")
        if month and year:
            detected_months.append({"month": month, "year": year, "label": f"{month:02d}/{year}", "source_sheet": ws.title, "confidence": m_conf})

        header_map: Dict[int, str] = {}
        for i, h in enumerate(best_header):
            if h:
                raw_headers.append(h)
            canonical = _canonical_header(h)
            if canonical:
                header_map[i] = canonical
                normalized_headers.append(canonical)

        for offset, row in enumerate(matrix[best_header_idx + 1 :], start=best_header_idx + 2):
            if not any(cell is not None and str(cell).strip() for cell in row):
                continue
            values: Dict[str, Any] = {}
            for col_idx, canonical in header_map.items():
                if col_idx < len(row):
                    val = row[col_idx]
                    values[canonical] = _normalize_text(str(val)) if val is not None else None
            nrow = _build_row_from_values(db, values, ws.title, None, offset, month, year)
            rows.append(nrow)

    wb.close()

    return {
        "source_type": "xlsx",
        "source_filename": filename,
        "detected_months": detected_months,
        "raw_headers": sorted(list(dict.fromkeys(raw_headers))),
        "normalized_headers": sorted(list(dict.fromkeys(normalized_headers))),
        "sheets": [{"name": ws.title} for ws in wb.worksheets],
        "rows": rows,
        "warnings": warnings,
        "errors": [],
        "metadata": {
            "detected_layout_type": "multi_sheet_tabular",
            "parser_version": "v2-document-normalizer",
            "ocr_provider": None,
            "overall_confidence": round(sum(r["confidence"] for r in rows) / len(rows), 2) if rows else 0.0,
        },
    }


def normalize_ocr_payload_document(db: Session, payload: Dict[str, Any], source_filename: str, source_type: str = "pdf") -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    warnings: List[str] = []
    detected_months: List[Dict[str, Any]] = []
    raw_headers: List[str] = []
    normalized_headers: List[str] = []

    pages = payload.get("pages") or []
    for page in pages:
        page_number = page.get("page_number")
        for table in page.get("tables") or []:
            title = _normalize_text(table.get("title"))
            month, year, conf = _extract_month_year(title)
            if month and year:
                detected_months.append({"month": month, "year": year, "label": title, "source_sheet": f"page-{page_number}", "confidence": conf})
            headers = [str(h) for h in (table.get("headers") or [])]
            raw_headers.extend(headers)
            canonical_by_idx = {i: _canonical_header(h) for i, h in enumerate(headers)}
            normalized_headers.extend([v for v in canonical_by_idx.values() if v])

            for idx, raw_row in enumerate(table.get("rows") or [], start=1):
                values: Dict[str, Any] = {}
                for col_idx, cell in enumerate(raw_row):
                    canonical = canonical_by_idx.get(col_idx)
                    if canonical:
                        values[canonical] = _normalize_text(str(cell))
                row = _build_row_from_values(db, values, f"page-{page_number}", int(page_number) if page_number else None, idx, month, year)
                row_conf = table.get("confidence")
                if isinstance(row_conf, (int, float)):
                    row["confidence"] = round((row["confidence"] + float(row_conf)) / 2, 2)
                rows.append(row)

    if not pages:
        warnings.append("Payload OCR sem páginas")

    return {
        "source_type": source_type,
        "source_filename": source_filename,
        "detected_months": detected_months,
        "raw_headers": sorted(list(dict.fromkeys(raw_headers))),
        "normalized_headers": sorted(list(dict.fromkeys(normalized_headers))),
        "sheets": [],
        "rows": rows,
        "warnings": warnings,
        "errors": [],
        "metadata": {
            "detected_layout_type": "ocr_table",
            "parser_version": "v2-document-normalizer",
            "ocr_provider": payload.get("provider") or "mockable",
            "overall_confidence": round(sum(r["confidence"] for r in rows) / len(rows), 2) if rows else 0.0,
        },
    }
