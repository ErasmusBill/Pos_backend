import uuid
from datetime import datetime, time, date
from typing import List, Optional
from sqlmodel import Session, select, func
from sqlalchemy.orm import selectinload

from src.inventory.models import StockLog, Product
from .models import Order, OrderItem
from src.users.models import User
from .schemas import DashboardAnalyticsResponse, PaymentMethodSummary, CashierPerformance, ProductRunoutForecast
from datetime import timedelta



def get_order_by_id(order_id: uuid.UUID, session: Session) -> Optional[Order]:
    """
    Fetch a complete order graph by its primary ID.
    Uses selectinload to eagerly pull all associated line items in an efficient query.
    """
    statement = (
        select(Order)
        .where(Order.id == order_id)
        .options(selectinload(Order.items))
    )
    return session.exec(statement).first()


def get_order_by_invoice_number(invoice_number: str, session: Session) -> Optional[Order]:
    """
    Look up an order by its unique, human-readable invoice identifier (e.g., INV-2026-0001).
    Useful for receipt lookups and barcode scanning on returns.
    """
    statement = (
        select(Order)
        .where(Order.invoice_number == invoice_number)
        .options(selectinload(Order.items))
    )
    return session.exec(statement).first()


def get_cashier_order_history(cashier_id: uuid.UUID, session: Session) -> List[Order]:
    """
    Retrieve all transactions handled by a specific cashier.
    Essential for shift reconciliation when matching their cash drawer balances.
    """
    statement = (
        select(Order)
        .where(Order.cashier_id == cashier_id)
        .order_by(Order.created_at.desc())
    )
    return session.exec(statement).all()


def get_orders_by_date_range(
        session: Session,
        start_date: datetime,
        end_date: Optional[datetime] = None
) -> List[Order]:
    """
    Extract transactions within a specific timeline.
    If no end_date is provided, it defaults to the end of the start_date's day.
    Perfect for generating EOD (End of Day) sales reports.
    """

    start_boundary = datetime.combine(start_date.date(), time.min)

    if end_date:
        end_boundary = datetime.combine(end_date.date(), time.max)
    else:
        end_boundary = datetime.combine(start_date.date(), time.max)

    statement = (
        select(Order)
        .where(Order.created_at >= start_boundary, Order.created_at <= end_boundary)
        .order_by(Order.created_at.desc())
        .options(selectinload(Order.items))
    )
    return session.exec(statement).all()


# --- 2. BACK-OFFICE REPORTING & BUSINESS INTELLIGENCE SELECTORS ---

