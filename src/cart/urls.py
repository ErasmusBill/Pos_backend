import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks  # Added BackgroundTasks
from fastapi_cache.decorator import cache
from sqlmodel import Session

from src.common.responses import CustomResponse
from src.db.engine import get_session
from src.users.services import get_current_user
from src.users.models import User, UserRole

# Core Business & Notification Layer Imports
from .services import OrderService
from .schemas import CheckoutRequest, OrderResponse, DashboardAnalyticsResponse, InventoryForecastResponse
from src.notification.services import POSNotificationService
from .selectors import (
    get_order_by_id,
    get_order_by_invoice_number,
    get_orders_by_date_range,
    get_cashier_order_history,
    get_eod_dashboard_metrics,
    get_low_stock_predictive_analysis
)

order_router = APIRouter(prefix="/orders", tags=["Order & Checkout Management"])
order_service = OrderService()
notification_service = POSNotificationService()  # <-- NEW: Instantiate the notification engine


@order_router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout_cart(
        payload: CheckoutRequest,
        background_tasks: BackgroundTasks,  # <-- NEW: Inject BackgroundTasks system hook
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Process an active checkout cart collection from the register screen.
    Validates physical inventory, applies active retail tax configurations, and saves the receipt.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is currently inactive. Contact your system admin."
        )

    processed_order = await order_service.process_checkout(
        payload=payload,
        cashier_id=current_user.id,
        session=session
    )


    # If the payload includes a customer phone number, offload the digital receipt delivery
    if getattr(payload, "customer_phone", None):
        background_tasks.add_task(
            notification_service.dispatch_customer_digital_receipt,
            phone=payload.customer_phone,
            invoice_number=processed_order.invoice_number,
            total_amount=processed_order.grand_total
        )

    response_data = OrderResponse.model_validate(processed_order).model_dump()

    return CustomResponse(
        message="Transaction finalized and inventory adjusted successfully.",
        status_code=status.HTTP_201_CREATED,
        data=response_data
    )


@order_router.get("/me/history", status_code=status.HTTP_200_OK)
@cache(namespace="sales", expire=3600)  # FIXED: Aligned namespace with services.py cache invalidation loop
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


@order_router.get("/analytics/dashboard", status_code=status.HTTP_200_OK)
async def get_management_dashboard_metrics(
        date: Optional[str] = None,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Exposes high-level gross margin, tax volume, cost profiling,
    and transaction ledger distribution analysis for administrative review panels.
    """
    # Security Rule: Restrict heavy aggregated analytics fields strictly to Admin users
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only system administrators can pull administrative dashboard analytics."
        )

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date parameters format layout. Please provide a standard 'YYYY-MM-DD' query string."
            )
    else:
        target_date = datetime.utcnow().date()

    metrics = get_eod_dashboard_metrics(session=session, lookup_date=target_date)

    return CustomResponse(
        message=f"Financial analytics dashboard dataset for {target_date} compiled successfully.",
        status_code=status.HTTP_200_OK,
        data=metrics.model_dump()
    )


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
    order = None

    try:
        target_uuid = uuid.UUID(order_id_or_invoice)
        order = get_order_by_id(order_id=target_uuid, session=session)
    except ValueError:
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
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only system administrators can pull complete sales ledgers."
        )

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
    response_data = [OrderResponse.model_validate(o).model_dump() for o in orders_list]

    return CustomResponse(
        message=f"Sales ledger records for {target_date.date()} retrieved successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )


@order_router.get("/analytics/predictive-stock", status_code=status.HTTP_200_OK)
async def get_inventory_runout_predictions(
        window: int = 14,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    """
    Evaluates rolling stock logging frequencies to forecast the remaining
    lifespan depletion window for store items.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied. Only inventory managers or admins can compute stock velocity forecasts."
        )

    if window < 7 or window > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Out of bounds window. Analysis range parameter must scale smoothly between 7 and 90 days."
        )

    predictions = get_low_stock_predictive_analysis(session=session, rolling_window_days=window)

    response_payload = InventoryForecastResponse(
        analysis_window_days=window,
        generated_at=datetime.utcnow(),
        forecasts=predictions
    )

    return CustomResponse(
        message="Predictive inventory velocity engine data computed successfully.",
        status_code=status.HTTP_200_OK,
        data=response_payload.model_dump()
    )