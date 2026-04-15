"""
Testes mínimos para rate limiting no endpoint /auth/login.
"""
from fastapi.testclient import TestClient


def test_login_rate_limit_exceeded(client: TestClient):
    # primeiro, N tentativas falhas (senha errada)
    for _ in range(5):
        resp = client.post("/auth/login", json={"email": "medico@agentescala.com", "password": "errada"})
        assert resp.status_code == 401

    # próxima tentativa deve ser bloqueada (429)
    resp = client.post("/auth/login", json={"email": "medico@agentescala.com", "password": "errada"})
    assert resp.status_code == 429
    assert "tente" in resp.json()["detail"].lower() or "many" in resp.json()["detail"].lower()
