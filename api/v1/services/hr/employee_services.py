# api/v1/services/employee_services.py
from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import date
from typing import Literal, Optional, List
from uuid import UUID

ALLOWED_ROLES = ['super_admin', 'hr_manager', 'manager', 'user']

class EmployeeCreateSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    hire_date: Optional[str] = None
    position: Optional[str] = None
    department_id: Optional[str] = None
    location_id: Optional[str] = None
    guarantor_name: Optional[str] = None
    guarantor_phone_number: Optional[str] = None
    guarantor_name_2: Optional[str] = None
    guarantor_phone_number_2: Optional[str] = None
    marital_status: Optional[Literal['Single', 'Married', 'Divorced', 'Widowed']] = None
    gender: Optional[Literal['Male', 'Female', 'Other']] = None
    avatar_url: Optional[str] = None
    signature_url: Optional[str] = None
    initial_role: Optional[str] = 'user'
    leave_balance: Optional[int] = Field(21, ge=0)
    initial_role: Optional[str]
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    shift_id: Optional[str] = None

    @field_validator('initial_role')
    def validate_initial_role(cls, v):
        if v not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role: {v}. Allowed roles are: {', '.join(ALLOWED_ROLES)}")
        return v

class EmployeeUpdateSchema(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[str] = None
    hire_date: Optional[str] = None
    employment_status: Optional[Literal['Active', 'Terminated', 'On Leave']] = None
    position: Optional[str] = None
    department_id: Optional[str] = None
    location_id: Optional[str] = None
    guarantor_name: Optional[str] = None
    guarantor_phone_number: Optional[str] = None
    guarantor_name_2: Optional[str] = None
    guarantor_phone_number_2: Optional[str] = None
    marital_status: Optional[Literal['Single', 'Married', 'Divorced', 'Widowed']] = None
    gender: Optional[Literal['Male', 'Female', 'Other']] = None
    avatar_url: Optional[str] = None
    leave_balance: Optional[int] = Field(None, ge=0)
    role: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_name: Optional[str] = None
    shift_id: Optional[str] = None

    @field_validator('role')
    def validate_role(cls, v):
        if v is not None and v not in ALLOWED_ROLES:
            raise ValueError(f"Invalid role: '{v}'. Must be one of {', '.join(ALLOWED_ROLES)}")
        return v
    
