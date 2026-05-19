import uuid
from datetime import datetime
from fastapi import HTTPException, status
from sqlmodel import Session, select

from .models import Order, OrderItem
from .schemas import CheckoutRequest
from src.sales.selectors import get_sales_product_by_id  # Or select directly
from src.inventory.models import Product, StockLog  # To read cost_price and adjust stock
from src.sales.models import SalesProduct


class OrderService:
    def __init__(self):
        self.namespace = "sales"

    async def _invalidate_cache(self):
        from fastapi_cache import FastAPICache
        await FastAPICache.clear(namespace=self.namespace)

    def _generate_invoice_number(self, session: Session) -> str:
        """
        Generates a sequential human-readable invoice identifier.
        e.g., INV-2026-0001
        """
        current_year = datetime.utcnow().year

        # Count existing orders for the current year to determine the next sequence number
        statement = select(Order).where(Order.invoice_number.like(f"INV-{current_year}-%"))
        existing_orders_count = len(session.exec(statement).all())

        next_sequence = existing_orders_count + 1
        return f"INV-{current_year}-{next_sequence:04d}"

    async def process_checkout(self, payload: CheckoutRequest, cashier_id: uuid.UUID, session: Session) -> Order:
        """
        Executes a complete POS checkout transaction block safely.
        Validates stock levels, matches pricing metadata, snapshots values, and updates inventory.
        """
        try:
            invoice_num = self._generate_invoice_number(session=session)
            db_order = Order(
                invoice_number=invoice_num,
                payment_method=payload.payment_method,
                cashier_id=cashier_id,
                sub_total=0.0,
                total_tax=0.0,
                grand_total=0.0
            )
            session.add(db_order)

            running_sub_total = 0.0
            running_total_tax = 0.0
            order_items_to_create = []

            # 2. Process Cart Line Items
            for cart_item in payload.items:
                # Fetch Physical Inventory Product details (for stock tracking and cost price)
                product = session.get(Product, cart_item.product_id)
                if not product:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Physical product with ID {cart_item.product_id} not found."
                    )

                # Fetch Active Sales Product Parameters (for retail selling prices and tax brackets)
                sales_product_statement = select(SalesProduct).where(
                    SalesProduct.product_id == cart_item.product_id,
                    SalesProduct.is_active == True
                )
                sales_product = session.exec(sales_product_statement).first()
                if not sales_product:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product '{product.name}' is not configured for retail storefront sales."
                    )

                # 3. Inventory Stock Validation Guard
                if product.quantity_in_stock < cart_item.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for '{product.name}'. Requested: {cart_item.quantity}, Available: {product.quantity_in_stock}."
                    )

                # 4. Physical Stock Allocation & Degradation
                product.quantity_in_stock -= cart_item.quantity
                session.add(product)

                # Optional: If you have a StockLog architecture for internal inventory audits, append it here
                # from src.inventory.models import StockLog
                log = StockLog(product_id=product.id, change_amount=-cart_item.quantity, reason="SALE", reference_id=invoice_num)
                session.add(log)

                # 5. Financial Mathematics Calculations
                unit_price = sales_product.selling_price
                cost_price = product.cost_price  # Retained for static historical margin analysis
                tax_rate = sales_product.tax_rate if sales_product.is_taxable else 0.0

                line_subtotal = unit_price * cart_item.quantity
                line_tax = line_subtotal * (tax_rate / 100.0)
                line_grand_total = line_subtotal + line_tax

                running_sub_total += line_subtotal
                running_total_tax += line_tax

                # 6. Instantiate Immutable Historical Snapshot Record Row
                db_item = OrderItem(
                    product_id=cart_item.product_id,
                    quantity=cart_item.quantity,
                    unit_price=unit_price,
                    cost_price=cost_price,
                    tax_rate=tax_rate,
                    line_total=line_grand_total,
                    order=db_order  # Direct model link
                )
                order_items_to_create.append(db_item)

            # 7. Bind Derived Financial Aggregations back onto Header
            db_order.sub_total = round(running_sub_total, 2)
            db_order.total_tax = round(running_total_tax, 2)
            db_order.grand_total = round(running_sub_total + running_total_tax, 2)

            # Stage line items to session context
            for item in order_items_to_create:
                session.add(item)

            # 8. Commit Atomic Unit of Work Block
            session.commit()
            session.refresh(db_order)

            # Flush read-side Redis cache layers
            await self._invalidate_cache()

            return db_order

        except HTTPException as he:
            session.rollback()
            raise he
        except Exception as e:
            session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An unhandled database tracking error crashed transaction execution: {str(e)}"
            )