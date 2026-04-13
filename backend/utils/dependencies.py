"""
Dependências de autenticação para endpoints FastAPI.
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ..config.database import get_db
from ..models.models import User, UserRole
from ..utils.auth import decode_access_token

# Esquema de token HTTP Bearer
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Obter o usuário autenticado a partir do token JWT.

    Args:
        credentials: Credenciais HTTP Bearer
        db: Sessão do banco de dados

    Returns:
        Objeto User se autenticado

    Raises:
        HTTPException: Se a autenticação falhar
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível validar as credenciais",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível validar as credenciais",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A conta do usuário está inativa"
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Obter o usuário atual ativo.

    Args:
        current_user: Usuário atual obtido do token

    Returns:
        Objeto User se ativo

    Raises:
        HTTPException: Se o usuário estiver inativo
    """
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Exigir que o usuário atual seja administrador.

    Args:
        current_user: Usuário atual obtido do token

    Returns:
        Objeto User se administrador

    Raises:
        HTTPException: Se o usuário não for administrador
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilégios de administrador são necessários"
        )

    return current_user
