from pydantic import BaseModel, Field
from typing import Optional, Literal

class ProductsCreateScheme(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: float
    color: Optional[str] = Field(default=None, description="e.g. Black, White, Blue Mesh")
    stock_quantity: Optional[int] = Field(default=0)
    product_image: Optional[str] = None
    type: Optional[Literal['multi_part', 'single_piece']] = Field(default='single_piece')

    class Config:
        extra = "forbid"


class ProductsUpdateScheme(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    color: Optional[str] = None
    stock_quantity: Optional[int] = None
    product_image: Optional[str] = None
    type: Optional[Literal['multi_part', 'single_piece']] = None

    class Config:
        extra = "forbid"