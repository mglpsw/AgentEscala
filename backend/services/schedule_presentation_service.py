from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import Shift, UserRole


class SchedulePresentationService:
    """Monta linhas de escala no formato consumido pela tabela final."""

    @staticmethod
    def build_essential_rows(shifts: List[Shift]) -> List[Dict[str, Any]]:
        return [SchedulePresentationService.build_essential_row(shift) for shift in shifts]

    @staticmethod
    def build_essential_row(shift: Shift) -> Dict[str, Any]:
        agent = shift.agent
        crm_number = SchedulePresentationService._crm_number(agent)
        crm_uf = SchedulePresentationService._crm_uf(agent)

        return {
            "shift_id": shift.id,
            "agent_id": shift.agent_id,
            "display_name": SchedulePresentationService._display_name(agent),
            "professional_type": SchedulePresentationService._professional_type(agent),
            "crm": SchedulePresentationService._format_crm(crm_number, crm_uf),
            "crm_number": crm_number,
            "crm_uf": crm_uf,
            "shift_start": shift.start_time,
            "shift_end": shift.end_time,
            "shift_period": SchedulePresentationService._format_shift_period(
                shift.start_time,
                shift.end_time,
            ),
        }

    @staticmethod
    def _future_profile(agent):
        if not agent:
            return None
        return getattr(agent, "profile", None) or getattr(agent, "user_profile", None)

    @staticmethod
    def _future_medical_profile(agent):
        if not agent:
            return None
        return getattr(agent, "medical_profile", None)

    @staticmethod
    def _display_name(agent) -> str:
        if not agent:
            return "N/D"

        profile = SchedulePresentationService._future_profile(agent)
        profile_display_name = getattr(profile, "display_name", None)
        if profile_display_name:
            return profile_display_name

        direct_display_name = getattr(agent, "display_name", None)
        if direct_display_name:
            return direct_display_name

        return agent.name

    @staticmethod
    def _professional_type(agent) -> str:
        if not agent:
            return "N/D"

        medical_profile = SchedulePresentationService._future_medical_profile(agent)
        raw_type = (
            getattr(medical_profile, "professional_type", None)
            or getattr(agent, "professional_type", None)
        )
        if raw_type:
            value = getattr(raw_type, "value", raw_type)
            return SchedulePresentationService._professional_type_label(str(value))

        if agent.role == UserRole.AGENT:
            return "Médico"
        return agent.role.value

    @staticmethod
    def _professional_type_label(value: str) -> str:
        labels = {
            "doctor": "Médico",
            "physician": "Médico",
            "nurse": "Enfermagem",
            "admin": "Administração",
            "coordinator": "Coordenação",
            "other": "Outro",
        }
        return labels.get(value.lower(), value)

    @staticmethod
    def _crm_number(agent) -> Optional[str]:
        medical_profile = SchedulePresentationService._future_medical_profile(agent)
        value = (
            getattr(medical_profile, "crm_number", None)
            or getattr(agent, "crm_number", None)
        )
        return str(value) if value else None

    @staticmethod
    def _crm_uf(agent) -> Optional[str]:
        medical_profile = SchedulePresentationService._future_medical_profile(agent)
        value = getattr(medical_profile, "crm_uf", None) or getattr(agent, "crm_uf", None)
        return str(value).upper() if value else None

    @staticmethod
    def _format_crm(crm_number: Optional[str], crm_uf: Optional[str]) -> str:
        if crm_number and crm_uf:
            return f"CRM-{crm_uf} {crm_number}"
        if crm_number:
            return crm_number
        return ""

    @staticmethod
    def _format_shift_period(start: datetime, end: datetime) -> str:
        start_date = start.strftime("%d/%m/%Y")
        start_time = start.strftime("%H:%M")
        end_time = end.strftime("%H:%M")

        if start.date() == end.date():
            return f"{start_date} {start_time}-{end_time}"

        end_date = end.strftime("%d/%m/%Y")
        return f"{start_date} {start_time} - {end_date} {end_time}"
