import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OrderItemCreate(BaseModel):
    """Represents a single row item inside the cashier's active retail cart."""
    product_id: uuid.UUID = Field(..., description="The physical asset ID being purchased")
    quantity: int = Field(..., gt=0, description="Quantity being bought")


class CheckoutRequest(BaseModel):
    """The root payload sent when clicking 'Pay & Print Receipt' at the POS client."""
    payment_method: str = Field(default="CASH", description="CASH, MOMO, CARD, or SPLIT")
    items: List[OrderItemCreate] = Field(..., min_items=1, description="Array of products in cart")


# --- OUTGOING LEDGER RESPONSE SCHEMAS ---

class OrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_price: float
    cost_price: float
    tax_rate: float
    line_total: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: uuid.UUID
    invoice_number: str
    sub_total: float
    total_tax: float
    grand_total: float
    payment_method: str
    status: str
    created_at: datetime
    cashier_id: uuid.UUID
    items: List[OrderItemResponse]

    class Config:
        from_attributes = True