"""
Endpoints de autenticação da API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import timedelta
from ..config.database import get_db
from ..models.models import User
from ..utils.auth import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from ..utils.dependencies import get_current_user
from ..utils.token_store import revoke_refresh_token, is_refresh_token_revoked

router = APIRouter(prefix="/auth", tags=["Autenticação"])


class TokenResponse(BaseModel):
    """Modelo de resposta para autenticação bem-sucedida"""
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user_id: int
    user_email: str
    user_role: str


class LoginRequest(BaseModel):
    """Modelo de requisição de login"""
    email: str
    password: str


class RefreshRequest(BaseModel):
    """Modelo de requisição de renovação de token"""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Modelo de resposta para renovação de token"""
    access_token: str
    token_type: str
    expires_in: int


class LogoutRequest(BaseModel):
    """Modelo de requisição de logout"""
    refresh_token: str


class LogoutResponse(BaseModel):
    """Modelo de resposta para logout"""
    message: str


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica o usuário e retorna access token + refresh token.

    Args:
        login_data: E-mail e senha do usuário
        db: Sessão de banco de dados

    Returns:
        Access token, refresh token e informações do usuário

    Raises:
        HTTPException: Se a autenticação falhar
    """
    # Busca o usuário pelo e-mail
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    # Verifica a senha
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    # Verifica se o usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A conta do usuário está inativa"
        )

    token_data = {"sub": str(user.id)}

    # Cria o token de acesso
    access_token = create_access_token(
        data=token_data,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    # Cria o refresh token
    refresh_token = create_refresh_token(
        data=token_data,
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "user_id": user.id,
        "user_email": user.email,
        "user_role": user.role.value
    }


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Renova o access token usando um refresh token válido.

    O refresh token não é rotacionado nesta etapa (MVP). Um mesmo refresh token
    pode ser usado várias vezes até expirar ou ser revogado via logout.

    Args:
        request: Refresh token atual
        db: Sessão de banco de dados

    Returns:
        Novo access token

    Raises:
        HTTPException 401: Token inválido, expirado, revogado ou de tipo errado
    """
    token = request.refresh_token

    # Verifica se o token está na blacklist
    if is_refresh_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token revogado",
        )

    # Decodifica e valida o token
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )

    # Garante que é realmente um refresh token
    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token fornecido não é um refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    # Confirma que o usuário ainda existe e está ativo
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado ou inativo",
        )

    # Emite novo access token
    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest):
    """
    Invalida o refresh token atual, efetivando o logout.

    O token é adicionado à blacklist em memória. Tokens de acesso em curso
    continuam válidos até expirarem naturalmente (comportamento padrão JWT).

    AVISO: A blacklist é volátil — reiniciar o serviço a limpa. Aceitável para MVP.

    Args:
        request: Refresh token a ser revogado

    Returns:
        Mensagem de confirmação
    """
    token = request.refresh_token

    # Valida minimamente antes de revogar (evita inserir lixo na blacklist)
    payload = decode_token(token)
    if payload is None or payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de logout inválido ou não é um refresh token",
        )

    revoke_refresh_token(token)

    return {"message": "Logout realizado com sucesso"}


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
