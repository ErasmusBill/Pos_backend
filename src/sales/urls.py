import uuid
from fastapi import APIRouter, Depends, status, HTTPException
from sqlmodel import Session

from src.common.responses import CustomResponse
from src.db.engine import get_session
from src.users.services import get_current_user
from src.users.models import User, UserRole

from .services import SalesService
from .selectors import get_all_active_sales_products, get_sales_product_by_id
from .schemas import SalesProductCreate, SalesProductUpdate, SalesProductResponse

sales_router = APIRouter(prefix="/sales", tags=["Sales Management"])
sales_service = SalesService()


@sales_router.post("/products", status_code=status.HTTP_201_CREATED)
async def create_sales_product(
        payload: SalesProductCreate,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(
            message="You ain't authorized to create sales products.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    new_sales_product = await sales_service.create_sales_product(
        data=payload,
        admin_id=current_user.id,
        session=session
    )
    response_data = SalesProductResponse.model_validate(new_sales_product).model_dump()

    return CustomResponse(
        message="Sales product configuration initialized successfully.",
        status_code=status.HTTP_201_CREATED,
        data=response_data
    )


@sales_router.get("/products", status_code=status.HTTP_200_OK)
async def get_active_sales_products(session: Session = Depends(get_session)):
    active_products = await get_all_active_sales_products(session=session)

    return CustomResponse(
        message="Active store products fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=active_products
    )


@sales_router.get("/products/{sales_product_id}", status_code=status.HTTP_200_OK)
async def get_single_sales_product(sales_product_id: uuid.UUID, session: Session = Depends(get_session)):
    sales_product = await get_sales_product_by_id(sales_product_id=sales_product_id, session=session)

    if not sales_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sales pricing configuration with ID {sales_product_id} not found."
        )

    response_data = SalesProductResponse.model_validate(sales_product).model_dump()

    return CustomResponse(
        message="Pricing configuration fetched successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )


@sales_router.patch("/products/{sales_product_id}", status_code=status.HTTP_200_OK)
async def update_sales_product(
        sales_product_id: uuid.UUID,
        payload: SalesProductUpdate,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(
            message="You ain't authorized to modify sales products.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    updated_product = await sales_service.update_sales_product(
        sales_product_id=sales_product_id,
        data=payload,
        admin_id=current_user.id,
        session=session
    )

    response_data = SalesProductResponse.model_validate(updated_product).model_dump()

    return CustomResponse(
        message="Sales product updated successfully.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )


@sales_router.delete("/products/{sales_product_id}", status_code=status.HTTP_200_OK)
async def soft_delete_sales_product(
        sales_product_id: uuid.UUID,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(
            message="You ain't authorized to deactivate sales products.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    deactivated_product = await sales_service.soft_delete_sales_product(
        sales_product_id=sales_product_id,
        admin_id=current_user.id,
        session=session
    )

    response_data = SalesProductResponse.model_validate(deactivated_product).model_dump()

    return CustomResponse(
        message="Product successfully removed from active customer-facing sale paths.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )

@sales_router.delete("/activate-sales-product/{sales_product_id}", status_code=status.HTTP_200_OK)
async def activate_sales_product(
        sales_product_id: uuid.UUID,
        session: Session = Depends(get_session),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN:
        return CustomResponse(
            message="You ain't authorized to deactivate sales products.",
            status_code=status.HTTP_403_FORBIDDEN
        )

    deactivated_product = await sales_service.soft_delete_sales_product(
        sales_product_id=sales_product_id,
        admin_id=current_user.id,
        session=session
    )

    response_data = SalesProductResponse.model_validate(deactivated_product).model_dump()

    return CustomResponse(
        message="Product successfully removed from active customer-facing sale paths.",
        status_code=status.HTTP_200_OK,
        data=response_data
    )