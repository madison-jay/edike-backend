from pydantic import BaseModel, Field
from typing import Optional


class ComponentCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None
    stock_quantity: int = Field(default=0, ge=0)
    sku: str
    color: Optional[str] = Field(default=None, description="e.g. Black, Red Fabric, Chrome")
    component_image: Optional[str] = None

    class Config:
        extra = "forbid"


class ComponentUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sku: Optional[str] = None
    color: Optional[str] = None
    component_image: Optional[str] = None
    stock_quantity: Optional[int] = Field(None, ge=0)

    class Config:
        extra = "forbid"