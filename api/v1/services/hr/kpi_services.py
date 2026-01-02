from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, Any
from uuid import UUID
import re

# Helper function to validate UUID strings
def validate_uuid(value: str) -> str:
    try:
        UUID(value)
        return value
    except ValueError:
        raise ValueError("Invalid UUID format")

# Helper function to validate HTTPS URLs
def validate_https_url(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    if not re.match(r'^https://', value):
        raise ValueError("URL must start with https://")
    return value

# Helper function to validate JSONB based on target_type
def validate_target_value(cls, value: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
    target_type = values.get('target_type')
    if target_type == 'numeric' and (not isinstance(value.get('value'), (int, float)) or value.get('value') < 0):
        raise ValueError("Numeric target_value must be a non-negative number")
    elif target_type == 'boolean' and not isinstance(value.get('value'), bool):
        raise ValueError("Boolean target_value must be a boolean")
    elif target_type == 'text' and not isinstance(value.get('value'), str):
        raise ValueError("Text target_value must be a string")
    elif target_type == 'percentage' and (not isinstance(value.get('value'), (int, float)) or not 0 <= value.get('value') <= 100):
        raise ValueError("Percentage target_value must be a number between 0 and 100")
    elif target_type == 'range' and (not isinstance(value.get('min'), (int, float)) or not isinstance(value.get('max'), (int, float)) or value.get('min') > value.get('max')):
        raise ValueError("Range target_value must have valid min and max numbers with min <= max")
    return value


# KPI Templates Models
class KPITemplateCreateSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    weight: float = Field(..., ge=0.0, le=1.0)
    target_type: Literal['numeric', 'boolean', 'text', 'percentage', 'range']
    target_value: Dict[str, Any]
    active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @validator('target_value')
    def validate_target(cls, v: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
        return validate_target_value(cls, v, values)

    class Config:
        extra = "forbid"

class KPITemplateUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    target_type: Optional[Literal['numeric', 'boolean', 'text', 'percentage', 'range']] = None
    target_value: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None
    updated_at: Optional[str] = None

    @validator('target_value')
    def validate_target(cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        target_type = values.get('target_type', None)
        if target_type is None and 'target_type' not in values:
            raise ValueError("target_type must be provided when updating target_value")
        return validate_target_value(cls, v, values)

    class Config:
        extra = "forbid"

# KPI Role Assignments Models
class KPIRoleAssignmentCreateSchema(BaseModel):
    kpi_id: str
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    department_id: Optional[str] = None
    created_at: Optional[str] = None

    @validator('kpi_id', 'department_id')
    def validate_uuid_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_uuid(v)

    class Config:
        extra = "forbid"

class KPIRoleAssignmentUpdateSchema(BaseModel):
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    department_id: Optional[str] = None

    @validator('department_id')
    def validate_uuid_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_uuid(v)

    class Config:
        extra = "forbid"

# Employee KPI Assignments Models
class EmployeeKPIAssignmentCreateSchema(BaseModel):
    kpi_id: str
    employee_id: str
    period_start: str
    period_end: str
    target_value: Dict[str, Any]
    status: Literal['Assigned', 'In Progress', 'Submitted', 'Approved', 'Rejected'] = 'Assigned'
    submitted_value: Optional[Dict[str, Any]] = None
    evidence_url: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_comments: Optional[str] = None
    reviewed_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: str  # From auth.uid()

    @validator('kpi_id', 'employee_id', 'reviewed_by')
    def validate_uuid_fields(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_uuid(v)

    @validator('evidence_url')
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_https_url(v)

    @validator('target_value')
    def validate_target(cls, v: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, Any]:
        # Assume target_type is fetched from kpi_templates via kpi_id in application logic
        # For simplicity, validate structure only
        if 'value' not in v and 'min' not in v and 'max' not in v:
            raise ValueError("target_value must contain 'value' or 'min' and 'max'")
        return v

    @validator('submitted_value')
    def validate_submitted(cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        # Similar validation as target_value
        if 'value' not in v and 'min' not in v and 'max' not in v:
            raise ValueError("submitted_value must contain 'value' or 'min' and 'max'")
        return v

    @validator('period_end')
    def validate_period(cls, v: str, values: Dict[str, Any]) -> str:
        from datetime import datetime
        start = datetime.fromisoformat(values.get('period_start').replace('Z', '+00:00'))
        end = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if end <= start:
            raise ValueError("period_end must be after period_start")
        return v

    class Config:
        extra = "forbid"

class EmployeeKPIAssignmentUpdateSchema(BaseModel):
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    target_value: Optional[Dict[str, Any]] = None
    status: Optional[Literal['Assigned', 'In Progress', 'Submitted', 'Approved', 'Rejected']] = None
    submitted_value: Optional[Dict[str, Any]] = None
    evidence_url: Optional[str] = None
    submitted_at: Optional[str] = None
    reviewed_by: Optional[str] = None
    review_comments: Optional[str] = None
    reviewed_at: Optional[str] = None
    updated_at: Optional[str] = None


    @validator('evidence_url')
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_https_url(v)

    @validator('target_value')
    def validate_target(cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        if 'value' not in v and 'min' not in v and 'max' not in v:
            raise ValueError("target_value must contain 'value' or 'min' and 'max'")
        return v

    @validator('submitted_value')
    def validate_submitted(cls, v: Optional[Dict[str, Any]], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        if 'value' not in v and 'min' not in v and 'max' not in v:
            raise ValueError("submitted_value must contain 'value' or 'min' and 'max'")
        return v

    @validator('period_end')
    def validate_period(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        if v is None or values.get('period_start') is None:
            return v
        from datetime import datetime
        start = datetime.fromisoformat(values.get('period_start').replace('Z', '+00:00'))
        end = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if end <= start:
            raise ValueError("period_end must be after period_start")
        return v

    class Config:
        extra = "forbid"