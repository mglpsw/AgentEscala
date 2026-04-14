"""
Testes dos routers críticos: auth (complementar), users, shifts, swaps.

Complementa test_api.py e test_auth.py sem duplicar cobertura existente.
Fixtures de banco, client e headers vêm do conftest.py (autouse reset_database).
"""
import pytest
from fastapi.testclient import TestClient


# ─── Fixture local ──────────────────────────────────────────────────────────

@pytest.fixture
def bob_headers(client: TestClient):
    """Token JWT de Bob (agente) — necessário para testes de visibilidade entre agentes."""
    resp = client.post(
        "/auth/login",
        json={"email": "bob@agentescala.com", "password": "password123"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _get_users(client, admin_headers):
    return client.get("/users", headers=admin_headers).json()


def _user_id(client, admin_headers, email):
    user_id = next(
        (u["id"] for u in _get_users(client, admin_headers) if u["email"] == email),
        None,
    )
    if user_id is None:
        pytest.fail(f"Usuário com e-mail {email!r} não encontrado na listagem de /users")
    return user_id


def _get_shifts(client, headers):
    return client.get("/shifts", headers=headers).json()


def _shift_of(client, headers, agent_email):
    """Retorna o primeiro turno do agente indicado."""
    shift = next(
        (s for s in _get_shifts(client, headers) if s["agent"]["email"] == agent_email),
        None,
    )
    if shift is None:
        pytest.fail(f"Nenhum turno encontrado para o agente {agent_email!r}.")
    return shift


def _create_swap(client, agent_headers, admin_headers):
    """Cria solicitação de troca Alice → Bob e retorna o objeto swap."""
    alice_shift = _shift_of(client, agent_headers, "alice@agentescala.com")
    bob_shift   = _shift_of(client, agent_headers, "bob@agentescala.com")
    bob_id      = _user_id(client, admin_headers, "bob@agentescala.com")
    resp = client.post(
        "/swaps/",
        headers=agent_headers,
        json={
            "target_agent_id": bob_id,
            "origin_shift_id": alice_shift["id"],
            "target_shift_id": bob_shift["id"],
            "reason": "setup de teste",
        },
    )
    assert resp.status_code == 201
    return resp.json()


# ─────────────────────────────────────────────────────────────────────────────
# AUTH router — complementar
# test_auth.py já cobre login/refresh/logout; aqui testamos o shape completo
# do response de login e os campos retornados por /auth/me.
# ─────────────────────────────────────────────────────────────────────────────

def test_login_response_inclui_user_id_e_role(client):
    """Login retorna user_id (int) e user_role — campos consumidos pela Web UI."""
    resp = client.post(
        "/auth/login",
        json={"email": "admin@agentescala.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["user_id"], int)
    assert data["user_role"] == "admin"


def test_me_retorna_campos_completos(client, admin_headers):
    """GET /auth/me inclui id, email, name, role e is_active."""
    resp = client.get("/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert {"id", "email", "name", "role", "is_active"} <= data.keys()
    assert data["email"] == "admin@agentescala.com"
    assert data["role"] == "admin"
    assert data["is_active"] is True


# ─────────────────────────────────────────────────────────────────────────────
# USERS router
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_cria_usuario_retorna_201(client, admin_headers):
    """Admin cria novo usuário com payload válido; resposta não expõe a senha."""
    resp = client.post(
        "/users/",
        headers=admin_headers,
        json={
            "email": "novo@agentescala.com",
            "name": "Novo Médico",
            "password": "senha_forte_123",
            "role": "agent",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "novo@agentescala.com"
    assert data["role"] == "agent"
    assert "id" in data
    assert "hashed_password" not in data  # senha nunca exposta na resposta


def test_agente_nao_pode_criar_usuario(client, agent_headers):
    """Agente não tem permissão para criar usuários — deve receber 403."""
    resp = client.post(
        "/users/",
        headers=agent_headers,
        json={"email": "hack@agentescala.com", "name": "X", "password": "x"},
    )
    assert resp.status_code == 403


def test_email_duplicado_retorna_400(client, admin_headers):
    """Tentativa de cadastrar e-mail já existente retorna 400."""
    resp = client.post(
        "/users/",
        headers=admin_headers,
        json={
            "email": "alice@agentescala.com",  # já existe no seed
            "name": "Duplicado",
            "password": "qualquer",
        },
    )
    assert resp.status_code == 400


def test_listar_agentes_retorna_somente_role_agent(client, agent_headers):
    """GET /users/agents lista apenas usuários com role=agent; admin não aparece."""
    resp = client.get("/users/agents", headers=agent_headers)
    assert resp.status_code == 200
    agents = resp.json()
    assert len(agents) >= 1
    assert all(a["role"] == "agent" for a in agents)
    emails = {a["email"] for a in agents}
    assert "admin@agentescala.com" not in emails


def test_admin_busca_usuario_por_id(client, admin_headers):
    """Admin obtém qualquer usuário pelo ID."""
    alice_id = _user_id(client, admin_headers, "alice@agentescala.com")
    resp = client.get(f"/users/{alice_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "alice@agentescala.com"


def test_agente_nao_pode_ver_outro_usuario(client, agent_headers, admin_headers):
    """Agente não pode consultar o perfil de outro usuário — deve receber 403."""
    admin_id = _user_id(client, admin_headers, "admin@agentescala.com")
    resp = client.get(f"/users/{admin_id}", headers=agent_headers)
    assert resp.status_code == 403


def test_usuario_inexistente_retorna_404(client, admin_headers):
    """Busca de ID inexistente retorna 404."""
    resp = client.get("/users/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_admin_desativa_usuario(client, admin_headers):
    """Admin desativa usuário (soft delete): DELETE → 204; GET posterior → is_active=False."""
    bob_id = _user_id(client, admin_headers, "bob@agentescala.com")

    del_resp = client.delete(f"/users/{bob_id}", headers=admin_headers)
    assert del_resp.status_code == 204

    # Registro ainda existe, mas marcado como inativo
    get_resp = client.get(f"/users/{bob_id}", headers=admin_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


# ─────────────────────────────────────────────────────────────────────────────
# SHIFTS router
# Listagem e get individual já exercidos em test_api.py; aqui cobrimos
# criação, permissões, filtro por agente, atualização e exclusão.
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_cria_shift_retorna_201(client, admin_headers):
    """Admin cria turno com payload válido; response contém id e agent_id corretos."""
    alice_id = _user_id(client, admin_headers, "alice@agentescala.com")
    resp = client.post(
        "/shifts/",
        headers=admin_headers,
        json={
            "agent_id": alice_id,
            "start_time": "2026-05-01T08:00:00",
            "end_time": "2026-05-01T16:00:00",
            "title": "Plantão Especial",
            "location": "UTI",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["agent_id"] == alice_id
    assert data["title"] == "Plantão Especial"
    assert "id" in data


def test_agente_nao_pode_criar_shift(client, agent_headers, admin_headers):
    """Agente não tem permissão para criar turnos — deve receber 403."""
    alice_id = _user_id(client, admin_headers, "alice@agentescala.com")
    resp = client.post(
        "/shifts/",
        headers=agent_headers,
        json={
            "agent_id": alice_id,
            "start_time": "2026-05-01T08:00:00",
            "end_time": "2026-05-01T16:00:00",
        },
    )
    assert resp.status_code == 403


def test_listar_shifts_inclui_agent_embutido(client, agent_headers):
    """GET /shifts/ retorna objetos com campo agent populado (usado pela Web UI)."""
    resp = client.get("/shifts", headers=agent_headers)
    assert resp.status_code == 200
    shifts = resp.json()
    assert len(shifts) >= 1
    for shift in shifts:
        assert "agent" in shift
        assert shift["agent"] is not None
        assert "email" in shift["agent"]


def test_listar_shifts_por_agente(client, agent_headers, admin_headers):
    """GET /shifts/agent/{id} retorna apenas os turnos daquele agente."""
    alice_id = _user_id(client, admin_headers, "alice@agentescala.com")
    resp = client.get(f"/shifts/agent/{alice_id}", headers=agent_headers)
    assert resp.status_code == 200
    shifts = resp.json()
    assert len(shifts) >= 1
    assert all(s["agent_id"] == alice_id for s in shifts)


def test_shift_inexistente_retorna_404(client, admin_headers):
    """GET /shifts/{id} com ID inválido retorna 404."""
    resp = client.get("/shifts/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_admin_atualiza_shift(client, admin_headers, agent_headers):
    """Admin altera o título de um turno; resposta reflete a mudança."""
    shift = _shift_of(client, agent_headers, "alice@agentescala.com")
    resp = client.patch(
        f"/shifts/{shift['id']}",
        headers=admin_headers,
        json={"title": "Turno Atualizado"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Turno Atualizado"


def test_admin_deleta_shift(client, admin_headers, agent_headers):
    """Admin exclui turno: DELETE → 204; GET posterior → 404."""
    shift = _shift_of(client, agent_headers, "alice@agentescala.com")

    del_resp = client.delete(f"/shifts/{shift['id']}", headers=admin_headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/shifts/{shift['id']}", headers=admin_headers)
    assert get_resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# SWAPS router
# Criação + aprovação + reassignment já cobertos em test_api.py; aqui cobrimos
# acesso a pendentes, rejeição, cancelamento e restrições por papel.
# ─────────────────────────────────────────────────────────────────────────────

def test_swaps_pendentes_exige_admin(client, agent_headers):
    """GET /swaps/pending recusa agentes com 403."""
    resp = client.get("/swaps/pending", headers=agent_headers)
    assert resp.status_code == 403


def test_admin_lista_swaps_pendentes(client, admin_headers, agent_headers):
    """Admin vê swap recém-criado em GET /swaps/pending."""
    swap = _create_swap(client, agent_headers, admin_headers)
    resp = client.get("/swaps/pending", headers=admin_headers)
    assert resp.status_code == 200
    ids = [s["id"] for s in resp.json()]
    assert swap["id"] in ids


def test_admin_rejeita_swap(client, admin_headers, agent_headers):
    """Admin rejeita solicitação; status muda para 'rejected' e admin_notes é gravado."""
    swap = _create_swap(client, agent_headers, admin_headers)
    resp = client.post(
        f"/swaps/{swap['id']}/reject",
        headers=admin_headers,
        json={"admin_notes": "turnos incompatíveis"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "rejected"
    assert data["admin_notes"] == "turnos incompatíveis"


def test_solicitante_cancela_proprio_swap(client, agent_headers, admin_headers):
    """Solicitante cancela sua própria solicitação pendente; status muda para 'cancelled'."""
    swap = _create_swap(client, agent_headers, admin_headers)
    resp = client.post(f"/swaps/{swap['id']}/cancel", headers=agent_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_nao_solicitante_nao_pode_cancelar(client, bob_headers, agent_headers, admin_headers):
    """Bob é alvo da troca, não o solicitante; tentar cancelar retorna 400."""
    swap = _create_swap(client, agent_headers, admin_headers)
    resp = client.post(f"/swaps/{swap['id']}/cancel", headers=bob_headers)
    assert resp.status_code == 400
