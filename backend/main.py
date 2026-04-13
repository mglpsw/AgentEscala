from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from .config.database import init_db
from .config.settings import settings
from .api import users, shifts, swaps, auth
from .api.schemas import HealthResponse

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
    allow_origins=["*"],  # Ajustar adequadamente para produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shifts.router)
app.include_router(swaps.router)


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
            "health": "/health"
        }
    }
