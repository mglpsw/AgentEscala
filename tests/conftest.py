import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_agentescala.db")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-characters")
os.environ["DEBUG"] = "false"
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("METRICS_ENABLED", "true")

from backend.config.database import Base, SessionLocal, engine
from backend.main import app
from backend.models import Shift, User, UserRole
from backend.utils.auth import get_password_hash
from backend.utils.rate_limiter import clear_rate_limits



@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = User(
            email="admin@agentescala.com",
            name="Admin User",
            hashed_password=get_password_hash("password123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        alice = User(
            email="alice@agentescala.com",
            name="Alice Silva",
            hashed_password=get_password_hash("password123"),
            role=UserRole.AGENT,
            is_active=True,
        )
        bob = User(
            email="bob@agentescala.com",
            name="Bob Santos",
            hashed_password=get_password_hash("password123"),
            role=UserRole.AGENT,
            is_active=True,
        )

        db.add_all([admin, alice, bob])
        db.commit()
        db.refresh(admin)
        db.refresh(alice)
        db.refresh(bob)

        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        shifts = [
            Shift(
                agent_id=alice.id,
                start_time=now + timedelta(days=1, hours=8),
                end_time=now + timedelta(days=1, hours=16),
                title="Turno Alice",
                description="Cobertura da manhã",
                location="Escritório",
            ),
            Shift(
                agent_id=bob.id,
                start_time=now + timedelta(days=1, hours=16),
                end_time=now + timedelta(days=2),
                title="Turno Bob",
                description="Cobertura da tarde",
                location="Escritório",
            ),
            Shift(
                agent_id=alice.id,
                start_time=now + timedelta(days=2, hours=8),
                end_time=now + timedelta(days=2, hours=16),
                title="Turno Alice 2",
                description="Cobertura extra",
                location="Escritório",
            ),
        ]
        db.add_all(shifts)
        db.commit()

        # limpa rate limiter entre testes para não interferir
        clear_rate_limits()

        yield
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_headers(client: TestClient):
    token = _login(client, "admin@agentescala.com", "password123")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers(client: TestClient):
    token = _login(client, "alice@agentescala.com", "password123")
    return {"Authorization": f"Bearer {token}"}