def get_eod_dashboard_metrics(session: Session, lookup_date: date) -> DashboardAnalyticsResponse:
    """
    Executes an optimized multi-dimensional financial aggregation across your database
    for a specific calendar date window. Leverages historical item cost price snapshots
    to yield mathematically pure profit margins unaffected by future wholesale changes.
    """
    # 1. Establish absolute daily timezone boundaries (00:00:00 to 23:59:59)
    start_bounds = datetime.combine(lookup_date, time.min)
    end_bounds = datetime.combine(lookup_date, time.max)

    # 2. Extract Base Financial Aggregations from Order Headers
    header_statement = select(
        func.count(Order.id).label("total_orders"),
        func.sum(Order.grand_total).label("gross_sales"),
        func.sum(Order.total_tax).label("total_tax")
    ).where(Order.created_at >= start_bounds, Order.created_at <= end_bounds)

    header_results = session.exec(header_statement).first()

    total_orders = header_results[0] or 0
    gross_sales = round(header_results[1] or 0.0, 2)
    total_tax = round(header_results[2] or 0.0, 2)
    net_sales = round(gross_sales - total_tax, 2)

    # 3. Calculate Total Cost of Goods Sold (COGS) from Order Items
    # Maps across all line items snapshotting purchase prices at transaction runtime
    cogs_statement = select(
        func.sum(OrderItem.cost_price * OrderItem.quantity)
    ).join(Order).where(Order.created_at >= start_bounds, Order.created_at <= end_bounds)

    total_cogs = round(session.exec(cogs_statement).first() or 0.0, 2)
    net_profit = round(net_sales - total_cogs, 2)

    # Avoid zero-division errors if the register hasn't processed any transactions today
    profit_margin = round((net_profit / net_sales) * 100, 2) if net_sales > 0 else 0.0

    # 4. Extract Payment Method Distribution Split
    payment_statement = select(
        Order.payment_method,
        func.sum(Order.grand_total),
        func.count(Order.id)
    ).where(
        Order.created_at >= start_bounds,
        Order.created_at <= end_bounds
    ).group_by(Order.payment_method)

    payment_results = session.exec(payment_statement).all()
    payment_methods_summary = [
        PaymentMethodSummary(payment_method=row[0], total_amount=round(row[1], 2), order_count=row[2])
        for row in payment_results
    ]

    # 5. Extract Cashier Operator Distribution Metrics (For Shift Audits)
    cashier_statement = select(
        Order.cashier_id,
        User.name,
        func.sum(Order.grand_total),
        func.count(Order.id)
    ).join(User, Order.cashier_id == User.id) \
        .where(Order.created_at >= start_bounds, Order.created_at <= end_bounds) \
        .group_by(Order.cashier_id, User.name)

    cashier_results = session.exec(cashier_statement).all()
    cashier_summary = [
        CashierPerformance(cashier_id=str(row[0]), cashier_name=row[1], total_sales=round(row[2], 2),
                           order_count=row[3])
        for row in cashier_results
    ]

    # 6. Return consolidated strongly-typed Pydantic response object
    return DashboardAnalyticsResponse(
        target_date=lookup_date,
        total_orders=total_orders,
        gross_sales=gross_sales,
        total_tax_collected=total_tax,
        net_sales=net_sales,
        total_cost_of_goods_sold=total_cogs,
        net_profit=net_profit,
        profit_margin_percentage=profit_margin,
        payment_methods=payment_methods_summary,
        cashier_breakdown=cashier_summary
    )


def get_low_stock_predictive_analysis(session: Session, rolling_window_days: int = 14) -> List[ProductRunoutForecast]:
    """
    Analyzes historical negative sales deltas within a rolling window to project
    the exact operational runout date for all store products.
    """
    # 1. Compute rolling historical date threshold
    cutoff_date = datetime.utcnow() - timedelta(days=rolling_window_days)

    # 2. Query aggregate sales deltas per product directly inside DB memory
    # We explicitly look for negative changes containing 'SALE' to isolate consumer drain
    velocity_statement = select(
        StockLog.product_id,
        func.sum(StockLog.quantity_changed).label("total_depleted")
    ).where(
        StockLog.created_at >= cutoff_date,
        StockLog.quantity_changed < 0,
        StockLog.reason.like("SALE%")
    ).group_by(StockLog.product_id)

    log_results = session.exec(velocity_statement).all()
    # Map out a clean look-up dictionary: {product_id: absolute_units_sold}
    sales_velocity_map = {row[0]: abs(row[1]) for row in log_results}

    # 3. Pull all active physical trackable products
    products_statement = select(Product)
    all_products = session.exec(products_statement).all()

    compiled_forecasts = []

    for product in all_products:
        units_sold = sales_velocity_map.get(product.id, 0)

        # Calculate daily velocity depletion rate
        daily_velocity = round(units_sold / rolling_window_days, 2)

        # Calculate trailing days remaining before running dry
        if daily_velocity > 0:
            days_remaining = round(product.quantity_in_stock / daily_velocity, 1)
        else:
            days_remaining = None  # Stagnant item, no active sales velocity recorded

        # Determine urgency status flags for manager notifications
        if days_remaining is None:
            urgency = "STABLE"
        elif days_remaining <= 3.0:
            urgency = "CRITICAL"
        elif days_remaining <= 7.0:
            urgency = "WARNING"
        else:
            urgency = "STABLE"

        compiled_forecasts.append(
            ProductRunoutForecast(
                product_id=product.id,
                product_name=product.name,
                current_stock=product.quantity_in_stock,
                units_sold_last_14_days=units_sold,
                daily_velocity_rate=daily_velocity,
                estimated_days_remaining=days_remaining,
                reorder_urgency=urgency
            )
        )


    compiled_forecasts.sort(key=lambda x: (x.estimated_days_remaining is None, x.estimated_days_remaining))

    return compiled_forecasts