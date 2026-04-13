from icalendar import Calendar, Event
from typing import List
from io import BytesIO
from datetime import datetime
from ..models import Shift


class ICSExporter:
    """Exportador simples de ICS (iCalendar) para turnos"""

    @staticmethod
    def export_shifts(shifts: List[Shift], calendar_name: str = "Turnos de trabalho") -> BytesIO:
        """
        Exportar turnos para o formato ICS (simples, unidirecional)

        Args:
            shifts: Lista de objetos Shift a serem exportados
            calendar_name: Nome do calendário

        Returns:
            BytesIO: Arquivo ICS em memória
        """
        cal = Calendar()
        cal.add('prodid', '-//AgentEscala//Turnos//PT-BR')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', calendar_name)
        cal.add('x-wr-timezone', 'UTC')

        for shift in shifts:
            event = Event()
            event.add('uid', f'shift-{shift.id}@agentescala.local')
            event.add('summary', shift.title)
            event.add('dtstart', shift.start_time)
            event.add('dtend', shift.end_time)
            event.add('dtstamp', datetime.utcnow())
            event.add('created', shift.created_at)
            event.add('last-modified', shift.updated_at)

            if shift.description:
                event.add('description', shift.description)

            if shift.location:
                event.add('location', shift.location)

            # Adiciona informações do agente na descrição
            if shift.agent:
                description_text = f"Agente: {shift.agent.name} ({shift.agent.email})"
                if shift.description:
                    description_text = f"{shift.description}\n\n{description_text}"
                event['description'] = description_text

            cal.add_component(event)

        # Save to BytesIO
        output = BytesIO()
        output.write(cal.to_ical())
        output.seek(0)
        return output

    @staticmethod
    def export_single_shift(shift: Shift) -> BytesIO:
        """
        Exportar um turno para o formato ICS

        Args:
            shift: Objeto Shift a ser exportado

        Returns:
            BytesIO: Arquivo ICS em memória
        """
        return ICSExporter.export_shifts([shift], calendar_name=f"Turno - {shift.title}")
