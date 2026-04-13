"""
Authentication API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from ..config.database import get_db
from ..models.models import User
from ..utils.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/auth", tags=["Authentication"])

# HTTP Basic auth for login endpoint
security = HTTPBasic()


class TokenResponse(BaseModel):
    """Response model for successful authentication"""
    access_token: str
    token_type: str
    expires_in: int
    user_id: int
    user_email: str
    user_role: str


class LoginRequest(BaseModel):
    """Request model for login"""
    email: str
    password: str


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticate user and return JWT access token.

    Args:
        login_data: User email and password
        db: Database session

    Returns:
        Access token and user information

    Raises:
        HTTPException: If authentication fails
    """
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "user_id": user.id,
        "user_email": user.email,
        "user_role": user.role.value
    }


@router.get("/me", response_model=dict)
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_db)  # This will be updated to use auth dependency
):
    """
    Get current authenticated user information.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        User information
    """
    from ..utils.dependencies import get_current_user
    user = await get_current_user(db=db)

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "is_active": user.is_active
    }
