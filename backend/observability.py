"""Métricas e utilitários de observabilidade do AgentEscala.

Módulo isolado para manter instrumentação em um único ponto,
sem alterar o fluxo de negócio existente.
"""

from __future__ import annotations

import logging

from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config.database import SessionLocal
from .models.models import ImportStatus, ScheduleImport, Shift, SwapRequest

logger = logging.getLogger("agentescala.observability")

request_counter = Counter(
    "agentescala_http_requests_total",
    "Total de requisições HTTP processadas pelo AgentEscala",
    ["method", "path", "status_code"],
)

request_duration = Histogram(
    "agentescala_http_request_duration_seconds",
    "Latência das requisições HTTP do AgentEscala",
    ["method", "path"],
)

# Métricas de alto nível da operação
shift_total_gauge = Gauge(
    "agentescala_total_shifts",
    "Quantidade total de plantões persistidos",
)

swap_total_gauge = Gauge(
    "agentescala_total_swaps",
    "Quantidade total de solicitações de troca persistidas",
)

imports_success_total = Counter(
    "agentescala_imports_success_total",
    "Total de importações concluídas com sucesso",
)

imports_failure_total = Counter(
    "agentescala_imports_failure_total",
    "Total de tentativas de importação com falha",
)


def refresh_domain_gauges(db: Session | None = None) -> None:
    """Atualiza gauges de contagem total sem impactar o fluxo de API."""
    owns_session = db is None
    session = db or SessionLocal()

    try:
        try:
            shift_total = session.query(Shift.id).count()
            swap_total = session.query(SwapRequest.id).count()
            shift_total_gauge.set(float(shift_total))
            swap_total_gauge.set(float(swap_total))
        except Exception as exc:
            logger.warning(
                "Falha ao atualizar gauges de domínio; mantendo último valor publicado. erro=%s",
                exc,
            )
    finally:
        if owns_session:
            session.close()


def bootstrap_import_counters(db: Session | None = None) -> None:
    """Inicializa os counters de importação com dados já persistidos."""
    owns_session = db is None
    session = db or SessionLocal()

    try:
        success = session.query(ScheduleImport.id).filter(ScheduleImport.status == ImportStatus.COMPLETED).count()
        failed = session.query(ScheduleImport.id).filter(ScheduleImport.status == ImportStatus.FAILED).count()
        if success > 0:
            imports_success_total.inc(float(success))
        if failed > 0:
            imports_failure_total.inc(float(failed))
    finally:
        if owns_session:
            session.close()


def check_database_status() -> str:
    """Retorna status textual do banco para healthcheck."""
    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"
    finally:
        session.close()
