"""
Armazenamento em memória para refresh tokens revogados (blacklist).

AVISO: Este estado é volátil — reiniciar o backend invalida todos os tokens
revogados anteriormente, fazendo com que voltem a ser aceitos. Comportamento
aceitável para MVP. Em produção, substituir por armazenamento persistente
(Redis, tabela de banco de dados, etc.).
"""
from typing import Set

# Conjunto de tokens revogados (strings completas do JWT)
_revoked_refresh_tokens: Set[str] = set()


def revoke_refresh_token(token: str) -> None:
    """Adiciona um refresh token à lista de revogados."""
    _revoked_refresh_tokens.add(token)


def is_refresh_token_revoked(token: str) -> bool:
    """Verifica se um refresh token está na blacklist."""
    return token in _revoked_refresh_tokens


def clear_revoked_tokens() -> None:
    """Limpa todos os tokens revogados. Usado em testes."""
    _revoked_refresh_tokens.clear()
