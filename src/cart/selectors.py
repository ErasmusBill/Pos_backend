import uuid
from datetime import datetime, time
from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload

from .models import Order


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
    # Normalize start_date to the absolute beginning of that day (00:00:00)
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