import logging
import time
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config.database import init_db
from .config.settings import settings
from .api import users, shifts, swaps, auth, schedule_imports, medical_profiles, me
from .api.schemas import HealthResponse
from .models import User
from .services.terminal_action_service import TerminalActionExecutor
from .utils.dependencies import require_admin

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

request_logger = logging.getLogger("agentescala.http")
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

# Inclui os routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shifts.router)
app.include_router(swaps.router)
app.include_router(schedule_imports.router)
app.include_router(medical_profiles.router)
app.include_router(me.router)


@app.on_event("startup")
async def startup_event():
    """Inicializar o banco de dados na inicialização"""
    init_db()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Endpoint de verificação de saúde"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION
    }


if settings.METRICS_ENABLED:
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
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
        }
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
        "/health", "/metrics", "/docs", "/redoc", "/openapi", "/api",
        "/assets",
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
