"""Staff and Doctor Authentication & Role-Based Authorization Router (MongoDB-backed)."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token
from app.services.auth_service import (
    create_user,
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
    list_users,
    seed_default_accounts,
)
from app.core.security import create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)


def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    """Extract authenticated user profile from JWT Bearer token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_email(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authenticated user record not found.",
        )
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        is_active=user.get("is_active", True),
        created_at=user.get("created_at", ""),
    )


def require_role(allowed_roles: List[str]):
    """Dependency factory enforcing role-based permissions on endpoints."""
    def role_checker(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        if current_user.role not in allowed_roles and current_user.role != "Admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{current_user.role}' lacks permission for this clinical operation.",
            )
        return current_user
    return role_checker


# Role helper dependencies
require_doctor = require_role(["Doctor"])
require_receptionist = require_role(["Receptionist"])
require_admin = require_role(["Admin"])


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new staff/doctor account",
)
def signup(payload: UserCreate) -> UserResponse:
    """Create user account in MongoDB."""
    try:
        return create_user(payload)
    except ValueError as val_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(exc)}",
        )


@router.post(
    "/login",
    response_model=Token,
    summary="User login with JSON payload",
    description="Authenticates staff or clinician and returns a JWT access token.",
)
def login(payload: UserLogin) -> Token:
    """Authenticate with email and password."""
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user["email"],
        claims={"role": user["role"], "user_id": user["user_id"], "name": user["full_name"]},
    )
    user_resp = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        is_active=user.get("is_active", True),
        created_at=user.get("created_at", ""),
    )
    return Token(access_token=access_token, token_type="bearer", user=user_resp)


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 Password Request Form Login",
    description="Standard OAuth2 form login endpoint compatible with Swagger UI.",
)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """OAuth2 compatible authentication endpoint."""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        subject=user["email"],
        claims={"role": user["role"], "user_id": user["user_id"], "name": user["full_name"]},
    )
    user_resp = UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"],
        department=user["department"],
        is_active=user.get("is_active", True),
        created_at=user.get("created_at", ""),
    )
    return Token(access_token=access_token, token_type="bearer", user=user_resp)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Return profile of authenticated token bearer."""
    return current_user


@router.post(
    "/logout",
    summary="User logout",
)
def logout() -> dict:
    """Acknowledge user logout session termination."""
    return {"message": "Successfully logged out. Please clear client-side tokens."}


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List staff users (Admin only)",
)
def get_users_list(
    current_user: UserResponse = Depends(require_admin),
) -> List[UserResponse]:
    """Admin endpoint to inspect active users."""
    return list_users()
