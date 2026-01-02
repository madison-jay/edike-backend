from flask import g, current_app, jsonify
from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import UUID

# Helper function for UUID validation
def is_valid_uuid(uuid_string: str) -> bool:
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False

class EmployeeDocumentCreateSchema(BaseModel):
    employee_id: Optional[str]
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50) 
    url: str
    created_by: Optional[str] = None  # Filled by API
    category: Literal["official documents", "payslips", "contracts", "certificates", "ids"] = "official documents"
    class Config:
        extra = "forbid"

class EmployeeDocumentUpdateSchema(BaseModel):
    created_by: Optional[str] = None  # Filled by API
    employee_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)  
    url: Optional[str] = None
    category: Optional[str] = None 

    class Config:
        extra = "forbid"

class TaskDocumentCreateSchema(BaseModel):
    task_id: str
    category: Literal['assignment', 'completion']
    name: str = Field(..., max_length=100)
    type: str = Field(..., max_length=50) 
    url: str
    created_by: Optional[str] = None  # Filled by API

    class Config:
        extra = "forbid"

class TaskDocumentUpdateSchema(BaseModel):
    task_id: Optional[str] = None
    category: Optional[Literal['assignment', 'completion']] = None
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[str] = Field(None, max_length=50)  # e.g., "cv", "certificate", "task_attachment"
    url: Optional[str] = None

    class Config:
        extra = "forbid"


def create_employee_document(documents: list[EmployeeDocumentCreateSchema], employee_id: str) -> list[EmployeeDocumentCreateSchema]:
    """create a document record"""
    
    creator_response = g.supabase_user_client.from_('employees').select('id').eq('user_id', g.current_user).is_('deleted_at', 'null').execute()
    if not creator_response.data:
        raise ValueError("Creator not found or deleted")
    processed_documents = []
    print(documents)
    for document in documents:
        print("Document: ", document)
        document_data = EmployeeDocumentCreateSchema(**document, employee_id=str(employee_id))
        document_data.created_by = creator_response.data[0]['id']
        document_data.employee_id = str(employee_id)

        # Check for duplicate name and URL
        existing = g.supabase_user_client.from_('employee_documents').select('id').eq('name', document_data.name).eq('url', document_data.url).eq('employee_id', document_data.created_by).execute()
        print(existing)
        if existing.data:
            continue
        response = g.supabase_user_client.from_('employee_documents').insert(document_data.model_dump()).execute()
        if not response.data:
            raise ValueError("Failed to create document")

        print(response)

        processed_documents.append(response.data[0])
    print("Processed Documents: ", processed_documents)

    return processed_documents
