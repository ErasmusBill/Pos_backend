import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session

#
from src.common.responses import CustomResponse
from src.db.engine import get_session
from src.users.services import get_current_user
from src.users.models import User, UserRole


from .services import OrderService
from .schemas import CheckoutRequest, OrderResponse
from .selectors import (
    get_order_by_id,
    get_order_by_invoice_number,
    get_orders_by_date_range,
    get_cashier_order_history
)

order_router = APIRouter(prefix="/orders", tags=["Order & Checkout Management"])
order_service = OrderService()



@order_router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout_cart(
        payload: CheckoutRequest,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Process an active checkout cart collection from the register screen.
    Validates physical inventory, applies active retail tax configurations, and saves the receipt.
    """
    # Safeguard: Block inactive accounts from creating transactions
    if not current_user.is_active:
        return CustomResponse(
            message="Your account is currently inactive. Contact your system admin.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Process transaction inside our atomic service method
    processed_order = await order_service.process_checkout(
        payload=payload,
        cashier_id=current_user.id,
        session=session
    )

    # Serialize output structure matching standard Pydantic models
    response_data = OrderResponse.model_validate(processed_order).model_dump()

    return CustomResponse(
        message="Transaction finalized and inventory adjusted successfully.",
        status_code=status.HTTP_201_CREATED,
        data=response_data
    )


# --- 2. RETRIEVE SINGLE RECEIPT DETAILS (ID OR INVOICE NUMBER) ---
@order_router.get("/{order_id_or_invoice}", status_code=status.HTTP_200_OK)
async def get_receipt_breakdown(
        order_id_or_invoice: str,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Fetch comprehensive audit logs and lines for a specific receipt record.
    Accepts either standard system UUIDs or alphanumeric invoice strings (e.g., INV-2026-0001).
    """
    # 1. Check if argument matches a system UUID format
    try:
        target_uuid = uuid.UUID(order_id_or_invoice)
        order = get_order_by_id(order_id=target_uuid, session=session)
    except ValueError:
        # 2. Treat as an alphanumeric invoice string if UUID validation fails
        order = get_order_by_invoice_number(invoice_number=order_id_or_invoice, session=session)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No matching sales transaction found for identifier: '{order_id_or_invoice}'."
        )

    response_data = OrderResponse.model_validate(order).model_dump()

    return CustomResponse(
        message="Receipt breakdown details fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )



@order_router.get("", status_code=status.HTTP_200_OK)
async def get_sales_ledger_history(
        date: Optional[str] = None,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Extract transaction records for back-office performance analysis.
    Filters transactions by an optional ISO date string (YYYY-MM-DD). If no date is provided, defaults to today.
    """
    # Security Rule: Restrict detailed financial ledger metrics to Management/Admin accounts
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(
            message="Access Denied. Only system administrators can pull complete sales ledgers.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # Normalize parsing query parameter string
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format configuration. Please pass parameters matching 'YYYY-MM-DD'."
            )
    else:
        target_date = datetime.utcnow()

    orders_list = get_orders_by_date_range(session=session, start_date=target_date)

    # Batch serialize complete array response collection
    response_data = [OrderResponse.model_validate(o).model_dump() for o in orders_list]

    return CustomResponse(
        message=f"Sales ledger records for {target_date.date()} retrieved successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )


@order_router.get("/me/history", status_code=status.HTTP_200_OK)
async def get_current_operator_history(
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Allows active cashiers to verify their transaction totals for shift reconciliation.
    """
    my_orders = get_cashier_order_history(cashier_id=current_user.id, session=session)
    response_data = [OrderResponse.model_validate(o).model_dump() for o in my_orders]

    return CustomResponse(
        message="Operator personal transaction history compiled successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )