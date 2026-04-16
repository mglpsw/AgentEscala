from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config.database import get_db
from ..models import User
from ..services import validate_schedule
from ..utils.dependencies import require_admin
from .schemas import ScheduleValidationRequest, ScheduleValidationResponse

router = APIRouter(prefix="/admin/schedule", tags=["Admin Schedule Validation"])


@router.post("/validate", response_model=ScheduleValidationResponse)
def validate_schedule_preview(
    payload: ScheduleValidationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Valida uma escala enviada no payload sem persistir alterações (modo preview)."""
    _ = db  # Mantém assinatura compatível com dependências atuais da aplicação.

    shifts_payload = [
        {
            "id": shift.shift_id,
            "agent_id": shift.agent_id,
            "start_time": shift.start_time,
            "end_time": shift.end_time,
        }
        for shift in payload.shifts
    ]
    errors = validate_schedule(shifts_payload)

    return ScheduleValidationResponse(
        valid=len(errors) == 0,
        preview=payload.preview,
        errors=errors,
        total_shifts=len(shifts_payload),
    )
