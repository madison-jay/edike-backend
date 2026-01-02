from pydantic import BaseModel, Field
from typing import Optional

class SupplierCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    contact_email: str = None
    contact_phone: str = None
    address: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        extra = "forbid"

class SupplierUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None

    class Config:
        extra = "forbid"