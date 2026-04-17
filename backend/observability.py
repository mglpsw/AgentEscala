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

# Métricas OCR (fase operacional 1.5.1 consolidada)
ocr_requests_total = Counter(
    "ocr_requests_total",
    "Total de execuções OCR por estratégia efetivamente utilizada",
    ["strategy"],
)

ocr_api_success_total = Counter(
    "ocr_api_success_total",
    "Total de chamadas OCR via API externa concluídas com sucesso",
)

ocr_api_failure_total = Counter(
    "ocr_api_failure_total",
    "Total de chamadas OCR via API externa com falha",
)

ocr_fallback_used_total = Counter(
    "ocr_fallback_used_total",
    "Total de vezes em que o fallback OCR local foi acionado",
    ["fallback_type"],
)

ocr_api_latency_seconds = Histogram(
    "ocr_api_latency_seconds",
    "Latência da chamada OCR na API externa (segundos)",
)


def record_ocr_request(strategy: str) -> None:
    """Registra execução OCR por estratégia com cardinalidade controlada."""
    normalized = "fallback_local" if strategy == "fallback_local" else "api"
    ocr_requests_total.labels(normalized).inc()


def record_ocr_api_success(latency_seconds: float) -> None:
    """Registra sucesso e latência de OCR externo."""
    ocr_api_success_total.inc()
    ocr_api_latency_seconds.observe(max(0.0, float(latency_seconds)))


def record_ocr_api_failure(latency_seconds: float | None = None) -> None:
    """Registra falha da OCR API e latência quando disponível."""
    ocr_api_failure_total.inc()
    if latency_seconds is not None:
        ocr_api_latency_seconds.observe(max(0.0, float(latency_seconds)))


def record_ocr_fallback_used(fallback_type: str) -> None:
    """Registra uso de fallback OCR local com tipos controlados."""
    normalized = fallback_type if fallback_type in {"local_pdf", "local_image"} else "local_unknown"
    ocr_fallback_used_total.labels(normalized).inc()


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
