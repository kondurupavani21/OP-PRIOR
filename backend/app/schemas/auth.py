"""Pydantic v2 schemas for authentication, user profiles, and RBAC."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user attributes."""
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="Doctor", description="Doctor, Receptionist, or Admin")
    department: str = Field(default="General Medicine")


class UserCreate(UserBase):
    """User registration payload."""
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    """User login payload."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """User public profile response."""
    user_id: str = Field(..., description="Unique alphanumeric identifier, e.g. USR-1001")
    is_active: bool = True
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Bearer access token payload."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Parsed token payload data."""
    email: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[str] = None
