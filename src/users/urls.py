import uuid
from datetime import timedelta
from typing import List, Optional
from fastapi import Depends, APIRouter, status, BackgroundTasks, HTTPException
from sqlmodel import Session
from fastapi_cache.decorator import cache

from src.common.utils import (
    send_email,
    ACTIVATION_SALT,
    generate_token,
    confirm_token
)
from src.common.responses import CustomResponse
from src.users.services import UserService, get_current_user
from .models import User, UserRole
from .schemas import (
    ProfileSchema,
    UserRoleUpdate,
    UserResponse,
    UserCreateRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    CompleteResetSchema, LoginRequest
)
from src.db.engine import get_session
from .selectors import get_user_by_id, get_all_users as selector_get_all_users
from .utils import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token

user_router = APIRouter()
user_service = UserService()



@user_router.post("/create-user", response_model=UserResponse, tags=["Public - Users"], status_code=status.HTTP_201_CREATED)
async def create_user(request: UserCreateRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    try:
        new_user = await user_service.create_user(
            user_data=request.user_data,
            profile_data=request.profile_data,
            session=session
        )
        token = generate_token(new_user.email, salt=ACTIVATION_SALT)
        activation_url = f"http://localhost:8000/api/v1/users/activate-account/{token}"

        send_email(
            background_tasks=background_tasks,
            subject="Activate Your Account",
            recipients=[new_user.email],
            body=f"Click the link to activate: {activation_url}"
        )
        return CustomResponse(message="User created successfully, Please check your email, a link has being sent to activate your account", status_code=status.HTTP_201_CREATED, data=UserResponse.model_validate(new_user))
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

@user_router.get("/activate-account/{token}", tags=["Public - Users"])
async def activate_account(token: str, session: Session = Depends(get_session)):
    email = confirm_token(token, salt=ACTIVATION_SALT, expiration=3600)
    if not email:
        return CustomResponse(message="The activation link is invalid or has expired.", status_code=status.HTTP_400_BAD_REQUEST)
    try:
        user = await user_service.activate_user_by_email(email=email, session=session)
        return CustomResponse(message="Account activated successfully!", data={"email": user.email, "is_verified": user.is_verified})
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=404)



@user_router.get("/me", response_model=UserResponse,tags=["Public - Users"])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return CustomResponse(message="Profile retrieved", data=UserResponse.model_validate(current_user))

@user_router.patch("/update-my-profile", response_model=UserResponse, tags=["Public - Users"])
async def update_my_profile(profile_data: ProfileSchema, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Updates the profile of the LOGGED-IN user."""
    try:
        updated_user = await user_service.update_user_profile(
            user_id=current_user.id, # Uses ID from token, not URL
            profile_data=profile_data,
            session=session
        )
        return CustomResponse(message="Profile updated", data=UserResponse.model_validate(updated_user))
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=status.HTTP_400_BAD_REQUEST)

@user_router.post("/change-password", tags=["Password Management"])
async def change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        updated_user = await user_service.change_password(user_id=current_user.id, data=data, session=session)
        return CustomResponse(message="Password updated successfully", data=UserResponse.model_validate(updated_user))
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=400)

@user_router.delete("/deactivate-me", tags=["Public - Users"])
async def deactivate_self(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    """Allows a user to deactivate their own account."""
    user = await user_service.soft_delete_user(
        user_id=current_user.id,
        current_user=current_user,
        session=session
    )
    return CustomResponse(message="Your account has been deactivated", data={"id": user.id, "is_active": user.is_active})



@user_router.patch("/update-user-role/{user_id}", response_model=UserResponse, tags=["User -Admin"])
async def update_user_role(user_id: uuid.UUID, role_data: UserRoleUpdate, current_admin: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if current_admin.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to perform this action"
        )
    try:
        updated_user = await user_service.update_user_role(
            user_id=user_id,
            role_data=role_data,
            current_admin=current_admin,
            session=session
        )
        return CustomResponse(message="User role updated", data=UserResponse.model_validate(updated_user))
    except (PermissionError, ValueError) as e:
        code = 403 if isinstance(e, PermissionError) else 400
        return CustomResponse(message=str(e), status_code=code)

@user_router.get("/all-users", tags=["User -Admin"])
@cache(expire=3600, namespace="users")
async def list_all_users(*, is_verified:Optional[bool] = True, current_admin: User = Depends(get_current_user), session: Session = Depends(get_session)):

    users = selector_get_all_users(session=session, is_verified=is_verified)
    return CustomResponse(message="All users retrieved", data=[UserResponse.model_validate(u) for u in users])



@user_router.post("/forgot-password", tags=["Password Management"])
async def forgot_password(data: ForgotPasswordRequest, background_tasks: BackgroundTasks, session: Session = Depends(get_session)):
    await user_service.request_password_reset(email=data.email, background_tasks=background_tasks, session=session)
    return CustomResponse(message="If an account exists, a reset link has been sent.")

@user_router.post("/reset-password-confirm", tags=["Password Management"])
async def reset_password_confirm(data: CompleteResetSchema, session: Session = Depends(get_session)):
    try:
        updated_user = await user_service.complete_password_reset(data=data, session=session)
        return CustomResponse(message="Password reset successful", data={"email": updated_user.email})
    except ValueError as e:
        return CustomResponse(message=str(e), status_code=400)


@user_router.post("/login", tags=["User - Authentication"])
async def login(data: LoginRequest,session: Session = Depends(get_session)):
    """
    Authenticates a user via email/username and returns a JWT access token.
    """
    try:
        user = await user_service.authenticate_user(data=data, session=session)

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)


        access_token = create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)

        return CustomResponse(
            message="Login successful",
            status_code=status.HTTP_200_OK,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": UserResponse.model_validate(user)
            }
        )

    except ValueError as e:
        return CustomResponse(
            message=str(e),
            status_code=status.HTTP_401_UNAUTHORIZED
        )
