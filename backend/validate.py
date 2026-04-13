import os
import sys

import httpx

DEFAULT_BASE_URL = os.getenv("AGENTESCALA_BASE_URL", "http://127.0.0.1:18000")
ADMIN_EMAIL = os.getenv("AGENTESCALA_ADMIN_EMAIL", "admin@agentescala.com")
ADMIN_PASSWORD = os.getenv("AGENTESCALA_ADMIN_PASSWORD", "password123")
AGENT_EMAIL = os.getenv("AGENTESCALA_AGENT_EMAIL", "alice@agentescala.com")
AGENT_PASSWORD = os.getenv("AGENTESCALA_AGENT_PASSWORD", "password123")


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    response.raise_for_status()
    return response.json()["access_token"]


def validate_runtime() -> bool:
    """Validar o runtime HTTP do AgentEscala contra uma instância real em execução."""

    print("=== Validação HTTP do AgentEscala ===\n")

    try:
        with httpx.Client(base_url=DEFAULT_BASE_URL, timeout=20.0, follow_redirects=True) as client:
            print(f"1. Verificando healthcheck em {DEFAULT_BASE_URL}/health ...")
            health_response = client.get("/health")
            health_response.raise_for_status()
            health_payload = health_response.json()
            assert health_payload["status"] == "healthy"
            print("   ✓ Healthcheck respondeu corretamente\n")

            print("2. Autenticando admin e agente seed...")
            admin_token = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
            agent_token = login(client, AGENT_EMAIL, AGENT_PASSWORD)
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            agent_headers = {"Authorization": f"Bearer {agent_token}"}
            print("   ✓ Login admin e agente funcionando\n")

            print("3. Validando rota protegida /auth/me ...")
            me_response = client.get("/auth/me", headers=agent_headers)
            me_response.raise_for_status()
            me_payload = me_response.json()
            assert me_payload["email"] == AGENT_EMAIL
            print("   ✓ JWT e resolução de usuário autenticado OK\n")

            print("4. Validando exportações de turnos...")
            excel_response = client.get("/shifts/export/excel", headers=agent_headers)
            excel_response.raise_for_status()
            assert "spreadsheetml" in excel_response.headers["content-type"]

            ics_response = client.get("/shifts/export/ics", headers=agent_headers)
            ics_response.raise_for_status()
            assert "text/calendar" in ics_response.headers["content-type"]
            print("   ✓ Exportações Excel e ICS OK\n")

            print("5. Validando fluxo real de swap com approve admin...")
            shifts_response = client.get("/shifts/", headers=agent_headers)
            shifts_response.raise_for_status()
            shifts = shifts_response.json()

            origin_shift = next(
                shift for shift in shifts
                if shift["agent"]["email"] == AGENT_EMAIL
            )
            target_shift = next(
                shift for shift in shifts
                if shift["agent"]["email"] != AGENT_EMAIL
            )

            create_swap_response = client.post(
                "/swaps/",
                headers=agent_headers,
                json={
                    "target_agent_id": target_shift["agent_id"],
                    "origin_shift_id": origin_shift["id"],
                    "target_shift_id": target_shift["id"],
                    "reason": "Validação runtime CT102",
                },
            )
            create_swap_response.raise_for_status()
            swap_payload = create_swap_response.json()

            forbidden_approve = client.post(
                f"/swaps/{swap_payload['id']}/approve",
                headers=agent_headers,
                json={"admin_notes": "não deveria aprovar"},
            )
            assert forbidden_approve.status_code == 403

            approve_response = client.post(
                f"/swaps/{swap_payload['id']}/approve",
                headers=admin_headers,
                json={"admin_notes": "Aprovado na validação runtime"},
            )
            approve_response.raise_for_status()
            approved_payload = approve_response.json()
            assert approved_payload["status"] == "approved"

            updated_origin_shift = client.get(
                f"/shifts/{origin_shift['id']}",
                headers=agent_headers,
            )
            updated_origin_shift.raise_for_status()
            assert updated_origin_shift.json()["agent_id"] == target_shift["agent_id"]
            print("   ✓ Fluxo de swap com restrição admin OK\n")

            print("6. Validando exportação administrativa de swaps...")
            swap_export_response = client.get("/swaps/export/excel", headers=admin_headers)
            swap_export_response.raise_for_status()
            assert "spreadsheetml" in swap_export_response.headers["content-type"]
            print("   ✓ Exportação de swaps OK\n")

            print("7. Validando endpoint de métricas simples...")
            metrics_response = client.get("/metrics")
            metrics_response.raise_for_status()
            assert "agentescala_http_requests_total" in metrics_response.text
            print("   ✓ Endpoint de métricas OK\n")

        print("=== Validação Concluída ===\n")
        print("✓ Healthcheck: OK")
        print("✓ Login JWT: OK")
        print("✓ Rotas protegidas: OK")
        print("✓ Exportações Excel/ICS: OK")
        print("✓ Fluxo de swap: OK")
        print("✓ Métricas simples: OK")
        return True

    except Exception as exc:
        print(f"\n✗ Falha na validação runtime: {exc}")
        return False


if __name__ == "__main__":
    success = validate_runtime()
    sys.exit(0 if success else 1)
