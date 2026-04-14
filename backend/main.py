import logging
import time
from datetime import datetime

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config.database import init_db
from .config.settings import settings
from .api import users, shifts, swaps, auth, schedule_imports
from .api.schemas import HealthResponse

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

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.on_event("startup")
async def startup_event():
    """Inicializar o banco de dados na inicialização"""
    init_db()


@app.get("/", response_model=HealthResponse)
async def root():
    """Endpoint raiz"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION
    }


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
        }
    }
