import logging
import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .config.database import init_db
from .config.settings import settings
from .api import users, shifts, swaps, auth, schedule_imports, medical_profiles, me, admin_schedule, admin_ocr, shift_requests
from .api.schemas import HealthResponse
from .models import User
from .services.terminal_action_service import TerminalActionExecutor
from .utils.dependencies import require_admin
from .observability import (
    bootstrap_import_counters,
    check_database_status,
    refresh_domain_gauges,
    request_counter,
    request_duration,
)

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

request_logger = logging.getLogger("agentescala.http")

# Inicializa o app FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AgentEscala - Sistema de gestão e troca de turnos",
    debug=settings.DEBUG
)

action_executor = TerminalActionExecutor()


class TerminalActionPayload(BaseModel):
    action: str = Field(min_length=2, max_length=64)
    params: dict = Field(default_factory=dict)
    dry_run: bool = False
    timeout_seconds: int = Field(default=20, ge=1, le=120)


# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.middleware("http")
async def http_observability_middleware(request: Request, call_next):
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - start_time
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)
        request_counter.labels(request.method, path, "500").inc()
        request_duration.labels(request.method, path).observe(duration)
        request_logger.exception(
            "request_failed method=%s path=%s duration_ms=%.2f",
            request.method,
            path,
            duration * 1000,
        )
        raise

    duration = time.perf_counter() - start_time
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    request_counter.labels(request.method, path, str(response.status_code)).inc()
    request_duration.labels(request.method, path).observe(duration)
    request_logger.info(
        "request method=%s path=%s status=%s duration_ms=%.2f",
        request.method,
        path,
        response.status_code,
        duration * 1000,
    )

    return response

def _include_api_routers(prefix: str = "") -> None:
    """Registrar routers da API com prefixo opcional para compatibilidade."""
    app.include_router(auth.router, prefix=prefix)
    app.include_router(users.router, prefix=prefix)
    app.include_router(shifts.router, prefix=prefix)
    app.include_router(swaps.router, prefix=prefix)
    app.include_router(shift_requests.router, prefix=prefix)
    app.include_router(schedule_imports.router, prefix=prefix)
    app.include_router(medical_profiles.router, prefix=prefix)
    app.include_router(me.router, prefix=prefix)
    app.include_router(admin_schedule.router, prefix=prefix)
    app.include_router(admin_ocr.router, prefix=prefix)


# Rotas canônicas sem prefixo + alias /api para ambientes com reverse proxy.
_include_api_routers()
_include_api_routers("/api")


@app.on_event("startup")
async def startup_event():
    """Inicializar o banco de dados e métricas na inicialização"""
    init_db()
    bootstrap_import_counters()
    refresh_domain_gauges()
    request_logger.info(
        "ocr_integration enabled=%s base_url=%s timeout_s=%.1f",
        settings.OCR_API_ENABLED,
        settings.OCR_API_BASE_URL,
        settings.OCR_API_TIMEOUT_SECONDS,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint de verificação de saúde"""
    db_status = check_database_status()
    app_status = "healthy" if db_status == "up" else "degraded"
    ocr_status = "enabled" if settings.OCR_API_ENABLED else "disabled"
    return {
        "status": app_status,
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION,
        "database": db_status,
        "ocr": ocr_status,
    }


if settings.METRICS_ENABLED:
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        refresh_domain_gauges()
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/info")
async def api_info():
    """Endpoint de informações da API"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "endpoints": {
            "users": "/users",
            "shifts": "/shifts",
            "swaps": "/swaps",
            "health": "/health",
            "auth": "/auth",
            "schedule_imports": "/schedule-imports",
            "medical_profiles": "/api/v1/medical-profiles",
            "me": "/me",
            "admin_schedule_validation": "/admin/schedule/validate",
        },
        "ocr": {
            "api_enabled": settings.OCR_API_ENABLED,
            "api_base_url": settings.OCR_API_BASE_URL,
            "api_timeout_seconds": settings.OCR_API_TIMEOUT_SECONDS,
            "api_verify_ssl": settings.OCR_API_VERIFY_SSL,
        },
    }


@app.post("/api/v1/terminal/action")
async def terminal_action(
    payload: TerminalActionPayload,
    _: User = Depends(require_admin),
):
    try:
        return action_executor.execute(
            action=payload.action,
            params=payload.params,
            timeout_seconds=payload.timeout_seconds,
            dry_run=payload.dry_run,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ─── Frontend estático ───────────────────────────────────────────────────────
# Serve o build do Vite quando frontend/dist existir.
# Rotas da API já registradas acima têm precedência sobre o catch-all.
# ─────────────────────────────────────────────────────────────────────────────

_frontend_logger = logging.getLogger("agentescala.frontend")
_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
_AVATAR_DIR = Path((os.getenv("AGENTESCALA_AVATAR_DIR", "backend/uploads/avatars")).strip()).resolve()

if _AVATAR_DIR.is_dir() or not _AVATAR_DIR.exists():
    _AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media/avatars", StaticFiles(directory=str(_AVATAR_DIR)), name="avatars_media")
    app.mount("/api/media/avatars", StaticFiles(directory=str(_AVATAR_DIR)), name="avatars_media_api")

if _FRONTEND_DIST.is_dir():
    _frontend_logger.info("Servindo frontend buildado em %s", _FRONTEND_DIST)

    # Assets Vite (JS/CSS com hash de conteúdo)
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIST / "assets")),
        name="frontend_assets",
    )

    # Prefixos exclusivos da API — 404s nesses caminhos voltam como JSON normal.
    # Qualquer outro caminho não-encontrado é tratado como rota SPA → index.html.
    _API_PATH_PREFIXES = (
        "/auth", "/users", "/shifts", "/swaps", "/schedule-imports",
        "/me", "/shift-requests", "/admin", "/health", "/metrics",
        "/docs", "/redoc", "/openapi", "/api", "/media", "/assets",
    )

    @app.exception_handler(404)
    async def spa_404_handler(request: Request, exc: Exception):
        """Fallback SPA: serve index.html para rotas do React Router.

        Rotas da API (ex.: /users/999 → "não encontrado") e assets estáticos
        continuam retornando 404 JSON sem servir o frontend por engano.
        """
        from fastapi.responses import JSONResponse

        path = request.url.path

        # Caminhos de API ou assets — preserva o 404 no formato JSON padrão
        if any(path.startswith(p) for p in _API_PATH_PREFIXES):
            detail = getattr(exc, "detail", "Not found")
            return JSONResponse({"detail": detail}, status_code=404)

        # Arquivos estáticos na raiz do dist (favicon.ico, vite.svg, …)
        candidate = _FRONTEND_DIST / path.lstrip("/")
        try:
            candidate.resolve().relative_to(_FRONTEND_DIST.resolve())
            if candidate.is_file() and candidate.suffix != ".html":
                return FileResponse(str(candidate))
        except ValueError:
            pass  # tentativa de path traversal — cai no fallback SPA

        # Rota do React Router — entrega index.html para o cliente resolver
        return FileResponse(str(_FRONTEND_DIST / "index.html"))

else:
    _frontend_logger.warning(
        "Frontend não buildado: %s não encontrado. "
        "Execute 'npm run build' dentro de frontend/ antes do deploy.",
        _FRONTEND_DIST,
    )
