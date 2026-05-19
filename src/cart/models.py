import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, Relationship, SQLModel
from src.common.models import BaseModel

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.inventory.models import Product
    from src.users.models import User


class Order(BaseModel, table=True):
    """
    The Order Header: Represents an immutable historical receipt.
    Tracks structural totals, aggregations, payment types, and the processing operator.
    """
    __tablename__ = "orders"

    invoice_number: str = Field(unique=True, index=True, description="Human-readable receipt ID (e.g., INV-2026-0001)")

    # Financial Aggregations
    sub_total: float = Field(default=0.0, ge=0, description="Total retail price before tax extraction")
    total_tax: float = Field(default=0.0, ge=0, description="Aggregated tax calculated across all line items")
    grand_total: float = Field(default=0.0, ge=0,
                               description="The final amount paid by the customer (sub_total + total_tax)")

    # Metadata Mechanics
    payment_method: str = Field(default="CASH", description="CASH, MOMO, CARD, or SPLIT")
    status: str = Field(default="COMPLETED", index=True, description="COMPLETED, PENDING, REFUNDED, CANCELLED")

    # Audit Logs
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    cashier_id: uuid.UUID = Field(foreign_key="users.id", description="The operator who checked out this transaction")

    # Relationships
    items: List["OrderItem"] = Relationship(back_populates="order", cascade_delete=True)


class OrderItem(BaseModel, table=True):
    """
    The Order Line Item: An absolute historical snapshot record of a sold item.
    Crucial Rule: We copy financial figures directly onto this row to prevent future
    SalesProduct price/tax adjustments from falsifying past accounting history.
    """
    __tablename__ = "order_items"

    quantity: int = Field(default=1, gt=0)

    # Historical Financial Snapshots
    unit_price: float = Field(..., ge=0, description="Snapshot copy of SalesProduct.selling_price during checkout")
    cost_price: float = Field(..., ge=0, description="Snapshot copy of Product.cost_price for dynamic margin profiling")
    tax_rate: float = Field(default=15.0, ge=0, description="Snapshot copy of SalesProduct.tax_rate during checkout")
    line_total: float = Field(..., ge=0, description="Calculated as: (unit_price * quantity)")

    # Foreign Keys
    order_id: uuid.UUID = Field(foreign_key="orders.id", ondelete="CASCADE", index=True)
    product_id: uuid.UUID = Field(foreign_key="products.id", ondelete="RESTRICT", index=True)

    # Relationships
    order: Optional[Order] = Relationship(back_populates="items")
    product: Optional["Product"] = Relationship()