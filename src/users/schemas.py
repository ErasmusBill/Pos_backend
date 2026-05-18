import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, model_validator, ConfigDict, Field

from .models import UserRole

class UserRoleUpdate(BaseModel):
    role: UserRole

class CreateUser(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str
    first_name: str
    last_name: str
    role: UserRole = UserRole.STAFF

    @model_validator(mode='after')
    def check_passwords_match(self) -> 'CreateUser':
        if self.password != self.confirm_password:
            raise ValueError("passwords do not match")
        return self

class ProfileSchema(BaseModel):
    user_id: Optional[uuid.UUID] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = Field(None, alias="avatar", validation_alias="avatar")
    phone_number: Optional[str] = None

class UserCreateRequest(BaseModel):
    """The wrapper schema that fixes the 422 Validation Error"""
    user_data: CreateUser
    profile_data: Optional[ProfileSchema] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class CompleteResetSchema(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class LoginRequest(BaseModel):
    identifier: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None