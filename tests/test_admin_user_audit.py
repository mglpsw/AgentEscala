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
