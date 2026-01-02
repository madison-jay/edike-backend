from pydantic import BaseModel, Field, EmailStr, HttpUrl
from typing import Optional, Literal, List, Dict

# Module Schemas
class ModuleCreateSchema(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = None


class ModuleUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None

# Lesson Schemas
class LessonCreateSchema(BaseModel):
    module_id: str
    title: str = Field(..., min_length=1)
    description: Optional[str] = None
    youtube_link: Optional[str] = None

class LessonUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    youtube_link: Optional[str] = None

# Assignment Schemas
class AssignmentCreateSchema(BaseModel):
    role: Literal['super_admin', 'hr_manager', 'manager', 'user'] = 'user'
    assignment_type: Literal['department', 'role'] = 'department'
    department_id: Optional[str] = None

class AssignmentUpdateSchema(BaseModel):
    role: Optional[Literal['super_admin', 'hr_manager', 'manager', 'user']] = None
    assignment_type: Optional[Literal['department', 'role']] = None
    department_id: Optional[str] = None

# Employee Lesson Progress Schemas
class EmployeeLessonProgressCreateSchema(BaseModel):
    employee_id: str
    lesson_id: str
    is_completed: bool = False
    completion_date: Optional[str] = None

class EmployeeLessonProgressUpdateSchema(BaseModel):
    is_completed: Optional[bool] = None
    completion_date: Optional[str] = None

# Question Schemas
class QuestionCreateSchema(BaseModel):
    module_id: str
    question_text: str = Field(..., min_length=1)
    question_type: Literal['multiple_choice', 'short_answer'] = 'multiple_choice'
    options: Dict[str, str] = Field(..., min_length=1)  # JSONB in DB
    correct_answer: str = Field(..., min_length=1)

class QuestionUpdateSchema(BaseModel):
    question_text: Optional[str] = Field(None, min_length=1)
    question_type: Optional[Literal['multiple_choice', 'short_answer']] = None
    options: Optional[Dict[str, str]] = None
    correct_answer: Optional[str] = Field(None, min_length=1)

# Employee Test Result Schemas
class EmployeeTestResultCreateSchema(BaseModel):
    employee_id: str
    module_id: str
    score: float = Field(..., ge=0.0, le=100.0)
    passed: bool = False
    completion_date: str

class EmployeeTestResultUpdateSchema(BaseModel):
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    passed: Optional[bool] = None
    completion_date: Optional[str] = None

# Employee Question Answer Schemas
class EmployeeQuestionAnswerCreateSchema(BaseModel):
    employee_id: str
    module_id: str
    question_id: str
    submitted_answer: Optional[str] = None
    is_correct: bool
    attempt_date: str

# class EmployeeQuestionAnswerUpdateSchema(BaseModel):
#     submitted_answer: Optional[str] = None
#     is_correct: Optional[bool] = None
#     attempt_date: Optional[str] = None