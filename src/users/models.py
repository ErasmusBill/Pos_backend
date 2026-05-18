import uuid
from enum import Enum
from typing import Optional
from sqlmodel import Relationship, Field
from src.common.models import BaseModel
from .utils import verify_password as hash_verify


class UserRole(str, Enum):
    ADMIN = "admin"
    CASHIER = "cashier"
    STAFF = "staff"

class User(BaseModel, table=True):
    __tablename__ = "users"

    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)
    email: str = Field(unique=True, index=True, nullable=False)
    username: str = Field(unique=True, index=True, nullable=False)
    password: str = Field(nullable=False)
    is_active: bool = Field(default=True)
    is_verified: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.STAFF, index=True)

    profile: Optional["Profile"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """
        Checks if the provided plain-text password matches
        the hashed password stored in the database.
        """
        return hash_verify(password, self.password)

    def __repr__(self):
        return f"<User {self.username}>"


class Profile(BaseModel, table=True):
    __tablename__ = "profiles"

    phone_number: Optional[str] = Field(default=None, nullable=True)
    avatar_url: Optional[str] = Field(default=None)
    bio: Optional[str] = Field(default=None)
    user_id: uuid.UUID = Field(foreign_key="users.id", unique=True, nullable=False)

    user: Optional[User] = Relationship(back_populates="profile")

    def __repr__(self):
        return f"<Profile {self.phone_number}>"