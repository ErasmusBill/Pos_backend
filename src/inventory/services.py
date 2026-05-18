import uuid
import logging
import os
import shutil
from typing import Optional

from sqlmodel import Session, select
from fastapi_cache import FastAPICache
from fastapi import UploadFile

from .models import Category, Product, StockLog
from .schema import (
    CreateCategory, UpdateCategory,
    CreateProduct, UpdateProduct, StockAdjustment
)
from .selectors import (
    category_exists_by_name, get_category_by_id,
    sku_exists, get_product_by_id
)

from src.common.utils import generate_sku, generate_image_blurhash

logger = logging.getLogger(__name__)


class InventoryService:
    def __init__(self, upload_dir: str = "static/uploads/products"):
        self.cache_namespace = "inventory"
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)

    async def _invalidate_cache(self):
        """Clears the inventory cache so the frontend sees fresh data."""
        try:
            await FastAPICache.clear(namespace=self.cache_namespace)
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    async def create_category(self, data: CreateCategory, session: Session):
        if category_exists_by_name(category_name=data.name, session=session):
            raise ValueError(f"Category with name '{data.name}' already exists")

        try:
            new_category = Category(**data.model_dump())
            session.add(new_category)
            session.commit()
            session.refresh(new_category)
            await self._invalidate_cache()
            return new_category
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating category: {e}")
            raise e

    async def update_category(self, category_id: uuid.UUID, data: UpdateCategory, session: Session):
        category = get_category_by_id(category_id=category_id, session=session)
        if not category:
            raise ValueError("Category does not exist")

        try:
            data_dict = data.model_dump(exclude_unset=True)
            for key, value in data_dict.items():
                setattr(category, key, value)
            session.add(category)
            session.commit()
            session.refresh(category)
            await self._invalidate_cache()
            return category
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating category {category_id}: {e}")
            raise e

    async def delete_category(self, category_id: uuid.UUID, session: Session):
        category = get_category_by_id(category_id=category_id, session=session)
        if not category:
            raise ValueError("Category does not exist")

        if category.items and len(category.items) > 0:
            raise ValueError("Cannot delete category: It contains linked products. Reassign items first.")

        try:
            session.delete(category)
            session.commit()
            await self._invalidate_cache()
            return True
        except Exception as e:
            session.rollback()
            raise e

    async def create_product(self, *, data: CreateProduct, image: Optional[UploadFile], session: Session):
        category = get_category_by_id(category_id=data.category_id, session=session)
        if not category:
            raise ValueError("Category not found")

        final_sku = data.sku
        if not final_sku:
            final_sku = generate_sku(data.name, category.name)
            while sku_exists(sku=final_sku, session=session):
                final_sku = generate_sku(data.name, category.name)
        else:
            if sku_exists(sku=final_sku, session=session):
                raise ValueError(f"SKU '{final_sku}' is already in use.")

        file_path = None
        image_blurhash = None

        try:
            if image:
                file_ext = image.filename.split(".")[-1]
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                file_path = os.path.join(self.upload_dir, unique_filename)

                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)

                image_blurhash = generate_image_blurhash(file_path)

            product_dict = data.model_dump(exclude={"sku", "image_url", "image_blurhash"})
            new_product = Product(
                **product_dict,
                sku=final_sku,
                image_url=file_path,
                image_blurhash=image_blurhash
            )

            session.add(new_product)
            session.commit()
            session.refresh(new_product)

            if new_product.quantity_in_stock > 0:
                initial_log = StockLog(
                    product_id=new_product.id,
                    quantity_changed=new_product.quantity_in_stock,
                    previous_quantity=0,
                    new_quantity=new_product.quantity_in_stock,
                    reason="Initial Stock Intake"
                )
                session.add(initial_log)
                session.commit()

            await self._invalidate_cache()
            return new_product

        except Exception as e:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            session.rollback()
            logger.error(f"Error creating product: {e}")
            raise e

    async def update_product(self, *, product_id: uuid.UUID, data: UpdateProduct, session: Session, new_image: Optional[UploadFile] = None):
        product = get_product_by_id(product_id=product_id, session=session)
        if not product:
            raise ValueError("Product does not exist")

        old_image_path = product.image_url
        new_file_path = None

        try:
            data_dict = data.model_dump(exclude_unset=True, exclude={"sku"})
            for key, value in data_dict.items():
                setattr(product, key, value)

            if new_image:
                file_ext = new_image.filename.split(".")[-1]
                unique_filename = f"{uuid.uuid4()}.{file_ext}"
                new_file_path = os.path.join(self.upload_dir, unique_filename)

                with open(new_file_path, "wb") as buffer:
                    shutil.copyfileobj(new_image.file, buffer)

                product.image_url = new_file_path
                product.image_blurhash = generate_image_blurhash(new_file_path)

            session.add(product)
            session.commit()
            session.refresh(product)

            if new_image and old_image_path and os.path.exists(old_image_path):
                try:
                    os.remove(old_image_path)
                except Exception as file_err:
                    logger.warning(f"Failed to clear old image asset {old_image_path}: {file_err}")

            await self._invalidate_cache()
            return product

        except Exception as e:
            if new_file_path and os.path.exists(new_file_path):
                os.remove(new_file_path)
            session.rollback()
            logger.error(f"Error updating product {product_id}: {e}")
            raise e

    async def delete_product(self, product_id: uuid.UUID, session: Session):
        product = get_product_by_id(product_id=product_id, session=session)
        if not product:
            raise ValueError("Product does not exist")

        try:
            product.is_active = False
            session.add(product)
            session.commit()
            session.refresh(product)
            await self._invalidate_cache()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error soft deleting product {product_id}: {e}")
            raise e

    async def adjust_stock(self, *, product_id: uuid.UUID, data: StockAdjustment, session: Session):
        """
        Adjusts stock safely using a pessimistic execution flow to ensure data concurrency stability.
        """
        try:
            statement = select(Product).where(Product.id == product_id).with_for_update()
            product = session.exec(statement).first()

            if not product:
                raise ValueError("Product does not exist")

            old_quantity = product.quantity_in_stock
            new_quantity = old_quantity + data.quantity

            if new_quantity < 0:
                raise ValueError(f"Cannot reduce stock below 0. Current stock is {old_quantity}.")

            product.quantity_in_stock = new_quantity
            session.add(product)

            log_entry = StockLog(
                product_id=product.id,
                quantity_changed=data.quantity,
                previous_quantity=old_quantity,
                new_quantity=new_quantity,
                reason=data.reason
            )
            session.add(log_entry)

            session.commit()
            session.refresh(product)
            await self._invalidate_cache()

            return product
        except Exception as e:
            session.rollback()
            logger.error(f"Failed stock adjustment for product {product_id}: {e}")
            raise e



    async def get_all_categories(self, *, session: Session, name: Optional[str] = None, skip: int = 0, limit: int = 100):
        """Fetches a paginated list of categories, optionally filtered by name."""
        from .selectors import get_all_categories
        return get_all_categories(session=session, name=name, skip=skip, limit=limit)

    async def get_category_by_id(self, *, category_id: uuid.UUID, session: Session):
        """Retrieves a single category instance by its unique UUID identifier."""
        from .selectors import get_category_by_id
        return get_category_by_id(category_id=category_id, session=session)

    async def get_category_by_name(self, *, category_name: str, session: Session):
        """Finds a single category matching an exact string name."""
        from .selectors import get_category_by_name
        return get_category_by_name(category_name=category_name, session=session)


    async def get_all_products(
        self,
        *,
        session: Session,
        name: Optional[str] = None,
        sku: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100
    ):
        """Fetches a paginated list of products with optional search and relation filters."""
        from .selectors import get_all_products
        return get_all_products(
            session=session,
            name=name,
            sku=sku,
            category_id=category_id,
            skip=skip,
            limit=limit
        )

    async def get_product_by_id(self, *, product_id: uuid.UUID, session: Session):
        """Retrieves a single product instance by its unique UUID identifier."""
        from .selectors import get_product_by_id
        return get_product_by_id(product_id=product_id, session=session)

    async def get_product_by_sku(self, *, sku: str, session: Session):
        """Retrieves a product corresponding to a scan barcode or custom string SKU."""
        from .selectors import get_product_by_sku
        return get_product_by_sku(sku=sku, session=session)

    async def get_products_by_category(self, *, category_id: uuid.UUID, session: Session):
        """Finds all existing items registered under a specific operational catalog group."""
        from .selectors import get_all_product_related_category
        return get_all_product_related_category(category_id=category_id, session=session)



    async def get_low_stock_alerts(self, *, session: Session, skip: int = 0, limit: int = 100):
        """Exposes operational alerts to flag reorders for the shop manager."""
        from .selectors import get_low_stock_products
        return get_low_stock_products(session=session, skip=skip, limit=limit)

    async def get_inventory_valuation(self, *, session: Session):
        """Computes current asset values to calculate net holding wealth values."""
        from .selectors import get_inventory_valuation
        return get_inventory_valuation(session=session)