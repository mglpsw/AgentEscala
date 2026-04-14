"""
Utilitários de autenticação para gestão de tokens JWT e hashing de senhas.
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config.settings import settings

# Contexto de hashing de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Configurações de JWT
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas
REFRESH_TOKEN_EXPIRE_DAYS = 30  # 30 dias


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar uma senha em relação ao seu hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gerar o hash de uma senha."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Criar um token JWT de acesso (token_type="access").

    Args:
        data: Dados a serem codificados no token (normalmente {"sub": user_id})
        expires_delta: Tempo opcional de expiração

    Returns:
        String do token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Criar um token JWT de renovação (token_type="refresh").

    O refresh token tem vida longa e só deve ser aceito no endpoint /auth/refresh.
    Não é válido como token de autenticação nos demais endpoints.

    Args:
        data: Dados a serem codificados (normalmente {"sub": user_id})
        expires_delta: Tempo opcional de expiração

    Returns:
        String do token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Decodificar e validar assinatura/expiração de um token JWT (qualquer tipo).

    Args:
        token: String do token JWT

    Returns:
        Payload decodificado se válido, None se inválido ou expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def decode_access_token(token: str) -> Optional[dict]:
    """
    Alias de decode_token mantido para compatibilidade com código existente.

    Valida assinatura e expiração. A verificação de token_type="access" é feita
    na camada de dependência (dependencies.py), onde tokens sem a claim são
    tratados como access tokens para compatibilidade com tokens emitidos antes
    desta versão.
    """
    return decode_token(token)
