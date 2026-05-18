import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from src.common.models import BaseModel

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.inventory.models import Product


class SalesProduct(BaseModel, table=True):
    __tablename__ = "sales_product"

    product_id: uuid.UUID = Field(foreign_key="products.id", unique=True, index=True)

    # Financial Structure
    selling_price: float = Field(ge=0)
    is_taxable: bool = Field(default=True)
    tax_rate: float = Field(default=15.0)

    # Status Guard
    is_active: bool = Field(default=True, index=True)
    updated_by_id: uuid.UUID = Field(foreign_key="users.id")

    # FIXED: back_populates matches the property name inside Product ('sales_product')
    product: "Product" = Relationship(back_populates="sales_product")