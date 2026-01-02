
from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Literal
from uuid import UUID

ALLOWED_STATUSES = Literal['pending', 'approved', 'rejected', 'cancelled']
ALLOWED_LEAVE_TYPES = Literal['vacation', 'sick', 'personal', 'unpaid']

class LeaveRequestCreateSchema(BaseModel):
    leave_type: ALLOWED_LEAVE_TYPES
    start_date: date
    end_date: date
    reason: Optional[str] = None

    class Config:
        extra = "forbid"

class LeaveRequestUpdateSchema(BaseModel):
    status: Optional[ALLOWED_STATUSES] = None
    reason: Optional[str] = None

    class Config:
        extra = "forbid"

class LeaveBalanceUpdateSchema(BaseModel):
    leave_balance: int = Field(..., ge=0)  # Must provide new balance, non-negative

    class Config:
        extra = "forbid"