from typing import Optional, Any, Sequence

from sqlmodel import select, Session, or_

from .models import User

def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email).where(User.is_active == True)
    return session.exec(statement).first()

def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(User.username == username)
    result = session.exec(statement)
    return result.first()

def get_user_by_id(*, session: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id).where(User.is_active == True)
    result = session.exec(statement)
    return result.first()



def get_all_users(*, session: Session, username: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None, email: Optional[str] = None, is_verified: bool,skip: int = 0, limit: int = 100) -> Sequence[User]:

    statement = select(User)

    if username:
        statement = statement.where(User.username.contains(username))

    if email:
        statement = statement.where(User.email.contains(email))

    if first_name:
        statement = statement.where(User.first_name.ilike(f"%{first_name}%"))

    if is_verified:
        statement = statement.where(User.is_verified == True)

    if last_name:
        statement = statement.where(User.last_name.ilike(f"%{last_name}%"))

    statement = statement.offset(skip).limit(limit)
    return session.exec(statement).all()

def get_active_users(*, session: Session):
    statement = select(User).where(User.is_active == True)
    return session.exec(statement).all()

def get_user_by_username_or_email(session: Session, identifier: str) -> User | None:
    """
    Finds a user where the 'username' OR 'email' matches the identifier.
    """
    statement = select(User).where(
        or_(
            User.username == identifier,
            User.email == identifier
        )
    )
    result = session.exec(statement)
    return result.first()