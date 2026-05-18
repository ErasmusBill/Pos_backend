import uuid
from sqlmodel import select
from sqlmodel import Session

from src.inventory.models import Product
from src.sales.models import SalesProduct

async def get_all_active_sales_products(session: Session):
    statement = (
        select(Product, SalesProduct)
        .join(SalesProduct, Product.id == SalesProduct.product_id)
        .where(SalesProduct.is_active == True)
    )
    results = (session.exec(statement)).all()


    return [
        {
            "product_id": product.id,
            "name": product.name,
            "sku": product.sku,
            "quantity_in_stock": product.quantity_in_stock,
            "selling_price": sales_config.selling_price,
            "is_taxable": sales_config.is_taxable,
            "tax_rate": sales_config.tax_rate
        }
        for product, sales_config in results
    ]

async def get_sales_product_by_id(*, sales_product_id: uuid.UUID, session: Session):
    statement = select(SalesProduct).where(SalesProduct.id == sales_product_id)
    result = session.exec(statement)
    return result.first()