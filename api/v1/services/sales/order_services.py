from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
import datetime
import secrets
import string
import time


class OrderCreateSchema(BaseModel):
    customer_id: str
    delivery_date: Optional[str] = None
    delivery_status: Optional[Literal['pending', 'shipped', 'delivered', 'processing', 'cancelled']] = 'pending'
    payment_status: Optional[Literal['unpaid', 'paid', 'refunded']] = 'unpaid'
    order_delivery_date: Optional[str] = None
    total_amount: float
    dispatch_address: str
    phone_number: str
    notes: Optional[str] = None
    additional_costs: Optional[float] = 0.0
    apply_discount: bool = False
    apply_vat: bool = False
    vat_percentage: Optional[float] = None
    discount_percentage: Optional[float] = None

    @field_validator('vat_percentage', 'discount_percentage', mode='before')
    @classmethod
    def handle_fixed_rates(cls, v: Optional[float], info):
        field_name = info.field_name
        
        if field_name == 'vat_percentage':
            return 7.5 if info.data.get('apply_vat') else 0.0
        elif field_name == 'discount_percentage':
            return 2.0 if info.data.get('apply_discount') else 0.0
        
        return 0.0 

class OrderUpdateSchema(BaseModel):
    delivery_status: Optional[Literal['pending', 'processing', 'shipped', 'delivered', 'cancelled']] = None
    payment_status: Optional[Literal['unpaid', 'paid', 'refunded']] = None
    delivery_date: Optional[str] = None
    total_amount: Optional[float] = None
    dispatch_address: Optional[str] = None
    phone_number: Optional[str] = None
    notes: Optional[str] = None
    additional_costs: Optional[float] = None

    class Config:
        extra = "forbid"



def generate_unique_order_number(prefix: str = "ORD") -> str:
    """
    Generates a unique, time-based order number.

    The format is: {PREFIX}-{YYYYMMDDHHMMSSmmm}-{RANDOM_ID}

    - YYYYMMDDHHMMSSmmm: Current time down to milliseconds.
    - RANDOM_ID: 6 cryptographically secure random characters (A-Z, 0-9).
                 This ensures uniqueness even if multiple orders are placed 
                 in the exact same millisecond.
    """
    # 1. Time Component (High-Resolution)
    # Get current time and format it down to milliseconds (e.g., 20241028163015456)
    timestamp_ms = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]

    characters = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(characters) for _ in range(6))

    # 3. Combine components
    order_number = f"{prefix}{timestamp_ms}-{random_part}"
    
    return order_number