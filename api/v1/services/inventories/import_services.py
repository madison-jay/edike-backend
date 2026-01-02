from pydantic import BaseModel, Field
from typing import Optional, Literal


class ImportServiceCreateSchema(BaseModel):
    supplier_id: str
    batch_number: str
    received_date: Optional[str] = None
    expected_date: Optional[str] = None
    status: Optional[Literal['in_transit', 'completed', 'processing']] = 'in_transit'
    notes: Optional[str] = None

    class Config:
        extra = "forbid"

class ImportServiceUpdateSchema(BaseModel):
    supplier_id: Optional[str] = None
    batch_number: Optional[str] = None
    received_date: Optional[str] = None
    expected_date: Optional[str] = None
    status: Optional[Literal['in_transit', 'completed', 'processing']] = None
    notes: Optional[str] = None

    class Config:
        extra = "forbid"