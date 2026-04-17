from fastapi.testclient import TestClient


def test_admin_users_requires_admin(client: TestClient, agent_headers):
    response = client.get('/admin/users', headers=agent_headers)
    assert response.status_code == 403


def test_admin_crud_users(client: TestClient, admin_headers):
    create = client.post(
        '/admin/users',
        headers=admin_headers,
        json={
            'name': 'Financeiro Teste',
            'email': 'financeiro@agentescala.com',
            'password': 'CHANGE_ME_TEST_PASSWORD',
            'role': 'financeiro',
            'is_active': True,
        },
    )
    assert create.status_code == 201
    created = create.json()
    user_id = created['id']
    assert created['role'] == 'financeiro'

    list_response = client.get('/admin/users', headers=admin_headers)
    assert list_response.status_code == 200
    assert any(user['email'] == 'financeiro@agentescala.com' for user in list_response.json())

    update = client.put(
        f'/admin/users/{user_id}',
        headers=admin_headers,
        json={
            'name': 'Médico Editado',
            'email': 'medico.editado@agentescala.com',
            'role': 'medico',
            'is_active': False,
            'password': 'CHANGE_ME_UPDATED_PASSWORD',
        },
    )
    assert update.status_code == 200
    updated = update.json()
    assert updated['name'] == 'Médico Editado'
    assert updated['email'] == 'medico.editado@agentescala.com'
    assert updated['role'] == 'medico'
    assert updated['is_active'] is False

    delete = client.delete(f'/admin/users/{user_id}', headers=admin_headers)
    assert delete.status_code == 204


def test_admin_cannot_delete_self(client: TestClient, admin_headers):
    me = client.get('/auth/me', headers=admin_headers)
    assert me.status_code == 200
    my_id = me.json()['id']

    response = client.delete(f'/admin/users/{my_id}', headers=admin_headers)
    assert response.status_code == 400


def test_logout_accepts_missing_or_invalid_token(client: TestClient):
    response = client.post('/auth/logout', json={})
    assert response.status_code == 200

    response_invalid = client.post('/auth/logout', json={'refresh_token': 'invalido'})
    assert response_invalid.status_code == 200
