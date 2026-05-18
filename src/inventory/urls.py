import uuid
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlmodel import Session
from fastapi_cache.decorator import cache

from src.users.services import get_current_user
from src.users.models import User, UserRole

from .schema import (
    CreateCategory, CategoryResponse, UpdateCategory,
    CreateProduct, ProductResponse, UpdateProduct, StockAdjustment
)
from .services import InventoryService
from src.common.responses import CustomResponse
from src.db.engine import get_session

logger = logging.getLogger(__name__)

# Single instance initialization for the service layer
inventory_service = InventoryService()
inventory_router = APIRouter(prefix="/inventory")




@inventory_router.post("/categories", response_model=CategoryResponse, tags=["Admin - Category"])
async def create_category(
        data: CreateCategory,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        # Pass the full schema directly to the service layer as designed
        new_category = await inventory_service.create_category(data=data, session=session)
        return CustomResponse(
            status_code=status.HTTP_201_CREATED,
            message="Category created successfully",
            data=CategoryResponse.model_validate(new_category)
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.patch("/categories/{category_id}", response_model=CategoryResponse, tags=["Admin - Category"])
async def update_category(
        category_id: uuid.UUID,
        data: UpdateCategory,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        updated_category = await inventory_service.update_category(
            category_id=category_id,
            data=data,
            session=session
        )
        return CustomResponse(
            status_code=status.HTTP_200_OK,
            message="Category updated successfully",
            data=CategoryResponse.model_validate(updated_category)
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.delete("/categories/{category_id}", tags=["Admin - Category"])
async def delete_category(
        category_id: uuid.UUID,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        await inventory_service.delete_category(category_id=category_id, session=session)
        return CustomResponse(
            message="Category deleted successfully",
            status_code=status.HTTP_200_OK
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.get("/categories", tags=["Public - Category"])
@cache(expire=3600, namespace="inventory")
async def get_categories(session: Session = Depends(get_session)):
    categories = await inventory_service.get_all_categories(session=session)
    return CustomResponse(
        status_code=status.HTTP_200_OK,
        data=[CategoryResponse.model_validate(c) for c in categories],
        message="Categories retrieved successfully"
    )


@inventory_router.get("/categories/{category_id}", tags=["Public - Category"])
@cache(expire=3600, namespace="inventory")
async def get_category_detail(category_id: uuid.UUID, session: Session = Depends(get_session)):
    category = await inventory_service.get_category_by_id(category_id=category_id, session=session)
    if not category:
        return CustomResponse(message="Category not found", status_code=status.HTTP_404_NOT_FOUND)
    return CustomResponse(
        status_code=status.HTTP_200_OK,
        data=CategoryResponse.model_validate(category),
        message="Category retrieved successfully"
    )



@inventory_router.post("/products", tags=["Admin - Product"])
async def create_product(
        name: str = Form(...),
        sku: Optional[str] = Form(None),
        cost_price: float = Form(0.0),
        reorder_level: int = Form(5),
        category_id: uuid.UUID = Form(...),
        quantity_in_stock: int = Form(0),
        is_active: bool = Form(True),
        image: Optional[UploadFile] = File(None),
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        data = CreateProduct(
            name=name, sku=sku, cost_price=cost_price,
            reorder_level=reorder_level, category_id=category_id,
            quantity_in_stock=quantity_in_stock, is_active=is_active
        )
        new_product = await inventory_service.create_product(data=data, image=image, session=session)
        return CustomResponse(
            status_code=status.HTTP_201_CREATED,
            data=ProductResponse.model_validate(new_product),
            message="Product created successfully"
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.patch("/products/{product_id}", tags=["Admin - Product"])
async def update_product(
        product_id: uuid.UUID,
        name: Optional[str] = Form(None),
        cost_price: Optional[float] = Form(None),
        reorder_level: Optional[int] = Form(None),
        category_id: Optional[uuid.UUID] = Form(None),
        is_active: Optional[bool] = Form(None),
        new_image: Optional[UploadFile] = File(None),
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        # Build payload extracting parameters cleanly
        update_data = UpdateProduct(
            name=name, cost_price=cost_price,
            reorder_level=reorder_level, category_id=category_id,
            is_active=is_active
        )

        updated_product = await inventory_service.update_product(
            product_id=product_id,
            data=update_data,
            new_image=new_image,
            session=session
        )
        return CustomResponse(
            status_code=status.HTTP_202_ACCEPTED,
            message="Product updated successfully",
            data=ProductResponse.model_validate(updated_product)
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.delete("/products/{product_id}", tags=["Admin - Product"])
async def delete_product(
        product_id: uuid.UUID,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")

    try:
        await inventory_service.delete_product(product_id=product_id, session=session)
        return CustomResponse(status_code=status.HTTP_200_OK, message="Product soft-deleted successfully")
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)


@inventory_router.get("/products", tags=["Public - Product"])
@cache(expire=3600, namespace="inventory")
async def get_all_products(session: Session = Depends(get_session)):
    products = await inventory_service.get_all_products(session=session)
    return CustomResponse(
        status_code=status.HTTP_200_OK,
        data=[ProductResponse.model_validate(p) for p in products],
        message="Products retrieved successfully"
    )


@inventory_router.get("/products/{product_id}", tags=["Public - Product"])
async def get_product(product_id: uuid.UUID, session: Session = Depends(get_session)):
    product = await inventory_service.get_product_by_id(product_id=product_id, session=session)
    if not product:
        return CustomResponse(message="Product does not exist", status_code=status.HTTP_404_NOT_FOUND)
    return CustomResponse(status_code=status.HTTP_200_OK, data=ProductResponse.model_validate(product), message="Product retrived sucessfully")


@inventory_router.post("/products/{product_id}/adjust-stock", tags=["Admin - Product"])
async def adjust_stock(
        product_id: uuid.UUID,
        data: StockAdjustment,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(status_code=status.HTTP_401_UNAUTHORIZED, message="Unauthorized role access.")
    try:
        updated_product = await inventory_service.adjust_stock(
            product_id=product_id,
            data=data,
            session=session
        )
        return CustomResponse(
            status_code=status.HTTP_201_CREATED,
            message="Stock level adjusted successfully",
            data=ProductResponse.model_validate(updated_product)
        )
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)