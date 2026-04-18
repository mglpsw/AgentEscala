from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from ...models import MedicalProfile, User

DATE_RE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
CRM_RE = re.compile(r"\bCRM\s*[:\-]?\s*(\d{4,8})\b", re.IGNORECASE)
TIME_RANGE_RE = re.compile(r"\b(\d{1,2})[:h]?(\d{2})?\s*[-–]\s*(\d{1,2})[:h]?(\d{2})?\b", re.IGNORECASE)

SHIFT_KEYWORDS = {
    "24 HORAS": ("00:00", "00:00"),
    "12H DIA": ("08:00", "20:00"),
    "12H NOITE": ("20:00", "08:00"),
    "10-22H": ("10:00", "22:00"),
}

WEEKDAYS = {
    "SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "SAB", "DOM",
    "SEGUNDA", "TERÇA", "TERCA", "QUARTA", "QUINTA", "SEXTA", "SÁBADO", "SABADO", "DOMINGO",
}


@dataclass
class ParsedScheduleCandidate:
    raw_line: str
    date: Optional[str]
    weekday: Optional[str]
    shift_label: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    professional_name: Optional[str]
    crm_number: Optional[str]


class OcrCalibrationService:
    @staticmethod
    def _normalize_name(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        return re.sub(r"\b(SEG|TER|QUA|QUI|SEX|SAB|SÁB|DOM)\b", "", text, flags=re.IGNORECASE).strip()

    @staticmethod
    def _parse_shift(line: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        upper = line.upper()
        for label, (start, end) in SHIFT_KEYWORDS.items():
            if label in upper:
                return label, start, end

        match = TIME_RANGE_RE.search(upper)
        if match:
            h1, m1, h2, m2 = match.groups()
            start = f"{int(h1):02d}:{int(m1 or '00'):02d}"
            end = f"{int(h2):02d}:{int(m2 or '00'):02d}"
            return f"{start}-{end}", start, end
        return None, None, None

    @staticmethod
    def parse_raw_text(raw_text: str) -> List[ParsedScheduleCandidate]:
        candidates: List[ParsedScheduleCandidate] = []
        for line in raw_text.splitlines():
            line = line.strip()
            if not line:
                continue

            date_match = DATE_RE.search(line)
            crm_match = CRM_RE.search(line)
            shift_label, start_time, end_time = OcrCalibrationService._parse_shift(line)

            tokens = [tok.strip() for tok in re.split(r"[|;,\t]", line) if tok.strip()]
            weekday = None
            for tok in tokens:
                cleaned = re.sub(r"[^A-ZÁÂÃÉÊÍÓÔÕÚÇ]", "", tok.upper())
                if cleaned in WEEKDAYS:
                    weekday = tok
                    break

            name_guess = None
            for tok in tokens:
                upper_tok = tok.upper()
                if DATE_RE.search(tok):
                    continue
                if TIME_RANGE_RE.search(tok):
                    continue
                if re.match(r"^\d{1,2}:\d{2}$", tok):
                    continue
                if re.sub(r"[^A-ZÁÂÃÉÊÍÓÔÕÚÇ]", "", upper_tok) in WEEKDAYS:
                    continue
                if any(ch.isalpha() for ch in tok) and len(tok) > 3:
                    name_guess = tok
                    break
            if not name_guess:
                cleaned_line = DATE_RE.sub("", line)
                cleaned_line = TIME_RANGE_RE.sub("", cleaned_line)
                cleaned_line = CRM_RE.sub("", cleaned_line)
                for label in SHIFT_KEYWORDS:
                    cleaned_line = cleaned_line.upper().replace(label, "")
                name_guess = cleaned_line.strip(" -|;")

            name_guess = OcrCalibrationService._normalize_name(name_guess or "")
            if len(name_guess) < 3:
                name_guess = None

            candidates.append(
                ParsedScheduleCandidate(
                    raw_line=line,
                    date=date_match.group(1) if date_match else None,
                    weekday=weekday,
                    shift_label=shift_label,
                    start_time=start_time,
                    end_time=end_time,
                    professional_name=name_guess,
                    crm_number=crm_match.group(1) if crm_match else None,
                )
            )

        return candidates

    @staticmethod
    def match_candidate(db: Session, candidate: ParsedScheduleCandidate) -> dict:
        name = (candidate.professional_name or "").strip()
        crm = (candidate.crm_number or "").strip()

        if crm:
            profile = db.query(MedicalProfile).filter(MedicalProfile.crm_numero == crm).first()
            if profile:
                return {
                    "status": "matched",
                    "user_id": profile.user_id,
                    "match_reason": "crm_exact",
                    "matched_name": profile.nome_completo,
                }

        if name:
            users = db.query(User).filter(User.is_active == True).all()  # noqa: E712
            normalized = name.lower()
            exact = [u for u in users if u.name.lower() == normalized]
            if len(exact) == 1:
                return {
                    "status": "matched",
                    "user_id": exact[0].id,
                    "match_reason": "name_exact",
                    "matched_name": exact[0].name,
                }

            partial = [u for u in users if normalized in u.name.lower() or u.name.lower() in normalized]
            if len(partial) == 1:
                return {
                    "status": "matched",
                    "user_id": partial[0].id,
                    "match_reason": "name_partial",
                    "matched_name": partial[0].name,
                }
            if len(partial) > 1:
                return {
                    "status": "ambiguous",
                    "user_id": None,
                    "match_reason": "name_ambiguous",
                    "candidates": [{"id": u.id, "name": u.name} for u in partial[:5]],
                }

        return {
            "status": "unmatched",
            "user_id": None,
            "match_reason": "no_match",
        }
