import uuid
import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# --- CATEGORY SCHEMAS ---

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class CreateCategory(CategoryBase):
    """Used for POST /categories"""
    pass


class UpdateCategory(BaseModel):
    """Used for PATCH /categories/{id}"""
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    """Used for returning category data"""
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# --- PRODUCT SCHEMAS ---

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2)
    sku: Optional[str] = Field(..., description="Unique Stock Keeping Unit")
    description: Optional[str] = None
    cost_price: Optional[float] = Field(..., ge=0, description="What you bought it for")
    reorder_level: int = Field(default=5, ge=0)
    category_id: uuid.UUID
    is_active: bool = Field(default=True)
    image_url: Optional[str] = None
    image_blurhash: Optional[str] = None


class CreateProduct(ProductBase):
    """Used for POST /products"""
    quantity_in_stock: int = Field(default=0, ge=0)


class UpdateProduct(BaseModel):
    """Used for PATCH /products/{id}"""
    name: Optional[str] = None
    description: Optional[str] = None
    cost_price: Optional[float] = Field(None, ge=0)
    image_url: Optional[str] = None
    reorder_level: Optional[int] = None
    category_id: Optional[uuid.UUID] = None


class ProductResponse(ProductBase):
    """Used for returning product data, includes category name"""
    id: uuid.UUID
    quantity_in_stock: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    # Optional: Include category details in the product response
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


# --- STOCK MANAGEMENT SCHEMAS ---

class StockAdjustment(BaseModel):
    """Used for adding or removing stock manually"""
    quantity: int = Field(..., description="Positive to add stock, negative to remove")
    reason: str = Field(..., description="Example: 'Restock', 'Damaged', 'Returned'")


# --- BULK & DASHBOARD SCHEMAS ---

class LowStockResponse(BaseModel):
    """Used for alerts in the POS dashboard"""
    id: uuid.UUID
    name: str
    sku: str
    quantity_in_stock: int
    reorder_level: int