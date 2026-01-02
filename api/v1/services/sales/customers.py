from pydantic import BaseModel, Field
from typing import Optional, Literal

class CustomerCreateSchema(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    status: Optional[Literal['active', 'inactive']] = 'active'

    class Config:
        extra = "forbid"

class CustomerUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    status: Optional[Literal['active', 'inactive']] = None

    class Config:
        extra = "forbid"