"""
Rate limiter simples em memória para proteger o endpoint de login.

Estratégia: contador de janelas fixas por IP (fixed window) com TTL.
- Limite configurável (padrão 5 tentativas por 60s)
- Implementação thread-safe via threading.Lock
- Baixo acoplamento: expõe uma dependência FastAPI `rate_limit_login`

Observação: em ambiente multi-replica/produção, trocar para Redis ou outro backend centralizado.
"""
from typing import Dict, Tuple
import time
import threading
from fastapi import Request, HTTPException, status

# Configuração simples
LOGIN_RATE_LIMIT = 5
WINDOW_SECONDS = 60

# Estrutura: ip -> (count, window_reset_timestamp)
_lock = threading.Lock()
_counters: Dict[str, Tuple[int, float]] = {}


def _is_allowed(ip: str) -> Tuple[bool, int]:
    """Retorna (allowed, retry_after_seconds).

    If allowed True, retry_after is 0. If not allowed, retry_after is seconds until window reset.
    """
    now = time.time()
    with _lock:
        entry = _counters.get(ip)
        if entry is None:
            # inicia janela
            _counters[ip] = (1, now + WINDOW_SECONDS)
            return True, 0

        count, reset_ts = entry
        if now >= reset_ts:
            # janela expirada -> reiniciar
            _counters[ip] = (1, now + WINDOW_SECONDS)
            return True, 0

        if count < LOGIN_RATE_LIMIT:
            _counters[ip] = (count + 1, reset_ts)
            return True, 0

        # excedeu
        retry_after = int(max(0, reset_ts - now))
        return False, retry_after


async def rate_limit_login(request: Request):
    """Dependência FastAPI que limita tentativas de login por IP.

    Levanta HTTPException 429 quando o limite é excedido.
    """
    client_host = None
    if request.client:
        client_host = request.client.host

    ip = client_host or "unknown"
    allowed, retry_after = _is_allowed(ip)
    if not allowed:
        headers = {"Retry-After": str(retry_after)}
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Tente novamente mais tarde.",
            headers=headers,
        )
    # caso permitido, apenas retorna e deixa a requisição prosseguir
    return None


def clear_rate_limits() -> None:
    """Limpa os contadores (útil para testes)."""
    with _lock:
        _counters.clear()
