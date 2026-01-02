from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal


class ShiftTypeUpdateSchema(BaseModel):
    name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class ShiftTypeCreateSchema(BaseModel):
    name: str
    start_time: str
    end_time: str

class ShiftScheduleCreateSchema(BaseModel):
    employee_id: str
    shift_type_id: str
    start_date: str
    end_date: str

class ShiftScheduleUpdateSchema(BaseModel):
    start_date: Optional[str]
    end_date: Optional[str]
    shift_type_id: Optional[str]