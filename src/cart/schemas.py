import uuid
from datetime import datetime, date
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


# --- 3. BACKOFFICE ANALYTICS & DASHBOARD SCHEMAS ---

class PaymentMethodSummary(BaseModel):
    """Aggregated financial summary metrics grouped by transaction type."""
    payment_method: str = Field(..., description="E.g., CASH, MOMO, CARD")
    total_amount: float = Field(..., description="Sum total of money processed through this channel")
    order_count: int = Field(..., description="Number of independent orders under this type")


class CashierPerformance(BaseModel):
    """Shift reconciliation breakdown tracking totals processed per operator."""
    cashier_id: str = Field(..., description="The unique system identifier of the worker")
    cashier_name: str = Field(..., description="The profile full name of the cashier")
    total_sales: float = Field(..., description="Gross revenue brought in by this specific user")
    order_count: int = Field(..., description="Total receipts printed by this operator during the timeframe")


class DashboardAnalyticsResponse(BaseModel):
    """The complete analytical data snapshot built for management dashboard views."""
    target_date: date = Field(..., description="The specific operational day being audited")
    total_orders: int = Field(..., description="Global count of checkout tickets generated")
    gross_sales: float = Field(..., description="Grand total inclusive of all retail product sales and taxes")
    total_tax_collected: float = Field(..., description="Sum of all localized values processed into tax brackets")
    net_sales: float = Field(..., description="Pure commercial sales value: Gross Sales minus Total Tax")
    total_cost_of_goods_sold: float = Field(..., description="Sum total of asset historical cost price profiles")
    net_profit: float = Field(..., description="True bottom-line money earned: Net Sales minus Cost of Goods Sold")
    profit_margin_percentage: float = Field(..., description="Calculated ratio: (Net Profit / Net Sales) * 100")
    payment_methods: List[PaymentMethodSummary] = Field(default_factory=list, description="Channel distribution mapping split")
    cashier_breakdown: List[CashierPerformance] = Field(default_factory=list, description="Operator volume ranking ledger")


class ProductRunoutForecast(BaseModel):
    product_id: uuid.UUID = Field(..., description="The database primary identifier of the asset")
    product_name: str = Field(..., description="The human-readable label of the item")
    current_stock: int = Field(..., description="Current physical quantity available in the store room")
    units_sold_last_14_days: int = Field(..., description="Total unit reduction metrics pulled via stock logs")
    daily_velocity_rate: float = Field(..., description="Average units depleted per single calendar day")
    estimated_days_remaining: Optional[float] = Field(
        None,
        description="Predicted threshold window before hitting zero stock. None indicates stagnant items."
    )
    reorder_urgency: str = Field(..., description="CRITICAL (less than 3 days), WARNING (3-7 days), or STABLE")


class InventoryForecastResponse(BaseModel):
    analysis_window_days: int = 14
    generated_at: datetime
    forecasts: List[ProductRunoutForecast]