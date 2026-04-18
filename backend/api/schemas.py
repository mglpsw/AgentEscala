import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from typing import List, Optional
from datetime import date, datetime
from ..models import UFEnum, UserRole, SwapStatus, FutureShiftRequestStatus, ShiftRequestStatus


CPF_PATTERN = re.compile(r"^\d{11}$")


# Esquemas de usuário
class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.MEDICO


class AdminUserCreate(UserBase):
    password: str = Field(min_length=6)
    role: UserRole
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=6)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_admin: bool = False
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True




class AdminUserAuditResponse(BaseModel):
    id: int
    action: str
    admin_user_id: int
    target_user_id: int
    change_summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class MeUpdatePayload(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=32)
    specialty: Optional[str] = Field(default=None, max_length=120)
    profile_notes: Optional[str] = Field(default=None, max_length=1500)


# Esquemas de turno
class ShiftBase(BaseModel):
    start_time: datetime
    end_time: datetime
    title: str = "Turno de trabalho"
    description: Optional[str] = None
    location: Optional[str] = None


class ShiftCreate(ShiftBase):
    agent_id: int
    user_id: Optional[int] = None
    legacy_agent_name: Optional[str] = None


class ShiftUpdate(BaseModel):
    agent_id: Optional[int] = None
    user_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    legacy_agent_name: Optional[str] = None


class ShiftResponse(ShiftBase):
    id: int
    agent_id: int
    user_id: Optional[int] = None
    legacy_agent_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShiftWithAgent(ShiftResponse):
    agent: Optional[UserResponse] = None

    class Config:
        from_attributes = True




class ScheduleValidationShift(BaseModel):
    shift_id: Optional[int] = None
    agent_id: int
    start_time: datetime
    end_time: datetime
    title: Optional[str] = None


class ScheduleValidationRequest(BaseModel):
    shifts: List[ScheduleValidationShift]
    preview: bool = True


class ScheduleValidationResponse(BaseModel):
    valid: bool
    preview: bool
    errors: List[dict]
    total_shifts: int

class FinalScheduleRow(BaseModel):
    shift_id: int
    agent_id: int
    display_name: str
    professional_type: str
    crm: str
    crm_number: Optional[str] = None
    crm_uf: Optional[str] = None
    medico: Optional[dict] = None
    shift_start: datetime
    shift_end: datetime
    shift_period: str


class FutureShiftRequestCreate(BaseModel):
    requested_date: date
    shift_period: str = Field(min_length=3, max_length=40)
    notes: Optional[str] = Field(default=None, max_length=500)


class FutureShiftRequestResponse(BaseModel):
    id: int
    user_id: int
    requested_date: date
    shift_period: str
    notes: Optional[str] = None
    status: FutureShiftRequestStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Esquemas de perfil médico
class MedicalProfileBase(BaseModel):
    nome_completo: str = Field(min_length=2)
    cpf: str
    crm_numero: str = Field(min_length=1)
    crm_uf: UFEnum
    data_nascimento: date
    cartao_nacional_saude: str = Field(min_length=1)
    email_profissional: EmailStr
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    rg: Optional[str] = None
    rg_orgao_emissor: Optional[str] = None
    rg_data_emissao: Optional[date] = None
    crm_data_emissao: Optional[date] = None
    arquivo_vacinacao: Optional[str] = None

    @field_validator("cpf")
    @classmethod
    def validar_formato_cpf(cls, value: str) -> str:
        """Validação estrutural do CPF; algoritmo completo fica para fase posterior."""
        if not CPF_PATTERN.match(value):
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return value


class MedicalProfileCreate(MedicalProfileBase):
    pass


class MedicalProfileUpdate(BaseModel):
    nome_completo: Optional[str] = Field(default=None, min_length=2)
    cpf: Optional[str] = None
    crm_numero: Optional[str] = Field(default=None, min_length=1)
    crm_uf: Optional[UFEnum] = None
    data_nascimento: Optional[date] = None
    cartao_nacional_saude: Optional[str] = Field(default=None, min_length=1)
    email_profissional: Optional[EmailStr] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    rg: Optional[str] = None
    rg_orgao_emissor: Optional[str] = None
    rg_data_emissao: Optional[date] = None
    crm_data_emissao: Optional[date] = None
    arquivo_vacinacao: Optional[str] = None

    @field_validator("cpf")
    @classmethod
    def validar_formato_cpf(cls, value: Optional[str]) -> Optional[str]:
        """Validação estrutural do CPF quando o campo é enviado para atualização."""
        if value is not None and not CPF_PATTERN.match(value):
            raise ValueError("CPF deve conter exatamente 11 dígitos.")
        return value


class MedicalProfileResponse(MedicalProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class FinalScheduleFilters(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class FinalScheduleMetadata(BaseModel):
    total: int
    generated_at: datetime
    filters: FinalScheduleFilters


class FinalScheduleExportResponse(BaseModel):
    shifts: List[FinalScheduleRow]
    metadata: FinalScheduleMetadata


class ShiftRequestCreate(BaseModel):
    requested_date: date
    shift_period: str = Field(min_length=3, max_length=40)
    note: Optional[str] = Field(default=None, max_length=500)
    target_shift_id: Optional[int] = None


class ShiftRequestResponse(BaseModel):
    id: int
    requester_id: int
    target_user_id: Optional[int] = None
    target_shift_id: Optional[int] = None
    requested_date: date
    shift_period: str
    note: Optional[str] = None
    target_response_note: Optional[str] = None
    admin_notes: Optional[str] = None
    status: ShiftRequestStatus
    reviewed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShiftRequestTargetResponsePayload(BaseModel):
    accept: bool
    note: Optional[str] = Field(default=None, max_length=500)


class ShiftRequestAdminReviewPayload(BaseModel):
    approve: bool
    admin_notes: Optional[str] = Field(default=None, max_length=500)


# Esquemas de SwapRequest
class SwapRequestCreate(BaseModel):
    target_agent_id: int
    origin_shift_id: int
    target_shift_id: int
    reason: Optional[str] = None


class SwapRequestResponse(BaseModel):
    id: int
    requester_id: int
    target_agent_id: int
    origin_shift_id: int
    target_shift_id: int
    status: SwapStatus
    reason: Optional[str] = None
    admin_notes: Optional[str] = None
    reviewed_by: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SwapRequestDetail(SwapRequestResponse):
    requester: Optional[UserResponse] = None
    target_agent: Optional[UserResponse] = None
    origin_shift: Optional[ShiftResponse] = None
    target_shift: Optional[ShiftResponse] = None

    class Config:
        from_attributes = True


class SwapApproval(BaseModel):
    admin_notes: Optional[str] = None


class SwapRejection(BaseModel):
    admin_notes: Optional[str] = None


# Verificação de saúde
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    database: str
    ocr: str
