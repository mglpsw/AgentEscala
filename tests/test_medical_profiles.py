"""Testes dos endpoints de perfis médicos."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def bob_headers(client: TestClient):
    """Token JWT de Bob para validar duplicidades entre usuários."""
    resp = client.post(
        "/auth/login",
        json={"email": "bob@agentescala.com", "password": "CHANGE_ME_TEST_PASSWORD"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _profile_payload(cpf="12345678901", crm_numero="12345", crm_uf="RS"):
    return {
        "nome_completo": "Alice Silva",
        "cpf": cpf,
        "crm_numero": crm_numero,
        "crm_uf": crm_uf,
        "data_nascimento": "1985-05-20",
        "cartao_nacional_saude": "700000000000001",
        "email_profissional": "alice.medica@agentescala.com",
        "telefone": "+5551999999999",
        "endereco": "Rua Exemplo, 100",
        "rg": "1234567890",
        "rg_orgao_emissor": "SSP",
        "rg_data_emissao": "2005-01-10",
        "crm_data_emissao": "2012-02-20",
        "arquivo_vacinacao": "/documentos/vacinacao/alice.pdf",
    }


def _create_profile(client, headers, **overrides):
    payload = _profile_payload(**overrides)
    resp = client.post("/api/v1/medical-profiles/", headers=headers, json=payload)
    assert resp.status_code == 201
    return resp.json()


def _current_user_id(client, headers):
    resp = client.get("/auth/me", headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


def test_usuario_cria_e_consulta_proprio_perfil_medico(client, agent_headers):
    """Usuário autenticado cria e consulta seu próprio perfil médico."""
    created = _create_profile(client, agent_headers)
    assert created["cpf"] == "12345678901"
    assert created["crm_uf"] == "RS"

    resp = client.get("/api/v1/medical-profiles/me", headers=agent_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_duplicidade_cpf_retorna_400(client, agent_headers, bob_headers):
    """CPF é identificador administrativo único."""
    _create_profile(client, agent_headers, cpf="12345678901", crm_numero="12345", crm_uf="RS")

    resp = client.post(
        "/api/v1/medical-profiles/",
        headers=bob_headers,
        json=_profile_payload(cpf="12345678901", crm_numero="67890", crm_uf="SC"),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Já existe perfil médico com este CPF."


def test_duplicidade_crm_uf_retorna_400(client, agent_headers, bob_headers):
    """CRM combinado com UF é único entre perfis médicos."""
    _create_profile(client, agent_headers, cpf="12345678901", crm_numero="12345", crm_uf="RS")

    resp = client.post(
        "/api/v1/medical-profiles/",
        headers=bob_headers,
        json=_profile_payload(cpf="22222222222", crm_numero="12345", crm_uf="RS"),
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Já existe perfil médico com este CRM e UF."


def test_rota_admin_recusa_usuario_comum(client, agent_headers):
    """Usuário comum não pode listar perfis médicos administrativos."""
    resp = client.get("/api/v1/medical-profiles/", headers=agent_headers)
    assert resp.status_code == 403


def test_rota_me_exige_autenticacao(client):
    """Perfis médicos não podem ser acessados sem JWT."""
    resp = client.get("/api/v1/medical-profiles/me")
    assert resp.status_code == 401


def test_admin_lista_edita_e_remove_perfil(client, agent_headers, admin_headers):
    """Admin tem governança completa sobre perfis médicos."""
    created = _create_profile(client, agent_headers)

    list_resp = client.get("/api/v1/medical-profiles/", headers=admin_headers)
    assert list_resp.status_code == 200
    assert any(profile["id"] == created["id"] for profile in list_resp.json())

    detail_resp = client.get(f"/api/v1/medical-profiles/{created['id']}", headers=admin_headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["cpf"] == created["cpf"]

    update_resp = client.put(
        f"/api/v1/medical-profiles/{created['id']}",
        headers=admin_headers,
        json={"telefone": "+5551888888888"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["telefone"] == "+5551888888888"

    delete_resp = client.delete(f"/api/v1/medical-profiles/{created['id']}", headers=admin_headers)
    assert delete_resp.status_code == 204

    missing_resp = client.get(f"/api/v1/medical-profiles/{created['id']}", headers=admin_headers)
    assert missing_resp.status_code == 404


def test_export_json_inclui_dados_medicos_quando_perfil_existe(client, agent_headers, admin_headers):
    """Exportação JSON usa MedicalProfile sem quebrar fallback atual de escala."""
    _create_profile(client, agent_headers, crm_numero="54321", crm_uf="SP")
    alice_id = _current_user_id(client, agent_headers)

    shift_resp = client.post(
        "/shifts/",
        headers=admin_headers,
        json={
            "agent_id": alice_id,
            "start_time": "2032-06-10T08:00:00",
            "end_time": "2032-06-10T16:00:00",
            "title": "Plantão Identidade Médica",
            "location": "PA Teste",
        },
    )
    assert shift_resp.status_code == 201

    export_resp = client.get(
        "/shifts/export/final/json?start_date=2032-06-10&end_date=2032-06-10",
        headers=agent_headers,
    )
    assert export_resp.status_code == 200
    medico = export_resp.json()["shifts"][0]["medico"]
    assert medico == {
        "nome": "Alice Silva",
        "crm": "54321",
        "uf": "SP",
    }
