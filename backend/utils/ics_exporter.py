from icalendar import Calendar, Event
from typing import List
from io import BytesIO
from datetime import datetime
from ..models import Shift


class ICSExporter:
    """Simple ICS (iCalendar) exporter for shifts"""

    @staticmethod
    def export_shifts(shifts: List[Shift], calendar_name: str = "Work Shifts") -> BytesIO:
        """
        Export shifts to ICS format (simple, unidirectional)

        Args:
            shifts: List of Shift objects to export
            calendar_name: Name of the calendar

        Returns:
            BytesIO: ICS file in memory
        """
        cal = Calendar()
        cal.add('prodid', '-//AgentEscala//Work Shifts//EN')
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

            # Add agent information in description
            if shift.agent:
                description_text = f"Agent: {shift.agent.name} ({shift.agent.email})"
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
        Export a single shift to ICS format

        Args:
            shift: Shift object to export

        Returns:
            BytesIO: ICS file in memory
        """
        return ICSExporter.export_shifts([shift], calendar_name=f"Shift - {shift.title}")
