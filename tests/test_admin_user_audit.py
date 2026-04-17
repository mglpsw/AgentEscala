import json

from fastapi.testclient import TestClient


def test_admin_status_change_generates_audit_log(client: TestClient, admin_headers):
    target = client.get('/admin/users', headers=admin_headers).json()[1]

    response = client.patch(
        f"/admin/users/{target['id']}/status",
        headers=admin_headers,
        json={'is_active': False},
    )
    assert response.status_code == 200

    audit = client.get('/admin/audit/users', headers=admin_headers)
    assert audit.status_code == 200
    entries = audit.json()
    assert len(entries) >= 1
    assert entries[0]['action'] == 'admin_user_status_change'
    assert entries[0]['target_user_id'] == target['id']
    assert json.loads(entries[0]['change_summary'])['is_active'] is False


def test_admin_create_and_update_generates_audit_log(client: TestClient, admin_headers):
    create = client.post(
        '/admin/users',
        headers=admin_headers,
        json={
            'name': 'Auditoria Teste',
            'email': 'audit.teste@agentescala.com',
            'password': 'CHANGE_ME_TEST_PASSWORD',
            'role': 'medico',
            'is_active': True,
        },
    )
    assert create.status_code == 201
    created = create.json()

    update = client.put(
        f"/admin/users/{created['id']}",
        headers=admin_headers,
        json={'name': 'Auditado', 'password': 'CHANGE_ME_UPDATED_PASSWORD'},
    )
    assert update.status_code == 200

    audit = client.get('/admin/audit/users', headers=admin_headers)
    assert audit.status_code == 200
    entries = audit.json()
    actions = [entry['action'] for entry in entries]
    assert 'admin_user_create' in actions
    assert 'admin_user_update' in actions

    update_entry = next(entry for entry in entries if entry['action'] == 'admin_user_update')
    update_summary = json.loads(update_entry['change_summary'])
    assert update_summary['name'] == 'Auditado'
    assert update_summary['password_changed'] is True
    assert 'password' not in update_summary


def test_non_admin_cannot_list_user_audit_logs(client: TestClient, agent_headers):
    response = client.get('/admin/audit/users', headers=agent_headers)
    assert response.status_code == 403


def test_admin_audit_supports_action_filter(client: TestClient, admin_headers):
    created = client.post(
        '/admin/users',
        headers=admin_headers,
        json={
            'name': 'Filtro Action',
            'email': 'filtro.action@agentescala.com',
            'password': 'CHANGE_ME_FILTER_ACTION',
            'role': 'medico',
            'is_active': True,
        },
    )
    assert created.status_code == 201
    created_payload = created.json()

    changed_status = client.patch(
        f"/admin/users/{created_payload['id']}/status",
        headers=admin_headers,
        json={'is_active': False},
    )
    assert changed_status.status_code == 200

    response = client.get(
        '/admin/audit/users?action=admin_user_status_change',
        headers=admin_headers,
    )
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 1
    assert all(entry['action'] == 'admin_user_status_change' for entry in entries)


def test_admin_audit_supports_target_user_id_and_pagination(client: TestClient, admin_headers):
    created = client.post(
        '/admin/users',
        headers=admin_headers,
        json={
            'name': 'Filtro Target',
            'email': 'filtro.target@agentescala.com',
            'password': 'CHANGE_ME_FILTER_TARGET',
            'role': 'medico',
            'is_active': True,
        },
    )
    assert created.status_code == 201
    created_payload = created.json()
    target_user_id = created_payload['id']

    updated = client.put(
        f"/admin/users/{target_user_id}",
        headers=admin_headers,
        json={'name': 'Filtro Target Atualizado'},
    )
    assert updated.status_code == 200

    status_change = client.patch(
        f"/admin/users/{target_user_id}/status",
        headers=admin_headers,
        json={'is_active': False},
    )
    assert status_change.status_code == 200

    filtered = client.get(
        f"/admin/audit/users?target_user_id={target_user_id}",
        headers=admin_headers,
    )
    assert filtered.status_code == 200
    filtered_entries = filtered.json()
    assert len(filtered_entries) >= 2
    assert all(entry['target_user_id'] == target_user_id for entry in filtered_entries)

    page = client.get(
        f"/admin/audit/users?target_user_id={target_user_id}&limit=1&skip=1",
        headers=admin_headers,
    )
    assert page.status_code == 200
    page_entries = page.json()
    assert len(page_entries) == 1
