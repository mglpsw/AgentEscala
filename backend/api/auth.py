"""
Endpoints de autenticação da API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from ..config.database import get_db
from ..models.models import User
from ..utils.auth import verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from ..utils.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# HTTP Basic auth for login endpoint
security = HTTPBasic()


class TokenResponse(BaseModel):
    """Modelo de resposta para autenticação bem-sucedida"""
    access_token: str
    token_type: str
    expires_in: int
    user_id: int
    user_email: str
    user_role: str


class LoginRequest(BaseModel):
    """Modelo de requisição de login"""
    email: str
    password: str


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica o usuário e retorna um token JWT de acesso.

    Args:
        login_data: E-mail e senha do usuário
        db: Sessão de banco de dados

    Returns:
        Token de acesso e informações do usuário

    Raises:
        HTTPException: Se a autenticação falhar
    """
    # Busca o usuário pelo e-mail
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verifica a senha
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verifica se o usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A conta do usuário está inativa"
        )

    # Cria o token de acesso
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
    current_user: User = Depends(get_current_user)
):
    """
    Obter as informações do usuário autenticado.

    Args:
        current_user: Usuário autenticado atual

    Returns:
        Informações do usuário
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "is_active": current_user.is_active
    }
