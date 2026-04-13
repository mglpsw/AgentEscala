from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from ..models import UserRole, SwapStatus


# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.AGENT


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Shift schemas
class ShiftBase(BaseModel):
    start_time: datetime
    end_time: datetime
    title: str = "Work Shift"
    description: Optional[str] = None
    location: Optional[str] = None


class ShiftCreate(ShiftBase):
    agent_id: int


class ShiftUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None


class ShiftResponse(ShiftBase):
    id: int
    agent_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShiftWithAgent(ShiftResponse):
    agent: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# SwapRequest schemas
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


# Health check
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
