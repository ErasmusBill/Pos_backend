import uuid
import os
from typing import Optional
from datetime import timedelta

from fastapi import BackgroundTasks, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
from fastapi_cache import FastAPICache
from jose import JWTError, jwt
from dotenv import load_dotenv

# Database and Utilities
from src.db.engine import get_session
from src.common.utils import (
    generate_token,
    PASSWORD_RESET_SALT,
    send_email,
    confirm_token,
    ACTIVATION_SALT
)
from .schemas import (
    CreateUser, ProfileSchema, UserRoleUpdate,
    ChangePasswordRequest, CompleteResetSchema, LoginRequest
)
from .selectors import (
    get_user_by_email, get_user_by_id,
    get_user_by_username, get_user_by_username_or_email
)
from .models import User, Profile, UserRole
from .utils import get_password_hash, decode_access_token
from fastapi.security import APIKeyHeader
load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))


oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=False)




async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    """
    Dependency used in routers to retrieve the currently logged-in user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    email = decode_access_token(token, credentials_exception)

    user = get_user_by_email(session=session, email=email)

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    return user



class UserService:
    def __init__(self):
        self.cache_namespace = "users"

    async def _invalidate_cache(self):
        await FastAPICache.clear(namespace=self.cache_namespace)

    async def create_user(self, *, user_data: CreateUser, profile_data: Optional[ProfileSchema] = None,
                          session: Session) -> User:
        if get_user_by_email(session=session, email=user_data.email):
            raise ValueError("Email already registered")

        if get_user_by_username(username=user_data.username, session=session):
            raise ValueError("Username already registered")

        try:
            user_dict = user_data.model_dump(exclude={"confirm_password"})
            user_dict["password"] = get_password_hash(user_data.password)

            new_user = User(**user_dict)
            session.add(new_user)
            session.flush()

            if profile_data is None:
                profile_data = ProfileSchema()

            profile_dict = profile_data.model_dump(exclude={"user_id"})
            new_profile = Profile(**profile_dict, user_id=new_user.id)
            session.add(new_profile)

            session.commit()
            session.refresh(new_user)

            await self._invalidate_cache()
            return new_user

        except Exception as e:
            session.rollback()
            raise e

    async def update_user_profile(self, *, user_id: uuid.UUID, profile_data: ProfileSchema, session: Session) -> User:
        user = get_user_by_id(session=session, user_id=user_id)
        if not user:
            raise ValueError("User Does Not Exist")

        try:
            data = profile_data.model_dump(exclude_unset=True, exclude={"user_id"})

            if user.profile:
                for key, value in data.items():
                    setattr(user.profile, key, value)
            else:
                new_profile = Profile(**data, user_id=user.id)
                session.add(new_profile)

            session.add(user)
            session.commit()
            session.refresh(user)
            await self._invalidate_cache()
            return user
        except Exception as e:
            session.rollback()
            raise e

    async def update_user_role(self, *, user_id: uuid.UUID, role_data: UserRoleUpdate, current_admin: User,
                               session: Session) -> User:
        if current_admin.role != UserRole.ADMIN:
            raise PermissionError("Only administrators can change user roles.")

        user = get_user_by_id(session=session, user_id=user_id)
        if not user:
            raise ValueError("User not found.")

        user.role = role_data.role
        session.add(user)
        session.commit()
        session.refresh(user)
        await self._invalidate_cache()
        return user

    async def soft_delete_user(self, *, user_id: uuid.UUID, current_user: User, session: Session) -> User:
        if current_user.role != UserRole.ADMIN:
            raise PermissionError("Only administrators can change user roles.")
        user = get_user_by_id(session=session, user_id=user_id)
        if not user:
            raise ValueError("User not found")

        user.is_active = False
        session.add(user)
        session.commit()
        session.refresh(user)
        await self._invalidate_cache()
        return user

    async def activate_user_by_email(self, email: str, session: Session) -> User:
        user = get_user_by_email(session=session, email=email)
        if not user:
            raise ValueError("User with this email does not exist")

        if not user.is_verified:
            user.is_verified = True
            session.add(user)
            session.commit()
            session.refresh(user)

        return user

    async def change_password(self, user_id: uuid.UUID, data: ChangePasswordRequest, session: Session) -> User:
        user = get_user_by_id(session=session, user_id=user_id)
        if not user:
            raise ValueError("User not found")

        if not user.verify_password(data.old_password):
            raise ValueError("The old password you entered is incorrect")

        if data.new_password != data.confirm_password:
            raise ValueError("New password and confirmation do not match")

        if len(data.new_password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        user.password = get_password_hash(data.new_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    async def request_password_reset(self, email: str, background_tasks: BackgroundTasks, session: Session):
        user = get_user_by_email(session=session, email=email)
        if user:
            token = generate_token(user.email, salt=PASSWORD_RESET_SALT)
            reset_link = f"http://localhost:8000/api/v1/users/reset-password-confirm?token={token}"

            send_email(
                background_tasks=background_tasks,
                subject="Password Reset Request",
                recipients=[user.email],
                body=f"Click here to reset your password: {reset_link}"
            )

    async def complete_password_reset(self, *, data: CompleteResetSchema, session: Session) -> User:
        email = confirm_token(data.token, salt=PASSWORD_RESET_SALT, expiration=900)
        if not email:
            raise ValueError("Invalid or expired reset token")

        user = get_user_by_email(session=session, email=email)
        if not user:
            raise ValueError("User no longer exists")

        if data.new_password != data.confirm_password:
            raise ValueError("Passwords do not match")

        user.password = get_password_hash(data.new_password)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    async def authenticate_user(self, data: LoginRequest, session: Session) -> User:
        user = get_user_by_username_or_email(session, data.identifier)

        if not user or not user.verify_password(data.password):
            raise ValueError("Invalid username/email or password")

        if not user.is_verified:
            raise ValueError("Please verify your email before logging in")

        return user