from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from .config.database import init_db
from .config.settings import settings
from .api import users, shifts, swaps, auth
from .api.schemas import HealthResponse

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AgentEscala - Shift Management and Swap System",
    debug=settings.DEBUG
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shifts.router)
app.include_router(swaps.router)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    # Database tables are now managed by Alembic migrations
    # Run: alembic upgrade head
    pass


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": settings.APP_VERSION
    }


@app.get("/api/v1/info")
async def api_info():
    """API information endpoint"""
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
