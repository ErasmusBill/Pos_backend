import uuid
from fastapi import HTTPException, status
from sqlmodel import Session

from .models import SalesProduct
from .schemas import SalesProductCreate, SalesProductUpdate
from .selectors import get_sales_product_by_id
from src.inventory.selectors import get_product_by_id


class SalesService:
    def __init__(self):
        self.namespace = "sales"

    async def _invalidate_cache(self):
        from fastapi_cache import FastAPICache
        await FastAPICache.clear(namespace=self.namespace)

    async def create_sales_product(self, data: SalesProductCreate, admin_id: uuid.UUID, session: Session) -> SalesProduct:
        product = get_product_by_id(product_id=data.product_id, session=session)

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {data.product_id} does not exist."
            )

        try:
            data_to_dict = data.model_dump()

            new_sales_product = SalesProduct(
                **data_to_dict,
                updated_by_id=admin_id
            )

            session.add(new_sales_product)
            session.commit()
            session.refresh(new_sales_product)

            self._invalidate_cache()

            return new_sales_product

        except Exception as e:
            session.rollback()
            raise e

    async def update_sales_product(self, sales_product_id: uuid.UUID, data: SalesProductUpdate, admin_id: uuid.UUID, session: Session) -> SalesProduct:
        sales_product = await get_sales_product_by_id(sales_product_id=sales_product_id, session=session)

        if not sales_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales configuration with ID {sales_product_id} not found."
            )

        try:
            update_data = data.model_dump(exclude_unset=True)

            for key, value in update_data.items():
                setattr(sales_product, key, value)

            # Keep an accurate track of who touched this pricing matrix last
            sales_product.updated_by_id = admin_id

            session.commit()
            session.refresh(sales_product)
            self._invalidate_cache()
            return sales_product

        except Exception as e:
            session.rollback()
            raise e

    async def soft_delete_sales_product(self, sales_product_id: uuid.UUID, admin_id: uuid.UUID, session: Session) -> SalesProduct:
        sales_product = await get_sales_product_by_id(sales_product_id=sales_product_id, session=session)

        if not sales_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales configuration with ID {sales_product_id} not found."
            )

        try:
            sales_product.is_active = False
            sales_product.updated_by_id = admin_id

            session.commit()
            session.refresh(sales_product)
            self._invalidate_cache()

            return sales_product

        except Exception as e:
            session.rollback()
            raise e

    async def activate_sales_product(self, sales_product_id: uuid.UUID, admin_id: uuid.UUID, session: Session) -> SalesProduct:
        sales_product = await get_sales_product_by_id(sales_product_id=sales_product_id, session=session)

        if not sales_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales configuration with ID {sales_product_id} not found."
            )

        try:
            sales_product.is_active = True
            sales_product.updated_by_id = admin_id

            session.commit()
            session.refresh(sales_product)
            self._invalidate_cache()

            return sales_product

        except Exception as e:
            session.rollback()
            raise e