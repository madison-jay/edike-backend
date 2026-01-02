from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal, List
from datetime import date

class TaskCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: str
    end_date: str
    status: Optional[Literal['Pending', 'In Progress', 'Completed', 'Cancelled']] = 'Pending'
    priority: Optional[Literal['low', 'medium', 'high']] = 'low'
    assigned_to: Optional[List[str]] = None  # Employee ID


class TaskUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[Literal['Pending', 'In Progress', 'Completed', 'Cancelled']] = None
    priority: Optional[Literal['low', 'medium', 'high']] = None
    assigned_to: Optional[List[str]] = None  # Employee ID

 