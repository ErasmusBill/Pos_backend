import uuid
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SalesProductCreate(BaseModel):
    product_id: uuid.UUID
    selling_price: float = Field(gt=0, description="The base retail selling price before tax")
    is_taxable: Optional[bool] = True
    tax_rate: Optional[float] = Field(default=15.0, ge=0)
    is_active: Optional[bool] = True


class SalesProductUpdate(BaseModel):
    selling_price: Optional[float] = Field(default=None, gt=0, description="New retail selling price")
    is_taxable: Optional[bool] = None
    tax_rate: Optional[float] = Field(default=None, ge=0)
    is_active: Optional[bool] = None


class SalesProductResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    selling_price: float
    is_taxable: bool
    tax_rate: float
    is_active: bool
    updated_by_id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)