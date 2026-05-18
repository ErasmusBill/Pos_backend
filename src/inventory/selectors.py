import uuid
from typing import Optional


from sqlmodel import Session,select

from .models import Category, Product


def get_category_by_name(*, category_name: str, session: Session):
    statement = select(Category).where(Category.name == category_name)
    result = session.exec(statement)
    return result.first()

def get_category_by_id(*, category_id: int, session: Session):
    statement = select(Category).where(Category.id == category_id)
    result = session.exec(statement)
    return result.first()

def get_product_by_name(*, product_name: str, session: Session):
    statement = select(Product).where(Product.name == product_name)
    result = session.exec(statement)
    return result.first()

def get_product_by_id(*, product_id: int, session: Session):
    statement = select(Product).where(Product.id == product_id)
    result = session.exec(statement)
    return result.first()

def get_product_by_sku(*, sku: str, session: Session):
    statement = select(Product).where(Product.sku == sku)
    result = session.exec(statement)
    return result.first()

def get_all_product_related_category(*, category_id: int, session: Session):
    statement = select(Product).where(Product.category_id == category_id)
    result = session.exec(statement)
    return result.all()

def get_all_products(*, session: Session, name: Optional[str] = None, sku: Optional[str] = None, category_id: Optional[uuid.UUID] = None, skip:
int=0, limit: int=100):
    statement = select(Product)

    if name:
        statement = statement.where(Product.name.ilike(f"%{name}%"))

    if sku:
        statement = statement.where(Product.sku == sku)

    if category_id:
        statement = statement.where(Product.category_id == category_id)

    statement = statement.offset(skip).limit(limit)

    result = session.exec(statement)

    return result.all()

def get_all_categories(*, session: Session, name: Optional[str] = None, skip: int = 0, limit: int = 100):
    statement = select(Category)

    if name:
        statement = statement.where(Category.name.ilike(f"%{name}%"))

    statement = statement.offset(skip).limit(limit)

    result = session.exec(statement)

    return result.all()

def category_exists_by_name(*, category_name: str, session: Session) -> bool:
    statement = select(Category).where(Category.name == category_name)
    result = session.exec(statement).first()
    return result is not None

def sku_exists(*, sku: str, session: Session) -> bool:
    statement = select(Product).where(Product.sku == sku)
    result = session.exec(statement).first()
    return result is not None

def get_low_stock_products(*, session: Session, skip: int = 0, limit: int = 100):
    """Finds all products where stock is at or below the reorder level."""
    statement = (
        select(Product)
        .where(Product.quantity_in_stock <= Product.reorder_level)
        .offset(skip)
        .limit(limit)
    )
    result = session.exec(statement)
    return result.all()

def get_inventory_valuation(*, session: Session):
    """Calculates the total value of your stock (Asset Value)."""
    # This is great for business owners to see how much money is sitting on shelves
    statement = select(Product)
    products = session.exec(statement).all()
    total_cost = sum(p.cost_price * p.quantity_in_stock for p in products)
    return {"total_cost_value": total_cost}