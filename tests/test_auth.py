"""
Testes de autenticação: login, refresh token e logout.
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["DATABASE_URL"] = "sqlite://"
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-characters")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "")
os.environ.setdefault("METRICS_ENABLED", "true")

from backend.config.database import Base, SessionLocal, engine
from backend.main import app
from backend.models import User, UserRole
from backend.utils.auth import get_password_hash
from backend.utils.token_store import clear_revoked_tokens


@pytest.fixture(autouse=True)
def setup_database():
    """Recria o banco e limpa a blacklist antes de cada teste."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    clear_revoked_tokens()

    db = SessionLocal()
    try:
        user = User(
            email="medico@agentescala.com",
            name="Dr. Teste",
            hashed_password=get_password_hash("senha123"),
            role=UserRole.AGENT,
            is_active=True,
        )
        inactive = User(
            email="inativo@agentescala.com",
            name="Inativo",
            hashed_password=get_password_hash("senha123"),
            role=UserRole.AGENT,
            is_active=False,
        )
        db.add_all([user, inactive])
        db.commit()
        yield
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str = "medico@agentescala.com", password: str = "senha123") -> dict:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_retorna_access_e_refresh_tokens(client):
    data = _login(client)
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user_email"] == "medico@agentescala.com"


def test_login_com_senha_errada_retorna_401(client):
    response = client.post("/auth/login", json={"email": "medico@agentescala.com", "password": "errada"})
    assert response.status_code == 401


def test_login_com_usuario_inativo_retorna_403(client):
    response = client.post("/auth/login", json={"email": "inativo@agentescala.com", "password": "senha123"})
    assert response.status_code == 403


def test_login_com_email_inexistente_retorna_401(client):
    response = client.post("/auth/login", json={"email": "naoexiste@x.com", "password": "qualquer"})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

def test_refresh_valido_retorna_novo_access_token(client):
    tokens = _login(client)
    response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    # O token retornado deve ser um JWT válido e utilizável
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200


def test_refresh_com_token_invalido_retorna_401(client):
    response = client.post("/auth/refresh", json={"refresh_token": "token.invalido.aqui"})
    assert response.status_code == 401


def test_refresh_com_access_token_retorna_401(client):
    """Access token não deve ser aceito no endpoint de refresh."""
    tokens = _login(client)
    response = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401
    assert "refresh token" in response.json()["detail"].lower()


def test_access_token_nao_aceito_como_refresh(client):
    """Refresh token não deve autenticar endpoints que exigem access token."""
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['refresh_token']}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout_retorna_sucesso(client):
    tokens = _login(client)
    response = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 200
    assert "sucesso" in response.json()["message"].lower()


def test_refresh_apos_logout_retorna_401(client):
    """Refresh token revogado não pode mais ser usado."""
    tokens = _login(client)
    refresh_token = tokens["refresh_token"]

    logout = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 200

    refresh = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh.status_code == 401
    assert "revogado" in refresh.json()["detail"].lower()


def test_logout_com_token_invalido_retorna_401(client):
    response = client.post("/auth/logout", json={"refresh_token": "nao.e.um.token"})
    assert response.status_code == 401


def test_logout_com_access_token_retorna_401(client):
    """Logout deve rejeitar access token (exige refresh token)."""
    tokens = _login(client)
    response = client.post("/auth/logout", json={"refresh_token": tokens["access_token"]})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Compatibilidade com fluxo anterior
# ---------------------------------------------------------------------------

def test_access_token_ainda_funciona_em_rota_protegida(client):
    """Garantia de não regressão: login e uso do access token continuam funcionando."""
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "medico@agentescala.com"
