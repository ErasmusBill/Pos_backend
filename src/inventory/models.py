import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Relationship, Field
from src.common.models import BaseModel


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.sales.models import SalesProduct


class Category(BaseModel, table=True):
    __tablename__ = "categories"

    name: str = Field(unique=True, index=True)
    description: Optional[str] = None

    items: List["Product"] = Relationship(back_populates="category")


class Product(BaseModel, table=True):
    __tablename__ = "products"

    name: str = Field(index=True)
    sku: str = Field(unique=True, index=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True)
    image_url: Optional[str] = None
    image_blurhash: Optional[str] = None


    cost_price: float = Field(default=0.0)
    quantity_in_stock: int = Field(default=0)
    reorder_level: int = Field(default=5)

    category_id: uuid.UUID = Field(foreign_key="categories.id")
    category: Optional[Category] = Relationship(back_populates="items")

    stock_logs: List["StockLog"] = Relationship(back_populates="product")


    sales_product: Optional["SalesProduct"] = Relationship(back_populates="product")


class StockLog(BaseModel, table=True):
    __tablename__ = "stock_logs"

    quantity_changed: int = Field(..., description="The change delta: e.g., +10 for restock, -3 for damages")
    previous_quantity: int = Field(..., description="Snapshot of stock before the change")
    new_quantity: int = Field(..., description="Snapshot of stock after the change")
    reason: str = Field(..., description="Categorization: e.g., 'Restock', 'Damaged', 'Theft', 'Sale', 'Return'")
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    product_id: uuid.UUID = Field(foreign_key="products.id", ondelete="CASCADE", index=True)
    product: Optional[Product] = Relationship(back_populates="stock_logs")